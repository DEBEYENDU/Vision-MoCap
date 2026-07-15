# Chapter 2: System Architecture

## 2.1 Design Philosophy

VisionMoCap follows the **Clean Architecture** pattern [4], which
separates the codebase into concentric layers with strict dependency
rules:

- **Core layer** (`src/core/`) — Domain entities, abstract interfaces,
  and exceptions.  No dependencies on frameworks or external libraries.
- **Application layer** (`src/config/`, `src/camera/`, `src/pose/`,
  `src/motion/`, `src/recording/`, `src/playback/`, `src/animation/`,
  `src/blender/`) — Use-case implementations that depend on core
  abstractions.
- **Infrastructure layer** (`src/gui/`, `src/utils/`) — GUI framework
  (CustomTkinter) and utilities.  Depends on application services.

```
┌──────────────────────────────────────┐
│          GUI (CustomTkinter)         │  Infrastructure
├──────────────────────────────────────┤
│  Camera │ Pose │ Motion │ Playback   │  Application
│  Recording │ Animation │ Blender     │
├──────────────────────────────────────┤
│       Core Interfaces & Models       │  Core
└──────────────────────────────────────┘
```

## 2.2 Threading Model

A two-thread model ensures the UI remains responsive during capture:

- **Worker thread** — Runs the continuous capture→detect→render
  pipeline.  Reads from the camera, runs pose inference, and pushes
  results to a thread-safe queue.
- **GUI thread** — Displays frames, handles user input, and runs the
  playback loop.  Never blocks on camera I/O.

Communication uses two `queue.Queue` instances:
- `_frame_queue` — Delivers annotated frames to the GUI.
- `_error_queue` — Delivers error information for user-facing dialogs.

## 2.3 Configuration Management

Configuration is managed through `ConfigManager`, which loads and saves
a JSON file (`config.json`).  The configuration is organized into
dataclass-backed sections:

- `CameraConfig` — Device ID, resolution, FPS, backend
- `PoseConfig` — Model complexity, confidence thresholds, delegate
- `MotionConfig` — Filter parameters, frame subsample rate
- `AnimationConfig` — Export format, scale factor
- `BlenderConfig` — Executable path, auto-launch
- `GuiConfig` — Theme selection
- `LoggingConfig` — Log level, directory, rotation

## 2.4 Component Dependencies

```
MainWindow
  └─ Toolbar ────────────┐
  └─ CameraWidget ───────┤
  └─ TimelineWidget ─────┤
  └─ StatusBar ──────────┤
  └─ SettingsDialog ─────┤
  └─ InfoPanel ──────────┤
                         ▼
                    AppController
  ┌───────────────────────┬──────────────────┐
  ▼                       ▼                  ▼
CameraManager       PoseDetector        FrameManager
  │                       │
  ▼                       ▼
_WorkerThread ─────> _capture_loop()
  │                       │
  ▼                       ▼
_recorder ─────────> MotionRecorder
_playback_ctrl ────> PlaybackController
```

---

**References**

[4] Martin, R. C. Clean Architecture: A Craftsman's Guide to Software
    Structure and Design. Prentice Hall, 2017.
