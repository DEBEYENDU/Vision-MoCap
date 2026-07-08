"""Blender integration module base abstractions for the VisionMoCap application."""

import logging

from src.config.manager import BlenderConfig
from src.core.interfaces import AnimationExporter
from src.core.models import MotionData


class BlenderExporterBase(AnimationExporter):
    """Base class for Blender export implementations.

    Provides common configuration for exporting motion data into Blender.
    Subclasses must implement the export() method to handle the specific
    Blender communication protocol (Python API, command-line, or add-on).

    Attributes:
        config: The BlenderConfig instance used to configure integration.
    """

    def __init__(self, config: BlenderConfig) -> None:
        self._config = config
        self._logger = logging.getLogger(self.__class__.__name__)

    @property
    def config(self) -> BlenderConfig:
        """Return the Blender exporter configuration."""
        return self._config

    def export(self, motion_data: MotionData, output_path: str) -> None:
        """Export motion data to Blender. Must be implemented by subclasses.

        Args:
            motion_data: Processed MotionData to export.
            output_path: Destination path for the exported animation file.
        """
        raise NotImplementedError("Subclasses must implement export().")

    def validate_environment(self) -> bool:
        """Check whether the Blender environment is properly configured."""
        self._logger.debug(
            "Blender environment validation not implemented; returning True."
        )
        return True
