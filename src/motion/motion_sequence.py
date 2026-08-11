"""Motion sequence data model for the VisionMoCap application.

Provides a serialisable container for recorded pose data with timing
metadata. Includes JSON serialisation helpers for persistence.

FPS integrity
-------------
``average_fps`` is the single source of truth for frame-rate timing
across the application (playback, animation, export).  A sequence must
never expose an invalid frame rate (zero, negative, NaN, infinity).
The dataclass :meth:`__post_init__` repairs an invalid ``average_fps``
at construction time via :meth:`resolve_average_fps`:

1. A stored valid FPS is preserved.
2. Otherwise FPS is derived from the real per-frame timestamps:
   ``(frame_count - 1) / (last_timestamp - first_timestamp)``.
3. If no usable timing information exists, the documented fallback
   (:data:`DEFAULT_FPS`) is used and a warning is logged.
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from src.pose.pose_result import Landmark, PoseResult

#: Fallback frame rate used when a recording carries no usable timing
#: information.  Documented in the user guide and log messages.
DEFAULT_FPS: float = 30.0

_LOGGER = logging.getLogger(__name__)

_FALLBACK_WARNING = (
    "Recording has no valid timing information. Using fallback FPS: %.1f"
)


def is_valid_fps(value: Any) -> bool:
    """Return True if *value* is a usable frame rate.

    A valid FPS must be greater than zero, finite, and not NaN.
    """
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value > 0.0
    )


def fps_from_timestamps(timestamps: Sequence[Any]) -> Optional[float]:
    """Derive an average frame rate from per-frame timestamps.

    FPS is computed as ``(frame_count - 1) / (last - first)`` over the
    finite timestamps in the sequence.

    Args:
        timestamps: One timestamp per recorded frame, in order.

    Returns:
        A positive finite FPS, or None when it cannot be computed
        (fewer than two frames, duplicate timestamps, invalid or
        non-finite values, or a non-positive time span).
    """
    finite = [
        t for t in timestamps
        if isinstance(t, (int, float)) and math.isfinite(t)
    ]
    if len(finite) < 2:
        return None
    span = finite[-1] - finite[0]
    if span <= 0.0 or not math.isfinite(span):
        return None
    return (len(finite) - 1) / span


@dataclass
class MotionSequence:
    """Container for a recorded sequence of pose detections with timing.

    Attributes:
        pose_results: Ordered list of PoseResult objects from the session.
        start_time: Monotonic timestamp when recording began (seconds).
        end_time: Monotonic timestamp when recording ended (seconds).
        total_frames: Number of pose frames in the sequence.
        average_fps: Mean frame rate over the recording duration.
        duration: Total recording duration in seconds.
    """

    pose_results: List[PoseResult] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0
    total_frames: int = 0
    average_fps: float = 0.0
    duration: float = 0.0

    # ------------------------------------------------------------------
    # Construction-time integrity repair
    # ------------------------------------------------------------------

    def __post_init__(self) -> None:
        """Normalise timing fields so the sequence is always usable.

        * ``average_fps`` is repaired via :meth:`resolve_average_fps`
          (preserve valid values, derive from timestamps, or fall back).
        * ``total_frames`` is reconciled with the actual pose list.
        * ``duration`` is derived from timestamps (or FPS) when missing.
        """
        if not is_valid_fps(self.average_fps):
            self.resolve_average_fps()

        if self.pose_results and self.total_frames != len(self.pose_results):
            self.total_frames = len(self.pose_results)

        if self.pose_results and self.duration <= 0.0:
            derived = fps_from_timestamps(
                [pr.timestamp for pr in self.pose_results]
            )
            if derived is not None:
                self.duration = (self.total_frames - 1) / derived
            elif is_valid_fps(self.average_fps):
                self.duration = self.total_frames / self.average_fps

    # ------------------------------------------------------------------
    # FPS resolution (central timing mechanism)
    # ------------------------------------------------------------------

    def resolve_average_fps(self) -> float:
        """Resolve a valid frame rate for this sequence.

        Resolution order:

        1. If the stored ``average_fps`` is already valid it is
           preserved and returned.
        2. Otherwise FPS is computed from the real per-frame
           timestamps (``(n-1) / (last - first)``).
        3. If no usable timing information exists, the documented
           fallback :data:`DEFAULT_FPS` is applied and a warning is
           logged — invalid recording data is never hidden silently.

        Returns:
            The resolved (positive, finite) frame rate.
        """
        if is_valid_fps(self.average_fps):
            return self.average_fps

        derived = fps_from_timestamps(
            [pr.timestamp for pr in self.pose_results]
        )
        if derived is not None:
            self.average_fps = derived
            _LOGGER.info(
                "Derived FPS %.2f from %d frame timestamp(s).",
                derived, len(self.pose_results),
            )
            return derived

        self.average_fps = DEFAULT_FPS
        _LOGGER.warning(_FALLBACK_WARNING, DEFAULT_FPS)
        return self.average_fps

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Convert this sequence to a JSON-serialisable dictionary."""
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_frames": self.total_frames,
            "average_fps": self.average_fps,
            "duration": self.duration,
            "pose_results": [_pose_result_to_dict(pr) for pr in self.pose_results],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MotionSequence:
        """Create a MotionSequence from a dictionary.

        Args:
            data: Dictionary previously produced by :meth:`to_dict`.

        Returns:
            A new MotionSequence with deserialised pose data.
        """
        return cls(
            start_time=data.get("start_time", 0.0),
            end_time=data.get("end_time", data.get("start_time", 0.0)),
            total_frames=data.get("total_frames", len(data["pose_results"])),
            average_fps=data.get("average_fps", 0.0),
            duration=data.get("duration", 0.0),
            pose_results=[
                _dict_to_pose_result(pr) for pr in data["pose_results"]
            ],
        )

    def save_json(self, path: Path) -> None:
        """Serialise this sequence to a JSON file.

        Args:
            path: Destination file path. Parent directories are created
                  automatically.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            f.write("\n")

    @classmethod
    def load_json(cls, path: Path) -> MotionSequence:
        """Deserialise a sequence from a JSON file.

        Args:
            path: Source file path.

        Returns:
            A new MotionSequence reconstructed from the file.
        """
        with open(path, "r", encoding="utf-8") as f:
            data: Dict[str, Any] = json.load(f)
        return cls.from_dict(data)


# ------------------------------------------------------------------
# Serialisation helpers for PoseResult / Landmark
# ------------------------------------------------------------------


def _pose_result_to_dict(pr: PoseResult) -> Dict[str, Any]:
    """Convert a single PoseResult to a JSON-safe dictionary."""
    return {
        "timestamp": pr.timestamp,
        "landmarks": [
            {"x": lm.x, "y": lm.y, "z": lm.z, "visibility": lm.visibility}
            for lm in pr.landmarks
        ],
        "world_landmarks": [
            {"x": lm.x, "y": lm.y, "z": lm.z, "visibility": lm.visibility}
            for lm in pr.world_landmarks
        ],
        "confidence": pr.confidence,
        "frame_width": pr.frame_width,
        "frame_height": pr.frame_height,
        "pose_detected": pr.pose_detected,
    }


def _dict_to_pose_result(data: Dict[str, Any]) -> PoseResult:
    """Reconstruct a PoseResult from a dictionary."""
    return PoseResult(
        timestamp=data.get("timestamp", 0.0),
        landmarks=[Landmark(**lm) for lm in data.get("landmarks", [])],
        world_landmarks=[
            Landmark(**lm) for lm in data.get("world_landmarks", [])
        ],
        confidence=data.get("confidence", 0.0),
        frame_width=data.get("frame_width", 0),
        frame_height=data.get("frame_height", 0),
        pose_detected=data.get("pose_detected", False),
    )
