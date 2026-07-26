"""Neutral data records shared by the CAD inspection workflow."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CadInsert:
    """Metadata captured from one CAD INSERT entity.

    This model deliberately contains only drawing metadata. It does not
    classify the block as HVAC equipment or apply any estimating rule.
    """

    block_name: str
    layer: str
    x: float
    y: float
    scale_x: float
    scale_y: float
    scale_z: float
    rotation: float


@dataclass(frozen=True, slots=True)
class BlockStatistic:
    """Occurrence summary for one CAD block name.

    Layers are metadata from the drawing only; this record does not infer a
    block's HVAC purpose.
    """

    block_name: str
    count: int
    layers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class IndoorUnitCatalogEntry:
    """One editable manufacturer mapping for a CAD block name."""

    block_name: str
    manufacturer: str
    unit_type: str
    capacity: str
    model: str


@dataclass(frozen=True, slots=True)
class IndoorUnit:
    """A recognized indoor unit with metadata copied from its CAD INSERT."""

    block_name: str
    manufacturer: str
    unit_type: str
    capacity: str
    model: str
    layer: str
    x: float
    y: float


@dataclass(frozen=True, slots=True)
class UnknownBlock:
    """An INSERT block name that has no catalog mapping."""

    block_name: str
    count: int
    layers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class IndoorUnitRecognitionResult:
    """Recognized indoor units and the separately aggregated unknown blocks."""

    indoor_units: tuple[IndoorUnit, ...]
    unknown_blocks: tuple[UnknownBlock, ...]
    total_insert_count: int

    @property
    def indoor_unit_count(self) -> int:
        return len(self.indoor_units)

    @property
    def unknown_insert_count(self) -> int:
        return sum(block.count for block in self.unknown_blocks)

    @property
    def recognition_rate(self) -> float:
        if not self.total_insert_count:
            return 0.0
        return self.indoor_unit_count / self.total_insert_count * 100


@dataclass(frozen=True, slots=True)
class SamsungCatalogCandidate:
    """A review-only Samsung mapping suggestion derived from a block name."""

    block_name: str
    manufacturer: str
    unit_type: str
    capacity: str
    model: str
    confidence: float
