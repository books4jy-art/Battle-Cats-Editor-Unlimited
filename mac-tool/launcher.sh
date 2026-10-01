#!/bin/bash
# BC Level Caps launcher: runs the bundled Python, Java and Android tools (nothing to install).
HERE="$(cd "$(dirname "$0")/.." && pwd)"   # .../BC Level Caps.app/Contents
RES="$HERE/Resources"
LOG="$HOME/Library/Logs/BC Level Caps.log"
mkdir -p "$HOME/Library/Logs"

# The app was downloaded, so macOS marks every file inside as "from the internet"; once you've opened the
# app itself, clear that mark so the bundled tools can run without a separate prompt each.
xattr -dr com.apple.quarantine "$HERE/.." 2>/dev/null || true

export JAVA_HOME="$RES/jre/Contents/Home"
export PATH="$RES/build-tools:$JAVA_HOME/bin:$RES/python/bin:$PATH"
export PYTHONNOUSERSITE=1
exec "$RES/python/bin/python3" "$RES/levelcap_app.py" >>"$LOG" 2>&1
