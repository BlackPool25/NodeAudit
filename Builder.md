# Builder Prompt — CodeReviewEnv

You are an expert Python engineer building a reinforcement learning environment called **CodeReviewEnv** for the OpenEnv Hackathon Round 1. Read everything below before writing a single line of code.

---

## What You Are Building

An OpenEnv-compliant RL environment where an LLM agent learns to perform dependency-aware code review on a Python codebase.

The environment:
1. Parses a Python codebase into a **persistent dependency graph** stored in SQLite via SQLModel. Nodes = modules. Edges = import relationships.
2. Each node stores: full source code, compressed AST summary (~50 tokens), linter ground truth (pylint + bandit output), and agent-written review annotations.
3. The agent reviews one module per episode via a multi-step loop: `reset()` → `step(action)` × N → done.
4. The agent sees **full code of the current module only**. Neighbors are always compressed summaries — never full code. This is a hard constraint for token budget.
5. The agent can take actions: FLAG_BUG, FLAG_STYLE, FLAG_SECURITY, FLAG_DEPENDENCY_ISSUE, ADD_COMMENT, REQUEST_CHANGES, APPROVE, REQUEST_CONTEXT (costs -0.1 reward), AMEND_REVIEW (updates a neighbor's annotation retroactively).
6. Rewards are computed by graders against pre-computed ground truth stored in the DB.
7. The final output is an annotated dependency graph — all module reviews, cross-module causal attributions, readable as JSON and Markdown.

The key differentiator: the environment models **cascading bugs** — where a bug in module B is caused by a design decision in module A. The agent is rewarded for identifying the upstream root cause, not just flagging the surface symptom.

---

## Persistence Strategy

**SQLite + SQLModel. This is non-negotiable for demo performance.**

- On first run: parse sample_codebase/ → populate DB with all nodes, edges, linter flags
- On subsequent runs: detect DB exists → skip parsing → load graph directly
- `reset()` clears only review annotations, never graph structure
- All episode history is stored for reproducibility

Use Context7 MCP to look up SQLModel, NetworkX, pylint programmatic API, bandit API, and OpenEnv spec documentation before implementing each component. Do not guess at APIs — look them up.

---

## Tech Stack

- Python 3.11
- SQLModel (SQLite persistence)
- NetworkX (graph construction and traversal)
- FastAPI (HTTP server for OpenEnv spec)
- Pydantic v2 (typed models)
- pylint + bandit (linter ground truth)
- Python `ast` module (AST parsing — stdlib, no extras)
- OpenAI client (all LLM calls in inference.py and hard grader)
- Docker (containerization)

---

## Project Structure

Follow this structure exactly — do not deviate:

```
code-review-env/
├── openenv.yaml
├── Dockerfile
├── README.md
├── inference.py
├── requirements.txt
├── env/
│   ├── environment.py
│   ├── models.py
│   ├── graph.py
│   ├── observation_builder.py
│   └── reward.py
├── db/
│   ├── schema.py
│   ├── store.py
│   └── migrations.py
├── parser/
│   ├── ast_parser.py
│   ├── linter.py
│   └── summarizer.py
├── graders/
│   ├── base_grader.py
│   ├── easy_grader.py
│   ├── medium_grader.py
│   └── hard_grader.py
├── tasks/
│   ├── task_registry.py
│   ├── easy_task.py
│   ├── medium_task.py
│   └── hard_task.py
├── server/
│   └── app.py
├── sample_codebase/
│   ├── auth.py
│   ├── checkout.py
│   ├── cart.py
│   ├── payments.py
│   ├── config.py
│   └── ground_truth.json
└── tests/
```

---

## Phase You Are Currently Building

**[INSERT PHASE NUMBER AND NAME HERE]**

Refer to the phase plan for exact tasks and completion criteria for this phase. Build only what is scoped to this phase. Do not build ahead.

---

## Non-Negotiable Constraints

1. All rewards must be clipped to 0.0–1.0. Never return outside this range.
2. Never feed full neighbor code into observations. Always use compressed summaries.
3. inference.py must use OpenAI client. Read API_BASE_URL, MODEL_NAME, HF_TOKEN from env vars.
4. inference.py must emit [START], [STEP], [END] log format exactly — no deviations.
5. Hard grader must use temperature=0 and a fixed rubric prompt stored as a constant.
6. DB must auto-populate on first Docker run without manual intervention.
7. All Pydantic models must be fully typed — no `Any`, no `dict` without a model.
8. Episode step limit is 10. Hard cap. Enforce in environment.py.

---

## Before You Start Each File

1. Use Context7 MCP to look up the relevant library documentation
2. Check if the schema/interface you are about to implement has dependencies on already-built files — import them, don't reimplement
3. If you need to make a design choice not covered in this prompt (e.g. exact DB column types, traversal tie-breaking, summary format), **ask the user before proceeding**
4. Write tests alongside implementation — not after

---

## Questions To Ask The User Before Starting

If any of the following are unclear, ask before building:

- What Python codebase should be used as the demo target? (default: the sample_codebase/ provided)
- Should the hard grader use the same MODEL_NAME from env vars, or a fixed model?
- Should REQUEST_CONTEXT return the full raw code or the full AST + raw code?
- Should AMEND_REVIEW require the agent to specify what was wrong with the original review?
- What is the maximum number of neighbors to include in an observation? (recommend: 5, confirm)