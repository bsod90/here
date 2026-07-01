#!/usr/bin/env bash
# HERE — enable the GPIO UART for the ESP-NOW bench receiver.
#
# The receiver XIAO's D3/TX is wired to the Pi's RXD (GPIO15, pin 10). We
# need the GPIO serial port enabled and the serial *console* (login getty)
# off, so the orchestrator can read /dev/serial0 cleanly.
#
# IMPORTANT: we do NOT disable Bluetooth. HERE uses BLE for phone control
# and A2DP for music, so we keep the PL011 on Bluetooth and use the
# mini-UART (ttyS0) on GPIO14/15 — which is what /dev/serial0 points to
# when BT is left enabled. Enabling the UART pins the core clock so the
# mini-UART baud is stable.
#
# Idempotent. Requires a REBOOT to take effect. Run as root (the deploy
# path calls it via sudo) or with sudo directly.
set -euo pipefail

SERVICE_USER="${SERVICE_USER:-here}"

echo "→ enabling GPIO serial hardware (keeps Bluetooth on PL011)"
# raspi-config convention: 0 = enable hardware UART.
raspi-config nonint do_serial_hw 0
# 1 = disable the serial login console (frees the port for our use).
raspi-config nonint do_serial_cons 1

# The orchestrator runs as ${SERVICE_USER}; it needs group access to the
# tty device to open /dev/serial0.
if id "${SERVICE_USER}" >/dev/null 2>&1; then
    if ! id -nG "${SERVICE_USER}" | tr ' ' '\n' | grep -qx dialout; then
        echo "→ adding ${SERVICE_USER} to the dialout group"
        usermod -aG dialout "${SERVICE_USER}"
    else
        echo "✓ ${SERVICE_USER} already in dialout"
    fi
fi

echo
echo "✓ UART configured. A reboot is required for /dev/serial0 to appear:"
echo "    sudo reboot"
echo
echo "After reboot, sanity-check the stream with:"
echo "    stty -F /dev/serial0 115200 && cat /dev/serial0"
