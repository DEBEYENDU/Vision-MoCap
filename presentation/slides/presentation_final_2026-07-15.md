---
marp: true
theme: default
paginate: true
---

# VisionMoCap
## Markerless Motion Capture from a Webcam

Final Presentation — July 2026

---

# Problem

Traditional motion capture requires:
- **Expensive hardware** ($10k–$100k+)
- **Multiple cameras** in a controlled studio
- **Reflective markers** attached to the subject
- **Complex setup** and calibration

---

# Solution

VisionMoCap: **Markerless** motion capture using a single webcam

```
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│  Webcam  │──▶│   Pose   │──▶│ Record & │──▶│  Export  │
│          │   │ Detect   │   │  Filter  │   │  (BVH,   │
│          │   │          │   │          │   │  CSV…)   │
└──────────┘   └──────────┘   └──────────┘   └──────────┘
                                                   │
                                                   ▼
                                              ┌──────────┐
                                              │  Blender │
                                              │  Add-on  │
                                              └──────────┘
```

---

# Pipeline

1. **Capture** — OpenCV webcam at 640×480, 30 FPS
2. **Detect** — MediaPipe Pose Landmarker (33 landmarks)
3. **Record** — Thread-safe accumulation with pause/resume
4. **Filter** — 5 filters (Moving Avg, Exp Smoothing, One-Euro, …)
5. **Retarget** — Map landmarks to skeleton bones
6. **Export** — BVH, CSV, NPY, JSON
7. **Blender** — Add-on with Mixamo/Rigify mapping

---

# Pose Detection

**MediaPipe Pose Landmarker** — 33 body landmarks

- 3 complexity levels: Lite / Full / Heavy
- GPU delegate for acceleration
- ~2–8 ms inference time

![Landmarks](https://developers.google.com/static/mediapipe/images/solutions/pose_landmarks_index.png)

---

# Architecture

Clean Architecture with strict layer separation:

```
┌──────────────────────────────────────┐
│          GUI (CustomTkinter)         │
├──────────────────────────────────────┤
│  Camera │ Pose │ Motion │ Playback   │
│  Recording │ Animation │ Blender     │
├──────────────────────────────────────┤
│       Core Interfaces & Models       │
└──────────────────────────────────────┘
```

Two-thread model: worker thread + GUI thread

---

# Export Formats

| Format | Size (1k frames) | Best For |
|--------|-----------------|----------|
| **JSON** | ~8 MB | Archival |
| **BVH** | ~200 KB | Animation |
| **CSV** | ~5 MB | Analysis |
| **NPY** | ~2 MB | Processing |

BVH uses ZXY Euler rotation, 22-bone Mixamo skeleton

---

# Blender Integration

Self-contained add-on with:
- BVH import with **automatic rig mapping**
- Support for **Mixamo** and **Rigify** skeletons
- **One-click bake** to keyframes

```bash
python scripts/package_blender_addon.py
# → visionmocap_addon.zip
```

Install in Blender: Edit → Preferences → Add-ons

---

# Motion Filters

Applied sequentially on loaded recordings:

1. **Outlier Removal** — Threshold-based frame replacement
2. **Moving Average** — Sliding window (3–15 frames)
3. **Exponential Smoothing** — Alpha-weighted blend
4. **One-Euro Filter** — Velocity-adaptive low-pass
5. **Savitzky–Golay** — Polynomial least-squares fit

---

# Performance

| Stage | Target | Achieved |
|-------|--------|----------|
| Pose inference | <33 ms | ~20 ms |
| Frame overhead | <16 ms | ~2 ms |
| End-to-end | <50 ms | ~35 ms |
| Seek latency | <1 ms | <0.1 ms |

GPU delegate: 1.5×–2× speedup over CPU

---

# Testing

**74 unit tests** covering:

- Playback state machine (46 tests)
- BVH export (14 tests)
- CSV/NPY export (10 tests)
- Blender integration (4 tests)
- Performance benchmarks (4 tests)

```bash
pytest tests/ -v
# → 74 passed
```

---

# Key Achievements

- ✅ Full pipeline: webcam → BVH/Blender
- ✅ Real-time at 30+ FPS on consumer hardware
- ✅ 5 production-grade motion filters
- ✅ Blender add-on with automated rig mapping
- ✅ Clean Architecture with 40+ modules
- ✅ 74 passing tests

---

# Limitations & Future Work

**Current limitations:**
- Single-camera (no 3D triangulation)
- 33 landmarks only (no fingers)
- Blender add-on requires manual install

**Future plans:**
- Multi-camera support
- Hand and face tracking
- Real-time retargeting preview
- FBX / glTF export
- Plugin system

---

# Thank You

**GitHub:** https://github.com/DEBEYENDU/Vision-MoCap

**Tech stack:** Python 3.14, MediaPipe, OpenCV 5, CustomTkinter, Blender

*Questions?*
