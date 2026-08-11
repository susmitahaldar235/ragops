import json
from pathlib import Path

import pytest

from examples.phoenix_recorded_scores.adapter import (
    PhoenixAnnotationError,
    convert_annotations,
    main,
)
from ragops.adapters.external_metrics import external_metric_envelope_from_dict

EXAMPLE_ROOT = Path("examples/phoenix_recorded_scores")


def _load(name: str) -> object:
    return json.loads((EXAMPLE_ROOT / name).read_text(encoding="utf-8"))


def test_phoenix_example_writes_expected_external_metrics(tmp_path: Path) -> None:
    output = tmp_path / "external-metrics.json"

    assert (
        main(
            [
                "--input",
                str(EXAMPLE_ROOT / "annotations.json"),
                "--case-ids",
                str(EXAMPLE_ROOT / "case_ids.json"),
                "--annotation-name",
                "answer_quality",
                "--output",
                str(output),
            ]
        )
        == 0
    )

    actual = json.loads(output.read_text(encoding="utf-8"))
    assert actual == _load("expected-envelope.json")
    envelope = external_metric_envelope_from_dict(actual)
    assert envelope.provider == "custom"
    assert envelope.metrics_by_case["support-001"]["phoenix.answer_quality"] == pytest.approx(87.5)
    assert envelope.metrics_by_case["support-002"]["phoenix.answer_quality"] == pytest.approx(42.0)


def test_phoenix_example_requires_complete_case_coverage() -> None:
    payload = _load("annotations.json")

    with pytest.raises(PhoenixAnnotationError, match="coverage mismatch"):
        convert_annotations(
            payload,
            ["support-001", "support-002", "support-003"],
            annotation_name="answer_quality",
        )


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda data: data["data"][0]["result"].update(score="87.5"), "numeric score"),
        (lambda data: data["data"][0]["result"].update(score=float("nan")), "must be finite"),
        (
            lambda data: data["data"][0]["metadata"].update(ragops_case_id="support-999"),
            "coverage mismatch",
        ),
        (
            lambda data: data["data"][0]["metadata"].update(ragops_case_id=" support-001"),
            "surrounding whitespace",
        ),
        (
            lambda data: data["data"][0]["metadata"].update(ragops_case_id="support-001 "),
            "surrounding whitespace",
        ),
        (lambda data: data["data"].append(data["data"][0].copy()), "case IDs must be unique"),
        (lambda data: data.update(next_cursor="next-page"), "pagination cursor"),
    ],
)
def test_phoenix_example_rejects_invalid_or_partial_records(change, message: str) -> None:
    payload = _load("annotations.json")
    change(payload)

    with pytest.raises(PhoenixAnnotationError, match=message):
        convert_annotations(
            payload,
            ["support-001", "support-002"],
            annotation_name="answer_quality",
        )


def test_phoenix_example_rejects_non_canonical_expected_case_ids() -> None:
    with pytest.raises(PhoenixAnnotationError, match="surrounding whitespace"):
        convert_annotations(
            _load("annotations.json"),
            ["support-001 ", "support-002"],
            annotation_name="answer_quality",
        )


def test_phoenix_cli_reports_invalid_input_without_traceback(capsys, tmp_path: Path) -> None:
    invalid_input = tmp_path / "invalid.json"
    invalid_input.write_text(json.dumps({"data": [], "next_cursor": None}), encoding="utf-8")

    with pytest.raises(SystemExit) as error:
        main(
            [
                "--input",
                str(invalid_input),
                "--case-ids",
                str(EXAMPLE_ROOT / "case_ids.json"),
                "--annotation-name",
                "answer_quality",
                "--output",
                str(tmp_path / "output.json"),
            ]
        )

    assert error.value.code == 2
    stderr = capsys.readouterr().err
    assert stderr.startswith("error: ")
    assert "Traceback" not in stderr


def test_phoenix_cli_reports_output_io_error_without_traceback(capsys, tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as error:
        main(
            [
                "--input",
                str(EXAMPLE_ROOT / "annotations.json"),
                "--case-ids",
                str(EXAMPLE_ROOT / "case_ids.json"),
                "--annotation-name",
                "answer_quality",
                "--output",
                str(tmp_path / "missing" / "output.json"),
            ]
        )

    assert error.value.code == 2
    stderr = capsys.readouterr().err
    assert stderr.startswith("error: ")
    assert "Traceback" not in stderr
