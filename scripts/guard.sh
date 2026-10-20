#!/bin/bash
# Hook (PostToolUse, UserPromptSubmit). When subscription usage crosses a threshold, injects a
# wrap-up instruction. Trusts only this session's own fresh snapshot (written by statusline.sh);
# without one it periodically reminds the model to poll a usage tool if it has one.
. "$(dirname "$0")/common.sh"
in=$(cat)
event=$(printf '%s' "$in" | jq -r '.hook_event_name // "PostToolUse"')
sid=$(printf '%s' "$in" | jq -r '.session_id // "x"')
now=$(date +%s)
emit() { jq -n --arg e "$event" --arg m "$1" '{hookSpecificOutput:{hookEventName:$e,additionalContext:$m}}'; }
t5=$(cfg .guard.five_hour_threshold); t7=$(cfg .guard.seven_day_threshold); tm=$(cfg .guard.model_weekly_threshold)
warn=$(cfg .guard.warn_margin); stale=$(cfg .guard.stale_seconds); refire=$(cfg .guard.refire_seconds)
uf="$TK_HOME/usage-$sid.json"; valid=0
if [ -f "$uf" ]; then
  read -r ts u5 r5 u7 r7 < <(jq -r '[.ts,(.five_hour.used//-1),(.five_hour.resets_at//0),(.seven_day.used//-1),(.seven_day.resets_at//0)]|@tsv' "$uf")
  if [ $((now - ts)) -le "$stale" ] && [ "$r5" -gt "$now" ] && [ "$r7" -gt "$now" ]; then valid=1; fi
fi
if [ "$valid" = 0 ]; then
  [ "$(cfg .guard.poll_fallback)" = true ] || exit 0
  n=$(cfg .guard.poll_every_calls); cf="$TK_HOME/.count-$sid"
  c=$(( $(cat "$cf" 2>/dev/null || echo 0) + 1 )); echo "$c" > "$cf"
  if [ $((c % n)) -eq 1 ]; then
    emit "USAGE GUARD: no live usage data for this session. IF you have a tool that reports plan usage (for example get_usage in the Claude desktop app), call it now and compare to the thresholds in $TK_HOME/config.json (5-hour ${t5}%, weekly all-models ${t7}%). HARD STOP (invoke the usage-handoff skill with that window's reset time): 5-hour >= ${t5}% or weekly all-models >= ${t7}%. Per-model weekly windows (labelled 'Weekly - <Model>') are NOT a stop: at >= ${tm}% only that model is capped; if you are that model, tell the user and switch to a model with headroom or delegate to subagents on other models. Under all thresholds: continue silently. If you have no such tool, ignore this message and do not mention it."
  fi
  exit 0
fi
hit=$(awk -v u5="$u5" -v t5="$t5" -v u7="$u7" -v t7="$t7" -v w="$warn" 'BEGIN{
  if (u5>=t5) print "5h_hard"; else if (u7>=t7) print "7d_hard";
  else if (u5>=t5-w) print "5h_warn"; else if (u7>=t7-w) print "7d_warn"; else print "none"}')
[ "$hit" = none ] && exit 0
mark="$TK_HOME/.fired-$sid-$hit"
if [ -f "$mark" ]; then
  age=$(( now - $(stat -c %Y "$mark" 2>/dev/null || stat -f %m "$mark") ))
  [ "$age" -lt "$refire" ] && exit 0
fi
touch "$mark"
case "$hit" in 5h_*) win="5-hour"; used=$u5; reset=$r5;; *) win="weekly"; used=$u7; reset=$r7;; esac
if [[ "$hit" == *_hard ]]; then
  emit "USAGE GUARD: ${win} limit is at ${used}% (threshold reached; resets at epoch ${reset}). STOP starting new work. Finish only the step in flight, reach a clean state, then invoke the usage-handoff skill with reset epoch ${reset} to write the handoff and schedule the resume. Do not continue the task after the handoff."
else
  emit "USAGE GUARD (warning): ${win} limit is at ${used}%, close to the wrap-up threshold. Do not begin large new steps; prefer finishing the current one cleanly. Be ready to invoke the usage-handoff skill (reset epoch ${reset})."
fi
