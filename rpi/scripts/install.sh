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
    libportaudio2 \
    swig python3-dev liblgpio-dev \
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
# 3.5 NTP — telemetry history records timestamps; if the Pi boots with a
#     wrong clock the charts will be misplaced on the timeline. Bookworm
#     ships systemd-timesyncd disabled by default on some images.
# ---------------------------------------------------------------------
systemctl enable --now systemd-timesyncd 2>/dev/null || true
timedatectl set-ntp true 2>/dev/null || true

# ---------------------------------------------------------------------
# 4. Journald rotation
# ---------------------------------------------------------------------
mkdir -p /etc/systemd/journald.conf.d
install -m 0644 "$STAGE/rpi/configs/journald.conf.d/here.conf" \
    /etc/systemd/journald.conf.d/here.conf
systemctl restart systemd-journald

# Polkit: let `netdev` members run nmcli without sudo (the orchestrator
# needs this to toggle the field-debug AP).
mkdir -p /etc/polkit-1/rules.d
install -m 0644 "$STAGE/rpi/configs/polkit/50-here-netdev.rules" \
    /etc/polkit-1/rules.d/50-here-netdev.rules

# Disable WiFi power-save on wlan0 (drops mDNS multicast / flaky assoc).
# Persistent via NetworkManager conf.d; applied live now without dropping
# the link (iw set is non-disruptive, unlike a radio toggle over SSH).
mkdir -p /etc/NetworkManager/conf.d
install -m 0644 "$STAGE/rpi/configs/NetworkManager/wifi-powersave-off.conf" \
    /etc/NetworkManager/conf.d/wifi-powersave-off.conf
systemctl reload NetworkManager 2>/dev/null || true
iw dev wlan0 set power_save off 2>/dev/null || true

# Stable OTA address: the ESP fleet downloads firmware from a hardcoded
# 192.168.1.110, but wlan0 is on DHCP and can drift after a reboot (→ OTA
# fails fleet-wide). A NetworkManager dispatcher keeps .110 as a wlan0 alias
# on every bring-up. Install + apply now (idempotent).
mkdir -p /etc/NetworkManager/dispatcher.d
install -m 0755 "$STAGE/rpi/configs/NetworkManager/dispatcher.d/90-here-ota-ip" \
    /etc/NetworkManager/dispatcher.d/90-here-ota-ip
ip -4 addr show dev wlan0 | grep -q "192.168.1.110/24" || \
    ip addr add 192.168.1.110/24 dev wlan0 2>/dev/null || true

# Floor-border LED strips need SPI. Enable both buses in config.txt (idempotent;
# takes effect on next reboot):
#   * SPI0 (dtparam=spi=on)      → /dev/spidev0.0, MOSI=GPIO10 — STABLE clock,
#                                  the recommended bus for WS2812.
#   * SPI1 (dtoverlay=spi1-1cs)  → /dev/spidev1.0, MOSI=GPIO20 — works, but the
#                                  aux-SPI clock can drift under core scaling.
BOOTCFG=/boot/firmware/config.txt
[ -f "$BOOTCFG" ] || BOOTCFG=/boot/config.txt
if [ -f "$BOOTCFG" ]; then
    if ! grep -qE "^dtparam=spi=on" "$BOOTCFG"; then
        echo "dtparam=spi=on" >> "$BOOTCFG"
        echo "  + enabled SPI0 (reboot required)"
    fi
    if ! grep -qE "^dtoverlay=spi1-1cs" "$BOOTCFG"; then
        echo "dtoverlay=spi1-1cs" >> "$BOOTCFG"
        echo "  + enabled SPI1 (reboot required)"
    fi
fi

# here.local self-heal: if a fast power-cycle made avahi rename to here-2,
# reclaim "here" once the stale mDNS record expires. Idempotent install.
install -m 0755 "$STAGE/rpi/scripts/here-mdns-reclaim.sh" \
    /usr/local/sbin/here-mdns-reclaim
install -m 0644 "$STAGE/rpi/configs/here-mdns-reclaim.service" \
    /etc/systemd/system/here-mdns-reclaim.service

# Boot-time AP fallback: if home WiFi STA doesn't associate within 60 s,
# bring up the field-debug AP. Idempotent install.
install -m 0755 "$STAGE/rpi/scripts/here-wifi-fallback.sh" \
    /usr/local/sbin/here-wifi-fallback
install -m 0644 "$STAGE/rpi/configs/here-wifi-fallback.service" \
    /etc/systemd/system/here-wifi-fallback.service
systemctl daemon-reload
systemctl enable here-wifi-fallback.service >/dev/null
systemctl enable here-mdns-reclaim.service >/dev/null

# ---------------------------------------------------------------------
# 5. Field-debug WiFi AP — defined but NOT auto-activated.
#    On RPi OS Trixie the CYW43455's AP+STA concurrency is not reliable
#    via a single wlan0 vif: bringing up the AP kicks the STA off the
#    home WiFi. So we leave the connection profile dormant (autoconnect
#    no) and let the orchestrator activate it on demand from the
#    dashboard. Activating it in the field — where there is no home
#    WiFi anyway — is fine.
#    Skipped if AP_SSID env var is empty.
# ---------------------------------------------------------------------
if [ -n "${AP_SSID:-}" ] && [ -n "${AP_PSK:-}" ]; then
    AP_CON=here-debug-ap
    AP_NET=192.168.50.1/24

    # Recreate from scratch each run so config matches .env on every
    # deploy. The connection only stores creds (no real state we'd lose).
    nmcli con delete "$AP_CON" >/dev/null 2>&1 || true

    echo "→ defining field-debug AP '$AP_SSID' (dormant, no autoconnect)"
    nmcli con add type wifi ifname wlan0 con-name "$AP_CON" \
        autoconnect no \
        ssid "$AP_SSID" \
        -- 802-11-wireless.mode ap \
           802-11-wireless.band bg \
           ipv4.method shared \
           ipv4.addresses "$AP_NET" \
           ipv4.never-default yes \
           ipv6.method disabled \
           wifi-sec.key-mgmt wpa-psk \
           wifi-sec.psk "$AP_PSK" >/dev/null
fi

# ---------------------------------------------------------------------
# 6. Disable swap (SD wear; we have 4 GB RAM)
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
# 7. Application — sync code → /opt/here, owned by `here`
# ---------------------------------------------------------------------
echo "→ syncing source → $APP"
mkdir -p "$APP" "$APP/sim" "$APP/data/sequences"
# Survive across deploys:
#   * config.json — user's saved settings (mode, BPM, palettes, slider tweaks,
#     active_sequence pointer). Never in git, must not be deleted by rsync.
#   * data/      — saved piano-roll loops in data/sequences/*.json.
rsync -a --delete --exclude '.venv' --exclude 'sim' --exclude 'data' \
    --exclude 'config.json' \
    --exclude '__pycache__' --exclude '*.pyc' \
    "$STAGE/orchestrator/" "$APP/"
# Simulator UI lives at /opt/here/sim, mounted by the orchestrator at /sim/.
if [ -d "$STAGE/simulator" ]; then
    rsync -a --delete --exclude '__pycache__' --exclude '*.pyc' \
        "$STAGE/simulator/" "$APP/sim/"
fi
# Audio + other media land at /opt/here/media/ — read by the AudioPlayer
# at start (config.audio.media_dir). Gitignored upstream, so this is the
# only place the files exist on the Pi.
if [ -d "$STAGE/media" ]; then
    mkdir -p "$APP/media"
    rsync -a --delete "$STAGE/media/" "$APP/media/"
fi
chown -R "$USER_HERE":"$USER_HERE" "$APP"

# ---------------------------------------------------------------------
# 8. Python venv + deps
# ---------------------------------------------------------------------
if [ ! -x "$APP/.venv/bin/python" ]; then
    echo "→ creating venv"
    sudo -u "$USER_HERE" python3 -m venv "$APP/.venv"
fi
sudo -u "$USER_HERE" "$APP/.venv/bin/pip" install -q --upgrade pip
sudo -u "$USER_HERE" "$APP/.venv/bin/pip" install -q -r "$APP/requirements.txt"

# ---------------------------------------------------------------------
# 9. Systemd unit
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
