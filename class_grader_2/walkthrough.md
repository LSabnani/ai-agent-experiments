# ML Specification Grader - Walkthrough & User Guide

The **ML Specification Grader** evaluates student coding projects against a `SPECIFICATIONS.md` file located in the project's folder. It calculates an objective compliance score (0–100%), persists each submission as a single-line JSON entry in `scores.json`, and offers an **Instructor View** to inspect top scores, latest submissions, and historical submissions per student.

---

## Key Features

### 1. Specification & Codebase Evaluation
- Parses requirements, function definitions, edge cases, error handling, and test requirements directly from `SPECIFICATIONS.md`.
- Performs static AST analysis, file discovery, dynamic test execution (`unittest` / `pytest`), and semantic criteria matching.
- Generates granular scores, letter grades (`A+` to `F`), itemized rubric breakdowns, strengths, deductions, and execution logs.

### 2. Single-Line JSON Persistence (`scores.json`)
Every submission is saved on a single line in `scores.json`:
```json
{"id":"aa0fdd97-f69d-440e-9904-a815f26bd701","student_name":"Alice Johnson","folder_name":"sample_submissions/student_alice_perfect","score":100.0,"letter_grade":"A+","timestamp":"2026-08-28T22:38:52.167719+00:00","evaluation_details":{...}}
```

### 3. Dual UI Views: Grader & Instructor Leaderboard
- **Submit & Grade Tab**:
  - Inputs for Student Full Name and Project Folder Path.
  - Quick-select buttons for sample submissions.
  - Live score dial, criteria checklist with pass/partial/fail badges, strengths, deductions, and execution logs.
- **Instructor View Tab**:
  - Summary stats: Total Students, Total Submissions, Class Top Score.
  - Table displaying:
    - **Student Name** (clickable link)
    - **Highest Score** attained
    - **Latest Submission Score**
    - **Latest Submission Timestamp**
    - **Total Submissions Count**
  - **Student History Drill-Down**: Clicking any student's name opens a modal revealing all historical submissions from that student in chronological order.

---

## How to Run

### Web Application (FastAPI & Dashboard UI)
Start the web server:
```bash
python3 -m uvicorn app:app --host 0.0.0.0 --port 8000
```
Open your browser at [http://localhost:8000](http://localhost:8000).

---

### Command Line Interface (CLI)

#### 1. Grade a Student Project
```bash
python3 cli.py --student "Alice Johnson" --folder "sample_submissions/student_alice_perfect"
```

#### 2. View Instructor Summary (Highest Scores & Latest Submissions)
```bash
python3 cli.py --list-students
```

#### 3. View All Submissions from a Specific Student
```bash
python3 cli.py --student-history "Alice Johnson"
```

#### 4. Output Raw JSON Result
```bash
python3 cli.py --student "Bob Smith" --folder "sample_submissions/student_bob_partial" --json
```

---

## Verification & Test Results

All unit tests in `tests/test_grader.py` passed successfully:
- ✓ **Single-line JSON format**: Each submission record is written on exactly one line.
- ✓ **Instructor summary aggregations**: Top scores, latest submissions, and historical drilldown verified.
- ✓ **Specification Parser**: Accurately extracts requirements, categories, weights, and rubric items.
- ✓ **Grade Perfect Submission**: Alice's submission passed all criteria (100% / A+).
- ✓ **Grade Partial Submission**: Bob's submission correctly received deductions (50% / F) for missing functions, missing error checks, and missing unit tests.
