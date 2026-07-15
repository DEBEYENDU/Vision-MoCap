# Sample Recordings

Pre-recorded motion captures for testing and demonstrations.

| File | Description | Duration | Frames |
|------|-------------|----------|--------|
| `recording_1783577177.json` | Test recording with various poses | ~2 s | ~60 |
| `recording_1783577188.json` | Extended recording with full-body motion | ~3 s | ~90 |

## Usage

1. Launch VisionMoCap: `python app.py`
2. Click **Load** and select a `.json` file
3. Use playback controls to view the recording
4. Apply filters, export as BVH/CSV, or send to Blender

## Loading Programmatically

```python
from src.motion.motion_sequence import MotionSequence

seq = MotionSequence.from_json("recording_1783577177.json")
print(f"Loaded {seq.total_frames} frames")
```
