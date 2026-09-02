import os
import re
import yaml
from typing import Dict, List, Any, Optional

DEFAULT_SUBMISSIONS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SUBMISSIONS.yaml")


class SubmissionsConfig:
    """Loads and parses class assignments and mandatory criteria from SUBMISSIONS.yaml with live reload."""

    def __init__(self, file_path: Optional[str] = None):
        self.file_path = file_path or self._find_submissions_file()
        self._last_mtime: float = 0.0
        self._cached_config: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        self._reload_if_needed()

    def _find_submissions_file(self) -> str:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidates = [
            os.path.join(base_dir, "SUBMISSIONS.yaml"),
            os.path.join(base_dir, "submissions.yaml"),
            os.path.join(base_dir, "SUBMISSIONS.yml"),
            os.path.join(base_dir, "submissions.yml"),
            os.path.join(base_dir, "SUBMISSIONS.md"),
            os.path.join(os.getcwd(), "SUBMISSIONS.yaml"),
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c
        return DEFAULT_SUBMISSIONS_FILE

    def _reload_if_needed(self):
        """Reloads configuration if the file timestamp has changed."""
        if not self.file_path or not os.path.isfile(self.file_path):
            self._cached_config = {}
            return

        try:
            mtime = os.path.getmtime(self.file_path)
            if mtime != self._last_mtime:
                self._cached_config = self._load_config()
                self._last_mtime = mtime
        except Exception as e:
            print(f"Warning: Failed to check SUBMISSIONS.yaml timestamp ({e})")

    def _load_config(self) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """Parses YAML file into a structured dictionary."""
        if not self.file_path or not os.path.isfile(self.file_path):
            return {}

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                raw_text = f.read()

            # Clean markdown codeblocks or headers if SUBMISSIONS.md was used
            clean_lines = []
            for line in raw_text.splitlines():
                if line.strip().startswith("```"):
                    continue
                if line.strip().startswith("#"):
                    # Comment line
                    continue
                clean_lines.append(line)
            clean_text = "\n".join(clean_lines)

            parsed = yaml.safe_load(clean_text)
            if not isinstance(parsed, dict):
                return {}

            structured_result: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}

            for class_name, assignments in parsed.items():
                if not isinstance(assignments, dict):
                    continue
                
                structured_result[class_name] = {}
                for assign_name, criteria_val in assignments.items():
                    structured_result[class_name][assign_name] = []
                    
                    # 1. Case: criteria_val is a list (e.g. list of strings or list of dicts)
                    if isinstance(criteria_val, list):
                        for item in criteria_val:
                            parsed_items = self._parse_criterion_items(item)
                            structured_result[class_name][assign_name].extend(parsed_items)

                    # 2. Case: criteria_val is a direct dict mapping criteria to percentages
                    elif isinstance(criteria_val, dict):
                        parsed_items = self._parse_criterion_items(criteria_val)
                        structured_result[class_name][assign_name].extend(parsed_items)

            return structured_result

        except Exception as e:
            print(f"Warning: Failed to parse SUBMISSIONS.yaml ({e})")
            return {}

    def _parse_criterion_items(self, item: Any) -> List[Dict[str, Any]]:
        """
        Parses item and extracts ALL criteria entries.
        Supports:
          - String: "Code Uses AI Agent: 30%"
          - Dict with 1 or MULTIPLE keys: {"Code Uses SKills in Agent": "25%", "Code Uses RAG in Agent": "25%"}
        """
        results: List[Dict[str, Any]] = []

        if isinstance(item, str):
            match = re.match(r"^([^:]+):\s*([0-9.]+)\s*%?$", item.strip())
            if match:
                title = match.group(1).strip()
                percent = float(match.group(2))
                results.append({
                    "criterion": title,
                    "weight_percent": percent,
                    "description": f"Mandatory requirement: {title} (-{percent:.0f}% if missing)"
                })
            else:
                results.append({
                    "criterion": item.strip(),
                    "weight_percent": 10.0,
                    "description": f"Mandatory requirement: {item.strip()}"
                })

        elif isinstance(item, dict):
            # Iterate through ALL entries in the dictionary
            for k, v in item.items():
                percent = 10.0
                if isinstance(v, (int, float)):
                    percent = float(v)
                elif isinstance(v, str):
                    pct_match = re.search(r"([0-9.]+)", v)
                    if pct_match:
                        percent = float(pct_match.group(1))
                results.append({
                    "criterion": str(k).strip(),
                    "weight_percent": percent,
                    "description": f"Mandatory requirement: {str(k).strip()} (-{percent:.0f}% if missing)"
                })

        return results

    def get_classes(self) -> List[str]:
        self._reload_if_needed()
        return list(self._cached_config.keys())

    def get_assignments(self, class_name: str) -> List[str]:
        self._reload_if_needed()
        # Direct match or case-insensitive fallback
        if class_name in self._cached_config:
            return list(self._cached_config[class_name].keys())
        for k, v in self._cached_config.items():
            if k.strip().lower() == class_name.strip().lower():
                return list(v.keys())
        return []

    def get_criteria(self, class_name: str, assignment_name: str) -> List[Dict[str, Any]]:
        self._reload_if_needed()
        
        # 1. Direct lookup
        if class_name in self._cached_config:
            if assignment_name in self._cached_config[class_name]:
                return self._cached_config[class_name][assignment_name]
        
        # 2. Case-insensitive lookup
        for c_k, assignments in self._cached_config.items():
            if c_k.strip().lower() == class_name.strip().lower():
                for a_k, crits in assignments.items():
                    if a_k.strip().lower() == assignment_name.strip().lower():
                        return crits

        return []

    def get_full_config(self) -> Dict[str, Any]:
        self._reload_if_needed()
        return self._cached_config


submissions_config = SubmissionsConfig()
