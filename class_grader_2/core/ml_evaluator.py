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
                 model_name: Optional[str] = None, trace_id: Optional[str] = None,
                 scoring_content: Optional[str] = None,
                 class_name: Optional[str] = None,
                 assignment_name: Optional[str] = None):
        self.folder_path = folder_path
        self.spec_content = spec_content
        self.criteria = criteria
        self.model_name = model_name or get_model_name()
        self.fallback_model_name = get_fallback_model_name()
        self.trace_id = trace_id or "adhoc_eval"
        self.scoring_content = scoring_content
        self.class_name = class_name
        self.assignment_name = assignment_name
        
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

        if not api_key:
            raise RuntimeError("The grader is not available at this time. (API key not configured)")

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
                    print(f"Warning: Fallback model '{self.fallback_model_name}' also failed ({fallback_err}).")

        # If the app can't call the model, display message that grader is not available
        raise RuntimeError("The grader is not available at this time. Please try again later.")

    def _evaluate_with_gemini_llm(self, api_key: str, active_model: str) -> EvaluationResult:
        """Evaluates compliance by prompting Gemini with deep script AST evidence, criteria details, deductions, and fix recommendations."""
        code_summary = self.snapshot.get_summary_text(max_length=25000)
        evidence_report = self.snapshot.get_deep_analysis_report()
        
        criteria_list_str = "\n".join([
            f"- Criterion ID: {c.id} | Title: {c.title} | Max Points: {c.weight * 10} | Category: {c.category} | Mandatory: {c.is_mandatory} | Description: {c.description}"
            for c in self.criteria
        ])

        assignment_info = f"\n=== ACTIVE CLASS & ASSIGNMENT ===\nClass: {self.class_name}\nAssignment: {self.assignment_name}\n" if self.class_name and self.assignment_name else ""
        scoring_section = f"\n=== SCORING DISTRIBUTIONS (SCORING.md) ===\n{self.scoring_content}\n" if self.scoring_content else ""

        prompt = f"""You are an expert automated code grader and teaching assistant.
Your task is to thoroughly analyze the student codebase and script execution against the provided SPECIFICATIONS.md, SCORING.md distributions, and mandatory assignment requirements.
{assignment_info}
{scoring_section}
=== SPECIFICATIONS.md ===
{self.spec_content}

{evidence_report}

=== CODEBASE SUMMARY & SCRIPTS ({os.path.basename(self.folder_path)}) ===
{code_summary}

=== EVALUATION CRITERIA TO SCORE ===
{criteria_list_str}

Please perform a rigorous, granular evaluation for EVERY criterion by analyzing the scripts and AST evidence.

CRITICAL INSTRUCTIONS FOR MANDATORY SCRIPT REQUIREMENTS:
1. "Code Uses AI Agent" (or similar):
   - Analyze the codebase to confirm if genuine AI/LLM model calls or generative AI SDKs are actively used (e.g. Google GenAI/Gemini `generate_content`, OpenAI `chat.completions`, Claude, LangChain with LLMs, Google ADK with Gemini).
   - CRITICAL: A plain Python class named 'Agent' or 'WeatherAgent' that merely uses hardcoded lookup dictionaries or ThreadPoolExecutor WITHOUT any LLM or AI model integration DOES NOT qualify as an AI Agent!
   - If genuine AI/LLM calls are present, cite the exact file, line, and SDK call in "evidence".
   - If NO genuine AI/LLM calls exist (even if classes are named 'Agent'), award 0.0 earned points, set status to 'FAIL', specify deduction_reason as "-50.0 pts: No AI/LLM model services (Google Gemini, OpenAI, etc.) are integrated; classes named 'Agent' contain only hardcoded procedural logic.", and provide actionable fix_recommendation.

2. "Code Uses Skills in Agent" (or similar):
   - Analyze if custom Agent Skills were created (e.g., `SKILL.md` skill directories, `@tool` decorators, or tool functions registered in `tools=[...]`).
   - If Skills are present, cite the exact skill definition file and tool functions in "evidence".
   - If NO Skills or tool registrations exist, award 0.0 earned points, set status to 'FAIL', and explain that no agent skills were created.

3. "Code Uses RAG in Agent" (or similar):
   - Analyze if Retrieval-Augmented Generation was built (vector DBs like ChromaDB/FAISS, embeddings, similarity search, document retriever, context injection into prompt).
   - If RAG is present, cite the exact vector store and retrieval lines in "evidence".
   - If NO RAG pipeline exists, award 0.0 earned points, set status to 'FAIL', and explain that no RAG components were found.

IMPORTANT INSTRUCTIONS FOR SCORING REASONS & DEDUCTIONS:
- If a criterion earns a PERFECT score: Cite the exact file names, line numbers, and script implementations that fulfilled the requirement in "evidence" and "feedback".
- If a criterion earns a PARTIAL or ZERO score:
  1. Provide a comprehensive explanation in "feedback" detailing what requirements were met versus what was missing.
  2. In "deduction_reason", specify the exact reason points were deducted.
  3. In "fix_recommendation", provide concrete, actionable implementation guidance (such as code patterns or missing files) so the student knows exactly how to fix the issue.
  4. In "evidence", cite specific code lines, functions, or explicitly state what script evidence is absent.

For each criterion, return:
1. "id": the exact criterion ID.
2. "earned_score": number between 0 and max_score.
3. "status": "PASS", "PARTIAL", or "FAIL".
4. "feedback": Comprehensive detailed explanation of the evaluation rationale and findings.
5. "deduction_reason": Explicit explanation of why points were lost (null if full score).
6. "fix_recommendation": Actionable steps/guidance to achieve full marks (null if full score).
7. "evidence": specific script line numbers, SDK calls, skill files, or explicit statement of missing evidence.

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
      "deduction_reason": null,
      "fix_recommendation": null,
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

        deficiencies: List[str] = []

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
            deduction_reason = item.get("deduction_reason")
            fix_recommendation = item.get("fix_recommendation")

            # Check for mandatory deficiency
            if crit.is_mandatory or crit.category == "Mandatory Requirement":
                if earned < max_score * 0.5 or status == "FAIL":
                    pct_deducted = (max_score - earned) / 10.0
                    def_msg = f"⚠️ MANDATORY DEFICIENCY: Code is missing required '{crit.title}' (-{pct_deducted:.0f}% penalty applied)."
                    deficiencies.append(def_msg)
                    if not deduction_reason:
                        deduction_reason = f"-{max_score - earned:.1f} pts: Missing required {crit.title}."
                    if not fix_recommendation:
                        fix_recommendation = f"Implement {crit.title} in your codebase to satisfy this mandatory assignment requirement."

            if earned < max_score and not deduction_reason:
                deduction_reason = f"-{max_score - earned:.1f} pts: Implementation does not completely fulfill all conditions in specification."

            criterion_results.append(CriterionResult(
                id=crit.id,
                title=crit.title,
                description=crit.description,
                max_score=max_score,
                earned_score=round(earned, 1),
                status=status,
                feedback=feedback,
                evidence=evidence,
                category=crit.category,
                is_mandatory=crit.is_mandatory,
                deduction_reason=deduction_reason,
                fix_recommendation=fix_recommendation
            ))

        percentage = round((total_earned / total_possible * 100.0) if total_possible > 0 else 0.0, 1)
        letter_grade = self._calculate_letter_grade(percentage)

        raw_summary = result_json.get("overall_summary", f"Model ({active_model}) evaluated {len(self.criteria)} criteria.")
        
        # If deficiencies were detected, place them prominently at the top of the summary
        if deficiencies:
            summary = "\n".join(deficiencies) + "\n\n" + raw_summary
        else:
            summary = raw_summary

        return EvaluationResult(
            total_score=round(total_earned, 2),
            max_possible_score=round(total_possible, 2),
            percentage_score=percentage,
            letter_grade=letter_grade,
            summary=summary,
            model_used=active_model,
            class_name=self.class_name,
            assignment_name=self.assignment_name,
            deficiencies=deficiencies,
            criteria=criterion_results,
            strengths=result_json.get("strengths", [])[:8],
            deductions=(deficiencies + result_json.get("deductions", []))[:10],
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
                deduction_msg = f"⚠ Partial {crit.title} ({res.earned_score}/{res.max_score} pts): {res.deduction_reason or res.feedback}"
                deductions.append(deduction_msg)
            else:
                deduction_msg = f"✗ Failed {crit.title} (0/{res.max_score} pts): {res.deduction_reason or res.feedback}"
                deductions.append(deduction_msg)

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

        # 0. Mandatory Requirement: AI Agent Usage & Popular AI Services
        if "ai agent" in lower_desc or "code uses ai agent" in lower_desc or "gemini" in lower_desc or "openai" in lower_desc:
            gemini_info = self.snapshot.ai_services_audit.get("Google Gemini", {})
            openai_info = self.snapshot.ai_services_audit.get("OpenAI / OpenAI Agents", {})
            
            any_service_used = self.snapshot.has_genuine_ai_agent
            any_service_imported = gemini_info.get("imported") or openai_info.get("imported")
            
            if any_service_used:
                first_ev = self.snapshot.genuine_ai_calls[0] if self.snapshot.genuine_ai_calls else {"file": "scripts", "line": 1, "description": "AI Agent Service Call"}
                call_sites = gemini_info.get("call_sites", []) + openai_info.get("call_sites", [])
                call_desc = f"Call site: {call_sites[0]}" if call_sites else f"{first_ev['file']}:L{first_ev['line']}"
                ev_str = f"Found {len(self.snapshot.genuine_ai_calls)} active AI Model / Agent calls ({call_desc})."
                return CriterionResult(
                    id=crit.id,
                    title=crit.title,
                    description=crit.description,
                    max_score=max_score,
                    earned_score=max_score,
                    status="PASS",
                    feedback=f"Full Credit: Popular AI service SDKs are imported and actively called in code execution. Evidence: {ev_str}",
                    evidence=ev_str,
                    category=crit.category,
                    is_mandatory=crit.is_mandatory
                )
            elif any_service_imported:
                imp_sites = gemini_info.get("import_sites", []) + openai_info.get("import_sites", [])
                imp_desc = imp_sites[0] if imp_sites else "Script imports"
                return CriterionResult(
                    id=crit.id,
                    title=crit.title,
                    description=crit.description,
                    max_score=max_score,
                    earned_score=round(max_score * 0.25, 1),
                    status="PARTIAL",
                    feedback=f"Incomplete Usage: AI service SDK is imported ({imp_desc}), but no active model generation or agent execution calls were found.",
                    evidence=f"Imported at {imp_desc}, but 0 generation/execution calls made.",
                    category=crit.category,
                    is_mandatory=crit.is_mandatory,
                    deduction_reason=f"-{max_score * 0.75:.1f} pts: AI service is imported but not actively called in code.",
                    fix_recommendation="Invoke the AI service model (e.g. client.models.generate_content or client.chat.completions.create) in your execution pipeline."
                )
            else:
                pseudo_msg = f" (Found {len(self.snapshot.pseudo_agent_classes)} classes named 'Agent', but they contain only hardcoded procedural Python without any AI/LLM models.)" if self.snapshot.pseudo_agent_classes else ""
                return CriterionResult(
                    id=crit.id,
                    title=crit.title,
                    description=crit.description,
                    max_score=max_score,
                    earned_score=0.0,
                    status="FAIL",
                    feedback=f"Missing AI Agent Implementation: Codebase contains no genuine AI/LLM services (Google Gemini, OpenAI, Claude) imported or called in scripts.{pseudo_msg}",
                    evidence=f"AST & semantic script scan found 0 genuine AI/LLM model calls.{pseudo_msg}",
                    category=crit.category,
                    is_mandatory=crit.is_mandatory,
                    deduction_reason=f"-{max_score:.1f} pts: Missing required AI Agent services in scripts.",
                    fix_recommendation="Import and call a popular AI service (e.g. from google import genai or import openai) in your Python scripts."
                )

        # 0. Mandatory Requirement: Agent Skills Usage
        if "skill" in lower_desc or "skills in agent" in lower_desc:
            if self.snapshot.skills_evidence:
                first_ev = self.snapshot.skills_evidence[0]
                ev_str = f"Found {len(self.snapshot.skills_evidence)} skill/tool occurrences (e.g. {first_ev.get('file', 'skills')}: {first_ev['description']})."
                return CriterionResult(
                    id=crit.id,
                    title=crit.title,
                    description=crit.description,
                    max_score=max_score,
                    earned_score=max_score,
                    status="PASS",
                    feedback=f"Full Credit: Codebase defines or registers Agent Skills/Tools. Evidence: {ev_str}",
                    evidence=ev_str,
                    category=crit.category,
                    is_mandatory=crit.is_mandatory
                )
            else:
                return CriterionResult(
                    id=crit.id,
                    title=crit.title,
                    description=crit.description,
                    max_score=max_score,
                    earned_score=0.0,
                    status="FAIL",
                    feedback="Missing Agent Skills: Codebase contains no SKILL.md skill definitions, @tool decorators, or agent tool registrations in scripts.",
                    evidence="AST & directory scan found 0 skills/tool registrations.",
                    category=crit.category,
                    is_mandatory=crit.is_mandatory,
                    deduction_reason=f"-{max_score:.1f} pts: Missing required Agent Skills / tool registrations.",
                    fix_recommendation="Create a skills/ directory with SKILL.md or register functions as tools for your agent (tools=[...])."
                )

        # 0. Mandatory Requirement: RAG in Agent
        if "rag" in lower_desc or "retrieval" in lower_desc:
            if self.snapshot.rag_evidence:
                first_ev = self.snapshot.rag_evidence[0]
                ev_str = f"Found {len(self.snapshot.rag_evidence)} RAG components (e.g. {first_ev['file']}:L{first_ev['line']} - {first_ev['description']})."
                return CriterionResult(
                    id=crit.id,
                    title=crit.title,
                    description=crit.description,
                    max_score=max_score,
                    earned_score=max_score,
                    status="PASS",
                    feedback=f"Full Credit: Codebase implements Retrieval-Augmented Generation (RAG). Evidence: {ev_str}",
                    evidence=ev_str,
                    category=crit.category,
                    is_mandatory=crit.is_mandatory
                )
            else:
                return CriterionResult(
                    id=crit.id,
                    title=crit.title,
                    description=crit.description,
                    max_score=max_score,
                    earned_score=0.0,
                    status="FAIL",
                    feedback="Missing RAG Pipeline: Codebase contains no vector database, embeddings, or retrieval pipeline in scripts.",
                    evidence="AST & semantic scan found 0 RAG components.",
                    category=crit.category,
                    is_mandatory=crit.is_mandatory,
                    deduction_reason=f"-{max_score:.1f} pts: Missing required RAG vector database or retrieval pipeline.",
                    fix_recommendation="Implement document chunking, embeddings, and a vector store retriever (e.g. ChromaDB/FAISS) for your agent."
                )

        # 1. Structural Integrity check (10%)
        if "structural integrity" in lower_desc:
            has_parallel = "parallelagent" in all_code_text
            has_loop = "loopagent" in all_code_text
            if has_parallel and has_loop:
                return CriterionResult(
                    id=crit.id,
                    title=crit.title,
                    description=crit.description,
                    max_score=max_score,
                    earned_score=max_score,
                    status="PASS",
                    feedback="Full Credit: Explicitly imports, declares, and constructs ParallelAgent and LoopAgent orchestration patterns.",
                    evidence="ParallelAgent and LoopAgent declared in pipeline.",
                    category=crit.category
                )
            elif has_parallel or has_loop:
                missing = "LoopAgent" if not has_loop else "ParallelAgent"
                found = "ParallelAgent" if has_parallel else "LoopAgent"
                return CriterionResult(
                    id=crit.id,
                    title=crit.title,
                    description=crit.description,
                    max_score=max_score,
                    earned_score=round(max_score * 0.5, 1),
                    status="PARTIAL",
                    feedback=f"Incomplete Agent Architecture: Discovered '{found}' but missing explicit '{missing}' framework declaration.",
                    evidence=f"Found: {found}. Missing: {missing}.",
                    category=crit.category,
                    deduction_reason=f"-{max_score*0.5:.1f} pts: Missing {missing} framework declaration.",
                    fix_recommendation=f"Import and construct {missing} in your pipeline module (e.g. from google.adk.agents import {missing})."
                )
            else:
                return CriterionResult(
                    id=crit.id,
                    title=crit.title,
                    description=crit.description,
                    max_score=max_score,
                    earned_score=0.0,
                    status="FAIL",
                    feedback="Missing Architectural Framework: Neither ParallelAgent nor LoopAgent framework declarations were found in the codebase.",
                    evidence="No agent frameworks discovered in AST scan.",
                    category=crit.category,
                    deduction_reason=f"-{max_score:.1f} pts: Complete absence of required ParallelAgent and LoopAgent classes.",
                    fix_recommendation="Implement both ParallelAgent (for discovery phase) and LoopAgent (for optimization phase) as required by the architecture specification."
                )

        # 2. Context Extraction & State Management (20%)
        if "context extraction" in lower_desc or "state management" in lower_desc:
            has_critic = "critic_feedback" in all_code_text
            has_state = "state" in all_code_text or "session_state" in all_code_text
            if has_critic and has_state:
                return CriterionResult(
                    id=crit.id,
                    title=crit.title,
                    description=crit.description,
                    max_score=max_score,
                    earned_score=max_score,
                    status="PASS",
                    feedback="Full Credit: Global state dictionary maintains structured session keys, and Scheduler actively extracts and responds to critic_feedback across loop iterations.",
                    evidence="Discovered 'critic_feedback' access and state dictionary mutations in pipeline tools.",
                    category=crit.category
                )
            else:
                missing_part = "critic_feedback propagation logic" if not has_critic else "centralized state dictionary schema"
                return CriterionResult(
                    id=crit.id,
                    title=crit.title,
                    description=crit.description,
                    max_score=max_score,
                    earned_score=round(max_score * 0.4, 1),
                    status="PARTIAL",
                    feedback=f"Partial State Management: Code implements basic session state but lacks complete {missing_part}.",
                    evidence="State found without critic_feedback reading.",
                    category=crit.category,
                    deduction_reason=f"-{max_score*0.6:.1f} pts: Missing {missing_part} to adaptively modify subsequent iterations.",
                    fix_recommendation="Ensure the Scheduler reads state['critic_feedback'] from prior loop iterations and adjusts itinerary options accordingly."
                )

        # 3. Graceful Failure Handling (10%)
        if "graceful failure" in lower_desc:
            has_fallback = "fallback" in all_code_text or "generate_fallback" in all_code_text or "try:" in all_code_text
            if has_fallback:
                return CriterionResult(
                    id=crit.id,
                    title=crit.title,
                    description=crit.description,
                    max_score=max_score,
                    earned_score=max_score,
                    status="PASS",
                    feedback="Full Credit: Implements robust fallback generator routines and error-handling try/except guards for impossible constraints (e.g. extremely low budgets).",
                    evidence="Discovered fallback handlers and safety try/except blocks.",
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
                    feedback="Missing Edge Case Protection: No fallback generation or graceful handling for impossible budget inputs was detected.",
                    evidence="No fallback routines found in runner or API layers.",
                    category=crit.category,
                    deduction_reason=f"-{max_score:.1f} pts: Application will crash or throw unhandled exceptions on extreme or impossible inputs.",
                    fix_recommendation="Add a fallback generation function (e.g. generate_fallback_itinerary) and wrap pipeline execution in defensive try-except blocks."
                )

        # 4. Code Quality and Documentation (15%)
        if "code quality" in lower_desc or "documentation" in lower_desc:
            has_docstrings = any('"""' in f or "'''" in f for f in self.snapshot.files.values())
            has_syntax_errors = bool(self.snapshot.syntax_errors)
            if has_docstrings and not has_syntax_errors:
                return CriterionResult(
                    id=crit.id,
                    title=crit.title,
                    description=crit.description,
                    max_score=max_score,
                    earned_score=max_score,
                    status="PASS",
                    feedback="Full Credit: Clean modular code structure, descriptive function docstrings, type annotations, and zero AST syntax errors.",
                    evidence="Docstrings present across all scanned Python modules.",
                    category=crit.category
                )
            elif has_syntax_errors:
                return CriterionResult(
                    id=crit.id,
                    title=crit.title,
                    description=crit.description,
                    max_score=max_score,
                    earned_score=0.0,
                    status="FAIL",
                    feedback=f"Syntax / Parsing Errors Detected: {list(self.snapshot.syntax_errors.values())[0]}",
                    evidence=f"Syntax errors in: {list(self.snapshot.syntax_errors.keys())}",
                    category=crit.category,
                    deduction_reason=f"-{max_score:.1f} pts: Code contains fatal Python syntax errors preventing AST execution.",
                    fix_recommendation="Fix Python syntax errors indicated in the scanned files."
                )
            else:
                return CriterionResult(
                    id=crit.id,
                    title=crit.title,
                    description=crit.description,
                    max_score=max_score,
                    earned_score=round(max_score * 0.5, 1),
                    status="PARTIAL",
                    feedback="Missing Comprehensive Documentation: Several key functions lack docstrings and type annotations.",
                    evidence="Partial docstring coverage across modules.",
                    category=crit.category,
                    deduction_reason=f"-{max_score*0.5:.1f} pts: Functions are missing descriptive docstrings and parameter type hints.",
                    fix_recommendation="Add triple-quoted docstrings ('\"\"\"') describing arguments and return values for every function."
                )

        # 5. Application Quality (5%)
        if "application quality" in lower_desc:
            has_frontend = any(f.endswith(".html") or f.endswith(".css") or "render_template" in c for f, c in self.snapshot.files.items())
            if has_frontend:
                return CriterionResult(
                    id=crit.id,
                    title=crit.title,
                    description=crit.description,
                    max_score=max_score,
                    earned_score=max_score,
                    status="PASS",
                    feedback="Full Credit: High application quality with responsive HTML/CSS frontend UI, form validation, and clear status indicators.",
                    evidence="HTML templates and UI styling present.",
                    category=crit.category
                )
            else:
                return CriterionResult(
                    id=crit.id,
                    title=crit.title,
                    description=crit.description,
                    max_score=max_score,
                    earned_score=round(max_score * 0.6, 1),
                    status="PARTIAL",
                    feedback="Limited UI Quality: Implements backend server logic but lacks a fully styled frontend web interface.",
                    evidence="API backend present without dedicated template views.",
                    category=crit.category,
                    deduction_reason=f"-{max_score*0.4:.1f} pts: Missing polished user-facing frontend UI.",
                    fix_recommendation="Provide an interactive web UI with HTML/CSS templates or frontend components to allow end users to interact with the application."
                )

        # 6. Specific named target files check (e.g. usages.csv, scores.json)
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
                        feedback=f"Missing Target File Logging: Specification requires logging user request data to '{tf}', but '{tf}' is not written in code and is not present on disk.",
                        evidence=f"Neither file '{tf}' nor file-writing operations found in codebase.",
                        category=crit.category,
                        deduction_reason=f"-{max_score:.1f} pts: Complete omission of '{tf}' data logging requirement.",
                        fix_recommendation=f"Implement file logging in append mode ('a') to write rows to '{tf}' containing the required columns."
                    )
                elif file_in_code and not has_csv_handling:
                    return CriterionResult(
                        id=crit.id,
                        title=crit.title,
                        description=crit.description,
                        max_score=max_score,
                        earned_score=round(max_score * 0.4, 1),
                        status="PARTIAL",
                        feedback=f"Incomplete File Logging: Code references filename '{tf}', but is missing standard CSV library formatting (e.g. import csv or csv.writer) to write structured records.",
                        evidence=f"Found string reference to '{tf}' but no csv.writer or csv.DictWriter usage.",
                        category=crit.category,
                        deduction_reason=f"-{max_score*0.6:.1f} pts: Data is not properly serialized into structured CSV format.",
                        fix_recommendation=f"Use Python's built-in 'csv' module (csv.writer or csv.DictWriter) to write structured headers and rows into '{tf}'."
                    )

        # 7. General Semantic Keyword Matching
        stopwords = {
            "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "with", 
            "by", "as", "is", "are", "be", "this", "that", "it", "of", "from", 
            "should", "must", "can", "will", "app", "application", "each", "all",
            "team", "room", "agent", "agents", "loop", "parallel", "milestones", "milestone", "json",
            "completeness", "scoring", "pts", "points"
        }
        # Clean title to remove rubric suffixes
        clean_text_for_keywords = re.sub(r"\(completeness\)|\(\d+%\)|\[.*?\]", "", crit.title + " " + crit.description, flags=re.IGNORECASE)
        words = [w.lower() for w in re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]{2,}\b", clean_text_for_keywords) if w.lower() not in stopwords]
        
        if not words:
            words = [crit.title.lower().split()[0]]

        matched_words = [w for w in words if w in all_symbols or any(w in code for code in self.snapshot.files.values())]
        missing_words = [w for w in words if w not in matched_words]
        ratio = len(matched_words) / max(len(words), 1)

        if ratio >= 0.6:
            return CriterionResult(
                id=crit.id,
                title=crit.title,
                description=crit.description,
                max_score=max_score,
                earned_score=max_score,
                status="PASS",
                feedback=f"Full Credit: Core functional concepts are implemented and match specification requirements.",
                evidence=f"Matched code terms: {matched_words[:4]}",
                category=crit.category
            )
        elif ratio >= 0.35:
            earned = round(max_score * 0.5, 1)
            return CriterionResult(
                id=crit.id,
                title=crit.title,
                description=crit.description,
                max_score=max_score,
                earned_score=earned,
                status="PARTIAL",
                feedback=f"Partially Satisfied: Implemented {len(matched_words)} of {len(words)} expected components, but missing key elements: {', '.join(missing_words[:3])}.",
                evidence=f"Matched: {matched_words[:3]}. Missing concepts: {missing_words[:3]}.",
                category=crit.category,
                deduction_reason=f"-{max_score - earned:.1f} pts: Incomplete implementation of required functionality ({', '.join(missing_words[:3])}).",
                fix_recommendation=f"Implement missing components and logic associated with {', '.join(missing_words[:3])}."
            )
        else:
            return CriterionResult(
                id=crit.id,
                title=crit.title,
                description=crit.description,
                max_score=max_score,
                earned_score=0.0,
                status="FAIL",
                feedback=f"Unfulfilled Requirement: Could not locate implementation or function definitions for: {', '.join(missing_words[:4])}.",
                evidence=f"Missing keywords/symbols in scanned files: {missing_words[:4]}.",
                category=crit.category,
                deduction_reason=f"-{max_score:.1f} pts: No matching code or functional implementation found in project files.",
                fix_recommendation=f"Implement the functionality specified in: '{crit.description[:100]}...'."
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
