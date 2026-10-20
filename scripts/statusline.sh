#!/bin/bash
# Claude Code statusLine command. Records subscription usage for guard.sh and prints a short status.
# Already have a statusline? Pipe its input to usage-capture.sh instead (see README).
in=$(cat)
printf '%s' "$in" | "$(dirname "$0")/usage-capture.sh"
f5=$(printf '%s' "$in" | jq -r '.rate_limits.five_hour.used_percentage // "?"')
f7=$(printf '%s' "$in" | jq -r '.rate_limits.seven_day.used_percentage // "?"')
printf '5h %s%% | 7d %s%%' "$f5" "$f7"
