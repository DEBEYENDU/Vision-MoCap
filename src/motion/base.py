"""Motion processing module base abstractions for the VisionMoCap application."""

import logging
from abc import ABC, abstractmethod
from typing import Any, List

from src.config.manager import MotionConfig
from src.core.interfaces import MotionProcessor
from src.core.models import MotionData
from src.motion.motion_sequence import MotionSequence
from src.pose.pose_result import Landmark, PoseResult


def deep_copy_pose_result(pose_result: PoseResult) -> PoseResult:
    """Create an independent deep copy of a PoseResult.

    Landmark lists are reconstructed so that modifications to the copy
    never affect the original.

    Args:
        pose_result: The PoseResult to copy.

    Returns:
        A new PoseResult with fully independent landmark lists.
    """
    return PoseResult(
        timestamp=pose_result.timestamp,
        landmarks=[
            Landmark(x=lm.x, y=lm.y, z=lm.z, visibility=lm.visibility)
            for lm in pose_result.landmarks
        ],
        world_landmarks=[
            Landmark(x=lm.x, y=lm.y, z=lm.z, visibility=lm.visibility)
            for lm in pose_result.world_landmarks
        ],
        confidence=pose_result.confidence,
        frame_width=pose_result.frame_width,
        frame_height=pose_result.frame_height,
        pose_detected=pose_result.pose_detected,
    )


def deep_copy_sequence(sequence: MotionSequence) -> MotionSequence:
    """Create an independent deep copy of a MotionSequence.

    All PoseResult objects and their landmark lists are duplicated so
    that filtering operations can mutate the copy without side effects.

    Args:
        sequence: The MotionSequence to copy.

    Returns:
        A new MotionSequence sharing no mutable state with the original.
    """
    return MotionSequence(
        pose_results=[
            deep_copy_pose_result(pr) for pr in sequence.pose_results
        ],
        start_time=sequence.start_time,
        end_time=sequence.end_time,
        total_frames=sequence.total_frames,
        average_fps=sequence.average_fps,
        duration=sequence.duration,
    )


class SequenceProcessor(ABC):
    """Abstract base for all sequence-level processing operations.

    Every subclass must implement :meth:`process` which receives a
    MotionSequence and returns a **new** MotionSequence. Implementations
    must not mutate the input sequence.
    """

    @property
    def name(self) -> str:
        """Human-readable processor name (class name by default)."""
        return self.__class__.__name__

    @abstractmethod
    def process(self, sequence: MotionSequence) -> MotionSequence:
        """Process a motion sequence and return a new one.

        Args:
            sequence: Input MotionSequence (must not be mutated).

        Returns:
            A new MotionSequence with the processing applied.
        """
        raise NotImplementedError

    def _log_start(self, logger: logging.Logger, count: int) -> None:
        logger.debug(
            "%s processing %d frames.", self.name, count
        )

    def _log_done(self, logger: logging.Logger, count: int) -> None:
        logger.debug(
            "%s finished on %d frames.", self.name, count
        )


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
