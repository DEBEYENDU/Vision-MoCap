"""Manual GUI smoke test for the scrollable toolbar (Group B/C fixes).

Run:  python tests/integration/_toolbar_smoke.py
Creates a real Tk window, exercises scrolling, state methods, and
button callbacks, then prints results.
"""

from __future__ import annotations

import sys

import customtkinter as ctk

from src.gui.toolbar import Toolbar

results = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name} {detail}")


def main() -> int:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    root = ctk.CTk()
    root.geometry("1280x400")

    clicked = []

    toolbar = Toolbar(
        root,
        on_start_camera=lambda: clicked.append("start"),
        on_stop_camera=lambda: clicked.append("stop"),
        on_record=lambda: clicked.append("record"),
        on_pause=lambda: clicked.append("pause"),
        on_load_recording=lambda: clicked.append("load"),
        on_play=lambda: clicked.append("play"),
        on_pause_playback=lambda: clicked.append("pause_pb"),
        on_stop_playback=lambda: clicked.append("stop_pb"),
        on_step_forward=lambda: clicked.append("step_fwd"),
        on_step_backward=lambda: clicked.append("step_bwd"),
        on_create_animation=lambda: clicked.append("anim"),
        on_export=lambda: clicked.append("export"),
        on_blender=lambda: clicked.append("blender"),
        on_settings=lambda: clicked.append("settings"),
        on_toggle_theme=lambda: clicked.append("theme"),
        on_filters=lambda: clicked.append("filters"),
        on_exit=lambda: clicked.append("exit"),
    )
    toolbar.pack(fill="x", padx=8, pady=4)

    failures = []
    state = {"done": False}

    def run_checks():
        try:
            # --- Group C: state methods must not raise (fg_color=None fix)
            toolbar.set_camera_started()
            toolbar.set_camera_stopped()
            toolbar.set_recording()
            toolbar.set_paused()
            toolbar.set_resumed()
            toolbar.set_not_recording()
            toolbar.set_playback_loaded()
            toolbar.set_playback_playing()
            toolbar.set_playback_paused()
            toolbar.set_playback_resumed()
            toolbar.set_playback_stopped()
            toolbar.set_playback_finished()
            toolbar.set_no_playback()
            toolbar.set_loop_enabled(True)
            toolbar.set_loop_enabled(False)
            toolbar.set_playback_loaded()
            toolbar.enable_animation()
            toolbar.set_animation_created()
            toolbar.set_animation_cleared()
            toolbar.enable_export()
            toolbar.enable_blender()
            toolbar.set_filters_enabled(True)
            toolbar.set_theme("light")
            toolbar.set_theme("dark")
            check("state methods no ValueError (fg_color fix)", True)

            # --- Group B: scrolling ---
            canvas = toolbar._canvas
            content = toolbar._content

            root.update_idletasks()
            root.update()
            content.update_idletasks()

            content_w = content.winfo_reqwidth()
            view_w = canvas.winfo_width()
            check("content wider than narrow viewport", content_w > view_w,
                  f"(content={content_w}, viewport={view_w})")

            # scrollbar must be visible when content overflows
            visible = toolbar._scrollbar.winfo_ismapped()
            check("scrollbar visible when overflowing", visible)

            # wheel over a button scrolls the canvas right
            canvas.xview_moveto(0)
            toolbar._load_btn.event_generate("<MouseWheel>", delta=120)
            root.update()
            frac = canvas.xview()[0]
            check("mousewheel scrolls toolbar right", frac > 0.0,
                  f"(xview={frac:.3f})")

            # wheel scrolls left again
            toolbar._load_btn.event_generate("<MouseWheel>", delta=-120)
            root.update()
            check("mousewheel scrolls left", canvas.xview()[0] == 0.0,
                  f"(xview={canvas.xview()[0]:.3f})")

            # shift+wheel (trackpad horizontal) scrolls
            before = canvas.xview()[0]
            toolbar._load_btn.event_generate("<Shift-MouseWheel>", delta=120)
            root.update()
            check("shift+wheel scrolls", canvas.xview()[0] != before,
                  f"(xview={canvas.xview()[0]:.3f})")

            # Button-4 (Unix wheel-up) scrolls too
            before = canvas.xview()[0]
            toolbar._load_btn.event_generate("<Button-4>")
            root.update()
            check("Button-4 scrolls", canvas.xview()[0] != before,
                  f"(xview={canvas.xview()[0]:.3f})")

            canvas.xview_moveto(0)
            root.update()
            check("xview_moveto(0) resets", canvas.xview()[0] == 0.0)

            # --- scrollbar hides when the viewport fits the content ---
            # (the real window can't widen past the screen; simulate the
            # content-shrinks case by lowering the tracked content width)
            toolbar._content_width = 100
            toolbar._on_viewport_configure(
                type("E", (), {"width": canvas.winfo_width()})())
            root.update()
            visible = toolbar._scrollbar.winfo_ismapped()
            check("wide viewport: scrollbar hidden", not visible)

            # and returns when the content overflows again
            toolbar._content_width = 3009
            toolbar._on_viewport_configure(
                type("E", (), {"width": canvas.winfo_width()})())
            root.update()
            visible = toolbar._scrollbar.winfo_ismapped()
            check("narrow viewport: scrollbar shown", visible)

            root.geometry("960x400")
            root.update_idletasks()
            root.update()

            # --- callbacks still fire after scrolling ---
            toolbar._load_btn.invoke()
            toolbar._settings_btn.invoke()
            toolbar._exit_btn.invoke()
            check("callbacks fire after scroll", clicked == ["load", "settings", "exit"],
                  f"(clicked={clicked})")

            # --- every button is reachable via scrolling ---
            children = [w for w in content.winfo_children()
                        if isinstance(w, ctk.CTkButton)]
            check("all 18 buttons exist", len(children) == 18, f"(count={len(children)})")

        except Exception as exc:  # pragma: no cover
            failures.append(exc)
            import traceback
            traceback.print_exc()
        finally:
            state["done"] = True
            root.quit()

    root.after(300, run_checks)
    root.mainloop()

    try:
        root.destroy()
    except Exception:
        pass

    ok = not failures and all(r[1] for r in results)
    print("\nSUMMARY:", "ALL PASS" if ok else f"{sum(1 for r in results if not r[1])} FAILURES")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
