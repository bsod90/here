"""LED grid geometry.

Two-tier API:
  * Module-level constants (`GRID`, `TOTAL`, `FRAME_BYTES`, `DISTANCES`, …)
    keep the 44×44 default for back-compat — every v1 file that imports
    `from grid import GRID` continues to work without changes.
  * `Grid(size, pitch)` dataclass + `make_grid(size, pitch)` factory let
    tests construct smaller grids for fast pixel-asserting tests, and let
    the scene engine swap geometry at runtime if the matrix size changes.

WLED handles all serpentine/panel remapping internally — we send data in
logical order: index 0 = (0,0) top-left, index `size-1` = (0,size-1)
top-right, index `size` = (1,0) second row, etc.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Grid:
    """Immutable geometry snapshot for an `size`×`size` LED matrix."""
    size: int
    pitch: int                       # mm between adjacent LEDs (physical)
    total: int                       # size * size
    frame_bytes: int                 # total * 3 (RGB)
    center: float                    # (size - 1) / 2 — LED-space center
    positions: list[tuple[int, int]] # (row, col) per linear index
    distances: list[float]           # distance from `center` per LED

    @classmethod
    def make(cls, size: int = 44, pitch: int = 50) -> "Grid":
        return make_grid(size, pitch)


def make_grid(size: int = 44, pitch: int = 50) -> Grid:
    """Factory: build a `Grid` of the given dimensions."""
    if size <= 0:
        raise ValueError(f"grid size must be positive, got {size}")
    total = size * size
    frame_bytes = total * 3
    center = (size - 1) / 2
    positions = [(i // size, i % size) for i in range(total)]
    distances = [
        math.sqrt((col - center) ** 2 + (row - center) ** 2)
        for row, col in positions
    ]
    return Grid(
        size=size,
        pitch=pitch,
        total=total,
        frame_bytes=frame_bytes,
        center=center,
        positions=positions,
        distances=distances,
    )


# Module-level defaults — preserved for v1 callers that import these directly.
DEFAULT_GRID = make_grid(44, 50)

GRID = DEFAULT_GRID.size
TOTAL = DEFAULT_GRID.total
FRAME_BYTES = DEFAULT_GRID.frame_bytes
PITCH = DEFAULT_GRID.pitch
CENTER = DEFAULT_GRID.center
GRID_POSITIONS = DEFAULT_GRID.positions
DISTANCES = DEFAULT_GRID.distances


def linear_to_grid(index: int) -> tuple[int, int]:
    """Convert a linear LED index to (row, col) using the default grid."""
    return (index // GRID, index % GRID)
