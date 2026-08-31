import os
import sys
import subprocess
from typing import Dict, Any, List, Optional


class DynamicRunner:
    def __init__(self, folder_path: str, timeout_seconds: int = 10):
        self.folder_path = os.path.abspath(folder_path)
        self.timeout = timeout_seconds

    def run_tests_if_present(self) -> Dict[str, Any]:
        """Detects and runs test suites if test files exist."""
        results = {
            "has_tests": False,
            "tests_passed": False,
            "output": "",
            "details": []
        }

        # Check for pytest or unittest files
        test_files = []
        for root, _, files in os.walk(self.folder_path):
            for f in files:
                if (f.startswith("test_") or f.endswith("_test.py")) and f.endswith(".py"):
                    test_files.append(os.path.relpath(os.path.join(root, f), self.folder_path))

        if not test_files:
            return results

        results["has_tests"] = True
        try:
            # Run unittest discovery inside target folder with folder in PYTHONPATH
            env = dict(os.environ)
            existing_pythonpath = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = f"{self.folder_path}:{existing_pythonpath}" if existing_pythonpath else self.folder_path

            cmd = [sys.executable, "-m", "unittest", "discover", "-s", ".", "-p", "*test*.py"]
            proc = subprocess.run(
                cmd,
                cwd=self.folder_path,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=self.timeout
            )
            results["output"] = proc.stdout
            results["tests_passed"] = (proc.returncode == 0)
        except subprocess.TimeoutExpired:
            results["output"] = "Test execution timed out after 10s."
            results["tests_passed"] = False
        except Exception as e:
            results["output"] = f"Test execution error: {e}"
            results["tests_passed"] = False

        return results

    def run_entrypoint_check(self, entrypoint_file: str = "main.py") -> Dict[str, Any]:
        """Checks if main script executes or provides help without crashing."""
        ep_path = os.path.join(self.folder_path, entrypoint_file)
        if not os.path.isfile(ep_path):
            return {"present": False, "ran": False, "output": ""}

        try:
            env = dict(os.environ)
            env["PYTHONPATH"] = f"{self.folder_path}:{env.get('PYTHONPATH', '')}"
            cmd = [sys.executable, entrypoint_file, "--help"]
            proc = subprocess.run(
                cmd,
                cwd=self.folder_path,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=self.timeout
            )
            return {
                "present": True,
                "ran": True,
                "exit_code": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr
            }
        except subprocess.TimeoutExpired:
            return {"present": True, "ran": False, "error": "Execution timed out"}
        except Exception as e:
            return {"present": True, "ran": False, "error": str(e)}
