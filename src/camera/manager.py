"""Camera management subsystem for the VisionMoCap application.

Simplified DSHOW-first camera management for the BE Project prototype.
Discovery and opening are combined — the first camera that returns
a valid frame is kept open.
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

_MAX_PROBE_INDEX = 5


class _FPSMonitor:
    """Tracks frame rate statistics over a sliding window of timestamps."""

    def __init__(self, window_size: int = 30) -> None:
        self._timestamps: deque[float] = deque(maxlen=window_size)
        self._intervals: deque[float] = deque(maxlen=window_size)

    def tick(self) -> None:
        now = time.perf_counter()
        if self._timestamps:
            self._intervals.append(now - self._timestamps[-1])
        self._timestamps.append(now)

    def reset(self) -> None:
        self._timestamps.clear()
        self._intervals.clear()

    @property
    def current_fps(self) -> float:
        if len(self._timestamps) < 2:
            return 0.0
        interval = self._timestamps[-1] - self._timestamps[-2]
        if interval <= 0.0:
            return 0.0
        return 1.0 / interval

    @property
    def average_fps(self) -> float:
        if len(self._timestamps) < 2:
            return 0.0
        elapsed = self._timestamps[-1] - self._timestamps[0]
        if elapsed <= 0.0:
            return 0.0
        return (len(self._timestamps) - 1) / elapsed

    @property
    def min_fps(self) -> float:
        if not self._intervals:
            return 0.0
        return 1.0 / max(self._intervals)

    @property
    def max_fps(self) -> float:
        if not self._intervals:
            return 0.0
        return 1.0 / min(self._intervals)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _safe_capture_property(capture: cv2.VideoCapture, prop_id: int, default: float = 0.0) -> float:
    try:
        return capture.get(prop_id)
    except cv2.error as e:
        logging.getLogger("CameraManager").debug(
            "CAP_PROP_%d get failed (cv2.error): %s", prop_id, e,
        )
        return default


def _safe_capture_set(capture: cv2.VideoCapture, prop_id: int, value: float) -> bool:
    try:
        return capture.set(prop_id, value)
    except cv2.error as e:
        logging.getLogger("CameraManager").debug(
            "CAP_PROP_%d set(%s) failed (cv2.error): %s", prop_id, value, e,
        )
        return False


def _safe_capture_release(capture: Optional[cv2.VideoCapture]) -> None:
    if capture is None:
        return
    try:
        capture.release()
    except cv2.error:
        pass


def _get_camera_name(capture: cv2.VideoCapture, index: int) -> str:
    try:
        desc = capture.get(cv2.CAP_PROP_DEVICE_DESCRIPTION)
        if desc and isinstance(desc, str) and desc.strip():
            return desc.strip()
    except cv2.error:
        pass
    except Exception:
        pass
    return f"Camera {index}"


def _warmup_camera(index: int) -> None:
    """Open and release *index* with ANY to initialise the driver.

    Required before DSHOW on some integrated webcams.
    """
    try:
        warmup = cv2.VideoCapture(index, cv2.CAP_ANY)
        if warmup.isOpened():
            warmup.release()
    except cv2.error:
        pass
    except Exception:
        pass


def _backend_order(config: CameraConfig) -> List[Backend]:
    """Return the backend candidates to try, most preferred first.

    The configured backend is tried first; ``ANY`` (driver auto-select)
    is always the final fallback so the manager works on platforms where
    the configured backend is unavailable.
    """
    try:
        preferred = Backend.from_string(config.backend)
    except ValueError:
        preferred = Backend.DIRECTSHOW
    order = [preferred]
    if Backend.ANY not in order:
        order.append(Backend.ANY)
    return order


# ---------------------------------------------------------------------------
# CameraManager
# ---------------------------------------------------------------------------


class CameraManager:
    """Simplified camera manager for the BE Project prototype.

    Discovery and opening are combined: `discover_cameras()` probes
    indices 0–4 with DSHOW (ANY warm-up) and keeps the first working
    camera open.
    """

    def __init__(self, config: Optional[CameraConfig] = None) -> None:
        self._config = config or CameraConfig()
        self._backend = self._resolve_backend()
        self._capture: Optional[cv2.VideoCapture] = None
        self._current_device: Optional[CameraDevice] = None
        self._fps_monitor = _FPSMonitor()
        self._logger = logging.getLogger(self.__class__.__name__)
        self._camera_list: List[CameraDevice] = []
        self._last_opened_index: int = -1

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def discover_cameras(self) -> List[CameraDevice]:
        """Probe cameras and keep the first working one open.

        Indices ``0..max_camera_index-1`` (config, capped at 10) are
        tested with the configured backend first, falling back to
        ``ANY`` when a backend cannot open the device.  The first
        camera that returns a valid frame is kept open; the remaining
        indices are still probed (for the dropdown) but their captures
        are released.

        Returns:
            A list of all probed ``CameraDevice`` instances for the
            GUI dropdown.
        """
        self._camera_list.clear()
        self.close_camera()

        max_index = max(1, min(self._config.max_camera_index, 10))
        backends = _backend_order(self._config)

        for index in range(max_index):
            device, cap, frame = self._probe_capture(index, backends)

            if cap is not None and frame is not None and self._capture is None:
                self._logger.info("Testing Camera %d...", index)
                self._finalise_open(index, cap, frame, device.backend)
                self._logger.info(
                    "Camera %d selected.  Resolution: %dx%d",
                    index,
                    device.resolution_width,
                    device.resolution_height,
                )
            elif cap is not None:
                _safe_capture_release(cap)

            self._camera_list.append(device)

        if self._capture is None:
            self._logger.warning("No working camera found during discovery.")

        return list(self._camera_list)

    def open_camera(self, index: int) -> bool:
        """Open *index* — only needed if the user switches camera.

        If a camera is already open, it is closed first.  The
        configured backend is tried first, then ``ANY`` as fallback.

        Raises:
            CameraError: If the index is negative or no backend can
                open the camera.
        """
        if index < 0:
            raise CameraError(
                f"Camera index must be non-negative, got {index}."
            )
        self.close_camera()

        backends = _backend_order(self._config)
        for backend in backends:
            _warmup_camera(index)
            cap = cv2.VideoCapture(index, backend)
            if not cap.isOpened():
                cap.release()
                self._logger.debug(
                    "Camera %d did not respond to %s.",
                    index, backend.name.lower(),
                )
                continue

            ret, frame = cap.read()
            if not ret or frame is None or frame.size == 0:
                cap.release()
                self._logger.debug(
                    "Camera %d opened with %s but produced no frame.",
                    index, backend.name.lower(),
                )
                continue

            self._finalise_open(index, cap, frame, backend)
            return True

        raise CameraError(
            f"Camera {index} did not respond to any available backend."
        )

    def close_camera(self) -> None:
        if self._capture is not None:
            name = (
                self._current_device.name
                if self._current_device
                else "unknown"
            )
            _safe_capture_release(self._capture)
            self._logger.info("Camera '%s' released.", name)
            self._capture = None
            self._current_device = None
            self._fps_monitor.reset()

    def switch_camera(self, index: int) -> bool:
        self.close_camera()
        return self.open_camera(index)

    def reconnect(self) -> bool:
        """Re-open the camera that was most recently active.

        Used after a device disconnect to restore the capture pipeline
        when the camera comes back.  Returns True if the camera was
        re-opened successfully.
        """
        index = self._last_opened_index
        if index < 0:
            return False
        try:
            ok = self.open_camera(index)
            if ok:
                self._logger.info("Camera %d reconnected.", index)
            return ok
        except CameraError as e:
            self._logger.warning("Reconnect failed for Camera %d: %s", index, e)
            return False

    def get_frame(self) -> Optional[NDArray[np.uint8]]:
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
        except cv2.error as e:
            self._logger.error("OpenCV error reading frame: %s", e)
            raise CameraError(f"OpenCV error reading frame: {e}", cause=e)
        except Exception as e:
            raise CameraError(f"Error reading frame: {e}", cause=e)

    def get_current_camera(self) -> Optional[CameraDevice]:
        return self._current_device

    def get_current_fps(self) -> float:
        return self._fps_monitor.current_fps

    def get_average_fps(self) -> float:
        return self._fps_monitor.average_fps

    def get_min_fps(self) -> float:
        return self._fps_monitor.min_fps

    def get_max_fps(self) -> float:
        return self._fps_monitor.max_fps

    def get_fps(self) -> float:
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

    def _probe_capture(
        self,
        index: int,
        backends: Optional[List[Backend]] = None,
    ) -> tuple[CameraDevice, Optional[cv2.VideoCapture], Optional[NDArray[np.uint8]]]:
        """Open *index* and read one frame, trying each backend in turn.

        Returns ``(device, capture, frame)`` where *capture* and *frame*
        are ``None`` if the camera did not respond on any backend.
        """
        candidates = backends or _backend_order(self._config)

        for backend in candidates:
            _warmup_camera(index)
            try:
                cap = cv2.VideoCapture(index, backend)
                if not cap.isOpened():
                    cap.release()
                    self._logger.debug(
                        "Probe Camera %d: %s did not respond.",
                        index, backend.name.lower(),
                    )
                    continue

                ret, frame = cap.read()
                if ret and frame is not None and frame.size > 0:
                    h, w = frame.shape[:2]
                    name = _get_camera_name(cap, index)
                    fps = _safe_capture_property(cap, cv2.CAP_PROP_FPS, 0.0)
                    device = CameraDevice(
                        index=index, name=name,
                        backend=backend, is_available=True,
                        resolution_width=max(w, 1),
                        resolution_height=max(h, 1), fps=fps,
                    )
                    # Discard the junk frame that follows the first successful
                    # read (DSHOW on this camera returns ret=False on read 1).
                    cap.read()
                    return device, cap, frame

                cap.release()
                self._logger.debug(
                    "Probe Camera %d: %s produced no valid frame.",
                    index, backend.name.lower(),
                )
            except cv2.error as e:
                self._logger.debug(
                    "Probe Camera %d: %s raised cv2.error: %s",
                    index, backend.name.lower(), e,
                )
            except Exception as e:
                self._logger.debug(
                    "Probe Camera %d: %s raised unexpected error: %s",
                    index, backend.name.lower(), e,
                )

        return (
            CameraDevice(
                index=index, name=f"Camera {index}",
                backend=candidates[0], is_available=False,
            ),
            None, None,
        )

    def _finalise_open(
        self,
        index: int,
        cap: cv2.VideoCapture,
        frame: NDArray[np.uint8],
        backend: Backend,
    ) -> None:
        """Configure *cap* as the active capture and store metadata."""
        h, w = frame.shape[:2]
        camera_name = _get_camera_name(cap, index)
        requested_w, requested_h = self._resolve_resolution()

        # Only set resolution if different from the camera's default.
        if (w != requested_w or h != requested_h) and requested_w > 0 and requested_h > 0:
            _safe_capture_set(cap, cv2.CAP_PROP_FRAME_WIDTH, requested_w)
            _safe_capture_set(cap, cv2.CAP_PROP_FRAME_HEIGHT, requested_h)
            retry = cap.read()
            if retry[0] and retry[1] is not None:
                h, w = retry[1].shape[:2]

        # Read FPS from camera — skip expensive set() calls.
        actual_fps = _safe_capture_property(cap, cv2.CAP_PROP_FPS, 0.0)
        if actual_fps <= 0.0:
            actual_fps = 0.0

        self._capture = cap
        self._backend = backend
        self._last_opened_index = index

        self._current_device = CameraDevice(
            index=index,
            name=camera_name,
            backend=backend,
            is_available=True,
            resolution_width=max(w, 1),
            resolution_height=max(h, 1),
            fps=actual_fps,
        )
        self._fps_monitor.reset()

        self._logger.info(
            "Camera %d active: %dx%d @ %.1f FPS "
            "(requested: %dx%d @ %.1f FPS, backend=%s).",
            index,
            self._current_device.resolution_width,
            self._current_device.resolution_height,
            self._current_device.fps,
            requested_w, requested_h,
            self._config.fps,
            backend.name.lower(),
        )

    def _resolve_backend(self) -> Backend:
        try:
            return Backend.from_string(self._config.backend)
        except ValueError:
            logging.getLogger(self.__class__.__name__).warning(
                "Unknown backend '%s' in config. Falling back to DSHOW.",
                self._config.backend,
            )
            return Backend.DIRECTSHOW

    def _resolve_resolution(self) -> tuple[int, int]:
        preset = self._config.resolution_preset
        if preset:
            resolved = RESOLUTION_PRESETS.get(preset)
            if resolved is not None:
                return resolved
        return self._config.width, self._config.height