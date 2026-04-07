# Phase 04 Plan - OpenEnv Core, Task Runtime, and API Contract (for GPT-5.3)

## 1) Phase Objective
Deliver Phase 04 only, without implementing Phase 05/06 features:
- Build OpenEnv-compliant environment runtime: `step()` / `reset()` / `state()`
- Implement typed environment state model and task orchestration
- Register and execute all three tasks end-to-end
- Expose environment through FastAPI server compatible with current local use and future hosted deployment
- Preserve SQLite as source of truth and never re-parse on reset

## 2) Inputs and Constraints From Prior Phases
1. Phase 01/02/03 artifacts are assumed available:
- Seeded SQLite with modules, edges, linter flags, annotations, task runs
- Graph manager + token budgeting observation system
- Action/reward models + deterministic graders (hard grader with temperature=0 judge)

2. Hard constraints that Phase 04 must enforce:
- DB-first state persistence (no critical in-memory-only state)
- `reset()` clears current task-run review annotations only, not seed graph/linter data
- Observations remain token-bounded (<=2000)
- OpenEnv contract is authoritative for method signatures and typed models

## 3) Context7-Validated API Decisions
1. OpenEnv (`/meta-pytorch/openenv`)
- Custom environment must implement `reset`, `step`, and `state`
- Use typed action/observation/state models backed by Pydantic
- Keep deterministic transition logic in environment core

2. SQLAlchemy ORM (`/websites/sqlalchemy_en_20_orm`)
- Use explicit `sessionmaker` and short-lived session scopes
- Keep transaction boundaries explicit (`with Session.begin()` where appropriate)
- Construct engine from env-configured URL to support local SQLite and SQLAlchemy-compatible alternatives

3. FastAPI (`/websites/fastapi_tiangolo`)
- Dependency-injected session provider for request lifecycle
- Pydantic model validation at boundaries
- Deterministic API responses and clear status/error handling for task execution flow

## 4) Scope for Phase 04
Required files:
- `env/environment.py`
- `env/state.py`
- `tasks/task_registry.py`
- `tasks/easy_task.py`
- `tasks/medium_task.py`
- `tasks/hard_task.py`
- `openenv.yaml`
- `server/app.py` (or root server entry if project keeps this convention)

Phase-04-compatible updates allowed in existing files only if needed for wiring:
- `db/database.py` for env-driven engine/session configuration
- `db/store.py` for task-run scoped reset helpers
- `README.md` for runtime contracts and env variables (documentation only)

## 5) Environment Variable Contract (Phase 04 Baseline)
Database:
- `GRAPHREVIEW_DATABASE_URL`
  - default: `sqlite:///./code_review_env.db`
  - required behavior: accept SQLAlchemy-compatible URL so remote SQLite-compatible backends can be used later
- `GRAPHREVIEW_DB_ECHO` default `false`

Judge provider/model switching:
- `GRAPHREVIEW_LLM_PROVIDER` values: `ollama_openai_compat`, `openai_compat`, `hf_openai_compat`
- `GRAPHREVIEW_LLM_BASE_URL` default local Ollama-compatible endpoint
- `GRAPHREVIEW_LLM_API_KEY` default local-safe placeholder for Ollama, required in hosted mode
- `GRAPHREVIEW_LLM_MODEL_AGENT` (baseline agent model)
- `GRAPHREVIEW_LLM_MODEL_JUDGE` default `gemma4:e4b`
- `GRAPHREVIEW_LLM_TEMPERATURE_JUDGE` fixed to `0` in hard grader logic

Runtime behavior:
- `GRAPHREVIEW_MAX_STEPS_PER_MODULE` default task-specific
- `GRAPHREVIEW_MAX_STEPS_PER_EPISODE` safety cap
- `GRAPHREVIEW_ENABLE_SECURITY_SCAN_ON_SEED` default `true`

Compatibility note:
Using OpenAI-compatible endpoints with base URL switching keeps current Ollama setup and future HF-hosted migration mostly configuration-only.

## 6) Design of `GraphState` for Persistent RL State
File: `env/state.py`

Define strict Pydantic v2 models (no loose fields):
- `ModuleReviewState`
  - `module_id`, `review_status`, `issues_found`, `last_action`, `last_reward`, `updated_at`
- `EpisodeState`
  - `episode_id`, `task_id`, `current_module_id`, `modules_remaining`, `step_count`, `cumulative_reward`, `done`, `status`
- `GraphState`
  - `episode`: `EpisodeState`
  - `modules`: list[`ModuleReviewState`]
  - `edge_count`, `module_count`, `annotation_count`
  - `task_run_id` (DB id)

Persistence rule:
- Environment reconstructs `GraphState` from SQLite records at boundaries rather than trusting process memory.

## 7) Design of `CodeReviewEnv` Runtime
File: `env/environment.py`

Core responsibilities:
1. `reset(task_id: str, seed: int | None = None, ...) -> CodeObservation`
- Validate task_id via task registry
- Create new `task_runs` row with `running` status
- Clear only task-run scoped annotations for current run context (or fresh run id)
- Resolve first module from task-defined ordering
- Return budgeted observation

2. `step(action: ReviewAction, ...) -> CodeObservation`
- Validate action with strict Pydantic model
- Route to task-specific grader
- Persist annotation and reward atomically
- Update module review status and episode counters in DB
- Transition module pointer or finalize episode
- Return next observation with latest token-bounded context

3. `state() -> GraphState`
- Hydrate full annotated graph summary from DB
- Include current episode/task run metadata

Determinism rules:
- No random ordering without explicit seeded RNG
- Tie-break all orderings lexicographically by module id
- Easy/medium graders remain pure deterministic

## 8) Task System Plan
Files: `tasks/task_registry.py`, `tasks/easy_task.py`, `tasks/medium_task.py`, `tasks/hard_task.py`

Task contract (`TaskDefinition` protocol/model):
- `task_id`
- `description`
- `entry_modules`
- `module_selection_strategy`
- `grader_name`
- `completion_criteria`
- `max_steps`

Task implementations:
1. `easy_task`:
- Focus: `cart.py` style-only
- Grader: easy
- Completion: all style findings addressed or max steps reached

2. `medium_task`:
- Focus: `checkout.py` + `auth.py`
- Grader: medium
- Completion: null-risk flagged and supported comment present

3. `hard_task`:
- Focus: cascade `config.py -> auth.py -> checkout.py`
- Grader: hard with graph consistency + judge call (`gemma4:e4b`, temp=0)
- Completion: downstream bug + correct root attribution evidence

Registry behavior:
- Explicit static registration with strict IDs
- Fail fast on unknown task IDs

## 9) OpenEnv and API Layer Plan
Files: `openenv.yaml`, `server/app.py`

`openenv.yaml` must define:
- Environment metadata (name, version, description)
- Action/observation/state schema references
- Task list and defaults
- Runtime capabilities and concurrency flags

FastAPI wrapper responsibilities:
- Expose endpoints required by OpenEnv validation flow
- Parse incoming action payloads into `ReviewAction`
- Surface structured errors for invalid actions/task transitions
- Health endpoint and reset ping behavior for hosted runtime checks

## 10) Review Accuracy, Storage Integrity, and Visualization Readiness
Accuracy verification in Phase 04 (without building visualizer yet):
1. Action-to-finding correctness:
- For each task, replay canonical action scripts and verify rewards align with expected findings

2. Storage integrity checks:
- Every accepted action creates a `review_annotations` row with correct `task_id`, `module_id`, `reward_given`, and timestamp
- `review_status` transitions are valid (`pending -> in_progress -> reviewed`)

3. Graph-readiness checks for later Pyvis:
- Persisted annotations include enough structured metadata for node tooltips/panels (action type, content, attribution, reward)
- Edge and node keys remain stable IDs suitable for rendering cross-links

4. Hard-review quality checks:
- Enforce evidence requirement for dependency attribution
- Record judge metadata (`model`, `provider`, `temperature`, `prompt_hash`, `score`) for auditability and later report quality review

## 11) Direct Module Testing (Beyond Sample Project)
Add module-targeted execution path in environment/task API design:
- Support `reset(task_id=..., module_override=[...])`
- Validate module IDs exist in DB graph
- Run same grading pipeline for arbitrary modules without changing seeded sample fixtures

Use cases:
- Regression testing a single production-like module
- Spot-checking grading behavior on custom codebases
- Running focused hard-review chains outside default task definitions

## 12) RL Validity Verification Plan (Phase 04)
The environment should prove RL loop integrity even before training:
1. Markov transition sanity:
- Next observation depends on prior state + action + persisted DB updates

2. Reward causality:
- Rewards derive from graded action against stored ground truth and graph relationships

3. Episode lifecycle correctness:
- `reset -> step* -> done` semantics are consistent across all tasks

4. Persistent trajectory:
- Full episode can be reconstructed from DB (`task_runs` + `review_annotations` + module statuses)

5. Deterministic replay harness:
- Replaying same action sequence on same seeded DB returns identical cumulative reward for easy/medium
- Hard task deterministic except judge-model nondeterminism is constrained by `temperature=0` and fixed rubric

## 13) Security and Quality Gates to Include in Phase 04 Plan
Static and dynamic quality checks:
- Ruff (lint + import/order hygiene)
- mypy (strict on env/tasks/server modules)
- pytest with deterministic fixtures
- Bandit security scan
- Semgrep for Python security anti-patterns
- pip-audit for dependency vulnerabilities

Architecture quality checks:
- Keep interfaces minimal and explicit (Occam's razor)
- Avoid duplicated business logic between environment and task modules
- Centralize env var parsing/config object

## 14) Step-by-Step Build Order for GPT-5.3
1. Finalize env var config module and database URL/provider model switches.
2. Implement `env/state.py` strict Pydantic models.
3. Implement task definitions and registry.
4. Implement `env/environment.py` with DB-backed reset/step/state flow.
5. Wire FastAPI/OpenEnv server endpoints and `openenv.yaml`.
6. Add direct-module override support for targeted testing.
7. Add integration tests for all three tasks and DB persistence checks.
8. Add RL validity tests (trajectory replay and determinism checks).
9. Document runtime contracts, env vars, and operational runbook.

## 15) Phase 04 Verification Checklist
Must pass before Phase 04 is declared complete:
1. `openenv validate` passes.
2. All three tasks run end-to-end without runtime errors.
3. `state()` returns full annotated graph summary from DB.
4. `reset()` does not reseed/reparse and does not delete base module/edge/linter data.
5. Review annotations are accurate, persisted, queryable, and graph-render ready.
6. Direct module override flow works for non-sample module IDs.
7. Easy/medium behavior is replay-deterministic across 10 runs.
8. Hard grader uses `gemma4:e4b` with `temperature=0` and records prompt hash.

## 16) Explicit Non-Goals for Phase 04
- No full Phase 05 visualization implementation yet
- No final `inference.py` mandatory log contract work (Phase 06)
- No schema overhaul unless approved by user

## 17) Design Questions Requiring User Confirmation Before Coding
1. DB schema alignment:
- Should hard-review judge audit metadata be stored in existing annotation JSON payload fields, or do you want a dedicated DB table now?

2. Remote SQLite expectation:
- Which remote SQLite-compatible backend do you intend to use first (for example, libSQL/Turso)? This affects URL examples and connection options.

3. OpenEnv endpoint surface:
- Do you want strict minimum OpenEnv endpoints only, or additional operational endpoints now (`/health`, `/debug/state`, `/tasks/{id}/run`)?

4. Direct module override policy:
- Should arbitrary module overrides be allowed in all tasks, or only in a dedicated `custom_review` task mode?

5. Hard-review quality policy:
- Should hard grader require a minimum judge score threshold before permitting `APPROVE`, or keep scoring-only without action blocking?
