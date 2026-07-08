"""Frame management for the VisionMoCap application.

Provides timestamping, frame counting, optional resizing, optional colour
conversion, and a fixed-size frame buffer between the camera and pose
detection pipeline.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from typing import Deque, Optional, Tuple

import cv2
import numpy as np
from numpy.typing import NDArray


class FrameManager:
    """Processes raw camera frames before they reach the pose detector.

    Each frame is assigned a monotonically increasing frame number and
    a high-resolution timestamp. Optional processing steps — resizing
    and colour conversion — can be enabled through the constructor.

    A fixed-size circular buffer of recent processed frames is maintained
    for deferred access.

    Attributes:
        frame_number: Current frame count (0 before the first frame).
        frame_width: Width of the most recently processed frame in pixels.
        frame_height: Height of the most recently processed frame in pixels.
        timestamp: ``time.perf_counter()`` value of the most recent frame.
        buffer_size: Maximum number of frames retained in the circular buffer.
    """

    def __init__(
        self,
        resize: Optional[Tuple[int, int]] = None,
        color_conversion: Optional[int] = None,
        buffer_size: int = 1,
    ) -> None:
        """
        Args:
            resize: Desired ``(width, height)`` or None to keep original size.
            color_conversion: OpenCV colour conversion constant e.g.
                ``cv2.COLOR_BGR2RGB``, or None to keep BGR.
            buffer_size: Maximum number of frames to keep in the circular
                buffer. 1 preserves only the latest frame.
        """
        self._resize = resize
        self._color_conversion = color_conversion
        self._buffer: Deque[NDArray[np.uint8]] = deque(maxlen=max(buffer_size, 1))

        self._frame_number: int = 0
        self._frame_width: int = 0
        self._frame_height: int = 0
        self._timestamp: float = 0.0
        self._logger = logging.getLogger(self.__class__.__name__)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(self, frame: NDArray[np.uint8]) -> NDArray[np.uint8]:
        """Process a raw camera frame.

     Steps performed in order:
        1. Increment frame number.
        2. Record frame dimensions.
        3. Record timestamp.
        4. Optionally resize.
        5. Optionally convert colour space.
        6. Store into the circular buffer.

        Args:
            frame: Raw BGR frame from the camera.

        Returns:
            The processed frame (may be a new array if resized/converted).
        """
        self._frame_number += 1
        self._frame_height, self._frame_width = frame.shape[:2]
        self._timestamp = time.perf_counter()

        result: NDArray[np.uint8] = frame

        if self._resize is not None:
            result = cv2.resize(result, self._resize, interpolation=cv2.INTER_LINEAR)
            self._frame_height, self._frame_width = result.shape[:2]

        if self._color_conversion is not None:
            result = cv2.cvtColor(result, self._color_conversion)

        self._buffer.append(result)
        return result

    def reset(self) -> None:
        """Reset the frame counter and clear the buffer.

        Dimensions and timestamp are zeroed.
        """
        self._frame_number = 0
        self._frame_width = 0
        self._frame_height = 0
        self._timestamp = 0.0
        self._buffer.clear()
        self._logger.debug("FrameManager reset.")

    def get_buffer(self) -> Tuple[NDArray[np.uint8], ...]:
        """Return a snapshot of the current frame buffer.

        Returns:
            Tuple of buffered frames from oldest to newest.
        """
        return tuple(self._buffer)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def frame_number(self) -> int:
        """Monotonically increasing frame counter (0 before first frame)."""
        return self._frame_number

    @property
    def frame_width(self) -> int:
        """Width of the most recently processed frame in pixels."""
        return self._frame_width

    @property
    def frame_height(self) -> int:
        """Height of the most recently processed frame in pixels."""
        return self._frame_height

    @property
    def timestamp(self) -> float:
        """``time.perf_counter()`` value when the last frame was processed."""
        return self._timestamp

    @property
    def buffer_size(self) -> int:
        """Maximum capacity of the circular frame buffer."""
        return self._buffer.maxlen

    @buffer_size.setter
    def buffer_size(self, size: int) -> None:
        """Resize the buffer (discards existing contents)."""
        self._buffer = deque(maxlen=max(size, 1))
