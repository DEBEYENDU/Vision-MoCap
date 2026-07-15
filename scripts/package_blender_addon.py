"""Package the VisionMoCap Blender add-on as a ``.zip`` file.

Usage::

    python scripts/package_blender_addon.py

The resulting ``visionmocap_addon.zip`` is written to the project root.
Install it in Blender via Edit → Preferences → Add-ons → Install….
"""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path


_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ADDON_SRC = _PROJECT_ROOT / "src" / "blender" / "addon"
_OUTPUT = _PROJECT_ROOT / "visionmocap_addon.zip"


def main() -> None:
    if not _ADDON_SRC.exists():
        print(f"Add-on source not found: {_ADDON_SRC}")
        raise SystemExit(1)

    if _OUTPUT.exists():
        _OUTPUT.unlink()

    with zipfile.ZipFile(_OUTPUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for py_file in sorted(_ADDON_SRC.rglob("*.py")):
            arcname = f"visionmocap_addon/{py_file.relative_to(_ADDON_SRC)}"
            zf.write(py_file, arcname)
            print(f"  Added {arcname}")

    print(f"\nAdd-on packaged: {_OUTPUT}")
    print("Install in Blender: Edit → Preferences → Add-ons → Install…")


if __name__ == "__main__":
    main()
