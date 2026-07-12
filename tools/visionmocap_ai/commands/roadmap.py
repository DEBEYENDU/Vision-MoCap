from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ..utils.config import config


def roadmap_command(
    console: Console,
    project_root: Optional[Path] = None,
) -> None:
    root = project_root or config.project_root
    roadmap_path = root / "ROADMAP.md"

    try:
        content = roadmap_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        console.print("[red]ROADMAP.md not found[/red]")
        raise typer.Exit(1)

    lines = content.splitlines()
    current_section = None
    sections = []

    for line in lines:
        if line.startswith("## "):
            current_section = line.strip("# ").strip()
            sections.append({"name": current_section, "items": []})
        elif line.strip().startswith("- [x]") and sections:
            sections[-1]["items"].append(("done", line.strip("- [x]").strip()))
        elif line.strip().startswith("- [ ]") and sections:
            sections[-1]["items"].append(("pending", line.strip("- [ ]").strip()))

    for section in sections:
        done = sum(1 for s, _ in section["items"] if s == "done")
        total = len(section["items"])
        label = f"{section['name']} ({done}/{total})"
        items_text = "\n".join(
            f"  {'[green]✓[/]' if s == 'done' else '[red]○[/]'} {t}"
            for s, t in section["items"]
        )
        console.print(Panel(items_text, title=label, border_style="blue"))
