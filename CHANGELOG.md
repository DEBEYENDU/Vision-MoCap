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
