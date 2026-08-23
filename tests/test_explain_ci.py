from __future__ import annotations

import json
import xml.etree.ElementTree as ET

import pytest

from ragops.ci import github_summary, junit_xml, sarif_report
from ragops.cli import main
from ragops.explain import explain_decision
from ragops.loader import ContractError
from ragops.policy_v2 import GateEvidence, ReleaseDecision, load_release_decision


def _decision() -> ReleaseDecision:
    return ReleaseDecision(
        schema_version="1.0",
        scenario_id="support",
        decision="BLOCK",
        passed=False,
        gates=(
            GateEvidence(
                id="global:citation_coverage:regression",
                metric="citation_coverage",
                scope="global",
                observed=-0.5,
                threshold=0.0,
                comparator=">=",
                passed=False,
                severity="block",
                policy_path="metrics.citation_coverage.max_regression",
                case_ids=("q2",),
            ),
            GateEvidence(
                id="global:latency_ms:maximum",
                metric="latency_ms",
                scope="global",
                observed=80.0,
                threshold=100.0,
                comparator="<=",
                passed=True,
                severity="block",
                policy_path="metrics.latency_ms.maximum",
                case_ids=("q1", "q2"),
            ),
            GateEvidence(
                id="slice:ja:groundedness:minimum",
                metric="groundedness",
                scope="ja",
                observed=0.6,
                threshold=0.8,
                comparator=">=",
                passed=False,
                severity="block",
                policy_path="slices.ja.metrics.groundedness.minimum",
                case_ids=("q2",),
                waived=True,
                waiver_owner="ml-platform",
                waiver_reason="migration window",
                waiver_expires_at="2026-09-01T00:00:00Z",
            ),
        ),
    )


def test_explanation_points_to_policy_cases_and_required_change():
    explanation = explain_decision(_decision())

    assert explanation.decision == "BLOCK"
    failed = explanation.items[0]
    assert failed.policy_path == "metrics.citation_coverage.max_regression"
    assert failed.case_ids == ("q2",)
    assert failed.required_change == 0.5
    assert explanation.items[1].waived is True


def test_junit_marks_blocking_failure_and_waiver_as_skipped():
    root = ET.fromstring(junit_xml(_decision()))

    assert root.attrib == {"name": "ragops: support", "tests": "3", "failures": "1", "skipped": "1"}
    assert len(root.findall(".//failure")) == 1
    assert len(root.findall(".//skipped")) == 1


def test_sarif_and_github_summary_are_bounded_and_escape_untrusted_text():
    decision = _decision()
    sarif = sarif_report(decision)
    summary = github_summary(decision, max_gates=2)

    assert sarif["version"] == "2.1.0"
    assert sarif["runs"][0]["results"][0]["ruleId"] == "global:citation_coverage:regression"
    assert "## RAGOps release gate: BLOCK" in summary
    assert len(summary.splitlines()) < 30


def test_explain_cli_renders_all_ci_formats(tmp_path, monkeypatch, capsys):
    source = tmp_path / "decision.json"
    source.write_text(json.dumps(_decision().to_dict()), encoding="utf-8")

    monkeypatch.setattr("sys.argv", ["ragops", "explain", "--input", str(source)])
    assert main() == 0
    assert json.loads(capsys.readouterr().out)["decision"] == "BLOCK"

    for output_format, suffix in (("junit", "xml"), ("sarif", "json"), ("github", "md")):
        output = tmp_path / f"report.{suffix}"
        monkeypatch.setattr(
            "sys.argv",
            [
                "ragops",
                "ci-render",
                "--input",
                str(source),
                "--format",
                output_format,
                "--output",
                str(output),
            ],
        )
        assert main() == 0
        assert output.stat().st_size > 20


@pytest.mark.parametrize(("field", "value"), [("passed", "false"), ("waived", 0), ("id", 42)])
def test_release_decision_loader_rejects_type_coercion(tmp_path, field, value):
    payload = _decision().to_dict()
    payload["gates"][0][field] = value
    source = tmp_path / "decision.json"
    source.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ContractError):
        load_release_decision(source)
