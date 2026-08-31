# ML Specification Grader

An intelligent Python-based application that evaluates student coding projects against requirements specified in a `SPECIFICATIONS.md` file. It computes a compliance score (0–100%), persists submission records as single-line JSON entries in `outputs/scores.json`, records detailed Gemini telemetry traces, and provides both a **Submit & Grade View**, an **Instructor Dashboard**, and a **Gemini Traces Viewer**.

---

## Features

- **Automated Specification Evaluation**: Parses `SPECIFICATIONS.md` from the target folder to extract functional requirements, functions/methods, error handling, and test requirements.
- **Multi-Vector Code Inspection**: Analyzes AST symbols, file presence, code syntax, and executes dynamic unit tests (`unittest`/`pytest`) in an isolated subprocess.
- **Gemini LLM Semantic Evaluation**: Evaluates architecture, edge cases, multi-agent frameworks, and state management using the Gemini API (model and API key loaded from `.env`).
- **Telemetry & Trace Logging**: Full audit trail of `MODEL_CALL`, `MODEL_RESPONSE`, `SKILL_USAGE`, and `TOOL_INVOCATION` events with latency ms and token counts saved to `outputs/gemini_traces.jsonl` and `outputs/traces/`.
- **Single-Line JSON Persistence (`outputs/scores.json`)**: Every submission is appended as a standalone single-line JSON record.
- **Instructor Dashboard**:
  - Displays a summary table of all students with their **highest score**, **latest submission score**, and **latest submission timestamp**.
  - **Student Drill-Down**: Clicking any student's name opens a modal displaying all historical submissions from that student.
- **Dual Interface**: Includes both a modern, responsive Web Dashboard and a full-featured Command Line Interface (CLI).

---

## Installation & Setup

1. **Activate your Python Virtual Environment**:
   ```bash
   source .venv/bin/activate
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment (`.env`)**:
   Create or edit `.env` with your Google API Key and preferred model:
   ```env
   GOOGLE_API_KEY="your_api_key_here"
   MODEL="gemini-2.5-flash"
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
2. Enter the **Student Full Name** (e.g. `Alice Johnson`).
3. Enter the **Project Folder Path** containing `SPECIFICATIONS.md` (or click one of the quick sample chips).
4. Click **"Run ML Evaluation"**.
5. View the real-time score dial, letter grade, strengths, deductions, itemized criteria breakdown, and execution logs.
6. The submission is automatically saved to `outputs/scores.json`.

### 2. Instructor Dashboard
1. Navigate to the **"Instructor View"** tab in the top navigation bar.
2. Review class statistics: Total Students, Total Submissions, and Class Top Score.
3. Review the leaderboard table showing each student's highest score and latest submission.
4. **Click any student's name** to view all past submissions from that student.

### 3. Gemini Telemetry Traces
1. Navigate to the **"Gemini Traces"** tab.
2. View real-time logs of all `MODEL_CALL`, `MODEL_RESPONSE`, `SKILL_USAGE`, and `TOOL_INVOCATION` events with exact durations, timestamps, and payload details.

---

## Using the Command Line Interface (CLI)

### Grade a Student Project
```bash
python3 cli.py --student "Alice Johnson" --folder "sample_submissions/student_alice_perfect"
```

### View Instructor Summary Table (Highest & Latest Scores)
```bash
python3 cli.py --list-students
```

### View Submission History for a Specific Student
```bash
python3 cli.py --student-history "Alice Johnson"
```

### View Gemini Telemetry Traces
```bash
python3 cli.py --view-traces
```

### Output Results as JSON
```bash
python3 cli.py --student "Bob Smith" --folder "sample_submissions/student_bob_partial" --json
```

---

## Output Files & Telemetry Logs

All evaluation results and trace logs are saved inside the `outputs/` folder:

- **`outputs/scores.json`**: Single-line JSON submission records.
- **`outputs/gemini_traces.jsonl`**: Real-time event stream of Gemini model calls, responses, tool calls, and skill usages.
- **`outputs/traces/<trace_id>.json`**: Comprehensive individual trace report generated per grading run.

---

## Running Automated Tests

```bash
python3 -m unittest discover -s tests -p "test_*.py"
```
