import argparse
import sys
import os
import json
from core.grader import Grader
from core.storage import ScoreStorage, DEFAULT_SCORES_PATH
from core.telemetry import tracer


def main():
    parser = argparse.ArgumentParser(description="ML Specification Grader CLI")
    parser.add_argument("--student", "-s", type=str, help="Student Name (e.g. 'Alice Johnson')")
    parser.add_argument("--folder", "-f", type=str, help="Path to project directory containing SPECIFICATIONS.md")
    parser.add_argument("--scores-file", default=DEFAULT_SCORES_PATH, help=f"Path to scores JSON file (default: {DEFAULT_SCORES_PATH})")
    parser.add_argument("--list-students", action="store_true", help="Display instructor summary of all students")
    parser.add_argument("--student-history", type=str, help="Show all submissions for a specific student")
    parser.add_argument("--view-traces", action="store_true", help="Display recent Gemini model calls, responses, skill usages, and tool invocations")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()
    storage = ScoreStorage(args.scores_file)

    # 1. View Traces
    if args.view_traces:
        events = tracer.get_trace_history(limit=30)
        if args.json:
            print(json.dumps(events, indent=2))
            return
        
        print("\n" + "="*80)
        print(f"{'GEMINI TELEMETRY TRACE LOG (outputs/gemini_traces.jsonl)':^80}")
        print("="*80)
        if not events:
            print("No telemetry events recorded yet.")
        for ev in events:
            ev_type = ev.get("event_type", "EVENT")
            ts = ev.get("timestamp", "")
            dur = f"{ev.get('duration_ms', 0):.1f}ms" if "duration_ms" in ev else ""
            details = ev.get("details", {})
            print(f"[{ts}] [{ev_type:<16}] {dur:>8} | {json.dumps(details)[:90]}...")
        print("="*80 + "\n")
        return

    # 2. Show all student summaries (Instructor view in CLI)
    if args.list_students:
        summaries = storage.get_instructor_student_summaries()
        if args.json:
            print(json.dumps([s.model_dump() for s in summaries], indent=2))
            return
        
        print("\n" + "="*80)
        print(f"{'INSTRUCTOR DASHBOARD - STUDENT SUMMARY':^80}")
        print("="*80)
        print(f"{'Student Name':<25} | {'Highest Score':<15} | {'Latest Score':<15} | {'Submissions':<12}")
        print("-" * 80)
        if not summaries:
            print("No submissions recorded yet.")
        for s in summaries:
            print(f"{s.student_name:<25} | {s.highest_score:>5.1f}% ({s.highest_grade:<2})  | {s.latest_score:>5.1f}% ({s.latest_grade:<2})  | {s.total_submissions:>5}")
        print("="*80 + "\n")
        return

    # 3. Show student history
    if args.student_history:
        subs = storage.get_submissions_for_student(args.student_history)
        if args.json:
            print(json.dumps([s.model_dump() for s in subs], indent=2))
            return
        
        print("\n" + "="*80)
        print(f"SUBMISSION HISTORY FOR: {args.student_history.upper()}")
        print("="*80)
        if not subs:
            print(f"No submissions found for student '{args.student_history}'.")
        for idx, sub in enumerate(subs, 1):
            print(f"[{idx}] Timestamp: {sub.timestamp} | Score: {sub.score}% ({sub.letter_grade})")
            print(f"    Folder: {sub.folder_name}")
            if sub.evaluation_details:
                print(f"    Summary: {sub.evaluation_details.summary}")
            print("-" * 80)
        print("="*80 + "\n")
        return

    # 4. Grade a submission
    if not args.student or not args.folder:
        parser.print_help()
        print("\nError: Both --student and --folder are required to run grading.")
        sys.exit(1)

    grader = Grader(scores_file=args.scores_file)
    try:
        sub_record, eval_result = grader.grade_submission(args.student, args.folder)
        
        if args.json:
            print(sub_record.model_dump_json(indent=2))
            return

        print("\n" + "="*80)
        print(f"EVALUATION RESULT: {args.student.upper()} - {os.path.basename(args.folder)}")
        print("="*80)
        print(f"Overall Score : {eval_result.percentage_score}% ({eval_result.letter_grade})")
        print(f"Points        : {eval_result.total_score} / {eval_result.max_possible_score}")
        print(f"Summary       : {eval_result.summary}")
        print(f"Stored in     : {args.scores_file} (Single-line JSON)")
        print(f"Trace logs in : outputs/gemini_traces.jsonl and outputs/traces/")
        print("\n--- CRITERIA BREAKDOWN ---")
        for c in eval_result.criteria:
            status_icon = "✓ PASS" if c.status == "PASS" else ("⚠ PARTIAL" if c.status == "PARTIAL" else "✗ FAIL")
            print(f"[{status_icon:<9}] {c.title:<35} | {c.earned_score:>4.1f}/{c.max_score:<4.1f} pts")
            print(f"             Feedback: {c.feedback}")
            if c.evidence:
                print(f"             Evidence: {c.evidence}")
        
        if eval_result.strengths:
            print("\n--- KEY STRENGTHS ---")
            for s in eval_result.strengths:
                print(f"  {s}")

        if eval_result.deductions:
            print("\n--- DEDUCTIONS & AREAS FOR IMPROVEMENT ---")
            for d in eval_result.deductions:
                print(f"  {d}")

        print("="*80 + "\n")

    except Exception as e:
        print(f"\nError during evaluation: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
