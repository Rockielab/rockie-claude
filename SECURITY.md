# Security policy

## Scope

idastone is a local-first harness. It does not listen on a network, does
not handle user auth, and has no server component. Its threat model is
therefore narrow: adversarial LLM output, malicious contributor PRs, and
compromised third-party services (ntfy.sh).

## Reporting a vulnerability

Please email security reports privately before filing a public issue:

    samlarson16 [at] gmail.com

Include:

- affected file(s) + line range
- concrete reproducer (ideally a shell snippet against a `mktemp` dir)
- impact assessment (file read / file write / code execution / info disclosure)

Expect acknowledgement within 72 hours. Fixes are prioritized over
disclosure timelines.

## Known risk surfaces (documented for transparency)

- **`[LEARN]` / `[DEAD-END]` capture** — any text the assistant emits
  can land in the FTS5 DB. Memory-poisoning attacks (MINJA, arXiv
  2601.05504; eTAMP, arXiv 2604.02623) are a real concern. Inserts are
  parameterized, so SQL injection is not a vector, but adversarial
  content in the rule text CAN influence future agent prompts. Users
  running untrusted subagents should review `.claude/memory/workflow.db`
  before trusting auto-injected rules.
- **ntfy.sh** — if the public server is compromised, response bodies
  reaching `ntfy_poll_responses.sh` can contain attacker-controlled
  strings. The poller does not shell-expand those strings and DB
  writes are parameterized, but downstream prompt layers should treat
  ntfy content as untrusted.
- **`/deploy-team` worktrees** — each agent writes to its own worktree;
  nothing prevents an agent from writing to paths outside the worktree
  via `Write`/`Edit` if Claude Code's sandbox doesn't restrict it.
  Project configuration should use Claude Code's permission system.
- **`apply_patch.py`** — now refuses absolute paths and `..` escapes
  after audit C-1 (2026-04-23). Any bypass of this containment is a
  CRITICAL issue — please report.
- **`autopilot.conf`** — parsed with an allow-listed key=value reader
  (not shell-sourced) after audit C-2. Any regression to dot-sourcing
  is CRITICAL.

## What we don't currently defend against

- A compromised Claude Code itself (out of scope).
- Local root or someone with write access to `~/.claude/`.
- Physical access.
- Resource-exhaustion via a flood of `[LEARN]` blocks (rate-limiting is
  roadmap, not shipped).

## Hardening checklist for production use

- Pin `NTFY_TOPIC` to a non-guessable value (`openssl rand -hex 16`).
- Set `.claude/budget.toml` ceilings before running autopilot.
- Register dry-run sentinels only after an actual forward+backward
  smoke test passes — never as a convenience.
- Don't commit `.claude/autopilot.conf` to a public repo (gitignored
  by default; do not un-ignore).
- Periodically `repair_fts.sh` if you see empty search results.
