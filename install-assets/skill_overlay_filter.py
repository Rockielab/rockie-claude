#!/usr/bin/env python3
"""Single source of truth for which project-harness/skills/ directories
get assembled into a live project's .claude/skills/ overlay at install
time.

Reads install-assets/skills-manifest.json and prints the excluded skill
names, one per line, to stdout. install.sh and tests/smoke-test.sh
consume this to build rsync --exclude flags rather than each keeping
their own copy of the list.

Guards (fail loudly, exit 2, print nothing on stdout):
  - refuses to exclude a name listed in "never_exclude" — the bootstrap
    paradox: find-skills/onboard can never be excluded from the harness
    overlay, because you cannot pull the skill that teaches you to pull
    skills.
  - refuses to exclude a name that has no matching directory under
    skills/ — catches typos and stale entries after a skill is renamed
    or removed.

See Rockielab/rockie-claude#30.
"""
import json
import pathlib
import sys


def load_excluded(manifest_path: pathlib.Path, skills_dir: pathlib.Path) -> list[str]:
    manifest = json.loads(manifest_path.read_text())
    never_exclude = set(manifest.get("never_exclude", []))
    excluded = manifest.get("excluded_from_overlay", {})

    violations = never_exclude & excluded.keys()
    if violations:
        # NOTE: `raise SystemExit(<str>)` exits 1, not 2 — Python treats a
        # non-int SystemExit argument as a message to print to stderr, with
        # the process exit code fixed at 1 regardless of the string's
        # content. Print explicitly, then exit with the actual intended
        # code so callers checking for a distinguishable guard-failure
        # status (install.sh, tests/smoke-test.sh) get exit 2 as documented
        # above, not exit 1.
        print(
            "skills-manifest.json excludes bootstrap-paradox skill(s): "
            f"{sorted(violations)} — find-skills/onboard can never be "
            "excluded from the harness overlay (see never_exclude).",
            file=sys.stderr,
        )
        raise SystemExit(2)

    missing = [name for name in excluded if not (skills_dir / name).is_dir()]
    if missing:
        print(
            "skills-manifest.json excludes non-existent skill dir(s): "
            f"{sorted(missing)} under {skills_dir}",
            file=sys.stderr,
        )
        raise SystemExit(2)

    return sorted(excluded)


def main(argv: list[str]) -> int:
    project_harness = pathlib.Path(argv[1] if len(argv) > 1 else ".")
    manifest_path = project_harness.parent / "install-assets" / "skills-manifest.json"
    skills_dir = project_harness / "skills"
    for name in load_excluded(manifest_path, skills_dir):
        print(name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
