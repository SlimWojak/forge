# FORGE v0.1 — Overview & Vision

> **Forge: An Open-Source Harness for Frontier/Local Model Orchestration**
> *Exploring the boundary between local and frontier AI for software engineering*

**Status:** v0.1 Draft — For lateral review
**Date:** 2026-03-18
**Author:** Craig @ a8ra / SlimWojak

---

## 1. What Is FORGE?

FORGE is an open-source, CLI-first agentic harness that orchestrates **both local and frontier LLMs** to build software. It is not a coding agent — it is the environment, constraints, feedback loops, and orchestration logic that turn models into a functioning engineering team.

FORGE exists to answer a question empirically:

> **What is the optimal orchestration between frontier and local models for software engineering, and how does that boundary move over time?**

It treats the frontier/local split as a first-class design concern — not a limitation to work around, but a variable to measure, optimize, and learn from.

---

## 2. Thesis

### The Harness Is Everything

The model is the reasoning engine. The harness is the context, the constraints, the feedback loops, and the structured knowledge that turns raw capability into consistent output.

This is now proven at scale:
- **SWE-agent** showed that the same model (GPT-4) goes from 3.97% to 12.47% task resolution simply by improving the Agent-Computer Interface — a 64% improvement from harness alone.
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

The hypothesis: **delegate volume work (coding, iteration, lint fixes, test writing) to local models, and judgment work (architectural review, go/no-go gates, re-scoping) to frontier models.** This is cost-optimal because coding loops are token-heavy but judgment-light, while review is token-light but reasoning-heavy.

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
- **Edit with immediate linting** — syntax check runs BEFORE applying edits. Errors return instantly, closing the feedback loop. Prevents cascading failures.
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

### Desloppify

- **Dual-scan architecture** — mechanical detection (dead code, duplication, complexity via tree-sitter) + LLM subjective review (naming, abstractions, module boundaries).
- **Prioritized fix queue** — `next` gives one fix at a time. Agent resolves before advancing.
- **Persistent state** — `.desloppify/` directory tracks progress across sessions. Incremental improvement over time.
- **Anti-gaming score** — the only way to improve the score is to actually make the code better. Strict scoring resists manipulation.
- **Living plan** — scan output includes agent instructions. The system directs the work, not the agent's own analysis.

**FORGE adaptation:** Desloppify runs between milestones (not continuously — GPU can't serve quality review and coding models simultaneously on local hardware). Quality delta becomes a confidence signal for gate decisions.

### RepoPrompt & the Oracle Concept

- **Two-stage Context Builder** — discovery agent curates relevant files, then analysis model generates deep analysis using codemaps (tree-sitter structural summaries at ~10x token savings).
- **Oracle Chat** — agents query the codebase mid-session; Context Builder finds answers using the full repo without manual file selection.
- **Token-efficient context** — codemaps show function/type signatures only, slices show specific line ranges. Full content only for files under active edit.

**FORGE adaptation:** The "Forge Oracle" — after every task completion, generate a structured snapshot (diff, codemap, lint/test results, quality delta, worker self-assessment). This is the handoff contract between local workers and frontier reviewers. Frontier models never see the full codebase — they see the Oracle. Keeps frontier costs bounded and predictable.

---

## 4. The "Board of Directors" Orchestration Model

FORGE uses a governance metaphor for its multi-model orchestration:

```
┌─────────────────────────────────────────────────┐
│                  CHAIRMAN (Opus)                 │
│  Synthesizes reviewer findings, makes go/no-go  │
│  decisions, rewrites TODOs with precision        │
└──────────────────────┬──────────────────────────┘
                       │ Structured verdict
          ┌────────────┴────────────┐
          │                         │
┌─────────┴──────────┐  ┌──────────┴─────────┐
│  REVIEWER (Sonnet)  │  │  REVIEWER (Codex)  │
│  Architectural      │  │  Correctness &     │
│  coherence, design  │  │  test coverage     │
│  patterns, naming   │  │  analysis          │
└─────────┬──────────┘  └──────────┬─────────┘
          │                         │
          └────────────┬────────────┘
                       │ Forge Oracle (snapshot)
┌──────────────────────┴──────────────────────────┐
│              CEO / WORKER (Qwen 3.5 / Nemotron) │
│  Local model — does all coding, iteration,      │
│  lint fixes, test writing. High throughput,      │
│  zero marginal cost. Iterates until gate passes. │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────┐
│              FORGE HARNESS (Python daemon)       │
│  Orchestrator, ACI tools, git worktree mgmt,    │
│  Oracle generation, mechanical enforcement,      │
│  Desloppify scheduling, trace/log collection     │
└─────────────────────────────────────────────────┘
```

### Flow Per Task

1. **Planner** (local big-brain or frontier) decomposes mission into milestones and tasks
2. **Worker** (local) codes in isolated git worktree using bounded ACI tools
3. After task completion, **Oracle Generator** (mechanical + local) creates structured snapshot
4. **Reviewers** (frontier, independent) assess the Oracle — different models catch different failure modes
5. **Chairman** (frontier, highest reasoning) synthesizes findings into structured verdict: PASS or FAIL + specific issues as actionable TODOs
6. If FAIL → Worker receives precise TODO, iterates. Loop repeats from step 2.
7. If PASS → Merge to main, advance to next task
8. At milestone boundaries → Desloppify scan + E2E validation

### Why This Works

- **Local does the volume** — coding iteration is token-heavy, latency-sensitive, and can be low-judgment. Perfect for local.
- **Frontier does the judgment** — review is token-light (Oracle, not full codebase) but reasoning-heavy. Perfect for frontier.
- **Independent reviewers reduce blind spots** — Sonnet and Codex have different training, different failure modes. Their disagreements surface real issues.
- **The Chairman role prevents reviewer noise** — Opus synthesizes, doesn't just aggregate. It decides what matters.
- **Cost scales with decisions, not keystrokes** — you pay frontier prices for judgment, not for typing.

---

## 5. Hardware Context

FORGE is designed to run on serious local hardware:

| Machine | Role in FORGE | Specs |
|---------|---------------|-------|
| DGX Spark #1 | Primary model server (big brain) | GB10 Blackwell, 128GB unified, 1 PFLOP FP4, NVLink-C2C |
| DGX Spark #2 | Secondary model server (fast hands) or fine-tuning | Same as above; ConnectX-7 for inter-Spark linking |
| M3 Ultra | Oracle generation, RepoPrompt, development | 512GB unified, 192GB/s bandwidth |
| M4 Studio | Test runner, secondary worker, experimentation | TBD specs |

### Model Deployment Strategy

| Role | Model (current candidates) | Hardware | Serving |
|------|---------------------------|----------|---------|
| Local Planner (big brain) | Nemotron 3 Super 120B-A12B or Qwen 3.5-35B | DGX Spark #1 | vLLM (FP4 native) |
| Local Worker (fast hands) | Qwen 3.5-35B or Nemotron 3 Nano 30B-A3B | DGX Spark #2 | vLLM or llama.cpp |
| Frontier Chairman | Opus 4.6 | API | — |
| Frontier Reviewer A | Sonnet 4.6 | API | — |
| Frontier Reviewer B | GPT-5.3 Codex | API | — |
| Quality Reviewer | Local model (Desloppify subjective) | DGX Spark #1 | vLLM |

**Note:** Model assignments are experimental and will evolve. A core purpose of FORGE is to measure which model performs best in which role and how that changes over time.

---

## 6. What FORGE Is Not

- **Not a Factory.ai competitor** — Factory uses frontier models end-to-end with massive compute. FORGE explores the frontier/local boundary.
- **Not a claim that local replaces frontier** — it's an instrument for measuring where each excels.
- **Not production-ready from day one** — it's a learning harness. Quality comes through iteration.
- **Not model-specific** — models are swappable. The harness, tools, and orchestration logic are the stable layer.
- **Not a solo project forever** — designed as open-source from the start, structured for community contribution.

---

## 7. Success Metrics

FORGE succeeds if it produces:

1. **Empirical data** on frontier/local task completion rates, iteration counts, and cost splits across task types
2. **A reusable harness** that others can install, configure with their own models, and run
3. **Published learnings** about harness design patterns that work (and don't work) with local models
4. **A fine-tuning pipeline** that demonstrably improves local model performance on codebase-specific tasks over time
5. **A personal deepening** of harness engineering intuition through sustained practice

---

## 8. Open Questions for Lateral Review

These are deliberately left unresolved for Opus/GPT/Grok jousting:

1. **Gate granularity** — Should frontier review happen per-task, per-milestone, or adaptively based on confidence signals?
2. **Oracle density** — How much context in the Oracle snapshot is optimal? Too little and reviewers miss issues; too much and you're paying for frontier tokens unnecessarily.
3. **Local model routing** — When should the "big brain" local model be used vs. the "fast hands"? Is role separation worth the complexity, or should one model do everything?
4. **Desloppify timing** — Between milestones only? After every N tasks? Continuous background with a smaller model?
5. **Skill persistence format** — Should learned patterns be stored as prompt snippets, YAML configs, or LoRA adapters? Different formats suit different timescales.
6. **Multi-Spark topology** — Independent model servers or linked 256GB unified memory? What workloads benefit from each?
7. **Human checkpoint frequency** — How much human intervention should FORGE expect in v1? Should it adapt over time?
8. **Frontier model selection for review** — Is Sonnet + Codex the right independent pair? Should Grok be a third reviewer for its X/Reddit sweep capability?
9. **Context window management for local models** — Nemotron 3 Super has 1M context. Should FORGE exploit this for larger task scopes, or stay conservative with fresh-context-per-task?
10. **The RepoPrompt dependency** — RepoPrompt is macOS-native and proprietary. Should FORGE build its own tree-sitter oracle pipeline for portability, or integrate via MCP?

---

*This document is a north star for discussion. It is deliberately opinionated to provoke useful disagreement.*
