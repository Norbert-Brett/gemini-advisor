---
name: gemini-advisor
description: "Dynamic frontier-to-execution routing for Antigravity: apex Frontier models (Gemini 4 Argon) plan and audit in read-only mode, while fast and economical models (Gemini Flash / Flash-Lite) execute code."
---

# Gemini Advisor Orchestration

**Gemini Advisor** is a capability-routed software delivery workflow for Google Antigravity. It dynamically assigns each phase of development to the optimal model tier:
- **Architect / Planner (Frontier Thinking Tier — e.g., Gemini 4 Argon)**: Owns high-level intent, architectural decomposition, contract drafting, escalation decisions, and final acceptance using the highest-reasoning model available.
- **Builder / Implementer (Economical Execution Tier — Gemini Flash or Flash-Lite)**: Executes bounded, fully specified code implementation at 10–30x lower token cost with lightning speed.
- **Reviewer / Auditor (Fresh Frontier Tier in read-only mode)**: Performs an unbiased audit of the accumulated git diff and test evidence using `Model: "inherit"` (preserving Frontier capability such as Gemini 4 Argon) or `"pro"` fallback, without builder confirmation bias or historical context bloat.

---

## 1. Pre-Flight Dynamic Model Check & Auto-Allocation (`scripts/model_allocator.sh`)

Before executing complex tasks or setting route allocations, Gemini Advisor verifies model tiers dynamically so no manual package updates are required when newer models are released:

```bash
# Check detected model tiers across Antigravity transcripts and environment
bash scripts/model_allocator.sh --check

# Output dynamic allocation recommendations for the active task
bash scripts/model_allocator.sh --allocate
```

The allocator automatically detects the highest-capability thinking model (currently **Gemini 4 Argon**, or any future Gemini 5+ frontier model) and pairs it with cheaper execution models (`flash` / `flash_lite`).

### The Subagent Model Inheritance Rule
Antigravity's `invoke_subagent` supports the `Model` enum: `["inherit", "flash_lite", "flash", "pro"]`.
- When the Architect runs on a Frontier model above `pro` (such as **Gemini 4 Argon**), invoking `gemini_advisor_reviewer` with `Model: "inherit"` preserves **Gemini 4 Argon** in a fresh, isolated read-only context!
- If the parent session is running on a lower tier (e.g. `flash`), the allocator falls back to `Model: "pro"` to ensure the auditor maintains high reasoning standards.

---

## 2. The Selective Route Declaration

Before making any modifying tool calls (`write_to_file`, `replace_file_content`, `write_file`, `edit_file`, destructive `run_command`), the Architect **MUST** evaluate the risk and emit the machine-auditable declaration:

```text
SELECTIVE ROUTE
mode: solo | delegate | audit | full
risk: <concise, task-specific rationale>
allocation: Planner (Gemini 4 Argon [Frontier]) -> Builder (Gemini Flash [Execution]) -> Reviewer (Fresh Gemini 4 Argon [inherit])
```

### Route Modes

| Mode | When to use | Execution Flow | Auxiliary Spawns |
| :--- | :--- | :--- | :--- |
| **`solo`** | Default for trivial tweaks, documentation, single-file edits, or tightly scoped fixes with zero architectural risk. | Architect (Frontier) plans, implements, tests, and self-reviews. | None (0 auxiliary) |
| **`delegate`** | Bounded, well-specified features, refactors, or boilerplate where implementation is purely mechanical. | Architect (Frontier) plans -> Builder (`flash` / `flash_lite`) implements -> Architect verifies. | 1 implementer (`gemini_advisor_builder`) |
| **`audit`** | Sensitive changes (security, schema migrations, public API contracts) written directly by the Architect that require independent verification. | Architect (Frontier) plans & implements -> Reviewer (Fresh Frontier via `inherit` or `pro`) audits diff & test results. | 1 reviewer (`gemini_advisor_reviewer`) |
| **`full`** | Substantial, multi-file features or high-risk components where both low-cost implementation and rigorous unbiased scrutiny are critical. | Architect (Frontier) plans -> Builder (`flash`) implements -> Architect tests -> Reviewer (Fresh Frontier) audits. | 2 auxiliaries sequentially (Builder, then Reviewer) |

> [!IMPORTANT]
> - `solo` is the baseline default to conserve tokens whenever risk is low.
> - A route can only **escalate** (e.g. `solo` -> `audit` or `delegate` -> `full`) if newly discovered risk justifies it. It must **never** silently downgrade.

---

## 3. Dynamic Subagent Configuration

Antigravity allows dynamic definition and invocation of subagents. When executing `delegate`, `audit`, or `full`, ensure the target subagents are defined and invoked as follows:

### A. Defining the Builder Subagent (`gemini_advisor_builder`)
Use `define_subagent` if not already registered:
- **`name`**: `"gemini_advisor_builder"`
- **`description`**: `"Fast, token-efficient implementation agent for bounded specifications."`
- **`enable_write_tools`**: `true`
- **`enable_subagent_tools`**: `false`
- **`enable_mcp_tools`**: `false`
- **`system_prompt`**: See [references/role_contracts.md](references/role_contracts.md#2-builder--implementer-gemini_advisor_builder)

### B. Defining the Reviewer Subagent (`gemini_advisor_reviewer`)
Use `define_subagent` if not already registered:
- **`name`**: `"gemini_advisor_reviewer"`
- **`description`**: `"Fresh, unbiased read-only reviewer for git diffs and test evidence."`
- **`enable_write_tools`**: `false` *(Strictly read-only; no code mutations allowed)*
- **`enable_subagent_tools`**: `false`
- **`enable_mcp_tools`**: `false`
- **`system_prompt`**: See [references/role_contracts.md](references/role_contracts.md#3-reviewer--auditor-gemini_advisor_reviewer)

---

## 4. The 5-Part Implementation Contract

When delegating to the Builder (`gemini_advisor_builder`), the Architect writes a prompt containing all five required sections:

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

## 5. Unbiased Review Protocol

In `audit` or `full` modes, once implementation is completed and verified by the parent session:

1. **Capture Evidence**: Run `git diff` or use `scripts/diff_summary.sh` to extract the exact changed lines and run the verification suite.
2. **Spawn Reviewer**: Invoke `gemini_advisor_reviewer` using `Model: "inherit"` (preserving Frontier tier e.g., Gemini 4 Argon) or `Model: "pro"` fallback with a **fresh context** (passing only the diff, verification evidence, and acceptance criteria).
3. **Reviewer Evaluation**: The reviewer returns one of three verdicts:
   - `VERDICT: SHIP` -> Ready to accept. Parent completes the task.
   - `VERDICT: FIX-FIRST` -> Actionable bugs, regressions, or missing tests. Parent either delegates fixes back to Builder or fixes directly, then reruns review.
   - `VERDICT: RETHINK` -> Fundamental architectural flaw. Parent revises the plan.

---

## 6. Token Economy Guidelines

To achieve maximum token savings:
1. **Leverage Frontier -> Execution Separation**: Let Frontier models (Gemini 4 Argon) reason and contract; let Execution models (Gemini Flash / Flash-Lite) write code and execute tests at 10–30x lower token cost.
2. **Never copy full files into prompts**: Use targeted snippets or point to file paths.
3. **Send clean diffs to Reviewer**: Do not forward intermediate scratchpads, hallucinated loops, or builder conversation history.
4. **Choose `flash_lite` for boilerplate**: When generating repetitive structures, tests, or config files, set `Model: "flash_lite"`.
5. **Refer to Reference Guides**:
   - [references/role_contracts.md](references/role_contracts.md) - Full prompt templates, schemas, and inheritance rules.
   - [references/routing_matrix.md](references/routing_matrix.md) - Decision guidelines for risk-gating.
   - [references/review_protocol.md](references/review_protocol.md) - Audit rubrics and inspection checklists.
   - [references/token_optimization.md](references/token_optimization.md) - Token benchmarking, model allocation CLI, and context optimization.
