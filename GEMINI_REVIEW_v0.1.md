# FORGE v0.1 — Gemini Lateral Review

> **A blue-sky ideation and challenge of the FORGE orchestration concept**

**Reviewer:** Gemini (gemini-3.1-pro-preview)
**Date:** 2026-03-18
**Input documents:** FORGE_OVERVIEW_v0.1.md, FORGE_ARCHITECTURE_v0.1.md, FORGE_PHASES_v0.1.md, GPT_REVIEW.md, COO_REVIEW_v0.1.md
**Status:** Lateral Ideation & Synthesis

---

## 1. The Lateral Take: Elevating the Concept

The core thesis of FORGE—treating the frontier/local split as a measurable, moving boundary—is excellent. However, the current architecture treats software engineering primarily as a **spatial text problem** (files, ASTs, diffs). To elevate FORGE from a smart script to a true orchestration engine, we need to expand the dimensions it operates in.

Here are the missing angles and blue-sky builds:

### Angle A: The Multimodal Oracle (Software is Behavior, Not Just Text)
Currently, the Oracle is a static text snapshot (diffs, codemaps, mechanical checks). But software is dynamic and visual. 
*   **The Build:** Elevate the Oracle to include **Runtime and Visual Context**. If the task involves UI, the local worker should use Playwright to take before/after screenshots, and a multimodal frontier model (like Gemini 1.5 Pro or GPT-4o) should review the visual diff. If it's a backend task, include a flame graph or a trace summary. 
*   **Why:** Local models often write code that compiles but looks terrible or performs poorly. Frontier models excel at multimodal spatial reasoning.

### Angle B: "Blast Radius" Routing (Dynamic Gate Intensity)
The current gate logic is based on schedule (per-task vs per-milestone) or historical trust. It should be based on **Blast Radius**.
*   **The Build:** Before a task begins, use a fast, mechanical AST diff predictor to calculate the blast radius. Does this touch `auth.ts` (high radius) or `button.css` (low radius)? 
*   **Why:** High-blast-radius tasks get the full Board of Directors. Low-blast-radius tasks get auto-merged if mechanical checks pass, skipping the frontier tax entirely.

### Angle C: Harness-Level "Mixture of Agents" (Compute is Cheap, Time is Expensive)
You have two DGX Sparks. The current plan uses them sequentially or routes between them.
*   **The Build:** For complex tasks, run the "Big Brain" (Nemotron) and "Fast Hands" (Qwen) **in parallel** on the exact same task in isolated worktrees. First one to pass the mechanical tests and local linting wins and submits its Oracle to the frontier. 
*   **Why:** Local compute has zero marginal cost. Optimize for wall-clock time and success probability by racing the models against each other.

### Angle D: Auto-Demotion of Judgment (The True Boundary Measurement)
The stated goal is to measure the moving boundary, but the system doesn't actively *move* it.
*   **The Build:** Implement an "Auto-Demotion" engine. If the local model successfully completes 10 "API Route" tasks in a row that the Frontier Chairman approves with zero iterations, FORGE should automatically demote "API Route" tasks to bypass Frontier review entirely in the future.
*   **Why:** This turns FORGE into a self-optimizing system where the frontier tax trends toward zero over time as the local models (or their fine-tunes) prove their competence.

---

## 2. Answers to the 10 Open Questions

Here is my perspective on the 10 questions, deliberately contrasting with the GPT and COO takes to provide a wider possibility space.

### 1. Gate granularity
**Answer: Blast-Radius Gating.**
Don't gate based on time (milestones) or just historical trust. Gate based on structural impact. A typo fix in a README and a database schema migration should not follow the same review path. Use tree-sitter to mechanically assess the "weight" of the diff, and scale the frontier review intensity proportionally.

### 2. Oracle density
**Answer: Semantic Zoom (Interactive Oracles).**
The Oracle shouldn't be a fixed-length document; it should be an interactive object. Send a highly compressed summary (diff stats, signatures) but give the Frontier Reviewers a `zoom_in(file_path)` tool. Let the frontier models *pull* the density they need, rather than trying to guess the perfect push density.

### 3. Local model routing
**Answer: Parallel Racing, not Routing.**
As mentioned in Angle C, don't route. Race them. If you have the hardware, give the task to both Qwen and Nemotron simultaneously. This eliminates the need for complex routing heuristics and guarantees the fastest possible time-to-first-pass.

### 4. Desloppify timing
**Answer: Asynchronous CPU Shadowing.**
The assumption that Desloppify blocks the GPU is a constraint of running it synchronously. Run the subjective LLM review asynchronously on a smaller quantized model (e.g., Llama-3-8B) that fits in system RAM or a secondary GPU, trailing one commit behind the worker. It generates a "quality debt" backlog that the worker addresses at the milestone boundary.

### 5. Skill persistence format
**Answer: Executable Invariants (Prompt → Rule → Test).**
Skills shouldn't just be text. A true skill solidifies into mechanics.
1. *Prompt*: "Remember to handle null users." (Fragile)
2. *Linter Rule*: Add AST rule to `architecture.yaml`. (Better)
3. *Executable Test*: Generate a unit test that enforces the behavior. (Best)
FORGE should automatically try to convert YAML prompt skills into mechanical tests over time.

### 6. Multi-Spark topology
**Answer: Enforced Information Hiding (Independent).**
Keep them independent. Linked memory is a trap for orchestration. If models share a memory space, they risk sharing context contamination. Independent nodes force models to communicate strictly through the Oracle contract. This clean separation is vital for measuring the boundary accurately.

### 7. Human checkpoint frequency
**Answer: Anomaly-Driven Paging.**
The human is an Exception Handler. Do not use scheduled checkpoints (they lead to alert fatigue and rubber-stamping). Instead, trigger `forge intervene` based on anomaly detection:
- Worker loops > 3 times on the same task.
- Desloppify score drops by > 10 points in one commit.
- Frontier reviewers completely disagree (Sonnet says PASS, Codex says FAIL).

### 8. Frontier model selection for review
**Answer: Introduce the "Red Team" (Breaker) Role.**
Sonnet (Architecture) and Codex (Correctness) are good. But you are missing an adversarial perspective. Replace one with a "Breaker" role (e.g., GPT-4o or Claude 3.5 Sonnet instructed specifically to find security flaws, race conditions, and edge cases). You don't just need reviewers; you need an attacker.

### 9. Context window management for local models
**Answer: The 1M Window is for the "Narrative", not the "Code".**
Keep fresh-context-per-task for the actual coding (to prevent drift). But use the 1M context window of Nemotron Super to hold the *entire temporal history* of the mission (every Oracle, every verdict, every iteration). This acts as a high-level "Narrative Planner" that ensures the worker isn't just writing passing code, but is actually moving toward the original architectural vision.

### 10. The RepoPrompt dependency
**Answer: OpenOracle Standard.**
Build your own tree-sitter pipeline, but don't just make it a FORGE internal tool—publish it as the `OpenOracle` standard. If FORGE is to be a community harness, the way it compresses codebases into LLM-readable context should be a standalone, portable library. RepoPrompt can be an adapter, but the core must be open.

---

## 3. The "Harness as a Compiler" Vision

To truly push this to v0.2, stop thinking of FORGE as a team of agents, and start thinking of it as an **LLM Compiler**.

When you write C code, `gcc` runs multiple passes (lexing, parsing, optimization, code generation). 
FORGE is doing the same thing for natural language intent:
1. **Lexing/Parsing:** The Planner decomposes intent into a feature list.
2. **Code Generation:** The Local Worker generates the implementation.
3. **Optimization/Linting:** Desloppify and mechanical hooks run passes.
4. **Linking/Verification:** The Frontier Reviewers ensure it integrates with the broader architecture.

If you adopt the Compiler metaphor, the metrics become obvious: you measure *compilation time* (wall clock), *compilation cost* (API spend), and *binary quality* (Desloppify score). The goal of FORGE is to build the most efficient compiler for natural language to software.