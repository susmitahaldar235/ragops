from pathlib import Path


def test_workbench_exposes_evaluation_and_team_history() -> None:
    page = Path("apps/web/index.html").read_text(encoding="utf-8")
    script = Path("src/ragops/web/app.js").read_text(encoding="utf-8")

    assert 'id="scenario"' in page
    assert 'id="responses"' in page
    assert 'id="api-key" type="password"' in page
    assert "'x-api-key':apiKey.value" in script
    assert "localStorage" not in page + script
    assert 'id="runs"' in page
    assert "fetch('/v1/evaluate'" in script
    assert "fetch(`/v1/runs?limit=" in script
    assert "RAGOPS_STORE" in page
    assert "NOT EVALUATED" in script
    assert "innerHTML" not in page + script
    assert "replaceChildren" in script
