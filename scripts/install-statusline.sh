#!/bin/bash
# Prints (or with --apply, merges) the statusLine setting that feeds the usage guard.
# --apply backs up ~/.claude/settings.json first and refuses to overwrite an existing statusLine.
. "$(dirname "$0")/common.sh"
snippet=$(jq -n --arg c "$TK_ROOT/scripts/statusline.sh" '{statusLine:{type:"command",command:$c}}')
if [ "$1" != "--apply" ]; then echo "Add to ~/.claude/settings.json:"; echo "$snippet"; echo "(If you already have a statusLine, pipe its stdin into $TK_ROOT/scripts/usage-capture.sh instead.)"; exit 0; fi
s="$HOME/.claude/settings.json"; [ -f "$s" ] || echo '{}' > "$s"
jq -e '.statusLine' "$s" >/dev/null 2>&1 && { echo "A statusLine already exists in $s; not overwriting. See the note above."; exit 1; }
cp "$s" "$s.bak-toolkit-$(date +%Y%m%d-%H%M%S)"
jq --argjson n "$snippet" '. + $n' "$s" > "$s.tmp" && mv "$s.tmp" "$s" && echo "statusLine added (backup saved next to settings.json)."
