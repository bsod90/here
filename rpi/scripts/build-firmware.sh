#!/usr/bin/env bash
# Build the bench firmware images for OTA and stage them with a manifest.
# Produces firmware/_staged/{bench_node_1.bin,bench_node_2.bin,
# rpi_receiver.bin,manifest.json}. deploy.sh copies these to the Pi's OTA
# directory (/opt/here/firmware); the boards then pull them over WiFi.
#
# Run from anywhere: rpi/scripts/build-firmware.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FW="$ROOT/firmware"
STAGE="$FW/_staged"
FQBN="esp32:esp32:XIAO_ESP32C6"

mkdir -p "$STAGE"

# Load OTA WiFi secrets from the gitignored .env (never committed) and inject
# them as -D defines so they don't live in any tracked source file.
if [ -f "$ROOT/.env" ]; then set -a; . "$ROOT/.env"; set +a; fi
CREDS="-DOTA_WIFI_SSID_RAW=${OTA_WIFI_SSID:-} -DOTA_WIFI_PASS_RAW=${OTA_WIFI_PASS:-}"
if [ -z "${OTA_WIFI_SSID:-}" ]; then
  echo "  ! warning: OTA_WIFI_SSID not set in .env — OTA WiFi join will fail"
fi

# Keep the shared headers in sync into each sketch folder (Arduino can't do
# ../ includes through its build copy).
cp "$FW/fw_version.h" "$FW/ota_config.h" "$FW/bench_node/"
cp "$FW/fw_version.h" "$FW/ota_config.h" "$FW/rpi_receiver/"

VER="$(grep -oE '#define[[:space:]]+FW_VERSION[[:space:]]+[0-9]+' \
       "$FW/fw_version.h" | grep -oE '[0-9]+$')"
echo "→ building firmware v${VER}"

build_to() {  # <out_basename> <sketch_dir> [extra_define]
  local out="$1" sketch="$2" extra="${3:-}"
  local tmp="$STAGE/.b_$out"
  rm -rf "$tmp"
  arduino-cli compile --fqbn "$FQBN" --output-dir "$tmp" \
    --build-property "compiler.cpp.extra_flags=-MMD -c $CREDS $extra" \
    "$sketch" >/dev/null
  cp "$tmp/$(basename "$sketch").ino.bin" "$STAGE/$out.bin"
  rm -rf "$tmp"
  echo "  ✓ $out.bin"
}

build_to "bench_node_1" "$FW/bench_node" "-DNODE_ID=1"
build_to "bench_node_2" "$FW/bench_node" "-DNODE_ID=2"
build_to "rpi_receiver" "$FW/rpi_receiver"

printf '{"version": %s}\n' "$VER" > "$STAGE/manifest.json"
echo "→ staged firmware v${VER} in $STAGE"
ls -1 "$STAGE"
