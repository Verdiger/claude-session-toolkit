# claude-session-toolkit

Two skills for long Claude Code sessions, packaged as one plugin.

| Skill | What it does |
|---|---|
| **usage-handoff** | Watches your subscription usage. At a threshold (default 95% of the 5-hour limit, 90% of the weekly limit) it makes Claude stop at a clean point, write a handoff file (done / in flight / what remains / what a fresh session needs), and schedule a headless resume after the limit resets. Goal: you never run out of usage mid-chat; the long job pauses instead. |
| **knowledge-harvest** | Scans your auto-memory, your skills, and recent session transcripts for knowledge that never made it into a skill, then adds or updates skills and memory. Optional timer runs it on idle sessions automatically. |

They are bundled because they share one config and one set of scripts, and both exist to keep long-running work from losing what was learned.

## Install

```
/plugin marketplace add Verdiger/claude-session-toolkit
/plugin install claude-session-toolkit@claude-session-toolkit
```

Requirements: `jq`, `python3`, and the `claude` CLI. Tested on macOS (Claude Code 2.1.x, CLI and desktop app). Linux paths exist but are untested. Windows is not supported.

### Enable the usage guard
The guard reads usage from the statusline feed. Claude Code only provides it to Pro and Max subscribers, and only after the first API response of a session.

```
scripts/install-statusline.sh          # prints the settings snippet
scripts/install-statusline.sh --apply  # merges it into ~/.claude/settings.json (backs up first, never overwrites an existing statusLine)
```
Already have a statusline? Pipe its stdin into `scripts/usage-capture.sh` instead. The plugin's hook (`hooks/hooks.json`, runs after tool calls and on each prompt) is registered automatically on install.

Where the statusline never runs (some desktop-app sessions), the hook falls back to reminding Claude every `poll_every_calls` calls to check usage with whatever tool it has (for example `get_usage` in the Claude desktop app). If no tool exists it does nothing.

### Enable unattended resume and idle harvest
Both run a headless `claude -p`, which needs a one-time login: `claude auth login`.

```
scripts/install-idle-timer.sh              # opt-in idle harvest (launchd on macOS, cron elsewhere)
scripts/install-idle-timer.sh --uninstall
```
The resume job is created per handoff by `scripts/schedule_resume.sh` (called by the skill).

## Configuration
`~/.claude/session-toolkit/config.json` (created from `config.default.json`):

- `guard.five_hour_threshold`, `seven_day_threshold`: stop-and-hand-off points.
- `guard.model_weekly_threshold`: per-model weekly windows cap one model only and never trigger a handoff.
- `resume.permission_mode`: permission mode for the resumed headless run (default `acceptEdits`).
- `harvest.apply_mode`: `propose` (default; actions wait in `~/claude-harvest`) or `apply`.
- `harvest.max_runs_per_day`, `idle_minutes`, `model`: how often and how cheaply the idle harvest runs.

## What to know before turning things on
- **Cost.** Each idle-harvest run is a headless Claude call (default: `sonnet`, up to 3 a day). Resumed sessions spend usage after the reset like any session.
- **Privacy.** The idle harvest reads your session transcripts and sends a bounded digest to Claude under your own account. Do not enable it for sessions with material you would not otherwise show Claude. Nothing is sent anywhere else.
- **Safety of auto-apply.** In `apply` mode, `scripts/apply_actions.py` only writes `.md` files inside `~/.claude/skills/<skill>/` or `~/.claude/projects/*/memory/`, refuses content that looks like a secret, caps size, backs up every overwrite to `<inbox>/backups/`, never deletes, and refuses to shrink a file below 70%. Everything is logged to `<inbox>/applied.log`. The content itself is model-written: review `applied.log` now and then. Memory is treated as leads, not proof.
- **Resume runs unattended** in the project directory with edit permission only. Review the handoff file; cancel with the command the script prints.

## Layout
```
.claude-plugin/    plugin + marketplace manifests
skills/            usage-handoff, knowledge-harvest
hooks/hooks.json   usage guard hook
scripts/           guard, statusline feed, resume scheduler, harvest scan/applier/idle runner, installers
config.default.json
```

## License
MIT
