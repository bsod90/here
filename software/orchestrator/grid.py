"""LED grid constants — simple row-major mapping.

WLED handles all serpentine/panel remapping internally.
We send data in logical order: index 0 = (0,0) top-left,
index 43 = (0,43) top-right, index 44 = (1,0) second row, etc.
"""
import math

GRID = 44
TOTAL = GRID * GRID  # 1936
FRAME_BYTES = TOTAL * 3
PITCH = 50
CENTER = (GRID - 1) / 2  # 21.5


def linear_to_grid(index: int) -> tuple[int, int]:
    return (index // GRID, index % GRID)


GRID_POSITIONS: list[tuple[int, int]] = [linear_to_grid(i) for i in range(TOTAL)]

DISTANCES: list[float] = [
    math.sqrt((col - CENTER) ** 2 + (row - CENTER) ** 2)
    for row, col in GRID_POSITIONS
]
