from ragops.benchmarks import scenario_summary
from ragops.config import load_evaluation_policy
from ragops.engine import evaluate
from ragops.loader import load_responses, load_scenario
from ragops.plugins import (
    AbstentionContractEvaluator,
    CitationCorrectnessEvaluator,
    ClaimSupportEvaluator,
    SourceFreshnessEvaluator,
)

SCENARIO = "scenarios/japanese_troubleshooting/benchmark-v0.2.json"
BASELINE = "scenarios/japanese_troubleshooting/benchmark-baseline.json"
FAILURE_ZOO = "scenarios/japanese_troubleshooting/failure-zoo-candidate.json"
RETRIEVAL_POISONING = "scenarios/japanese_troubleshooting/retrieval-poisoning-candidate.json"


def test_reference_benchmark_meets_published_taxonomy() -> None:
    summary = scenario_summary(load_scenario(SCENARIO))

    assert summary["case_count"] == 30
    assert len(summary["categories"]) == 9
    assert min(summary["categories"].values()) >= 3
    assert summary["languages"] == {"ja": 30}
    assert len(summary["attack_categories"]) >= 6


def test_reference_benchmark_baseline_passes() -> None:
    report = evaluate(load_scenario(SCENARIO), load_responses(BASELINE))

    assert report.passed is True
    assert report.metrics["citation_coverage"] == 1.0
    assert report.metrics["citation_precision"] == 1.0
    assert report.metrics["critical_findings"] == 0.0


def test_failure_zoo_candidate_is_blocked_with_critical_and_quality_evidence() -> None:
    report = evaluate(
        load_scenario(SCENARIO),
        load_responses(FAILURE_ZOO),
        evaluators=(SourceFreshnessEvaluator(), AbstentionContractEvaluator()),
        policy=load_evaluation_policy(
            "scenarios/japanese_troubleshooting/failure-zoo-policy.toml"
        ),
    )

    assert report.passed is False
    assert report.metrics["critical_findings"] == 3.0
    assert "critical_redteam_finding" in report.failed_gates
    assert "citation_coverage" in report.failed_gates
    assert "citation_precision" in report.failed_gates
    assert "metric_minimum:source_freshness" in report.failed_gates
    assert "metric_minimum:abstention_contract" in report.failed_gates
    rules = {finding.rule for case in report.cases for finding in case.findings}
    assert "stale_source_contract_violation" in rules
    assert "abstention_contract_violation" in rules


def test_retrieval_poisoning_candidate_is_blocked() -> None:
    report = evaluate(
        load_scenario(SCENARIO),
        load_responses(RETRIEVAL_POISONING),
        evaluators=(
            CitationCorrectnessEvaluator(),
            ClaimSupportEvaluator(),
        ),
        policy=load_evaluation_policy(
            "scenarios/japanese_troubleshooting/evaluation-policy.toml"
        ),
    )

    assert report.passed is False
    assert "citation_coverage" in report.failed_gates
    assert "citation_precision" in report.failed_gates
    assert "finding_severity:high" in report.failed_gates

    rules = {finding.rule for case in report.cases for finding in case.findings}
    assert "unsupported_citation" in rules
    assert "unsupported_claim" in rules
    assert "forbidden_output_term" in rules
