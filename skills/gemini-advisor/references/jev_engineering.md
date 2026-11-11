# JEV Engineering & Micro-Routing Architecture

**JEV (Joint Evaluation & Value)** is a high-speed, zero-token "System One" decision engine. While heavy Large Language Models (Gemini 4 Argon, Claude Opus, Gemini Flash) stream natural language and generate code, JEV executes deterministic micro-evaluations across structured criteria in **sub-millisecond time**.

---

## 1. The Micro-Fork Philosophy

In typical agent execution, agents waste millions of expensive tokens on trivial micro-forks:
- *Which tool should I invoke for this search?* (Takes 1-3 seconds and 1,500 tokens in an LLM).
- *Which file matches this symbol?* (Burns tokens generating list directory calls).
- *Did this error just happen again?* (LLMs often overlook that they just ran the same failing edit).
- *Should I use `solo`, `delegate`, or `audit`?*

**JEV Engineering moves these micro-forks one layer down**:
> The forks that need no deep thinker (tool selection, path ranking, retry vs. loop detection, explorer dispatch) go to **JEV in microseconds**.
> The big models only see the forks that split the full tree.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        AGENT ARCHITECTURE TIERS                        │
├──────────────┬─────────────────────────┬───────────────┬───────────────┤
│ Tier         │ Model / Engine          │ Typical Time  │ Cost / Decision│
├──────────────┼─────────────────────────┼───────────────┼───────────────┤
│ L1 Micro-Fork│ JEV Router (Python std) │ 0.010 ms      │ $0.00000000   │
│ L2 Explorers │ Flash-Lite / Haiku 5.5  │ 300 - 800 ms  │ $0.0000375    │
│ L3 Execution │ Flash 3.8 / Sonnet 5.5  │ 1.0 - 2.5 s   │ $0.0000750    │
│ L4 Advisor   │ Gemini 4 Argon / Opus   │ On-Call Only  │ $0.0025000    │
└──────────────┴─────────────────────────┴───────────────┴───────────────┘
```

---

## 2. JEV Micro-Routing Capabilities

### A. Deterministic Route Evaluation (`--route`)
Evaluates structural blast radius, file counts, and cryptographic/security markers:
- `solo`: Localized changes (<3 files, low risk).
- `delegate`: Bounded implementations (features, tests) handed to Flash/Flash-Lite.
- `audit`: Sensitive subsystems written by parent, audited by fresh Frontier.
- `full`: Multi-file, high-risk features requiring both delegated implementation and fresh Frontier audit.

```bash
python3 scripts/jev_router.py --route --task "Add search subagent tests" --files scripts/jev_router.py tests/test_jev.py
```

### B. Fast Tool Selection (`--tool-choice`)
Maps natural language intent directly to the optimal tool signature:
- Call sites and symbol queries -> `gemini_advisor_grep`
- Repository tree and file layout -> `gemini_advisor_search`
- External API / spec documentation -> `gemini_advisor_docs`
- Surgical modifications -> `edit_file`
- New files -> `write_file`
- Testing / commands -> `run_command`

```bash
python3 scripts/jev_router.py --tool-choice --task "Find all call sites of resolve_allocation"
# Output: TOOL: gemini_advisor_grep (Confidence: 0.95)
```

### C. Path Selection (`--select-path`)
Scans project files in memory, tokenizes query strings, and returns ranked relative file paths in under 10ms.

```bash
python3 scripts/jev_router.py --select-path --task "model allocator python tests"
# Output:
# MATCHED PATHS:
#   - scripts/model_allocator.py
#   - scripts/model_allocator.sh
#   - config/model_tiers.json
```

### D. Error Normalization & Loop Breaker (`--check-error`)
Normalizes volatile error details (timestamps, line numbers, memory pointers, absolute file paths) to generate a stable SHA-256 fingerprint:
- **Attempt 1**: `action: RETRY` (Single failure is allowed to retry).
- **Attempt 2**: `action: ESCALATE_ADVISOR`, `trigger_advisor: True`!
Trips **Advisor Trigger 2 (Error Loop)** immediately to halt builder hallucination.

```bash
python3 scripts/jev_router.py --check-error --error "AssertionError: expected 200 got 500 at line 42"
```

### E. Explorer Dispatch (`--explorer-route`)
Directs exploratory read queries to the matching parallel scout:
- `search` (maps directory structures)
- `grep` (locates symbols and usages)
- `docs` (retrieves API references)

---

## 3. Performance Benchmark & Latency SLA

JEV is built with zero external Python dependencies using high-performance standard library primitives (`hashlib`, `re`, `json`, `pathlib`).

Benchmark results over 1,000 continuous decisions:
- **Average Decision Latency**: **0.010 ms (10 microseconds)**
- **P50 Latency**: **0.009 ms**
- **P95 Latency**: **0.011 ms**
- **P99 Latency**: **0.021 ms**
- **Token Cost**: **0 tokens**

To run the benchmark in your local environment:
```bash
python3 scripts/jev_router.py --benchmark
```
