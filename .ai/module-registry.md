# Module Registry

Complete inventory of every Python file, class, enum, and public function in `src/`.

---

## `app.py` (33 lines)
**Entry point.** Loads config, sets up logging, creates `MainWindow`, runs GUI.
- **Function:** `main()`

---

## `src/core/` — Domain layer (zero project dependencies)

### `src/core/models.py` (212 lines)
Domain models — the heart of the data layer.
- **`JointType(Enum)`** — 33 members (NOSE, LEFT_EYE_INNER, ..., RIGHT_FOOT_INDEX)
- **`Vector3D(frozen dataclass)`** — `x: float, y: float, z: float`. Ops: `+`, `-`, `*`, `/`, `magnitude`, `dot()`, `cross()`, `normalize()`
- **`Joint(dataclass)`** — `joint_type: JointType, position: Vector3D, confidence: float`
- **`Pose(dataclass)`** — `joints: Dict[JointType, Joint], timestamp: float, frame_id: int`
- **`MotionData(dataclass)`** — `poses: List[Pose], fps: float, duration: float`. Property: `frame_count`
- **`BoneConnection(frozen dataclass)`** — `parent: JointType, child: JointType`
- **Constant:** `SKELETON_HIERARCHY: List[BoneConnection]` — 32 connections

### `src/core/interfaces.py` (165 lines)
Abstract base classes defining the pipeline contracts.
- **`VideoSource(ABC)`** — `open()`, `read()`, `release()`, props: `is_opened`, `frame_width`, `frame_height`, `fps`
- **`PoseEstimator(ABC)`** — `initialize()`, `estimate(frame)`, `shutdown()`
- **`MotionProcessor(ABC)`** — `process(pose_data) -> MotionData`, `reset()`
- **`AnimationExporter(ABC)`** — `export(motion_data, output_path)`, `validate_environment()`
- **`FrameRenderer(ABC)`** — `render(frame, pose_data)`, `initialize_display()`, `destroy_display()`

### `src/core/exceptions.py` (49 lines)
Exception hierarchy.
- **`VisionMoCapError(Exception)`** — base, has `cause` field
- **`ConfigurationError`**, **`CameraError`**, **`PoseEstimationError`**, **`MotionProcessingError`**, **`AnimationExportError`**, **`RetargetingError`**, **`BlenderIntegrationError`**, **`GUIError`**

---

## `src/config/` — Configuration management

### `src/config/manager.py` (246 lines)
JSON-backed typed configuration.
- **Dataclasses:** `CameraConfig`, `PoseConfig`, `MotionConfig`, `AnimationConfig`, `BlenderConfig`, `LoggingConfig`, `AppConfig`
- **`ConfigManager`** — `load()`, `save()`, `config` property. Internal: `_load_from_file()`, `_create_default()`, `_save_to_file()`, `_config_to_dict()`, `_dict_to_config()`
- **Constant:** `RESOLUTION_PRESETS: dict[str, tuple[int,int]]`

---

## `src/camera/` — Camera input

### `src/camera/base.py` (72 lines)
- **`CameraBase(VideoSource)`** — stores config, implements lifecycle. `read()` raises NotImplemented.

### `src/camera/backend.py` (50 lines)
- **`Backend(IntEnum)`** — `DIRECTSHOW`, `MEDIA_FOUNDATION`, `V4L2`, `AVFOUNDATION`. Class method: `from_string()`.

### `src/camera/device.py` (35 lines)
- **`CameraDevice(dataclass)`** — `index, name, backend, is_available, resolution_width, resolution_height, fps`

### `src/camera/manager.py` (386 lines)
- **`_FPSMonitor`** — sliding window FPS (deque maxlen=30). `tick()`, `reset()`. Properties: `current_fps`, `average_fps`, `min_fps`, `max_fps`.
- **`CameraManager`** — `discover_cameras()`, `open_camera(index)`, `close_camera()`, `switch_camera(index)`, `get_frame()`, `get_current_camera()`. Context manager. **Not thread-safe.**

---

## `src/pose/` — Pose estimation

### `src/pose/base.py` (49 lines)
- **`PoseEstimatorBase(PoseEstimator)`** — stores config, `initialize()`, `shutdown()`, `estimate()` raises NotImplemented.

### `src/pose/pose_detector.py` (267 lines)
- **`PoseDetector`** — **does NOT extend PoseEstimatorBase**. Wraps MediaPipe Tasks PoseLandmarker. Methods: `initialize()`, `detect(frame) -> PoseResult`, `shutdown()`. Static: `_extract_landmarks()`.
- **Internal:** `_resolve_model_path()`, `_download_model()` — auto-downloads from Google CDN.

### `src/pose/pose_result.py` (46 lines)
- **`Landmark(dataclass)`** — `x, y, z, visibility: float`
- **`PoseResult(dataclass)`** — `timestamp, landmarks, world_landmarks, confidence, frame_width, frame_height, pose_detected`

### `src/pose/skeleton_renderer.py` (194 lines)
- **`SkeletonRenderer`** — draws skeleton overlay on frame. Config: `draw_landmarks`, `draw_connections`, `draw_joint_ids`, `draw_confidence`. Method: `render(frame, pose_result) -> NDArray`.
- **Constant:** `POSE_CONNECTIONS` — 26 MediaPipe landmark index pairs.

---

## `src/motion/` — Motion processing, recording, and replay

### `src/motion/base.py` (138 lines)
- **Functions:** `deep_copy_pose_result()`, `deep_copy_sequence()` — deep copy helpers.
- **`SequenceProcessor(ABC)`** — `name` property, `process(sequence) -> MotionSequence`.
- **`MotionProcessorBase(MotionProcessor)`** — stores config, `process()`, `reset()`.

### `src/motion/filters.py` (457 lines)
- **`MovingAverageFilter(SequenceProcessor)`** — sliding window smoothing.
- **`ExponentialSmoothingFilter(SequenceProcessor)`** — first-order IIR.
- **`OutlierRemovalFilter(SequenceProcessor)`** — displacement threshold + linear interpolation fill.

### `src/motion/frame_manager.py` (151 lines)
- **`FrameManager`** — `process(frame)`, `reset()`, `get_buffer()`. Properties: `frame_number`, `frame_width`, `frame_height`, `timestamp`, `buffer_size`.

### `src/motion/interpolator.py` (221 lines)
- **`LinearInterpolator(SequenceProcessor)`** — fills low-visibility landmarks via linear interpolation between nearest valid frames.

### `src/motion/motion_player.py` (242 lines)
- **`PlaybackState(Enum)`** — `STOPPED, PLAYING, PAUSED` (3 states, no FINISHED).
- **`MotionPlayer`** — replay of MotionSequence. Methods: `load()`, `play()`, `pause()`, `resume()`, `stop()`, `advance()`, `step_forward()`, `step_backward()`, `get_current_frame()`, `set_speed()`. **Used for recording-adjacent preview. For new playback features, use `src/playback/`.**

### `src/motion/motion_recorder.py` (174 lines)
- **`MotionRecorder`** — accumulates PoseResult into MotionSequence. Methods: `start()`, `record()`, `pause()`, `resume()`, `stop()`, `cancel()`/`discard()`. Properties: `is_recording`, `is_paused`, `recorded_frame_count`, `elapsed_time`.

### `src/motion/motion_sequence.py` (136 lines)
- **`MotionSequence(dataclass)`** — `pose_results, start_time, end_time, total_frames, average_fps, duration`. Methods: `to_dict()`, `from_dict()`, `save_json()`, `load_json()`.
- **Functions:** `_pose_result_to_dict()`, `_dict_to_pose_result()` — JSON helpers.

### `src/motion/motion_processor.py` (166 lines)
- **`MotionProcessor`** — pipeline orchestrator. Default: `OutlierRemoval → LinearInterpolator → MovingAverage → ExponentialSmoothing`. Methods: `process()`, `add_processor()`, `insert_processor()`, `remove_processor()`, `clear_pipeline()`.

---

## `src/recording/` — Recording session management

### `src/recording/recording_metadata.py` (75 lines)
- **`RecordingMetadata(dataclass)`** — `date_iso, duration_seconds, average_fps, average_confidence, frame_count, camera_index`. Class method: `build()` (auto-sets date). Method: `to_dict()`.

### `src/recording/session.py` (259 lines)
- **`RecordingSession`** — state machine: `STATE_IDLE → STATE_RECORDING ↔ STATE_PAUSED → STATE_COMPLETED`. Methods: `start()`, `pause()`, `resume()`, `stop()`, `discard()`, `record_pose()`. Properties: `state`, `is_recording`, `is_paused`, `is_completed`, `is_active`, `frame_count`, `frames`, `frame_numbers`, `fps_values`, `elapsed_seconds`, `wall_seconds`. Query: `get_average_fps()`, `get_average_confidence()`.

### `src/recording/session_manager.py` (274 lines)
- **`SessionManager`** — thread-safe facade (via `threading.Lock`). Owns `RecordingSession` + `MotionRecorder`. Methods: `start_session()`, `record_pose()` (thread-safe), `pause_session()`, `resume_session()`, `stop_session()`, `discard_session()`, `save_recording() -> Optional[Path]`, `shutdown()`.

---

## `src/animation/` — Retargeting and animation

### `src/animation/base.py` (43 lines)
- **`AnimationExporterBase(AnimationExporter)`** — stores config, stub `export()`, `validate_environment()`.

### `src/animation/bone.py` (67 lines)
- **`Bone(dataclass)`** — `name, parent, children, head_position, tail_position, rotation (quaternion), length`. Property: `direction`.

### `src/animation/keyframe.py` (50 lines)
- **`InterpolationType(Enum)`** — `LINEAR, STEP`
- **`Keyframe(dataclass)`** — `timestamp, frame_number, bone_transforms, interpolation`

### `src/animation/retargeted_motion.py` (72 lines)
- **`BoneTransform(dataclass)`** — `position, rotation` (quaternion)
- **`RetargetedFrame(dataclass)`** — `bones: Dict[str, BoneTransform], timestamp`
- **`RetargetedMotion(dataclass)`** — `frames, avatar_name, fps, duration`

### `src/animation/avatar.py` (161 lines)
- **`Avatar`** — skeleton with named bone hierarchy. Class method: `from_parent_pairs()`. Properties: `name`, `root_bone`, `bones`, `bone_names`, `bone_count`. Method: `bone(name)`.

### `src/animation/skeleton_mapper.py` (274 lines)
- **Type aliases:** `BoneMapping = Dict[str, int]`, `SkeletonMapping = Dict[str, BoneMapping]`
- **`SkeletonMapper`** — maps MediaPipe landmarks to avatar bones. Constructor: custom `mapping` or named `preset`. Methods: `has_bone()`, `bone_names`, `map_frame(pose_result)`.
- **Presets:** `PRESET_MIXAMO`, `PRESET_BLENDER`, `PRESET_VRM`, `PRESET_READY_PLAYER_ME`, `AVAILABLE_PRESETS`

### `src/animation/retargeter.py` (199 lines)
- **`Retargeter`** — converts `MotionSequence → RetargetedMotion`. Method: `retarget(sequence)`. Static: `_direction_to_quaternion()`.

### `src/animation/animation_clip.py` (318 lines)
- **`AnimationClip`** — keyframe sequence with interpolation (lerp + slerp). Methods: `add_keyframe()`, `remove_keyframe()`, `get_keyframe()`, `interpolate(timestamp)`.

### `src/animation/animation_engine.py` (236 lines)
- **`AnimationEngine`** — `convert(motion, fps) -> AnimationClip`, `generate_keyframes()`, `find_frame()`.

### `src/animation/animation_player.py` (207 lines)
- **`PlaybackState(Enum)`** — `STOPPED, PLAYING, PAUSED` (3 states, independent from other PlaybackState enums).
- **`AnimationPlayer`** — `play()`, `pause()`, `resume()`, `stop()`, `seek(timestamp)`, `update(delta_time)`. Properties: `state`, `current_time`, `current_frame`, `speed`, `loop`.

---

## `src/blender/` — Blender export (stub)

### `src/blender/base.py` (44 lines)
- **`BlenderExporterBase(AnimationExporter)`** — stub, `export()` and `validate_environment()` are no-ops.

---

## `src/gui/` — Desktop GUI (CustomTkinter)

### `src/gui/base.py` (45 lines)
- **`GUIAppBase(ABC)`** — `initialize()`, `run()` (abstract), `shutdown()`. Properties: `title`, `is_running`.

### `src/gui/app_controller.py` (457 lines)
**Central orchestrator.** Owns camera manager, frame manager, pose detector, skeleton renderer, motion recorder, session manager. Manages worker thread.
- **`AppController`** — camera: `discover_cameras()`, `start_camera(index)`, `stop_camera()`, `is_camera_open`. Pipeline (internal): `_capture_loop()`. GUI-facing: `get_next_frame()`, `get_pose_result()`, `get_average_fps()`, `get_tracking_confidence()`, `get_frame_number()`, `get_current_camera()`, `get_camera_index()`, `get_camera_name()`, `pop_error()`. Recording: `start_recording()`, `stop_recording()`, `pause_recording()`, `resume_recording()`, `discard_recording()`.
- **Internal state (under `_lock`):** `_camera_open`, `_latest_pose`, `_status_fps`, `_status_confidence`, `_status_cam_index`, `_status_cam_name`, `_status_frame_number`
- **Threading:** `_frame_queue: Queue` (maxsize=2), `_error_queue: Queue`, `_stop_event: Event`, `_worker: Thread`, `_lock: Lock`

### `src/gui/main_window.py` (504 lines)
- **`InfoPanel(ctk.CTkFrame)`** — side panel with device info, pose status, recording indicator.
- **`MainWindow(GUIAppBase)`** — top-level CTk window. Layout: camera preview + info panel + toolbar + status bar. Update loop at 33ms. Callbacks: `_on_start_camera`, `_on_stop_camera`, `_on_record`, `_on_pause`, `_on_export`, `_on_settings`, `_on_exit`.

### `src/gui/camera_widget.py` (116 lines)
- **`CameraWidget(ctk.CTkFrame)`** — frame display with aspect-ratio-preserving resize. `update_frame(frame)`, `clear()`.

### `src/gui/status_bar.py` (182 lines)
- **`StatusBar(ctk.CTkFrame)`** — FPS, confidence, camera status, recording status, flash messages. `flash(message, level)` auto-clears after 5s.

### `src/gui/toolbar.py` (168 lines)
- **`Toolbar(ctk.CTkFrame)`** — buttons: Start/Stop Camera, Record, Pause, Export, Settings, Exit. State management: `set_camera_started()`, `set_camera_stopped()`, `set_recording()`, `set_paused()`, etc.

---

## `src/playback/` — Independent playback system

### `src/playback/playback_state.py` (21 lines)
- **`PlaybackState(Enum)`** — `STOPPED, PLAYING, PAUSED, FINISHED` (4 states).

### `src/playback/playback_player.py` (289 lines)
Core timing engine.
- **`PlaybackPlayer`** — `load(sequence)`, `play()`, `pause()`, `resume()`, `stop()`, `advance() -> PoseResult`, `seek(frame)`, `step_forward()`, `step_backward()`, `set_speed()`. Timing rebased on speed change. State machine: STOPPED ↔ PLAYING ↔ PAUSED, PLAYING → FINISHED, FINISHED → PLAYING rewinds.

### `src/playback/playback_controller.py` (244 lines)
User-facing API with file I/O.
- **`PlaybackController`** — `load(path) -> bool`, `unload()`, `play()`, `pause()`, `stop()`, `seek(frame)`, `next_frame()`, `previous_frame()`, `set_speed()`, `get_current_pose()`, `advance()`. Properties for all playback state.

---

## `src/utils/` — Utilities

### `src/utils/logger.py` (84 lines)
- **`LoggerSetup`** — rotating file handler + console handler. `get_logger() -> Logger`.

---

## Import dependency graph

```
src/core/         ← (no project imports)
src/config/       ← core.exceptions
src/camera/       ← core.interfaces, core.exceptions, config
src/pose/         ← core.interfaces, core.exceptions, config
src/motion/       ← core.interfaces, core.models, core.exceptions, config, pose.pose_result
src/recording/    ← pose.pose_result, motion.motion_sequence, motion.motion_recorder
src/animation/    ← core.models, core.interfaces, core.exceptions, config, motion.motion_sequence, pose.pose_result
src/blender/      ← core.interfaces, core.models, config
src/gui/          ← camera, config, core.exceptions, motion, pose, recording
src/playback/     ← motion.motion_sequence, pose.pose_result
src/utils/        ← (std lib only)
```
