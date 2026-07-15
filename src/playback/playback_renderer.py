"""Renders recorded pose data onto a displayable frame for playback.

Completely independent of the live camera pipeline.  Creates a dark
canvas matching the original recording dimensions and draws the
skeleton overlay using the existing SkeletonRenderer.
"""

from __future__ import annotations

import logging
from typing import Optional

import cv2
import numpy as np
from numpy.typing import NDArray

from src.pose.pose_result import PoseResult
from src.pose.skeleton_renderer import SkeletonRenderer


_DEFAULT_BG: tuple[int, int, int] = (30, 30, 30)  # dark grey
_WATERMARK_TEXT: str = "PLAYBACK"
_WATERMARK_COLOR: tuple[int, int, int] = (100, 100, 100)


class PlaybackRenderer:
    """Creates displayable BGR frames from PoseResult data.

    Uses the project's existing SkeletonRenderer to draw the skeleton
    onto a blank canvas sized to match the recording's frame dimensions.

    Attributes:
        skeleton_renderer: Shared renderer for drawing skeleton overlays.
    """

    def __init__(self, skeleton_renderer: Optional[SkeletonRenderer] = None) -> None:
        self._logger = logging.getLogger(self.__class__.__name__)
        self._skeleton_renderer = skeleton_renderer or SkeletonRenderer(
            draw_landmarks=True,
            draw_connections=True,
            draw_joint_ids=False,
            draw_confidence=False,
        )

    @property
    def skeleton_renderer(self) -> SkeletonRenderer:
        return self._skeleton_renderer

    def render_frame(self, pose_result: PoseResult) -> Optional[NDArray[np.uint8]]:
        """Create a BGR frame showing the skeleton for *pose_result*.

        Produces a dark canvas sized to the recording's original
        frame dimensions and draws the skeleton overlay on it.

        Args:
            pose_result: Pose data to visualise.

        Returns:
            A BGR numpy array ready for display, or None if the pose
            result has invalid dimensions.
        """
        w = pose_result.frame_width
        h = pose_result.frame_height
        if w < 1 or h < 1:
            self._logger.debug(
                "Skipping render — invalid frame dimensions %dx%d.", w, h
            )
            return None

        canvas = np.full((h, w, 3), _DEFAULT_BG, dtype=np.uint8)
        canvas = self._skeleton_renderer.render(canvas, pose_result)

        cv2.putText(
            canvas,
            _WATERMARK_TEXT,
            (12, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            _WATERMARK_COLOR,
            1,
            cv2.LINE_AA,
        )

        return canvas
