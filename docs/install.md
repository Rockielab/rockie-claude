# Install

## Prerequisites

- macOS or Linux (bash, Python 3.9+, `/usr/bin/sqlite3` with FTS5)
- [Claude Code](https://claude.com/claude-code) CLI installed
- Git
- Node 20+ (only if using the `/deploy-team` Node orchestrator — the
  Python orchestrator is always available and has no Node dep)

Check:

```bash
/usr/bin/sqlite3 --version    # must be present (PATH sqlite3 sometimes lacks FTS5)
# Real FTS5 test — try to create a virtual FTS5 table. Succeeds only if
# the build has FTS5 compiled in.
/usr/bin/sqlite3 :memory: "CREATE VIRTUAL TABLE t USING fts5(x)" && echo "FTS5 ok"
python3 --version             # 3.9+
```

## Quick install

```bash
git clone https://github.com/saml212/rockie.git
cd rockie
./install.sh
```

The installer is idempotent and interactive. It asks before overwriting
anything that already exists in your target `<project>/.claude/` or
`~/.claude/`. Re-running it updates the harness without touching your
`workflow.db`.

## Manual install

If you want to understand what the installer does, or do it a piece at
a time:

### 1. Project-local harness (into `<your-project>/.claude/`)

```bash
cd /path/to/your/project
mkdir -p .claude
cp -a /path/to/rockie/project-harness/. .claude/
```

This gives you `hooks/`, `scripts/`, `skills/`, `memory/schema.sql`,
`settings.json`.

### 2. Initialize the learnings DB

```bash
bash .claude/scripts/init_db.sh            # creates workflow.db from schema
python3 .claude/scripts/seed_hard_rules.py # seeds generic harness rules
```

### 3. User-global harness (into `~/.claude/`)

```bash
mkdir -p ~/.claude/{hooks,skills,scripts,teams}
cp /path/to/rockie/user-harness/hooks/*.sh ~/.claude/hooks/
cp -a /path/to/rockie/user-harness/scripts/memory ~/.claude/scripts/
cp -a /path/to/rockie/user-harness/skills/deploy-team ~/.claude/skills/
cp -a /path/to/rockie/user-harness/teams/. ~/.claude/teams/
```

Then merge the hooks block from `user-harness/settings.json` into your
existing `~/.claude/settings.json`. The installer does this automatically
via its own Python merge helper (dedupes by command string, so re-install
is idempotent). Manual merge can use `jq -s 'reduce .[] as $x ({}; . * $x)'`
for simple cases.

### 4. (Optional) `/deploy-team` Node orchestrator

```bash
cd ~/.claude/teams/orchestrator
npm install
```

### 5. Drop a CLAUDE.md

```bash
cp /path/to/rockie/claude-md/CLAUDE.md.template /path/to/your/project/CLAUDE.md
# or for ML research:
# cp /path/to/rockie/claude-md/ml-research.md /path/to/your/project/CLAUDE.md
```

Edit the `Project` section for your specifics.

### 6. (Optional) ntfy

See [ntfy-setup.md](ntfy-setup.md).

## Verification

Start a new Claude Code session in your project. On `SessionStart` the
user-global memory hook should run and print something like:

```
✓ surface: wrote 0 memories to <project>/.claude/memory/rules-compiled.md
```

Submit any prompt. The `UserPromptSubmit` hooks should fire. Check:

```bash
tail -5 .claude/memory/hook.log
```

You should see `load-relevant-rules: fired` and `correction-detect: fired`.

Write a `[LEARN]` block in Claude's response to yourself, then `/exit`
or end the turn. Check:

```bash
/usr/bin/sqlite3 .claude/memory/workflow.db "SELECT category, rule FROM learnings ORDER BY id DESC LIMIT 5"
```

Your new learning should be at the top.

## Uninstall

```bash
rm -rf <your-project>/.claude     # or just remove the rockie-specific pieces
rm -rf ~/.claude/teams            # only if you used the Node orchestrator
# Edit ~/.claude/settings.json to remove the rockie hook entries.
```

Nothing persists outside those paths.
