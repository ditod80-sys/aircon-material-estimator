"""Generic aggregation of CAD INSERT metadata."""

from __future__ import annotations

from collections.abc import Iterable

from engine.model import BlockStatistic, CadInsert


class BlockStatisticsBuilder:
    """Group INSERT records by exact block name without classifying them."""

    def build(self, inserts: Iterable[CadInsert]) -> list[BlockStatistic]:
        counts: dict[str, int] = {}
        layers_by_block: dict[str, set[str]] = {}

        for insert in inserts:
            counts[insert.block_name] = counts.get(insert.block_name, 0) + 1
            layers_by_block.setdefault(insert.block_name, set()).add(insert.layer)

        statistics = [
            BlockStatistic(
                block_name=block_name,
                count=count,
                layers=tuple(sorted(layers_by_block[block_name], key=str.casefold)),
            )
            for block_name, count in counts.items()
        ]
        return sorted(statistics, key=lambda item: (-item.count, item.block_name.casefold()))
