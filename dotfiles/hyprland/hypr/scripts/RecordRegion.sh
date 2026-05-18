#!/bin/bash
# Region recording — select area and record

RECORD_DIR="$HOME/Videos/recordings"
mkdir -p "$RECORD_DIR"

PIDFILE="/tmp/recording-region.pid"

if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    kill "$(cat "$PIDFILE")"
    rm -f "$PIDFILE"
    notify-send "Recording" "Region recording stopped" -i media-record -t 2000
else
    wf-recorder -g "$(slurp)" -f "$RECORD_DIR/region_$(date +%Y-%m-%d_%H-%M-%S).mp4" &
    echo $! > "$PIDFILE"
    notify-send "Recording" "Region recording started" -i media-record -t 2000
fi
