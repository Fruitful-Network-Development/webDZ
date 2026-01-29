"""Data environment config."""
from __future__ import annotations

import os

DATA_ENV_ROOT = os.getenv("DATA_ENV_ROOT", "/srv/demo-data")
DATA_ENV_BOOTSTRAP = os.getenv("DATA_ENV_BOOTSTRAP", "platform.profile.json")

