"""Session manager orchestrating the full recording lifecycle.

SessionManager is the single entry point that AppController uses for
all recording operations.  It owns a RecordingSession, a MotionRecorder
(for backward compatibility and MotionSequence production), and
handles JSON export with embedded RecordingMetadata.

Thread safety: ``record_pose()`` is called from the camera worker
thread; all other methods run on the GUI thread.  Internal state is
protected by a lock.
"""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Optional

from src.core.exceptions import RecordingError
from src.motion.motion_recorder import MotionRecorder
from src.motion.motion_sequence import MotionSequence
from src.pose.pose_result import PoseResult
from src.recording.recording_metadata import RecordingMetadata
from src.recording.session import RecordingSession


class SessionManager:
    """Manages the lifecycle of a single recording session.

    The manager is **single-use per session** — start, optionally
    pause/resume, then stop or discard.  After stop you may call
    ``save_recording()`` to persist.  After that, a new session
    can be started.

    Attributes:
        output_dir: Directory under which session sub-directories
            and JSON files are written.
    """

    def __init__(self, output_dir: Optional[Path] = None) -> None:
        self._logger = logging.getLogger(self.__class__.__name__)
        self._output_dir = (output_dir or Path("exports/recordings")).resolve()
        self._recorder = MotionRecorder()
        self._session: Optional[RecordingSession] = None
        self._lock = threading.Lock()
        self._last_saved_path: Optional[Path] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start_session(self, camera_index: int = -1, frame_rate: float = 30.0) -> None:
        """Begin a new recording session.

        Any previous unsaved session is discarded.  A new
        RecordingSession is created and the internal MotionRecorder
        is started.

        Args:
            camera_index: Camera device index for metadata.
            frame_rate: Nominal capture framerate.
        """
        with self._lock:
            self._session = RecordingSession(
                camera_index=camera_index, frame_rate=frame_rate,
            )
            self._session.start()
            self._recorder.start()
        self._logger.info(
            "Session started (camera %d).", camera_index,
        )

    def record_pose(
        self,
        pose: PoseResult,
        frame_number: int,
        current_fps: float,
    ) -> None:
        """Record one frame's pose data into the active session.

        Thread-safe — called from the camera worker thread.
        No-op when no session is active.
        """
        with self._lock:
            if self._session is None:
                return
            self._session.record_pose(pose, frame_number, current_fps)
        self._recorder.record(pose)

    def pause_session(self) -> None:
        """Pause the active recording session.

        No-op if not currently recording.
        """
        with self._lock:
            if self._session is None:
                return
            self._session.pause()
        self._logger.info("Session paused.")

    def resume_session(self) -> None:
        """Resume a paused recording session.

        No-op if not currently paused.
        """
        with self._lock:
            if self._session is None:
                return
            self._session.resume()
        self._logger.info("Session resumed.")

    def stop_session(self) -> None:
        """Stop the active session without saving.

        Data is retained in the session for later export via
        ``save_recording()``.
        """
        with self._lock:
            if self._session is None:
                return
            self._session.stop()
        self._recorder.stop()
        self._logger.info(
            "Session stopped: %d frames.",
            self._session.frame_count,
        )

    def discard_session(self) -> None:
        """Discard the current session entirely.

        All recorded data is lost.  Safe to call even when no
        session is active.
        """
        with self._lock:
            if self._session is not None:
                self._session.discard()
            self._session = None
        self._recorder.cancel()
        self._last_saved_path = None
        self._logger.info("Session discarded.")

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def save_recording(self) -> Optional[Path]:
        """Save the completed session to a JSON file on disk.

        The file is written under ``output_dir`` with a filename like
        ``recording_<timestamp>.json``.  The JSON contains both a
        ``metadata`` block and the full ``pose_results`` array.

        Returns:
            The path of the saved file, or None if the session has no
            data or is still active.
        """
        with self._lock:
            if self._session is None:
                return None
            if not self._session.is_completed:
                self._logger.warning(
                    "save_recording() called on non-completed session."
                )
                return None
            if self._session.frame_count == 0:
                self._logger.warning("No frames to save.")
                return None

            metadata = RecordingMetadata.build(
                duration_seconds=self._session.elapsed_seconds,
                average_fps=self._session.get_average_fps(),
                average_confidence=self._session.get_average_confidence(),
                frame_count=self._session.frame_count,
                camera_index=self._session.camera_index,
            )

            motion_seq = MotionSequence(
                pose_results=self._session.frames,
                start_time=0.0,
                end_time=self._session.elapsed_seconds,
                total_frames=self._session.frame_count,
                average_fps=metadata.average_fps,
                duration=metadata.duration_seconds,
            )

            export_dict = motion_seq.to_dict()
            export_dict["metadata"] = metadata.to_dict()
            export_dict["frame_numbers"] = self._session.frame_numbers
            export_dict["fps_values"] = self._session.fps_values

        # Save outside the lock to avoid blocking the worker.
        timestamp_str = f"{time.time():.0f}"
        path = self._output_dir / f"recording_{timestamp_str}.json"

        import json
        try:
            self._output_dir.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(export_dict, f, indent=2, ensure_ascii=False)
                f.write("\n")
        except (OSError, TypeError, ValueError) as e:
            raise RecordingError(
                f"Failed to save recording to {path}: {e}",
                cause=e,
            )

        self._last_saved_path = path
        self._logger.info(
            "Saved %d frames to %s (%.1f FPS, %.1f s).",
            metadata.frame_count,
            path.name,
            metadata.average_fps,
            metadata.duration_seconds,
        )
        return path

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    @property
    def is_recording(self) -> bool:
        """Whether a session is currently accumulating frames."""
        with self._lock:
            return self._session is not None and self._session.is_recording

    @property
    def is_paused(self) -> bool:
        """Whether the session is currently paused."""
        with self._lock:
            return self._session is not None and self._session.is_paused

    @property
    def is_active(self) -> bool:
        """Whether a session exists and is not completed/discarded."""
        with self._lock:
            return self._session is not None and self._session.is_active

    @property
    def elapsed_seconds(self) -> float:
        """Live wall-clock recording duration excluding pauses."""
        with self._lock:
            if self._session is None:
                return 0.0
            return self._session.elapsed_seconds

    @property
    def frame_count(self) -> int:
        """Frames accumulated in the current session."""
        with self._lock:
            if self._session is None:
                return 0
            return self._session.frame_count

    @property
    def average_confidence(self) -> float:
        """Mean tracking confidence across recorded frames."""
        with self._lock:
            if self._session is None:
                return 0.0
            return self._session.get_average_confidence()

    @property
    def last_saved_path(self) -> Optional[Path]:
        """Path of the most recently saved recording file."""
        return self._last_saved_path

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        """Cancel any active session and release resources."""
        with self._lock:
            if self._session is not None and self._session.is_active:
                self._session.discard()
            self._session = None
        self._recorder.cancel()
        self._logger.info("SessionManager shut down.")