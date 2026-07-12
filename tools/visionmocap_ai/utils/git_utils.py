from pathlib import Path
from typing import Optional

from git import Repo, InvalidGitRepositoryError


def get_repo(project_root: Path) -> Optional[Repo]:
    try:
        return Repo(project_root)
    except InvalidGitRepositoryError:
        return None


def get_current_branch(repo: Repo) -> str:
    try:
        return repo.active_branch.name
    except (TypeError, ValueError):
        return "(detached HEAD)"


def get_git_status(repo: Repo) -> str:
    if repo.is_dirty():
        changed = [item.a_path for item in repo.index.diff(None)]
        staged = [item.a_path for item in repo.index.diff("HEAD")]
        parts = []
        if staged:
            parts.append(f"{len(staged)} staged")
        if changed:
            parts.append(f"{len(changed)} modified")
        if repo.untracked_files:
            parts.append(f"{len(repo.untracked_files)} untracked")
        return ", ".join(parts) if parts else "clean"
    return "clean"
