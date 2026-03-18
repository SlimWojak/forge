# FORGE

> **An Open-Source Harness for Frontier/Local Model Orchestration in Software Engineering**

FORGE is a CLI-first agentic harness that orchestrates both local and frontier LLMs to build software. It exists to answer a question empirically: *what is the optimal orchestration between frontier and local models, and how does that boundary move over time?*

**Status:** v0.2 — Architecture locked, scaffold complete, Phase 1 implementation in progress.

---

## Core Idea

Local models do the volume work (coding, iteration, lint fixes). Frontier models do the judgment work (architectural review, go/no-go gates). A structured "Oracle" snapshot keeps frontier costs bounded by sending diffs and codemaps — not full codebases — for review.

The headline metric is **frontier/local delta** — not task completion rate.

```
Local Worker (Qwen/Nemotron) → codes task in isolated worktree
         ↓
    Enforcement Layer → hooks, linters, Desloppify (mechanical)
         ↓
    Forge Oracle → structured 2-4K token snapshot (tree-sitter)
         ↓
    Frontier Reviewer (Sonnet/Codex) → PASS or FAIL + structured TODO
         ↓
    If FAIL → Worker iterates with fresh context
    If PASS → Shadow mode: human approves merge
```

## Quick Start

```bash
# Clone and set up
git clone <repo-url>
cd forge-docs
bash init.sh

# Activate the environment
source .venv/bin/activate

# Verify
forge --help
pytest
```

## Project Structure

```
forge-docs/
├── src/forge/                    # Main package
│   ├── cli.py                    # Click CLI commands (§2)
│   ├── aci/                      # Agent-Computer Interface tools (§11)
│   ├── orchestrator/             # Mission → milestone → task (§3)
│   ├── oracle/                   # Tree-sitter Oracle generator (§4)
│   ├── gate/                     # Gate engine + verdicts (§5)
│   ├── enforcement/              # Hooks, linters, Desloppify (§6)
│   ├── boundary/                 # Boundary measurement (§7)
│   ├── benchmark/                # Benchmark cartridge runner (§8)
│   ├── skills/                   # Skill crystallization (§9)
│   ├── observability/            # OTel → DuckDB pipeline (§10)
│   ├── models/                   # Model provider abstraction (§13)
│   ├── git/                      # Worktree isolation (§12)
│   └── config/                   # Config loader (§13)
├── tests/                        # Test suite
├── docs/                         # Spec documents (READ-ONLY)
│   ├── FORGE_OVERVIEW_v0.2.md
│   └── FORGE_ARCHITECTURE_v0.2.md
├── .forge/                       # Harness state directory
│   ├── config.yaml               # Master config
│   ├── hooks.yaml                # Mechanical hooks (L1)
│   ├── architecture.yaml         # Architectural linter rules (L2)
│   └── benchmarks/               # Benchmark cartridges
├── AGENTS.md                     # Agent orientation file
├── pyproject.toml                # Python project config
└── init.sh                       # Dev environment setup
```

## CLI Commands

```bash
# Project lifecycle
forge init <project>              # Scaffold project with .forge/
forge task "<description>"        # Single task execution
forge mission "<description>"     # Multi-milestone mission (Phase 2+)
forge status                      # Current state summary

# Quality & review
forge quality                     # Desloppify scan (mechanical + subjective)
forge oracle [task-id]            # Generate/display Oracle snapshot
forge review [task-id]            # Send Oracle to frontier reviewer

# Boundary measurement
forge boundary                    # Frontier/local split report
forge taxonomy                    # Error taxonomy distribution

# Monitoring
forge metrics                     # Aggregated metrics
forge log                         # Recent trace history
forge digest                      # Daily summary

# Configuration
forge config models               # Model assignments
forge config gate                 # Gate policy
forge config frontier             # Frontier API config
forge config hooks                # Hook configuration

# Benchmarks
forge benchmark run               # Run benchmark suite
forge benchmark compare t1 t2     # Compare runs
forge benchmark list              # List cartridges

# Skills
forge skills list                 # List learned patterns by tier
forge skills promote <id>         # Promote skill to next tier

# Intervention
forge intervene                   # Pause execution
forge approve [task-id]           # Approve shadow-mode merge
forge reject [task-id] "<reason>" # Reject with feedback
```

## Architecture Documents

| Document | Description |
|----------|-------------|
| [FORGE_ARCHITECTURE_v0.2.md](docs/FORGE_ARCHITECTURE_v0.2.md) | Complete technical architecture — normative spec |
| [FORGE_OVERVIEW_v0.2.md](docs/FORGE_OVERVIEW_v0.2.md) | Vision, design decisions, all DECIDED items |
| [AGENTS.md](AGENTS.md) | Agent orientation — boot sequence, code standards |

## Foundational Influences

- **SWE-Agent ACI** — bounded tools, stateful navigation, immediate feedback
- **Anthropic's Two-Agent Pattern** — initializer + worker, immutable feature lists, clean-state handoffs
- **Factory.ai Missions** — milestone decomposition, fresh worker sessions, skill learning
- **Desloppify** — dual-scan quality (mechanical + LLM), anti-gaming scoring, prioritized fix queue
- **Tree-sitter** — custom codemap pipeline for token-efficient Oracle generation

## Hardware Target

Designed for DGX Spark (128GB, 1 PFLOP FP4) + Apple Silicon. Model-agnostic — any OpenAI-compatible API works.

## License

TBD (MIT or Apache 2.0)

---

*This project is a learning harness. Its purpose is to build harness engineering intuition, measure the frontier/local boundary empirically, and contribute patterns to the open-source community.*
