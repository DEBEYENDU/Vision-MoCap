"""Bone data model for the VisionMoCap animation subsystem.

A Bone represents a single rigid segment in an animated character's
skeleton hierarchy. Bones are connected via parent-child relationships
to form a tree rooted at the avatar's root bone.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from src.core.models import Vector3D


@dataclass
class Bone:
    """A single bone in an animated character's skeleton.

    Each bone sits in a parent-child hierarchy that forms the skeleton
    tree.  The *head_position* is the joint at the parent end of the
    bone and *tail_position* is the joint at the child end.  These are
    specified in the avatar's **bind pose** (rest / T-pose).

    The *rotation* is stored as a unit quaternion ``(w, x, y, z)``
    representing the bone's orientation in the bind pose relative to
    the world axes.  During retargeting the per-frame rotation is
    derived from the current head→tail direction.

    Attributes:
        name: Unique identifier for this bone within the skeleton.
        parent: Name of the parent bone, or ``None`` for the root.
        children: Names of child bones that have this bone as parent.
        head_position: Bind-pose position of the joint at the proximal
            (parent) end of the bone.
        tail_position: Bind-pose position of the joint at the distal
            (child) end of the bone.
        rotation: Bind-pose orientation as a unit quaternion
            ``(w, x, y, z)``.  Defaults to the identity quaternion.
        length: Euclidean distance from head to tail in the bind pose.
            Computed automatically on construction.
    """

    name: str
    parent: Optional[str] = None
    children: List[str] = field(default_factory=list)
    head_position: Vector3D = field(
        default_factory=lambda: Vector3D(0.0, 0.0, 0.0)
    )
    tail_position: Vector3D = field(
        default_factory=lambda: Vector3D(0.0, 0.0, 0.0)
    )
    rotation: Tuple[float, float, float, float] = (1.0, 0.0, 0.0, 0.0)
    length: float = 0.0

    def __post_init__(self) -> None:
        if self.length == 0.0:
            dx = self.tail_position.x - self.head_position.x
            dy = self.tail_position.y - self.head_position.y
            dz = self.tail_position.z - self.head_position.z
            self.length = math.sqrt(dx * dx + dy * dy + dz * dz)

    @property
    def direction(self) -> Vector3D:
        """Unit vector pointing from head toward tail in the bind pose."""
        return (self.tail_position - self.head_position).normalize()

    @property
    def is_root(self) -> bool:
        """True if this bone is the root of the skeleton hierarchy."""
        return self.parent is None
