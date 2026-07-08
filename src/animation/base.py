"""Animation module base abstractions for the VisionMoCap application."""

import logging

from src.config.manager import AnimationConfig
from src.core.interfaces import AnimationExporter
from src.core.models import MotionData


class AnimationExporterBase(AnimationExporter):
    """Base class for animation exporter implementations.

    Provides common configuration for exporting processed MotionData to
    various animation formats. Subclasses must implement the export() method.

    Attributes:
        config: The AnimationConfig instance used to configure export.
    """

    def __init__(self, config: AnimationConfig) -> None:
        self._config = config
        self._logger = logging.getLogger(self.__class__.__name__)

    @property
    def config(self) -> AnimationConfig:
        """Return the animation exporter configuration."""
        return self._config

    def export(self, motion_data: MotionData, output_path: str) -> None:
        """Export motion data. Must be implemented by subclasses.

        Args:
            motion_data: Processed MotionData to export.
            output_path: Destination path for the exported animation file.
        """
        raise NotImplementedError("Subclasses must implement export().")

    def validate_environment(self) -> bool:
        """Validate that the export environment is properly configured."""
        self._logger.debug(
            "Animation environment validation not implemented; returning True."
        )
        return True
