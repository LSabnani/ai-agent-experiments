import os
import time
from typing import Tuple, Optional
from core.models import EvaluationResult, SubmissionRecord
from core.spec_parser import SpecParser
from core.ml_evaluator import MLEvaluator
from core.storage import ScoreStorage, DEFAULT_SCORES_PATH
from core.telemetry import tracer


class Grader:
    def __init__(self, scores_file: str = DEFAULT_SCORES_PATH):
        self.storage = ScoreStorage(scores_file)

    def grade_submission(self, student_name: str, folder_name: str, 
                         model_name: Optional[str] = None) -> Tuple[SubmissionRecord, EvaluationResult]:
        if not student_name or not student_name.strip():
            raise ValueError("Student name is required.")
        
        folder_name = folder_name.strip()
        if not os.path.exists(folder_name):
            raise FileNotFoundError(f"Target folder '{folder_name}' does not exist.")
        
        if not os.path.isdir(folder_name):
            raise NotADirectoryError(f"Provided path '{folder_name}' is not a directory.")

        # 1. Initialize Telemetry Trace
        trace_id = tracer.start_trace(student_name, folder_name)

        # 2. Skill: SpecParser
        spec_start = time.time()
        parser = SpecParser(folder_name)
        spec_content = parser.read_spec_content()
        criteria = parser.parse_criteria()
        spec_dur = (time.time() - spec_start) * 1000
        
        tracer.log_skill_usage(
            trace_id=trace_id,
            skill_name="SpecParser",
            inputs={"folder_path": folder_name, "spec_file": parser.spec_file_path},
            outputs={"criteria_count": len(criteria), "spec_length_chars": len(spec_content)},
            duration_ms=spec_dur,
            status="SUCCESS"
        )

        # 3. Skill & Model: MLEvaluator
        evaluator = MLEvaluator(folder_path=folder_name, spec_content=spec_content, 
                                criteria=criteria, model_name=model_name, trace_id=trace_id)
        evaluation_result = evaluator.evaluate()

        # 4. Store Submission in outputs/scores.json as single-line JSON
        submission_record = self.storage.add_submission(
            student_name=student_name,
            folder_name=folder_name,
            score=evaluation_result.percentage_score,
            letter_grade=evaluation_result.letter_grade,
            evaluation_details=evaluation_result
        )

        # 5. Finish Trace
        tracer.finish_trace(
            trace_id=trace_id,
            overall_score=evaluation_result.percentage_score,
            letter_grade=evaluation_result.letter_grade,
            summary=evaluation_result.summary
        )

        return submission_record, evaluation_result
