# Phase 03 Plan - Action Space, Reward Engine, and Deterministic Graders (for GPT-5.3)

## 1) Phase Objective
Deliver Phase 03 only, with no Phase 04+ behavior:
- Build typed action/reward models.
- Build deterministic easy/medium graders.
- Build hard grader with deterministic graph checks and temperature=0 LLM judge.
- Keep SQLite as source of truth for review outcomes and annotations.

## 2) Current Repository Reality
- `env/action.py` does not exist yet.
- `env/reward.py` and all `graders/*.py` are placeholders.
- DB uses SQLModel tables in `db/schema.py` with existing entities:
  - `ModuleNode`, `ModuleEdge`, `LinterFinding`, `ReviewAnnotation`, `EpisodeRecord`, `TaskDefinition`, `SeedMeta`.
- `db/store.py` already persists annotations and linter findings.

Implication:
Phase 03 should implement new files and logic without breaking existing schema or seed flow.

## 3) Context7-Validated API Decisions
Based on latest Context7 docs:
- SQLAlchemy/SQLModel session lifecycle:
  - Use short-lived explicit session scopes.
  - Keep deterministic writes and explicit commits.
- Pydantic v2 strictness:
  - Use `ConfigDict(strict=True, extra="forbid")` for all action/reward/judge payload models.
  - Prefer `model_validate` and `model_dump` for boundaries.
- OpenAI Python client compatibility:
  - Use env-driven `base_url` and `api_key` so current Ollama and future hosted endpoints are switchable.

## 4) Design Principles
- Occam's razor: implement only behavior required by Phase 03 criteria.
- Determinism first: same input graph + same action sequence => same easy/medium score.
- DB-first persistence: grading side effects and review annotations are persisted to SQLite.
- Clear contracts: action validation, reward reason codes, and grader outputs are typed.

## 5) Required Files and Responsibilities
1. `env/action.py`
- Define `ActionType` enum:
  - `FLAG_STYLE`, `FLAG_BUG`, `FLAG_SECURITY`, `FLAG_DEPENDENCY_ISSUE`,
    `ADD_COMMENT`, `REQUEST_CONTEXT`, `REQUEST_CHANGES`, `APPROVE`, `AMEND_REVIEW`.
- Define strict `ReviewAction` Pydantic model:
  - required: `action_type`
  - optional: `target_line`, `attributed_to`
  - conditional required fields:
    - `content` required for `ADD_COMMENT`, `AMEND_REVIEW`
    - `context_request` required for `REQUEST_CONTEXT`
- Add model validators to enforce conditional requirements and reject invalid combinations.

2. `env/reward.py`
- Define strict reward artifacts:
  - `RewardReason` enum
  - `ReviewReward` model: `value`, `reason`, `feedback`, `matched_flag_id`, metadata.
- Implement reward table as constants and a single deterministic reward function.
- Clamp and validate single-step reward into [0.0, 1.0] only where contract requires bounded rewards.
  - If penalties must be negative for task-level economics, store raw reward and also provide normalized score field for strict [0.0, 1.0] reporting.

3. `graders/base_grader.py`
- Define abstract grader interface:
  - `grade_action(...) -> ReviewReward`
  - `grade_episode(...) -> EpisodeGradeSummary`
- Add typed input envelope (module context, action, graph context, prior annotations).

4. `graders/easy_grader.py`
- Deterministic linter matching only:
  - Match action category to linter finding category.
  - Line tolerance: +-3.
  - Explicit false-positive and miss handling.
- No LLM calls.

5. `graders/medium_grader.py`
- Easy logic plus deterministic comment quality scoring:
  - Keyword overlap/Jaccard threshold (fixed, documented).
  - Same line tolerance rule.
- No LLM calls.

6. `graders/hard_grader.py`
- Step 1 deterministic graph consistency check:
  - For `FLAG_DEPENDENCY_ISSUE`, verify dependency path exists (direct edge minimum, optional path depth <= 2 if configured).
- Step 2 judge call for cascade reasoning quality:
  - temperature=0, fixed rubric, fixed output schema.
  - model default: `gemma4:e4b`.
  - provider path: OpenAI-compatible client, env-switchable base URL.
- Persist judge request metadata minimally (prompt hash, model id, provider) for reproducibility.

## 6) Environment Variable Contract (Important)
Add a single source config module (Phase 03 can define and consume; no full env integration yet):

Database:
- `GRAPHREVIEW_DATABASE_URL`
  - default local: `sqlite:///./code_review_env.db`
  - optional remote SQLite-compatible URL for future deployments.
- `GRAPHREVIEW_DB_ECHO` (default `false`)

Judge model/provider:
- `GRAPHREVIEW_JUDGE_PROVIDER` values: `ollama_openai_compat`, `openai_compat`
- `GRAPHREVIEW_JUDGE_MODEL` default: `gemma4:e4b`
- `GRAPHREVIEW_JUDGE_BASE_URL` default for local Ollama compat: `http://localhost:11434/v1`
- `GRAPHREVIEW_JUDGE_API_KEY` default: `ollama` (or required in hosted mode)
- `GRAPHREVIEW_JUDGE_TIMEOUT_SECONDS` default: `30`

Compatibility note:
Using OpenAI-compatible client with base_url makes migration from local Ollama to HF-hosted endpoint mostly a config change.

## 7) SQLite Local/Remote Strategy
- Keep SQLite primary and supported by default.
- Local mode: file-backed SQLite URL.
- Remote mode: URL from env var, with documented requirement that remote endpoint must be SQLAlchemy-compatible.
- No hidden in-memory fallback for production paths.

## 8) Review Information Persistence Rules
For each graded action:
- Persist `ReviewAnnotation` row with action type, note, episode, step.
- Update `ModuleNode.review_status` and `review_summary` deterministically.
- For amendment actions, preserve prior annotation trail and mark amendment in note payload (until schema expands).

For hard grader judge calls:
- Persist deterministic audit metadata in annotation note JSON payload:
  - `judge_model`, `judge_provider`, `temperature`, `prompt_hash`, `judge_score`.

## 9) Security, Quality, and Redundancy Tooling (Plan-Level Requirements)
Integrate in implementation PR checks (do not overbuild runtime logic):
- Lint/format: Ruff.
- Type checking: mypy (strict on `env/` and `graders/`).
- Security static analysis: Bandit + Semgrep ruleset for Python security.
- Dependency vulnerability check: `pip-audit`.
- Dead code/redundancy checks: Vulture (non-blocking report), optional Radon complexity thresholds.
- Test determinism gate:
  - run easy/medium grader test vectors 10 times and assert identical outputs.

## 10) Step-by-Step Build Order for GPT-5.3
1. Create `env/action.py` strict action schema + validators.
2. Create `env/reward.py` reward enums/models and deterministic table mapping.
3. Implement `graders/base_grader.py` typed abstract contracts.
4. Implement `graders/easy_grader.py` deterministic linter matching logic.
5. Implement `graders/medium_grader.py` deterministic keyword and attribution logic.
6. Implement `graders/hard_grader.py`:
  - graph consistency check first,
  - then LLM judge with env-configured OpenAI-compatible client and temperature=0.
7. Add/extend tests:
  - `tests/test_graders.py`
  - `tests/test_phase3_actions_rewards.py` (new)
  - `tests/test_phase3_hard_grader_determinism.py` (new)
8. Add docs update in README:
  - env vars table,
  - hard grader prompt hash policy,
  - deterministic behavior guarantees.

## 11) Phase 03 Success Criteria Verification Checklist
- Easy grader produces identical results across 10 repeated runs.
- Medium grader produces identical results across 10 repeated runs.
- Hard grader uses temperature=0 and logs/stores prompt hash.
- Reward outputs satisfy project contract and are explicitly tested for boundary cases.
- False positives and false negatives are covered with explicit test vectors.
- Review data is persisted to SQLite and reflected on graph node review fields.

## 12) Explicit Non-Goals in Phase 03
- No OpenEnv `step/reset/state` implementation yet.
- No full visualization/reporting implementation yet.
- No inference loop finalization yet.

## 13) Open Questions Requiring Confirmation Before Coding
1. Reward range conflict:
- Current reward table includes negative values, while phase criteria says all rewards must be within [0.0, 1.0].
- Proposed resolution: keep `raw_reward` (can be negative) and add `normalized_reward` in [0.0, 1.0].

2. Remote SQLite definition:
- Confirm acceptable remote backend (for example libSQL/Turso or SQLAlchemy-compatible proxy) for `GRAPHREVIEW_DATABASE_URL`.

3. Hard grader path check depth:
- Confirm whether attribution validation should be direct edge only or allow multi-hop path up to depth 2.

## 14) Handoff Notes for GPT-5.3
- Do not modify existing DB schema names without explicit migration notes.
- Keep all new models fully typed; avoid `Any` unless unavoidable.
- Treat inference log contract and temperature=0 as immutable requirements.
- Preserve backward compatibility with current seed/store data flow while adding Phase 03 logic.
