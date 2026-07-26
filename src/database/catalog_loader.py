"""Load editable indoor-unit block mappings from JSON catalogs."""

from __future__ import annotations

import json
from pathlib import Path

from engine.model import IndoorUnitCatalogEntry


CATALOG_DIR = Path(__file__).resolve().parent / "catalogs"
CATALOG_FILENAMES = (
    "samsung_indoor_units.json",
    "lg_indoor_units.json",
    "mitsubishi_indoor_units.json",
)
REQUIRED_FIELDS = ("block_name", "manufacturer", "type", "capacity", "model")


class CatalogLoadError(RuntimeError):
    """Raised when an editable catalog cannot be read or validated."""


class CatalogSaveError(RuntimeError):
    """Raised when new Samsung catalog entries cannot be safely appended."""


class IndoorUnitCatalog:
    """Case-insensitive lookup of manufacturer-owned indoor-unit mappings."""

    def __init__(self, entries: list[IndoorUnitCatalogEntry]) -> None:
        self._by_block_name: dict[str, IndoorUnitCatalogEntry] = {}
        for entry in entries:
            normalized_name = entry.block_name.casefold()
            if normalized_name in self._by_block_name:
                existing = self._by_block_name[normalized_name]
                raise CatalogLoadError(
                    "Duplicate block_name across indoor-unit catalogs: "
                    f"'{entry.block_name}' ({existing.manufacturer} and {entry.manufacturer})"
                )
            self._by_block_name[normalized_name] = entry

    @classmethod
    def load_default(cls) -> "IndoorUnitCatalog":
        """Load Samsung first, followed by LG and Mitsubishi catalogs."""
        entries: list[IndoorUnitCatalogEntry] = []
        for filename in CATALOG_FILENAMES:
            catalog_path = CATALOG_DIR / filename
            entries.extend(cls._load_file(catalog_path))
        return cls(entries)

    def find(self, block_name: str) -> IndoorUnitCatalogEntry | None:
        """Return the mapping for a CAD block name, ignoring name case."""
        return self._by_block_name.get(block_name.casefold())

    @property
    def entry_count(self) -> int:
        """Return the total number of mappings across all loaded catalogs."""
        return len(self._by_block_name)

    def contains(self, block_name: str) -> bool:
        """Return whether a mapping exists for the supplied block name."""
        return block_name.casefold() in self._by_block_name

    @staticmethod
    def _load_file(catalog_path: Path) -> list[IndoorUnitCatalogEntry]:
        try:
            data = json.loads(catalog_path.read_text(encoding="utf-8"))
        except FileNotFoundError as error:
            raise CatalogLoadError(f"Indoor-unit catalog was not found: {catalog_path}") from error
        except (OSError, json.JSONDecodeError) as error:
            raise CatalogLoadError(f"Could not read indoor-unit catalog '{catalog_path}': {error}") from error

        if not isinstance(data, list):
            raise CatalogLoadError(f"Indoor-unit catalog must contain a JSON list: {catalog_path}")

        entries: list[IndoorUnitCatalogEntry] = []
        for index, mapping in enumerate(data, start=1):
            if not isinstance(mapping, dict):
                raise CatalogLoadError(f"Catalog entry {index} in '{catalog_path.name}' must be an object.")
            missing_fields = [field for field in REQUIRED_FIELDS if field not in mapping]
            if missing_fields:
                raise CatalogLoadError(
                    f"Catalog entry {index} in '{catalog_path.name}' is missing: {', '.join(missing_fields)}"
                )
            if any(not isinstance(mapping[field], str) for field in REQUIRED_FIELDS):
                raise CatalogLoadError(
                    f"Catalog entry {index} in '{catalog_path.name}' must use strings for all required fields."
                )
            if any(not mapping[field].strip() for field in REQUIRED_FIELDS):
                raise CatalogLoadError(
                    f"Catalog entry {index} in '{catalog_path.name}' cannot contain blank required fields."
                )

            entries.append(
                IndoorUnitCatalogEntry(
                    block_name=mapping["block_name"].strip(),
                    manufacturer=mapping["manufacturer"].strip(),
                    unit_type=mapping["type"].strip(),
                    capacity=mapping["capacity"].strip(),
                    model=mapping["model"].strip(),
                )
            )

        return entries


class SamsungCatalogRepository:
    """Append validated mappings to the Samsung JSON catalog only."""

    SAMSUNG_CATALOG_PATH = CATALOG_DIR / "samsung_indoor_units.json"

    def append(self, entries: list[IndoorUnitCatalogEntry]) -> int:
        """Append complete Samsung mappings after rejecting all duplicate names."""
        if not entries:
            return 0

        catalog = IndoorUnitCatalog.load_default()
        submitted_names: set[str] = set()
        for entry in entries:
            normalized_name = entry.block_name.casefold()
            if entry.manufacturer.casefold() != "samsung":
                raise CatalogSaveError(
                    f"Samsung catalog entries must use manufacturer 'Samsung': {entry.block_name}"
                )
            if catalog.contains(entry.block_name):
                raise CatalogSaveError(f"Block name already exists in a catalog: {entry.block_name}")
            if normalized_name in submitted_names:
                raise CatalogSaveError(f"Duplicate block name in rows selected for saving: {entry.block_name}")
            submitted_names.add(normalized_name)

        try:
            raw_entries = json.loads(self.SAMSUNG_CATALOG_PATH.read_text(encoding="utf-8"))
        except FileNotFoundError as error:
            raise CatalogSaveError(f"Samsung catalog was not found: {self.SAMSUNG_CATALOG_PATH}") from error
        except (OSError, json.JSONDecodeError) as error:
            raise CatalogSaveError(f"Could not read Samsung catalog: {error}") from error
        if not isinstance(raw_entries, list):
            raise CatalogSaveError("Samsung catalog must contain a JSON list.")

        raw_entries.extend(
            {
                "block_name": entry.block_name,
                "manufacturer": "Samsung",
                "type": entry.unit_type,
                "capacity": entry.capacity,
                "model": entry.model,
            }
            for entry in entries
        )
        temporary_path = self.SAMSUNG_CATALOG_PATH.with_suffix(".json.tmp")
        try:
            temporary_path.write_text(
                json.dumps(raw_entries, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            temporary_path.replace(self.SAMSUNG_CATALOG_PATH)
        except OSError as error:
            raise CatalogSaveError(f"Could not save Samsung catalog: {error}") from error

        return len(entries)
