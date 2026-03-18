# FORGE v0.1 — Phased Build Plan

> **From minimum viable loop to compound learning engine**

**Status:** v0.1 Draft — For lateral review
**Date:** 2026-03-18
**Author:** Craig @ a8ra / SlimWojak

---

## Guiding Principle

Each phase must be independently useful. FORGE is a learning project — every phase should produce usable data and working infrastructure, not scaffolding that only pays off later.

---

## Phase 0: Foundation (Week 1-2)

**Goal:** Establish the repo, tooling, and local model serving infrastructure.

### Deliverables

- [ ] Repository created at `github.com/SlimWojak/forge`
- [ ] Python project structure (Poetry/uv, Click CLI, pytest)
- [ ] `.forge/` directory scaffolding and state schema
- [ ] Local model serving validated on DGX Spark (vLLM or llama.cpp)
  - Confirm Nemotron 3 Nano/Super inference on Spark #1
  - Confirm Qwen 3.5-35B inference on Spark #2
  - Validate tool calling / function calling reliability for each
- [ ] OpenAI-compatible API wrapper (abstracts local vs. frontier behind one interface)
- [ ] Basic `forge init` command that creates project scaffolding
- [ ] Frontier API configuration (Anthropic, OpenAI keys in env vars)

### Learning Outcomes

- How fast do these models actually run on DGX Spark for coding tasks?
- How reliable is tool calling with local models via vLLM?
- What's the practical context window behavior (advertised vs. useful)?

### Exit Criteria

`forge init my-project` creates a working scaffold. Both local models respond to structured prompts via API. Frontier APIs are callable.

---

## Phase 1: The Minimum Viable Loop (Week 3-5)

**Goal:** Build the core task execution loop: local worker → Oracle → frontier review → verdict → iterate.

### Deliverables

- [ ] ACI tools (core set): `view_file`, `edit_file`, `search_file`, `run_command`, `run_tests`, `git_commit`, `tree`, `codemap`
  - All bounded, structured JSON output
  - `edit_file` with immediate lint check
- [ ] Worker agent: takes a task description, uses ACI tools to implement, commits
- [ ] Oracle Generator: produces structured snapshot after task completion
  - Diff extraction
  - Tree-sitter codemap of changed files
  - Mechanical checks (lint, type check, tests, build)
  - Worker self-assessment prompt
- [ ] Gate Engine: sends Oracle to frontier reviewers, collects verdicts
  - Parallel independent review (Sonnet + Codex)
  - Chairman synthesis (Opus)
  - Structured PASS/FAIL with actionable TODO on failure
- [ ] Iteration loop: on FAIL, feed TODO back to worker, re-execute, re-Oracle, re-review
- [ ] Basic `forge task "description"` command that runs the full loop
- [ ] Trace logging: every model call logged with model, tokens, latency, outcome

### The Loop in Practice

```
User: forge task "Add rate limiting middleware to all API routes"

FORGE:
  1. Worker (Qwen 3.5-35B, local) receives task
  2. Worker uses ACI tools: search_file → view_file → edit_file → run_tests
  3. Worker commits: "Add express-rate-limit to API routes"
  4. Oracle generated: diff (42 lines), codemap (3 files), tests pass, lint clean
  5. Sent to Sonnet 4.6: "Architectural coherence looks good. Rate limit config
     should be externalized, not hardcoded in middleware."
  6. Sent to Codex: "Missing test for rate limit exceeded response (429).
     No test for rate limit reset behavior."
  7. Opus synthesizes: FAIL
     TODO:
     - [ ] Move rate limit config to config/rate-limits.yaml (BLOCKING)
     - [ ] Add test: POST /api/auth/login x 101 → expect 429 (BLOCKING)
     - [ ] Add test: wait for rate limit reset → expect 200 (ADVISORY)
  8. Worker receives TODO, iterates
  9. New Oracle generated → reviewers → Opus: PASS
  10. Merge to main.

Metrics: 2 iterations, 89K local tokens, 4.2K frontier tokens, $0.03 frontier cost
```

### Learning Outcomes

- What's the first-pass success rate for local models on simple tasks?
- What failure modes recur? (Naming? Testing? Architecture? Logic?)
- How useful is the worker self-assessment signal?
- What's the actual frontier cost per task?
- How long does the full loop take wall-clock?

### Exit Criteria

`forge task` runs end-to-end for simple coding tasks (add endpoint, fix bug, add test). Metrics are logged. At least 20 tasks completed to build baseline data.

---

## Phase 2: Mission Decomposition & Milestones (Week 6-8)

**Goal:** Add multi-task mission planning with milestone-based validation.

### Deliverables

- [ ] Mission planner: decomposes "Build X" into milestones → tasks
  - Can use either local planner (big brain) or frontier (Opus) for initial decomposition
  - Outputs structured `feature_list.json` (Anthropic pattern: immutable success criteria)
- [ ] Milestone validation: at milestone boundaries, run full E2E check
  - Desloppify scan
  - Playwright browser tests (if web project)
  - Integration test suite
  - Oracle for entire milestone (aggregated)
- [ ] Git worktree isolation: one worktree per active task
- [ ] Sequential task execution within milestones
- [ ] `forge mission "description"` command
- [ ] `forge status` shows mission progress, milestone state, task queue
- [ ] Feature list tracking: which features are done, which remain, overall progress %

### Mission Flow

```
forge mission "Build user authentication with login, signup, password reset, and JWT refresh"

FORGE Mission Plan:
  Milestone 1: Core Auth Infrastructure
    Task 1.1: Set up auth module structure and config
    Task 1.2: Implement password hashing utilities
    Task 1.3: Create user model and database schema
    Validation: Unit tests pass, module structure lint clean

  Milestone 2: Login & Signup
    Task 2.1: Implement signup endpoint
    Task 2.2: Implement login endpoint with JWT
    Task 2.3: Add input validation and error handling
    Validation: E2E tests (signup flow, login flow), Desloppify scan

  Milestone 3: Token Management
    Task 3.1: Implement JWT refresh endpoint
    Task 3.2: Implement token revocation
    Validation: E2E tests (full auth lifecycle), security review

  Milestone 4: Password Reset
    Task 4.1: Implement password reset request (email token)
    Task 4.2: Implement password reset confirmation
    Validation: Full E2E suite, Desloppify final scan, milestone Oracle → frontier review

Approve? [y/n/edit]
```

### Learning Outcomes

- Can local models produce useful task decompositions, or is this a frontier-only capability?
- How do milestone-level Oracle reviews compare to per-task reviews in catching issues?
- What's the right milestone granularity?
- How does git worktree isolation behave in practice with local models?

### Exit Criteria

`forge mission` decomposes, executes, and validates a multi-task project end-to-end. At least 3 missions completed with different project types.

---

## Phase 3: Enforcement, Quality & Adaptive Gates (Week 9-12)

**Goal:** Add the three enforcement layers and adaptive gate intelligence.

### Deliverables

- [ ] Hook system: pre/post tool-use hooks in `.forge/hooks.yaml`
  - Auto-format on edit
  - Allowlist enforcement on shell commands
  - Secret detection pre-commit
- [ ] Architectural linters: `.forge/architecture.yaml` with agent-readable error messages
  - Project-specific rules that encode design decisions
  - Import boundary enforcement
  - Naming convention enforcement
- [ ] Desloppify integration:
  - `forge quality` runs scan
  - Score included in Oracle snapshots
  - Threshold gate at milestone boundaries
  - `desloppify next` integration for remediation tasks
- [ ] Adaptive gate policy:
  - Track first-pass success rate by task type
  - Confidence-based review intensity (skip full review for high-confidence tasks)
  - Escalation: if N consecutive tasks fail first-pass, increase review intensity
- [ ] Skills system v1:
  - Capture successful patterns as YAML skills
  - Inject relevant skills into worker context
  - `forge skills` to list and manage
- [ ] `forge metrics` dashboard:
  - Frontier/local token split
  - Iteration count distribution
  - First-pass success rate trend
  - Cost per task/milestone/mission
  - Quality score trend
  - Model comparison (when swapping)

### Learning Outcomes

- How much does mechanical enforcement reduce iteration loops?
- What's the right threshold for adaptive gate relaxation?
- Do skills actually improve first-pass success rate over time?
- Where does Desloppify add most value — preventing regressions or improving existing code?

### Exit Criteria

All three enforcement layers operational. Adaptive gate making measurably different decisions than static per-task review. Skills injected into at least 5 tasks. Metrics dashboard showing real trends.

---

## Phase 4: LoRA Fine-Tuning Loop (Week 13-16)

**Goal:** Close the learning loop — use accumulated task data to fine-tune local models.

### Deliverables

- [ ] Training data export: `forge export-training`
  - Successful completions as instruction-tuning examples
  - Failed-then-corrected pairs as preference data (DPO/RLHF)
  - Filter for quality (only tasks with Desloppify score above threshold)
- [ ] LoRA fine-tuning pipeline on DGX Spark
  - NeMo framework for Nemotron models
  - QLoRA for Qwen models
  - Automated: export → preprocess → fine-tune → evaluate → deploy
- [ ] A/B testing infrastructure:
  - Run same tasks on base model vs. fine-tuned model
  - Compare first-pass success rate, iteration count, quality scores
  - Statistical significance tracking
- [ ] Model versioning: track which fine-tune version is active, rollback if quality drops
- [ ] `forge train` command to trigger fine-tuning pipeline
- [ ] `forge compare` command to run A/B evaluation

### Learning Outcomes

- Does fine-tuning on task data actually improve first-pass success rate?
- How much data is needed before fine-tuning shows gains?
- Do gains generalize across task types, or only within the trained distribution?
- What's the right re-training frequency?

### Exit Criteria

At least one fine-tuning cycle completed. A/B comparison data showing measurable impact (positive or negative — both are valid learnings). Pipeline is automated and repeatable.

---

## Phase 5: Open-Source Packaging & Community (Week 17+)

**Goal:** Make FORGE installable and usable by others.

### Deliverables

- [ ] `pip install forge-ai` (or similar) — clean installation
- [ ] Documentation: getting started, configuration, model recommendations
- [ ] Example projects: small worked examples showing the full loop
- [ ] Hardware guide: what works on different setups (single GPU, multi-GPU, Mac, Spark)
- [ ] Published learnings: blog post or thread summarizing empirical findings
- [ ] Contribution guide: how to add tools, linters, gate policies, model integrations
- [ ] License: open-source (MIT or Apache 2.0)

### Ongoing

- [ ] Model updates: as new local models release, test and document performance
- [ ] Community patterns: collect and share harness patterns that work
- [ ] Benchmark suite: standardized tasks for comparing harness configurations

---

## Phase X: Experimental Extensions (Ongoing, Opportunistic)

These are ideas to explore as they become relevant. Not committed to any timeline.

### Grok as Frontier Scout

Use Grok to sweep X/Reddit for relevant patterns, new tool releases, community learnings. Feed findings into mission planning context.

### Multi-Spark Topology

Link two DGX Sparks via ConnectX-7 for 256GB unified memory. Test whether larger models (200B+) at lower quantization outperform smaller models at higher precision for specific roles.

### Council Mode

For critical architectural decisions, convene a "model council" — send the same question to 3+ frontier models independently, then synthesize. High cost, high confidence for irreversible decisions.

### RepoPrompt Deep Integration

If RepoPrompt exposes sufficient MCP tooling, integrate its Context Builder as the primary oracle generation pipeline rather than building a custom one. Trade portability for capability.

### Cross-Project Learning

When FORGE is used across multiple projects, can skills and fine-tuning data from one project improve performance on another? Transfer learning at the harness level.

### Real-Time Collaboration

A mode where FORGE works alongside a human developer in real-time — human handles the creative/architectural decisions, FORGE handles the implementation and iteration loops. Less autonomous, more collaborative.

---

## Resource Estimates

| Phase | Duration | Primary Effort | Hardware Needs |
|-------|----------|---------------|----------------|
| 0: Foundation | 2 weeks | DevOps, model serving | DGX Sparks + model downloads |
| 1: MVP Loop | 3 weeks | Core harness engineering | DGX Sparks + frontier API credits |
| 2: Missions | 3 weeks | Orchestration logic | Same |
| 3: Enforcement | 4 weeks | Linters, hooks, Desloppify, metrics | Same |
| 4: Fine-Tuning | 4 weeks | ML pipeline, A/B testing | DGX Spark for training |
| 5: Open-Source | Ongoing | Documentation, packaging | — |

**Frontier API Budget Estimate (Phases 1-3):**
- ~50-100 tasks during development and testing
- Average ~4K frontier tokens per task review
- Estimated: $5-15 total (Sonnet + Codex review, Opus synthesis)
- This is deliberately cheap — the Oracle keeps frontier token consumption minimal

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Local models can't reliably follow ACI tool schemas | Blocks Phase 1 | Test tool calling thoroughly in Phase 0. Simplify schemas. Fall back to text-based tool use with regex parsing. |
| Frontier review latency makes the loop too slow | Degrades experience | Batch reviews. Async execution (review happens while next task starts). Per-milestone review as default. |
| DGX Spark can't serve models fast enough for practical use | Blocks core thesis | Quantize aggressively. Use MoE models (Nemotron Super 12B active). Fall back to M3 Ultra for some roles. |
| Fine-tuning doesn't improve performance | Phase 4 value unclear | Still generates useful data about the boundary. Learnings are published regardless. |
| RepoPrompt dependency limits portability | Limits open-source adoption | Build custom tree-sitter oracle pipeline in Phase 1. RepoPrompt integration is additive, not required. |
| Scope creep from too many experimental extensions | Delays core phases | Phase X is explicitly opportunistic. Core phases 0-4 are the commitment. |
| Open-source models change faster than FORGE can adapt | Architecture churn | Model-agnostic design. Config-based model swapping. Performance testing on model update. |

---

## Decision Log

| Decision | Rationale | Revisit When |
|----------|-----------|--------------|
| vLLM over Ollama for model serving | Production-grade tool calling, PagedAttention, concurrent requests | If vLLM setup is too complex for DGX Spark |
| Sequential task execution (not parallel) in Phase 1-2 | DGX Spark single GPU can't serve multiple large model instances concurrently | If multi-Spark topology unlocks real parallelism |
| Oracle as structured JSON (not natural language) | Parseable by both models and metrics pipelines. Token-efficient. | If reviewers consistently ask for more context |
| Desloppify between milestones only (not continuous) | GPU can't serve quality model and worker simultaneously | If smaller quality models can run alongside worker |
| Python for harness (not Rust/Go) | Fastest iteration speed for a learning project. Rich LLM ecosystem. | If performance becomes a bottleneck |
| Tree-sitter for codemap (not LSP) | Lightweight, no runtime dependencies, works offline | If LSP provides significantly better structural analysis |

---

*This plan is designed to be wrong in useful ways. Each phase generates data that informs whether the next phase should proceed as designed, pivot, or be skipped entirely.*
