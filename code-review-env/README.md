# GraphReview — Dependency-Aware RL Environment for Python Code Review

GraphReview is an OpenEnv-compliant reinforcement learning environment where an LLM
agent learns to review Python code with full dependency graph awareness.

## What it does

- Parses a Python codebase into a persistent SQLite-backed dependency graph
- Pre-computes ground truth linter findings (pylint + bandit) at seed time
- Presents an agent with one module at a time, with compressed AST summaries of neighbors
- Scores agent actions against real ground truth — no training data needed
- Accumulates review annotations back onto graph nodes

## Architecture

````
Codebase (.py files)
      │
      ▼
  db/seed.py ──► SQLite DB (modules, edges, linter_flags)
      │
      ▼
  env/environment.py
  ┌───────────────────────────────────┐
  │  reset() → CodeObservation        │
  │  step(ReviewAction) → reward      │
  │  state() → GraphState             │
  └───────────────────────────────────┘
      │
      ▼
  graders/
  ├── easy_grader.py   (linter match — deterministic)
  ├── medium_grader.py (AST + keyword match — deterministic)
  └── hard_grader.py   (graph consistency + LLM judge — temperature=0)
      │
      ▼
  inference.py (baseline agent — OpenAI-compatible client)
````

## Tasks

| Task | Difficulty | Description |
|------|-----------|-------------|
| style_review | Easy | Flag style/linting violations in a single module |
| logic_review | Medium | Identify null-reference logic bug with dependency context |
| cascade_review | Hard | Trace a bug from root cause across 3 modules |

## Quickstart

```bash
# Install dependencies
pip install -r requirements.txt

# Seed the database (parse codebase, run linters, store graph)
python -m db.seed sample_project/

# Start the API server
uvicorn server.app:app --host 0.0.0.0 --port 8000

# Run the baseline inference agent
python inference.py sample_project
```

## Environment Variables

```bash
# LLM provider (any OpenAI-compatible endpoint)
API_BASE_URL=http://localhost:11434/v1   # Ollama default; use https://api.openai.com/v1 for OpenAI
MODEL_NAME=hf.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF:latest
HF_TOKEN=your_token_here                 # HuggingFace token / API key

# Optional
GRAPHREVIEW_OUTPUT_DIR=outputs
GRAPHREVIEW_SEMGREP_ENABLED=false
RL_MAX_STEPS=20
RL_TASK_TIMEOUT=300
```

## Supported LLM Providers

GraphReview works with any OpenAI-compatible endpoint:

| Provider | API_BASE_URL | MODEL_NAME example |
|----------|-------------|-------------------|
| Ollama (local) | http://localhost:11434/v1 | hf.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF:latest |
| OpenAI | https://api.openai.com/v1 | gpt-4o-mini |
| Custom | your endpoint | your model |

## Action Space

| Action | Description | Reward |
|--------|-------------|--------|
| FLAG_STYLE | Style/formatting issue | +0.5 if matches linter |
| FLAG_BUG | Logic error | +0.5 if matches linter |
| FLAG_SECURITY | Security vulnerability | +0.5 if matches linter |
| FLAG_DEPENDENCY_ISSUE | Upstream cause, with attribution | +0.6 if edge verified |
| ADD_COMMENT | Explanatory comment | +0.3 if keyword match |
| REQUEST_CONTEXT | Fetch neighbor code | -0.1 (investigation cost) |
| REQUEST_CHANGES | End review — changes needed | +0.2 if issues found |
| APPROVE | End review — approved | -1.0 if issues missed |

## Baseline Scores (sample_project)

| Task | Score | Notes |
|------|-------|-------|
| style_review | ~0.80 | Deterministic — pylint flags |
| logic_review | ~0.55 | Requires null-ref reasoning |
| cascade_review | ~0.40 | Requires 3-hop attribution |

## API Endpoints

````
POST /reset          Start new episode
POST /step           Take one action
GET  /state          Current graph state
GET  /tasks          List available tasks
GET  /health         Health check
POST /reports/generate  Generate HTML/JSON/MD report
````

## OpenEnv Compliance

- Typed Pydantic models: ReviewAction, CodeObservation, GraphState
- Full step() / reset() / state() interface
- openenv.yaml metadata
- Baseline inference script: inference.py
- Docker deployment ready
