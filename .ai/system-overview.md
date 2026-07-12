# VisionMoCap — System Overview

## What it does

VisionMoCap is a **markerless motion capture application** that uses a webcam and MediaPipe Pose to track human pose in real-time, records motion sequences, processes (filters/interpolates) them, retargets to avatar skeletons, and exports to animation formats.

## Technology stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.14 |
| GUI | CustomTkinter (Tkinter wrapper) |
| Pose Detection | MediaPipe Tasks Pose Landmarker |
| Camera | OpenCV (cv2.VideoCapture) |
| Math | NumPy, SciPy (scipy not yet used) |
| Image | Pillow (PIL) |
| Serialization | JSON (standard library) |

## High-level architecture

The project follows **Clean Architecture** with layered packages and strict dependency direction:

```
src/core/           (domain models, interfaces, exceptions)
    ^
    |
src/config/         (configuration management)
    ^
    |
src/camera/   src/pose/  src/motion/  src/recording/   src/animation/   src/blender/
    ^              ^
    |              |
    +------+-------+
           |
    src/gui/         (orchestrator + CustomTkinter UI)
           |
    src/playback/    (independent — no deps on camera/mediapipe)
```

**Dependency rule:** A package may only depend on packages below or at the same level. `gui/` depends on everything else. `playback/` depends only on `motion/motion_sequence` (data model) and `pose/pose_result`.

## Subsystems

### Core (`src/core/`)
Zero external dependencies. Defines:
- **`JointType`** enum — 33 body landmarks
- **`Vector3D`** — immutable 3D vector with math operations
- **`Joint`**, **`Pose`**, **`MotionData`** — domain data structures
- **`BoneConnection`**, **`SKELETON_HIERARCHY`** — skeleton topology
- **5 ABCs**: `VideoSource`, `PoseEstimator`, `MotionProcessor`, `AnimationExporter`, `FrameRenderer`
- **9 exception classes** in a hierarchy under `VisionMoCapError`

### Config (`src/config/`)
JSON-backed configuration with typed dataclasses and fallback defaults.

### Camera (`src/camera/`)
OpenCV `VideoCapture` wrapper with device discovery, FPS monitoring, and backend selection (DirectShow, MediaFoundation, V4L2, AVFoundation). **Not thread-safe.**

### Pose (`src/pose/`)
MediaPipe Tasks Pose Landmarker wrapper. `PoseDetector` is the concrete implementation — notably does NOT inherit from `PoseEstimatorBase`. Produces `PoseResult` objects.

### Motion (`src/motion/`)
Recording, processing, and serialization of pose sequences:
- **`MotionRecorder`** — accumulates PoseResult objects into a `MotionSequence`
- **`MotionPlayer`** — replay of recorded sequences (limited; `src/playback/` is the future)
- **`MotionProcessor`** — pipeline of filters (outlier removal, interpolation, smoothing)
- **`MotionSequence`** — serializable container with JSON I/O

### Recording (`src/recording/`)
Session-based recording management:
- **`RecordingSession`** — state machine (idle → recording ↔ paused → completed)
- **`SessionManager`** — thread-safe facade, owns both `RecordingSession` and `MotionRecorder`
- **`RecordingMetadata`** — export metadata

### Animation (`src/animation/`)
Retargeting from MediaPipe landmarks to avatar skeletons:
- **`SkeletonMapper`** — maps landmarks to bone positions (presets for Mixamo, Blender, VRM, Ready Player Me)
- **`Retargeter`** — converts `MotionSequence` → `RetargetedMotion`
- **`AnimationEngine`** — converts `RetargetedMotion` → `AnimationClip`
- **`AnimationPlayer`** — playback of `AnimationClip`

### Blender (`src/blender/`)
Stub — `BlenderExporterBase` is a placeholder.

### GUI (`src/gui/`)
CustomTkinter application:
- **`AppController`** — central orchestrator, manages pipeline and threading
- **`MainWindow`** — top-level window, layout, 33ms update loop
- **`CameraWidget`**, **`StatusBar`**, **`Toolbar`**, **`InfoPanel`** — UI components

### Playback (`src/playback/`)
Independent replay system for recorded JSON files. No dependency on camera or MediaPipe.

### Utils (`src/utils/`)
Logging configuration (`LoggerSetup`).

## Threading model

The application has exactly **two threads**:

### Main Thread (GUI Thread)
- CustomTkinter event loop (`mainloop()`)
- Owns all UI widgets
- Calls `AppController` methods for camera/recording lifecycle
- Runs `_update_loop` every 33ms via `after()`:
  1. Drains frame queue (non-blocking)
  2. Updates camera widget display
  3. Checks for worker errors
  4. Updates status bar (throttled to 1Hz)
  5. Updates recording timer

### Worker Thread (Capture Thread)
- Created by `AppController.start_camera()` as a daemon thread
- Runs `_capture_loop()`:
  1. `camera_mgr.get_frame()` — blocking OpenCV read
  2. `frame_mgr.process()` — timestamp + resize
  3. `pose_detector.detect()` — MediaPipe inference
  4. `renderer.render()` — skeleton overlay
  5. `recorder.record()` — MotionRecorder (no lock)
  6. `session_mgr.record_pose()` — acquires thread lock
  7. Updates shared state under lock
  8. Pushes frame to queue (maxsize=2)

### Synchronization primitives
| Primitive | Purpose |
|-----------|---------|
| `threading.Event` (`_stop_event`) | Signal worker to stop |
| `threading.Lock` (`_lock`) | Protect shared pose/FPS/camera state |
| `queue.Queue(maxsize=2)` | Frame delivery: worker → GUI |
| `queue.Queue` (unbounded) | Error delivery: worker → GUI |

## Data flow (live pipeline)

```
Camera → CameraManager → FrameManager → PoseDetector → PoseResult
                                                        ↓
                                           ┌────────────┼────────────┐
                                           ↓            ↓            ↓
                                    SkeletonRenderer  MotionRecorder  SessionManager
                                           ↓                           ↓
                                      Annotated frame              RecordingSession
                                           ↓
                                      Frame Queue (maxsize=2)
                                           ↓
                                      CameraWidget → GUI display
```

## Data flow (playback pipeline)

```
Recording JSON file (exported from session)
    ↓
PlaybackController.load(path)
    ↓
MotionSequence (in-memory)
    ↓
PlaybackPlayer.advance() / step_forward() / step_backward()
    ↓
PoseResult (per frame)
    ↓
[to be connected to GUI or processing pipeline]
```

## Key design patterns

| Pattern | Usage |
|---------|-------|
| Clean Architecture | Layer dependency direction |
| Strategy (ABCs) | `VideoSource`, `PoseEstimator`, `MotionProcessor`, etc. |
| Chain of Responsibility | `MotionProcessor` pipeline of filters |
| State Machine | `RecordingSession` (4 states), `PlaybackPlayer` (4 states) |
| Facade | `SessionManager` wraps `RecordingSession` + `MotionRecorder` |
| Controller | `AppController` orchestrates pipeline |
| Worker Thread | Producer-consumer with frame queue |
| Factory Method | `RecordingMetadata.build()`, `Avatar.from_parent_pairs()` |
| Value Object | `Vector3D` (frozen, with math ops) |
