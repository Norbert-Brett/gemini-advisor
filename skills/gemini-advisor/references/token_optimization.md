# Token Optimization Guide

Gemini Advisor is explicitly engineered to achieve the highest possible code quality while drastically reducing total token burn. This document explains the quantitative principles and operational techniques behind dynamic Frontier-to-Execution tier allocation.

---

## 1. The Multi-Model Cost Reality

In modern agentic AI systems, models fall into distinct capability and cost tiers:
- **Frontier / Apex Tier (e.g., Gemini 4 Argon)**: The highest reasoning capability, deepest problem-solving depth, and strongest architectural judgment available. Ideal for architectural decomposition, precise contract definition, and strict, unbiased code audits.
- **Professional Tier (e.g., Gemini Pro)**: Strong general-purpose reasoning and fallback analysis.
- **Execution / High-Velocity Tier (e.g., Gemini Flash / Flash-Lite)**: Extremely high throughput, minimal latency, and drastically lower token cost (**10x to 30x cheaper** than Frontier models).

### The Monolithic Anti-Pattern
In traditional agent interactions, a single high-tier model is used for every step:
- Reading large project files: Expensive Frontier tokens.
- Generating repetitive boilerplate classes and methods: Expensive Frontier tokens.
- Parsing hundreds of lines of compiler logs, terminal chatter, and tracebacks: Expensive Frontier tokens.
- Accumulated context of 100,000+ tokens repeatedly re-sent on every single turn: Enormous financial and token burn.

### The Gemini Advisor Pattern
By separating concerns across dynamically discovered tiers:
1. **Planning is concise**: The Architect (Gemini 4 Argon) expends only a few thousand tokens to analyze requirements and generate an exact 5-part contract.
2. **Implementation is offloaded**: The Builder (Gemini Flash or Flash-Lite) processes verbose files, executes commands, and writes code at a fraction of the cost, saving **80–90%** on implementation token spend.
3. **Auditing is isolated**: The Reviewer (Fresh Gemini 4 Argon via `Model: "inherit"`) receives only a distilled unified diff (~50–200 lines) and verification evidence (~30 lines), evaluating in a fresh ~3,000-token context without re-ingesting a 150,000-token historical backlog.

---

## 2. Quantified Token Savings Comparison

Consider a representative feature implementation (e.g., adding a new authenticated endpoint with unit tests):

| Workflow Step | Monolithic (All Frontier / Argon) | Gemini Advisor Triad | Effective Savings |
| :--- | :--- | :--- | :--- |
| **Requirements & Planning** | 4,000 tokens (Frontier Argon) | 4,000 tokens (Frontier Argon) | Equivalent |
| **Code Implementation & Edits** | 40,000 tokens (Frontier Argon) | 40,000 tokens (**Gemini Flash**) | **~90% Cost Reduction** |
| **Terminal & Test Iterations** | 30,000 tokens (Frontier Argon) | 30,000 tokens (**Gemini Flash**) | **~90% Cost Reduction** |
| **Independent Audit / Verification** | 50,000 tokens (Accumulated Argon context) | 5,000 tokens (**Fresh Frontier Argon**) | **~90% Context Reduction** |
| **Total Effective Cost Profile** | **124,000 Frontier Argon tokens** | **9,000 Frontier Argon + 70,000 Flash tokens** | **~80–90% Overall Cost Reduction** |

---

## 3. Dynamic Model Allocation Tooling (`scripts/model_allocator.sh`)

Gemini Advisor includes an automated model discovery and tier allocation CLI (`scripts/model_allocator.sh`) so no manual package updates are required when newer models release:

```bash
# Check currently detected Frontier and Execution models
bash scripts/model_allocator.sh --check

# Recommend model allocation for the active task
bash scripts/model_allocator.sh --allocate

# Discover all available models from environment, transcripts, and API
bash scripts/model_allocator.sh --discover

# Calculate the heuristic capability score for a specific model name
bash scripts/model_allocator.sh --score "gemini-4-argon"
bash scripts/model_allocator.sh --score "gemini-2.5-pro"
bash scripts/model_allocator.sh --score "gemini-2.5-flash"

# Run automated tests on model discovery and tier scoring
bash scripts/model_allocator.sh --test
```

---

## 4. Core Techniques for Burning Fewer Tokens

### 1. Diff Distillation (Don't Re-send Full Files)
Instead of feeding entire files to the reviewer, generate a compact unified diff using `scripts/diff_summary.sh`:
```bash
git diff -U3 -- <file_list>
```
This strips away thousands of lines of unmodified boilerplate and focuses the reviewer's attention strictly on the delta.

### 2. Context Pruning via Subagents
When a subagent completes its task, Antigravity records its conversation in transcripts, but only the structured `IMPLEMENTATION REPORT` is returned to the parent agent. All intermediate terminal chatter, retry loops, and temporary debugging steps stay inside the subagent and do NOT pollute the main conversation context.

### 3. Smart Fallback to `solo`
Spawning subagents has a baseline coordination overhead (~500 tokens). For tasks that only touch 1 file and take < 20 lines of code, running in `solo` mode is strictly cheaper and faster. Use the [Selective Routing Matrix](routing_matrix.md) to guard against unnecessary delegation.

### 4. Flash-Lite for Repetitive Generation
For purely mechanical code generation tasks (e.g., generating 20 mock data fixtures, converting JSON schemas to TypeScript interfaces, or generating boilerplate CRUD routes), invoke the builder with `Model: "flash_lite"`.

---

## 5. Token Counter CLI (`scripts/token_counter.sh`)

Gemini Advisor includes an integrated tokenizer and cost estimator calibrated for Gemini's 256k vocabulary:

```bash
# Compare Monolithic vs Triad ROI
bash scripts/token_counter.sh --compare

# Estimate tokens for a file before passing it to an agent
bash scripts/token_counter.sh --file path/to/source.py

# Check how many tokens a diff will consume during audit
bash scripts/token_counter.sh --diff

# Audit an actual conversation transcript to inspect token distributions
bash scripts/token_counter.sh --transcript ~/.gemini/antigravity/transcript.jsonl
```
