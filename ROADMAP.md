# Roadmap

VisionMoCap development milestones and future plans.

---

## ✅ v1.0 — Pose Detection *(Complete)*

- [x] Real-time markerless pose detection using MediaPipe
- [x] Webcam support with device selection
- [x] 33-landmark skeleton overlay rendering
- [x] Clean Architecture project structure
- [x] Configuration management (`config.json`)

## ✅ v1.1 — GUI *(Complete)*

- [x] VisionMoCap Studio GUI (CustomTkinter)
- [x] Real-time confidence, FPS, and recording info display
- [x] Status bar with system state feedback
- [x] Settings panel for cameras and detection parameters
- [x] Theme switching (light/dark)

## ✅ v1.2 — Motion Recording *(Complete)*

- [x] Recording session with pause/resume/discard/save
- [x] JSON export with landmarks, confidence, FPS, metadata
- [x] Thread-safe recording in camera worker loop

## ✅ v1.3 — Playback *(Complete)*

- [x] Load recorded JSON sessions from disk
- [x] Timeline scrubber with play/pause/stop/step controls
- [x] Skeleton overlay rendered during playback
- [x] 46 playback unit tests

## ✅ v1.4 — Motion Filters *(Complete)*

- [x] Moving average filter for sliding-window smoothing
- [x] Exponential smoothing filter for real-time noise reduction
- [x] Outlier removal filter for anomalous frame detection
- [x] One-Euro filter for adaptive jitter reduction
- [x] Savitzky–Golay smoothing via polynomial fitting
- [x] Configurable filter parameters in GUI (FilterDialog)

## ✅ v1.5 — Blender Integration *(Complete)*

- [x] Blender add-on for importing VisionMoCap BVH exports
- [x] Automated rig mapping for Mixamo / Rigify
- [x] One-click animation bake in Blender

## ✅ v1.6 — BVH Export *(Complete)*

- [x] Convert recorded landmarks to BVH skeleton hierarchy
- [x] BVH joint rotation computation
- [x] Export with configurable frame rate

## ✅ v1.7 — Export Formats *(Complete)*

- [x] JSON export with full metadata
- [x] CSV export with per-frame landmark columns
- [x] NumPy binary (.npy) export
- [x] BVH animation export
- [x] Animation data structures for future pipeline integration

## 🟡 v1.8 — Performance Optimization *(In Progress)*

- [ ] Frame processing profiling and benchmarks
- [ ] GPU acceleration (CUDA/OpenCL) for pose estimation
- [ ] Reduced memory footprint during long recordings

## ✅ v1.9 — Documentation *(Partial)*

- [x] Project structure and architecture docs
- [x] VISIONMOCAP_BIBLE.md — comprehensive engineering reference
- [x] API reference (in-code docstrings)
- [ ] User guide and installation walkthrough
- [ ] Video tutorial series

## ✅ v2.0 — Retargeting System *(Complete)*

- [x] SkeletonMapper for mapping between skeleton definitions
- [x] Retargeter class with 4 built-in presets

## ⚪ v2.1 — Final Presentation *(Planned)*

- [ ] Polished demo with sample recordings
- [ ] Presentation slides and figures
- [ ] Formal report with chapters and references

---

*Legend: ✅ Done · ⚪ Planned*
