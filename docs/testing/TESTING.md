# Testing

## Running the Tests

The unit suite is headless and needs no camera or display:

```
python -m pytest tests/unit -q
```

Expected: all tests pass (~240 tests). The suite covers the pose,
motion, recording, playback (including loop playback), animation,
export, Blender bridge, camera manager (OpenCV mocked), and error-path
wrapping.

## GUI Smoke Tests

The GUI cannot be exercised by pytest headlessly, so a scripted smoke
test drives the real CustomTkinter toolbar:

```
PYTHONPATH="C:/Users/GOD KAKAROT/VisionMoCap" ^
  python tests/integration/_toolbar_smoke.py
```

It creates the Toolbar, simulates clicks (camera menu, start/stop,
record, load, settings, exit), verifies all 18 buttons exist, checks
the scrollbar appears in narrow viewports, and confirms the loop and
playback state changes. `conftest.py` excludes it from pytest
collection because it opens a Tk root.

## Testing New Code

- **Unit tests**: one `tests/unit/test_<subsystem>.py` per subsystem.
- **Mocks**: OpenCV is mocked at the module level
  (`tests/unit/test_camera_manager.py`) with a `FakeCv2`/`FakeCapture`
  so camera logic is testable without hardware. `subprocess.Popen` is
  mocked in the Blender bridge tests.
- **Error paths**: always test the failure branch (unwritable paths,
  missing executables, empty sequences) as well as the happy path.

## Benchmarks

`scripts/benchmark_pipeline.py` measures the CPU-side pipeline on
synthetic data (no camera required):

```
python scripts/benchmark_pipeline.py --frames 2000
```

MediaPipe inference is benchmarked automatically when a model file is
present; otherwise that row is reported as skipped.
