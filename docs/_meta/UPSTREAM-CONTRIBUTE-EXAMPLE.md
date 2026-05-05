# /upstream-contribute — paper trace of one end-to-end run

This document walks the meta-loop through a single concrete example
so future contributors and skeptics can see the moving parts. The
skill is at `project-harness/skills/upstream-contribute/SKILL.md`;
the wire-up nudge is the "Post-audit hook" section of
`project-harness/skills/clean/SKILL.md`.

The example we trace is **the FTS5 BM25 retrieval thresholding** —
the rule in `hooks/load-relevant-rules.sh` that injects the top-5
matched `[LEARN]` rules only when the best BM25 score is genuinely
strong (`< -4`), so weak matches don't pollute the next prompt.

We pick this one because:

1. It's a real, shipped pattern in rockie-claude today.
2. It's a small, self-contained tweak on one hook script — exactly the
   shape of change the skill is for.
3. It generalizes cleanly across research domains. ML, biology,
   linguistics — any rockie user benefits when noise gets suppressed.
4. It's easy to imagine an external user discovering this in their
   own work ("my rules are getting injected for prompts that have
   nothing to do with them") and wanting to upstream the fix.

## 1. What the skill notices

The session ends; `/clean` runs an audit; sentinel writes; the
post-audit hook surfaces the nudge. The user types
`/upstream-contribute`.

The Scout step queries `workflow.db` for `[LEARN]` rows added in the
last 6 hours and gets back (among other rows):

```
category: fts5-retrieval
rule: bm25 score threshold should be tightened to -4 to suppress weak matches
mistake: top-5 rules injected on every prompt regardless of match quality;
         injection became background noise that the user started ignoring
correction: gate injection on bm25(...) < -4; print only matched rules,
            not pad-to-five
```

The Scout also reads `git log --since='6 hours ago' --name-only` and
sees `project-harness/hooks/load-relevant-rules.sh` was edited in
the most recent commit.

## 2. Generalizability scoring

The Scout asks the four questions:

| Question | Answer |
|---|---|
| Would this help another rockie user across a different research domain? | **Yes.** Noise-suppression on rule injection is universal — every user has a `[LEARN]` corpus and a UserPromptSubmit injection step. |
| Is the pattern small and self-contained? | **Yes.** One hook script, one threshold constant. |
| Can it be described without naming any internal project, person, or dataset? | **Yes.** The fix is purely about retrieval-quality math; no project, person, or dataset needs to be referenced. |
| Does it survive without project-specific configuration? | **Yes.** The threshold is a literal in the hook, not a per-project knob. |

All four pass. The candidate moves forward.

## 3. Stripping project-specific specificity

The original mistake reads:

> "top-5 rules injected on every prompt regardless of match quality;
> injection became background noise that the user started ignoring"

That's already generic enough — no project name, no dataset name, no
person. The Scout passes it through verbatim. (If the mistake had
read "during the matrix-token autopilot run we noticed…" the Scout
would rewrite to "during a multi-day autopilot run we noticed…" or,
if that still felt too narrow, "for any rockie deployment with
substantial `[LEARN]` history, we noticed…")

The generalized change description handed to the writer sub-agent:

```
Tighten the BM25 score threshold in load-relevant-rules.sh from -3
to -4 so weak FTS5 matches don't get injected on every prompt. Cap
output at the count of rules that actually pass the threshold rather
than padding to five. The previous behavior caused injection to
become background noise users learned to ignore; the tightened
threshold preserves signal.
```

## 4. What the writer sub-agent does

Dispatched via the `Agent` tool with no prior context. Receives:
the description above + the file list `["project-harness/hooks/load-relevant-rules.sh"]`
+ `target_repo=saml212/rockie-claude` + `branch=contrib/fts5-bm25-threshold`.

It performs:

```bash
gh repo fork saml212/rockie-claude --clone --remote
cd rockie-claude
git checkout -b contrib/fts5-bm25-threshold

# Apply the change — single literal swap, plus the count-cap rewrite.
# Edit project-harness/hooks/load-relevant-rules.sh:
#   - replace BM25_THRESHOLD=-3 with BM25_THRESHOLD=-4
#   - in the SQL, change "LIMIT 5" gating logic so output is the
#     intersection of {top-5 by BM25} and {bm25 < threshold}, not
#     the union padded to five
# Hook script is ~80 lines so the diff is small.

bash tests/smoke-test.sh
# All 75+ assertions green; FTS5 retrieval round-trip test passes
# on the new threshold.

git add project-harness/hooks/load-relevant-rules.sh
git commit -m "fix(retrieval): tighten BM25 threshold from -3 to -4

Weak FTS5 matches were getting injected on every UserPromptSubmit;
users learned to ignore the injection block, undermining the whole
[LEARN] -> retrieval pipeline. Tighter threshold preserves signal
and shrinks the average inject size from 5 rules to 1-2 when the
match quality is genuinely there.

Cap output at the count of rules that pass the threshold rather
than padding to five."
git push -u origin contrib/fts5-bm25-threshold
gh pr create --title "fix(retrieval): tighten BM25 threshold from -3 to -4" \
             --body-file pr-body.md
```

## 5. The PR body (filled-in template)

```markdown
## What

Tighten the BM25 score threshold in `load-relevant-rules.sh` from
-3 to -4. Cap injection output at the count of rules that pass the
threshold instead of padding to five.

## Why this is generalizable

Every rockie user has a `[LEARN]` corpus injected on every prompt
via FTS5 BM25. The previous threshold let weak matches through, so
injection became background noise users learned to ignore — which
undermined the whole [LEARN] -> retrieval pipeline. Tighter
threshold preserves signal across any research domain. Domains with
small corpora benefit most: a 12-row `[LEARN]` table at -3 was
returning 5 rules per prompt almost regardless of relevance; at -4
it returns 0-2 when the match quality is genuinely there.

## What this isn't

Not a rewrite of the retrieval ranker. Not a configurable knob (the
literal -4 stays in the script; users who want different behavior
can fork). Not a change to the schema, the FTS5 tokenizer
(`porter unicode61` stays), or the trigger functions.

## Smoke-test status

`bash tests/smoke-test.sh` -> 75+ assertions, all green
(local run on 2026-04-29; CI will re-run on push).

## Composition with existing differentiators

Composes with `[LEARN]` DB (the threshold lives in the consumer of
that pipeline; nothing about the writer changes). Does not duplicate
any of the four differentiators.

## Acknowledgements

This pattern was uncovered by an external rockie-claude user during
their own research work. They asked for upstreaming via
`/upstream-contribute`. Crediting opt-in withheld.
```

## 6. What `tests/smoke-test.sh` would assert

The relevant assertions in the smoke suite that prove the change
doesn't break anything:

- FTS5 retrieval round-trip: insert a `[LEARN]` block, run the
  retrieval-injection hook against a prompt that should match
  strongly, assert the rule is in the injection block.
- FTS5 retrieval round-trip with a prompt that should match weakly,
  assert the rule is NOT in the injection block (this is the new
  assertion the writer would add to lock the threshold-tightening
  behavior in).
- Hook fail-open: feed malformed transcript JSON into the hook,
  assert exit code 0 and no crash.
- DB connection cleanup: assert no lingering `workflow.db-wal` /
  `workflow.db-shm` files after the hook returns.

If the writer sub-agent's run of the smoke suite passes all of those
on the `contrib/fts5-bm25-threshold` branch, the PR is opened. If
even one fails, the Generator aborts and reports back to the user
with the failure trace; the PR is never opened.

## 7. What the Updater (the human) does

The PR sits open at `https://github.com/saml212/rockie-claude/pull/<n>`.
The maintainers review:

- Does the diff match the description?
- Do the smoke assertions actually catch the regression they claim to?
- Does the change compose, or duplicate?
- Any leak-protection concerns in the body or the diff?

If yes/yes/composes/no, they merge. The next release ships the
tightened threshold to every rockie user. The contributor doesn't
need to be a rockie maintainer — the meta-loop closes.

## Anti-patterns this trace deliberately avoids

- **Auto-merge.** The skill stops at "PR opened." The maintainers'
  judgement is the final gate. Future automation only happens once
  the false-approve rate is empirically measured.
- **Bundled changes.** One PR, one logical change. If the user has
  three candidates, three PRs (or three commits in one PR if they're
  obviously related) — never one PR that mixes a hook fix, a schema
  change, and a docs tweak.
- **Project context leakage.** Even though the PR body says "an
  external rockie-claude user", it never names the project, the
  domain, the dataset, or the contributor (unless they explicitly
  opt in). The Scout's strip step is the first line of defense; the
  Generator's PR-body template is the second; the human reviewer is
  the third.
- **Skill self-modification.** The Generator will refuse if the
  candidate change touches `project-harness/skills/upstream-contribute/SKILL.md`
  or the Verifier's prompt. Self-improvement footgun.
