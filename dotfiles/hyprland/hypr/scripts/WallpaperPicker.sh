#!/bin/bash
# Pick an image and set as wallpaper
IMAGE=$(zenity --file-selection --title="Select Wallpaper" \
    --file-filter="Images (jpg, png, webp) | *.jpg *.jpeg *.png *.webp" 2>/dev/null) || \
IMAGE=$(kdialog --getopenfilename "$HOME/Pictures" "Images (*.jpg *.jpeg *.png *.webp)" 2>/dev/null)

if [ -n "$IMAGE" ]; then
    cp "$IMAGE" "$HOME/Pictures/wallpaper.jpg"
    swww img "$HOME/Pictures/wallpaper.jpg" --transition-type center --transition-fps 60 2>/dev/null
fi
