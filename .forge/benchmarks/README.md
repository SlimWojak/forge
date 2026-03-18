# FORGE Benchmark Cartridge System

## Purpose

Benchmark cartridges are a fixed suite of 20–50 representative tasks for
controlled comparison. When you change **any** harness variable — new model,
new LoRA, new Oracle format, new gate policy — re-run the benchmark suite
and compare apples to apples.

## Structure

Each cartridge is a self-contained task definition:

```
.forge/benchmarks/
├── cartridge-manifest.yaml     # List of all cartridges with metadata
├── add-endpoint-01/
│   ├── task.yaml               # Task description + expected behavior
│   ├── repo-snapshot.tar.gz    # Starting state (or git ref)
│   ├── success-criteria.yaml   # Mechanical checks that must pass
│   └── expected-oracle.json    # Reference Oracle for Oracle quality testing
├── refactor-module-01/
│   └── ...
└── ...
```

## Cartridge Manifest

The `cartridge-manifest.yaml` lists all available cartridges with their
difficulty class, category, and estimated token usage. This is the entry
point for `forge benchmark list` and `forge benchmark run`.

## Creating a Cartridge

1. Copy `cartridge-template.yaml` to a new directory
2. Fill in the task description and success criteria
3. Add a repo snapshot (tar.gz of the starting state or a git ref)
4. Optionally add an expected Oracle for quality comparison
5. Register the cartridge in `cartridge-manifest.yaml`

## Running Benchmarks

```bash
forge benchmark run                           # Run all cartridges
forge benchmark run --cartridge add-endpoint-01  # Run single cartridge
forge benchmark run --tag "qwen35-lora-v2"    # Tag this run for comparison
forge benchmark compare tag1 tag2             # Compare two runs
```

## Categories

| Category           | Difficulty     | Description                              |
|--------------------|----------------|------------------------------------------|
| add-endpoint       | mechanical     | Add REST/GraphQL endpoint with validation |
| refactor-module    | architectural  | Extract/restructure module boundaries    |
| fix-test           | local-reasoning| Fix failing test from error message      |
| add-e2e            | local-reasoning| Add end-to-end test for existing flow    |
| wire-config        | mechanical     | Thread a config value through the stack  |
| repair-typing      | mechanical     | Fix type errors from compiler output     |
| implement-feature  | local-reasoning| Build feature from spec (multi-file)     |
| patch-lint         | mechanical     | Fix linting violations                   |
| schema-migration   | architectural  | Add/modify database schema + migration   |
| add-auth           | architectural  | Add authentication to existing endpoint  |

## Results

Benchmark results are stored in `.forge/benchmark-results/<run-id>.json`
with full trace data cross-referenced by trace_id. See the architecture
doc §8.3 for the complete results schema.

---

See: FORGE_ARCHITECTURE_v0.2.md §8
