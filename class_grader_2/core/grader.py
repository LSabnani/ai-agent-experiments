import os
import time
from typing import Tuple, Optional
from core.models import EvaluationResult, SubmissionRecord
from core.spec_parser import SpecParser
from core.ml_evaluator import MLEvaluator
from core.storage import ScoreStorage, DEFAULT_SCORES_PATH
from core.telemetry import tracer
from core.git_fetcher import GitFetcher


class Grader:
    def __init__(self, scores_file: str = DEFAULT_SCORES_PATH, scoring_file: Optional[str] = None):
        self.storage = ScoreStorage(scores_file)
        self.scoring_file = scoring_file

    def grade_submission(self, student_name: str, folder_name: str, 
                         subfolder: Optional[str] = None,
                         model_name: Optional[str] = None) -> Tuple[SubmissionRecord, EvaluationResult]:
        if not student_name or not student_name.strip():
            raise ValueError("Student name is required.")
        
        folder_input = folder_name.strip()
        
        # 1. Resolve GitHub URL or local path
        if GitFetcher.is_git_url(folder_input):
            target_folder = GitFetcher.resolve_and_fetch(folder_input, explicit_subfolder=subfolder)
        else:
            target_folder = folder_input
            if subfolder:
                target_folder = os.path.join(target_folder, subfolder)

        if not os.path.exists(target_folder):
            raise FileNotFoundError(f"Target folder '{target_folder}' does not exist.")
        
        if not os.path.isdir(target_folder):
            raise NotADirectoryError(f"Provided path '{target_folder}' is not a directory.")

        # 2. Initialize Telemetry Trace
        trace_id = tracer.start_trace(student_name, folder_input)

        # 3. Skill: SpecParser (loads SPECIFICATIONS.md & SCORING.md)
        spec_start = time.time()
        parser = SpecParser(target_folder, scoring_file_path=self.scoring_file)
        spec_content = parser.read_spec_content()
        scoring_content = parser.read_scoring_content()
        criteria = parser.parse_criteria()
        spec_dur = (time.time() - spec_start) * 1000
        
        tracer.log_skill_usage(
            trace_id=trace_id,
            skill_name="SpecParser",
            inputs={"folder_path": target_folder, "source_input": folder_input, "spec_file": parser.spec_file_path, "scoring_file": parser.scoring_file_path},
            outputs={"criteria_count": len(criteria), "spec_length_chars": len(spec_content), "has_scoring_rubric": scoring_content is not None},
            duration_ms=spec_dur,
            status="SUCCESS"
        )

        # 4. Skill & Model: MLEvaluator
        evaluator = MLEvaluator(
            folder_path=target_folder,
            spec_content=spec_content,
            criteria=criteria,
            model_name=model_name,
            trace_id=trace_id,
            scoring_content=scoring_content
        )
        evaluation_result = evaluator.evaluate()

        # 5. Store Submission in outputs/scores.json as single-line JSON
        submission_record = self.storage.add_submission(
            student_name=student_name,
            folder_name=folder_input,
            score=evaluation_result.percentage_score,
            letter_grade=evaluation_result.letter_grade,
            evaluation_details=evaluation_result
        )

        # 6. Finish Trace
        tracer.finish_trace(
            trace_id=trace_id,
            overall_score=evaluation_result.percentage_score,
            letter_grade=evaluation_result.letter_grade,
            summary=evaluation_result.summary
        )

        return submission_record, evaluation_result
