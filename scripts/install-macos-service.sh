#!/bin/zsh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="$(command -v python3)"
PORT="${PORT:-8080}"
REFRESH_HOUR="${REFRESH_HOUR:-5}"
REFRESH_MINUTE="${REFRESH_MINUTE:-0}"
UID_NUM="$(id -u)"

install_agent() {
  local label="$1"
  local plist="$HOME/Library/LaunchAgents/${label}.plist"
  mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"
  cat > "$plist"
  launchctl bootout "gui/${UID_NUM}/${label}" >/dev/null 2>&1 || true
  launchctl bootstrap "gui/${UID_NUM}" "$plist"
  launchctl enable "gui/${UID_NUM}/${label}"
}

install_agent "com.rdb.tivimate-playlist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.rdb.tivimate-playlist</string>
  <key>ProgramArguments</key>
  <array>
    <string>${PYTHON}</string>
    <string>${REPO_ROOT}/scripts/serve.py</string>
    <string>--port</string>
    <string>${PORT}</string>
  </array>
  <key>WorkingDirectory</key>
  <string>${REPO_ROOT}</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>${HOME}/Library/Logs/rdb-tivimate.log</string>
  <key>StandardErrorPath</key>
  <string>${HOME}/Library/Logs/rdb-tivimate.log</string>
</dict>
</plist>
EOF

install_agent "com.rdb.tivimate-refresh" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.rdb.tivimate-refresh</string>
  <key>ProgramArguments</key>
  <array>
    <string>${PYTHON}</string>
    <string>${REPO_ROOT}/scripts/refresh_playlist.py</string>
  </array>
  <key>WorkingDirectory</key>
  <string>${REPO_ROOT}</string>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>${REFRESH_HOUR}</integer>
    <key>Minute</key>
    <integer>${REFRESH_MINUTE}</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>${HOME}/Library/Logs/rdb-tivimate-refresh.log</string>
  <key>StandardErrorPath</key>
  <string>${HOME}/Library/Logs/rdb-tivimate-refresh.log</string>
</dict>
</plist>
EOF

echo "Installed playlist server (port ${PORT}) and daily refresh at ${REFRESH_HOUR}:$(printf '%02d' "$REFRESH_MINUTE")."
echo "Running one refresh now so the file is current..."
"$PYTHON" "$REPO_ROOT/scripts/refresh_playlist.py"
echo
"$PYTHON" "$REPO_ROOT/scripts/serve.py" --port "$PORT" --urls
echo "Server log:   $HOME/Library/Logs/rdb-tivimate.log"
echo "Refresh log:  $HOME/Library/Logs/rdb-tivimate-refresh.log"
echo "Remove later: $REPO_ROOT/scripts/uninstall-macos-service.sh"
