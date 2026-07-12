from pathlib import Path
from typing import List, Optional
from datetime import datetime


def read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return f"*File not found: {path}*"
    except Exception as e:
        return f"*Error reading {path}: {e}*"


def build_feature_prompt(feature_name: str, ai_dir: Path, src_dir: Path) -> str:
    context = read_file(ai_dir / "CONTEXT.md")
    system_overview = read_file(ai_dir / "system-overview.md")
    module_registry = read_file(ai_dir / "module-registry.md")
    data_model = read_file(ai_dir / "data-model.md")
    architecture_rules = read_file(ai_dir / "architecture-rules.md")
    file_map = read_file(ai_dir / "file-map.md")

    prompt = f"""# AI Feature Implementation Prompt

## Feature
{feature_name}

## Context
{context}

## System Overview
{system_overview}

## Module Registry
{module_registry}

## Data Model
{data_model}

## Architecture Rules
{architecture_rules}

## File Map
{file_map}

## Instructions

Implement the feature "{feature_name}" following these rules:

1. Read all context files above before making changes.
2. Follow Clean Architecture dependency rules.
3. Do NOT modify existing public APIs.
4. All new playback features go in src/playback/.
5. Thread safety must be preserved.
6. Add tests in tests/unit/ or tests/integration/.
7. Use Google-style docstrings and type hints.
8. Do NOT add comments explaining what code does.
"""
    return prompt


def build_bug_prompt(bug_description: str, ai_dir: Path) -> str:
    context = read_file(ai_dir / "CONTEXT.md")
    arch_rules = read_file(ai_dir / "architecture-rules.md")
    module_registry = read_file(ai_dir / "module-registry.md")

    return f"""# AI Bug Fix Prompt

## Bug Description
{bug_description}

## Context
{context}

## Architecture Rules
{arch_rules}

## Module Registry
{module_registry}

## Instructions

Fix the bug described above following these rules:
1. Read the relevant source files before making changes.
2. Do NOT change public API signatures.
3. Do NOT break the recording pipeline.
4. Preserve thread safety.
5. Add tests for the fix.
6. Follow the project's coding conventions.
"""



