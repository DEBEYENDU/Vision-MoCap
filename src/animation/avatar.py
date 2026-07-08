"""Avatar data model for the VisionMoCap animation subsystem.

An Avatar represents an animated character with a named skeleton
hierarchy.  It holds the bind-pose bone definitions and is consumed
by the Retargeter together with a MotionSequence.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.animation.bone import Bone


class Avatar:
    """An animated character with a named skeleton.

    The skeleton is stored as a flat list of :class:`Bone` objects whose
    parent-child relationships form a tree.  The *root_bone* is the
    ancestor of all other bones in the hierarchy.

    Attributes:
        name: Human-readable avatar identifier.
        root_bone: Name of the root bone (top of the skeleton tree).
        bones: Flat list of all bones in the skeleton.
        metadata: Arbitrary key-value store for rig-specific data
            (e.g. scale, exporter hints).
    """

    def __init__(
        self,
        name: str,
        root_bone: str,
        bones: List[Bone],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._name = name
        self._root_bone = root_bone
        self._bones = list(bones)
        self._metadata = dict(metadata) if metadata else {}
        self._logger = logging.getLogger(self.__class__.__name__)
        self._rebuild_index()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """The avatar's human-readable name."""
        return self._name

    @property
    def root_bone(self) -> str:
        """The name of the root bone."""
        return self._root_bone

    @property
    def bones(self) -> List[Bone]:
        """Read-only view of the skeleton's bone list."""
        return list(self._bones)

    @property
    def metadata(self) -> Dict[str, Any]:
        """Read-only view of the avatar metadata."""
        return dict(self._metadata)

    def bone(self, name: str) -> Bone:
        """Look up a bone by name.

        Args:
            name: The bone's unique identifier.

        Returns:
            The matching Bone.

        Raises:
            KeyError: If no bone with *name* exists.
        """
        idx = self._index.get(name)
        if idx is None:
            raise KeyError(f"Bone '{name}' not found in avatar '{self._name}'.")
        return self._bones[idx]

    def has_bone(self, name: str) -> bool:
        """Return whether a bone with *name* exists in the skeleton."""
        return name in self._index

    @property
    def bone_names(self) -> List[str]:
        """Return the names of all bones in order."""
        return [b.name for b in self._bones]

    @property
    def bone_count(self) -> int:
        """Return the total number of bones in the skeleton."""
        return len(self._bones)

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def from_parent_pairs(
        cls,
        name: str,
        pairs: List[tuple[str, Optional[str]]],
        root_bone: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Avatar:
        """Construct an Avatar from ``(bone_name, parent_name)`` pairs.

        Each pair defines one bone.  Children are computed automatically
        from the parent links.  Bones can be given custom positions and
        rotations after construction by modifying the returned Avatar's
        bone list.

        Args:
            name: Avatar name.
            pairs: List of ``(bone_name, parent_name)`` tuples.
            root_bone: Name of the root bone.
            metadata: Optional metadata dict.

        Returns:
            A new Avatar with children populated.
        """
        bones: List[Bone] = []
        name_to_children: Dict[str, List[str]] = {}

        for bone_name, parent_name in pairs:
            name_to_children.setdefault(bone_name, [])
            if parent_name is not None:
                name_to_children.setdefault(parent_name, [])
                name_to_children[parent_name].append(bone_name)

        for bone_name, parent_name in pairs:
            bones.append(
                Bone(
                    name=bone_name,
                    parent=parent_name,
                    children=name_to_children.get(bone_name, []),
                )
            )

        return cls(
            name=name,
            root_bone=root_bone,
            bones=bones,
            metadata=metadata,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _rebuild_index(self) -> None:
        """Rebuild the name-to-index lookup table."""
        self._index: Dict[str, int] = {
            b.name: i for i, b in enumerate(self._bones)
        }
