# ML Specification Grader App - Implementation Plan

## Goal
Build a Python-based intelligent ML Specification Grader application that accepts a **student name** and **folder name**, evaluates whether the code in the folder fulfills the requirements specified in `SPECIFICATIONS.md`, calculates a score, saves every submission record as a single-line JSON entry in `scores.json`, and provides an **Instructor View** to inspect top scores, latest submissions, and historical submission drill-downs per student.

---

## Key Features & Requirements

1. **Submission & ML Grader Workflow**:
   - Accepts `student_name` and `folder_name`.
   - Parses `SPECIFICATIONS.md` from the target folder to extract key functional requirements, criteria, edge cases, and constraints.
   - Performs intelligent ML / Semantic + Static + Dynamic analysis on the codebase in the folder to evaluate compliance with the specification.
   - Generates an overall score (0–100%) and itemized breakdown of pass/partial/fail criteria.

2. **Single-Line JSON Persistence (`scores.json`)**:
   - Each submission is appended as a single-line JSON record in `scores.json`:
     ```json
     {"id": "sub_123", "student_name": "Alice Smith", "folder_name": "/path/to/project", "score": 92.5, "timestamp": "2026-08-28T15:30:00Z", "breakdown": [...], "feedback": "..."}
     ```

3. **Instructor View & Leaderboard**:
   - Displays all students with:
     - **Highest Score** attained
     - **Latest Submission** (timestamp & score)
     - Total submission count & progress status
   - **Student History Drill-down**: Clicking a student's name opens their complete submission history timeline with scores, folder paths, and grading breakdown.

4. **Modern, Responsive Web UI & CLI**:
   - Clean, premium dark/glassmorphic interface with tabs for **"Submit & Grade"** and **"Instructor Dashboard"**.
   - Built-in CLI `python cli.py --student "Alice" --folder "./submission_folder"`.

---

## Proposed Architecture & File Structure

```
class_grader_2/
├── app.py                      # FastAPI web server and API endpoints
├── cli.py                      # Command line interface for grading
├── scores.json                 # Single-line JSON submission records
├── requirements.txt            # Python dependencies (fastapi, uvicorn, jinja2, rich, etc.)
├── core/
│   ├── __init__.py
│   ├── spec_parser.py          # Extracts requirements, constraints & rubrics from SPECIFICATIONS.md
│   ├── ml_evaluator.py         # ML/LLM semantic evaluation & rule-based grading engine
│   ├── dynamic_runner.py       # Code inspection and execution checks
│   ├── storage.py              # Single-line JSON reader/writer for scores.json
│   └── models.py               # Data models for Submissions, Criteria, Scores
├── static/
│   ├── style.css               # Modern UI styling & micro-animations
│   └── app.js                  # Frontend interactions, instructor modal, submission forms
├── templates/
│   └── index.html              # Main single-page application template (Student & Instructor tabs)
└── sample_submissions/         # Test fixtures for validation
    ├── student_alice_perfect/
    │   ├── SPECIFICATIONS.md
    │   └── app.py
    └── student_bob_partial/
        ├── SPECIFICATIONS.md
        └── app.py
```

---

## Verification Plan

### Automated & Unit Tests
- Test single-line JSON persistence in `scores.json` (append, read all, aggregate student stats).
- Test ML/Spec parser with sample markdown specifications.
- Test end-to-end evaluation pipeline with `sample_submissions/student_alice_perfect` and `sample_submissions/student_bob_partial`.

### Manual & Interactive Verification
- Grade submissions via Web UI and verify records in `scores.json`.
- Switch to Instructor View, verify highest score and latest submission columns.
- Click student names and verify the popup/modal reveals all past submissions accurately.
