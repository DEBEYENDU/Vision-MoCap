from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ..utils.config import config
from ..utils.git_utils import get_git_info


def status_command(
    console: Console,
    project_root: Optional[Path] = None,
) -> None:
    root = project_root or config.project_root
    git_info = get_git_info(root)

def status_command(
    console: Console,
    project_root: Optional[Path] = None,
) -> None:
    root = project_root or config.project_root
    git_info = get_git_info(root)

    version = _read_version(root)
    features_done, features_total = _count_roadmap_items(root / "ROADMAP.md")
    bugs = _count_bugs(root / "KNOWN_BUGS.md")
    test_files = len(list((root / "tests").rglob("test_*.py")))
    next_task = _find_next_task(root / "ROADMAP.md")

    table = Table(title="VisionMoCap Status")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Current Version", version)
    table.add_row("Completed Features", f"{features_done} / {features_total}")
    table.add_row("Current Feature", _find_current_feature(root / "ROADMAP.md"))
    table.add_row("Known Bugs", str(_count_bugs(root / "KNOWN_BUGS.md")))
    table.add_row("Test Files", str(len(list((root / "tests").rglob("test_*.py")))))
    table.add_row("Next Task", next_task)
    table.add_row("Git Branch", git_info["branch"])
    table.add_row("Git Status", git_info["status"])
    table.add_row("Git Hash", git_info["hash"])

    console.print(table)

    console.print(table)


def _read_version(project_root: Path) -> str:
    changelog = project_root / "CHANGELOG.md"
    try:
        content = changelog.read_text(encoding="utf-8")
        for line in content.splitlines():
            if line.startswith("## [") and "Unreleased" not in line:
                return line.strip("## []").strip()
    except (FileNotFoundError, Exception):
        pass
    return "0.0.0"


def _count_roadmap_items(path: Path):
    done = 0
    total = 0
    try:
        content = path.read_text(encoding="utf-8")
        for line in content.splitlines():
            if "- [x]" in line:
                done += 1
                total += 1
            elif "- [ ]" in line:
                total += 1
    except (FileNotFoundError, Exception):
        pass
    return done, total


def _count_bugs(path: Path) -> int:
    try:
        content = path.read_text(encoding="utf-8")
        return content.count("- [ ]") + content.count("- [x]")
    except (FileNotFoundError, Exception):
        return 0


def _find_next_task(roadmap_path: Path) -> str:
    try:
        content = roadmap_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            if line.strip().startswith("- [ ]"):
                return line.strip("- [ ]").strip()
    except (FileNotFoundError, Exception):
        pass
    return "No pending tasks"


def _find_current_feature(roadmap_path: Path) -> str:
    try:
        content = roadmap_path.read_text(encoding="utf-8")
        current_section = None
        for line in content.splitlines():
            if line.startswith("## "):
                current_section = line.strip("# ").strip()
            if line.strip().startswith("- [ ]") and current_section:
                return current_section
    except (FileNotFoundError, Exception):
        pass
    return "N/A"
