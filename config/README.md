# `config/` — the control panel

One file: `taxonomy.yaml`. It is the single source of truth for:

- `doc_classes:` — the document taxonomy (key, label, schema, specialist,
  field types)
- `confidence:` — classification thresholds (`high`/`low`/`retry_max`,
  `conflict_threshold`)
- `field_scoring:` — ambiguous band `[0.5, 0.85]`, bipartite match
  threshold, embedding model/rescue, `partial_gt_fields`,
  `containment_fields`, `token_coverage`
- `agents:` — agent -> model/provider mapping
- `vision:` — vision-enabled models and image budget
- `llm_retry:` — backoff/jitter tunables

**Editing `taxonomy.yaml` requires a process restart** — it is cached at
process level (`taxonomy.load_taxonomy` is `lru_cache`d). The same taxonomy
drives llm-mailroom (`llm-mailroom/src/config/taxonomy.yaml`); keep the two
in sync.
