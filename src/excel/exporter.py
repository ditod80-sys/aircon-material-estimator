"""Export inspection results to files consumable by spreadsheet software."""

from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path

from database.settings import OUTPUT_DIR
from engine.model import BlockStatistic, CadInsert, IndoorUnit


class InsertCsvExportError(RuntimeError):
    """Raised when INSERT metadata cannot be written to CSV."""


class InsertCsvExporter:
    """Write neutral CAD INSERT metadata to a UTF-8 CSV file."""

    FIELDNAMES = (
        "block_name",
        "layer",
        "x",
        "y",
        "scale_x",
        "scale_y",
        "scale_z",
        "rotation",
    )

    def export(self, drawing_path: str | Path, inserts: Iterable[CadInsert]) -> Path:
        """Export every supplied INSERT record and return the created CSV path."""
        drawing = Path(drawing_path)
        output_path = OUTPUT_DIR / f"{drawing.stem}_insert_entities.csv"

        try:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            with output_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=self.FIELDNAMES)
                writer.writeheader()
                for insert in inserts:
                    writer.writerow(
                        {
                            "block_name": insert.block_name,
                            "layer": insert.layer,
                            "x": insert.x,
                            "y": insert.y,
                            "scale_x": insert.scale_x,
                            "scale_y": insert.scale_y,
                            "scale_z": insert.scale_z,
                            "rotation": insert.rotation,
                        }
                    )
        except OSError as error:
            raise InsertCsvExportError(f"Could not write CSV file '{output_path}': {error}") from error

        return output_path


class BlockStatisticsCsvExportError(RuntimeError):
    """Raised when block statistics cannot be written to CSV."""


class BlockStatisticsCsvExporter:
    """Write grouped CAD block occurrence statistics to a UTF-8 CSV file."""

    FIELDNAMES = ("Block Name", "Count", "Layer(s)")

    def export(self, drawing_path: str | Path, statistics: Iterable[BlockStatistic]) -> Path:
        """Export block-name counts, sorted by the supplied statistics order."""
        drawing = Path(drawing_path)
        output_path = OUTPUT_DIR / f"{drawing.stem}_block_statistics.csv"

        try:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            with output_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=self.FIELDNAMES)
                writer.writeheader()
                for statistic in statistics:
                    writer.writerow(
                        {
                            "Block Name": statistic.block_name,
                            "Count": statistic.count,
                            "Layer(s)": ", ".join(statistic.layers),
                        }
                    )
        except OSError as error:
            raise BlockStatisticsCsvExportError(
                f"Could not write block statistics CSV '{output_path}': {error}"
            ) from error

        return output_path


class IndoorUnitsCsvExportError(RuntimeError):
    """Raised when recognized indoor units cannot be written to CSV."""


class IndoorUnitsCsvExporter:
    """Write catalog-recognized indoor units to a UTF-8 CSV file."""

    FIELDNAMES = ("Block Name", "Manufacturer", "Type", "Capacity", "Model", "Layer", "X", "Y")

    def export(self, drawing_path: str | Path, indoor_units: Iterable[IndoorUnit]) -> Path:
        """Export recognized units and return the created CSV path."""
        drawing = Path(drawing_path)
        output_path = OUTPUT_DIR / f"{drawing.stem}_indoor_units.csv"

        try:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            with output_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=self.FIELDNAMES)
                writer.writeheader()
                for unit in indoor_units:
                    writer.writerow(
                        {
                            "Block Name": unit.block_name,
                            "Manufacturer": unit.manufacturer,
                            "Type": unit.unit_type,
                            "Capacity": unit.capacity,
                            "Model": unit.model,
                            "Layer": unit.layer,
                            "X": unit.x,
                            "Y": unit.y,
                        }
                    )
        except OSError as error:
            raise IndoorUnitsCsvExportError(
                f"Could not write indoor-units CSV '{output_path}': {error}"
            ) from error

        return output_path
