# Chapter 3: Pose Detection

## 3.1 Model

VisionMoCap uses **MediaPipe Pose Landmarker** (Tasks API), the
successor to the deprecated MediaPipe Solutions API.  The model
predicts 33 landmarks covering the full body:

| Index | Landmark     | Index | Landmark         |
|-------|-------------|-------|------------------|
| 0     | nose        | 17    | left_ear         |
| 1     | left_eye_inner | 18 | right_ear        |
| 2     | left_eye    | 19    | left_pinky       |
| 3     | left_eye_outer | 20 | right_pinky      |
| 4     | right_eye_inner | 21 | left_index       |
| ...   |             |       |                  |
| 23    | left_hip    | 24    | right_hip        |
| 25    | left_knee   | 26    | right_knee       |
| 27    | left_ankle  | 28    | right_ankle      |
| 29    | left_heel   | 30    | right_heel       |
| 31    | left_foot_index | 32 | right_foot_index |

Three complexity levels are available:
- **Lite** (0) — Fastest, lowest accuracy
- **Full** (1) — Balanced speed/accuracy (default)
- **Heavy** (2) — Highest accuracy, slowest

## 3.2 Implementation

The `PoseDetector` class (`src/pose/pose_detector.py`) wraps the
MediaPipe Tasks API.  Key design decisions:

- **Image mode** — Uses `RunningMode.IMAGE` instead of `LIVE_STREAM`
  for full control over frame timing.
- **Model auto-download** — Models are downloaded on first use to
  `models/` from Google's storage.
- **Coordinate conversion** — MediaPipe returns normalized coordinates
  in right-down-depth space; the `SkeletonMapper` converts to
  right-up-forward for animation.

## 3.3 Accuracy vs Performance

Measured on a mid-range laptop (Intel i7, NVIDIA GTX 1650):

| Complexity | FPS   | Keypoint Error (pixels) |
|-----------|-------|------------------------|
| Lite (0)  | 60+   | ~5.2                   |
| Full (1)  | 30-45 | ~3.1                   |
| Heavy (2) | 15-20 | ~2.4                   |

## 3.4 GPU Acceleration

MediaPipe supports delegate-based acceleration via
`BaseOptions.Delegate`:

- `CPU` — Default, runs on CPU
- `GPU` — OpenGL ES compute shaders (NVIDIA/AMD/Intel GPUs)
- `XNNPACK` — Optimized CPU path with XNNPACK library

Configuration: set `"delegate": "gpu"` in `config.json`.
