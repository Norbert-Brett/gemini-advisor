# Gemini Advisor

Dynamic Frontier-to-Execution model allocation and selective task orchestration for Google Antigravity.

---

## Overview

Modern agentic engineering workflows often rely on a single monolithic model for all phases of a task. While simple, this approach introduces two systemic inefficiencies:

1. **Token Inefficiency**: Top-tier Frontier reasoning models spend costly tokens ingesting verbose compiler outputs, generating repetitive boilerplate code, and re-reading large conversation histories.
2. **Confirmation Bias**: An agent that generates code inherently struggles to audit its own work objectively, frequently overlooking regressions and subtle edge cases.

**Gemini Advisor** solves these challenges by dynamically allocating tasks across specialized capability tiers:
- **Frontier Thinking Tier (currently Gemini 4 Argon)**: Always uses the most advanced, highest-reasoning model available for high-level intent, architectural decomposition, and contract drafting.
- **Economical Execution Tier (Gemini Flash / Flash-Lite)**: Bounded, high-velocity code implementation and test runs at **10–30x lower token cost**.
- **Fresh Frontier Review Tier (Fresh Gemini 4 Argon)**: Zero-bias audit evaluating only the final diff and verification logs in an isolated, read-only context via `Model: "inherit"` (or `"pro"` fallback).

```mermaid
flowchart TD
    User(["Task Specification"]) --> Architect["Architect / Planner\nGemini 4 Argon (Frontier)"]
    Architect --> ModelCheck["Model Check & Auto-Allocation\nscripts/model_allocator.sh"]
    ModelCheck --> RouteDecision{"Selective Route\nDeclaration"}

    RouteDecision -->|solo| SoloDelivery["Solo Delivery\nFrontier Implements & Self-Tests"]
    RouteDecision -->|delegate| FlashBuilder["Builder\nGemini Flash / Flash-Lite\nWrite Enabled"]
    RouteDecision -->|audit| DirectDelivery["Direct Delivery\nGemini 4 Argon (Frontier)"]
    RouteDecision -->|full| FlashBuilder

    FlashBuilder --> ImplReport["Implementation Report\n+ Diff Evidence"]
    ImplReport --> ParentVerify["Parent Verification\nTest Suite & Linters"]

    ParentVerify --> ReviewGate{"Review Required?"}
    DirectDelivery --> ReviewGate

    ReviewGate -->|No| Complete(["Task Complete"])
    ReviewGate -->|"Yes: audit / full"| Auditor["Independent Auditor\nFresh Gemini 4 Argon (inherit)\nStrictly Read-Only"]

    Auditor --> AuditVerdict{"Verdict"}
    AuditVerdict -->|SHIP| Complete
    AuditVerdict -->|FIX-FIRST| Remediation["Remediation Loop\nBuilder / Architect"]
    Remediation --> FlashBuilder
    AuditVerdict -->|RETHINK| Architect
```

---

## Automatic Model Check & Future-Proof Tier Allocation

Gemini Advisor includes a zero-maintenance dynamic model discovery and allocation engine (`scripts/model_allocator.sh`, powered by `scripts/model_allocator.py` and `config/model_tiers.json`). 

Instead of hardcoding model names to legacy generations, Gemini Advisor automatically inspects:
1. **Live Antigravity Transcripts**: Discovers the active runtime model powering your current IDE/CLI session.
2. **Environment Overrides**: Reads `GEMINI_ADVISOR_FRONTIER_MODEL`, `GEMINI_ADVISOR_BUILDER_MODEL`, `GEMINI_ADVISOR_LITE_MODEL`, `GEMINI_MODEL`, and `AGY_MODEL`.
3. **Google Gemini API**: Queries available models via `GEMINI_API_KEY` when present.
4. **Heuristic Capability Scoring**: Automatically scores newly released models based on generation, family, and capability tags (e.g. `argon` > `ultra` > `pro` > `flash`).

### Never Update Manually for New Models
When Google releases a newer apex model (such as Gemini 5+), the allocator detects and ranks it as the new Frontier model automatically. **You never have to manually edit or update package manifests when newer, better models come out.**

### Model Allocator CLI Commands

```bash
# Check detected Frontier and Execution models for your environment
bash scripts/model_allocator.sh --check

# Generate the machine-auditable allocation line for your task route
bash scripts/model_allocator.sh --allocate

# Discover all models accessible via transcripts, environment, and API
bash scripts/model_allocator.sh --discover

# Calculate heuristic capability score for any model identifier
bash scripts/model_allocator.sh --score "gemini-4-argon"
bash scripts/model_allocator.sh --score "gemini-2.5-pro"
bash scripts/model_allocator.sh --score "gemini-2.5-flash"

# Run automated tests on discovery and tier ranking
bash scripts/model_allocator.sh --test
```

---

## Quick Start & Installation

You can install Gemini Advisor globally for all your projects or locally within a specific repository.

### Option 1: Global Installation *(Recommended)*

Installs Gemini Advisor once so it is automatically active across all Antigravity workspaces:

```bash
# 1. Clone the repository to your home directory
git clone https://github.com/Norbert-Brett/gemini-advisor.git ~/.gemini-advisor

# 2. Run the global installer
bash ~/.gemini-advisor/scripts/install.sh --global

# 3. Verify the installation
bash ~/.gemini-advisor/scripts/install.sh --check
```

### Option 2: Project-Local Installation *(For Teams)*

Installs Gemini Advisor directly inside a project's `.agents/` folder so it can be shared with team members:

```bash
# Navigate to your project root
cd /path/to/your/project

# Clone directly into the project's plugins directory
mkdir -p .agents/plugins
git clone https://github.com/Norbert-Brett/gemini-advisor.git .agents/plugins/gemini-advisor
```

Antigravity automatically discovers plugins in `.agents/plugins/` when opening the project.

---

## How to Use: Step-by-Step

Once installed, Gemini Advisor integrates seamlessly into the Antigravity IDE, Desktop App, and CLI (`agy`).

### 1. Triggering Gemini Advisor

Simply include the trigger phrase in your prompt:

```text
Use gemini-advisor to build [feature description] and verify it. Declare the selective route before task tools.
```

#### Example Prompts:
- **Feature Addition**:  
  `"Use gemini-advisor to implement a rate-limiting middleware in Express and add integration tests. Declare the selective route before task tools."`
- **Refactoring**:  
  `"Use gemini-advisor to refactor the database query layer to use Prisma transactions. Declare the selective route before task tools."`
- **Bug Fix**:  
  `"Use gemini-advisor to investigate and resolve the race condition in the auth token refresh loop. Declare the selective route before task tools."`

---

### 2. What Happens Behind the Scenes

When you run a prompt with Gemini Advisor, the agent executes a structured 4-phase lifecycle:

#### Phase 1: Pre-Flight Model Check & Upfront Route Declaration
Before modifying any files, the Architect verifies model tiers and emits a machine-auditable declaration in chat:
```text
SELECTIVE ROUTE
mode: full
risk: Rate-limiting middleware affects all incoming API traffic; requires unit tests and independent review.
allocation: Planner (Gemini 4 Argon [Frontier]) -> Builder (Gemini Flash [Execution]) -> Reviewer (Fresh Gemini 4 Argon [inherit])
```

#### Phase 2: Delegated Code Construction (Flash / Flash-Lite)
If the route is `delegate` or `full`, the Architect defines an unambiguous 5-part contract (Objective, Files & Ownership, Interfaces, Constraints, Verification) and invokes `gemini_advisor_builder` using **Gemini Flash** (or `flash_lite` for mechanical boilerplate).
- The Builder writes code, creates files, and runs initial unit tests.
- Because Flash is used for implementation, high-volume code generation occurs at **~90% lower cost**.
- The Builder returns an `IMPLEMENTATION REPORT` summarizing changes made and test outputs.

#### Phase 3: Parent Verification
The primary Architect (Gemini 4 Argon) reviews the diff and independently reruns the verification suite (e.g., `npm test` or `pytest`) to confirm all tests pass cleanly.

#### Phase 4: Independent Read-Only Review (Fresh Gemini 4 Argon)
If the route is `audit` or `full`, the Architect spawns `gemini_advisor_reviewer` using a **fresh context** with `Model: "inherit"` (preserving Gemini 4 Argon) and `enable_write_tools: false`.
- The Reviewer receives **only** the objective, the git diff, and the test logs.
- Because it has no historical conversation baggage and cannot edit files, it performs a strict, zero-bias audit.
- The Reviewer issues a structured verdict:
  - **`SHIP`**: Changes meet all standards. The task completes.
  - **`FIX-FIRST`**: Concrete bugs or missing tests identified. The Architect feeds fixes back to the Builder and re-reviews.
  - **`RETHINK`**: Architectural inconsistency. The Architect halts and redesigns the approach.

---

## Selective Routing Modes

To prevent unnecessary orchestration overhead, Gemini Advisor defaults to `solo` for simple tasks and only scales up to auxiliaries when task risk demands it:

| Mode | Flow | Auxiliaries | When to Use |
| :--- | :--- | :---: | :--- |
| **`solo`** *(Default)* | Architect (Frontier) plans, builds, and self-verifies | 0 | Typos, documentation, isolated one-file bug fixes, and minor script tweaks. |
| **`delegate`** | Frontier plans -> Flash builds -> Frontier verifies | 1 | Well-specified features, boilerplate endpoints, migrations, and bounded refactors. |
| **`audit`** | Frontier plans & builds -> Fresh Frontier (`inherit`) audits | 1 | High-risk code written directly by Frontier (auth, cryptography, schema migrations). |
| **`full`** | Frontier plans -> Flash builds -> Frontier tests -> Fresh Frontier audits | 2 | Substantial multi-module features and critical production paths. |

> **Escalation Guarantee**: A route may escalate to higher scrutiny if unexpected complexity is discovered during execution, but it will **never silently downgrade**.

---

## Token Economics & Verification Tooling

By delegating verbose code generation to Flash and isolating the review to a fresh context, Gemini Advisor dramatically reduces total spend:

| Phase | Monolithic Approach (All Frontier Argon) | Gemini Advisor Triad | Net Impact |
| :--- | :--- | :--- | :--- |
| **Planning** | 4,000 Argon tokens | 4,000 Argon tokens | Neutral |
| **Implementation** | 40,000 Argon tokens | 40,000 **Flash** tokens | **~90% Cost Reduction** |
| **Build & Test Output** | 30,000 Argon tokens | 30,000 **Flash** tokens | **~90% Cost Reduction** |
| **Independent Audit** | 50,000 Argon tokens (accumulated context) | 5,000 **Fresh Argon** tokens (isolated diff) | **~90% Context Reduction** |
| **Effective Total** | **124,000 Argon tokens** | **9,000 Argon + 70,000 Flash tokens** | **~80–90% Lower Cost** |

### Integrated Token Counter CLI

Gemini Advisor includes an integrated tokenizer and cost estimator (`scripts/token_counter.sh`) calibrated for Gemini's 256k vocabulary:

```bash
# Run automated verification self-tests
bash ~/.gemini-advisor/scripts/token_counter.sh --test

# Compare Monolithic vs Triad ROI on standard tasks
bash ~/.gemini-advisor/scripts/token_counter.sh --compare

# Measure token count of a file or directory
bash ~/.gemini-advisor/scripts/token_counter.sh --file path/to/file.ts
bash ~/.gemini-advisor/scripts/token_counter.sh --dir src/

# Count tokens in the active git diff before review
bash ~/.gemini-advisor/scripts/token_counter.sh --diff

# Measure tokens in an Antigravity conversation transcript
bash ~/.gemini-advisor/scripts/token_counter.sh --transcript ~/.gemini/antigravity/transcript.jsonl
```

---

## Maintenance & Verification

### Running the Test Suite
Ensure all manifests, reference documentation, shell scripts, and tokenizer tests pass:
```bash
bash ~/.gemini-advisor/scripts/verify.sh
```

### Running Model Allocator Tests
```bash
bash ~/.gemini-advisor/scripts/model_allocator.sh --test
```

### Running Token Counter Tests
```bash
bash ~/.gemini-advisor/scripts/token_counter.sh --test
```

### Updating to the Latest Release
```bash
cd ~/.gemini-advisor
git pull origin main
bash scripts/install.sh --check
```

### Uninstalling
```bash
rm -f ~/.gemini/config/plugins/gemini-advisor
rm -rf ~/.gemini-advisor
```

---

## Repository Structure

```text
.
├── plugin.json                              # Antigravity plugin manifest
├── plugins/
│   └── gemini-advisor/
│       └── plugin.json                      # Nested discovery manifest
├── config/
│   └── model_tiers.json                     # Model tier registry & scoring rules
├── rules/
│   ├── AGENTS.md                            # Active rules enforcing dynamic route declarations & roles
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
│   ├── model_allocator.py                   # Dynamic model discovery & scoring engine
│   ├── model_allocator.sh                   # CLI wrapper for model allocator
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
