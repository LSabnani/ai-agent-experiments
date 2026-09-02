import os
import re
import subprocess
import shutil
from typing import Tuple, Optional


class GitFetcher:
    """Clones or updates a GitHub repository and resolves specific subfolder paths."""

    DEFAULT_CACHE_DIR = os.path.join("outputs", "git_repos")

    @staticmethod
    def is_git_url(path_or_url: str) -> bool:
        """Returns True if the string looks like a GitHub/Git repository URL and is not an existing local folder."""
        if not path_or_url:
            return False
        clean = path_or_url.strip().strip("'").strip('"')
        
        # If it exists on the local filesystem as a folder or file, treat as local path
        try:
            expanded = os.path.abspath(os.path.expanduser(clean))
            if os.path.exists(expanded):
                return False
        except Exception:
            pass

        return (
            clean.startswith("http://") 
            or clean.startswith("https://") 
            or clean.startswith("git@") 
            or clean.startswith("github.com/")
            or clean.endswith(".git")
        )

    @classmethod
    def parse_github_url(cls, url: str) -> Tuple[str, Optional[str], Optional[str]]:
        """
        Parses a GitHub URL into (clone_url, branch, subfolder).
        Supports formats:
          - https://github.com/owner/repo
          - https://github.com/owner/repo.git
          - https://github.com/owner/repo/tree/main/subfolder/path
          - https://github.com/owner/repo/tree/master/assignments/hw1
        """
        clean_url = url.strip()

        # Match github.com/owner/repo/tree/<branch>/<subfolder...>
        tree_match = re.match(
            r"^https?://github\.com/([^/]+)/([^/]+)/tree/([^/]+)(?:/(.+))?$",
            clean_url,
            re.IGNORECASE
        )
        if tree_match:
            owner, repo, branch, subfolder = tree_match.groups()
            repo = re.sub(r"\.git$", "", repo)
            clone_url = f"https://github.com/{owner}/{repo}.git"
            return clone_url, branch, (subfolder.strip("/") if subfolder else None)

        # Standard github.com/owner/repo or github.com/owner/repo.git
        std_match = re.match(
            r"^https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?(?:/)?$",
            clean_url,
            re.IGNORECASE
        )
        if std_match:
            owner, repo = std_match.groups()
            clone_url = f"https://github.com/{owner}/{repo}.git"
            return clone_url, None, None

        # Generic git clone URL
        return clean_url, None, None

    @classmethod
    def resolve_and_fetch(
        cls, 
        path_or_url: str, 
        explicit_subfolder: Optional[str] = None,
        cache_dir: Optional[str] = None
    ) -> str:
        """
        Fetches the repository if path_or_url is a Git URL and returns the local directory path.
        If path_or_url is already a local path, returns it directly.
        """
        path_or_url = path_or_url.strip()

        # If it's a local folder, return it
        if not cls.is_git_url(path_or_url):
            if explicit_subfolder:
                combined = os.path.join(path_or_url, explicit_subfolder)
                if os.path.exists(combined):
                    return combined
            return path_or_url

        clone_url, branch, url_subfolder = cls.parse_github_url(path_or_url)
        target_subfolder = explicit_subfolder or url_subfolder

        base_cache = cache_dir or cls.DEFAULT_CACHE_DIR
        os.makedirs(base_cache, exist_ok=True)

        # Create sanitized repo directory name (e.g. owner_repo)
        repo_name_match = re.search(r"[:/]([^/:]+)/([^/:]+?)(?:\.git)?$", clone_url)
        if repo_name_match:
            owner, repo = repo_name_match.groups()
            local_repo_name = f"{owner}_{repo}"
        else:
            local_repo_name = re.sub(r"[^\w\-_]", "_", clone_url)

        local_repo_dir = os.path.abspath(os.path.join(base_cache, local_repo_name))

        # Clone or Pull
        if not os.path.exists(local_repo_dir):
            cmd = ["git", "clone", "--depth", "1"]
            if branch:
                cmd.extend(["--branch", branch])
            cmd.extend([clone_url, local_repo_dir])
            
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode != 0:
                raise RuntimeError(
                    f"Failed to clone repository from '{clone_url}'. "
                    f"Git error: {res.stderr.strip() or res.stdout.strip()}"
                )
        else:
            # Update existing clone
            try:
                subprocess.run(
                    ["git", "pull", "--ff-only"],
                    cwd=local_repo_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=30
                )
            except Exception:
                pass  # Use existing cloned state if offline or up-to-date

        # Resolve subfolder
        if target_subfolder:
            resolved_path = os.path.join(local_repo_dir, target_subfolder)
            if not os.path.exists(resolved_path):
                # Search case-insensitively for subfolder
                found = None
                for root, dirs, _ in os.walk(local_repo_dir):
                    for d in dirs:
                        if d.lower() == target_subfolder.lower():
                            found = os.path.join(root, d)
                            break
                    if found:
                        break
                if found and os.path.exists(found):
                    return found
                
                raise FileNotFoundError(
                    f"Subfolder '{target_subfolder}' was not found in cloned repository at '{local_repo_dir}'."
                )
            return resolved_path

        return local_repo_dir
