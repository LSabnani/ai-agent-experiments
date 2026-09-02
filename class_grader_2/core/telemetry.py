import os
import json
import uuid
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


def get_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TelemetryTracer:
    """Logs detailed traces for model calls, model responses, skill usages, and tool invocations."""
    
    def __init__(self, output_dir: str = "outputs"):
        self.output_dir = output_dir
        self.traces_dir = os.path.join(output_dir, "traces")
        self.log_file = os.path.join(output_dir, "gemini_traces.jsonl")
        self._active_traces: Dict[str, Dict[str, Any]] = {}
        self._ensure_directories()

    def _ensure_directories(self):
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.traces_dir, exist_ok=True)

    def _append_event(self, event: Dict[str, Any]):
        """Appends a single line JSON event to gemini_traces.jsonl and in-memory trace."""
        trace_id = event.get("trace_id")
        if trace_id and trace_id in self._active_traces:
            self._active_traces[trace_id]["events"].append(event)
            
        line = json.dumps(event, separators=(',', ':'))
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception as e:
            print(f"Warning: Failed to write telemetry event to {self.log_file}: {e}")

    def start_trace(self, student_name: str, folder_name: str, 
                    class_name: Optional[str] = None,
                    assignment_name: Optional[str] = None,
                    trace_id: Optional[str] = None) -> str:
        tid = trace_id or str(uuid.uuid4())
        start_time = get_utc_iso()
        self._active_traces[tid] = {
            "trace_id": tid,
            "student_name": student_name,
            "folder_name": folder_name,
            "class_name": class_name,
            "assignment_name": assignment_name,
            "start_time": start_time,
            "status": "RUNNING",
            "events": []
        }
        
        event = {
            "trace_id": tid,
            "timestamp": start_time,
            "event_type": "TRACE_START",
            "details": {
                "student_name": student_name,
                "folder_name": folder_name,
                "class_name": class_name,
                "assignment_name": assignment_name,
                "system": "ML Specification Grader",
                "framework": "Google Gemini Tracing"
            }
        }
        self._append_event(event)
        return tid

    def log_model_call(self, trace_id: str, model_name: str, prompt: str, 
                       generation_config: Optional[Dict[str, Any]] = None, 
                       endpoint_url: Optional[str] = None) -> Dict[str, Any]:
        timestamp = get_utc_iso()
        call_id = str(uuid.uuid4())
        event = {
            "trace_id": trace_id,
            "call_id": call_id,
            "timestamp": timestamp,
            "event_type": "MODEL_CALL",
            "details": {
                "model": model_name,
                "endpoint": endpoint_url or f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent",
                "prompt_length_chars": len(prompt),
                "prompt_preview": prompt[:300] + "..." if len(prompt) > 300 else prompt,
                "full_prompt": prompt,
                "generation_config": generation_config or {"temperature": 0.1, "response_mime_type": "application/json"},
                "start_time_epoch": time.time()
            }
        }
        self._append_event(event)
        return event

    def log_model_response(self, trace_id: str, model_name: str, 
                           response_data: Any, duration_ms: float, 
                           status_code: int = 200, 
                           usage_metadata: Optional[Dict[str, Any]] = None,
                           call_id: Optional[str] = None):
        timestamp = get_utc_iso()
        
        # Extract response text if structured
        response_text = str(response_data)
        if isinstance(response_data, dict) and "candidates" in response_data:
            try:
                response_text = response_data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception:
                pass

        event = {
            "trace_id": trace_id,
            "call_id": call_id,
            "timestamp": timestamp,
            "event_type": "MODEL_RESPONSE",
            "duration_ms": round(duration_ms, 2),
            "details": {
                "model": model_name,
                "status_code": status_code,
                "response_length_chars": len(response_text),
                "response_preview": response_text[:300] + "..." if len(response_text) > 300 else response_text,
                "full_response": response_data,
                "usage_metadata": usage_metadata or {
                    "prompt_token_count": len(response_text) // 4,
                    "candidates_token_count": len(response_text) // 4,
                    "total_token_count": len(response_text) // 2
                },
                "finish_reason": "STOP" if status_code == 200 else "ERROR"
            }
        }
        self._append_event(event)

    def log_tool_invocation(self, trace_id: str, tool_name: str, arguments: Dict[str, Any], caller: str = "MLEvaluator"):
        timestamp = get_utc_iso()
        tool_call_id = str(uuid.uuid4())
        event = {
            "trace_id": trace_id,
            "tool_call_id": tool_call_id,
            "timestamp": timestamp,
            "event_type": "TOOL_INVOCATION",
            "details": {
                "tool_name": tool_name,
                "caller": caller,
                "arguments": arguments,
                "start_time_epoch": time.time()
            }
        }
        self._append_event(event)
        return tool_call_id

    def log_tool_response(self, trace_id: str, tool_name: str, 
                          result: Any, duration_ms: float, 
                          status: str = "SUCCESS", 
                          tool_call_id: Optional[str] = None):
        timestamp = get_utc_iso()
        event = {
            "trace_id": trace_id,
            "tool_call_id": tool_call_id,
            "timestamp": timestamp,
            "event_type": "TOOL_RESPONSE",
            "duration_ms": round(duration_ms, 2),
            "details": {
                "tool_name": tool_name,
                "status": status,
                "result_summary": str(result)[:300] if len(str(result)) > 300 else str(result),
                "result": result
            }
        }
        self._append_event(event)

    def log_skill_usage(self, trace_id: str, skill_name: str, 
                        inputs: Dict[str, Any], outputs: Dict[str, Any], 
                        duration_ms: float, status: str = "SUCCESS"):
        timestamp = get_utc_iso()
        event = {
            "trace_id": trace_id,
            "timestamp": timestamp,
            "event_type": "SKILL_USAGE",
            "duration_ms": round(duration_ms, 2),
            "details": {
                "skill_name": skill_name,
                "status": status,
                "inputs": inputs,
                "outputs": outputs
            }
        }
        self._append_event(event)

    def finish_trace(self, trace_id: str, overall_score: float, letter_grade: str, summary: str):
        end_time = get_utc_iso()
        event = {
            "trace_id": trace_id,
            "timestamp": end_time,
            "event_type": "TRACE_END",
            "details": {
                "overall_score": overall_score,
                "letter_grade": letter_grade,
                "summary": summary,
                "completed_at": end_time
            }
        }
        self._append_event(event)
        
        # Save individual consolidated trace report
        if trace_id in self._active_traces:
            trace_obj = self._active_traces[trace_id]
            trace_obj["status"] = "COMPLETED"
            trace_obj["end_time"] = end_time
            trace_obj["overall_score"] = overall_score
            trace_obj["letter_grade"] = letter_grade
            trace_obj["summary"] = summary
            
            trace_path = os.path.join(self.traces_dir, f"{trace_id}.json")
            try:
                with open(trace_path, "w", encoding="utf-8") as f:
                    json.dump(trace_obj, f, indent=2)
            except Exception as e:
                print(f"Warning: Failed to write trace to {trace_path}: {e}")

    def get_grouped_trace_sessions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Returns list of submissions / trace sessions grouped with their events, sorted newest first."""
        if not os.path.exists(self.log_file):
            return []

        all_events = []
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            all_events.append(json.loads(line))
                        except Exception:
                            pass
        except Exception as e:
            print(f"Error reading {self.log_file}: {e}")
            return []

        # Group by trace_id maintaining order
        sessions_map: Dict[str, Dict[str, Any]] = {}
        for event in all_events:
            tid = event.get("trace_id")
            if not tid:
                continue

            if tid not in sessions_map:
                sessions_map[tid] = {
                    "trace_id": tid,
                    "student_name": "Unknown Student",
                    "folder_name": "--",
                    "start_time": event.get("timestamp"),
                    "end_time": None,
                    "model_name": "Google Gemini",
                    "overall_score": None,
                    "letter_grade": None,
                    "summary": "",
                    "status": "RUNNING",
                    "event_count": 0,
                    "events": []
                }

            session = sessions_map[tid]
            session["events"].append(event)
            session["event_count"] += 1

            # Extract metadata from event types
            etype = event.get("event_type")
            details = event.get("details", {})

            if etype == "TRACE_START":
                session["student_name"] = details.get("student_name", session["student_name"])
                session["folder_name"] = details.get("folder_name", session["folder_name"])
                session["class_name"] = details.get("class_name")
                session["assignment_name"] = details.get("assignment_name")
                session["start_time"] = event.get("timestamp", session["start_time"])

            elif etype == "MODEL_CALL":
                session["model_name"] = details.get("model", session["model_name"])

            elif etype == "MODEL_RESPONSE":
                if "model" in details:
                    session["model_name"] = details.get("model", session["model_name"])

            elif etype == "TRACE_END":
                session["status"] = "COMPLETED"
                session["end_time"] = event.get("timestamp")
                session["overall_score"] = details.get("overall_score")
                session["letter_grade"] = details.get("letter_grade")
                session["summary"] = details.get("summary", "")

        # Convert to list and sort by start_time descending (newest first)
        sessions_list = list(sessions_map.values())
        sessions_list.sort(key=lambda s: s.get("start_time") or "", reverse=True)
        return sessions_list[:limit]

    def get_trace_by_id(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Returns details and events for a specific trace_id."""
        sessions = self.get_grouped_trace_sessions(limit=500)
        for s in sessions:
            if s.get("trace_id") == trace_id:
                return s

        # Check isolated traces json file if present
        trace_file = os.path.join(self.traces_dir, f"{trace_id}.json")
        if os.path.exists(trace_file):
            try:
                with open(trace_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    def get_trace_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns recent traces from gemini_traces.jsonl."""
        if not os.path.exists(self.log_file):
            return []
        
        events = []
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        events.append(json.loads(line))
        except Exception as e:
            print(f"Error reading {self.log_file}: {e}")
        return events[-limit:]


# Global Telemetry instance
tracer = TelemetryTracer(output_dir="outputs")

