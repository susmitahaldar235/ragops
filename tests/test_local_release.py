import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("local_release", Path("scripts/local_release.py"))
assert SPEC and SPEC.loader
local_release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(local_release)


def test_tag_must_match_package_version() -> None:
    assert local_release.assert_tag(local_release.milestone_tag()) == "v2.0.0"


def test_checksum_manifest_is_deterministic(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(local_release, "DIST", tmp_path)
    artifact = tmp_path / "artifact.whl"
    artifact.write_bytes(b"ragops")
    manifest = local_release.checksums([artifact])
    assert manifest.read_text().endswith("  artifact.whl\n")
    assert len(manifest.read_text().split()[0]) == 64
    local_release.verify_checksums(tmp_path)


def test_checksum_verification_rejects_tampering(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(local_release, "DIST", tmp_path)
    artifact = tmp_path / "artifact.whl"
    artifact.write_bytes(b"ragops")
    local_release.checksums([artifact])
    artifact.write_bytes(b"tampered")
    try:
        local_release.verify_checksums(tmp_path)
    except SystemExit as error:
        assert "checksum mismatch" in str(error)
    else:
        raise AssertionError("tampered artifact must be rejected")


def test_checksum_verification_rejects_path_traversal(tmp_path) -> None:
    (tmp_path / "SHA256SUMS").write_text(f"{'0' * 64}  ../outside.whl\n")
    try:
        local_release.verify_checksums(tmp_path)
    except SystemExit as error:
        assert "invalid checksum target" in str(error)
    else:
        raise AssertionError("checksum target must stay inside release directory")


def test_pypi_requires_explicit_token(monkeypatch) -> None:
    monkeypatch.delenv("PYPI_API_TOKEN", raising=False)
    try:
        local_release.pypi(local_release.milestone_tag(), True)
    except SystemExit as error:
        assert "PYPI_API_TOKEN" in str(error)
    else:
        raise AssertionError("publish must fail closed without a token")


def test_environment_tool_prefers_active_python_scripts_directory(tmp_path, monkeypatch) -> None:
    scripts = tmp_path / "bin"
    scripts.mkdir()
    python = scripts / "python"
    python.touch()
    ruff = scripts / "ruff"
    ruff.touch()
    monkeypatch.setattr(local_release.sys, "executable", str(python))

    assert local_release.environment_tool("ruff") == str(ruff)
