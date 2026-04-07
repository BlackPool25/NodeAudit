# CodeReviewEnv — Phased Build Plan
## For: LLM-Assisted Development

---

## 🧠 What You Are Building

An OpenEnv-compliant reinforcement learning environment where an LLM agent learns to perform **dependency-aware code review**. 

The environment parses a Python codebase into a **persistent dependency graph** (nodes = modules, edges = import relationships). Each node stores compressed AST summaries, linter-generated ground truth issues, and agent-written review annotations.

The agent reviews one module per episode. It receives the **full code of the current module** plus **compressed AST summaries of its neighbors** (never full neighbor code — token budget). It takes multi-step actions (flag bugs, add comments, request context, amend upstream reviews). The environment rewards correct, well-attributed findings and penalizes false positives.

The final output is an **annotated dependency graph** — a machine-readable + human-readable map of the entire codebase with reviews on every module, including cross-module causal attributions.

This is differentiated from tools like CodeRabbit because:
- It models cascading dependency bugs (bug in B caused by design in A)
- Reviews are stored back into the graph and can be amended as agent learns more
- It is an RL training/evaluation environment, not a static analysis tool
- The agent learns a policy over multi-step decisions, not a single LLM call

---

## 🗂️ Persistence Strategy

**Use SQLite via SQLModel** for all persistent state. Do NOT reparse the codebase on every run. The database stores:
- Parsed module nodes (code, AST summary, linter flags)
- Graph edges (dependency relationships + reasons)
- Review annotations (written by agent, updatable)
- Episode history (for reproducibility)
- Task definitions and ground truth

On startup: check if DB exists → if yes, load graph from DB → if no, parse codebase and populate DB.

This makes demos fast (parse once, review many times) and makes `reset()` cheap (clear annotations only, keep graph structure).

---

## 📁 Target Project Structure

```
code-review-env/
├── openenv.yaml
├── Dockerfile
├── README.md
├── inference.py               # Required by spec, root level
├── requirements.txt
├── pyproject.toml
│
├── env/
│   ├── __init__.py
│   ├── environment.py         # Main CodeReviewEnv class
│   ├── models.py              # Pydantic: Observation, Action, Reward, GraphState
│   ├── graph.py               # Graph construction, traversal, compression
│   ├── observation_builder.py # Assembles tiered observation per step
│   └── reward.py              # Reward computation logic
│
├── db/
│   ├── __init__.py
│   ├── schema.py              # SQLModel table definitions
│   ├── store.py               # DB read/write operations
│   └── migrations.py          # Init and seed scripts
│
├── parser/
│   ├── __init__.py
│   ├── ast_parser.py          # AST extraction: signatures, imports, classes
│   ├── linter.py              # Pylint + Bandit runner, stores results to DB
│   └── summarizer.py          # Converts AST output → compressed node summary
│
├── graders/
│   ├── __init__.py
│   ├── base_grader.py         # Abstract grader interface
│   ├── easy_grader.py         # Linter match — fully deterministic
│   ├── medium_grader.py       # AST + line attribution match
│   └── hard_grader.py         # LLM-as-judge, temp=0, seed=42, rubric-constrained
│
├── tasks/
│   ├── __init__.py
│   ├── task_registry.py       # Registers and loads tasks
│   ├── easy_task.py           # Style/linter issue in isolated module
│   ├── medium_task.py         # Logic bug with direct dependency context
│   └── hard_task.py           # Cascading bug across 2+ modules
│
├── server/
│   ├── __init__.py
│   └── app.py                 # FastAPI server exposing OpenEnv HTTP endpoints
│
├── sample_codebase/           # Synthetic test codebase for demo
│   ├── auth.py
│   ├── checkout.py
│   ├── cart.py
│   ├── payments.py
│   └── config.py
│
└── tests/
    ├── test_parser.py
    ├── test_graders.py
    ├── test_environment.py
    └── test_inference.py
```

---

## 📐 Core Data Models (Design Intent — Implementation Is Your Choice)

### Graph Node
Stores everything about one module. Persisted in DB.
- module_id (filename/path)
- raw_code (full source)
- ast_summary (compressed: signatures, classes, exports)
- linter_flags (pre-computed ground truth from pylint/bandit)
- dependency_reason (why this module needs its neighbors — extracted from import context)
- review_annotation (agent-written, nullable, updatable)
- review_status (pending | in_progress | reviewed)
- review_summary (one-line, written at episode end)

### Graph Edge
- source_module_id
- target_module_id
- edge_type (explicit_import | implicit_name_resolution)
- import_line (the actual import statement)
- weight (1.0 explicit, 0.5 implicit)

### Observation (Pydantic)
- current_module: full code + full AST summary
- direct_dependencies: list of compressed node summaries (NOT full code)
- dependents: list of compressed node summaries
- existing_reviews: list of one-line review summaries from already-reviewed neighbors
- constraint_flags: any known forced decisions from upstream
- step_number: int
- episode_id: str

### Action (Pydantic, discriminated union)
- APPROVE
- FLAG_STYLE(line: int, description: str)
- FLAG_BUG(line: int, description: str)
- FLAG_SECURITY(line: int, description: str)
- FLAG_DEPENDENCY_ISSUE(source_module: str, description: str)
- ADD_COMMENT(text: str)
- REQUEST_CHANGES(summary: str)
- REQUEST_CONTEXT(module_id: str)  ← costs -0.1 reward, returns full code of neighbor
- AMEND_REVIEW(module_id: str, note: str)  ← retroactively updates neighbor annotation

### Reward (Pydantic)
- value: float (0.0–1.0)
- reason: str
- cumulative: float

---

## 🏗️ PHASE 1 — Foundation & Persistence
**Goal: Database schema, parser, graph construction. No RL yet.**

### Tasks
1. Define SQLModel schema for all tables (nodes, edges, annotations, episodes, tasks)
2. Build `ast_parser.py` — extract from any .py file: all function signatures with type hints, all class definitions, all import statements with source resolution, all module-level constants
3. Build `linter.py` — run pylint and bandit programmatically on a file, parse output into structured list of {line, severity, code, message}. Store results directly to DB as ground truth.
4. Build `summarizer.py` — convert AST output into a compressed summary string under 100 tokens. Format: "exports: [fn(args)->return, ...] | issues: N | depends_on: [module, ...]"
5. Build `store.py` — CRUD operations for all tables. Key operations: upsert_node, upsert_edge, get_node_with_neighbors, update_annotation, get_full_graph
6. Build `graph.py` — on first run: parse all files in target directory → populate DB. On subsequent runs: load from DB. Build NetworkX DiGraph from DB records. Implement traversal order: topological sort weighted by betweenness centrality (leaf modules first, high-centrality modules last).
7. Build `sample_codebase/` — 5 Python files with known injected issues: one style issue, one logic bug with a direct dependency cause, one security issue, one cascading bug where the root cause is 2 hops away. Document every injected issue in a ground_truth.json file.

### Completion Criteria
- `python -m parser.ast_parser sample_codebase/` populates DB with all nodes and edges
- DB persists across runs (second run loads from DB, does not reparse)
- `python -m db.store` can query a node and return its summary and neighbors
- ground_truth.json matches linter output for easy/medium tasks

---

## 🏗️ PHASE 2 — OpenEnv Core (RL Environment)
**Goal: Full step()/reset()/state() loop with reward. This is the RL part.**

### Tasks
1. Build `models.py` — all Pydantic models: Observation, Action (discriminated union), Reward, GraphState, EpisodeRecord. Must be fully typed.
2. Build `observation_builder.py` — given a module_id and current graph state, assemble the tiered observation: full code for current module, compressed summaries for neighbors (pulled from DB), existing review annotations for already-reviewed neighbors, constraint flags
3. Build `reward.py` — implement reward logic:
   - Easy: compare agent flags against linter ground truth. Correct flag = +0.5, false positive = -0.2, missed critical = -0.4
   - Medium: check flag + line number within ±3 lines of ground truth = +0.5, correct comment attribution = +0.3
   - Hard: call hard_grader with agent's FLAG_DEPENDENCY_ISSUE and the known root cause. Score returned by judge × 0.8 as reward.
   - REQUEST_CONTEXT action always costs -0.1 (thinking cost)
   - AMEND_REVIEW with correct attribution = +0.4 (high reward — this is the key cascading behavior)
   - Episode completion bonus: +0.2 if all critical issues found, -0.1 if APPROVE on module with known critical bugs
4. Build `graders/` — implement all three graders per spec above. Hard grader must use OpenAI client (per competition spec), temperature=0, fixed rubric prompt stored as a constant.
5. Build `environment.py` — main class implementing full OpenEnv interface:
   - `reset(task_id)` → clears annotations for task modules, returns first observation
   - `step(action)` → validates action, updates graph annotations in DB, computes reward, returns (obs, reward, done, info)
   - `state()` → returns full GraphState (serialized NetworkX graph + all annotations)
   - Episode ends when: agent calls APPROVE or REQUEST_CHANGES, OR step limit reached (max 10 steps)
6. Build `tasks/` — register 3 tasks pointing to specific modules in sample_codebase with known ground truth issues

### Completion Criteria
- `env.reset("easy_task")` returns a valid typed Observation
- `env.step(FLAG_BUG(line=12, description="null risk"))` returns reward > 0 for correct flag
- `env.state()` returns serializable graph with annotations
- Full episode runs without error on all 3 tasks
- Reward values all fall in 0.0–1.0 range

---

## 🏗️ PHASE 3 — HTTP Server & OpenEnv Spec Compliance
**Goal: Wrap environment in FastAPI, pass openenv validate.**

### Tasks
1. Build `server/app.py` — FastAPI app exposing:
   - POST /reset → calls env.reset(), returns Observation JSON
   - POST /step → calls env.step(action), returns (obs, reward, done, info) JSON
   - GET /state → calls env.state(), returns GraphState JSON
   - GET /health → returns 200 (required for HF Space ping)
2. Build `openenv.yaml` — fill all required metadata: name, version, description, tasks list, observation_space, action_space, reward_range
3. Run `openenv validate` — fix all compliance errors
4. Confirm all Pydantic models serialize/deserialize correctly over HTTP

### Completion Criteria
- `openenv validate` passes with no errors
- All endpoints return correct typed responses
- GET /health returns 200

---

## 🏗️ PHASE 4 — Inference Script
**Goal: Build inference.py that runs Gemma 4 as the agent. This is what judges auto-run.**

### Critical Requirements (Non-Negotiable)
- File must be named `inference.py` at root
- Use OpenAI client for all LLM calls
- Read API_BASE_URL, MODEL_NAME, HF_TOKEN from environment variables
- Emit structured stdout logs in EXACTLY this format:
```
[START] task=<task_id> episode=<n>
[STEP] step=<n> action=<action_type> reward=<float> cumulative=<float>
[END] task=<task_id> total_reward=<float> steps=<n>
```
- Must complete all 3 tasks in under 20 minutes total
- Must run on 2 vCPU / 8GB RAM

### Tasks
1. Build the agent loop — for each task: reset env, loop step() until done, collect rewards
2. Build the LLM action parser — send observation to model with a structured prompt, parse response into typed Action. Use JSON mode or structured output. Handle parse failures gracefully (default to APPROVE with penalty).
3. Build the action prompt — system prompt explaining the environment, action space, and output format. Include the compressed observation in user message. Tell model to output JSON action only.
4. Implement all 3 task runs sequentially
5. Emit all required log lines to stdout
6. Final output: baseline scores for all 3 tasks printed to stdout

### Completion Criteria
- Script runs end to end without error
- All [START]/[STEP]/[END] logs emitted correctly
- Produces a score for each task between 0.0–1.0
- Completes in under 20 minutes

---

## 🏗️ PHASE 5 — Containerization & Deployment
**Goal: Docker build works, HF Space deploys, pre-validation script passes.**

### Tasks
1. Write `Dockerfile`:
   - Base: python:3.11-slim
   - Install system deps for pylint, bandit, networkx
   - Copy project, install requirements
   - On container start: run parser to populate DB if not exists, then start FastAPI server
   - Expose port 7860 (HF Spaces default)
2. Write `README.md` with all required sections: environment description and motivation, observation and action space definitions, all 3 task descriptions with difficulty, setup instructions, baseline scores
3. Run pre-submission validation script — fix all failures
4. Deploy to HF Space with `openenv push`
5. Confirm Space URL returns 200 on GET /health and responds to POST /reset

### Completion Criteria
- `docker build .` succeeds
- `docker run -p 7860:7860` starts server cleanly
- HF Space URL responds to reset()
- Pre-validation script passes all checks

---

## ⏱️ Suggested Time Allocation (Given ~36hrs remaining)

| Phase | Time |
|---|---|
| Phase 1 — Foundation | 6 hrs |
| Phase 2 — RL Environment | 8 hrs |
| Phase 3 — Server + Spec | 3 hrs |
| Phase 4 — Inference Script | 4 hrs |
| Phase 5 — Docker + Deploy | 3 hrs |
| Buffer / debugging | 4 hrs |

---

## ⚠️ Known Risk Areas (Watch These)

1. **Hard grader reproducibility** — document judge prompt and seed explicitly
2. **DB migration on fresh Docker build** — first run must auto-populate DB from sample_codebase
3. **Inference script runtime** — test full 3-task run locally before submitting, must be under 20 min
4. **openenv validate strictness** — run it early in Phase 3, not at the end
5. **Reward always in 0.0–1.0** — clip all reward values, graders must never return outside range