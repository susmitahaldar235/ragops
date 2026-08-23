from __future__ import annotations

import json

import pytest

from ragops.adapter_sdk import AdapterContext, discover_adapters
from ragops.adapters.import_profiles import convert_import
from ragops.cli import main
from ragops.loader import ContractError


@pytest.mark.parametrize(
    ("profile", "payload"),
    [
        ("ragas", {"records": [{"case_id": "q1", "faithfulness": 0.91}]}),
        ("deepeval", {"test_results": [{"name": "q1", "metrics": [{"name": "faithfulness", "score": 0.92}]}]}),
        ("phoenix", {"evaluations": [{"span_id": "q1", "name": "groundedness", "score": 0.93}]}),
        ("langsmith", {"runs": [{"reference_example_id": "q1", "feedback": [{"key": "correctness", "score": 0.94}]}]}),
        ("mlflow", {"results": [{"request_id": "q1", "metrics": {"relevance": 0.95}}]}),
        ("promptfoo", {"results": [{"vars": {"case_id": "q1"}, "scores": {"faithfulness": 0.96}}]}),
    ],
)
def test_builtin_profiles_normalize_without_vendor_sdks(profile, payload):
    output = convert_import(profile, payload, AdapterContext(case_ids=("q1",)))

    assert output.records[0]["case_id"] == "q1"
    assert output.records[0]["metrics"]
    assert output.provenance["producer"] == profile
    assert output.provenance["adapter_version"] == "1.0"


def test_import_preserves_unmapped_fields_and_reports_missing_cases():
    output = convert_import(
        "ragas",
        {"records": [{"case_id": "q1", "faithfulness": 0.9, "note": "manual"}]},
        AdapterContext(case_ids=("q1", "q2")),
    )

    assert output.provenance["unmapped_fields"] == ["note"]
    assert output.warnings == ("missing case IDs: q2",)


def test_unknown_case_and_non_finite_score_fail_closed():
    with pytest.raises(ContractError, match="unknown case ID"):
        convert_import(
            "ragas",
            {"records": [{"case_id": "q9", "faithfulness": 0.9}]},
            AdapterContext(case_ids=("q1",)),
        )
    with pytest.raises(ContractError, match="finite numeric"):
        convert_import(
            "mlflow",
            {"results": [{"request_id": "q1", "metrics": {"score": float("nan")}}]},
            AdapterContext(),
        )


def test_adapter_discovery_includes_builtins_without_loading_vendors():
    names = [item.name for item in discover_adapters(include_entry_points=False)]

    assert names == ["custom", "deepeval", "langsmith", "mlflow", "phoenix", "promptfoo", "ragas"]


def test_adapter_convert_cli_writes_portable_envelope(tmp_path, monkeypatch):
    source = tmp_path / "source.json"
    output = tmp_path / "portable.json"
    source.write_text(
        json.dumps({"results": [{"request_id": "q1", "metrics": {"relevance": 0.95}}]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "ragops", "adapter", "convert", "--profile", "mlflow", "--input", str(source),
            "--case-id", "q1", "--output", str(output),
        ],
    )

    assert main() == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "0.1"
    assert payload["provider"] == "mlflow"
    assert payload["records"] == [{"case_id": "q1", "metrics": {"relevance": 0.95}}]
    assert payload["provenance"]["producer"] == "mlflow"
