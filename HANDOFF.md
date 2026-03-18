# HANDOFF.md — Builder Transition Protocol

> **This document defines the explicit contracts between each build phase.**
> **Each transition has deliverables, acceptance criteria, and mandates. No ambiguity.**

---

## Build Path

```
Phase 0 (P + Craig)
  │
  │  Architecture, scaffold, spec
  │
  ▼
Phase 1 (Factory.ai Droid)
  │
  │  Core implementation
  │
  ▼
Phase 1.5 (Bootstrap Test)
  │
  │  FORGE reviews itself
  │
  ▼
Phase 2+ (Claw Builder — Opus brain + FORGE self-review)
  │
  │  Advanced features, real-world deployment
  │
  ▼
Ongoing: Lateral Reviews (P + Craig periodic check-ins)
```

---

## Phase 0 → Phase 1 Handoff: P + Craig → Factory.ai Droid

### What Phase 0 Delivers

| Deliverable | Description | Location |
|-------------|-------------|----------|
| **v0.2 Overview spec** | Vision, decisions, thesis, all items marked DECIDED are locked | `docs/FORGE_OVERVIEW_v0.2.md` |
| **v0.2 Architecture spec** | Full technical architecture with normative JSON schemas, CLI contract, state machines, enforcement rules | `docs/FORGE_ARCHITECTURE_v0.2.md` |
| **Scaffolded Python project** | CLI skeleton using Click, package structure matching Architecture §2.2 and §12.1 | `src/forge/` |
| **ACI tool interface definitions** | Base class, tool registry, structured JSON return contract per Architecture §11 | `src/forge/aci/` |
| **Tree-sitter Oracle pipeline stub** | Interface defined, generation steps outlined, Core Oracle JSON schema in spec | `src/forge/oracle/` |
| **Config schema** | Full `.forge/config.yaml` schema per Architecture §13.1 | `.forge/config.yaml` |
| **Benchmark cartridge template** | Cartridge structure, manifest schema, success criteria format per Architecture §8.2 | `.forge/benchmarks/` |
| **feature_list.json** | Phase 1 work queue — every feature that must be built, with completion tracking | `feature_list.json` |
| **AGENTS.md** | Agent orientation document — boot sequence, code standards, decision authority, boundaries | `AGENTS.md` |
| **HANDOFF.md** | This document | `HANDOFF.md` |
| **init.sh** | Dev environment setup script (if applicable) | `init.sh` |

### What Factory.ai Receives

A repo that is ready for implementation:

- **Scaffold is complete.** Directory structure exists. Package hierarchy is established. CLI entry points are wired. No structural decisions to make.
- **Spec is clear.** Every Phase 1 component is described in Architecture with JSON schemas, state machines, interface definitions, and CLI command signatures. Schemas are normative.
- **Work queue is defined.** `feature_list.json` is the single source of truth for what to build. Features are ordered. Each references the relevant spec section.
- **Boot document exists.** `AGENTS.md` tells the agent exactly how to start, what to read, what to write, and what never to touch.

### Factory.ai's Mandate

1. **Implement all features marked Phase 1 in `feature_list.json`.**
   - Work through features in order
   - Mark each as `passes: true` when tests pass and implementation matches spec
   - Do not skip features. Do not reorder without cause.

2. **Follow the architecture spec exactly for interfaces and schemas.**
   - CLI commands match Architecture §2.1 — same names, same flags, same behavior
   - JSON schemas match the normative schemas in Architecture §3–§13 — same fields, same types, same structure
   - State machine transitions match Architecture §1.3 — same states, same edges, same triggers
   - If the spec defines it, build it as specified. If the spec leaves room, implement and document.

3. **Tests for everything.**
   - Every public function has at least one test
   - Every CLI command has integration tests
   - Every JSON schema has validation tests
   - Every state machine transition has tests
   - Test names describe the behavior being tested
   - Use `pytest`. No other test framework.

4. **Do NOT implement Phase 2+ features.**
   - Architecture §16 lists Phase 1 scope and Phase 2+ scope explicitly
   - Components marked `PHASE 2+` in the architecture doc are out of scope
   - This includes: trust × blast-radius matrix, auto-merge, full board review, trained difficulty classifier, interactive Oracle annexes, visual/multimodal annexes, Tiers 4–5 skill crystallization, parallel model racing, Grok intelligence integration
   - **However:** do not make Phase 1 design choices that block Phase 2+ features. Leave extension points open. Use the extensibility mechanisms defined in Architecture §15.

5. **Handle ambiguity explicitly.**
   - If a Phase 1 feature requires a design decision not covered in the spec: create `.forge/blocked/<issue>.md` with description, options, and recommendation
   - If an OPEN question (Overview §15, Q11–Q18) must be resolved to implement a feature: resolve it, document in `.forge/decisions/<question-id>.md`, and move on
   - Never guess at spec intent when the answer affects interfaces or data schemas

---

## Phase 1 → Phase 1.5 Handoff: Factory.ai Droid → Bootstrap Test

### Success Criteria for Factory.ai Completion

Factory.ai's work is complete when ALL of the following are true:

| Criterion | Verification |
|-----------|-------------|
| All Phase 1 features in `feature_list.json` marked `passes: true` | Inspect `feature_list.json` — no Phase 1 feature has `passes: false` or is missing the field |
| `forge task` runs end-to-end | Execute: submit task → worker codes in worktree → Oracle generated → single frontier reviewer → verdict → iterate on FAIL → propose commit on PASS |
| `forge mission` decomposes and executes | Execute: mission description → planner decomposes into milestones → milestones into tasks → tasks execute via `forge task` loop → Desloppify subjective at milestone boundary |
| `forge boundary` produces output | Execute with accumulated task data → displays frontier/local split report matching Architecture §7.3 format |
| `forge taxonomy` produces output | Execute with accumulated verdict data → displays error taxonomy distribution matching Architecture §7.4 format |
| Benchmark cartridge runner works | Execute `forge benchmark run` → cartridges execute → results stored per Architecture §8.3 schema → `forge benchmark compare` works |
| Desloppify mechanical produces a score | Execute on FORGE's own codebase → returns structured score per Architecture §6.3 |
| All tests pass | `pytest` with zero failures, zero errors |
| Shadow mode captures human decisions | `forge approve` / `forge reject` → events logged to `.forge/shadow-log.jsonl` per Architecture §5.5 |
| Observability pipeline works | Events flow from components → OpenTelemetry → DuckDB → queryable via `forge log`, `forge metrics` |
| Config system loads and validates | `.forge/config.yaml` parsed per Architecture §13.1 schema, referenced by all components |

### Bootstrap Test Protocol

The bootstrap test is both a quality check AND the first boundary measurement data point. It proves FORGE works by using FORGE on itself.

**Procedure:**

```
1. Point FORGE at its own repository
   - Configure .forge/config.yaml with local model endpoints + frontier API keys
   - Set project root to the FORGE repo itself

2. Generate Oracle of FORGE's own codebase
   - Run: forge oracle
   - Verify: Core Oracle JSON matches Architecture §4.2 schema
   - Verify: Annexes are staged correctly
   - Verify: Token count is within 2–4K target for Core Oracle

3. Send Oracle to frontier reviewer
   - Run: forge review
   - Verify: Reviewer receives Core Oracle
   - Verify: Reviewer can pull Annexes
   - Verify: Verdict JSON matches Architecture §5.6 schema

4. Record the verdict
   - Store verdict in .forge/verdicts/
   - Log boundary record to .forge/boundary-data.jsonl
   - Verify: forge boundary shows the bootstrap task result

5. Run Desloppify mechanical on FORGE's own code
   - Run: forge quality --mechanical-only
   - Record baseline mechanical score
   - This score becomes the starting quality metric

6. Run benchmark cartridge suite
   - Execute: forge benchmark run --tag bootstrap-baseline
   - Record baseline results
   - Store in .forge/benchmark-results/

7. Document results
   - Write .forge/bootstrap-results.md with:
     - Oracle generation: pass/fail + token count
     - Frontier review: verdict + issues found
     - Desloppify score: baseline number
     - Benchmark results: pass rate by difficulty class
     - Any issues discovered
```

**What the bootstrap test proves:**
- The Oracle pipeline works end-to-end (tree-sitter → structured JSON → frontier-readable)
- The gate engine works (Oracle → reviewer → verdict → structured response)
- The observability pipeline captures data
- The boundary measurement system records and reports correctly
- The benchmark system produces reproducible results
- FORGE's own code quality is measurable

---

## Phase 1.5 → Phase 2+ Handoff: Bootstrap → Claw Builder

### What the Claw Builder Receives

| Deliverable | Description |
|-------------|-------------|
| **Working FORGE** | All Phase 1 features operational, tested, passing |
| **Bootstrap test results** | First data point: Oracle quality, frontier verdict on FORGE code, Desloppify baseline, benchmark baseline |
| **Benchmark cartridge baseline data** | Stored in `.forge/benchmark-results/` — the comparison point for all future harness changes |
| **feature_list.json updated with Phase 2+ features** | P + Craig add Phase 2+ features to the work queue before Claw builder begins |
| **AGENTS.md** | Same orientation document — boot sequence, standards, boundaries still apply |
| **All accumulated `.forge/` state** | Boundary data, shadow log, skill observations, trace database — continuity from Phase 1 |

### Claw Builder's Mandate

1. **Use FORGE to review its own work.**
   - This is the recursive loop. FORGE's gate engine reviews PRs to the FORGE repo.
   - Desloppify runs on FORGE's own codebase after every milestone.
   - If FORGE's own reviewer rejects a change to FORGE, the Claw builder iterates.
   - This is both self-improvement and dogfooding.

2. **Implement Phase 2+ features from `feature_list.json`.**
   - Architecture §16 lists Phase 2+ scope:
     - Trust × blast-radius gate matrix with auto-merge
     - Full board review (independent reviewers + chairman synthesis)
     - Trained difficulty classifier (replaces planner assignment)
     - Interactive Oracle annexes (reviewer tool calls)
     - Visual/multimodal Oracle annexes (screenshots, flame graphs)
     - Tiers 4–5 skill crystallization (generated tests + LoRA fine-tuning)
     - Full Textual TUI dashboard
     - Oracle density self-optimization (feedback loop)
     - Mathematical trust function with auto-demotion and decay
     - Parallel model racing
     - Grok as intelligence/research agent
     - Cross-project skill transfer

3. **Daily digest to Telegram.**
   - End of each work day, generate and send:
     - Tasks completed (count, descriptions)
     - Tasks failed (count, error taxonomy tags, blocked items)
     - Decisions made (which OPEN questions resolved, what was chosen)
     - Blocked items (created `.forge/blocked/*.md` files)
     - Desloppify scores (mechanical + subjective)
     - Boundary data (first-pass success rates)
     - Cost summary (frontier spend)
   - Format: structured Markdown, machine-readable by Opus COO

4. **Opus (COO) reviews daily digest and provides steering.**
   - Opus receives the daily digest
   - Opus can: reprioritize features, add new features to `feature_list.json`, unblock blocked items with design decisions, flag quality concerns, adjust gate policy
   - Opus's steering is authoritative for Phase 2+ — equivalent to Craig's authority in Phase 0
   - Craig retains override authority via periodic lateral reviews

5. **Maintain the fresh context axiom.**
   - Every Claw builder session starts clean
   - No accumulated conversation state between sessions
   - `feature_list.json` + `.forge/state.json` + git log are the continuity mechanism
   - This applies to the Claw builder itself, not just to the models FORGE orchestrates

---

## Periodic Review Protocol

### Who

- **Craig** (human sovereign)
- **P** (Perplexity Computer — lateral review partner)

### When

Periodically — no fixed schedule. Triggered by:
- Major Phase 2+ milestone completion
- Significant boundary data accumulation (100+ tasks)
- Claw builder blocked items accumulating (3+ unresolved)
- Craig's discretion

### What Happens

```
1. Pull latest repo
   - git pull, read .forge/state.json, read feature_list.json
   - Review git log since last check-in

2. Review state
   - Which features are complete? Which are blocked?
   - What do boundary measurements show?
   - What does the error taxonomy look like?
   - Are Desloppify scores trending up or down?
   - Are benchmark results stable or regressing?

3. Joust on direction
   - P + Craig discuss: Is the architecture holding up?
   - Are Phase 2+ features being implemented correctly?
   - Is the boundary moving in interesting directions?
   - Are there new patterns from the field (SWE-agent, Anthropic, OpenAI, Factory.ai) that should inform FORGE?
   - Should any DECIDED item be reconsidered based on data?

4. Push course corrections
   - Updated feature_list.json entries (reprioritize, add, modify scope)
   - Spec amendments (new sections to docs/ if architectural evolution is needed — versioned as v0.3, v0.4, etc.)
   - Blocked item resolutions (decisions on .forge/blocked/*.md files)
   - Gate policy changes (if boundary data suggests different review intensity)
   - New benchmark cartridges (if coverage gaps identified)

5. Document the review
   - Write docs/LATERAL_REVIEW_<date>.md with:
     - What was reviewed
     - Key findings
     - Decisions made
     - Action items pushed
```

### Scope of Lateral Review Authority

- **Can modify:** `feature_list.json`, `.forge/config.yaml`, gate policies, benchmark cartridges, OPEN question resolutions, Phase 2+ scope
- **Can create:** New spec documents (versioned), new blocked-item resolutions, new architectural linter rules
- **Cannot modify without versioning:** `docs/FORGE_OVERVIEW_v0.2.md`, `docs/FORGE_ARCHITECTURE_v0.2.md` — these are the v0.2 spec. Amendments create v0.3+ documents that explicitly note what changed and why.
- **Can override:** Opus COO steering decisions (Craig is ultimately sovereign)

---

## Transition Checklist

Use this to verify each handoff is complete before the next phase begins.

### Phase 0 → Phase 1 ✓

- [ ] `docs/FORGE_OVERVIEW_v0.2.md` exists and is complete
- [ ] `docs/FORGE_ARCHITECTURE_v0.2.md` exists and is complete
- [ ] `src/forge/` scaffold exists with package structure
- [ ] CLI skeleton wired with Click (all commands from Architecture §2.2 as stubs)
- [ ] `feature_list.json` exists with Phase 1 features
- [ ] `.forge/config.yaml` exists with schema from Architecture §13.1
- [ ] `AGENTS.md` exists (this boot document)
- [ ] `HANDOFF.md` exists (this transition document)
- [ ] `init.sh` exists (dev environment setup)
- [ ] Initial git commit with all scaffold files

### Phase 1 → Phase 1.5

- [ ] All Phase 1 features in `feature_list.json` marked `passes: true`
- [ ] `forge task` end-to-end: worker → Oracle → reviewer → verdict → iterate
- [ ] `forge mission` end-to-end: decompose → milestones → tasks → execute → validate
- [ ] `forge boundary` produces formatted report
- [ ] `forge taxonomy` produces error distribution
- [ ] `forge benchmark run` executes cartridges and stores results
- [ ] `forge quality --mechanical-only` produces Desloppify score
- [ ] All tests pass (`pytest` — zero failures)
- [ ] Shadow mode logging operational
- [ ] DuckDB observability pipeline captures events
- [ ] Config system loads and validates

### Phase 1.5 → Phase 2+

- [ ] Bootstrap test completed (FORGE reviewed its own code)
- [ ] Bootstrap results documented in `.forge/bootstrap-results.md`
- [ ] Baseline Desloppify score recorded
- [ ] Baseline benchmark results stored
- [ ] `feature_list.json` updated with Phase 2+ features
- [ ] Claw builder Telegram digest pipeline configured
- [ ] Opus COO steering channel established

---

*This document is a contract between build phases. Each phase delivers specific artifacts with specific acceptance criteria. No phase begins until the prior phase's checklist is complete. No exceptions.*
