#!/bin/bash
# Screen recording toggle — start/stop with wf-recorder

RECORD_DIR="$HOME/Videos/recordings"
mkdir -p "$RECORD_DIR"

PIDFILE="/tmp/recording.pid"

if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    # Stop recording
    kill "$(cat "$PIDFILE")"
    rm -f "$PIDFILE"
    notify-send "Recording" "Stopped and saved to $RECORD_DIR" -i media-record -t 2000
else
    # Start recording — full screen
    wf-recorder -f "$RECORD_DIR/$(date +%Y-%m-%d_%H-%M-%S).mp4" &
    echo $! > "$PIDFILE"
    notify-send "Recording" "Started — press again to stop" -i media-record -t 2000
fi
