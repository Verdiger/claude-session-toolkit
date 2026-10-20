"""Shared config/paths for the toolkit's Python scripts."""
import json, os, shutil
H = os.path.expanduser("~")
TK_HOME = os.environ.get("CLAUDE_SESSION_TOOLKIT_HOME", f"{H}/.claude/session-toolkit")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = f"{H}/.claude/skills"
PROJECTS = f"{H}/.claude/projects"

def config():
    os.makedirs(TK_HOME, exist_ok=True)
    p = f"{TK_HOME}/config.json"
    if not os.path.exists(p): shutil.copy(f"{ROOT}/config.default.json", p)
    return json.load(open(p))

def claude_bin():
    return shutil.which("claude") or f"{H}/.local/bin/claude"

def inbox(cfg):
    return os.path.expanduser(cfg["harvest"]["inbox_dir"])
