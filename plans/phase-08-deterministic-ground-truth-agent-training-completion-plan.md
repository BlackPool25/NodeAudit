# Phase 08 Plan - Deterministic Ground Truth Completion + Agent Training Integration (for GPT-5.3)

## 1) Goal
Complete the major refactor so GraphReview is deterministic-first for detection and grading, with LLMs used only for reasoning and explanations where intended.

This plan is based on repository verification, not assumptions.

---

## 2) Verified Current State (April 8, 2026)

## 2.1 What is working
- Analyzer persistence exists in DB:
  - `AnalyzerRun` and `AnalyzerFinding` tables are present.
- Deterministic analyzer pipeline exists:
  - Runs `mypy`, `pyright`, `semgrep`.
- Seed integration exists:
  - Analyzer outputs are persisted and mirrored into `LinterFinding` for compatibility.
- Training utility scaffolding exists:
  - `training/run_manager.py` and `training/weights.py` are implemented.
- API/UI refactor exists:
  - Static UI with separate HTML/CSS/JS, plus `/analysis/run` and `/training/bootstrap`.
- Tests:
  - Focused tests passed (`tests/test_inference.py`, `tests/test_graders.py`, `tests/test_seed.py`).

## 2.2 Verified gaps against requested architecture
1. Full deterministic stack not integrated in analyzer pipeline:
   - Current pipeline runs only `mypy`, `pyright`, `semgrep`.
   - Missing unified analyzer-run integration for `pylint`, `pyflakes`, `bandit`, `vulture`.

2. Graders are still legacy/compatibility driven:
   - Easy/medium/hard read from `LinterFinding` and keyword/comment logic.
   - Hard grader still blends deterministic checks with online LLM judge output in reward path.

3. Training harness is not agent-integrated yet:
   - `inference.py` uses placeholder `agent_keys = set()`.
   - No real Qwen GGUF inference loop producing actions/findings.

4. Sample project does not match required canonical spec:
   - Required files missing: `models.py`, `api.py`, `main.py`.
   - Extra files present that violate exact fixture requirement (for challenge path): `huge_module.py`, `inventory.py`, `notifications.py`, `validators.py`.

5. Inference run reliability issue discovered:
   - End-to-end run can hang/slow due to edge summarizer LLM call path during seed when edge summary is enabled by env.
   - This undermines deterministic/offline reproducibility.

6. Test suite is not fully green:
   - Full run result: 25 passed, 1 failed.
   - Failure is UI assertion mismatch in `tests/test_phase5_server_api.py` expecting previous title string.

7. Runtime model defaults are misaligned with requested target:
   - `llm_model_agent` default still `gemma4:e4b` (should route agent role to Qwen path/config).

---

## 3) Non-Negotiable Architecture Rules for Phase 08
1. DB is source of truth for all findings and run metadata.
2. Deterministic grading path must not depend on LLM output.
3. Agent prompt/context must not include deterministic findings (strict no-leak).
4. Token budget remains hard-capped at 2000 tokens.
5. Reset must clear run annotations only; no reparsing.
6. Easy/medium graders deterministic for identical inputs.
7. Explanation artifacts are explicitly non-scoring.

---

## 4) Required Design Decisions (must be confirmed before schema/interface changes)
These are high-impact and hard to reverse:

1. Canonical fixture strategy:
   - Option A: enforce exact `sample_project/` contents directly.
   - Option B: introduce `sample_project_canonical/` and keep current `sample_project/` for regression compatibility.

2. Analyzer source-of-truth migration strategy:
   - Option A: fully switch graders to `AnalyzerFinding` table by tool class.
   - Option B: maintain compatibility mirror in `LinterFinding` with explicit deprecation timeline.

3. Hard grader reward semantics:
   - Option A: pure deterministic reward (semgrep + graph path), zero LLM contribution.
   - Option B: deterministic reward + separate non-reward LLM explanation quality metric.

4. Agent execution backend for Qwen GGUF:
   - Option A: local llama.cpp-compatible runtime adapter in `inference.py`.
   - Option B: OpenAI-compatible wrapper with reproducibility guardrails + model fingerprint logging.

---

## 5) Phase 08 Implementation Tracks

## Track A - Analyzer Completion and Normalization
Objective: complete deterministic truth generation with one normalized schema.

Tasks:
1. Extend `analyzers/pipeline.py` with runners for:
   - `pylint`, `pyflakes`, `bandit`, `vulture`.
2. Normalize all outputs into strict record schema:
   - analyzer, module_id, line, severity, rule_id, message, evidence.
3. Persist run metadata:
   - command/config hash, analyzer version, timestamps, status.
4. Add deterministic dedupe policy:
   - unique key `(analyzer, module_id, line, rule_id, message_hash)`.

Exit criteria:
- One seed creates unified records for all analyzers.
- Repeated unchanged seed runs produce stable finding sets.

## Track B - Grader Migration to Analyzer-Native Truth
Objective: remove compatibility dependence and enforce deterministic scoring.

Tasks:
1. Easy grader truth mapping:
   - analyzer classes: `pylint`, `pyflakes`, `bandit`, `vulture`.
2. Medium grader truth mapping:
   - analyzer classes: `mypy`, `pyright`.
3. Hard grader truth mapping:
   - `semgrep` custom rules + graph path validation.
4. Remove reward dependency on judge/verifier calls.
5. Keep optional explanation/judge output as metadata only.

Exit criteria:
- Easy and medium replay determinism x10 (identical cumulative reward).
- Hard reward reproducible with deterministic inputs.

## Track C - Prompt No-Leak Contract + Agent Tasking
Objective: enforce true reasoning task without exposing answers.

Tasks:
1. Define strict prompt payload contract:
   - allow: code, AST summary, graph-neighbor context, task description, action schema.
   - disallow: analyzer finding text, rule IDs, line hints from ground truth.
2. Add prompt audit utility:
   - fail test if forbidden fields/tokens appear.
3. Replace current hard issue finder prompt with detailed multi-paragraph objective prompt designed for graph-aware attribution.
4. Persist prompt hash + context hash for reproducibility.

Exit criteria:
- Prompt no-leak tests pass.
- Run artifacts contain hashes for audit reproducibility.

## Track D - Qwen2.5 GGUF Agent Integration + Training Suite
Objective: convert bootstrap harness into real train/eval pipeline.

Tasks:
1. Implement real agent inference adapter for Qwen2.5 GGUF.
2. Parse model outputs into typed action/finding proposals.
3. Execute episodes and compare proposals against deterministic truth.
4. Persist training run registry in DB:
   - run_id, model fingerprint/hash, config, seed, metrics, artifact paths.
5. Expand training dataset records:
   - prompt/context hash, agent output, deterministic targets, reward, correction notes.
6. Add non-regression gate on precision/recall and attribution-F1.

Exit criteria:
- `inference.py` runs with real agent outputs (no placeholder key set).
- Training artifacts are reproducible and queryable.

## Track E - Gemma 4 Explanation Pipeline (Non-Scoring)
Objective: use Gemma 4 for summaries/explanations only after deterministic grading.

Tasks:
1. Add post-grading summarizer module consuming:
   - deterministic findings, agent findings, mismatch analysis, graph attribution outcomes.
2. Generate:
   - edge relationship narratives,
   - what agent got right,
   - false positives/false negatives,
   - root-cause attribution misses.
3. Label all generated text as non-scoring.

Exit criteria:
- Reports cleanly separate deterministic score and narrative explanation.

## Track F - Canonical Sample Project Compliance
Objective: align challenge fixture exactly with required file set and bug mapping.

Tasks:
1. Implement canonical fixture with exact required files:
   - `auth.py`, `checkout.py`, `cart.py`, `config.py`, `database.py`, `utils.py`, `models.py`, `payments.py`, `api.py`, `main.py`.
2. Encode required bug mapping:
   - easy: style issues in `cart.py`.
   - medium: nullable flow `auth.py` -> `checkout.py`.
   - hard: cascade `config.py` -> `auth.py` -> `checkout.py`.
3. Add fixture validator script and test.

Exit criteria:
- Validator guarantees exact file set and injected signatures.

## Track G - Reliability, Security, and CI Gates
Objective: harden for hackathon reproducibility and safe operation.

Tasks:
1. Ensure deterministic fallback path always available when LLM endpoints unavailable.
2. Make edge summarizer opt-in and non-blocking for seed/inference critical path.
3. Add secure subprocess execution controls for analyzers:
   - timeouts, non-shell invocation, sanitized target paths.
4. Strengthen CI quality gates:
   - `pytest`, `ruff`, `mypy`, `bandit`, `semgrep`, `pip-audit`.
5. Add DB migration tests and rollback checks.

Exit criteria:
- CI green.
- No network dependence required for deterministic scoring path.

---

## 6) Test and Verification Matrix (Phase 08)

## 6.1 Functional
1. Full test suite passes with deterministic mode enabled.
2. New analyzer-native grader tests pass for all task levels.
3. Inference harness runs end-to-end without hanging when no LLM service is available.

## 6.2 Determinism
1. Easy replay x10 same reward.
2. Medium replay x10 same reward.
3. Hard replay x10 same reward for identical action sequence.

## 6.3 No-Leak
1. Prompt payload scanner fails on any analyzer finding leakage.
2. Snapshot tests verify only allowed context fields are sent to agent.

## 6.4 Security
1. Analyzer command invocations use safe argument lists and bounded timeouts.
2. Path traversal checks on artifact/report routes.
3. Dependency audit clean for high/critical issues.

---

## 7) Suggested Execution Order
1. Track A (Analyzer completion)
2. Track B (Grader migration)
3. Track C (No-leak contract)
4. Track F (Canonical fixture)
5. Track D (Qwen agent + training integration)
6. Track E (Gemma explanation pipeline)
7. Track G (hardening + CI gates)

Rationale:
- Build deterministic truth and scoring first.
- Freeze interface contracts before integrating agent runtime and narrative layer.

---

## 8) Immediate Fixes to Unblock Track Work
1. Fix failing UI title assertion or update test expectation to current UI copy.
2. Ensure deterministic seed/inference path cannot block on edge LLM summarization.
3. Add explicit phase status section in README reflecting implemented vs planned phase items.

---

## 9) Definition of Done for Phase 08
Phase 08 is complete only when all conditions are true:
1. Ground truth is fully generated from deterministic analyzers and persisted in analyzer-native tables.
2. Easy/medium/hard reward paths are deterministic and analyzer-native.
3. Agent receives no leaked answers and is evaluated against deterministic truth.
4. Qwen2.5 GGUF inference is integrated into train/eval harness with run registry.
5. Gemma 4 generates explanatory/critical analysis text outside scoring.
6. Canonical sample project exactly matches required challenge fixture and mapping.
7. Full quality/security gates pass in CI.
