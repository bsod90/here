"""LED grid constants and serpentine mapping.

Ported from software/simulator/public/js/leds.js.
"""
import math

GRID = 44          # 44×44 matrix
TOTAL = GRID * GRID  # 1936 LEDs
HALF = GRID // 2   # 22 columns per channel
FRAME_BYTES = TOTAL * 3  # 5808 bytes per RGB frame
PITCH = 50         # mm between LEDs
CENTER = (GRID - 1) / 2  # 21.5


def linear_to_grid(index: int) -> tuple[int, int]:
    """Convert linear LED index (0-1935) to (row, col) grid position.

    Serpentine layout: 2 channels of 22 columns each.
    Channel 0 = cols 0-21, Channel 1 = cols 22-43.
    Even rows: left→right, odd rows: right→left within each half.
    """
    channel = 0 if index < GRID * HALF else 1
    local_index = index - channel * (GRID * HALF)
    row = local_index // HALF
    local_col = local_index % HALF
    if row % 2 != 0:
        local_col = HALF - 1 - local_col
    col = local_col if channel == 0 else local_col + HALF
    return (row, col)


# Pre-computed grid positions for every LED
GRID_POSITIONS: list[tuple[int, int]] = [linear_to_grid(i) for i in range(TOTAL)]

# Pre-computed distance from grid center for every LED (used by animations)
DISTANCES: list[float] = [
    math.sqrt((col - CENTER) ** 2 + (row - CENTER) ** 2)
    for row, col in GRID_POSITIONS
]
