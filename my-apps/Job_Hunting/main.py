"""
AI Job Hunting Agent Pipeline - CLI Entry Point
"""
import argparse
import sys
import os
import config
from pipeline import JobHuntingPipeline

def main():
    parser = argparse.ArgumentParser(description="AI Agent Pipeline for Job Hunting")
    parser.add_argument(
        "--linkedin", 
        type=str, 
        default=None,
        help="LinkedIn Profile URL (default: https://www.linkedin.com/in/lalitsabnani)"
    )
    parser.add_argument(
        "--resume", 
        type=str, 
        default=None,
        help="Path to candidate resume file (.docx, .pdf, .txt) (default: 2026Sep12 LSabnani PMv1.docx)"
    )
    parser.add_argument(
        "--roles",
        type=str,
        default=None,
        help="Comma-separated target job roles (default: Program Manager, Supply Chain Analyst, Materials Program Manager)"
    )
    parser.add_argument(
        "--jobs", 
        type=str, 
        default=os.path.join(config.SAMPLE_DATA_DIR, "jobs_sample.json"),
        help="Path to job listings JSON file"
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Use default LinkedIn profile, resume, and roles automatically without prompting"
    )

    args = parser.parse_args()

    linkedin_input = args.linkedin
    resume_input = args.resume
    roles_input = [r.strip() for r in args.roles.split(",") if r.strip()] if args.roles else None

    pipeline = JobHuntingPipeline()
    output = pipeline.run(
        linkedin_url=linkedin_input,
        resume_path=resume_input,
        target_roles=roles_input,
        job_source_file=args.jobs,
        prompt_if_missing=not args.sample
    )

    print("Pipeline Execution Results Summary:")
    print(f"- Candidate Name: {output.candidate_profile.name}")
    print(f"- Evaluation Source Used: {output.candidate_profile.source_used}")
    print(f"- Jobs Analyzed: {output.jobs_analyzed_count}")
    print(f"- Cover Letters Generated: {len(output.cover_letters)}")
    for a in output.analyses:
        print(f"  - {a.job_title} @ {a.company} [Platform: {a.platform} | Source: {a.source_used}]: Fit Score {a.fit_score}% (Meets Threshold: {a.meets_threshold})")

if __name__ == "__main__":
    main()
