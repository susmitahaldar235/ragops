from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import zipfile
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("local_release", Path("scripts/local_release.py"))
assert SPEC and SPEC.loader
local_release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(local_release)


def test_chatgpt_plugin_bundle_is_deterministic_and_self_contained(tmp_path, monkeypatch):
    monkeypatch.setattr(local_release, "DIST", tmp_path)

    first = local_release.build_plugin_bundle("2.0.0")
    first_bytes = first.read_bytes()
    second = local_release.build_plugin_bundle("2.0.0")

    assert second.read_bytes() == first_bytes
    with zipfile.ZipFile(first) as archive:
        names = archive.namelist()
        manifest = json.loads(archive.read(".codex-plugin/plugin.json"))
    assert manifest["version"] == "2.0.0"
    assert "skills/evaluate-ai-release/SKILL.md" in names
    assert "skills/evaluate-ai-release/scripts/run_ragops.py" in names
    assert "skills/evaluate-ai-release/scripts/vendor/ragops/cli.py" in names
    assert "skills/evaluate-ai-release/scripts/vendor/ragops/schemas/evidence-bundle-1.0.schema.json" in names
    assert "skills/evaluate-ai-release/references/fixtures/japanese_troubleshooting/scenario.json" in names
    assert not any("__pycache__" in name or name.endswith(".pyc") for name in names)


def test_extracted_chatgpt_bundle_runs_without_install(tmp_path, monkeypatch):
    monkeypatch.setattr(local_release, "DIST", tmp_path)
    bundle = local_release.build_plugin_bundle("2.0.0")
    extracted = tmp_path / "plugin"
    with zipfile.ZipFile(bundle) as archive:
        archive.extractall(extracted)
    runner = extracted / "skills/evaluate-ai-release/scripts/run_ragops.py"

    result = subprocess.run(
        [sys.executable, str(runner), "--version"],
        cwd=extracted,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == "ragops 2.0.0"
