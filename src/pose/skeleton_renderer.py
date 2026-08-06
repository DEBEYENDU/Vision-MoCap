"""Skeleton rendering module for the VisionMoCap application.

Draws skeletal overlays on video frames from PoseResult data.
This module performs no inference — only visualisation.
"""

from __future__ import annotations

from typing import List, Tuple

import cv2
import numpy as np
from numpy.typing import NDArray

from src.pose.pose_result import Landmark, PoseResult

# MediaPipe Pose landmark connections (index pairs).
POSE_CONNECTIONS: List[Tuple[int, int]] = [
    (0, 1), (1, 2), (2, 3), (3, 7),
    (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10),
    (11, 12),
    (11, 13), (13, 15),
    (12, 14), (14, 16),
    (11, 23), (12, 24),
    (23, 24),
    (23, 25), (25, 27),
    (24, 26), (26, 28),
    (27, 29), (29, 31),
    (28, 30), (30, 32),
    (27, 31), (28, 32),
]

# Left/right colour groups for skeleton visualisation.
_COLOR_LEFT = (255, 180, 50)    # BGR — teal/orange
_COLOR_RIGHT = (50, 180, 255)
_COLOR_TORSO = (200, 200, 200)
_COLOR_FACE = (220, 220, 220)
_COLOR_LANDMARK = (0, 255, 0)
_COLOR_TEXT = (255, 255, 255)

# Maps each connection to a colour based on its body region.
# Torso connections (both landmarks in torso set) are checked FIRST
# so they are not overridden by left/right arm/leg checks.
_TORSO_SET = {11, 12, 23, 24}
_CONNECTION_COLORS: List[Tuple[int, int, int]] = []
for a, b in POSE_CONNECTIONS:
    if a in _TORSO_SET and b in _TORSO_SET:
        _CONNECTION_COLORS.append(_COLOR_TORSO)
    elif a in {11, 13, 15, 17, 19, 21} or b in {11, 13, 15, 17, 19, 21}:
        _CONNECTION_COLORS.append(_COLOR_LEFT)
    elif a in {12, 14, 16, 18, 20, 22} or b in {12, 14, 16, 18, 20, 22}:
        _CONNECTION_COLORS.append(_COLOR_RIGHT)
    elif a in {23, 25, 27, 29, 31} or b in {23, 25, 27, 29, 31}:
        _CONNECTION_COLORS.append(_COLOR_LEFT)
    elif a in {24, 26, 28, 30, 32} or b in {24, 26, 28, 30, 32}:
        _CONNECTION_COLORS.append(_COLOR_RIGHT)
    else:
        _CONNECTION_COLORS.append(_COLOR_FACE)


class SkeletonRenderer:
    """Renders skeleton overlays on video frames from PoseResult data.

    Responsibilities:
      - Drawing landmark connections (bones).
      - Drawing landmark keypoints.
      - Drawing landmark index labels.
      - Optionally drawing confidence values.

    The renderer performs **no inference** — it only draws.
    """

    def __init__(
        self,
        draw_landmarks: bool = True,
        draw_connections: bool = True,
        draw_joint_ids: bool = False,
        draw_confidence: bool = False,
    ) -> None:
        self._draw_landmarks = draw_landmarks
        self._draw_connections_flag = draw_connections
        self._draw_joint_ids = draw_joint_ids
        self._draw_confidence = draw_confidence

    def render(
        self, frame: NDArray[np.uint8], pose_result: PoseResult
    ) -> NDArray[np.uint8]:
        """Draw the full skeleton overlay on *frame* from *pose_result*.

        Args:
            frame: Original BGR frame (will be drawn on in-place).
            pose_result: Pose data to visualise.

        Returns:
            The annotated frame (same object as *frame*).
        """
        if not pose_result.pose_detected or not pose_result.landmarks:
            return frame

        landmarks = pose_result.landmarks
        h, w = pose_result.frame_height, pose_result.frame_width

        if self._draw_connections_flag:
            self._draw_pose_connections(frame, landmarks, w, h)
        if self._draw_landmarks:
            self._draw_pose_landmarks(frame, landmarks, w, h)
        if self._draw_joint_ids:
            self._draw_joint_labels(frame, landmarks, w, h)
        if self._draw_confidence:
            self._draw_confidence_labels(frame, landmarks, w, h)

        return frame

    # ------------------------------------------------------------------
    # Drawing helpers
    # ------------------------------------------------------------------

    def _draw_pose_connections(
        self,
        frame: NDArray[np.uint8],
        landmarks: List[Landmark],
        w: int,
        h: int,
    ) -> None:
        """Draw coloured lines between connected landmarks."""
        for (a, b), color in zip(POSE_CONNECTIONS, _CONNECTION_COLORS):
            if a >= len(landmarks) or b >= len(landmarks):
                continue
            lm_a = landmarks[a]
            lm_b = landmarks[b]
            if lm_a.visibility < 0.5 or lm_b.visibility < 0.5:
                continue
            x1, y1 = int(lm_a.x * w), int(lm_a.y * h)
            x2, y2 = int(lm_b.x * w), int(lm_b.y * h)
            cv2.line(frame, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)

    def _draw_pose_landmarks(
        self,
        frame: NDArray[np.uint8],
        landmarks: List[Landmark],
        w: int,
        h: int,
    ) -> None:
        """Draw filled circles at each landmark position."""
        for lm in landmarks:
            if lm.visibility < 0.5:
                continue
            cx, cy = int(lm.x * w), int(lm.y * h)
            cv2.circle(frame, (cx, cy), 4, _COLOR_LANDMARK, -1, cv2.LINE_AA)

    def _draw_joint_labels(
        self,
        frame: NDArray[np.uint8],
        landmarks: List[Landmark],
        w: int,
        h: int,
    ) -> None:
        """Draw the landmark index number above each keypoint."""
        for i, lm in enumerate(landmarks):
            if lm.visibility < 0.5:
                continue
            cx, cy = int(lm.x * w), int(lm.y * h)
            cv2.putText(
                frame,
                str(i),
                (cx + 6, cy - 6),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                _COLOR_TEXT,
                1,
                cv2.LINE_AA,
            )

    def _draw_confidence_labels(
        self,
        frame: NDArray[np.uint8],
        landmarks: List[Landmark],
        w: int,
        h: int,
    ) -> None:
        """Draw the visibility value beside each landmark."""
        for i, lm in enumerate(landmarks):
            if lm.visibility < 0.5:
                continue
            cx, cy = int(lm.x * w), int(lm.y * h)
            label = f"{lm.visibility:.2f}"
            cv2.putText(
                frame,
                label,
                (cx + 6, cy + 12),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.35,
                _COLOR_TEXT,
                1,
                cv2.LINE_AA,
            )
