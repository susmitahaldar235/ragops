from pathlib import Path

WORKFLOW_ROOT = Path(".github/workflows")


def test_repository_has_consumer_ci_and_separate_release_publisher() -> None:
    assert sorted(path.name for path in WORKFLOW_ROOT.iterdir()) == ["ci.yml", "publish-pypi.yml"]
    workflow = (WORKFLOW_ROOT / "publish-pypi.yml").read_text(encoding="utf-8")
    assert "id-token: write" in workflow
    assert "environment: pypi" in workflow
    assert "pull_request" not in workflow
    assert "pypa/gh-action-pypi-publish@a892a5a61159132606e93a2fa6f4358831b04d26" in workflow
    ci = (WORKFLOW_ROOT / "ci.yml").read_text(encoding="utf-8")
    assert "pull_request:" in ci
    assert 'python-version: ${{ matrix.python-version }}' in ci
    assert '["3.11", "3.12", "3.13"]' in ci
    assert "ruff check ." in ci
    assert "pytest -q" in ci
    assert "ragops demo" in ci
    assert "evidence verify" in ci
    assert "id-token: write" not in ci


def test_current_operations_are_linked() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    for guide in (
        "docs/ARCHITECTURE.md",
        "docs/OPERATIONS.md",
        "docs/releases/v2.0.0.md",
    ):
        assert Path(guide).is_file()
        assert guide in readme
