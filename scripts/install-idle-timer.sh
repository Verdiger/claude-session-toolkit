#!/bin/bash
# Opt-in: run the idle-session knowledge harvest every 15 minutes. Usage: install-idle-timer.sh [--uninstall]
# Each run may spend a small amount of model usage (see README). Needs headless login: `claude auth login`.
set -e
. "$(dirname "$0")/common.sh"
script="$TK_ROOT/scripts/idle_harvest.py"; py=$(command -v python3)
mkdir -p "$HOME/Library/LaunchAgents"
if [ "$(uname)" = Darwin ]; then
  label="com.claude-session-toolkit.idle-harvest"; plist="$HOME/Library/LaunchAgents/$label.plist"
  if [ "$1" = "--uninstall" ]; then launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true; rm -f "$plist"; echo removed; exit 0; fi
  cat > "$plist" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>$label</string>
<key>ProgramArguments</key><array><string>$py</string><string>$script</string></array>
<key>StartInterval</key><integer>900</integer>
<key>StandardOutPath</key><string>$TK_HOME/idle-harvest.log</string>
<key>StandardErrorPath</key><string>$TK_HOME/idle-harvest.log</string>
<key>EnvironmentVariables</key><dict><key>PATH</key><string>$PATH</string></dict>
</dict></plist>
PL
  launchctl bootstrap "gui/$(id -u)" "$plist" && echo "installed (every 15 min). Log: $TK_HOME/idle-harvest.log"
else
  line="*/15 * * * * $py $script >> $TK_HOME/idle-harvest.log 2>&1"
  if [ "$1" = "--uninstall" ]; then crontab -l 2>/dev/null | grep -vF "$script" | crontab -; echo removed; exit 0; fi
  (crontab -l 2>/dev/null | grep -vF "$script"; echo "$line") | crontab - && echo "installed via cron: $line"
fi
