import os
import re
from typing import List, Dict, Any, Optional
from core.models import Criterion


class SpecParser:
    def __init__(self, folder_path: str, scoring_file_path: Optional[str] = None):
        self.folder_path = folder_path
        self.spec_file_path = self._find_spec_file()
        self.scoring_file_path = scoring_file_path or self._find_scoring_file()

    def _find_spec_file(self) -> Optional[str]:
        candidates = [
            "SPECIFICATIONS.md",
            "specifications.md",
            "SPECIFICATION.md",
            "specification.md",
            "SPEC.md",
            "spec.md",
            "README.md"
        ]
        for candidate in candidates:
            path = os.path.join(self.folder_path, candidate)
            if os.path.isfile(path):
                return path
        return None

    def _find_scoring_file(self) -> Optional[str]:
        # 1. First priority: SCORING.md inside the target project folder
        folder_candidates = [
            os.path.join(self.folder_path, "SCORING.md"),
            os.path.join(self.folder_path, "scoring.md")
        ]
        for candidate in folder_candidates:
            if os.path.isfile(candidate):
                return candidate

        # 2. Workspace root SCORING.md (apply only if relevant to the project or if project has matching architecture)
        root_candidates = [
            os.path.join(os.getcwd(), "SCORING.md"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SCORING.md")
        ]
        for candidate in root_candidates:
            if os.path.isfile(candidate):
                # Check relevance to avoid applying multi-agent scoring to simple standalone scripts
                try:
                    with open(candidate, "r", encoding="utf-8") as f:
                        scoring_text = f.read().lower()
                    spec_text = self.read_spec_content().lower()
                    
                    # If root SCORING.md mentions specific concepts like ParallelAgent/LoopAgent, ensure spec or code relates
                    if "parallelagent" in scoring_text or "loopagent" in scoring_text or "critic_feedback" in scoring_text:
                        if any(k in spec_text for k in ["agent", "parallel", "loop", "critic", "pipeline", "itinerary", "scheduler"]):
                            return candidate
                    else:
                        return candidate
                except Exception:
                    pass
        return None

    def read_spec_content(self) -> str:
        if not self.spec_file_path:
            raise FileNotFoundError(
                f"No SPECIFICATIONS.md found in folder '{self.folder_path}'. "
                f"Please ensure a SPECIFICATIONS.md file is present."
            )
        with open(self.spec_file_path, "r", encoding="utf-8") as f:
            return f.read()

    def read_scoring_content(self) -> Optional[str]:
        if self.scoring_file_path and os.path.isfile(self.scoring_file_path):
            try:
                with open(self.scoring_file_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception:
                pass
        return None

    def parse_criteria(self) -> List[Criterion]:
        spec_content = self.read_spec_content()
        scoring_content = self.read_scoring_content()

        if scoring_content:
            return self._parse_criteria_with_scoring_distribution(spec_content, scoring_content)
        
        return self._parse_raw_spec_criteria(spec_content)

    def _parse_criteria_with_scoring_distribution(self, spec_content: str, scoring_content: str) -> List[Criterion]:
        """Aligns criteria strictly with the weights and dimensions in SCORING.md using whole point distributions."""
        criteria: List[Criterion] = []
        bullet_pattern = re.compile(r"^(\s*[-*+]|\s*\d+\.)\s+(.+)$", re.MULTILINE)

        # Extract subtasks from SPECIFICATIONS.md for the "Completeness" bucket
        subtask_criteria = self._parse_raw_spec_criteria(spec_content)
        
        # Filter out milestone headers from subtask list if already in spec
        filtered_subtasks = [
            c for c in subtask_criteria 
            if not any(k in c.title.lower() for k in ["structural integrity", "context extraction", "state management", "graceful failure", "quality evaluation", "student assignment milestones"])
        ]
        
        item_counter = 1

        # Parse SCORING.md lines
        for match in bullet_pattern.finditer(scoring_content):
            line = match.group(2).strip()
            title = self._clean_title(line)
            weight = self._extract_weight(line)
            lower_title = title.lower()

            if "structural integrity" in lower_title:
                cat_weight = round(weight) if weight > 0 else 10.0
                criteria.append(Criterion(
                    id=f"crit_{item_counter}",
                    title=f"Structural Integrity ({int(cat_weight)}%)",
                    description=f"[SCORING.md] {line}",
                    weight=cat_weight,
                    category="Architecture & Structure"
                ))
                item_counter += 1

            elif "context extraction" in lower_title or "state management" in lower_title:
                cat_weight = round(weight) if weight > 0 else 20.0
                criteria.append(Criterion(
                    id=f"crit_{item_counter}",
                    title=f"Context Extraction & State Management ({int(cat_weight)}%)",
                    description=f"[SCORING.md] {line}",
                    weight=cat_weight,
                    category="State & Context"
                ))
                item_counter += 1

            elif "graceful failure" in lower_title:
                cat_weight = round(weight) if weight > 0 else 10.0
                criteria.append(Criterion(
                    id=f"crit_{item_counter}",
                    title=f"Graceful Failure Handling ({int(cat_weight)}%)",
                    description=f"[SCORING.md] {line}",
                    weight=cat_weight,
                    category="Robustness & Edge Cases"
                ))
                item_counter += 1

            elif "completeness" in lower_title:
                total_completeness_pts = int(round(weight if weight > 0 else 50.0))
                num_subtasks = max(len(filtered_subtasks), 1)
                
                # Distribute using whole points
                base_weight = total_completeness_pts // num_subtasks
                remainder = total_completeness_pts % num_subtasks
                
                for idx, st in enumerate(filtered_subtasks):
                    assigned_weight = base_weight + (1 if idx < remainder else 0)
                    criteria.append(Criterion(
                        id=f"crit_{item_counter}",
                        title=f"{st.title} (Completeness)",
                        description=f"[Completeness ({total_completeness_pts}%)] {st.description}",
                        weight=float(max(1, assigned_weight)),
                        category="Completeness"
                    ))
                    item_counter += 1

            elif "code quality" in lower_title or "documentation" in lower_title:
                cat_weight = round(weight) if weight > 0 else 15.0
                criteria.append(Criterion(
                    id=f"crit_{item_counter}",
                    title=f"Code Quality and Documentation ({int(cat_weight)}%)",
                    description=f"[SCORING.md] {line}",
                    weight=cat_weight,
                    category="Code Quality"
                ))
                item_counter += 1

            elif "application quality" in lower_title:
                cat_weight = round(weight) if weight > 0 else 5.0
                criteria.append(Criterion(
                    id=f"crit_{item_counter}",
                    title=f"Application Quality ({int(cat_weight)}%)",
                    description=f"[SCORING.md] {line}",
                    weight=cat_weight,
                    category="Application Quality"
                ))
                item_counter += 1

        if not criteria:
            return subtask_criteria

        return criteria

    def _parse_raw_spec_criteria(self, content: str) -> List[Criterion]:
        criteria: List[Criterion] = []
        sections = re.split(r"\n(?=#{1,4}\s+)", content)
        bullet_pattern = re.compile(r"^(\s*[-*+]|\s*\d+\.)\s+(.+)$", re.MULTILINE)
        header_pattern = re.compile(r"^(#{1,4})\s+(.+)$")
        item_counter = 1

        for sec in sections:
            sec = sec.strip()
            if not sec:
                continue

            lines = sec.splitlines()
            header_line = lines[0].strip()
            header_match = header_pattern.match(header_line)
            section_title = header_match.group(2).strip() if header_match else "General Requirements"
            lower_header = section_title.lower()
            
            if any(w in lower_header for w in ["structure", "files", "setup", "install", "dependency"]):
                current_category = "Project Setup & Structure"
            elif any(w in lower_header for w in ["quality", "clean", "style", "doc", "comment"]):
                current_category = "Code Quality"
            elif any(w in lower_header for w in ["test", "verify", "validation"]):
                current_category = "Testing & Verification"
            elif any(w in lower_header for w in ["error", "edge", "exception", "constraint"]):
                current_category = "Robustness & Edge Cases"
            elif any(w in lower_header for w in ["log", "logging", "csv", "storage", "database", "data"]):
                current_category = "Data Logging & Persistence"
            else:
                current_category = "Functionality"

            body_lines = lines[1:] if header_match else lines
            bullet_matches = list(bullet_pattern.finditer("\n".join(body_lines)))
            
            if bullet_matches:
                for bm in bullet_matches:
                    req_text = bm.group(2).strip()
                    if len(req_text) < 5 or req_text.lower().startswith("table of contents"):
                        continue
                    
                    weight = self._extract_weight(req_text)
                    clean_title = self._clean_title(req_text)
                    
                    criteria.append(Criterion(
                        id=f"crit_{item_counter}",
                        title=clean_title if clean_title else f"Requirement #{item_counter}",
                        description=f"[{section_title}] {req_text}",
                        weight=weight,
                        category=current_category
                    ))
                    item_counter += 1

            non_bullet_text = bullet_pattern.sub("", "\n".join(body_lines)).strip()
            paragraphs = [p.strip() for p in non_bullet_text.split("\n\n") if p.strip()]

            for p in paragraphs:
                p_single_line = " ".join(p.split())
                actionable_keywords = ["store", "log", "save", "use ", "create", "implement", "build", "must", "should", "require", "frontend", "backend", "csv", "json", "api"]
                if len(p_single_line) >= 20 and any(w in p_single_line.lower() for w in actionable_keywords):
                    if not any(p_single_line[:40].lower() in c.description.lower() for c in criteria):
                        weight = self._extract_weight(p_single_line)
                        clean_title = self._clean_title(p_single_line)
                        
                        criteria.append(Criterion(
                            id=f"crit_{item_counter}",
                            title=clean_title,
                            description=f"[{section_title}] {p_single_line}",
                            weight=weight,
                            category=current_category
                        ))
                        item_counter += 1

        if not criteria:
            criteria.append(Criterion(
                id="crit_1",
                title="Specification Compliance",
                description="The application fulfills the instructions described in SPECIFICATIONS.md",
                weight=1.0,
                category="Functionality"
            ))

        return criteria

    def _extract_weight(self, text: str) -> float:
        weight_match = re.search(r"\((\d+(?:\.\d+)?)\s*(?:%|pts?|points?)?\)|\[(\d+(?:\.\d+)?)\s*(?:%|pts?|points?)?\]", text, re.IGNORECASE)
        if weight_match:
            try:
                return float(weight_match.group(1) or weight_match.group(2))
            except ValueError:
                pass
        return 1.0

    def _clean_title(self, text: str) -> str:
        clean = text.split(":")[0] if ":" in text and len(text.split(":")[0]) < 60 else text[:60]
        clean = re.sub(r"[\*`#]", "", clean).strip()
        if "." in clean and len(clean.split(".")[0]) > 10:
            clean = clean.split(".")[0].strip()
        return clean
