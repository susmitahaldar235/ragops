#!/usr/bin/env python3
"""Quota-independent release lane for RAGOps.

Build and validate locally, then publish the exact artifacts to GitHub and,
only with an explicitly supplied project-scoped token, PyPI.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


def environment_tool(name: str) -> str:
    suffix = ".exe" if os.name == "nt" else ""
    candidate = Path(sys.executable).parent / f"{name}{suffix}"
    return str(candidate) if candidate.is_file() else name


def run(
    *args: str,
    env: dict[str, str] | None = None,
    cwd: Path = ROOT,
) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.run(args, cwd=cwd, env=env, check=True)


def version() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def milestone_tag() -> str:
    parts = version().split(".")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        raise SystemExit("package version must use numeric MAJOR.MINOR.PATCH")
    return f"v{'.'.join(parts)}"


def assert_tag(tag: str) -> str:
    expected = milestone_tag()
    if tag != expected:
        raise SystemExit(f"tag {tag!r} does not match package version {expected!r}")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if f"## [{version()}]" not in changelog:
        raise SystemExit(f"missing CHANGELOG entry for {version()}")
    return expected


def artifacts() -> list[Path]:
    result = sorted(DIST.glob("ragops-*.whl")) + sorted(DIST.glob("ragops-*.tar.gz"))
    if len(result) != 2:
        raise SystemExit("expected exactly one wheel and one source distribution in dist/")
    return result


def checksums(paths: list[Path]) -> Path:
    manifest = DIST / "SHA256SUMS"
    lines = [f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}" for path in paths]
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest


def verify_checksums(directory: Path) -> None:
    manifest = directory / "SHA256SUMS"
    if not manifest.is_file():
        raise SystemExit("release is missing SHA256SUMS")
    lines = manifest.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise SystemExit("SHA256SUMS is empty")
    for line in lines:
        try:
            digest, filename = line.split("  ", 1)
        except ValueError as exc:
            raise SystemExit("invalid SHA256SUMS line") from exc
        path = directory / filename
        if Path(filename).name != filename or not path.is_file():
            raise SystemExit(f"invalid checksum target: {filename}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if len(digest) != 64 or actual != digest:
            raise SystemExit(f"checksum mismatch: {filename}")


def verify_clean_install(wheel: Path, expected_version: str) -> None:
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
    required = {
        "ragops/api/main.py",
        "ragops/web/index.html",
        "ragops/web/app.js",
        "ragops/schemas/evidence-bundle-1.0.schema.json",
    }
    missing = sorted(required - names)
    if missing:
        raise SystemExit(f"wheel is missing packaged surfaces: {missing}")
    with tempfile.TemporaryDirectory(prefix="ragops-release-") as temp:
        venv = Path(temp) / "venv"
        run(sys.executable, "-m", "venv", str(venv))
        python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        run(str(python), "-m", "pip", "install", "--no-deps", str(wheel))
        run(
            str(python),
            "-c",
            f"import ragops; assert ragops.__version__ == {expected_version!r}",
        )
        demo = Path(temp) / "demo"
        run(str(python), "-m", "ragops.cli", "demo", "--output", str(demo))
        run(str(python), "-m", "ragops.cli", "evidence", "verify", "--bundle", str(demo / "evidence"))


def build_plugin_bundle(expected_version: str) -> Path:
    manifest = json.loads((ROOT / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
    if manifest.get("version") != expected_version:
        raise SystemExit("ChatGPT plugin manifest version does not match package version")
    DIST.mkdir(parents=True, exist_ok=True)
    output = DIST / f"ragops-chatgpt-plugin-{expected_version}.zip"
    sources: dict[str, Path] = {
        ".codex-plugin/plugin.json": ROOT / ".codex-plugin/plugin.json",
        "assets/plugin-icon.png": ROOT / "assets/plugin-icon.png",
    }
    skill_root = ROOT / "skills" / "evaluate-ai-release"
    for path in skill_root.rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            sources[path.relative_to(ROOT).as_posix()] = path
    for path in (ROOT / "src" / "ragops").rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            relative = path.relative_to(ROOT / "src" / "ragops")
            sources[f"skills/evaluate-ai-release/scripts/vendor/ragops/{relative.as_posix()}"] = path
    for path in (ROOT / "schemas").glob("*.json"):
        sources[f"skills/evaluate-ai-release/scripts/vendor/ragops/schemas/{path.name}"] = path
    fixture_root = ROOT / "scenarios" / "japanese_troubleshooting"
    fixture_names = (
        "benchmark-baseline.json",
        "benchmark-regressed.json",
        "benchmark-v0.2.json",
        "sample_responses.json",
        "scenario.json",
    )
    for name in fixture_names:
        sources[f"skills/evaluate-ai-release/references/fixtures/japanese_troubleshooting/{name}"] = fixture_root / name
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for archive_name, source in sorted(sources.items()):
            info = zipfile.ZipInfo(archive_name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            mode = 0o755 if archive_name.endswith("/run_ragops.py") else 0o644
            info.external_attr = mode << 16
            archive.writestr(info, source.read_bytes())
    return output


def verify(tag: str) -> None:
    assert_tag(tag)
    run(environment_tool("ruff"), "check", ".")
    env = os.environ.copy()
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    run(sys.executable, "-m", "pytest", "-q", env=env)
    run(sys.executable, "-m", "ragops.cli", "evaluate", "--scenario",
        "scenarios/japanese_troubleshooting/scenario.json", "--responses",
        "scenarios/japanese_troubleshooting/sample_responses.json")
    blocked = subprocess.run(
        [sys.executable, "-m", "ragops.cli", "compare", "--scenario",
         "scenarios/japanese_troubleshooting/benchmark-v0.2.json",
         "--baseline", "scenarios/japanese_troubleshooting/benchmark-baseline.json", "--candidate",
         "scenarios/japanese_troubleshooting/benchmark-regressed.json"], cwd=ROOT
    )
    if blocked.returncode != 2:
        raise SystemExit(f"expected regression gate exit 2, got {blocked.returncode}")
    shutil.rmtree(DIST, ignore_errors=True)
    run(sys.executable, "-m", "build")
    built = artifacts()
    wheel = next(path for path in built if path.suffix == ".whl")
    verify_clean_install(wheel, version())
    plugin = build_plugin_bundle(version())
    sbom = DIST / f"ragops-{version()}.cdx.json"
    cyclonedx = environment_tool("cyclonedx-py")
    if Path(cyclonedx).is_file() or shutil.which(cyclonedx):
        run(cyclonedx, "environment", sys.executable, "--output-reproducible",
            "--output-file", str(sbom))
    else:
        raise SystemExit("cyclonedx-py is required: python -m pip install cyclonedx-bom==7.3.0")
    manifest = checksums([*built, sbom, plugin])
    evidence = {
        "schema": "ragops-local-release-evidence-0.1",
        "tag": tag,
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "created_at": datetime.now(UTC).isoformat(),
        "validation": "pass",
        "trusted_publishing": True,
        "artifacts": [path.name for path in [*built, sbom, plugin, manifest]],
    }
    (DIST / "LOCAL_RELEASE_EVIDENCE.json").write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
    )


def github(tag: str, yes: bool) -> None:
    assert_tag(tag)
    if not yes:
        raise SystemExit("publishing requires --yes")
    paths = [*artifacts(), DIST / f"ragops-{version()}.cdx.json",
             DIST / f"ragops-chatgpt-plugin-{version()}.zip", DIST / "SHA256SUMS",
             DIST / "LOCAL_RELEASE_EVIDENCE.json"]
    if any(not path.is_file() for path in paths):
        raise SystemExit("run verify first; release artifacts are incomplete")
    run("git", "diff", "--quiet")
    run("git", "diff", "--cached", "--quiet")
    run("git", "tag", "-a", tag, "-m", f"RAGOps {tag}")
    run("git", "push", "origin", tag)
    run("gh", "release", "create", tag, *(str(path) for path in paths), "--verify-tag",
        "--title", f"RAGOps {tag}", "--generate-notes")


def pypi(tag: str, yes: bool) -> None:
    assert_tag(tag)
    token = os.environ.get("PYPI_API_TOKEN")
    if not yes or not token:
        raise SystemExit("PyPI publish requires --yes and PYPI_API_TOKEN (project-scoped)")
    release_dir = ROOT / ".local-release" / tag
    shutil.rmtree(release_dir, ignore_errors=True)
    release_dir.mkdir(parents=True)
    run("gh", "release", "download", tag, "--dir", str(release_dir))
    verify_checksums(release_dir)
    distributions = sorted(release_dir.glob("ragops-*.whl")) + sorted(release_dir.glob("ragops-*.tar.gz"))
    if len(distributions) != 2:
        raise SystemExit("GitHub Release must contain exactly one wheel and one source distribution")
    env = os.environ.copy()
    env.update({"TWINE_USERNAME": "__token__", "TWINE_PASSWORD": token})
    run(sys.executable, "-m", "twine", "upload", *(str(path) for path in distributions), env=env)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("verify", "publish-github", "publish-pypi"):
        command = sub.add_parser(name)
        command.add_argument("--tag", required=True)
        if name != "verify":
            command.add_argument("--yes", action="store_true")
    args = parser.parse_args()
    if args.command == "verify":
        verify(args.tag)
    elif args.command == "publish-github":
        github(args.tag, args.yes)
    else:
        pypi(args.tag, args.yes)


if __name__ == "__main__":
    main()
