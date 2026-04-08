# GraphReview RL Environment — Complete Phased Build Plan v2

---

## What You Are Building

An OpenEnv-compliant RL environment where an LLM agent learns to review Python code with full dependency graph awareness. The environment:

1. Parses a Python codebase into a **persistent dependency graph** stored in SQLite
2. Splits large files (>300 lines) into sub-nodes by class/function to keep observations manageable
3. Pre-computes ground truth linter flags (pylint + bandit + pyflakes) per node at seed time
4. Presents the agent with one module at a time + compressed AST summaries of neighbors
5. Receives structured actions (FLAG_BUG, ADD_COMMENT, REQUEST_CONTEXT, etc.)
6. Scores actions against pre-computed ground truth — no training data needed, ground truth IS the data
7. Accumulates review annotations back onto graph nodes in SQLite
8. Outputs an annotated dependency graph visualized via Pyvis (interactive HTML) + markdown report

**The RL loop:** Agent takes multi-step actions per module episode, receives per-step rewards, learns to reason about cascading dependency issues. This is online RL — the environment generates interaction data live. No pre-existing dataset required.

**The key differentiator vs CodeRabbit:** Agent sees WHY a decision was made (upstream context) before flagging it. Reviews are stored back into the graph. Agent can AMEND earlier reviews as it learns more about root causes downstream.

---

## Why No Training Data Is Needed

This is online RL, not offline supervised learning:
- Ground truth = pylint/bandit/pyflakes results, computed once at seed time, stored in DB
- Agent explores environment → receives rewards → that interaction IS the training signal
- For Round 1, the baseline inference script evaluates a pre-trained LLM (Gemma 4 E4B) acting as agent
- You are not training a model — you are building the environment that COULD train one
- The three graders define what "correct behavior" looks like — that is your data

---

## Tech Stack (Fixed)

- Python 3.11
- OpenEnv: step() / reset() / state() + Pydantic typed models + openenv.yaml
- SQLite via SQLAlchemy ORM (persistent, file-based, ships in Docker)
- NetworkX for graph operations and traversal
- Python built-in `ast` module for structure extraction
- `astroid` for scope-aware name resolution and intra-file conflict detection
- pylint + bandit + pyflakes for ground truth generation (run once at seed time)
- Pyvis for interactive graph visualization
- OpenAI client (inference.py + hard task LLM judge)
- Gemma 4 E4B as baseline agent model
- FastAPI for HTTP server (required for HF Spaces)
- Docker + Hugging Face Spaces
- context7 MCP for library documentation during build

---

## File Structure

```
graphreview/
├── sample_project/          # synthetic input codebase with injected bugs
│   ├── auth.py
│   ├── checkout.py
│   ├── cart.py
│   ├── database.py
│   └── ...
├── parser/
│   ├── ast_parser.py        # extract signatures, imports, classes per file
│   ├── chunker.py           # split files >300 lines into sub-nodes
│   ├── graph_builder.py     # build NetworkX DiGraph from parsed output
│   └── summarizer.py        # compress each node to ~50 token summary
├── db/
│   ├── database.py          # SQLAlchemy engine, session factory
│   ├── models.py            # ORM models for all tables
│   └── seed.py              # parse once → store → skip if seeded
├── graph/
│   ├── graph_manager.py     # load graph from DB, traversal, neighbor queries
│   └── token_budget.py      # enforce token limits on observations
├── env/
│   ├── environment.py       # CodeReviewEnv main class
│   ├── observation.py       # Pydantic: CodeObservation
│   ├── action.py            # Pydantic: ReviewAction
│   ├── reward.py            # Pydantic: ReviewReward + reward table
│   └── state.py             # Pydantic: GraphState
├── graders/
│   ├── base_grader.py       # abstract interface
│   ├── easy_grader.py       # linter match (deterministic)
│   ├── medium_grader.py     # AST + line attribution (deterministic)
│   └── hard_grader.py       # graph consistency + LLM judge (temperature=0)
├── tasks/
│   ├── task_registry.py     # register 3 tasks
│   ├── easy_task.py         # style/linter review
│   ├── medium_task.py       # logic bug + direct dep context
│   └── hard_task.py         # cascading bug across 2+ module hops
├── visualizer/
│   ├── pyvis_renderer.py    # NetworkX → interactive HTML graph
│   └── report_generator.py  # markdown + JSON final report
├── server.py                # FastAPI wrapper for OpenEnv HTTP spec
├── inference.py             # baseline agent script (mandatory, root level)
├── openenv.yaml             # spec metadata
├── Dockerfile
└── README.md
```

---

## Database Schema (SQLite — Persistent)

**modules**
```
id                TEXT PK      (relative file path, or "file.py::ClassName" for sub-nodes)
name              TEXT
code              TEXT         (full source — full file or chunked section)
ast_summary       JSON         (signatures, classes, return types, decorators)
linter_flags      JSON         (pre-computed pylint+bandit+pyflakes — GROUND TRUTH)
summary           TEXT         (~50 token natural language description)
parent_module_id  TEXT NULL    (set if this is a sub-node chunk of a larger file)
review_status     TEXT         (pending | in_progress | reviewed)
is_chunk          BOOLEAN
```

**edges**
```
source_id         TEXT FK → modules.id
target_id         TEXT FK → modules.id
edge_type         TEXT         (explicit_import | implicit_dependency | intra_file)
import_line       TEXT
dependency_reason TEXT
scope             TEXT         (module_level | function_level)
weight            FLOAT        (1.0 explicit, 0.5 implicit)
```

**review_annotations**
```
id                INTEGER PK AUTOINCREMENT
module_id         TEXT FK → modules.id
task_id           TEXT
action_type       TEXT
content           TEXT
reward_given      FLOAT
attributed_to     TEXT NULL    (module_id for cascade attribution)
is_amendment      BOOLEAN      (true if this amends a prior review)
created_at        TIMESTAMP
```

**task_runs**
```
id                INTEGER PK AUTOINCREMENT
task_id           TEXT
started_at        TIMESTAMP
completed_at      TIMESTAMP NULL
total_reward      FLOAT
total_steps       INTEGER
status            TEXT         (running | complete | failed)
```

**seed_meta**
```
key               TEXT PK
value             TEXT
```
(stores seeded=true flag, seed timestamp, codebase hash)

---

## Chunking Strategy for Large Files

```
File ≤ 300 lines  → one node, id = "filename.py"

File > 300 lines  → chunk by top-level class or function
  Each chunk becomes a sub-node:
  id = "filename.py::ClassName" or "filename.py::function_name"
  parent_module_id = "filename.py"
  
  A virtual parent node is kept for the file itself
  with no code but with all inter-file edges
  
  Intra-file edges added between chunks:
  if function_a calls function_b in same file →
  edge(filename.py::function_a → filename.py::function_b, type=intra_file)

Dependency conflict detection (via astroid):
  If import is used only inside one function → scope=function_level, weight=0.5
  If import used at module level → scope=module_level, weight=1.0
  Circular imports → flagged as edge with type=circular, added to linter_flags
```

---

## Observation Token Budget

```
Current module full code:        ~800 tokens  (hard cap, truncate with notice)
AST summary of current:          ~100 tokens
Direct dependency summaries:     ~50 tokens × up to 5 deps = 250 tokens
Dependent summaries:             ~50 tokens × up to 3 = 150 tokens
Existing neighbor reviews:       ~30 tokens × up to 4 = 120 tokens
Task description + action space: ~200 tokens
Buffer:                          ~280 tokens
─────────────────────────────────────────────
Total:                           ~1900 tokens (well within E4B 128K window)
```

If a module has >5 direct dependencies, rank by betweenness centrality and include top 5 only.

---

## Action Space

```python
action_type options:
  FLAG_STYLE              # style/formatting issue
  FLAG_BUG                # logic error
  FLAG_SECURITY           # security vulnerability
  FLAG_DEPENDENCY_ISSUE   # issue caused by upstream module
  ADD_COMMENT             # explanation (requires content field)
  REQUEST_CONTEXT         # fetch full code of a neighbor (-0.1 reward cost)
  REQUEST_CHANGES         # end episode, verdict = changes needed
  APPROVE                 # end episode, verdict = approved
  AMEND_REVIEW            # update a prior annotation on a neighbor node

Fields:
  action_type:     required
  target_line:     optional int
  content:         required for ADD_COMMENT, AMEND_REVIEW
  attributed_to:   optional module_id (for FLAG_DEPENDENCY_ISSUE, AMEND_REVIEW)
  context_request: required for REQUEST_CONTEXT (module_id to fetch)
```

---

## Reward Table

```
Correct FLAG_* matching linter ground truth:          +0.5
Accurate ADD_COMMENT (keyword match to linter desc):  +0.3
FLAG_DEPENDENCY_ISSUE with correct attribution:       +0.6
FLAG_DEPENDENCY_ISSUE wrong attribution:              +0.1
AMEND_REVIEW correctly updating prior annotation:     +0.4
REQUEST_CONTEXT (investigation cost):                 -0.1
False positive flag (no linter match):                -0.2
APPROVE on module with unflagged critical issues:     -1.0
REQUEST_CHANGES on clean module:                      -0.3
Episode completion bonus (all issues caught):         +0.2
```

---

## Grader Architecture

### Easy Grader (fully deterministic)
- Load linter_flags JSON from DB for current module
- For each agent FLAG_* action: check if a matching linter flag exists (type + line ±3)
- Score per action, aggregate for episode
- No LLM call. Zero variance.

### Medium Grader (fully deterministic)
- Easy grader logic PLUS:
- For ADD_COMMENT: extract keywords from linter flag description, check overlap with agent comment (Jaccard similarity > 0.3 = match)
- For line attribution: ±3 line tolerance
- Still no LLM call.

### Hard Grader (quasi-deterministic)
- Graph consistency check (deterministic):
  If FLAG_DEPENDENCY_ISSUE with attributed_to=X: verify edge(current → X) or edge(X → current) exists in graph
  If no edge: reward = 0.0, feedback = "no dependency relationship found"
- LLM-as-judge (temperature=0, fixed rubric):
  Separate API call to judge model (NOT the agent)
  Fixed system prompt with scoring rubric
  Scores cascade reasoning quality: 0.0 | 0.5 | 1.0
  Document prompt hash in README for reproducibility

---

## Three Tasks

### Task 1: style_review (Easy)
- Input: single module with 3 pylint style violations
- Agent must: flag all 3 style issues
- No dependency context needed
- Grader: easy_grader only
- Expected baseline score: 0.7–0.9

### Task 2: logic_review (Medium)  
- Input: checkout.py with a null-reference bug
- auth.py (its dependency) has validate_token that can return None
- Agent must: flag the bug + add comment referencing the None return risk
- Grader: medium_grader
- Expected baseline score: 0.4–0.7

### Task 3: cascade_review (Hard)
- Input: 3-module chain: config.py → auth.py → checkout.py
- Bug originates in config.py (missing key), propagates through auth.py, surfaces in checkout.py
- Agent must: flag issue in checkout.py AND attribute root cause to config.py
- Grader: hard_grader (graph consistency + LLM judge)
- Expected baseline score: 0.2–0.5

---

## Visualization

### Pyvis Interactive Graph (primary)
- Nodes colored by review_status: grey=pending, yellow=in_progress, green=approved, red=changes_requested
- Node size = number of dependents (centrality)
- Edge color: blue=explicit_import, orange=implicit, red=circular
- Edge thickness = weight (1.0 explicit, 0.5 implicit)
- Click node → shows review_annotations panel
- Rendered as standalone HTML, embedded in HF Space

### Final Report Output (end of all episodes)
- `graphreview_report.md`: per-module sections with verdict + issues + cascade attributions
- `graphreview_report.json`: machine-readable full graph + annotations
- `graphreview_graph.html`: pyvis interactive visualization

---

## inference.py Log Format (Mandatory)

```
[START] task=cascade_review module_count=3
[STEP] module=checkout.py action=FLAG_BUG line=24 reward=0.5 cumulative=0.5
[STEP] module=checkout.py action=ADD_COMMENT content="null risk from auth" reward=0.3 cumulative=0.8
[STEP] module=checkout.py action=FLAG_DEPENDENCY_ISSUE attributed_to=auth.py reward=0.6 cumulative=1.4
[STEP] module=checkout.py action=REQUEST_CHANGES reward=0.2 cumulative=1.6 done=true
[STEP] module=auth.py action=FLAG_BUG line=15 reward=0.5 cumulative=2.1
[STEP] module=auth.py action=FLAG_DEPENDENCY_ISSUE attributed_to=config.py reward=0.6 cumulative=2.7
[STEP] module=auth.py action=REQUEST_CHANGES reward=0.2 cumulative=2.9 done=true
[STEP] module=config.py action=FLAG_BUG line=8 reward=0.5 cumulative=3.4
[STEP] module=config.py action=REQUEST_CHANGES reward=0.2 cumulative=3.6 done=true
[END] task=cascade_review total_reward=3.6 modules_reviewed=3 report=graphreview_report.md
```

---

## Phase 1 — Persistence Layer & Sample Project
**Goal: Parse once, store forever, never re-parse**

Build:
- `sample_project/` — 10 Python files, ~50 functions total, with injected known bugs for each task
- `db/models.py` — all SQLAlchemy ORM models
- `db/database.py` — engine setup, session factory, init_db()
- `db/seed.py` — orchestrate full parse → lint → store pipeline
- `parser/ast_parser.py` — extract structure per file using Python ast
- `parser/chunker.py` — split files >300 lines by class/function into sub-nodes
- `parser/graph_builder.py` — build NetworkX DiGraph, explicit + implicit edges
- `parser/summarizer.py` — ~50 token summaries per node

Success criteria:
- seed.py completes in <30s on sample_project
- Second run detects seeded flag, loads in <1s
- All modules, edges, linter_flags correctly stored
- Chunking correctly splits a 400-line test file into sub-nodes

---

## Phase 2 — Graph Manager & Observation Builder
**Goal: Efficient, token-budgeted observations from DB**

Build:
- `graph/graph_manager.py` — load graph, traversal order, neighbor queries
- `graph/token_budget.py` — enforce per-component token limits
- `env/observation.py` — Pydantic CodeObservation model

Success criteria:
- Observation for any node fits within 2000 token budget
- Traversal order: leaf nodes first, high-centrality nodes last
- REQUEST_CONTEXT returns full neighbor code within budget

---

## Phase 3 — Action Space, Reward Engine & Graders
**Goal: All actions scored correctly and deterministically**

Build:
- `env/action.py` — Pydantic ReviewAction
- `env/reward.py` — Pydantic ReviewReward + reward table logic
- `graders/base_grader.py` — abstract interface
- `graders/easy_grader.py` — linter match
- `graders/medium_grader.py` — linter + keyword + line attribution
- `graders/hard_grader.py` — graph consistency + LLM judge

Success criteria:
- Easy grader: same input always gives same output (verified with 10 runs)
- Hard grader: temperature=0 verified, prompt hash documented
- All reward values within 0.0–1.0 range
- False positive and false negative cases handled explicitly

---

## Phase 4 — OpenEnv Core
**Goal: Fully compliant step() / reset() / state()**

Build:
- `env/environment.py` — CodeReviewEnv main class
- `env/state.py` — GraphState Pydantic model
- `tasks/task_registry.py` + 3 task files
- `openenv.yaml`
- `server.py` — FastAPI HTTP wrapper

Success criteria:
- `openenv validate` passes
- All 3 tasks run end-to-end without error
- state() correctly returns full annotated graph
- reset() clears only current task annotations, not full DB

---

## Phase 5 — Visualization & Reporting
**Goal: Useful output the user actually sees**

Build:
- `visualizer/pyvis_renderer.py` — interactive HTML graph
- `visualizer/report_generator.py` — markdown + JSON report

Success criteria:
- Graph colors update correctly as reviews accumulate
- Report correctly attributes cascade issues across modules
- HTML renders in browser without external dependencies

---

## Phase 6 — inference.py & Deployment
**Goal: Baseline script + Docker + HF Space**

Build:
- `inference.py` — runs Gemma 4 E4B against all 3 tasks, emits mandatory log format
- `Dockerfile` — clean build + run
- `README.md` — full documentation
- HF Space deployment

Success criteria:
- inference.py completes all 3 tasks in <20 minutes
- Runs on 2 vCPU / 8GB RAM
- docker build && docker run works cleanly
- HF Space deploys and responds to reset() ping
- Baseline scores reproducible across 3 runs