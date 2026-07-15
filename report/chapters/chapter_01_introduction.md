# Chapter 1: Introduction

## 1.1 Background

Motion capture (mocap) is the process of recording the movement of
objects or people.  Traditional optical mocap systems — such as Vicon
or OptiTrack — rely on multiple infrared cameras and reflective markers
worn by the subject.  While accurate, these systems are expensive,
require controlled environments, and involve lengthy setup times.

The rise of deep learning-based pose estimation has enabled markerless
alternatives that work from a single RGB camera.  MediaPipe Pose
Landmarker [1] by Google, OpenPose [2], and MoveNet [3] can detect 33
body landmarks in real time on consumer hardware.

## 1.2 Problem Statement

Despite the availability of pose estimation models, there is no
end-to-end, open-source toolchain that:

- Captures pose landmarks from a webcam
- Records and plays back motion data
- Filters noise and jitter from the recorded signals
- Exports to standard animation formats (BVH, CSV)
- Integrates with Blender for animation

VisionMoCap addresses this gap by providing a complete desktop
application with a clean GUI, real-time pipeline, and production-ready
export capabilities.

## 1.3 Objectives

1. **Real-time pose detection** — Run MediaPipe Pose Landmarker at
   ≥30 FPS on consumer hardware.
2. **Recording and playback** — Store detected landmarks with timing
   metadata; replay with full skeleton overlay.
3. **Motion filtering** — Apply signal-processing filters to reduce
   noise and smooth recorded motion.
4. **Multi-format export** — Support BVH (Biovision Hierarchy), CSV,
   JSON, and NumPy binary formats.
5. **Blender integration** — Provide a Blender add-on for one-click
   animation import with automatic rig mapping.
6. **Clean, extensible architecture** — Follow Clean Architecture
   principles to isolate concerns and simplify maintenance.

## 1.4 Scope

This report covers the design, implementation, and evaluation of
VisionMoCap version 1.0–2.0.  It assumes familiarity with Python,
computer vision, and basic animation concepts.

## 1.5 Report Structure

- **Chapter 2** describes the system architecture and design
  decisions.
- **Chapter 3** details the pose detection pipeline.
- **Chapter 4** covers motion recording and playback subsystems.
- **Chapter 5** presents the motion filtering framework.
- **Chapter 6** describes the export pipeline (JSON, BVH, CSV, NPY).
- **Chapter 7** documents the Blender integration.
- **Chapter 8** discusses performance and optimization.
- **Chapter 9** concludes and outlines future work.

---

**References**

[1] Google. MediaPipe Pose Landmarker.
    https://developers.google.com/mediapipe/solutions/vision/pose_landmarker

[2] Cao, Z. et al. OpenPose: Realtime Multi-Person 2D Pose Estimation
    using Part Affinity Fields. IEEE TPAMI, 2019.

[3] Google. MoveNet: Ultra fast and accurate pose detection model.
    https://www.tensorflow.org/hub/tutorials/movenet
