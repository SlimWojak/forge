# FORGE

> **An Open-Source Harness for Frontier/Local Model Orchestration in Software Engineering**

FORGE is a CLI-first agentic harness that orchestrates both local and frontier LLMs to build software. It exists to answer a question empirically: *what is the optimal orchestration between frontier and local models, and how does that boundary move over time?*

**Status:** v0.1 Planning — Documents under lateral review

---

## Core Idea

Local models do the volume work (coding, iteration, lint fixes). Frontier models do the judgment work (architectural review, go/no-go gates). A structured "Oracle" snapshot keeps frontier costs bounded by sending diffs and codemaps — not full codebases — for review.

```
Local Worker (Qwen/Nemotron) → codes task
         ↓
    Forge Oracle (structured snapshot)
         ↓
Frontier Reviewers (Sonnet + Codex) → independent review
         ↓
   Chairman (Opus) → PASS or FAIL + TODO
         ↓
   If FAIL → Worker iterates until gate passes
```

## Planning Documents

| Document | Description |
|----------|-------------|
| [FORGE_OVERVIEW_v0.1.md](FORGE_OVERVIEW_v0.1.md) | Vision, thesis, positioning, hybrid architecture concept |
| [FORGE_ARCHITECTURE_v0.1.md](FORGE_ARCHITECTURE_v0.1.md) | Technical architecture, Oracle layer, enforcement, observability |
| [FORGE_PHASES_v0.1.md](FORGE_PHASES_v0.1.md) | Phased build plan from MVP loop to LoRA fine-tuning |

## Foundational Influences

- **SWE-Agent ACI** — bounded tools, stateful navigation, immediate feedback
- **Anthropic's Two-Agent Pattern** — initializer + worker, immutable feature lists, clean-state handoffs
- **Factory.ai Missions** — milestone decomposition, fresh worker sessions, skill learning
- **Desloppify** — dual-scan quality (mechanical + LLM), anti-gaming scoring, prioritized fix queue
- **RepoPrompt** — token-efficient oracle generation via tree-sitter codemaps

## Hardware Target

Designed for DGX Spark (128GB, 1 PFLOP FP4) + Apple Silicon. Model-agnostic — any OpenAI-compatible API works.

## License

TBD (MIT or Apache 2.0)

---

*This project is a learning harness. Its purpose is to build harness engineering intuition, measure the frontier/local boundary empirically, and contribute patterns to the open-source community.*
