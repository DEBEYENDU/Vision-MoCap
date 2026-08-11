"""Motion recording subsystem for the VisionMoCap application.

Accumulates PoseResult objects during a recording session and produces
a serialisable MotionSequence when recording stops.  Supports pause,
resume, and discard in addition to the basic start/stop lifecycle.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import List, Optional

from src.motion.motion_sequence import (
    MotionSequence,
    fps_from_timestamps,
)
from src.pose.pose_result import PoseResult


class MotionRecorder:
    """Records pose detections into a time-bounded MotionSequence.

    Start a session with :meth:`start`, feed PoseResult objects with
    :meth:`record` (no-ops when not recording), then call :meth:`stop`
    to receive a populated MotionSequence.

    Pause and resume allow the operator to temporarily halt frame
    accumulation without losing the session.  ``elapsed_time`` tracks
    the wall-clock duration excluding pauses.

    The recorder is a stateless accumulator — it holds no reference to
    any camera or detector.
    """

    def __init__(self, subsample: int = 1) -> None:
        self._subsample = max(1, subsample)
        self._buffer: List[PoseResult] = []
        self._frame_counter: int = 0
        self._start_time: float = 0.0
        self._is_recording: bool = False
        self._paused: bool = False
        self._pause_start: float = 0.0
        self._total_paused: float = 0.0
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
        self._total_paused = 0.0
        self._paused = False
        self._is_recording = True
        self._logger.info("Recording started.")

    def record(self, pose_result: PoseResult) -> None:
        """Record a single pose result if a session is active.

        When *subsample* > 1, only every Nth frame is stored, reducing
        memory usage during long recordings.

        This is a no-op when the recorder is not recording or is
        paused, making it safe to call on every frame without
        checking state first.

        Args:
            pose_result: The pose detection result to accumulate.
        """
        if not self._is_recording or self._paused:
            return
        self._frame_counter += 1
        if self._frame_counter % self._subsample != 0:
            return
        self._buffer.append(pose_result)

    def pause(self) -> None:
        """Pause frame accumulation.

        No-op if not currently recording or already paused.
        """
        if not self._is_recording or self._paused:
            return
        self._paused = True
        self._pause_start = time.perf_counter()
        self._logger.info("Recording paused.")

    def resume(self) -> None:
        """Resume frame accumulation after a pause.

        No-op if not paused.
        """
        if not self._paused:
            return
        self._total_paused += time.perf_counter() - self._pause_start
        self._paused = False
        self._pause_start = 0.0
        self._logger.info("Recording resumed.")

    def stop(self) -> Optional[MotionSequence]:
        """Stop the recording session and produce a MotionSequence.

        Returns:
            A MotionSequence containing all recorded pose data, or None
            if no frames were recorded.
        """
        if not self._is_recording:
            self._logger.warning("stop() called but no session was active.")
            return None
        if self._paused:
            self._total_paused += time.perf_counter() - self._pause_start
            self._paused = False
        self._is_recording = False
        end_time = time.perf_counter()
        duration = end_time - self._start_time - self._total_paused
        total_frames = len(self._buffer)
        average_fps = fps_from_timestamps(
            [pr.timestamp for pr in self._buffer]
        )
        if average_fps is None:
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
            self._paused = False
            self._buffer.clear()
            self._logger.info("Recording cancelled.")

    def discard(self) -> None:
        """Alias for :meth:`cancel` with clearer intent."""
        self.cancel()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_recording(self) -> bool:
        """Whether a recording session is currently active."""
        return self._is_recording

    @property
    def is_paused(self) -> bool:
        """Whether the recording session is paused."""
        return self._paused

    @property
    def recorded_frame_count(self) -> int:
        """Number of frames accumulated in the current session."""
        return len(self._buffer)

    @property
    def elapsed_time(self) -> float:
        """Wall-clock recording duration excluding pauses (seconds).

        Returns 0.0 if no session is active.
        """
        if not self._is_recording and not self._paused:
            return 0.0
        elapsed = time.perf_counter() - self._start_time - self._total_paused
        if self._paused:
            elapsed -= time.perf_counter() - self._pause_start
        return max(elapsed, 0.0)
