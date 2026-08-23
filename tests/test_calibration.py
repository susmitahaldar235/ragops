import json
import math
from pathlib import Path

import pytest

from ragops.calibration import (
    CalibrationPolicy,
    CalibrationRecord,
    HumanLabel,
    calibrate_evaluator,
    load_calibration_set,
)
from ragops.cli import main
from ragops.loader import ContractError


def _records() -> tuple[CalibrationRecord, ...]:
    return (
        CalibrationRecord("q1", 0.9, (HumanLabel("alice", 1), HumanLabel("bob", 1))),
        CalibrationRecord("q2", 0.1, (HumanLabel("alice", 1), HumanLabel("bob", 1))),
        CalibrationRecord("q3", 0.9, (HumanLabel("alice", 0), HumanLabel("bob", 0))),
        CalibrationRecord("q4", 0.1, (HumanLabel("alice", 0), HumanLabel("bob", 0))),
    )


def _policy() -> CalibrationPolicy:
    return CalibrationPolicy(
        threshold=0.5,
        minimum_coverage=1.0,
        minimum_accuracy=0.5,
        maximum_mae=0.5,
        maximum_false_pass_rate=0.25,
        minimum_agreement=0.5,
    )


def test_calibration_reports_false_decisions_and_reviewer_agreement() -> None:
    report = calibrate_evaluator("groundedness-v1", _records(), _policy())

    assert report.coverage == 1.0
    assert report.accuracy == 0.5
    assert report.mae == pytest.approx(0.5)
    assert report.false_pass_rate == 0.25
    assert report.false_block_rate == 0.25
    assert report.reviewer_agreement == 1.0
    assert report.decision == "PASS"


def test_calibration_blocks_evaluator_misaligned_with_reviewers() -> None:
    records = (
        CalibrationRecord("q1", 0.9, (HumanLabel("alice", 1), HumanLabel("bob", 1))),
        CalibrationRecord("q2", 0.9, (HumanLabel("alice", 1), HumanLabel("bob", 0))),
        CalibrationRecord("q3", 0.1, (HumanLabel("alice", 0), HumanLabel("bob", 1))),
        CalibrationRecord("q4", 0.1, (HumanLabel("alice", 0), HumanLabel("bob", 0))),
    )

    report = calibrate_evaluator("judge", records, _policy())

    assert report.reviewer_agreement == 0.0
    assert "reviewer_agreement" in report.failed_gates
    assert report.decision == "BLOCK"


def test_calibration_reports_insufficient_reviewer_overlap() -> None:
    records = (
        CalibrationRecord("q1", 0.9, (HumanLabel("alice", 1),)),
        CalibrationRecord("q2", 0.1, (HumanLabel("bob", 0),)),
    )

    report = calibrate_evaluator("judge", records, _policy())

    assert report.reviewer_agreement is None
    assert "reviewer_agreement_insufficient" in report.failed_gates
    assert report.decision == "BLOCK"


def test_calibration_rejects_duplicate_reviewer_label_for_case() -> None:
    records = (
        CalibrationRecord("q1", 0.9, (HumanLabel("alice", 1), HumanLabel("alice", 0))),
    )

    with pytest.raises(ContractError, match="duplicate reviewer"):
        calibrate_evaluator("judge", records, _policy())


@pytest.mark.parametrize("score", [math.nan, math.inf, -0.1, 1.1])
def test_calibration_rejects_invalid_automated_score(score: float) -> None:
    with pytest.raises(ContractError, match="between 0 and 1"):
        calibrate_evaluator(
            "judge", (CalibrationRecord("q1", score, (HumanLabel("alice", 1),)),), _policy()
        )


def test_load_calibration_set_and_cli(tmp_path: Path, monkeypatch, capsys) -> None:
    source = tmp_path / "calibration.json"
    output = tmp_path / "report.json"
    source.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "evaluator": "groundedness-v1",
                "policy": {
                    "threshold": 0.5,
                    "minimum_coverage": 1.0,
                    "minimum_accuracy": 0.5,
                    "maximum_mae": 0.5,
                    "maximum_false_pass_rate": 0.25,
                    "minimum_agreement": 0.5,
                },
                "records": [
                    {
                        "case_id": record.case_id,
                        "automated_score": record.automated_score,
                        "human_labels": [
                            {"reviewer": label.reviewer, "label": label.label}
                            for label in record.human_labels
                        ],
                    }
                    for record in _records()
                ],
            }
        ),
        encoding="utf-8",
    )

    loaded = load_calibration_set(source)
    assert loaded.evaluator == "groundedness-v1"
    monkeypatch.setattr(
        "sys.argv", ["ragops", "calibrate", "--input", str(source), "--output", str(output)]
    )
    assert main() == 0
    assert json.loads(output.read_text(encoding="utf-8"))["decision"] == "PASS"
    assert json.loads(capsys.readouterr().out)["decision"] == "PASS"
