# Versioned contracts

RAGOps keeps contract validation and migration in the dependency-free core.

| Contract | Versions | Compatibility rule |
| --- | --- | --- |
| Scenario | 0.1, 0.2 | Explicit `contract migrate`; inputs are never overwritten |
| Trace | 0.3, 0.4 | Preserve unknown producer attributes during migration |
| Trace graph | 1.0 | Validate graph references and reject cycles |
| Dataset manifest | 1.0 | Provenance, review state, split membership, leakage checks |
| Evidence bundle | 1.0 | Canonical manifest, SHA-256 content addresses, no undeclared files |
| Release policy/decision | 2.0 / 1.0 | Stable gate IDs and canonical `PASS`, `WARN`, `BLOCK` |

Use `ragops contract validate`, `ragops contract diff`, and `ragops contract migrate`. Schema files are packaged under `ragops/schemas` and available offline.
