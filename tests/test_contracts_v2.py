import json
from pathlib import Path

import pytest

from ragops.cli import main
from ragops.contracts import diff_contract, migrate_contract, validate_contract
from ragops.loader import ContractError


def scenario_01_fixture() -> dict:
    return {
        "schema_version": "0.1",
        "id": "support",
        "name": "Support",
        "thresholds": {
            "citation_coverage": 1.0,
            "lexical_groundedness": 0.5,
            "max_latency_ms": 1000,
            "max_cost_usd": 0.01,
        },
        "cases": [
            {
                "id": "q1",
                "question": "What is the policy?",
                "evidence": ["Human approval is required."],
                "required_citation_ids": ["policy-1"],
            }
        ],
    }


def trace_03_fixture() -> dict:
    return {
        "case_id": "q1",
        "output": {"answer": "Human approval is required.", "citation_ids": ["policy-1"]},
        "latency_ms": 10,
        "usage": {"cost_usd": 0.001},
    }


def test_migrate_scenario_01_to_02_is_explicit_and_valid() -> None:
    source = scenario_01_fixture()

    migrated = migrate_contract(source, "scenario", "0.1", "0.2")

    assert source["schema_version"] == "0.1"
    assert migrated["schema_version"] == "0.2"
    assert migrated["thresholds"]["citation_precision"] == 0.0
    assert migrated["cases"][0]["category"] == "unspecified"
    assert migrated["cases"][0]["severity"] == "medium"
    assert migrated["cases"][0]["language"] == "und"
    result = validate_contract(migrated, "scenario")
    assert result.kind == "scenario"
    assert result.version == "0.2"


def test_migrate_trace_03_to_04_preserves_payload_and_records_migration() -> None:
    migrated = migrate_contract(trace_03_fixture(), "trace", "0.3", "0.4", question="Policy?")

    assert migrated["schema_version"] == "0.4"
    assert migrated["input"] == {"question": "Policy?"}
    assert migrated["output"]["answer"] == "Human approval is required."
    assert migrated["metadata"]["migrated_from"] == "0.3"
    assert validate_contract(migrated, "trace").version == "0.4"


def test_unknown_contract_version_fails_closed() -> None:
    with pytest.raises(ContractError, match="Unsupported scenario schema"):
        validate_contract({**scenario_01_fixture(), "schema_version": "9.9"}, "scenario")


def test_contract_diff_reports_required_field_additions() -> None:
    difference = diff_contract("scenario", "0.1", "0.2").to_dict()

    assert difference["compatibility"] == "migration-required"
    assert "thresholds.citation_precision" in difference["added_required_fields"]
    assert "cases[].severity" in difference["added_required_fields"]


def test_contract_migrate_cli_never_overwrites_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "scenario.json"
    target = tmp_path / "scenario-v02.json"
    source.write_text(json.dumps(scenario_01_fixture()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "ragops",
            "contract",
            "migrate",
            "--kind",
            "scenario",
            "--from",
            "0.1",
            "--to",
            "0.2",
            "--input",
            str(source),
            "--output",
            str(target),
        ],
    )

    assert main() == 0
    assert json.loads(source.read_text(encoding="utf-8"))["schema_version"] == "0.1"
    assert json.loads(target.read_text(encoding="utf-8"))["schema_version"] == "0.2"
    assert json.loads(capsys.readouterr().out)["output"] == str(target)


def test_contract_migrate_cli_rejects_same_input_and_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "scenario.json"
    source.write_text(json.dumps(scenario_01_fixture()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "ragops",
            "contract",
            "migrate",
            "--kind",
            "scenario",
            "--from",
            "0.1",
            "--to",
            "0.2",
            "--input",
            str(source),
            "--output",
            str(source),
        ],
    )

    with pytest.raises(SystemExit, match="must differ"):
        main()
