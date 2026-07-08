"""Camera module base abstractions for the VisionMoCap application."""

import logging
from typing import Optional

import numpy as np
from numpy.typing import NDArray

from src.config.manager import CameraConfig
from src.core.interfaces import VideoSource


class CameraBase(VideoSource):
    """Base class for camera implementations.

    Provides default lifecycle management for opening, reading, and
    releasing a video source. Subclasses must implement the read()
    method and may override open() and release() as needed.

    Attributes:
        config: The CameraConfig instance used to configure this camera.
    """

    def __init__(self, config: CameraConfig) -> None:
        self._config = config
        self._logger = logging.getLogger(self.__class__.__name__)
        self._opened: bool = False

    @property
    def config(self) -> CameraConfig:
        """Return the camera configuration."""
        return self._config

    def open(self) -> None:
        """Open the camera device and mark it as active."""
        self._opened = True
        self._logger.info(
            "Camera opened (device_id=%d, %dx%d @ %.1f fps).",
            self._config.device_id,
            self._config.width,
            self._config.height,
            self._config.fps,
        )

    def release(self) -> None:
        """Release the camera device and mark it as inactive."""
        self._opened = False
        self._logger.info("Camera released.")

    @property
    def is_opened(self) -> bool:
        """Return whether the camera is currently open."""
        return self._opened

    def read(self) -> Optional[NDArray[np.uint8]]:
        """Read the next frame. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement read().")

    @property
    def frame_width(self) -> int:
        """Return the configured frame width in pixels."""
        return self._config.width

    @property
    def frame_height(self) -> int:
        """Return the configured frame height in pixels."""
        return self._config.height

    @property
    def fps(self) -> float:
        """Return the configured frame rate in frames per second."""
        return self._config.fps
