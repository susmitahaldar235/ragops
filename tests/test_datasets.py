import json
from pathlib import Path

import pytest

from ragops.cli import main
from ragops.datasets import (
    create_dataset_manifest,
    diff_dataset_manifests,
    load_dataset_manifest,
    validate_dataset_manifest,
    write_dataset_manifest,
)
from ragops.loader import ContractError


def _case(case_id: str, question: str, *, reviewed: bool = True) -> dict:
    return {
        "id": case_id,
        "question": question,
        "evidence": ["Human approval is required."],
        "required_citation_ids": ["policy-1"],
        "category": "policy",
        "severity": "critical",
        "language": "en",
        "tags": ["approval"],
        "source": "support-export-2026-08",
        "reviewed": reviewed,
    }


def test_dataset_validation_quarantines_cross_split_leakage() -> None:
    manifest = create_dataset_manifest(
        "support",
        "1.0",
        (_case("a", "Reset password"), _case("b", "  RESET   PASSWORD ")),
        splits={"train": ("a",), "eval": ("b",)},
        source_classification="production-derived",
        owners=("eval-team",),
    )

    issues = validate_dataset_manifest(manifest)

    assert {item.code for item in issues} >= {"normalized_content_leakage"}
    leakage = next(item for item in issues if item.code == "normalized_content_leakage")
    assert leakage.case_ids == ("a", "b")


def test_production_case_requires_review_before_promotion() -> None:
    manifest = create_dataset_manifest(
        "support",
        "1.0",
        (_case("a", "Reset password", reviewed=False),),
        splits={"eval": ("a",)},
        source_classification="production-derived",
        owners=("eval-team",),
    )

    assert "review_required" in {item.code for item in validate_dataset_manifest(manifest)}


def test_dataset_validation_enforces_minimum_slice_coverage() -> None:
    manifest = create_dataset_manifest(
        "support",
        "1.0",
        (_case("a", "Reset password"),),
        splits={"eval": ("a",)},
        source_classification="synthetic",
        owners=("eval-team",),
    )

    issues = validate_dataset_manifest(manifest, minimum_slice_counts={"severity=critical": 2})

    issue = next(item for item in issues if item.code == "slice_coverage")
    assert issue.observed == 1
    assert issue.required == 2


def test_dataset_diff_is_deterministic() -> None:
    before = create_dataset_manifest(
        "support",
        "1.0",
        (_case("a", "Reset password"), _case("b", "Billing")),
        splits={"eval": ("a", "b")},
        source_classification="synthetic",
        owners=("eval-team",),
    )
    after = create_dataset_manifest(
        "support",
        "1.1",
        (_case("a", "Reset password safely"), _case("c", "Shipping")),
        splits={"eval": ("a", "c")},
        source_classification="synthetic",
        owners=("eval-team",),
    )

    difference = diff_dataset_manifests(before, after)

    assert difference.added_case_ids == ("c",)
    assert difference.removed_case_ids == ("b",)
    assert difference.changed_case_ids == ("a",)


def test_dataset_creation_rejects_duplicate_case_ids() -> None:
    with pytest.raises(ContractError, match="case IDs must be unique"):
        create_dataset_manifest(
            "support",
            "1.0",
            (_case("a", "One"), _case("a", "Two")),
            splits={"eval": ("a",)},
            source_classification="synthetic",
            owners=("eval-team",),
        )


def test_dataset_manifest_round_trip_and_cli_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest = create_dataset_manifest(
        "support",
        "1.0",
        (_case("a", "Reset password"),),
        splits={"eval": ("a",)},
        source_classification="synthetic",
        owners=("eval-team",),
    )
    path = tmp_path / "dataset.json"
    write_dataset_manifest(path, manifest)

    assert load_dataset_manifest(path) == manifest
    monkeypatch.setattr("sys.argv", ["ragops", "dataset", "validate", "--manifest", str(path)])
    assert main() == 0
    assert json.loads(capsys.readouterr().out)["valid"] is True


def test_dataset_cli_creates_and_diffs_manifests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "dataset.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "ragops",
            "dataset",
            "create",
            "--scenario",
            "scenarios/japanese_troubleshooting/scenario.json",
            "--dataset-id",
            "support",
            "--version",
            "1.0",
            "--source-classification",
            "synthetic",
            "--owner",
            "eval-team",
            "--split",
            "eval=error-e42,escalation-e42",
            "--reviewed",
            "--output",
            str(output),
        ],
    )
    assert main() == 0
    assert json.loads(capsys.readouterr().out)["dataset_id"] == "support"

    monkeypatch.setattr(
        "sys.argv",
        ["ragops", "dataset", "diff", "--before", str(output), "--after", str(output)],
    )
    assert main() == 0
    assert json.loads(capsys.readouterr().out)["changed_case_ids"] == []
