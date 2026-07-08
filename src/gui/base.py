"""GUI module base abstractions for the VisionMoCap application."""

import logging
from abc import abstractmethod


class GUIAppBase:
    """Base class for GUI application implementations.

    Provides a common interface for initializing, running, and shutting
    down the graphical user interface. Subclasses must implement the
    run() method with framework-specific rendering logic.

    Attributes:
        title: The application window title.
    """

    def __init__(self, title: str = "VisionMoCap AI") -> None:
        self._title = title
        self._logger = logging.getLogger(self.__class__.__name__)
        self._running: bool = False

    @property
    def title(self) -> str:
        """Return the application window title."""
        return self._title

    @property
    def is_running(self) -> bool:
        """Return whether the GUI application is currently running."""
        return self._running

    def initialize(self) -> None:
        """Initialize the GUI framework and create the main window."""
        self._running = True
        self._logger.info("GUI application '%s' initialized.", self._title)

    @abstractmethod
    def run(self) -> None:
        """Start the GUI main event loop. Must be implemented by subclasses."""

    def shutdown(self) -> None:
        """Shut down the GUI application and clean up resources."""
        self._running = False
        self._logger.info("GUI application shut down.")
