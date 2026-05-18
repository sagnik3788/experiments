#!/bin/bash
# ── Cava visualizer for Waybar ────────────────────────────────
# Reads raw ASCII bar data from cava, renders as unicode blocks.
# Kills existing instance on each run to avoid duplicates.

pkill -f "cava -p /dev/stdout" 2>/dev/null
sleep 0.1

# Cava config for raw ASCII output to stdout
CONFIG=/tmp/cava_waybar_config
cat > "$CONFIG" << 'EOF'
[general]
bars = 12
framerate = 30

[input]
method = pipewire
source = auto

[output]
method = raw
raw_target = /dev/stdout
data_format = ascii
ascii_max_range = 1000
bar_delimiter = 59
frame_delimiter = 10

[smoothing]
noise_reduction = 88

[color]
gradient = 0

[eq]
1 = 1
2 = 1
3 = 1
4 = 1
5 = 1
6 = 1
7 = 1
8 = 1
9 = 1
10 = 1
11 = 1
12 = 1
EOF

# Read raw ascii data and render unicode blocks
cava -p "$CONFIG" | while read -r line; do
    IFS=';' read -ra bars <<< "$line"
    output=""
    for bar in "${bars[@]}"; do
        bar=$((bar))
        if [ "$bar" -gt 75 ]; then
            output+="█"
        elif [ "$bar" -gt 50 ]; then
            output+="▓"
        elif [ "$bar" -gt 25 ]; then
            output+="▒"
        elif [ "$bar" -gt 5 ]; then
            output+="░"
        else
            output+=" "
        fi
    done
    echo "<span foreground='#c6a0f6'>$output</span>"
done
