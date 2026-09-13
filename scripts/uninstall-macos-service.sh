#!/bin/zsh
set -euo pipefail

UID_NUM="$(id -u)"

for label in com.rdb.tivimate-playlist com.rdb.tivimate-refresh; do
  launchctl bootout "gui/${UID_NUM}/${label}" >/dev/null 2>&1 || true
  rm -f "$HOME/Library/LaunchAgents/${label}.plist"
done

echo "Removed the playlist server and the daily refresh job."
