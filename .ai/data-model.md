# Data Model Reference

Complete reference for every dataclass, enum, type alias, and JSON schema in the project.

---

## Enums

### `JointType` (`src/core/models.py`)
33 MediaPipe pose landmark labels:
`NOSE`, `LEFT_EYE_INNER`, `LEFT_EYE`, `LEFT_EYE_OUTER`, `RIGHT_EYE_INNER`, `RIGHT_EYE`, `RIGHT_EYE_OUTER`, `LEFT_EAR`, `RIGHT_EAR`, `MOUTH_LEFT`, `MOUTH_RIGHT`, `LEFT_SHOULDER`, `RIGHT_SHOULDER`, `LEFT_ELBOW`, `RIGHT_ELBOW`, `LEFT_WRIST`, `RIGHT_WRIST`, `LEFT_PINKY`, `RIGHT_PINKY`, `LEFT_INDEX`, `RIGHT_INDEX`, `LEFT_THUMB`, `RIGHT_THUMB`, `LEFT_HIP`, `RIGHT_HIP`, `LEFT_KNEE`, `RIGHT_KNEE`, `LEFT_ANKLE`, `RIGHT_ANKLE`, `LEFT_HEEL`, `RIGHT_HEEL`, `LEFT_FOOT_INDEX`, `RIGHT_FOOT_INDEX`

### `Backend` (`src/camera/backend.py`)
- `DIRECTSHOW = cv2.CAP_DSHOW`
- `MEDIA_FOUNDATION = cv2.CAP_MSMF`
- `V4L2 = cv2.CAP_V4L2`
- `AVFOUNDATION = cv2.CAP_AVFOUNDATION`
- Class method: `from_string(name) -> Backend`

### `PlaybackState` (`src/motion/motion_player.py`)
`STOPPED`, `PLAYING`, `PAUSED` (3-state)

### `PlaybackState` (`src/animation/animation_player.py`)
`STOPPED`, `PLAYING`, `PAUSED` (3-state, independent)

### `PlaybackState` (`src/playback/playback_state.py`)
`STOPPED`, `PLAYING`, `PAUSED`, `FINISHED` (4-state, independent)

### `InterpolationType` (`src/animation/keyframe.py`)
`LINEAR`, `STEP`

---

## Core dataclasses

### `Vector3D` — `src/core/models.py` (frozen)
| Field | Type | Description |
|-------|------|-------------|
| `x` | `float` | X coordinate |
| `y` | `float` | Y coordinate |
| `z` | `float` | Z coordinate |

Operations: `+`, `-`, `*` (scalar), `/` (scalar). Methods: `magnitude() -> float`, `dot(other) -> float`, `cross(other) -> Vector3D`, `normalize() -> Vector3D`. Validates `isfinite` on construction.

### `Joint` — `src/core/models.py`
| Field | Type | Description |
|-------|------|-------------|
| `joint_type` | `JointType` | Which landmark |
| `position` | `Vector3D` | 3D position |
| `confidence` | `float` | Detection confidence [0,1], validated on construction |

### `Pose` — `src/core/models.py`
| Field | Type | Description |
|-------|------|-------------|
| `joints` | `Dict[JointType, Joint]` | All detected joints |
| `timestamp` | `float` | Monotonic timestamp |
| `frame_id` | `int` | Frame number |

### `MotionData` — `src/core/models.py`
| Field | Type | Description |
|-------|------|-------------|
| `poses` | `List[Pose]` | Ordered pose sequence |
| `fps` | `float` | Average frame rate |
| `duration` | `float` | Total duration (s) |
| `frame_count` | `int` | Property, `len(poses)` |

### `BoneConnection` — `src/core/models.py` (frozen)
| Field | Type | Description |
|-------|------|-------------|
| `parent` | `JointType` | Parent joint |
| `child` | `JointType` | Child joint |

### `SKELETON_HIERARCHY` — `src/core/models.py`
`List[BoneConnection]` — 32 connections defining the full-body skeleton (e.g., `NOSE→LEFT_EYE_INNER`, `LEFT_SHOULDER→LEFT_ELBOW`, etc.)

---

## Pose result dataclasses

### `Landmark` — `src/pose/pose_result.py`
| Field | Type | Description |
|-------|------|-------------|
| `x` | `float` | Normalized x [0,1] |
| `y` | `float` | Normalized y [0,1] |
| `z` | `float` | Depth (negative = closer to camera) |
| `visibility` | `float` | Detection visibility [0,1] |

### `PoseResult` — `src/pose/pose_result.py`
| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | `float` | Monotonic timestamp (s) |
| `landmarks` | `List[Landmark]` | 33 normalized landmarks |
| `world_landmarks` | `List[Landmark]` | 33 world-space landmarks (meters) |
| `confidence` | `float` | Overall detection confidence [0,1] |
| `frame_width` | `int` | Input frame width (px) |
| `frame_height` | `int` | Input frame height (px) |
| `pose_detected` | `bool` | Whether a pose was found |

---

## Motion sequence dataclass

### `MotionSequence` — `src/motion/motion_sequence.py`
| Field | Type | Description |
|-------|------|-------------|
| `pose_results` | `List[PoseResult]` | Ordered pose frame data |
| `start_time` | `float` | Monotonic recording start (s) |
| `end_time` | `float` | Monotonic recording end (s) |
| `total_frames` | `int` | Frame count |
| `average_fps` | `float` | Mean frame rate |
| `duration` | `float` | Total duration (s) |

Methods:
- `to_dict() -> dict` — JSON-serializable dict
- `from_dict(dict) -> MotionSequence` — classmethod deserializer
- `save_json(path: Path)` — write to file
- `load_json(path: Path) -> MotionSequence` — classmethod file loader

---

## Recording metadata dataclass

### `RecordingMetadata` — `src/recording/recording_metadata.py`
| Field | Type | Description |
|-------|------|-------------|
| `date_iso` | `str` | ISO 8601 date string |
| `duration_seconds` | `float` | Recording duration |
| `average_fps` | `float` | Average frame rate |
| `average_confidence` | `float` | Mean detection confidence |
| `frame_count` | `int` | Number of frames |
| `camera_index` | `int` | Camera device index |

Class method: `build(duration_seconds, average_fps, average_confidence, frame_count, camera_index) -> RecordingMetadata`

---

## Configuration dataclasses (`src/config/manager.py`)

### `CameraConfig`
`device_id: int = 0`, `width: int = 640`, `height: int = 480`, `fps: float = 30.0`, `max_camera_index: int = 20`, `resolution_preset: str = "640x480"`, `backend: str = "directshow"`

### `PoseConfig`
`model_complexity: int = 1`, `min_detection_confidence: float = 0.5`, `min_tracking_confidence: float = 0.5`, `static_image_mode: bool = False`, `model_path: Optional[str] = None`

### `MotionConfig`
`smoothing_window: int = 5`, `velocity_threshold: float = 0.1`, `interpolation_enabled: bool = True`, `outlier_threshold: float = 0.15`, `exponential_alpha: float = 0.5`, `visibility_threshold: float = 0.5`

### `AnimationConfig`
`export_format: str = "fbx"`, `scale_factor: float = 1.0`, `apply_smoothing: bool = True`

### `BlenderConfig`
`blender_executable: str = "blender"`, `script_path: str = ""`, `auto_launch: bool = False`

### `LoggingConfig`
`level: str = "INFO"`, `directory: str = "logs"`, `max_file_size_mb: int = 10`, `backup_count: int = 5`

### `AppConfig`
Root config: `camera: CameraConfig`, `pose: PoseConfig`, `motion: MotionConfig`, `animation: AnimationConfig`, `blender: BlenderConfig`, `logging: LoggingConfig`

### `RESOLUTION_PRESETS`
```python
{
    "640x480": (640, 480),
    "1280x720": (1280, 720),
    "1920x1080": (1920, 1080),
}
```

---

## Camera dataclasses

### `CameraDevice` — `src/camera/device.py`
| Field | Type | Description |
|-------|------|-------------|
| `index` | `int` | Device index |
| `name` | `str` | Device name |
| `backend` | `Backend` | OpenCV backend |
| `is_available` | `bool` | Whether device responds |
| `resolution_width` | `int` | Native width |
| `resolution_height` | `int` | Native height |
| `fps` | `float` | Native frame rate |

---

## Animation dataclasses

### `Bone` — `src/animation/bone.py`
| Field | Type |
|-------|------|
| `name` | `str` |
| `parent` | `Optional[str]` |
| `children` | `List[str]` |
| `head_position` | `Vector3D` |
| `tail_position` | `Vector3D` |
| `rotation` | `Tuple[float,float,float,float]` (w,x,y,z quat) |
| `length` | `float` (auto-computed from head/tail) |
| Property: `direction` | unit head→tail vector |

### `Keyframe` — `src/animation/keyframe.py`
| Field | Type |
|-------|------|
| `timestamp` | `float` |
| `frame_number` | `int` |
| `bone_transforms` | `Dict[str, BoneTransform]` |
| `interpolation` | `InterpolationType` |

### `BoneTransform` — `src/animation/retargeted_motion.py`
| Field | Type |
|-------|------|
| `position` | `Vector3D` |
| `rotation` | `Tuple[float,float,float,float]` |

### `RetargetedFrame` — `src/animation/retargeted_motion.py`
| Field | Type |
|-------|------|
| `bones` | `Dict[str, BoneTransform]` |
| `timestamp` | `float` |

### `RetargetedMotion` — `src/animation/retargeted_motion.py`
| Field | Type |
|-------|------|
| `frames` | `List[RetargetedFrame]` |
| `avatar_name` | `str` |
| `fps` | `float` |
| `duration` | `float` |

---

## Type aliases

### `BoneMapping` — `src/animation/skeleton_mapper.py`
`Dict[str, int]` — `{"head": <landmark_idx>, "tail": <landmark_idx>}`

### `SkeletonMapping` — `src/animation/skeleton_mapper.py`
`Dict[str, BoneMapping]` — maps bone names to landmark index pairs

---

## JSON schemas

### Recording JSON (exported by SessionManager.save_recording)

Two formats are supported by the playback system:

**Plain format** (from `MotionSequence.to_dict()`):
```json
{
  "start_time": float,
  "end_time": float,
  "total_frames": int,
  "average_fps": float,
  "duration": float,
  "pose_results": [
    {
      "timestamp": float,
      "landmarks": [{"x": float, "y": float, "z": float, "visibility": float}, ...],
      "world_landmarks": [{"x": float, "y": float, "z": float, "visibility": float}, ...],
      "confidence": float,
      "frame_width": int,
      "frame_height": int,
      "pose_detected": bool
    },
    ...
  ]
}
```

**Enhanced format** (from SessionManager — adds metadata):
```json
{
  ...all plain fields...,
  "metadata": {
    "date_iso": "2026-07-11T...",
    "duration_seconds": float,
    "average_fps": float,
    "average_confidence": float,
    "frame_count": int,
    "camera_index": int
  },
  "frame_numbers": [int, ...],
  "fps_values": [float, ...]
}
```

### Config JSON (`config.json`)
```json
{
  "camera": { "device_id": 0, "width": 640, ... },
  "pose": { "model_complexity": 1, ... },
  "motion": { "smoothing_window": 5, ... },
  "animation": { "export_format": "fbx", ... },
  "blender": { "blender_executable": "blender", ... },
  "logging": { "level": "INFO", "directory": "logs", ... }
}
```

---

## Important: Two joint numbering systems

The project has **two independent numbering systems** for body landmarks:

1. **`JointType` enum** (`src/core/models.py`) — 33 symbolic names (e.g., `LEFT_SHOULDER`, `RIGHT_ELBOW`)
2. **MediaPipe landmark indices** (0–32, used in `POSE_CONNECTIONS`, `SkeletonMapper` presets) — e.g., MediaPipe index 11 = left shoulder, MediaPipe index 12 = right shoulder

**Do NOT assume they correspond by ordinal position.** Always verify which system a module uses.
