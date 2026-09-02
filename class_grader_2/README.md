# ML Specification Grader

An intelligent Python-based application that evaluates student coding projects against requirements specified in a `SPECIFICATIONS.md` file. It computes a compliance score (0–100%), persists submission records as single-line JSON entries in `outputs/scores.json`, records detailed Gemini telemetry traces, and provides both a **Submit & Grade View**, an **Instructor Dashboard**, **PDF / Text Grade Reports**, and a **Gemini Traces Viewer**.

---

## Features

- **Automated Specification Evaluation**: Parses `SPECIFICATIONS.md` in the submission folder (student repository) to extract functional requirements, functions/methods, error handling, and test requirements.
- **Gemini LLM Rubrics**: Uses Gemini to evaluate the student's implementation against the rubrics defined in `SCORING.md`. This is where the "intelligence" of the grading comes from. It evaluates architecture, edge cases, multi-agent frameworks, and state management using the Gemini API. Displays the exact **AI Model Name** used for evaluation in all reports.
- **Mandatory Requirements**: For the assignments are configured in `SUBMISSIONS.yaml` file in the grader app. Missing an AI Agent automatically deducts a percentage of the total score.
- **GitHub Repository & Subfolder Support**: Directly takes GitHub repository URLs (e.g. `https://github.com/owner/repo` or `https://github.com/owner/repo/tree/main/subfolder`) or local folders.
- **Gemini LLM Semantic Evaluation**: Evaluates architecture, edge cases, multi-agent frameworks, and state management using the Gemini API. Displays the exact **AI Model Name** used for evaluation in all reports.
- **Downloadable PDF & Text Reports**: Students and instructors can download full evaluation reports as styled **`.pdf`** or formatted **`.txt`** files directly from the web interface or CLI.
- **Granular Deductions & Actionable Fix Guidance**: For any non-perfect score, provides quantified deduction reasons (`⚠️ Deduction`) and step-by-step remediation advice (`💡 How to Fix`).
- **Telemetry & Trace Logging**: Full audit trail of `MODEL_CALL`, `MODEL_RESPONSE`, `SKILL_USAGE`, and `TOOL_INVOCATION` events saved to `outputs/gemini_traces.jsonl` and `outputs/traces/`.
- **Single-Line JSON Persistence (`outputs/scores.json`)**: Every submission is appended as a standalone single-line JSON record.
- **Instructor Dashboard**:
  - Displays a summary table of all students with their **highest score**, **latest score**, **model used**, and **latest submission timestamp**.
  - **Student Drill-Down**: Clicking any student's name opens a modal displaying all historical submissions with quick download buttons.

---

## Installation & Setup

1. **Activate your Python Virtual Environment**:
   ```bash
   source .venv/bin/activate
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install reportlab
   ```

3. **Configure Environment (`.env`)**:
   Create or edit `.env` with your Google API Key and preferred model:
   ```env
   GOOGLE_API_KEY="your_api_key_here"
   MODEL="gemini-3.5-flash"
   FALLBACK_MODEL="gemini-3.5-flash"
   ```

---

## Starting the Web Application

To launch the web server and user interface:

```bash
python3 -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Once running, open your web browser at:
👉 **[http://localhost:8000](http://localhost:8000)**

---

## Using the Web Application

### 1. Submit & Grade View
1. Navigate to the **"Submit & Grade"** tab.
2. Select the **Course / Class** and **Assignment** from the dropdowns (dynamically loaded from `SUBMISSIONS.yaml`).
3. Enter the **Student Full Name** (e.g. `Alice Johnson`).
4. Enter either a **Local Folder Path** or a **GitHub URL** (e.g. `https://github.com/owner/repo/tree/main/my-apps/travel-Itinerary-builder`).
5. Click **"Run ML Evaluation"**.
6. View the real-time score, mandatory criteria at the top of the breakdown, model badge (`🤖 Model: gemini-3.5-flash`), and deficiency deduction alerts.
7. Click **"Download PDF (.pdf)"**, **"Download Text (.txt)"**, or **"🖨️ View & Print to PDF"**.

### 2. Mandatory Criteria in `SUBMISSIONS.yaml`
Define class assignments and mandatory penalty criteria in `SUBMISSIONS.yaml`:
```yaml
Agent Engineering:
  My AI Agent Assignments:
    - Code Uses AI Agent: 30%
    - Code Uses Skills in Agent: 20%
```
- Missing an AI Agent automatically subtracts 30% from the grade.
- Missing Agent Skills automatically subtracts 20% from the grade.
- Deficiencies are prominently flagged at the top of the **Grading Summary** and the **Criteria Breakdown**.
1. Navigate to the **"Instructor View"** tab.
2. Review the class leaderboard table showing each student's highest score, latest score, and model used.
3. **Click any student's name** to open their full submission history and download past reports.

---

## Using the Command Line Interface (CLI)

### Grade a Student Project & Export PDF / TXT
```bash
# Grade and view in terminal
python3 cli.py --student "Alice Johnson" --folder "sample_submissions/student_alice_perfect"

# Grade and export to PDF and TXT
python3 cli.py --student "Alice Johnson" --folder "sample_submissions/student_alice_perfect" --export-pdf "report.pdf" --export-txt "report.txt"

# Grade from a GitHub repository link
python3 cli.py --student "Alice Johnson" --folder "https://github.com/owner/repo/tree/main/assignment1"
```

### View Instructor Summary Table
```bash
python3 cli.py --list-students
```

### View Submission History for a Student
```bash
python3 cli.py --student-history "Alice Johnson"
```

---

## Running Automated Tests

```bash
python3 -m unittest discover -s tests -p "test_*.py"
```
