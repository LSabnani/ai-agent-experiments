import json
from typing import List, Optional
from models import CandidateProfile, JobOpportunity, AnalysisResult
import config

try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

class CapabilityAnalystAgent:
    """Capability Analyst Agent responsible for fit scoring, gap analysis, and ATS/course recommendations."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.GEMINI_API_KEY
        self.client = None
        if HAS_GENAI and self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"[CapabilityAnalystAgent] Note: Could not initialize GenAI client: {e}")

    def analyze(self, profile: CandidateProfile, job: JobOpportunity) -> AnalysisResult:
        """Perform comprehensive capability and gap analysis for a job opportunity."""
        if self.client:
            try:
                prompt = f"""You are an expert HR & Capability Analyst Agent. Analyze the fit between the candidate profile and the target job opportunity.

Candidate Profile:
- Skills: {', '.join(profile.core_skills)}
- Summary: {profile.experience_summary}
- Target Roles: {', '.join(profile.target_roles)}

Job Opportunity:
- Title: {job.title} at {job.company}
- Required Skills: {', '.join(job.required_skills)}
- Description: {job.description}

Evaluate the fit and return ONLY valid JSON matching this schema:
{{
  "fit_score": 85.0,
  "matched_keywords": ["Skill A", "Skill B"],
  "missing_keywords": ["Skill C"],
  "course_recommendations": ["Recommended Course / Certification for missing skills"],
  "resume_keyword_tuning": ["Specific recommendation on adding or placing keywords in resume"]
}}
"""
                response = self.client.models.generate_content(
                    model=config.DEFAULT_MODEL,
                    contents=prompt
                )
                raw_json = response.text.strip()
                if raw_json.startswith("```json"):
                    raw_json = raw_json[7:-3].strip()
                elif raw_json.startswith("```"):
                    raw_json = raw_json[3:-3].strip()
                
                data = json.loads(raw_json)
                fit_score = float(data.get("fit_score", 50.0))
                meets = fit_score >= config.FIT_SCORE_THRESHOLD

                return AnalysisResult(
                    job_id=job.id,
                    job_title=job.title,
                    company=job.company,
                    platform=job.platform,
                    source_used=profile.source_used,
                    fit_score=fit_score,
                    matched_keywords=data.get("matched_keywords", []),
                    missing_keywords=data.get("missing_keywords", []),
                    course_recommendations=data.get("course_recommendations", []),
                    resume_keyword_tuning=data.get("resume_keyword_tuning", []),
                    meets_threshold=meets
                )
            except Exception as e:
                print(f"[CapabilityAnalystAgent] LLM analysis failed ({e}), using heuristic analysis fallback.")

        # Heuristic / Keyword-based Fallback
        job_reqs = set(s.lower() for s in job.required_skills)
        candidate_text = (profile.raw_resume_text or "").lower() + " " + " ".join(s.lower() for s in profile.core_skills)
        
        matched = []
        missing = []
        for req in job.required_skills:
            req_clean = req.lower()
            if req_clean in candidate_text or any(word in candidate_text for word in req_clean.split() if len(word) > 3):
                matched.append(req)
            else:
                missing.append(req)
        
        total_reqs = len(job.required_skills) or 1
        fit_score = round((len(matched) / total_reqs) * 100, 1)
        
        course_recs = [f"Take advanced course/certification in '{m}'" for m in missing] if missing else ["No urgent skill gaps identified."]
        tuning_recs = [f"Explicitly highlight '{m}' experience in your resume technical skills section." for m in missing] if missing else ["Resume keywords are well-aligned."]
        
        return AnalysisResult(
            job_id=job.id,
            job_title=job.title,
            company=job.company,
            platform=job.platform,
            source_used=profile.source_used,
            fit_score=fit_score,
            matched_keywords=matched,
            missing_keywords=missing,
            course_recommendations=course_recs,
            resume_keyword_tuning=tuning_recs,
            meets_threshold=fit_score >= config.FIT_SCORE_THRESHOLD
        )
