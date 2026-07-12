# File Map

Complete directory tree with one-line file descriptions. Use this for quick navigation.

```
VisionMoCap/
├── app.py                          # Entry point: init logging, load config, run GUI
├── config.json                     # Default application configuration
├── requirements.txt                # Pinned Python dependencies (6 packages)
│
├── .ai/                            # AI workspace (this directory)
│   ├── CONTEXT.md                  # Entry point for AI agents
│   ├── ai-instructions.md          # Operating protocol for AI
│   ├── system-overview.md          # High-level architecture
│   ├── module-registry.md          # Every module/class/function documented
│   ├── data-model.md               # All dataclasses, enums, JSON schemas
│   ├── architecture-rules.md       # Invariants and constraints
│   └── file-map.md                 # This file — directory tree
│
├── src/
│   ├── __init__.py                 # Package docstring
│   │
│   ├── core/                       # Domain layer — no external deps
│   │   ├── __init__.py             # Re-exports all core classes
│   │   ├── models.py               # JointType enum, Vector3D, Joint, Pose, MotionData, BoneConnection, SKELETON_HIERARCHY
│   │   ├── interfaces.py           # 5 ABCs: VideoSource, PoseEstimator, MotionProcessor, AnimationExporter, FrameRenderer
│   │   └── exceptions.py           # VisionMoCapError hierarchy (8 subclasses)
│   │
│   ├── config/                     # Configuration management
│   │   ├── __init__.py             # Re-exports
│   │   └── manager.py              # 7 config dataclasses + ConfigManager (load/save/validate)
│   │
│   ├── camera/                     # Camera input
│   │   ├── __init__.py             # Re-exports
│   │   ├── base.py                 # CameraBase(VideoSource) — abstract camera
│   │   ├── backend.py              # Backend IntEnum (DirectShow, MediaFoundation, V4L2, AVFoundation)
│   │   ├── device.py               # CameraDevice dataclass
│   │   └── manager.py              # CameraManager — discovery, open/close/switch, FPS monitor
│   │
│   ├── pose/                       # Pose estimation
│   │   ├── __init__.py             # Re-exports
│   │   ├── base.py                 # PoseEstimatorBase ABC
│   │   ├── pose_detector.py        # PoseDetector — MediaPipe Tasks PoseLandmarker wrapper (does NOT extend base)
│   │   ├── pose_result.py          # Landmark + PoseResult dataclasses
│   │   └── skeleton_renderer.py    # SkeletonRenderer — draws pose overlay on frames
│   │
│   ├── motion/                     # Motion processing and recording
│   │   ├── __init__.py             # Re-exports
│   │   ├── base.py                 # SequenceProcessor ABC, deep copy helpers
│   │   ├── filters.py              # MovingAverage, ExponentialSmoothing, OutlierRemoval filters
│   │   ├── frame_manager.py        # FrameManager — timestamping, resizing, buffer
│   │   ├── interpolator.py         # LinearInterpolator — fill low-visibility landmarks
│   │   ├── motion_player.py        # MotionPlayer + PlaybackState — legacy replay (use src/playback/ for new work)
│   │   ├── motion_recorder.py      # MotionRecorder — accumulate PoseResult → MotionSequence
│   │   ├── motion_sequence.py      # MotionSequence dataclass + JSON serialization
│   │   └── motion_processor.py     # MotionProcessor — pipeline orchestrator (4 default filters)
│   │
│   ├── recording/                  # Recording session management
│   │   ├── __init__.py             # Re-exports
│   │   ├── recording_metadata.py   # RecordingMetadata dataclass
│   │   ├── session.py              # RecordingSession — state machine (idle/recording/paused/completed)
│   │   └── session_manager.py      # SessionManager — thread-safe facade, JSON export
│   │
│   ├── animation/                  # Retargeting and animation
│   │   ├── __init__.py             # Re-exports
│   │   ├── base.py                 # AnimationExporterBase ABC
│   │   ├── animation_clip.py       # AnimationClip — keyframe sequence with lerp/slerp
│   │   ├── animation_engine.py     # AnimationEngine — RetargetedMotion → AnimationClip
│   │   ├── animation_player.py     # AnimationPlayer + PlaybackState — clip playback with speed/loop
│   │   ├── avatar.py               # Avatar — skeleton with named bone hierarchy
│   │   ├── bone.py                 # Bone dataclass
│   │   ├── keyframe.py             # Keyframe dataclass + InterpolationType enum
│   │   ├── retargeted_motion.py    # BoneTransform, RetargetedFrame, RetargetedMotion dataclasses
│   │   ├── retargeter.py           # Retargeter — MotionSequence → RetargetedMotion
│   │   └── skeleton_mapper.py      # SkeletonMapper — landmark indices → bone positions (4 presets)
│   │
│   ├── blender/                    # Blender export (stub)
│   │   ├── __init__.py             # Re-exports
│   │   └── base.py                 # BlenderExporterBase — stub (export/validate no-op)
│   │
│   ├── gui/                        # Desktop GUI (CustomTkinter)
│   │   ├── __init__.py             # Re-exports
│   │   ├── base.py                 # GUIAppBase ABC
│   │   ├── app_controller.py       # AppController — orchestrator, threading, pipeline (457 lines)
│   │   ├── main_window.py          # MainWindow + InfoPanel — top-level CTk window (504 lines)
│   │   ├── camera_widget.py        # CameraWidget — camera preview display
│   │   ├── status_bar.py           # StatusBar — FPS, confidence, flash messages
│   │   └── toolbar.py              # Toolbar — action buttons with state management
│   │
│   ├── playback/                   # Independent playback system (new)
│   │   ├── __init__.py             # Re-exports
│   │   ├── playback_state.py       # PlaybackState enum (STOPPED, PLAYING, PAUSED, FINISHED)
│   │   ├── playback_player.py      # PlaybackPlayer — timing engine, frame stepping, speed control
│   │   └── playback_controller.py  # PlaybackController — file I/O, user-facing API
│   │
│   └── utils/                      # Utilities
│       ├── __init__.py             # Re-exports
│       └── logger.py               # LoggerSetup — rotating file handler + console
│
├── tests/
│   ├── README.md                   # Test suite conventions
│   ├── unit/
│   │   └── test_playback.py        # 46 tests for playback subsystem
│   ├── integration/
│   ├── performance/
│   └── test_data/
│
├── exports/                        # Exported recording JSON files
│   ├── recording_*.json            # Recorded motion sequences
│   └── recordings/
│       └── recording_*.json
│
├── models/                         # MediaPipe model files
│   ├── pose_landmarker_lite.task
│   ├── pose_landmarker_full.task
│   └── pose_landmarker_heavy.task
│
├── logs/                           # Application logs
├── assets/                         # Static resources (empty)
├── screenshots/                    # Screenshots (empty)
├── demo/                           # Demo assets (empty)
├── docs/                           # Documentation (empty)
├── presentation/                   # Presentation materials (empty)
├── report/                         # Formal report (empty)
├── scripts/                        # Utility scripts (empty)
├── tools/                          # Standalone tools (empty)
├── config/                         # Config file references (empty)
└── temp/                           # Temporary files (empty)
```
