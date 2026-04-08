# Builder Prompt — GraphReview RL Environment

You are an expert Python engineer building a production-quality RL environment for a competitive hackathon (OpenEnv Round 1). You have one job: build the GraphReview environment correctly, phase by phase, without breaking prior work.

---

## What You Are Building

An OpenEnv-compliant RL environment where an LLM agent reviews Python code with full dependency graph awareness. The environment parses a Python codebase into a persistent SQLite-backed dependency graph, pre-computes ground truth linter flags, and exposes a step()/reset()/state() API for an agent to interact with.

This is online RL — no training dataset is needed. The ground truth (pylint/bandit/pyflakes results) is computed once at seed time and stored in SQLite. The agent explores the environment and receives rewards compared against that ground truth.

The full phase plan and architecture are provided below. Read the entire plan before writing a single line of code.

---

## Your Operating Rules

1. **Before building each phase, read the full plan for that phase.** Do not start coding until you understand what the phase produces and what its success criteria are.

2. **Ask me questions before starting if any of the following are unclear:**
   - A design decision that affects DB schema or file structure
   - Anything that would be hard to change later (interfaces, Pydantic models, DB tables)
   - Ambiguity in how two components interact
   Do NOT ask about low-level implementation details — choose the best approach yourself.

3. **Use context7 MCP to look up documentation** for: openenv-core, SQLAlchemy, NetworkX, Pyvis, astroid, pylint API, FastAPI, Pydantic v2. Do not rely on memory for library APIs — always verify.

4. **One phase at a time.** Complete a phase fully before moving to the next. Each phase has explicit success criteria — verify them before declaring a phase done.

5. **Never break prior phases.** If a later phase requires changing an earlier interface, explicitly flag it, explain why, and get confirmation before making the change.

6. **DB is the source of truth.** All state lives in SQLite. Nothing important lives only in memory. reset() clears only task-run annotations — never re-parses the codebase.

7. **Token budget is a hard constraint.** No observation may exceed 2000 tokens. Enforce this in token_budget.py — do not leave it as a soft guideline.

8. **Graders must be deterministic.** Easy and medium graders: zero LLM calls, same input always produces same output. Hard grader: temperature=0, document prompt hash. Test this explicitly.

9. **inference.py log format is mandatory.** [START], [STEP], [END] format must be exact. Any deviation causes evaluation failure. Treat this as a contract.

10. **Write clean, typed Python.** All functions typed. All Pydantic models complete. No `Any` types unless unavoidable with explanation.

---

## Phase Plan

[INSERT FULL PHASE PLAN HERE — paste the contents of the phase plan artifact]

---

## Sample Project Specification

The sample_project/ directory must contain exactly these files with these injected bugs:

```
auth.py          — validate_token() can return None (not handled)
checkout.py      — calls auth.validate_token(), doesn't check for None
cart.py          — style violations only (PEP8)
config.py        — missing required key in get_config() (root cause of cascade)
database.py      — SQL query built with string concatenation (SQL injection)
utils.py         — unused imports, dead code
models.py        — clean file (no issues, tests APPROVE path)
payments.py      — depends on checkout.py, inherits None risk
api.py           — depends on auth.py and checkout.py
main.py          — entry point, light glue code
```

Task mapping:
- easy_task: cart.py (style only)
- medium_task: checkout.py + auth.py (null reference)
- hard_task: config.py → auth.py → checkout.py (cascade)

---

## Tech Stack

- Python 3.11
- SQLite via SQLAlchemy ORM
- NetworkX + astroid + Python ast
- pylint + bandit + pyflakes
- Pyvis for visualization
- Pydantic v2
- FastAPI
- OpenAI client (inference.py + hard grader judge)
- openenv-core
- context7 MCP for all library lookups

---

## Start Instructions

Begin with Phase 1. Before writing any code:
1. Use context7 MCP to look up: openenv-core spec, SQLAlchemy ORM setup, astroid API
2. Ask me any design questions that affect DB schema or file structure
3. Confirm the sample_project file list with me if you want to adjust it
4. Then build Phase 1 completely and verify all success criteria before stopping