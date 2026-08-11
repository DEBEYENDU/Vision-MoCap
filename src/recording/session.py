"""Single recording session model.

RecordingSession owns the raw data buffer (PoseResult list), tracks
wall-clock duration including paused intervals, and computes metadata
when stopped.  It also carries the frame_number and per-frame FPS
alongside each PoseResult via a lightweight wrapper dict.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from src.motion.motion_sequence import fps_from_timestamps
from src.pose.pose_result import PoseResult


class RecordingSession:
    """Mutable accumulator for a single recording session.

    A session begins in the **idle** state.  Call ``start()`` to enter
    the **recording** state, during which ``record_pose()`` is called
    on every frame.  The session may be **paused** and **resumed**
    arbitrarily many times.  ``stop()`` transitions to **completed**
    (irreversible).  ``discard()`` empties all data without producing
    output.

    ``elapsed_seconds`` is always the real wall-clock time elapsed
    since ``start()``, regardless of pauses — it is the live timer
    value the GUI displays.

    State machine::

        idle  →  recording  →  completed
                     ↕              ↑
                  paused  ──────────┘

    Attributes:
        camera_index: Device index this session belongs to.
        frame_rate: Nominal capture FPS (from CameraConfig).
    """

    STATE_IDLE: str = "idle"
    STATE_RECORDING: str = "recording"
    STATE_PAUSED: str = "paused"
    STATE_COMPLETED: str = "completed"

    def __init__(self, camera_index: int = -1, frame_rate: float = 30.0) -> None:
        self._logger = logging.getLogger(self.__class__.__name__)
        self._camera_index: int = camera_index
        self._frame_rate: float = frame_rate

        # Data buffer
        self._frames: List[PoseResult] = []
        self._frame_numbers: List[int] = []
        self._fps_values: List[float] = []

        # Timing state
        self._state: str = self.STATE_IDLE
        self._start_wall: float = 0.0      # monotonic clock at first start()
        self._pause_start: float = 0.0     # monotonic clock when pause() called
        self._total_paused: float = 0.0    # accumulated pause duration
        self._last_frame_time: float = 0.0

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Begin a new recording session (from idle).

        Any previously accumulated data is discarded.
        """
        self._frames.clear()
        self._frame_numbers.clear()
        self._fps_values.clear()
        self._start_wall = time.monotonic()
        self._pause_start = 0.0
        self._total_paused = 0.0
        self._last_frame_time = self._start_wall
        self._state = self.STATE_RECORDING
        self._logger.info("Recording session started.")

    def pause(self) -> None:
        """Pause recording (from recording).

        No-op if not currently recording.
        """
        if self._state != self.STATE_RECORDING:
            return
        self._pause_start = time.monotonic()
        self._state = self.STATE_PAUSED
        self._logger.info("Recording session paused.")

    def resume(self) -> None:
        """Resume recording (from paused).

        No-op if not currently paused.  The accumulated pause
        duration is added to the running total.
        """
        if self._state != self.STATE_PAUSED:
            return
        now = time.monotonic()
        self._total_paused += now - self._pause_start
        self._pause_start = 0.0
        self._last_frame_time = now
        self._state = self.STATE_RECORDING
        self._logger.info("Recording session resumed.")

    def stop(self) -> None:
        """Finish the session.  Data is retained for later export.

        No-op if in idle or completed state.
        """
        if self._state in (self.STATE_IDLE, self.STATE_COMPLETED):
            return
        if self._state == self.STATE_PAUSED:
            now = time.monotonic()
            self._total_paused += now - self._pause_start
            self._pause_start = 0.0
        self._state = self.STATE_COMPLETED
        self._logger.info(
            "Recording session completed: %d frames over %.2f wall seconds.",
            len(self._frames),
            self.elapsed_seconds,
        )

    def discard(self) -> None:
        """Discard all data and return to idle."""
        self._frames.clear()
        self._frame_numbers.clear()
        self._fps_values.clear()
        self._start_wall = 0.0
        self._total_paused = 0.0
        self._pause_start = 0.0
        self._state = self.STATE_IDLE
        self._logger.info("Recording session discarded.")

    # ------------------------------------------------------------------
    # Data accumulation
    # ------------------------------------------------------------------

    def record_pose(
        self,
        pose: PoseResult,
        frame_number: int,
        current_fps: float,
    ) -> None:
        """Accumulate one frame's pose data if the session is active.

        Args:
            pose: The PoseResult to store.
            frame_number: Monotonically increasing frame counter.
            current_fps: Instantaneous FPS for this frame.
        """
        if self._state != self.STATE_RECORDING:
            return
        self._frames.append(pose)
        self._frame_numbers.append(frame_number)
        self._fps_values.append(current_fps)
        self._last_frame_time = time.monotonic()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def state(self) -> str:
        """Current session state string."""
        return self._state

    @property
    def is_recording(self) -> bool:
        """Whether the session is currently accumulating frames."""
        return self._state == self.STATE_RECORDING

    @property
    def is_paused(self) -> bool:
        return self._state == self.STATE_PAUSED

    @property
    def is_completed(self) -> bool:
        return self._state == self.STATE_COMPLETED

    @property
    def is_active(self) -> bool:
        """Recording or paused (i.e. started but not completed/discarded)."""
        return self._state in (self.STATE_RECORDING, self.STATE_PAUSED)

    @property
    def frame_count(self) -> int:
        return len(self._frames)

    @property
    def frames(self) -> List[PoseResult]:
        return list(self._frames)

    @property
    def frame_numbers(self) -> List[int]:
        return list(self._frame_numbers)

    @property
    def fps_values(self) -> List[float]:
        return list(self._fps_values)

    @property
    def camera_index(self) -> int:
        return self._camera_index

    @property
    def elapsed_seconds(self) -> float:
        """Real wall-clock seconds since start(), excluding pauses.

        This is the "live" timer value that the GUI should display.
        Returns 0.0 before start() and after discard().
        """
        if self._start_wall == 0.0:
            return 0.0
        if self._state == self.STATE_COMPLETED:
            total = (
                self._last_frame_time
                - self._start_wall
                - self._total_paused
            )
            return max(total, 0.0)
        now = time.monotonic()
        paused_so_far = self._total_paused
        if self._state == self.STATE_PAUSED:
            paused_so_far += now - self._pause_start
        elapsed = now - self._start_wall - paused_so_far
        return max(elapsed, 0.0)

    @property
    def wall_seconds(self) -> float:
        """Total wall-clock time since start() including pauses."""
        if self._start_wall == 0.0:
            return 0.0
        if self._state == self.STATE_COMPLETED:
            return self._last_frame_time - self._start_wall
        return time.monotonic() - self._start_wall

    def get_average_fps(self) -> float:
        """Average FPS computed from the real recording timing.

        Preference order:
        1. Per-frame timestamps (``(n-1) / (last - first)``) — the real
           timing information captured during recording.
        2. ``frame_count / elapsed_seconds`` (wall-clock duration).
        3. ``0.0`` when no frames are available (the MotionSequence
           layer applies the documented fallback at construction).

        Returns 0.0 when no frames have been recorded yet.
        """
        if not self._frames:
            return 0.0
        derived = fps_from_timestamps(
            [pr.timestamp for pr in self._frames]
        )
        if derived is not None:
            return derived
        if len(self._frames) < 2:
            return 0.0
        elapsed = self.elapsed_seconds
        if elapsed <= 0.0:
            return 0.0
        return len(self._frames) / elapsed

    def get_average_confidence(self) -> float:
        """Mean tracking confidence across all recorded frames."""
        if not self._frames:
            return 0.0
        total = sum(pr.confidence for pr in self._frames)
        return total / len(self._frames)