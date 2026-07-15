# Chapter 5: Motion Filtering

## 5.1 Overview

Raw MediaPipe landmarks contain jitter and occasional outlier frames.
VisionMoCap provides five filters via a pipeline architecture:

- **Outlier Removal** — Detects frames where landmark positions deviate
  beyond a configurable threshold and replaces them via interpolation.
- **Moving Average** — Sliding window average of landmark positions
  (configurable window size 3–15).
- **Exponential Smoothing** — Weighted average with configurable alpha
  (0.1–0.9).  Higher alpha = less smoothing.
- **One-Euro Filter** — Adaptive low-pass filter that adjusts cutoff
  frequency based on velocity.  Effective for jitter reduction without
  introducing lag.
- **Savitzky–Golay** — Polynomial least-squares fitting across a
  sliding window.  Preserves high-frequency features better than
  simple averaging.

## 5.2 Pipeline Architecture

All filters extend `SequenceProcessor` (`src/motion/base.py`) and
implement `process(sequence: MotionSequence) -> MotionSequence`.
Filters are chainable and applied in a fixed order:

```
OutlierRemoval → MovingAverage → ExponentialSmoothing → OneEuro → SavitzkyGolay
```

## 5.3 GUI Integration

The FilterDialog (`src/gui/settings_dialog.py`) provides sliders and
toggles for each filter parameter.  The "Apply" button runs the
pipeline, and "Reset" restores the original unfiltered sequence.
