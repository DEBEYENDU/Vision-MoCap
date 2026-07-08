"""VisionMoCap AI - Markerless Motion Capture Application."""

import sys
from pathlib import Path

from src.config.manager import ConfigManager
from src.utils.logger import LoggerSetup


def main() -> None:
    """Initialize and run the VisionMoCap application."""
    config_manager = ConfigManager()
    config = config_manager.load()

    logger_setup = LoggerSetup(
        name="VisionMoCap",
        level=config.logging.level,
        log_dir=Path(config.logging.directory),
        max_file_size_mb=config.logging.max_file_size_mb,
        backup_count=config.logging.backup_count,
    )
    logger = logger_setup.get_logger()
    logger.info("VisionMoCap AI initialized successfully.")

    sys.exit(0)


if __name__ == "__main__":
    main()
