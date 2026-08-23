from pathlib import Path

import pytest

from ragops.cli import main
from ragops.loader import ContractError, scenario_from_dict
from ragops.models import CaseResult, EvaluationReport
from ragops.policy_v2 import (
    PolicyGate,
    PolicyWaiver,
    ReleasePolicyV2,
    SlicePolicy,
    TailGate,
    apply_release_policy,
    load_release_policy_v2,
)
from ragops.slices import SliceSelector

NOW = "2026-08-23T00:00:00Z"


def _scenario():
    return scenario_from_dict(
        {
            "schema_version": "0.2",
            "id": "release-v2",
            "name": "Release v2",
            "thresholds": {
                "citation_coverage": 0,
                "citation_precision": 0,
                "lexical_groundedness": 0,
                "max_latency_ms": 5000,
                "max_cost_usd": 1,
            },
            "cases": [
                {
                    "id": "critical",
                    "question": "Critical?",
                    "evidence": ["Critical evidence"],
                    "required_citation_ids": ["c1"],
                    "category": "policy",
                    "severity": "critical",
                    "language": "ja",
                },
                {
                    "id": "routine",
                    "question": "Routine?",
                    "evidence": ["Routine evidence"],
                    "required_citation_ids": ["c2"],
                    "category": "faq",
                    "severity": "low",
                    "language": "en",
                },
            ],
        }
    )


def _report(critical_coverage: float, routine_coverage: float, latencies=(100, 200)):
    average = (critical_coverage + routine_coverage) / 2
    cases = (
        CaseResult("critical", critical_coverage, 1.0, 1.0, latencies[0], 0.001),
        CaseResult("routine", routine_coverage, 1.0, 1.0, latencies[1], 0.001),
    )
    return EvaluationReport(
        report_version="0.1",
        scenario_id="release-v2",
        passed=True,
        metrics={
            "citation_coverage": average,
            "citation_precision": 1.0,
            "lexical_groundedness": 1.0,
            "avg_latency_ms": sum(latencies) / 2,
            "avg_cost_usd": 0.001,
            "critical_findings": 0.0,
        },
        failed_gates=(),
        cases=cases,
    )


def _policy(*, waiver: PolicyWaiver | None = None) -> ReleasePolicyV2:
    return ReleasePolicyV2(
        minimum_cases=1,
        insufficient_evidence="block",
        metrics=(
            PolicyGate(
                metric="citation_coverage",
                direction="higher",
                minimum=0.9,
                severity="block",
            ),
        ),
        slices=(),
        tails=(),
        waivers=(waiver,) if waiver else (),
    )


def test_active_waiver_can_only_change_block_to_warn() -> None:
    waiver = PolicyWaiver(
        gate_id="global:citation_coverage:minimum",
        owner="release-owner",
        reason="bounded rollout",
        issued_at="2026-08-20T00:00:00Z",
        expires_at="2030-01-01T00:00:00Z",
    )

    decision = apply_release_policy(
        _policy(waiver=waiver), _report(1.0, 1.0), _report(0.5, 1.0), _scenario(), now=NOW
    )

    assert decision.decision == "WARN"
    assert decision.passed is False
    assert decision.gates[0].waived is True
    assert decision.gates[0].waiver_owner == "release-owner"


def test_expired_waiver_leaves_gate_blocked() -> None:
    waiver = PolicyWaiver(
        gate_id="global:citation_coverage:minimum",
        owner="release-owner",
        reason="expired",
        issued_at="2026-01-01T00:00:00Z",
        expires_at="2026-08-01T00:00:00Z",
    )

    decision = apply_release_policy(
        _policy(waiver=waiver), _report(1.0, 1.0), _report(0.5, 1.0), _scenario(), now=NOW
    )

    assert decision.decision == "BLOCK"
    assert decision.gates[0].waived is False


def test_worst_slice_blocks_even_when_global_metric_passes() -> None:
    policy = ReleasePolicyV2(
        minimum_cases=1,
        insufficient_evidence="block",
        metrics=(PolicyGate("citation_coverage", "higher", minimum=0.7),),
        slices=(
            SlicePolicy(
                selector=SliceSelector("critical", severity="critical"), minimum_cases=1
            ),
        ),
        tails=(),
        waivers=(),
    )

    decision = apply_release_policy(
        policy, _report(1.0, 1.0), _report(0.5, 1.0), _scenario(), now=NOW
    )

    assert decision.decision == "BLOCK"
    assert any(gate.id == "slice:critical:citation_coverage:minimum" for gate in decision.gates)
    failed = next(gate for gate in decision.gates if not gate.passed and gate.scope == "critical")
    assert failed.case_ids == ("critical",)


def test_insufficient_slice_evidence_fails_closed() -> None:
    policy = ReleasePolicyV2(
        minimum_cases=1,
        insufficient_evidence="block",
        metrics=(PolicyGate("citation_coverage", "higher", minimum=0.4),),
        slices=(
            SlicePolicy(
                selector=SliceSelector("critical", severity="critical"), minimum_cases=2
            ),
        ),
        tails=(),
        waivers=(),
    )

    decision = apply_release_policy(
        policy, _report(1.0, 1.0), _report(1.0, 1.0), _scenario(), now=NOW
    )

    gate = next(item for item in decision.gates if item.id == "slice:critical:minimum_cases")
    assert gate.passed is False
    assert decision.decision == "BLOCK"


def test_tail_gate_blocks_latency_p95() -> None:
    policy = ReleasePolicyV2(
        minimum_cases=1,
        insufficient_evidence="warn",
        metrics=(),
        slices=(),
        tails=(TailGate("latency_ms", 0.95, maximum=500.0),),
        waivers=(),
    )

    decision = apply_release_policy(
        policy, _report(1.0, 1.0), _report(1.0, 1.0, latencies=(100, 1000)), _scenario(), now=NOW
    )

    gate = next(item for item in decision.gates if item.id == "tail:latency_ms:p95:maximum")
    assert gate.observed == pytest.approx(955.0)
    assert decision.decision == "BLOCK"


def test_policy_loader_rejects_unknown_section(tmp_path: Path) -> None:
    path = tmp_path / "policy.toml"
    path.write_text("[release]\nminimum_cases=1\ninsufficient_evidence='block'\n[unknown]\nx=1\n")

    with pytest.raises(ContractError, match="unknown sections"):
        load_release_policy_v2(path)


def test_gate_v2_cli_returns_block_exit_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    policy = tmp_path / "policy.toml"
    policy.write_text(
        """
[release]
minimum_cases = 1
insufficient_evidence = "block"

[metrics.citation_coverage]
direction = "higher"
minimum = 1.0
max_regression = 0.0
severity = "block"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    scenario = Path("scenarios/japanese_troubleshooting/benchmark-v0.2.json")
    baseline = Path("scenarios/japanese_troubleshooting/benchmark-baseline.json")
    candidate = Path("scenarios/japanese_troubleshooting/benchmark-regressed.json")
    monkeypatch.setattr(
        "sys.argv",
        [
            "ragops",
            "gate-v2",
            "--scenario",
            str(scenario),
            "--baseline",
            str(baseline),
            "--candidate",
            str(candidate),
            "--policy",
            str(policy),
            "--now",
            NOW,
        ],
    )

    assert main() == 2
    assert '"decision": "BLOCK"' in capsys.readouterr().out
