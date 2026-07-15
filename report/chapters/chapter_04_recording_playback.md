# Chapter 4: Motion Recording and Playback

## 4.1 Recording Subsystem

The `MotionRecorder` (`src/motion/motion_recorder.py`) accumulates
`PoseResult` objects during a capture session.

**Lifecycle:** `start()` → `record(pose)` × N → `stop()` → `MotionSequence`

- **Pause/Resume** — Paused time is tracked separately and excluded
  from the final duration calculation.
- **Frame subsampling** — A configurable `frame_subsample` parameter
  (`MotionConfig`) stores only every Nth frame, reducing memory
  usage during long recordings.
- **Thread safety** — The recorder is designed for single-thread
  access (called from the worker thread).

## 4.2 MotionSequence Data Model

`MotionSequence` (`src/motion/motion_sequence.py`) is the central data
container:

```python
@dataclass
class MotionSequence:
    pose_results: List[PoseResult]  # Ordered frames
    start_time: float               # Monotonic start timestamp
    end_time: float                 # Monotonic end timestamp
    total_frames: int
    average_fps: float
    duration: float
```

Each `PoseResult` contains 33 `Landmark` objects (x, y, z, visibility)
for both normalized and world-space coordinates.

## 4.3 Playback Subsystem

The playback module (`src/playback/`) provides:

- **PlaybackPlayer** — Core state machine (STOPPED / PLAYING / PAUSED /
  FINISHED) with frame-accurate seeking and speed control.
- **PlaybackController** — Higher-level API that loads both plain and
  enhanced JSON formats, handles speed normalization, and provides
  frame stepping.
- **PlaybackRenderer** — Renders the skeleton overlay during playback
  using the same drawing primitives as the live view.

## 4.4 State Machine

```
STOPPED ──play()──▶ PLAYING ──pause()──▶ PAUSED
  ▲                  │   ▲                 │
  └──stop()──────────┘   └──resume()───────┘
  │
  └──(finished)──▶ FINISHED ──play()──▶ PLAYING
```

## 4.5 Frame Seeking

Seeking uses frame index (0-based) rather than time to avoid
floating-point accumulation errors.  The `seek()` method clamps to
valid range and is O(1).
