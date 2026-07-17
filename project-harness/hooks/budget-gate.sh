#!/usr/bin/env bash
# PreToolUse hook: abort the session when any configured budget ceiling
# is crossed. Reads .claude/budget.toml; consults .claude/memory/workflow.db
# for cumulative usage (see scripts/budget.py for the model).
#
# The hook runs on every tool call, so it's on the hot path — keep it cheap.
# We only call the Python CLI (which touches SQLite) and exit on its return
# code. All file reads + SQLite queries complete in <5ms typical.
set +e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CFG="$ROOT/budget.toml"

# Fast path: no budget.toml means no ceilings, skip.
[ ! -f "$CFG" ] && exit 0

bash "$ROOT/scripts/rotate_hook_log.sh" 2>/dev/null

# Tool call is always one tool call :)
INPUT=$(cat)

# Extract session id + update tool_calls metric first (so 'check' sees it).
SESSION_ID=$(echo "$INPUT" | python3 -c 'import sys,json
try: print(json.load(sys.stdin).get("session_id",""))
except: print("")' 2>/dev/null)
export CLAUDE_SESSION_ID="${SESSION_ID:-cli}"

python3 "$ROOT/scripts/budget.py" add tool_calls 1 >/dev/null 2>&1

# Check all configured ceilings.
python3 "$ROOT/scripts/budget.py" check
CHECK_EXIT=$?

# Fail CLOSED: block on ANY non-zero exit, not just the documented
# "ceiling crossed" code 2. budget.py previously crashed with
# ModuleNotFoundError on Python <3.11 without tomli (system python3 on
# stock macOS), exiting 1 — and this hook only blocked on exit==2, so a
# broken budget.py made the gate fall through to `exit 0` and silently
# allow every tool call, ceilings included. A budget check we can't run
# is not the same as a budget check that passed.
if [ "$CHECK_EXIT" -ne 0 ]; then
  echo "[$(date -Iseconds)] budget-gate: BLOCKED — ceiling crossed or budget.py failed (exit $CHECK_EXIT)" >> "$ROOT/memory/hook.log"
  # Exit 2 tells Claude Code to block the tool call.
  exit 2
fi

exit 0
