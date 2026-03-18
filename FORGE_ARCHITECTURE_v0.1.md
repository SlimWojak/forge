# FORGE v0.1 — Technical Architecture

> **The harness, orchestration, and enforcement systems that make FORGE work**

**Status:** v0.1 Draft — For lateral review
**Date:** 2026-03-18
**Author:** Craig @ a8ra / SlimWojak

---

## 1. System Architecture Overview

FORGE is a Python-based CLI application with an optional TUI (Textual) that orchestrates local and frontier LLMs through a structured task execution pipeline. It runs as a daemon that manages model serving, task scheduling, git operations, and frontier API calls.

```
                                    ┌──────────────┐
                                    │   FRONTIER    │
                                    │   APIs        │
                                    │  ┌─────────┐  │
                                    │  │  Opus   │  │
                                    │  │ Sonnet  │  │
                                    │  │  Codex  │  │
                                    │  └─────────┘  │
                                    └──────┬───────┘
                                           │ Oracle review / verdicts
┌──────────────────────────────────────────┼──────────────────────────────┐
│  FORGE HARNESS (Python)                  │                              │
│                                          │                              │
│  ┌─────────────┐    ┌──────────────┐    ┌┴─────────────┐               │
│  │ CLI / TUI   │───▶│ Orchestrator │───▶│ Gate Engine  │               │
│  │ (Click /    │    │ (Mission     │    │ (Frontier    │               │
│  │  Textual)   │    │  Control)    │    │  review      │               │
│  └─────────────┘    └──────┬───────┘    │  loop)       │               │
│                            │            └──────────────┘               │
│                ┌───────────┼───────────┐                               │
│                │           │           │                               │
│         ┌──────┴──────┐ ┌──┴────┐ ┌───┴──────┐                        │
│         │ ACI Tools   │ │ Git   │ │ Oracle   │                        │
│         │ (bounded,   │ │ Mgr   │ │ Generator│                        │
│         │  stateful)  │ │       │ │          │                        │
│         └──────┬──────┘ └──┬────┘ └───┬──────┘                        │
│                │           │          │                                │
│         ┌──────┴───────────┴──────────┴──────┐                        │
│         │        Enforcement Layer            │                        │
│         │  Hooks · Linters · Desloppify       │                        │
│         └──────────────────┬─────────────────┘                        │
│                            │                                           │
│         ┌──────────────────┴─────────────────┐                        │
│         │        Trace / Observability        │                        │
│         │  OpenTelemetry → DuckDB             │                        │
│         └────────────────────────────────────┘                        │
│                                                                        │
└───────────────────────────┬────────────────────────────────────────────┘
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

---

## 2. Core Components

### 2.1 CLI Interface (`forge`)

The primary interface. Built with Click (CLI) + Textual (optional TUI dashboard).

```bash
# Project lifecycle
forge init <project-name>          # Scaffold repo with .forge/ state
forge mission "description"        # Start a new mission (decompose → plan → execute)
forge task "description"           # Single task execution (simpler loop)

# Monitoring & control
forge status                       # Current state: active tasks, quality score, loop metrics
forge dashboard                    # TUI: live progress, quality trends, model usage
forge log                          # Recent trace history

# Intervention
forge intervene                    # Pause execution, enter human PM mode
forge approve                      # Manually approve a pending gate
forge reject "reason"              # Reject with specific feedback
forge replan                       # Trigger re-decomposition of current milestone

# Quality
forge quality                      # Run Desloppify scan now
forge oracle                       # Generate Oracle snapshot of current state
forge review                       # Send current Oracle to frontier reviewers

# Configuration
forge config models                # Configure model assignments per role
forge config gate                  # Configure gate policy (per-task, per-milestone, adaptive)
forge config frontier              # Configure frontier API keys and model preferences

# Metrics & learning
forge metrics                      # Show frontier/local split, iteration counts, cost data
forge skills                       # List learned patterns / skills
forge export-training              # Export accumulated data for LoRA fine-tuning
```

### 2.2 Orchestrator (Mission Control)

The central daemon that manages the task execution lifecycle.

**Responsibilities:**
- Decompose missions into milestones and tasks (via local planner model)
- Schedule task execution in isolated git worktrees
- Manage the Oracle → Review → Verdict → Iterate loop
- Track state in `.forge/state.json`
- Handle failure recovery (rollback to last clean commit on context exhaustion or unrecoverable errors)
- Coordinate Desloppify scans at milestone boundaries

**State Machine:**

```
INIT → PLANNING → EXECUTING → ORACLE_GENERATED → UNDER_REVIEW → VERDICT
  │                                                                  │
  │                          ┌───────────────────────────────────────┘
  │                          │
  │                    ┌─────┴─────┐
  │                    │           │
  │                  PASS        FAIL
  │                    │           │
  │                    ▼           ▼
  │                  MERGE    ITERATE (back to EXECUTING)
  │                    │
  │                    ▼
  │              NEXT_TASK (or MILESTONE_VALIDATION if last task in milestone)
  │                    │
  │                    ▼
  └──────────── MISSION_COMPLETE
```

### 2.3 Agent-Computer Interface (ACI)

Bounded, stateful tools designed for local LLM capabilities. Every tool returns structured, predictable output.

| Tool | Behavior | Bounds |
|------|----------|--------|
| `search_file` | Regex/literal search in a file | Max 50 results, truncated matches |
| `search_dir` | Search across directory | Max 50 results, grouped by file |
| `find_file` | Find files by name pattern | Max 30 results |
| `view_file` | Stateful viewer, shows 100 lines with line numbers | Remembers position, scrollable |
| `edit_file` | Replace lines start:end with new content | Immediate lint check; rejects syntax errors before applying |
| `create_file` | Create new file with content | Lint check on creation |
| `run_tests` | Execute test suite (or specific tests) | Timeout enforced, structured pass/fail output |
| `run_command` | Execute approved shell command | Allowlist-based; dangerous commands blocked by hook |
| `browser_test` | Playwright-based E2E test | Structured assertions, screenshot on failure |
| `tree` | Show directory structure | Depth-limited, respects .gitignore |
| `codemap` | Tree-sitter structural summary | Function/type signatures only, 10x token savings |
| `git_status` | Current git state | Structured output |
| `git_commit` | Commit with descriptive message | Enforced message format, pre-commit hooks run |

**Design Principles:**
- Every tool returns structured JSON (not free-form text)
- Output is always bounded — no tool can flood the context window
- Errors are immediate and actionable — "Syntax error on line 47: unexpected '}'" not "something went wrong"
- Tools are the same regardless of which model is using them — the harness normalizes the interface

### 2.4 The Forge Oracle

The Oracle is a structured snapshot of system state generated after every task completion. It serves as the handoff contract between local workers and frontier reviewers.

**Oracle Structure:**

```json
{
  "oracle_version": "0.1",
  "timestamp": "2026-03-18T10:30:00Z",
  "mission": "Build user auth with JWT",
  "milestone": 1,
  "task": "Implement login endpoint",
  "task_description": "Create POST /api/auth/login that validates credentials and returns JWT",

  "diff": {
    "files_changed": 3,
    "insertions": 87,
    "deletions": 12,
    "patch": "... unified diff ..."
  },

  "codemap": {
    "changed_files": [
      {
        "path": "src/api/auth.ts",
        "signatures": ["export async function login(req, res)", "function validateCredentials(email, password)", "function generateToken(userId)"],
        "dependencies": ["src/db/users.ts", "src/utils/jwt.ts"]
      }
    ],
    "affected_files": [
      {
        "path": "src/routes/index.ts",
        "change": "Added route /api/auth/login → auth.login"
      }
    ]
  },

  "mechanical_checks": {
    "lint": {"status": "pass", "warnings": 2, "errors": 0},
    "type_check": {"status": "pass"},
    "tests": {"status": "pass", "passed": 14, "failed": 0, "new": 3},
    "build": {"status": "pass"}
  },

  "quality": {
    "desloppify_score": 82,
    "delta": "+3",
    "new_issues": ["Duplicate validation logic in auth.ts and signup.ts"],
    "resolved_issues": ["Missing error handling in JWT generation"]
  },

  "worker_self_assessment": {
    "confidence": "medium",
    "concerns": ["JWT expiry time hardcoded — should be configurable", "No rate limiting on login endpoint"],
    "decisions_made": ["Used bcrypt for password hashing (argon2 was alternative)", "Stored refresh token in httpOnly cookie"]
  },

  "context": {
    "feature_list_progress": "4/14 complete",
    "milestone_progress": "2/4 tasks in milestone 1",
    "total_iterations_this_task": 1,
    "tokens_consumed_local": 45000,
    "tokens_consumed_frontier": 0
  }
}
```

**Why This Structure:**
- **Diff** — reviewers see exactly what changed, not what exists
- **Codemap** — structural context at 10x token savings vs. full files
- **Mechanical checks** — binary pass/fail data that doesn't need LLM judgment
- **Quality delta** — trend matters more than absolute score
- **Worker self-assessment** — the local model's own uncertainty signals are informative
- **Context** — reviewers understand where this task sits in the larger mission

**Token Budget:** A typical Oracle is ~2-4K tokens. This means frontier review of one task costs roughly $0.01-0.05 depending on model and response length. Even at 100 tasks per mission, frontier review stays under $5.

### 2.5 Gate Engine (Frontier Review Loop)

The Gate Engine sends Oracle snapshots to frontier models and processes their verdicts.

**Review Flow:**

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
     ├── PASS → merge, advance
     │
     └── FAIL → structured TODO with:
              - Specific file(s) and line(s)
              - What's wrong (clear, actionable)
              - What "fixed" looks like (acceptance criteria)
              - Priority (blocking vs. advisory)
```

**Gate Policies (configurable):**

| Policy | When | Trade-off |
|--------|------|-----------|
| `per-task` | Every task goes through full review | Maximum safety, highest frontier cost |
| `per-milestone` | Review at milestone boundaries only | Lower cost, larger blast radius for issues |
| `adaptive` | Review intensity based on confidence signals | Best balance, requires calibration data |

**Adaptive signals:**
- Desloppify score delta (positive + above threshold → lower review intensity)
- Worker confidence self-assessment
- Task complexity classification
- Historical first-pass success rate for similar tasks
- Number of mechanical check failures

### 2.6 Enforcement Layer

Three distinct enforcement mechanisms, operating at different points in the pipeline:

#### Layer 1: Mechanical Hooks (Real-time, Pre/Post Tool Use)

Hooks run outside the model — the model cannot override them.

```yaml
# .forge/hooks.yaml
pre_edit:
  - action: lint_check
    description: "Syntax check before applying edit"
    on_fail: reject_edit

post_edit:
  - action: auto_format
    description: "Run formatter after every edit"
    formatter: prettier  # or black, rustfmt, etc.

pre_command:
  - action: allowlist_check
    description: "Block commands not in approved list"
    blocked_patterns:
      - "rm -rf"
      - "curl | bash"
      - "sudo"

post_commit:
  - action: pre_commit_hooks
    description: "Run pre-commit hook suite"
```

#### Layer 2: Architectural Linters (Mechanical, CI-style)

Custom linters that encode project-specific rules. Error messages are written for agents — they explain WHY the rule exists and the CORRECT approach.

```yaml
# .forge/architecture.yaml
rules:
  - name: no_cross_module_imports
    pattern: "import.*from.*modules/((?!${current_module}).)*/"
    message: |
      VIOLATION: Cross-module import detected.
      WHY: Modules must communicate through the public API layer (src/api/),
      not import each other's internals directly.
      FIX: Move the shared logic to src/shared/ or expose it through the
      module's public API in src/api/{module}.ts

  - name: no_hardcoded_secrets
    pattern: "(password|secret|token|key)\\s*=\\s*['\"][^'\"]+['\"]"
    message: |
      VIOLATION: Hardcoded secret detected.
      WHY: Secrets must come from environment variables or the config system.
      FIX: Use process.env.{SECRET_NAME} or config.get('secrets.{name}')

  - name: handler_error_boundary
    files: "src/api/**/*.ts"
    must_contain: "try.*catch|ErrorBoundary|withErrorHandler"
    message: |
      VIOLATION: API handler missing error boundary.
      WHY: Unhandled errors crash the server and expose stack traces.
      FIX: Wrap handler body in try/catch or use the withErrorHandler() wrapper.
```

#### Layer 3: Desloppify Quality Loop (Scheduled, Between Milestones)

```
Milestone Complete
     │
     ▼
desloppify scan --path .
     │
     ▼
Score + issue queue generated
     │
     ├── Score above threshold → proceed to next milestone
     │
     └── Score below threshold or critical issues →
              desloppify next (one fix at a time)
              Worker resolves → desloppify next → repeat
              Until score threshold met
```

**Integration:** Desloppify quality delta is included in every Oracle snapshot. Trend data feeds into the adaptive gate policy.

### 2.7 Observability & Trace System

Every model interaction, tool call, and decision is traced for analysis.

**Stack:**
- OpenTelemetry SDK (Python) for instrumentation
- Local collector → DuckDB (lightweight, queryable, no infrastructure)
- Traces include: model used, tokens consumed, tool calls, latency, pass/fail outcomes

**Agent Self-Observability:**
Workers can query their own traces:
```sql
-- "Did the test suite pass faster after my optimization?"
SELECT span_name, duration_ms
FROM traces
WHERE service = 'test_runner'
  AND timestamp > '2026-03-18T10:00:00'
ORDER BY timestamp DESC
LIMIT 5;
```

**Dashboard Metrics:**
- Frontier/local token split per mission
- Iteration count per task (how many loops before PASS)
- First-pass success rate trend
- Quality score trend over time
- Cost per task / milestone / mission
- Model performance comparison (when swapping models)

---

## 3. Git & Workspace Management

### Worktree Isolation

Every active task runs in an isolated git worktree:

```
project/
├── .git/                    # Shared object database
├── main/                    # Main branch (clean state)
├── .forge/                  # Harness state (gitignored)
│   ├── state.json           # Current mission/task state
│   ├── oracles/             # Generated Oracle snapshots
│   ├── verdicts/            # Frontier review verdicts
│   ├── traces/              # DuckDB trace database
│   ├── skills/              # Learned patterns
│   ├── quality/             # Desloppify history
│   └── config.yaml          # Model and gate configuration
└── .forge-worktrees/        # Isolated working copies
    ├── task-001-login/      # One worktree per active task
    └── task-002-signup/
```

### Handoff Protocol

1. Worker starts in clean worktree branched from latest main
2. Worker codes, commits incrementally (enforced descriptive messages)
3. On task completion: Oracle generated from diff against main
4. If PASS: squash-merge to main with structured commit message
5. If FAIL: worker continues in same worktree with TODO
6. On context exhaustion: rollback to last clean commit, fresh session

### Commit Message Format

```
[FORGE] task-001: Implement login endpoint

- Created POST /api/auth/login with JWT token generation
- Added bcrypt password hashing
- Added 3 unit tests for auth flow
- Desloppify: 82 (+3)

Reviewed-by: sonnet-4.6, codex-5.3
Approved-by: opus-4.6
Iterations: 1
```

---

## 4. Model Interface Layer

FORGE communicates with all models through an OpenAI-compatible API abstraction. This means any model accessible via this interface is pluggable.

### Local Model Serving

**Primary:** vLLM (production-grade tool calling, PagedAttention, concurrent requests)
**Fallback:** llama.cpp (lighter weight, good for Nemotron Nano on single Spark)

```yaml
# .forge/config.yaml
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

  frontier:
    chairman:
      provider: "anthropic"
      model: "claude-opus-4.6"
      role: "Final verdict synthesis, go/no-go decisions"

    reviewer_a:
      provider: "anthropic"
      model: "claude-sonnet-4.6"
      role: "Architectural coherence, design pattern review"

    reviewer_b:
      provider: "openai"
      model: "gpt-5.3-codex"
      role: "Correctness, test coverage, edge case analysis"

  # Future: Grok as frontier scout for X/Reddit pattern scanning
  # scout:
  #   provider: "xai"
  #   model: "grok-3"
  #   role: "Lateral research, community pattern discovery"
```

### Model Swapping

Models are roles, not identities. Swapping is a config change:

```bash
forge config models worker --model "nemotron-3-super-120b" --endpoint "http://dgx-spark-2:8000/v1"
```

All traces are tagged with model identity, so performance can be compared across swaps.

---

## 5. The Skills & Learning System

### Runtime Skills (Prompt-Level)

Successful patterns stored as structured YAML:

```yaml
# .forge/skills/auth-pattern.yaml
skill:
  name: "JWT Auth Pattern"
  learned_from: "task-001-login"
  confidence: 0.85
  pattern: |
    When implementing JWT authentication in this codebase:
    - Use bcrypt for password hashing (not argon2 — bcrypt is the project standard)
    - Store refresh tokens in httpOnly cookies
    - JWT expiry comes from config.get('auth.jwt_expiry'), not hardcoded
    - All auth endpoints must use the withErrorHandler() wrapper
    - Rate limiting middleware must be applied to auth routes
  applicable_when: "task involves authentication or token generation"
```

Skills are injected into worker context when applicable (matched by task description keywords).

### Fine-Tuning Data Collection (Phase 4)

Every task completion generates a training example:

```json
{
  "task_description": "Implement login endpoint with JWT",
  "context": "... codemap + relevant file content ...",
  "successful_completion": "... final diff that passed review ...",
  "iterations": 1,
  "first_attempt_passed": true,
  "reviewer_feedback": null
}
```

Failed first attempts with subsequent corrections become preference pairs:

```json
{
  "task_description": "Implement login endpoint with JWT",
  "rejected": "... first attempt diff ...",
  "chosen": "... corrected diff that passed ...",
  "correction_reason": "Missing rate limiting on auth endpoint"
}
```

These accumulate in `.forge/training/` and can be exported for LoRA fine-tuning:

```bash
forge export-training --format preference-pairs --output training-data.jsonl
```

---

## 6. Security & Privacy Model

- **Local models:** All inference on-premises. No data leaves the network.
- **Frontier models:** Only Oracle snapshots are sent (diffs + codemaps, not full codebase). Token-efficient by design.
- **Secrets:** Never included in Oracle snapshots. `.forge/config.yaml` supports env var references for API keys.
- **Git:** All code stays in local repos. Push to remote is a separate, explicit action.
- **Hooks:** Mechanical enforcement prevents accidental secret leakage in commits.

---

## 7. Extensibility Points

FORGE is designed for experimentation. Key extension points:

| Extension | Mechanism | Example |
|-----------|-----------|---------|
| New ACI tools | Python plugin in `.forge/tools/` | Custom database query tool |
| New linter rules | YAML in `.forge/architecture.yaml` | Project-specific invariants |
| New hooks | YAML in `.forge/hooks.yaml` | Custom pre-commit actions |
| New model roles | Config in `.forge/config.yaml` | Add a "security reviewer" role |
| New gate policies | Python plugin in `.forge/policies/` | Custom adaptive logic |
| New Oracle sections | Python plugin in `.forge/oracle/` | Add dependency graph analysis |
| Language support | Tree-sitter grammar + formatter config | Add Rust, Go, etc. |

---

*This architecture is a starting point. The specific tools, Oracle structure, and gate policies will evolve through experimentation — that's the point of FORGE.*
