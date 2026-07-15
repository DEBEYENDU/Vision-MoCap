# Chapter 6: Export Pipeline

## 6.1 Architecture

The export pipeline converts a captured `MotionSequence` to animation
files through a two-stage process:

1. **Retargeting** — `Retargeter.retarget(sequence)` converts raw
   landmarks to a `RetargetedMotion` with bone-relative transforms.
2. **Conversion** — `AnimationEngine.convert(motion)` produces an
   `AnimationClip` with interpolated keyframes.

## 6.2 Retargeting

The `SkeletonMapper` maps MediaPipe landmark indices to bone names
using configurable presets: Mixamo, Blender, VRM, and Ready Player Me.
Each preset maps bone names to (head_landmark, tail_landmark) pairs.

The `Retargeter` computes bone rotations in parent space:
```
rotation = conjugate(parent_world_quat) * child_world_quat
```

## 6.3 BVH Export

The `BvhExporter` produces standard Biovision Hierarchy files with:

- 22-bone Mixamo-compatible skeleton hierarchy
- ZXY Euler rotation order (converted from quaternion)
- 6 root channels (XYZ position + ZXY rotation)
- 3 child bone channels (ZXY rotation)
- Configurable frame rate

## 6.4 CSV and NPY Export

`CsvExporter` writes a wide-format CSV with 134 columns (frame,
timestamp, 33 landmarks × 4 fields).  `NpyExporter` writes the same
layout as a NumPy binary for efficient loading in Python.

## 6.5 Format Comparison

| Format | Size (1000 frames) | Precision | Readable | Use Case |
|--------|-------------------|-----------|----------|----------|
| JSON   | ~8 MB             | Full      | Yes      | Archival |
| BVH    | ~200 KB           | Deg.      | Yes      | Animation |
| CSV    | ~5 MB             | Full      | Yes      | Analysis |
| NPY    | ~2 MB             | Full      | No       | Processing |
