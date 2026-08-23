import math

import pytest

from ragops.distribution import holm_adjust, minimum_paired_sample, paired_effect, quantile
from ragops.loader import scenario_from_dict
from ragops.models import CaseResult, EvaluationReport
from ragops.slices import SliceSelector, summarize_slices


def _scenario():
    return scenario_from_dict(
        {
            "schema_version": "0.2",
            "id": "slices",
            "name": "Slice checks",
            "thresholds": {
                "citation_coverage": 0,
                "citation_precision": 0,
                "lexical_groundedness": 0,
                "max_latency_ms": 1000,
                "max_cost_usd": 1,
            },
            "cases": [
                {
                    "id": "ja-critical",
                    "question": "Q1",
                    "evidence": ["E1"],
                    "required_citation_ids": ["e1"],
                    "category": "policy",
                    "severity": "critical",
                    "language": "ja",
                    "tags": ["production"],
                },
                {
                    "id": "en-low",
                    "question": "Q2",
                    "evidence": ["E2"],
                    "required_citation_ids": ["e2"],
                    "category": "faq",
                    "severity": "low",
                    "language": "en",
                    "tags": ["synthetic"],
                },
            ],
        }
    )


def _report() -> EvaluationReport:
    return EvaluationReport(
        report_version="0.1",
        scenario_id="slices",
        passed=False,
        metrics={},
        failed_gates=("citation_coverage",),
        cases=(
            CaseResult("ja-critical", 0.0, 0.5, 0.4, 900, 0.02),
            CaseResult("en-low", 1.0, 1.0, 1.0, 100, 0.001),
        ),
    )


def test_slice_summary_exposes_worst_language_and_severity_slice() -> None:
    summaries = summarize_slices(
        _scenario(),
        _report(),
        (SliceSelector("ja-critical", language="ja", severity="critical"),),
    )

    assert summaries[0].case_ids == ("ja-critical",)
    assert summaries[0].count == 1
    assert summaries[0].metrics["citation_coverage"] == 0.0
    assert summaries[0].metrics["latency_ms"] == 900.0


def test_slice_selector_combines_category_and_tag() -> None:
    summaries = summarize_slices(
        _scenario(),
        _report(),
        (SliceSelector("production-policy", category="policy", tags=("production",)),),
    )

    assert summaries[0].case_ids == ("ja-critical",)


def test_empty_slice_has_no_fabricated_metrics() -> None:
    summary = summarize_slices(
        _scenario(), _report(), (SliceSelector("missing", language="vi"),)
    )[0]

    assert summary.count == 0
    assert summary.metrics == {}


def test_quantile_and_holm_are_hand_checkable() -> None:
    assert quantile((0.0, 10.0, 20.0, 30.0), 0.5) == 15.0
    assert holm_adjust({"a": 0.01, "b": 0.04, "c": 0.03}) == {
        "a": pytest.approx(0.03),
        "b": pytest.approx(0.06),
        "c": pytest.approx(0.06),
    }


def test_paired_effect_uses_candidate_minus_baseline() -> None:
    result = paired_effect((1.0, 2.0, 4.0), (2.0, 4.0, 5.0))

    assert result.mean_delta == pytest.approx(4 / 3)
    assert result.median_delta == 1.0
    assert result.standardized_effect == pytest.approx(2.309401076758503)


def test_minimum_sample_estimate_is_deterministic() -> None:
    assert minimum_paired_sample(effect=0.5, alpha=0.05, power=0.8) == 32


@pytest.mark.parametrize("values", [(), (math.nan,), (math.inf,)])
def test_quantile_rejects_empty_or_nonfinite_values(values: tuple[float, ...]) -> None:
    with pytest.raises(ValueError):
        quantile(values, 0.5)


def test_distribution_rejects_invalid_probability() -> None:
    with pytest.raises(ValueError, match="probability"):
        quantile((1.0,), 1.1)
