"""Pose estimation module base abstractions for the VisionMoCap application."""

import logging
from typing import Any

import numpy as np
from numpy.typing import NDArray

from src.config.manager import PoseConfig
from src.core.interfaces import PoseEstimator


class PoseEstimatorBase(PoseEstimator):
    """Base class for pose estimator implementations.

    Provides common configuration and lifecycle management for pose
    estimation backends. Subclasses must implement the estimate() method
    and may override initialize() and shutdown() as needed.

    Attributes:
        config: The PoseConfig instance used to configure the estimator.
    """

    def __init__(self, config: PoseConfig) -> None:
        self._config = config
        self._logger = logging.getLogger(self.__class__.__name__)
        self._initialized: bool = False

    @property
    def config(self) -> PoseConfig:
        """Return the pose estimator configuration."""
        return self._config

    def initialize(self) -> None:
        """Initialize the pose estimation model and allocate resources."""
        self._initialized = True
        self._logger.info(
            "Pose estimator initialized (model_complexity=%d).",
            self._config.model_complexity,
        )

    def shutdown(self) -> None:
        """Shut down the pose estimation model and release resources."""
        self._initialized = False
        self._logger.info("Pose estimator shut down.")

    def estimate(self, frame: NDArray[np.uint8]) -> Any:
        """Run pose estimation. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement estimate().")
