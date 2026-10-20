---
name: usage-handoff
description: Use when the USAGE GUARD hook says a usage limit is reached, when the user says "wrap up", "hand off", or "I'm running low on tokens", or when a usage report shows the 5-hour or weekly limit past its threshold. Stops work at a clean point, writes a full handoff file, and schedules an automatic resume after the limit resets.
---

# Usage handoff

Goal: the user always keeps usage left to chat, plan and research. When a limit is near, stop at a clean point, record everything a fresh session needs, and schedule the continuation for after the reset.

Scripts live in the plugin's `scripts/` directory: the folder two levels above this skill's base directory (`<base directory>/../../scripts/`). Thresholds and settings are in `~/.claude/session-toolkit/config.json` (created on first use from `config.default.json`).

## When it triggers
- The `guard.sh` hook injects "USAGE GUARD" messages from live usage data (needs the statusline feed: run `scripts/install-statusline.sh`).
- Without that feed the hook only reminds you to poll. If you have a usage tool (for example `get_usage` in the Claude desktop app), call it and compare each window's percent to the thresholds.
- Only the 5-hour window and "weekly all models" trigger a handoff. Per-model weekly windows ("Weekly - <Model>") cap one model only: if you are that model, tell the user and switch to another model or delegate to subagents on other models; do not hand off.

## Steps
1. **Stop new work.** Finish only the step in flight. Do not start a subagent, a long run, or a merge.
2. **Reach a clean state.** No half-run tests or half-applied edits. Commit work in progress to the current branch if reasonable. Never push, merge, deploy, or message anyone as part of wrap-up.
3. **Write the handoff** to `~/claude-handoffs/<YYYYMMDD-HHMM>-<slug>.md` using the template below. Facts only: paths, branch, commit, commands run and their results. Mark anything unverified.
4. **Schedule the resume:** `<scripts>/schedule_resume.sh <handoff.md> <reset_epoch> <project_dir>`. Use the reset epoch from the hook message (or convert the usage tool's reset time). Use the window that tripped; if both are over, use the later reset.
5. **Tell the user** in 3-4 plain sentences: where it stopped, where the handoff is, when it resumes, and the cancel command the script printed. Then stop. Do not continue the task.

## Handoff template
```
# Handoff: <task title>
Written: <date time> | Reason: <5-hour|weekly> limit at <N>% | Resumes: <date time>
Project dir: <abs path> | Branch: <name> | Last commit: <hash> | Dirty files: <list or none>

## Goal
<what the user asked for, in their words, plus decisions already made>

## Done (verified)
- <item> — evidence: <test/command/output>

## In flight when stopped
- <what was mid-step and its exact state>

## What remains (ordered)
1. <next step, concrete: file, function, command>

## Knowledge a fresh session needs
Stack/versions, paths, env, commands to run and test, gotchas found, rejected approaches and why.

## Do NOT do without the user
<push/merge/deploy/send/delete items that were pending approval>

## Resume check
First run: <commands to confirm repo state matches this file>. If the limit is still above threshold, stop and say so.
```

## Notes
- The resume runs a fresh headless `claude -p` in the project directory with the permission mode from config (default `acceptEdits`): it can edit files but cannot get approvals; anything needing approval waits for the user.
- It needs headless login (`claude auth login`, once). The script warns if you are logged out.
- macOS uses a one-shot launchd agent, Linux uses `systemd-run --user` when present. The Linux path is untested; otherwise the script prints the command to run manually.
