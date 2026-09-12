import csv
import json
import os
import re
from typing import List, Optional
from models import CandidateProfile, JobOpportunity
import config

try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

class ResearcherAgent:
    """Researcher Agent responsible for parsing candidate resumes and sourcing matching job opportunities across LinkedIn, CSV imports, Indeed, Glassdoor, etc."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.GEMINI_API_KEY
        self.client = None
        if HAS_GENAI and self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"[ResearcherAgent] Note: Could not initialize GenAI client: {e}")

    DEFAULT_LINKEDIN = "https://www.linkedin.com/in/lalitsabnani"
    DEFAULT_RESUME = os.path.join(config.BASE_DIR, "2026Sep12 LSabnani PMv1.docx")
    DEFAULT_ROLES = ["Program Manager", "Supply Chain Analyst", "Materials Program Manager"]

    def load_jobs_from_file(self, file_path: str) -> List[JobOpportunity]:
        """Load job opportunities from JSON or CSV file."""
        if not os.path.exists(file_path):
            return []
        
        if file_path.lower().endswith('.csv'):
            jobs = []
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Parse required skills list
                    skills_raw = row.get('required_skills', '')
                    if isinstance(skills_raw, str):
                        skills = [s.strip() for s in skills_raw.split(',') if s.strip()]
                    else:
                        skills = list(skills_raw)
                    
                    jobs.append(JobOpportunity(
                        id=row.get('id', f"JOB-{len(jobs)+100}"),
                        title=row.get('title', 'Unknown Title'),
                        company=row.get('company', 'Unknown Company'),
                        location=row.get('location', 'Remote/Unspecified'),
                        description=row.get('description', ''),
                        required_skills=skills,
                        url=row.get('url', None),
                        platform=row.get('platform', 'CSV Import')
                    ))
            return jobs
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_jobs = json.load(f)
                return [JobOpportunity(**j) for j in raw_jobs]

    def prompt_user_for_input(self) -> tuple[List[str], str, str]:
        """Interactively ask the user for target roles, LinkedIn profile URL, and attached resume document path."""
        print("\n" + "="*60)
        print("[INPUT REQUIRED] Researcher Agent: Candidate Roles & Profile Input")
        print("="*60)
        roles_str = ""
        linkedin_url = ""
        resume_path = ""
        try:
            default_roles_str = ", ".join(self.DEFAULT_ROLES)
            print(f"1. Enter target roles of interest (comma-separated):")
            roles_str = input(f"   [Default: {default_roles_str}]: ").strip()

            print("2. Enter LinkedIn Profile URL:")
            linkedin_url = input(f"   [Default: {self.DEFAULT_LINKEDIN}]: ").strip()
            
            print("3. Enter Resume File Path (.docx/.pdf/.txt):")
            resume_path = input(f"   [Default: 2026Sep12 LSabnani PMv1.docx]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[Non-interactive shell detected / EOF - using defaults]")
        
        if roles_str:
            roles = [r.strip() for r in roles_str.split(",") if r.strip()]
        else:
            roles = list(self.DEFAULT_ROLES)

        if not linkedin_url:
            linkedin_url = self.DEFAULT_LINKEDIN
        if not resume_path:
            resume_path = self.DEFAULT_RESUME
            
        return roles, linkedin_url, resume_path

    def load_resume_text(self, file_or_text_input: str) -> str:
        """Read resume content from PDF, DOCX, text file, or direct text input."""
        if not file_or_text_input:
            _, _, file_or_text_input = self.prompt_user_for_input()

        # Check if input is a valid file path
        if os.path.exists(file_or_text_input):
            if file_or_text_input.lower().endswith('.pdf'):
                if not HAS_PYPDF:
                    raise ImportError("pypdf is required to parse PDF resumes. Install via pip install pypdf.")
                reader = pypdf.PdfReader(file_or_text_input)
                text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
                return text
            elif file_or_text_input.lower().endswith('.docx'):
                import zipfile
                import xml.etree.ElementTree as ET
                z = zipfile.ZipFile(file_or_text_input)
                tree = ET.fromstring(z.read('word/document.xml'))
                paragraphs = []
                for p in tree.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
                    texts = [node.text for node in p.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t') if node.text]
                    if texts:
                        paragraphs.append(''.join(texts))
                return '\n'.join(paragraphs)
            else:
                with open(file_or_text_input, 'r', encoding='utf-8') as f:
                    return f.read()
        
        # If it's direct text input or LinkedIn profile URL text
        return file_or_text_input

    def parse_profile(
        self, 
        resume_text: str, 
        target_roles: Optional[List[str]] = None,
        source_used: str = "Resume (2026Sep12 LSabnani PMv1.docx)"
    ) -> CandidateProfile:
        """Parse raw resume text into structured CandidateProfile using Gemini or rule-based fallback."""
        specified_roles = target_roles if target_roles else self.DEFAULT_ROLES

        if self.client:
            try:
                prompt = f"""Extract structured candidate information from the following resume text.
Target Roles of Interest: {', '.join(specified_roles)}

Return ONLY valid JSON matching this schema:
{{
  "name": "Full Name",
  "headline": "Professional headline",
  "target_roles": ["Role 1", "Role 2"],
  "core_skills": ["Skill 1", "Skill 2"],
  "experience_summary": "Summary paragraph of experience"
}}

Resume:
{resume_text}
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
                data['raw_resume_text'] = resume_text
                data['source_used'] = source_used
                if target_roles:
                    data['target_roles'] = target_roles
                return CandidateProfile(**data)
            except Exception as e:
                print(f"[ResearcherAgent] LLM parsing failed ({e}), using rule-based extraction fallback.")

        # Fallback Rule-Based Parser
        lines = [l.strip() for l in resume_text.split('\n') if l.strip()]
        name = lines[0] if lines else "Candidate"
        if name.upper() in ["SUMMARY", "PROFILE", "RESUME", "CURRICULUM VITAE", "OBJECTIVE"]:
            extracted_name = None
            if "Resume (" in source_used:
                file_part = source_used.split("Resume (")[1].split(")")[0]
                possible_name = file_part.split("Resume")[0].strip()
                if possible_name and len(possible_name) > 1:
                    extracted_name = possible_name
            name = extracted_name or (lines[1] if len(lines) > 1 else "Candidate")

        headline = lines[1] if len(lines) > 1 else "Professional"
        
        # Extract skills & roles
        roles = specified_roles
        skills = [
            "Program Management", 
            "Supply Chain Optimization", 
            "Materials Management", 
            "Data Analytics", 
            "Digital Transformation", 
            "Product Ownership", 
            "AI Tools Experience", 
            "Building & Leading Successful Projects", 
            "BOM Management"
        ]
        
        return CandidateProfile(
            name=name,
            headline=headline,
            target_roles=roles,
            core_skills=skills,
            experience_summary="Experienced professional passionate about building and leading successful projects, leveraging AI tools, digital transformation, product ownership, and supply chain optimization.",
            raw_resume_text=resume_text,
            source_used=source_used
        )

    def fetch_opportunities(self, profile: CandidateProfile, job_source_file: Optional[str] = None) -> List[JobOpportunity]:
        """Fetch or load candidate job opportunities matching target roles across platforms (LinkedIn, job-list.csv, Indeed, Glassdoor, etc.)."""
        jobs = []
        if job_source_file and os.path.exists(job_source_file):
            jobs = self.load_jobs_from_file(job_source_file)
        else:
            # Check for job-list.csv in base directory first, then sample_data/job-list.csv, then jobs_sample.json
            csv_path = os.path.join(config.BASE_DIR, "job-list.csv")
            sample_csv_path = os.path.join(config.SAMPLE_DATA_DIR, "job-list.csv")
            default_json_path = os.path.join(config.SAMPLE_DATA_DIR, "jobs_sample.json")
            
            if os.path.exists(csv_path):
                jobs = self.load_jobs_from_file(csv_path)
            elif os.path.exists(sample_csv_path):
                jobs = self.load_jobs_from_file(sample_csv_path)
            elif os.path.exists(default_json_path):
                jobs = self.load_jobs_from_file(default_json_path)

        # Prioritize or filter jobs that match target roles if profile has specific target roles
        if profile.target_roles and jobs:
            lowered_target = [r.lower() for r in profile.target_roles]
            matching_jobs = []
            other_jobs = []
            for j in jobs:
                if any(tr in j.title.lower() for tr in lowered_target):
                    matching_jobs.append(j)
                else:
                    other_jobs.append(j)
            return matching_jobs + other_jobs

        return jobs


