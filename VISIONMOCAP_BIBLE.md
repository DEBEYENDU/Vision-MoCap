# VisionMoCap Studio — Engineering Bible

> **Master engineering reference for VisionMoCap Studio.**
> Every contributor — human or AI — should read this document before writing code.

---

## Table of Contents

1. [Project Philosophy](#1-project-philosophy)
2. [Long-Term Vision](#2-long-term-vision)
3. [Development Principles](#3-development-principles)
4. [Design Philosophy](#4-design-philosophy)
5. [Coding Standards](#5-coding-standards)
6. [Error Handling Standards](#6-error-handling-standards)
7. [Logging Standards](#7-logging-standards)
8. [Threading Rules](#8-threading-rules)
9. [Performance Goals](#9-performance-goals)
10. [UI Design Philosophy](#10-ui-design-philosophy)
11. [AI Development Rules](#11-ai-development-rules)
12. [Definition of Done](#12-definition-of-done)
13. [Testing Philosophy](#13-testing-philosophy)
14. [Documentation Standards](#14-documentation-standards)
15. [Future Architecture Direction](#15-future-architecture-direction)
16. [Long-Term Roadmap](#16-long-term-roadmap)

---

## 1. Project Philosophy

VisionMoCap Studio exists to make **markerless motion capture accessible** to everyone with a webcam. The project prioritises:

- **Accuracy** — Faithful reproduction of human motion from video
- **Performance** — Real-time processing at 30+ FPS on consumer hardware
- **Extensibility** — Clean architecture that welcomes new features
- **Reliability** — Production-quality code that doesn't crash or lose data
- **Transparency** — Every step from camera to export is observable and debuggable

---

## 2. Long-Term Vision

VisionMoCap Studio aims to become a complete end-to-end motion capture pipeline:

```
Camera → Pose Detection → Motion Processing → Animation → Export → Blender
```

Each stage is independently replaceable and testable. Future milestones include BVH export, Blender add-on integration, multi-camera support, and retargeting to arbitrary rigs.

---

## 3. Development Principles

### 3.1 No Breaking Changes

Never introduce changes that break existing functionality. The recording, playback, camera, and GUI systems must remain stable.

### 3.2 Incremental Development

Each feature is implemented as a self-contained milestone. Milestones are never skipped. If a milestone depends on another, that dependency must be completed first.

### 3.3 Single Responsibility

Every class has exactly one reason to change. If a class does two things, split it.

### 3.4 Test Before Merge

All code must be tested before integration. The test suite must pass at 100% before any commit is considered complete.

### 3.5 Read Before Write

Before modifying any file, read its full content. Understand the context, imports, and dependencies. Never assume.

---

## 4. Design Philosophy

### 4.1 Clean Architecture

The application follows Robert C. Martin's Clean Architecture:

- **Domain Layer** (`src/core/`) — Enterprise business rules. No external dependencies.
- **Application Layer** (`src/motion/`, `src/playback/`, `src/recording/`) — Use cases. Depends only on domain.
- **Interface Adapters** (`src/camera/`, `src/pose/`, `src/gui/`, `src/blender/`) — Converts data between domain and external systems.
- **Infrastructure** (`src/config/`, `src/utils/`) — Configuration and logging.

### 4.2 Dependency Rule

Dependencies point **inward**. Nothing in `src/core/` depends on anything outside it. Outer layers depend on inner layers, never the reverse.

### 4.3 Interface Segregation

Abstract interfaces (`VideoSource`, `PoseEstimator`, `MotionProcessor`, `AnimationExporter`, `FrameRenderer`) define contracts between layers. Concrete implementations satisfy these contracts.

### 4.4 Composition Over Inheritance

Prefer composition over inheritance. Use dataclasses for data containers and classes with injected dependencies for behaviour.

### 4.5 Package Structure

Each package in `src/` has:
- `__init__.py` that re-exports all public symbols
- `base.py` or `__init__.py` for abstract base classes
- Clear naming that reflects responsibility

---

## 5. Coding Standards

### 5.1 Python Version

Target Python 3.12+. Use `from __future__ import annotations` in all files.

### 5.2 Style Guide

- **PEP 8** for all code
- **PEP 484** type hints required on all functions and methods
- **PEP 257** docstrings on all public classes, methods, and functions
- Line length: 100 characters maximum
- Indentation: 4 spaces (no tabs)

### 5.3 Naming Conventions

| Construct | Convention | Example |
|-----------|------------|---------|
| Classes | PascalCase | `PlaybackController`, `SkeletonRenderer` |
| Methods/functions | snake_case | `get_current_pose()`, `load_recording()` |
| Private attributes | snake_case with leading underscore | `_current_frame`, `_state` |
| Constants | UPPER_SNAKE_CASE | `_DEFAULT_BG`, `_COLOR_LEFT` |
| Modules | snake_case | `playback_controller.py`, `skeleton_renderer.py` |
| Type variables | PascalCase | `T`, `Optional[T]` |

### 5.4 Imports

Group in this order, separated by blank lines:

1. `from __future__ import annotations`
2. Standard library imports
3. Third-party library imports
4. Internal project imports

Internal imports use absolute paths from the `src/` package root:

```python
from src.motion.motion_sequence import MotionSequence
from src.playback.playback_controller import PlaybackController
```

### 5.5 Dataclasses

Use `@dataclass` for data containers. Use frozen dataclasses for immutable value objects:

```python
@dataclass(frozen=True)
class Vector3D:
    x: float
    y: float
    z: float
```

### 5.6 Properties

Use `@property` for computed attributes that have no side effects:

```python
@property
def is_playing(self) -> bool:
    return self._state == PlaybackState.PLAYING
```

---

## 6. Error Handling Standards

### 6.1 Exception Hierarchy

All application exceptions inherit from `VisionMoCapError`:

```
VisionMoCapError
├── ConfigurationError
├── CameraError
├── PoseEstimationError
├── MotionProcessingError
├── AnimationExportError
├── RetargetingError
├── BlenderIntegrationError
└── GUIError
```

### 6.2 Exception Usage

- Raise specific exceptions (never bare `Exception`)
- Include informative error messages
- Chain original exceptions with `cause` parameter
- Catch specific exceptions at the appropriate layer
- Let exceptions propagate to the GUI layer where they are shown to the user

### 6.3 Worker Thread Errors

Errors in the worker thread are pushed to `_error_queue` as `(title, message)` tuples. The GUI thread checks and displays them as modal dialogs.

---

## 7. Logging Standards

### 7.1 Logger Initialisation

Each class creates its own logger:

```python
self._logger = logging.getLogger(self.__class__.__name__)
```

### 7.2 Log Levels

| Level | When to Use |
|-------|-------------|
| `DEBUG` | Detailed diagnostic information (frame-by-frame, per-iteration) |
| `INFO` | Major lifecycle events (startup, shutdown, recording, loading) |
| `WARNING` | Recoverable issues (missing model file, low confidence) |
| `ERROR` | Failures that prevent an operation from completing |

### 7.3 Configuration

Logging is configured via `LoggingConfig` in `config.json`:
- Level: INFO by default
- Directory: `logs/`
- Max file size: 10 MB
- Backup count: 5 (rotating file handler)

---

## 8. Threading Rules

### 8.1 Thread Model

The application uses exactly **two threads**:

| Thread | Purpose | Loop |
|--------|---------|------|
| **Main (GUI) Thread** | CustomTkinter event loop, widget updates, playback | `mainloop()` + `after(33ms)` |
| **Worker Thread** | Camera capture → pose detection → rendering → enqueue | `_capture_loop()` (daemon) |

### 8.2 Synchronisation Primitives

| Mechanism | Purpose |
|-----------|---------|
| `threading.Event` (`_stop_event`) | Signal the worker thread to shut down |
| `threading.Lock` (`_lock`) | Protect shared state (pose, FPS, camera info) |
| `queue.Queue(maxsize=2)` | Deliver annotated frames from worker to GUI (drop-oldest on overflow) |
| `queue.Queue` (unbounded) | Deliver error tuples from worker to GUI |

### 8.3 Rules

- **Never block the GUI thread.** All I/O and heavy computation happens in the worker thread.
- **Playback runs in the GUI thread.** The `PlaybackPlayer` uses wall-clock timing via `time.perf_counter()`, advanced once per GUI cycle (33ms). No separate thread needed.
- **Worker never touches GUI widgets.** The worker pushes frames to a queue; the GUI drains it.
- **Worker writes shared state under lock.** The GUI reads shared state under the same lock.
- **No busy loops.** Use `time.sleep()` or `wait()` in the worker when idle.
- **Joining the worker thread** has a 5-second timeout to prevent deadlock on shutdown.

---

## 9. Performance Goals

| Metric | Target |
|--------|--------|
| Camera capture FPS | 30 FPS (configurable) |
| Pose detection latency | < 33 ms per frame |
| Frame queue latency | < 2 frames behind live |
| Playback seek | O(1) — no iteration |
| GUI update interval | 33 ms (~30 FPS) |
| Recoding file size | ~1 KB per frame (JSON) |
| Memory (idle) | < 200 MB |
| Memory (recording) | < 500 MB |

---

## 10. UI Design Philosophy

### 10.1 Layout

- **Camera preview** occupies the left, expanding area (grid column 0, weight=1)
- **Info panel** is fixed-width on the right (280 px)
- **Toolbar** is at the bottom with button groups separated by vertical bars
- **Timeline** sits between the toolbar and status bar
- **Status bar** is at the very bottom

### 10.2 Colour Scheme

- Dark theme by default (CustomTkinter "dark-blue")
- Recording: red dot + red timer
- Paused recording: orange dot + orange label
- Playback: green for PLAYING, orange for PAUSED, blue for FINISHED
- Errors: red flash in status bar
- Warnings: yellow flash in status bar

### 10.3 State-Driven UI

Buttons are enabled/disabled based on application state. The Toolbar exposes state-helper methods (e.g., `set_camera_started()`, `set_playback_playing()`) rather than individual button configuration.

### 10.4 Update Loop

The GUI uses a polling model via `_update_loop()` scheduled with `after(33ms)`:
1. Drain frame queue (non-blocking, keep latest only)
2. Check for worker errors
3. Update playback frame (if active)
4. Update InfoPanel (frame, pose, recording, playback)
5. Update status bar (throttled to 1 Hz)
6. Reschedule

---

## 11. AI Development Rules

### 11.1 Before Writing Code

1. **Read the repository structure** — Understand the folder layout
2. **Read existing code** — Understand naming conventions, patterns, and style
3. **Identify every file that needs modification** — Document the list
4. **Explain the rationale** — For each change, explain why it's necessary
5. **Plan the architecture** — Before implementing, describe the design

### 11.2 During Implementation

1. **Implement one milestone at a time** — Don't skip ahead
2. **Don't modify what you don't understand** — Read fully before editing
3. **Maintain existing conventions** — Match the style of surrounding code
4. **Don't break the build** — Tests must pass after every change
5. **Don't add features that aren't requested** — Stay within scope

### 11.3 After Implementation

1. **Run all tests** — Verify 100% pass rate
2. **Check imports** — Verify the import chain works
3. **Verify by running** — Execute the application or integration tests
4. **Update this document** — If architecture changed, update the Bible
5. **Report** — Summarise what was done, what files changed, and why

---

## 12. Definition of Done

A feature is "done" when:

1. All required functionality is implemented
2. All edge cases are handled (empty, invalid, boundary inputs)
3. The existing test suite passes at 100%
4. New tests exist for the feature (if applicable)
5. No regressions in existing functionality
6. Code compiles without warnings
7. Logging is appropriate (INFO for lifecycle, DEBUG for details)
8. Error handling is in place
9. Documentation is updated (this file, README, CHANGELOG)
10. All modified files are listed and explained

---

## 13. Testing Philosophy

### 13.1 Test Framework

Pytest is the test framework.

### 13.2 Test Location

Tests reside in `tests/unit/` organised by module:
```
tests/unit/test_playback.py
```

### 13.3 What to Test

- **State machines** — Every valid and invalid state transition
- **Edge cases** — Empty sequences, boundary values, error conditions
- **File I/O** — Load/save round-trips, invalid formats, missing files
- **Timing** — Correct behaviour under various timing scenarios

### 13.4 What Not to Test

- **GUI widgets** — CustomTkinter components are not unit-testable without a display server
- **External dependencies** — MediaPipe, OpenCV are assumed to work correctly
- **Private implementation details** — Test public API behaviour, not internal state

### 13.5 Test Pattern

Use fixtures and factory functions for test data:

```python
def make_sequence(n_frames=10, fps=30.0):
    poses = [_make_pose(i / fps) for i in range(n_frames)]
    return MotionSequence(pose_results=poses, ...)
```

---

## 14. Documentation Standards

### 14.1 Docstrings

Google-style docstrings with:
- **Brief description** on the first line
- **Args** section with types and descriptions
- **Returns** section with type and description
- **Raises** section (when applicable)

### 14.2 Markdown Files

- Use GitHub-flavoured Markdown
- Use tables for structured data
- Use code blocks with language identifiers
- Cross-reference between documents
- Mark implemented features with ✅ and planned features with ⚪

### 14.3 Comments

- Prefer self-documenting code over comments
- Use comments only to explain *why*, not *what*
- Avoid commented-out code

---

## 15. Future Architecture Direction

### 15.1 Event System

Replace the polling-based GUI update with an event-driven architecture:
- Worker emits events (frame ready, pose updated, error occurred)
- GUI subscribes to relevant events
- Reduces polling overhead and improves responsiveness

### 15.2 Plugin System

Allow external pose estimators, renderers, and exporters to be loaded as plugins:
- Define a plugin interface
- Auto-discover plugins from a directory
- Register them in the GUI

### 15.3 Multi-Camera Support

Support multiple simultaneous camera inputs:
- Each camera gets its own worker thread
- Frame synchronisation across cameras
- Combined pose estimation from multiple viewpoints

### 15.4 Recording Database

Replace file-based recording storage with a lightweight database:
- SQLite for metadata and search
- Optimised binary format for landmark data
- Recording catalogue with thumbnails

---

## 16. Long-Term Roadmap

### Phase 1 — Foundation (Current)
- Camera capture and pose detection
- Recording and JSON export
- Motion playback with timeline
- Desktop GUI

### Phase 2 — Motion Quality
- Motion smoothing and filtering
- Outlier removal
- Frame interpolation

### Phase 3 — Export Pipeline
- BVH file export
- FBX format support
- Configurable frame rate export

### Phase 4 — Blender Integration
- Blender add-on for importing VisionMoCap data
- Rig mapping (Mixamo, Rigify)
- One-click animation bake

### Phase 5 — Advanced Features
- Multi-camera support
- Retargeting to arbitrary skeletons
- Real-time streaming to external applications
- Performance profiling and optimisation
