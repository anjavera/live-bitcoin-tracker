#!/bin/sh
# Installs the downloaded Linux desktop app for the current user and adds an app-menu entry (no terminal needed to run it).
# Usage: sh install-gui.sh [path/to/btc15-gui-linux-x86_64]   (run it from the folder holding the download)
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
BIN="${1:-$HERE/btc15-gui-linux-x86_64}"
if [ ! -f "$BIN" ]; then
  echo "Could not find the app at: $BIN"
  echo "Usage: sh install-gui.sh path/to/btc15-gui-linux-x86_64"
  exit 1
fi
mkdir -p "$HOME/.local/bin" "$HOME/.local/share/applications" "$HOME/.local/share/icons"
cp "$BIN" "$HOME/.local/bin/btc15-gui"
chmod +x "$HOME/.local/bin/btc15-gui"
[ -f "$HERE/icon.png" ] && cp "$HERE/icon.png" "$HOME/.local/share/icons/btc15-widget.png"
sed "s|^Exec=.*|Exec=$HOME/.local/bin/btc15-gui|" "$HERE/btc15-gui.desktop" > "$HOME/.local/share/applications/btc15-gui.desktop"
echo "Installed. Find 'BTC 15m Tracker' in your app menu, or run: $HOME/.local/bin/btc15-gui"
echo "(If the window does not open on an X11 desktop, install one system library: sudo apt install libxcb-cursor0)"
echo "(If the command is not found, add \$HOME/.local/bin to your PATH.)"
