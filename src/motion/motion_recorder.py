"""Motion recording subsystem for the VisionMoCap application.

Accumulates PoseResult objects during a recording session and produces
a serialisable MotionSequence when recording stops.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import List, Optional

from src.motion.motion_sequence import MotionSequence
from src.pose.pose_result import PoseResult


class MotionRecorder:
    """Records pose detections into a time-bounded MotionSequence.

    Start a session with :meth:`start`, feed PoseResult objects with
    :meth:`record` (no-ops when not recording), then call :meth:`stop`
    to receive a populated MotionSequence.

    The recorder is a stateless accumulator — it holds no reference to
    any camera or detector.
    """

    def __init__(self) -> None:
        self._buffer: List[PoseResult] = []
        self._start_time: float = 0.0
        self._is_recording: bool = False
        self._logger = logging.getLogger(self.__class__.__name__)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Begin a new recording session.

        Any previously accumulated data is discarded.
        """
        self._buffer.clear()
        self._start_time = time.perf_counter()
        self._is_recording = True
        self._logger.info("Recording started.")

    def record(self, pose_result: PoseResult) -> None:
        """Record a single pose result if a session is active.

        This is a no-op when the recorder is not recording, making it
        safe to call on every frame without checking state first.

        Args:
            pose_result: The pose detection result to accumulate.
        """
        if not self._is_recording:
            return
        self._buffer.append(pose_result)

    def stop(self) -> Optional[MotionSequence]:
        """Stop the recording session and produce a MotionSequence.

        Returns:
            A MotionSequence containing all recorded pose data, or None
            if no frames were recorded.
        """
        if not self._is_recording:
            self._logger.warning("stop() called but no session was active.")
            return None
        self._is_recording = False
        end_time = time.perf_counter()
        duration = end_time - self._start_time
        total_frames = len(self._buffer)
        average_fps = total_frames / duration if duration > 0.0 else 0.0
        self._logger.info(
            "Recording stopped: %d frames over %.2f s (%.1f FPS).",
            total_frames,
            duration,
            average_fps,
        )
        if total_frames == 0:
            self._logger.warning("Recording has zero frames.")
            return None
        return MotionSequence(
            pose_results=list(self._buffer),
            start_time=self._start_time,
            end_time=end_time,
            total_frames=total_frames,
            average_fps=average_fps,
            duration=duration,
        )

    def cancel(self) -> None:
        """Discard the current recording without producing a sequence."""
        if self._is_recording:
            self._is_recording = False
            self._buffer.clear()
            self._logger.info("Recording cancelled.")

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_recording(self) -> bool:
        """Whether a recording session is currently active."""
        return self._is_recording

    @property
    def recorded_frame_count(self) -> int:
        """Number of frames accumulated in the current session."""
        return len(self._buffer)
