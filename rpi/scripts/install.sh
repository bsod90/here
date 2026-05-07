#!/usr/bin/env bash
# HERE — Pi-side install/update. Idempotent; safe to re-run.
# Invoked over SSH by rpi/scripts/deploy.sh.
#
# Expects a staging tree at $STAGE (default: ~/here-stage) populated by
# the deploy script with rpi/ + orchestrator/.

set -euo pipefail

# Derive the staging dir from this script's own location, so we work
# correctly under sudo (where $HOME becomes /root).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAGE="${STAGE:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
APP=/opt/here
USER_HERE=here

if [ "$EUID" -ne 0 ]; then
    echo "install.sh must run as root (called via sudo)." >&2
    exit 1
fi

echo "=== HERE install — staging from $STAGE ==="

# ---------------------------------------------------------------------
# 1. apt packages
# ---------------------------------------------------------------------
echo "→ apt packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends \
    python3-venv python3-pip rsync \
    avahi-daemon ffmpeg alsa-utils \
    >/dev/null

# ---------------------------------------------------------------------
# 2. Static IP on eth0 (private link to WLED)
#    Pi:   192.168.10.10/24
#    WLED: 192.168.10.20  (matches software/orchestrator/config.json)
# ---------------------------------------------------------------------
ETH_CON="Wired connection 1"
ETH_IP=192.168.10.10/24
if ! nmcli -g ipv4.addresses con show "$ETH_CON" 2>/dev/null \
        | grep -q "$ETH_IP"; then
    echo "→ configuring eth0 static $ETH_IP"
    nmcli con mod "$ETH_CON" \
        ipv4.method manual \
        ipv4.addresses "$ETH_IP" \
        ipv4.gateway "" \
        ipv4.dns "" \
        ipv4.never-default yes \
        ipv6.method disabled \
        connection.autoconnect yes
    nmcli con up "$ETH_CON" 2>/dev/null || true
fi

# ---------------------------------------------------------------------
# 3. Hardware watchdog
# ---------------------------------------------------------------------
WDT_CFG=/boot/firmware/config.txt
if ! grep -q '^dtparam=watchdog=on' "$WDT_CFG"; then
    echo "→ enabling hardware watchdog in $WDT_CFG"
    echo 'dtparam=watchdog=on' >> "$WDT_CFG"
    NEEDS_REBOOT=1
fi

mkdir -p /etc/systemd/system.conf.d
WATCHDOG_DST=/etc/systemd/system.conf.d/here-watchdog.conf
WATCHDOG_SRC="$STAGE/rpi/configs/system.conf.d/here-watchdog.conf"
if ! cmp -s "$WATCHDOG_SRC" "$WATCHDOG_DST" 2>/dev/null; then
    install -m 0644 "$WATCHDOG_SRC" "$WATCHDOG_DST"
    # /etc/systemd/system.conf.d is read only at PID 1 start; re-exec
    # systemd in place so RuntimeWatchdogSec takes effect without a
    # full reboot.
    systemctl daemon-reexec
fi

# ---------------------------------------------------------------------
# 4. Journald rotation
# ---------------------------------------------------------------------
mkdir -p /etc/systemd/journald.conf.d
install -m 0644 "$STAGE/rpi/configs/journald.conf.d/here.conf" \
    /etc/systemd/journald.conf.d/here.conf
systemctl restart systemd-journald

# ---------------------------------------------------------------------
# 5. Disable swap (SD wear; we have 4 GB RAM)
# ---------------------------------------------------------------------
if systemctl list-unit-files dphys-swapfile.service 2>/dev/null \
        | grep -q dphys-swapfile; then
    echo "→ disabling swap"
    systemctl disable --now dphys-swapfile 2>/dev/null || true
    apt-get -y purge dphys-swapfile >/dev/null 2>&1 || true
fi

# Also clear /var/swap if the file exists from a previous purge
[ -f /var/swap ] && rm -f /var/swap || true

# ---------------------------------------------------------------------
# 6. Application — sync code → /opt/here, owned by `here`
# ---------------------------------------------------------------------
echo "→ syncing source → $APP"
mkdir -p "$APP"
rsync -a --delete --exclude '.venv' --exclude '__pycache__' --exclude '*.pyc' \
    "$STAGE/orchestrator/" "$APP/"
chown -R "$USER_HERE":"$USER_HERE" "$APP"

# ---------------------------------------------------------------------
# 7. Python venv + deps
# ---------------------------------------------------------------------
if [ ! -x "$APP/.venv/bin/python" ]; then
    echo "→ creating venv"
    sudo -u "$USER_HERE" python3 -m venv "$APP/.venv"
fi
sudo -u "$USER_HERE" "$APP/.venv/bin/pip" install -q --upgrade pip
sudo -u "$USER_HERE" "$APP/.venv/bin/pip" install -q -r "$APP/requirements.txt"

# ---------------------------------------------------------------------
# 8. Systemd unit
# ---------------------------------------------------------------------
install -m 0644 "$STAGE/rpi/configs/here-orchestrator.service" \
    /etc/systemd/system/here-orchestrator.service
systemctl daemon-reload
systemctl enable here-orchestrator.service
systemctl restart here-orchestrator.service

echo
if [ "${NEEDS_REBOOT:-0}" = "1" ]; then
    echo "=== install done — REBOOT REQUIRED to activate hardware watchdog ==="
    echo "    sudo reboot"
else
    echo "=== install done ==="
fi
echo "Tail logs:  journalctl -u here-orchestrator -f"
echo "Status:     systemctl status here-orchestrator"
