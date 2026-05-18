#!/bin/bash
# Toggle blur in Hyprland
current=$(hyprctl getoption decoration:blur:enabled | grep -oP 'int: \K\d')
if [ "$current" = "1" ]; then
    hyprctl keyword decoration:blur:enabled false
else
    hyprctl keyword decoration:blur:enabled true
fi
