from __future__ import annotations

import argparse
import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


class PhoenixAnnotationError(ValueError):
    """Raised when recorded Phoenix annotations cannot form a complete envelope."""


_ANNOTATION_FIELDS = {
    "id",
    "created_at",
    "updated_at",
    "source",
    "user_id",
    "name",
    "annotator_kind",
    "result",
    "metadata",
    "identifier",
    "trace_id",
}
_RESULT_FIELDS = {"label", "score", "explanation"}
_ANNOTATOR_KINDS = {"LLM", "CODE", "HUMAN"}
_CASE_METADATA_KEY = "ragops_case_id"
_METRIC_PREFIX = "phoenix"


def _read_json(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON number {value}")
            ),
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise PhoenixAnnotationError(f"Cannot load JSON from {path}: {exc}") from exc


def _case_ids(values: Any) -> tuple[str, ...]:
    if not isinstance(values, list) or not values:
        raise PhoenixAnnotationError("Expected case IDs to be a non-empty JSON array")
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise PhoenixAnnotationError("Expected every case ID to be a non-empty string")
    if any(value != value.strip() for value in values):
        raise PhoenixAnnotationError("Case IDs must not contain surrounding whitespace")
    case_ids = tuple(values)
    if len(set(case_ids)) != len(case_ids):
        raise PhoenixAnnotationError("Expected case IDs to be unique")
    return case_ids


def _payload_records(payload: Any) -> list[Any]:
    if not isinstance(payload, dict):
        raise PhoenixAnnotationError("Phoenix input must be an object")
    unknown_fields = set(payload) - {"data", "next_cursor"}
    if unknown_fields:
        raise PhoenixAnnotationError(
            f"Phoenix input has unknown fields: {sorted(unknown_fields)}"
        )
    if payload.get("next_cursor") is not None:
        raise PhoenixAnnotationError(
            "Phoenix input has an unconsumed pagination cursor; provide a complete export"
        )
    records = payload.get("data")
    if not isinstance(records, list) or not records:
        raise PhoenixAnnotationError("Phoenix input needs a non-empty data array")
    return records


def _score(record: Mapping[str, Any], index: int) -> float:
    result = record.get("result")
    if not isinstance(result, dict):
        raise PhoenixAnnotationError(f"Phoenix annotation {index} needs a result object")
    unknown_fields = set(result) - _RESULT_FIELDS
    if unknown_fields:
        raise PhoenixAnnotationError(
            f"Phoenix annotation {index} result has unknown fields: {sorted(unknown_fields)}"
        )
    value = result.get("score")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PhoenixAnnotationError(f"Phoenix annotation {index} needs a numeric score")
    try:
        score = float(value)
    except (OverflowError, ValueError) as exc:
        raise PhoenixAnnotationError(
            f"Phoenix annotation {index} score must be a finite number"
        ) from exc
    if not math.isfinite(score):
        raise PhoenixAnnotationError(f"Phoenix annotation {index} score must be finite")
    return score


def convert_annotations(
    payload: Mapping[str, Any],
    expected_case_ids: Sequence[str],
    *,
    annotation_name: str,
) -> dict[str, Any]:
    """Convert a complete Phoenix trace-annotation response to an envelope.

    Phoenix owns the annotation's score meaning, scale, and direction. This
    function only joins a recorded score to an explicit RAGOps case ID and
    copies the numeric value without calibration.
    """

    expected = _case_ids(list(expected_case_ids))
    annotation_name = annotation_name.strip()
    if not annotation_name:
        raise PhoenixAnnotationError("Annotation name must be non-empty")
    records = _payload_records(payload)
    metrics_by_case: dict[str, float] = {}

    for index, raw_record in enumerate(records):
        if not isinstance(raw_record, dict):
            raise PhoenixAnnotationError(f"Phoenix annotation {index} must be an object")
        unknown_fields = set(raw_record) - _ANNOTATION_FIELDS
        if unknown_fields:
            raise PhoenixAnnotationError(
                f"Phoenix annotation {index} has unknown fields: {sorted(unknown_fields)}"
            )
        trace_id = raw_record.get("trace_id")
        if not isinstance(trace_id, str) or not trace_id.strip():
            raise PhoenixAnnotationError(
                f"Phoenix annotation {index} needs a non-empty trace_id"
            )
        if raw_record.get("name") != annotation_name:
            raise PhoenixAnnotationError(
                f"Phoenix annotation {index} must use annotation {annotation_name!r}"
            )
        annotator_kind = raw_record.get("annotator_kind")
        if annotator_kind not in _ANNOTATOR_KINDS:
            raise PhoenixAnnotationError(
                f"Phoenix annotation {index} has an invalid annotator_kind"
            )
        metadata = raw_record.get("metadata")
        if not isinstance(metadata, dict):
            raise PhoenixAnnotationError(
                f"Phoenix annotation {index} needs metadata.{_CASE_METADATA_KEY}"
            )
        case_id = metadata.get(_CASE_METADATA_KEY)
        if not isinstance(case_id, str) or not case_id.strip():
            raise PhoenixAnnotationError(
                f"Phoenix annotation {index} needs metadata.{_CASE_METADATA_KEY}"
            )
        if case_id != case_id.strip():
            raise PhoenixAnnotationError(
                f"Phoenix annotation {index} case ID must not contain surrounding whitespace"
            )
        if case_id in metrics_by_case:
            raise PhoenixAnnotationError(f"Phoenix case IDs must be unique: {case_id!r}")
        metrics_by_case[case_id] = _score(raw_record, index)

    supplied = set(metrics_by_case)
    expected_set = set(expected)
    if supplied != expected_set:
        missing = sorted(expected_set - supplied)
        unknown = sorted(supplied - expected_set)
        raise PhoenixAnnotationError(
            f"Phoenix case coverage mismatch; missing={missing}, unknown={unknown}"
        )

    return {
        "schema_version": "0.1",
        "provider": "custom",
        "records": [
            {
                "case_id": case_id,
                "metrics": {f"{_METRIC_PREFIX}.{annotation_name}": metrics_by_case[case_id]},
            }
            for case_id in sorted(metrics_by_case)
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert recorded Phoenix trace scores to a RAGOps metric envelope"
    )
    parser.add_argument("--input", required=True, type=Path, help="Phoenix JSON response")
    parser.add_argument(
        "--case-ids",
        required=True,
        type=Path,
        help="JSON array containing the complete expected RAGOps case IDs",
    )
    parser.add_argument("--output", required=True, type=Path, help="RAGOps JSON envelope")
    parser.add_argument("--annotation-name", required=True, help="Phoenix annotation name")
    args = parser.parse_args(argv)

    try:
        envelope = convert_annotations(
            _read_json(args.input),
            _read_json(args.case_ids),
            annotation_name=args.annotation_name,
        )
        args.output.write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")
    except (OSError, PhoenixAnnotationError) as exc:
        parser.exit(2, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
