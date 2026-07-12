# AI Agent Operating Instructions

## Before making any change

1. Read this file.
2. Read `CONTEXT.md` to orient.
3. Read `architecture-rules.md` to understand constraints.
4. Read the relevant section of `module-registry.md` for any file you plan to touch.
5. Read `data-model.md` for any data structures you plan to use.
6. **Read the actual source file** you plan to modify — do not rely solely on summaries.

## Reading protocol

- **Always read the file you are about to edit** with the Read tool before editing.
- When searching for patterns (e.g., "how does recording work?"), use grep across the codebase.
- For cross-module impact analysis, trace imports using the dependency graph in `module-registry.md`.

## Writing protocol

- **Never redesign existing architecture** — the project uses Clean Architecture with strict dependency direction (core -> config -> camera/pose/motion/recording -> animation/blender -> gui).
- **Never rewrite existing modules** — extend, don't replace.
- **Never change public API signatures** — you may add new public methods but not remove or change existing ones.
- **Never add GUI code to backend modules** — GUI imports backend, not vice versa.
- **All new playback features go in `src/playback/`** — do not modify `src/motion/motion_player.py`.
- **Thread safety** — any code called from the worker thread (`_capture_loop`) must either be thread-safe or protected by `AppController._lock`.

## Code style

- Follow the project's existing style: Google-style docstrings, `from __future__ import annotations`, type hints on all public APIs.
- Use `Optional[X]` instead of `X | None` for consistency with existing code.
- Use dataclasses for data containers, ABCs for interfaces.
- Log via `logging.getLogger(self.__class__.__name__)`.
- Keep classes focused — one responsibility per class.
- Do NOT add comments unless they explain *why* something is done a certain way (not *what*).

## Testing protocol

- Tests go in `tests/unit/` (unit), `tests/integration/` (integration).
- Test file name: `test_<module_name>.py`
- Run with: `python -m pytest tests/`
- Coverage-sensitive test files (real recordings) handle edge cases gracefully (e.g., frames with pose_detected=False).

## What to do when stuck

- Search the codebase for similar patterns.
- Check `data-model.md` for data structure relationships.
- Check `architecture-rules.md` for constraints that might apply.
- If a problem crosses multiple subsystems, create a plan before coding.
