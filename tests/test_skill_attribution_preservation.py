from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / "project-harness" / "skills"

MIRRORED_COMMUNITY_SKILLS = {
    "build-agent",
    "diligence-deck",
    "excel",
    "physics",
    "powerpoint",
    "upstream-contribute",
}

FORBIDDEN_PRODUCT_PRIVATE_KEYS = {
    "agent_run_id",
    "api_key",
    "auth_header",
    "bearer_token",
    "challenge",
    "conflicted_proposal_details",
    "contact_email",
    "credential_row_id",
    "email",
    "hf_token",
    "huggingface_token",
    "internal_tenant_id",
    "internal_user_id",
    "moderation_internal",
    "nonce",
    "oauth_token",
    "phone",
    "private_contact",
    "proposal_record",
    "raw_proposal",
    "raw_proposal_record",
    "raw_vote",
    "raw_vote_row",
    "rejected_proposal_details",
    "review_comments",
    "tenant_id",
    "token",
    "user_id",
    "verification_challenge",
    "vote_rows",
    "voter_identity",
    "withdrawn_proposal_details",
}


def _frontmatter(path: Path) -> dict:
    text = path.read_text()
    assert text.startswith("---\n"), f"{path} is missing YAML frontmatter"
    try:
        raw = text.split("---\n", 2)[1]
    except IndexError:
        pytest.fail(f"{path} has unterminated YAML frontmatter")
    return yaml.safe_load(raw) or {}


def _walk_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_keys(item)


def _assert_person_list(frontmatter, field):
    attribution = frontmatter["attribution"]
    people = attribution.get(field)
    assert isinstance(people, list) and people, f"attribution.{field} is required"

    profiles = attribution.get("profiles")
    assert isinstance(profiles, dict) and profiles, "attribution.profiles is required"

    for person in people:
        assert isinstance(person.get("rockie_username"), str) and person["rockie_username"]
        assert isinstance(person.get("display_name"), str) and person["display_name"]
        refs = person.get("profile_refs")
        assert isinstance(refs, list) and refs, f"{field} profile_refs is required"
        for ref in refs:
            assert isinstance(ref, str) and ref
            assert ref in profiles, f"{field} profile ref {ref!r} is missing from profiles"


def test_mirrored_community_skills_include_parseable_attribution():
    mirrored_skill_dirs = {path.parent.name for path in SKILLS_ROOT.glob("*/SKILL.md")}
    assert MIRRORED_COMMUNITY_SKILLS <= mirrored_skill_dirs

    for skill in sorted(MIRRORED_COMMUNITY_SKILLS):
        frontmatter = _frontmatter(SKILLS_ROOT / skill / "SKILL.md")
        assert frontmatter.get("scope") == "community"

        attribution = frontmatter.get("attribution")
        assert isinstance(attribution, dict), "attribution must be a mapping"
        assert attribution.get("schema_version") == 1
        assert attribution.get("completeness") == "complete"
        _assert_person_list(frontmatter, "authors")
        _assert_person_list(frontmatter, "maintainers")


def test_mirrored_community_skill_frontmatter_excludes_private_product_keys():
    for skill in sorted(MIRRORED_COMMUNITY_SKILLS):
        frontmatter = _frontmatter(SKILLS_ROOT / skill / "SKILL.md")
        keys = {key.lower().replace("-", "_") for key in _walk_keys(frontmatter)}
        leaked = keys & FORBIDDEN_PRODUCT_PRIVATE_KEYS
        assert not leaked, f"{skill} contains forbidden private/product keys: {sorted(leaked)}"
