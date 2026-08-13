"""Lightweight tooltip helper for CustomTkinter widgets."""

from __future__ import annotations

import tkinter as tk
from typing import Optional


class Tooltip:
    """Show a small floating label when the mouse hovers over a widget.

    The tooltip appears after *delay_ms* of uninterrupted hover and
    disappears on leave.  It is intentionally dependency-free and works
    with any ``tk``-based widget (including CustomTkinter controls).

    Usage::

        Tooltip(button, "Start the camera")
    """

    def __init__(
        self,
        widget: tk.Misc,
        text: str,
        delay_ms: int = 500,
        bg: str = "#333333",
        fg: str = "#eeeeee",
    ) -> None:
        self._widget = widget
        self._text = text
        self._delay_ms = delay_ms
        self._bg = bg
        self._fg = fg
        self._after_id: Optional[str] = None
        self._window: Optional[tk.Toplevel] = None

        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        widget.bind("<ButtonPress>", self._on_leave, add="+")

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_enter(self, event) -> None:
        self._cancel()
        top = self._widget.winfo_toplevel()
        if not top.winfo_viewable():
            return
        self._after_id = self._widget.after(
            self._delay_ms, self._show_tooltip
        )

    def _on_leave(self, event) -> None:
        self._cancel()
        self._hide_tooltip()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _cancel(self) -> None:
        if self._after_id is not None:
            try:
                self._widget.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None

    def _show_tooltip(self) -> None:
        self._after_id = None
        if self._window is not None:
            return
        try:
            x = self._widget.winfo_rootx()
            y = self._widget.winfo_rooty()
            width = self._widget.winfo_width()
        except tk.TclError:
            return

        self._window = tk.Toplevel(self._widget)
        self._window.wm_overrideredirect(True)
        self._window.wm_geometry(f"+{x + width + 6}+{y + 4}")

        label = tk.Label(
            self._window,
            text=self._text,
            bg=self._bg,
            fg=self._fg,
            padx=6,
            pady=3,
            font=("Segoe UI", 9),
            relief="flat",
        )
        label.pack()

    def _hide_tooltip(self) -> None:
        if self._window is not None:
            try:
                self._window.destroy()
            except tk.TclError:
                pass
            self._window = None

    def set_text(self, text: str) -> None:
        """Update the tooltip text."""
        self._text = text