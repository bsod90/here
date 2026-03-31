# HERE - Burning Man 2026 Breathing Meditation Installation

## Project Overview

![[87AB6094-8DEC-43B0-8CF4-D0AF3FF20901_1_105_c.jpeg]]

A guided breathing meditation installation for Burning Man. Participants sit on a bench centered on a ~8×8ft wooden platform (2× 4×8ft plywood sheets) embedded with a 44×44 LED matrix. The LEDs display breathing-synchronized radial animations while audio guides the meditation. Solar-powered (or battery-only with 2 batteries).

The bench is a **plywood box** (5ft × 20in × 14in) oriented diagonally on the platform, sitting on 4×4 lumber legs. It doubles as the electronics enclosure housing the battery, RPi, WLED controller, speakers (facing down), and a ventilation fan with dust filter for positive pressure. See [bench/bench.md](bench/bench.md) for the 3D model and interior layout.

## Hardware

See [docs/inventory.md](docs/inventory.md) for full BOM with links.

- **LED Matrix**: 44x44 WS2811 pebble pixel strips (DC12V) — 2x 22x44 panels on 4x8ft plywood sheets
- **Controller**: Gledopto WLED controller (ESP32, Ethernet)
- **Orchestrator**: Raspberry Pi 4 — runs the meditation sequences, audio playback, and WLED coordination
- **Power**: ~200W solar panel + charge controller → 12V 100Ah LiFePO4 battery (1,280Wh)

## Architecture

```
[Solar] → [Battery] → [RPi 4] → (Ethernet) → [WLED ESP32] → [44x44 LED matrix]
                        ↓ 3.5mm
                   [ZK-1002T amp] → [2× Pyle 6.5" marine speakers]
                        ↓ BLE
                   [Phone control app] (Flutter, mode toggle, logs)
                        ↓ BT A2DP
                   [Phone music] → RPi → PipeWire (mix + FFT) → amp
```

## Repository Structure

```
here/
├── CLAUDE.md              # This file
├── bench/                 # Bench/enclosure design (OpenSCAD + 3D models)
├── docs/                  # Design docs, diagrams, BOM, inventory
├── rpi/
│   ├── scripts/           # RPi setup & provisioning scripts
│   └── configs/           # System configs (systemd units, network, etc.)
├── software/
│   ├── orchestrator/      # Main meditation orchestrator (runs on RPi)
│   ├── animations/        # LED animation generators / presets
│   └── mobile/            # Mobile control app (if needed)
├── wled/                  # WLED configs, presets, JSON API scripts
└── notes/                 # Obsidian vault — design notes, journal, ideas
```

## Development Guidelines

- Target platform: Raspberry Pi 4 running Raspberry Pi OS (Bookworm)
- WLED communication via its JSON/HTTP API or UDP
- LED animations should be testable without hardware (simulator/preview mode)
- Keep scripts idempotent — safe to re-run on the RPi
- All configs should be version-controlled; no secrets in the repo

## WLED Notes

- Matrix: 44x44 = 1,936 LEDs
- WLED supports 2D matrix mode natively
- Coordinate system: define origin and serpentine layout in WLED config
- Use WLED JSON API for real-time control from the orchestrator
