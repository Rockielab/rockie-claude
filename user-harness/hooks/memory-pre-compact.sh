#!/usr/bin/env bash
# PreCompact hook — runs BEFORE Claude Code compacts the session, extracting
# any unsaved [LEARN] blocks from the transcript so they survive compaction.
#
# The per-turn Stop hook (learn-capture.sh) catches most [LEARN] blocks as
# the session runs. This sweep is a backstop: if the Stop hook missed one
# (e.g., a transient error), the full-session scan here picks it up before
# the transcript summary replaces the raw blocks.
#
# Receives JSON on stdin with `transcript_path`.

set -u

INPUT="$(cat)"
command -v jq >/dev/null 2>&1 || exit 0

TRANSCRIPT="$(echo "$INPUT" | jq -r '.transcript_path // empty' 2>/dev/null)"
SESSION_ID="$(echo "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"

if [ -z "$TRANSCRIPT" ] || [ ! -f "$TRANSCRIPT" ]; then
  exit 0
fi

python3 "$HOME/.claude/scripts/memory/extract-from-transcript.py" \
  "$TRANSCRIPT" \
  ${SESSION_ID:+--session-id "$SESSION_ID"} \
  ${REPO_ROOT:+--repo "$REPO_ROOT"} \
  2>&1 | sed 's/^/  /' || true

exit 0
