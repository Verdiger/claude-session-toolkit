#!/bin/bash
# Usage: schedule_resume.sh <handoff.md> <reset_epoch> <project_dir>
# Schedules a one-shot job that starts a fresh headless Claude session to continue from the handoff.
# macOS: launchd. Linux: systemd-run --user (if available). Otherwise prints a manual command.
set -e
. "$(dirname "$0")/common.sh"
handoff="$1"; reset="$2"; proj="$3"
[ -f "$handoff" ] && [ -n "$reset" ] && [ -d "$proj" ] || { echo "usage: $0 <handoff.md> <reset_epoch> <project_dir>"; exit 1; }
CLAUDE=$(claude_bin)
"$CLAUDE" auth status 2>/dev/null | grep -q '"loggedIn": true' || echo "WARNING: headless claude is not logged in; the resume will fail until you run 'claude auth login' in a terminal."
delay=$(cfg .resume.delay_seconds); mode=$(cfg .resume.permission_mode)
at=$((reset + delay)); now=$(date +%s); [ "$at" -le "$now" ] && at=$((now + 60))
id="$(date +%Y%m%d-%H%M%S)"; log="$TK_HOME/resume-$id.log"; runner="$TK_HOME/run-$id.sh"
prompt="You are resuming interrupted work. Read $handoff fully, verify the repo state it describes, then continue from 'What remains'. Before starting, check usage; if the relevant limit is still above its threshold, stop and say so."
cat > "$runner" <<RUN
#!/bin/bash
cd "$proj" || exit 1
echo "start \$(date)" >> "$log"
"$CLAUDE" -p --permission-mode "$mode" "$prompt" </dev/null >> "$log" 2>&1
echo "exit \$? \$(date)" >> "$log"
RUN
chmod +x "$runner"
case "$(uname)" in
Darwin)
  label="com.claude-session-toolkit.resume.$id"; plist="$HOME/Library/LaunchAgents/$label.plist"; mkdir -p "$HOME/Library/LaunchAgents"
  # self-cleanup appended after the run
  echo "launchctl bootout gui/\$(id -u)/$label 2>/dev/null; rm -f \"$plist\"" >> "$runner"
  read -r M D H Mi < <(date -r "$at" '+%-m %-d %-H %-M')
  cat > "$plist" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>$label</string>
<key>ProgramArguments</key><array><string>/bin/bash</string><string>$runner</string></array>
<key>StartCalendarInterval</key><dict><key>Month</key><integer>$M</integer><key>Day</key><integer>$D</integer><key>Hour</key><integer>$H</integer><key>Minute</key><integer>$Mi</integer></dict>
<key>EnvironmentVariables</key><dict><key>PATH</key><string>$PATH</string></dict>
</dict></plist>
PL
  launchctl bootstrap "gui/$(id -u)" "$plist"
  echo "scheduled for $(date -r "$at"). Cancel: launchctl bootout gui/$(id -u)/$label && rm \"$plist\" \"$runner\"" ;;
*)
  if command -v systemd-run >/dev/null; then
    systemd-run --user --on-calendar="$(date -d "@$at" '+%Y-%m-%d %H:%M:%S')" --unit="claude-resume-$id" /bin/bash "$runner" >/dev/null
    echo "scheduled for $(date -d "@$at"). Cancel: systemctl --user stop claude-resume-$id.timer"
  else
    echo "No scheduler found. Run this at $(date -d "@$at" 2>/dev/null || echo "epoch $at"): /bin/bash $runner"
  fi ;;
esac
