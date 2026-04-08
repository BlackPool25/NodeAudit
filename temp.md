You are a project planning expert. I am attending a pre Hackathon competition and I need to build a rl environment. I am building this project for this submission

# Builder Prompt — GraphReview RL Environment

You are an expert Python engineer planner. You do not build. You can add more tools to catch more security vulnerabilities for the modules before actually sending it out. ANd you can also turn on thinking for the gemma 4 model if it works better and ensure it runs on all the modules and actually finds info not just repeating the stuff from previous models. But the previous info should also be provided as context and told to find more if possible about those errors and any new errors. a production-quality RL environment for a competitive hackathon (OpenEnv Round 1). You have one job: build the GraphReview environment correctly, phase by phase, without breaking prior work.

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

These are the requirements

Registration

14th March - 3rd April

Declaration

Before R1

Prepare

Now - 25th March

Round 1

25th March - 8th April

Results

10th April

Finale

25th-26th April

Welcome Shreyas  S Joshi!

shreyasjoshi2511@gmail.com
Copy
Join the Discord Community

All announcements, mentor access, and team matching happens here.


Join Discord
QUICK TOGGLe

Team form Submission

Preparatory Course

Start Assessment

FAQs

step 1

How will you compete?

Choose solo or team before you can start the assessment

Step 1 Complete
Team: Shreyas S Joshi's team

👤
Athmabhiram S J
athmabhiram@gmail.com
Accepted
👤
Shreyas S Joshi
shreyasjoshi2511@gmail.com
Team Lead
🔒
Team is permanently locked. Changes are not allowed after confirmation.

OpenEnv Round 1 Bootcamp

OpenEnv Round 1 Bootcamp

OpenEnv Round 1 Bootcamp

OpenEnv Round 1 Bootcamp

OpenEnv Round 1 Bootcamp

OpenEnv Round 1 Bootcamp

OpenEnv Round 1 Bootcamp

OpenEnv Round 1 Bootcamp

OpenEnv Round 1 Bootcamp

OpenEnv Round 1 Bootcamp: Build Your First RL Environment

Live walkthrough to submit a strong Round 1 entry

timing

8:00 PM Onwards

Wednesday, 1st April

Host


Ben Burtenshaw

Community Education in AI at Hugging Face


Pulkit Aneja

Scaler Instructor

Watch Recording

PROBLEM STATEMENT

Round 1 — Problem Statement

The Task

Build a complete, real-world OpenEnv environment that an AI agent can learn from through the standard  step() / reset() / state()  API.

Key Requirements at a Glance

Must simulate a real-world task (not games or toys)

Implement full OpenEnv spec: typed models, step()/reset()/state(), openenv.yaml

Minimum 3 tasks with agent graders (easy → medium → hard, scores/reward 0.0–1.0)

Meaningful reward function with partial progress signals

Baseline inference script with reproducible scores

Deploy to Hugging Face Spaces + working Dockerfile

README with environment description, action/observation spaces, setup instructions

Functional Requirements

Real-world task simulation

The environment must simulate a task humans actually do. Not games, not toys. Examples: email triage, code review, data cleaning, scheduling, customer support, content moderation.

OpenEnv spec compliance

Implement the full OpenEnv interface: typed Observation, Action, and Reward Pydantic models. step(action) → returns observation, reward, done, info. reset() → returns initial observation. state() → returns current state. openenv.yaml with metadata. Tested via openenv validate.

Minimum 3 tasks with agent graders

Each task defines a concrete objective an agent must accomplish, with a programmatic grader that scores performance (0.0–1.0). Tasks should range: easy → medium → hard. Graders must have clear, deterministic success/failure criteria.

Meaningful reward function

Provides signal over the full trajectory (not just binary end-of-episode). Rewards partial progress toward task completion. Penalizes clearly undesirable behavior (e.g. infinite loops, destructive actions).

Baseline inference script

Uses the OpenAI API client to run a model against the environment. Reads API credentials from environment variables (OPENAI_API_KEY). Produces a reproducible baseline score on all 3 tasks.

Detailed Requirements

Non-Functional Requirements

Deploys to a Hugging Face Space

Environment must run as a containerized HF Space tagged with openenv.

Containerized execution

Must include a working Dockerfile. The environment should start cleanly with docker build + docker run.

Documentation

README must include: environment description and motivation, action and observation space definitions, task descriptions with expected difficulty, setup and usage instructions, baseline scores.

Parameter

Weight

Description

Real-world utility

30%

Does the environment model a genuine task? Would someone actually use this to train or evaluate agents?

Task & grader quality

25%

Are tasks well-defined with clear objectives? Do graders accurately and fairly measure success? Meaningful difficulty progression?

Environment design

20%

Clean state management, sensible action/observation spaces, good reward shaping, proper episode boundaries.

Code quality & spec compliance

15%

Follows OpenEnv spec, clean project structure, typed models, documented, tested, Dockerfile works.

Creativity & novelty

10%

Novel problem domain, interesting mechanics, clever reward design, original approach.

Scoring Breakdown

Real-world utility (30%)

•  0–5: Toy/artificial problem with no practical application

•  6–15: Valid domain but shallow modeling of the real task

•  16–25: Good domain modeling, would be useful for agent evaluation

•  26–30: Excellent — fills a real gap, immediate value for the RL/agent community

Task & grader quality (25%)

•  3+ tasks with difficulty range?

•  Graders produce scores between 0.0–1.0?

•  Graders deterministic and reproducible?

•  Hard task genuinely challenges frontier models?

Environment design (20%)

•  reset() produces clean state?

•  Action/observation types well-designed and documented?

•  Reward function provides useful varying signal (not just sparse)?

•  Episode boundaries sensible?

Code quality & spec compliance (15%)

•  openenv validate passes?

•  docker build && docker run works?

•  HF Space deploys and responds?

•  Baseline script runs and reproduces scores?

Creativity & novelty (10%)

•  Domain we haven’t seen in OpenEnv before?

•  Reward design has interesting properties?

•  Clever mechanics that make the environment engaging?

Evaluation Criteria

Phase 1: Automated Validation

Pass/fail gate — HF Space deploys, OpenEnv spec compliance, Dockerfile builds, baseline reproduces, 3+ tasks with graders.

Phase 2: Agentic Evaluation

Scored — baseline agent re-run, standard Open LLM agent (e.g. Nemotron 3 Super) run against all environments, score variance check.

Phase 3: Human Review

Top submissions reviewed by Meta and Hugging Face engineers for real-world utility, creativity, and exploit checks.

Disqualification Criteria

Environment does not deploy or respond

Plagiarized or trivially modified existing environments

Graders that always return the same score

No baseline inference script

How Judging works

Pre-Submission Checklist  — all must pass or you're disqualified

HF Space deploys

Automated ping to the Space URL — must return 200 and respond to reset()

OpenEnv spec compliance

Validate openenv.yaml, typed models, step()/reset()/state() endpoints

Dockerfile builds

Automated docker build on the submitted repo

Baseline reproduces

Run the submitted inference script — must complete without error and produce scores

3+ tasks with graders

Enumerate tasks, run each grader, verify scores/reward in 0.0–1.0 range

Mandatory Additional Instructions

Before submitting, ensure the following variables are defined in your environment configuration:

API_BASE_URL   The API endpoint for the LLM.

MODEL_NAME     The model identifier to use for inference.

HF_TOKEN       Your Hugging Face / API key.

The inference script must be named `inference.py` and placed in the root directory of the project

Participants must use OpenAI Client for all LLM calls using above variables

Participants must emit structured stdout logs strictly following the [START], [STEP], and [END] format defined in the sample inference.py provided below. Any deviation in field names, ordering, or formatting will result in incorrect evaluation scoring. Refer to the Sample Inference Script for the complete format specification and examples.

Infra Restrictions

Runtime of inference script should be less than 20min 

Make sure your env and inference can run on a machine with vcpu=2, memory=8gb

Validator

Run the pre-submission validation script before submitting

NEW
Sample Inference Script 

NEW
Pre Validation Script

Submission window opens on 28th March

Deadline: 8 Apr 11:59 PM


Submit your Assessment
→
Study material

Preparatory Course

4 modules · ~3.5 hours 

Each module: read the README first, then open the notebook in Colab. No local setup needed.

 Module 1: Why OpenEnv?

ESSENTIAL FOR ROUND 1

45 min

Module 2: Using Existing Environments

ESSENTIAL FOR ROUND 1

50 min

 Module 3: Deploying Environments

ESSENTIAL FOR ROUND 1

45 min

Module 4: Building Your Own Environment

 MOST IMPORTANT FOR ROUND 1

60 min

View full course repository

GUIDE

Round 1 Guide

What to Expect

When Round 1 opens, you'll choose 1 of 4–5 problem statements and build an OpenEnv environment around it.

Example of what a problem statement looks like

"Build a mini-game RL environment with clearly defined tasks, automated graders, and reward logic using the OpenEnv framework."

→ Create a mini-game an AI agent can play

→ Define tasks with increasing difficulty

→ Write graders that verify task completion

→ Define reward logic for scoring

→ Package using OpenEnv for automated evaluation

Evaluation Criteria

Runtime correctness

Runs without errors

Interface compliance

Follows OpenEnv standard

Task design

 Clear, realistic, testable

Grading logic

 Reward system makes sense

20,000 → 3,000 teams advance

Prerequisites

Install before April 1st.

Required

Python 3.10+

Install 3.10, 3.11, or 3.12.

$
python --version
Copy
Git + GitHub account

Push your submission to GitHub or HF.

$
git --version
Copy
Hugging Face CLI

Deploy to HF Spaces.

$
pip install huggingface_hub --version
Copy
$
huggingface-cli login
Copy
OpenEnv

The framework.

$
pip install openenv-core
Copy
Google Colab

Prep course runs in Colab. Free tier works.

$
pip install openenv-core
Copy
OpenEnv

The framework.

→ colab.research.google.com
Copy
Docker

Isolated container testing.

docker --version
Copy
Recommended

VS Code

Best Python + Docker support

How to Submit

When Round 1 starts on 1 April:

Step 1

Application Form
Choose 1 of the 4–5 problem statements revealed on the platform.

Step 2

 Scaffold
$
openenv init my_env
Copy
Generate project structure.

Step 3

Build
Define your environment in the generated files.

Step 4

Test locally
$
uv run server
Copy
Step 5

Deploy
$
openenv push --repo-id your-username/my-env
Copy
Step 6

 Submit
Paste your HF Spaces URL here before the deadline.

Deadline: 8 April 2026, 11:59 PM IST

Step 2

Submit your Assessment

Complete Step 1 first

Problem Statement is live. Build and submit.

Round 1 begins 

Submission window opens on 28th March

Deadline: 8 Apr 11:59 PM


Submit your Assessment
→
NOTE: Only team leaders can make the final submission.

FAQs

Frequently Asked Questions













Need help? Reach out to us

help_openenvhackathon@scaler.com

Contact Support

submission Deadline: 8th April 11:59 PM


Submit your Assessment
→
How to Submit?



Great question. Here's exactly what the agent does in a **Code Review RL Environment:**

---

## 🤖 The Agent's Job

The agent acts as a **junior code reviewer**. Each episode, it's shown a code snippet and must take actions to review it — just like a human would on GitHub.

---

## 🎮 The Action Space

The agent can take these actions:

```
APPROVE          → Code looks good, no issues
FLAG_STYLE       → Flag a style/formatting issue
FLAG_BUG         → Flag a logic bug
FLAG_SECURITY    → Flag a security vulnerability
ADD_COMMENT(txt) → Leave a review comment explaining the issue
REQUEST_CHANGES  → Block the PR from merging
```

---

## 🔁 One Episode — Step by Step

```
reset()
  → Agent receives a code snippet (the PR diff)

step(FLAG_BUG)
  → Grader checks: was there actually a bug?
  → Reward: +0.5 if correct, -0.2 if false positive

step(ADD_COMMENT("This causes a null pointer on line 12"))
  → Grader checks comment relevance
  → Reward: +0.3 if accurate, 0.0 if vague

step(REQUEST_CHANGES)
  → Episode ends
  → Final reward tallied
```

---

## 📊 The 3 Tasks (Easy → Hard)

| Task | What the agent sees | What it must do | Grader |
|---|---|---|---|
| **Easy** | Code with a PEP8 style issue | Flag the style issue | Deterministic — AST/linter check |
| **Medium** | Code with a subtle logic bug | Flag the bug + comment location | Check flag + line number accuracy |
| **Hard** | Code with a hidden security vuln (SQL injection, path traversal) | Flag security issue + explain risk | Check flag + comment quality via LLM grader |

---

## 🏅 Reward Design

| Action | Reward |
|---|---|
| Correct flag on real issue | +0.5 |
| Accurate comment/explanation | +0.3 |
| False positive flag | -0.2 |
| Missed critical issue | -0.4 |
| APPROVE on buggy code | -1.0 |
| Clean episode completion | +0.2 bonus |

This gives **partial progress signals** across the whole trajectory, not just end-of-episode — which directly satisfies one of the judging criteria.

---

## 🔑 Why This Works Well for You

- Every action is **deterministic to grade** (you're a SE, you can write the graders confidently)
- Code snippets can be **synthetically generated** — no dataset needed
- The hard task grader can use an **LLM call internally** to score comment quality, which is also where GraphRAG could plug in

Want me to now create the **full file structure and implementation plan** you can start coding today?

Okay so basically what if I take the code covert it into a graph and then feed the model and ask it review and that also will again be stored in the graph and in the end the user will have a dependency graph and a review of each module in depth and using the LLM to read the logical reasoning behind the code not just the pylint errors beging caught.

That's a genuinely clever idea! Let me break down what you're describing and stress-test it against the requirements.

---

## 🧠 What You're Describing

```
Codebase
    ↓
GraphRAG parses it → Dependency Graph (nodes = modules, edges = imports/calls)
    ↓
Agent receives a module + its graph context as observation
    ↓
Agent reviews that module (flags bugs, security issues, style)
    ↓
Review is stored back into the graph as an annotation
    ↓
Final output: Annotated dependency graph with reviews on every module
```

This is actually a **multi-episode environment** where each episode = one module, and the final deliverable is a fully reviewed codebase graph.

---

## ✅ Why This Is Strong

| Criteria | How it scores |
|---|---|
| Real-world utility (30%) | Extremely high — this is literally what code review tools like CodeClimate do, but agent-driven |
| Creativity (10%) | Very novel — graph-aware code review hasn't been done in OpenEnv |
| Environment design (20%) | Graph context as observation is well-structured and meaningful |
| Task & grader quality (25%) | Natural difficulty progression across modules |

---

## 🔁 How the RL Loop Works

```
reset()
→ Load codebase graph
→ Pick starting module (e.g. lowest dependency = easiest)
→ Observation = {code, graph_neighbors, import_chain}

step(action)
→ Agent flags issues, adds comments
→ Grader scores the review
→ Reward returned
→ Review annotation stored on graph node
→ Next module selected (traversal order)

state()
→ Returns current graph with all annotations so far

done = True when all modules reviewed
```

---

## ⚠️ One Risk to Manage

The **grader for review quality** needs to be deterministic to pass the auto-validation gate. Two ways to handle this:

- **Easy/Medium tasks** — use AST + linter (pylint, bandit) as ground truth. Grader checks if agent caught what the linter already knows.
- **Hard tasks** — LLM-as-judge internally, but with a fixed seed/prompt so it's reproducible.

---

## 🛠️ Tech Stack

| Component | Tool |
|---|---|
| Graph construction | NetworkX + AST parser |
| Graph storage | NetworkX (in-memory, no DB needed) |
| RAG layer | LightRAG or simple vector search over node embeddings |
| Grader (easy/medium) | pylint, bandit, pyflakes |
| Grader (hard) | LLM-as-judge with fixed prompt |
| Observation model | Pydantic — code + graph context |

---

## 💡 My Honest Take

This is your **best idea yet**. It's novel, it's real-world, and the graph-as-state is a genuinely interesting RL mechanic that judges from Meta/HF will notice. The risk is build time — this is more complex than a flat code review env.

**Given you have ~1.5 days, want me to scope a minimal viable version of this that hits all the judging criteria without overbuilding?**

Okay so a particular module might have let's say a dependency issue but that might be due to another issue. Like that module has taken a particular decision because of a requirement in another module but due to that another issue has raised but the model might report to remove that crucial decision for the project. Also a module might be needed in a lot of places how would you suggest to traverse the graph cause you need to compare all the dependencies and issues with all the modules it's not just bfs. And is gemma 4 4Eb good enough for the demo? Search online

Great questions — you're thinking about this at a deep level. Let me tackle each part.Good news on Gemma 4. Now let me address all three of your questions properly.

---

## 1. 🧠 The Cascading Dependency Problem

You're describing a real and important issue — **a decision in module A causes a problem in module B, but the agent reviewing B in isolation flags it as wrong without knowing why.**

The solution is **context-aware observations**. When the agent reviews a module, its observation must include:

```
Observation = {
  current_module: code + issues found,
  upstream_deps: why they made decisions that affect this module,
  downstream_deps: what modules depend on THIS module,
  existing_reviews: annotations already written on neighbors,
  constraint_flags: ["decision X is forced by module Y's requirement"]
}
```

So the agent never reviews a module in isolation. It always sees the **"why" from upstream** before flagging anything. If module B has a weird pattern because module A forced it, the agent sees that constraint and should reward `ADD_COMMENT("dependency constraint from A")` over `FLAG_BUG`.

This is actually what makes your environment **genuinely novel** — most code review tools don't model this.

---

## 2. 🗺️ Graph Traversal Strategy

You're right that BFS is wrong here. Here's what I'd suggest — a **weighted priority traversal**:

```
Score each node by:
  - Dependency centrality (how many modules import this one)
  - Issue density (how many raw linter flags exist)
  - Review dependency (can't review B properly until A is reviewed)

Traversal order:
  Step 1 → Leaf modules (no dependencies) — safe to review in isolation
  Step 2 → High centrality nodes — review these with full leaf context
  Step 3 → Complex nodes — reviewed last with full graph context available
```

Think of it like a **topological sort weighted by centrality**. NetworkX has both `topological_sort()` and `betweenness_centrality()` built in — you can combine them directly.

The key insight: **a module's review is only valid once all its dependencies have been reviewed first.** That's your episode ordering logic.

---

## 3. 🤖 Is Gemma 4 E4B Good Enough?

**Short answer: Yes for a demo, but use the 27B MoE if you can.**

Here's what the search shows:

- Gemma 4 E4B is designed for edge devices, prioritizing multimodal capability, low-latency processing, and on-device utility. It's capable but optimized for efficiency over raw reasoning power.

- The 26B MoE model runs almost as fast as a 4B model since it only activates 4B parameters at a time — so if your HF Space can handle it, the 27B MoE gives you much stronger reasoning at nearly the same inference speed.

- E4B has a 128K context window — which is actually great for your use case since you'll be feeding code + graph context into each prompt.

- Gemma 4 shows significant improvements in coding benchmarks and native function-calling support for agentic workflows — which directly maps to what your agent needs to do.

**My recommendation:**

| Scenario | Model |
|---|---|
| Local testing / dev | Gemma 4 E4B — fits in 8GB RAM |
| HF Space demo (inference.py) | Gemma 4 27B MoE — stronger reviews, still fast |
| Fallback if quota issues | Gemma 4 E4B is acceptable for passing evaluation |

The competition's inference script runs on 2 vCPU / 8GB RAM — E4B fits, 27B MoE likely won't. So **E4B is your safest bet for the submission**, but use 27B MoE via API if you're calling it remotely.

---

Want me to now draft the **actual file structure and core implementation skeleton** so you can start coding today?

Great questions — let me search for both.Great — I have a thorough picture now. Here's the full analysis:

---

## 🔍 Does Your Idea Already Exist?

### What CodeRabbit Does

CodeRabbit uses a "Codegraph" to understand complex dependencies across files and uncover the impact of changes, pulling in 40+ linters and security scanners. Sounds similar, right? But here's the critical difference:

CodeRabbit reviews are tied to diff visibility only — it can't reason about system-wide architecture, cross-repo dependencies, or historical design decisions. It can't validate whether a microservice change breaks contracts with downstream services.

That's exactly the gap your environment targets. CodeRabbit handles first-pass mechanical review: style violations, security issues, common bugs. Human reviewers still need to evaluate architecture, business logic, and design decisions.

### The Core Differentiation of Your Idea

| Feature | CodeRabbit | Your RL Environment |
|---|---|---|
| Graph of codebase | ✅ Lightweight map | ✅ Full dependency graph |
| Context-aware review | Partial (diff only) | ✅ Full upstream/downstream context |
| Cascading dependency reasoning | ❌ | ✅ Core mechanic |
| Reviews stored back to graph | ❌ | ✅ Annotated output |
| RL agent learns from rewards | ❌ Static tool | ✅ Trainable agent |
| Final deliverable to user | PR comments | Annotated dependency map |

**Your environment fills a documented gap.** This is strong for the real-world utility score (30%).

---

## 🏗️ Architectural Questions You Still Need to Answer

### 1. Graph Schema Design
What does a node actually contain?
```
Node = {
  module_id: str,
  code: str,
  ast_summary: dict,       # function signatures, classes
  linter_flags: list,      # pre-computed ground truth for graders
  dependency_reason: str,  # WHY it depends on neighbors
  review_annotation: dict  # written by agent, starts null
}
```
You need to decide this upfront — it drives everything else.

---

### 2. Observation Construction Strategy
How much graph context do you inject per step? Too little = agent reviews blindly. Too much = exceeds context window.

**Recommended approach — tiered context:**
```
Easy task   → current module only
Medium task → current module + direct neighbors
Hard task   → current module + 2-hop neighborhood + existing reviews
```
This naturally creates difficulty progression and respects the 128K context window of Gemma 4 E4B.

---

### 3. Episode Boundary Design
When does an episode end? Two valid designs:

- **Per-module episodes** — one episode = one module reviewed. Fast, easy to grade.
- **Full-codebase episodes** — one episode = entire codebase reviewed in traversal order. More realistic, harder to grade.

For the submission I'd recommend **per-module with a meta-episode wrapper** — each module is an episode, but the graph state persists across them so reviews accumulate.

---

### 4. Reward Attribution Problem
If the agent correctly identifies a cascading issue (bug in B caused by A), who gets the reward — the step that flagged it, or the final episode? You need a clear policy:

```
Reward policy:
  +0.6 if agent flags issue AND correctly attributes it to upstream module
  +0.3 if agent flags issue but misattributes cause
  -0.3 if agent flags false positive ignoring upstream context
```

---

### 5. Graph Generation Strategy
Where does the test codebase come from? Three options:

| Option | Pro | Con |
|---|---|---|
| Parse a real OSS repo (e.g. Flask, FastAPI) | Realistic | Complex to control |
| Synthetically generate modules | Fully deterministic graders | Less realistic |
| Hybrid — real structure, injected bugs | Best of both | Medium effort |

**Hybrid is the right call** — use a real repo's structure but inject known bugs so graders can be 100% deterministic.

---

### 6. Grader Architecture (Critical for Pass/Fail Gate)

```
Easy grader   → pylint/bandit pre-run, check if agent flagged same issues ✅ fully deterministic
Medium grader → AST diff between agent's suggested fix and ground truth ✅ deterministic  
Hard grader   → LLM-as-judge with fixed seed + rubric for cascading reasoning ⚠️ quasi-deterministic
```

The hard grader is your biggest risk. Fix the judge prompt, temperature=0, and document it clearly in README.

---

### 7. State Persistence Across Episodes
The graph with accumulated annotations IS your `state()`. You need to define:
- What gets serialized (NetworkX graph → JSON)
- How `reset()` clears annotations but keeps graph structure
- Whether partial reviews survive between episodes (they should)

---

## ✅ Summary: What Makes You Novel vs CodeRabbit

The key architectural insight is that an AI seeing only one file without context on its neighbors leads to false positives — it worries about things that are actually handled upstream. Your environment is the first RL training ground that explicitly teaches agents to reason about this. That's your pitch to the judges.

---

Full up and full down will be too heavy for the model to look at in complex projects right having thousands of lines of code

Exactly right. You've identified the most critical architectural bottleneck. Here's how to solve it:

---

## 🧠 The Core Problem

A real project could have:
- Module A → 500 lines
- 10 direct dependencies → each 300 lines
- 2-hop neighbors → another 20 modules

That's **thousands of tokens just for context**, before the agent even starts reviewing. Gemma 4 E4B's 128K window sounds big but fills fast.

---

## ✅ Solution: Compressed Graph Context (Not Raw Code)

**Never feed raw code as context. Feed summaries.**

```
Instead of:
  "Here is module_auth.py [500 lines of code]..."

Feed:
  "module_auth.py → exposes: validate_token(str) → User | None
   Known issues: may return None on expired token
   Depended on by: checkout.py, cart.py
   Review status: flagged null return risk"
```

This is your **Graph Summary Layer** — sitting between the raw graph and the agent's observation.

---

## 🏗️ The 3-Layer Observation Architecture

```
Layer 1: AST Compression
  Raw code → extract only signatures, return types, 
  decorators, class names
  Tool: Python's ast module
  Output: ~50 tokens per module (vs 500+ raw)

Layer 2: Graph Summary Node
  Per node store:
  {
    exports: ["validate_token(str) → User | None"],
    known_issues: ["may return None"],
    constraint_flags: ["forced by requirement in auth_service.py"],
    review_status: "pending | reviewed | flagged",
    review_summary: "one line of what was found"  ← written by agent
  }

Layer 3: Agent Observation (what model actually sees)
  {
    current_module: full code,        ← only this is full
    direct_deps: [graph summaries],   ← compressed
    dependents: [graph summaries],    ← compressed
    relevant_reviews: [one-liners]    ← already written
  }
```

So the agent always sees **one module in full**, and everything else as compressed summaries.

---

## 📐 Token Budget Estimate

| Component | Tokens |
|---|---|
| Current module (full code) | ~800 |
| 5 dependency summaries × 50 tokens | ~250 |
| 5 dependent summaries × 50 tokens | ~250 |
| Existing review annotations | ~200 |
| System prompt + action space | ~300 |
| **Total per step** | **~1,800** |

That's well within E4B's window, even for complex projects.

---

## 🎯 Bonus: This Becomes a Feature, Not a Workaround

The **summary layer is actually what makes your environment novel**. You're teaching the agent to:

1. Read compressed dependency context
2. Decide if a deeper look is needed
3. Optionally request full code of a neighbor via a `REQUEST_CONTEXT(module_id)` action

That `REQUEST_CONTEXT` action costs a small reward penalty (simulating real reviewer time cost), which is **genuinely interesting RL reward shaping** that judges will notice.

---

## The Revised Action Space

```
APPROVE
FLAG_STYLE
FLAG_BUG  
FLAG_SECURITY
FLAG_DEPENDENCY_ISSUE   ← new: cascading problem from neighbor
ADD_COMMENT(txt)
REQUEST_CHANGES
REQUEST_CONTEXT(module)  ← new: pay token cost, get full neighbor code
```

This elegantly solves your original cascading dependency problem too — the agent can *choose* to investigate upstream before judging.

Want me to now write the full file structure and implementation skeleton?

Great — these are the four hardest design questions in the project. Let me work through each one carefully.

---

## 1. 🔪 Converting Code Into Modules Accurately

The challenge is — what IS a module? You need a deterministic answer.

**Recommended: File = Module, with AST sub-structure**

```
Step 1: File-level split
  Each .py file = one node in the graph
  filename → module_id

Step 2: AST parsing per file
  Extract:
  - All function signatures + return types
  - All class definitions
  - All imports (this gives you edges)
  - All global variables

Step 3: Edge construction from imports
  "from auth import validate_token"
  → edge: current_module → auth.py

Step 4: Dependency reason tagging
  Use the import line + first usage context
  as the "why this depends on that" annotation
```

**The hard problem: implicit dependencies**
Sometimes module B doesn't import A directly but uses a shared global or config. Handle this with a second pass:

```
Pass 1: Explicit edges (imports)
Pass 2: Name resolution edges
  - scan function bodies for names not defined locally
  - trace them back to source module
  - add a "implicit dependency" edge with lower weight
```

Python's `ast` module handles all of this natively. No external library needed.

---

## 2. 📊 How Reporting Works

Think of reporting as **three layers that build progressively**:

```
Layer 1: Per-step annotation (live)
  Every time agent calls ADD_COMMENT or FLAG_*,
  that gets written immediately to the graph node
  as a review_annotation field

Layer 2: Per-module summary (end of episode)
  When episode ends (agent calls APPROVE or REQUEST_CHANGES),
  environment compiles all step annotations into:
  {
    verdict: "approved | changes_requested",
    issues: [...],
    dependency_notes: [...],
    confidence: 0.0-1.0  ← derived from reward trajectory
  }

Layer 3: Full codebase report (end of all episodes)
  state() returns the entire annotated graph
  Serialize to:
  - JSON (machine readable)
  - Markdown report (human readable)
  - Visual graph (NetworkX → graphviz or mermaid)
```

**Updating reviews as agent learns more** is the elegant part. Because reviews are stored on graph nodes, when the agent later reviews module B and discovers the root cause was actually in module A, it can call:

```
AMEND_REVIEW(module_id="auth.py", note="root cause of checkout.py null issue")
```

This updates the node annotation retroactively. The reward for this action is high — it's exactly the cascading reasoning you want to incentivize.

---

## 3. ✅ Does This Align With Round 1 Requirements?

Let's go requirement by requirement:

| Requirement | Your Design | Status |
|---|---|---|
| Real-world task | Code review with dependency reasoning | ✅ Strong |
| step() / reset() / state() | Per-module episodes, graph persists in state() | ✅ |
| Typed Pydantic models | Observation = code + summaries, Action = flag/comment/request, Reward = float | ✅ |
| Minimum 3 tasks easy→hard | Easy: style/linter, Medium: logic bug with direct dep context, Hard: cascading bug across 2+ modules | ✅ |
| Reward 0.0–1.0 with partial signal | Per-step rewards for each correct flag/comment/attribution | ✅ |
| Deterministic graders | Easy/medium use AST+linter ground truth, hard uses fixed-seed LLM judge | ✅ with care |
| Baseline inference script | Agent reviews all 3 task codebases, emits [START]/[STEP]/[END] logs | ✅ |
| Dockerfile + HF Space | Standard containerization | ✅ |
| openenv.yaml + validate | Standard spec compliance | ✅ |

One gap to watch: **the hard task grader quasi-determinism**. Document your judge prompt and temperature=0 explicitly in README to satisfy the reproducibility requirement.

---

## 4. 🤖 Where Is The RL? Where Is OpenEnv?

This is the most important question to be clear on — because judges WILL ask.

### The RL Loop

```
Environment (your code)          Agent (Gemma 4 / any LLM)
─────────────────────────        ──────────────────────────
reset()                    →     receives initial observation
                                 (module code + graph context)

                           ←     action: FLAG_BUG

step(FLAG_BUG)             →     returns:
                                 - new observation (updated graph)
                                 - reward (+0.5 if real bug)
                                 - done (False)
                                 - info {}

                           ←     action: ADD_COMMENT("null risk line 12")

step(ADD_COMMENT(...))     →     reward (+0.3 if accurate)

                           ←     action: REQUEST_CHANGES

step(REQUEST_CHANGES)      →     reward (+0.2 episode bonus)
                                 done = True

state()                    →     full annotated graph so far
```

The **RL part** is: the agent is learning a *policy* — which actions to take given a code observation and graph context — to maximize cumulative reward. It's not just calling an LLM once. It's a multi-step decision loop.

### Where OpenEnv Fits

```
openenv.yaml
  name: code-review-env
  version: 1.0.0
  tasks: [style_review, logic_review, cascading_review]

environment.py
  class CodeReviewEnv:
    observation: CodeObservation    ← Pydantic model
    action: ReviewAction            ← Pydantic model  
    reward: ReviewReward            ← Pydantic model

    def reset() → CodeObservation
    def step(action) → (obs, reward, done, info)
    def state() → GraphState

graders/
  easy_grader.py    ← linter diff check
  medium_grader.py  ← AST + line attribution check
  hard_grader.py    ← LLM judge, fixed seed

inference.py        ← runs Gemma 4 as the agent
  [START] task=cascading_review
  [STEP]  action=FLAG_DEPENDENCY_ISSUE reward=0.5
  [STEP]  action=ADD_COMMENT reward=0.3
  [END]   total_reward=0.8
```

OpenEnv is the **standardized wrapper** that makes your environment pluggable — any agent, any model, can be dropped in and evaluated against your graders. That's the whole point of the spec.

---

## The One-Line Pitch to Judges

> *"An RL environment where an agent learns to review code with full dependency awareness — outputting an annotated codebase graph, not just PR comments. It teaches agents to reason about WHY a bug exists, not just WHERE."*

That's differentiated from CodeRabbit, aligned with all Round 1 requirements, and has a clear RL loop.

**Ready to build the file skeleton now?**


What I basically want is there should be RL in this project meaning it will first see and find out issues about the code and then there should be a review of the bug reported and if the bug is correctly reported there should be reward or else punishment and based on that the actual model should learn and understand this should be integrated into it.

Also right now we have an issue where all the modules are not linked properly. And it's not just about imports but also where they are being called or run and this linking is not proper and causes isolated modules. And also for large modules it's broken into many things. Also Right now I suspect that the LLM is not grading properly the code it's just passing through it and just repeating the errors from the previous the hard filter should also catch errors and find issues and give detailed reports on all in clear tasks. Give it a super detailed agent prompt for this task and the format for output also ensuring it is adaptable. And after the errors being found it should then again verify those errors with another model which the user can define and then it will learn from it and become RL. Assign proper grades for the machine learning to be good for this particular task. Also the arrow marks in the graph are too thick sometimes and when I hover over them they give me a big like of text rather than a well formatted overlay where it gives me info about the modules and also when I click on the module it should show in the side bar the report for it well formatted