# Phoenix recorded scores

This example converts a complete, already-recorded Phoenix trace-annotation response into the RAGOps external-metrics envelope. It is intentionally offline: it uses only the Python standard library, reads local JSON, and does not initialize Phoenix, call a hosted service, or require credentials.

## Run it

From the repository root:

```bash
python examples/phoenix_recorded_scores/adapter.py \
  --input examples/phoenix_recorded_scores/annotations.json \
  --case-ids examples/phoenix_recorded_scores/case_ids.json \
  --annotation-name answer_quality \
  --output /tmp/phoenix-external-metrics.json
```

The output is equivalent to `expected-envelope.json` and can be passed to the existing external-metrics evaluator. The `custom` provider keeps the published 0.1 envelope unchanged; the `phoenix.` metric prefix identifies the score's provenance. This does not claim that Phoenix and RAGOps metrics are equivalent.

When using the envelope in an evaluation policy, the resulting metric key is `custom.phoenix.answer_quality` (the evaluator name is the envelope provider, followed by the metric name).

## Input boundary

The input fixture follows Phoenix's recorded trace-annotation shape:

- `data` contains recorded Phoenix trace annotations, including the REST response fields (`id`, timestamps, `source`, `user_id`, `trace_id`, `name`, `annotator_kind`, `result`, and `metadata`). The converter reads only the fields needed for the case join and score envelope.
- `result.score` is required and must be a finite number. Labels and explanations are retained in the source record but are not silently converted into metrics.
- `metadata.ragops_case_id` is an explicit join key. The adapter never guesses a RAGOps case from array order or a Phoenix trace ID.
- `next_cursor` must be absent or `null`; a non-null cursor means the export is incomplete and is rejected.
- `case_ids.json` is the complete expected case set. Missing, unknown, duplicate, or non-canonical case IDs fail closed; IDs are matched exactly and surrounding whitespace is rejected. Multiple Phoenix annotations on one trace are allowed, but they still must resolve to distinct RAGOps case IDs.

Phoenix owns the annotation's meaning, scale, and optimization direction. This example copies the recorded score (`87.5` remains `87.5`) without clamping, normalization, inversion, or recalibration. The RAGOps policy owner must choose a compatible gate, such as a minimum for a higher-is-better score or a maximum for a lower-is-better score.

Authoritative references checked on 2026-08-09:

- [Phoenix annotation concepts](https://arize.com/docs/phoenix/tracing/concepts-tracing/annotations-concepts)
- [Phoenix annotation REST models](https://github.com/Arize-ai/phoenix/blob/main/src/phoenix/server/api/routers/v1/annotations.py)
