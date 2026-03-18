# FORGE v0.1 — COO Review (a8ra-m3)

> **Lateral review of the 10 Open Questions + one strategic addition**

**Reviewer:** COO (Claude Opus 4.6, a8ra-m3 station)
**Date:** 2026-03-18
**Input documents:** FORGE_OVERVIEW_v0.1.md, FORGE_ARCHITECTURE_v0.1.md, FORGE_PHASES_v0.1.md
**Status:** Raw feedback for v0.2 synthesis

---

## Review Approach

Fresh-eyes review of the 10 Open Questions posed in FORGE_OVERVIEW_v0.1.md §8. Each question is treated as a jousting prompt — the goal is to pressure-test the thinking, elevate where possible, and surface what's missing.

---

## Q1: Gate Granularity — Per-Task, Per-Milestone, or Adaptive?

The doc frames this as a spectrum but the real insight is that **gate granularity should be a function of trust, not schedule**. Per-task is training wheels. Per-milestone is cruise control. The interesting question isn't which one — it's what the graduation function looks like.

A worker that's been fine-tuned on 200 successful tasks in this codebase shouldn't get the same scrutiny as a fresh base model. The adaptive policy should track **worker identity**, not just task complexity. This means the gate engine needs to model *which worker* produced the output, not just *what* the output is. That's a deeper design than the doc currently captures — it makes the gate engine a trust system, not just a review system.

**Recommendation:** Reframe adaptive gates as a trust model with worker identity as a first-class input. The gate engine is not a review scheduler — it's a trust system.

---

## Q2: Oracle Density — How Much Context Is Optimal?

The current Oracle spec is well-structured but is missing a feedback loop. The right density isn't static — it should be **shaped by reviewer complaints**. If Opus keeps asking "I need to see the full file to assess this," that's a signal to increase density for that task type. If reviewers consistently ignore the codemap section, strip it.

The Oracle should have a **meta-learning layer**: track which Oracle sections reviewers actually reference in their verdicts, and weight accordingly. This turns Oracle generation into an optimization problem with a measurable objective — reviewer verdict quality per frontier token spent.

**Recommendation:** Add a reviewer-feedback loop to Oracle generation. Measure which sections reviewers reference in verdicts. Optimize density dynamically per task type.

---

## Q3: Local Model Routing — Big Brain vs Fast Hands

The doc presents this as a deployment question but it's actually an **empirical question that FORGE itself should answer**. Don't pre-commit to a split. Run the same tasks through both models, measure first-pass success rate, iteration count, and wall-clock time. Let the data decide.

The more interesting routing question the doc doesn't ask: **should the same model handle planning and coding?** SWE-Agent showed that giving the agent both navigation and editing tools in one session works. Factory.ai showed that separating planning from execution works. These are contradictory findings. FORGE is positioned to actually test which is true for local models — that's a publishable result.

**Recommendation:** Don't pre-commit to role separation. Make it an experiment. The planning-vs-coding split for local models is a publishable empirical question FORGE can answer.

---

## Q4: Desloppify Timing

The constraint cited — "GPU can't serve quality model and worker simultaneously" — is a hardware limitation, not a design principle. Conceptually, continuous quality feedback is obviously superior. Design the abstraction assuming eventual compute availability.

More importantly: **Desloppify should be asymmetric**. Mechanical detection (dead code, duplication, complexity) costs nothing — it's tree-sitter, not a model. Run that continuously. The LLM subjective pass is the expensive part. Run *that* at milestones. The doc conflates the two.

**Recommendation:** Split Desloppify into mechanical (continuous, free) and subjective (milestone-gated, model-dependent). Design the interface to support both modes regardless of current hardware constraints.

---

## Q5: Skill Persistence Format — Prompts, YAML, or LoRA?

This question hides the real question: **what's the half-life of a skill?**

- **Prompt snippets**: hours to days. Contextual, disposable. "In this codebase, we use bcrypt not argon2."
- **YAML configs**: weeks to months. Structural patterns. "Auth endpoints always need rate limiting."
- **LoRA adapters**: permanent. Baked into weights. "How to write idiomatic TypeScript."

These aren't alternatives — they're three tiers of a **knowledge crystallization pipeline**. Raw pattern → validated pattern → fine-tuned weight. The system should promote skills upward as confidence increases, not choose one format.

This is the most architecturally significant question in the list because it defines FORGE's compounding mechanism.

**Recommendation:** Design skills as a three-tier crystallization pipeline (prompt → YAML → LoRA) with confidence-based promotion between tiers. This is FORGE's compounding flywheel.

---

## Q6: Multi-Spark Topology — Independent or Linked?

The conceptual question: **is there a workload that benefits from a single large memory space over two independent inference servers?**

Yes: serving a single 120B+ model at higher precision. No: running two different models in two different roles. Since FORGE's architecture explicitly calls for role-separated models (planner vs worker), independent servers align better with the design. Linked memory is a solution looking for a different problem — maybe training, maybe a future 200B+ model that doesn't exist yet.

**Recommendation:** Default to independent servers. Linked topology is a Phase X experiment for training or very large single-model serving, not core architecture.

---

## Q7: Human Checkpoint Frequency

The doc asks this as a dial to tune. The frame is wrong. **The human isn't a checkpoint — the human is the sovereign.**

FORGE should be designed so the human sees *everything* but is only *required* at explicit gates: mission approval, milestone sign-off, and any invariant tension the Chairman can't resolve. The difference is visibility vs. intervention. High visibility, low required intervention, with `forge intervene` available at any point.

Don't add mandatory checkpoints that train the human to rubber-stamp.

**Recommendation:** High visibility, low mandatory intervention. The human is sovereign, not a checkpoint. `forge intervene` is the right pattern — preserve it, don't erode it with routine approval gates.

---

## Q8: Frontier Model Selection — Sonnet + Codex? Grok as Third?

The two-reviewer model is sound because it exploits **training distribution diversity**. Each additional reviewer follows diminishing returns — more latency and cost, decreasing marginal signal.

Grok's value isn't as a code reviewer — it's as a **scout**. Its differentiation is real-time web knowledge, not code reasoning. Use it for: "are there known vulnerabilities in this dependency version?", "has anyone reported issues with this API pattern?", "what's the community consensus on this library?"

That's a different role — not Reviewer C, but **Intelligence**.

**Recommendation:** Keep two reviewers for code. Add Grok as a distinct Intelligence role (not a reviewer). Different capability, different use pattern.

---

## Q9: Context Window Management — Exploit 1M or Stay Conservative?

Stay conservative. Fresh-context-per-task is one of the strongest patterns across all the influences cited (Anthropic's clean-state requirement, Factory.ai's fresh worker sessions). Long context is useful for *reading* (understanding a codebase) but harmful for *writing* (accumulated context creates drift, earlier errors compound, attention degrades).

The 1M window is an asset for the **planner** role, not the worker. A planner that can ingest the full codebase codemap + all previous Oracle snapshots + the full feature list to plan the next milestone — that's where long context earns its keep. The worker should get a clean, bounded context every task.

**Recommendation:** Strong architectural opinion — fresh context per task for workers, long context for planners only. Do not conflate reading capability with writing discipline.

---

## Q10: RepoPrompt Dependency — Build Custom or Integrate?

Build custom. Not because RepoPrompt is bad — it's excellent — but because **Oracle generation is the core of FORGE's value proposition**. It's the boundary between local and frontier. It's what makes frontier review cost-bounded. It's the thing that needs to evolve fastest.

Depending on a proprietary macOS-native tool for your core differentiator is a strategic error. Tree-sitter is open, multi-platform, and well-understood. Build the Oracle pipeline on tree-sitter from day one. If RepoPrompt later exposes MCP tooling that's genuinely better, integrate it as an *alternative* Oracle backend — but the custom pipeline must exist and be the default.

**Recommendation:** Own the Oracle pipeline. Tree-sitter from day one. RepoPrompt as optional backend, never as dependency.

---

## Q11 (NEW): The Question That Isn't Asked — What Does FORGE Measure That Nobody Else Does?

The 10 questions above are all operational — *how* to build FORGE. The strategic question missing:

**What does FORGE measure that nobody else is measuring?**

Every agentic coding tool measures task completion. FORGE's unique position is that it can measure the **frontier/local boundary empirically, per task type, over time**. That's the thesis in the Overview. But the architecture doesn't have a first-class mechanism for this measurement.

What's missing:
- No `forge boundary` command
- No dashboard panel showing "tasks where local succeeded first-pass vs. tasks that required frontier correction"
- No automated experiment where the same task runs local-only and hybrid to measure the delta
- No structured data capture of *why* frontier review caught something local missed

If FORGE ships without making this measurement trivially easy, it's just another agentic harness. The boundary measurement is the thing that makes it a contribution to the field.

**Recommendation:** Elevate boundary measurement from "success metric" (§7) to **core feature**. Design Phase 1 around it. Add `forge boundary` as a first-class command. Make the frontier/local delta the headline metric in the dashboard, not an afterthought.

---

## Summary of Recommendations

| # | Core Recommendation |
|---|---------------------|
| Q1 | Gate engine is a trust system, not a review scheduler. Track worker identity. |
| Q2 | Oracle density should self-optimize via reviewer feedback loop. |
| Q3 | Planning-vs-coding split is an empirical question. Don't pre-commit. |
| Q4 | Split Desloppify: mechanical (continuous) + subjective (milestone-gated). |
| Q5 | Skills are a three-tier crystallization pipeline. This is the compounding flywheel. |
| Q6 | Independent servers. Linked topology is Phase X. |
| Q7 | Human is sovereign, not a checkpoint. High visibility, low required intervention. |
| Q8 | Two reviewers for code. Grok as Intelligence, not Reviewer C. |
| Q9 | Fresh context for workers. Long context for planners only. |
| Q10 | Own the Oracle pipeline. Tree-sitter. RepoPrompt as optional backend. |
| Q11 | Elevate boundary measurement to core feature. It's the differentiator. |

---

*Review complete. Ready for synthesis into v0.2 alongside other advisor input.*
