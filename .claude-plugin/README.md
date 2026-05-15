# `.claude-plugin/` — Claude Code Plugin packaging (stub)

This directory holds the Claude Code Plugin manifest so that, once the
asset layout is reorganized, `rockie-claude` can be installed via:

```
/plugin marketplace add https://github.com/saml212/rockie-claude
/plugin install rockie-claude
```

## Current status: stub only

`plugin.json` declares the plugin's name, version, and description. It
does **not** yet wire up the skills, hooks, and agents that live under
`project-harness/` and `user-harness/`.

## What's needed for a full plugin

Claude Code's plugin loader expects assets at conventional paths
relative to the plugin root:

- `skills/<name>/SKILL.md` — currently at `project-harness/skills/...`
  and `user-harness/skills/...`
- `agents/<name>.md` — currently mostly absent; `/deploy-team` agents
  live under `user-harness/teams/`
- `commands/<name>.md` — slash-command definitions
- `hooks/hooks.json` — currently split across `project-harness/hooks/`
  and `user-harness/hooks/` with shell scripts referenced from
  `settings.json`

Two viable paths forward:

1. **Symlink / mirror layout.** Keep `install.sh` as the canonical
   install path; add a small `bin/build-plugin.sh` that materializes
   the plugin layout (`skills/`, `hooks/`, etc.) by copying from the
   `*-harness/` source-of-truth dirs. Plugin users get installable
   convenience; `install.sh` users get the existing two-target install
   (project `.claude/` + user `~/.claude/`) which the plugin loader
   alone cannot reproduce.

2. **Reshape the repo.** Move `project-harness/skills/` →
   `skills/`, `project-harness/hooks/` → `hooks/`, and have
   `install.sh` derive the install set from the new layout. Cleaner
   long-term; more breaking for existing users mid-alpha.

The second option is probably correct once we hit v0.1. For now this
stub exists so:

- Search engines / agents / marketplace crawlers see we *intend* to
  publish a plugin.
- The JSON Schema reference makes the manifest self-validating once
  it gets fleshed out.

Tracked in `docs/_meta/ROADMAP.md` (add an entry there when wiring
this up for real).
