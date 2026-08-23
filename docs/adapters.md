# Portable adapters

RAGOps converts evaluator exports into a dependency-free envelope before evaluation. Built-in profiles support Phoenix, Ragas, DeepEval, LangSmith, MLflow, Promptfoo, and custom JSON; no vendor SDK is imported by the core.

```bash
ragops adapter list
ragops adapter convert \
  --profile mlflow \
  --input mlflow-evaluation.json \
  --case-id case-001 \
  --output ragops-metrics.json
```

The output records the producer, adapter version, unmapped fields, and missing-case warnings. Unknown case IDs, duplicate metrics, and non-finite scores fail closed.

Third-party packages can register an adapter through the `ragops.adapters` entry-point group. The entry point must expose an object with `name`, `version`, and `convert(payload, context)` members and return `ragops.adapter_sdk.AdapterOutput`.
