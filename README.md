# Gemini Advisor

Multi-model capability routing and selective task orchestration for Google Antigravity.

---

## Overview

Modern agentic engineering workflows often rely on a single monolithic model for all phases of a task. While effective, this approach introduces two systemic inefficiencies:

1. **Token Inefficiency**: High-reasoning models spend costly tokens ingesting verbose compiler outputs, generating boilerplate code, and re-reading large conversation histories.
2. **Confirmation Bias**: An agent that generates code inherently struggles to audit its own work objectively, frequently missing regressions and edge cases.

**Gemini Advisor** solves these challenges by implementing a capability-routed architecture. It assigns architectural planning to **Gemini Pro**, delegates bounded code construction to **Gemini Flash**, and routes completed diffs to an isolated, read-only **Fresh Gemini Pro** auditor.

```mermaid
flowchart TD
    User([Task Specification]) --> Architect[Architect / Planner\nGemini Pro]
    Architect --> RouteDecision{Selective Route\nDeclaration}

    RouteDecision -->|solo| SoloDelivery[Solo Delivery\nRoot Implements & Self-Tests]
    RouteDecision -->|delegate| FlashBuilder[Builder\nGemini Flash\nWrite Enabled]
    RouteDecision -->|audit| ProDirect[Direct Delivery\nGemini Pro]
    RouteDecision -->|full| FlashBuilder

    FlashBuilder --> ImplReport[Implementation Report\n+ Diff Evidence]
    ImplReport --> ParentVerify[Parent Verification\nTest Suite & Linters]

    ParentVerify --> ReviewGate{Review Required?}
    ProDirect --> ReviewGate

    ReviewGate -->|No| Complete([Task Complete])
    ReviewGate -->|Yes: audit / full| Auditor[Independent Auditor\nFresh Gemini Pro\nStrictly Read-Only]

    Auditor --> AuditVerdict{Verdict}
    AuditVerdict -->|SHIP| Complete
    AuditVerdict -->|FIX-FIRST| Remediation[Remediation Loop\nBuilder / Architect]
    Remediation --> FlashBuilder
    AuditVerdict -->|RETHINK| Architect
```

---

## Architecture: The Model Triad

Gemini Advisor structures development across three distinct responsibilities:

### 1. Architect / Lead Planner (`pro`)
- Runs in the primary Antigravity session.
- Conducts non-destructive codebase exploration.
- Declares the upfront `SELECTIVE ROUTE` before executing any modifying tool.
- Decomposes goals into modular milestones with strict file ownership boundaries.
- Generates unambiguous 5-part implementation contracts.
- Owns parent verification and user acceptance.

### 2. Builder / Implementer (`flash` or `flash_lite`)
- Invoked as a subagent (`gemini_advisor_builder`) with write access.
- Executes bounded coding, test writing, and mechanical refactors at a fraction of the cost.
- Strictly adheres to declared file ownership boundaries; never modifies external files.
- Executes local verification commands and returns an `IMPLEMENTATION REPORT`.

### 3. Auditor / Reviewer (Fresh `pro` in read-only mode)
- Invoked as an independent subagent (`gemini_advisor_reviewer`) in a clean context.
- Configured with `enable_write_tools: false` to enforce non-destructive evaluation.
- Inspects the accumulated unified git diff and test logs against specification criteria.
- Issues a definitive verdict: `SHIP`, `FIX-FIRST`, or `RETHINK`.

---

## Selective Routing Engine

Before executing any file modifications or destructive commands, the Architect issues a machine-auditable route declaration:

```text
SELECTIVE ROUTE
mode: solo | delegate | audit | full
risk: <concise, task-specific rationale>
allocation: Planner (Pro) -> Builder (Flash) -> Reviewer (Fresh Pro)
```

### Routing Modes

| Mode | Workflow | Auxiliary Agents | When to Use |
| :--- | :--- | :--- | :--- |
| **`solo`** | Architect plans, implements, and self-verifies | 0 | Default for minor bug fixes, documentation, single-file edits, and low-risk tasks. |
| **`delegate`** | Pro plans -> Flash builds -> Pro verifies | 1 (`gemini_advisor_builder`) | Well-specified features, boilerplate endpoints, migrations, and bounded refactors. |
| **`audit`** | Pro plans & builds -> Fresh Pro audits | 1 (`gemini_advisor_reviewer`) | Security-sensitive logic, authentication flows, core abstractions, and schema updates. |
| **`full`** | Pro plans -> Flash builds -> Pro verifies -> Fresh Pro audits | 2 (sequential) | Substantial multi-module features and high-blast-radius implementations. |

> **Escalation Policy**: `solo` is the default baseline to prevent coordination overhead on trivial tasks. A route may escalate to higher scrutiny if newly discovered complexity warrants it, but it may never silently downgrade.

---

## Structured Contracts

### Implementation Contract
When delegating work to the Builder, the Architect provides a structured contract:

```text
OBJECTIVE:
<Concrete, observable outcome and business rationale.>

FILES AND OWNERSHIP:
You own ONLY:
- <file1>
- <file2>
Do NOT modify any files outside this list.

INTERFACES:
- <Public types, function signatures, endpoints, or CLI flags to maintain or introduce.>

CONSTRAINTS:
- <Coding conventions, dependency limits, error handling patterns, and settled decisions.>

VERIFICATION:
- Command: <exact test or build command>
  Expected: <expected exit code or output signature>
- Inspect: <target file or diff>
  Expected: <observable behavior>

RETURN:
Structured IMPLEMENTATION REPORT covering STATUS, CHANGES, VERIFIED, JUDGMENT CALLS, and GAPS.
```

### Audit Protocol & Verdicts
The Reviewer evaluates the unified diff and test logs against four pillars:
1. **Contract Compliance**: Respect of file boundaries and interface parity.
2. **Correctness & Logic**: Absence of off-by-one errors, unhandled nil/null checks, and concurrency bugs.
3. **Security & Resource Safety**: Absence of command injections, data leaks, and memory leaks.
4. **Verification Evidence**: Proof of passing test and build outputs.

| Verdict | Definition | Next Step |
| :--- | :--- | :--- |
| **`SHIP`** | All criteria met without blocking findings. | Parent accepts changes and delivers to user. |
| **`FIX-FIRST`** | Actionable defects or missing test coverage identified. | Parent delegates targeted fixes to Builder, then requests re-review. |
| **`RETHINK`** | Fundamental architectural inconsistency. | Parent halts, reverts invalid changes, and redesigns the approach. |

---

## Token Economics & Verification Tooling

By delegating verbose code generation to Flash and isolating the review to a fresh context, Gemini Advisor reduces token burn and operational costs:

| Phase | Monolithic Approach (Pro) | Gemini Advisor Triad | Net Impact |
| :--- | :--- | :--- | :--- |
| **Planning** | 4,000 Pro tokens | 4,000 Pro tokens | Neutral |
| **Implementation** | 40,000 Pro tokens | 40,000 **Flash** tokens | ~90% Cost Reduction |
| **Build & Test Output** | 30,000 Pro tokens | 30,000 **Flash** tokens | ~90% Cost Reduction |
| **Audit** | 50,000 Pro tokens (accumulated context) | 5,000 **Fresh Pro** tokens (isolated diff) | ~90% Context Reduction |
| **Effective Total** | **124,000 Pro tokens** | **9,000 Pro + 70,000 Flash tokens** | **~75–85% Lower Cost** |

### Integrated Token Counter

Gemini Advisor includes an integrated tokenizer and cost calculator (`scripts/token_counter.sh`):

```bash
# Run automated verification self-tests
bash scripts/token_counter.sh --test

# Compare Monolithic vs Triad ROI on standard tasks
bash scripts/token_counter.sh --compare

# Measure token count of a file or directory
bash scripts/token_counter.sh --file skills/gemini-advisor/SKILL.md
bash scripts/token_counter.sh --dir skills/

# Count tokens in the active git diff
bash scripts/token_counter.sh --diff

# Measure tokens in an Antigravity transcript
bash scripts/token_counter.sh --transcript path/to/transcript.jsonl
```

---

## Installation & Usage

### 1. Installation
Install globally across all Antigravity workspaces, or link within a single repository:

```bash
# Global installation (recommended)
bash scripts/install.sh --global

# Workspace-local installation
bash scripts/install.sh --workspace

# Check installation status
bash scripts/install.sh --check
```

### 2. Running Verification
Ensure all manifests, reference documentation, shell scripts, and tokenizer tests pass:

```bash
bash scripts/verify.sh
```

### 3. Usage in Antigravity
Prompt the agent in the Antigravity IDE or CLI (`agy`):

```text
Use gemini-advisor to build [feature description] and verify it. Declare the selective route before task tools.
```

---

## Repository Structure

```text
.
├── plugin.json                              # Antigravity plugin manifest
├── plugins/
│   └── gemini-advisor/
│       └── plugin.json                      # Nested discovery manifest
├── rules/
│   ├── AGENTS.md                            # Active rules enforcing route declarations & roles
│   └── GEMINI.md                            # Compatibility alias
├── skills/
│   └── gemini-advisor/
│       ├── SKILL.md                         # Core Antigravity orchestration skill
│       └── references/
│           ├── role_contracts.md            # Role definitions and prompt templates
│           ├── routing_matrix.md            # Risk evaluation decision matrix
│           ├── review_protocol.md           # 4-pillar audit rubric & verdicts
│           └── token_optimization.md        # Token saving strategies & benchmarks
├── scripts/
│   ├── token_counter.py                     # Real token counter & economic estimator
│   ├── token_counter.sh                     # Shell CLI wrapper for token counter
│   ├── install.sh                           # Idempotent plugin installer
│   ├── verify.sh                            # Test & validation suite
│   └── diff_summary.sh                      # Unified diff extractor for reviews
├── LICENSE                                  # MIT License
└── README.md                                # Project documentation
```

---

## License & Acknowledgements

This project is licensed under the MIT License.

The selective routing architecture is inspired by the orchestration methodology of [sol-advisor](https://github.com/DannyMac180/sol-advisor).
