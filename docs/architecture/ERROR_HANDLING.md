# Error Handling & Resilience

This document defines how VisionMoCap reports and recovers from
failures, and the contract every subsystem must follow.

## Exception Hierarchy

All project exceptions derive from `VisionMoCapError`
(`src/core/exceptions.py`):

```
VisionMoCapError
├── ConfigurationError        invalid / unreadable config files
├── ResourceNotFoundError     missing model, executable, or file
├── CameraError               open/read/backend failures, disconnects
├── PoseEstimationError       model download, init, or inference errors
├── MotionProcessingError     filtering / interpolation failures
├── RecordingError            session save failures (JSON write)
├── PlaybackError             load / replay failures
├── AnimationExportError      BVH / CSV / NPY write failures
├── RetargetingError          avatar retarget failures
├── BlenderIntegrationError   add-on / launch failures
└── GUIError                  UI-layer failures
```

Every raised exception carries the underlying cause via the `cause`
keyword argument (kept as the `__cause__` attribute) so logs retain
the full original traceback.

## Rules for New Code

1. **Never leak raw exceptions to the GUI.** Wrap filesystem and
   third-party I/O at the subsystem boundary and re-raise a typed
   exception with `cause=`.
2. **Never return silent `False`** for user-visible failures. Set a
   human-readable reason (e.g. `BlenderExporter.last_error`) and log it.
3. **Message boxes are the last resort**, used only by
   `MainWindow._show_error`; all logic layers log instead of popping UI.
4. **Transient failures retry**: camera read failures retry via
   `reconnect()`; the model download is a one-shot with a typed error.

## Failure Paths and Their Handling

| Failure                       | Detection                      | User-visible behavior                          |
|-------------------------------|--------------------------------|------------------------------------------------|
| Missing pose model            | `_resolve_model_path`          | Download attempt, typed error if it fails     |
| Camera not responding         | `open_camera` raises           | Message box "Camera Error"                     |
| Camera disconnect mid-capture | 5 consecutive read failures    | Auto-reconnect (3 tries), then error dialog   |
| Recording save fails          | `save_recording` raises        | Log + ERROR status, returns None               |
| BVH/CSV/NPY write fails       | exporter raises                | Log + ERROR status with path and reason       |
| Blender executable missing    | `_launch_blender`              | `last_error` + "Install Blender or set the    |
|                               | (FileNotFoundError)            | correct path in Settings."                     |
| Fatal startup error           | `app.py` `_show_fatal_error`   | Message box, exit code 1 (config: exit 1,     |
|                               |                                | Ctrl+C: 130)                                   |

## Application-Level Exit Codes

| Code | Meaning                              |
|------|--------------------------------------|
| 0    | Clean shutdown                       |
| 1    | Configuration load failure / fatal   |
| 130  | Interrupted (Ctrl+C / SIGINT)        |

## Resilience Features

- **Reconnect**: `CameraManager.reconnect()` re-opens the most recent
  camera; `AppController._try_reconnect` retries with backoff
  (0.5 s / 1.0 s / 1.5 s).
- **Temp-file hygiene**: `BlenderExporter` cleans `visionmocap_*.bvh`
  files older than 24 h and removes the last temp BVH on
  `cleanup_temp_bvh()`.
- **Idempotent shutdown**: `SessionManager.shutdown` / player `stop`
  are safe to call repeatedly and from any state.
