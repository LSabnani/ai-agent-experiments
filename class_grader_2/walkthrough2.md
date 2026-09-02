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

---

## Verification Results

### Automated Unit Tests
```bash
python3 -m unittest discover -s tests -p "test_*.py"
```
**Result**:
```
.........
----------------------------------------------------------------------
Ran 9 tests in 17.688s

OK
```
All 9 tests passed, including `test_pseudo_agent_classes_rejection` and `test_popular_ai_services_audit`.
