"""Catalog-driven recognition of indoor units from CAD INSERT records."""

from __future__ import annotations

from collections.abc import Iterable

from database.catalog_loader import IndoorUnitCatalog
from engine.model import CadInsert, IndoorUnit, IndoorUnitRecognitionResult, UnknownBlock


class IndoorUnitRecognizer:
    """Recognize only catalog-mapped INSERT blocks; do not infer unknown blocks."""

    def __init__(self, catalog: IndoorUnitCatalog) -> None:
        self.catalog = catalog

    def recognize(self, inserts: Iterable[CadInsert]) -> IndoorUnitRecognitionResult:
        indoor_units: list[IndoorUnit] = []
        unknown_counts: dict[str, int] = {}
        unknown_layers: dict[str, set[str]] = {}
        total_insert_count = 0

        for insert in inserts:
            total_insert_count += 1
            mapping = self.catalog.find(insert.block_name)
            if mapping is None:
                unknown_counts[insert.block_name] = unknown_counts.get(insert.block_name, 0) + 1
                unknown_layers.setdefault(insert.block_name, set()).add(insert.layer)
                continue

            indoor_units.append(
                IndoorUnit(
                    block_name=insert.block_name,
                    manufacturer=mapping.manufacturer,
                    unit_type=mapping.unit_type,
                    capacity=mapping.capacity,
                    model=mapping.model,
                    layer=insert.layer,
                    x=insert.x,
                    y=insert.y,
                )
            )

        unknown_blocks = tuple(
            sorted(
                (
                    UnknownBlock(
                        block_name=block_name,
                        count=count,
                        layers=tuple(sorted(unknown_layers[block_name], key=str.casefold)),
                    )
                    for block_name, count in unknown_counts.items()
                ),
                key=lambda block: (-block.count, block.block_name.casefold()),
            )
        )
        return IndoorUnitRecognitionResult(
            indoor_units=tuple(indoor_units),
            unknown_blocks=unknown_blocks,
            total_insert_count=total_insert_count,
        )
