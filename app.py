"""VisionMoCap AI - Markerless Motion Capture Application.

Launches the VisionMoCap Studio GUI (CustomTkinter).
"""

import sys
from pathlib import Path

from src.config.manager import ConfigManager
from src.gui.main_window import MainWindow
from src.utils.logger import LoggerSetup


def main() -> None:
    """Initialize logging, create the MainWindow, and run the GUI."""
    config_manager = ConfigManager()
    config = config_manager.load()

    LoggerSetup(
        name="VisionMoCap",
        level=config.logging.level,
        log_dir=Path(config.logging.directory),
        max_file_size_mb=config.logging.max_file_size_mb,
        backup_count=config.logging.backup_count,
    ).get_logger()

    window = MainWindow()
    window.initialize()
    window.run()


if __name__ == "__main__":
    main()
