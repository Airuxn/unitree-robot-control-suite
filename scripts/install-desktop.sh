#!/bin/bash
# Install desktop launcher with correct paths for this machine.
set -e

INSTALL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
DESKTOP_FILE="$DESKTOP_DIR/unitree-robot-control-suite.desktop"

mkdir -p "$DESKTOP_DIR"
sed "s|@INSTALL_DIR@|$INSTALL_DIR|g" "$INSTALL_DIR/unitree-robot-control-suite.desktop.in" > "$DESKTOP_FILE"
chmod +x "$DESKTOP_FILE"

echo "Desktop launcher installed: $DESKTOP_FILE"
echo "Install dir: $INSTALL_DIR"
