# Changelog

All notable changes to idastone are tracked here. Versions follow
[SemVer](https://semver.org/) once a `v0.1` is tagged; until then every
commit on `main` is considered alpha.

## [Unreleased] — post-audit hardening (2026-04-24)

### Security
- `apply_patch.py` now refuses absolute paths and `..` escapes
  (audit C-1).
- `autopilot.conf` is no longer shell-sourced; replaced with an
  allow-listed `key=value` parser that rejects `$(…)` and backticks.
  Added to `.gitignore` so it never lands in public repos (audit C-2).
- `pre-train-gate.sh` regex broadened to catch `python3.11`, `python3.12`,
  etc.; `#`-shell-comments are stripped before the arm-check and the
  smoke-exception, so `python3 train.py # --smoke` no longer bypasses
  the gate (audit M-2).
- `budget.py` rejects empty `CLAUDE_SESSION_ID` (audit M-1) — can no
  longer be silently bypassed.
- `queue.py release` requires `claimed_by = current session` (or
  `--force`) so one session can't un-claim another's work (audit m-2).

### Fixed
- Installer refuses to install idastone into its own clone.
- `YOUR-ORG` placeholder replaced with `saml212` across all docs.
- "cascade" (old codename) renamed to idastone in Node orchestrator
  package + lockfile + migration helper.
- README claim "5 loop types" corrected to 4 — `condensation-loop` is
  OpenHands-specific and not ported.
- `examples/launch_experiment.example.sh` now exists (autopilot.conf.example
  had referenced a missing file).
- `init_db.sh` corruption probe no longer wipes the WAL of an active
  writer (audit F9).
- Gate scope check inverted: `pre-commit-gate` and `pre-train-gate`
  now enforce only when `TARGET_REPO == OWN_REPO`, not when empty
  (audit F2).
- `autopilot_loop.sh` uses real `flock` instead of `touch` for the
  run lock (audit F6), preventing race-start of two autopilots.

### Added
- Schema versioning via `PRAGMA user_version` + `memory/migrations/`
  directory. `init_db.sh` applies numbered migrations in order (audit F4).
- `queue.py reap` reapplies zombie `claimed` rows older than N hours
  to `pending`. `autopilot_loop.sh` calls it at startup (audit F5).
- `repair_fts.sh` rebuilds the FTS5 virtual tables (audit F10).
- `install.sh` stamps a UUID into `.claude/project_id` on first
  install so two checkouts of the same repo don't collide (audit F12).
- `SECURITY.md`, `CHANGELOG.md` (this file), issue + PR templates.

## [0.0.1] — initial public scaffold (2026-04-23)

- First 50 commits shipping README, LICENSE (Apache-2.0), NOTICE,
  docs, CLAUDE.md templates, schema, hooks, scripts, skills,
  installer, 47-assertion smoke test, and CI.
- Ports shipped: A1 (dead-end registry), A2 (hypothesis calibration),
  A3 (stuck detector — 4 loop types), A5 (stage-gated CLAUDE.md),
  A6 (convergence token), A7 (SEARCH/REPLACE patch), B1 (experiments
  journal tree), B3 (post-run review skill), B4 (budget controller),
  C4 (failure classification), plus the experiment queue, ZCM,
  autopilot loop, dry-run gate, and scheduled-notes skill.
