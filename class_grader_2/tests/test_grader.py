import os
import unittest
import tempfile
import json
from core.storage import ScoreStorage
from core.spec_parser import SpecParser
from core.grader import Grader
from core.models import EvaluationResult, CriterionResult
from core.telemetry import TelemetryTracer


class TestGraderApp(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.scores_path = os.path.join(self.temp_dir.name, "outputs", "scores.json")
        self.storage = ScoreStorage(self.scores_path)
        self.grader = Grader(scores_file=self.scores_path)
        self.tracer = TelemetryTracer(output_dir=os.path.join(self.temp_dir.name, "outputs"))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_single_line_json_storage(self):
        """Verify that every submission is stored as exactly one single line in outputs/scores.json."""
        sub1 = self.storage.add_submission("Alice", "/path/a", 95.0, "A")
        sub2 = self.storage.add_submission("Bob", "/path/b", 70.0, "C-")

        with open(self.scores_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]

        self.assertEqual(len(lines), 2)
        for line in lines:
            parsed = json.loads(line)
            self.assertIn("student_name", parsed)
            self.assertIn("score", parsed)
            self.assertIn("id", parsed)

    def test_instructor_student_summary_and_drilldown(self):
        """Verify instructor view summarizes highest score, latest score, and filters by student."""
        self.storage.add_submission("Alice", "/path/a1", 75.0, "C")
        self.storage.add_submission("Alice", "/path/a2", 98.0, "A+")
        self.storage.add_submission("Bob", "/path/b1", 82.0, "B-")

        summaries = self.storage.get_instructor_student_summaries()
        self.assertEqual(len(summaries), 2)

        alice_summary = next(s for s in summaries if s.student_name == "Alice")
        self.assertEqual(alice_summary.highest_score, 98.0)
        self.assertEqual(alice_summary.latest_score, 98.0)
        self.assertEqual(alice_summary.total_submissions, 2)

        alice_subs = self.storage.get_submissions_for_student("Alice")
        self.assertEqual(len(alice_subs), 2)
        self.assertEqual(alice_subs[0].folder_name, "/path/a2")

    def test_telemetry_tracing(self):
        """Verify telemetry tracer records model calls, responses, skill usages, and tool invocations."""
        tid = self.tracer.start_trace("Test Student", "/test/folder")
        
        # Log skill usage
        self.tracer.log_skill_usage(tid, "SpecParser", {"folder": "/test/folder"}, {"criteria": 5}, duration_ms=12.5)
        
        # Log tool invocation and response
        tool_id = self.tracer.log_tool_invocation(tid, "DynamicRunner.run_tests", {"path": "/test"})
        self.tracer.log_tool_response(tid, "DynamicRunner.run_tests", {"passed": True}, duration_ms=45.0, tool_call_id=tool_id)
        
        # Log model call and response
        self.tracer.log_model_call(tid, "gemini-2.5-flash", "test prompt")
        self.tracer.log_model_response(tid, "gemini-2.5-flash", {"text": "score: 100"}, duration_ms=1200.0, status_code=200)
        
        # Finish trace
        self.tracer.finish_trace(tid, 100.0, "A+", "Great job")
        
        events = self.tracer.get_trace_history()
        self.assertGreaterEqual(len(events), 5)
        event_types = [e["event_type"] for e in events]
        self.assertIn("MODEL_CALL", event_types)
        self.assertIn("MODEL_RESPONSE", event_types)
        self.assertIn("SKILL_USAGE", event_types)
        self.assertIn("TOOL_INVOCATION", event_types)
        self.assertIn("TOOL_RESPONSE", event_types)

    def test_grade_alice_perfect(self):
        """Alice's submission should score high (>=90%) or return grader unavailable message when rate limited."""
        folder = os.path.join(os.path.dirname(__file__), "..", "sample_submissions", "student_alice_perfect")
        try:
            sub, res = self.grader.grade_submission("Alice Johnson", folder)
            self.assertGreaterEqual(res.percentage_score, 90.0)
            self.assertIn(res.letter_grade, ["A+", "A", "A-"])
            self.assertTrue(any(c.status == "PASS" for c in res.criteria))
        except RuntimeError as e:
            self.assertIn("The grader is not available at this time", str(e))


    def test_spec_file_name_variants(self):
        """Verify SpecParser finds SPECIFICATION.md, SPECIFICATIONS.md, SPEC.md, SPECS.md in upper/lower case."""
        variants = ["SPECIFICATION.md", "SPECIFICATIONS.md", "SPEC.md", "SPECS.md", "specification.md", "specs.md", "spec.md"]
        for v in variants:
            with tempfile.TemporaryDirectory() as tmpdir:
                with open(os.path.join(tmpdir, v), "w", encoding="utf-8") as f:
                    f.write("# Sample Spec\n### Requirements\n- Feature 1\n- Feature 2")
                parser = SpecParser(tmpdir)
                self.assertIsNotNone(parser.spec_file_path, f"Failed to find {v}")
                self.assertEqual(os.path.basename(parser.spec_file_path).lower(), v.lower())
    def test_submissions_config_and_mandatory_criteria(self):
        """Verify SUBMISSIONS.yaml loads and mandatory criteria are placed at top of list."""
        from core.submissions_config import SubmissionsConfig
        
        yaml_content = """
Agent Engineering:
  my_first_agent_app:
    - Code Uses AI Agent: 30%
    - Code Uses Skills in Agent: 20%
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            yaml_path = f.name

        try:
            cfg = SubmissionsConfig(yaml_path)
            self.assertIn("Agent Engineering", cfg.get_classes())
            self.assertIn("my_first_agent_app", cfg.get_assignments("Agent Engineering"))
            crits = cfg.get_criteria("Agent Engineering", "my_first_agent_app")
            self.assertEqual(len(crits), 2)
            self.assertEqual(crits[0]["weight_percent"], 30.0)
            self.assertEqual(crits[1]["weight_percent"], 20.0)

            # Test parser prepending
            with tempfile.TemporaryDirectory() as tmpdir:
                with open(os.path.join(tmpdir, "SPECIFICATIONS.md"), "w") as sf:
                    sf.write("# Spec\n### Tasks\n- Task 1\n- Task 2")
                
                # Mock submissions_config in spec_parser
                from core import spec_parser
                original_cfg = spec_parser.submissions_config
                spec_parser.submissions_config = cfg

                try:
                    parser = SpecParser(tmpdir, class_name="Agent Engineering", assignment_name="my_first_agent_app")
                    parsed_crits = parser.parse_criteria()
                    
                    # Mandatory criteria must be at the very top
                    self.assertTrue(parsed_crits[0].is_mandatory)
                    self.assertIn("Code Uses AI Agent", parsed_crits[0].title)
                    self.assertEqual(parsed_crits[0].weight, 30.0)
                    
                    self.assertTrue(parsed_crits[1].is_mandatory)
                    self.assertIn("Code Uses Skills in Agent", parsed_crits[1].title)
                    self.assertEqual(parsed_crits[1].weight, 20.0)
                finally:
                    spec_parser.submissions_config = original_cfg
        finally:
            if os.path.exists(yaml_path):
                os.remove(yaml_path)


    def test_script_ast_evidence_analysis(self):
        """Verify CodebaseSnapshot extracts script evidence for AI Agent calls, Skills, and RAG."""
        from core.code_analyzer import CodebaseSnapshot
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. Python script with AI Agent call and Tool registration
            py_code = """
import os
from google.genai import types
from google.genai import Client

class TravelPlannerAgent:
    def __init__(self):
        self.client = Client()
    
    def generate_plan(self, prompt: str):
        return self.client.models.generate_content(
            model="gemini-2.5",
            contents=prompt,
            config=types.GenerateContentConfig(tools=[self.weather_tool])
        )

    def weather_tool(self, city: str):
        return {"temp": "72F"}
"""
            with open(os.path.join(tmpdir, "agent_pipeline.py"), "w") as f:
                f.write(py_code)

            # 2. Skill folder with SKILL.md
            skill_dir = os.path.join(tmpdir, "skills", "weather-fetcher")
            os.makedirs(skill_dir, exist_ok=True)
            with open(os.path.join(skill_dir, "SKILL.md"), "w") as f:
                f.write("---\nname: weather-fetcher\ndescription: Fetches city weather\n---\n# Instructions")

            snap = CodebaseSnapshot(tmpdir)
            
            # Check AI Agent evidence
            self.assertTrue(snap.has_genuine_ai_agent)
            self.assertGreater(len(snap.genuine_ai_calls), 0)

            # Check Skills evidence
            self.assertGreater(len(snap.skills_evidence), 0)
            skill_types = [e["type"] for e in snap.skills_evidence]
            self.assertIn("SKILL_FILE", skill_types)

            report = snap.get_deep_analysis_report()
            self.assertIn("GENUINE AI MODEL & LLM CALLS FOUND", report)

    def test_pseudo_agent_classes_rejection(self):
        """Verify that plain Python classes named 'Agent' without LLM/AI model calls are NOT recognized as AI Agents."""
        from core.code_analyzer import CodebaseSnapshot
        with tempfile.TemporaryDirectory() as tmpdir:
            py_code = """
class WeatherAgent:
    def __init__(self):
        self.data = {"sunny": 75}
    def run(self, city: str):
        return {"temp": self.data.get("sunny", 70)}

class CalendarAgent:
    def run(self):
        return ["event 1"]
"""
            with open(os.path.join(tmpdir, "weather.py"), "w") as f:
                f.write(py_code)

            snap = CodebaseSnapshot(tmpdir)
            self.assertFalse(snap.has_genuine_ai_agent, "Plain Python classes without LLM calls must not qualify as AI agents")
            self.assertEqual(len(snap.genuine_ai_calls), 0)
            self.assertGreater(len(snap.pseudo_agent_classes), 0)

    def test_popular_ai_services_audit(self):
        """Verify CodebaseSnapshot audits Google Gemini and OpenAI for both import and calling/usage."""
        from core.code_analyzer import CodebaseSnapshot
        with tempfile.TemporaryDirectory() as tmpdir:
            # Code importing AND using Gemini
            gemini_code = """
import os
from google import genai

def run_gemini():
    client = genai.Client()
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Plan a trip"
    )
    return response.text
"""
            with open(os.path.join(tmpdir, "gemini_service.py"), "w") as f:
                f.write(gemini_code)

            snap = CodebaseSnapshot(tmpdir)
            gemini_audit = snap.ai_services_audit["Google Gemini"]
            self.assertTrue(gemini_audit["imported"], "Expected Google Gemini to be marked as imported")
            self.assertTrue(gemini_audit["used"], "Expected Google Gemini to be marked as used")
            self.assertGreater(len(gemini_audit["import_sites"]), 0)
            self.assertGreater(len(gemini_audit["call_sites"]), 0)

            # OpenAI should not be imported or used
            openai_audit = snap.ai_services_audit["OpenAI / OpenAI Agents"]
            self.assertFalse(openai_audit["imported"])
            self.assertFalse(openai_audit["used"])

    def test_telemetry_grouped_sessions(self):
        """Verify TelemetryTracer groups trace events by submission/session."""
        from core.telemetry import TelemetryTracer
        with tempfile.TemporaryDirectory() as tmpdir:
            tracer = TelemetryTracer(output_dir=tmpdir)
            
            # Start trace 1
            tid1 = tracer.start_trace("Student A", "/path/to/repoA")
            tracer.log_model_call(tid1, "gemini-3.5-flash", "Prompt A")
            tracer.log_model_response(tid1, "gemini-3.5-flash", {"candidates": []}, duration_ms=120.0)
            tracer.finish_trace(tid1, overall_score=95.0, letter_grade="A", summary="Great work")

            # Start trace 2
            tid2 = tracer.start_trace("Student B", "/path/to/repoB")
            tracer.finish_trace(tid2, overall_score=50.0, letter_grade="F", summary="Missing items")

            sessions = tracer.get_grouped_trace_sessions()
            self.assertEqual(len(sessions), 2)
            self.assertEqual(sessions[0]["trace_id"], tid2)  # Newest first
            self.assertEqual(sessions[1]["trace_id"], tid1)
            self.assertEqual(sessions[1]["student_name"], "Student A")
            self.assertEqual(sessions[1]["overall_score"], 95.0)
            self.assertEqual(len(sessions[1]["events"]), 4)

            # Test single session lookup
            detail = tracer.get_trace_by_id(tid1)
            self.assertIsNotNone(detail)
            self.assertEqual(detail["student_name"], "Student A")

    def test_instructor_multi_assignment_summaries(self):
        """Verify that submitting for two assignments results in two distinct instructor view rows for the same student."""
        self.storage.add_submission("Peeya", "/path/app", 100.0, "A+", class_name="Agent Engineering", assignment_name="AI Agent Assignments")
        self.storage.add_submission("Peeya", "/path/app", 75.0, "C", class_name="Agent Engineering", assignment_name="Skill Assignments")

        summaries = self.storage.get_instructor_student_summaries()
        self.assertEqual(len(summaries), 2, "Expected two rows for the two distinct assignments submitted")
        
        assignments = {s.latest_assignment for s in summaries}
        self.assertIn("AI Agent Assignments", assignments)
        self.assertIn("Skill Assignments", assignments)


if __name__ == "__main__":
    unittest.main()
