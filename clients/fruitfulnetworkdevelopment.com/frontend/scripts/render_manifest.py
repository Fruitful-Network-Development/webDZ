#!/usr/bin/env python3
"""Build the current frontend from its content manifest."""

from __future__ import annotations

import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from render_lib.site_builder import build_site


if __name__ == "__main__":
    build_site(SCRIPT_ROOT.parent)
