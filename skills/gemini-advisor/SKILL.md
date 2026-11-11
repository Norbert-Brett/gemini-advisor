---
name: gemini-advisor
description: "Capability-routed multi-agent architecture with JEV micro-routing: Frontier models (Gemini 4 Argon / Claude Opus) advise at Three Golden Triggers, Execution models (Flash 3.8 / Sonnet 5.5) build code, and Lite scouts (Flash-Lite / Haiku) explore in parallel."
---

# Gemini Advisor Orchestration & JEV Engineering

**Gemini Advisor** is an advanced, capability-routed multi-agent delivery framework for Google Antigravity and Claude Code. Inspired by modern frontier-to-execution architectures, it organizes software development into a clean 4-tier cognitive hierarchy where every model does only what it is best at:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        THE 4-TIER COGNITIVE HIERARCHY                  │
├─────────────────────┬───────────────────────────┬──────────────────────┤
│ Role                │ Allocated Model Tier      │ Core Responsibility  │
├─────────────────────┼───────────────────────────┼──────────────────────┤
│ 1. On-Call Advisor  │ Frontier (Argon 4 / Opus) │ The 3 Golden Triggers│
│ 2. Main Builder     │ Execution (Flash / Sonnet)│ Edits code & builds  │
│ 3. Parallel Scouts  │ Lite (Flash-Lite / Haiku) │ Search, Grep, Docs   │
│ 4. JEV Micro-Router │ System One Decision Engine│ Micro-forks in < 1ms │
└─────────────────────┴───────────────────────────┴──────────────────────┘
```

- **Main Driver / Builder**: Runs the session and writes code with high speed and economical token cost (Gemini 3.8 Flash in Antigravity, Sonnet 5.5 in Claude Code).
- **Parallel Explorers (Read-Only Scouts)**: Three lightweight subagents run concurrently at ultra-low cost (Gemini Flash-Lite / Haiku):
  - `search`: Maps repository directories, finds file locations, and charts project layouts.
  - `grep`: Locates symbol definitions, traces call sites, and finds regex patterns.
  - `docs`: Pulls external/internal API references, Context7 documentation, and specifications.
- **On-Call Frontier Advisor**: Apex reasoning model (Gemini 4 Argon / Claude Opus 5.5) stays on call for the critical decisions. It reads the full transcript/diff only when consulted, completely eliminating Frontier token burn on routine turns.
- **JEV Micro-Router**: Evaluates deterministic micro-forks (tool choice, path selection, 2x error loop detection, and advisor triggers) in **sub-millisecond time (<0.02ms)** with zero token cost.

---

## 1. The Three Golden Advisor Triggers

The Frontier Advisor steps in strictly at three pivotal moments:

1. **Trigger 1: Plan Lock (`plan_lock`)**: Before any architectural plan or 5-part contract is approved and before code editing begins.
2. **Trigger 2: Error Loop (`error_loop`)**: When JEV detects the **identical normalized error signature twice in succession**. The builder halts immediately, and the Advisor diagnoses root cause to break the hallucination loop.
3. **Trigger 3: Task Done (`task_done`)**: Before marking a task complete or committing changes. The Advisor conducts an independent, zero-tolerance diff and evidence audit.

See [references/advisor_triggers.md](references/advisor_triggers.md) for full trigger specifications.

---

## 2. JEV Deterministic Micro-Routing (`scripts/jev_router.sh`)

Micro-forks that require no creative thinking are offloaded to JEV in milliseconds:

```bash
# 1. Evaluate delivery route mode (solo, delegate, audit, full)
bash scripts/jev_router.sh --route --task "Add search scout tests" --files scripts/jev_router.py

# 2. Select optimal tool signature deterministically
bash scripts/jev_router.sh --tool-choice --task "Find all call sites of resolve_allocation"

# 3. Fast path ranking from project structure
bash scripts/jev_router.sh --select-path --task "model allocator python tests"

# 4. Error loop detection (trips Advisor Trigger 2 on 2nd repeat)
bash scripts/jev_router.sh --check-error --error "AssertionError: expected 200 got 500 at line 42"

# 5. Check advisor trigger status
bash scripts/jev_router.sh --advisor-trigger --stage plan_lock

# 6. Benchmark micro-routing latency (< 0.05 ms)
bash scripts/jev_router.sh --benchmark
```

See [references/jev_engineering.md](references/jev_engineering.md) for architecture and benchmarks.

---

## 3. Dynamic Model Allocation (`scripts/model_allocator.sh`)

Before executing tasks, Gemini Advisor discovers and verifies active model tiers dynamically:

```bash
# Verify model tiers and check allocation invariants
bash scripts/model_allocator.sh --check

# Emit dynamic SELECTIVE ROUTE allocation line
bash scripts/model_allocator.sh --allocate
```

### Subagent Model Inheritance Rule
- When the parent session runs on a Frontier model (e.g. **Gemini 4 Argon**), invoking subagents with `Model: "inherit"` preserves the Frontier tier in a fresh, isolated context.
- When the parent session runs on an Execution model (e.g. Flash), subagent escalation automatically falls back to `Model: "pro"` to ensure strict audit standards.

---

## 4. Upfront Route Declaration

Before making any modifying tool calls (`write_file`, `edit_file`, destructive `run_command`), emit the machine-auditable declaration:

```text
SELECTIVE ROUTE
mode: solo | delegate | audit | full
risk: <concise, task-specific rationale>
allocation: Planner (Gemini 4 Argon [Frontier]) -> Builder (Gemini 3.8 Flash [flash]) -> Reviewer (Fresh Gemini 4 Argon [inherit])
```

| Mode | When to use | Execution Flow | Scouts / Auxiliaries |
| :--- | :--- | :--- | :--- |
| **`solo`** | Default for trivial tweaks, documentation, single-file edits (<3 files). | Main driver plans, executes, and self-checks. | None (0 auxiliary) |
| **`delegate`** | Bounded features, boilerplate, or unit test suites. | Main driver plans -> Builder (`flash`) implements -> Driver tests. | 1 builder (`gemini_advisor_builder`) |
| **`audit`** | Sensitive changes (auth, security, schemas, public APIs). | Main driver plans & writes -> Reviewer (`inherit` / `pro`) audits. | 1 reviewer (`gemini_advisor_reviewer`) |
| **`full`** | Multi-file features or high-impact architectural components. | Main driver plans -> Builder (`flash`) implements -> Reviewer audits. | Builder + Reviewer + Scouts |

---

## 5. Parallel Explorer Scouts

When exploratory mapping is needed, dispatch lightweight read-only scouts in parallel:

### A. Repository Structure Mapper (`gemini_advisor_search`)
- **Model**: `flash_lite` (Antigravity) / `haiku` (Claude Code)
- **Role**: Maps directory structures, charts file trees, and returns layout summaries.

### B. Call-Site & Symbol Investigator (`gemini_advisor_grep`)
- **Model**: `flash_lite` (Antigravity) / `haiku` (Claude Code)
- **Role**: Locates symbol definitions, call sites, regex patterns, and imports.

### C. API Reference Explorer (`gemini_advisor_docs`)
- **Model**: `flash_lite` (Antigravity) / `haiku` (Claude Code)
- **Role**: Retrieves API signatures, Context7 library documentation, and specifications.

---

## 6. The 5-Part Implementation Contract

When delegating to the Builder (`gemini_advisor_builder`), provide all five required sections:

```text
OBJECTIVE:
<Concrete, observable outcome and why it matters.>

FILES AND OWNERSHIP:
You own ONLY:
- <path/to/file1>
- <path/to/file2>
Do NOT modify any files outside this list. Respect existing code style and concurrent edits.

INTERFACES:
- <Signatures, types, endpoints, schemas, or CLI flags that must remain intact or be added.>

CONSTRAINTS:
- <Framework conventions, dependency rules, safety boundaries, and settled decisions.>

VERIFICATION:
- Command: <exact command to run, e.g. npm test or bash scripts/verify.sh>
  Expected: <exact exit status or output signature>
- Inspect: <exact file or diff>
  Expected: <concrete observable changes>

RETURN:
Provide a structured IMPLEMENTATION REPORT:
STATUS: complete | partial | blocked
OBJECTIVE: <one-line restatement>
CHANGES: <file-by-file summary of changes made>
VERIFIED: <exact commands executed and actual output captured>
JUDGMENT CALLS: <any decisions left unspecified, or "none">
GAPS: <any unfinished work or blocking issues, or "none">
```

---

## 7. Cross-Platform Execution: Claude Code & Antigravity

Gemini Advisor is fully compatible across agent environments:

### Google Antigravity
- Main session: Frontier (`Gemini 4 Argon`) or Builder (`Gemini 3.8 Flash`)
- Scouts: `gemini_advisor_search`, `gemini_advisor_grep`, `gemini_advisor_docs` (`flash_lite`)
- Advisor: `gemini_advisor_advisor` (`inherit` / `pro`)

### Claude Code
Launch Claude Code using the advisor flag:
```bash
claude --model sonnet --advisor opus
```
- Driver: Sonnet 5.5
- Advisor: Opus 5.5 (summoned at the 3 Golden Triggers)
- Scouts: Haiku 5.5 subagents (`search`, `grep`, `docs`)
- Rules: Defined in `rules/CLAUDE.md`

---

## 8. Reference Documentation
- [references/advisor_triggers.md](references/advisor_triggers.md) - The Three Golden Advisor Triggers (Plan Lock, Error Loop, Task Done).
- [references/jev_engineering.md](references/jev_engineering.md) - JEV System One micro-routing, schemas, and latency benchmarks.
- [references/role_contracts.md](references/role_contracts.md) - Role prompts, subagent definitions, and schemas.
- [references/routing_matrix.md](references/routing_matrix.md) - Risk matrix, blast-radius formulas, and escalation rules.
- [references/review_protocol.md](references/review_protocol.md) - Independent audit rubrics, checklists, and verdicts.
- [references/token_optimization.md](references/token_optimization.md) - Token accounting and cost comparison models.
