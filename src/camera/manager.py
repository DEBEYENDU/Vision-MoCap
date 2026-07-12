"""Camera management subsystem for the VisionMoCap application.

Provides camera discovery, selection, frame capture, and FPS monitoring
using configurable OpenCV backends.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from typing import List, Optional

import cv2
import numpy as np
from numpy.typing import NDArray

from src.camera.backend import Backend
from src.camera.device import CameraDevice
from src.config.manager import RESOLUTION_PRESETS, CameraConfig
from src.core.exceptions import CameraError


class _FPSMonitor:
    """Tracks frame rate statistics over a sliding window of timestamps.

    Maintains a fixed-size deque of frame timestamps and per-frame
    intervals, exposing current, average, minimum, and maximum FPS.
    """

    def __init__(self, window_size: int = 30) -> None:
        self._timestamps: deque[float] = deque(maxlen=window_size)
        self._intervals: deque[float] = deque(maxlen=window_size)

    def tick(self) -> None:
        """Record a new frame timestamp and the interval since the last."""
        now = time.perf_counter()
        if self._timestamps:
            self._intervals.append(now - self._timestamps[-1])
        self._timestamps.append(now)

    def reset(self) -> None:
        """Clear all recorded timestamps and intervals."""
        self._timestamps.clear()
        self._intervals.clear()

    @property
    def current_fps(self) -> float:
        """FPS based on the interval between the last two frames."""
        if len(self._timestamps) < 2:
            return 0.0
        interval = self._timestamps[-1] - self._timestamps[-2]
        if interval <= 0.0:
            return 0.0
        return 1.0 / interval

    @property
    def average_fps(self) -> float:
        """Average FPS over the entire sliding window."""
        if len(self._timestamps) < 2:
            return 0.0
        elapsed = self._timestamps[-1] - self._timestamps[0]
        if elapsed <= 0.0:
            return 0.0
        return (len(self._timestamps) - 1) / elapsed

    @property
    def min_fps(self) -> float:
        """Minimum FPS observed in the sliding window."""
        if not self._intervals:
            return 0.0
        return 1.0 / max(self._intervals)

    @property
    def max_fps(self) -> float:
        """Maximum FPS observed in the sliding window."""
        if not self._intervals:
            return 0.0
        return 1.0 / min(self._intervals)


class CameraManager:
    """Manages camera discovery, selection, and frame capture operations.

    Uses the configurable OpenCV backend (default DirectShow on Windows).
    Provides a clean API for the full camera lifecycle: discovery, open,
    close, switch, frame capture, and comprehensive FPS statistics.

    Supports the context manager protocol for safe resource handling::

        with CameraManager(config) as mgr:
            mgr.open_camera(0)
            frame = mgr.get_frame()

    Every detected camera is treated uniformly — no hardcoded logic for
    DroidCam, Iriun, or OBS Virtual Camera. All DirectShow-compatible
    devices are discovered and managed identically.
    """

    def __init__(self, config: Optional[CameraConfig] = None) -> None:
        self._config = config or CameraConfig()
        self._backend = self._resolve_backend()
        self._capture: Optional[cv2.VideoCapture] = None
        self._current_device: Optional[CameraDevice] = None
        self._fps_monitor = _FPSMonitor()
        self._logger = logging.getLogger(self.__class__.__name__)
        self._camera_list: List[CameraDevice] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def discover_cameras(self) -> List[CameraDevice]:
        """Probe camera indices and return a list of available devices.

        Tests indices 0 through ``max_camera_index - 1`` using the
        configured backend. Each index is briefly opened and a test frame
        is attempted to confirm responsiveness.

        Returns:
            A list of CameraDevice instances for every detected camera.
        """
        self._camera_list.clear()
        max_index = self._config.max_camera_index
        self._logger.info(
            "Discovering cameras (0-%d, backend=%s)...",
            max_index - 1,
            self._backend.name.lower(),
        )
        for index in range(max_index):
            device = self._probe_camera(index)
            if device is not None:
                self._camera_list.append(device)
                self._logger.info(
                    "Discovered [%d] %s | %dx%d @ %.1f FPS",
                    device.index,
                    device.name,
                    device.resolution_width,
                    device.resolution_height,
                    device.fps,
                )
        if not self._camera_list:
            self._logger.warning("No cameras found during discovery.")
        return list(self._camera_list)

    def open_camera(self, index: int) -> bool:
        """Open a camera by its device index.

        Any previously opened camera is released first. The camera is
        configured with the stored resolution preset and frame rate
        settings from CameraConfig.

        Args:
            index: Zero-based device index of the camera to open.

        Returns:
            True if the camera was opened and configured successfully.

        Raises:
            CameraError: If *index* is negative or the camera cannot be opened.
        """
        if index < 0:
            raise CameraError(
                f"Camera index must be non-negative, got {index}."
            )
        self.close_camera()
        self._logger.info("Opening camera %d...", index)
        try:
            capture = cv2.VideoCapture(index, self._backend.value)
            if not capture.isOpened():
                capture.release()
                raise CameraError(f"Failed to open camera {index}.")
            self._apply_config(capture)
            self._capture = capture
            actual_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = capture.get(cv2.CAP_PROP_FPS)
            self._current_device = CameraDevice(
                index=index,
                name=f"Camera {index}",
                backend=self._backend,
                is_available=True,
                resolution_width=actual_width,
                resolution_height=actual_height,
                fps=actual_fps,
            )
            self._fps_monitor.reset()
            requested_w, requested_h = self._resolve_resolution()
            self._logger.info(
                "Camera %d opened: %dx%d @ %.1f FPS "
                "(requested: %dx%d @ %.1f FPS, backend=%s).",
                index,
                actual_width,
                actual_height,
                actual_fps,
                requested_w,
                requested_h,
                self._config.fps,
                self._backend.name.lower(),
            )
            return True
        except CameraError:
            raise
        except Exception as e:
            raise CameraError(
                f"Unexpected error opening camera {index}: {e}", cause=e
            )

    def close_camera(self) -> None:
        """Release the currently opened camera, if any.

        Safe to call even when no camera is open. All internal state
        is reset after release.
        """
        if self._capture is not None:
            try:
                self._capture.release()
                name = (
                    self._current_device.name
                    if self._current_device
                    else "unknown"
                )
                self._logger.info("Camera '%s' released.", name)
            except Exception as e:
                self._logger.error("Error releasing camera: %s", e)
            finally:
                self._capture = None
                self._current_device = None
                self._fps_monitor.reset()

    def switch_camera(self, index: int) -> bool:
        """Switch to a different camera device.

        Closes the currently open camera (if any) and opens the specified
        camera index.

        Args:
            index: Zero-based device index of the camera to switch to.

        Returns:
            True if the new camera was opened successfully.

        Raises:
            CameraError: If the new camera cannot be opened.
        """
        self.close_camera()
        return self.open_camera(index)

    def get_frame(self) -> Optional[NDArray[np.uint8]]:
        """Read the next frame from the currently opened camera.

        Returns:
            The captured frame as a BGR numpy array of shape
            ``(H, W, 3)``, or None if the frame could not be read.

        Raises:
            CameraError: If no camera is currently open.
        """
        if self._capture is None:
            raise CameraError(
                "No camera is open. Call open_camera() first."
            )
        try:
            ret, frame = self._capture.read()
            if not ret or frame is None:
                self._logger.warning("Failed to read frame from camera.")
                return None
            self._fps_monitor.tick()
            return frame
        except Exception as e:
            raise CameraError(f"Error reading frame: {e}", cause=e)

    def get_current_camera(self) -> Optional[CameraDevice]:
        """Return metadata for the currently active camera.

        Returns:
            The CameraDevice for the open camera, or None if no camera
            is open.
        """
        return self._current_device

    def get_current_fps(self) -> float:
        """FPS based on the interval between the last two frames."""
        return self._fps_monitor.current_fps

    def get_average_fps(self) -> float:
        """Average FPS over the recent sliding window (~30 frames)."""
        return self._fps_monitor.average_fps

    def get_min_fps(self) -> float:
        """Minimum FPS observed over the recent sliding window."""
        return self._fps_monitor.min_fps

    def get_max_fps(self) -> float:
        """Maximum FPS observed over the recent sliding window."""
        return self._fps_monitor.max_fps

    def get_fps(self) -> float:
        """Alias for :meth:`get_average_fps` (backward compatibility)."""
        return self.get_average_fps()

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> CameraManager:
        return self

    def __exit__(self, *args: object) -> None:
        self.close_camera()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _probe_camera(self, index: int) -> Optional[CameraDevice]:
        """Test whether a camera index is available and responsive."""
        capture = None
        try:
            capture = cv2.VideoCapture(index, self._backend.value)
            if not capture.isOpened():
                return None
            ret, _ = capture.read()
            if not ret:
                return None
            width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = capture.get(cv2.CAP_PROP_FPS)
            return CameraDevice(
                index=index,
                name=f"Camera {index}",
                backend=self._backend,
                is_available=True,
                resolution_width=width,
                resolution_height=height,
                fps=fps,
            )
        except Exception:
            return None
        finally:
            if capture is not None:
                capture.release()

    def _apply_config(self, capture: cv2.VideoCapture) -> None:
        """Apply resolution and FPS settings from CameraConfig."""
        width, height = self._resolve_resolution()
        width_ok = capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        if not width_ok:
            self._logger.warning(
                "Failed to set frame width to %d.", width
            )
        height_ok = capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        if not height_ok:
            self._logger.warning(
                "Failed to set frame height to %d.", height
            )
        fps_ok = capture.set(cv2.CAP_PROP_FPS, self._config.fps)
        if not fps_ok:
            self._logger.warning(
                "Failed to set FPS to %.1f.", self._config.fps
            )

    def _resolve_resolution(self) -> tuple[int, int]:
        """Return (width, height) from the configured preset or raw values."""
        preset = self._config.resolution_preset
        if preset:
            resolved = RESOLUTION_PRESETS.get(preset)
            if resolved is not None:
                return resolved
            self._logger.warning(
                "Unknown resolution preset '%s', falling back to %dx%d.",
                preset,
                self._config.width,
                self._config.height,
            )
        return self._config.width, self._config.height

    def _resolve_backend(self) -> Backend:
        """Convert the config backend string to a Backend enum member."""
        try:
            return Backend.from_string(self._config.backend)
        except ValueError as e:
            self._logger.warning(
                "%s Falling back to DirectShow.", e
            )
            return Backend.DIRECTSHOW
