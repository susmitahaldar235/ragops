from __future__ import annotations

from importlib.resources import files
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from apps.api.main import app as compatibility_app
from ragops.api.main import SECURITY_HEADERS, app, dashboard, workbench_asset
from ragops.cli import build_parser


def test_api_compatibility_shim_uses_packaged_app():
    assert compatibility_app is app


def test_packaged_workbench_has_csp_and_no_untrusted_html_writes():
    web = files("ragops.web")
    page = web.joinpath("index.html").read_text(encoding="utf-8")
    script = web.joinpath("app.js").read_text(encoding="utf-8")

    assert "Content-Security-Policy" in page
    assert "default-src 'self'" in page
    assert "innerHTML" not in page + script
    assert "outerHTML" not in page + script
    assert "document.write" not in page + script
    assert "http://" not in page + script
    assert "https://" not in page + script
    assert ".textContent" in script
    assert "createElement" in script


def test_dashboard_serves_packaged_assets_with_security_headers():
    page = dashboard()
    script = workbench_asset("app.js")

    assert Path(page.path).read_text(encoding="utf-8").startswith("<!doctype html>")
    assert "createElement" in Path(script.path).read_text(encoding="utf-8")
    assert SECURITY_HEADERS["Content-Security-Policy"].startswith("default-src 'self'")
    assert SECURITY_HEADERS["X-Content-Type-Options"] == "nosniff"


def test_serve_command_is_lazy_and_configurable():
    args = build_parser().parse_args(["serve", "--host", "127.0.0.1", "--port", "9010"])

    assert args.command == "serve"
    assert args.host == "127.0.0.1"
    assert args.port == 9010


def test_hatch_configuration_packages_api_web_and_schemas():
    project = Path("pyproject.toml").read_text(encoding="utf-8")

    assert '"schemas" = "ragops/schemas"' in project
    assert Path("src/ragops/api/main.py").is_file()
    assert Path("src/ragops/web/index.html").is_file()
