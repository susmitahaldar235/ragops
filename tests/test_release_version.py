import json
import tomllib
from pathlib import Path

from ragops import __version__


def test_package_and_release_metadata_versions_match() -> None:
    metadata = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    version = metadata["project"]["version"]
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert version == __version__ == "2.0.1"
    assert f"## [{version}]" in changelog
    assert Path("docs/releases/v2.0.1.md").is_file()


def test_plugin_manifests_match_package_version() -> None:
    versions = {
        json.loads(Path(path).read_text(encoding="utf-8"))["version"]
        for path in (
            ".codex-plugin/plugin.json",
            ".claude-plugin/plugin.json",
            ".kimi-plugin/plugin.json",
        )
    }

    assert versions == {"2.0.1"}
