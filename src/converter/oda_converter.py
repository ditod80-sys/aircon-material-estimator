"""Adapter for the external ODA File Converter used for DWG input."""

from __future__ import annotations

import subprocess
from pathlib import Path

from database.settings import DXF_VERSION, ODA_EXE, TEMP_DIR


class ODAConversionError(RuntimeError):
    """Raised when DWG conversion cannot complete."""


class ODAConverter:
    """Convert a DWG file to DXF using a locally installed ODA converter."""

    def __init__(self, executable: Path = ODA_EXE) -> None:
        self.executable = executable

    def convert(self, dwg_path: str | Path) -> Path:
        dwg = Path(dwg_path).expanduser()
        if not dwg.is_file():
            raise ODAConversionError(f"DWG file was not found: {dwg}")
        if dwg.suffix.lower() != ".dwg":
            raise ODAConversionError(f"Expected a .dwg file, received: {dwg.name}")
        if not self.executable.is_file():
            raise ODAConversionError(
                "ODA File Converter was not found. Configure AIRCON_ODA_EXE or install ODA File Converter.\n"
                f"Configured path: {self.executable}"
            )

        output_dir = TEMP_DIR / dwg.stem
        output_dir.mkdir(parents=True, exist_ok=True)
        output_dxf = output_dir / f"{dwg.stem}.dxf"

        command = [
            str(self.executable),
            str(dwg.parent),
            str(output_dir),
            DXF_VERSION,
            "DXF",
            "0",
            "1",
            dwg.name,
        ]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
        except OSError as error:
            raise ODAConversionError(f"Could not start ODA File Converter: {error}") from error
        except subprocess.TimeoutExpired as error:
            raise ODAConversionError("ODA File Converter did not finish within 120 seconds.") from error

        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "No converter output was provided."
            raise ODAConversionError(f"ODA File Converter failed (exit code {result.returncode}):\n{detail}")
        if not output_dxf.is_file():
            raise ODAConversionError(f"ODA File Converter completed but did not create: {output_dxf}")

        return output_dxf
