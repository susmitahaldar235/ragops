from __future__ import annotations

import hashlib
import json

import pytest

from ragops.cli import main
from ragops.governance import GovernanceStore


def _digest(value: str = "artifact") -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def test_artifact_state_machine_and_audit_are_transactional(tmp_path):
    store = GovernanceStore(tmp_path / "governance.db")
    store.register_artifact(
        "eval-1",
        kind="release-decision",
        digest=_digest(),
        public_metadata={"scenario_id": "support"},
        blinded_metadata={"candidate": "model-b"},
        actor="ci",
    )

    with pytest.raises(ValueError, match="draft -> accepted"):
        store.transition("eval-1", "accepted", actor="owner")

    store.transition("eval-1", "reviewed", actor="owner")
    store.record_review("eval-1", reviewer="alice", verdict="approve", note="evidence holds")
    store.transition("eval-1", "accepted", actor="owner")
    store.transition("eval-1", "superseded", actor="ci")

    assert store.get_artifact("eval-1")["state"] == "superseded"
    assert [item["action"] for item in store.audit_events("eval-1")] == [
        "artifact.registered",
        "artifact.transitioned",
        "review.recorded",
        "artifact.transitioned",
        "artifact.transitioned",
    ]


def test_blind_queue_reveals_candidate_only_after_reviewer_votes(tmp_path):
    store = GovernanceStore(tmp_path / "governance.db")
    store.register_artifact(
        "eval-1",
        kind="release-decision",
        digest=_digest(),
        public_metadata={"scenario_id": "support"},
        blinded_metadata={"candidate": "model-b", "provider": "vendor-x"},
        actor="ci",
    )
    store.transition("eval-1", "reviewed", actor="owner")

    before = store.review_queue("alice")[0]
    assert before["metadata"] == {"scenario_id": "support"}
    assert before["blinded"] is True

    store.record_review("eval-1", reviewer="alice", verdict="block", note="weak slice")

    after = store.review_queue("alice")[0]
    assert after["metadata"]["candidate"] == "model-b"
    assert after["blinded"] is False
    assert store.review_queue("bob")[0]["blinded"] is True


def test_reviews_are_append_only_and_acceptance_requires_approval(tmp_path):
    store = GovernanceStore(tmp_path / "governance.db")
    store.register_artifact(
        "eval-1", kind="decision", digest=_digest(), public_metadata={}, blinded_metadata={}, actor="ci"
    )
    store.transition("eval-1", "reviewed", actor="owner")
    store.record_review("eval-1", reviewer="alice", verdict="block")

    with pytest.raises(ValueError, match="already reviewed"):
        store.record_review("eval-1", reviewer="alice", verdict="approve")
    with pytest.raises(ValueError, match="approval review"):
        store.transition("eval-1", "accepted", actor="owner")


def test_waiver_is_audited_and_must_expire_after_issue(tmp_path):
    store = GovernanceStore(tmp_path / "governance.db")

    waiver_id = store.create_waiver(
        gate_id="slice:ja:coverage",
        owner="ml-platform",
        reason="migration",
        issued_at="2026-08-23T00:00:00Z",
        expires_at="2026-09-01T00:00:00Z",
        actor="release-manager",
    )

    assert store.list_waivers()[0]["id"] == waiver_id
    assert store.audit_events()[0]["action"] == "waiver.created"
    with pytest.raises(ValueError, match="expire after"):
        store.create_waiver(
            gate_id="bad", owner="x", reason="x",
            issued_at="2026-09-01T00:00:00Z", expires_at="2026-08-23T00:00:00Z", actor="x",
        )


def test_governance_cli_registers_and_reads_artifact(tmp_path, monkeypatch, capsys):
    database = tmp_path / "governance.db"
    metadata = tmp_path / "metadata.json"
    metadata.write_text(json.dumps({"scenario_id": "support"}), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "ragops", "governance", "register", "--store", str(database), "--artifact-id", "eval-1",
            "--kind", "decision", "--digest", _digest(), "--metadata", str(metadata), "--actor", "ci",
        ],
    )

    assert main() == 0
    assert json.loads(capsys.readouterr().out)["state"] == "draft"

    monkeypatch.setattr(
        "sys.argv", ["ragops", "governance", "audit", "--store", str(database), "--artifact-id", "eval-1"]
    )
    assert main() == 0
    assert json.loads(capsys.readouterr().out)["events"][0]["action"] == "artifact.registered"
