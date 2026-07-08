"""Motion sequence data model for the VisionMoCap application.

Provides a serialisable container for recorded pose data with timing
metadata. Includes JSON serialisation helpers for persistence.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.pose.pose_result import Landmark, PoseResult


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
            start_time=data["start_time"],
            end_time=data.get("end_time", data["start_time"]),
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
        timestamp=data["timestamp"],
        landmarks=[Landmark(**lm) for lm in data.get("landmarks", [])],
        world_landmarks=[
            Landmark(**lm) for lm in data.get("world_landmarks", [])
        ],
        confidence=data.get("confidence", 0.0),
        frame_width=data.get("frame_width", 0),
        frame_height=data.get("frame_height", 0),
        pose_detected=data.get("pose_detected", False),
    )
