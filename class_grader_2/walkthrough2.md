# Walkthrough: SUBMISSIONS.yaml Integration, Class/Assignment Dropdowns & Deficiency Deductions

## Summary of Changes

We implemented configuration loading from `SUBMISSIONS.yaml` with Class and Assignment dropdown selectors, mandatory prerequisite scoring deductions, and prominent deficiency callouts in the grading summary and at the top of the Criteria Breakdown.

---

### Key Components Added & Modified

1. **`SUBMISSIONS.yaml` Config Parser ([core/submissions_config.py](file:///home/pi-net/Documents/agent_eng_labs/class_grading/class_grader_2/core/submissions_config.py))**:
   - Parses `SUBMISSIONS.yaml`, `submissions.yaml`, `SUBMISSIONS.yml`, or `SUBMISSIONS.md`.
   - Structures Class $\to$ Assignment $\to$ Criteria with explicit penalty percentages (e.g. `Code Uses AI Agent: 30%`, `Code Uses SKills in Agent: 10%`).

2. **UI Class & Assignment Dropdowns ([templates/index.html](file:///home/pi-net/Documents/agent_eng_labs/class_grading/class_grader_2/templates/index.html) & [static/app.js](file:///home/pi-net/Documents/agent_eng_labs/class_grading/class_grader_2/static/app.js))**:
   - Added **Course / Class** and **Assignment** dropdowns positioned before the Student Name and Folder/GitHub inputs.
   - Dynamic auto-population of assignments upon selecting a class.
   - Live information box displaying the active mandatory criteria and their point penalties.

3. **Mandatory Criteria Prepending & Penalty Engine ([core/spec_parser.py](file:///home/pi-net/Documents/agent_eng_labs/class_grading/class_grader_2/core/spec_parser.py) & [core/ml_evaluator.py](file:///home/pi-net/Documents/agent_eng_labs/class_grading/class_grader_2/core/ml_evaluator.py))**:
   - Mandatory assignment criteria are prepended **at the very top of the Criteria Breakdown**.
   - If the student's submission fails to use AI Agents, it receives 0 points for that criterion, subtracting **30%** from the overall score.
   - If the student's submission fails to use Agent Skills, it receives 0 points for that criterion, subtracting **10% / 20%** from the overall score.
   - Prominently displays `⚠️ MANDATORY DEFICIENCY` warnings at the top of the **Grading Summary** and at the top of the **Criteria Breakdown**.

4. **Deep AST & Semantic Script Analysis ([core/code_analyzer.py](file:///home/pi-net/Documents/agent_eng_labs/class_grading/class_grader_2/core/code_analyzer.py))**:
   - Strictly distinguishes between **genuine AI/LLM model calls** and **plain procedural Python classes named 'Agent'**:
     - Plain classes like `class WeatherAgent(BaseAgent):` using hardcoded dictionaries or arithmetic without AI model calls are identified as procedural code and **fail** the mandatory AI Agent requirement.
     - Genuine AI Agent requirement checks for active invocations of Google Gemini (`generate_content`), OpenAI (`chat.completions`), Anthropic Claude, or LLM-backed agent frameworks (Google ADK, LangChain).
   - Generates a structured **`EVIDENCE & AST CODE ANALYSIS REPORT`** with exact line numbers and code snippets to ground the evaluation.

5. **Interactive 2-Box Gemini Traces Viewer ([templates/index.html](file:///home/pi-net/Documents/agent_eng_labs/class_grading/class_grader_2/templates/index.html) & [static/app.js](file:///home/pi-net/Documents/agent_eng_labs/class_grading/class_grader_2/static/app.js))**:
   - **Box 1 (Top Scrollable Box)**: Lists all student submissions with Student Name, Repository / Folder, Model Used, Score & Letter Grade, Timestamp, and Event Count. Clicking any submission highlights it and updates Box 2.
   - **Box 2 (Bottom Events & Logs Box)**: Displays the full execution timeline and logs for the selected submission (`TRACE_START`, `SKILL_USAGE`, `MODEL_CALL`, `MODEL_RESPONSE`, `TOOL_INVOCATION`, `TRACE_END`) with live filtering pills and collapsible prompt/response payload viewers.

6. **Instructor View Multi-Assignment Support & Filtering ([core/storage.py](file:///home/pi-net/Documents/agent_eng_labs/class_grading/class_grader_2/core/storage.py), [templates/index.html](file:///home/pi-net/Documents/agent_eng_labs/class_grading/class_grader_2/templates/index.html), & [static/app.js](file:///home/pi-net/Documents/agent_eng_labs/class_grading/class_grader_2/static/app.js))**:
   - **Multi-Assignment Submission Rows**: Instructor summary records in `core/storage.py` are grouped by `(student_name, class_name, assignment_name)`. When a student submits repositories for multiple different assignments (e.g. `AI Agent Assignments` and `Skill Assignments`), a dedicated summary row is displayed for each assignment.
   - **New Table Columns**: `Course / Class` and `Assignment` columns with structured badge tags. If fields are missing in legacy logs, they are left blank (`--`).
   - **Single-Select Filter Group 1 (Student Name)**: Filters the leaderboard by a specific student across all their assignment submissions.
   - **Single-Select Filter Group 2 (Course / Class & Assignment)**:
     - Dropdown 1 selects the Course/Class.
     - Dropdown 2 dynamically populates with assignments for the selected course.
7. **Single Input Box for Repository or Local Machine Folder ([templates/index.html](file:///home/pi-net/Documents/agent_eng_labs/class_grading/class_grader_2/templates/index.html), [static/app.js](file:///home/pi-net/Documents/agent_eng_labs/class_grading/class_grader_2/static/app.js), [core/grader.py](file:///home/pi-net/Documents/agent_eng_labs/class_grading/class_grader_2/core/grader.py), & [core/git_fetcher.py](file:///home/pi-net/Documents/agent_eng_labs/class_grading/class_grader_2/core/git_fetcher.py))**:
   - **Unified Single Input Box**: Replaced the separate repository and subfolder fields with a single input: `Repository or Local Machine Folder`.
   - **Local Machine Folder Support**: Users can enter local directory paths on this machine (e.g. `/home/pi-net/Documents/agent_eng_labs/...` or relative paths like `sample_submissions/student_alice_perfect`). Tilde (`~`) paths and surrounding quotes are cleanly expanded and verified.
   - **GitHub Repository URL Support**: Single-box input supports root repository URLs (e.g. `https://github.com/owner/repo`) as well as tree URLs with embedded branch and subfolders (e.g. `https://github.com/owner/repo/tree/main/subfolder/path`).

8. **Gemini Traces Viewer Filtering by Student, Course, Assignment, & Date Range ([templates/index.html](file:///home/pi-net/Documents/agent_eng_labs/class_grading/class_grader_2/templates/index.html), [static/app.js](file:///home/pi-net/Documents/agent_eng_labs/class_grading/class_grader_2/static/app.js), & [static/style.css](file:///home/pi-net/Documents/agent_eng_labs/class_grading/class_grader_2/static/style.css))**:
   - **Student Name Filter**: Dropdown with `All Students` and distinct student names found in trace records.
   - **Course / Class Filter**: Dropdown strictly sourced from `SUBMISSIONS.yaml` course-level keys (e.g. `Agent Engineering`), eliminating internal schema keys or non-course entries.
   - **Cascading Assignment Filter**: Dynamically updates to show only assignments belonging to the selected course as defined in `SUBMISSIONS.yaml` (e.g., `AI Agent Assignments`, `Skill Assignments`, `Tool Engineering Assignments`, `Multi-Agent Workflows and Human Approval Assignments`).
   - **Date Range Filter**: Start date (`From`) and End date (`To`) date pickers filtering timestamps from `start_time`.
   - **Table Columns Added**: Added `Course / Class` and `Assignment` badge columns directly in the Top Box trace submissions table.
   - **Reset Filters**: One-click button restoring all trace filters to default.

---

## Verification Results

### Automated Unit Tests
```bash
python3 -m unittest discover -s tests -p "test_*.py"
```
**Result**:
```
............
----------------------------------------------------------------------
Ran 12 tests in 19.144s

OK
```
All 12 tests passed, including `test_single_input_local_and_git_resolution` and `test_instructor_multi_assignment_summaries`.
