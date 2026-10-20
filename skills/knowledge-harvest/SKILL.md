---
name: knowledge-harvest
description: Use when the user says "harvest knowledge", "what should become skills", "update the skills from what we learned", or after finishing a milestone or pipeline in any project. Scans auto-memory, existing skills and recent transcripts for knowledge, pipelines and gotchas not yet captured, then adds or updates skills and memory (with backups and a log). Can also run automatically on idle sessions (opt-in).
---

# Knowledge harvest

Goal: what we learn while working ends up where the next session will find it, without bloating context and without inventing anything. Memory holds short facts loaded every session. A skill holds procedures and deep knowledge that load only when relevant. Harvest decides which is which.

Scripts live in the plugin's `scripts/` directory: `<base directory of this skill>/../../scripts/`.

## Run it
1. `python3 <scripts>/harvest_scan.py` prints memory entries (`~/.claude/projects/*/memory/`) grouped by topic, which user skill (if any) names each one, and what changed since the last harvest. `name?` marks a weak match. "Uncovered" is a worklist, not a verdict: most project facts correctly stay in memory.
2. Cluster by topic. Pick the clusters with the most uncovered or recently changed entries.
3. Decide with the table below. State the decision and why in one line.
4. For clusters that earn a skill, delegate extraction to cheaper subagents, one per cluster (a few at a time). Brief each with the memory files, the repo paths they name, and the output shape. They read sources; they do not write from memory of the memory.
5. Write into `~/.claude/skills/<name>/` (new) or as a new reference file in an existing skill. Back up any file you replace (`cp f f.bak-YYYY-MM-DD`).
6. Apply on your own judgment, then report what changed. Never delete a skill, never shrink a file by more than 30%, never push, merge, or message anyone.
7. Run `python3 <scripts>/harvest_scan.py --mark`, and add a one-line pointer in memory if the skill is new.

## Skill, memory, or nothing
| Knowledge | Goes to |
|---|---|
| Multi-step pipeline that gets rerun (build, release, data pipeline) | **Skill** with the exact commands and gates |
| Deep domain reference too big for memory | **Skill reference file**, linked from SKILL.md |
| "How to work in project X" that should auto-trigger when touching it (conventions, gotchas, where things live, what is shipped) | **Project skill** (short SKILL.md, details in references) |
| One-line fact, decision, preference, status | Stay in **memory** |
| True only for this conversation, or already recorded in code/git | **Nothing** |
| Superseded or contradicted by newer evidence | Fix or retire the old entry; do not skill-ify stale facts |

A skill description must say when to use it, in the user's own trigger words. Keep SKILL.md under ~150 lines; put detail in reference files.

## Quality gates (non-negotiable)
- Every claim traces to a source: a file path, a commit or PR, a test or measurement, a doc, or an explicit statement by the user. Memory entries are leads, not proof: verify against the repo or mark "unverified (memory only)".
- No secrets, tokens, keys, or credentials in a skill. Point to where they live.
- Honor the user's stated preferences from memory (language, spelling, style).
- Record what was dropped and why, so nothing disappears silently.
- Merge into an existing skill rather than duplicating one. Check `ls ~/.claude/skills` first.

## As-we-go mode (cheap, after each milestone)
When a project milestone lands, do a mini-harvest without the full scan: list what this session learned that a fresh session would need (new command, gotcha, shipped surface, rejected approach), check the owning skill, and make the smallest addition. One reference-file append beats a new skill.

## Idle auto-harvest (opt-in)
`<scripts>/install-idle-timer.sh` installs a timer (launchd on macOS, cron elsewhere; `--uninstall` removes it). Every 15 minutes `idle_harvest.py` picks the newest session transcript idle for at least `idle_minutes`, builds a bounded digest, and runs a headless `claude -p` (default model `sonnet`, at most `max_runs_per_day` runs) that writes an `actions.json` to the inbox (`~/claude-harvest` by default). It needs headless login (`claude auth login`).
- `apply_mode: "propose"` (default): the actions file waits in the inbox. Read it, then apply with `python3 <scripts>/apply_actions.py <file>`.
- `apply_mode: "apply"`: a guarded applier (`apply_actions.py`) applies them automatically: `.md` files inside skill folders or memory directories only, no secrets, size caps, backups to `<inbox>/backups/`, no deletes, no shrinking, log in `<inbox>/applied.log`.
When asked "what did the idle harvest find", read the inbox files or `applied.log`, summarize, flag anything wrong, and restore from backups if asked.

## Report format
Three short lists: **Added**, **Updated**, **Left in memory / dropped** (with reasons). Say how to restore from backups.
