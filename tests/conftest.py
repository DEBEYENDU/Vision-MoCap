"""pytest configuration for VisionMoCap tests.

Automatically adds the project root to ``sys.path`` so tests can import
``src`` without package-install ceremony.

Blender integration scripts require the ``bpy`` module (only present when
run inside Blender), so they are excluded from host-pytest collection.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

collect_ignore = [
    "integration/blender_headless_test.py",
    "integration/_toolbar_smoke.py",
]
