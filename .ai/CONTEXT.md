# VisionMoCap AI Workspace

This directory (`.ai/`) is the **source of truth** for AI-assisted development on the VisionMoCap project.

## How to use this workspace

1. **Start here** — read this file first to understand the workspace layout.
2. **Read `ai-instructions.md`** — contains your operating protocol: how to read, how to write, what to never do.
3. **Read `system-overview.md`** — high-level architecture, subsystem boundaries, data flow, threading model.
4. **Consult `module-registry.md`** — detailed inventory of every module, class, and public function.
5. **Refer to `data-model.md`** — all shared data structures, enums, JSON schemas, and their relationships.
6. **Check `architecture-rules.md`** — invariants, constraints, and conventions that must never be violated.
7. **Use `file-map.md`** — quick navigation: directory tree with one-line file descriptions.

## Workspace contents

| File | Purpose |
|------|---------|
| `CONTEXT.md` | This file — workspace entry point |
| `ai-instructions.md` | Operating protocol for AI agents |
| `system-overview.md` | High-level architecture and data flow |
| `module-registry.md` | Every module, class, function documented |
| `data-model.md` | All dataclasses, enums, types, JSON schemas |
| `architecture-rules.md` | Invariants, constraints, conventions |
| `file-map.md` | Directory tree with file descriptions |

## Golden rules

- **Do NOT modify existing modules unless explicitly instructed.**
- **Do NOT change public APIs** (method signatures, public class interfaces).
- **Do NOT break the recording pipeline** — it is the most critical feature.
- **Preserve thread safety** — the worker thread / GUI thread split must be maintained.
- **Do NOT add GUI logic to non-GUI modules** — keep separation of concerns.
- **All new playback features must live in `src/playback/`** — the existing `src/motion/motion_player.py` handles recording-adjacent playback and must not be modified.
