#!/usr/bin/env bash
# Render all bench assembly views to PNG.
# Usage: ./render.sh           (render all)
#        ./render.sh open_iso  (render one view by name)
set -euo pipefail
cd "$(dirname "$0")"

SCAD="assembly.scad"
SIZE="1600,1200"
SCHEME="Sunset"

# ── camera presets ──────────────────────────────────────────
CAM_ISO="0,0,200,60,0,225,5500"
CAM_ISO_FRONT="0,0,200,55,0,315,5500"
CAM_TOP="0,0,200,0,0,45,5000"
CAM_SIDE="0,0,250,80,0,225,4500"
CAM_BENCH="0,0,350,55,0,225,2500"

# ── common overrides ────────────────────────────────────────
BASE="two_batteries=true;show_desert=true"

# ── render function ─────────────────────────────────────────
render() {
    local name="$1" camera="$2" defs="$3"
    local out="renders/${name}.png"
    printf "  %-25s" "${name}..."
    openscad -o "$out" \
        --camera="$camera" \
        --imgsize="$SIZE" \
        --colorscheme="$SCHEME" \
        -D "$defs" \
        "$SCAD" 2>/dev/null
    echo "done"
}

mkdir -p renders

# ── view definitions: name|camera|overrides ─────────────────
VIEWS=(
"open_iso|${CAM_ISO}|${BASE};lid_open=true;show_leds=true;for_export=true"
"open_front|${CAM_ISO_FRONT}|${BASE};lid_open=true;show_leds=true;for_export=true"
"open_top|${CAM_TOP}|${BASE};lid_open=true;show_leds=true;for_export=true"
"open_side|${CAM_SIDE}|${BASE};lid_open=true;show_leds=true;for_export=true"
"open_close|${CAM_BENCH}|${BASE};lid_open=true;show_leds=false;show_platform=false;show_desert=false;for_export=true"
"closed_iso|${CAM_ISO}|${BASE};lid_open=false;show_leds=true;for_export=true"
"dims_iso|${CAM_ISO}|${BASE};lid_open=true;show_leds=false;show_dimensions=true;for_export=false"
"dims_top|${CAM_TOP}|${BASE};lid_open=true;show_leds=false;show_dimensions=true;for_export=false"
)

# ── main ────────────────────────────────────────────────────
if [ $# -gt 0 ]; then
    for target in "$@"; do
        found=0
        for entry in "${VIEWS[@]}"; do
            IFS='|' read -r name cam defs <<< "$entry"
            if [ "$name" = "$target" ]; then
                render "$name" "$cam" "$defs"
                found=1
            fi
        done
        if [ "$found" -eq 0 ]; then
            echo "Unknown view: $target"
            echo "Available:"
            for entry in "${VIEWS[@]}"; do
                echo "  $(echo "$entry" | cut -d'|' -f1)"
            done
            exit 1
        fi
    done
else
    echo "Rendering all views..."
    for entry in "${VIEWS[@]}"; do
        IFS='|' read -r name cam defs <<< "$entry"
        render "$name" "$cam" "$defs"
    done
    count=$(ls renders/*.png 2>/dev/null | wc -l | tr -d ' ')
    echo ""
    echo "Done! ${count} images in bench/renders/"
fi
