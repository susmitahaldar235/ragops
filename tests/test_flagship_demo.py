from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from ragops.cli import main
from ragops.demo import write_demo
from ragops.evidence import verify_evidence_bundle


@pytest.mark.parametrize("profile", ["executive", "engineer", "auditor"])
def test_profiles_share_one_synthetic_block_decision(tmp_path: Path, profile: str) -> None:
    output = tmp_path / profile
    summary = write_demo(output, scenario_id="japanese-troubleshooting", profile=profile)

    assert summary["candidate_decision"] == "BLOCK"
    assert summary["evidence_classification"] == "synthetic"
    assert summary["profile"] == profile
    assert verify_evidence_bundle(output / "evidence").decision == "BLOCK"
    profile_text = (output / "profile-summary.md").read_text(encoding="utf-8")
    assert "synthetic" in profile_text.casefold()
    assert "demonstrates production adoption" not in profile_text.casefold()


def test_demo_formats_share_stable_gate_ids_and_metrics(tmp_path: Path) -> None:
    output = tmp_path / "demo"
    summary = write_demo(output, profile="engineer")
    decision = json.loads((output / "decision.json").read_text(encoding="utf-8"))
    comparison = json.loads((output / "comparison.json").read_text(encoding="utf-8"))
    sarif = json.loads((output / "release.sarif").read_text(encoding="utf-8"))
    junit = ET.parse(output / "junit.xml").getroot()
    github = (output / "github-summary.md").read_text(encoding="utf-8")

    gate_ids = [gate["id"] for gate in decision["gates"]]
    assert gate_ids == summary["failed_gates"]
    assert [item["ruleId"] for item in sarif["runs"][0]["results"]] == gate_ids
    assert [item.attrib["name"] for item in junit.findall("testcase")] == gate_ids
    assert all(gate_id in github for gate_id in gate_ids)
    assert comparison["baseline"]["metrics"]["citation_coverage"] == 1.0
    assert comparison["candidate"]["metrics"]["citation_coverage"] == 0.5
    assert comparison["candidate"]["metrics"]["citation_precision"] == 0.5
    assert comparison["candidate"]["metrics"]["lexical_groundedness"] == 0.6


def test_demo_evidence_declares_limitations_and_verifies_after_force(tmp_path: Path) -> None:
    output = tmp_path / "demo"
    write_demo(output)
    write_demo(output, force=True)

    manifest = verify_evidence_bundle(output / "evidence")
    logical_names = {item.logical_name for item in manifest.artifacts}
    assert {"scenario", "baseline", "candidate", "comparison", "decision", "html", "junit", "sarif"} <= logical_names
    assert manifest.metadata["evidence_classification"] == "synthetic"
    assert any("not production adoption" in item.casefold() for item in manifest.limitations)


def test_demo_cli_accepts_profile(monkeypatch, capsys, tmp_path: Path) -> None:
    output = tmp_path / "auditor"
    monkeypatch.setattr(
        "sys.argv", ["ragops", "demo", "--profile", "auditor", "--output", str(output)]
    )

    assert main() == 0
    assert json.loads(capsys.readouterr().out)["profile"] == "auditor"
