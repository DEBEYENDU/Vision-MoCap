# VisionMoCap Studio

**Markerless Motion Capture Desktop Application**

VisionMoCap Studio is a production-grade desktop application that captures human body movement using a standard webcam, performs real-time pose estimation via MediaPipe, records the motion data, and provides playback and export capabilities. Built with Python and CustomTkinter, it follows Clean Architecture principles for maintainability and testability.

---

## Features

### ✅ Currently Implemented

| Feature | Description |
|---------|-------------|
| **Real-time Pose Detection** | 33-landmark skeleton tracking via MediaPipe Tasks Pose Landmarker |
| **Live Camera Feed** | Webcam support with configurable backend (DirectShow, Media Foundation) |
| **Skeleton Rendering** | Colour-coded overlay with left/right/torso/face distinction and visibility filtering |
| **Settings Panel** | Tabbed dialog for camera device/resolution/backend, pose model complexity and confidence, GUI theme, and logging level |
| **Motion Recording** | Professional recording system with pause, resume, discard, and save |
| **Session Management** | Per-session metadata (FPS, confidence, duration, frame count, camera info) |
| **JSON Export** | Full landmark data export with frame-by-frame fidelity |
| **Motion Playback** | Load and replay recorded motion sequences with play, pause, resume, stop |
| **Frame Stepping** | Step forward/backward through recorded frames |
| **Timeline Scrubbing** | Drag a timeline slider to instantly jump to any frame |
| **Desktop GUI** | CustomTkinter-based VisionMoCap Studio with dark/light theme toggle |
| **Configuration** | JSON-based configuration with field-level validation |
| **Logging** | Rotating file logger with configurable level and size limits |

### 🟡 Partially Implemented

| Feature | Status |
|---------|--------|
| **Animation System** | Core data structures exist (`AnimationClip`, `Keyframe`, `Bone`, `Avatar`). No export pipeline. |
| **Blender Integration** | Abstract base class exists. No concrete implementation. |
| **Motion Smoothing** | 5 filters implemented (MovingAverage, ExponentialSmoothing, OutlierRemoval, OneEuro, SavitzkyGolay). Configurable via GUI FilterDialog with per-filter parameters. |
| **Retargeting** | `SkeletonMapper` and `Retargeter` classes exist with 4 presets. Not connected to pipeline. |

---

## Screenshots

> *(Screenshots to be added. See `screenshots/` directory.)*

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Language** | Python 3.12+ |
| **GUI Framework** | CustomTkinter 6.0 (Tkinter wrapper) |
| **Pose Estimation** | MediaPipe 0.10.35 (Tasks Pose Landmarker API) |
| **Camera** | OpenCV 5.0 (cv2) with DirectShow / Media Foundation backends |
| **Image Processing** | NumPy, Pillow 12.3 |
| **Testing** | Pytest |
| **Architecture** | Clean Architecture / Domain-Driven Design |
| **Logging** | Python `logging` module with rotating file handler |

---

## Installation

### Requirements

- Python 3.12 or later
- Webcam (built-in or USB)
- Windows (DirectShow), macOS (AVFoundation), or Linux (V4L2)

### Dependencies

```
numpy==2.5.1
opencv-python==5.0.0.93
mediapipe==0.10.35
scipy==1.18.0
customtkinter==6.0.0
Pillow==12.3.0
```

### Setup

```bash
# Clone the repository
git clone https://github.com/your-org/VisionMoCap.git
cd VisionMoCap

# Create and activate a virtual environment
python -m venv venv

# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Usage

```bash
python app.py
```

### Basic Workflow

1. **Start Camera** — Click "Start Camera" to begin the live feed
2. **Record** — Click "Record" to capture pose data; use "Pause" to pause/resume
3. **Stop Recording** — Click "Stop Recording" to save the recording as JSON
4. **Load Recording** — Click "Load Recording" to open a previously saved JSON file
5. **Playback** — Use Play, Pause, Stop, Step Forward/Backward to navigate frames
6. **Timeline** — Drag the slider to scrub through the recording
7. **Export** — Click "Export" to copy the latest recording to a chosen location

---

## Project Structure

```
VisionMoCap/
├── app.py                     # Entry point
├── config.json                # Application configuration
├── requirements.txt           # Python dependencies
│
├── src/                       # Source code
│   ├── core/                  # Domain entities, interfaces, exceptions
│   ├── config/                # Configuration management
│   ├── camera/                # Camera input abstraction
│   ├── pose/                  # Pose estimation and rendering
│   ├── motion/                # Motion processing, recording, filtering
│   ├── recording/             # Recording session management
│   ├── playback/              # Motion playback engine
│   ├── animation/             # Animation data structures
│   ├── blender/               # Blender integration stubs
│   ├── gui/                   # CustomTkinter desktop GUI
│   └── utils/                 # Logging utilities
│
├── tests/                     # Test suite
│   └── unit/
│       └── test_playback.py   # 46 playback tests
│
├── exports/                   # Exported recording JSON files
│   └── recordings/
│
├── models/                    # MediaPipe .task model files
├── logs/                      # Application logs
├── assets/                    # Static resources
├── screenshots/               # Application screenshots
├── demo/                      # Demo assets
├── docs/                      # Documentation
├── presentation/              # Presentation materials
├── report/                    # Formal reports
├── scripts/                   # Utility scripts
├── config/                    # Configuration files
├── temp/                      # Temporary files
└── tools/                     # Standalone helper tools
```

---

## Architecture Summary

The application follows **Clean Architecture** with strict dependency inversion:

```
┌─────────────────────────────────────────────────────────┐
│                      GUI (CustomTkinter)                 │
│  ┌──────────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │  MainWindow   │  │  Toolbar  │  │  StatusBar         │  │
│  └──────┬───────┘  └──────────┘  └───────────────────┘  │
│         │                                                 │
│  ┌──────▼───────┐  ┌────────────┐  ┌──────────────────┐  │
│  │ AppController │  │ InfoPanel   │  │ TimelineWidget   │  │
│  └──────┬───────┘  └────────────┘  └──────────────────┘  │
└─────────┼─────────────────────────────────────────────────┘
          │
┌─────────▼─────────────────────────────────────────────────┐
│                    Application Layer                        │
│  ┌──────────────┐  ┌───────────┐  ┌────────────────────┐  │
│  │ PlaybackCtrl  │  │ MotionRec  │  │ SessionManager     │  │
│  └──────────────┘  └───────────┘  └────────────────────┘  │
└─────────┬─────────────────────────────────────────────────┘
          │
┌─────────▼─────────────────────────────────────────────────┐
│                  Interface Adapters                         │
│  ┌──────────────┐  ┌───────────┐  ┌────────────────────┐  │
│  │ CameraManager │  │PoseDetector│  │ SkeletonRenderer   │  │
│  └──────────────┘  └───────────┘  └────────────────────┘  │
└─────────┬─────────────────────────────────────────────────┘
          │
┌─────────▼─────────────────────────────────────────────────┐
│                    Domain / Core                            │
│  ┌──────────────┐  ┌───────────┐  ┌────────────────────┐  │
│  │  Models       │  │Interfaces  │  │ Exceptions         │  │
│  └──────────────┘  └───────────┘  └────────────────────┘  │
└───────────────────────────────────────────────────────────┘
```

### Key Design Decisions

- **2-Thread Model**: GUI thread (CustomTkinter event loop) + Worker thread (camera capture → pose detection → rendering)
- **Thread-safe Communication**: `queue.Queue(maxsize=2)` for frame delivery, `queue.Queue` for error delivery, `threading.Lock` for shared state, `threading.Event` for shutdown signalling
- **Playback runs in GUI thread**: Uses timer-based advancement via the existing `after()` loop (33ms interval)
- **No busy loops**: All timing is event-driven or timer-based

---

## License

Proprietary. All rights reserved.
