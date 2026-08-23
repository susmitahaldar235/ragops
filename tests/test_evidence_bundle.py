import json
import os
from pathlib import Path

import pytest

from ragops.cli import main
from ragops.evidence import create_evidence_bundle, verify_evidence_bundle
from ragops.loader import ContractError

CREATED_AT = "2026-08-23T00:00:00Z"


def test_evidence_bundle_is_reproducible_and_detects_tampering(tmp_path: Path) -> None:
    source = tmp_path / "report.json"
    source.write_text('{"passed":false}\n', encoding="utf-8")

    first = create_evidence_bundle(
        tmp_path / "one",
        {"report": source},
        "BLOCK",
        ("synthetic benchmark",),
        CREATED_AT,
        {"commit": "abc123"},
    )
    second = create_evidence_bundle(
        tmp_path / "two",
        {"report": source},
        "BLOCK",
        ("synthetic benchmark",),
        CREATED_AT,
        {"commit": "abc123"},
    )

    assert first.canonical_bytes() == second.canonical_bytes()
    bundled = tmp_path / "one" / first.artifacts[0].path
    bundled.write_bytes(b"X" * first.artifacts[0].bytes)
    with pytest.raises(ContractError, match="digest mismatch"):
        verify_evidence_bundle(tmp_path / "one")


def test_evidence_bundle_verifies_complete_artifacts(tmp_path: Path) -> None:
    report = tmp_path / "release-report.md"
    report.write_text("# BLOCK\n", encoding="utf-8")
    create_evidence_bundle(
        tmp_path / "evidence",
        {"release_report": report},
        "BLOCK",
        ("synthetic", "not production adoption"),
        CREATED_AT,
        {},
    )

    verified = verify_evidence_bundle(tmp_path / "evidence")

    assert verified.decision == "BLOCK"
    assert verified.artifacts[0].logical_name == "release_report"
    assert verified.artifacts[0].bytes == len(b"# BLOCK\n")


def test_evidence_verification_rejects_manifest_path_traversal(tmp_path: Path) -> None:
    report = tmp_path / "report.json"
    report.write_text("{}", encoding="utf-8")
    create_evidence_bundle(
        tmp_path / "evidence", {"report": report}, "PASS", ("synthetic",), CREATED_AT, {}
    )
    path = tmp_path / "evidence" / "manifest.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["artifacts"][0]["path"] = "../report.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ContractError, match="artifact path"):
        verify_evidence_bundle(tmp_path / "evidence")


def test_evidence_verification_rejects_undeclared_file(tmp_path: Path) -> None:
    report = tmp_path / "report.json"
    report.write_text("{}", encoding="utf-8")
    create_evidence_bundle(
        tmp_path / "evidence", {"report": report}, "PASS", ("synthetic",), CREATED_AT, {}
    )
    (tmp_path / "evidence" / "artifacts" / "extra.txt").write_text("extra", encoding="utf-8")

    with pytest.raises(ContractError, match="undeclared files"):
        verify_evidence_bundle(tmp_path / "evidence")


def test_evidence_creation_rejects_invalid_decision(tmp_path: Path) -> None:
    report = tmp_path / "report.json"
    report.write_text("{}", encoding="utf-8")

    with pytest.raises(ContractError, match="PASS, WARN, or BLOCK"):
        create_evidence_bundle(
            tmp_path / "evidence", {"report": report}, "FAIL", ("synthetic",), CREATED_AT, {}
        )


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlinks are unavailable")
def test_evidence_creation_rejects_symlinked_artifact(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    source.write_text("{}", encoding="utf-8")
    linked = tmp_path / "linked.json"
    linked.symlink_to(source)

    with pytest.raises(ContractError, match="regular non-symlink"):
        create_evidence_bundle(
            tmp_path / "evidence", {"report": linked}, "PASS", ("synthetic",), CREATED_AT, {}
        )


def test_evidence_verification_rejects_unknown_schema_version(tmp_path: Path) -> None:
    report = tmp_path / "report.json"
    report.write_text("{}", encoding="utf-8")
    create_evidence_bundle(
        tmp_path / "evidence", {"report": report}, "PASS", ("synthetic",), CREATED_AT, {}
    )
    path = tmp_path / "evidence" / "manifest.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["schema_version"] = "9.9"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ContractError, match="Unsupported evidence bundle schema"):
        verify_evidence_bundle(tmp_path / "evidence")


def test_evidence_cli_creates_and_verifies_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    report = tmp_path / "report.json"
    report.write_text("{}", encoding="utf-8")
    bundle = tmp_path / "bundle"
    monkeypatch.setattr(
        "sys.argv",
        [
            "ragops",
            "evidence",
            "create",
            "--bundle",
            str(bundle),
            "--decision",
            "PASS",
            "--artifact",
            f"report={report}",
            "--limitation",
            "synthetic",
            "--created-at",
            CREATED_AT,
        ],
    )
    assert main() == 0
    assert json.loads(capsys.readouterr().out)["decision"] == "PASS"

    monkeypatch.setattr("sys.argv", ["ragops", "evidence", "verify", "--bundle", str(bundle)])
    assert main() == 0
    assert json.loads(capsys.readouterr().out)["verified"] is True
