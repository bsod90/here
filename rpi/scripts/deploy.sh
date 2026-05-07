#!/usr/bin/env bash
# HERE — one-shot deploy from laptop to the Pi over SSH.
#   - Reads PI_HOST and PI_USER from .env at the repo root
#   - rsyncs rpi/ (configs + scripts) and software/orchestrator/
#   - Runs install.sh on the Pi (idempotent: full bootstrap on first
#     run, incremental thereafter)
#
# Usage:  ./rpi/scripts/deploy.sh
#         FORCE_REBOOT=1 ./rpi/scripts/deploy.sh   # reboot Pi at end
#
# Requires: ssh, rsync. Assumes ~/.ssh/config already routes the host
# to the right user + key (we set this up at provisioning time).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

# Load .env (gitignored)
if [ -f .env ]; then
    set -a; . ./.env; set +a
fi

PI_HOST="${PI_HOST:-here.local}"
PI_USER="${PI_USER:-here}"
PI_TARGET="${PI_USER}@${PI_HOST}"
STAGE='~/here-stage'

echo "→ deploying to ${PI_TARGET}"

# Sanity: SSH reachable + non-interactive
if ! ssh -o BatchMode=yes -o ConnectTimeout=5 "$PI_TARGET" true 2>/dev/null; then
    echo "✗ cannot SSH to ${PI_TARGET}." >&2
    echo "  - check the Pi is on the network (ping ${PI_HOST})" >&2
    echo "  - check ~/.ssh/config aliases ${PI_HOST}" >&2
    exit 1
fi

# Stage on the Pi
ssh "$PI_TARGET" "mkdir -p ${STAGE}"

# rsync rpi/ (configs + scripts)
rsync -az --delete \
    --exclude '__pycache__' --exclude '*.pyc' \
    rpi/ "${PI_TARGET}:${STAGE}/rpi/"

# rsync orchestrator/
rsync -az --delete \
    --exclude '__pycache__' --exclude '*.pyc' --exclude '.venv' \
    software/orchestrator/ "${PI_TARGET}:${STAGE}/orchestrator/"

# Run install (idempotent)
ssh "$PI_TARGET" "sudo bash ${STAGE}/rpi/scripts/install.sh"

if [ "${FORCE_REBOOT:-0}" = "1" ]; then
    echo "→ rebooting Pi"
    ssh "$PI_TARGET" 'sudo reboot' || true
fi

echo
echo "✓ deploy complete"
echo
echo "Tail logs:    ssh ${PI_TARGET} -- journalctl -u here-orchestrator -f"
echo "Status:       ssh ${PI_TARGET} -- systemctl status here-orchestrator"
echo "Admin panel:  http://${PI_HOST}:8000/"
