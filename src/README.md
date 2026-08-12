# `src/` — core modules

Everything the eval loop builds on. The package is importable from anywhere
(`pip install -e .`).

| Module | Responsibility |
|---|---|
| `bootstrap.py` | percentile-bootstrap 95% CIs over per-document scores (`bootstrap_ci`) + two-sample delta significance (`delta_significance`) |
| `cost_models.py` | verified per-model token prices + deterministic cost estimation (`estimate_cost`, `estimate_for_record`) |
| `prompts.py` | ALL prompts, versioned in `PROMPT_VERSIONS`; `get_prompt(version)`, `list_prompts()`. The version key IS the experiment identity |
| `experiment_log.py` | append-only JSONL + markdown renderer (`append_experiment`, `experiment_markdown`, `render_full_log`, `tokens_summary(model=)`) |
| `field_scoring.py` | field-type-aware content scorer + factuality audit + ambiguous band + embedding rescue |
| `scorers.py` | Braintrust lookups: `exact_match`, `failure`, `cost`, `per_class_stats`, `macro_accuracy` |
| `evaluation.py` | dataset validation, `dataset_fingerprint`, `ManifestStore` (resumable JSONL checkpoints) |
| `cuad_ground_truth.py` | CUAD 41-category catalog -> expected fields + presence + `build_subtype_handoff()` |
| `taxonomy.py` | loads `config/taxonomy.yaml` (doc classes, field types, agent->model mapping, thresholds) |
| `classifier.py` | label/confidence/reasoning parsers (RVL-CDIP style), `classify_image` |
| `braintrust_config.py` | loads `braintrust.env` / `.env` (org, project, model, api base) |
| `braintrust_utils.py` | Braintrust HTTP: list/fetch experiments, load/upload datasets, attachments |
| `langfuse_config.py` / `langfuse_tracing.py` | Langfuse mirror: project config + per-document tracer (`agent_observation`) |
| `llm_chain.py` | LangChain chain factory for the eval loops |
| `image_utils.py` | PDF/TIFF -> 1024x1024 grayscale PNG helpers |
| `env_utils.py` | dotenv loading + required-var validation |
| `openrouter_utils.py` | OpenRouter base URLs, message builders, prompt splitting |
