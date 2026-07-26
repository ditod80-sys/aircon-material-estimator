"""Application paths and configuration defaults."""

from __future__ import annotations

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
SAMPLES_DIR = ROOT_DIR / "samples"
OUTPUT_DIR = ROOT_DIR / "output"
TEMP_DIR = ROOT_DIR / "temp"

DEFAULT_ODA_EXE = Path(r"C:\Program Files\ODA\ODAFileConverter 27.1.0\ODAFileConverter.exe")
ODA_EXE = Path(os.environ.get("AIRCON_ODA_EXE", DEFAULT_ODA_EXE)).expanduser()
DXF_VERSION = "ACAD2018"

APP_NAME = "Aircon Material Estimator"
VERSION = "0.1.0"
