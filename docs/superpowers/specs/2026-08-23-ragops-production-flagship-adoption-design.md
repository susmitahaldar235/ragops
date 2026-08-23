# RAGOps Production, Flagship, and Adoption Design

**Status:** Approved for autonomous implementation

**Date:** 2026-08-23

**Target release:** 2.0.0

## Baseline

RAGOps 1.2.0 has a dependency-free Python core, deterministic and statistical gates,
portable recorded traces, baseline manifests, evaluator-drift checks, an API/workbench in
the source tree, adapter examples, and a skills-only plugin. The audited baseline passes
Ruff and 202 tests. Its five-minute demo correctly blocks a candidate whose citation
coverage and precision fall from 1.0 to 0.5 and groundedness falls from 1.0 to 0.6.

The upgrade must not turn synthetic results into production-adoption claims. It must make
the evidence contract stronger, the regression easier to localize, the installable package
complete, and production-derived evidence easier to import and govern.

## Goals

1. Make release evidence content-addressed, reproducible, verifiable, and explainable.
2. Preserve all supported 1.x CLI behavior and artifact readers while adding explicit
   contract migration and compatibility inspection.
3. Gate worst slices and distribution tails rather than relying only on global means.
4. evaluate agents at trace, span, retrieval, and tool-call scopes without binding the
   core to a tracing or model vendor.
5. Calibrate automated evaluators against human labels and make evaluator quality a
   release input.
6. Govern benchmark promotion, baseline acceptance, review, and temporary waivers through
   append-only local evidence.
7. Ship the optional API and safe workbench in the wheel and provide CI-native reports.
8. Provide a differentiated five-minute flagship demo and practical import adapters.
9. Release the exact verified artifacts to GitHub and PyPI, then update the skills-only
   ChatGPT plugin submission package.

## Non-goals

- Hosted trace ingestion, model proxying, billing, prompt playgrounds, or user management.
- A proprietary LLM judge or red-team attack generator.
- Automatic claims of semantic correctness, compliance, security, or production fitness.
- Silent migration, mutation of accepted artifacts, or network calls from the core.

## Compatibility policy

- Python remains `>=3.11` and `ragops` retains zero required runtime dependencies.
- Existing commands, flags, exit codes, scenario 0.1/0.2, trace 0.3/0.4, report 0.2,
  replay 0.1, and baseline-manifest 0.1 remain readable.
- New contracts use stable names with explicit versions. Readers fail closed on unknown
  versions and unknown fields where the schema is closed.
- Migrations are explicit commands that write a new file; inputs are never modified.
- Canonical decision values are `PASS`, `WARN`, and `BLOCK`. Existing `passed` booleans
  remain in legacy reports and are derived from the canonical decision.
- Deprecations appear in machine-readable `contract diff` output and release notes. No 1.x
  contract is removed in 2.0.0.

## Architecture

### Dependency-free core

`src/ragops/` owns contracts, hashing, policies, deterministic/statistical evaluation,
calibration, dataset governance, trace-graph evaluation, evidence creation, explanation,
and report rendering. It uses only the Python standard library.

Core modules have narrow responsibilities:

- `contracts.py`: registry, validation dispatch, compatibility diff, and migrations.
- `evidence.py`: canonical JSON, artifact digests, evidence-bundle creation/verification.
- `policy_v2.py`: structured TOML policy parsing, global/slice/tail gates, and waivers.
- `slices.py`: case selection and slice aggregation.
- `distribution.py`: quantiles, paired effects, multiple-comparison correction, and
  deterministic minimum-sample estimates.
- `calibration.py`: human-label loading, agreement, automated-evaluator accuracy, and
  calibration gates.
- `datasets.py`: manifests, normalized deduplication, split leakage checks, coverage, and
  promotion evidence.
- `trace_graph.py`: portable trace graph and component/trajectory metrics.
- `explain.py`: causal gate path and counterfactual remediation.
- `adapter_sdk.py`: local adapter registry and normalized conversion contract.
- `governance.py`: baseline registry, review queue, state transitions, and waiver audit.
- `ci.py`: JUnit, GitHub step-summary, and SARIF rendering.

Existing modules remain import-compatible. New code may call existing evaluators and
statistics but must not duplicate their public semantics.

### Optional adapters and applications

- `ragops.adapters.*` converts exported vendor data into portable contracts. Built-ins
  cover OpenTelemetry GenAI JSON, Phoenix annotations, Ragas, DeepEval, LangSmith, MLflow,
  Promptfoo, and a documented custom profile.
- Third parties register adapters with the `ragops.adapters` Python entry-point group.
- `src/ragops/api/` contains the optional FastAPI application.
- `src/ragops/web/` contains the packaged workbench asset.
- `apps/api/main.py` remains a compatibility shim importing the packaged application.
- `ragops serve` imports FastAPI/Uvicorn lazily and gives an actionable error when the
  `api` extra is absent.

The core never imports FastAPI, Uvicorn, provider SDKs, or adapter packages.

## Data flow

1. `contract validate` identifies and validates each input contract.
2. Optional adapters normalize exported traces, annotations, or evaluator scores.
3. Dataset and baseline manifests bind approved inputs to SHA-256 digests.
4. Deterministic, statistical, slice, trace-graph, and calibration evaluators produce
   typed result objects.
5. Policy v2 evaluates global, slice, tail, calibration, and provenance gates.
6. Explanation maps every failed gate to policy path, metric evidence, affected cases,
   provenance dimensions, and a counterfactual remediation value when calculable.
7. Evidence bundling copies the bounded artifacts, records sizes and digests, writes a
   canonical manifest, and optionally signs that manifest using the existing SSH lane.
8. Reporters render JSON, Markdown, safe self-contained HTML, JUnit, step summary, or SARIF
   from the same evidence object.
9. Governance can accept or reject the candidate, but never rewrites evaluation evidence.

## Contracts

### Contract registry

Every registered contract declares `kind`, `version`, schema filename, validator, and
available migrations. CLI commands are:

```text
ragops contract validate --kind auto --input FILE
ragops contract diff --kind scenario --from 0.1 --to 0.2
ragops contract migrate --kind scenario --from 0.1 --to 0.2 --input IN --output OUT
```

Initial migration coverage is scenario 0.1 to 0.2 and trace 0.3 to 0.4. The scenario
migration supplies explicit conservative defaults already used by the 1.x reader:
`citation_precision=0.0`, `category=unspecified`, `severity=medium`, and `language=und`.
The trace migration requires a caller-provided or empty question, records the migration in
metadata, and never invents semantic provenance.

Schemas are included inside the wheel while the repository-level `schemas/` paths remain
available for existing consumers.

### Evidence bundle 1.0

An evidence bundle is a directory with `manifest.json` plus copied artifacts. The manifest
contains:

- schema version, RAGOps version, creation timestamp, and canonical decision;
- scenario, policy, input, baseline, candidate, evaluator, report, and environment artifact
  records where available;
- original logical name, media type, byte length, SHA-256, and relative bundle path;
- evaluator identities/configuration digests and relevant application provenance;
- limitations including synthetic/production-derived classification;
- optional source commit and CI run metadata.

Verification rejects path traversal, symlinks, missing/extra declared files, size changes,
digest changes, malformed decisions, and unknown schema versions. Deterministic mode accepts
an explicit creation time so fixtures are byte-for-byte reproducible.

### Policy 2.0

Policy remains structured TOML rather than a general-purpose expression language. It has:

- `[release]`: decision defaults and minimum case counts;
- `[metrics.<name>]`: direction, absolute threshold, maximum regression, and severity;
- `[[slices]]`: name plus exact-match selectors for category, severity, language, or tags;
- `[tails.<metric>]`: p50/p95/p99 thresholds;
- `[calibration.<evaluator>]`: minimum accuracy/agreement and maximum error;
- `[[waivers]]`: exact gate ID, owner, reason, issued-at, expires-at, and optional case/slice.

Expired or malformed waivers fail closed. Active waivers change `BLOCK` to `WARN`, never to
`PASS`, and remain visible in evidence.

## Evaluation additions

### Slice and tail gates

Case results are grouped by declared slices. Reports include selected case IDs, count,
means, tails, and failed gates for every slice. A slice below its minimum count is
`insufficient_evidence`; policy decides whether that is `WARN` or `BLOCK`.

Quantiles use a documented deterministic linear interpolation method. Latency and cost
support p50, p95, and p99. Paired comparisons include mean delta, median delta, standardized
paired effect, and deterministic bootstrap bounds. Holm correction controls family-wise
error across simultaneously gated metrics. Minimum sample estimates use a normal
approximation and are advisory evidence, not a pass condition unless policy declares it.

### Evaluator calibration

Calibration input binds case IDs to one or more human reviewer labels and automated scores.
The report includes coverage, MAE, threshold accuracy, false-pass rate, false-block rate,
and pairwise Cohen kappa for binary reviewer labels. Multi-reviewer agreement is the mean
of defined reviewer-pair kappas and reports insufficient evidence when no pair overlaps.
Calibration policies can gate accuracy, MAE, false-pass rate, and agreement.

### Agent trace graph

Trace graph 1.0 represents a trace as ordered spans with stable IDs, parent IDs, kind,
operation, input/output, timing, status, attributes, and optional tool call details. It
preserves original vendor attributes and records the adapter version.

Deterministic metrics include tool-name precision/recall, tool-argument exactness, expected
ordering, tool success rate, retrieval document recall, error recovery, and excess-step
ratio. Component failures retain span IDs for localization. The OpenTelemetry adapter maps
known `gen_ai.*` attributes but preserves unrecognized and development-status attributes.

## Benchmark lifecycle

Dataset manifest 1.0 records dataset ID/version, case digests, splits, slice counts, source
classification, owners, and review state. Validation provides:

- duplicate case-ID and normalized-content detection;
- exact and normalized-content leakage across declared splits;
- minimum per-slice coverage;
- missing provenance and unreviewed production-derived case quarantine;
- a deterministic diff between dataset versions.

Promotion is `draft -> reviewed -> accepted -> superseded`. Every transition records actor,
timestamp, reason, previous state, and manifest digest. Invalid transitions fail closed.

## Explainability and reports

`ragops explain` consumes a comparison/evidence report and returns:

- canonical decision and unwaived/waived gates;
- policy path and observed/allowed values;
- affected slice and case IDs;
- relevant provenance changes;
- minimum threshold or metric change required to clear numeric gates.

The flagship HTML report renders summary, regression path, slice heatmap, case evidence,
provenance, limitations, and remediation without JavaScript injection sinks. All dynamic
content uses text nodes. A restrictive CSP blocks remote resources and inline event
handlers. Executive, engineer, and auditor demo profiles render different summaries from
the same evidence.

## Governance and adoption

The SQLite governance store contains immutable artifact records, baseline states, review
queue items, reviewer decisions, waiver records, and audit events. The CLI exposes list,
submit, review, promote, supersede, and audit operations. Pairwise reviews hide candidate
labels until a decision is recorded. Multi-reviewer agreement is reported, while state
transitions require the configured minimum approvals.

Adapters operate on explicit local files. They never fetch remote traces, upload data, or
read credentials. Import output records producer, producer schema/version when present,
adapter name/version, unmapped fields, and conversion warnings.

## Packaging, security, and CI

- The wheel includes schemas, packaged API, and workbench assets.
- A clean-wheel smoke test runs CLI demo and imports the API only when the `api` extra is
  installed.
- The workbench never stores API keys outside the active tab, interpolates untrusted HTML,
  or loads remote assets. API request limits and fail-closed authentication remain.
- JUnit represents failed gates as test failures and warnings as skipped tests. SARIF uses
  stable rule IDs and artifact-relative locations. GitHub summaries use bounded Markdown.
- Consumer GitHub/GitLab templates call a pinned RAGOps version, verify the evidence bundle,
  publish bounded artifacts, and expose the canonical decision as a required check.
- Repository CI validates Python 3.11, 3.12, and 3.13 on pushes and pull requests. Publishing
  remains a separate tag-bound Trusted Publishing workflow.

## Flagship demo

`ragops demo --profile executive|engineer|auditor` remains credential-free and under five
minutes. It generates the same BLOCK regression, an evidence bundle, JSON/Markdown/HTML,
JUnit, SARIF, and step-summary outputs. The report explicitly marks the data synthetic.

The engineer view localizes citation and groundedness failures to cases and policy paths.
The auditor view exposes hashes, versions, provenance, active waivers, and limitations. The
executive view states decision, business risk, and remediation without overstating adoption.

## Release process

1. Run Ruff, the full test suite, supported-Python matrix where available, schema instance
   validation, demos, API/workbench smoke tests, and clean-wheel installation.
2. Build wheel/sdist, SBOM, checksums, and local release evidence from a clean commit.
3. Verify version parity across package, changelog, plugin manifests, skills, examples, and
   release notes.
4. Create annotated `v2.0.0`, push the branch/tag, and promote the exact local artifacts to
   a GitHub Release.
5. Publish those verified artifacts to PyPI through OIDC Trusted Publishing and verify a
   clean install from PyPI.
6. Update the ChatGPT skills-only plugin manifest and submission evidence, validate the
   plugin package, submit/update it through the authenticated OpenAI directory workflow,
   and record any account-only review state without claiming approval prematurely.

## Verification criteria

- All existing tests remain green and every production behavior added here has a witnessed
  failing test before implementation.
- Legacy CLI smoke fixtures are byte-compatible unless the output is explicitly versioned.
- Contract migration round trips validate and never overwrite inputs.
- Evidence tampering, traversal, symlinks, expiration, leakage, invalid transitions, and
  untrusted HTML each have negative tests.
- The built wheel contains API, workbench, and schemas and passes isolated installation.
- The dependency-free core imports without any optional dependency installed.
- Demo artifacts agree on decision, gate IDs, hashes, limitations, and version.
- Release claims distinguish synthetic benchmark evidence, production-derived evidence,
  PyPI publication, GitHub publication, ChatGPT submission, and ChatGPT approval.
