import os
from typing import Optional


def load_env(env_path: Optional[str] = None):
    """Loads environment variables from .env file without external dependencies."""
    search_paths = []
    if env_path:
        search_paths.append(env_path)
    else:
        # Check current working directory, script directory, and parent directories
        curr = os.getcwd()
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        search_paths.extend([
            os.path.join(curr, ".env"),
            os.path.join(base_dir, ".env"),
            os.path.join(base_dir, "..", ".env"),
            os.path.join(base_dir, "..", "..", ".env")
        ])

    for path in search_paths:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if line.startswith("export "):
                            line = line[7:].strip()
                        if "=" in line:
                            key, val = line.split("=", 1)
                            key = key.strip()
                            val = val.strip()
                            # Strip surrounding quotes
                            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                                val = val[1:-1]
                            os.environ[key] = val
                break
            except Exception as e:
                print(f"Warning: Could not read .env at {path}: {e}")


# Load on initial import
load_env()


def get_api_key() -> Optional[str]:
    """Returns the Gemini / Google API Key from environment or .env."""
    load_env()
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


def get_model_name() -> str:
    """Returns the model name from .env or environment, defaulting to gemini-2.5-flash."""
    load_env()
    model = (
        os.environ.get("GRADER_MODEL") or 
        os.environ.get("MODEL") or 
        os.environ.get("MODEL_NAME") or 
        os.environ.get("GEMINI_MODEL") or 
        "gemini-2.5-flash"
    )
    return model
