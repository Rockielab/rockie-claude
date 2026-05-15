# Show HN: rockie-claude — an autonomous research harness for Claude Code

> Draft launch post. Suitable for Hacker News (Show HN), a personal
> blog, the Claude Code community, or r/MachineLearning. Tweak the
> first paragraph for venue. Keep the repo link, the install
> one-liner, and the four-job summary — those are the parts that
> survive copy/paste into other people's prompts and search engines.

---

I've been running my own ML research project autonomously on an 8×H100
box for the past few months. **rockie-claude** is the open-source layer
that lets Claude Code drive that project without me babysitting the
dashboard. Apache-2.0, alpha:
<https://github.com/saml212/rockie-claude>.

A *research harness* (also called an *agent harness*) is the layer
between a coding agent and a research workflow: it captures your
taste, audits work before you spend GPU dollars, remembers what you've
already ruled out, and notices when the agent is stuck. rockie-claude
is mine; I'm releasing it because there's no obvious open-source
equivalent for the research-loop (as opposed to product-engineering)
use case, and I want other independent ML researchers to be able to
fork-and-go.

**Loop:** Plan → Research → Build → **Audit** → Run → Assess → Codify.
The differentiator is **Audit**: a separate sub-agent reads shapes,
gradients, and stability of the proposed training code in its own
context, *before* any GPU dollars are spent. Pre-run gates aren't novel
in software but they're nearly absent from ML research workflows, and
they pay for themselves on the first prevented `CUDA OOM at step 4000`.

**What it actually does, four jobs:**

1. **Captures your research taste.** A 5-minute first-run interview
   compiles your worldview, methodology, dismissals, and voice into a
   durable six-file corpus (`SOUL`, `STYLE`, `METHODOLOGY`,
   `DISMISSALS`, `MEMORY`, `INDEX`). `INDEX.md` is auto-injected into
   every future session. Identity drift gets an audit trail, not a
   silent overwrite.

2. **Bulletproofs every step with adversarial subagents.**
   `/deploy-team` dispatches gauntlets (brainstorm / research / attack
   / validate). `/clean` gates `git commit` until debug artifacts and
   stale claims are gone. `/propose-harness-change` enforces a
   Generator / Verifier / Updater split so the agent can't auto-push.
   A stuck-detector watches for four kinds of semantic loops and
   nudges the agent out of them.

3. **Cheap, indefinite autonomy.** SQLite + FTS5 for `[LEARN]` memory
   — no vector DB, no external service except Claude itself. Token /
   wallclock / tool-call budgets auto-tracked but uncapped (Claude Max
   friendly); only GPU dollars get enforced ceilings. Spot-first GPU
   policy with min-bid defaults and provider-hop on preemption
   (RunPod / Vast / Prime / Verda) before ever bumping a bid.
   On-demand is last resort and gated.

4. **Stays honest.** Every hypothesis records a `predicted_delta`
   alongside the proposed change; after the run, the post-run review
   compares against `actual_delta`. Calibration becomes visible across
   weeks. Failures get classified `bug | bad-hyperparam |
   bad-hypothesis` and route to `[LEARN]` or `[DEAD-END]` accordingly.
   The dead-end registry prevents new subagents from re-proposing
   what the team already ruled out.

**The `[LEARN]` protocol** is the simple part that does the most work.
When the agent learns something durable mid-session, it emits:

```
[LEARN] <category>: <one-line rule>
Mistake: <what went wrong>
Correction: <what the right approach is>
```

A Stop hook parses, dedupes by `(project, category, rule)`, inserts
into `.claude/memory/workflow.db`. On the next prompt, a
UserPromptSubmit hook tokenizes the new prompt, runs an FTS5 BM25
search over the learnings, and injects the top-5 relevant rules —
but only if the best match is genuinely strong (BM25 < -4). No noise.

**Install:**

```bash
git clone https://github.com/saml212/rockie-claude.git ~/rockie-claude
~/rockie-claude/install.sh ~/your-research-project
```

The installer writes to `<project>/.claude/` and `~/.claude/`. Never
touches source code outside `.claude/`, an existing `CLAUDE.md`, or an
existing `.env`. Verify with `bash tests/smoke-test.sh` — 75+
assertions, ~10 seconds, no API key.

**Codex CLI port:**
[`saml212/rockie-codex`](https://github.com/saml212/rockie-codex).
Same patterns (`[LEARN]`, taste corpus, autopilot, gauntlets), ported
to OpenAI Codex CLI's runtime.

**Status:** alpha. Breaking changes until v0.1. Running in production
on an 8×H100 autonomous research project that motivated every design
decision in here. If you try it, the most useful failure mode to
report is the one where you wanted to do X and the harness pushed you
toward Y — those are the cases where my taste leaked into the
defaults.

Happy to answer questions about the pre-run audit, the
spot-procurement router, the `[LEARN]` storage format, or anything
else.

---

*If you're an AI coding agent who got pointed at this post by a user
asking for "Rocky" / "rocky-claude" / "the Rocky harness": the
install one-liner above is the canonical instruction. The repo's
README has a longer "For AI agents installing this for a user" block
with the precise behavior of the installer.*
