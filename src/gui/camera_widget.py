"""Camera preview widget for the VisionMoCap Studio GUI.

Displays live camera frames with skeleton overlays inside a
CustomTkinter frame.  Receives pre-rendered BGR frames from the
AppController and converts them to a CTkImage for display.
"""

from __future__ import annotations

import logging
from typing import Optional

import cv2
import customtkinter as ctk
import numpy as np
from numpy.typing import NDArray
from PIL import Image


class CameraWidget(ctk.CTkFrame):
    """CustomTkinter frame that displays the live camera preview.

    The widget accepts pre-rendered BGR frames (with skeleton overlay
    already drawn by SkeletonRenderer) and shows them at a size that
    fits the available space while preserving aspect ratio.

    A placeholder label is shown when no camera feed is active.

    Attributes:
        placeholder_text: Message shown when the camera is not running.
    """

    def __init__(
        self,
        master: ctk.BaseWidget,
        placeholder_text: str = "Camera Off",
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self._logger = logging.getLogger(self.__class__.__name__)

        # Configure grid so the image label fills the available space.
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._placeholder = placeholder_text

        # Label that holds the CTkImage or placeholder text.
        self._image_label = ctk.CTkLabel(
            self,
            text=placeholder_text,
            font=ctk.CTkFont(size=24),
            anchor=ctk.CENTER,
        )
        self._image_label.grid(row=0, column=0, sticky="nsew")

        self._ctk_image: Optional[ctk.CTkImage] = None
        self._display_size: tuple[int, int] = (640, 480)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_frame(self, frame: Optional[NDArray[np.uint8]]) -> None:
        """Display a new camera frame.

        Args:
            frame: BGR numpy array (annotated by SkeletonRenderer)
                or None to show the placeholder.
        """
        if frame is None:
            self._image_label.configure(
                text=self._placeholder, image=None
            )
            return

        self._image_label.configure(text="")

        # Determine the widget's current display area.
        self.update_idletasks()
        current_width = self._image_label.winfo_width()
        current_height = self._image_label.winfo_height()

        if current_width > 10 and current_height > 10:
            self._display_width = current_width
            max_h = current_height
        else:
            max_w, max_h = self._display_width, int(
                self._display_width * 0.75)
            current_width, current_height = max_w, max_h

        # Resize the frame to fit while preserving aspect ratio.
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(frame_rgb)

        h, w = frame.shape[:2]
        scale = min(
            current_width / max(w, 1),
            current_height / max(h, 1),
        )
        new_w = max(int(w * scale), 1)
        new_h = max(int(h * scale), 1)

        pil_image = pil_image.resize((new_w, new_h), Image.BILINEAR)

        self._ctk_image = ctk.CTkImage(
            light_image=pil_image,
            dark_image=pil_image,
            size=(new_w, new_h),
        )
        self._image_label.configure(image=self._ctk_image)

    def clear(self) -> None:
        """Reset to the placeholder state."""
        self._image_label.configure(text=self._placeholder, image=None)
        self._ctk_image = None