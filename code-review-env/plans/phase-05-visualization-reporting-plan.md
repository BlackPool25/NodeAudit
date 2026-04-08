# Phase 05 Plan - Visualization, Reporting, and Review Quality Assurance (for GPT-5.3)

## 1) Phase Objective
Deliver Phase 05 only, without implementing Phase 06 deployment/inference contract work:
- Build interactive graph visualization and report outputs users can trust.
- Ensure review annotations are accurate, attributable, and persisted in SQLite for replay and audit.
- Verify hard-review quality and reliability before visualization output is considered valid.
- Add direct module-level evaluation workflow beyond the bundled sample project.
- Preserve prior phase guarantees: deterministic core grading where required, DB-first state, OpenEnv compatibility.

## 2) Hard Constraints and Non-Negotiables
1. SQLite remains the primary source of truth.
- No critical review facts may exist only in memory.
- Visualization and reports must be generated from DB records.

2. Phase boundary discipline.
- Do not rewrite prior phase interfaces unless absolutely required.
- If a prior-phase interface change is required for correctness, stop and request user confirmation before changing it.

3. Hard-review judge requirement.
- Judge model default: gemma4:e4b.
- Judge temperature fixed at 0.
- Judge metadata (provider/model/temperature/prompt_hash) must be persisted for auditability.

4. Configurability for local now, hosted later.
- Local Ollama-compatible path now.
- HF/OpenAI-compatible endpoint switching via environment variables only.

## 3) Scope for Phase 05
Primary files:
- visualizer/pyvis_renderer.py
- visualizer/report_generator.py

Allowed supporting updates (only if required to satisfy Phase 05 criteria):
- db/store.py for query helpers used by visualization/reporting
- db/models.py or db/schema.py only for additive metadata fields if absolutely required (with migration)
- env/environment.py only for report trigger hooks and zero logic regressions
- README.md for visualization, validation workflow, and env var documentation
- tests/ additions for Phase 05 verification

## 4) Context7-Validated API Decisions
1. Pyvis (/westhealth/pyvis)
- Build graph via NetworkX then convert with from_nx or add nodes/edges directly.
- Use node title fields for rich hover details (review summaries and annotation snippets).
- Render to standalone HTML output file and verify browser rendering.

2. SQLAlchemy ORM (/websites/sqlalchemy_en_20_orm)
- Use short-lived session scopes.
- Use explicit transaction boundaries with session.begin() for report snapshot consistency.
- Keep engine URL environment-driven for local SQLite and SQLAlchemy-compatible remote mode.

3. OpenEnv (/meta-pytorch/openenv)
- Keep environment contract stable around reset/step/state.
- Treat report generation as read-side projection from persisted trajectories, not mutable runtime state.

## 5) Environment Variable Contract (Phase 05)
Database and storage:
- GRAPHREVIEW_DATABASE_URL
  - default: sqlite:///./code_review_env.db
  - supports SQLAlchemy-compatible remote URL for optional remote SQLite/libSQL-compatible deployment
- GRAPHREVIEW_DB_ECHO default false

Model provider switching:
- GRAPHREVIEW_LLM_PROVIDER values:
  - ollama_openai_compat
  - openai_compat
  - hf_openai_compat
- GRAPHREVIEW_LLM_BASE_URL
- GRAPHREVIEW_LLM_API_KEY
- GRAPHREVIEW_LLM_MODEL_JUDGE default gemma4:e4b
- GRAPHREVIEW_LLM_MODEL_AGENT configurable for future inference phase
- GRAPHREVIEW_LLM_TEMPERATURE_JUDGE hard-set to 0 in code path

Visualization/report outputs:
- GRAPHREVIEW_OUTPUT_DIR default ./outputs
- GRAPHREVIEW_REPORT_PREFIX default graphreview
- GRAPHREVIEW_GRAPH_HTML_NAME default graphreview_graph.html
- GRAPHREVIEW_REPORT_MD_NAME default graphreview_report.md
- GRAPHREVIEW_REPORT_JSON_NAME default graphreview_report.json

## 6) Data Integrity Contract for Review Annotations
Every persisted annotation used in visualization/reporting must include:
- module_id
- task_id
- action_type
- content (nullable only where action semantics allow)
- reward_given
- attributed_to (nullable)
- is_amendment
- created_at

Recommended additive metadata payload for quality and traceability:
- reviewer_kind (agent, judge, system)
- evidence_refs (linter ids, edge ids, module ids)
- judge_meta:
  - model
  - provider
  - temperature
  - prompt_hash
  - score

Rule:
If these fields are currently fragmented across tables, add non-breaking query projection helpers before changing schema.

## 7) Graph Rendering Design (visualizer/pyvis_renderer.py)
Node rules:
- Node id: stable module id from DB.
- Node label: compact module name.
- Node size: dependent count or chosen centrality metric from graph manager.
- Node color by review status:
  - pending: grey
  - in_progress: yellow
  - approved: green
  - changes_requested: red

Edge rules:
- explicit_import: blue
- implicit_dependency: orange
- circular: red
- Thickness by weight (1.0 explicit, 0.5 implicit minimum)

Tooltip/panel content:
- Module summary
- Top annotations (latest first, capped)
- Cascade attribution lines (when attributed_to is present)
- Last reward and task context

Rendering rules:
- Generate standalone HTML without requiring external runtime services.
- Include deterministic layout option for reproducible snapshots (seeded physics config or fixed positions when available).
- Write output atomically (tmp then move) to avoid partial files.

## 8) Report Generation Design (visualizer/report_generator.py)
Outputs:
1. Markdown report
- Per-module section with verdict, issues, evidence, and attributions.
- Task-level summary and cumulative reward.
- Hard-review quality summary with judge metadata.

2. JSON report
- Machine-readable graph projection with modules, edges, annotations, verdicts, and quality metrics.
- Stable schema version included (report_schema_version).

Required report sections:
- Executive summary (module counts, flagged findings, approvals, changes requested)
- Cascade issue attribution table (source -> impacted modules)
- False-positive/false-negative audit summary versus ground truth
- Determinism and reproducibility notes (temperature, prompt hash, run id)

## 9) Accuracy and Reliability Verification Framework
A. Ground truth alignment checks:
- Compare FLAG_* actions against stored linter flags (line tolerance policy inherited from grader).
- Compute precision/recall/F1 per task and overall.

B. Hard-review reliability checks:
- Verify each dependency attribution has graph evidence (edge or approved path rule).
- Require judge metadata presence for all hard-review judged annotations.
- Detect contradictory amendments and mark confidence downgrade.

C. Storage correctness checks:
- Annotation count parity between DB query and rendered report totals.
- No orphan annotations (module_id must exist).
- Timestamp ordering monotonic per task run.

D. Visualization consistency checks:
- Rendered node status color must match latest persisted review status.
- Rendered edge count/type breakdown must match DB edge projection.

## 10) Direct Module Testing Beyond sample_project
Add a module-targeted execution and reporting path:
- Allow specifying one or more module ids/paths from seeded DB.
- Run the same grading + persistence + reporting pipeline for selected modules.
- Output isolated reports with explicit module filter metadata.

Required capabilities:
- CLI or callable API helper that accepts:
  - task_id
  - module filter list
  - run label
- Validation that requested modules exist in current DB graph.

Use cases:
- Benchmarking real project modules.
- Focused hard-review analysis on known risky dependency chains.
- Regression checks after parser/grader changes.

## 11) RL Validity Verification in Phase 05
Even though Phase 05 is visualization/reporting, add explicit RL integrity checks in generated reports:
1. Trajectory reconstructability:
- From DB alone, reconstruct full episode transitions and cumulative reward.

2. Reward causality:
- Each reward line in report must map to a persisted action and grading rationale.

3. Policy-learning signal health:
- Report action diversity and reward variance per task.
- Highlight if reward signal collapses (all near-zero or uniformly positive).

4. Deterministic replay checks:
- Easy/medium replay consistency summary over repeated runs.
- Hard task reproducibility note with fixed judge settings.

## 12) Security and Redundancy Analysis Gates
Integrate these checks into Phase 05 acceptance workflow:
- Ruff (style/lint)
- mypy strict for visualizer and reporting modules
- Bandit and Semgrep for security anti-patterns
- pip-audit for dependency vulnerabilities
- Redundancy/complexity checks (for example vulture/radon) as advisory

Security-focused reporting requirement:
- Security flags from ground truth must be highlighted distinctly in report and graph tooltips.

## 13) Step-by-Step Build Order for GPT-5.3
1. Confirm no prior-phase interface change is required; if required, ask user first.
2. Implement DB projection/query helpers for report-ready data snapshots.
3. Implement visualizer/pyvis_renderer.py with status colors, edge typing, and tooltip payloads.
4. Implement visualizer/report_generator.py for markdown + JSON outputs.
5. Implement module-filtered run/report entrypoint for direct module testing.
6. Add verification routines for accuracy, storage parity, and RL trajectory integrity.
7. Add/extend tests for rendering invariants and report schema correctness.
8. Update README with env vars, execution flow, and validation commands.
9. Validate on sample project and at least one non-sample module set from seeded DB.

## 14) Phase 05 Success Criteria Checklist
Must pass before Phase 05 completion:
1. Graph colors update correctly as reviews accumulate.
2. Report correctly attributes cascade issues across modules.
3. HTML renders in browser without external dependencies.
4. Report totals match persisted DB records exactly.
5. Hard-review annotations include judge model gemma4:e4b and temperature=0 metadata.
6. Module-targeted testing works for non-default module selections.
7. Accuracy metrics against stored ground truth are generated and non-empty.
8. RL integrity section is present and reconstructs trajectory from DB.

## 15) Test Matrix (Phase 05)
1. Unit tests:
- Node and edge style mapping logic.
- Report JSON schema validation.
- Annotation projection transformation and ordering.

2. Integration tests:
- End-to-end run produces md/json/html artifacts.
- Artifact contents match DB snapshot.
- Module-filtered run only includes requested modules.

3. Determinism checks:
- Easy/medium repeated runs produce identical summary metrics.
- Hard run logs identical config metadata with fixed temperature.

4. Regression checks:
- Existing environment reset/step/state tests still pass.

## 16) README Update Requirements (when implementation is done)
Document:
- How to generate graph + reports.
- How to run module-targeted review/testing.
- Env vars for DB and model provider switching.
- How to run quality/security checks.
- How to interpret accuracy and RL integrity sections.

## 17) Open Questions to Confirm Before Implementation
1. Remote SQLite target:
- Should remote mode explicitly support libSQL/Turso first, or remain generic SQLAlchemy-compatible URL only?

2. Hard-review path evidence:
- For dependency attribution validation, should evidence allow only direct edges or also bounded multi-hop paths (for example <= 2 hops)?

3. Confidence scoring policy:
- Should report expose a single review confidence score per module, or only raw metrics (precision/recall/attribution validity/judge score)?

4. Non-sample module testing entrypoint preference:
- Prefer CLI-only, API endpoint, or both for module-filtered execution in later phases?

## 18) Explicit Non-Goals for Phase 05
- Do not implement Phase 06 inference log contract changes yet.
- Do not introduce training logic; keep environment as online RL interaction runtime.
- Do not replace SQLite as primary database mode.
