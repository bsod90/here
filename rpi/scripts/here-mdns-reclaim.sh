#!/usr/bin/env bash
# here-mdns-reclaim — guarantee here.local resolves after a fast power-cycle.
#
# Symptom this fixes:
#   On a quick power-cycle, the previous boot's "here.local" mDNS record is
#   still cached on the LAN (RFC 6762 hostname TTL ~120 s). The fresh avahi
#   probes the name, sees the stale record answered, assumes someone else
#   owns it, and renames itself to "here-2". here.local then stops resolving
#   until the next power-cycle (by which time the cache has expired) — exactly
#   the "have to power-cycle twice" behaviour.
#
# What it does:
#   After the network is up, ask avahi which name it actually claimed. If it
#   isn't our hostname, restart avahi and retry. Within the ~120 s TTL the
#   stale record expires and avahi reclaims "here". On a healthy boot avahi
#   already owns the name, so the very first check passes and we exit at once.
#
# Logs go to the journal:  journalctl -u here-mdns-reclaim
set -u

WANT="$(hostname)"
TRIES=${TRIES:-9}        # 9 × 20 s ≈ 3 min, comfortably past the ~120 s TTL
SLEEP=${SLEEP:-20}

log() { printf '%(%Y-%m-%d %H:%M:%S)T  %s\n' -1 "$1"; }

avahi_name() {
    busctl call org.freedesktop.Avahi / org.freedesktop.Avahi.Server \
        GetHostName 2>/dev/null | awk '{gsub(/"/,"",$2); print $2}'
}

for i in $(seq 1 "$TRIES"); do
    cur="$(avahi_name)"
    if [ -z "$cur" ]; then
        log "avahi not answering yet (try $i/$TRIES) — waiting"
    elif [ "$cur" = "$WANT" ]; then
        log "avahi owns '$WANT.local' (try $i) — ok"
        exit 0
    else
        log "avahi claimed '$cur' not '$WANT' (try $i/$TRIES) — restarting avahi-daemon"
        systemctl restart avahi-daemon || true
    fi
    [ "$i" -lt "$TRIES" ] && sleep "$SLEEP"
done

log "gave up: avahi is '$(avahi_name)' after $TRIES tries"
exit 0   # never fail the boot over an mDNS name
