# `config/` — the control panel

`taxonomy.yaml` is the single source of truth for:

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

## `environments/` — live dotenv files (gitignored)

The runtime dotenv files live under `config/environments/` (templates committed
as `.example`, live files gitignored); every loader resolves them via
`src/env_utils.py` (`ENV_DIR` / `BRAINTRUST_ENV_FILE` / `DOTENV_FILE` /
`LANGFUSE_ENV_FILE` + `resolve_env_file()` for CLI `--env-file` args):

| Template | Live copy | Holds |
|---|---|---|
| `.env.example` | `.env` | OpenRouter key, provider overrides, observability flags |
| `braintrust.env.example` | `braintrust.env` | Braintrust org/project/keys — config source of truth |
| `langfuse.env.example` | `langfuse.env` | Langfuse project-scoped keys (llm-dojo experiment env) |

```bash
cp config/environments/braintrust.env.example config/environments/braintrust.env
cp config/environments/.env.example config/environments/.env
cp config/environments/langfuse.env.example config/environments/langfuse.env
```

Extra Langfuse projects are added as
`config/environments/langfuse-<project>.env` (pass via `--env-file`; ignored by
`*.env.local` or an explicit pattern).

