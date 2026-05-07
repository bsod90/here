#!/usr/bin/env bash
# Field-debug AP fallback.
#
# At boot, wait up to $WAIT_S seconds for the home-WiFi STA on wlan0 to
# associate. If it doesn't, bring up the dormant `here-debug-ap` so a
# phone can connect and reach the dashboard / SSH.
#
# At home, STA usually connects within ~10 s and this script exits
# early. On the playa (no home network), the AP comes up after the wait
# window. The dashboard toggle still works either way.
#
# Logs go to stdout — systemd captures them in the journal:
#   journalctl -u here-wifi-fallback

set -u

WAIT_S=${WAIT_S:-60}
POLL_S=${POLL_S:-2}
AP_CON=${AP_CON:-here-debug-ap}

log() { printf '%(%Y-%m-%d %H:%M:%S)T  %s\n' -1 "$1"; }

# Profile must exist (defined by install.sh from .env)
if ! nmcli -t -f NAME con show 2>/dev/null | grep -qx "$AP_CON"; then
    log "AP profile '$AP_CON' not defined — nothing to do"
    exit 0
fi

# Don't re-fire if it's already up
if nmcli -t -f NAME con show --active 2>/dev/null | grep -qx "$AP_CON"; then
    log "'$AP_CON' already active — nothing to do"
    exit 0
fi

# Poll wlan0's active connection. STA presence == any non-AP profile.
elapsed=0
while [ "$elapsed" -lt "$WAIT_S" ]; do
    sta_con=$(nmcli -t -g GENERAL.CONNECTION dev show wlan0 2>/dev/null || true)
    if [ -n "$sta_con" ] && [ "$sta_con" != "$AP_CON" ]; then
        log "wlan0 STA on '$sta_con' after ${elapsed}s — AP stays dormant"
        exit 0
    fi
    sleep "$POLL_S"
    elapsed=$((elapsed + POLL_S))
done

log "wlan0 STA didn't connect within ${WAIT_S}s — bringing up '$AP_CON'"
if nmcli con up "$AP_CON"; then
    log "'$AP_CON' is up at 192.168.50.1"
else
    log "AP activation failed"
    exit 1
fi
