# Hardware Inventory

## Compute & Control

| Item | Qty | Status | Notes |
|------|-----|--------|-------|
| Raspberry Pi 4 | 1 | Have | Orchestrator — runs meditation sequences, audio, WLED control |
| [Gledopto WLED Controller GL-C-618WL (Ethernet)](https://www.amazon.com/dp/B0FZ7WCYCK) | 1 | Have | ESP32-based, 4-channel, Ethernet + WiFi |

### Gledopto WLED Controller Specs

- **MCU:** ESP32 (dual-core, WiFi + Bluetooth)
- **Connectivity:** Ethernet (RJ45) + WiFi + USB-C (flashing/UART)
- **Output channels:** 4 independent digital LED channels
- **GPIO pins:** GPIO16 (default), GPIO2, IO18, IO19, IO25, IO33
- **Max addressable ICs:** 1,600 total
- **Input voltage:** DC 5V / 12V / 24V
- **Max output current:** 15A total, 10A per channel
- **Fuse:** 20A replaceable (5A spare included)
- **Built-in:** Level shifter, ESD protection, energy-saving relay, I2S microphone (sound-reactive)
- **Housing:** IP20 (needs weatherproof enclosure for playa)
- **Dimensions:** 129 × 50 × 23mm

**Channel plan:** 2 channels used (of 4 available), one per 22×44 panel half = 968 LEDs/channel.
WLED on ESP32 supports up to 1,000 LEDs per channel, so this is within limits.

---

## LED Matrix

| Item | Qty | Status | Notes |
|------|-----|--------|-------|
| [WS2811 Pebble Pixel LED strips (DC12V)](https://www.amazon.com/dp/B0CDWNVK2F) | ~2,000 | Have | Arranged into 2× 22×44 matrices on plywood |
| 4×8ft plywood sheets | 2 | Have | Substrate for LED matrices |

**Matrix layout:** 2 panels of 22×44 LEDs side by side → 44×44 total (1,936 LEDs)

### LED Specs

- **IC:** WS2811 (not WS2812B — these are 12V, not 5V)
- **Voltage:** DC 12V
- **Power per LED:** 0.1W (~8mA per pixel)
- **Full white power (1,936 LEDs):** ~194W @ 12V (~16A)
- **LED spacing:** 5cm pitch, 20 LEDs/m
- **Color depth:** 24-bit RGB (GRB order), 256 brightness levels
- **Viewing angle:** 360°
- **IP rating:** IP65 (sealed pebble encapsulation — good for playa dust)
- **Operating temp:** −20°C to +50°C
- **Lifespan:** 50,000+ hours
- **Power injection:** Recommended every 100 LEDs
- **Wire:** 3-conductor (~22 AWG), bare pigtails

---

## Power

| Item | Qty | Status | Notes |
|------|-----|--------|-------|
| [ECO-WORTHY LiFePO4 battery](https://www.amazon.com/dp/B09W245MXD) | 1 | Have | See specs below — verify 12V vs 48V variant |
| ~200W solar panel | 1 | Have | With charge controller |

### Battery Specs (from Amazon listing — 48V variant)

> **NOTE:** The Amazon link resolves to a **48V 50Ah (2,560Wh)** battery. If you
> actually have the 12V 100Ah variant, update the specs below accordingly.

- **Nominal voltage:** 51.2V (48V nominal)
- **Capacity:** 50Ah / 2,560Wh
- **Max continuous charge/discharge:** 50A
- **Peak current:** 300A
- **BMS:** Built-in 50A (overcharge, over-discharge, overcurrent, short circuit)
- **Cycle life:** 3,000+ deep cycles (80% capacity retention)
- **Charge temp:** 0°C to 55°C
- **Discharge temp:** −20°C to 55°C
- **Weight:** 44.75 lbs (20.3 kg)
- **Terminals:** M8 screw

### Solar

- ~200W panel
- Charge controller (model TBD)
- At Black Rock City in late August: ~6 peak sun hours/day → **~1,200Wh/day** solar input

---

## Audio

| Item | Qty | Status | Notes |
|------|-----|--------|-------|
| [Pyle PLMRS6B 6.5" Marine Speakers](https://www.amazon.com/dp/B07FMKC7HW) | 1 pair | TBD | Marine-grade, facing down through bench bottom. 60W RMS/ea, 4 ohm, 90 dB, 60Hz-18kHz. Super slim 23mm mounting depth. |
| [ZK-1002T Class D Amp (BT 5.0 + AUX)](https://www.amazon.com/ZK-1002T-Bluetooth-Amplifier-Antenna-TPA3116D2/dp/B0GK12BKCK) | 1 | TBD | TPA3116D2, ~20W/ch at 12V into 4 ohm. BT 5.0 available as fallback. RPi connects via 3.5mm AUX. 12-24V DC input. |
| [TP-Link UB500 USB BT 5.0 Dongle](https://www.amazon.com/s?k=TP-Link+UB500+Bluetooth+5.0) | 1 | TBD | Backup: if RPi's built-in BT can't handle A2DP + BLE simultaneously. RTL8761B chipset, Linux/Bookworm compatible. |

### Audio Architecture

```
Phone ──[BT A2DP]──→ RPi ──[PipeWire: analyze + 3.5mm out]──→ ZK-1002T ──→ 6.5" Speakers
Phone ──[BLE]──────→ RPi (control app via GATT server)
RPi meditation audio ──→ [same PipeWire sink] ──→ ZK-1002T ──→ Speakers
```

- RPi handles BT audio (A2DP sink) + BLE control on its built-in adapter
- PipeWire mixes incoming BT audio with local meditation files
- Audio stream forked for FFT analysis → music-synced LED animations
- If dual BT causes issues, plug in TP-Link UB500 dongle ($10) to separate A2DP and BLE
- ZK-1002T's built-in BT available as a fallback if RPi BT fails entirely

## Ventilation

| Item | Qty | Status | Notes |
|------|-----|--------|-------|
| 120mm fan (e.g. Noctua NF-F12) | 1 | TBD | Bottom-mount intake, creates positive pressure inside bench enclosure |
| Dust filter material | 1 | TBD | Standard furnace filter, cut to ~130×130mm, below fan |

- **120mm fan power draw:** ~1-2W (12V DC)

---

## Still Needed

- [ ] Pyle PLMRS6B 6.5" marine speakers (~$30)
- [ ] ZK-1002T amp board (~$15-20)
- [ ] TP-Link UB500 BT dongle (~$10, insurance)
- [ ] 120mm fan + dust filter for positive-pressure ventilation
- [ ] Power step-down (48V→12V for LEDs, 48V→5V for RPi) — or 110V inverter + off-the-shelf PSU
- [ ] Ethernet cable (RPi ↔ Gledopto, direct connection)
- [ ] Power injection wiring (every ~100 LEDs)
- [ ] Bench materials (plywood for box, 4×4 lumber for legs)
- [ ] Cable management / connectors / grommets for cable pass-throughs
- [ ] 3.5mm audio cable (RPi → amp AUX input)

---

## Power Budget

### Component Power Draw

| Component | Standby | Active | Notes |
|-----------|---------|--------|-------|
| Raspberry Pi 4 | 3W | 6W | Audio playback + orchestrator |
| WLED controller | 1W | 2W | Relay cuts LED power when idle |
| Audio (ZK-1002T + 6.5" speakers) | 2W | 15W | Idle ~2W (BT standby). Meditation voice ~8W, music ~15W |
| 120mm ventilation fan | 1.5W | 1.5W | Runs 24/7 for positive pressure |
| LEDs — standby sparkle | — | 5W | ~100 random LEDs at low brightness |
| LEDs — breathing animation | — | 35W | ~700 LEDs avg, radial pulse, ~50% brightness |
| LEDs — full white (max) | — | 194W | All 1,936 LEDs at 100% — theoretical max |

### Daily Energy Budget (24h cycle)

Assumptions: art runs 24/7. Daytime (6am–6pm) = voice-only. Nighttime (6pm–6am) = standby sparkle animation + ocean audio, with ~2h of active breathing meditation sessions. Fan runs 24/7.

| Period                                                                | Hours | Avg Power | Energy         |
| --------------------------------------------------------------------- | ----- | --------- | -------------- |
| **Daytime** (voice only, LEDs off)                                    | 12h   | 16.5W     | 198Wh          |
| RPi (6W) + Audio (8W) + WLED idle (1W) + Fan (1.5W)                   |       |           |                |
| **Night standby** (sparkle + ocean)                                   | 10h   | 20.5W     | 205Wh          |
| RPi (5W) + Audio (8W) + WLED (2W) + LEDs sparkle (4W) + Fan (1.5W)    |       |           |                |
| **Night active** (breathing meditation)                               | 2h    | 57.5W     | 115Wh          |
| RPi (6W) + Audio (13W) + WLED (2W) + LEDs animation (35W) + Fan (1.5W)|       |           |                |
|                                                                       |       | **Total** | **~518Wh/day** |

### Battery Runtime (no solar)

| Battery | Capacity (usable 80%) | Runtime |
|---------|----------------------|---------|
| 12V 100Ah (1,280Wh) | 1,024Wh | ~2.8 days |
| 48V 50Ah (2,560Wh) | 2,048Wh | ~5.7 days |

### Solar Balance

| | Daily |
|--|-------|
| Solar input (~200W panel, 6 peak sun hours) | +1,200Wh |
| Consumption | −518Wh |
| **Net surplus** | **+682Wh** |

Solar comfortably covers daily usage with ~2.3× margin.

### Battery-Only Option (no solar)

Option to borrow a second battery. With ~518Wh/day (+15% conversion losses ≈ 596Wh/day), 7-day target = ~4,172Wh needed.

| Setup | Usable capacity (80% DoD) | Runtime |
|-------|---------------------------|---------|
| 1× 12V 100Ah (1,280Wh) | 1,024Wh | ~1.7 days |
| 2× 12V 100Ah (2,560Wh) | 2,048Wh | ~3.4 days |
| 1× 48V 50Ah (2,560Wh) | 2,048Wh | ~3.4 days |
| 2× 48V 50Ah (5,120Wh) | 4,096Wh | **~6.9 days** |

**Verdict:** 2× 48V batteries can just barely do 7 days battery-only. Solar panel recommended as backup. Decision TBD.

> **Note:** Conversion losses (48V→12V→5V or 12V→5V) add ~10-15% overhead, factored in above.
