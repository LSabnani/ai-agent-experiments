from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


def get_utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Criterion(BaseModel):
    id: str
    title: str
    description: str
    weight: float = 1.0
    category: str = "Functionality"  # Mandatory Requirement, Functionality, Code Quality, Constraints, Testing
    is_mandatory: bool = False
    penalty_percent: Optional[float] = None


class CriterionResult(BaseModel):
    id: str
    title: str
    description: str
    max_score: float
    earned_score: float
    status: str  # "PASS", "PARTIAL", "FAIL"
    feedback: str
    evidence: Optional[str] = None
    category: str = "Functionality"
    is_mandatory: bool = False
    deduction_reason: Optional[str] = None
    fix_recommendation: Optional[str] = None


class EvaluationResult(BaseModel):
    total_score: float
    max_possible_score: float
    percentage_score: float
    letter_grade: str
    summary: str
    model_used: Optional[str] = None
    class_name: Optional[str] = None
    assignment_name: Optional[str] = None
    deficiencies: List[str] = []
    criteria: List[CriterionResult] = []
    strengths: List[str] = []
    deductions: List[str] = []
    execution_logs: Optional[str] = None
    evaluated_at: str = Field(default_factory=get_utc_now_iso)


class SubmissionRecord(BaseModel):
    id: str
    student_name: str
    folder_name: str
    score: float
    letter_grade: str
    class_name: Optional[str] = None
    assignment_name: Optional[str] = None
    model_used: Optional[str] = None
    timestamp: str = Field(default_factory=get_utc_now_iso)
    evaluation_details: Optional[EvaluationResult] = None


class StudentSummary(BaseModel):
    student_name: str
    total_submissions: int
    highest_score: float
    highest_grade: str
    latest_submission_time: str
    latest_score: float
    latest_grade: str
    latest_folder: str
    latest_class: Optional[str] = None
    latest_assignment: Optional[str] = None
    latest_model_used: Optional[str] = None


class GradeRequest(BaseModel):
    student_name: str
    folder_name: str
    subfolder: Optional[str] = None
    class_name: Optional[str] = None
    assignment_name: Optional[str] = None
