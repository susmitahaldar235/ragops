# RAGOps operations / Vận hành / 運用

## English

Install with `pip install -e '.[dev]'`, run `ruff check .`, then `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q`. Verify `ragops demo --profile engineer`, `ragops evidence verify`, the packaged API/UI, every schema instance, and a clean `--no-deps` wheel import. Build wheel/sdist/SBOM/checksums from a clean commit, promote those exact artifacts to a GitHub Release, then dispatch the tag-bound PyPI Trusted Publishing workflow. GitHub publication, PyPI publication, ChatGPT directory submission, and ChatGPT approval are separate states and must be reported separately.

## Tiếng Việt

Cài bằng `pip install -e '.[dev]'`, chạy lint/test, demo/evidence verify, API/UI, schema và clean-wheel import. Build wheel/sdist/SBOM/checksum từ commit sạch, phát hành đúng artifact lên GitHub rồi mới chạy PyPI Trusted Publishing theo tag. Phải phân biệt GitHub release, PyPI release, ChatGPT submission và ChatGPT approval.

## 日本語

`pip install -e '.[dev]'` 後に lint/test、demo/evidence verify、API/UI、schema、clean-wheel import を確認します。clean commit から wheel/sdist/SBOM/checksum を作成し、同一 artifact を GitHub Release に昇格してから tag-bound PyPI workflow を実行します。GitHub、PyPI、ChatGPT submission、ChatGPT approval は別状態です。
