"""Motion processing subsystem for the VisionMoCap application.

Provides the MotionProcessor orchestrator that chains multiple
SequenceProcessor operations into a processing pipeline.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from src.config.manager import MotionConfig
from src.core.exceptions import MotionProcessingError
from src.motion.base import (
    SequenceProcessor,
    deep_copy_pose_result,
    deep_copy_sequence,
)
from src.motion.interpolator import LinearInterpolator
from src.motion.motion_sequence import MotionSequence
from src.pose.pose_result import Landmark, PoseResult


class MotionProcessor:
    """Orchestrates the motion processing pipeline.

    Builds a default pipeline in the recommended order::

        Outlier Removal -> Interpolation -> Moving Average -> Exponential Smoothing

    Custom pipelines may be injected via the *processors* constructor
    argument (Dependency Injection).

    Usage::

        processor = MotionProcessor(config.motion)
        cleaned = processor.process(raw_sequence)
    """

    def __init__(
        self,
        config: Optional[MotionConfig] = None,
        processors: Optional[List[SequenceProcessor]] = None,
    ) -> None:
        self._config = config or MotionConfig()
        self._logger = logging.getLogger(self.__class__.__name__)
        if processors is not None:
            self._processors: List[SequenceProcessor] = list(processors)
        else:
            self._processors = self._build_default_pipeline()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(self, sequence: MotionSequence) -> MotionSequence:
        """Run the full processing pipeline on a MotionSequence.

        Each processor receives the output of the previous one, forming
        a chain. The input sequence is never mutated.

        Args:
            sequence: The raw recorded MotionSequence.

        Returns:
            A fully processed MotionSequence.

        Raises:
            MotionProcessingError: If any processor fails.
        """
        if not sequence.pose_results:
            self._logger.warning("Empty sequence received; returning as-is.")
            return deep_copy_sequence(sequence)
        self._logger.info(
            "Processing %d frames through %d stage(s): [%s].",
            sequence.total_frames,
            len(self._processors),
            " -> ".join(p.name for p in self._processors),
        )
        result = sequence
        for processor in self._processors:
            try:
                result = processor.process(result)
            except MotionProcessingError:
                raise
            except Exception as e:
                raise MotionProcessingError(
                    f"Stage '{processor.name}' failed: {e}",
                    cause=e,
                )
        self._logger.info("Processing pipeline complete.")
        return result

    def add_processor(self, processor: SequenceProcessor) -> None:
        """Append a processor to the end of the pipeline.

        Args:
            processor: A SequenceProcessor instance to add.
        """
        self._processors.append(processor)
        self._logger.debug("Added processor '%s'.", processor.name)

    def insert_processor(self, index: int, processor: SequenceProcessor) -> None:
        """Insert a processor at a specific pipeline position.

        Args:
            index: Zero-based insertion position.
            processor: A SequenceProcessor instance to insert.
        """
        self._processors.insert(index, processor)
        self._logger.debug(
            "Inserted processor '%s' at position %d.", processor.name, index
        )

    def remove_processor(self, processor: SequenceProcessor) -> bool:
        """Remove a processor from the pipeline.

        Args:
            processor: The processor instance to remove.

        Returns:
            True if the processor was found and removed, False otherwise.
        """
        if processor in self._processors:
            self._processors.remove(processor)
            self._logger.debug("Removed processor '%s'.", processor.name)
            return True
        return False

    def clear_pipeline(self) -> None:
        """Remove all processors from the pipeline."""
        self._processors.clear()
        self._logger.debug("Pipeline cleared.")

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def pipeline(self) -> List[SequenceProcessor]:
        """A snapshot of the current processing pipeline."""
        return list(self._processors)

    @property
    def config(self) -> MotionConfig:
        """The MotionConfig used to build the default pipeline."""
        return self._config

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_default_pipeline(self) -> List[SequenceProcessor]:
        """Construct the default four-stage processing pipeline."""
        from src.motion.filters import (
            ExponentialSmoothingFilter,
            MovingAverageFilter,
            OutlierRemovalFilter,
        )

        return [
            OutlierRemovalFilter(self._config),
            LinearInterpolator(self._config),
            MovingAverageFilter(self._config),
            ExponentialSmoothingFilter(self._config),
        ]
