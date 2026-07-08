"""Logging setup for the VisionMoCap application."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


class LoggerSetup:
    """Configures and provides application-wide logging with console and file output.

    The file handler uses log rotation to prevent unbounded disk usage.
    If the log directory cannot be created, the file handler is omitted
    and only console logging is active.
    """

    _FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"
    _DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    def __init__(
        self,
        name: str = "VisionMoCap",
        level: str = "INFO",
        log_dir: Optional[Path] = None,
        max_file_size_mb: int = 10,
        backup_count: int = 5,
    ) -> None:
        self._name = name
        self._level = self._resolve_level(level)
        self._log_dir = log_dir or Path("logs")
        self._max_file_size_mb = max_file_size_mb
        self._backup_count = backup_count
        self._logger: Optional[logging.Logger] = None

    def get_logger(self) -> logging.Logger:
        """Return the configured logger, creating it on first access."""
        if self._logger is not None:
            return self._logger
        logger = logging.getLogger(self._name)
        logger.setLevel(self._level)
        if not logger.handlers:
            logger.addHandler(self._create_console_handler())
            file_handler = self._create_file_handler()
            if file_handler is not None:
                logger.addHandler(file_handler)
        self._logger = logger
        return logger

    def _create_console_handler(self) -> logging.Handler:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(self._level)
        handler.setFormatter(self._create_formatter())
        return handler

    def _create_file_handler(self) -> Optional[logging.Handler]:
        try:
            self._log_dir.mkdir(parents=True, exist_ok=True)
            log_file = self._log_dir / f"{self._name.lower()}.log"
            handler = RotatingFileHandler(
                log_file,
                maxBytes=self._max_file_size_mb * 1024 * 1024,
                backupCount=self._backup_count,
                encoding="utf-8",
            )
            handler.setLevel(self._level)
            handler.setFormatter(self._create_formatter())
            return handler
        except OSError as e:
            print(
                f"Failed to create file handler for {self._log_dir}: {e}",
                file=sys.stderr,
            )
            return None

    def _create_formatter(self) -> logging.Formatter:
        return logging.Formatter(self._FORMAT, datefmt=self._DATE_FORMAT)

    @staticmethod
    def _resolve_level(level: str) -> int:
        resolved = getattr(logging, level.upper(), None)
        if not isinstance(resolved, int):
            return logging.INFO
        return resolved
