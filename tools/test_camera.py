#!/usr/bin/env python3
"""Camera test utility for VisionMoCap Studio.

Tests camera indices 0–5 and reports:

    Camera Index  |  Opened  |  Frame Read  |  Resolution

Usage::

    python tools/test_camera.py
"""

from __future__ import annotations

import argparse
import sys

import cv2


def _test_index(index: int, backend: int) -> dict:
    """Test a single (index, backend) combination.

    Returns a dict with keys: opened, frame_read, width, height.
    """
    result: dict = {
        "opened": False,
        "frame_read": False,
        "width": 0,
        "height": 0,
    }
    try:
        cap = cv2.VideoCapture(index, backend)
        if cap.isOpened():
            result["opened"] = True
            ret, frame = cap.read()
            if ret and frame is not None and frame.size > 0:
                result["frame_read"] = True
                h, w = frame.shape[:2]
                result["width"] = max(w, 1)
                result["height"] = max(h, 1)
        cap.release()
    except cv2.error:
        pass
    except Exception:
        pass
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test camera indices 0–5 and report status.",
    )
    parser.add_argument(
        "--max-index", type=int, default=5,
        help="Maximum camera index to test (default: 5).",
    )
    args = parser.parse_args()

    backends = [
        ("DSHOW", cv2.CAP_DSHOW),
        ("ANY", cv2.CAP_ANY),
    ]

    print()
    print("Camera Test")
    print("-" * 60)
    print(f"{'Index':<8} {'Opened':<10} {'Frame Read':<14} {'Resolution':<12} {'Backend':<10}")
    print("-" * 60)

    for index in range(args.max_index + 1):
        best: dict | None = None
        best_backend = ""
        for bname, bcode in backends:
            r = _test_index(index, bcode)
            if r["frame_read"]:
                best = r
                best_backend = bname
                break
            if best is None and r["opened"]:
                best = r
                best_backend = bname

        if best is None:
            best = {"opened": False, "frame_read": False, "width": 0, "height": 0}

        resolution = (
            f"{best['width']}x{best['height']}"
            if best["width"] and best["height"]
            else "-"
        )
        opened = "Yes" if best["opened"] else "No"
        frame_read = "Yes" if best["frame_read"] else "No"

        print(
            f"{index:<8} {opened:<10} {frame_read:<14} {resolution:<12} "
            f"{best_backend:<10}"
        )

    print("-" * 60)
    print("Done.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(1)