import os
import re
from typing import List, Dict, Any, Optional
from core.models import Criterion


class SpecParser:
    def __init__(self, folder_path: str):
        self.folder_path = folder_path
        self.spec_file_path = self._find_spec_file()

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

    def read_spec_content(self) -> str:
        if not self.spec_file_path:
            raise FileNotFoundError(
                f"No SPECIFICATIONS.md found in folder '{self.folder_path}'. "
                f"Please ensure a SPECIFICATIONS.md file is present."
            )
        with open(self.spec_file_path, "r", encoding="utf-8") as f:
            return f.read()

    def parse_criteria(self) -> List[Criterion]:
        content = self.read_spec_content()
        criteria: List[Criterion] = []
        
        # Split content into sections by markdown headers (## ...)
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
            
            # 1. Look for bullets inside this section
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

            # 2. ALSO parse standalone requirement paragraphs in this section (e.g. "Store user input in CSV...")
            # Remove bullet lines from body to extract standalone paragraphs
            non_bullet_text = bullet_pattern.sub("", "\n".join(body_lines)).strip()
            paragraphs = [p.strip() for p in non_bullet_text.split("\n\n") if p.strip()]

            for p in paragraphs:
                p_single_line = " ".join(p.split())
                # Check if paragraph contains actionable requirement phrasing
                actionable_keywords = ["store", "log", "save", "use ", "create", "implement", "build", "must", "should", "require", "frontend", "backend", "csv", "json", "api"]
                if len(p_single_line) >= 20 and any(w in p_single_line.lower() for w in actionable_keywords):
                    # Check if this paragraph isn't already covered by a bullet
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

        # Default fallback if empty spec
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
        weight = 1.0
        weight_match = re.search(r"\[(\d+(?:\.\d+)?)\s*(?:pts?|points?|%)?\]|\((\d+(?:\.\d+)?)\s*(?:pts?|points?|%)?\)", text, re.IGNORECASE)
        if weight_match:
            try:
                weight = float(weight_match.group(1) or weight_match.group(2))
            except ValueError:
                weight = 1.0
        return weight

    def _clean_title(self, text: str) -> str:
        clean = text.split(":")[0] if ":" in text and len(text.split(":")[0]) < 60 else text[:60]
        # Remove asterisks and backticks while preserving underscores
        clean = re.sub(r"[\*`#]", "", clean).strip()
        # If title is a full sentence, shorten to first sentence or 60 chars
        if "." in clean and len(clean.split(".")[0]) > 10:
            clean = clean.split(".")[0].strip()
        return clean
