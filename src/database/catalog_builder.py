"""Build review-only Samsung catalog candidates from block-statistics CSV files."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from database.settings import OUTPUT_DIR
from engine.model import SamsungCatalogCandidate


class CatalogBuilderError(RuntimeError):
    """Raised when catalog-candidate input or output cannot be processed."""


class SamsungCatalogCandidateBuilder:
    """Infer limited, non-authoritative Samsung mapping metadata from block names."""

    OUTPUT_FILENAME = "samsung_catalog_candidates.json"
    REQUIRED_COLUMNS = ("Block Name", "Count", "Layer(s)")
    TYPE_PATTERNS = (
        (re.compile(r"1\s*[-_ ]?WAY", re.IGNORECASE), "1Way"),
        (re.compile(r"2\s*[-_ ]?WAY", re.IGNORECASE), "2Way"),
        (re.compile(r"4\s*[-_ ]?WAY", re.IGNORECASE), "4Way"),
        (re.compile(r"(?<!\d)360(?!\d)"), "360"),
    )
    CAPACITY_PATTERN = re.compile(r"(?<!\d)(016|020|023|032|040|052|072|090|112|140)(?!\d)")

    def build_from_statistics(self, statistics_path: str | Path) -> list[SamsungCatalogCandidate]:
        """Read block statistics and create one conservative candidate per block name."""
        rows = self._read_statistics(Path(statistics_path))
        return [self.suggest_for_block_name(block_name) for block_name in rows]

    def suggest_for_block_name(self, block_name: str) -> SamsungCatalogCandidate:
        """Return a non-authoritative suggestion for one CAD block name."""
        return self._candidate_from_block_name(block_name)

    def export(self, candidates: list[SamsungCatalogCandidate]) -> Path:
        """Write candidates outside the source catalogs and return the output path."""
        output_path = OUTPUT_DIR / self.OUTPUT_FILENAME
        payload = [
            {
                "block_name": candidate.block_name,
                "manufacturer": candidate.manufacturer,
                "type": candidate.unit_type,
                "capacity": candidate.capacity,
                "model": candidate.model,
                "confidence": candidate.confidence,
            }
            for candidate in candidates
        ]

        try:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError as error:
            raise CatalogBuilderError(f"Could not write Samsung catalog candidates '{output_path}': {error}") from error

        return output_path

    def _read_statistics(self, statistics_path: Path) -> list[str]:
        try:
            with statistics_path.open("r", newline="", encoding="utf-8-sig") as csv_file:
                reader = csv.DictReader(csv_file)
                if reader.fieldnames is None:
                    raise CatalogBuilderError(f"Block statistics CSV has no header row: {statistics_path}")
                missing_columns = [column for column in self.REQUIRED_COLUMNS if column not in reader.fieldnames]
                if missing_columns:
                    raise CatalogBuilderError(
                        f"Block statistics CSV is missing columns: {', '.join(missing_columns)}"
                    )

                block_names: list[str] = []
                for row_number, row in enumerate(reader, start=2):
                    block_name = (row["Block Name"] or "").strip()
                    if not block_name:
                        raise CatalogBuilderError(f"Block statistics CSV has a blank Block Name at row {row_number}.")
                    try:
                        count = int(row["Count"] or "")
                    except ValueError as error:
                        raise CatalogBuilderError(
                            f"Block statistics CSV has an invalid Count at row {row_number}."
                        ) from error
                    if count < 1:
                        raise CatalogBuilderError(f"Block statistics CSV has a non-positive Count at row {row_number}.")
                    block_names.append(block_name)
                return block_names
        except FileNotFoundError as error:
            raise CatalogBuilderError(
                f"Block statistics CSV was not found: {statistics_path}. Run INSERT inspection first."
            ) from error
        except OSError as error:
            raise CatalogBuilderError(f"Could not read block statistics CSV '{statistics_path}': {error}") from error

    def _candidate_from_block_name(self, block_name: str) -> SamsungCatalogCandidate:
        unit_type = self._find_type(block_name)
        capacity_match = self.CAPACITY_PATTERN.search(block_name)
        capacity = capacity_match.group(1) if capacity_match else ""

        confidence = 0.0
        if unit_type:
            confidence += 0.5
        if capacity:
            confidence += 0.4
        if "SAMSUNG" in block_name.upper():
            confidence += 0.1

        return SamsungCatalogCandidate(
            block_name=block_name,
            manufacturer="Samsung",
            unit_type=unit_type,
            capacity=capacity,
            model="",
            confidence=round(confidence, 2),
        )

    def _find_type(self, block_name: str) -> str:
        for pattern, unit_type in self.TYPE_PATTERNS:
            if pattern.search(block_name):
                return unit_type
        return ""
