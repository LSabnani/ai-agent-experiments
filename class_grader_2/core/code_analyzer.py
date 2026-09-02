import os
import ast
import re
from typing import Dict, List, Any, Optional


class CodebaseSnapshot:
    """Scans and performs deep AST & semantic analysis on codebase scripts to extract evidence of AI Agents, Services, Skills, and RAG."""

    def __init__(self, folder_path: str):
        self.folder_path = folder_path
        self.files: Dict[str, str] = {}  # rel_path -> content
        self.python_ast: Dict[str, ast.AST] = {}
        self.syntax_errors: Dict[str, str] = {}
        self.functions_found: List[str] = []
        self.classes_found: List[str] = []
        self.imports_found: List[str] = []
        
        # Deep Evidence Trackers
        self.genuine_ai_calls: List[Dict[str, Any]] = []
        self.pseudo_agent_classes: List[Dict[str, Any]] = []
        self.skills_evidence: List[Dict[str, Any]] = []
        self.rag_evidence: List[Dict[str, Any]] = []
        
        # Popular AI Services Audit
        self.ai_services_audit: Dict[str, Dict[str, Any]] = {
            "Google Gemini": {"imported": False, "used": False, "import_sites": [], "call_sites": []},
            "OpenAI / OpenAI Agents": {"imported": False, "used": False, "import_sites": [], "call_sites": []},
            "Anthropic Claude": {"imported": False, "used": False, "import_sites": [], "call_sites": []},
            "Agent Orchestration Frameworks": {"imported": False, "used": False, "import_sites": [], "call_sites": []}
        }
        
        self._scan()
        self._analyze_deep_evidence()

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
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    self.functions_found.append(f"{rel_path}:{node.name}")
                elif isinstance(node, ast.ClassDef):
                    self.classes_found.append(f"{rel_path}:{node.name}")
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

    def _analyze_deep_evidence(self):
        """Analyzes code and scripts for genuine AI model/service calls vs plain classes."""
        
        # 1. Look for SKILL.md definitions across all directories (including skills/ folders)
        for rel_path, content in self.files.items():
            fname = os.path.basename(rel_path)
            if fname.lower() == "skill.md" or "skills/" in rel_path.lower():
                skill_name_match = re.search(r"^name:\s*([^\n]+)", content, re.MULTILINE | re.IGNORECASE)
                skill_name = skill_name_match.group(1).strip() if skill_name_match else os.path.dirname(rel_path)
                desc_match = re.search(r"^description:\s*([^\n]+)", content, re.MULTILINE | re.IGNORECASE)
                desc = desc_match.group(1).strip() if desc_match else "Skill definition file"
                
                self.skills_evidence.append({
                    "type": "SKILL_FILE",
                    "file": rel_path,
                    "skill_name": skill_name,
                    "description": desc,
                    "evidence": f"Found Skill definition in {rel_path} ('{skill_name}')"
                })

        # 2. Analyze Python AST and Script text
        for rel_path, content in self.files.items():
            if not rel_path.endswith((".py", ".js", ".ts", ".sh")):
                continue

            lines = content.splitlines()

            # --- A. Service-Specific Detection: Google Gemini ---
            gemini_import_pats = [
                r"import\s+google\.genai", r"from\s+google\s+import\s+genai",
                r"import\s+google\.generativeai", r"from\s+google\.generativeai",
                r"from\s+google\.genai\s+import", r"from\s+google\.adk"
            ]
            gemini_call_pats = [
                r"generate_content|generate_content_async",
                r"genai\.Client\(|client\.models\.generate_content",
                r"genai\.configure\(|GenerativeModel\(",
                r"Gemini\.", r"google\.adk\.agents"
            ]

            for idx, line in enumerate(lines, 1):
                for p in gemini_import_pats:
                    if re.search(p, line, re.IGNORECASE):
                        self.ai_services_audit["Google Gemini"]["imported"] = True
                        self.ai_services_audit["Google Gemini"]["import_sites"].append(f"{rel_path}:L{idx} (`{line.strip()[:90]}`)")
                for p in gemini_call_pats:
                    if re.search(p, line, re.IGNORECASE):
                        self.ai_services_audit["Google Gemini"]["used"] = True
                        self.ai_services_audit["Google Gemini"]["call_sites"].append(f"{rel_path}:L{idx} (`{line.strip()[:90]}`)")
                        self.genuine_ai_calls.append({
                            "service": "Google Gemini",
                            "file": rel_path,
                            "line": idx,
                            "code_snippet": line.strip()[:120],
                            "description": "Google Gemini Model Generation / Agent Call"
                        })

            # --- B. Service-Specific Detection: OpenAI / OpenAI Agents ---
            openai_import_pats = [
                r"import\s+openai", r"from\s+openai\s+import",
                r"from\s+crewai\s+import", r"from\s+autogen\s+import"
            ]
            openai_call_pats = [
                r"OpenAI\(|AsyncOpenAI\(",
                r"chat\.completions\.create",
                r"beta\.assistants|beta\.threads",
                r"openai\.ChatCompletion"
            ]

            for idx, line in enumerate(lines, 1):
                for p in openai_import_pats:
                    if re.search(p, line, re.IGNORECASE):
                        self.ai_services_audit["OpenAI / OpenAI Agents"]["imported"] = True
                        self.ai_services_audit["OpenAI / OpenAI Agents"]["import_sites"].append(f"{rel_path}:L{idx} (`{line.strip()[:90]}`)")
                for p in openai_call_pats:
                    if re.search(p, line, re.IGNORECASE):
                        self.ai_services_audit["OpenAI / OpenAI Agents"]["used"] = True
                        self.ai_services_audit["OpenAI / OpenAI Agents"]["call_sites"].append(f"{rel_path}:L{idx} (`{line.strip()[:90]}`)")
                        self.genuine_ai_calls.append({
                            "service": "OpenAI",
                            "file": rel_path,
                            "line": idx,
                            "code_snippet": line.strip()[:120],
                            "description": "OpenAI Model / Agent Execution Call"
                        })

            # --- C. Service-Specific Detection: Anthropic ---
            anthropic_import_pats = [r"import\s+anthropic", r"from\s+anthropic\s+import"]
            anthropic_call_pats = [r"Anthropic\(|AsyncAnthropic\(", r"messages\.create"]

            for idx, line in enumerate(lines, 1):
                for p in anthropic_import_pats:
                    if re.search(p, line, re.IGNORECASE):
                        self.ai_services_audit["Anthropic Claude"]["imported"] = True
                        self.ai_services_audit["Anthropic Claude"]["import_sites"].append(f"{rel_path}:L{idx} (`{line.strip()[:90]}`)")
                for p in anthropic_call_pats:
                    if re.search(p, line, re.IGNORECASE):
                        self.ai_services_audit["Anthropic Claude"]["used"] = True
                        self.ai_services_audit["Anthropic Claude"]["call_sites"].append(f"{rel_path}:L{idx} (`{line.strip()[:90]}`)")
                        self.genuine_ai_calls.append({
                            "service": "Anthropic Claude",
                            "file": rel_path,
                            "line": idx,
                            "code_snippet": line.strip()[:120],
                            "description": "Anthropic Claude Model Call"
                        })

            # --- D. Track Pseudo Classes Named 'Agent' (without AI models) ---
            for idx, line in enumerate(lines, 1):
                if re.search(r"class\s+\w*(?:Agent|Planner|Assistant|Worker|Critic|Scheduler)", line):
                    self.pseudo_agent_classes.append({
                        "file": rel_path,
                        "line": idx,
                        "code_snippet": line.strip()[:120]
                    })

            # --- E. Check Skills / Tools / Function Calling ---
            skill_tool_patterns = [
                (r"@tool|def\s+\w+_tool\(|tools\s*=\s*\[", "Tool / Skill Registration with Agent"),
                (r"FunctionDeclaration|Tool\(", "Agent Function/Tool Declaration"),
                (r"load_skill|invoke_skill|run_skill|read_skill", "Skill Loading / Invocation Function"),
                (r"def\s+(?:weather|calendar|image|fetch|search|query|calculate|scrape|database)_\w+", "Agent Specialization Tool Function")
            ]

            for pat, desc in skill_tool_patterns:
                for idx, line in enumerate(lines, 1):
                    if re.search(pat, line, re.IGNORECASE):
                        self.skills_evidence.append({
                            "type": "AGENT_SKILL_OR_TOOL",
                            "file": rel_path,
                            "line": idx,
                            "code_snippet": line.strip()[:120],
                            "description": desc
                        })

            # --- F. Check RAG (Retrieval-Augmented Generation) ---
            rag_patterns = [
                (r"chromadb|faiss|pinecone|qdrant|weaviate", "Vector Database Engine"),
                (r"embed_content|text-embedding|OpenAIEmbeddings|SentenceTransformer", "Embedding Generation Model"),
                (r"similarity_search|query_vector|find_nearest|cosine_similarity", "Vector Similarity Search / Retrieval"),
                (r"retriever|vectorstore|chunk_size|Document\(", "Document Chunking & Vector Store Retriever"),
                (r"f[\"'].*?(?:context|retrieved).*?\{.*?\}", "Context Injection into Prompt (RAG Pipeline)")
            ]

            for pat, desc in rag_patterns:
                for idx, line in enumerate(lines, 1):
                    if re.search(pat, line, re.IGNORECASE):
                        self.rag_evidence.append({
                            "type": "RAG_PIPELINE",
                            "file": rel_path,
                            "line": idx,
                            "code_snippet": line.strip()[:120],
                            "description": desc
                        })

    @property
    def has_genuine_ai_agent(self) -> bool:
        """Returns True only if genuine AI/LLM model calls or generative AI SDKs are actively used."""
        return len(self.genuine_ai_calls) > 0 or any(info["used"] for info in self.ai_services_audit.values())

    @property
    def agent_evidence(self) -> List[Dict[str, Any]]:
        """Backwards-compatible alias returning genuine AI calls."""
        return self.genuine_ai_calls

    def get_deep_analysis_report(self) -> str:
        """Generates a structured evidence report summarizing AST & script analysis and popular AI service audits."""
        lines = [
            f"=== CODEBASE AST & SEMANTIC EVIDENCE REPORT ({os.path.basename(self.folder_path)}) ===",
            f"Total Files Scanned: {len(self.files)}",
            f"Syntax Errors: {len(self.syntax_errors)}",
            ""
        ]

        # 1. Popular AI Services Audit Section
        lines.append("🌐 POPULAR AI SERVICES AUDIT (Google Gemini, OpenAI, Claude, Agent Frameworks):")
        for service, info in self.ai_services_audit.items():
            imp_status = "IMPORTED" if info["imported"] else "NOT IMPORTED"
            use_status = "ACTIVELY CALLED/USED" if info["used"] else "NOT CALLED/USED"
            lines.append(f"  • {service}: [{imp_status} | {use_status}]")
            if info["import_sites"]:
                lines.append(f"    - Import sites: {', '.join(info['import_sites'][:3])}")
            if info["call_sites"]:
                lines.append(f"    - Call/Usage sites: {', '.join(info['call_sites'][:3])}")
        lines.append("")

        # 2. Genuine AI Model / LLM Calls
        lines.append(f"🤖 GENUINE AI MODEL & LLM CALLS FOUND ({len(self.genuine_ai_calls)} occurrences):")
        if self.genuine_ai_calls:
            for item in self.genuine_ai_calls[:10]:
                lines.append(f"  - [{item['file']}:L{item['line']}] {item['description']}: `{item['code_snippet']}`")
        else:
            lines.append("  - ⚠️ ZERO AI / LLM Model Calls (Google Gemini, OpenAI, Claude, etc.) detected in codebase.")
            if self.pseudo_agent_classes:
                lines.append(f"  - ℹ️ Found {len(self.pseudo_agent_classes)} regular Python classes with 'Agent' in name (e.g. {self.pseudo_agent_classes[0]['file']}:L{self.pseudo_agent_classes[0]['line']} `{self.pseudo_agent_classes[0]['code_snippet']}`), but these are PLAIN PROCEDURAL PYTHON without any AI/LLM model calls.")
        lines.append("")

        # 3. Skills Evidence
        lines.append(f"🛠️ AGENT SKILLS & TOOLS EVIDENCE FOUND ({len(self.skills_evidence)} occurrences):")
        if self.skills_evidence:
            for item in self.skills_evidence[:10]:
                if item.get("type") == "SKILL_FILE":
                    lines.append(f"  - [Skill File: {item['file']}] '{item['skill_name']}': {item['description']}")
                else:
                    lines.append(f"  - [{item['file']}:L{item.get('line', 1)}] {item['description']}: `{item.get('code_snippet', '')}`")
        else:
            lines.append("  - ⚠️ ZERO Skills (SKILL.md, @tool, or tool registrations) detected in codebase.")
        lines.append("")

        # 4. RAG Evidence
        lines.append(f"📚 RAG (RETRIEVAL-AUGMENTED GENERATION) EVIDENCE FOUND ({len(self.rag_evidence)} occurrences):")
        if self.rag_evidence:
            for item in self.rag_evidence[:10]:
                lines.append(f"  - [{item['file']}:L{item['line']}] {item['description']}: `{item['code_snippet']}`")
        else:
            lines.append("  - ⚠️ ZERO Vector DBs, embeddings, or retrieval pipelines detected in codebase.")
        lines.append("")

        return "\n".join(lines)

    def get_summary_text(self, max_length: int = 25000) -> str:
        """Constructs a consolidated text representation of the codebase including the deep analysis report."""
        evidence_report = self.get_deep_analysis_report()
        
        file_sections = [f"=== Project Files in {os.path.basename(self.folder_path)} ==="]
        for rel_path, content in sorted(self.files.items()):
            if rel_path.lower().startswith("spec"):
                continue
            file_sections.append(f"\n--- FILE: {rel_path} ---")
            if len(content) > 4000:
                file_sections.append(content[:4000] + f"\n... [Truncated {len(content) - 4000} chars] ...")
            else:
                file_sections.append(content)
        
        full_text = evidence_report + "\n\n" + "\n".join(file_sections)
        if len(full_text) > max_length:
            return full_text[:max_length] + "\n... [Codebase truncated for evaluation] ..."
        return full_text
