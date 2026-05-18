#!/bin/bash
# Volume control stub - uses wpctl
case "$1" in
    --inc) wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%+ ;;
    --dec) wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%- ;;
esac
