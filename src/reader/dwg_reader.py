"""Read supported CAD drawings into raw modelspace entities."""

from __future__ import annotations

from pathlib import Path

import ezdxf

from converter.oda_converter import ODAConversionError, ODAConverter
from engine.model import CadInsert


class DrawingReadError(RuntimeError):
    """Raised when a drawing cannot be prepared or parsed."""


class DWGReader:
    """Read DWG files through ODA and DXF files directly with ezdxf."""

    SUPPORTED_SUFFIXES = {".dwg", ".dxf"}

    def read(self, drawing_file: str | Path) -> list[object]:
        """Return all raw modelspace entities for the selected drawing."""
        document = self._load_document(drawing_file)
        return list(document.modelspace())

    def read_inserts(self, drawing_file: str | Path) -> list[CadInsert]:
        """Return metadata for every INSERT entity across every drawing layout."""
        document = self._load_document(drawing_file)
        inserts: list[CadInsert] = []

        try:
            for layout in document.layouts:
                for entity in layout:
                    if entity.dxftype() == "INSERT":
                        inserts.append(self._to_cad_insert(entity))
        except (AttributeError, TypeError, ValueError) as error:
            raise DrawingReadError(f"Could not inspect INSERT entities: {error}") from error

        return inserts

    def _load_document(self, drawing_file: str | Path):
        drawing = Path(drawing_file).expanduser()
        self._validate_input(drawing)

        try:
            dxf_file = ODAConverter().convert(drawing) if drawing.suffix.lower() == ".dwg" else drawing
            return ezdxf.readfile(dxf_file)
        except ODAConversionError as error:
            raise DrawingReadError(str(error)) from error
        except (OSError, IOError, ezdxf.DXFError) as error:
            raise DrawingReadError(f"Could not read '{drawing}': {error}") from error

    @staticmethod
    def _to_cad_insert(entity: object) -> CadInsert:
        dxf = entity.dxf
        insertion_point = dxf.insert
        return CadInsert(
            block_name=str(dxf.name),
            layer=str(dxf.layer),
            x=float(insertion_point.x),
            y=float(insertion_point.y),
            scale_x=float(getattr(dxf, "xscale", 1.0)),
            scale_y=float(getattr(dxf, "yscale", 1.0)),
            scale_z=float(getattr(dxf, "zscale", 1.0)),
            rotation=float(getattr(dxf, "rotation", 0.0)),
        )

    def _validate_input(self, drawing: Path) -> None:
        if not drawing.is_file():
            raise DrawingReadError(f"Drawing file was not found: {drawing}")
        if drawing.suffix.lower() not in self.SUPPORTED_SUFFIXES:
            supported = ", ".join(sorted(self.SUPPORTED_SUFFIXES))
            raise DrawingReadError(f"Unsupported drawing type '{drawing.suffix}'. Supported types: {supported}")
