"""Automated verification suite for Travel Itinerary Builder."""
import os
import unittest
import json
from pipeline.state import create_initial_state
from pipeline.gemini_service import GeminiService
from pipeline.parallel_agent import ParallelAgent
from pipeline.loop_agent import LoopAgent, Scheduler, BudgetEnforcer
from pipeline.orchestrator import PipelineOrchestrator
from services.tracker import Tracker
from services.export_service import generate_text_itinerary, generate_pdf_itinerary
from app import app
import config

class TestItineraryPipeline(unittest.TestCase):
    def setUp(self):
        self.run_id = "test_run_123"
        self.gemini = GeminiService(self.run_id)

    def test_global_state_schema(self):
        """Validates that Global State strictly conforms to SPECIFICATIONS.md schema."""
        state = create_initial_state(
            destination="Rome, Italy",
            budget=1500.0,
            days=4,
            interests=["Architecture", "Food"],
            origin="New York, USA"
        )
        self.assertIn("user_input", state)
        self.assertIn("raw_research", state)
        self.assertIn("current_itinerary", state)
        self.assertIn("critic_feedback", state)
        self.assertIn("budget_approved", state)

        # Check raw_research subfields
        self.assertIn("flights", state["raw_research"])
        self.assertIn("hotels", state["raw_research"])
        self.assertIn("activities", state["raw_research"])

        # Check user_input subfields
        self.assertEqual(state["user_input"]["destination"], "Rome, Italy")
        self.assertEqual(state["user_input"]["budget"], 1500.0)
        self.assertEqual(state["user_input"]["days"], 4)
        self.assertEqual(state["budget_approved"], False)

    def test_parallel_agent_execution(self):
        """Verifies ParallelAgent executes discovery concurrently and updates state."""
        state = create_initial_state(
            destination="Barcelona, Spain",
            budget=1200.0,
            days=3,
            interests=["Art", "Beach"],
            origin="London, UK"
        )
        agent = ParallelAgent(self.gemini, self.run_id)
        updated_state = agent.execute(state)

        self.assertTrue(len(updated_state["raw_research"]["flights"]) > 0)
        self.assertTrue(len(updated_state["raw_research"]["hotels"]) > 0)
        self.assertTrue(len(updated_state["raw_research"]["activities"]) > 0)

    def test_loop_agent_refinement_and_budget_approval(self):
        """Verifies LoopAgent runs Scheduler and BudgetEnforcer with critic feedback."""
        state = create_initial_state(
            destination="Paris, France",
            budget=2500.0,  # Generous budget
            days=3,
            interests=["Art", "Pastries"],
            origin="New York, USA"
        )
        # Populate mock research
        state["raw_research"]["flights"] = [
            {"carrier": "AirFrance", "route": "Direct", "travel_time_hours": 7.5, "estimated_cost": 450.0, "tier": "Economy"}
        ]
        state["raw_research"]["hotels"] = [
            {"name": "Hotel Louvre", "neighborhood": "1st Arr.", "nightly_rate": 180.0, "tier": "Comfort"}
        ]
        state["raw_research"]["activities"] = [
            {"name": "Louvre Tour", "neighborhood": "1st Arr.", "category": "Museum", "estimated_cost": 25.0, "duration_hours": 3.0}
        ]

        loop_agent = LoopAgent(self.gemini, self.run_id, max_iterations=3)
        final_state = loop_agent.execute(state)

        self.assertTrue(final_state["budget_approved"])
        self.assertIn("schedule", final_state["current_itinerary"])
        self.assertTrue(final_state["current_itinerary"]["total_estimated_cost"] <= 2500.0)

    def test_graceful_failure_handling_tight_budget(self):
        """Verifies pipeline does not crash on impossible budgets ($5 for 5 days)."""
        orchestrator = PipelineOrchestrator(run_id="impossible_budget_test")
        result = orchestrator.run(
            origin="NYC",
            destination="Tokyo, Japan",
            days=5,
            budget=5.0,  # Structurally impossible budget
            interests=["Culture"]
        )
        self.assertTrue(result["success"])  # Pipeline executed cleanly without exception
        self.assertFalse(result["state"]["budget_approved"])  # Marked as budget exceeded
        self.assertIn("tight or insufficient", result["state"]["critic_feedback"].lower())

    def test_tracker_artifact_logging(self):
        """Verifies usages.csv and events.json tracking and metric queries."""
        test_run = "tracker_test_run"
        Tracker.record_event(test_run, "test_event", "TestAgent", "Unit test summary", {"key": "val"})
        Tracker.record_usage(
            run_id=test_run,
            origin="SF",
            destination="Hawaii",
            days=4,
            budget=1500.0,
            estimated_cost=1400.0,
            budget_approved=True,
            status="success",
            iterations=1,
            events_count=3
        )

        metrics = Tracker.get_metrics()
        self.assertGreaterEqual(metrics["total_itineraries"], 1)
        self.assertGreaterEqual(metrics["total_events"], 1)

        run_events = Tracker.get_events_for_run(test_run)
        self.assertTrue(len(run_events) >= 1)
        self.assertEqual(run_events[0]["agent_source"], "TestAgent")
        self.assertEqual(run_events[0]["payload"], {"key": "val"})

        # Verify each event log in events.json is on a single line
        with open(config.EVENTS_JSON, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if line_str:
                    ev_obj = json.loads(line_str)
                    self.assertIsInstance(ev_obj, dict)
                    self.assertIn("event_id", ev_obj)
                    self.assertIn("payload", ev_obj)

    def test_export_service(self):
        """Verifies text and PDF generators."""
        state = create_initial_state("Vienna, Austria", 1200, 3, ["Classical Music"])
        state["current_itinerary"] = {
            "total_estimated_cost": 850.0,
            "selected_flight": {"carrier": "Austrian Air", "estimated_cost": 300.0},
            "selected_hotel": {"name": "Grand Hotel", "nightly_rate": 120.0, "neighborhood": "Old Town"},
            "cost_breakdown": {"flight": 300.0, "lodging": 360.0, "activities": 190.0},
            "schedule": [
                {
                    "day": 1,
                    "neighborhood_focus": "Innere Stadt",
                    "insider_tip": "Visit St. Stephen at morning light.",
                    "events": [
                        {"name": "Opera House Tour", "time_slot": "Morning", "category": "Culture", "estimated_cost": 20.0}
                    ]
                }
            ]
        }
        text_out = generate_text_itinerary(state)
        self.assertIn("VIENNA, AUSTRIA", text_out)
        self.assertIn("Opera House Tour", text_out)

        pdf_buf = generate_pdf_itinerary(state)
        self.assertGreater(pdf_buf.getbuffer().nbytes, 100)

    def test_flask_endpoints(self):
        """Verifies web application endpoints."""
        client = app.test_client()

        # Test Main Page
        res = client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"WanderAI", res.data)

        # Test History Endpoint
        res = client.get("/api/history")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("metrics", data)
        self.assertIn("itineraries", data)

        # Test Generate API
        res = client.post("/api/generate", json={
            "origin": "Seattle, USA",
            "destination": "Vancouver, Canada",
            "duration": 2,
            "budget": 800,
            "interests": "Coffee, Mountains"
        })
        self.assertEqual(res.status_code, 200)
        gen_data = res.get_json()
        self.assertTrue(gen_data["success"])
        run_id = gen_data["run_id"]

        # Test Events for Run
        res = client.get(f"/api/events/{run_id}")
        self.assertEqual(res.status_code, 200)
        ev_data = res.get_json()
        self.assertTrue(len(ev_data["events"]) > 0)

        # Test TXT and PDF Downloads
        res_txt = client.get(f"/download/txt/{run_id}")
        self.assertEqual(res_txt.status_code, 200)

        res_pdf = client.get(f"/download/pdf/{run_id}")
        self.assertEqual(res_pdf.status_code, 200)

if __name__ == "__main__":
    unittest.main()
