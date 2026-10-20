#!/usr/bin/env python3
"""Coverage scan for knowledge-harvest. Read-only except TK_HOME/last-harvest.json (--mark).

Lists auto-memory entries (~/.claude/projects/*/memory/*.md) grouped by topic, which user skill
(if any) names each one, and entries/transcripts changed since the last harvest. Output is a
worklist for the model to curate; it makes no judgement about what is worth a skill.
"""
import glob, json, os, re, sys, time
from tk import H, TK_HOME, SKILLS, PROJECTS
STATE = f"{TK_HOME}/last-harvest.json"

def fm(path):
    t = open(path, errors="ignore").read()
    m = re.match(r"---\n(.*?)\n---\n", t, re.S)
    d = {}
    if m:
        for line in m.group(1).splitlines():
            k, _, v = line.partition(":")
            if v and not line.startswith(" "): d[k.strip()] = v.strip().strip('"')
    return d

def topic(fname):
    base = re.sub(r"^(project|feedback|reference|user)_", "", fname[:-3])
    return re.split(r"[_\-]", base)[0]

def main():
    last = json.load(open(STATE)).get("ts", 0) if os.path.exists(STATE) else 0
    if "--mark" in sys.argv:
        os.makedirs(TK_HOME, exist_ok=True); json.dump({"ts": int(time.time())}, open(STATE, "w")); return print("marked", time.ctime())
    corpus = {}
    for p in glob.glob(f"{SKILLS}/*/SKILL.md") + glob.glob(f"{SKILLS}/*/*/*.md"):
        sk = p[len(SKILLS) + 1:].split("/")[0]
        corpus[sk] = corpus.get(sk, "") + open(p, errors="ignore").read().lower() + "\n"
    rows = []
    for p in sorted(glob.glob(f"{PROJECTS}/*/memory/*.md")):
        f = os.path.basename(p)
        if f == "MEMORY.md": continue
        d = fm(p); slug = d.get("name", f[:-3]).lower()
        namew = [w for w in re.split(r"[-_ ]", slug) if len(w) > 2]
        hits = {}
        for sk, txt in corpus.items():
            if slug in txt or f[:-3].lower() in txt: hits[sk] = 99
            elif len(namew) >= 2 and all(w in txt for w in namew): hits[sk] = 1
        rows.append(dict(file=f, mtime=os.path.getmtime(p), desc=d.get("description", "")[:110],
                         covered_by=[k + ("" if hits[k] == 99 else "?") for k in sorted(hits, key=hits.get, reverse=True)[:2]]))
    new = [r for r in rows if r["mtime"] > last]
    unc = [r for r in rows if not any(not c.endswith("?") for c in r["covered_by"]) and not r["file"].startswith("feedback_")]
    print(f"# memory entries: {len(rows)} | changed since last harvest: {len(new)} | not named by any skill (project/reference): {len(unc)}")
    print(f"# last harvest: {time.ctime(last) if last else 'never'}\n## Uncovered, grouped by topic (biggest first)")
    groups = {}
    for r in unc: groups.setdefault(topic(r["file"]), []).append(r)
    for t, rs in sorted(groups.items(), key=lambda x: -len(x[1])):
        print(f"\n### {t} ({len(rs)})")
        for r in rs: print(f"- {r['file']}: {r['desc']}")
    print("\n## Changed since last harvest (any coverage)")
    for r in sorted(new, key=lambda r: -r["mtime"])[:40]:
        print(f"- {r['file']} [{','.join(r['covered_by']) or 'uncovered'}] {time.strftime('%m-%d', time.localtime(r['mtime']))}")
    tr = [(os.path.getsize(p), p) for p in glob.glob(f"{PROJECTS}/*/*.jsonl") if os.path.getmtime(p) > last]
    print(f"\n## Transcripts changed since last harvest: {len(tr)} (largest 15)")
    for sz, p in sorted(tr, reverse=True)[:15]: print(f"- {sz//1024}KB {p[len(PROJECTS)+1:]}")

main()
