# VisionMoCap User Guide

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Quick Start](#quick-start)
5. [Recording Motion](#recording-motion)
6. [Playback](#playback)
7. [Motion Filters](#motion-filters)
8. [Creating an Animation](#creating-an-animation)
9. [Exporting](#exporting)
10. [Blender Integration](#blender-integration)
11. [Troubleshooting](#troubleshooting)

---

## Overview

VisionMoCap is a markerless motion capture application that uses
MediaPipe Pose Landmarker to track 33 body landmarks in real time
from a standard webcam.  Recorded motion can be played back,
filtered, and exported to multiple formats including BVH, CSV, and
NumPy, or sent directly to Blender for animation.

**Key features:**
- Real-time pose detection at up to 30 FPS
- Recording with pause/resume/discard
- Full playback with timeline scrubbing and frame stepping
- 5 configurable motion filters (Moving Average, Exponential
  Smoothing, Outlier Removal, One-Euro, Savitzky–Golay)
- Export: JSON, BVH, CSV, NumPy (.npy)
- Blender add-on for one-click animation import and rig mapping
- GPU delegate support for faster inference

---

## Installation

### Requirements

- **Python** 3.12 or later
- **Operating System:** Windows 10/11, Linux, macOS
- **Webcam** (built-in or USB)

### Steps

1. **Clone the repository:**

   ```bash
   git clone https://github.com/DEBEYENDU/Vision-MoCap.git
   cd Vision-MoCap
   ```

2. **Create a virtual environment (recommended):**

   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Copy the default configuration:**

   ```bash
   # config.json is gitignored — copy the template:
   cp config.json.example config.json
   ```

5. **Run the application:**

   ```bash
   python app.py
   ```

> **Note:** The first launch downloads the pose model automatically
> (~10 MB).  An internet connection is required.

---

## Configuration

Settings are stored in `config.json` at the project root.  Key
sections:

### Camera

```json
{
  "camera": {
    "device_id": 0,
    "width": 640,
    "height": 480,
    "fps": 30.0,
    "resolution_preset": "640x480",
    "backend": "directshow"
  }
}
```

- `device_id`: Camera index (0 = default webcam).
- `width`/`height`: Capture resolution (lower = faster).
- `backend`: Platform-specific — ``directshow`` (Windows),
  ``avfoundation`` (macOS), ``v4l2`` (Linux).

### Pose

```json
{
  "pose": {
    "model_complexity": 1,
    "min_detection_confidence": 0.5,
    "min_tracking_confidence": 0.5,
    "delegate": "cpu"
  }
}
```

- `model_complexity`: 0 (lite, fastest), 1 (full, balanced), 2
  (heavy, most accurate).
- `delegate`: ``"cpu"``, ``"gpu"``, or ``"xnnpack"``.  GPU
  acceleration requires a compatible graphics card.

---

## Quick Start

1. Launch the app: `python app.py`
2. Click **Start Camera** — your webcam feed appears.
3. Strike a pose — the skeleton overlay tracks your movement.
4. Click the red **Record** button to start capturing.
5. Click **Stop** to save the recording.
6. Click **Load** to open the recording, then **Create Animation**
   to turn it into a character animation, and **Export** to save it
   as BVH/CSV/NumPy or send it to Blender.

> **Tip:** No camera handy? Load a demo recording from
> `demo/sample_recordings/` and follow the playback steps below.

---

## Recording Motion

### Basic Recording

1. Ensure the camera is running and a pose is detected (skeleton
   overlay visible).
2. Click the **Record** button (circular, turns red when active).
3. Perform your motion.
4. Click **Stop** (square button) to end the session.
5. The recording is saved automatically to `exports/recordings/`.

### Pause and Resume

- Click **Pause** during recording to temporarily halt frame
  accumulation.
- Click **Resume** to continue adding frames to the same session.
- Paused time is excluded from the recording duration.

### Discard

- Click **Discard** to throw away the current session without saving.

### Frame Subsampling

To reduce memory usage during long recordings, set
`frame_subsample` in `config.json`:

```json
{
  "motion": {
    "frame_subsample": 2
  }
}
```

A value of 2 stores every other frame, halving memory usage.
Default is 1 (store every frame).

---

## Playback

1. Click **Load** and select a ``.json`` recording file.
2. Use the playback controls:
   - **Play / Pause** — start and pause playback.
   - **Stop** — reset to the first frame.
   - **Step Forward / Backward** — one frame at a time.
3. Drag the **timeline scrubber** to jump to any point.
4. Adjust **speed** with the slider (0.5× – 3.0×).

The skeleton overlay is rendered during playback just like live
mode.

---

## Motion Filters

Filters smooth out jitter and remove outlier frames.  Apply them
from the **Filters** dialog (toolbar button) after loading a
recording.

| Filter | Purpose | Key Parameter |
|--------|---------|---------------|
| Moving Average | Sliding-window smoothing | Window size (3–15) |
| Exponential Smoothing | Real-time noise reduction | Alpha (0.1–0.9) |
| Outlier Removal | Detect and replace anomalous frames | Threshold (0.05–0.5) |
| One-Euro Filter | Adaptive jitter reduction | Min cutoff, Beta |
| Savitzky–Golay | Polynomial smoothing | Window length, Poly order |

Filters can be enabled/disabled independently and are applied in
sequence.  Use **Reset** to restore the original unfiltered
sequence.

---

## Creating an Animation

A recording is raw landmark data; **Create Animation** converts it
into a character animation (`AnimationClip`) that can be exported
and driven onto a rigged figure.

1. Load a recording (or record one).
2. Click **Create Animation** in the toolbar.  The button label
   changes to **Recreate Animation** once a clip exists.
3. If the recording is not suitable (e.g. no usable poses), the app
   shows an error dialog explaining why — nothing is exported.
4. Export the clip with the **Export** button (BVH) or send it to
   Blender directly.

The conversion runs: landmark validation → retargeting to a
Mixamo-compatible skeleton → keyframe animation.  The result is
cached, so exporting twice reuses the same clip unless the loaded
recording changes.

---

## Exporting

Load a recording first, then click **Export**.  The file dialog
offers these formats:

| Format | Extension | Description |
|--------|-----------|-------------|
| JSON | ``.json`` | Raw recording with full metadata |
| BVH | ``.bvh`` | Biovision Hierarchy animation file |
| CSV | ``.csv`` | Wide-format landmarks (frame × 134 columns) |
| NumPy | ``.npy`` | Binary numpy array (same layout as CSV) |

### BVH Export Details

The BVH exporter uses a Mixamo-compatible skeleton (22 bones) with
Euler rotations in ZXY order.  The skeleton hierarchy is:

```
Hips → Spine → Spine1 → Spine2 → Neck → Head
     → LeftUpLeg → LeftLeg → LeftFoot → LeftToeBase
     → RightUpLeg → RightLeg → RightFoot → RightToeBase
     → LeftShoulder → LeftUpperArm → LeftForearm → LeftHand
     → RightShoulder → RightUpperArm → RightForearm → RightHand
```

The root bone has 6 channels (X/Y/Z position + Z/X/Y rotation).
Child bones have 3 channels (Z/X/Y rotation).

---

## Blender Integration

### Install the Add-on

1. Package the add-on:
   ```bash
   python scripts/package_blender_addon.py
   ```
   This creates `visionmocap_addon.zip` in the project root.

2. In Blender, go to **Edit → Preferences → Add-ons**.
3. Click **Install…** and select the ``.zip`` file.
4. Enable **"VisionMoCap — Motion Capture Importer"**.

### Usage

1. In Blender, open the **3D Viewport** and press **N** to show the
   sidebar.
2. Find the **VisionMoCap** tab.
3. Click **Import BVH…** and select your exported ``.bvh`` file.
4. Choose a **Target Rig**:
   - **Mixamo** — bone names match the Mixamo convention.
   - **Rigify** — maps to Rigify Meta-Rig bone names.
   - **None** — keeps the original BVH armature.
5. Enable **Auto-Bake** to automatically bake the animation to
   keyframes.

### Sending from VisionMoCap

With a recording loaded, click **Create Animation** first, then the
**Blender** button in the toolbar.  The app exports a temporary BVH
file.  If ``auto_launch`` is enabled in ``config.json``, Blender
starts with the add-on pre-loaded.

```json
{
  "blender": {
    "blender_executable": "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe",
    "auto_launch": true
  }
}
```

> ``blender_executable`` must be the full path to the Blender
> executable — a bare ``"blender"`` only works if Blender is on your
> system PATH.  Tested with Blender 4.2+ and Blender 5.1.

---

## Troubleshooting

### Camera not found

- Check `device_id` in `config.json` (try 0, 1, 2…).
- On Windows, ensure the camera is not in use by another
  application.
- Try setting `"backend": "dshow"` explicitly.

### Low frame rate

- Reduce capture resolution (`width`/`height` in config).
- Set `model_complexity` to 0 (lite model).
- Enable GPU delegate: `"delegate": "gpu"`.
- Close other GPU-intensive applications.

### Pose not detected

- Ensure adequate lighting (avoid strong backlight).
- Stand at least 1–2 meters from the camera.
- The full body should be visible in the frame.
- Lower `min_detection_confidence` if necessary.

### Blender add-on not working

- Ensure the add-on is enabled (check the checkbox).
- Blender 4.2+ is required.
- For Rigify mapping, generate the Rigify rig first, then import
  the BVH and select "Rigify" as the target.

### Export fails

- Ensure a playback sequence is loaded before exporting BVH/CSV/NPY.
- Check that the output directory is writable.
- For BVH, the sequence must have at least one frame.
