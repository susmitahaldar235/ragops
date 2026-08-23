import re
from pathlib import Path


def test_gitlab_recipe_preserves_evidence_and_exit_code() -> None:
    recipe = Path("docs/examples/gitlab-ci-ragops.yml").read_text(encoding="utf-8")

    assert 'RAGOPS_VERSION: "2.0.1"' in recipe
    assert 'if: \'$CI_PIPELINE_SOURCE == "merge_request_event"\'' in recipe
    assert "gate_exit=$?" in recipe
    assert 'exit "$gate_exit"' in recipe
    assert "when: always" in recipe
    assert "ragops-report.md" in recipe
    assert "ragops-command.log" in recipe
    assert "allow_failure" not in recipe
    assert "PRIVATE-TOKEN" not in recipe


def test_downstream_github_publisher_is_copyable_and_least_privilege() -> None:
    recipe = Path("docs/examples/github-pr-comment.yml").read_text(encoding="utf-8")

    assert 'workflows: ["RAGOps"]' in recipe
    assert "RAGOPS_SOURCE_WORKFLOW: RAGOps" in recipe
    assert "actions: read" in recipe
    assert "contents: read" in recipe
    assert "pull-requests: write" in recipe
    assert "pull_request_target" not in recipe
    assert "persist-credentials: false" in recipe
    assert "repository: thangldw/ragops" in recipe
    assert re.search(r"ref: [0-9a-f]{40}", recipe)
    assert re.search(r"actions/checkout@[0-9a-f]{40}", recipe)
    assert "python .ragops-publisher/apps/github_pr_comment.py" in recipe


def test_github_caller_is_read_only_and_verifies_evidence() -> None:
    recipe = Path("docs/examples/github-actions-ragops.yml").read_text(encoding="utf-8")

    assert "pull_request:" in recipe
    assert "contents: read" in recipe
    assert "id-token: write" not in recipe
    assert "persist-credentials: false" in recipe
    assert re.search(r"actions/checkout@[0-9a-f]{40}", recipe)
    assert '"ragops==2.0.1"' in recipe
    assert "ragops evidence verify" in recipe
    assert '>> "$GITHUB_STEP_SUMMARY"' in recipe
