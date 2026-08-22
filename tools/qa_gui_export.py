"""GUI-level regression for the Load-JSON -> Export bug.

Drives the REAL MainWindow handlers with stubbed file dialogs:
  1. _on_load_recording  (Load JSON)
  2. _on_create_animation (Create Animation)
  3. _on_export           (Export -> BVH)
and asserts the Export button becomes enabled and a valid BVH is written
for BOTH a loaded JSON recording and the animation-created state.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import customtkinter as ctk

from src.config.manager import AppConfig
from src.gui.app_controller import AppController
from src.gui.main_window import MainWindow

RECORDING = Path("exports/recordings/recording_1785820551.json")
OUT_DIR = Path("exports/qa_gui")
OUT_BVH = OUT_DIR / "gui_loaded.bvh"
OUT_BVH2 = OUT_DIR / "gui_anim.bvh"

passed = 0
failed = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS  {name}" + (f"  ({detail})" if detail else ""))
    else:
        failed += 1
        print(f"  FAIL  {name}  {detail}")


def main() -> int:
    global passed, failed
    ctrl = AppController(config=AppConfig())
    window = MainWindow(controller=ctrl)
    window.initialize()

    from tkinter import filedialog
    dialog_state = {"next_save": str(OUT_BVH)}
    filedialog.askopenfilename = lambda **kw: str(RECORDING)
    filedialog.asksaveasfilename = lambda **kw: dialog_state["next_save"]

    try:
        print("\n[PATH A] Load JSON -> Create Animation -> Export")
        window._on_load_recording()
        check("recording loaded", ctrl.has_playback_sequence,
              f"{ctrl.playback_total_frames} frames")
        check("Export button ENABLED after load",
              window._toolbar._export_btn.cget("state") == "normal")
        check("Create Animation button ENABLED",
              window._toolbar._create_anim_btn.cget("state") == "normal")

        window._on_create_animation()
        check("animation created + stored", ctrl.has_animation,
              f"{ctrl.animation_clip.frame_count} keyframes")
        check("Export button ENABLED after animation",
              window._toolbar._export_btn.cget("state") == "normal")

        window._on_export()
        check("BVH exported via GUI handler", OUT_BVH.exists(), str(OUT_BVH))
        if OUT_BVH.exists():
            text = OUT_BVH.read_text(encoding="utf-8")
            check("BVH valid", "HIERARCHY" in text and "MOTION" in text,
                  f"{OUT_BVH.stat().st_size} bytes")

        print("\n[PATH B] Create Animation again, export to second file")
        dialog_state["next_save"] = str(OUT_BVH2)
        window._on_create_animation()
        window._on_export()
        check("second BVH exported (re-animation path)",
              OUT_BVH2.exists() and OUT_BVH2.stat().st_size > 0)

        print("\n[CLEANUP] file handles")
        for p in (OUT_BVH, OUT_BVH2):
            try:
                p.unlink()
                print(f"  PASS  deleted {p.name}")
            except PermissionError:
                print(f"  FAIL  locked {p.name}")
                failed += 1
        try:
            OUT_DIR.rmdir()
        except OSError:
            pass

        ctrl.shutdown()
        window._window.destroy()
        print(f"\n===== GUI REGRESSION: {passed} passed, {failed} failed =====")
        return 0 if failed == 0 else 1
    except Exception:
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
