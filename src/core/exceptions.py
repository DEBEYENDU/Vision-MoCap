"""Custom exception hierarchy for the VisionMoCap application."""

from typing import Optional


class VisionMoCapError(Exception):
    """Base exception for all VisionMoCap application errors."""

    def __init__(
        self,
        message: str = "An error occurred in VisionMoCap AI.",
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message)
        self.cause = cause


class ConfigurationError(VisionMoCapError):
    """Raised when configuration loading or validation fails."""


class CameraError(VisionMoCapError):
    """Raised when camera operations fail."""


class PoseEstimationError(VisionMoCapError):
    """Raised when pose estimation fails."""


class MotionProcessingError(VisionMoCapError):
    """Raised when motion data processing fails."""


class AnimationExportError(VisionMoCapError):
    """Raised when animation export fails."""


class RetargetingError(VisionMoCapError):
    """Raised when motion retargeting fails."""


class BlenderIntegrationError(VisionMoCapError):
    """Raised when Blender integration fails."""


class GUIError(VisionMoCapError):
    """Raised when GUI operations fail."""
