import os
import re
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
        self.scores_file = scores_file
        self.storage = ScoreStorage(scores_file)
        self.scoring_file = scoring_file

    def grade_submission(self, student_name: str, folder_name: str, 
                         subfolder: Optional[str] = None,
                         model_name: Optional[str] = None,
                         class_name: Optional[str] = None,
                         assignment_name: Optional[str] = None) -> Tuple[SubmissionRecord, EvaluationResult]:
        if not student_name or not student_name.strip():
            raise ValueError("Student name is required.")
        
        folder_input = folder_name.strip().strip("'").strip('"')
        
        # 1. Resolve GitHub URL or local machine path
        if GitFetcher.is_git_url(folder_input):
            target_folder = GitFetcher.resolve_and_fetch(folder_input, explicit_subfolder=subfolder)
        else:
            expanded = os.path.abspath(os.path.expanduser(folder_input))
            if subfolder:
                expanded = os.path.join(expanded, subfolder)
            target_folder = expanded

        if not os.path.exists(target_folder):
            raise FileNotFoundError(f"Target folder '{target_folder}' does not exist on local machine. Please enter a valid directory path or GitHub repository URL.")
        
        if not os.path.isdir(target_folder):
            raise NotADirectoryError(f"Provided path '{target_folder}' is not a directory.")

        # 2. Initialize Telemetry Trace
        trace_id = tracer.start_trace(
            student_name=student_name, 
            folder_name=folder_input,
            class_name=class_name,
            assignment_name=assignment_name
        )

        # 3. Skill: SpecParser (loads SPECIFICATIONS.md & SCORING.md & SUBMISSIONS.yaml criteria)
        spec_start = time.time()
        parser = SpecParser(
            target_folder, 
            scoring_file_path=self.scoring_file,
            class_name=class_name,
            assignment_name=assignment_name
        )
        spec_content = parser.read_spec_content()
        scoring_content = parser.read_scoring_content()
        criteria = parser.parse_criteria()
        spec_dur = (time.time() - spec_start) * 1000
        
        tracer.log_skill_usage(
            trace_id=trace_id,
            skill_name="SpecParser",
            inputs={"folder_path": target_folder, "source_input": folder_input, "spec_file": parser.spec_file_path, "scoring_file": parser.scoring_file_path, "class_name": class_name, "assignment_name": assignment_name},
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
            scoring_content=scoring_content,
            class_name=class_name,
            assignment_name=assignment_name
        )
        evaluation_result = evaluator.evaluate()

        # 5. Store Submission in outputs/scores.json as single-line JSON
        submission_record = self.storage.add_submission(
            student_name=student_name,
            folder_name=folder_input,
            score=evaluation_result.percentage_score,
            letter_grade=evaluation_result.letter_grade,
            model_used=evaluation_result.model_used,
            class_name=class_name,
            assignment_name=assignment_name,
            evaluation_details=evaluation_result
        )

        # 6. Auto-save PDF & TXT copies in outputs/reports/
        try:
            from core.exporter import ReportExporter
            reports_dir = os.path.join(os.path.dirname(self.scores_file), "reports")
            os.makedirs(reports_dir, exist_ok=True)
            safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', student_name)
            txt_path = os.path.join(reports_dir, f"{safe_name}_grade_report.txt")
            pdf_path = os.path.join(reports_dir, f"{safe_name}_grade_report.pdf")
            
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(ReportExporter.generate_text_report(submission_record))
            
            pdf_bytes = ReportExporter.generate_pdf_report(submission_record)
            with open(pdf_path, "wb") as f:
                f.write(pdf_bytes)
        except Exception as export_err:
            print(f"Warning: Failed to auto-save report copies in outputs/reports/: {export_err}")

        # 7. Finish Trace
        tracer.finish_trace(
            trace_id=trace_id,
            overall_score=evaluation_result.percentage_score,
            letter_grade=evaluation_result.letter_grade,
            summary=evaluation_result.summary
        )

        return submission_record, evaluation_result
