"""Motion-to-animation conversion for the VisionMoCap application.

The MotionToAnimationConverter is the single public entry point from
the motion subsystem (a :class:`MotionSequence`) to the animation
subsystem (an :class:`AnimationClip`).  It composes the existing
building blocks — SkeletonMapper, Avatar, Retargeter and
AnimationEngine — behind one validated, user-friendly API::

    converter = MotionToAnimationConverter()
    clip = converter.convert(sequence)

    # The clip can then be exported:
    BvhExporter(converter.avatar, clip).export(path)
"""

from __future__ import annotations

import logging
from typing import Optional

from src.animation.animation_clip import AnimationClip
from src.animation.animation_engine import AnimationEngine
from src.animation.avatar import Avatar
from src.animation.avatar_templates import build_mixamo_avatar
from src.animation.keyframe import InterpolationType
from src.animation.retargeted_motion import RetargetedMotion
from src.animation.retargeter import Retargeter
from src.animation.skeleton_mapper import SkeletonMapper
from src.core.exceptions import RetargetingError
from src.motion.motion_sequence import MotionSequence, is_valid_fps

_ERROR_EMPTY = "Cannot create animation: the recording is empty."
_ERROR_NO_VALID_POSES = (
    "Cannot create animation: recording contains no valid pose frames "
    "(pose not detected)."
)
_ERROR_NO_MOTION = (
    "Cannot create animation: no motion recording loaded."
)
_ERROR_NO_BONES = (
    "Cannot create animation: no mapped bones available for retargeting."
)
_ERROR_INVALID_FPS = (
    "Cannot create animation: invalid frame rate {value!r}. A frame "
    "rate must be a positive finite number greater than zero."
)


class MotionToAnimationConverter:
    """Convert a MotionSequence into an AnimationClip.

    The converter owns the skeleton mapping and avatar template used
    for retargeting so callers do not need to construct (or duplicate)
    the retargeting pipeline themselves.  Both can be overridden for
    custom rigs.

    Attributes:
        avatar: The Avatar the converted clip is retargeted onto.
        mapper: The SkeletonMapper used for landmark→bone mapping.
    """

    def __init__(
        self,
        mapper: Optional[SkeletonMapper] = None,
        avatar: Optional[Avatar] = None,
    ) -> None:
        self._mapper = mapper if mapper is not None else SkeletonMapper(preset="mixamo")
        self._avatar = avatar if avatar is not None else build_mixamo_avatar()
        self._retargeter = Retargeter(mapper=self._mapper, avatar=self._avatar)
        self._engine = AnimationEngine()
        self._logger = logging.getLogger(self.__class__.__name__)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def mapper(self) -> SkeletonMapper:
        """The SkeletonMapper used for retargeting."""
        return self._mapper

    @property
    def avatar(self) -> Avatar:
        """The Avatar template the clip is retargeted onto."""
        return self._avatar

    def validate(self, sequence: Optional[MotionSequence]) -> None:
        """Validate a sequence before conversion.

        Args:
            sequence: The motion sequence to validate.

        Raises:
            RetargetingError: If the sequence is missing, empty, or has
                no frames in which a pose was detected.
        """
        if sequence is None:
            raise RetargetingError(_ERROR_NO_MOTION)
        if not sequence.pose_results:
            raise RetargetingError(_ERROR_EMPTY)
        if not any(_is_valid_frame(pr) for pr in sequence.pose_results):
            raise RetargetingError(_ERROR_NO_VALID_POSES)

    def retarget(self, sequence: MotionSequence) -> RetargetedMotion:
        """Retarget a validated sequence onto the avatar.

        Args:
            sequence: The motion sequence to retarget.

        Returns:
            A RetargetedMotion with one frame per valid pose frame.

        Raises:
            RetargetingError: If the sequence cannot be retargeted.
        """
        self.validate(sequence)
        try:
            return self._retargeter.retarget(sequence)
        except ValueError as exc:
            raise RetargetingError(
                "Cannot create animation: retargeting failed.", cause=exc
            ) from exc

    def convert(
        self,
        sequence: MotionSequence,
        interpolation: InterpolationType = InterpolationType.LINEAR,
        fps: Optional[float] = None,
    ) -> AnimationClip:
        """Convert a MotionSequence into an AnimationClip.

        Args:
            sequence: The motion sequence to convert.
            interpolation: Default interpolation for keyframes.
            fps: Optional target frame rate for the clip (defaults to
                the sequence's own rate).

        Returns:
            A new AnimationClip with one keyframe per valid pose frame.

        Raises:
            RetargetingError: If the sequence is missing, empty, has no
                valid pose frames, or fails to retarget.
        """
        self.validate(sequence)
        if not self._mapper.bone_names:
            raise RetargetingError(_ERROR_NO_BONES)
        if fps is not None and not is_valid_fps(fps):
            raise RetargetingError(_ERROR_INVALID_FPS.format(value=fps))

        motion = self.retarget(sequence)
        try:
            clip = self._engine.convert(
                motion,
                fps=fps,
                interpolation=interpolation,
            )
        except ValueError as exc:
            raise RetargetingError(
                "Cannot create animation: failed to build animation clip.",
                cause=exc,
            ) from exc

        self._logger.info(
            "Created animation clip (%d keyframes, %.1f fps, %.2fs).",
            clip.frame_count,
            clip.fps,
            clip.duration,
        )
        return clip


def _is_valid_frame(pr: object) -> bool:
    """Return True if a PoseResult reports pose detection with data."""
    pose_detected = getattr(pr, "pose_detected", True)
    if not pose_detected:
        return False
    landmarks = getattr(pr, "landmarks", None) or getattr(pr, "world_landmarks", None)
    return bool(landmarks)