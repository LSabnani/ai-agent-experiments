"""
Job Hunting Pipeline Orchestrator
"""
import json
import os
from typing import List, Optional
from models import PipelineOutput, CandidateProfile
from agents.researcher import ResearcherAgent
from agents.analyst import CapabilityAnalystAgent
from agents.writer import CoverLetterWriterAgent
import config

class JobHuntingPipeline:
    """Orchestrator pipeline executing Researcher -> Capability Analyst -> Cover Letter Writer agents."""

    def __init__(self, api_key: Optional[str] = None):
        self.researcher = ResearcherAgent(api_key=api_key)
        self.analyst = CapabilityAnalystAgent(api_key=api_key)
        self.writer = CoverLetterWriterAgent(api_key=api_key)

    def run(
        self, 
        linkedin_url: Optional[str] = None, 
        resume_path: Optional[str] = None, 
        target_roles: Optional[List[str]] = None,
        job_source_file: Optional[str] = None,
        prompt_if_missing: bool = False
    ) -> PipelineOutput:
        """Run the end-to-end Job Hunting AI Agent Pipeline."""
        print(f"\n==================================================")
        print(f"[START] Starting AI Agent Pipeline for Job Hunting")
        print(f"==================================================")

        # Step 1: Researcher Agent - Prompt user if requested & missing, or use defaults per spec.md
        if prompt_if_missing and (not linkedin_url or not resume_path or not target_roles):
            p_roles, p_linkedin, p_resume = self.researcher.prompt_user_for_input()
            target_roles = target_roles or p_roles
            linkedin_url = linkedin_url or p_linkedin
            resume_path = resume_path or p_resume

        if not linkedin_url:
            linkedin_url = self.researcher.DEFAULT_LINKEDIN
        if not resume_path:
            resume_path = self.researcher.DEFAULT_RESUME
        if not target_roles:
            target_roles = list(self.researcher.DEFAULT_ROLES)

        # Determine source_used string
        linkedin_name = linkedin_url if linkedin_url else self.researcher.DEFAULT_LINKEDIN
        resume_name = os.path.basename(resume_path) if os.path.exists(resume_path) else resume_path

        source_used = f"Resume ({resume_name})"
        if linkedin_url and linkedin_url != self.researcher.DEFAULT_LINKEDIN:
            source_used = f"LinkedIn Profile ({linkedin_url})"
            if os.path.exists(resume_path) and resume_path != self.researcher.DEFAULT_RESUME:
                source_used = f"Resume ({resume_name}) & LinkedIn Profile ({linkedin_url})"

        print(f"\n[Stage 1] Researcher Agent: Reading profile input...")
        print(f"  * LinkedIn Profile: {linkedin_url}")
        print(f"  * Resume File: {resume_path}")
        print(f"  * Selected Target Roles: {', '.join(target_roles)}")
        print(f"  * Source Used for Evaluation: {source_used}")

        resume_text = self.researcher.load_resume_text(resume_path)
        profile = self.researcher.parse_profile(resume_text, target_roles=target_roles, source_used=source_used)
        print(f"  * Candidate Profile Parsed: {profile.name}")
        print(f"  * Target Roles Identified: {', '.join(profile.target_roles)}")

        # Step 1b: Sourcing opportunities
        print(f"\n[Stage 1b] Researcher Agent: Sourcing job opportunities...")
        jobs = self.researcher.fetch_opportunities(profile, job_source_file=job_source_file)
        print(f"  * Found {len(jobs)} job opportunities to evaluate.")

        # Step 2: Capability Analyst Agent - Fit & Gap Analysis
        print(f"\n[Stage 2] Capability Analyst Agent: Running fit & gap analysis...")
        analyses = []
        cover_letters = []

        for idx, job in enumerate(jobs, 1):
            print(f"  -> [{idx}/{len(jobs)}] Analyzing: {job.title} at {job.company} [Platform: {job.platform}]...")
            analysis = self.analyst.analyze(profile, job)
            analyses.append(analysis)

            print(f"     Fit Score: {analysis.fit_score}% | Meets Threshold (>= {config.FIT_SCORE_THRESHOLD}%): {analysis.meets_threshold}")
            if analysis.missing_keywords:
                print(f"     Gaps/Missing Keywords: {', '.join(analysis.missing_keywords)}")

            # Step 3: Cover Letter Writer Agent (if threshold met)
            if analysis.meets_threshold:
                print(f"\n[Stage 3] Cover Letter Writer Agent: Generating Rebecca Okamoto style cover letter...")
                cover_letter = self.writer.generate(profile, job, analysis)
                cover_letters.append(cover_letter)

                # Save individual cover letter markdown file
                cl_filename = f"cover_letter_{job.id}.md"
                cl_filepath = os.path.join(config.OUTPUT_DIR, cl_filename)
                with open(cl_filepath, 'w', encoding='utf-8') as f:
                    f.write(f"# Cover Letter - {job.title} at {job.company}\n\n")
                    f.write(cover_letter.content)
                print(f"     * Saved Cover Letter to: {cl_filepath}")

        # Assemble pipeline output
        pipeline_output = PipelineOutput(
            candidate_profile=profile,
            jobs_analyzed_count=len(jobs),
            analyses=analyses,
            cover_letters=cover_letters
        )

        # Save structured pipeline report JSON
        report_path = os.path.join(config.OUTPUT_DIR, "output_report.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(pipeline_output.model_dump_json(indent=2))
        print(f"\n==================================================")
        print(f"[SUCCESS] Pipeline Completed Successfully!")
        print(f"Summary Report saved to: {report_path}")
        print(f"==================================================\n")

        return pipeline_output
