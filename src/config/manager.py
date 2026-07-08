"""Configuration management for the VisionMoCap application."""

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Optional

from src.core.exceptions import ConfigurationError


RESOLUTION_PRESETS: dict[str, tuple[int, int]] = {
    "640x480": (640, 480),
    "1280x720": (1280, 720),
    "1920x1080": (1920, 1080),
}


@dataclass
class CameraConfig:
    """Configuration for camera input source."""

    device_id: int = 0
    width: int = 640
    height: int = 480
    fps: float = 30.0
    max_camera_index: int = 20
    resolution_preset: str = "640x480"
    backend: str = "directshow"


@dataclass
class PoseConfig:
    """Configuration for pose estimation (MediaPipe Tasks API).

    Attributes:
        model_complexity: 0=lite, 1=full, 2=heavy.
        min_detection_confidence: Minimum confidence for pose detection.
        min_tracking_confidence: Minimum confidence for tracking between frames.
        static_image_mode: Kept for backward compatibility (unused by Tasks API).
        model_path: Path to the PoseLandmarker ``.task`` model file. When
            ``None`` the model is auto-resolved from *model_complexity* and
            downloaded to ``models/`` if not present.
    """

    model_complexity: int = 2
    min_detection_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    static_image_mode: bool = False
    model_path: Optional[str] = None


@dataclass
class MotionConfig:
    """Configuration for motion processing.

    Controls the parameters of the MotionProcessing pipeline. New fields
    have defaults so existing config files remain valid.
    """

    smoothing_window: int = 5
    velocity_threshold: float = 0.1
    interpolation_enabled: bool = True
    outlier_threshold: float = 0.15
    exponential_alpha: float = 0.5
    visibility_threshold: float = 0.5


@dataclass
class AnimationConfig:
    """Configuration for animation export."""

    export_format: str = "fbx"
    scale_factor: float = 1.0
    apply_smoothing: bool = True


@dataclass
class BlenderConfig:
    """Configuration for Blender integration."""

    blender_executable: str = "blender"
    script_path: str = ""
    auto_launch: bool = False


@dataclass
class LoggingConfig:
    """Configuration for application logging."""

    level: str = "INFO"
    directory: str = "logs"
    max_file_size_mb: int = 10
    backup_count: int = 5


@dataclass
class AppConfig:
    """Root configuration aggregating all module-specific configurations."""

    camera: CameraConfig = field(default_factory=CameraConfig)
    pose: PoseConfig = field(default_factory=PoseConfig)
    motion: MotionConfig = field(default_factory=MotionConfig)
    animation: AnimationConfig = field(default_factory=AnimationConfig)
    blender: BlenderConfig = field(default_factory=BlenderConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


class ConfigManager:
    """Manages loading, validation, and persistence of application configuration.

    Loads configuration from a JSON file on disk. If the file does not exist,
    a default configuration is created and persisted automatically.
    """

    _DEFAULT_FILENAME = "config.json"

    def __init__(self, config_path: Optional[Path] = None) -> None:
        self._config_path = config_path or Path(self._DEFAULT_FILENAME)
        self._config: Optional[AppConfig] = None
        self._logger = logging.getLogger(self.__class__.__name__)

    @property
    def config(self) -> AppConfig:
        """Return the loaded configuration.

        Raises:
            ConfigurationError: If configuration has not been loaded yet.
        """
        if self._config is None:
            raise ConfigurationError(
                "Configuration has not been loaded. Call load() first."
            )
        return self._config

    def load(self) -> AppConfig:
        """Load configuration from file or create and persist a default.

        Returns:
            The loaded or newly created AppConfig instance.
        """
        if self._config_path.exists():
            self._config = self._load_from_file()
        else:
            self._config = self._create_default()
        self._logger.info(
            "Configuration loaded from %s", self._config_path.resolve()
        )
        return self._config

    def save(self) -> None:
        """Persist the current configuration to the JSON file.

        Raises:
            ConfigurationError: If no configuration has been loaded yet.
        """
        if self._config is None:
            raise ConfigurationError(
                "No configuration to save. Call load() first."
            )
        self._save_to_file(self._config)
        self._logger.info(
            "Configuration saved to %s", self._config_path.resolve()
        )

    def _load_from_file(self) -> AppConfig:
        """Deserialize configuration from the JSON file on disk."""
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                data: Dict[str, Any] = json.load(f)
            return self._dict_to_config(data)
        except (json.JSONDecodeError, IOError) as e:
            raise ConfigurationError(
                f"Failed to load configuration from {self._config_path}: {e}",
                cause=e,
            )

    def _create_default(self) -> AppConfig:
        """Create a default configuration and persist it to disk."""
        config = AppConfig()
        self._save_to_file(config)
        return config

    def _save_to_file(self, config: AppConfig) -> None:
        """Serialize configuration to the JSON file on disk."""
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(
                    self._config_to_dict(config),
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
                f.write("\n")
        except IOError as e:
            raise ConfigurationError(
                f"Failed to save configuration to {self._config_path}: {e}",
                cause=e,
            )

    @staticmethod
    def _config_to_dict(config: AppConfig) -> Dict[str, Any]:
        """Convert an AppConfig instance to a JSON-serializable dictionary."""
        return asdict(config)

    @staticmethod
    def _dict_to_config(data: Dict[str, Any]) -> AppConfig:
        """Convert a dictionary to an AppConfig with field-level validation.

        Unknown or malformed fields fall back to their default values
        instead of causing a hard failure.
        """
        validated: Dict[str, Any] = {}
        field_map = {
            "camera": CameraConfig,
            "pose": PoseConfig,
            "motion": MotionConfig,
            "animation": AnimationConfig,
            "blender": BlenderConfig,
            "logging": LoggingConfig,
        }
        for key, config_cls in field_map.items():
            raw_subconfig = data.get(key, {})
            if not isinstance(raw_subconfig, dict):
                validated[key] = config_cls()
                continue
            known_fields = config_cls.__dataclass_fields__
            kwargs: Dict[str, Any] = {}
            for field_name, field_def in known_fields.items():
                if field_name not in raw_subconfig:
                    kwargs[field_name] = field_def.default
                    continue
                value = raw_subconfig[field_name]
                expected_type = field_def.type
                if isinstance(expected_type, type) and not isinstance(
                    value, expected_type
                ):
                    try:
                        kwargs[field_name] = expected_type(value)
                    except (TypeError, ValueError):
                        kwargs[field_name] = field_def.default
                else:
                    kwargs[field_name] = value
            validated[key] = config_cls(**kwargs)
        return AppConfig(**validated)
