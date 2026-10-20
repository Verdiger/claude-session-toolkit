#!/bin/bash
# Reads statusLine JSON on stdin, writes $TK_HOME/usage-<session_id>.json. Prints nothing.
. "$(dirname "$0")/common.sh"
in=$(cat)
sid=$(printf '%s' "$in" | jq -r '.session_id // empty'); [ -n "$sid" ] || exit 0
f5=$(printf '%s' "$in" | jq -r '.rate_limits.five_hour.used_percentage // empty')
r5=$(printf '%s' "$in" | jq -r '.rate_limits.five_hour.resets_at // empty')
f7=$(printf '%s' "$in" | jq -r '.rate_limits.seven_day.used_percentage // empty')
r7=$(printf '%s' "$in" | jq -r '.rate_limits.seven_day.resets_at // empty')
[ -n "$f5$f7" ] || exit 0
tmp=$(mktemp "$TK_HOME/.usage.XXXXXX")
jq -n --arg f5 "$f5" --arg r5 "$r5" --arg f7 "$f7" --arg r7 "$r7" --arg sid "$sid" --argjson ts "$(date +%s)" \
  '{ts:$ts, session_id:$sid,
    five_hour:{used:($f5|tonumber? // null), resets_at:($r5|tonumber? // null)},
    seven_day:{used:($f7|tonumber? // null), resets_at:($r7|tonumber? // null)}}' > "$tmp" && mv "$tmp" "$TK_HOME/usage-$sid.json"
