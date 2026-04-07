# CodeReviewEnv

Dependency-aware RL environment for Python code review, backed by persistent SQLite/libSQL graph storage.

## Implemented Through Phase 4

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
    - `GET /graph/export`

## Database and Turso Support

The project remains SQLite-first and supports Turso/libSQL via environment variables.

Primary DB configuration:

- `GRAPHREVIEW_DATABASE_URL`
  - If set, used directly by SQLAlchemy.
  - Works for local SQLite and SQLAlchemy-compatible backends.

Turso/libSQL fallback configuration:

- `TURSO_DATABASE_URL` (example: `libsql://your-db.turso.io`)
- `TURSO_AUTH_TOKEN`

When `GRAPHREVIEW_DATABASE_URL` is not set and `TURSO_DATABASE_URL` is set, engine is built as:

- `sqlite+${TURSO_DATABASE_URL}?secure=true`
with `auth_token` connect arg.

## LLM and Runtime Env Vars

Judge settings:

- `GRAPHREVIEW_JUDGE_PROVIDER` (default `ollama_openai_compat`)
- `GRAPHREVIEW_JUDGE_MODEL` (default `gemma4:e4b`)
- `GRAPHREVIEW_JUDGE_BASE_URL` (default `http://localhost:11434/v1`)
- `GRAPHREVIEW_JUDGE_API_KEY` (default `ollama`)
- `GRAPHREVIEW_JUDGE_TIMEOUT_SECONDS` (default `30`)

General runtime settings:

- `GRAPHREVIEW_SOURCE_ROOT` (default `sample_project`)
- `GRAPHREVIEW_DB_PATH` (optional local DB path)
- `GRAPHREVIEW_DB_ECHO` (`true|false`, default `false`)
- `GRAPHREVIEW_MAX_STEPS_PER_EPISODE` (default `80`)
- `GRAPHREVIEW_MAX_FILES` (default `5000`)
- `GRAPHREVIEW_SEED_WORKERS` (default `min(4, cpu_count)`)
- `GRAPHREVIEW_PROGRESS` (`true|false`, default `true`)

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

## Accuracy Verification Against Ground Truth

Verified on `sample_project` by running each task with deterministic action generation and comparing stored review actions against persisted linter findings.

Observed run (current implementation):

- `style_review`: precision `1.0`, recall `1.0`
- `logic_review`: precision `1.0`, recall `1.0`
- `cascade_review`: precision `1.0`, recall `1.0`

Notes:

- Accuracy endpoint computes precision/recall from persisted annotations and module findings.
- Hard grader stores judge metadata for auditability in structured annotation payloads.

## Testing

Targeted regression + phase tests:

```bash
pytest -q tests/test_phase2_graph_manager.py \
  tests/test_phase2_token_budget.py \
  tests/test_phase2_observation.py \
  tests/test_graders.py \
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
