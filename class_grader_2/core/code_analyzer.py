import os
import ast
import re
from typing import Dict, List, Any, Optional


class CodebaseSnapshot:
    def __init__(self, folder_path: str):
        self.folder_path = folder_path
        self.files: Dict[str, str] = {}  # rel_path -> content
        self.python_ast: Dict[str, ast.AST] = {}
        self.syntax_errors: Dict[str, str] = {}
        self.functions_found: List[str] = []
        self.classes_found: List[str] = []
        self.imports_found: List[str] = []
        self._scan()

    def _scan(self):
        ignore_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv", ".pytest_cache", ".gemini", ".idea"}
        allowed_extensions = {".py", ".js", ".ts", ".html", ".css", ".json", ".md", ".sh", ".sql", ".yaml", ".yml", ".txt"}
        
        for root, dirs, filenames in os.walk(self.folder_path):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for fname in filenames:
                ext = os.path.splitext(fname)[1].lower()
                if ext in allowed_extensions:
                    full_path = os.path.join(root, fname)
                    rel_path = os.path.relpath(full_path, self.folder_path)
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                            content = f.read()
                            self.files[rel_path] = content
                            
                            if ext == ".py":
                                self._analyze_python(rel_path, content)
                    except Exception as e:
                        print(f"Error reading file {full_path}: {e}")

    def _analyze_python(self, rel_path: str, content: str):
        try:
            tree = ast.parse(content, filename=rel_path)
            self.python_ast[rel_path] = tree
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    self.functions_found.append(node.name)
                elif isinstance(node, ast.ClassDef):
                    self.classes_found.append(node.name)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        self.imports_found.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        self.imports_found.append(node.module)
        except SyntaxError as e:
            self.syntax_errors[rel_path] = f"Syntax error at line {e.lineno}: {e.msg}"
        except Exception as e:
            self.syntax_errors[rel_path] = str(e)

    def get_summary_text(self, max_length: int = 15000) -> str:
        """Constructs a consolidated text representation of the codebase for analysis."""
        lines = [f"=== Project Files in {os.path.basename(self.folder_path)} ==="]
        for rel_path, content in sorted(self.files.items()):
            # Don't duplicate specifications in code snapshot
            if rel_path.lower().startswith("spec"):
                continue
            lines.append(f"\n--- FILE: {rel_path} ---")
            # Truncate very long files if needed
            if len(content) > 3000:
                lines.append(content[:3000] + f"\n... [Truncated {len(content) - 3000} chars] ...")
            else:
                lines.append(content)
        
        full_text = "\n".join(lines)
        if len(full_text) > max_length:
            return full_text[:max_length] + "\n... [Codebase truncated for evaluation] ..."
        return full_text
