#!/usr/bin/env bash
# HERE Installation — Raspberry Pi 4 setup script
# Run on a fresh Raspberry Pi OS (Bookworm) install
# Usage: sudo bash setup.sh

set -euo pipefail

echo "=== HERE RPi Setup ==="

# Update system
apt-get update && apt-get upgrade -y

# Install essentials
apt-get install -y \
  git \
  python3 \
  python3-pip \
  python3-venv \
  ffmpeg \
  alsa-utils \
  avahi-daemon

# Enable audio
usermod -aG audio "$SUDO_USER"

# Set hostname
hostnamectl set-hostname here

echo "=== Setup complete. Reboot recommended. ==="
