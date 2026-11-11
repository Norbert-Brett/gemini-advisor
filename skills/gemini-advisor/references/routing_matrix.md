# Selective Routing Matrix

The Selective Routing Matrix dictates which delivery mode the Architect declares before starting task execution. Choosing the correct mode is the primary mechanism for burning fewer tokens while maintaining rigorous engineering standards by dynamically balancing Frontier Thinking (`Gemini 4 Argon` / auto-detected apex model) and Economical Execution (`Gemini Flash` / `Flash-Lite`), coordinated by the sub-millisecond JEV micro-routing engine.

---

## 1. Decision Table

| Mode | Token Cost | Blast Radius | Implementation Uncertainty | Audit Scrutiny | Typical Scenarios |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`solo`** | **Lowest** (1x) | Minimal (< 3 files) | Low | Self-checked | Typos, docs, script adjustments, isolated unit test additions, localized bug fixes handled end-to-end by Frontier Architect. |
| **`delegate`** | **Medium** (~1.2x) | Moderate (3-8 files) | Low to Medium | Parent verified | Bounded features with established patterns, boilerplate endpoints, database migrations, refactoring internal methods delegated to Flash / Flash-Lite. |
| **`audit`** | **Medium** (~1.5x) | High | High | Strict Fresh Frontier (`inherit`) | Security-sensitive auth flows, payment handling, core architectural changes, cryptographic operations written by Frontier Architect and audited independently. |
| **`full`** | **Higher** (~1.8x) | High | High | Strict Fresh Frontier (`inherit`) | Multi-module feature development, external API overhauls, high-impact changes combining Flash execution with fresh Frontier audit. |

---

## 2. Evaluation Criteria

When analyzing a user request, evaluate these 4 risk dimensions:

### 1. Structural Blast Radius
- **Isolated**: Single function, single script, or non-shared module -> `solo`
- **Component**: Contained within a single subsystem or feature folder -> `delegate`
- **System-Wide**: Cross-cutting changes across core packages, base types, or API gateways -> `audit` or `full`

### 2. Specification Clarity
- Can the task be specified completely upfront with crisp signatures and deterministic tests?
  - **Yes**: Ideal for `delegate` to Economical Execution (`flash` / `flash_lite`).
  - **No**: If substantial exploratory discovery is required during coding, the Architect should run `solo` or break into smaller delegated milestones.

### 3. Safety & Reversibility
- Can errors easily corrupt state, expose credentials, or break public consumers?
  - **Yes**: High risk requires independent review by a fresh Frontier model (`Gemini 4 Argon` via `inherit`) -> `audit` or `full`.
  - **No**: Low impact -> `solo` or `delegate`.

### 4. Token Budget Optimization
- If a task requires writing hundreds of lines of predictable code (e.g. data models, React UI widgets, test fixtures), doing it in Frontier (`Gemini 4 Argon`) burns costly tokens unnecessarily. Delegate to `flash` or `flash_lite` at 10–30x lower token cost!
- If the entire task is only a 5-line configuration change, spawning a subagent burns more tokens in orchestration overhead than executing it in `solo`. Stay `solo`!

---

## 3. Fast Deterministic JEV Micro-Routing

Instead of making slow, manual routing estimations, invoke the JEV micro-routing engine:

```bash
# Calculate exact route mode, risk score, and allocation in < 0.05 ms
python3 scripts/jev_router.py --route --task "<user task description>" --files file1.py file2.py
```

JEV computes:
- Structural risk score (0.00 to 1.00).
- Recommended delivery mode (`solo`, `delegate`, `audit`, or `full`).
- Dynamic allocation string with exact model names.

---

## 4. The Three Golden Advisor Triggers

Regardless of the selected route mode, the Frontier Advisor is summoned strictly at:

1. **Trigger 1: Plan Lock (`plan_lock`)**: Before any plan or 5-part contract is approved.
2. **Trigger 2: Error Loop (`error_loop`)**: When the same error signature recurs twice.
3. **Trigger 3: Task Done (`task_done`)**: Before marking any task complete or committing.

See [references/advisor_triggers.md](advisor_triggers.md) for full protocol details.

---

## 5. Escalation Protocol

The Architect may escalate the route if new evidence reveals unexpected complexity during execution:

```text
ROUTE ESCALATION
original_mode: solo
escalated_mode: delegate | audit | full
reason: <specific discovery, e.g. "Discovered database schema change affects 12 dependent services.">
```

### Golden Rules
1. **Never Silently Downgrade**: A route can only escalate to higher scrutiny, never downgrade to lower verification.
2. **Document the Evidence**: Every escalation must cite the concrete file, error, or finding that triggered the increased risk assessment.
