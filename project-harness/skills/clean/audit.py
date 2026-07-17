#!/usr/bin/env python3
"""
audit.py — pre-commit anti-slop audit for this repo.

Three tracks, changed-files-only:
  - Static lint (ruff for .py, shellcheck for .sh — skip if not installed)
  - Doc audit (.md): new-file blocker, broken internal links, length,
    TODO/FIXME markers, stale time-sensitive phrases
  - AI slop prompt: returned in the report for the agent to action

On zero-blocker pass, hands off to <workspace>/scripts/clean-finalize.sh,
which writes the sentinel <workspace>/.state/clean-ok-<hash> AND emits
the upstream-contribute nudge to stderr. The pre-commit-gate hook reads
this sentinel. <workspace> is self-located from this file's path (see
resolve_workspace_dir()) — no environment variable is required or
honored.

Exit codes:
  0  zero blockers (sentinel written)
  1  blockers present (no sentinel)
  2  script error
"""

import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def resolve_workspace_dir():
    """Resolve the workspace root that owns this script, self-located
    from this file's own path — never from an environment variable.

    audit.py lives at <workspace>/skills/clean/audit.py in every copy:
    this repo's own checkout, and every deployed/overlay copy (tenant
    runtime images, sibling harness repos) that preserves the same
    two-level `skills/clean/` nesting under whatever directory serves
    as that copy's workspace root. The same three-parent hop lands on
    the right workspace root in all of them.

    This used to read OPENCLAW_WORKSPACE_DIR from the environment and
    exit 2 if unset — but nothing in this repo, and nothing in a
    deployed tenant image, ever sets it. That made audit.py exit 2
    without writing the sentinel, while pre-commit-gate.sh's own block
    message told the user to re-run the exact command that had just
    failed: a catch-22 that could never resolve (issue backported from
    Rockielab/rockie-claude#29).

    No env-var override is honored, on purpose: a stale value (left set
    from a previous session, or pointed at a sibling checkout) would
    silently redirect the sentinel to the WRONG .state dir. This bites
    hardest in a `git worktree add` checkout — `.state/` is untracked,
    so a worktree never inherits the main checkout's copy — so a
    leftover override would write the sentinel into the wrong tree
    while the commit gate, self-locating independently from its own
    script path, checks the worktree's own (empty) .state and still
    blocks: /clean reports clean, the commit stays blocked. Always
    self-locating avoids that class of bug entirely.
    """
    return str(pathlib.Path(__file__).resolve().parent.parent.parent)


def changed_files(scope, since=None):
    if scope == "staged":
        out = run(["git", "diff", "--cached", "--name-only"]).stdout
    elif scope == "dirty":
        mod = run(["git", "diff", "--name-only"]).stdout
        unt = run(["git", "ls-files", "--others", "--exclude-standard"]).stdout
        out = mod + unt
    elif scope == "since":
        # Audit files changed since a given ref (commit, tag, branch,
        # or relative like HEAD~15). Useful for post-hoc review of
        # recent work when nothing is dirty.
        ref = since or "HEAD~1"
        out = run(["git", "diff", f"{ref}..HEAD", "--name-only"]).stdout
    else:
        return []
    files = [f.strip() for f in out.splitlines() if f.strip()]
    return [f for f in files if os.path.exists(f)]


def audit_python(f):
    issues = []
    if shutil.which("ruff"):
        r = run(["ruff", "check", "--select", "F401,F811,F841,E711,E712", f])
        for line in r.stdout.strip().splitlines():
            # Skip ruff's summary/status lines — only real findings matter.
            if not line:
                continue
            if line.startswith(("Found", "All checks passed")):
                continue
            if "warning:" in line.lower() or "error:" in line.lower() or f in line:
                issues.append((f, "warning", line.strip()))
    else:
        issues.append((f, "info", "ruff not installed — static lint skipped"))

    try:
        source = pathlib.Path(f).read_text()
        # print() detection is meant to catch debug artifacts, not CLI UI.
        # Skip files that look like CLIs (import argparse) or test files.
        is_cli = ("import argparse" in source) or ("argparse.ArgumentParser" in source)
        is_test = "test" in f.lower()
        if not is_cli and not is_test:
            for i, line in enumerate(source.splitlines(), 1):
                if re.match(r"\s*print\s*\(", line):
                    issues.append((f, "warning", f"L{i}: stray print() — debug artifact?"))
    except Exception:
        pass
    return issues


def audit_shell(f):
    issues = []
    if shutil.which("shellcheck"):
        r = run(["shellcheck", "-f", "gcc", "-S", "warning", f])
        for line in r.stdout.strip().splitlines():
            issues.append((f, "warning", line.strip()))
    else:
        issues.append((f, "info", "shellcheck not installed — static lint skipped"))
    return issues


def audit_markdown(f, is_new, repo_root):
    issues = []
    # Block creation of new .md files — user's rule for this repo.
    # Exempt: harness infrastructure (.claude/** legacy or .openclaw/**)
    # where .md files are skill/agent definitions required to exist,
    # AND the handful of root-level docs the harness itself mandates:
    # CLAUDE.md (install.sh's own bootstrap tells every new user to
    # `cp claude-md/CLAUDE.md.template CLAUDE.md` as their first action
    # after installing — issue backported from Rockielab/rockie-claude#29),
    # plus README.md/STATE.md/EXPERIMENT_LOG.md (the generated CLAUDE.md
    # itself instructs every project to maintain STATE.md and
    # EXPERIMENT_LOG.md at repo root, and every repo needs a README —
    # dogfooding surfaced /clean blocking exactly those three on a new
    # user's first real commit, forcing a CLEAN_BYPASS just to satisfy
    # the harness's own onboarding instructions). These are singular,
    # harness-mandated files at a fixed repo-root path, not the
    # arbitrary doc proliferation this rule targets — unlike a new
    # NOTES.md/REPORT.md, or any .md nested in a subdirectory, there is
    # only ever one of each, always at repo root. The exemption is
    # root-only by construction: a nested docs/STATE.md or docs/README.md
    # doesn't match the bare filename and still blocks.
    ROOT_MANDATED_MD = {"CLAUDE.md", "README.md", "STATE.md", "EXPERIMENT_LOG.md"}
    if (
        is_new
        and f not in ROOT_MANDATED_MD
        and not (f.startswith(".claude/") or f.startswith(".openclaw/"))
    ):
        issues.append((
            f, "blocker",
            "NEW .md file. Repo convention: consolidate into existing docs. "
            "If this is genuinely a novel topic (paper draft, design doc the user requested), "
            "override with CLEAN_BYPASS=1 at commit time."
        ))

    try:
        content = pathlib.Path(f).read_text()
    except Exception as e:
        issues.append((f, "info", f"read failed: {e}"))
        return issues

    base = pathlib.Path(f).parent

    # Broken internal links
    for m in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", content):
        link = m.group(2).strip().split()[0]  # strip ` "title"`
        if link.startswith(("http://", "https://", "mailto:", "#")):
            continue
        path_only = link.split("#")[0].split("?")[0]
        if not path_only:
            continue
        target = (base / path_only).resolve()
        if not target.exists():
            issues.append((f, "warning", f"broken link: [{m.group(1)}]({link})"))

    # TODO/FIXME/XXX
    for i, line in enumerate(content.splitlines(), 1):
        if re.search(r"\b(TODO|FIXME|XXX)\b", line):
            issues.append((f, "info", f"L{i}: marker — {line.strip()[:80]}"))

    # Length
    n = len(content.splitlines())
    if n > 500:
        issues.append((f, "warning", f"length {n} lines — consider consolidation"))

    # Stale markers — specific phrases that usually go out of date
    stale = re.findall(
        r"\b(currently running|in progress|as of \d{4}-\d{2}-\d{2}|this week|last week)\b",
        content, flags=re.IGNORECASE,
    )
    if stale:
        issues.append((f, "info", f"time-sensitive phrases present ({len(stale)}); verify currency"))

    return issues


def compute_hash():
    ws = resolve_workspace_dir()
    r = run(["bash", f"{ws}/scripts/compute_clean_hash.sh"])
    return r.stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", choices=["staged", "dirty", "since"], default="staged")
    ap.add_argument("--since", help="Ref (commit/branch/HEAD~N) for --scope since")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    repo = run(["git", "rev-parse", "--show-toplevel"]).stdout.strip()
    if not repo:
        print("not a git repo", file=sys.stderr)
        sys.exit(2)
    os.chdir(repo)

    files = changed_files(args.scope, since=args.since)
    scope_note = args.scope if args.scope != "since" else f"since {args.since or 'HEAD~1'}"
    if args.scope == "staged" and not files:
        files = changed_files("dirty")
        scope_note = "dirty (no staged)"

    tracked = set(run(["git", "ls-tree", "--name-only", "-r", "HEAD"]).stdout.splitlines())

    issues = []
    for f in files:
        ext = pathlib.Path(f).suffix.lower()
        if ext == ".py":
            issues += audit_python(f)
        elif ext in (".sh", ".bash"):
            issues += audit_shell(f)
        elif ext == ".md":
            issues += audit_markdown(f, f not in tracked, repo)

    blockers = [i for i in issues if i[1] == "blocker"]
    warnings = [i for i in issues if i[1] == "warning"]
    info = [i for i in issues if i[1] == "info"]

    if args.json:
        print(json.dumps({
            "scope": scope_note,
            "files_audited": len(files),
            "blockers": [{"file": a, "msg": c} for a, _, c in blockers],
            "warnings": [{"file": a, "msg": c} for a, _, c in warnings],
            "info": [{"file": a, "msg": c} for a, _, c in info],
        }, indent=2))
    else:
        print(f"--- /clean audit ({scope_note}, {len(files)} files) ---")
        for label, group in (("BLOCKERS", blockers), ("WARNINGS", warnings), ("INFO", info)):
            if not group:
                continue
            print(f"\n{label} ({len(group)}):")
            for f, _, msg in group:
                print(f"  [{f}] {msg}")
        print()
        print("=== AI slop audit prompt (agent should address) ===")
        print("Review the diffs for the files above for:")
        print("  - debug artifacts (print/console.log/fmt.Println left in non-test code)")
        print("  - single-use helper functions (inline them)")
        print("  - restating comments (// CreateX above func CreateX)")
        print("  - catch-rethrow without added context")
        print("  - over-abstraction serving hypothetical needs")
        print("  - bloated docstrings that repeat the function signature")

    if not blockers:
        h = compute_hash()
        if h and h != "no-changes":
            # Delegate sentinel write + upstream-contribute nudge to
            # clean-finalize.sh so the nudge is deterministic (not
            # prose-only in SKILL.md) and the sentinel format stays in
            # one place shared with pre-commit-gate.sh.
            ws = resolve_workspace_dir()
            # Forward our self-located workspace value to clean-finalize.sh
            # via the environment too. Harmless if the target script
            # ignores it (self-locating scripts do); required if it
            # doesn't (some deployed clean-finalize.sh copies still read
            # OPENCLAW_WORKSPACE_DIR from their own environment). Setting
            # it here rather than requiring the caller's shell to have it
            # also overrides any stale inherited value, so the same
            # worktree-safety guarantee holds end to end either way.
            r = subprocess.run(
                ["bash", f"{ws}/scripts/clean-finalize.sh", h],
                text=True,
                env={**os.environ, "OPENCLAW_WORKSPACE_DIR": ws},
            )
            if r.returncode != 0:
                print(f"\n✗ clean-finalize.sh failed (exit {r.returncode})")
                sys.exit(2)
            print(f"\n✓ sentinel written: clean-ok-{h}")
        else:
            print("\n(nothing staged — no sentinel needed)")
        sys.exit(0)
    else:
        print(f"\n✗ {len(blockers)} blocker(s) — fix and rerun")
        sys.exit(1)


if __name__ == "__main__":
    main()
