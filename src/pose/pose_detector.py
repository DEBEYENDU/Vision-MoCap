"""Pose detection module using MediaPipe Tasks Vision Pose Landmarker.

This module is completely independent — it performs inference only.
No rendering, GUI, or OpenCV drawing is done here.

Uses the MediaPipe Tasks API (``mp.tasks.vision.PoseLandmarker``) instead
of the deprecated Solutions API (``mp.solutions.pose.Pose``).
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import List, Optional

import cv2
import mediapipe as mp
import numpy as np
from numpy.typing import NDArray

from src.config.manager import PoseConfig
from src.core.exceptions import PoseEstimationError
from src.pose.pose_result import Landmark, PoseResult

# ------------------------------------------------------------------
# Model management
# ------------------------------------------------------------------

_MODEL_URLS: dict[int, str] = {
    0: (
        "https://storage.googleapis.com/mediapipe-models/"
        "pose_landmarker/pose_landmarker_lite/float16/latest/"
        "pose_landmarker_lite.task"
    ),
    1: (
        "https://storage.googleapis.com/mediapipe-models/"
        "pose_landmarker/pose_landmarker_full/float16/latest/"
        "pose_landmarker_full.task"
    ),
    2: (
        "https://storage.googleapis.com/mediapipe-models/"
        "pose_landmarker/pose_landmarker_heavy/float16/latest/"
        "pose_landmarker_heavy.task"
    ),
}

_MODEL_FILENAMES: dict[int, str] = {
    0: "pose_landmarker_lite.task",
    1: "pose_landmarker_full.task",
    2: "pose_landmarker_heavy.task",
}

_PROJECT_MODELS_DIR = Path("models")


def _resolve_model_path(config: PoseConfig) -> Path:
    """Return the absolute path to the ``.task`` model file.

    If *model_path* is set in the config it is used directly.
    Otherwise the path is resolved from *model_complexity* under the
    project's ``models/`` directory.
    """
    if config.model_path:
        return Path(config.model_path)

    models_dir = _PROJECT_MODELS_DIR
    models_dir.mkdir(parents=True, exist_ok=True)
    filename = _MODEL_FILENAMES.get(config.model_complexity, "pose_landmarker_full.task")
    return models_dir / filename


def _download_model(url: str, dest: Path) -> None:
    """Download the PoseLandmarker model file from *url* to *dest*."""
    import urllib.request

    dest.parent.mkdir(parents=True, exist_ok=True)
    logging.getLogger("PoseDetector").info(
        "Downloading pose model from %s ...", url
    )
    try:
        urllib.request.urlretrieve(url, dest)
    except Exception as e:
        raise PoseEstimationError(
            f"Failed to download pose model from {url} to {dest}: {e}",
            cause=e,
        )


# ------------------------------------------------------------------
# PoseDetector
# ------------------------------------------------------------------


class PoseDetector:
    """MediaPipe Tasks Pose Landmarker wrapper.

    Responsibilities are limited to:
      - Initializing the PoseLandmarker model.
      - Converting BGR frames to RGB.
      - Running inference and extracting landmarks.
      - Returning a structured PoseResult.

    No rendering, GUI, or display logic is included.
    """

    def __init__(self, config: Optional[PoseConfig] = None) -> None:
        self._config = config or PoseConfig()
        self._landmarker: Optional[mp.tasks.vision.PoseLandmarker] = None
        self._logger = logging.getLogger(self.__class__.__name__)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Download the model (if needed) and create the PoseLandmarker.

        Raises:
            PoseEstimationError: If model resolution, download, or
                landmarker creation fails.
        """
        try:
            model_path = _resolve_model_path(self._config)

            if not model_path.exists():
                complexity = self._config.model_complexity
                url = _MODEL_URLS.get(complexity)
                if url is None:
                    raise PoseEstimationError(
                        f"Unknown model_complexity {complexity}. "
                        f"Use 0 (lite), 1 (full), or 2 (heavy)."
                    )
                _download_model(url, model_path)

            self._logger.info(
                "Loading pose model: %s (complexity=%d).",
                model_path.resolve(),
                self._config.model_complexity,
            )

            base_options = mp.tasks.BaseOptions(
                model_asset_path=str(model_path.resolve())
            )
            options = mp.tasks.vision.PoseLandmarkerOptions(
                base_options=base_options,
                running_mode=mp.tasks.vision.RunningMode.IMAGE,
                min_pose_detection_confidence=self._config.min_detection_confidence,
                min_pose_presence_confidence=self._config.min_detection_confidence,
                min_tracking_confidence=self._config.min_tracking_confidence,
                num_poses=1,
                output_segmentation_masks=False,
            )
            self._landmarker = mp.tasks.vision.PoseLandmarker.create_from_options(
                options
            )
            self._logger.info(
                "PoseDetector initialized (model_complexity=%d, "
                "min_detection_confidence=%.2f).",
                self._config.model_complexity,
                self._config.min_detection_confidence,
            )
        except PoseEstimationError:
            raise
        except Exception as e:
            raise PoseEstimationError(
                "Failed to initialise MediaPipe Pose Landmarker.", cause=e
            )

    def detect(self, frame: NDArray[np.uint8]) -> PoseResult:
        """Run pose inference on a single BGR frame.

        Args:
            frame: Input frame in BGR channel order (OpenCV default).

        Returns:
            A PoseResult with extracted landmarks. If no pose is detected
            the result will have ``pose_detected=False``.
        """
        if self._landmarker is None:
            raise PoseEstimationError(
                "PoseDetector is not initialised. Call initialize() first."
            )
        timestamp = time.perf_counter()
        frame_height, frame_width = frame.shape[:2]

        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = self._landmarker.detect(mp_image)
        except Exception as e:
            raise PoseEstimationError(
                "Pose inference failed on frame.", cause=e
            )

        if not result.pose_landmarks:
            return PoseResult(
                timestamp=timestamp,
                frame_width=frame_width,
                frame_height=frame_height,
                pose_detected=False,
            )

        # Use the first detected pose.
        landmarks = self._extract_landmarks(result.pose_landmarks[0])
        world_landmarks = self._extract_landmarks(result.pose_world_landmarks[0])

        confidence = float(
            min((lm.visibility for lm in landmarks), default=0.0)
        )

        return PoseResult(
            timestamp=timestamp,
            landmarks=landmarks,
            world_landmarks=world_landmarks,
            confidence=confidence,
            frame_width=frame_width,
            frame_height=frame_height,
            pose_detected=True,
        )

    def shutdown(self) -> None:
        """Release the PoseLandmarker and free resources."""
        if self._landmarker is not None:
            try:
                self._landmarker.close()
            except Exception as e:
                self._logger.warning(
                    "Error during PoseLandmarker shutdown: %s", e
                )
            finally:
                self._landmarker = None
                self._logger.info("PoseDetector shut down.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_landmarks(
        landmark_list: object,
    ) -> List[Landmark]:
        """Convert a MediaPipe Tasks landmark list to List[Landmark].

        Args:
            landmark_list: A ``NormalizedLandmarkList`` or ``LandmarkList``
                from the Tasks API (iterable with ``.x``, ``.y``, ``.z``,
                ``.visibility`` attributes per element).

        Returns:
            A list of :class:`Landmark` dataclass instances.
        """
        result: List[Landmark] = []
        for lm in landmark_list:
            result.append(
                Landmark(
                    x=float(lm.x),
                    y=float(lm.y),
                    z=float(lm.z),
                    visibility=float(lm.visibility),
                )
            )
        return result
