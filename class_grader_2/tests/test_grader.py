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


if __name__ == "__main__":
    unittest.main()
