# Architecture Rules — Invariants, Constraints, and Conventions

These rules must **never be violated** during AI-assisted development.

---

## Layer dependency rule

A package may only import from packages below it or at the same level in this hierarchy:

```
core  →  config  →  {camera, pose, motion, recording, animation, blender}  →  gui
                                                                             →  playback
```

**Violations:**
- `camera` must not import from `gui`
- `pose` must not import from `recording`
- `motion` must not import from `camera`
- `playback` must not import from `camera`, `pose` (except `pose_result`), `gui`, `recording`
- `gui` may import from any backend package

---

## Thread safety rules

1. **`CameraManager` is NOT thread-safe** — only access from the worker thread.
2. **`PoseDetector` is NOT thread-safe** — only access from the worker thread.
3. **`MotionRecorder` is NOT thread-safe** — only access from the worker thread.
4. **`SessionManager.record_pose()` acquires `_lock`** — thread-safe for worker thread calls.
5. **`SessionManager` non-record_pose methods acquire `_lock`** — thread-safe for GUI thread calls.
6. **Shared state in `AppController`** (`_latest_pose`, `_status_*`) is protected by `_lock`.
7. **Frame delivery** uses `queue.Queue(maxsize=2)` — worker produces, GUI consumes.
8. **Never call GUI methods from the worker thread** — use queues to communicate.
9. **`save_recording()` file I/O occurs outside the lock** — session data is captured under lock first.

---

## Recording pipeline rules

1. **`RecordingSession` and `MotionRecorder` record in parallel** — both receive the same `PoseResult` objects during `SessionManager.record_pose()`.
2. **`MotionRecorder.record()` is called WITHOUT the `SessionManager._lock`** — `SessionManager.record_pose()` acquires the lock, calls `_session.record_pose()` inside lock, then calls `_recorder.record(pose)` outside lock.
3. **Recording state machine is irreversible at COMPLETED** — `STOPPED → RECORDING ↔ PAUSED → COMPLETED`. Once completed, no more frames can be added.
4. **`save_recording()` requires COMPLETED state** — returns None if session is active.
5. **Export JSON combines `MotionSequence.to_dict()` + extra metadata keys** — `MotionSequence.load_json()` gracefully ignores extra keys.

---

## Playback system rules

1. **All new playback features go in `src/playback/`** — do not modify `src/motion/motion_player.py`.
2. **Playback must NOT depend on camera** — no `import` from `src/camera/`.
3. **Playback must NOT require MediaPipe** — no `import mediapipe`.
4. **Playback may depend on** `src/motion/motion_sequence.MotionSequence` (pure data) and `src/pose/pose_result.{Landmark, PoseResult}` (pure data).
5. **Playback `PlaybackState` enum is independent** — do not reuse from `motion/` or `animation/`.
6. **Frame stepping auto-pauses** — `next_frame()` / `previous_frame()` should pause playing to let users examine individual frames.
7. **Speed change during play rebases timing** to avoid frame jumps.

---

## Data mutation rules

1. **`SkeletonRenderer.render()` mutates the input frame in-place** — callers must be aware.
2. **`MotionProcessor.process()` must NOT mutate its input** — the pipeline's `deep_copy_sequence()` usage ensures immutability.
3. **Filters create deep copies of `MotionSequence`** — the original sequence is never modified.
4. **`FrameManager.process()` stores frames in internal buffer** — buffer can be discarded via `reset()`.

---

## Configuration rules

1. **`ConfigManager._dict_to_config()` silently falls back to defaults** for malformed fields — broken config files degrade gracefully.
2. **ConfigManager raises `ConfigurationError`** for fundamental failures (IO, parsing).
3. **`AppConfig` is the root config** — all sub-configs are nested dataclasses with `default_factory`.

---

## GUI rules

1. **No GUI code in backend modules** — GUI imports backend, not vice versa.
2. **`MainWindow._update_loop` runs at ~30fps (33ms interval)** — controls all UI polling.
3. **Status bar FPS and confidence are throttled to 1Hz** — not updated every frame.
4. **Camera starts automatically** with the first discovered device — not user-selected.
5. **Export is a mock** — copies latest JSON from `exports/recordings/`.
6. **Settings dialog is a placeholder** — shows stub message.

---

## Exception handling rules

1. **All custom exceptions inherit from `VisionMoCapError`** — catch `VisionMoCapError` for application-level error handling.
2. **`VisionMoCapError` has a `cause` field** — use `except VisionMoCapError as e: e.cause` for root cause.
3. **Worker thread errors go to `_error_queue`** — GUI polls via `pop_error()`.
4. **Camera and pose estimation errors are caught in `_capture_loop`** and pushed to error queue.

---

## Coding conventions

1. **All files use `from __future__ import annotations`** — deferred evaluation of type hints.
2. **Type hints on all public APIs** — private methods may omit.
3. **Use `Optional[X]` not `X | None`** — for consistency with existing code.
4. **ABCs for interfaces** — use `abc.ABC` and `@abstractmethod`.
5. **Dataclasses for data containers** — use `@dataclass` with proper defaults.
6. **Enums via `auto()`** — use `from enum import Enum, auto`.
7. **Logging via `logging.getLogger(self.__class__.__name__)`** — class-level logger.
8. **Module-level constants in UPPER_CASE** — like `POSE_CONNECTIONS`, `SKELETON_HIERARCHY`.
9. **Private methods prefixed with `_`** — internal implementation detail.
10. **No comments explaining *what* the code does** — comments explain *why*.

---

## Known issues (do NOT fix unless instructed)

1. `PoseDetector` does NOT extend `PoseEstimatorBase` — the ABC hierarchy is not used by the concrete implementation.
2. `CameraManager._probe_camera()` creates/releases 20 `VideoCapture` instances — slow discovery.
3. Camera names are always `"Camera {index}"` — no real device name.
4. `AnimationClip._slerp_quaternion` has potential numerical instability near dot=1.0 (falls back to nlerp at `>0.9995`).
5. Three separate FPS tracking mechanisms exist (camera `_FPSMonitor`, `PoseResult.confidence`, `RecordingSession._fps_values`).
6. Three separate `PlaybackState` enums (motion, animation, playback) — all independent.
