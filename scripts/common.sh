# Shared helpers (sourced). State, config and usage snapshots live in $TK_HOME.
TK_HOME="${CLAUDE_SESSION_TOOLKIT_HOME:-$HOME/.claude/session-toolkit}"
TK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$TK_HOME"
[ -f "$TK_HOME/config.json" ] || cp "$TK_ROOT/config.default.json" "$TK_HOME/config.json"
cfg() { jq -r "$1" "$TK_HOME/config.json"; }
claude_bin() { command -v claude 2>/dev/null || echo "$HOME/.local/bin/claude"; }
