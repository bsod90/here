#!/usr/bin/env bash
# Wire the repo's HERE.amxd into Ableton's User Library via a symlink,
# and (re)build the device from gen_metadata + build_patcher + build_amxd
# on demand.
#
# Usage:
#   ./setup.sh           # link/refresh the symlink (rebuilds if .amxd missing)
#   ./setup.sh rebuild   # regenerate metadata + .maxpat + .amxd, then link
#   ./setup.sh unlink    # remove the symlink, leave repo files alone
#
# After running, HERE shows up in Live's browser under
#   User Library → MIDI Effects → HERE → HERE.amxd
# Drag onto a MIDI track BEFORE any instrument. Play MIDI; OSC flows to
# the Pi at here.local:9000.

set -euo pipefail
cd "$(dirname "$0")"

REPO_PATCH="HERE.maxpat"
REPO_AMXD="HERE.amxd"

USER_LIB_DIR="${HOME}/Music/Ableton/User Library/Presets/MIDI Effects/HERE"
LINK_PATH="${USER_LIB_DIR}/HERE.amxd"

# Old device's install path — we clean it up on every link so the User
# Library reflects only the current device.
OLD_LINK_PATH="${HOME}/Music/Ableton/User Library/Presets/Audio Effects/HERE/HERE Sender.amxd"
OLD_LINK_DIR="${HOME}/Music/Ableton/User Library/Presets/Audio Effects/HERE"

# Prefer the project's virtualenv if it exists (gen_metadata.py imports
# from `software/orchestrator/scene/animations/synth.py` which is plain
# Python — no numpy needed for the import path used here).
if [ -x "../orchestrator/.venv/bin/python" ]; then
  PY="../orchestrator/.venv/bin/python"
else
  PY="python3"
fi

case "${1:-link}" in
  rebuild)
    echo "→ regenerating metadata JSONs"
    "${PY}" gen_metadata.py
    echo "→ regenerating ${REPO_PATCH}"
    "${PY}" build_patcher.py > "${REPO_PATCH}"
    echo "→ assembling ${REPO_AMXD}"
    "${PY}" build_amxd.py "${REPO_PATCH}" "${REPO_AMXD}"
    ;;
  unlink)
    if [ -L "${LINK_PATH}" ]; then
      rm "${LINK_PATH}"
      echo "✓ removed ${LINK_PATH}"
    else
      echo "(no symlink at ${LINK_PATH})"
    fi
    exit 0
    ;;
  link|"")
    if [ ! -f "${REPO_AMXD}" ]; then
      echo "→ building ${REPO_AMXD} (missing)"
      "${PY}" gen_metadata.py
      "${PY}" build_patcher.py > "${REPO_PATCH}"
      "${PY}" build_amxd.py "${REPO_PATCH}" "${REPO_AMXD}"
    fi
    ;;
  *)
    echo "unknown command: $1" >&2
    exit 1
    ;;
esac

# Clean up the stale Audio Effects symlink from the old HERE Sender.
if [ -L "${OLD_LINK_PATH}" ] || [ -e "${OLD_LINK_PATH}" ]; then
  rm -f "${OLD_LINK_PATH}"
  echo "✓ removed stale ${OLD_LINK_PATH}"
fi
# Remove the now-empty HERE folder under Audio Effects.
if [ -d "${OLD_LINK_DIR}" ] && [ -z "$(ls -A "${OLD_LINK_DIR}")" ]; then
  rmdir "${OLD_LINK_DIR}"
  echo "✓ removed empty ${OLD_LINK_DIR}"
fi

# Install the new device.
#
# We COPY rather than symlink. Live's browser indexes real files in the
# User Library reliably; symlinked *files* are flaky — they often don't
# appear until a full rescan/restart (which is why the HERE folder showed
# up empty). The repo stays the source of truth; `./setup.sh rebuild`
# regenerates the .amxd and re-copies it, and Live reloads the device when
# the file on disk changes — same iteration loop, just always via setup.sh.
mkdir -p "${USER_LIB_DIR}"
if [ -L "${LINK_PATH}" ] || [ -e "${LINK_PATH}" ]; then
  rm "${LINK_PATH}"
fi
cp "$(pwd)/${REPO_AMXD}" "${LINK_PATH}"
echo "✓ installed ${LINK_PATH}"
echo "  → copy of $(pwd)/${REPO_AMXD} ($(wc -c < "${LINK_PATH}") bytes)"
# The `v8` object loads here.js as a SEPARATE file, resolved from the
# device's own folder first. Without this, Max falls back to a stale
# here.js from its search path / cache (→ "no function note/palette").
cp "$(pwd)/here.js" "${USER_LIB_DIR}/here.js"
echo "✓ installed here.js alongside the device"

cat <<EOF

Next:
  1. Open Live. The device appears under
       User Library → MIDI Effects → HERE → HERE
  2. Drag onto a MIDI track (BEFORE any instrument).
  3. Make sure here.local:9000 is reachable (the Pi orchestrator).
  4. Play MIDI notes (or run a clip with notes C1..D#4 = 36..75).

Iteration loop:
  - Edit Python source (build_patcher.py, here.js, gen_metadata.py)
  - Run ./setup.sh rebuild
  - Live auto-reloads the device

Caveat: if you edit-in-place inside Max and ⌘S, Max writes a real file
and breaks the symlink. Re-run ./setup.sh to restore the link.
EOF
