"""VisionMoCap AI - Markerless Motion Capture Application.

Launches the VisionMoCap Studio GUI (CustomTkinter).

Top-level failures (corrupt configuration, missing display, import
errors) are logged and shown in a message box instead of surfacing
as raw tracebacks.
"""

import logging
import sys
import traceback
from pathlib import Path

from src.config.manager import ConfigManager
from src.utils.logger import LoggerSetup


def _show_fatal_error(title: str, message: str, log: logging.Logger) -> None:
    """Show a message box (when possible) and exit with a non-zero code."""
    log.error("%s\n%s", title, message)
    try:
        import tkinter.messagebox as messagebox
        import tkinter

        root = tkinter.Tk()
        root.withdraw()
        messagebox.showerror(title, message)
        root.destroy()
    except Exception:
        print(f"{title}: {message}", file=sys.stderr)


def main() -> int:
    """Initialize logging, create the MainWindow, and run the GUI.

    Returns:
        Process exit code (0 = clean shutdown).
    """
    log = logging.getLogger("VisionMoCap")
    try:
        LoggerSetup(
            name="VisionMoCap",
            level="INFO",
            log_dir=Path("logs"),
        ).get_logger()
    except Exception as e:
        print(f"Failed to initialise logging: {e}", file=sys.stderr)

    try:
        config_manager = ConfigManager()
        config = config_manager.load()
    except Exception as e:
        _show_fatal_error(
            "Configuration Error",
            "VisionMoCap could not load its configuration.\n\n"
            f"{e}\n\n"
            "Fix or delete config.json and restart the application.",
            log,
        )
        return 1

    # Reconfigure logging with the user's settings now that config is loaded.
    try:
        LoggerSetup(
            name="VisionMoCap",
            level=config.logging.level,
            log_dir=Path(config.logging.directory),
            max_file_size_mb=config.logging.max_file_size_mb,
            backup_count=config.logging.backup_count,
        ).get_logger()
    except Exception as e:
        print(f"Failed to configure file logging: {e}", file=sys.stderr)

    try:
        from src.gui.main_window import MainWindow

        window = MainWindow()
        window.initialize()
        window.run()
        return 0
    except KeyboardInterrupt:
        log.info("Interrupted by user.")
        return 130
    except Exception as e:
        _show_fatal_error(
            "Fatal Error",
            "VisionMoCap encountered an unexpected error:\n\n"
            f"{e}\n\n"
            "Check the log file for details.",
            log,
        )
        log.debug("%s", traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
