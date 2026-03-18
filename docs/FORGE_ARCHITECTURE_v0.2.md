# FORGE v0.2 — Technical Architecture

> **The harness, orchestration, enforcement, and measurement systems that make FORGE work**

**Status:** v0.2 — Definitive architecture for implementation
**Date:** 2026-03-18
**Author:** Craig @ a8ra / SlimWojak
**Source of truth:** FORGE_OVERVIEW_v0.2.md (all decisions locked)
**Implementors:** Phase 1 → Factory.ai Droid | Phase 2+ → Claw builder

---

## How to Read This Document

Every component is marked:
- **`PHASE 1`** — In scope for Factory.ai Droid implementation. Build this.
- **`PHASE 2+`** — Design target for Claw builder. Do not build in Phase 1 but do not make design choices that prevent it.

JSON schemas are normative. ASCII diagrams are structural references. CLI commands are the public interface contract.

---

## 1. System Architecture Overview

### 1.1 High-Level Topology `PHASE 1`

```
                                    ┌──────────────────┐
                                    │   FRONTIER APIs   │
                                    │  ┌──────────────┐ │
                                    │  │ Sonnet 4.6   │ │
                                    │  │ Opus 4.6     │ │
                                    │  │ GPT-5.3      │ │
                                    │  │ Grok (intel) │ │
                                    │  └──────────────┘ │
                                    └────────┬─────────┘
                                             │ Oracle review / verdicts
┌────────────────────────────────────────────┼──────────────────────────────────┐
│  FORGE HARNESS (Python)                    │                                  │
│                                            │                                  │
│  ┌───────────────┐  ┌────────────────┐  ┌──┴───────────────┐                 │
│  │  CLI / TUI    │─▶│  Orchestrator  │─▶│  Gate Engine     │                 │
│  │  (Click /     │  │  (Mission      │  │  (Trust system,  │                 │
│  │   Textual)    │  │   Control)     │  │   review loop)   │                 │
│  └───────────────┘  └──────┬─────────┘  └──────────────────┘                 │
│                            │                                                  │
│           ┌────────────────┼────────────────┐                                │
│           │                │                │                                 │
│    ┌──────┴───────┐  ┌─────┴──────┐  ┌──────┴──────────┐                    │
│    │  ACI Tools   │  │  Git Mgr   │  │  Oracle         │                    │
│    │  (bounded,   │  │  (worktree  │  │  Generator      │                    │
│    │   stateful)  │  │   isolation)│  │  (tree-sitter)  │                    │
│    └──────┬───────┘  └─────┬──────┘  └──────┬──────────┘                    │
│           │                │                │                                 │
│    ┌──────┴────────────────┴────────────────┴──────────┐                     │
│    │              Enforcement Layer                     │                     │
│    │  L1: Mechanical Hooks (real-time)                 │                     │
│    │  L2: Architectural Linters (CI-style)             │                     │
│    │  L3a: Desloppify Mechanical (continuous)          │                     │
│    │  L3b: Desloppify Subjective (milestone-gated)     │                     │
│    └──────────────────────┬───────────────────────────┘                     │
│                            │                                                  │
│    ┌──────────────────────┴───────────────────────────┐                     │
│    │        Observability & Boundary Measurement       │                     │
│    │  OpenTelemetry → DuckDB                          │                     │
│    │  Error taxonomy · Benchmark cartridges           │                     │
│    │  `forge boundary` dashboard                      │                     │
│    └──────────────────────────────────────────────────┘                     │
│                                                                              │
│    ┌──────────────────────────────────────────────────┐                     │
│    │        Skill Crystallization Pipeline             │                     │
│    │  Tier 1: Prompts → Tier 2: YAML → Tier 3: Lint  │                     │
│    │  → Tier 4: Tests → Tier 5: LoRA                  │                     │
│    └──────────────────────────────────────────────────┘                     │
│                                                                              │
└───────────────────────────┬──────────────────────────────────────────────────┘
                            │ OpenAI-compatible API (localhost)
               ┌────────────┴────────────┐
               │                         │
        ┌──────┴──────┐          ┌───────┴──────┐
        │ DGX Spark 1 │          │ DGX Spark 2  │
        │ vLLM        │          │ vLLM         │
        │ "Big Brain" │          │ "Fast Hands" │
        │ Planner /   │          │ Worker /     │
        │ Quality     │          │ Coder        │
        └─────────────┘          └──────────────┘
```

### 1.2 Data Flow — Single Task Lifecycle `PHASE 1`

```
┌──────────┐     ┌───────────┐     ┌──────────┐     ┌───────────┐
│ PLANNER  │────▶│  WORKER   │────▶│ ORACLE   │────▶│ REVIEWER  │
│          │     │ (local)   │     │ GENERATOR│     │ (frontier)│
│ Decompose│     │ ACI tools │     │ tree-sit │     │           │
│ + classify     │ git ops   │     │ diff/map │     │ Core +    │
│ difficulty│    │ lint/test │     │ mech chk │     │ Annexes   │
└──────────┘     └─────┬─────┘     └──────────┘     └─────┬─────┘
                       │                                    │
                       │        ┌────────────┐              │
                       │        │  VERDICT   │◀─────────────┘
                       │        │            │
                       │        │ PASS: ─────│──▶ Propose commit (shadow mode)
                       │◀───────│ FAIL: ─────│──▶ Structured TODO + iterate
                       │        │ FAIL×2: ───│──▶ Escalate to 2nd reviewer
                       │        │ FAIL×3: ───│──▶ Recovery mode
                       │        └────────────┘
                       │
                ┌──────┴──────┐
                │ ENFORCEMENT │
                │ L1: Hooks   │ ◀── runs on every tool call
                │ L2: Linters │ ◀── runs on every commit
                │ L3a: Mech   │ ◀── runs in hooks (tree-sitter)
                │ L3b: Subj   │ ◀── runs at milestone boundary
                └─────────────┘
```

### 1.3 State Machine `PHASE 1`

```
INIT
  │
  ▼
PLANNING ──────────────────────────────────────────────────────┐
  │                                                            │
  ▼                                                            │
DIFFICULTY_CLASSIFIED                                          │
  │                                                            │
  ▼                                                            │
EXECUTING                                                      │
  │                                                            │
  ▼                                                            │
MECHANICAL_CHECKS                                              │
  │                                                            │
  ├── FAIL ──▶ EXECUTING (worker fixes mechanical issues)      │
  │                                                            │
  ▼                                                            │
ORACLE_GENERATED                                               │
  │                                                            │
  ▼                                                            │
UNDER_REVIEW                                                   │
  │                                                            │
  ▼                                                            │
VERDICT                                                        │
  │                                                            │
  ├── PASS ──▶ PROPOSE_COMMIT ──▶ SHADOW_MERGE ──▶ NEXT_TASK  │
  │                                                    │       │
  ├── FAIL (iteration < N) ──▶ EXECUTING (with TODO)   │       │
  │                                                    │       │
  ├── FAIL (iteration == 2) ──▶ ESCALATE_REVIEWER      │       │
  │                              │                     │       │
  │                              ▼                     │       │
  │                           UNDER_REVIEW (2nd)       │       │
  │                                                    │       │
  ├── FAIL (iteration >= 3) ──▶ RECOVERY_MODE          │       │
  │                              │                     │       │
  │                              ├── REWRITE_TASK ─────│───────┤
  │                              ├── SPLIT_TASK ───────│───────┤
  │                              ├── ESCALATE_HUMAN    │       │
  │                              └── ABORT_TASK        │       │
  │                                                    │       │
  └── MILESTONE_BOUNDARY ──▶ DESLOPPIFY_SUBJECTIVE ────┘       │
                                │                              │
                                ▼                              │
                          MILESTONE_VALIDATED ─────────────────┘
                                │
                                ▼
                          MISSION_COMPLETE
```

---

## 2. CLI Interface `PHASE 1`

### 2.1 Command Reference

```bash
# ─── Project Lifecycle ───
forge init <project-name>            # Scaffold repo with .forge/ state directory
forge mission "<description>"        # Start multi-milestone mission (decompose → plan → execute)
  --mode delivery|research           # Mission class (default: delivery)
forge task "<description>"           # Single task execution (simpler loop, no milestones)
  --difficulty mechanical|local-reasoning|architectural|uncertain
                                     # Manual difficulty override (default: planner classifies)

# ─── Monitoring & Control ───
forge status                         # Current state: active tasks, quality, loop metrics, phase
forge dashboard                      # TUI: live progress, quality trends, model usage (Textual)
forge log                            # Recent trace history (last 20 events)
  --task <task-id>                   # Filter to specific task
  --full                             # Include full Oracle + verdict payloads

# ─── Boundary Measurement ───
forge boundary                       # Frontier/local split report (see §7 for output format)
  --period 7d|30d|all                # Time window (default: 7d)
  --by-type                          # Group by difficulty class
  --by-worker                        # Group by worker identity
forge taxonomy                       # Error taxonomy distribution and trends

# ─── Intervention ───
forge intervene                      # Pause execution, enter human PM mode
forge approve [task-id]              # Manually approve a pending gate / shadow-merge commit
forge reject [task-id] "<reason>"    # Reject with specific feedback
forge replan                         # Trigger re-decomposition of current milestone

# ─── Quality ───
forge quality                        # Run Desloppify scan now (mechanical + subjective)
  --mechanical-only                  # Skip LLM subjective review
forge oracle [task-id]               # Generate/display Oracle snapshot of current state
forge review [task-id]               # Send current Oracle to frontier reviewer(s)

# ─── Benchmarks ───
forge benchmark run                  # Execute full benchmark cartridge suite
  --cartridge <name>                 # Run single cartridge
  --tag <harness-variant>            # Label this run for comparison
forge benchmark compare <tag1> <tag2>  # Compare two benchmark runs
forge benchmark list                 # List available cartridges

# ─── Configuration ───
forge config models                  # Configure model assignments per role
forge config gate                    # Configure gate policy and trust parameters
forge config frontier                # Configure frontier API keys and model preferences
forge config hooks                   # Show/edit mechanical hooks configuration

# ─── Skills & Learning ───
forge skills                         # List learned patterns / skills by tier
forge skills promote <skill-id>      # Manually promote a skill to next tier
forge export-training                # Export accumulated data for LoRA fine-tuning
  --format preference-pairs|sft|both
  --output <path>

# ─── Metrics & Observability ───
forge metrics                        # Frontier/local split, iteration counts, cost data
forge trace <span-id>               # Inspect a specific trace span
forge digest                         # Generate daily digest summary now
```

### 2.2 CLI Architecture `PHASE 1`

```
forge (Click group)
├── init          → scaffold.py
├── mission       → orchestrator.py  (starts daemon)
├── task          → orchestrator.py  (single-task mode)
├── status        → state.py        (reads .forge/state.json)
├── dashboard     → tui.py          (Textual app — PHASE 2+: full TUI)
├── log           → trace.py        (queries DuckDB)
├── boundary      → boundary.py     (queries DuckDB + renders report)
├── taxonomy      → taxonomy.py     (queries DuckDB)
├── intervene     → orchestrator.py (pause + interactive)
├── approve       → gate.py
├── reject        → gate.py
├── replan        → orchestrator.py
├── quality       → desloppify.py
├── oracle        → oracle.py
├── review        → gate.py
├── benchmark     → benchmark.py
├── config        → config.py
├── skills        → skills.py
├── export-training → training.py
├── metrics       → metrics.py
├── trace         → trace.py
└── digest        → digest.py
```

**Phase 1 scope:** All commands listed above must exist. `forge dashboard` can be minimal (text-only summary). Full Textual TUI is Phase 2+.

---

## 3. Orchestrator (Mission Control) `PHASE 1`

### 3.1 Responsibilities

- Decompose missions into milestones and tasks (via planner model)
- Classify task difficulty before execution
- Schedule task execution in isolated git worktrees
- Manage the Oracle → Review → Verdict → Iterate loop
- Track state in `.forge/state.json`
- Handle recovery mode (rollback, escalate, split)
- Coordinate Desloppify scans at milestone boundaries
- Generate daily digests for human sovereign
- Record all events to observability pipeline

### 3.2 State Schema `PHASE 1`

```json
{
  "$schema": "forge-state-v0.2",
  "mission": {
    "id": "mission-001",
    "description": "Build user authentication system with JWT",
    "mode": "delivery",
    "status": "executing",
    "created_at": "2026-03-18T10:00:00Z",
    "milestones": [
      {
        "id": "milestone-001",
        "description": "Core auth endpoints",
        "status": "in_progress",
        "tasks": [
          {
            "id": "task-001",
            "description": "Implement POST /api/auth/login with JWT",
            "difficulty_class": "local-reasoning",
            "status": "under_review",
            "worker_identity": {
              "model": "qwen3.5-35b",
              "lora_version": null,
              "endpoint": "http://dgx-spark-2:8000/v1",
              "serving_config": "fp4-vllm"
            },
            "iteration": 1,
            "max_iterations": 3,
            "worktree": ".forge-worktrees/task-001-login",
            "branch": "forge/task-001-login",
            "oracle_id": "oracle-001-iter-1",
            "verdict_id": null,
            "error_taxonomy_tags": [],
            "timestamps": {
              "started": "2026-03-18T10:05:00Z",
              "oracle_generated": "2026-03-18T10:15:00Z",
              "review_started": "2026-03-18T10:15:05Z",
              "verdict_received": null,
              "completed": null
            },
            "cost": {
              "local_tokens": 45000,
              "frontier_tokens_in": 0,
              "frontier_tokens_out": 0,
              "wall_clock_seconds": 600
            }
          }
        ],
        "desloppify": {
          "mechanical_score": 78,
          "subjective_score": null,
          "last_scan": "2026-03-18T10:00:00Z"
        }
      }
    ]
  },
  "shadow_mode": {
    "enabled": true,
    "pending_merges": ["task-001"],
    "total_proposed": 0,
    "total_approved": 0,
    "total_rejected": 0
  },
  "recovery_mode": {
    "active": false,
    "consecutive_failures": 0,
    "threshold": 3
  },
  "config_hash": "sha256:abc123..."
}
```

### 3.3 Recovery Mode `PHASE 1`

Recovery mode is architecturally distinct from normal iteration. It activates after `N` consecutive failures (configurable, default 3).

**Trigger conditions:**
- Same task fails gate review N times consecutively
- Worker exhausts context window without producing passing code
- Mechanical checks fail after M attempts (configurable, default 5)

**Recovery sequence:**

```
RECOVERY_MODE activated
  │
  ▼
1. Stop iteration — do NOT loop again
  │
  ▼
2. Generate failure summary:
   {
     "task_id": "task-001",
     "attempts": 3,
     "error_taxonomy_tags": ["incorrect-logic", "missing-tests"],
     "attempt_summaries": [
       {"iteration": 1, "failure": "Missing error handling in JWT validation",
        "reviewer": "sonnet-4.6"},
       {"iteration": 2, "failure": "Error handling added but wrong HTTP status codes",
        "reviewer": "sonnet-4.6"},
       {"iteration": 3, "failure": "Status codes fixed but no test coverage",
        "reviewer": "gpt-5.3-codex"}
     ],
     "patterns": "Worker repeatedly fixes surface issues without addressing root cause"
   }
  │
  ▼
3. Escalate to planner/frontier:
   │
   ├── REWRITE_TASK  → planner rewrites task description with more specificity
   ├── SPLIT_TASK    → planner decomposes into smaller subtasks
   ├── CHANGE_APPROACH → different strategy, tools, or file ordering
   └── ESCALATE_HUMAN → `forge intervene` notification with full context
  │
  ▼
4. Rollback to last clean commit in worktree
  │
  ▼
5. If rewritten/split: new task(s) enter PLANNING state
   If escalated: wait for human intervention
```

**Interface:**
- Input: task state with N failed iterations, all Oracle snapshots, all verdicts
- Output: `RecoveryDecision` enum + new task spec(s) if applicable
- Planner receives the failure summary and all prior Oracles/verdicts as context

---

## 4. The Forge Oracle `PHASE 1`

### 4.1 Architecture

The Oracle is a structured snapshot that mediates between local workers and frontier reviewers. Frontier models never see the full codebase — they see the Oracle. This keeps frontier costs bounded and predictable.

**Built on a custom tree-sitter pipeline. Not RepoPrompt-dependent.** RepoPrompt may be an optional alternative backend but is never on the critical path.

```
Worker completes task
  │
  ▼
┌──────────────────────────────────┐
│       ORACLE GENERATOR           │
│                                  │
│  1. git diff main..worktree     │
│  2. tree-sitter parse changed   │
│     files → extract signatures, │
│     dependencies, call graph    │
│  3. Run mechanical checks       │
│     (lint, typecheck, test)     │
│  4. Compute quality delta       │
│     (Desloppify mechanical)     │
│  5. Collect worker self-assess  │
│  6. Assemble task context       │
│  7. Package Core Oracle         │
│  8. Stage Annexes (not sent)    │
│                                  │
└──────────┬───────────────────────┘
           │
     ┌─────┴──────┐
     │             │
Core Oracle    Annexes (on-demand)
(~2-4K tokens)  (pulled by reviewer)
```

### 4.2 Two-Tier Oracle Structure

#### Tier 1 — Core Oracle `PHASE 1`

Default payload sent to all reviewers. Target: 2–4K tokens.

```json
{
  "$schema": "forge-oracle-v0.2",
  "oracle_version": "0.2",
  "oracle_id": "oracle-001-iter-1",
  "timestamp": "2026-03-18T10:15:00Z",

  "task_context": {
    "mission": "Build user auth with JWT",
    "milestone": "milestone-001",
    "milestone_description": "Core auth endpoints",
    "task_id": "task-001",
    "task_description": "Implement POST /api/auth/login that validates credentials and returns JWT",
    "difficulty_class": "local-reasoning",
    "mission_mode": "delivery",
    "feature_list_progress": "4/14 complete",
    "milestone_progress": "2/4 tasks in milestone 1",
    "iteration": 1,
    "total_iterations_this_task": 1
  },

  "worker_identity": {
    "model": "qwen3.5-35b",
    "lora_version": null,
    "serving_config": "fp4-vllm",
    "historical_success_rate": {
      "overall": 0.72,
      "by_difficulty": {
        "mechanical": 1.0,
        "local-reasoning": 0.68,
        "architectural": 0.33,
        "uncertain": 0.0
      }
    }
  },

  "diff_summary": {
    "files_changed": 3,
    "files_added": 1,
    "files_deleted": 0,
    "insertions": 87,
    "deletions": 12,
    "functions_added": ["login(req, res)", "validateCredentials(email, password)", "generateToken(userId)"],
    "functions_modified": [],
    "functions_deleted": []
  },

  "codemap": {
    "changed_files": [
      {
        "path": "src/api/auth.ts",
        "language": "typescript",
        "signatures": [
          "export async function login(req: Request, res: Response): Promise<void>",
          "function validateCredentials(email: string, password: string): Promise<User | null>",
          "function generateToken(userId: string): string"
        ],
        "imports_added": ["bcrypt", "jsonwebtoken", "../db/users"],
        "exports_added": ["login"],
        "dependencies": ["src/db/users.ts", "src/utils/jwt.ts"]
      }
    ],
    "affected_files": [
      {
        "path": "src/routes/index.ts",
        "change_summary": "Added route /api/auth/login → auth.login"
      }
    ]
  },

  "mechanical_checks": {
    "lint": {"status": "pass", "warnings": 2, "errors": 0},
    "type_check": {"status": "pass", "errors": 0},
    "tests": {"status": "pass", "passed": 14, "failed": 0, "new_tests": 3, "coverage_delta": "+2.1%"},
    "build": {"status": "pass"},
    "desloppify_mechanical": {"score": 82, "delta": "+3", "new_issues": 1, "resolved_issues": 2}
  },

  "quality_delta": {
    "desloppify_mechanical_score": 82,
    "delta_from_previous": "+3",
    "new_issues": ["Duplicate validation logic in auth.ts and signup.ts"],
    "resolved_issues": ["Missing error handling in JWT generation", "Unused import in routes/index.ts"]
  },

  "worker_self_assessment": {
    "confidence": "medium",
    "concerns": [
      "JWT expiry time hardcoded — should be configurable",
      "No rate limiting on login endpoint"
    ],
    "decisions_made": [
      "Used bcrypt for password hashing (argon2 was alternative)",
      "Stored refresh token in httpOnly cookie"
    ],
    "tools_used": ["view_file", "edit_file", "create_file", "run_tests", "codemap"],
    "tool_call_count": 23,
    "tokens_consumed": 45000
  },

  "available_annexes": [
    "full_patch",
    "file:src/api/auth.ts",
    "file:src/routes/index.ts",
    "test_output",
    "prior_verdicts"
  ]
}
```

#### Tier 2 — Expandable Annexes `PHASE 1`

Reviewers pull these on demand. Not auto-included. In Phase 1, annexes are returned inline when requested. In Phase 2+, reviewers have tool calls to pull them.

| Annex | Content | When Pulled |
|-------|---------|-------------|
| `full_patch` | Complete unified diff | Reviewer needs line-level detail |
| `file:<path>` | Full file content or specific function body | Signature change is ambiguous |
| `test_output` | Full test runner output, stack traces, coverage diff | Test failures or coverage concerns |
| `prior_verdicts` | Previous reviewer feedback on this task (all iterations) | Multi-iteration task, reviewer needs history |
| `lint_details` | Full linter output with warnings | Lint warnings need inspection |

**Phase 1 implementation:** Annexes are pre-staged as files in `.forge/oracles/<oracle-id>/annexes/`. The reviewer prompt includes the `available_annexes` list. If the reviewer says "I need to see the full patch," the harness appends it to the conversation and re-queries. Simple request-response, no tool calling required.

**Phase 2+ implementation:** Reviewers get tool calls (`pull_annex(annex_id)`) to interactively request annexes. This is the "semantic zoom" pattern.

#### Extension Point: Visual/Multimodal Annexes `PHASE 2+`

```
available_annexes (Phase 2+):
  - "screenshot:before"      # Playwright screenshot before changes
  - "screenshot:after"       # Playwright screenshot after changes
  - "flame_graph"            # Performance profile
  - "dependency_graph"       # Visual dependency tree
```

Phase 1 is text-only. The annex system is designed to accept any content type without schema changes.

### 4.3 Oracle Storage `PHASE 1`

```
.forge/oracles/
├── oracle-001-iter-1/
│   ├── core.json           # Core Oracle (Tier 1)
│   ├── annexes/
│   │   ├── full_patch.diff
│   │   ├── file_src_api_auth_ts.txt
│   │   ├── test_output.txt
│   │   └── prior_verdicts.json
│   └── metadata.json       # Generation timing, token counts
├── oracle-001-iter-2/
│   └── ...
```

### 4.4 Oracle Generation Pipeline `PHASE 1`

Steps executed by the Oracle Generator (mechanical, no LLM required for core):

1. **`git diff`** — compute diff against main branch
2. **Tree-sitter parse** — extract AST for all changed files; produce signatures, imports, exports, call graph edges
3. **Dependency analysis** — follow imports to identify affected files (1 hop)
4. **Mechanical checks** — run lint, typecheck, test suite, build; capture structured results
5. **Desloppify mechanical scan** — tree-sitter based quality metrics on changed files
6. **Worker self-assessment** — extract from worker's final message (structured JSON output enforced by system prompt)
7. **Assemble Core Oracle** — combine above into the Tier 1 JSON structure
8. **Stage annexes** — write full patch, file contents, test output to annex directory

**Interface:**
- Input: task ID, worktree path, main branch ref
- Output: Oracle JSON (Tier 1) + staged annex files (Tier 2)
- Side effects: writes to `.forge/oracles/`

---

## 5. Gate Engine `PHASE 1 (simple) + PHASE 2+ (full)`

### 5.1 Gate Engine Overview

The Gate Engine is a **trust system**, not a review scheduler. It determines review intensity based on worker trust and task blast radius.

### 5.2 Difficulty Classifier `PHASE 1`

Runs before task execution begins. Every task is classified.

| Class | Definition | Examples | Default Gate (Phase 1) |
|-------|-----------|----------|----------------------|
| `mechanical` | Lint fix, dep bump, config wire, type annotation, formatting | Fix ESLint errors, add missing type, update package version | Single reviewer |
| `local-reasoning` | Implement endpoint, write tests, refactor module, fix bug with clear repro | Build login API, write unit tests for auth, fix off-by-one | Single reviewer |
| `architectural` | Cross-module refactor, new abstraction, schema migration, auth/payment flow | Redesign data layer, add new service boundary, DB migration | Single reviewer + escalate to 2nd on any concern |
| `uncertain` | Ambiguous scope, research-dependent, novel pattern | "Make the app faster," integrate unknown library | Frontier-assisted planning before execution |

**Phase 1 implementation:**
- Planner model classifies difficulty at task creation time
- Human can override via `forge task --difficulty <class>`
- Classification stored in task state

**Phase 2+ implementation:**
- Classifier becomes a trained function using historical task data
- Features: file paths touched, AST diff complexity, keyword analysis, prior task success rates for similar descriptions
- Misclassification detection: if a `mechanical` task fails review for `architectural-drift`, log the misclassification and retrain

**Classifier interface:**
- Input: task description (string), file paths hint (optional), codemap of affected area (optional)
- Output: `{ "difficulty_class": "local-reasoning", "confidence": 0.85, "rationale": "Implements a single endpoint with clear spec" }`

### 5.3 Phase 1 Gate Flow `PHASE 1`

```
Worker completes task
  │
  ▼
Mechanical checks (lint, typecheck, tests, Desloppify mechanical)
  │
  ├── FAIL → return to worker with structured errors (no frontier call)
  │
  ▼
Oracle generation
  │
  ▼
Single frontier reviewer receives Core Oracle
  │
  ├── PASS → propose commit (human merges in shadow mode)
  │
  ├── FAIL → structured TODO sent to worker:
  │          {
  │            "verdict": "FAIL",
  │            "error_taxonomy_tags": ["missing-tests"],
  │            "issues": [
  │              {
  │                "file": "src/api/auth.ts",
  │                "line_range": [23, 35],
  │                "severity": "blocking",
  │                "what": "No test for invalid credentials case",
  │                "why": "Login endpoint must handle wrong password gracefully",
  │                "fix": "Add test: POST /login with wrong password returns 401",
  │                "acceptance_criteria": "Test exists and passes"
  │              }
  │            ]
  │          }
  │
  ├── FAIL ×2 → escalate: second frontier reviewer sees Core Oracle +
  │             first reviewer's verdict as annex
  │
  └── FAIL ×3 → recovery mode (§3.3)
```

**Reviewer configuration (Phase 1):**
```yaml
# .forge/config.yaml → gate section
gate:
  phase: 1
  default_reviewer: "sonnet-4.6"
  escalation_reviewer: "gpt-5.3-codex"
  max_iterations: 3
  recovery_threshold: 3
  shadow_mode: true
```

### 5.4 Phase 2+ Gate Flow — Trust × Blast-Radius Matrix `PHASE 2+`

```
                      BLAST RADIUS
                      Low                High
                ┌───────────────────┬───────────────────┐
                │                   │                   │
   High TRUST   │  AUTO-MERGE       │  SINGLE REVIEWER  │
                │  Mechanical       │  + mechanical     │
                │  checks only.     │  checks.          │
                │  No frontier.     │                   │
                │                   │                   │
                ├───────────────────┼───────────────────┤
                │                   │                   │
   Low TRUST    │  SINGLE REVIEWER  │  FULL BOARD       │
                │  + mechanical     │  Independent      │
                │  checks.          │  reviewers +      │
                │                   │  chairman          │
                │                   │  synthesis.        │
                │                   │                   │
                └───────────────────┴───────────────────┘
```

**Trust computation (Phase 2+):**
```
trust(worker, task_type) = f(
  worker.identity,                    # model + LoRA version + serving config
  worker.success_rate[task_type],     # historical first-pass rate for this type
  worker.consecutive_successes,       # streak length (resets on failure)
  worker.recent_failure_severity      # worst error taxonomy tag in last N tasks
)
```

Trust increases with consecutive successes, resets on certain failure types (architectural-drift resets harder than missing-tests).

**Blast radius computation (Phase 2+, mechanical):**
```
blast_radius(task) = f(
  files_touched.count,
  max(dependency_depth(f) for f in files_touched),
  any(f in SENSITIVE_PATHS for f in files_touched),  # auth, payments, config
  diff_size_lines
)

SENSITIVE_PATHS defined in .forge/config.yaml
```

**Full board review (Phase 2+):**
```
Oracle Generated
  │
  ├──▶ Reviewer A (Sonnet 4.6): architectural coherence, design patterns
  │
  ├──▶ Reviewer B (Codex / GPT): correctness, test coverage, edge cases
  │
  │    (parallel, independent — they don't see each other's reviews)
  │
  ▼
Chairman (Opus 4.6): receives both reviews + Oracle
  │
  ├── PASS → merge
  ├── FAIL → synthesized TODO (best of both reviews)
  └── SPLIT → conflicting reviews, human paged
```

### 5.5 Shadow Mode `PHASE 1`

Phase 1 operates entirely in shadow mode.

**Behavior:**
- FORGE executes end-to-end autonomously (plan → code → review → verdict)
- On PASS: FORGE proposes a commit with full context (Oracle, verdict, diff)
- Human is the final merger every time (`forge approve` / `forge reject`)
- Every human merge/reject decision is logged as a training signal

**Shadow mode data capture:**
```json
{
  "shadow_event": {
    "task_id": "task-001",
    "oracle_id": "oracle-001-iter-1",
    "gate_verdict": "PASS",
    "human_decision": "approved",
    "human_feedback": null,
    "timestamp": "2026-03-18T10:20:00Z",
    "time_to_decision_seconds": 120
  }
}
```

Stored in `.forge/shadow-log.jsonl` (append-only).

**Graduation criteria (Phase 2+):**
- Minimum 100 tasks completed in shadow mode
- Human override rate below 5%
- No task category showing systematic human rejection
- Human explicitly enables auto-merge per task type / trust level

### 5.6 Verdict Schema `PHASE 1`

```json
{
  "$schema": "forge-verdict-v0.2",
  "verdict_id": "verdict-001-iter-1",
  "oracle_id": "oracle-001-iter-1",
  "task_id": "task-001",
  "timestamp": "2026-03-18T10:16:00Z",
  "reviewer": {
    "model": "claude-sonnet-4.6",
    "provider": "anthropic",
    "role": "primary_reviewer"
  },
  "verdict": "FAIL",
  "error_taxonomy_tags": ["missing-tests", "incorrect-logic"],
  "summary": "Login endpoint handles happy path but lacks error case coverage and has a logic issue in token expiry calculation.",
  "issues": [
    {
      "id": "issue-001",
      "file": "src/api/auth.ts",
      "line_range": [45, 52],
      "severity": "blocking",
      "category": "incorrect-logic",
      "what": "Token expiry calculated as Date.now() + expiry, but expiry is in seconds and Date.now() returns milliseconds",
      "why": "Tokens will expire 1000x sooner than intended, breaking all auth flows",
      "fix": "Use Date.now() + (expiry * 1000) or use a library like jsonwebtoken's built-in expiresIn",
      "acceptance_criteria": "Token with 1h expiry is valid for ~60 minutes (test with time mock)"
    },
    {
      "id": "issue-002",
      "file": "src/api/auth.ts",
      "line_range": [23, 35],
      "severity": "blocking",
      "category": "missing-tests",
      "what": "No test for invalid credentials, expired tokens, or malformed requests",
      "why": "Auth endpoints are security-critical; untested error paths are vulnerabilities",
      "fix": "Add tests for: wrong password → 401, missing email → 400, malformed body → 400",
      "acceptance_criteria": "3+ error case tests exist and pass"
    }
  ],
  "annexes_pulled": ["full_patch"],
  "oracle_sections_referenced": ["diff_summary", "codemap", "mechanical_checks", "worker_self_assessment"],
  "tokens_consumed": {
    "input": 3200,
    "output": 850
  }
}
```

Stored in `.forge/verdicts/<verdict-id>.json`.

---

## 6. Enforcement Layer `PHASE 1`

Three architecturally distinct enforcement systems with different trigger conditions, compute profiles, and output schemas.

### 6.1 Layer 1: Mechanical Hooks (Real-Time) `PHASE 1`

Hooks run outside the model — the model cannot override them. They execute on every relevant tool call.

```yaml
# .forge/hooks.yaml
pre_edit:
  - action: syntax_check
    description: "Parse file with tree-sitter before applying edit"
    on_fail: reject_edit
    error_format: |
      EDIT REJECTED: Syntax error at line {line}, column {col}.
      Error: {message}
      The edit was not applied. Fix the syntax and try again.

post_edit:
  - action: auto_format
    description: "Run formatter after every successful edit"
    formatter: auto  # Detects from project config (prettier, black, rustfmt, etc.)

  - action: secret_scan
    description: "Check for hardcoded secrets in edited content"
    patterns:
      - "(password|secret|api_key|token)\\s*=\\s*['\"][^'\"]{8,}['\"]"
      - "-----BEGIN (RSA |EC )?PRIVATE KEY-----"
      - "AKIA[0-9A-Z]{16}"
    on_fail: reject_edit
    error_format: |
      EDIT REJECTED: Potential secret detected at line {line}.
      Matched pattern: {pattern_name}
      Secrets must come from environment variables or the config system.
      Use: process.env.{SUGGESTED_VAR} or config.get('secrets.{name}')

pre_command:
  - action: allowlist_check
    description: "Block commands not in approved list"
    allowed_patterns:
      - "npm (test|run|install|build|lint)"
      - "python -m pytest"
      - "cargo (test|build|clippy)"
      - "git (status|diff|log|add|commit)"
      - "cat|head|tail|wc|grep|find|ls"
    blocked_patterns:
      - "rm -rf"
      - "curl.*\\| *(bash|sh)"
      - "sudo"
      - "chmod 777"
      - "eval"
    on_fail: reject_command
    error_format: |
      COMMAND BLOCKED: "{command}" is not in the allowed command list.
      Allowed commands: {allowed_list}
      If you need this command, explain why and the human will review.

post_commit:
  - action: desloppify_mechanical
    description: "Run tree-sitter quality scan on committed files"
    # See Layer 3a

  - action: architectural_lint
    description: "Run architectural linter rules"
    # See Layer 2
```

**Interface:**
- Input: tool call type + arguments (before) or tool call result (after)
- Output: `{ "allowed": true }` or `{ "allowed": false, "error": "...", "suggestion": "..." }`
- Latency budget: < 100ms per hook (must not perceptibly slow the worker)

### 6.2 Layer 2: Architectural Linters (CI-Style) `PHASE 1`

Custom linters that encode project-specific structural rules. Error messages are written for agents — they explain WHY the rule exists and the CORRECT approach.

```yaml
# .forge/architecture.yaml
version: "0.2"

sensitive_paths:
  - "src/auth/**"
  - "src/payments/**"
  - "src/config/**"
  - "migrations/**"

rules:
  - id: "no-cross-module-imports"
    name: "No cross-module imports"
    pattern: "import.*from.*modules/((?!${current_module}).)*/internal"
    files: "src/modules/**"
    severity: "error"
    message: |
      VIOLATION: Cross-module internal import detected.
      File: {file}:{line}
      Import: {matched_text}

      WHY: Modules must communicate through the public API layer (src/api/),
      not import each other's internals directly. This prevents tight coupling
      and allows modules to evolve independently.

      FIX: Move the shared logic to src/shared/ or expose it through the
      module's public API in src/api/{module_name}.ts

      EXAMPLE:
        WRONG:  import { hashPassword } from '../modules/auth/internal/crypto'
        RIGHT:  import { hashPassword } from '../shared/crypto'
        RIGHT:  import { AuthService } from '../api/auth'

  - id: "handler-error-boundary"
    name: "API handlers must have error boundaries"
    files: "src/api/**/*.ts"
    must_contain: "try.*catch|ErrorBoundary|withErrorHandler"
    severity: "error"
    message: |
      VIOLATION: API handler missing error boundary.
      File: {file}

      WHY: Unhandled errors crash the server and expose stack traces to clients.
      Every API handler must catch exceptions and return structured error responses.

      FIX: Wrap handler body in try/catch or use the withErrorHandler() wrapper.

      EXAMPLE:
        export const handler = withErrorHandler(async (req, res) => {
          // your code here — errors are caught automatically
        });

  - id: "no-hardcoded-secrets"
    name: "No hardcoded secrets"
    pattern: "(password|secret|api_key|token|private_key)\\s*=\\s*['\"][^'\"]{8,}['\"]"
    severity: "error"
    message: |
      VIOLATION: Hardcoded secret detected.
      File: {file}:{line}

      WHY: Secrets must come from environment variables or the config system.
      Hardcoded secrets get committed to git and are a security vulnerability.

      FIX: Use process.env.{SECRET_NAME} or config.get('secrets.{name}')

  - id: "test-file-naming"
    name: "Test files must follow naming convention"
    files: "src/**/*.test.*"
    custom_check: "test_file_matches_source"
    severity: "warning"
    message: |
      WARNING: Test file {file} does not correspond to a source file.
      Expected source: {expected_source}

      WHY: Test files should mirror the source tree for discoverability.
      FIX: Rename to match the source file it tests.
```

**Execution:**
- Runs on `post_commit` hook and as part of CI-style checks before Oracle generation
- Rules are evaluated via regex matching and tree-sitter AST analysis
- Results included in Oracle `mechanical_checks` section

**Interface:**
- Input: list of changed files, file contents
- Output: `{ "violations": [...], "warnings": [...], "pass": true|false }`
- Each violation includes: rule ID, file, line, severity, agent-readable message

### 6.3 Layer 3a: Desloppify Mechanical (Continuous) `PHASE 1`

Zero-GPU, tree-sitter-based quality detection. Runs in hooks on every commit.

**Detectors:**

| Detector | Method | Output |
|----------|--------|--------|
| Dead code | Tree-sitter: unreferenced functions, unused imports, unreachable branches | `{ "file": "...", "line": N, "type": "dead_code", "detail": "Function foo() is never called" }` |
| Duplication | AST subtree similarity hashing (min 6 statements) | `{ "file_a": "...", "file_b": "...", "similarity": 0.92, "lines_a": [10,25], "lines_b": [30,45] }` |
| Cyclomatic complexity | Count decision points per function (tree-sitter) | `{ "file": "...", "function": "...", "complexity": 15, "threshold": 10 }` |
| Function length | Line count per function body | `{ "file": "...", "function": "...", "lines": 85, "threshold": 50 }` |
| Nesting depth | Max indent level in function body | `{ "file": "...", "function": "...", "depth": 6, "threshold": 4 }` |

**Score computation:**
```
mechanical_score = 100 - (
  dead_code_issues * 1 +
  duplication_issues * 2 +
  complexity_violations * 3 +
  length_violations * 2 +
  nesting_violations * 2
)
# Clamped to [0, 100]
```

**Interface:**
- Input: list of changed files (or full repo for `forge quality`)
- Output: `{ "score": 82, "delta": "+3", "issues": [...], "resolved": [...] }`
- Latency: < 2 seconds for typical commit (purely mechanical)

### 6.4 Layer 3b: Desloppify Subjective (Milestone-Gated) `PHASE 1`

LLM-dependent quality review. Runs at milestone boundaries and on `forge quality` manual trigger.

**Assesses:**
- Naming quality (variables, functions, modules — are names descriptive and consistent?)
- Abstraction boundaries (is the right code in the right module?)
- Module cohesion (does each module do one thing?)
- Pattern consistency (does new code match established patterns?)
- API design quality (are interfaces clean and predictable?)

**Execution:**
- Scheduled when GPU is not serving workers (milestone boundary)
- Uses the planner model (DGX Spark #1) or a dedicated quality model
- Receives: full codemap + changed files since last subjective scan
- Produces: quality score, issue list, recommendations

**Output schema:**
```json
{
  "desloppify_subjective": {
    "score": 76,
    "delta_from_previous": "-2",
    "scan_scope": "milestone-001",
    "issues": [
      {
        "category": "naming",
        "file": "src/api/auth.ts",
        "detail": "Function 'doIt()' should be renamed to describe its action (e.g., 'refreshExpiredToken')",
        "severity": "suggestion",
        "effort": "trivial"
      },
      {
        "category": "abstraction",
        "file": "src/api/auth.ts",
        "detail": "Token generation and validation should be in a dedicated TokenService, not inline in the route handler",
        "severity": "recommendation",
        "effort": "moderate"
      }
    ],
    "model_used": "nemotron-3-super-120b",
    "tokens_consumed": 8500,
    "timestamp": "2026-03-18T12:00:00Z"
  }
}
```

**Gate interaction:**
- If subjective score drops below threshold (configurable, default: 60): block milestone advancement
- Worker receives Desloppify issues as TODO items, resolves one at a time
- Score must reach threshold before next milestone begins

---

## 7. Boundary Measurement System `PHASE 1`

### 7.1 Overview

Boundary measurement is a **core feature**, not a metric. It is what makes FORGE a contribution to the field rather than just another agentic harness.

Every task execution automatically records the data needed for boundary analysis. No manual tagging required beyond the initial difficulty classification.

### 7.2 Data Capture `PHASE 1`

Every completed task produces a boundary record:

```json
{
  "$schema": "forge-boundary-record-v0.2",
  "task_id": "task-001",
  "mission_id": "mission-001",
  "mission_mode": "delivery",
  "timestamp": "2026-03-18T10:20:00Z",

  "classification": {
    "difficulty_class": "local-reasoning",
    "classified_by": "planner",
    "classification_confidence": 0.85
  },

  "worker": {
    "model": "qwen3.5-35b",
    "lora_version": null,
    "serving_config": "fp4-vllm"
  },

  "outcome": {
    "first_pass_success": false,
    "total_iterations": 2,
    "final_verdict": "PASS",
    "error_taxonomy_tags": ["missing-tests"],
    "frontier_intervention_type": "reviewer_caught_missing_coverage",
    "recovery_mode_activated": false
  },

  "cost": {
    "local_tokens": 82000,
    "frontier_tokens_in": 6400,
    "frontier_tokens_out": 1700,
    "frontier_cost_usd": 0.04,
    "wall_clock_seconds": 1200
  },

  "oracle_utilization": {
    "core_sections_referenced": ["diff_summary", "codemap", "worker_self_assessment"],
    "annexes_pulled": ["full_patch"]
  }
}
```

Stored as append-only JSONL in `.forge/boundary-data.jsonl` and also ingested into DuckDB for querying.

### 7.3 `forge boundary` Output `PHASE 1`

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

BY WORKER:
  qwen3.5-35b (base)      18/30 (60%)
  qwen3.5-35b (lora-v2)   10/17 (59%)   # LoRA not yet showing improvement

BOUNDARY MOVEMENT (30-day trend):
  mechanical:       100% → 100% (stable)
  local-reasoning:   58% →  73% (+15%, LoRA v2 deployed day 12)
  architectural:     29% →  36% (+7%, skill crystallization)

TOP FRONTIER CORRECTIONS:
  1. Missing error boundary in auth flow (architectural)
  2. Incorrect transaction isolation level (local-reasoning)
  3. Test coverage gap in edge case (local-reasoning)

COST SUMMARY:
  Total frontier spend:     $2.14
  Average per task:         $0.046
  Cost per frontier fix:    $0.11
  Estimated local-only:     $0.00 (hardware already owned)
```

### 7.4 Error Taxonomy `PHASE 1`

Every failure is tagged with one or more categories by the frontier reviewer.

| Tag | Definition | Example |
|-----|-----------|---------|
| `tool-misuse` | Worker used an ACI tool incorrectly | Passed wrong arguments to file editor |
| `navigation-failure` | Worker couldn't find the right file/function | Edited wrong module, missed import |
| `incorrect-logic` | Code compiles but logic is wrong | Off-by-one, wrong comparison operator |
| `missing-tests` | Implementation works but tests absent/insufficient | No edge case coverage |
| `architectural-drift` | Code violates established patterns or boundaries | Bypassed service layer, direct DB from handler |
| `context-confusion` | Worker confused files, mixed up names, lost state | Used stale reference, wrong function signature |
| `flaky-validation` | Test or check is non-deterministic | Race condition in test, timing-dependent assertion |

**Taxonomy storage:** Tags are stored on each verdict and each boundary record. Queryable via DuckDB.

**`forge taxonomy` output:**
```
$ forge taxonomy --period 30d

Error Taxonomy Distribution — last 30 days (19 failures)

  missing-tests        7  (36.8%)  ████████████
  incorrect-logic      4  (21.1%)  ███████
  architectural-drift  3  (15.8%)  █████
  navigation-failure   2  (10.5%)  ████
  context-confusion    2  (10.5%)  ████
  tool-misuse          1  (5.3%)   ██
  flaky-validation     0  (0.0%)

TREND:
  missing-tests:       ↓ was 45% last period (skill "always-test-errors" deployed)
  incorrect-logic:     ↑ was 15% last period (investigate)
```

### 7.5 Research vs. Delivery Mission Modes `PHASE 1`

Two explicit mission classes. Set at mission creation time.

| Mode | Optimization Target | Key Metrics |
|------|--------------------|----|
| `delivery` | Successful software completion | Task completion rate, wall-clock time, cost per feature |
| `research` | Learning about orchestration/routing/models | Boundary movement data, error taxonomy coverage, model comparison data |

Research missions that deliberately route tasks to weaker models for comparison data should not penalize delivery metrics. The mode tag propagates to all boundary records.

---

## 8. Benchmark Cartridges `PHASE 1`

### 8.1 Purpose

A fixed suite of 20–50 representative tasks for controlled comparison. When you change any harness variable (new model, new LoRA, new Oracle format, new gate policy), re-run the benchmark suite and compare apples to apples.

### 8.2 Cartridge Structure `PHASE 1`

```
.forge/benchmarks/
├── cartridge-manifest.yaml     # List of all cartridges with metadata
├── add-endpoint-01/
│   ├── task.yaml               # Task description + expected behavior
│   ├── repo-snapshot.tar.gz    # Starting state (or git ref)
│   ├── success-criteria.yaml   # Mechanical checks that must pass
│   └── expected-oracle.json    # Reference Oracle (for Oracle quality testing)
├── refactor-module-01/
│   └── ...
├── fix-test-01/
│   └── ...
└── ...
```

**Cartridge manifest:**
```yaml
# .forge/benchmarks/cartridge-manifest.yaml
version: "0.2"
cartridges:
  - id: "add-endpoint-01"
    name: "Add REST endpoint (CRUD for users)"
    difficulty_class: "mechanical"
    category: "add-endpoint"
    estimated_tokens: 30000
    description: "Add GET/POST/PUT/DELETE for /api/users with validation"

  - id: "refactor-module-01"
    name: "Extract auth logic into service layer"
    difficulty_class: "architectural"
    category: "refactor-module"
    estimated_tokens: 50000
    description: "Move inline auth logic from route handlers into AuthService class"

  - id: "fix-test-01"
    name: "Fix failing test from error message"
    difficulty_class: "local-reasoning"
    category: "fix-test"
    estimated_tokens: 15000
    description: "Test fails with 'Cannot read property of undefined'. Fix the source code."

  # ... 17-47 more cartridges
```

**Task definition:**
```yaml
# .forge/benchmarks/add-endpoint-01/task.yaml
id: "add-endpoint-01"
name: "Add REST endpoint (CRUD for users)"
description: |
  Add a full CRUD API for users at /api/users.
  - GET /api/users — list all users (paginated)
  - GET /api/users/:id — get single user
  - POST /api/users — create user (validate email, name required)
  - PUT /api/users/:id — update user
  - DELETE /api/users/:id — soft delete user
  Use the existing database connection and follow established patterns in src/api/.
difficulty_class: "mechanical"
timeout_seconds: 600
max_iterations: 5
```

**Success criteria:**
```yaml
# .forge/benchmarks/add-endpoint-01/success-criteria.yaml
mechanical_checks:
  lint: must_pass
  type_check: must_pass
  tests: must_pass
  build: must_pass

required_files:
  - pattern: "src/api/users.*"
    min_count: 1

required_tests:
  - pattern: "src/**/*.test.*"
    must_contain: ["users", "CRUD"]
    min_count: 1

required_endpoints:
  - method: GET
    path: "/api/users"
  - method: GET
    path: "/api/users/:id"
  - method: POST
    path: "/api/users"
  - method: PUT
    path: "/api/users/:id"
  - method: DELETE
    path: "/api/users/:id"
```

### 8.3 Benchmark Results Schema `PHASE 1`

```json
{
  "$schema": "forge-benchmark-result-v0.2",
  "run_id": "bench-run-20260318-001",
  "tag": "qwen35-base-oracle-v2",
  "timestamp": "2026-03-18T14:00:00Z",
  "harness_config": {
    "worker_model": "qwen3.5-35b",
    "lora_version": null,
    "reviewer_model": "claude-sonnet-4.6",
    "oracle_version": "0.2",
    "hooks_config_hash": "sha256:def456...",
    "architecture_rules_hash": "sha256:789abc..."
  },
  "summary": {
    "total_cartridges": 25,
    "passed_first_try": 14,
    "passed_with_iteration": 8,
    "failed": 3,
    "first_pass_rate": 0.56,
    "overall_pass_rate": 0.88,
    "avg_iterations": 1.6,
    "total_local_tokens": 1250000,
    "total_frontier_tokens": 85000,
    "total_frontier_cost_usd": 1.87,
    "total_wall_clock_seconds": 14400
  },
  "by_difficulty": {
    "mechanical": {"total": 8, "first_pass": 8, "rate": 1.0},
    "local-reasoning": {"total": 10, "first_pass": 5, "rate": 0.5},
    "architectural": {"total": 5, "first_pass": 1, "rate": 0.2},
    "uncertain": {"total": 2, "first_pass": 0, "rate": 0.0}
  },
  "by_category": {
    "add-endpoint": {"total": 4, "first_pass": 3, "rate": 0.75},
    "refactor-module": {"total": 3, "first_pass": 1, "rate": 0.33},
    "fix-test": {"total": 3, "first_pass": 2, "rate": 0.67},
    "add-e2e": {"total": 3, "first_pass": 1, "rate": 0.33},
    "wire-config": {"total": 3, "first_pass": 3, "rate": 1.0},
    "repair-typing": {"total": 3, "first_pass": 3, "rate": 1.0},
    "implement-feature": {"total": 3, "first_pass": 1, "rate": 0.33},
    "patch-lint": {"total": 3, "first_pass": 3, "rate": 1.0}
  },
  "error_taxonomy": {
    "missing-tests": 4,
    "incorrect-logic": 2,
    "architectural-drift": 2,
    "navigation-failure": 1,
    "context-confusion": 1
  },
  "cartridge_results": [
    {
      "cartridge_id": "add-endpoint-01",
      "status": "passed",
      "first_pass": true,
      "iterations": 1,
      "local_tokens": 32000,
      "frontier_tokens": 3200,
      "wall_clock_seconds": 480,
      "error_taxonomy_tags": [],
      "oracle_id": "oracle-bench-add-endpoint-01",
      "trace_id": "trace-bench-add-endpoint-01"
    }
  ]
}
```

Stored in `.forge/benchmark-results/<run-id>.json` with full trace data cross-referenced by `trace_id`.

### 8.4 Benchmark Categories `PHASE 1`

Build the initial suite with these categories (minimum 2 cartridges each):

| Category | Difficulty Class | Description |
|----------|-----------------|-------------|
| `add-endpoint` | mechanical | Add REST/GraphQL endpoint with validation |
| `refactor-module` | architectural | Extract/restructure module boundaries |
| `fix-test` | local-reasoning | Fix failing test from error message |
| `add-e2e` | local-reasoning | Add end-to-end test for existing flow |
| `wire-config` | mechanical | Thread a config value through the stack |
| `repair-typing` | mechanical | Fix type errors from compiler output |
| `implement-feature` | local-reasoning | Build feature from spec (multi-file) |
| `patch-lint` | mechanical | Fix linting violations |
| `schema-migration` | architectural | Add/modify database schema + migration |
| `add-auth` | architectural | Add authentication to existing endpoint |

---

## 9. Skill Crystallization Pipeline `PHASE 1 (Tiers 1-3) + PHASE 2+ (Tiers 4-5)`

### 9.1 Pipeline Overview

Skills crystallize downward from soft (prompt) to hard (weights). Each tier is independently valuable. The system promotes skills downward as confidence increases.

```
Tier 0: OBSERVATION                                      PHASE 1
  │  Raw data: "Reviewer caught missing rate-limit on auth endpoint"
  │  Lifetime: single event | Cost: zero (logging)
  │
  ▼
Tier 1: PROMPT SKILL                                     PHASE 1
  │  Injected into worker system prompt when relevant
  │  Lifetime: session to days | Cost: tokens (prompt overhead)
  │  Storage: in-memory + .forge/skills/prompts/
  │
  ▼
Tier 2: YAML PATTERN                                     PHASE 1
  │  Structured rule with examples and counter-examples
  │  Lifetime: weeks to months | Cost: tokens (loaded contextually)
  │  Storage: .forge/skills/patterns/
  │
  ▼
Tier 3: ARCHITECTURAL LINTER RULE                        PHASE 1
  │  Tree-sitter AST rule or regex rule in .forge/architecture.yaml
  │  Lifetime: months to permanent | Cost: zero (AST check)
  │  Storage: .forge/architecture.yaml (appended)
  │
  ▼
Tier 4: GENERATED TEST (executable invariant)            PHASE 2+
  │  Auto-generated test that enforces the learned behavior
  │  Lifetime: permanent | Cost: zero (test suite)
  │  Storage: project test directory
  │
  ▼
Tier 5: LoRA WEIGHT                                      PHASE 2+
  │  Baked into model weights via fine-tuning
  │  Lifetime: permanent (until model swap)
  │  Cost: zero at inference (already in weights)
  │  Storage: .forge/lora/ + model serving config
```

### 9.2 Tier Schemas

**Tier 1 — Prompt Skill:**
```yaml
# .forge/skills/prompts/rate-limit-auth.yaml
id: "skill-prompt-001"
tier: 1
name: "Rate limit on auth endpoints"
learned_from: "verdict-015-iter-1"
created_at: "2026-03-18T10:00:00Z"
confidence: 0.6
applications: 0
successes: 0
content: "All auth endpoints in this codebase must include rate limiting middleware. Apply rateLimiter({windowMs: 15*60*1000, max: 5}) before the route handler."
applicable_when:
  file_patterns: ["src/api/auth/**", "src/routes/auth*"]
  task_keywords: ["auth", "login", "signup", "password", "token"]
```

**Tier 2 — YAML Pattern:**
```yaml
# .forge/skills/patterns/auth-endpoint-pattern.yaml
id: "skill-pattern-001"
tier: 2
name: "Auth Endpoint Complete Pattern"
promoted_from: "skill-prompt-001"
created_at: "2026-03-19T10:00:00Z"
confidence: 0.85
applications: 8
successes: 7
pattern: |
  When implementing any authentication endpoint in this codebase:
  1. Use bcrypt for password hashing (not argon2 — bcrypt is the project standard)
  2. Store refresh tokens in httpOnly cookies
  3. JWT expiry comes from config.get('auth.jwt_expiry'), not hardcoded
  4. All auth endpoints must use the withErrorHandler() wrapper
  5. Rate limiting middleware must be applied: rateLimiter({windowMs: 15*60*1000, max: 5})
  6. Always write tests for: valid credentials, invalid credentials, missing fields, expired token
examples:
  - task: "Implement login endpoint"
    key_files: ["src/api/auth/login.ts", "src/middleware/rateLimiter.ts"]
counter_examples:
  - mistake: "Hardcoded JWT expiry to '1h'"
    correction: "Use config.get('auth.jwt_expiry')"
applicable_when:
  file_patterns: ["src/api/auth/**", "src/routes/auth*"]
  task_keywords: ["auth", "login", "signup", "password", "token", "JWT"]
```

**Tier 3 — Architectural Linter Rule:**
```yaml
# Appended to .forge/architecture.yaml
- id: "auth-rate-limit"
  name: "Auth endpoints must have rate limiting"
  promoted_from: "skill-pattern-001"
  created_at: "2026-03-25T10:00:00Z"
  files: "src/api/auth/**/*.ts"
  must_contain: "rateLimiter|rateLimit|rate_limit"
  severity: "error"
  message: |
    VIOLATION: Auth endpoint missing rate limiting.
    File: {file}

    WHY: Auth endpoints are brute-force targets. Rate limiting is mandatory
    on all routes in src/api/auth/.

    FIX: Add rateLimiter middleware before the route handler:
      router.post('/login', rateLimiter({windowMs: 15*60*1000, max: 5}), loginHandler)

    LEARNED FROM: Reviewer caught this pattern 7 times. Now enforced mechanically.
```

### 9.3 Promotion Logic `PHASE 1`

```
Tier 0 → Tier 1:
  Trigger: Same pattern observed N times (default N=2)
  Who decides: Harness (automatic)
  Validation: None — prompt skills are cheap to try

Tier 1 → Tier 2:
  Trigger: Prompt skill applied M times successfully (default M=5)
  Who decides: Harness (automatic) with human review flag
  Validation: Success = task passed review without the same error recurring

Tier 2 → Tier 3:
  Trigger: YAML pattern stable for P applications (default P=10) AND
           pattern is expressible as structural check (AST/regex)
  Who decides: Harness proposes, human approves (Phase 1)
               Harness proposes, frontier validates (Phase 2+)
  Validation: Rule must not produce false positives on existing passing code
```

**Phase 2+ promotions (Tier 4 and 5) are design targets only:**

```
Tier 3 → Tier 4 (Generated Test):                       PHASE 2+
  Trigger: Linter rule proven stable + behavior is testable
  Who decides: Frontier model generates test, harness validates it passes
  Validation: Generated test must pass on current codebase

Tier 4 → Tier 5 (LoRA Weight):                          PHASE 2+
  Trigger: Sufficient accumulated training data (100+ examples)
  Who decides: Human initiates fine-tuning run
  Validation: Benchmark cartridge regression test
```

### 9.4 Skill Injection `PHASE 1`

When a worker starts a task, the harness:

1. Matches task description + file paths against all Tier 1 and Tier 2 skills
2. Injects matching skills into the worker system prompt (ordered by confidence, max 5 skills, max 500 tokens total)
3. Tier 3 rules are enforced mechanically — they don't need injection
4. Logs which skills were injected for later analysis

**Interface:**
- Input: task description, file paths hint, skill database
- Output: list of skill IDs + concatenated skill text for system prompt injection

---

## 10. Observability System `PHASE 1`

### 10.1 Stack

```
Worker / Orchestrator / Gate Engine / Oracle Generator
  │
  │  OpenTelemetry spans
  │
  ▼
Local OTel Collector
  │
  ▼
DuckDB (.forge/traces/forge.duckdb)
  │
  ├── Agent self-query (SQL via ACI tool)
  ├── forge log / forge metrics / forge boundary
  ├── forge digest (daily summary generation)
  └── Dashboard (Phase 2+ TUI)
```

### 10.2 Trace Schema `PHASE 1`

```sql
-- Core spans table
CREATE TABLE spans (
  span_id       VARCHAR PRIMARY KEY,
  trace_id      VARCHAR NOT NULL,
  parent_span_id VARCHAR,
  span_name     VARCHAR NOT NULL,
  service       VARCHAR NOT NULL,  -- 'worker', 'orchestrator', 'gate', 'oracle', 'enforcement'
  start_time    TIMESTAMP NOT NULL,
  end_time      TIMESTAMP,
  duration_ms   INTEGER,
  status        VARCHAR,           -- 'ok', 'error'
  attributes    JSON                -- Flexible key-value pairs
);

-- Model interactions
CREATE TABLE model_calls (
  call_id       VARCHAR PRIMARY KEY,
  span_id       VARCHAR REFERENCES spans(span_id),
  model         VARCHAR NOT NULL,
  provider      VARCHAR NOT NULL,  -- 'local', 'anthropic', 'openai', 'xai'
  role          VARCHAR NOT NULL,  -- 'worker', 'planner', 'reviewer', 'chairman', 'quality'
  tokens_in     INTEGER NOT NULL,
  tokens_out    INTEGER NOT NULL,
  latency_ms    INTEGER NOT NULL,
  cost_usd      DECIMAL(10,6),
  temperature   DECIMAL(3,2),
  lora_version  VARCHAR
);

-- Tool calls
CREATE TABLE tool_calls (
  call_id       VARCHAR PRIMARY KEY,
  span_id       VARCHAR REFERENCES spans(span_id),
  tool_name     VARCHAR NOT NULL,
  arguments     JSON,
  result_status VARCHAR NOT NULL,  -- 'success', 'error', 'rejected'
  result_summary VARCHAR,
  duration_ms   INTEGER,
  hook_triggered VARCHAR           -- Which hook intercepted, if any
);

-- Boundary measurement records
CREATE TABLE boundary_records (
  task_id             VARCHAR PRIMARY KEY,
  mission_id          VARCHAR NOT NULL,
  mission_mode        VARCHAR NOT NULL,
  difficulty_class    VARCHAR NOT NULL,
  worker_model        VARCHAR NOT NULL,
  lora_version        VARCHAR,
  first_pass_success  BOOLEAN NOT NULL,
  total_iterations    INTEGER NOT NULL,
  error_taxonomy_tags JSON,
  local_tokens        INTEGER NOT NULL,
  frontier_tokens_in  INTEGER NOT NULL,
  frontier_tokens_out INTEGER NOT NULL,
  frontier_cost_usd   DECIMAL(10,6),
  wall_clock_seconds  INTEGER NOT NULL,
  timestamp           TIMESTAMP NOT NULL
);

-- Error taxonomy log
CREATE TABLE error_taxonomy (
  verdict_id    VARCHAR NOT NULL,
  task_id       VARCHAR NOT NULL,
  tag           VARCHAR NOT NULL,
  detail        VARCHAR,
  reviewer_model VARCHAR NOT NULL,
  timestamp     TIMESTAMP NOT NULL
);

-- Benchmark results
CREATE TABLE benchmark_runs (
  run_id          VARCHAR PRIMARY KEY,
  tag             VARCHAR NOT NULL,
  timestamp       TIMESTAMP NOT NULL,
  config_snapshot JSON NOT NULL,
  summary         JSON NOT NULL
);

CREATE TABLE benchmark_cartridge_results (
  run_id        VARCHAR REFERENCES benchmark_runs(run_id),
  cartridge_id  VARCHAR NOT NULL,
  status        VARCHAR NOT NULL,
  first_pass    BOOLEAN NOT NULL,
  iterations    INTEGER NOT NULL,
  local_tokens  INTEGER NOT NULL,
  frontier_tokens INTEGER NOT NULL,
  wall_clock_seconds INTEGER NOT NULL,
  error_tags    JSON,
  trace_id      VARCHAR,
  PRIMARY KEY (run_id, cartridge_id)
);

-- Shadow mode log
CREATE TABLE shadow_log (
  task_id         VARCHAR NOT NULL,
  oracle_id       VARCHAR NOT NULL,
  gate_verdict    VARCHAR NOT NULL,
  human_decision  VARCHAR NOT NULL,  -- 'approved', 'rejected'
  human_feedback  VARCHAR,
  decision_time_s INTEGER,
  timestamp       TIMESTAMP NOT NULL
);

-- Skill events
CREATE TABLE skill_events (
  skill_id      VARCHAR NOT NULL,
  event_type    VARCHAR NOT NULL,  -- 'created', 'applied', 'succeeded', 'failed', 'promoted'
  from_tier     INTEGER,
  to_tier       INTEGER,
  task_id       VARCHAR,
  timestamp     TIMESTAMP NOT NULL
);
```

### 10.3 Agent Self-Observability `PHASE 1`

Workers have a `query_traces` ACI tool that lets them inspect their own performance:

```sql
-- "Did the test suite pass faster after my optimization?"
SELECT span_name, duration_ms
FROM spans
WHERE service = 'test_runner'
  AND start_time > '2026-03-18T10:00:00'
ORDER BY start_time DESC
LIMIT 5;

-- "What's my first-pass rate on local-reasoning tasks?"
SELECT
  difficulty_class,
  COUNT(*) as total,
  SUM(CASE WHEN first_pass_success THEN 1 ELSE 0 END) as passed,
  ROUND(AVG(CASE WHEN first_pass_success THEN 1.0 ELSE 0.0 END), 2) as rate
FROM boundary_records
WHERE worker_model = 'qwen3.5-35b'
GROUP BY difficulty_class;
```

### 10.4 Daily Digest `PHASE 1`

Generated automatically at end of day (or via `forge digest`). Sent to human sovereign.

**Digest contents:**
- Tasks completed today (count, pass rates)
- Boundary data (first-pass success by type)
- Error taxonomy distribution for failures
- Cost summary (frontier spend, local tokens)
- Anomalies (if any recovery modes triggered, benchmark regressions, score drops)
- Skill events (new skills created/promoted)
- Pending shadow-mode merges awaiting approval

**Format:** Markdown file written to `.forge/digests/YYYY-MM-DD.md`. Also displayed by `forge digest`.

---

## 11. Agent-Computer Interface (ACI) `PHASE 1`

### 11.1 Tool Catalog

Every tool returns structured JSON. Output is always bounded. Errors are immediate and actionable.

| Tool | Behavior | Bounds | Output Schema |
|------|----------|--------|---------------|
| `search_file` | Regex/literal search in a file | Max 50 results | `{ "matches": [{"line": N, "content": "..."}], "total": N, "truncated": bool }` |
| `search_dir` | Search across directory | Max 50 results | `{ "files": [{"path": "...", "matches": [...]}], "total": N }` |
| `find_file` | Find files by name pattern | Max 30 results | `{ "files": ["path/to/file"], "total": N }` |
| `view_file` | Stateful viewer, 100 lines with line numbers | Remembers position | `{ "path": "...", "start_line": N, "end_line": N, "content": "...", "total_lines": N }` |
| `edit_file` | Replace lines start:end with new content | Immediate lint check | `{ "status": "applied" \| "rejected", "reason": "..." }` |
| `create_file` | Create new file with content | Lint check on creation | `{ "status": "created", "path": "..." }` |
| `run_tests` | Execute test suite (or specific tests) | Timeout: 120s | `{ "status": "pass" \| "fail", "passed": N, "failed": N, "errors": [...] }` |
| `run_command` | Execute approved shell command | Allowlist-checked | `{ "stdout": "...", "stderr": "...", "exit_code": N }` |
| `tree` | Show directory structure | Depth-limited (default: 3) | `{ "tree": "..." }` |
| `codemap` | Tree-sitter structural summary | Signatures only | `{ "files": [{"path": "...", "signatures": [...]}] }` |
| `git_status` | Current git state | — | `{ "branch": "...", "modified": [...], "staged": [...] }` |
| `git_commit` | Commit with descriptive message | Enforced format | `{ "status": "committed", "sha": "..." }` |
| `git_diff` | Show diff against main | Max 500 lines | `{ "diff": "...", "truncated": bool }` |
| `query_traces` | SQL query against DuckDB traces | Max 100 rows | `{ "columns": [...], "rows": [...] }` |

**Design principles (unchanged from v0.1):**
- Every tool returns structured JSON (not free-form text)
- Output is always bounded — no tool can flood the context window
- Errors are immediate and actionable — `"Syntax error on line 47: unexpected '}'"` not `"something went wrong"`
- Tools are the same regardless of which model is using them — the harness normalizes the interface

### 11.2 Extension Point `PHASE 1`

New ACI tools are Python plugins in `.forge/tools/`:

```python
# .forge/tools/custom_db_query.py
from forge.aci import Tool, ToolResult

class CustomDbQuery(Tool):
    name = "db_query"
    description = "Execute a read-only SQL query against the project database"
    parameters = {
        "query": {"type": "string", "description": "SQL SELECT query"},
    }

    def execute(self, query: str) -> ToolResult:
        # Implementation with safety checks
        if not query.strip().upper().startswith("SELECT"):
            return ToolResult.error("Only SELECT queries are allowed")
        # ... execute and return structured result
        return ToolResult.success({"columns": [...], "rows": [...]})
```

---

## 12. Git & Workspace Management `PHASE 1`

### 12.1 Directory Structure

```
project/
├── .git/                       # Shared object database
├── src/                        # Project source (main branch)
├── tests/                      # Project tests
├── .forge/                     # Harness state directory (gitignored)
│   ├── state.json              # Current mission/task state
│   ├── config.yaml             # Model, gate, and hook configuration
│   ├── architecture.yaml       # Architectural linter rules
│   ├── hooks.yaml              # Mechanical hook configuration
│   ├── oracles/                # Generated Oracle snapshots
│   │   ├── oracle-001-iter-1/
│   │   │   ├── core.json
│   │   │   └── annexes/
│   │   └── ...
│   ├── verdicts/               # Frontier review verdicts
│   ├── traces/                 # DuckDB trace database
│   │   └── forge.duckdb
│   ├── skills/                 # Learned patterns
│   │   ├── prompts/            # Tier 1
│   │   └── patterns/           # Tier 2
│   ├── benchmarks/             # Benchmark cartridges
│   │   ├── cartridge-manifest.yaml
│   │   └── add-endpoint-01/
│   ├── benchmark-results/      # Benchmark run results
│   ├── boundary-data.jsonl     # Boundary measurement records
│   ├── shadow-log.jsonl        # Shadow mode merge decisions
│   ├── digests/                # Daily digest summaries
│   ├── training/               # Accumulated fine-tuning data
│   └── tools/                  # Custom ACI tool plugins
└── .forge-worktrees/           # Isolated working copies (gitignored)
    ├── task-001-login/         # One worktree per active task
    └── task-002-signup/
```

### 12.2 Worktree Isolation `PHASE 1`

Every active task runs in an isolated git worktree:

1. Orchestrator creates worktree: `git worktree add .forge-worktrees/task-001 -b forge/task-001`
2. Worker operates exclusively within the worktree
3. Worker makes incremental commits with enforced message format
4. On task completion: Oracle generated from diff against main
5. If PASS + approved: squash-merge to main with structured commit message
6. If FAIL: worker continues in same worktree with TODO
7. On context exhaustion / recovery mode: rollback to last clean commit in worktree
8. On task complete (either way): worktree cleaned up

### 12.3 Commit Message Format `PHASE 1`

```
[FORGE] task-001: Implement login endpoint

- Created POST /api/auth/login with JWT token generation
- Added bcrypt password hashing
- Added 3 unit tests for auth flow
- Desloppify mechanical: 82 (+3)

Worker: qwen3.5-35b
LoRA: none
Difficulty: local-reasoning
Iterations: 2
Error-tags: missing-tests (iter 1)
Reviewed-by: claude-sonnet-4.6
Shadow-approved-by: human
```

### 12.4 Handoff Protocol `PHASE 1`

1. Worker starts in clean worktree branched from latest main
2. Worker codes, commits incrementally (enforced descriptive messages)
3. On task completion: Oracle generated from diff against main
4. If PASS: propose commit (shadow mode → human reviews and merges)
5. If FAIL: worker receives structured TODO, iterates with fresh context (same worktree, new session)
6. On context exhaustion: rollback to last clean commit, fresh worker session
7. On recovery mode: rollback, escalate to planner for rewrite/split

---

## 13. Configuration System `PHASE 1`

### 13.1 Master Config Schema

```yaml
# .forge/config.yaml
forge_version: "0.2"

# ─── Model Configuration ───
models:
  local:
    planner:
      endpoint: "http://dgx-spark-1:8000/v1"
      model: "nemotron-3-super-120b"
      role: "Mission decomposition, milestone planning, quality review"
      max_tokens: 8192
      temperature: 0.3

    worker:
      endpoint: "http://dgx-spark-2:8000/v1"
      model: "qwen3.5-35b"
      role: "Code generation, test writing, bug fixing, lint resolution"
      max_tokens: 4096
      temperature: 0.2
      lora_path: null  # Path to LoRA adapter if fine-tuned

  frontier:
    reviewer:
      provider: "anthropic"
      model: "claude-sonnet-4.6"
      api_key_env: "ANTHROPIC_API_KEY"
      role: "Primary reviewer (Phase 1)"

    escalation_reviewer:
      provider: "openai"
      model: "gpt-5.3-codex"
      api_key_env: "OPENAI_API_KEY"
      role: "Escalation reviewer (on 2nd failure)"

    chairman:  # Phase 2+ only
      provider: "anthropic"
      model: "claude-opus-4.6"
      api_key_env: "ANTHROPIC_API_KEY"
      role: "Chairman synthesis (Phase 2+)"

    intelligence:  # Optional
      provider: "xai"
      model: "grok-3"
      api_key_env: "XAI_API_KEY"
      role: "Web/community research (not code review)"

# ─── Gate Configuration ───
gate:
  phase: 1
  shadow_mode: true
  default_reviewer: "reviewer"  # References models.frontier.reviewer
  escalation_reviewer: "escalation_reviewer"
  max_iterations: 3
  recovery_threshold: 3

  # Phase 2+ trust parameters (designed but not active in Phase 1)
  trust:
    consecutive_successes_to_promote: 10
    failure_reset_factor: 0.5
    architectural_drift_reset: true  # Full trust reset on architectural-drift tag
    sensitive_paths:
      - "src/auth/**"
      - "src/payments/**"
      - "src/config/**"
      - "migrations/**"
    auto_merge_min_trust: 0.95
    auto_merge_max_blast_radius: "low"

# ─── Enforcement Configuration ───
enforcement:
  hooks_file: ".forge/hooks.yaml"
  architecture_file: ".forge/architecture.yaml"
  desloppify:
    mechanical:
      enabled: true
      run_on: "post_commit"
      thresholds:
        dead_code_max: 5
        duplication_max: 3
        complexity_max: 10
        function_length_max: 50
        nesting_depth_max: 4
    subjective:
      enabled: true
      run_on: "milestone_boundary"
      min_score_to_advance: 60
      model: "planner"  # Uses planner model for quality review

# ─── Benchmark Configuration ───
benchmarks:
  cartridge_dir: ".forge/benchmarks"
  results_dir: ".forge/benchmark-results"
  default_timeout_seconds: 600
  max_iterations_per_cartridge: 5

# ─── Observability Configuration ───
observability:
  trace_db: ".forge/traces/forge.duckdb"
  boundary_data: ".forge/boundary-data.jsonl"
  shadow_log: ".forge/shadow-log.jsonl"
  digest:
    enabled: true
    schedule: "daily"  # Generate at end of day
    output_dir: ".forge/digests"

# ─── Skill Configuration ───
skills:
  prompts_dir: ".forge/skills/prompts"
  patterns_dir: ".forge/skills/patterns"
  max_injected_skills: 5
  max_injection_tokens: 500
  promotion:
    tier0_to_tier1_observations: 2
    tier1_to_tier2_applications: 5
    tier2_to_tier3_applications: 10
    tier3_requires_human_approval: true  # Phase 1 safety
```

---

## 14. Security & Privacy Model `PHASE 1`

| Concern | Mitigation |
|---------|-----------|
| Local model data privacy | All local inference on-premises. No data leaves the network. |
| Frontier data exposure | Only Oracle snapshots sent (diffs + codemaps, not full codebase). Token-efficient by design. |
| Secret leakage | Layer 1 hook scans for secrets on every edit. Architectural linter rule backs it up. Secrets never in Oracle. |
| API keys | Stored as env var references in config (`api_key_env`), never plaintext. |
| Git safety | All code stays in local repos. Push to remote is explicit, not automatic. |
| Command execution | Allowlist-based. Dangerous commands blocked mechanically. |
| Worktree isolation | Workers cannot access files outside their worktree (enforced by ACI tools). |

---

## 15. Extensibility Points `PHASE 1`

| Extension | Mechanism | Location | Example |
|-----------|-----------|----------|---------|
| New ACI tools | Python plugin | `.forge/tools/` | Custom database query tool |
| New linter rules | YAML | `.forge/architecture.yaml` | Project-specific structural invariants |
| New hooks | YAML | `.forge/hooks.yaml` | Custom pre-commit actions |
| New model roles | YAML | `.forge/config.yaml` | Add a "security reviewer" role |
| New gate policies | Python plugin | `.forge/policies/` | Custom trust computation (Phase 2+) |
| New Oracle sections | Python plugin | `.forge/oracle/` | Add dependency graph analysis |
| New benchmark cartridges | YAML + snapshot | `.forge/benchmarks/` | Project-specific benchmark tasks |
| Language support | Tree-sitter grammar + formatter | `.forge/languages/` | Add Rust, Go, Python, etc. |
| New Desloppify detectors | Python plugin | `.forge/desloppify/` | Custom quality checks |

---

## 16. Phase Scope Summary

### Phase 1 — Factory.ai Droid Scope

**Build all of the following:**

| System | What to Build |
|--------|--------------|
| CLI | All commands listed in §2.1 (dashboard can be minimal text) |
| Orchestrator | Mission → milestone → task decomposition, state machine, recovery mode |
| Oracle Generator | Two-tier Oracle (Core + Annexes), custom tree-sitter pipeline |
| Gate Engine | Single reviewer + escalation on fail, shadow mode, difficulty classifier (planner-assigned) |
| Enforcement L1 | Mechanical hooks (syntax, format, secrets, allowlist) |
| Enforcement L2 | Architectural linters with agent-readable messages |
| Enforcement L3a | Desloppify mechanical (tree-sitter, on every commit) |
| Enforcement L3b | Desloppify subjective (LLM, at milestone boundaries) |
| Boundary Measurement | Full data capture, `forge boundary`, `forge taxonomy` |
| Benchmarks | Cartridge runner, results storage, `forge benchmark` commands |
| Skills (Tiers 1-3) | Prompt skills, YAML patterns, architectural linter rule promotion |
| Observability | OpenTelemetry → DuckDB, agent self-query, daily digest |
| Git | Worktree isolation, commit format, handoff protocol |
| Shadow Mode | Propose commits, log human decisions, no auto-merge |
| Config | Full config system per §13 |
| ACI | All tools in §11.1 |

### Phase 2+ — Claw Builder Scope

**Design target. Do not build in Phase 1. Do not block with Phase 1 decisions.**

| System | What to Build |
|--------|--------------|
| Gate Engine | Trust × blast-radius matrix, auto-merge, full board review (chairman + independent reviewers) |
| Shadow Mode | Graduation criteria, auto-merge for trusted task types |
| Difficulty Classifier | Trained classifier (replaces planner assignment) |
| Oracle | Interactive annexes (reviewer tool calls), visual/multimodal annexes |
| Skills (Tiers 4-5) | Generated tests (executable invariants), LoRA fine-tuning pipeline |
| Observability | Full Textual TUI dashboard, Oracle feedback loop (density optimization) |
| Trust System | Mathematical trust function, auto-demotion, trust decay |
| Parallel Racing | Run multiple local models on same task (Gemini Angle C) |
| Intelligence | Grok as scout/research agent |
| Cross-Project | Skill transfer between projects |

---

## Appendix A: Terminology

| Term | Definition |
|------|-----------|
| **ACI** | Agent-Computer Interface. The tool layer between model and environment. |
| **Annex** | Expandable section of the Oracle that reviewers pull on demand. |
| **Benchmark cartridge** | A fixed, reproducible task used for controlled harness comparison. |
| **Blast radius** | Mechanically computed impact scope of a code change (files, deps, sensitivity). |
| **Board of Directors** | Full multi-reviewer governance model (Phase 2+): independent reviewers + chairman. |
| **Boundary** | The empirical frontier/local split — which tasks need frontier judgment. |
| **Chairman** | Frontier model (Opus) that synthesizes reviewer verdicts. Phase 2+ only. |
| **Core Oracle** | Default, token-efficient snapshot sent to reviewers (~2–4K tokens). |
| **Crystallization** | Hardening a learned pattern from soft (prompt) to hard (linter/weights). |
| **Desloppify** | Quality enforcement. Two subsystems: mechanical (tree-sitter) and subjective (LLM). |
| **Difficulty class** | Task classification: mechanical, local-reasoning, architectural, uncertain. |
| **Error taxonomy** | Failure categories: tool-misuse, navigation-failure, incorrect-logic, missing-tests, architectural-drift, context-confusion, flaky-validation. |
| **Fresh context axiom** | Workers get clean, bounded context per task. Not tunable. |
| **Gate engine** | Trust system that routes tasks to appropriate review intensity. |
| **Intelligence** | Grok role: web/community research, not code review. |
| **Oracle** | Structured snapshot mediating between local workers and frontier reviewers. |
| **Recovery mode** | Triggered after N failures. Stops iteration, escalates, rewrites, or splits. |
| **Shadow mode** | FORGE proposes commits; human is final merger. Phase 1 default. |
| **Skill** | A learned pattern at any tier of the crystallization pipeline. |
| **Trust** | Computed confidence in a worker for a task type without frontier review. |
| **Worker identity** | First-class tracking of model + LoRA version + config that produced output. |

---

## Appendix B: File Inventory

All FORGE state lives under `.forge/`. The entire directory is gitignored.

```
.forge/
├── config.yaml                     # Master configuration
├── architecture.yaml               # Architectural linter rules (Layer 2 + Tier 3 skills)
├── hooks.yaml                      # Mechanical hooks configuration (Layer 1)
├── state.json                      # Current mission/task state
├── boundary-data.jsonl             # Boundary measurement records (append-only)
├── shadow-log.jsonl                # Shadow mode decisions (append-only)
├── oracles/                        # Oracle snapshots
│   └── <oracle-id>/
│       ├── core.json               # Tier 1 Core Oracle
│       ├── annexes/                # Tier 2 Expandable Annexes
│       └── metadata.json           # Generation metadata
├── verdicts/                       # Reviewer verdicts
│   └── <verdict-id>.json
├── traces/                         # Observability
│   └── forge.duckdb                # DuckDB trace database
├── skills/                         # Skill crystallization
│   ├── prompts/                    # Tier 1
│   └── patterns/                   # Tier 2
├── benchmarks/                     # Benchmark cartridges
│   ├── cartridge-manifest.yaml
│   └── <cartridge-id>/
│       ├── task.yaml
│       ├── repo-snapshot.tar.gz
│       ├── success-criteria.yaml
│       └── expected-oracle.json
├── benchmark-results/              # Benchmark run results
│   └── <run-id>.json
├── digests/                        # Daily digest summaries
│   └── YYYY-MM-DD.md
├── training/                       # Fine-tuning data (Phase 2+)
│   ├── sft-examples.jsonl
│   └── preference-pairs.jsonl
└── tools/                          # Custom ACI tool plugins
    └── *.py
```

---

*This architecture is the implementation spec for FORGE v0.2. Phase 1 components are the Factory.ai Droid's mission scope. Phase 2+ components are the Claw builder's scope. Build to the schemas. Extend through the extension points. Measure everything.*
