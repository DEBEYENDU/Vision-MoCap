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
from PIL import Image, ImageTk
import tkinter as tk


class CameraWidget(ctk.CTkFrame):
    def __init__(
        self,
        master: ctk.BaseWidget,
        placeholder_text: str = "Camera Off",
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self._logger = logging.getLogger(self.__class__.__name__)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._placeholder = placeholder_text

        # Use a plain tk.Label to avoid CTkLabel's PhotoImage lifecycle issues.
        # The PhotoImage is created once and reused via paste().
        self._image_label = tk.Label(
            self,
            text=placeholder_text,
            font=("TkDefaultFont", 24),
            anchor=tk.CENTER,
            bg="#2b2b2b",
            fg="white",
        )
        self._image_label.grid(row=0, column=0, sticky="nsew")

        self._photo: Optional[ImageTk.PhotoImage] = None
        self._display_size: tuple[int, int] = (640, 480)
        self._display_width: int = 640

    def update_frame(self, frame: Optional[NDArray[np.uint8]]) -> None:
        if frame is None:
            self.clear()
            return

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

        if self._photo is None or (new_w, new_h) != self._photo_size():
            # Create a new PhotoImage when size changes
            self._photo = ImageTk.PhotoImage(pil_image)
            self._image_label.configure(image=self._photo, text="")
        else:
            # Reuse the existing PhotoImage — no GC risk
            self._photo.paste(pil_image)

    def _photo_size(self) -> tuple[int, int]:
        if self._photo is None:
            return (0, 0)
        return (self._photo.width(), self._photo.height())

    def clear(self) -> None:
        self._image_label.configure(text=self._placeholder)
        if self._photo is not None:
            self._image_label.configure(image="")
            self._photo = None
