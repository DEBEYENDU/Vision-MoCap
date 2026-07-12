"""Metadata model for a completed recording session.

Carries summary statistics and ISO-formatted date alongside the raw
frame count and average metrics that are already stored in the
MotionSequence.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict


@dataclass
class RecordingMetadata:
    """Summary metadata attached to every saved recording.

    This dataclass is serialised alongside the frame data as a
    top-level ``"metadata"`` key in the export JSON.  It is purely
    informational and never used for deserialisation of the motion
    data itself.

    Attributes:
        date_iso: ISO-8601 UTC timestamp of when recording stopped.
        duration_seconds: Wall-clock duration of the recording (including
            pauses, since it measures real elapsed time).
        average_fps: Mean frame rate across the recording.
        average_confidence: Mean pose tracking confidence across all
            frames (0.0 if no valid detections).
        frame_count: Total number of PoseResult frames captured.
        camera_index: Device index of the camera used.
    """

    date_iso: str = ""
    duration_seconds: float = 0.0
    average_fps: float = 0.0
    average_confidence: float = 0.0
    frame_count: int = 0
    camera_index: int = -1

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable dictionary."""
        return asdict(self)

    @classmethod
    def build(
        cls,
        *,
        duration_seconds: float,
        average_fps: float,
        average_confidence: float,
        frame_count: int,
        camera_index: int,
    ) -> RecordingMetadata:
        """Factory that auto-sets the ISO date.

        Args:
            duration_seconds: Wall-clock duration.
            average_fps: Mean FPS.
            average_confidence: Mean confidence.
            frame_count: Number of frames.
            camera_index: Camera device index.

        Returns:
            A fully populated RecordingMetadata.
        """
        return cls(
            date_iso=datetime.now(timezone.utc).isoformat(),
            duration_seconds=duration_seconds,
            average_fps=average_fps,
            average_confidence=average_confidence,
            frame_count=frame_count,
            camera_index=camera_index,
        )