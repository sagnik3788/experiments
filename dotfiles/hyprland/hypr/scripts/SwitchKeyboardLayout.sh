#!/bin/bash
# Keyboard layout toggle
current=$(hyprctl getoption input:kb_layout | grep -oP 'str: "\K[^"]+')
if [ "$current" = "us" ]; then
    hyprctl keyword input:kb_layout us
else
    hyprctl keyword input:kb_layout us
fi
