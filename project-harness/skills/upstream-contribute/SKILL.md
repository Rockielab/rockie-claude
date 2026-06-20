---
name: upstream-contribute
description: Scan the current session for harness-level patterns that would be useful to other rockie users, then either package a reviewed local harness patch or dispatch a public upstream contribution PR. Uses Scout/Generator/Verifier/Updater separation, never auto-merges, and requires human sign-off before pushing. Triggers when the user says "upstream this", "contribute back", "propose a harness change", "write a PR for rockie", or after `/clean` emits its post-audit nudge.
scope: community
attribution:
  schema_version: 1
  authors:
    - rockie_username: "amara-singh"
      display_name: "Amara Singh"
      profile_refs: ["platform-skills:amara-singh"]
  maintainers:
    - rockie_username: "amara-singh"
      display_name: "Amara Singh"
      profile_refs: ["platform-skills:amara-singh"]
  profiles:
    platform-skills:amara-singh:
      provider: "platform-skills"
      url: "https://github.com/Rockielab/platform-skills/tree/main/skills/upstream-contribute"
      verified: false
  source:
    repo: "Rockielab/platform-skills"
    path: "skills/upstream-contribute/SKILL.md"
    version: "2026-05-14"
    url: "https://github.com/Rockielab/platform-skills/tree/main/skills/upstream-contribute"
  contact_policy:
    maintainer_contact: "profile_public_only"
    contribution_channel: "product_proposals"
  completeness: "complete"
---

# /upstream-contribute — meta-loop: rockie users improve rockie

`/upstream-contribute` covers two contribution modes:

- **Local harness patch** — package an improvement against the user's
  own local rockie clone as a reviewed patch proposal.
- **Public upstream PR** — generalize the pattern and dispatch a PR
  against `Rockielab/rockie-claude` so the next release ships it to
  everyone.

This is the meta-loop. Researchers using rockie-claude in their own
work uncover patterns that generalize — a tighter `[DEAD-END]` query,
a hook that catches a stuck-detector edge case, a skill that helps
across disciplines. The skill captures one of those, generalizes it,
and opens a reviewable PR. The maintainers merge; the next user
benefits.

## When to run

- The user says "upstream this", "contribute back", "anything
  generalizable here", "open-source this", "propose a harness change",
  or "write a PR for rockie".
- `/clean` finishes an audit and emits the post-audit nudge (see
  `clean/SKILL.md` → "Post-audit hook").
- A `[LEARN harness-upstream]` or `[LEARN cross-discipline]` block was
  written this session and the user wants to act on it.

Run **at most once** per session, near the end. Don't dispatch the
writer sub-agent during active work — the user wants to review the
candidates before any forking happens.

## Method

The skill uses **Scout / Generator / Verifier / Updater** separation.
The proposing agent never verifies and commits its own change.

### 1. Scout (this skill, in-session)

Read recent context to identify candidates:

```bash
# [LEARN] rows added this session
sqlite3 ${OPENCLAW_WORKSPACE_DIR}/memory/workflow.db "
  SELECT category, rule, mistake, correction
  FROM learnings
  WHERE created_at >= datetime('now','-6 hours')
  ORDER BY created_at DESC
"

# Files changed in the last N commits
git log --since='6 hours ago' --name-only --pretty=format:'%h %s'

# Any new skill / hook / script files
git diff --name-only HEAD~5..HEAD -- '${OPENCLAW_SKILLS_DIR}/' '${OPENCLAW_WORKSPACE_DIR}/hooks/' '${OPENCLAW_WORKSPACE_DIR}/scripts/' \
  | grep -E '\.(md|sh|py)$' || true
```

For each candidate, score (yes/no/no — keep only "yes"):

| Question | Why it matters |
|---|---|
| Would this help another rockie user across a different research domain? | Cross-discipline generalizability is the bar for upstream. |
| Is the pattern small and self-contained (one file, one function, one rule)? | Big architectural changes need an explicit local patch proposal first. |
| Can it be described without naming any internal project, person, or dataset? | Leak-protection. |
| Does it survive without `(your-project)`-specific configuration? | If it doesn't, it's a fork patch, not an upstream patch. |

Drop anything that fails any of the four. Then surface the survivors
to the user with one sentence each:

> Found 3 candidates. Take any of them upstream?
> 1. `[LEARN]` row "fts5: strip hyphens from MATCH" → would generalize as a fix in `load-relevant-rules.sh`.
> 2. New script `scripts/queue_audit.py` → would generalize as a small helper around the queue runtime.
> 3. Tighter `[DEAD-END]` query in `load-relevant-deadends.sh` → would generalize as a hook fix.
>
> Reply with the numbers (e.g. "1, 3") to dispatch.

### 2. Strip project-specific specificity

For each chosen candidate, the skill **rewrites** before sending to
the writer sub-agent. Examples:

- "in our matrix-token research we found X" → "for any iterative ML
  reasoning research, we found X"
- "we noticed in the Pebble run that Y" → "we noticed during a
  multi-day autonomous run that Y" (and never mention the
  project name)
- "this fixed the hang we had during the Tuesday kickoff" → "this
  fixes a hang that occurs when the queue is empty at start"

Concrete project names, dataset names, internal repo paths, and
collaborator names get stripped. The agent does NOT proceed if it
can't generalize the change — it returns the candidate to the user
with "this looks too project-specific to upstream cleanly."

### 3. Choose mode

Ask the user which mode to run:

- `local patch` for a private proposal against their own local rockie
  clone.
- `public upstream` for a fork/branch/PR against `Rockielab/rockie-claude`.

Default to `local patch` when the candidate is risky, touches schema or
hooks, or the user has not explicitly asked to publish.

### 4A. Local patch mode — Generator / Verifier / Updater

The Generator:

- Writes the diff against a LOCAL CLONE of the rockie source repo.
- Writes a short rationale: what pattern broke, why the fix composes
  with existing differentiators, what smoke-test assertion proves it.
- Never commits directly. Produces
  `~/rockie-proposals/<YYYY-MM-DD-slug>/patch.diff`, `rationale.md`,
  and `test.sh`.

The Verifier is fresh-context and reads the patch, rationale, files
touched, and `CONTRIBUTING.md`. It must answer:

1. Does this compose with existing differentiators, or duplicate one?
2. Does the smoke test actually test the claimed improvement?
3. Is the change local, or does it ripple across schema?
4. Is there path-traversal, SQL-injection, or shell-injection risk?

The Updater is the human. They review the verifier report and diff,
run the smoke test, then choose whether to apply, commit, or push.

### 4B. Public upstream mode — writer sub-agent

Use the `Agent` tool with NO prior session context. Pass:

- The generalized change description (text)
- The list of files to touch (paths only)
- `target_repo=Rockielab/rockie-claude`
- `branch=contrib/<short-slug>`

The Generator must:

1. `gh repo fork Rockielab/rockie-claude --clone --remote` (if not
   already forked).
2. `cd rockie-claude && git checkout -b contrib/<slug>`.
3. Apply the change. Each file edit must compose with existing
   differentiators (taste corpus, modes, pre-run audit, `[LEARN]`
   DB, waterfall, journal tree, experiment-runs/, `/deploy-team`,
   pre-commit sentinel). Duplicates of existing capability get
   rejected by the maintainers and waste review cycles — abort if
   the change would duplicate.
4. Run `bash tests/smoke-test.sh`. Must be green.
5. `git add -p` (deliberate hunks only; never `git add -A`).
6. Commit with Conventional Commit prefix (`feat:`, `fix:`, `docs:`,
   `chore:`, `port:`). Sign-off if upstream `CONTRIBUTING.md`
   requires it.
7. Draft the PR body with the template below and report the branch,
   commit SHA, smoke-test result, and exact push/PR commands.
8. Stop. Do not push or open the PR unless the user explicitly confirms
   public publishing in this invocation. After that confirmation only,
   run `git push -u origin contrib/<slug>` and `gh pr create` with the
   reviewed body.

### 5. Verify (fresh-context audit, optional)

For changes touching hooks, schema, or anything that runs on every
prompt — dispatch a fresh-context Verifier to read the diff and the
four verifier questions BEFORE the PR is opened. Store the verdict in
the PR body. For docs-only or one-skill changes, skip this; the
maintainers' PR review is enough.

### 6. Updater (the human, asynchronous)

The user reviews the body, runs the smoke test locally if they want
extra confidence, and explicitly chooses whether to publish. If they
approve publication, the PR sits open for maintainer review and merge.
The skill is done once the draft publish commands or PR URL are
reported back.

## PR body template

```markdown
## What

<one-line description of the generalized change>

## Why this is generalizable

<2-3 sentences explaining how this helps users across research
domains, not just one project>

## What this isn't

<1-2 sentences explicitly noting what this PR deliberately does NOT
do — scope discipline, so the maintainers don't have to ask>

## Smoke-test status

`bash tests/smoke-test.sh` → 75+ assertions, all green
(local run on <date>; CI will re-run on push).

## Composition with existing differentiators

<one sentence per relevant pillar — taste corpus / adversarial
gauntlets / cheap autonomy / honesty — confirming this composes
rather than duplicates>

## Acknowledgements

This pattern was uncovered by an external rockie-claude user during
their own research work. They asked for upstreaming via
`/upstream-contribute`. Crediting the contributor by GitHub handle
(if they opted in): @<handle>.
```

The user's GitHub handle is included **only** if they explicitly
opt in during the scout step. Default is no attribution — leak
protection.

## What qualifies as upstream-worthy

Same safety bar as local patch mode, plus a stronger generalizability
filter:

**Yes:**
- Bug fixes in hooks/scripts that affect any user (regardless of
  domain).
- New smoke-test assertions catching general-purpose regressions.
- New skill that's useful across disciplines (e.g. a portable continuity-note helper
  works for any research project; `/matrix-decomposition-helper`
  doesn't).
- Memory-schema upgrades with migrations (`memory/migrations/NNN_*.sql`).
- Cross-discipline-useful capabilities (e.g. an FTS5 retrieval
  tweak; a new `[DEAD-END]` matcher).
- README / docs improvements that clarify install or usage.

**No:**
- Domain-specific changes (ML-preset rules that don't generalize
  beyond ML, NLP-specific patterns that don't help other research,
  etc.). Keep these in the user's own fork.
- Anything depending on private config or internal infra.
- Reformatting / "nice to have" cosmetic changes without a clear win.
- Schema changes without a migration file.
- Anything that would require the user to reveal internal project
  context to make sense.

## Refusal paths

The skill must REFUSE to dispatch a Generator if:

- The candidate change can't be generalized without leaking project
  context. (Surface the candidate back to the user with a "looks
  project-specific" note; they can rewrite manually.)
- The change touches `memory/schema.sql` without a companion migration.
- The change modifies the Verifier's own definition or this skill's
  own SKILL.md (canonical self-improvement footgun — those go through
  ordinary maintainer review, not via the skill).
- The change adds a network dependency that isn't already in
  upstream `NOTICE`.
- `bash tests/smoke-test.sh` fails on the writer sub-agent's branch.
- The user hasn't reviewed and approved at least one candidate.

## Composition with other skills

- **`/clean`** — emits the post-audit nudge that surfaces this skill.
  Runs after the audit sentinel is written; never blocks the commit.
- **local patch mode** — for changes scoped at the user's own local
  rockie clone. If the user wants the change in their fork first (and
  only later upstream), use that mode instead of public upstream mode.
- **`/post-run-review`** — populates `[LEARN]` rows that this skill
  will scan for candidates.
- **autopilot** — autopilot writes `[LEARN]` blocks during long runs;
  those become candidates here.

## Open questions (roadmap)

- Public publishing is intentionally gated behind an explicit user
  confirmation. After 10+ real proposals, revisit whether draft PR
  creation can be safely automated while still preserving leak review.
- The Verifier panel is single-agent today. A bias-probe panel (two
  Verifiers with opposite priors + a meta-Verifier) is future work.
- A "draft PR" mode that opens the PR with `--draft` and lets the
  user re-edit the body before un-drafting is on the roadmap.
