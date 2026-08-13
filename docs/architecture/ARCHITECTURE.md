# Architecture Overview

VisionMoCap is a desktop application for real-time 2D human pose
capture, motion recording, animation export, and Blender integration.
This document describes the runtime architecture, module boundaries,
and data flow.

## Module Map

```
app.py                     Entry point; config load, logging setup,
                           top-level error handling, exit codes.
src/config/                AppConfig + typed sub-configs (Camera,
                           Pose, Motion, Blender, Recording), JSON
                           persistence, validation.
src/core/                  Shared models (Vector3D, JointType),
                           exception hierarchy (VisionMoCapError).
src/camera/                CameraManager (discovery, open/close,
                           backend fallback, reconnect), FPS monitor.
src/pose/                  PoseDetector (MediaPipe Tasks Pose
                           Landmarker), PoseResult, base interface.
src/motion/                MotionProcessor (outlier removal,
                           interpolation, smoothing), MotionSequence,
                           MotionRecorder, filters library.
src/recording/             SessionManager + RecordingSession, JSON
                           session export with RecordingMetadata.
src/animation/             Avatar/Bone/Keyframe, retargeting,
                           BvhExporter / CsvExporter / NpyExporter.
src/blender/               BlenderExporter (temp BVH + add-on launch);
                           addon/ = Blender-side add-on package.
src/playback/              PlaybackPlayer (timer-based engine),
                           PlaybackController, PlaybackState.
src/gui/                   CustomTkinter UI: MainWindow, Toolbar,
                           AppController (orchestration + worker
                           threads), timeline & skeleton widgets.
tests/                     Unit suite (pytest, headless) +
                           integration smoke scripts (GUI).
```

## Data Flow

```
Camera (OpenCV)
   │  frames (BGR)
   ▼
CameraManager.get_frame()
   │  frame + FPS monitor
   ▼
PoseDetector.detect(frame)          [worker thread]
   │  PoseResult (33 landmarks)
   ▼
AppController capture loop
   ├─► SkeletonRenderer ──► GUI viewport (live preview)
   ├─► MotionProcessor ──► MotionSequence (filtering pipeline)
   └─► SessionManager.record_pose (when recording)
             │
             ▼
       JSON recording file (metadata + frames)
             │
             ▼
       PlaybackController ──► SkeletonRenderer (replay)
             │
             ▼
       Retargeter ──► AnimationClip (Avatar + Keyframes)
             │
             ├─► BvhExporter ──► .bvh ──► BlenderExporter ──► Blender
             ├─► CsvExporter ──► .csv
             └─► NpyExporter ──► .npy
```

## Threading Model

| Thread        | Owner              | Work                                            |
|---------------|--------------------|-------------------------------------------------|
| Main / GUI    | Tkinter mainloop   | Rendering, playback, recording UI, exports      |
| Camera worker | AppController      | `CameraManager.get_frame` → `PoseDetector` →    |
|               |                    | pose result queue (30 FPS poll in MainWindow)   |
| Pose queue    | `queue.Queue`      | Bounded hand-off between worker and GUI thread  |

`SessionManager` guards session state with a lock because
`record_pose()` is invoked from the camera worker thread while the GUI
thread reads session statistics.

## Failure Handling Contract

All failures that can reach the user surface as typed exceptions
derived from `VisionMoCapError` (see `src/core/exceptions.py`). The
GUI layer (`AppController`, `MainWindow`) catches these, logs the
stack, and shows a single actionable message box — never a raw
traceback or a silent `False`.

Camera disconnects during capture are handled automatically: after
repeated read failures the worker retries `CameraManager.reconnect()`
up to 3 times before surfacing an error.

## Key Design Decisions

- **MediaPipe Tasks API** (`RunningMode.IMAGE`) rather than the
  deprecated Solutions API; the model file is auto-downloaded to
  `models/`.
- **BVH export** uses ZXY Euler order with root translation, offsets
  derived from the first keyframe; compatible with Blender's BVH
  importer and the bundled `visionmocap_addon` bake operators.
- **Playback timing** is wall-clock based with accumulated time, so
  pausing/resuming and speed changes never drift from the sequence.
- **Backend fallback**: the camera manager tries the configured OpenCV
  backend first, then `CAP_ANY`, so one config works across Windows
  (DSHOW / MSMF) and other platforms.
