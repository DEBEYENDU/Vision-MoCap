"""Camera management subsystem for the VisionMoCap application.

Provides camera discovery, selection, frame capture, and FPS monitoring
using OpenCV's DirectShow backend on Windows for broad compatibility.
"""

import logging
import time
from collections import deque
from typing import List, Optional

import cv2
import numpy as np
from numpy.typing import NDArray

from src.camera.device import CameraDevice
from src.config.manager import CameraConfig
from src.core.exceptions import CameraError


class _FPSMonitor:
    """Tracks frame rate using a sliding window of frame timestamps.

    Maintains a fixed-size deque of timestamps and computes FPS as the
    number of frame intervals divided by the total elapsed time.
    """

    def __init__(self, window_size: int = 30) -> None:
        self._timestamps: deque[float] = deque(maxlen=window_size)

    def tick(self) -> None:
        """Record a new frame timestamp."""
        self._timestamps.append(time.perf_counter())

    def reset(self) -> None:
        """Clear all recorded timestamps."""
        self._timestamps.clear()

    @property
    def fps(self) -> float:
        """Compute the average FPS over the current sliding window.

        Returns:
            Measured frames per second, or 0.0 if fewer than 2 frames.
        """
        if len(self._timestamps) < 2:
            return 0.0
        elapsed = self._timestamps[-1] - self._timestamps[0]
        if elapsed <= 0.0:
            return 0.0
        return (len(self._timestamps) - 1) / elapsed


class CameraManager:
    """Manages camera discovery, selection, and frame capture operations.

    Uses OpenCV's DirectShow (CAP_DSHOW) backend on Windows for broad
    compatibility with laptop webcams, USB webcams, DroidCam, and Iriun
    Webcam. Provides a clean API for the full camera lifecycle including
    discovery, open, close, switch, frame capture, and FPS measurement.

    Supports context manager protocol for safe resource handling::

        with CameraManager(config) as mgr:
            mgr.open_camera(0)
            frame = mgr.get_frame()
    """

    _DEFAULT_BACKEND = cv2.CAP_DSHOW
    _MAX_DISCOVERY_INDEX = 10

    def __init__(self, config: Optional[CameraConfig] = None) -> None:
        self._config = config or CameraConfig()
        self._capture: Optional[cv2.VideoCapture] = None
        self._current_device: Optional[CameraDevice] = None
        self._fps_monitor = _FPSMonitor()
        self._logger = logging.getLogger(self.__class__.__name__)
        self._camera_list: List[CameraDevice] = []

    def discover_cameras(self) -> List[CameraDevice]:
        """Probe camera indices and return a list of available devices.

        Tests indices 0 through 9 using the DirectShow backend. Each index
        is briefly opened and a test frame is attempted to confirm that the
        camera is responsive.

        Returns:
            A list of CameraDevice instances for every detected camera.
        """
        self._camera_list.clear()
        self._logger.info("Discovering available cameras...")
        for index in range(self._MAX_DISCOVERY_INDEX):
            device = self._probe_camera(index)
            if device is not None:
                self._camera_list.append(device)
                self._logger.info("Discovered: %s", device.name)
        if not self._camera_list:
            self._logger.warning("No cameras found during discovery.")
        return list(self._camera_list)

    def open_camera(self, index: int) -> bool:
        """Open a camera by its device index.

        Any previously opened camera is released first. The camera is
        configured with the stored resolution and frame rate settings
        from CameraConfig.

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
            capture = cv2.VideoCapture(index, self._DEFAULT_BACKEND)
            if not capture.isOpened():
                raise CameraError(f"Failed to open camera {index}.")
            self._apply_config(capture)
            self._capture = capture
            self._current_device = CameraDevice(
                index=index,
                name=f"Camera {index}",
                backend=self._DEFAULT_BACKEND,
                is_available=True,
            )
            self._fps_monitor.reset()
            actual_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = capture.get(cv2.CAP_PROP_FPS)
            self._logger.info(
                "Camera %d opened: %dx%d @ %.1f FPS "
                "(requested: %dx%d @ %.1f FPS).",
                index,
                actual_width,
                actual_height,
                actual_fps,
                self._config.width,
                self._config.height,
                self._config.fps,
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

        The returned frame is a numpy array of shape (H, W, 3) in BGR
        channel order, as produced by OpenCV.

        Returns:
            The captured frame, or None if the frame could not be read
            (e.g. the camera was disconnected).

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

    def get_fps(self) -> float:
        """Return the measured frame rate based on recent frame timestamps.

        The FPS is computed from a sliding window of the last 30 frame
        timestamps, providing a stable real-time measurement.

        Returns:
            Measured frames per second, or 0.0 if insufficient data.
        """
        return self._fps_monitor.fps

    def get_current_camera(self) -> Optional[CameraDevice]:
        """Return metadata for the currently active camera.

        Returns:
            The CameraDevice for the open camera, or None if no camera
            is open.
        """
        return self._current_device

    def __enter__(self) -> "CameraManager":
        return self

    def __exit__(self, *args: object) -> None:
        self.close_camera()

    def _probe_camera(self, index: int) -> Optional[CameraDevice]:
        """Test whether a camera index is available and responsive."""
        capture = None
        try:
            capture = cv2.VideoCapture(index, self._DEFAULT_BACKEND)
            if not capture.isOpened():
                return None
            ret, _ = capture.read()
            if not ret:
                return None
            return CameraDevice(
                index=index,
                name=f"Camera {index}",
                backend=self._DEFAULT_BACKEND,
                is_available=True,
            )
        except Exception:
            return None
        finally:
            if capture is not None:
                capture.release()

    def _apply_config(self, capture: cv2.VideoCapture) -> None:
        """Apply resolution and FPS settings from CameraConfig."""
        width_ok = capture.set(
            cv2.CAP_PROP_FRAME_WIDTH, self._config.width
        )
        if not width_ok:
            self._logger.warning(
                "Failed to set frame width to %d.", self._config.width
            )
        height_ok = capture.set(
            cv2.CAP_PROP_FRAME_HEIGHT, self._config.height
        )
        if not height_ok:
            self._logger.warning(
                "Failed to set frame height to %d.", self._config.height
            )
        fps_ok = capture.set(
            cv2.CAP_PROP_FPS, self._config.fps
        )
        if not fps_ok:
            self._logger.warning(
                "Failed to set FPS to %.1f.", self._config.fps
            )
