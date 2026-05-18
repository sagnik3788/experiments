#!/bin/bash
# ── Wlogout Power Menu ───────────────────────────────────────
# Graphical logout/power screen with 6 buttons
# Install: sudo dnf install wlogout

# Kill existing wlogout instances
pkill -f "wlogout" 2>/dev/null

# Launch wlogout with themed layout
wlogout \
    --layout ~/.config/wlogout/layout \
    --css ~/.config/wlogout/style.css \
    --protocol layer-shell \
    --buttons-per-row 6 \
    --margin-top 150 \
    --margin-bottom 150 \
    --margin-left 200 \
    --margin-right 200
