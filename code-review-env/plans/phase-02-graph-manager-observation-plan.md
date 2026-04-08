# Phase 2 Plan — Graph Manager & Observation Builder (for GPT-5.3)

## Objective
Deliver Phase 2 only:
- graph/graph_manager.py: load graph from SQLite, traversal order, neighbor queries
- graph/token_budget.py: hard 2000-token enforcement with per-component limits
- env/observation.py: strict Pydantic v2 CodeObservation model

No Phase 3+ implementation in this phase.

## Context7-Validated Constraints To Use
1. SQLAlchemy 2.0 + SQLite:
- Use SQLAlchemy ORM patterns with Declarative models and explicit Session boundaries.
- Keep read-heavy graph fetches in short-lived sessions.

2. NetworkX traversal and determinism:
- Use DAG topological utilities when possible.
- Use deterministic ordering (lexicographical tie-breaking) to avoid run-to-run drift.
- Betweenness centrality is available for ranking high-impact nodes.

3. Pydantic v2 model strictness:
- Use BaseModel with strict config and forbid unknown fields.
- Use model_validate/model_dump APIs consistently.

## Current Codebase Reality (important for Phase 2)
1. Existing graph logic is in env/graph.py, not graph/graph_manager.py.
2. env/observation_builder.py and env/models.py are placeholders.
3. DB layer currently uses SQLModel schema classes in db/schema.py.

Implication: Phase 2 should add the target files while preserving compatibility with existing imports/tests where possible.

## Proposed Phase 2 Deliverables

### 1) Create graph package and GraphManager
Files:
- code-review-env/graph/__init__.py
- code-review-env/graph/graph_manager.py

Planned API:
- class GraphManager:
  - __init__(self, source_root: str, db_path: str | None = None)
  - load_graph(self) -> nx.DiGraph
  - get_node(self, module_id: str) -> dict[str, object]
  - get_neighbors(self, module_id: str, direction: Literal["out", "in", "both"], limit: int | None = None) -> list[str]
  - traversal_order(self) -> list[str]
  - centrality(self) -> dict[str, float]

Implementation rules:
- Load modules/edges from SQLite as source of truth.
- Add all module metadata needed for observations as node attributes.
- traversal_order target behavior:
  - Prefer leaf-first review order.
  - Push high-centrality nodes later.
  - Deterministic tie-breaker by module_id.
- Recommended approach:
  - Reverse-edge DAG ordering for leaf-first when acyclic.
  - If cyclic, condense SCCs or apply stable fallback ordering by:
    1) out_degree ascending
    2) betweenness centrality ascending
    3) module_id ascending

Compatibility note:
- Keep env/graph.py as a thin wrapper or adapter to GraphManager until all callers migrate.

### 2) Implement hard token budget module
File:
- code-review-env/graph/token_budget.py

Constants:
- MAX_TOTAL_TOKENS = 2000
- COMPONENT_BUDGETS (initial defaults from plan):
  - current_code: 800
  - ast_summary: 100
  - direct_deps: 250
  - dependents: 150
  - neighbor_reviews: 120
  - task_and_actions: 200
  - buffer: 280

Planned API:
- estimate_tokens(text: str) -> int
- truncate_to_budget(text: str, max_tokens: int, suffix_notice: str) -> str
- allocate_budget(components: dict[str, str | list[str]]) -> dict[str, object]
  - returns included/truncated text + per-component token usage + total
- enforce_observation_budget(observation_payload: dict[str, object]) -> dict[str, object]

Implementation rules:
- Budget must be enforced, never advisory.
- If full payload exceeds 2000, trim in priority order:
  1) dependent summaries
  2) neighbor reviews
  3) direct dependency summaries (lowest-ranked first)
  4) current code (but preserve critical context header + truncation notice)
- REQUEST_CONTEXT path must still obey MAX_TOTAL_TOKENS and return full neighbor code only when it fits; otherwise return bounded code + explicit truncation marker.

Token estimator policy:
- Start with deterministic approximation for stability (for example chars/4 heuristic).
- Keep estimator in one function to allow later swap to model-specific tokenizer without API break.

### 3) Implement strict Pydantic observation model
File:
- code-review-env/env/observation.py

Planned models:
- class NeighborSummary(BaseModel)
  - module_id: str
  - relation: Literal["dependency", "dependent"]
  - summary: str
  - review_snippet: str | None

- class RequestedContext(BaseModel)
  - module_id: str
  - code: str
  - was_truncated: bool

- class CodeObservation(BaseModel)
  - module_id: str
  - code: str
  - ast_summary: dict[str, object]
  - dependency_summaries: list[NeighborSummary]
  - dependent_summaries: list[NeighborSummary]
  - neighbor_reviews: list[str]
  - task_description: str
  - available_actions: list[str]
  - requested_context: RequestedContext | None = None
  - token_usage: dict[str, int]
  - total_tokens: int
  - within_budget: bool

Model config:
- strict=True
- extra="forbid"

Validation rules:
- total_tokens <= 2000 must be true.
- module_id and code cannot be empty.
- dependency/dependent list limits enforced before serialization.

### 4) Observation assembly integration path
File to update in Phase 2:
- code-review-env/env/observation_builder.py

Plan:
- Replace placeholder with builder that composes:
  - GraphManager neighbor and ordering queries
  - DB-backed module source + summaries + review annotations
  - TokenBudget allocation and enforcement
  - CodeObservation validation

Behavior:
- Default observation returns current module + compressed neighbors.
- REQUEST_CONTEXT(module_id): include requested neighbor code in requested_context while still meeting global budget.

## Verification Plan (must pass before Phase 2 complete)

### A) Unit tests to add/update
1. tests/test_graph_manager_phase2.py
- load_graph builds expected node/edge counts from seeded DB.
- traversal_order places leaf nodes earlier than high-centrality hubs.
- ordering is deterministic across repeated calls.

2. tests/test_token_budget_phase2.py
- enforce_observation_budget always returns total_tokens <= 2000.
- long current code is truncated with explicit notice.
- REQUEST_CONTEXT path stays within 2000.

3. tests/test_observation_phase2.py
- CodeObservation strict validation rejects unknown fields/type coercion.
- valid payload serializes with model_dump and preserves token fields.

### B) Scenario checks
1. Seed sample_project SQLite DB.
2. Build observation for every module_id in modules table.
3. Assert all observations are within budget.
4. Trigger REQUEST_CONTEXT for high-fanout node and validate bounded response.

### C) Determinism checks
1. Run traversal_order 10 times on same DB snapshot.
2. Output order must be identical each run.

## Risks and Mitigations
1. Existing env/graph.py may conflict with new graph/graph_manager.py.
- Mitigation: keep wrapper compatibility until callers migrate.

2. SQLModel vs SQLAlchemy ORM naming mismatch in current schema.
- Mitigation: Phase 2 consumes existing schema as-is; DB table redesign deferred unless explicitly approved.

3. Token estimation mismatch vs actual model tokenizer.
- Mitigation: enforce conservative budget with safety buffer; keep estimator swappable.

## Design Questions To Resolve Before Implementation
1. File structure decision:
- Should Phase 2 introduce new graph/ package now and keep env/graph.py compatibility wrapper, or refactor callers immediately?

2. Schema alignment decision:
- Keep current SQLModel-backed tables in Phase 2 and map to planned names later, or perform a schema migration now?

3. REQUEST_CONTEXT strictness:
- If full neighbor code cannot fit, should response be truncated (with marker) or should the action fail with explicit error and no code body?

## Definition of Done for Phase 2
1. graph/graph_manager.py, graph/token_budget.py, env/observation.py implemented with type hints and docstrings.
2. observation_builder builds validated CodeObservation objects.
3. All Phase 2 tests pass.
4. Every generated observation satisfies hard <= 2000 token limit.
5. Traversal order behavior matches leaf-first and high-centrality-last intent with deterministic ties.