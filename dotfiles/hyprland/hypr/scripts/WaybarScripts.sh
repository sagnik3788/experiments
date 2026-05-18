#!/bin/bash
case "$1" in
    --files)  nautilus ;;
    --term)   kitty ;;
    *)        echo "Usage: $0 --files | --term" ;;
esac
