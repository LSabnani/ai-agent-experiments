# Job Hunting Agent Specification

## Overview & Objective
Make it easier for job hunters to find opportunities with a good match and create tailored responses, allowing job hunters with multiple capabilities to pursue relevant roles effectively.

---

## Agent System Architecture & Capabilities

### 1. Researcher Agent
- Ask user for roles they are interested in- Only if none provided use (Default roles - "Program Manager", "Supply Chain Analyst", "Materials Program Manager").
- Research available jobs based on roles provided in linked-in, in job-list.csv, indeed.com, glassdoor.com etc.
Ask user for linkedin profile Only if none provided use (Default linked-in profile -https://www.linkedin.com/in/lalitsabnani and
-Ask user for resume - Only if none provided use (Default sample resume: `2025_Dec10  L Sabnani PMv2.docx`).

- **Input Processing**: Read LinkedIn Resume and/or attached PDF/DOCX resume (`2025_Dec10  L Sabnani PMv2.docx`).
- **Opportunity Sourcing**: Search LinkedIn for job opportunities matching target roles based on the resume (e.g., Program Manager, Supply Chain Analyst, Materials Program Manager)and roles selected

### 2. Capability Analyst Agent
- **Fit Assessment**: Determine goodness of fit via keyword filters comparing job opportunities against the resume. Show linked-in profile or Resume used for the evaluation.
- **Gap Analysis**: Identify gaps or differences in keywords between the job posting and resume.
- **Skill Development Recommendations**: If there are gaps in abilities, identify learning opportunities (e.g., classes, certifications) to bridge them.
- **Resume Optimization**: If gaps stem from underutilized keywords, identify specific keywords to add or replace in the resume to successfully pass ATS / keyword filters.

### 3. Cover Letter Writer Agent
- **Tailored Generation**: If match quality is high, write an appropriate cover letter highlighting key abilities and interests.
- **Style & Tone**: Adopt the style and presentation approach of Rebecca Okamoto's TED Talk ([Watch on YouTube](https://youtu.be/f_N3PGvnVKg?si=JYrpl_OjkYmnvh0s)). Highlight digital transformation skills and product ownership/management experience, passionate about building and leading successful projects and experience in using AI tools.