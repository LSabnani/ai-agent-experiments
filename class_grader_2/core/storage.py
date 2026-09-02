import os
import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict
from core.models import SubmissionRecord, StudentSummary, EvaluationResult, get_utc_now_iso

DEFAULT_SCORES_PATH = os.path.join("outputs", "scores.json")


class ScoreStorage:
    def __init__(self, file_path: str = DEFAULT_SCORES_PATH):
        self.file_path = file_path
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        parent_dir = os.path.dirname(self.file_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
            
        if not os.path.exists(self.file_path):
            # Only migrate legacy root scores.json if initializing the default output file
            if self.file_path == DEFAULT_SCORES_PATH:
                legacy_path = "scores.json"
                if os.path.exists(legacy_path):
                    try:
                        with open(legacy_path, "r", encoding="utf-8") as src, open(self.file_path, "w", encoding="utf-8") as dst:
                            dst.write(src.read())
                        return
                    except Exception:
                        pass
            with open(self.file_path, "w", encoding="utf-8") as f:
                pass  # create empty file

    def add_submission(self, student_name: str, folder_name: str, score: float, 
                       letter_grade: str, model_used: Optional[str] = None,
                       class_name: Optional[str] = None,
                       assignment_name: Optional[str] = None,
                       evaluation_details: Optional[EvaluationResult] = None) -> SubmissionRecord:
        record = SubmissionRecord(
            id=str(uuid.uuid4()),
            student_name=student_name.strip(),
            folder_name=folder_name.strip(),
            score=round(score, 2),
            letter_grade=letter_grade,
            model_used=model_used or (evaluation_details.model_used if evaluation_details else None),
            class_name=class_name or (evaluation_details.class_name if evaluation_details else None),
            assignment_name=assignment_name or (evaluation_details.assignment_name if evaluation_details else None),
            timestamp=get_utc_now_iso(),
            evaluation_details=evaluation_details
        )
        # Store as single-line JSON format
        line = record.model_dump_json()
        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        return record

    def get_all_submissions(self) -> List[SubmissionRecord]:
        if not os.path.exists(self.file_path):
            return []
        
        submissions = []
        with open(self.file_path, "r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    submissions.append(SubmissionRecord(**data))
                except Exception as e:
                    print(f"Warning: Failed to parse line {line_number} in {self.file_path}: {e}")
        return submissions

    def get_submissions_for_student(self, student_name: str) -> List[SubmissionRecord]:
        target = student_name.strip().lower()
        all_subs = self.get_all_submissions()
        student_subs = [s for s in all_subs if s.student_name.strip().lower() == target]
        # Sort latest first
        student_subs.sort(key=lambda s: s.timestamp, reverse=True)
        return student_subs

    def get_submission_by_id(self, submission_id: str) -> Optional[SubmissionRecord]:
        for sub in self.get_all_submissions():
            if sub.id == submission_id:
                return sub
        return None

    def get_instructor_student_summaries(self) -> List[StudentSummary]:
        all_subs = self.get_all_submissions()
        students_map: Dict[str, List[SubmissionRecord]] = {}
        
        # Group submissions by student (case-preserved display name from most recent submission)
        for sub in all_subs:
            normalized_key = sub.student_name.strip().lower()
            if normalized_key not in students_map:
                students_map[normalized_key] = []
            students_map[normalized_key].append(sub)

        summaries: List[StudentSummary] = []
        for key, subs in students_map.items():
            if not subs:
                continue
            
            # Sort by timestamp ascending for sequential processing
            subs.sort(key=lambda s: s.timestamp)
            latest_sub = subs[-1]
            
            # Find submission with highest score
            highest_sub = max(subs, key=lambda s: s.score)
            
            # Calculate display name
            display_name = latest_sub.student_name.strip()
            
            summary = StudentSummary(
                student_name=display_name,
                total_submissions=len(subs),
                highest_score=highest_sub.score,
                highest_grade=highest_sub.letter_grade,
                latest_submission_time=latest_sub.timestamp,
                latest_score=latest_sub.score,
                latest_grade=latest_sub.letter_grade,
                latest_folder=latest_sub.folder_name,
                latest_class=latest_sub.class_name,
                latest_assignment=latest_sub.assignment_name,
                latest_model_used=latest_sub.model_used or (latest_sub.evaluation_details.model_used if latest_sub.evaluation_details else None)
            )
            summaries.append(summary)

        # Sort summary by highest score descending by default
        summaries.sort(key=lambda s: s.highest_score, reverse=True)
        return summaries
