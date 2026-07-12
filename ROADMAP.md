# Roadmap

VisionMoCap development milestones and future plans.

---

## v1.0 — Pose Detection ✅ *(Current)*

- [x] Real-time markerless pose detection using MediaPipe
- [x] Webcam support with device selection
- [x] 33-landmark skeleton overlay rendering
- [x] Clean Architecture project structure
- [x] Configuration management (`config.json`)

## v1.1 — GUI

- [x] VisionMoCap Studio GUI (CustomTkinter)
- [ ] Settings panel for cameras and detection parameters
- [ ] Real-time confidence and FPS display
- [ ] Theme switching (light/dark)

## v1.2 — Motion Recording

- [x] Recording session with pause/resume/discard/save
- [x] JSON export with landmarks, confidence, FPS, metadata
- [x] Thread-safe recording in camera worker loop

## v1.3 — Playback

- [ ] Load recorded JSON sessions from disk
- [ ] Timeline scrubber and playback controls
- [ ] Overlay skeleton on playback viewer

## v1.4 — Motion Smoothing

- [ ] One-Euro filter for jitter reduction
- [ ] Savitzky–Golay smoothing option
- [ ] Configurable filter parameters in GUI

## v1.5 — Blender Integration

- [ ] Blender add-on for importing VisionMoCap exports
- [ ] Automated rig mapping for Mixamo / Rigify
- [ ] One-click animation bake in Blender

## v1.6 — BVH Export

- [ ] Convert recorded landmarks to BVH skeleton hierarchy
- [ ] BVH joint rotation computation
- [ ] Export with configurable frame rate

## v1.7 — JSON Export

- [x] JSON export with full metadata (done in v1.2)
- [ ] Additional export formats (CSV, NPY)

## v1.8 — Performance Optimization

- [ ] Frame processing profiling and benchmarks
- [ ] GPU acceleration (CUDA/OpenCL) for pose estimation
- [ ] Reduced memory footprint during long recordings

## v1.9 — Documentation

- [x] Project structure and architecture docs
- [x] API reference (in-code docstrings)
- [ ] User guide and installation walkthrough
- [ ] Video tutorial series

## v2.0 — Final Presentation

- [ ] Polished demo with sample recordings
- [ ] Presentation slides and figures
- [ ] Formal report with chapters and references

---

*Legend: ✅ Done · In Progress · ❌ Not started*
