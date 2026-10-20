#!/usr/bin/env python3
"""Idle-session harvest (opt-in; see install-idle-timer.sh). --dry-run prints what it would do.

Every run picks ONE session transcript that has been idle >= idle_minutes, was active within
max_session_age_hours, is big enough to matter, and has not been harvested at its current mtime.
It builds a bounded text digest, asks a headless `claude -p` run for an actions.json, and then
either applies it (apply_mode "apply", via apply_actions.py) or leaves it in the inbox
(apply_mode "propose", the default) for you to review and apply.
"""
import fcntl, glob, json, os, subprocess, sys, time
from tk import H, TK_HOME, ROOT, PROJECTS, config, claude_bin, inbox
CFG = config()["harvest"]
INBOX = inbox(config())
STATE = f"{TK_HOME}/idle-state.json"
CLAUDE = claude_bin()
DRY = "--dry-run" in sys.argv
NOISE = ("<system-reminder", "<task-notification", "[SYSTEM", "<command-", "Base directory for this skill")

def load_state():
    try: return json.load(open(STATE))
    except Exception: return {"done": {}, "runs": []}

def logged_in():
    try:
        r = subprocess.run([CLAUDE, "auth", "status"], capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=30)
        return json.loads(r.stdout).get("loggedIn") is True
    except Exception:
        return False

def digest(path, cap):
    out = []
    for line in open(path, errors="ignore"):
        try: d = json.loads(line)
        except Exception: continue
        t, m = d.get("type"), d.get("message") or {}
        c = m.get("content")
        if t == "user":
            if isinstance(c, list):
                c = "\n".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
            if isinstance(c, str) and c.strip() and not c.startswith(NOISE):
                out.append("USER: " + c[:1200])
        if t == "assistant" and isinstance(c, list):
            for b in c:
                if b.get("type") == "text" and len(b.get("text", "")) > 40: out.append("CLAUDE: " + b["text"][:1500])
                elif b.get("type") == "tool_use" and b.get("name") in ("Write", "Edit", "NotebookEdit"):
                    out.append("FILE_CHANGED: " + str(b.get("input", {}).get("file_path", "")))
    text = "\n".join(out)
    if len(text) > cap:  # keep the start (goal) and the end (outcome)
        h = cap // 3
        text = text[:h] + "\n[... middle trimmed ...]\n" + text[-(cap - h):]
    return text

def main():
    if not CFG["enabled"]: return print("disabled")
    if not DRY and not logged_in(): return print("headless claude is not logged in (run `claude auth login` once); skipping")
    os.makedirs(INBOX, exist_ok=True)
    lock = open(f"{TK_HOME}/.idle-lock", "w")
    try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError: return print("another run active")
    st = load_state(); now = time.time()
    st["runs"] = [r for r in st["runs"] if now - r < 86400]
    if len(st["runs"]) >= CFG["max_runs_per_day"] and not DRY: return print("daily cap reached")
    cands = []
    for p in glob.glob(f"{PROJECTS}/*/*.jsonl"):
        mt, sz = os.path.getmtime(p), os.path.getsize(p)
        if (now - mt) / 60 < CFG["idle_minutes"] or (now - mt) > CFG["max_session_age_hours"] * 3600: continue
        if sz < CFG["min_transcript_kb"] * 1024 or st["done"].get(p, 0) >= mt: continue
        cands.append((mt, sz, p))
    if not cands: return print("nothing idle to harvest")
    text, p = "", ""
    for mt, sz, p in sorted(cands, reverse=True):  # newest idle session first
        text = digest(p, CFG["digest_max_kb"] * 1024)
        if len(text) >= CFG["min_digest_chars"] and not text.startswith("USER: <scheduled-task"): break
        st["done"][p] = mt  # automated or trivial session: skip for free, no model call
        text = ""
    if not DRY: json.dump(st, open(STATE, "w"))
    if not text: return print(f"{len(cands)} candidates, none with enough human content")
    sid = os.path.basename(p)[:8]; memdir = f"{os.path.dirname(p)}/memory"
    dpath = f"{TK_HOME}/digest-{sid}.txt"; open(dpath, "w").write(text)
    out = f"{INBOX}/{time.strftime('%Y-%m-%d-%H%M')}-{sid}.actions.json"
    print(f"picked {p} ({sz//1024}KB, idle {int((now-mt)/60)} min); {len(cands)} candidates")
    if DRY: print(f"[dry-run] digest {len(text)} chars; would write {out}"); return os.remove(dpath)
    skill_md = f"{ROOT}/skills/knowledge-harvest/SKILL.md"
    prompt = (f"Run an automatic knowledge harvest. Read {skill_md} (decision table and quality gates). "
              f"The session digest is {dpath} (full transcript {p}; grep it for specifics, do not read it whole). "
              f"The memory directory for this project is {memdir}; user skills live in ~/.claude/skills. Check both first so nothing duplicates; "
              f"verify load-bearing claims against the files named. Your ONLY output is one JSON file written to {out}: "
              '{"summary": "1 line", "actions": [{"op": "add_memory"|"write_file"|"append_file", '
              '"name","description","type","body" (for add_memory) | "path","content" (for write_file/append_file; .md files under ~/.claude/skills/<skill>/ or the memory dir), '
              '"reason": "REQUIRED why this belongs", "evidence": "REQUIRED what in the digest/files proves it"}], "dropped": ["item: why"]}. '
              "At most 6 actions. Prefer the smallest change: append to an existing reference file or fix a stale memory entry over a new skill. "
              "To fix contradicted memory use write_file with the corrected full file. Mark unverified claims as 'unverified'. "
              "Empty actions is a valid, good answer. No secrets. Do NOT edit anything yourself; a validator handles the actions.")
    r = subprocess.run([CLAUDE, "-p", "--model", CFG["model"], "--allowedTools", "Read", "Grep", "Glob", "Write", "--", prompt],
                       capture_output=True, text=True, timeout=1800, cwd=H, stdin=subprocess.DEVNULL)
    ok = os.path.exists(out)
    if ok or r.returncode == 0: st["done"][p] = mt  # a failed run is retried on the next tick
    st["runs"].append(now); json.dump(st, open(STATE, "w")); os.remove(dpath)
    print("exit", r.returncode, "actions file written" if ok else "NO actions file", (r.stdout + r.stderr)[-300:])
    if not ok: return
    data = json.load(open(out)); data["memory_dir"] = memdir; json.dump(data, open(out, "w"), indent=1)
    if CFG["apply_mode"] == "apply":
        ar = subprocess.run([sys.executable, f"{ROOT}/scripts/apply_actions.py", out], capture_output=True, text=True)
        print(ar.stdout[-1500:], ar.stderr[-300:]); n = ar.stdout.count("APPLIED"); msg = f"Knowledge harvest applied {n} change(s). See {INBOX}/applied.log"
    else:
        n = len(data.get("actions", [])); msg = f"Knowledge harvest proposed {n} change(s). Review {out}, apply with apply_actions.py"
    if n and sys.platform == "darwin":
        subprocess.run(["osascript", "-e", f'display notification "{msg}" with title "Claude"'])
    elif n: print(msg)

main()
