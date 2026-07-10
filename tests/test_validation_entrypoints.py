from pathlib import Path


def test_pre_push_uses_canonical_validator():
    text = Path(".githooks/pre-push").read_text(encoding="utf-8")
    assert "./scripts/validate.sh" in text


def test_ci_uses_canonical_validator():
    text = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "./scripts/validate.sh" in text
