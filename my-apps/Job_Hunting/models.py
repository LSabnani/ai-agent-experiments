"""
Data Models and Pydantic Schemas for Job Hunting Agent Pipeline
"""
from typing import List, Optional
from pydantic import BaseModel, Field

class CandidateProfile(BaseModel):
    name: str = Field(description="Candidate's full name")
    headline: Optional[str] = Field(None, description="Professional headline or summary")
    target_roles: List[str] = Field(default_factory=list, description="Target job titles identified from profile")
    core_skills: List[str] = Field(default_factory=list, description="Primary technical and domain skills")
    experience_summary: str = Field(description="Summary of work history and key achievements")
    raw_resume_text: Optional[str] = Field(None, description="Raw extracted resume text")
    source_used: str = Field(default="Resume (2026Sep12 LSabnani PMv1.docx)", description="Explicitly indicates LinkedIn profile or Resume file used for evaluation")

class JobOpportunity(BaseModel):
    id: str = Field(description="Unique job identifier")
    title: str = Field(description="Job title")
    company: str = Field(description="Company name")
    location: str = Field(description="Job location or Remote status")
    description: str = Field(description="Full job description")
    required_skills: List[str] = Field(default_factory=list, description="Key required skills and keywords")
    url: Optional[str] = Field(None, description="Job posting URL")
    platform: str = Field(default="LinkedIn", description="Source platform (e.g. LinkedIn, Indeed, Glassdoor, job-list.csv)")

class AnalysisResult(BaseModel):
    job_id: str = Field(description="Identifier of analyzed job opportunity")
    job_title: str = Field(description="Title of analyzed job opportunity")
    company: str = Field(description="Company name")
    platform: str = Field(default="LinkedIn", description="Source platform for the job posting")
    source_used: str = Field(default="Resume (2026Sep12 LSabnani PMv1.docx)", description="Explicitly indicates the Resume file or LinkedIn Profile used for evaluation")
    fit_score: float = Field(description="Calculated fit score percentage (0 - 100)")
    matched_keywords: List[str] = Field(default_factory=list, description="Keywords present in both resume and job posting")
    missing_keywords: List[str] = Field(default_factory=list, description="Keywords required by job but absent/weak in resume")
    course_recommendations: List[str] = Field(default_factory=list, description="Recommended classes or training to bridge capability gaps")
    resume_keyword_tuning: List[str] = Field(default_factory=list, description="Specific keyword replacements or additions for ATS optimization")
    meets_threshold: bool = Field(description="Whether fit_score meets or exceeds threshold")

class CoverLetter(BaseModel):
    job_id: str = Field(description="Job identifier")
    job_title: str = Field(description="Job title")
    company: str = Field(description="Company name")
    content: str = Field(description="Generated cover letter content in Rebecca Okamoto style")
    style_notes: str = Field(description="Explanation of storytelling and positioning choices used")

class PipelineOutput(BaseModel):
    candidate_profile: CandidateProfile
    jobs_analyzed_count: int
    analyses: List[AnalysisResult]
    cover_letters: List[CoverLetter]
