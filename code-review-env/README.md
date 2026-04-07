# CodeReviewEnv

Dependency-aware code review RL environment with persistent SQLite graph storage.

## Current Status

- Phase 1: implemented and validated
  - persistent seed pipeline with hash-based cache
  - parser/chunker/graph builder + linter findings persistence
- Phase 2: implemented
  - graph manager for DB-backed graph loading and deterministic traversal
  - hard token budget enforcement (max 2000 tokens)
  - strict Pydantic v2 observation models
  - observation builder with neighbor summaries and REQUEST_CONTEXT support

## Implemented Phase 2 Components

- [graph/graph_manager.py](graph/graph_manager.py)
  - Loads graph nodes/edges from SQLite.
  - Exposes neighbor queries (in/out/both).
  - Provides deterministic traversal ordering with leaf-first preference.

- [graph/token_budget.py](graph/token_budget.py)
  - Enforces hard observation token cap (<= 2000).
  - Applies per-component token limits.
  - Truncates oversized components with explicit marker.

- [env/observation.py](env/observation.py)
  - Strict Pydantic models: `NeighborSummary`, `RequestedContext`, `CodeObservation`.
  - Forbids extra fields and type coercion.
  - Enforces `total_tokens <= 2000`.

- [env/observation_builder.py](env/observation_builder.py)
  - Builds observation payloads from DB graph state.
  - Ranks dependency context using graph centrality.
  - Produces validated `CodeObservation` objects.

## Compatibility

- [env/graph.py](env/graph.py) remains stable for existing callers and now delegates to GraphManager.

## Quickstart

```bash
pip install -r requirements.txt
python -m db.seed sample_project/
python -m db.store --module checkout
```

## Validation

Run tests:

```bash
pytest -q
```

Phase 2-focused tests:

```bash
pytest -q tests/test_phase2_graph_manager.py tests/test_phase2_token_budget.py tests/test_phase2_observation.py
```

## Security and Quality Notes

- SQLite is used as the source of truth for graph and review state.
- No dynamic code execution is introduced in Phase 2 paths.
- Input handling fails closed for unknown `module_id` values.
- Observations are hard-capped to prevent context overflow.
- Code follows typed interfaces and minimal stateful behavior.
