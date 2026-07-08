"""Domain models for the VisionMoCap application."""

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List


class JointType(Enum):
    """Enumeration of tracked joint types in the human body."""

    NOSE = auto()
    LEFT_EYE_INNER = auto()
    LEFT_EYE = auto()
    LEFT_EYE_OUTER = auto()
    RIGHT_EYE_INNER = auto()
    RIGHT_EYE = auto()
    RIGHT_EYE_OUTER = auto()
    LEFT_EAR = auto()
    RIGHT_EAR = auto()
    MOUTH_LEFT = auto()
    MOUTH_RIGHT = auto()
    LEFT_SHOULDER = auto()
    RIGHT_SHOULDER = auto()
    LEFT_ELBOW = auto()
    RIGHT_ELBOW = auto()
    LEFT_WRIST = auto()
    RIGHT_WRIST = auto()
    LEFT_PINKY = auto()
    RIGHT_PINKY = auto()
    LEFT_INDEX = auto()
    RIGHT_INDEX = auto()
    LEFT_THUMB = auto()
    RIGHT_THUMB = auto()
    LEFT_HIP = auto()
    RIGHT_HIP = auto()
    LEFT_KNEE = auto()
    RIGHT_KNEE = auto()
    LEFT_ANKLE = auto()
    RIGHT_ANKLE = auto()
    LEFT_HEEL = auto()
    RIGHT_HEEL = auto()
    LEFT_FOOT_INDEX = auto()
    RIGHT_FOOT_INDEX = auto()


@dataclass(frozen=True)
class Vector3D:
    """Immutable 3D vector representing a point in space.

    Provides arithmetic operations and normalization for 3D coordinates
    used in joint positions and motion vectors.
    """

    x: float
    y: float
    z: float

    def __post_init__(self) -> None:
        if not all(math.isfinite(v) for v in (self.x, self.y, self.z)):
            raise ValueError(
                f"Vector3D components must be finite numbers, "
                f"got ({self.x}, {self.y}, {self.z})."
            )

    def __add__(self, other: "Vector3D") -> "Vector3D":
        return Vector3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: "Vector3D") -> "Vector3D":
        return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> "Vector3D":
        return Vector3D(self.x * scalar, self.y * scalar, self.z * scalar)

    def __truediv__(self, scalar: float) -> "Vector3D":
        if scalar == 0.0:
            raise ZeroDivisionError("Cannot divide Vector3D by zero.")
        return Vector3D(self.x / scalar, self.y / scalar, self.z / scalar)

    @property
    def magnitude(self) -> float:
        """Compute the Euclidean norm of the vector."""
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def normalize(self) -> "Vector3D":
        """Return a unit vector pointing in the same direction."""
        mag = self.magnitude
        if mag == 0.0:
            return Vector3D(0.0, 0.0, 0.0)
        return self / mag


@dataclass
class Joint:
    """Represents a single tracked joint with its spatial position and confidence.

    Attributes:
        joint_type: The anatomical label for this joint.
        position: 3D coordinates of the joint in the captured space.
        confidence: Detection confidence between 0.0 and 1.0.
    """

    joint_type: JointType
    position: Vector3D
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"Joint confidence must be between 0.0 and 1.0, "
                f"got {self.confidence}."
            )


@dataclass
class Pose:
    """Represents a complete human pose at a specific point in time.

    Attributes:
        joints: Mapping of joint types to their detected Joint data.
        timestamp: Monotonic timestamp of the capture in seconds.
        frame_id: Monotonically increasing frame identifier.
    """

    joints: Dict[JointType, Joint]
    timestamp: float
    frame_id: int


@dataclass
class MotionData:
    """Container for a sequence of poses representing captured motion over time.

    Attributes:
        poses: Ordered list of Pose objects forming the motion sequence.
        fps: Frame rate at which the motion was captured.
        duration: Total duration of the motion sequence in seconds.
    """

    poses: List[Pose]
    fps: float
    duration: float

    @property
    def frame_count(self) -> int:
        """Return the total number of pose frames in this motion data."""
        return len(self.poses)


@dataclass(frozen=True)
class BoneConnection:
    """Defines a directed hierarchical connection between two joints.

    Attributes:
        parent: The proximal joint in the skeletal hierarchy.
        child: The distal joint connected to the parent.
    """

    parent: JointType
    child: JointType


SKELETON_HIERARCHY: List[BoneConnection] = [
    BoneConnection(JointType.LEFT_SHOULDER, JointType.LEFT_ELBOW),
    BoneConnection(JointType.LEFT_ELBOW, JointType.LEFT_WRIST),
    BoneConnection(JointType.LEFT_WRIST, JointType.LEFT_PINKY),
    BoneConnection(JointType.LEFT_WRIST, JointType.LEFT_INDEX),
    BoneConnection(JointType.LEFT_WRIST, JointType.LEFT_THUMB),
    BoneConnection(JointType.RIGHT_SHOULDER, JointType.RIGHT_ELBOW),
    BoneConnection(JointType.RIGHT_ELBOW, JointType.RIGHT_WRIST),
    BoneConnection(JointType.RIGHT_WRIST, JointType.RIGHT_PINKY),
    BoneConnection(JointType.RIGHT_WRIST, JointType.RIGHT_INDEX),
    BoneConnection(JointType.RIGHT_WRIST, JointType.RIGHT_THUMB),
    BoneConnection(JointType.LEFT_HIP, JointType.LEFT_KNEE),
    BoneConnection(JointType.LEFT_KNEE, JointType.LEFT_ANKLE),
    BoneConnection(JointType.LEFT_ANKLE, JointType.LEFT_HEEL),
    BoneConnection(JointType.LEFT_ANKLE, JointType.LEFT_FOOT_INDEX),
    BoneConnection(JointType.RIGHT_HIP, JointType.RIGHT_KNEE),
    BoneConnection(JointType.RIGHT_KNEE, JointType.RIGHT_ANKLE),
    BoneConnection(JointType.RIGHT_ANKLE, JointType.RIGHT_HEEL),
    BoneConnection(JointType.RIGHT_ANKLE, JointType.RIGHT_FOOT_INDEX),
    BoneConnection(JointType.NOSE, JointType.LEFT_EYE_INNER),
    BoneConnection(JointType.NOSE, JointType.RIGHT_EYE_INNER),
    BoneConnection(JointType.LEFT_EYE_INNER, JointType.LEFT_EYE),
    BoneConnection(JointType.LEFT_EYE, JointType.LEFT_EYE_OUTER),
    BoneConnection(JointType.RIGHT_EYE_INNER, JointType.RIGHT_EYE),
    BoneConnection(JointType.RIGHT_EYE, JointType.RIGHT_EYE_OUTER),
    BoneConnection(JointType.LEFT_EYE_OUTER, JointType.LEFT_EAR),
    BoneConnection(JointType.RIGHT_EYE_OUTER, JointType.RIGHT_EAR),
    BoneConnection(JointType.LEFT_SHOULDER, JointType.RIGHT_SHOULDER),
    BoneConnection(JointType.LEFT_HIP, JointType.RIGHT_HIP),
    BoneConnection(JointType.LEFT_SHOULDER, JointType.LEFT_HIP),
    BoneConnection(JointType.RIGHT_SHOULDER, JointType.RIGHT_HIP),
]
"""Predefined skeletal hierarchy mapping joint connections for the full body.

This list defines which joints are connected to form the skeleton structure
used for rendering and animation. Connections are listed as (parent, child)
pairs representing the kinematic chain.
"""
