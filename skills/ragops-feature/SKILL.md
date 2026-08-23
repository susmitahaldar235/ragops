---
name: ragops-feature
description: Implement or review a RAGOps capability or repository contract while preserving evaluation semantics, compatibility, offline behavior, and release evidence.
---

# RAGOps feature workflow

Use for any new or changed capability or repository contract.

1. Read `AGENTS.md`, `docs/product/requirements.md`,
   `docs/architecture/decisions.md`, and the affected canonical guide.
2. Record the user outcome, public compatibility, acceptance criteria, and
   explicit non-goals before implementation.
3. Keep evaluation semantics in `src/ragops/`; keep adapters outside the core.
4. Add contract, unit, integration, and negative coverage proportional to risk.
5. Preserve offline deterministic behavior unless an optional adapter is the
   stated scope.
6. Run lint, full tests, and affected CLI/API paths.
7. Update the canonical documentation and changelog; remove superseded copy.

Never silently change metric meaning, schema compatibility, critical-gate
behavior, or the open-core boundary.
