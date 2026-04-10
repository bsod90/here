"""Debug grid pattern — static 6x6 grid of 2-LED-thick lines in varying colors."""
from grid import GRID, TOTAL

# 6x6 grid means lines every ~7.3 LEDs. Use spacing of 7.
SPACING = 7
LINE_WIDTH = 2

# Each grid line gets a distinct color for easy identification
COLORS = [
    (255, 0, 0),      # red
    (0, 255, 0),      # green
    (0, 0, 255),      # blue
    (255, 255, 0),    # yellow
    (255, 0, 255),    # magenta
    (0, 255, 255),    # cyan
    (255, 128, 0),    # orange
]


def render(frame: bytearray, time_ms: float, params: dict):
    # Clear
    for i in range(len(frame)):
        frame[i] = 0

    # Draw horizontal lines
    for line_idx in range(7):
        row_center = line_idx * SPACING
        color = COLORS[line_idx % len(COLORS)]
        for w in range(LINE_WIDTH):
            row = row_center + w
            if 0 <= row < GRID:
                for col in range(GRID):
                    idx = row * GRID + col
                    off = idx * 3
                    frame[off] = color[0]
                    frame[off + 1] = color[1]
                    frame[off + 2] = color[2]

    # Draw vertical lines (overwrite where they cross for a grid look)
    for line_idx in range(7):
        col_center = line_idx * SPACING
        color = COLORS[(line_idx + 3) % len(COLORS)]  # offset palette so verticals differ
        for w in range(LINE_WIDTH):
            col = col_center + w
            if 0 <= col < GRID:
                for row in range(GRID):
                    idx = row * GRID + col
                    off = idx * 3
                    # Blend with existing (average at intersections)
                    r = (frame[off] + color[0]) // 2 if frame[off] > 0 else color[0]
                    g = (frame[off + 1] + color[1]) // 2 if frame[off + 1] > 0 else color[1]
                    b = (frame[off + 2] + color[2]) // 2 if frame[off + 2] > 0 else color[2]
                    frame[off] = r
                    frame[off + 1] = g
                    frame[off + 2] = b
