---
name: ragops-release
description: Assess RAGOps release readiness, run its quality gates, and produce owner acceptance evidence without publishing or tagging a release.
---

# RAGOps release-readiness workflow

Use to prepare owner acceptance. It does not authorize publication.

1. Read `docs/product/requirements.md`, `docs/architecture/decisions.md`,
   `docs/project/status.md`, and `CHANGELOG.md`.
2. Verify version consistency and supported Python versions where available.
3. Run lint, full tests, schema checks, PASS/BLOCK samples, API health/evaluate,
   package build, and clean install.
4. Review security-sensitive changes, dependencies, generated files, secrets,
   and Git state.
5. Produce acceptance evidence with passed/failed gates, limitations,
   compatibility impact, and a go/hold recommendation.

Only the product owner may tag, release, publish packages, or deploy public
assets.
