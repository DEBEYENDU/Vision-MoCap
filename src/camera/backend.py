"""OpenCV backend abstraction for the VisionMoCap application."""

from __future__ import annotations

from enum import IntEnum

import cv2


class Backend(IntEnum):
    """Cross-platform OpenCV backend abstraction.

    Maps human-readable backend names to OpenCV VideoCapture backend
    constants. Supports Windows, Linux, and macOS backends.

    Usage::

        cap = cv2.VideoCapture(index, Backend.DIRECTSHOW)
    """

    DIRECTSHOW = cv2.CAP_DSHOW
    MEDIA_FOUNDATION = cv2.CAP_MSMF
    V4L2 = cv2.CAP_V4L2
    AVFOUNDATION = cv2.CAP_AVFOUNDATION

    @classmethod
    def from_string(cls, name: str) -> Backend:
        """Resolve a backend name string to a Backend enum member.

        The lookup is case-insensitive. Spaces and hyphens are replaced
        with underscores before matching.

        Args:
            name: Backend name (e.g. ``"directshow"``, ``"v4l2"``,
                  ``"media_foundation"``, ``"avfoundation"``).

        Returns:
            The matching Backend member.

        Raises:
            ValueError: If *name* does not match any known backend.
        """
        normalized = name.strip().lower().replace("-", "_").replace(" ", "_")
        try:
            return cls[normalized.upper()]
        except KeyError:
            valid = ", ".join(m.name.lower() for m in cls)
            raise ValueError(
                f"Unknown backend '{name}'. Valid options: {valid}."
            )
