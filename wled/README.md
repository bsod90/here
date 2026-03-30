# WLED Configuration

## Matrix Setup

- **Size**: 44 columns x 44 rows = 1,936 LEDs
- **Layout**: Serpentine (zigzag) wiring
- **LED type**: WS2812B (or similar — TBD)

## Files

- `wled_cfg.json` — Full WLED backup/config (export from WLED UI)
- `presets.json` — Animation presets

## WLED API

The orchestrator communicates with WLED via its JSON API:
- `http://<wled-ip>/json/state` — get/set state
- `http://<wled-ip>/json/si` — state + info combined
- UDP port 21324 — real-time LED data (DRGB/DNRGB protocol)

For 1,936 LEDs at 30fps, UDP (DNRGB) is the recommended transport.
