# Implementation Plan: SUBMISSIONS.yaml Integration, Class/Assignment Dropdowns & Deficiency Deductions

Support class and assignment selection from `SUBMISSIONS.yaml` with strict mandatory criteria evaluation (e.g., deducting 30% for missing AI Agent, 20% for missing Skills in Agent), prominent deficiency callouts in summary, and top-of-breakdown positioning.

## User Review Required

> [!IMPORTANT]
> - `SUBMISSIONS.yaml` in the project root defines classes, assignments, and specific mandatory criteria weights (e.g. `Code Uses AI Agent: 30%`, `Code Uses Skills in Agent: 20%`).
> - When an assignment is chosen, these criteria are placed **at the top of the Criteria Breakdown** and evaluated first.
> - Any missing required component directly reduces the overall score by the declared percentage (e.g., -30% without AI Agent, -20% without Agent Skills) and displays a prominent warning banner in the summary.

## Proposed Changes

### Configuration & Data Layer

#### [NEW] [SUBMISSIONS.yaml](file:///home/pi-net/Documents/agent_eng_labs/class_grading/class_grader_2/SUBMISSIONS.yaml)
- Create `SUBMISSIONS.yaml` with classes (e.g. `Agent Engineering`) and assignments (e.g. `my_first_agent_app`, `travel_itinerary_builder`, `weather_dashboard`) and their penalty percentages.

#### [NEW] [core/submissions_config.py](file:///home/pi-net/Documents/agent_eng_labs/class_grading/class_grader_2/core/submissions_config.py)
- Helper class to parse `SUBMISSIONS.yaml` / `submissions.yaml` with fallback defaults.
- Retrieves available classes, assignments, and criteria with parsed penalty percentages.

#### [MODIFY] [core/models.py](file:///home/pi-net/Documents/agent_eng_labs/class_grading/class_grader_2/core/models.py)
- Add `class_name: Optional[str] = None` and `assignment_name: Optional[str] = None` to `GradeRequest`, `SubmissionRecord`, and `StudentSummary`.
- Add `is_mandatory: bool = False` and `deficiency_warning: Optional[str] = None` to `CriterionResult` and `EvaluationResult`.

---

### Evaluation & Scoring Engine

#### [MODIFY] [core/spec_parser.py](file:///home/pi-net/Documents/agent_eng_labs/class_grading/class_grader_2/core/spec_parser.py)
- Accept `class_name` and `assignment_name`.
- Load additional criteria from `SUBMISSIONS.yaml` and prepend them to the criteria list so they appear **at the very top of the criteria breakdown**.
- Scale baseline rubric weights appropriately so total possible remains normalized to 100%.

#### [MODIFY] [core/ml_evaluator.py](file:///home/pi-net/Documents/agent_eng_labs/class_grading/class_grader_2/core/ml_evaluator.py)
- Detect agent usage (checking for `Agent`, `Google Antigravity SDK`, `ParallelAgent`, `LoopAgent`, LLM model calls, etc.) and skill usage (checking for `skills/`, `SKILL.md`, `Skill`, etc.).
- Enforce strict mathematical deduction for missing mandatory criteria (e.g., subtract 30% if no AI Agent, subtract 20% if no Skills in Agent).
- Add prominent deficiency warnings into `EvaluationResult.summary` and `EvaluationResult.deductions`.

#### [MODIFY] [core/grader.py](file:///home/pi-net/Documents/agent_eng_labs/class_grading/class_grader_2/core/grader.py)
- Pass `class_name` and `assignment_name` to `SpecParser`, `MLEvaluator`, and store them in `SubmissionRecord`.

---

### API & Web Frontend

#### [MODIFY] [app.py](file:///home/pi-net/Documents/agent_eng_labs/class_grading/class_grader_2/app.py)
- Add `GET /api/config/submissions` endpoint returning classes, assignments, and criteria.
- Update `/api/grade` to accept and pass `class_name` and `assignment_name`.

#### [MODIFY] [templates/index.html](file:///home/pi-net/Documents/agent_eng_labs/class_grading/class_grader_2/templates/index.html)
- Add **Class Dropdown** (`#class-select`) and **Assignment Dropdown** (`#assignment-select`) before the Student Name input.
- Show selected assignment criteria summary badge.

#### [MODIFY] [static/app.js](file:///home/pi-net/Documents/agent_eng_labs/class_grading/class_grader_2/static/app.js)
- Fetch `/api/config/submissions` on startup and populate Class & Assignment dropdowns.
- Send selected `class_name` and `assignment_name` in `/api/grade` payload.
- Highlight mandatory criteria and deficiency alerts prominently at the top of the results.

#### [MODIFY] [cli.py](file:///home/pi-net/Documents/agent_eng_labs/class_grading/class_grader_2/cli.py)
- Add `--class-name` and `--assignment` arguments.

---

## Verification Plan

### Automated Tests
- Run `python3 -m unittest discover -s tests -p "test_*.py"` to test:
  1. `SUBMISSIONS.yaml` parsing.
  2. Scoring deduction when AI Agent or Skill is missing.
  3. Prepending criteria to the top of the breakdown.

### Manual Verification
1. Launch `uvicorn app:app --port 8000 --reload`.
2. Select **Agent Engineering** -> **my_first_agent_app**.
3. Grade a submission with and without agent/skill implementations, verifying:
   - Without AI Agent: -30% deducted, deficiency shown in summary & top criterion.
   - Without Skills: -20% deducted, deficiency shown in summary & top criterion.
