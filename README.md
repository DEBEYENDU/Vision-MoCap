# VisionMoCap AI

Markerless Motion Capture Desktop Application

## Project Overview

VisionMoCap AI is a production-grade desktop application that captures human body
movement using a standard webcam and animates rigged 3D characters in Blender.
The system uses computer vision and pose estimation techniques to extract skeletal
motion data in real time, processes and filters the data, and exports it to Blender
for character animation.

## Features

- **Real-time Pose Detection** — 33-landmark skeleton tracking via MediaPipe Pose
- **Live Camera Feed** — Webcam support with skeleton overlay rendering
- **Motion Recording** — Professional recording system with pause, resume, discard, and save
- **Session Management** — Per-session metadata (FPS, confidence, duration, frame count)
- **JSON Export** — Full landmark data export with frame-by-frame fidelity
- **Desktop GUI** — CustomTkinter-based VisionMoCap Studio (light/dark theme)
- **Blender Integration** — Ready for rig mapping and animation bake
- **Clean Architecture** — Domain-driven, testable, and maintainable codebase

## Tech Stack

| Component         | Technology                                          |
|-------------------|-----------------------------------------------------|
| Language          | Python 3.12+                                        |
| GUI Framework     | CustomTkinter (Tkinter wrapper)                     |
| Pose Estimation   | MediaPipe Pose (mp_pose)                            |
| Camera            | OpenCV (cv2)                                        |
| Testing           | Pytest                                              |
| Architecture      | Clean Architecture / Domain-Driven Design           |
| Logging           | Python `logging` module                             |

## Architecture

The application follows **Clean Architecture** principles, ensuring separation of
concerns, testability, and maintainability.

### Layers

| Layer              | Package                 | Responsibility                                    |
|--------------------|-------------------------|---------------------------------------------------|
| **Domain**         | `src/core/`             | Enterprise business rules, domain entities, interfaces |
| **Application**    | `src/motion/`, `src/animation/` | Motion processing and animation export use cases |
| **Interface Adapters** | `src/camera/`, `src/pose/`, `src/blender/`, `src/gui/` | Adapters connecting domain logic to external systems |
| **Infrastructure** | `src/config/`, `src/utils/` | Configuration management and logging             |

### Data Flow

```
Webcam -> Camera Adapter -> Pose Estimator -> Motion Processor -> Animation Exporter -> Blender
         (src/camera/)      (src/pose/)       (src/motion/)      (src/animation/)      (src/blender/)
```

### Dependency Rule

Dependencies point inward. `src/core/` has no dependencies on other packages.
`src/config/` depends only on `src/core/`. All modules depend on `src/config/`
and `src/core/`.

## Installation

```bash
git clone https://github.com/your-org/VisionMoCap.git
cd VisionMoCap

python -m venv .venv

# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

## Usage

```bash
python app.py
```

## Project Structure

```
VisionMoCap/
├── app.py                     # Application entry point
├── requirements.txt           # Python dependencies
├── README.md                  # Project documentation
├── ROADMAP.md                 # Development roadmap
├── CONTRIBUTING.md            # Contribution guidelines
├── CHANGELOG.md               # Version history
├── .gitignore                 # Git ignore rules
├── src/                       # Source code
│   ├── core/                  # Domain entities, interfaces, exceptions
│   ├── camera/                # Camera input abstractions
│   ├── pose/                  # Pose estimation abstractions
│   ├── motion/                # Motion processing / recording abstractions
│   ├── animation/             # Animation export abstractions
│   ├── blender/               # Blender integration abstractions
│   ├── gui/                   # GUI application abstractions
│   ├── recording/             # Recording session management
│   ├── config/                # Configuration management
│   └── utils/                 # Utility modules (logging)
├── assets/                    # Static resources (icons, logos, models, fonts, shaders, textures)
├── screenshots/               # Application screenshots (gui, pose_detection, blender, exports, development)
├── demo/                      # Demo assets (videos, gifs, sample_recordings, sample_exports)
├── docs/                      # Documentation (architecture, diagrams, api, setup, research, images)
├── presentation/              # Presentation materials (slides, figures, videos)
├── report/                    # Formal reports (chapters, images, references, plagiarism)
├── exports/                   # Exported animation files (json, bvh, fbx, gltf, recordings)
├── tests/                     # Test suite (unit, integration, performance, test_data)
├── scripts/                   # Utility scripts
├── tools/                     # Standalone helper tools
├── config/                    # Configuration files
├── logs/                      # Application logs
└── temp/                      # Temporary files
```

## Roadmap

See [ROADMAP.md](ROADMAP.md) for planned milestones and feature tracking.

## Screenshots

> *(Screenshots to be added. See `screenshots/` directory.)*

## Demo

> *(Demo assets to be added. See `demo/` directory.)*

## Development

### Code Style

- PEP 8 conventions
- Type hints throughout
- Google-style docstrings
- Clean Architecture with dependency inversion
- Comprehensive logging and error handling

### Testing

```bash
pytest tests/
```

## License

Proprietary. All rights reserved.
