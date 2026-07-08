"""Core interfaces and abstract base classes for the VisionMoCap pipeline."""

from abc import ABC, abstractmethod
from typing import Any, Optional

import numpy as np
from numpy.typing import NDArray

from src.core.models import MotionData


class VideoSource(ABC):
    """Abstract interface for video input sources.

    Defines the contract for capturing video frames from any source,
    such as webcams, video files, or IP cameras.
    """

    @abstractmethod
    def open(self) -> None:
        """Open the video source and prepare it for frame capture."""

    @abstractmethod
    def read(self) -> Optional[NDArray[np.uint8]]:
        """Read the next frame from the video source.

        Returns:
            The captured frame as a numpy array of shape (H, W, 3) in BGR
            order, or None if no frame is available or the stream ended.
        """

    @abstractmethod
    def release(self) -> None:
        """Release the video source and free associated resources."""

    @property
    @abstractmethod
    def is_opened(self) -> bool:
        """Return whether the video source is currently open."""

    @property
    @abstractmethod
    def frame_width(self) -> int:
        """Return the frame width in pixels."""

    @property
    @abstractmethod
    def frame_height(self) -> int:
        """Return the frame height in pixels."""

    @property
    @abstractmethod
    def fps(self) -> float:
        """Return the frame rate of the video source in frames per second."""


class PoseEstimator(ABC):
    """Abstract interface for pose estimation backends.

    Defines the contract for estimating human poses from image frames
    using various pose estimation models.
    """

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the pose estimation model and allocate resources."""

    @abstractmethod
    def estimate(self, frame: NDArray[np.uint8]) -> Any:
        """Estimate poses in the given frame.

        Args:
            frame: Input image frame as a numpy array.

        Returns:
            Raw pose estimation result whose structure depends on the
            specific backend implementation.
        """

    @abstractmethod
    def shutdown(self) -> None:
        """Release resources held by the pose estimator."""


class MotionProcessor(ABC):
    """Abstract interface for motion data processing.

    Defines the contract for processing raw pose estimation data
    into structured motion data suitable for animation.
    """

    @abstractmethod
    def process(self, pose_data: Any) -> MotionData:
        """Process raw pose data into structured motion data.

        Args:
            pose_data: Raw pose data from the pose estimator.

        Returns:
            Structured MotionData containing the processed pose sequence.
        """

    @abstractmethod
    def reset(self) -> None:
        """Reset the processor state for a new capture session."""


class AnimationExporter(ABC):
    """Abstract interface for animation export targets.

    Defines the contract for exporting processed motion data
    to various animation formats or external applications.
    """

    @abstractmethod
    def export(self, motion_data: MotionData, output_path: str) -> None:
        """Export motion data to the specified output path.

        Args:
            motion_data: Processed MotionData to export.
            output_path: Destination path for the exported animation file.
        """

    @abstractmethod
    def validate_environment(self) -> bool:
        """Validate that the export environment is properly configured.

        Returns:
            True if the environment is valid and export can proceed,
            False otherwise.
        """


class FrameRenderer(ABC):
    """Abstract interface for rendering annotated frames.

    Defines the contract for rendering visual annotations such as
    skeleton overlays on video frames.
    """

    @abstractmethod
    def render(
        self, frame: NDArray[np.uint8], pose_data: Any
    ) -> NDArray[np.uint8]:
        """Render pose annotations on the given frame.

        Args:
            frame: Original video frame.
            pose_data: Pose data to render as visual overlay.

        Returns:
            Annotated frame with pose visualizations drawn.
        """

    @abstractmethod
    def initialize_display(self, window_name: str) -> None:
        """Initialize the display window for rendering.

        Args:
            window_name: Title string for the display window.
        """

    @abstractmethod
    def destroy_display(self) -> None:
        """Destroy the display window and clean up rendering resources."""
