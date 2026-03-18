# FORGE v0.2 — Overview & Vision

> **Forge: An Open-Source Harness for Frontier/Local Model Orchestration in Software Engineering**
> *Measuring and optimizing the moving boundary between local and frontier AI*

**Status:** v0.2 — Synthesized from lateral review
**Date:** 2026-03-18
**Author:** Craig @ a8ra / SlimWojak
**Reviewers:** COO (Opus 4.6, a8ra-m3), GPT (GPT-5.3), Gemini (gemini-3.1-pro-preview)

---

## What Changed from v0.1

This section exists so both humans and agents can quickly diff mental models.

| # | Change | Source | Status |
|---|--------|--------|--------|
| 1 | **Boundary measurement elevated from metric to core feature.** `forge boundary` is a first-class command. Dashboard headline is frontier/local delta, not task completion. | COO Q11 | DECIDED |
| 2 | **Gate engine reframed as a trust system.** Worker identity is first-class. Phase 1 is simple (one reviewer + escalate on fail). Full trust × blast-radius 2D matrix is the design target. | COO Q1, Gemini Angle B | DECIDED |
| 3 | **Desloppify split into two architecturally distinct systems.** Mechanical detection (tree-sitter) runs continuously via hooks. LLM subjective review runs at milestone gates. | COO Q4 | DECIDED |
| 4 | **Skill persistence redesigned as a downward-crystallization pipeline.** Observation → Prompt → YAML → Linter rule → LoRA weight. Environment learning compounds before model adaptation. | COO Q5, Gemini Q5 | DECIDED |
| 5 | **Shadow mode before merge authority.** Phase 1 proposes commits; human is final merger. Trust data accumulates before automation. | GPT Additive D | DECIDED |
| 6 | **Error taxonomy and benchmark cartridges from day one.** Failures tagged by type. 20–50 fixed benchmark tasks for controlled comparison. | GPT Additives C, F | DECIDED |
| 7 | **Oracle is text-first, extensible, and custom tree-sitter.** Two-tier structure (Core + Annexes). Visual/multimodal is an extension point, not Phase 1. No RepoPrompt dependency. | GPT Q2, COO Q10, Gemini Angle A | DECIDED |
| 8 | **Board of Directors simplified for Phase 1.** One reviewer + escalation on fail. Full board (independent reviewers + chairman synthesis) is Phase 2+. | GPT Q1, Q8 | DECIDED |
| 9 | **Fresh context for workers is an architectural axiom.** Long context (1M) is for planners only. Workers get clean, bounded context per task. Not tunable. | COO Q9, GPT Q9 | DECIDED |
| 10 | **Grok is Intelligence, not a Reviewer.** Distinct role for community/web research. Not in the code review critical path. | COO Q8 | DECIDED |
| 11 | **Independent DGX Sparks.** Linked topology is Phase X only. | COO Q6, GPT Q6, Gemini Q6 | DECIDED |
| 12 | **Human is sovereign, not a checkpoint.** High visibility, low mandatory intervention. Anomaly-driven paging. `forge intervene` at any point. | COO Q7, Gemini Q7 | DECIDED |
| 13 | **GPT's additive builds absorbed.** Difficulty classifier, recovery mode, shadow mode, research vs. delivery mission classes — all incorporated. | GPT Additives A–F | DECIDED |
| 14 | **Build path made explicit.** Phase 0 → Phase 1 (Factory.ai) → Phase 1.5 (Bootstrap) → Phase 2+ (Claw builder with self-review). | New | DECIDED |

---

## 1. What Is FORGE?

FORGE is an open-source, CLI-first agentic harness that orchestrates **both local and frontier LLMs** to build software. It is not a coding agent. It is the environment, constraints, feedback loops, and orchestration logic that turn models into a functioning engineering team.

FORGE exists to answer a question empirically:

> **What is the optimal orchestration between frontier and local models for software engineering, and how does that boundary move over time?**

It treats the frontier/local split as a first-class design concern and a first-class measurement target. The boundary is not a limitation to work around — it is the thing FORGE measures, optimizes, and learns from.

**FORGE is not:**
- A Factory.ai competitor. Factory uses frontier models end-to-end with massive compute. FORGE explores the frontier/local boundary.
- A claim that local replaces frontier. It is an instrument for measuring where each excels.
- Production-ready from day one. It is a learning harness. Quality comes through iteration.
- Model-specific. Models are swappable. The harness, tools, and orchestration logic are the stable layer.
- A solo project forever. Designed as open-source from the start, structured for community contribution.

---

## 2. Thesis

### The Harness Is Everything

The model is the reasoning engine. The harness is the context, the constraints, the feedback loops, and the structured knowledge that turns raw capability into consistent output.

This is now proven at scale:
- **SWE-agent** showed that the same model (GPT-4) goes from 3.97% to 12.47% task resolution by improving the Agent-Computer Interface — a 64% improvement from harness alone.
- **Anthropic** proved that multi-session autonomy requires an initializer agent, immutable feature lists, clean-state handoffs, and browser-level E2E testing — not better prompts.
- **OpenAI's Codex** demonstrated that a repo with zero human-written code can reach 1M lines through mechanical architecture enforcement, progressive disclosure, and agent-readable observability.
- **Factory.ai Missions** showed that long-horizon autonomy (up to 16 days) works when you decompose into milestones, give each worker fresh context, and validate at every checkpoint.

### The Frontier/Local Synergy Hypothesis

Local models are not frontier models. They are weaker at complex reasoning, less reliable at multi-step instruction following, and more prone to drift. But they are:
- **Free per token** after hardware investment
- **Private** — no data leaves your machine
- **Fine-tunable** on your specific codebase patterns
- **Fast** for iteration loops (no API latency, no rate limits)
- **Improving rapidly** — Qwen 3.5's 35B now outperforms Qwen 3's 235B; Nemotron 3 Super runs 120B/12B-active with a 1M token context window

**The hypothesis:** delegate volume work (coding, iteration, lint fixes, test writing) to local models, and judgment work (architectural review, go/no-go gates, re-scoping) to frontier models. This is cost-optimal because coding loops are token-heavy but judgment-light, while review is token-light but reasoning-heavy.

### The Learning Objective

FORGE is explicitly a learning project. Its purpose is to:
1. Build practical harness engineering intuition through doing, not reading
2. Measure the frontier/local boundary empirically across task types
3. Contribute to the open-source agentic harness conversation with data and patterns
4. Create a platform for experimenting with orchestration strategies as local models improve
5. Explore how LoRA fine-tuning on accumulated task data can compound local model capability over time

---

## 3. Foundational Influences

### SWE-Agent & the Agent-Computer Interface (ACI)

The ACI is the abstraction layer between the model and the computer, designed for how LLMs process information — not how humans do. Key principles FORGE inherits:

- **Bounded tool outputs** — search returns max 50 results, file viewer shows 100 lines with position tracking. Prevents context flooding.
- **Stateful file navigation** — the viewer remembers position across interactions. No re-reading from scratch.
- **Edit with immediate linting** — syntax check runs BEFORE applying edits. Errors return instantly, closing the feedback loop.
- **Context compression** — older observations collapse into summaries. Keeps the working window focused.

**FORGE adaptation:** Tools must be even simpler and more bounded for local models. Fewer choices per step, harder guardrails, structured outputs enforced mechanically.

### Anthropic's Two-Agent Pattern

- **Initializer agent** (one-time, high intelligence) creates the environment: startup script, comprehensive feature list as JSON, progress tracking, initial git commit.
- **Coding agent** (every session) reads progress, runs init, implements features, verifies, commits.
- **Immutable success criteria** — agents cannot delete or modify tests. Must fix code, not change what "passing" means.
- **Clean state requirement** — every session ends with all tests passing and a clean git commit. Context exhaustion triggers rollback to last clean state.

**FORGE adaptation:** The initializer can be a frontier model (Opus/GPT) since it runs once. Workers are local. The immutable feature list and clean-state contract translate directly.

### Factory.ai Missions

- **Milestone decomposition** — large projects broken into milestones, each ending with a validation phase.
- **Fresh worker sessions** — each feature gets clean context. No single session holds the entire project.
- **Skill-based learning** — the system captures reusable patterns and gets better at your domain over time.
- **Multi-model orchestration** — different models assigned to different roles (planning, coding, validation, research).
- **Computer use for validation** — workers launch the app, navigate flows, check rendering, catch visual bugs.

**FORGE adaptation:** Sequential milestones with bounded parallelism (matching DGX Spark's single-GPU reality). The skill system becomes fine-tuning data. Computer use via local Playwright for validation.

### Desloppify (Now Two Systems)

**v0.1 treated Desloppify as a single system. v0.2 splits it. This is DECIDED.**

**System 1 — Mechanical Detection (continuous, zero GPU cost):**
- Tree-sitter AST analysis: dead code, duplication, cyclomatic complexity
- Runs as git hooks on every commit
- Produces structured reports: file, line, category, severity
- No model inference required — purely mechanical

**System 2 — LLM Subjective Review (milestone-gated, model-dependent):**
- Naming quality, abstraction boundaries, module cohesion, pattern consistency
- Runs at milestone boundaries and on `forge quality` manual trigger
- Requires model inference — scheduled when GPU is not serving workers
- Produces a quality delta score that feeds into gate decisions

These are architecturally distinct subsystems with different trigger conditions, different compute profiles, and different output schemas. They share a unified reporting interface but do not share scheduling logic.

**Source:** COO Q4 identified the conflation. GPT Q4 confirmed milestone timing for subjective review.

### The Forge Oracle (Custom Tree-Sitter Pipeline)

**v0.1 described Oracle as a concept. v0.2 specifies its architecture. This is DECIDED.**

The Oracle is the structured snapshot that mediates between local workers and frontier reviewers. Frontier models never see the full codebase — they see the Oracle. This keeps frontier costs bounded and predictable.

**Two-tier structure:**

**Tier 1 — Core Oracle (default, sent to all reviewers):**
- Diff summary (files changed, lines added/removed, function signatures touched)
- Codemap of affected modules (tree-sitter structural summary, ~10x token savings vs. raw source)
- Mechanical check results (lint, type-check, test pass/fail, Desloppify mechanical score)
- Task context (original task description, worker self-assessment, iteration count)
- Target token budget: 2–4K tokens

**Tier 2 — Expandable Annexes (reviewers pull when needed):**
- Full patch content
- Selective file excerpts (e.g., full function body when signature change is ambiguous)
- Related test output (full stack traces, coverage diffs)
- Prior verdict chain (previous reviewer feedback on this task)
- Accessible via structured tool calls from reviewers, not auto-included

**Key decisions:**
- Oracle pipeline is custom tree-sitter, not RepoPrompt-dependent. RepoPrompt may be an optional alternative backend but is never on the critical path.
- Visual/multimodal Oracle sections (screenshots, flame graphs) are an extension point for Phase 2+. Phase 1 is text-only.
- Oracle density self-optimizes over time: track which sections reviewers reference in verdicts, weight accordingly. (COO Q2)

**Source:** COO Q2 (feedback loop), COO Q10 (own the pipeline), GPT Q2 (two-tier), Gemini Angle A (multimodal as extension).

---

## 4. Boundary Measurement — FORGE's Core Feature

**This is DECIDED. Boundary measurement is a core feature, not a metric.**

Every agentic coding tool measures task completion. FORGE's unique position is that it measures the **frontier/local boundary empirically, per task type, over time**. If FORGE ships without making this measurement trivially easy, it is just another agentic harness.

### `forge boundary` — First-Class Command

`forge boundary` displays the current state of the frontier/local split:

```
$ forge boundary

FORGE Boundary Report — Project: claw-api
Period: last 7 days | 47 tasks completed

LOCAL FIRST-PASS SUCCESS:     28/47 (59.6%)
FRONTIER CORRECTION NEEDED:   19/47 (40.4%)
AVG ITERATIONS (local only):  1.3
AVG ITERATIONS (with fix):    2.8

BY TASK TYPE:
  mechanical      12/12 (100%)  — LOCAL SUFFICIENT
  local-reasoning 11/15 (73%)   — BOUNDARY ZONE
  architectural    5/14 (36%)   — FRONTIER DEPENDENT
  uncertain        0/6  (0%)    — FRONTIER REQUIRED

BOUNDARY MOVEMENT (30-day trend):
  mechanical:       100% → 100% (stable)
  local-reasoning:   58% →  73% (+15%, LoRA v2 deployed day 12)
  architectural:     29% →  36% (+7%, skill crystallization)

TOP FRONTIER CORRECTIONS:
  1. Missing error boundary in auth flow (architectural)
  2. Incorrect transaction isolation level (local-reasoning)
  3. Test coverage gap in edge case (local-reasoning)
```

### Research vs. Delivery Mission Modes

**DECIDED.** Two explicit mission classes:

- **Delivery missions:** Optimize for successful software completion. Metrics: task completion rate, wall-clock time, cost per feature.
- **Research missions:** Optimize for learning about orchestration, routing, gate design, or model capability. Metrics: boundary movement data, error taxonomy coverage, model comparison data.

This keeps the metrics honest. A research mission that deliberately routes tasks to a weaker model to gather comparison data should not penalize delivery metrics.

**Source:** GPT Additive E.

### What Gets Measured

Every task execution records:
- **Task difficulty class:** mechanical / local-reasoning / architectural / uncertain (classified before execution)
- **Worker identity:** which model, which LoRA version, which serving config
- **First-pass result:** PASS or FAIL at each gate
- **Iteration count:** how many worker loops before pass
- **Frontier intervention type:** what the reviewer caught (maps to error taxonomy)
- **Cost:** local compute time + frontier API tokens
- **Oracle utilization:** which Oracle sections the reviewer referenced

This data is the raw material for boundary analysis. It accumulates automatically. No manual tagging required beyond the initial difficulty classification, which itself becomes a learnable function over time.

---

## 5. The Gate Engine — A Trust System

**This is DECIDED. The gate engine is a trust system, not a review scheduler.**

### Phase 1 — Simple Trust (DECIDED)

Phase 1 starts minimal:

```
Worker completes task
  → Mechanical checks (lint, typecheck, tests, Desloppify mechanical)
  → Oracle generation
  → Single frontier reviewer
  → If PASS: propose commit (human merges in shadow mode)
  → If FAIL: worker receives structured TODO, iterates
  → If FAIL ×2: escalate to second reviewer
  → If FAIL ×3: enter recovery mode (see §5.2)
```

One reviewer. Escalation on fail. No chairman synthesis. This is sufficient to collect trust data.

### Phase 2+ — Trust × Blast-Radius Matrix (DECIDED design target)

The full gate engine is a 2D routing matrix:

```
                    BLAST RADIUS
                    Low              High
              ┌─────────────────┬─────────────────┐
    High      │ Auto-merge      │ Single reviewer  │
              │ Mechanical       │ + mechanical     │
    TRUST     │ checks only     │ checks           │
              ├─────────────────┼─────────────────┤
    Low       │ Single reviewer │ Full board       │
              │ + mechanical    │ review           │
              │ checks          │ (independent     │
              │                 │ reviewers +      │
              │                 │ chairman)        │
              └─────────────────┴─────────────────┘
```

**Trust** is computed from: worker identity, task type, recent first-pass rate for this worker on this task type, LoRA version. Trust increases with consecutive successes and resets on certain failure types.

**Blast radius** is computed mechanically before execution: AST impact analysis (which modules touched, dependency depth), file sensitivity classification (auth, payments, config = high; UI, docs, tests = low), and diff size.

**Worker identity is first-class.** The gate engine does not ask "did this task pass?" — it asks "did *this worker* pass *this type of task*?" A fine-tuned model with 200 successful auth-endpoint tasks gets different scrutiny than a base model on its first attempt.

**Source:** COO Q1 (trust system, worker identity), Gemini Angle B (blast radius routing), Gemini Angle D (auto-demotion).

### Difficulty Classifier

**DECIDED.** Before execution begins, every task is classified:

| Class | Definition | Default Gate Intensity |
|-------|-----------|----------------------|
| `mechanical` | Lint fix, dependency bump, config wire, type annotation | Mechanical checks only (if trust is high) |
| `local-reasoning` | Implement endpoint, write tests, refactor module, fix bug with clear repro | Single reviewer |
| `architectural` | Cross-module refactor, new abstraction, schema migration, auth flow change | Full board (Phase 2+) or escalated review (Phase 1) |
| `uncertain` | Ambiguous scope, research-dependent, novel pattern | Frontier-assisted planning before execution begins |

The classifier runs at task creation time. Phase 1: human or planner assigns the class. Phase 2+: the classifier itself becomes a learnable function trained on historical task data and outcomes.

**Source:** GPT Additive A.

### Recovery Mode

**DECIDED.** Recovery mode is architecturally distinct from normal iteration.

Normal iteration: worker fails → receives structured TODO → tries again with fresh context.

Recovery mode triggers after N consecutive failures (default N=3):

1. **Generate failure summary** — structured analysis of what was attempted and why it failed, tagged with error taxonomy categories
2. **Escalate to planner/frontier** — the planner (or frontier model) receives the failure summary and decides:
   - **Rewrite task** — the task description was ambiguous or incorrect
   - **Split task** — the task is too complex for a single worker session
   - **Change approach** — different tools, different file ordering, different strategy
   - **Escalate to human** — `forge intervene` notification with full context
3. **Restart from last clean commit** — worker gets fresh context, new task description

Recovery mode prevents thrash loops. It also generates high-value error taxonomy data — repeated failures on a task type reveal harness weaknesses.

**Source:** GPT Additive B.

---

## 6. Error Taxonomy & Benchmark Cartridges

**This is DECIDED. Both are day-one infrastructure, not afterthoughts.**

### Error Taxonomy

Every failure is tagged with one or more categories:

| Tag | Definition | Example |
|-----|-----------|---------|
| `tool-misuse` | Worker used an ACI tool incorrectly | Passed wrong arguments to file editor |
| `navigation-failure` | Worker couldn't find the right file/function | Edited wrong module, missed import |
| `incorrect-logic` | Code compiles but logic is wrong | Off-by-one, wrong comparison operator |
| `missing-tests` | Implementation works but tests are absent or insufficient | No edge case coverage |
| `architectural-drift` | Code violates established patterns or boundaries | Bypassed service layer, direct DB access from handler |
| `context-confusion` | Worker confused files, mixed up variable names, lost track of state | Used stale reference, wrong function signature |
| `flaky-validation` | Test or check is non-deterministic | Race condition in test, timing-dependent assertion |

Tags are applied by the frontier reviewer during gate review. They accumulate in a structured log. `forge taxonomy` displays the distribution. This data tells you what the harness is actually bad at — which is more valuable than knowing the overall pass rate.

### Benchmark Cartridges

A fixed suite of 20–50 representative tasks used for controlled comparison:

**Categories:**
- Add REST endpoint (mechanical)
- Refactor module boundary (architectural)
- Fix failing test from error message (local-reasoning)
- Add E2E test for existing flow (local-reasoning)
- Wire configuration value end-to-end (mechanical)
- Repair type error (mechanical)
- Implement feature from spec (local-reasoning)
- Patch lint violations (mechanical)
- Database schema migration (architectural)
- Add authentication to existing endpoint (architectural)

**Purpose:** When you change any harness variable (new model, new LoRA, new Oracle format, new gate policy), re-run the benchmark suite. Compare apples to apples. Without this, you drown in anecdotal comparisons.

**Format:** Each cartridge is a self-contained directory:
```
benchmarks/
  add-endpoint-01/
    task.yaml          # Task description, difficulty class, expected outcome
    repo-snapshot/     # Git ref or tarball of starting state
    oracle-expected/   # What a correct Oracle should look like (for Oracle quality testing)
    success-criteria/  # Mechanical checks that must pass
```

Benchmark results are stored as structured data and feed into `forge boundary` reporting.

**Source:** GPT Additive F (benchmark cartridges), GPT Additive C (error taxonomy).

---

## 7. The Skill Crystallization Pipeline

**This is DECIDED. Skills crystallize downward into enforcement before upward into weights.**

The pipeline has five tiers. Each tier is independently valuable. The system promotes skills downward (toward harder enforcement) as confidence increases.

```
Tier 0: OBSERVATION
  │  Raw data: "Reviewer caught missing rate-limit on auth endpoint"
  │  Lifetime: single event
  │  Cost: zero (logging)
  │
  ▼
Tier 1: PROMPT SKILL
  │  Injected into worker system prompt: "All auth endpoints require rate limiting"
  │  Lifetime: session to days
  │  Cost: tokens (prompt overhead)
  │  Trigger: manual or after N observations of same pattern
  │
  ▼
Tier 2: YAML PATTERN
  │  Stored in .forge/skills/: structured rule with examples and counter-examples
  │  Lifetime: weeks to months
  │  Cost: tokens (loaded into context when relevant files are touched)
  │  Trigger: prompt skill validated across M successful applications
  │
  ▼
Tier 3: ARCHITECTURAL LINTER RULE
  │  Tree-sitter AST rule in .forge/lint/: mechanically enforced, zero inference cost
  │  Lifetime: months to permanent
  │  Cost: zero (AST check)
  │  Trigger: YAML pattern stable enough to express as structural invariant
  │  Example: "Function in auth/ must call rate_limit() — AST check for call presence"
  │
  ▼
Tier 4: LoRA WEIGHT
  │  Baked into model weights via fine-tuning on accumulated successful examples
  │  Lifetime: permanent (until model swap)
  │  Cost: zero at inference (already in weights)
  │  Trigger: sufficient training data accumulated from Tiers 0–3
```

**Key principle:** Environment learning compounds before model adaptation. Tiers 1–3 improve the harness. Tier 4 improves the model. Most value comes from Tiers 2–3 because they are durable, debuggable, and model-independent. LoRA is the final crystallization, not the first goal.

**Gemini's addition (absorbed):** Tier 3 can also include generated tests — a skill that solidifies into an executable test is even stronger than a linter rule because it validates behavior, not just structure.

**Source:** COO Q5 (three-tier crystallization), GPT Q5 (YAML for v1), Gemini Q5 (executable invariants).

---

## 8. The Orchestration Model

### Board of Directors — Phase 1 (Simplified)

**DECIDED.** Phase 1 uses a simplified governance model. Full board is Phase 2+.

```
┌─────────────────────────────────────────────────────────┐
│                    HUMAN SOVEREIGN                       │
│  Sees everything. Required only at: mission approval,   │
│  milestone sign-off, anomaly pages. `forge intervene`   │
│  available at any point. Final merger in shadow mode.    │
└──────────────────────────┬──────────────────────────────┘
                           │ Daily digest + anomaly pages
┌──────────────────────────┴──────────────────────────────┐
│              PLANNER (frontier or local big-brain)       │
│  Decomposes mission → milestones → tasks.               │
│  Uses long context (1M) to hold full codemap +          │
│  all prior Oracles + feature list.                      │
│  Classifies task difficulty. Writes task specs.          │
└──────────────────────────┬──────────────────────────────┘
                           │ Task spec + difficulty class
┌──────────────────────────┴──────────────────────────────┐
│              WORKER (local model)                        │
│  Codes in isolated git worktree. Fresh context per      │
│  task (AXIOM — not tunable). Uses bounded ACI tools.    │
│  Iterates until mechanical checks pass, then submits.   │
└──────────────────────────┬──────────────────────────────┘
                           │ Oracle (structured snapshot)
┌──────────────────────────┴──────────────────────────────┐
│              REVIEWER (single frontier model, Phase 1)  │
│  Reviews Core Oracle. Pulls Annexes when needed.        │
│  Verdict: PASS or FAIL + structured TODO.               │
│  On FAIL ×2: second reviewer activated.                 │
│  On FAIL ×3: recovery mode.                             │
└──────────────────────────┬──────────────────────────────┘
                           │ Verdict
┌──────────────────────────┴──────────────────────────────┐
│              INTELLIGENCE (Grok — optional)              │
│  Not in the review critical path.                       │
│  Queries: dependency vulnerabilities, community          │
│  consensus, API pattern issues, library status.          │
│  Invoked by planner or reviewer, not per-task.           │
└─────────────────────────────────────────────────────────┘
```

### Board of Directors — Phase 2+ (Full)

```
┌─────────────────────────────────────────────────────────┐
│                  CHAIRMAN (Opus)                         │
│  Synthesizes reviewer findings. Makes go/no-go.         │
│  Rewrites TODOs with precision. Only activated when     │
│  reviewers disagree or task is architectural.            │
└──────────────────────────┬──────────────────────────────┘
                           │ Structured verdict
              ┌────────────┴────────────┐
              │                         │
┌─────────────┴──────────┐  ┌──────────┴──────────────┐
│  REVIEWER A (Sonnet)   │  │  REVIEWER B (Codex)     │
│  Architectural          │  │  Correctness & test     │
│  coherence, design      │  │  coverage analysis      │
│  patterns, naming       │  │                         │
└────────────────────────┘  └─────────────────────────┘
```

Independent reviewers reduce blind spots — different training distributions catch different failure modes. The Chairman synthesizes, doesn't just aggregate. Phase 2+ activates this for `architectural` tasks and any task where the single Phase 1 reviewer is uncertain.

### Flow Per Task (Phase 1)

1. **Planner** decomposes mission into milestones and tasks, assigns difficulty class
2. **Worker** (local, fresh context) codes in isolated git worktree using bounded ACI tools
3. After task completion, **Oracle Generator** (mechanical + local) creates structured snapshot
4. **Reviewer** (single frontier) assesses Core Oracle, pulls Annexes if needed
5. If PASS → propose commit (human merges in shadow mode)
6. If FAIL → worker receives structured TODO with error taxonomy tag, iterates with fresh context
7. If FAIL ×2 → escalate to second reviewer
8. If FAIL ×3 → recovery mode (escalate to planner, rewrite/split task, or page human)
9. At milestone boundaries → Desloppify LLM subjective scan + E2E validation

### Why This Works

- **Local does the volume** — coding iteration is token-heavy, latency-sensitive, and can be low-judgment. Perfect for local.
- **Frontier does the judgment** — review is token-light (Oracle, not full codebase) but reasoning-heavy. Perfect for frontier.
- **Cost scales with decisions, not keystrokes** — you pay frontier prices for judgment, not for typing.
- **Shadow mode builds trust data** — every human merge decision is a training signal for the gate engine.
- **Fresh context prevents drift** — workers never accumulate stale state. Every task is a clean start.

---

## 9. Human Sovereignty

**This is DECIDED. The human is sovereign, not a checkpoint.**

### Design Principle

High visibility. Low mandatory intervention. The system is designed so the human sees everything but is only required at explicit moments. Do not add mandatory checkpoints that train the human to rubber-stamp.

### Visibility Layer

- **Daily digest** — summary of tasks completed, boundary data, error taxonomy distribution, anomalies
- **`forge status`** — real-time view of current mission progress, active workers, pending reviews
- **`forge boundary`** — frontier/local split data (see §4)
- **`forge taxonomy`** — error distribution and trends
- **Full trace logs** — every worker session, every Oracle, every reviewer verdict is stored and browsable

### Intervention Points

- **`forge intervene`** — available at any time, pauses current execution, opens interactive session
- **Mission approval** — human approves mission plan before execution begins
- **Milestone sign-off** — human reviews milestone completion before advancing (Phase 1; becomes optional in Phase 2+ for trusted task types)
- **Shadow mode merge** — human is the final merger for all commits (Phase 1)

### Anomaly-Driven Paging

The system pages the human (notification, not blocking gate) when:
- Worker loops > 3 times on the same task (entering recovery mode)
- Desloppify score drops by > 10 points in one commit
- Frontier reviewers disagree (Phase 2+ with multiple reviewers)
- Benchmark regression detected
- Cost anomaly (frontier spend exceeds expected budget for task type)

Outside these anomalies, the system runs autonomously. The human reads the daily digest and intervenes when they choose to, not when the system demands it.

**Source:** COO Q7 (sovereign, not checkpoint), Gemini Q7 (anomaly-driven paging).

---

## 10. Hardware Context

FORGE is designed to run on serious local hardware:

| Machine | Role in FORGE | Specs |
|---------|---------------|-------|
| DGX Spark #1 | Primary model server (big brain) | GB10 Blackwell, 128GB unified, 1 PFLOP FP4, NVLink-C2C |
| DGX Spark #2 | Secondary model server (fast hands) or fine-tuning | Same as above; ConnectX-7 for inter-Spark linking |
| M3 Ultra | Oracle generation, development, Desloppify mechanical | 512GB unified, 192GB/s bandwidth |
| M4 Studio | Test runner, secondary worker, experimentation | TBD specs |

**DGX Spark topology: DECIDED — Independent.** Each Spark runs its own model server. No linked memory in Phase 1–2. Linked topology is Phase X, only if a concrete workload (e.g., serving a single model larger than 128GB at acceptable precision) proves it necessary.

**Source:** COO Q6, GPT Q6, Gemini Q6 — unanimous.

### Model Deployment Strategy

| Role | Model (current candidates) | Hardware | Serving |
|------|---------------------------|----------|---------|
| Local Planner (big brain) | Nemotron 3 Super 120B-A12B or Qwen 3.5-35B | DGX Spark #1 | vLLM (FP4 native) |
| Local Worker (fast hands) | Qwen 3.5-35B or Nemotron 3 Nano 30B-A3B | DGX Spark #2 | vLLM or llama.cpp |
| Frontier Reviewer (Phase 1) | Sonnet 4.6 or GPT-5.3 Codex | API | — |
| Frontier Chairman (Phase 2+) | Opus 4.6 | API | — |
| Intelligence (optional) | Grok | API | — |
| Quality Reviewer (Desloppify LLM) | Local model on DGX Spark #1 | DGX Spark #1 | vLLM |

**Note:** Model assignments are experimental and will evolve. A core purpose of FORGE is to measure which model performs best in which role. The benchmark cartridge system (§6) exists specifically to make these comparisons rigorous.

---

## 11. Fresh Context Axiom

**This is DECIDED. This is an architectural axiom, not a tunable parameter.**

```
AXIOM: Workers get clean, bounded context per task.
       Long context (1M) is for planners only.
```

**Rationale:**
- Fresh-context-per-task is one of the strongest patterns across all foundational influences (Anthropic's clean-state requirement, Factory.ai's fresh worker sessions).
- Long context is useful for *reading* (understanding a codebase) but harmful for *writing* (accumulated context creates drift, earlier errors compound, attention degrades).
- The 1M window is an asset for the **planner** role — a planner that can ingest the full codebase codemap + all previous Oracle snapshots + the full feature list to plan the next milestone. That is where long context earns its keep.

**What this means for implementation:**
- Worker sessions are stateless between tasks. No carry-over of prior conversation.
- Worker context contains only: task spec, relevant file contents (bounded), ACI tool definitions, active skills (Tier 1–2).
- Planner context contains: full codemap, mission plan, all prior Oracles for current milestone, feature list, boundary data.
- If a worker needs information from a prior task, it must be in the Oracle chain or the skill system — not in residual context.

**Source:** COO Q9, GPT Q9 — unanimous and emphatic.

---

## 12. Shadow Mode

**This is DECIDED. Phase 1 operates entirely in shadow mode.**

Shadow mode means:
- FORGE executes end-to-end autonomously (plan → code → review → verdict)
- FORGE proposes commits with full context (Oracle, reviewer verdict, diff)
- **Human is the final merger every time**
- Every human merge/reject decision is logged as a training signal

Shadow mode serves two purposes:
1. **Safety** — no autonomous repo modification until trust is established
2. **Calibration** — human merge decisions generate ground-truth data for the gate engine

**Graduation from shadow mode** is a Phase 2+ decision based on accumulated trust data. The criteria are:
- Minimum N tasks completed in shadow mode (suggested: 100+)
- Human override rate below threshold (suggested: < 5%)
- No category of task showing systematic human rejection
- Human explicitly enables auto-merge for specific task types / trust levels

**Source:** GPT Additive D.

---

## 13. FORGE's Build Path

**This is DECIDED.**

```
Phase 0: P + Craig
  │  CLI skeleton, model serving validation, 5 ACI tools,
  │  one local worker, one frontier reviewer, Oracle v0,
  │  benchmark cartridge v0, error taxonomy schema
  │
Phase 1: Factory.ai Mission
  │  Factory.ai Droid builds FORGE's core systems using
  │  this document as the mission spec. Mission decomposition,
  │  worktree isolation, milestone validation, skill capture,
  │  gate engine v1, boundary measurement, shadow mode.
  │
Phase 1.5: Bootstrap — FORGE Reviews Itself
  │  FORGE's own gate engine reviews PRs to the FORGE repo.
  │  Desloppify runs on FORGE's own codebase.
  │  Dogfooding validates the harness architecture.
  │
Phase 2+: Claw Builder with FORGE Self-Review
  │  FORGE builds the Claw project (or other real software)
  │  while simultaneously reviewing its own changes.
  │  Full board activated. Trust × blast-radius matrix.
  │  Auto-merge for trusted task types.
  │
Ongoing: Lateral Reviews via P / Opus / GPT
  │  Periodic architecture reviews of FORGE itself by
  │  frontier models, producing v0.3, v0.4, etc.
```

### Phase 0 Deliverables (Minimum Viable Loop)

1. `forge task <description>` — submit a single task to a local worker
2. `forge review` — generate Oracle, send to single frontier reviewer, display verdict
3. `forge boundary` — display frontier/local split data from accumulated task results
4. `forge status` — show current task state
5. Benchmark cartridge runner — execute a cartridge, record results
6. Error taxonomy logger — tag failures, store structured data
7. Mechanical Desloppify hooks — tree-sitter checks on commit

**This is the minimum viable loop. Everything else is downstream.**

**Source:** GPT recommended build sequence (Weekend 1–3), adapted to FORGE's specific context.

---

## 14. Success Metrics

FORGE succeeds if it produces:

1. **Empirical boundary data** — frontier/local task completion rates, iteration counts, cost splits, and error taxonomy distributions across task types, published and reproducible via benchmark cartridges
2. **A reusable harness** that others can install, configure with their own models, and run
3. **Published learnings** about harness design patterns that work (and don't work) with local models
4. **A skill crystallization pipeline** that demonstrably compounds — patterns move from prompt to YAML to linter rule, measurably reducing frontier correction rates
5. **A fine-tuning pipeline** (Phase 4) that demonstrably improves local model performance on codebase-specific tasks over time
6. **A personal deepening** of harness engineering intuition through sustained practice

The dashboard headline is **frontier/local delta**, not task completion rate. The question is not "did we finish?" but "how much frontier judgment did we need, and is that number going down?"

---

## 15. Open Questions (Updated)

v0.1 had 10 open questions. The lateral review resolved most of them. This section retains questions that are genuinely open and adds new ones that emerged from synthesis.

### RESOLVED from v0.1

| v0.1 # | Question | Resolution | Source |
|---------|----------|-----------|--------|
| Q1 | Gate granularity | Trust system with worker identity. Phase 1: one reviewer + escalate. Phase 2+: trust × blast-radius matrix. | COO, Gemini |
| Q4 | Desloppify timing | Mechanical: continuous. Subjective: milestone-gated. | COO |
| Q5 | Skill persistence format | Five-tier crystallization pipeline (Observation → Prompt → YAML → Linter → LoRA). | COO, GPT, Gemini |
| Q6 | Multi-Spark topology | Independent. Linked is Phase X. | Unanimous |
| Q7 | Human checkpoint frequency | Sovereign, not checkpoint. Anomaly-driven paging. | COO, Gemini |
| Q8 | Frontier model selection | One reviewer Phase 1. Grok as Intelligence, not reviewer. Full board Phase 2+. | COO, GPT |
| Q9 | Context window management | Fresh context axiom for workers. Long context for planners only. | COO, GPT |
| Q10 | RepoPrompt dependency | Custom tree-sitter. RepoPrompt as optional backend. | COO, GPT |

### PARTIALLY RESOLVED from v0.1

| v0.1 # | Question | Current State | Remaining Uncertainty |
|---------|----------|--------------|----------------------|
| Q2 | Oracle density | Two-tier structure decided. Core Oracle target: 2–4K tokens. | Optimal density per task type is empirical. Reviewer feedback loop designed but unvalidated. |
| Q3 | Local model routing | Start with one worker model. Planner escalation optional. | Planning-vs-coding split for local models is an empirical question FORGE should answer, not pre-commit. |

### NEW Open Questions (v0.2)

**Q11: Difficulty classifier implementation.** DECIDED that tasks are classified before execution (mechanical / local-reasoning / architectural / uncertain). OPEN: what classifies them? Phase 1 is human/planner assignment. When does this become automated? What training data is needed? What's the cost of misclassification (e.g., routing an architectural task as mechanical)?

**Q12: Trust function shape.** DECIDED that trust is a function of worker identity, task type, and recent performance. OPEN: what is the mathematical shape? Linear accumulation? Exponential decay on failure? How many consecutive successes to promote? How many failures to demote? This needs empirical calibration.

**Q13: Oracle feedback loop mechanics.** DECIDED that Oracle density should self-optimize based on reviewer behavior. OPEN: how exactly? Track which annexes are pulled? Measure correlation between Oracle sections referenced and verdict quality? What's the feedback cycle — weekly? Per-milestone? This is a Phase 2 design problem.

**Q14: Benchmark cartridge coverage.** DECIDED that 20–50 fixed tasks exist. OPEN: what's the right distribution across difficulty classes? How do you avoid benchmarks becoming stale as the codebase evolves? Should cartridges be project-specific or generic?

**Q15: Skill promotion criteria.** DECIDED that skills crystallize downward (Prompt → YAML → Linter → LoRA). OPEN: what triggers each promotion? How many successful applications of a YAML pattern before it becomes a linter rule? Who validates that a linter rule is correct (human? frontier?)? What's the rollback mechanism if a promoted skill is wrong?

**Q16: Parallel model racing.** Gemini proposed racing multiple local models on the same task and taking the first to pass. OPEN: is the wall-clock benefit worth the doubled compute? When does racing make sense (high-value tasks only? research missions only?)? Deferred to Phase 2+ experimentation.

**Q17: Auto-demotion of judgment.** Gemini proposed automatically demoting task types to skip frontier review after N consecutive local successes. OPEN: what's the safety margin? How do you detect silent regression (tasks that pass mechanical checks but have subtle architectural drift)? This interacts with the trust function (Q12).

**Q18: Cross-project skill transfer.** OPEN: Can skills learned on Project A transfer to Project B? At which tier? Prompt skills are likely project-specific. YAML patterns might transfer within a language/framework. Linter rules are more portable. LoRA weights are model-specific. This is Phase 3+ research.

---

## Appendix A: Terminology

| Term | Definition |
|------|-----------|
| **ACI** | Agent-Computer Interface. The tool layer between model and environment. |
| **Annex** | Expandable section of the Oracle that reviewers pull on demand. |
| **Benchmark cartridge** | A fixed, reproducible task used for controlled harness comparison. |
| **Blast radius** | Mechanically computed impact scope of a code change (files touched, dependency depth, sensitivity). |
| **Board of Directors** | The full multi-reviewer governance model (Phase 2+): independent reviewers + chairman synthesis. |
| **Boundary** | The empirical frontier/local split — which task types require frontier judgment and which don't. |
| **Chairman** | Frontier model (Opus) that synthesizes multiple reviewer verdicts into a single decision. Phase 2+ only. |
| **Core Oracle** | The default, token-efficient snapshot sent to all reviewers (~2–4K tokens). |
| **Crystallization** | The process of hardening a learned pattern from soft (prompt) to hard (linter rule / weights). |
| **Desloppify** | Quality enforcement system. Two subsystems: mechanical (tree-sitter, continuous) and subjective (LLM, milestone-gated). |
| **Difficulty class** | Task classification: mechanical, local-reasoning, architectural, uncertain. |
| **Error taxonomy** | Structured failure categorization: tool-misuse, navigation-failure, incorrect-logic, missing-tests, architectural-drift, context-confusion, flaky-validation. |
| **Fresh context axiom** | Workers get clean, bounded context per task. Not tunable. |
| **Gate engine** | The trust system that routes tasks to appropriate review intensity. |
| **Intelligence** | The Grok role: web/community research, not code review. |
| **Oracle** | The structured snapshot mediating between local workers and frontier reviewers. |
| **Recovery mode** | Distinct from normal iteration. Triggered after N failures. Escalates, rewrites, or splits the task. |
| **Shadow mode** | FORGE proposes commits; human is final merger. Phase 1 default. |
| **Skill** | A learned pattern at any tier of the crystallization pipeline. |
| **Trust** | Computed confidence in a worker's ability to handle a task type without frontier review. |
| **Worker identity** | First-class tracking of which model, LoRA version, and config produced a given output. |

---

## Appendix B: Decision Log

All decisions marked DECIDED in this document are **locked for Phase 1 implementation.** They may be revisited in v0.3+ based on empirical data, but they are not open for re-litigation during build.

| Decision | Section | Rationale |
|----------|---------|-----------|
| Boundary measurement is a core feature | §4 | COO Q11: without it, FORGE is just another agentic harness |
| Gate engine is a trust system | §5 | COO Q1: review intensity should be a function of trust × blast-radius, not schedule |
| Desloppify splits into two systems | §3 (Desloppify) | COO Q4: mechanical detection is free; conflating it with LLM review is a design error |
| Skills crystallize downward | §7 | COO Q5: environment learning compounds before model adaptation |
| Shadow mode before merge authority | §12 | GPT Additive D: calibration data without ceding repo control |
| Error taxonomy from day one | §6 | GPT Additive C: failure categorization is more valuable than pass/fail rates |
| Benchmark cartridges from day one | §6 | GPT Additive F: without fixed benchmarks, all comparison is anecdotal |
| Oracle is text-first, two-tier, custom tree-sitter | §3 (Oracle) | COO Q10, GPT Q2: own the core pipeline, multimodal is extension |
| Phase 1 board is one reviewer + escalation | §8 | GPT Q1: minimize frontier calls while collecting trust data |
| Fresh context is an axiom | §11 | COO Q9, GPT Q9: strongest pattern across all foundational influences |
| Grok is Intelligence, not Reviewer | §8 | COO Q8: different capability, different use pattern |
| Independent DGX Sparks | §10 | Unanimous: linked topology solves a problem FORGE doesn't have yet |
| Human is sovereign | §9 | COO Q7: high visibility, low mandatory intervention |
| Difficulty classifier before execution | §5.3 | GPT Additive A: not all tasks deserve the same gate pattern |
| Recovery mode distinct from iteration | §5.4 | GPT Additive B: prevents thrash loops |
| Research vs. delivery mission modes | §4 | GPT Additive E: keeps metrics honest |
| Build path: Phase 0 → 1 → 1.5 → 2+ | §13 | Synthesis of GPT build sequence + bootstrap concept |

---

*This document is the spec for FORGE v0.2. It is designed to be read by both humans and AI agents. Decisions marked DECIDED are locked. Questions marked OPEN are active research. Build to the decisions. Experiment on the questions.*
