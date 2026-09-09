from typing import List, Optional
from models import CandidateProfile, JobOpportunity, AnalysisResult, CoverLetter
import config

try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

class CoverLetterWriterAgent:
    """Cover Letter Writer Agent adopting Rebecca Okamoto's TED talk communication & storytelling style."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.GEMINI_API_KEY
        self.client = None
        if HAS_GENAI and self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"[CoverLetterWriterAgent] Note: Could not initialize GenAI client: {e}")

    def generate(self, profile: CandidateProfile, job: JobOpportunity, analysis: AnalysisResult) -> CoverLetter:
        """Generate a tailored cover letter in Rebecca Okamoto's TED Talk style."""
        
        style_prompt = f"""
Write a targeted, high-impact cover letter following Rebecca Okamoto's TED Talk principles (https://youtu.be/f_N3PGvnVKg):
1. **Bold Positioning**: Start directly with strategic narrative, value proposition, and passion for building and leading successful projects—avoid boring intros like "I am writing to apply for...".
2. **Authentic Storytelling & Core Pillars**: Highlight:
   - Digital transformation skills and product ownership/management experience.
   - Passion for building and leading successful projects.
   - Hands-on experience in using AI tools to boost operational efficiency and innovate workflows.
3. **Value Alignment**: Clearly articulate how your digital transformation capabilities, product management leadership, and AI tool integration solve the company's specific needs ({job.title} at {job.company}).
4. **Confident Executive Tone**: Professional, energetic, articulate, and compelling.
"""

        if self.client:
            try:
                prompt = f"""{style_prompt}

Candidate Name: {profile.name}
Candidate Summary: {profile.experience_summary}
Core Skills: {', '.join(profile.core_skills)}

Job Title: {job.title}
Company: {job.company}
Matched Strengths: {', '.join(analysis.matched_keywords)}
Job Description: {job.description}

Generate the full markdown text of the cover letter emphasizing Digital Transformation leadership, Product Ownership/Management experience, passion for building and leading successful projects, and hands-on experience in using AI tools:
"""
                response = self.client.models.generate_content(
                    model=config.DEFAULT_MODEL,
                    contents=prompt
                )
                content = response.text.strip()
                
                return CoverLetter(
                    job_id=job.id,
                    job_title=job.title,
                    company=job.company,
                    content=content,
                    style_notes="Crafted using Rebecca Okamoto's strategic narrative framework, highlighting digital transformation leadership, product ownership, passion for project leadership, and AI tools experience."
                )
            except Exception as e:
                print(f"[CoverLetterWriterAgent] LLM generation failed ({e}), using template fallback.")

        # High quality template fallback embodying Rebecca Okamoto's principles with Digital Transformation, Product Ownership, Project Leadership & AI Tools emphasis
        fallback_content = f"""Dear Hiring Team at {job.company},

When leading complex operational transformations in high-growth organizations, real impact requires more than keeping systems running—it demands driving digital transformation, exercising clear product ownership, leveraging cutting-edge AI tools, and rallying cross-functional teams around a high-value vision.

As a strategic leader passionate about building and leading successful projects with deep expertise in digital transformation, product ownership/management, AI tool integration, and {', '.join(profile.core_skills[:3])}, I was immediately drawn to the {job.title} position at {job.company}. Throughout my career, I have specialized in turning intricate technical frameworks into streamlined digital solutions that deliver measurable ROI and operational agility.

Key Highlights & Strategic Capabilities I Bring:
- **Digital Transformation & Product Ownership**: Managed product life cycles from strategic roadmap definition to cross-functional deployment, cutting operational lead times by over 20% while building resilient, data-driven capabilities.
- **Project Leadership & Execution**: Passionate about building and leading high-performing cross-functional teams across engineering, materials management, and operations to deliver successful projects on time and on budget.
- **AI Tools & Workflow Innovation**: Hands-on experience deploying AI tools and automated analytical workflows to optimize decision-making, boost productivity, and drive continuous improvement.
- **Domain Strengths**: Hands-on proficiency in {', '.join(analysis.matched_keywords[:4]) if analysis.matched_keywords else 'Product Management, Digital Workflows, Supply Chain Analytics, and AI Tool Integration'}.

I welcome the opportunity to discuss how my digital transformation expertise, AI tool experience, and passion for leading successful projects will accelerate strategic goals for {job.company}.

Warm regards,

{profile.name}
{profile.headline or 'Product Manager & Digital Transformation Leader'}
"""

        return CoverLetter(
            job_id=job.id,
            job_title=job.title,
            company=job.company,
            content=fallback_content,
            style_notes="Crafted using Rebecca Okamoto's strategic narrative framework, highlighting digital transformation leadership, product ownership, passion for project leadership, and AI tools experience."
        )

