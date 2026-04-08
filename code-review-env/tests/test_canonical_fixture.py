from pathlib import Path

from tasks.validate_canonical_fixture import validate_fixture


def test_canonical_fixture_layout_and_patterns() -> None:
    root = Path("sample_project_canonical").resolve()
    ok, errors = validate_fixture(root)
    assert ok, "\n".join(errors)
