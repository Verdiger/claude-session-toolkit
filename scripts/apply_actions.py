#!/usr/bin/env python3
"""Validate and apply a harvest actions.json. Usage: apply_actions.py <actions.json> [--dry-run]

Guardrails: .md files only, only inside ~/.claude/skills/<skill>/ or ~/.claude/projects/*/memory/;
no secrets; size caps; backup before any overwrite; no deletes; no shrinking an existing file
below 70%; MEMORY.md is only touched by appending an index line for a new memory file.
Every result is logged to <inbox>/applied.log.
"""
import json, os, re, shutil, sys, time
from tk import H, SKILLS, PROJECTS, config, inbox
INBOX = inbox(config())
SKILLS, PROJECTS = os.path.realpath(SKILLS), os.path.realpath(PROJECTS)  # resolve symlinked homes
MEM_RE = re.compile(re.escape(PROJECTS) + r"/[^/]+/memory/[^/]+\.md$")
SECRET = re.compile(r"(sk-[A-Za-z0-9_\-]{20,}|eyJ[A-Za-z0-9_\-]{20,}\.|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|xox[abp]-[A-Za-z0-9\-]{10,}|(?i:password|passwd|secret|api[_-]?key|token)\s*[:=]\s*\S{8,})")
MAX_ACTIONS, MAX_BYTES = 6, 30 * 1024
DRY = "--dry-run" in sys.argv
log_lines = []

def log(s): log_lines.append(s); print(s)

def allowed(path):
    p = os.path.expanduser(path)
    rp = os.path.realpath(p)
    if not rp.endswith(".md") or os.path.islink(p): return None
    if rp.startswith(SKILLS + "/") and len(rp[len(SKILLS) + 1:].split("/")) >= 2: return rp
    if MEM_RE.match(rp) and os.path.basename(rp) != "MEMORY.md": return rp
    return None

def frontmatter_ok(rp, content):
    if os.path.basename(rp) != "SKILL.md": return True
    m = re.match(r"---\nname:\s*(\S+)\ndescription:\s*(.+?)\n(?:.*\n)*?---\n", content)
    return bool(m) and m.group(1) == rp.split("/")[-2]

def backup(rp):
    if os.path.exists(rp):
        dst = f"{INBOX}/backups/{time.strftime('%Y%m%d-%H%M%S')}" + rp.replace(H, "")
        os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy2(rp, dst)

def apply_one(a, memdir):
    op, path, content, index_line = a.get("op"), a.get("path", ""), a.get("content", ""), None
    if op == "add_memory":
        name, desc, typ = a["name"], a["description"], a.get("type", "project")
        if typ not in ("user", "feedback", "reference", "project"): return "bad memory type"
        path = f"{memdir}/{typ}_{re.sub(r'[^a-z0-9_]', '_', name.lower())}.md"
        content = f"---\nname: {name}\ndescription: {desc}\nmetadata:\n  type: {typ}\n---\n\n{a['body']}\n"
        op = "write_file"
    rp = allowed(path)
    if not rp: return f"path not allowed: {path}"
    if op not in ("write_file", "append_file"): return f"unknown op {op}"
    if len(content.encode()) > MAX_BYTES: return "content too large"
    if SECRET.search(content): return "looks like a secret; refused"
    old = open(rp).read() if os.path.exists(rp) else None
    if old is None and MEM_RE.match(rp):  # new memory file: derive its index line from frontmatter
        fmm = re.match(r"---\n(.*?)\n---", content, re.S)
        nm = re.search(r"^name:\s*(.+)$", fmm.group(1), re.M) if fmm else None
        ds = re.search(r"^description:\s*(.+)$", fmm.group(1), re.M) if fmm else None
        if not (nm and ds): return "new memory file needs name+description frontmatter"
        index_line = f"- [{nm.group(1).strip()}]({os.path.basename(rp)}) — {ds.group(1).strip().strip(chr(34))[:110]}\n"
    new = content if (op == "write_file" or old is None) else old.rstrip("\n") + "\n\n" + content.strip("\n") + "\n"
    if old is not None and op == "write_file":
        if new == old: return "no change"
        if len(new) < 0.7 * len(old): return "would shrink file below 70%; refused"
    if not frontmatter_ok(rp, new): return "SKILL.md frontmatter invalid (name must match its directory, description required)"
    if DRY: return f"OK (dry-run) {op} {rp} ({len(new)} bytes)"
    backup(rp); os.makedirs(os.path.dirname(rp), exist_ok=True); open(rp, "w").write(new)
    if index_line:
        idx = f"{os.path.dirname(rp)}/MEMORY.md"
        if not os.path.exists(idx) or index_line not in open(idx).read(): open(idx, "a").write(index_line)
    return f"APPLIED {op} {rp}"

def main():
    data = json.load(open(sys.argv[1]))
    memdir = os.path.expanduser(data.get("memory_dir", ""))
    log(f"== {time.strftime('%F %T')} {os.path.basename(sys.argv[1])}: {data.get('summary', '')[:200]}")
    for i, a in enumerate(data.get("actions", [])[:MAX_ACTIONS]):
        try: res = apply_one(a, memdir)
        except Exception as e: res = f"error {e!r}"
        log(f"  [{i}] {res} | why: {a.get('reason', '')[:140]} | evidence: {str(a.get('evidence', ''))[:140]}")
    for d in data.get("dropped", [])[:10]: log(f"  dropped: {d}")
    if not DRY:
        os.makedirs(INBOX, exist_ok=True); open(f"{INBOX}/applied.log", "a").write("\n".join(log_lines) + "\n")

main()
