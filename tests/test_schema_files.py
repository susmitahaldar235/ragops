import json
import tomllib
from pathlib import Path


def test_all_published_schemas_are_valid_json() -> None:
    schemas = sorted(Path("schemas").glob("*.json"))

    assert schemas
    for schema in schemas:
        document = json.loads(schema.read_text(encoding="utf-8"))
        assert document["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert document["$id"]


def test_wheel_configuration_packages_public_schemas() -> None:
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    force_include = project["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
    assert force_include["schemas"] == "ragops/schemas"
