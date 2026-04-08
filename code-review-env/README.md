# CodeReviewEnv

Dependency-aware RL environment for Python code review, backed by persistent SQLite/libSQL graph storage.

## Implemented Through Phase 5

Phase 1:

- Seed pipeline parses Python modules, runs linters, and stores nodes/edges/findings in DB.
- Hash-based cache avoids unnecessary re-parse.

Phase 2:

- Graph manager loads graph from DB and exposes deterministic traversal and neighbor queries.
- Observation builder enforces strict 2000-token hard cap.

Phase 3:

- Typed actions/rewards and deterministic easy/medium graders.
- Hard grader includes deterministic graph checks + temperature=0 LLM judge.
- Review annotations are persisted per step.

Phase 4:

- Implemented `CodeReviewEnv.reset()` / `step()` / `state()` runtime.
- Added task registry and task orchestration for `style_review`, `logic_review`, `cascade_review`.
- Added operational FastAPI endpoints for automation and future phases.
- Added module override policy for direct module reviews.

Phase 5:

- Added `visualizer/pyvis_renderer.py` for standalone interactive dependency graph HTML output.
- Added `visualizer/report_generator.py` for markdown + JSON reports from persisted DB state.
- Added module-filtered report scope (seed modules + related dependency neighbors by hop count).
- Added confidence scoring that balances precision/recall with severity/security coverage and attribution validity.
- Added API endpoint to generate artifacts and CLI support for real project runs.

Phase 6:

- Added adaptive hard-grader fusion: deterministic graph gate + primary judge + verifier judge.
- Added disagreement-aware reweighting to reduce single-model catastrophic errors.
- Added per-edge `connection_summary` generation using LLM with deterministic fallback.
- Added optional LoRA trajectory logging for cross-project learning data collection.
- Added root `.env` support for centralized configuration management.

## Core Runtime Components

- `env/environment.py`
  - Persistent episode runtime over SQLite.
  - Deterministic module progression and reward accumulation.
  - Task-aware reset/step/state semantics.

- `env/state.py`
  - Strict Pydantic state models for episode and graph status.

- `tasks/task_registry.py`
  - Static task registration and dependency-aware module resolution.
  - Direct review policy:
    - easy task: optional direct module override only.
    - medium/hard tasks: module override expands one-hop dependencies for context reliability.

- `server/app.py`
  - API endpoints:
    - `POST /reset`
    - `POST /step`
    - `GET /state`
    - `GET /health`
    - `GET /tasks`
    - `GET /debug/state`
    - `POST /debug/reset-annotations`
    - `POST /tasks/{task_id}/run`
    - `GET /reports/accuracy`
    - `POST /reports/generate`
    - `GET /graph/export`

- `visualizer/pyvis_renderer.py`
  - Renders dependency graph with review-aware colors and edge-type styling.
  - Produces standalone HTML suitable for local and hosted viewing.

- `visualizer/report_generator.py`
  - Produces:
    - `*_report.md`
    - `*_report.json`
    - `*_graph.html`
  - Includes:
    - module-level summaries
    - security findings analysis
    - cascade attribution summaries
    - RL trajectory integrity notes
    - confidence scoring metrics

## Database and Turso Support

The project remains SQLite-first and supports Turso/libSQL via environment variables.

Primary DB configuration:

- `GRAPHREVIEW_DATABASE_URL`
  - If set, used directly by SQLAlchemy.
  - Works for local SQLite and SQLAlchemy-compatible backends.

Turso/libSQL fallback configuration:

- `TURSO_DATABASE_URL` (example: `libsql://your-db.turso.io`)
- `TURSO_AUTH_TOKEN`
- `GRAPHREVIEW_REMOTE_SQLITE_URL` (alias of `TURSO_DATABASE_URL`)
- `GRAPHREVIEW_REMOTE_SQLITE_AUTH_TOKEN` (alias of `TURSO_AUTH_TOKEN`)

When `GRAPHREVIEW_DATABASE_URL` is not set and `TURSO_DATABASE_URL` is set, engine is built as:

- `sqlite+${TURSO_DATABASE_URL}?secure=true`
with `auth_token` connect arg.

## LLM and Runtime Env Vars

`.env` at project root is auto-loaded by runtime configuration, DB initialization, and server startup.

Judge settings:

- `GRAPHREVIEW_JUDGE_PROVIDER` (default `ollama_openai_compat`)
- `GRAPHREVIEW_JUDGE_MODEL` (default `gemma4:e4b`)
- `GRAPHREVIEW_JUDGE_BASE_URL` (default `http://localhost:11434/v1`)
- `GRAPHREVIEW_JUDGE_API_KEY` (default `ollama`)
- `GRAPHREVIEW_JUDGE_TIMEOUT_SECONDS` (default `8`)
- `GRAPHREVIEW_JUDGE_ENABLED` (`true|false`, default `true`)
- `GRAPHREVIEW_JUDGE_MAX_CALLS` (default `200`)
- `GRAPHREVIEW_JUDGE_MAX_CONSECUTIVE_FAILURES` (default `3`)
- `GRAPHREVIEW_JUDGE_THINK` (`false|true|low|medium|high`, default `false`)

Verifier and adaptive fusion settings:

- `GRAPHREVIEW_VERIFIER_ENABLED` (default `true`)
- `GRAPHREVIEW_VERIFIER_PROVIDER`
- `GRAPHREVIEW_VERIFIER_MODEL`
- `GRAPHREVIEW_VERIFIER_BASE_URL`
- `GRAPHREVIEW_VERIFIER_API_KEY`
- `GRAPHREVIEW_VERIFIER_TIMEOUT_SECONDS`
- `GRAPHREVIEW_JUDGE_WEIGHT_DETERMINISTIC` (default `0.5`)
- `GRAPHREVIEW_JUDGE_WEIGHT_PRIMARY` (default `0.3`)
- `GRAPHREVIEW_JUDGE_WEIGHT_VERIFIER` (default `0.2`)
- `GRAPHREVIEW_JUDGE_DISAGREEMENT_THRESHOLD` (default `0.5`)

Edge summary settings:

- `GRAPHREVIEW_EDGE_SUMMARY_ENABLED` (default `false`, enable when you want LLM edge summaries)
- `GRAPHREVIEW_EDGE_SUMMARY_MODEL`
- `GRAPHREVIEW_EDGE_SUMMARY_BASE_URL`
- `GRAPHREVIEW_EDGE_SUMMARY_API_KEY`
- `GRAPHREVIEW_EDGE_SUMMARY_TIMEOUT_SECONDS`
- `GRAPHREVIEW_EDGE_SUMMARY_MAX_CALLS`

LoRA trajectory hooks:

- `GRAPHREVIEW_LORA_ENABLED` (default `false`)
- `GRAPHREVIEW_LORA_DATA_PATH` (default `outputs/lora/transitions.jsonl`)

Generate a LoRA-ready SFT dataset from transitions:

```bash
python -m llm.lora_finetune --transitions outputs/lora/transitions.jsonl --output outputs/lora/sft_dataset.jsonl
```

General runtime settings:

- `GRAPHREVIEW_SOURCE_ROOT` (default `sample_project`)
- `GRAPHREVIEW_DB_PATH` (optional local DB path)
- `GRAPHREVIEW_DB_ECHO` (`true|false`, default `false`)
- `GRAPHREVIEW_MAX_STEPS_PER_EPISODE` (default `80`)
- `GRAPHREVIEW_MAX_FILES` (default `5000`)
- `GRAPHREVIEW_SEED_WORKERS` (default `min(4, cpu_count)`)
- `GRAPHREVIEW_PROGRESS` (`true|false`, default `true`)
- `GRAPHREVIEW_OUTPUT_DIR` (optional report output folder, default `outputs`)

## Quickstart

```bash
pip install -r requirements.txt
python -m db.seed sample_project/
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

Run API smoke checks:

```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/tasks
```

## Unified One-Command Runner

Run seed + easy/medium/hard reviews + artifact generation on any target codebase:

```bash
graphreview /absolute/path/to/your/codebase --force-seed
```

Equivalent without installing entrypoints:

```bash
python run_project.py /absolute/path/to/your/codebase --force-seed
```

Optional focused run:

```bash
graphreview /absolute/path/to/your/codebase --modules checkout auth --filter-hops 1 --report-prefix myrun
```

## Direct Module Review (Phase 4)

Example: run `logic_review` with explicit module focus:

```bash
curl -s -X POST http://localhost:8000/reset \
  -H "content-type: application/json" \
  -d '{"task_id":"logic_review","module_override":["checkout"]}'
```

Policy behavior:

- For medium/hard tasks, module overrides are automatically expanded to one-hop dependencies and dependents.
- This preserves dependency context quality for cascade reasoning.

CLI module-filtered execution (generic, real projects supported):

```bash
python -m graders.review_runner /path/to/project \
  --grader hard \
  --force-seed \
  --modules checkout auth \
  --filter-hops 1 \
  --report \
  --output-dir outputs/real_project \
  --report-prefix real_project
```

This mode keeps review scope connected to selected modules by traversing related dependencies.

API report generation (future UI/server integration):

```bash
curl -s -X POST http://localhost:8000/reports/generate \
  -H "content-type: application/json" \
  -d '{"module_override":["checkout"],"hops":1,"output_dir":"outputs/api"}'
```

Frontend results console (served by uvicorn app):

- `GET /` opens the report browser UI.
- `GET /ui/results` lists discovered `*_report.json` artifacts under `GRAPHREVIEW_OUTPUT_DIR`.
- `GET /ui/result?report_path=...` returns report payload + DB schema columns + connectivity diagnostics.
- `GET /artifacts/...` serves generated HTML/JSON/Markdown assets for direct viewing.

If graphs look fragmented, regenerate with the latest parser/edge builder and force reseed:

```bash
python -m db.seed /path/to/project --force --db-path /tmp/graphreview.db
```

## Accuracy Verification Against Ground Truth

Verified on `sample_project` by running each task with deterministic action generation and comparing stored review actions against persisted linter findings.

Observed run (current implementation):

- `style_review`: precision `1.0`, recall `1.0`
- `logic_review`: precision `1.0`, recall `1.0`
- `cascade_review`: precision `1.0`, recall `1.0`

Notes:

- Accuracy endpoint computes precision/recall from persisted annotations and module findings.
- Hard grader stores judge metadata for auditability in structured annotation payloads.

## Confidence Scoring Policy (Phase 5)

Confidence score is designed to generalize beyond sample fixtures. It is not recall-only.

Computed metrics:

- precision
- recall
- f1
- severity-weighted finding coverage
- security finding coverage (Bandit findings matched by review flags)
- dependency attribution validity (graph-backed)
- consistency (penalizes contradictory terminal actions)

Weighted confidence formula:

- `0.35 * f1`
- `0.20 * severity_weighted_coverage`
- `0.15 * security_coverage`
- `0.20 * dependency_attribution_validity`
- `0.10 * consistency`

This design rewards useful review behavior on unseen modules where raw recall alone can be misleading.

## Visualization and Reporting Output

Generated artifacts include:

- Interactive graph with color-coded review status and edge-type styling.
- Markdown report with module summaries, security analysis, and cascade attribution details.
- JSON report with machine-readable nodes, edges, reviews, and quality metrics.

Security report behavior:

- Security findings are listed per module with severity/code/line/message.
- Reports call out what is wrong and whether reviews covered each security signal.
- Cascade attributions are listed with step/action/reward evidence.

## Testing

Targeted regression + phase tests:

```bash
pytest -q tests/test_phase2_graph_manager.py \
  tests/test_phase2_token_budget.py \
  tests/test_phase2_observation.py \
  tests/test_graders.py \
  tests/test_phase5_reporting.py \
  tests/test_phase4_environment.py \
  tests/test_phase4_server.py
```

## OpenEnv Metadata

`openenv.yaml` includes phase 4 task metadata, runtime endpoint contract, and model type references for action/observation/state.

## Security and Design Notes

- SQLite/libSQL remains the source of truth for graph, episode, and annotation state.
- Reset behavior clears only episode-specific annotations, not seeded graph/linter data.
- Observation token budget is hard-enforced.
- Graders and task traversal use deterministic ordering and strict typed boundaries.
- Review annotations are stored with structured JSON payloads for future visualization/report phases.
