# rockie-claude

**An autonomous AI research harness for Claude Code.**

Inspired by Project Hail Mary's Rocky — the alien research partner you
couldn't have built the answer without.

> **Looking for the Codex CLI version?** See
> [`saml212/rockie-codex`](https://github.com/saml212/rockie-codex).
> Same patterns (`[LEARN]`, taste corpus, autopilot, gauntlets) ported
> to OpenAI Codex CLI's runtime.

---

## What rockie-claude does for you

Four jobs, run continuously, until you tell it to stop:

### 1. Captures your research taste — and iterates on it

A 5-minute first-run interview compiles your worldview, methodology,
dismissals, and voice into a durable `.rockie/taste/` corpus. Every
future session loads it automatically. Your agent knows what *you*
think a good result looks like, what dead ends you've sworn off, and
what register you want it to write in. Refresh anytime with
`/onboard --section <name>`. Voice-first deep mode for laddering.

### 2. Bulletproofs every step with adversarial subagent networks

Plan → Research → Build → Audit → Run → Assess → Codify. Each step has
adversarial review built in:

- **`/deploy-team`** — gauntlets (brainstorm / research / attack / validate),
  pre-launch audits, post-run analysis. A team of agents fight over
  every important call.
- **`/clean`** — pre-commit anti-slop audit gates `git commit` until
  debug artifacts and stale claims are gone.
- **`/propose-harness-change`** — Generator / Verifier / Updater split.
  The agent never auto-pushes.
- **stuck-detector + hypothesis calibration + dead-end registry** —
  background services that nudge the agent when it's spinning, when
  its priors are drifting, when it's about to re-propose a dead idea.

### 3. Cheap, resource-efficient autonomy — indefinitely

- **Local-first.** SQLite + FTS5 `[LEARN]` memory. No vector DB. No
  service except Claude itself.
- **Claude Max friendly.** Tokens/wallclock/tool-calls auto-tracked
  but uncapped (they cost nothing). Only GPU dollars get enforced
  ceilings.
- **Spot-first GPU policy.** Min-bid defaults. Provider-hop on
  preemption (RunPod / Vast / Prime / Verda) before ever bumping a
  bid. On-demand last resort, gated.
- **Modes** — `/mode switch paper-crunch` for deadline-locked
  scope-lock + Opus-on-attack; `/mode switch exploratory` for broad
  reading + sonnet-first speed; build your own. Swap operational
  policy without changing your identity.

### 4. Stays honest

- Catches bugs *before* you burn GPU time (separate auditor agent
  reads shapes/gradients/stability pre-launch).
- Notices when it's stuck (4 semantic-loop types, periods 2/3/4).
- Tracks whether predictions were right (`predicted_delta` vs
  `actual_delta` per experiment).
- Classifies every failure: `bug | bad-hyperparam | bad-hypothesis`.
  Routes `[LEARN]` and `[DEAD-END]` accordingly.

> Status: **alpha / pre-launch.** Running in production on an 8×H100
> autonomous research project. This repo packages it for the
> community. Breaking changes until `v0.1`.

---

## What you and your agent will go through

A chronological walkthrough of the first week. Each phase below is
what actually happens; the rest of this README explains the machinery.

**Hour 0 — Install + onboard.** Run `./install.sh ~/your-research-project`.
Open Claude Code in that project; the SessionStart hook spots that no
taste corpus exists and prompts `/onboard`. Five to seven questions,
~5 minutes, voice optional. Output: a six-file taste corpus committed
to `<project>/.rockie/taste/` (SOUL, STYLE, METHODOLOGY, DISMISSALS,
MEMORY, INDEX). `INDEX.md` is auto-injected into every future session.

**Day 1 — Plan + first experiment.** You talk to Claude. Subagents
verify novelty and check for re-proposing dead ends already logged in
the registry. Before any GPU dollars are spent, the pre-launch audit
agent reads shapes, gradients, and stability of the proposed code in a
separate context. Only then does the first training run launch. Every
prediction (`predicted_delta`) is recorded alongside the hypothesis.

**Day 1+ — Continuous loop.** `/autopilot` takes over. The Zero-Cost
Monitor polls training logs without LLM calls, so a stable run costs
nothing while it churns. ntfy push notifications wake you only on
anomalies, ceiling crosses, or genuine decisions — never on routine
heartbeats. Every run produces a `[LEARN]` block on completion; the
next prompt's UserPromptSubmit hook auto-injects the top-5 relevant
rules via FTS5 BM25 search.

**Week 1+ — Iteration compounds.** Predicted-vs-actual deltas roll up
per experiment so calibration becomes visible. Failures are classified
`bug | bad-hyperparam | bad-hypothesis` and route `[LEARN]` or
`[DEAD-END]` accordingly. The dead-end registry prevents new subagents
from re-proposing what the team already ruled out. When your standards
shift, refresh the relevant slice with `/onboard --section <name>` —
identity drift gets an audit trail, not a silent overwrite.

---

## The loop

```
                  ┌─ Plan ─────────── you talk to Claude
                  │
                  ├─ Research ─────── subagents verify, check novelty
                  │
                  ├─ Build ────────── write code, clean, comment the non-obvious
                  │
                  ├─ Audit ────────── SEPARATE agent reviews shapes/gradients/stability
                  │                   (the pre-run gate nobody else has)
                  │
                  ├─ Run ──────────── execute; ntfy push on preemption / block / win
                  │
                  ├─ Assess ───────── post-run review emits {is_bug, bad-hyperparam, bad-hypothesis}
                  │
                  └─ Codify ───────── [LEARN] block → workflow.db (FTS5)
                                      next prompt auto-injects relevant rules
```

Every cycle should make the next cycle better.

---

## Install

```bash
git clone https://github.com/saml212/rockie-claude.git ~/rockie-claude
cd ~/rockie-claude
./install.sh ~/path/to/your/research-project
```

The installer:

1. Copies `project-harness/` → `<your-project>/.claude/`
2. Copies `user-harness/` → `~/.claude/`
3. Initializes `workflow.db` (FTS5 required — pinned to `/usr/bin/sqlite3`)
4. Seeds harness rules + 5 mode templates (default, paper-crunch,
   exploratory, dogfooding, learning)
5. Prints a `CLAUDE.md` template path to drop into your repo root.

**On first session:** SessionStart hook prompts you to run `/onboard`
— 5–7 questions, ~5 minutes, voice optional. Produces your taste
corpus.

**Verify the install:** `bash tests/smoke-test.sh` runs 75+ assertions
(hooks fire, FTS5 search, atomic queue claim, installer idempotency,
path-traversal refusal, budget-ceiling enforcement, autopilot
end-to-end with mock launcher, schema migrations, autopilot.conf safe
parser, GPU router with fake providers). CI runs the same on every
push. ~10 seconds, no API key.

See [docs/install.md](docs/install.md) for manual install,
[docs/quickstart.md](docs/quickstart.md) for first-session walkthrough,
[docs/ntfy-setup.md](docs/ntfy-setup.md) for push notifications
(optional).

---

## The skills you'll invoke

| Skill | What |
|---|---|
| `/onboard` | researcher-taste interview → six-file `taste/` corpus that auto-loads every session |
| `/mode` | swap operational overlays (paper-crunch / exploratory / dogfooding / learning / your own) |
| `/deploy-team` | dispatch adversarial subagent gauntlets — Python local + Node global with worktrees |
| `/clean` | pre-commit anti-slop audit + sentinel; gates `git commit` |
| `/propose-harness-change` | package an upstream-back patch with Generator/Verifier/Updater review |
| `/queue-refill` | brainstorm 3–5 new high-quality experiments when the queue runs dry |
| `/post-run-review` | structured review after every training/eval run; emits `[LEARN]` or `[DEAD-END]` |
| `/autopilot` | continuous-operation mode for days-long autonomous work |

---

## The `[LEARN]` protocol

When Claude learns something durable mid-session, it emits:

```
[LEARN] <category>: <one-line rule>
Mistake: <what went wrong>
Correction: <what the right approach is>
```

The Stop hook parses, dedupes by `(project, category, rule)`, inserts
into `.claude/memory/workflow.db`. On the next prompt, the
UserPromptSubmit hook tokenizes the prompt, runs an FTS5 BM25 search
over the learnings, and injects the top-5 relevant rules — but only
if the best match is genuinely strong (BM25 score < -4). No noise.

---

## Use it on an existing project

If you already have a research repo and just want rockie's hooks, skills,
and memory layered on top:

```bash
git clone https://github.com/saml212/rockie-claude.git ~/rockie-claude
~/rockie-claude/install.sh ~/your-research-project
```

What gets written:

- `<your-project>/.claude/` — the project-harness: hooks, skills,
  memory schema, settings.json, project_id stamp, sentinels dir.
- `~/.claude/` — the user-harness: cross-project memory lib,
  user-global hooks, the `/deploy-team` Node orchestrator + dashboard.

What stays untouched:

- All existing source code in your repo. The installer never edits
  anything outside `.claude/` and `.gitignore` (it adds a managed
  block between `# BEGIN rockie` / `# END rockie` markers; rules
  outside the markers are never touched).
- An existing `CLAUDE.md` is preserved. If absent, the installer
  prints the template path and you copy it in deliberately.
- Your existing `.env` is left alone; the installer creates one from
  `.env.example` only if it doesn't exist.

First time you open Claude Code in that project, the SessionStart
hook spots the missing `.rockie/taste/INDEX.md` and prompts
`/onboard` (~5 minutes, voice optional). After that, normal Claude
Code workflow + harness intercepts.

## Use it on a new project

Starting fresh:

```bash
git clone https://github.com/saml212/rockie-claude.git ~/rockie-claude
mkdir ~/your-research-project && cd ~/your-research-project
git init
~/rockie-claude/install.sh .
```

What `install.sh` creates:

- Skeleton `.claude/` (hooks, scripts, skills, memory dir, .state dir)
- `workflow.db` initialized + seeded with the harness rules
- A managed `.gitignore` block (so `workflow.db`, `.state/`, sentinels
  stay out of git)
- A printed pointer to the `CLAUDE.md` template — copy it, edit the
  Project section, commit.

First session walkthrough:

1. Open Claude Code in the new project.
2. SessionStart hook prompts `/onboard`. Five to seven questions,
   ~5 minutes; voice optional. Output: a six-file `.rockie/taste/`
   corpus committed to your repo.
3. Talk to Claude. Subagents verify novelty; the pre-launch audit
   reads shapes/gradients before any GPU dollars are spent.
4. After the first run completes, `/post-run-review` emits a `[LEARN]`
   block and the next prompt's UserPromptSubmit hook auto-injects
   relevant rules. The loop is now closed.

## Bring your own GPU (bypass the spot-procurement flow)

rockie's default GPU layer is a cross-provider router (RunPod / Vast /
Prime / Verda) with min-bid spot defaults and provider-hop on
preemption. That's the right choice if you have nothing pre-configured.

If you already have GPU infra — a university cluster, on-prem H100s,
your own AWS account, an SSH-tunneled workstation, or credentials at
a provider we don't route to — rockie steps out of the way.

**One-time setup:**

```bash
# in your-research-project/
echo 'ROCKIE_GPU_MODE=custom' >> .env
```

Then in your first agent session, ask Claude about GPUs. The agent
runs `/gpu-custom-setup` — a Q&A that captures your auth, provision,
connect, monitor, and terminate flow, then writes
`.claude/gpu-custom.md`. Subsequent sessions read that file when
GPUs come up.

**Minimal `autopilot.conf` for an SSH-based launcher:**

```ini
LAUNCHER_CMD=/usr/local/bin/my-launch.sh
ROCKIE_GPU_MODE=custom
```

`my-launch.sh` is whatever you already use to dispatch a training
run (sbatch + sshfs, ssh + nohup, terraform apply, etc.). The
autopilot loop, the Zero-Cost Monitor, the budget gate, the
post-run review, and the dead-end registry all keep working — only
the `gpu.py` cross-provider router is bypassed.

After that, `/gpu-custom` is the agent's runtime gateway:
provision / connect / status / cost / terminate are all routed
through your captured flow, not through rockie's router. The
terminate command is run **verbatim** from your setup file —
never improvised — because cost-sensitive teardown deserves
zero ambiguity.

See `project-harness/skills/gpu-custom-setup/SKILL.md` for the
full Q&A spec and `project-harness/skills/gpu-custom/SKILL.md` for
the runtime routing rules.

## Contributing back upstream

`/upstream-contribute` is the meta-loop: rockie users improve rockie
itself as they work. After `/clean` finishes an audit, the skill
surfaces a nudge — *"Anything in this session worth upstreaming?"* —
and on opt-in, scans the session for generalizable patterns (pruning
fixes, small skill improvements, new hooks, cross-discipline
capabilities, memory-schema upgrades), strips project-specific
specificity, and dispatches a writer sub-agent that forks
`saml212/rockie-claude`, applies the change on a `contrib/<slug>`
branch, runs the smoke test, and opens a PR. The agent never
auto-merges; the maintainers review; the next release ships the
pattern to everyone.

The bar is generalizability. Domain-specific changes stay in your
fork via `/propose-harness-change`. Anything that would require
revealing internal project context to make sense gets refused.

See `project-harness/skills/upstream-contribute/SKILL.md` for the
full Scout / Generator / Verifier / Updater flow and the leak-protection
rules the writer sub-agent enforces.

## Licensing

Apache-2.0. See [LICENSE](LICENSE).

Ports from other open-source harnesses are credited in
[docs/PORTS.md](docs/PORTS.md). We only vendor MIT/Apache-2.0 code;
patterns from restrictively-licensed harnesses are clean-room
reimplemented.

## Contributing

- Every port must cite source file + line range.
- Every new feature must compose with existing differentiators (taste
  corpus, modes, pre-run audit, `[LEARN]` DB, waterfall, journal tree,
  experiment-runs/, `/deploy-team`, pre-commit sentinel). Duplicates
  get rejected. See [docs/_meta/PHILOSOPHY.md](docs/_meta/PHILOSOPHY.md).
- Run `/clean` before committing — the pre-commit-gate hook enforces it.

**Upstream-back from agents — two paths.** If an agent using
rockie-claude in your own project discovers a harness-level
improvement, it can emit `[LEARN harness-upstream] …` mid-session.

- `/propose-harness-change` — reviewed/verified patch against your
  OWN local rockie clone. The Generator/Verifier/Updater split keeps
  the agent from auto-committing; the human pushes when ready.
- `/upstream-contribute` — the public meta-loop. Scans the session,
  strips project-specific specificity, dispatches a writer sub-agent
  to fork `saml212/rockie-claude`, applies the generalized change,
  runs the smoke test, and opens a PR. Maintainers review; the next
  release ships the pattern to everyone.

The agent never auto-pushes in either path.

---

## Further reading

**For users:**

- [docs/quickstart.md](docs/quickstart.md) — 5-minute install + first commands
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — event flow + storage model
- [docs/budgets.md](docs/budgets.md) — 4-dimension auto-tracking
- [docs/environment.md](docs/environment.md) — `.env` + rotation
- [docs/ntfy-setup.md](docs/ntfy-setup.md) — push notifications
- [docs/self-hosted-runner.md](docs/self-hosted-runner.md) — Mac mini runner + PR review
- [docs/PORTS.md](docs/PORTS.md) — every competitor we read, source-cited
- [SECURITY.md](SECURITY.md) — threat model + risk surfaces
- [CHANGELOG.md](CHANGELOG.md) — what changed, by release

**For agents and contributors working on rockie-claude itself:**

- [docs/_meta/README.md](docs/_meta/README.md) — meta-doc index (start here)
- [docs/_meta/PHILOSOPHY.md](docs/_meta/PHILOSOPHY.md) — what rockie-claude is and is not
- [docs/_meta/USER_JOURNEYS.md](docs/_meta/USER_JOURNEYS.md) — researcher + agent flows
- [docs/_meta/FEATURES.md](docs/_meta/FEATURES.md) — built / partial / planned
- [docs/_meta/ROADMAP.md](docs/_meta/ROADMAP.md) — outstanding work, prioritized
- [docs/_meta/DECISIONS.md](docs/_meta/DECISIONS.md) — architectural decisions log
- [docs/_meta/LESSONS.md](docs/_meta/LESSONS.md) — durable user feedback + audit findings
- [docs/_meta/ONBOARDING_DESIGN.md](docs/_meta/ONBOARDING_DESIGN.md) — `/onboard` design spec
- [docs/_meta/PLAN.md](docs/_meta/PLAN.md) — current snapshot of in-flight work

---

## Related projects

- [`saml212/rockie-codex`](https://github.com/saml212/rockie-codex) —
  OpenAI Codex CLI sibling. Same patterns, different runtime.

## Acknowledgements

This harness was extracted from research originally driven on a
learned-representations workspace; see
[pebbleml.com](https://www.pebbleml.com) for the kind of project a
researcher might run rockie-claude on.
