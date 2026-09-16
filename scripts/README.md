<div align="center">

# ⚙️ Entity Extraction Scripts

**Utility scripts for the llm-entity-extraction package.**

</div>

---

## Functional index

| Group | Script | Purpose |
|:---|:---|:---|
| **Root tools** | `prompt_engineer.py` | Automated DRAFT-phase mutations for the docclass family (DMR-014 operators + registry) |
| | `run_agent_bench.py` | Durability benches for every classification-chain role |
| | `gen_edge_cases.py` | Edge-case suite generator — the durability matrix (writes `data/gt/edge_suites/`) |
| | `gt_workbench.py` | GT validation for hand-labeled extraction ground truth |
| | `smoke_vllm_endpoint.py` | Smoke-test a vLLM / OpenAI-compatible endpoint (KANBAN-096) |
| | `sync_edge_suites.py` | Sync generated edge suites into The-Mailroom's Langfuse env as datasets |
| | `durability_gate.sh` | Production-readiness scoreboard over the full agent roster (report-only) |
| | `release.py` | Semver release workflow for the package |
| **datasets/** | `build_*.py` / `publish_*.py` / `stream_*.py` / `export_*.py` | Dataset acquisition, building, streaming, and Hub publishing (v5/v6 lineage + v9 mirrors) |
| **deploy/** | `deploy_phoenix.sh` | Apache Phoenix deployment for local observability |
| **eda/** | `explore_cuad.py` / `explore_pipeline_sources.py` | CUAD + pipeline-source exploration |
| **eval/** | `run_*_eval.py` / `run_langfuse_*_eval.py` | Per-surface evaluation runners over registry models/Langfuse datasets |
| | `sync_braintrust_*.py` / `sync_langfuse_*.py` | Dataset/prompt sync to Braintrust + Langfuse |
| **reporting/** | `report_generator.py` / `export_*` / `monte_carlo_*` / `rescore_manifests.py` | Experiment reporting, decks, and monte-carlo analyzers |
| **site/** | `build_site.py` | Build the experiment site |

## Usage

```bash
cd packages/llm-entity-extraction

# Durable bench suite (per-role)
python scripts/run_agent_bench.py --role contracts_specialist --model <model>
scripts/durability_gate.sh 2           # scoreboard over all roles, limit 2

# Edge cases + GT workbench
python scripts/gen_edge_cases.py --all
python scripts/gt_workbench.py --help
```

## Related Files

- `reports/` — Generated reports
- `docs/` — Documentation
- `data/` — Source data