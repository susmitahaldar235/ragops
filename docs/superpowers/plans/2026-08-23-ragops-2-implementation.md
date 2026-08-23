# RAGOps 2.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship RAGOps 2.0 as a backward-compatible, verifiable offline release-governance toolkit, then publish the verified artifacts to GitHub, PyPI, and the ChatGPT plugin workflow.

**Architecture:** Extend the dependency-free core with versioned contracts, evidence, policy, calibration, datasets, trace graphs, explanations, adapters, and governance. Package FastAPI/workbench as an optional application surface, keep source compatibility shims, and make every reporter consume the same canonical decision evidence.

**Tech Stack:** Python 3.11+ standard library core, optional FastAPI/Uvicorn, SQLite, JSON Schema 2020-12 artifacts, Pytest, Ruff, Hatchling, GitHub Actions, OIDC Trusted Publishing.

**Spec:** `docs/superpowers/specs/2026-08-23-ragops-production-flagship-adoption-design.md`

## Global Constraints

- Python remains `>=3.11`; `ragops` retains zero required runtime dependencies.
- Existing CLI commands, flags, exit codes, and 1.x artifact readers remain supported.
- Core performs no implicit network calls and imports no optional packages.
- Canonical decisions are `PASS`, `WARN`, and `BLOCK`; legacy `passed` remains derived.
- Inputs and accepted evidence are immutable; migration always writes a separate output.
- Synthetic evidence is labeled synthetic and is never described as production adoption.
- Every production behavior follows witnessed RED, minimal GREEN, then regression verification.

---

### Task 1: Contract registry, validation, migration, and packaged schemas

**Files:** Create `src/ragops/contracts.py`, `tests/test_contracts_v2.py`; modify `src/ragops/cli.py`, `pyproject.toml`, `tests/test_schema_files.py`.

**Interfaces:** Produces `ContractDescriptor`, `ValidationResult`, `registered_contracts()`, `validate_contract(data, kind="auto")`, `diff_contract(kind, from_version, to_version)`, `migrate_contract(data, kind, from_version, to_version, question="")`, and `ragops contract validate|diff|migrate`.

- [ ] **Step 1: Write failing migration and fail-closed tests**

```python
def test_migrate_scenario_01_to_02_is_explicit_and_valid() -> None:
    source = scenario_01_fixture()
    migrated = migrate_contract(source, "scenario", "0.1", "0.2")
    assert source["schema_version"] == "0.1"
    assert migrated["thresholds"]["citation_precision"] == 0.0
    assert migrated["cases"][0]["severity"] == "medium"
    assert validate_contract(migrated, "scenario").version == "0.2"

def test_unknown_contract_version_fails_closed() -> None:
    with pytest.raises(ContractError, match="Unsupported scenario schema"):
        validate_contract({**scenario_01_fixture(), "schema_version": "9.9"}, "scenario")
```

- [ ] **Step 2: Run RED**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/pytest tests/test_contracts_v2.py -q`

Expected: import failure because `ragops.contracts` does not exist.

- [ ] **Step 3: Implement frozen descriptors, literal registry, pure migrations, and nested CLI commands**

Scenario migration adds the conservative reader defaults. Trace migration adds required 0.4 fields and records `metadata.migrated_from="0.3"`. CLI rejects resolved input/output equality.

- [ ] **Step 4: Package root schemas inside the wheel and verify contents**

Add Hatch `force-include` from `schemas/` to `ragops/schemas/`; test for `ragops/schemas/scenario-0.2.schema.json` in the wheel.

- [ ] **Step 5: Verify and commit**

```bash
.venv/bin/ruff check src/ragops/contracts.py src/ragops/cli.py tests/test_contracts_v2.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/pytest tests/test_contracts_v2.py tests/test_schema_files.py -q
git add src/ragops/contracts.py src/ragops/cli.py tests/test_contracts_v2.py tests/test_schema_files.py pyproject.toml
git commit -m "feat: add versioned contract tooling"
```

### Task 2: Verifiable evidence bundles

**Files:** Create `src/ragops/evidence.py`, `schemas/evidence-bundle-1.0.schema.json`, `tests/test_evidence_bundle.py`; modify `src/ragops/cli.py`, `src/ragops/__init__.py`.

**Interfaces:** Produces `ArtifactRecord`, `EvidenceManifest`, `create_evidence_bundle(...)`, `load_evidence_manifest(path)`, `verify_evidence_bundle(path)`, and `ragops evidence create|verify`.

- [ ] **Step 1: Write failing reproducibility, tamper, traversal, symlink, missing-file, and decision tests**

```python
def test_evidence_bundle_is_reproducible_and_detects_tampering(tmp_path: Path) -> None:
    source = tmp_path / "report.json"
    source.write_text('{"passed":false}\n')
    first = create_evidence_bundle(tmp_path / "one", {"report": source}, "BLOCK",
                                   ("synthetic benchmark",), "2026-08-23T00:00:00Z", {})
    second = create_evidence_bundle(tmp_path / "two", {"report": source}, "BLOCK",
                                    ("synthetic benchmark",), "2026-08-23T00:00:00Z", {})
    assert first.canonical_bytes() == second.canonical_bytes()
    (tmp_path / "one/artifacts/report.json").write_text("tampered")
    with pytest.raises(ContractError, match="digest mismatch"):
        verify_evidence_bundle(tmp_path / "one")
```

- [ ] **Step 2: Run RED, implement bounded canonical bundles, then run GREEN**

Copy regular files under `artifacts/`, canonicalize JSON with sorted keys, and verify path, size, digest, schema, decision, and undeclared regular files.

Run: `.venv/bin/ruff check src/ragops/evidence.py tests/test_evidence_bundle.py && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/pytest tests/test_evidence_bundle.py -q`

- [ ] **Step 3: Add CLI and commit**

```bash
git add src/ragops/evidence.py src/ragops/cli.py src/ragops/__init__.py schemas/evidence-bundle-1.0.schema.json tests/test_evidence_bundle.py
git commit -m "feat: add verifiable evidence bundles"
```

### Task 3: Slice and distribution evidence

**Files:** Create `src/ragops/slices.py`, `src/ragops/distribution.py`, `tests/test_slice_distribution.py`; modify `src/ragops/models.py`.

**Interfaces:** Produces `SliceSelector`, `SliceSummary`, `summarize_slices(...)`, `quantile(...)`, `paired_effect(...)`, `holm_adjust(...)`, and `minimum_paired_sample(...)`.

- [ ] **Step 1: Write failing selector and hand-derived math tests**

```python
def test_quantile_and_holm_are_hand_checkable() -> None:
    assert quantile((0.0, 10.0, 20.0, 30.0), 0.5) == 15.0
    assert holm_adjust({"a": 0.01, "b": 0.04, "c": 0.03}) == {
        "a": 0.03, "b": 0.06, "c": 0.06,
    }
```

Add exact case-ID/count/metric assertions for language, severity, category, and tag selectors; reject non-finite inputs and invalid probabilities.

- [ ] **Step 2: Run RED, implement deterministic primitives, then run GREEN**

Run: `.venv/bin/ruff check src/ragops/slices.py src/ragops/distribution.py tests/test_slice_distribution.py && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/pytest tests/test_slice_distribution.py -q`

- [ ] **Step 3: Commit**

```bash
git add src/ragops/slices.py src/ragops/distribution.py src/ragops/models.py tests/test_slice_distribution.py
git commit -m "feat: add slice and distribution evidence"
```

### Task 4: Policy 2.0, waivers, and canonical decisions

**Files:** Create `src/ragops/policy_v2.py`, `schemas/release-policy-2.0.schema.json`, `schemas/release-decision-1.0.schema.json`, `tests/test_policy_v2.py`; modify `src/ragops/models.py`, `src/ragops/cli.py`.

**Interfaces:** Produces `ReleasePolicyV2`, `PolicyGate`, `PolicyWaiver`, `GateEvidence`, `ReleaseDecision`, `load_release_policy_v2(path)`, `apply_release_policy(...)`, and `ragops gate-v2`.

- [ ] **Step 1: Write failing worst-slice, insufficient-evidence, and waiver tests**

```python
def test_active_waiver_can_only_change_block_to_warn() -> None:
    decision = apply_release_policy(policy_with_waiver("2030-01-01T00:00:00Z"), baseline(),
                                    candidate(), scenario(), now="2026-08-23T00:00:00Z")
    assert decision.decision == "WARN"
    assert decision.gates[0].waived is True
```

Add a separate expired-waiver test expecting `BLOCK`, plus malformed timestamp, duplicate gate ID, unknown section, and empty selector tests.

- [ ] **Step 2: Run RED, implement strict TOML policy and gate evaluation, then run GREEN**

Run: `.venv/bin/ruff check src/ragops/policy_v2.py tests/test_policy_v2.py && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/pytest tests/test_policy_v2.py -q`

- [ ] **Step 3: Add schemas/CLI and commit**

```bash
git add src/ragops/policy_v2.py src/ragops/models.py src/ragops/cli.py schemas/release-policy-2.0.schema.json schemas/release-decision-1.0.schema.json tests/test_policy_v2.py
git commit -m "feat: add slice-aware release policy v2"
```

### Task 5: Evaluator calibration

**Files:** Create `src/ragops/calibration.py`, `schemas/calibration-set-1.0.schema.json`, `schemas/calibration-report-1.0.schema.json`, `tests/test_calibration.py`; modify `src/ragops/cli.py`.

**Interfaces:** Produces `CalibrationRecord`, `CalibrationPolicy`, `CalibrationReport`, `load_calibration_set(path)`, `calibrate_evaluator(...)`, and `ragops calibrate`.

- [ ] **Step 1: Write failing coverage, MAE, threshold accuracy, false-pass, false-block, kappa, and insufficient-overlap tests**

```python
def test_calibration_reports_false_passes_and_reviewer_agreement() -> None:
    report = calibrate_evaluator(calibration_fixture(), calibration_policy())
    assert report.coverage == 1.0
    assert report.false_pass_rate == 0.25
    assert report.reviewer_agreement is not None
```

- [ ] **Step 2: Run RED, implement calibration math/gates, then run GREEN**

Run: `.venv/bin/ruff check src/ragops/calibration.py tests/test_calibration.py && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/pytest tests/test_calibration.py -q`

- [ ] **Step 3: Add CLI/schemas and commit**

```bash
git add src/ragops/calibration.py src/ragops/cli.py schemas/calibration-set-1.0.schema.json schemas/calibration-report-1.0.schema.json tests/test_calibration.py
git commit -m "feat: add evaluator calibration gates"
```

### Task 6: Portable agent trace graph and OpenTelemetry adapter

**Files:** Create `src/ragops/trace_graph.py`, `src/ragops/adapters/otel_genai.py`, `schemas/trace-graph-1.0.schema.json`, `tests/test_trace_graph.py`; modify `src/ragops/cli.py`.

**Interfaces:** Produces `TraceSpan`, `TraceGraph`, `TraceExpectation`, `TraceGraphReport`, `trace_graph_from_dict(...)`, `evaluate_trace_graph(...)`, `otel_spans_to_trace_graph(...)`, and `ragops trace evaluate|convert-otel`.

- [ ] **Step 1: Write failing graph-integrity and trajectory tests**

```python
def test_trace_graph_localizes_wrong_tool_arguments() -> None:
    report = evaluate_trace_graph(tool_trace_fixture(), trace_expectation_fixture())
    assert report.metrics["tool_name_precision"] == 1.0
    assert report.metrics["tool_argument_exactness"] == 0.0
    assert report.failed_span_ids == ("tool-1",)
```

Add cycles, missing parents, duplicate IDs, negative duration, tool order, recovery, excess-step, retrieval recall, and raw unknown `gen_ai.*` preservation tests.

- [ ] **Step 2: Run RED, implement graph/adapter, then run GREEN**

Run: `.venv/bin/ruff check src/ragops/trace_graph.py src/ragops/adapters/otel_genai.py tests/test_trace_graph.py && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/pytest tests/test_trace_graph.py -q`

- [ ] **Step 3: Add CLI/schema and commit**

```bash
git add src/ragops/trace_graph.py src/ragops/adapters/otel_genai.py src/ragops/cli.py schemas/trace-graph-1.0.schema.json tests/test_trace_graph.py
git commit -m "feat: evaluate portable agent trace graphs"
```

### Task 7: Benchmark manifests and leakage checks

**Files:** Create `src/ragops/datasets.py`, `schemas/dataset-manifest-1.0.schema.json`, `tests/test_datasets.py`; modify `src/ragops/cli.py`.

**Interfaces:** Produces `DatasetManifest`, `DatasetIssue`, `DatasetDiff`, `create_dataset_manifest(...)`, `validate_dataset_manifest(...)`, `diff_dataset_manifests(...)`, and `ragops dataset create|validate|diff`.

- [ ] **Step 1: Write failing duplicate, leakage, provenance, coverage, and deterministic-diff tests**

```python
def test_dataset_validation_quarantines_cross_split_leakage() -> None:
    issues = validate_dataset_manifest(manifest_with_cross_split_duplicate())
    assert {item.code for item in issues} >= {"normalized_content_leakage", "review_required"}
```

- [ ] **Step 2: Run RED, implement normalized hashing/manifests/diff, then run GREEN**

Run: `.venv/bin/ruff check src/ragops/datasets.py tests/test_datasets.py && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/pytest tests/test_datasets.py -q`

- [ ] **Step 3: Add CLI/schema and commit**

```bash
git add src/ragops/datasets.py src/ragops/cli.py schemas/dataset-manifest-1.0.schema.json tests/test_datasets.py
git commit -m "feat: govern benchmark dataset lifecycle"
```

### Task 8: Regression explanation and CI renderers

**Files:** Create `src/ragops/explain.py`, `src/ragops/ci.py`, `tests/test_explain_and_ci.py`; modify `src/ragops/reporters.py`, `src/ragops/cli.py`.

**Interfaces:** Produces `explain_decision(...)`, `remediation_for_gate(...)`, `junit_report(...)`, `github_summary(...)`, `sarif_report(...)`, `ragops explain`, and CI output formats.

- [ ] **Step 1: Write failing causal-path, counterfactual, JUnit, summary, SARIF, and escaping tests**

```python
def test_explanation_maps_gate_to_policy_case_and_remediation() -> None:
    item = explain_decision(blocked_decision_fixture()).items[0]
    assert item.policy_path == "metrics.citation_coverage.max_regression"
    assert item.case_ids == ("q2",)
    assert item.required_change == 0.5
```

- [ ] **Step 2: Run RED, implement bounded renderers, then run GREEN**

Use ElementTree for XML and dictionaries for SARIF. Strip control characters and bound Markdown fields.

Run: `.venv/bin/ruff check src/ragops/explain.py src/ragops/ci.py tests/test_explain_and_ci.py && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/pytest tests/test_explain_and_ci.py tests/test_store_and_html.py -q`

- [ ] **Step 3: Add CLI and commit**

```bash
git add src/ragops/explain.py src/ragops/ci.py src/ragops/reporters.py src/ragops/cli.py tests/test_explain_and_ci.py
git commit -m "feat: explain regressions and emit CI evidence"
```

### Task 9: Adapter SDK and offline import profiles

**Files:** Create `src/ragops/adapter_sdk.py`, `src/ragops/adapters/importers.py`, `tests/test_adapter_sdk.py`, `docs/ADAPTERS.md`; modify `src/ragops/cli.py`.

**Interfaces:** Produces `Adapter`, `AdapterContext`, `AdapterOutput`, `discover_adapters()`, `convert_export(...)`, entry-point group `ragops.adapters`, and `ragops adapter list|convert`. Built-ins are `phoenix`, `ragas`, `deepeval`, `langsmith`, `mlflow`, `promptfoo`, and `custom`.

- [ ] **Step 1: Write failing producer, complete-coverage, provenance, unmapped-field, duplicate, non-finite, and safe-discovery tests**

```python
@pytest.mark.parametrize("producer", ["phoenix", "ragas", "deepeval", "langsmith", "mlflow", "promptfoo"])
def test_builtin_imports_preserve_provenance(producer: str) -> None:
    output = convert_export(producer, producer_fixture(producer), AdapterContext(("q1",)))
    assert output.provenance["producer"] == producer
    assert output.records[0]["case_id"] == "q1"
```

- [ ] **Step 2: Run RED, implement strict converters/discovery, then run GREEN**

Run: `.venv/bin/ruff check src/ragops/adapter_sdk.py src/ragops/adapters/importers.py tests/test_adapter_sdk.py && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/pytest tests/test_adapter_sdk.py tests/test_phoenix_recorded_scores.py tests/test_provider_metric_adapters.py -q`

- [ ] **Step 3: Document and commit**

```bash
git add src/ragops/adapter_sdk.py src/ragops/adapters/importers.py src/ragops/cli.py tests/test_adapter_sdk.py docs/ADAPTERS.md
git commit -m "feat: add vendor-neutral adapter SDK"
```

### Task 10: Local governance and blind review queue

**Files:** Create `src/ragops/governance.py`, `tests/test_governance.py`; modify `src/ragops/cli.py`.

**Interfaces:** Produces `GovernanceStore.register_artifact|submit_review|record_review|promote|supersede|create_waiver|list_queue|audit_events` and `ragops governance` subcommands.

- [ ] **Step 1: Write failing immutability, blind-review, quorum, transition, expiry, and append-only audit tests**

```python
def test_invalid_promotion_transition_fails_closed(tmp_path: Path) -> None:
    store = GovernanceStore(tmp_path / "governance.db")
    with pytest.raises(ValueError, match="draft -> accepted"):
        store.promote("digest", actor="alice", target="accepted", reason="skip review")
```

- [ ] **Step 2: Run RED, implement transactional SQLite governance, then run GREEN**

Use foreign keys, `BEGIN IMMEDIATE`, immutable artifact rows, ISO-8601 timestamps, and deterministic JSON.

Run: `.venv/bin/ruff check src/ragops/governance.py tests/test_governance.py && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/pytest tests/test_governance.py tests/test_control_plane.py tests/test_team_workflow.py -q`

- [ ] **Step 3: Add CLI and commit**

```bash
git add src/ragops/governance.py src/ragops/cli.py tests/test_governance.py
git commit -m "feat: add local release governance"
```

### Task 11: Packaged API and CSP-safe workbench

**Files:** Create `src/ragops/api/__init__.py`, `src/ragops/api/main.py`, `src/ragops/web/__init__.py`, `src/ragops/web/index.html`, `tests/test_packaged_api.py`; modify `apps/api/main.py`, `apps/web/index.html`, `src/ragops/cli.py`, `pyproject.toml`, `tests/test_workbench.py`, `tests/test_api_contract.py`.

**Interfaces:** Produces wheel-importable `ragops.api.main:app`, `ragops serve`, packaged web asset, and preserves `apps.api.main:app`.

- [ ] **Step 1: Write failing wheel-content, API import, CSP, and DOM-safety tests**

```python
def test_packaged_workbench_has_no_untrusted_inner_html() -> None:
    html = files("ragops.web").joinpath("index.html").read_text()
    assert ".innerHTML" not in html
    assert "Content-Security-Policy" in html
```

Add a clean-wheel test for schema/API/web contents and a `--no-deps` test proving `import ragops` works without FastAPI.

- [ ] **Step 2: Run RED, package API/assets, add compatibility shim, and replace unsafe DOM writes**

Dynamic values use `textContent`/element creation. No event-handler attributes or remote assets are allowed. `serve` imports Uvicorn lazily.

- [ ] **Step 3: Run API/workbench tests and commit**

```bash
.venv/bin/ruff check src/ragops/api apps/api src/ragops/cli.py tests/test_packaged_api.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/pytest tests/test_packaged_api.py tests/test_api_contract.py tests/test_workbench.py -q
git add src/ragops/api src/ragops/web apps/api/main.py apps/web/index.html src/ragops/cli.py pyproject.toml tests/test_packaged_api.py tests/test_workbench.py tests/test_api_contract.py
git commit -m "feat: package secure API workbench"
```

### Task 12: Flagship demo, docs, and consumer CI

**Files:** Modify `src/ragops/demo.py`, `src/ragops/cli.py`, `src/ragops/reporters.py`, `tests/test_demo.py`, `README.md`, `docs/ARCHITECTURE.md`, `docs/OPERATIONS.md`, `docs/examples/github-pr-comment.yml`, `docs/examples/gitlab-ci-ragops.yml`; create `tests/test_flagship_demo.py`, `docs/CONTRACTS.md`, `docs/GOVERNANCE.md`, `.github/workflows/ci.yml`.

**Interfaces:** Produces `ragops demo --profile executive|engineer|auditor` with evidence bundle, JSON, Markdown, safe HTML, JUnit, SARIF, and GitHub summary.

- [ ] **Step 1: Write failing cross-artifact/profile consistency tests**

```python
@pytest.mark.parametrize("profile", ["executive", "engineer", "auditor"])
def test_profiles_share_one_block_decision(tmp_path: Path, profile: str) -> None:
    summary = write_demo(tmp_path / profile, scenario_id="customer-support", profile=profile)
    assert summary["candidate_decision"] == "BLOCK"
    assert summary["evidence_classification"] == "synthetic"
    assert verify_evidence_bundle(tmp_path / profile / "evidence").decision == "BLOCK"
```

- [ ] **Step 2: Run RED, implement all formats/profiles, then run GREEN**

Verify stable failed-gate IDs across formats and absence of production-adoption claims.

Run: `.venv/bin/ruff check src/ragops/demo.py src/ragops/reporters.py tests/test_flagship_demo.py && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/pytest tests/test_demo.py tests/test_flagship_demo.py tests/test_adoption_recipes.py -q`

- [ ] **Step 3: Add pinned Python 3.11/3.12/3.13 CI and adoption docs, then commit**

```bash
git add src/ragops/demo.py src/ragops/cli.py src/ragops/reporters.py tests/test_demo.py tests/test_flagship_demo.py README.md docs .github/workflows/ci.yml
git commit -m "feat: deliver flagship release-gate workflow"
```

### Task 13: Version 2.0 release candidate and plugin package

**Files:** Modify `pyproject.toml`, `src/ragops/__init__.py`, `CHANGELOG.md`, `scripts/local_release.py`, release/version/plugin tests, `.codex-plugin/plugin.json`, `.claude-plugin/plugin.json`, `.kimi-plugin/plugin.json`, `skills/evaluate-ai-release/`, `docs/submission/DIRECTORY_SUBMISSION.md`; create `docs/releases/v2.0.0.md`.

**Interfaces:** Produces version-consistent 2.0.0 source, wheel, sdist, SBOM, checksums, local release evidence, and skills-only plugin submission bundle.

- [ ] **Step 1: Write failing parity and clean-wheel tests**

```python
def test_public_release_metadata_matches_200() -> None:
    assert project_version() == runtime_version() == "2.0.0"
    assert plugin_versions() == {"2.0.0"}

def test_clean_wheel_contains_optional_surfaces(built_wheel: Path) -> None:
    names = wheel_names(built_wheel)
    assert "ragops/web/index.html" in names
    assert "ragops/api/main.py" in names
    assert "ragops/schemas/evidence-bundle-1.0.schema.json" in names
```

- [ ] **Step 2: Run RED, update release metadata/evidence, then run targeted GREEN**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/pytest tests/test_release_version.py tests/test_local_release.py tests/test_plugin_release.py -q`

- [ ] **Step 3: Run full verification and exact artifact build**

```bash
.venv/bin/ruff check .
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/pytest -q
.venv/bin/ragops demo --profile auditor --output /tmp/ragops-v2-demo
.venv/bin/ragops evidence verify --bundle /tmp/ragops-v2-demo/evidence
.venv/bin/pip install -q build cyclonedx-bom==7.3.0
.venv/bin/python scripts/local_release.py verify --tag v2.0.0
git diff --check
```

- [ ] **Step 4: Commit release candidate**

```bash
git add pyproject.toml src/ragops/__init__.py CHANGELOG.md docs/releases/v2.0.0.md scripts/local_release.py tests .codex-plugin .claude-plugin .kimi-plugin skills docs/submission
git commit -m "release: prepare RagOps 2.0.0"
```

### Task 14: Review and external publication

**Files:** Evidence only: `dist/*`, GitHub Release `v2.0.0`, PyPI `ragops`, and ChatGPT plugin submission state.

**Interfaces:** Consumes exact clean-commit artifacts from Task 13; produces publication URLs and submission state.

- [ ] **Step 1: Review `origin/main...HEAD` against every spec criterion and fix critical/important findings**

Inspect path handling, HTML, SQLite, signatures, contract compatibility, and release scripts. Run the full suite after fixes.

- [ ] **Step 2: Verify provenance immediately before release**

```bash
git status --short
git rev-parse HEAD
.venv/bin/python scripts/local_release.py verify --tag v2.0.0
sha256sum dist/ragops-2.0.0-py3-none-any.whl dist/ragops-2.0.0.tar.gz
```

- [ ] **Step 3: Push branch and land through repository policy without force operations**

If branch protection requires review, create a PR against `main`, wait for required checks, and merge through GitHub.

- [ ] **Step 4: Create GitHub Release from exact verified artifacts**

Run: `.venv/bin/python scripts/local_release.py publish-github --tag v2.0.0 --yes`

Verify one wheel, one sdist, SBOM, `SHA256SUMS`, and `LOCAL_RELEASE_EVIDENCE.json` on the release.

- [ ] **Step 5: Publish through PyPI Trusted Publishing and verify public install**

Dispatch the tag-bound workflow, wait for success, install `ragops==2.0.0` into a clean temporary venv, then run `ragops --version` and the credential-free demo.

- [ ] **Step 6: Validate and submit the ChatGPT plugin update**

Use official OpenAI guidance and authenticated browser state. Validate manifest, skills, policy URLs, icons, version, and directory test prompts. Record `submitted`, `in review`, or `approved` accurately.

- [ ] **Step 7: Report final evidence**

Report commit/tag, test count, Ruff, clean-wheel evidence, GitHub URL, PyPI URL/install result, ChatGPT submission state, and synthetic limitations.
