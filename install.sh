#!/bin/bash
# Football Club Tracker installer for macOS.
#
#   Install or update:  curl -fsSL https://raw.githubusercontent.com/varungirish97/football-club-tracker/main/install.sh | bash
#   Uninstall:          curl -fsSL https://raw.githubusercontent.com/varungirish97/football-club-tracker/main/install.sh | bash -s -- --uninstall
#
# What it does: downloads the app, makes sure SwiftBar is installed, points
# SwiftBar at the app, asks you to pick your club, then starts SwiftBar.

set -euo pipefail

REPO="${FCT_REPO:-varungirish97/football-club-tracker}"
BRANCH="${FCT_BRANCH:-main}"
DEST="$HOME/Library/Application Support/FootballClubTracker"
PLUGIN_NAME="football.1m.py"

bold() { printf "\n\033[1m%s\033[0m\n" "$*"; }
fail() { printf "\n\033[31m%s\033[0m\n" "$*" >&2; exit 1; }

swiftbar_dir() { defaults read com.ameba.SwiftBar PluginDirectory 2>/dev/null || true; }

[ "$(uname)" = "Darwin" ] || fail "This app only runs on macOS."

# ---------- uninstall ----------
if [ "${1:-}" = "--uninstall" ]; then
  bold "Removing Football Club Tracker…"
  current="$(swiftbar_dir)"
  if [ -n "$current" ] && [ -L "$current/$PLUGIN_NAME" ]; then
    rm -f "$current/$PLUGIN_NAME"
  fi
  if [ "$current" = "$DEST/plugins" ]; then
    defaults delete com.ameba.SwiftBar PluginDirectory 2>/dev/null || true
  fi
  rm -rf "$DEST"
  bold "Done. SwiftBar itself is still installed; drag it from Applications to the Bin if you don't need it."
  exit 0
fi

bold "⚽  Installing Football Club Tracker"

# ---------- 1. Python ----------
# macOS has a python3 placeholder that offers to install Apple's developer tools.
if ! /usr/bin/python3 -c "import sys" >/dev/null 2>&1; then
  xcode-select --install >/dev/null 2>&1 || true
  fail "macOS needs to install Python first. Click Install in the window that just opened, wait for it to finish, then run this installer again."
fi

# ---------- 2. Download the app ----------
bold "Downloading…"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
curl -fsSL "https://github.com/$REPO/archive/refs/heads/$BRANCH.zip" -o "$tmp/app.zip" \
  || fail "Couldn't download the app. Check your internet connection and try again."
unzip -q "$tmp/app.zip" -d "$tmp"
src="$(find "$tmp" -mindepth 1 -maxdepth 1 -type d | head -n 1)"

mkdir -p "$DEST"
rm -rf "$DEST/plugins"                 # drop old plugin versions; config.json and caches stay
cp -R "$src/." "$DEST/"
chmod +x "$DEST/setup.py" "$DEST/plugins/"*.py

# ---------- 3. SwiftBar ----------
if [ ! -d "/Applications/SwiftBar.app" ] && [ ! -d "$HOME/Applications/SwiftBar.app" ]; then
  bold "Installing SwiftBar, the free app that shows this in your menu bar…"
  if command -v brew >/dev/null 2>&1; then
    brew install --cask swiftbar
  else
    echo "Opening the SwiftBar website. Download it, drag it into Applications,"
    echo "then come back here."
    open "https://swiftbar.app"
    read -r -p "Press Enter once SwiftBar is in your Applications folder… " </dev/tty
    [ -d "/Applications/SwiftBar.app" ] || [ -d "$HOME/Applications/SwiftBar.app" ] \
      || fail "SwiftBar still isn't in Applications. Install it, then run this installer again."
  fi
fi

# ---------- 4. Point SwiftBar at the app ----------
osascript -e 'quit app "SwiftBar"' >/dev/null 2>&1 || true
current="$(swiftbar_dir)"
if [ -z "$current" ] || [ "$current" = "$DEST/plugins" ] || [ ! -d "$current" ]; then
  defaults write com.ameba.SwiftBar PluginDirectory "$DEST/plugins"
else
  # You already use SwiftBar with other plugins: add ours alongside them.
  ln -sf "$DEST/plugins/$PLUGIN_NAME" "$current/$PLUGIN_NAME"
fi

# ---------- 5. Pick a club ----------
if [ -f "$DEST/config.json" ]; then
  bold "Updated. Keeping your current club (use 'Change club…' in the menu to switch)."
else
  /usr/bin/python3 "$DEST/setup.py" </dev/tty
fi

# ---------- 6. Start ----------
open -a SwiftBar
bold "✅  All set! Look for your club's crest in the menu bar."
echo "Can't see it? On MacBooks with a notch, macOS hides menu bar icons that don't fit."
echo "Quit another menu bar app to make room."
