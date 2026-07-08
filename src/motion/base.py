"""Motion processing module base abstractions for the VisionMoCap application."""

import logging
from typing import Any

from src.config.manager import MotionConfig
from src.core.interfaces import MotionProcessor
from src.core.models import MotionData


class MotionProcessorBase(MotionProcessor):
    """Base class for motion processor implementations.

    Provides common configuration and state management for processing
    raw pose data into structured MotionData. Subclasses must implement
    the process() method.

    Attributes:
        config: The MotionConfig instance used to configure processing.
    """

    def __init__(self, config: MotionConfig) -> None:
        self._config = config
        self._logger = logging.getLogger(self.__class__.__name__)

    @property
    def config(self) -> MotionConfig:
        """Return the motion processor configuration."""
        return self._config

    def reset(self) -> None:
        """Reset the processor state for a new capture session."""
        self._logger.debug("Motion processor state reset.")

    def process(self, pose_data: Any) -> MotionData:
        """Process pose data into structured motion data.

        Must be implemented by subclasses.

        Args:
            pose_data: Raw pose data from the pose estimator.

        Returns:
            Structured MotionData instance.
        """
        raise NotImplementedError("Subclasses must implement process().")
