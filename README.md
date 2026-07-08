# VisionMoCap AI

Markerless Motion Capture Desktop Application

## Overview

VisionMoCap AI is a production-grade desktop application that captures human body
movement using a standard webcam and animates rigged 3D characters in Blender.
The system uses computer vision and pose estimation techniques to extract skeletal
motion data in real time, processes and filters the data, and exports it to Blender
for character animation.

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

## Project Structure

```
VisionMoCap/
├── app.py                    # Application entry point
├── requirements.txt          # Python dependencies
├── README.md                 # Project documentation
├── .gitignore                # Git ignore rules
├── src/                      # Source code
│   ├── core/                 # Domain entities, interfaces, exceptions
│   ├── camera/               # Camera input abstractions
│   ├── pose/                 # Pose estimation abstractions
│   ├── motion/               # Motion processing abstractions
│   ├── animation/            # Animation export abstractions
│   ├── blender/              # Blender integration abstractions
│   ├── gui/                  # GUI application abstractions
│   ├── config/               # Configuration management
│   └── utils/                # Utility modules (logging)
├── assets/                   # Static assets
├── docs/                     # Documentation
├── logs/                     # Application logs
├── exports/                  # Exported animation files
└── tests/                    # Test suite
```

## Requirements

- Python 3.11+
- See `requirements.txt` for dependencies

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
