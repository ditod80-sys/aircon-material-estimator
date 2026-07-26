"""Read supported CAD drawings into raw modelspace entities."""

from __future__ import annotations

from pathlib import Path

import ezdxf

from converter.oda_converter import ODAConversionError, ODAConverter


class DrawingReadError(RuntimeError):
    """Raised when a drawing cannot be prepared or parsed."""


class DWGReader:
    """Read DWG files through ODA and DXF files directly with ezdxf."""

    SUPPORTED_SUFFIXES = {".dwg", ".dxf"}

    def read(self, drawing_file: str | Path) -> list[object]:
        drawing = Path(drawing_file).expanduser()
        self._validate_input(drawing)

        try:
            dxf_file = ODAConverter().convert(drawing) if drawing.suffix.lower() == ".dwg" else drawing
            document = ezdxf.readfile(dxf_file)
            return list(document.modelspace())
        except ODAConversionError as error:
            raise DrawingReadError(str(error)) from error
        except (OSError, IOError, ezdxf.DXFError) as error:
            raise DrawingReadError(f"Could not read '{drawing}': {error}") from error

    def _validate_input(self, drawing: Path) -> None:
        if not drawing.is_file():
            raise DrawingReadError(f"Drawing file was not found: {drawing}")
        if drawing.suffix.lower() not in self.SUPPORTED_SUFFIXES:
            supported = ", ".join(sorted(self.SUPPORTED_SUFFIXES))
            raise DrawingReadError(f"Unsupported drawing type '{drawing.suffix}'. Supported types: {supported}")
