"""Application controller bridging the GUI layer with the VisionMoCap pipeline.

AppController owns CameraManager, PoseDetector, SkeletonRenderer,
MotionRecorder, and FrameManager.  When the camera is started a
dedicated worker thread is spawned that runs the full capture →
detect → render pipeline and delivers annotated frames to the GUI
thread via a thread-safe queue.  Error information is surfaced
through a second queue so the GUI can show user-friendly dialogs
without blocking.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from pathlib import Path
from typing import Callable, Optional

import numpy as np
from numpy.typing import NDArray

from src.camera.device import CameraDevice
from src.camera.manager import CameraManager
from src.config.manager import AppConfig, ConfigManager
from src.core.exceptions import CameraError, PoseEstimationError
from src.motion.frame_manager import FrameManager
from src.motion.motion_recorder import MotionRecorder
from src.pose.pose_detector import PoseDetector
from src.pose.pose_result import PoseResult
from src.pose.skeleton_renderer import SkeletonRenderer
from src.recording.session_manager import SessionManager


class AppController:
    """Orchestrates the VisionMoCap pipeline for the GUI layer.

    Owns the camera, pose detector, renderer, frame manager, and
    recorder.  When the camera is active a dedicated background
    thread runs the full capture → detect → render pipeline and
    delivers annotated frames to the GUI via an internal queue.

    The public API is identical to the synchronous version so the
    GUI layer does not need to know about threading concerns.

    Attributes:
        on_status: Callable ``(level, message)`` for status-bar flashes.
    """

    def __init__(
        self,
        config: Optional[AppConfig] = None,
        config_path: Optional[Path] = None,
    ) -> None:
        self._logger = logging.getLogger(self.__class__.__name__)

        if config is not None:
            self._config = config
        else:
            cfg_mgr = ConfigManager(config_path)
            self._config = cfg_mgr.load()

        # Pipeline components (created once, reused across sessions)
        self._camera_mgr = CameraManager(self._config.camera)
        self._frame_mgr = FrameManager(
            resize=None, color_conversion=None, buffer_size=1,
        )
        self._pose_detector = PoseDetector(self._config.pose)
        self._renderer = SkeletonRenderer(
            draw_landmarks=True,
            draw_connections=True,
            draw_joint_ids=False,
            draw_confidence=False,
        )
        self._recorder = MotionRecorder()
        self._session_mgr = SessionManager()

        # ---- Threading primitives ----
        self._frame_queue: queue.Queue[NDArray[np.uint8]] = queue.Queue(
            maxsize=2
        )
        self._stop_event = threading.Event()
        self._worker: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Shared state written by worker, read by GUI under lock
        self._camera_open: bool = False
        self._latest_pose: Optional[PoseResult] = None
        self._status_fps: float = 0.0
        self._status_confidence: float = 0.0
        self._status_cam_index: int = -1
        self._status_cam_name: str = "Off"
        self._status_frame_number: int = 0

        # Error channel (worker → GUI)
        self._error_queue: queue.Queue[tuple[str, str]] = queue.Queue()

        # Callbacks
        self.on_status: Optional[Callable[[str, str], None]] = None

        self._logger.info("AppController created.")

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------

    def _emit(self, level: str, message: str) -> None:
        getattr(self._logger, level.lower(), self._logger.info)(
            "%s", message
        )
        if self.on_status is not None:
            self.on_status(level, message)

    # ------------------------------------------------------------------
    # Camera API
    # ------------------------------------------------------------------

    def discover_cameras(self) -> list[CameraDevice]:
        """Probe all available camera indices and return detected devices."""
        return self._camera_mgr.discover_cameras()

    def start_camera(self, index: int) -> bool:
        """Open a camera, initialise the pose detector, start the worker.

        The camera and detector are set up synchronously so the caller
        immediately knows whether startup succeeded.  The frame-capture
        pipeline runs in a background daemon thread thereafter.

        Args:
            index: Zero-based device index.

        Returns:
            True if the camera was opened and the detector initialised.
        """
        try:
            ok = self._camera_mgr.open_camera(index)
            if not ok:
                self._emit("ERROR", f"Failed to open camera {index}.")
                return False
            self._pose_detector.initialize()
        except (CameraError, PoseEstimationError) as e:
            self._emit("ERROR", str(e))
            return False

        self._camera_open = True
        device = self._camera_mgr.get_current_camera()
        self._status_cam_index = device.index if device else index
        self._status_cam_name = device.name if device else f"Camera {index}"

        self._stop_event.clear()
        self._worker = threading.Thread(
            target=self._capture_loop, daemon=True
        )
        self._worker.start()

        self._emit(
            "INFO",
            f"Camera started: {self._status_cam_name} "
            f"(index {self._status_cam_index}).",
        )
        return True

    def stop_camera(self) -> None:
        """Stop the worker thread, release the camera, shut down pose detector.

        Safe to call when the camera is already stopped.  Blocks until
        the worker thread has exited (with a 5 s timeout).
        """
        self._stop_event.set()

        if self._worker is not None and self._worker.is_alive():
            self._camera_mgr.close_camera()
            self._worker.join(timeout=5.0)
            if self._worker.is_alive():
                self._logger.warning(
                    "Worker thread did not exit within the timeout."
                )
        self._worker = None

        try:
            self._pose_detector.shutdown()
        except PoseEstimationError:
            pass

        # Drain frame queue
        while True:
            try:
                self._frame_queue.get_nowait()
            except queue.Empty:
                break

        with self._lock:
            self._camera_open = False
            self._latest_pose = None
            self._status_fps = 0.0
            self._status_confidence = 0.0
            self._status_cam_index = -1
            self._status_cam_name = "Off"
            self._status_frame_number = 0

        self._emit("INFO", "Camera stopped.")

    @property
    def is_camera_open(self) -> bool:
        """Whether a camera is currently active and the worker is running."""
        with self._lock:
            return self._camera_open

    # ------------------------------------------------------------------
    # Frame pipeline  (runs in the worker thread)
    # ------------------------------------------------------------------

    def _capture_loop(self) -> None:
        """Background thread: capture → detect → render → enqueue."""
        self._logger.info("Capture thread started.")
        log_counter = 0

        while not self._stop_event.is_set():
            try:
                raw = self._camera_mgr.get_frame()
            except CameraError:
                if self._stop_event.is_set():
                    break
                self._emit("ERROR", "Camera disconnected during capture.")
                self._error_queue.put(
                    ("Camera Error",
                     "The camera was disconnected or became unavailable.")
                )
                break

            if raw is None:
                self._stop_event.wait(0.005)
                continue

            processed = self._frame_mgr.process(raw)

            self._logger.debug(
                "Frame size: %dx%d",
                processed.shape[1],
                processed.shape[0],
            )


            try:
                pose_result = self._pose_detector.detect(processed)
            except PoseEstimationError as e:
                self._logger.warning("Frame #%d: pose detection failed: %s",
                                     self._frame_mgr.frame_number, e)
                pose_result = None

            if pose_result is not None and pose_result.pose_detected:
                try:
                    processed = self._renderer.render(processed, pose_result)
                except Exception as e:
                    self._logger.exception("Skeleton renderer failed: %s", e)

            if pose_result is not None:
                try:
                    self._recorder.record(pose_result)

                    self._session_mgr.record_pose(
                        pose_result,
                        self._frame_mgr.frame_number,
                        self._camera_mgr.get_current_fps(),
                    )
                except Exception as e:
                    self._logger.exception("Recording error: %s", e)

            # Thread-safe state snapshot
            with self._lock:
                self._latest_pose = pose_result
                self._status_fps = self._camera_mgr.get_average_fps()
                self._status_confidence = (
                    pose_result.confidence
                    if pose_result is not None
                    else 0.0
                )
                self._status_frame_number = self._frame_mgr.frame_number

            # Frame delivery to GUI (drop oldest when queue is full)
            try:
                self._frame_queue.put_nowait(processed)
            except queue.Full:
                try:
                    self._frame_queue.get_nowait()
                except queue.Empty:
                    pass
                self._frame_queue.put(processed)

            # Periodic logging
            log_counter += 1
            if log_counter % 30 == 0 and pose_result is not None:
                self._logger.info(
                    "Frame #%d processed | FPS: %.1f | "
                    "Pose confidence: %.3f | Recording: %s",
                    self._frame_mgr.frame_number,
                    self._camera_mgr.get_average_fps(),
                    pose_result.confidence,
                    "yes" if self._session_mgr.is_recording else "no",
                )

        self._logger.info("Capture thread stopped.")

    # ------------------------------------------------------------------
    # GUI-facing accessors
    # ------------------------------------------------------------------

    def get_next_frame(self) -> Optional[NDArray[np.uint8]]:
        """Return the most recent annotated frame, or None if none available.

        Called from the GUI thread.  Never blocks.
        """
        try:
            return self._frame_queue.get_nowait()
        except queue.Empty:
            return None

    def get_pose_result(self) -> Optional[PoseResult]:
        """Return the most recent pose result."""
        with self._lock:
            return self._latest_pose

    def get_average_fps(self) -> float:
        """Average FPS over the recent sliding window (worker computed)."""
        with self._lock:
            return self._status_fps

    def get_tracking_confidence(self) -> float:
        """Confidence of the most recent pose detection (0.0 if none)."""
        with self._lock:
            return self._status_confidence

    def get_frame_number(self) -> int:
        """Monotonically increasing frame counter from the frame manager."""
        with self._lock:
            return self._status_frame_number

    def get_current_camera(self) -> Optional[CameraDevice]:
        """Metadata for the currently active camera."""
        return self._camera_mgr.get_current_camera()

    def get_camera_index(self) -> int:
        """Index of the currently active camera, or -1 if none."""
        with self._lock:
            return self._status_cam_index

    def get_camera_name(self) -> str:
        """Human-readable name of the active camera, or ``Off``."""
        with self._lock:
            return self._status_cam_name

    def pop_error(self) -> Optional[tuple[str, str]]:
        """Return the next pending error ``(title, message)`` or ``None``."""
        try:
            return self._error_queue.get_nowait()
        except queue.Empty:
            return None

    # ------------------------------------------------------------------
    # Recording API
    # ------------------------------------------------------------------

    def start_recording(self) -> None:
        """Begin accumulating pose data (no-op if already recording).

        Creates a new recording session via the SessionManager with
        the current camera index and frame rate.
        """
        if self._session_mgr.is_active:
            return
        cam_index = self._camera_mgr.get_current_camera()
        idx = cam_index.index if cam_index is not None else -1
        frame_rate = self._config.camera.fps
        self._session_mgr.start_session(camera_index=idx, frame_rate=frame_rate)
        self._emit(
            "INFO",
            f"Recording started (camera {idx}).",
        )

    def stop_recording(self) -> Optional[Path]:
        """Stop recording and persist to disk.

        Stops the session manager and saves the recording.  Returns
        the path of the saved file, or None if no data was captured.

        Returns:
            The path to the saved JSON file, or None if no data.
        """
        if not self._session_mgr.is_active:
            self._emit("WARNING", "No active recording to stop.")
            return None

        self._session_mgr.stop_session()
        path = self._session_mgr.save_recording()
        if path is None:
            self._emit("WARNING", "Recording stopped with no frames.")
            return None

        self._emit(
            "INFO",
            f"Saved recording: {path.name}",
        )
        return path

    def pause_recording(self) -> None:
        """Pause the active recording session."""
        self._session_mgr.pause_session()
        self._emit("INFO", "Recording paused.")

    def resume_recording(self) -> None:
        """Resume a paused recording session."""
        self._session_mgr.resume_session()
        self._emit("INFO", "Recording resumed.")

    def discard_recording(self) -> None:
        """Discard the current recording without saving."""
        self._session_mgr.discard_session()
        self._emit("INFO", "Recording discarded.")

    @property
    def is_recording(self) -> bool:
        """Whether a recording session is currently accumulating."""
        return self._session_mgr.is_recording

    @property
    def is_recording_paused(self) -> bool:
        """Whether the recording session is paused."""
        return self._session_mgr.is_paused

    @property
    def recorded_frame_count(self) -> int:
        """Number of frames accumulated in the current session."""
        return self._session_mgr.frame_count

    @property
    def recording_elapsed(self) -> float:
        """Live wall-clock recording duration excluding pauses."""
        return self._session_mgr.elapsed_seconds

    @property
    def recording_confidence(self) -> float:
        """Mean tracking confidence across recorded frames so far."""
        return self._session_mgr.average_confidence

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        """Release all resources."""
        if self._session_mgr.is_active:
            self._session_mgr.discard_session()
        if self._camera_open:
            self.stop_camera()
        self._session_mgr.shutdown()
        self._emit("INFO", "AppController shut down.")