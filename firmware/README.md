# HERE — ESP32-C6 telemetry firmware

Three Seeed **XIAO ESP32-C6** boards:

- `bench_node/` — flashed onto **two** boards, one per bench leg. Battery
  powered, reads battery voltage + an HX711 load cell, broadcasts over
  ESP-NOW, then deep-sleeps. Flash the **left** leg `NODE_ID=1`, the
  **right** leg `NODE_ID=2`.
- `rpi_receiver/` — flashed onto the **third** board, wired to the Pi's
  UART. Always on. Receives the broadcasts and prints one JSON line per
  packet to the Pi over D3, and also to USB (for laptop testing).

ESP-NOW is used in **broadcast** mode on a **fixed channel (1)** — no
pairing, no MAC addresses to configure. Keep `ESPNOW_CHANNEL` the same in
all three sketches.

> **Sensor assumption:** D3/D6 are wired to an **HX711 load-cell amp**
> (DOUT/PD_SCK). If your D3/D6 sensor is something else, only `hx711_read()`
> / `hx711_powerdown()` in `bench_node.ino` need to change.

## Wiring — bench node (XIAO ESP32-C6)

| Silk | GPIO | Connect to |
|------|------|-----------|
| D0 / A0 | GPIO0 | Battery divider **midpoint** (100k from BAT+, 100k to GND, + 100nF to GND) |
| D3 | GPIO21 | HX711 **DOUT** (data) |
| D6 | GPIO16 | HX711 **PD_SCK** (clock) |
| 3V3 | — | HX711 VCC |
| GND | — | HX711 GND + divider bottom |
| BAT+ / BAT- | — | 1S LiPo (the XIAO charges it over USB) |

Battery math: `battery_mv = ADC_mv × 2` (equal 100k/100k legs). The 100nF
cap across the bottom resistor keeps the ADC reading clean.

## Wiring — receiver → Raspberry Pi (3 wires)

| XIAO pad | → Pi pin | Note |
|----------|----------|------|
| 5V  | 5V (pin 2 or 4)  | powers the XIAO through its onboard regulator |
| GND | GND (pin 6)      | common ground (required) |
| D3 (GPIO21, UART TX) | RXD / GPIO15 (pin 10) | data: ESP → Pi |

Both ends are 3.3V logic, so **no level shifter** is needed. It's one-way
(ESP → Pi); the Pi never needs to talk back. If you soldered the power
wire to the XIAO's `3V3` pad instead of `5V`, take it from a Pi 3V3 pin
(pin 1) instead — don't feed 5V into a 3V3 pad. So yes: two power wires
(VCC + GND) + one data wire on D3 is exactly right.

## Power budget (bench node)

Per-wake cost is one short radio blip; the rest of the time the board is
asleep. The wake cadence is **dynamic**: 1 s while the leg is occupied,
5 s while empty (the node decides this itself from a coarse self-tare;
the Pi does the accurate tare/calibration).

| State | Current |
|-------|---------|
| Deep sleep (board + 100k/100k divider ~19µA + HX711 asleep) | ~35 µA |
| Awake + ESP-NOW TX | ~80 mA for ~0.3 s |

Rough average current and life on a 2000 mAh cell:

| Cadence | Avg current | Life on 2000 mAh |
|---------|-------------|------------------|
| 5 s (empty) | ~5 mA | ~16 days |
| 1 s (occupied) | ~24 mA | ~3.5 days |

In practice the bench is empty most of the time, so you sit near the 5 s
figure with short 1 s bursts during sessions. If you want longer life,
raise `SLEEP_IDLE_S` / `SLEEP_OCCUPIED_S` in `bench_node.ino`.

> Occupancy resolution = the wake cadence (the load cell is only read on
> wake). There's no way to threshold-wake on an analog load cell without
> keeping the HX711 powered, which would cost far more than this.

## Flashing

### One-time toolchain setup

```bash
arduino-cli config init
arduino-cli config add board_manager.additional_urls \
  https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
arduino-cli core update-index
arduino-cli core install esp32:esp32          # needs 3.0.x+
```

Find the port (plug in one board at a time):

```bash
arduino-cli board list      # e.g. /dev/cu.usbmodemXXXX
```

FQBN: `esp32:esp32:XIAO_ESP32C6`

### Receiver (the one going to the Pi)

```bash
cd firmware
arduino-cli compile --fqbn esp32:esp32:XIAO_ESP32C6 -u -p /dev/cu.usbmodemXXXX rpi_receiver
```

### Bench legs — NODE_ID via build flag

The `-DNODE_ID` define is injected through `compiler.cpp.extra_flags`.
**Keep the default `-MMD -c`** in the override, or the link fails:

Left leg (`NODE_ID=1`):

```bash
arduino-cli compile --fqbn esp32:esp32:XIAO_ESP32C6 -u -p /dev/cu.usbmodemXXXX \
  --build-property "compiler.cpp.extra_flags=-MMD -c -DNODE_ID=1" bench_node
```

Right leg (`NODE_ID=2`):

```bash
arduino-cli compile --fqbn esp32:esp32:XIAO_ESP32C6 -u -p /dev/cu.usbmodemXXXX \
  --build-property "compiler.cpp.extra_flags=-MMD -c -DNODE_ID=2" bench_node
```

> `-u` compiles and uploads in one step so the binary matches the flag.
> Cold-boot self-tare assumes an **empty bench at power-on** — connect the
> leg battery with nobody sitting down.

## Testing

### Bench → laptop (no Pi needed)

1. Flash a leg, power it from battery.
2. Open the receiver's USB serial monitor at 115200:
   ```bash
   arduino-cli monitor -p /dev/cu.usbmodemXXXX -c baudrate=115200
   ```
3. You should see a line every ~5 s (empty) / ~1 s (hand pressing the
   cell), e.g. `{"node":2,"occ":0,"batt_mv":3810,"weight":...,"rssi":-46}`.

### Receiver → Pi over UART

After the Pi UART is enabled (`rpi/scripts/enable-uart.sh` + reboot):

```bash
stty -F /dev/serial0 115200 && cat /dev/serial0      # raw stream
```

The orchestrator's `bench_link.py` reads `/dev/serial0` automatically and
feeds weight into the existing scale subsystem; battery + link health show
up in the admin panel (Run tab → Bench Scale, and the Telemetry tab).

## Raspberry Pi side

The orchestrator integration is built in:

- `software/orchestrator/bench_link.py` — reads `/dev/serial0`, keeps the
  latest per-leg weight + battery, maps `node_id → leg`.
- `software/orchestrator/scale.py` — pulls raw weight from `bench_link`
  instead of on-Pi HX711 GPIO; all tare/calibration/occupancy reused.
- Tare/calibrate from the admin UI (Run tab → Bench Scale) exactly as
  before: empty the bench → **Tare**, put a known weight → **Calibrate**.

Enable the UART once (keeps Bluetooth/BLE intact — uses the mini-UART on
GPIO14/15):

```bash
sudo bash rpi/scripts/enable-uart.sh
sudo reboot
```
