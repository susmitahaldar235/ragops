# RAGOps regression check: FAIL

Scenario: `techretail-support-v1`

| Metric | Baseline | Candidate | Delta |
| --- | ---: | ---: | ---: |
| citation_coverage | 1 | 0.75 | -0.25 |
| citation_precision | 1 | 0.75 | -0.25 |
| lexical_groundedness | 0.6241 | 0.5299 | -0.0942 |
| avg_latency_ms | 767.25 | 254.75 | -512.5 |
| avg_cost_usd | 0.01 | 0.0026 | -0.0074 |
| critical_findings | 0 | 1 | +1 |

## Failed gates

- `candidate_release_gate`
- `citation_coverage_regression`
- `citation_precision_regression`
- `groundedness_regression`
- `new_critical_findings`
