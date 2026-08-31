import os
import re
import json
import time
import ast
import requests
from typing import List, Dict, Any, Tuple, Optional
from core.models import Criterion, CriterionResult, EvaluationResult
from core.code_analyzer import CodebaseSnapshot
from core.dynamic_runner import DynamicRunner
from core.config import get_api_key, get_model_name, get_fallback_model_name, load_env
from core.telemetry import tracer

REQUEST_TIMEOUT = int(os.environ.get("GRADER_TIMEOUT", "120"))


class MLEvaluator:
    def __init__(self, folder_path: str, spec_content: str, criteria: List[Criterion], 
                 model_name: Optional[str] = None, trace_id: Optional[str] = None):
        self.folder_path = folder_path
        self.spec_content = spec_content
        self.criteria = criteria
        self.model_name = model_name or get_model_name()
        self.fallback_model_name = get_fallback_model_name()
        self.trace_id = trace_id or "adhoc_eval"
        
        # Tool / Skill: Codebase Snapshot
        snap_start = time.time()
        tool_id = tracer.log_tool_invocation(self.trace_id, "CodebaseSnapshot.scan", {"folder_path": folder_path})
        self.snapshot = CodebaseSnapshot(folder_path)
        snap_dur = (time.time() - snap_start) * 1000
        tracer.log_tool_response(self.trace_id, "CodebaseSnapshot.scan", 
                                {"files_scanned": list(self.snapshot.files.keys()), "functions_found": len(self.snapshot.functions_found)}, 
                                snap_dur, status="SUCCESS", tool_call_id=tool_id)

        self.runner = DynamicRunner(folder_path)

    def evaluate(self) -> EvaluationResult:
        api_key = get_api_key()

        if api_key:
            # 1. Try primary configured model
            try:
                return self._evaluate_with_gemini_llm(api_key, self.model_name)
            except Exception as e:
                print(f"Warning: LLM evaluation with primary model '{self.model_name}' failed ({e}).")
                
                # 2. Try fallback model (gemini-3.5-flash)
                if self.model_name != self.fallback_model_name:
                    try:
                        print(f"Attempting fallback to '{self.fallback_model_name}'...")
                        return self._evaluate_with_gemini_llm(api_key, self.fallback_model_name)
                    except Exception as fallback_err:
                        print(f"Warning: Fallback model '{self.fallback_model_name}' also failed ({fallback_err}), using intelligent heuristic engine.")

        # 3. Heuristic Multi-Vector Evaluation Engine (Offline / Local fallback)
        return self._evaluate_with_heuristics()

    def _evaluate_with_gemini_llm(self, api_key: str, active_model: str) -> EvaluationResult:
        """Evaluates compliance by prompting Gemini with the specification and code snapshot."""
        code_summary = self.snapshot.get_summary_text(max_length=20000)
        
        criteria_list_str = "\n".join([
            f"- Criterion ID: {c.id} | Title: {c.title} | Max Points: {c.weight * 10} | Description: {c.description}"
            for c in self.criteria
        ])

        prompt = f"""You are an expert automated code grader and teaching assistant.
Your task is to evaluate the student codebase against the provided SPECIFICATIONS.md.

=== SPECIFICATIONS.md ===
{self.spec_content}

=== CODEBASE SUMMARY ({os.path.basename(self.folder_path)}) ===
{code_summary}

=== EVALUATION CRITERIA TO SCORE ===
{criteria_list_str}

Please evaluate each criterion rigorously. If a criterion requests a specific feature, file (e.g. usages.csv), or tool that is NOT implemented in the code summary, assign 0.0 or partial score with explicit failure feedback.

For each criterion, return:
1. "id": the exact criterion ID.
2. "earned_score": number between 0 and max_score.
3. "status": "PASS", "PARTIAL", or "FAIL".
4. "feedback": 1-2 concise sentences explaining what was met or missing.
5. "evidence": specific code lines, functions, classes, or patterns found.

Respond ONLY with a valid JSON object in the following format:
{{
  "overall_summary": "Summary of overall quality and spec compliance.",
  "strengths": ["Strength 1", "Strength 2"],
  "deductions": ["Deduction 1", "Deduction 2"],
  "criteria_evaluations": [
    {{
      "id": "crit_1",
      "earned_score": 10.0,
      "status": "PASS",
      "feedback": "...",
      "evidence": "..."
    }}
  ]
}}
"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{active_model}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        generation_config = {
            "temperature": 0.1,
            "response_mime_type": "application/json"
        }
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": generation_config
        }

        # 1. Log MODEL_CALL Trace
        call_event = tracer.log_model_call(
            trace_id=self.trace_id,
            model_name=active_model,
            prompt=prompt,
            generation_config=generation_config,
            endpoint_url=url
        )
        call_id = call_event.get("call_id")

        start_time = time.time()
        resp = requests.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
        duration_ms = (time.time() - start_time) * 1000

        # 2. Log MODEL_RESPONSE Trace
        if resp.status_code == 200:
            data = resp.json()
            usage = data.get("usageMetadata", {})
            tracer.log_model_response(
                trace_id=self.trace_id,
                model_name=active_model,
                response_data=data,
                duration_ms=duration_ms,
                status_code=resp.status_code,
                usage_metadata=usage,
                call_id=call_id
            )
        else:
            tracer.log_model_response(
                trace_id=self.trace_id,
                model_name=active_model,
                response_data=resp.text,
                duration_ms=duration_ms,
                status_code=resp.status_code,
                call_id=call_id
            )

        resp.raise_for_status()
        data = resp.json()
        raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
        result_json = json.loads(raw_text)

        eval_map = {item["id"]: item for item in result_json.get("criteria_evaluations", [])}
        
        criterion_results = []
        total_earned = 0.0
        total_possible = 0.0

        for crit in self.criteria:
            max_score = crit.weight * 10.0
            total_possible += max_score
            item = eval_map.get(crit.id, {})
            earned = float(item.get("earned_score", 0.0))
            earned = max(0.0, min(earned, max_score))
            total_earned += earned

            status = item.get("status", "PASS" if earned >= max_score * 0.85 else ("PARTIAL" if earned > 0 else "FAIL"))
            feedback = item.get("feedback", "Evaluated against codebase.")
            evidence = item.get("evidence", "Semantic match.")

            criterion_results.append(CriterionResult(
                id=crit.id,
                title=crit.title,
                description=crit.description,
                max_score=max_score,
                earned_score=round(earned, 1),
                status=status,
                feedback=feedback,
                evidence=evidence,
                category=crit.category
            ))

        percentage = round((total_earned / total_possible * 100.0) if total_possible > 0 else 0.0, 1)
        letter_grade = self._calculate_letter_grade(percentage)

        return EvaluationResult(
            total_score=round(total_earned, 2),
            max_possible_score=round(total_possible, 2),
            percentage_score=percentage,
            letter_grade=letter_grade,
            summary=result_json.get("overall_summary", f"Model ({active_model}) evaluated {len(self.criteria)} criteria."),
            criteria=criterion_results,
            strengths=result_json.get("strengths", [])[:8],
            deductions=result_json.get("deductions", [])[:8],
            execution_logs=f"Evaluated with LLM Model ({active_model})"
        )

    def _evaluate_with_heuristics(self) -> EvaluationResult:
        criterion_results = []
        strengths = []
        deductions = []

        # Tool Invocation: DynamicRunner
        test_start = time.time()
        tool_call_id = tracer.log_tool_invocation(self.trace_id, "DynamicRunner.run_tests_if_present", {"folder_path": self.folder_path})
        dynamic_test_results = self.runner.run_tests_if_present()
        test_dur = (time.time() - test_start) * 1000
        tracer.log_tool_response(self.trace_id, "DynamicRunner.run_tests_if_present", dynamic_test_results, test_dur, 
                                status="SUCCESS" if dynamic_test_results.get("tests_passed") else "PARTIAL", 
                                tool_call_id=tool_call_id)

        if self.snapshot.syntax_errors:
            for fpath, err in self.snapshot.syntax_errors.items():
                deductions.append(f"Syntax Error in {fpath}: {err}")

        total_earned = 0.0
        total_possible = 0.0

        for crit in self.criteria:
            res = self._evaluate_single_criterion_heuristic(crit, dynamic_test_results)
            criterion_results.append(res)
            total_earned += res.earned_score
            total_possible += res.max_score
            
            if res.status == "PASS":
                strengths.append(f"✓ {crit.title}: {res.feedback}")
            elif res.status == "PARTIAL":
                deductions.append(f"⚠ Partial {crit.title}: {res.feedback}")
            else:
                deductions.append(f"✗ Failed {crit.title}: {res.feedback}")

        percentage = round((total_earned / total_possible * 100.0) if total_possible > 0 else 0.0, 1)
        letter_grade = self._calculate_letter_grade(percentage)

        summary = (
            f"Evaluated {len(self.criteria)} criteria against codebase in '{os.path.basename(self.folder_path)}'. "
            f"Achieved a score of {percentage}% ({letter_grade})."
        )

        logs = dynamic_test_results.get("output", "") if dynamic_test_results.get("has_tests") else "Static AST and structural analysis completed."

        return EvaluationResult(
            total_score=round(total_earned, 2),
            max_possible_score=round(total_possible, 2),
            percentage_score=percentage,
            letter_grade=letter_grade,
            summary=summary,
            criteria=criterion_results,
            strengths=strengths[:8],
            deductions=deductions[:8],
            execution_logs=logs
        )

    def _evaluate_single_criterion_heuristic(self, crit: Criterion, dynamic_tests: Dict[str, Any]) -> CriterionResult:
        max_score = crit.weight * 10.0
        full_text = f"{crit.title} {crit.description}".strip()
        lower_desc = full_text.lower()
        
        all_code_text = " ".join(self.snapshot.files.values()).lower()
        all_symbols = [s.lower() for s in self.snapshot.functions_found + self.snapshot.classes_found]

        # 1. Check for specific named target files or data logging requirements (e.g. usages.csv, scores.json)
        target_files = re.findall(r"\b([a-zA-Z0-9_\-]+\.(?:csv|json|txt|log|sqlite|db))\b", full_text)
        for tf in target_files:
            tf_lower = tf.lower()
            if any(w in lower_desc for w in ["store", "log", "save", "write", "csv", "named", "record"]):
                file_in_code = tf_lower in all_code_text
                file_on_disk = any(tf_lower == os.path.basename(f).lower() for f in self.snapshot.files.keys())
                has_csv_handling = "import csv" in all_code_text or "csv.writer" in all_code_text or "to_csv" in all_code_text if "csv" in tf_lower else True

                if not file_in_code and not file_on_disk:
                    return CriterionResult(
                        id=crit.id,
                        title=crit.title,
                        description=crit.description,
                        max_score=max_score,
                        earned_score=0.0,
                        status="FAIL",
                        feedback=f"Missing implementation: Target file '{tf}' is neither written in code nor present on disk.",
                        evidence=f"Could not find '{tf}' or CSV writer in codebase.",
                        category=crit.category
                    )
                elif file_in_code and not has_csv_handling:
                    return CriterionResult(
                        id=crit.id,
                        title=crit.title,
                        description=crit.description,
                        max_score=max_score,
                        earned_score=round(max_score * 0.4, 1),
                        status="PARTIAL",
                        feedback=f"Referenced '{tf}' but missing standard CSV parsing/logging library.",
                        evidence=f"Found filename '{tf}' in code without csv handling.",
                        category=crit.category
                    )

        # 2. Required Source Files Check (e.g. calculator.py, test_calculator.py)
        source_mentions = re.findall(r"\b([a-zA-Z0-9_\-]+\.(?:py|js|ts|html|css|sh))\b", full_text)
        missing_source = [f for f in source_mentions if not any(f.lower() in existing.lower() for existing in self.snapshot.files.keys())]
        if missing_source and ("deliverables" in lower_desc or "setup" in lower_desc or "required" in lower_desc or "files" in lower_desc):
            return CriterionResult(
                id=crit.id,
                title=crit.title,
                description=crit.description,
                max_score=max_score,
                earned_score=0.0 if len(missing_source) == len(source_mentions) else round(max_score * 0.5, 1),
                status="FAIL" if len(missing_source) == len(source_mentions) else "PARTIAL",
                feedback=f"Missing required file(s): {', '.join(missing_source)}.",
                evidence=f"Present files: {list(self.snapshot.files.keys())}",
                category=crit.category
            )

        # 3. Automated Test Suite Check
        if "test" in lower_desc and ("unit" in lower_desc or "suite" in lower_desc or "pytest" in lower_desc or "coverage" in lower_desc):
            if dynamic_tests.get("has_tests"):
                if dynamic_tests.get("tests_passed"):
                    return CriterionResult(
                        id=crit.id,
                        title=crit.title,
                        description=crit.description,
                        max_score=max_score,
                        earned_score=max_score,
                        status="PASS",
                        feedback="Automated test suite discovered and all tests passed successfully.",
                        evidence="Test suite executed without errors.",
                        category=crit.category
                    )
                else:
                    return CriterionResult(
                        id=crit.id,
                        title=crit.title,
                        description=crit.description,
                        max_score=max_score,
                        earned_score=round(max_score * 0.3, 1),
                        status="PARTIAL",
                        feedback="Tests exist but one or more test cases failed.",
                        evidence=dynamic_tests.get("output", "")[:180],
                        category=crit.category
                    )
            else:
                return CriterionResult(
                    id=crit.id,
                    title=crit.title,
                    description=crit.description,
                    max_score=max_score,
                    earned_score=0.0,
                    status="FAIL",
                    feedback="No unit test suite or test files found in project.",
                    evidence="Looked for test_*.py or *_test.py",
                    category=crit.category
                )

        # 4. Explicit Function Signature Check e.g. `calculate_mean(numbers)` or `add(a, b)`
        func_patterns = re.findall(r"(?:`|\b)([a-zA-Z_][a-zA-Z0-9_]*)\s*\([a-zA-Z0-9_,\s]*\)(?:`|\b)", full_text)
        func_patterns = [fn for fn in func_patterns if len(fn) > 2 and fn.lower() not in {"milestones", "integrity", "management", "handling", "agent", "room", "team", "json", "planner", "pipeline"}]

        if func_patterns:
            matched = [fn for fn in func_patterns if any(fn.lower() == s for s in all_symbols)]
            unmatched = [fn for fn in func_patterns if fn not in matched]

            if not unmatched:
                return CriterionResult(
                    id=crit.id,
                    title=crit.title,
                    description=crit.description,
                    max_score=max_score,
                    earned_score=max_score,
                    status="PASS",
                    feedback="Requirement satisfied with matching function definitions.",
                    evidence=f"Matched functions: {matched}",
                    category=crit.category
                )
            elif matched:
                earned = round(max_score * (len(matched) / len(func_patterns)), 1)
                return CriterionResult(
                    id=crit.id,
                    title=crit.title,
                    description=crit.description,
                    max_score=max_score,
                    earned_score=earned,
                    status="PARTIAL",
                    feedback=f"Found: {', '.join(matched)}, but missing: {', '.join(unmatched)}.",
                    evidence=f"Discovered functions: {matched}",
                    category=crit.category
                )
            else:
                return CriterionResult(
                    id=crit.id,
                    title=crit.title,
                    description=crit.description,
                    max_score=max_score,
                    earned_score=0.0,
                    status="FAIL",
                    feedback=f"Required function(s) not implemented: {', '.join(unmatched)}.",
                    evidence="No matching function definitions found.",
                    category=crit.category
                )

        # 5. Error and Edge-Case Handling Check
        if any(w in lower_desc for w in ["zero", "empty", "exception", "zero_division", "division by zero"]):
            has_error_handling = any("raise ValueError" in c or "raise ZeroDivisionError" in c or "if b == 0" in c or "if not numbers" in c for c in self.snapshot.files.values())
            if has_error_handling:
                return CriterionResult(
                    id=crit.id,
                    title=crit.title,
                    description=crit.description,
                    max_score=max_score,
                    earned_score=max_score,
                    status="PASS",
                    feedback="Robust error handling & validation logic detected.",
                    evidence="Validation & exception guards present.",
                    category=crit.category
                )
            else:
                return CriterionResult(
                    id=crit.id,
                    title=crit.title,
                    description=crit.description,
                    max_score=max_score,
                    earned_score=0.0,
                    status="FAIL",
                    feedback="No explicit error handling (e.g. division by zero or empty input guards) found.",
                    evidence="Missing exception/validation guards",
                    category=crit.category
                )

        # 6. General Semantic Keyword Matching
        stopwords = {
            "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "with", 
            "by", "as", "is", "are", "be", "this", "that", "it", "of", "from", 
            "should", "must", "can", "will", "app", "application", "each", "all",
            "team", "room", "agent", "agents", "loop", "parallel", "milestones", "milestone", "json"
        }
        words = [w.lower() for w in re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]{2,}\b", crit.title + " " + crit.description) if w.lower() not in stopwords]
        
        if not words:
            words = [crit.title.lower()]

        matched_words = [w for w in words if w in all_symbols or any(w in code for code in self.snapshot.files.values())]
        ratio = len(matched_words) / max(len(words), 1)

        if ratio >= 0.7:
            return CriterionResult(
                id=crit.id,
                title=crit.title,
                description=crit.description,
                max_score=max_score,
                earned_score=max_score,
                status="PASS",
                feedback="Requirement fully satisfied in codebase.",
                evidence=f"Matched code terms: {matched_words[:4]}",
                category=crit.category
            )
        elif ratio >= 0.4:
            return CriterionResult(
                id=crit.id,
                title=crit.title,
                description=crit.description,
                max_score=max_score,
                earned_score=round(max_score * 0.5, 1),
                status="PARTIAL",
                feedback=f"Partially met ({len(matched_words)}/{len(words)} key terms found).",
                evidence=f"Matched: {matched_words[:3]}",
                category=crit.category
            )
        else:
            missing = [w for w in words if w not in matched_words]
            return CriterionResult(
                id=crit.id,
                title=crit.title,
                description=crit.description,
                max_score=max_score,
                earned_score=0.0,
                status="FAIL",
                feedback=f"Could not find implementation for: {', '.join(missing[:4])}.",
                evidence="No matching symbols or tokens found in codebase.",
                category=crit.category
            )

    def _calculate_letter_grade(self, percentage: float) -> str:
        if percentage >= 97:
            return "A+"
        elif percentage >= 93:
            return "A"
        elif percentage >= 90:
            return "A-"
        elif percentage >= 87:
            return "B+"
        elif percentage >= 83:
            return "B"
        elif percentage >= 80:
            return "B-"
        elif percentage >= 77:
            return "C+"
        elif percentage >= 73:
            return "C"
        elif percentage >= 70:
            return "C-"
        elif percentage >= 60:
            return "D"
        else:
            return "F"
