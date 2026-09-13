# Token Optimization Guide

Gemini Advisor is explicitly engineered to achieve the highest possible code quality while drastically reducing total token burn. This document explains the quantitative principles and operational techniques behind this efficiency.

---

## 1. The Multi-Model Cost Reality

In modern agentic AI systems, models fall into distinct tiers:
- **High-Reasoning Tier (e.g. Gemini Pro)**: Superior architectural judgment, complex contract reasoning, deep problem solving.
- **High-Velocity Tier (e.g. Gemini Flash / Flash-Lite)**: Extremely high throughput, low latency, lower token cost (~10x to 20x cheaper than Pro).

### The Monolithic Anti-Pattern
In typical agent interactions, a single high-reasoning model is used for the entire session:
- Reading large files: High-cost tokens.
- Writing boilerplate repetitive functions: High-cost tokens.
- Running compilers and parsing 500 lines of build logs: High-cost tokens.
- Accumulated context of 100,000+ tokens re-sent on every single turn: Enormous token burn.

### The Gemini Advisor Pattern
By separating concerns across specialized models:
1. **Planning is concise**: The Architect (Pro) only needs a few thousand tokens to analyze and produce a tight 5-part contract.
2. **Implementation is delegated**: The Builder (Flash) processes the voluminous file contents, runs commands, and writes code at a fraction of the cost.
3. **Auditing is isolated**: The Reviewer (Fresh Pro) only receives a compact diff (~50-200 lines) and test outputs (~30 lines), evaluating in a fresh ~3,000-token context rather than re-ingesting a 150,000-token historical backlog.

---

## 2. Quantified Token Savings Comparison

Consider a representative feature implementation (e.g., adding a new authenticated endpoint with unit tests):

| Workflow Step | Monolithic (Single Pro Agent) | Gemini Advisor Triad | Effective Savings |
| :--- | :--- | :--- | :--- |
| **Requirements & Planning** | 4,000 tokens (Pro) | 4,000 tokens (Pro) | Equivalent |
| **Code Implementation & Edits** | 40,000 tokens (Pro) | 40,000 tokens (Flash) | **~90% Cost Reduction** |
| **Terminal & Test Iterations** | 30,000 tokens (Pro) | 30,000 tokens (Flash) | **~90% Cost Reduction** |
| **Self-Review / Verification** | 50,000 tokens (Accumulated Pro context) | 5,000 tokens (Fresh Pro isolated diff) | **~90% Context Reduction** |
| **Total Effective Cost Profile** | **124,000 Pro tokens** | **9,000 Pro tokens + 70,000 Flash tokens** | **~75-80% Overall Cost Reduction** |

---

## 3. Core Techniques for Burning Fewer Tokens

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
