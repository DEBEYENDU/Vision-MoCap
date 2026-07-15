# Changelog

All notable changes to VisionMoCap are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/)
and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Added
- Repository folder structure for docs, assets, screenshots, demo, etc.
- README files for each top-level directory explaining purpose and conventions.
- ROADMAP.md, CONTRIBUTING.md with project guidelines.
- Changelog following SemVer.

### Added — Settings Panel
- `SettingsDialog` with three tabs: Camera, Pose Detection, and General.
- Camera tab: device selection dropdown, resolution presets, backend selection, target FPS slider.
- Pose tab: model complexity (Lite/Full/Heavy), detection/tracking confidence sliders.
- General tab: GUI theme toggle, logging level selection.
- Settings are persisted to `config.json` via the existing `ConfigManager`.
- `src/gui/settings_dialog.py` — new module following existing UI patterns (modal dialog with Apply/Cancel).
- Exported `SettingsDialog` from `src/gui/__init__.py`.

### Added — Playback System
- Full motion playback engine (`PlaybackController`, `PlaybackPlayer`) with play, pause, resume, stop.
- Frame-step forward/backward and timeline scrubbing.
- Timeline widget integrated into the GUI.
- 46 playback unit tests covering all state transitions and edge cases.

### Added — Animation System
- `AnimationClip`, `Keyframe`, `Bone`, `Avatar` data structures.
- `AnimationExporter` abstract base class for future export pipelines.

### Added — Motion Filters
- `MovingAverageFilter` for smoothing landmarks over a sliding window.
- `ExponentialSmoothingFilter` for lightweight real-time smoothing.
- `OutlierRemovalFilter` for detecting and replacing anomalous frames.

### Added — Retargeting System
- `SkeletonMapper` for mapping between different skeleton definitions.
- `Retargeter` class with 4 built-in retargeting presets.

### Added — Blender Integration Stubs
- `BlenderIntegration` abstract base class for future Blender add-on.

### Added — VISIONMOCAP_BIBLE.md
- Comprehensive engineering reference document covering architecture, coding standards, threading rules, testing philosophy, and long-term roadmap.

### Fixed — Missing AppController properties
- Added `playback_progress` and `current_time_seconds` property passthroughs to `AppController` so the GUI timeline updates work without crashing.

### Added — Theme Switching
- `GuiConfig` dataclass with `theme` field added to configuration system.
- Theme toggle button in the toolbar (dark ↔ light) with visual feedback.
- Theme persisted to `config.json` across sessions.
- `AppController.set_theme()` and `Toolbar.set_theme()` for integration.

---

## [1.0.0] — 2026-07-09

### Added
- Real-time markerless pose detection via MediaPipe Pose.
- Webcam support with configurable camera index.
- 33-landmark skeleton rendering overlay on camera feed.
- Motion recording with pause, resume, discard, and save.
- Recording session manager with JSON export.
- Per-frame tracking of landmarks, world landmarks, confidence, and FPS.
- VisionMoCap Studio GUI built with CustomTkinter.
- Recording timer, red-dot indicator, and frame counter in GUI.
- Clean Architecture project structure:
  - `src/core/` — Domain entities and interfaces.
  - `src/camera/` — Camera adapter abstraction.
  - `src/pose/` — Pose estimation abstraction.
  - `src/motion/` — Motion processing and recording.
  - `src/animation/` — Animation export abstractions.
  - `src/blender/` — Blender integration stubs.
  - `src/gui/` — Desktop GUI application.
  - `src/config/` — Configuration management.
  - `src/utils/` — Logging and utilities.
- Configuration via `config.json`.
- Comprehensive logging across all subsystems.
- Pytest test suite with unit and integration tests.

[Unreleased]: https://github.com/your-org/VisionMoCap/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/your-org/VisionMoCap/releases/tag/v1.0.0
