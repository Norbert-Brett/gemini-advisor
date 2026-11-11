# Gemini Advisor Operating Rules

When the Gemini Advisor plugin is active, all Antigravity agents operating within this workspace must adhere to the following principles:

## 1. Upfront Route Declaration & JEV Micro-Routing Check
- Before calling any modifying tools (`write_file`, `edit_file`, destructive `run_command`), the Architect MUST verify active model tiers (via `scripts/model_allocator.sh --check` or JEV `scripts/jev_router.sh --route`) and emit a machine-auditable `SELECTIVE ROUTE` block declaring `mode` (`solo`, `delegate`, `audit`, `full`), `risk`, and dynamic `allocation`.
- Default to `solo` for low-risk, localized tasks (< 3 files) to avoid unnecessary orchestration token burn.
- Never silently downgrade a route. Upgrades/escalations require newly discovered risk evidence.

## 2. Dynamic 4-Tier Role Segregation
- **On-Call Frontier Advisor (Frontier Thinking Tier — e.g. Gemini 4 Argon / Claude Opus 5.5)**: Stays on call for apex judgment calls. Consulted strictly at the **Three Golden Triggers** without burning tokens on routine turns.
- **Main Driver / Builder (Execution Tier — Gemini Flash / Sonnet 5.5)**: Executes implementation, writes code, and runs builds at 10–30x lower token cost. Must strictly adhere to file ownership boundaries and never modify files outside declared scope.
- **Parallel Read-Only Scouts (Lite Tier — Gemini Flash-Lite / Haiku 5.5)**: Dispatched concurrently for exploratory tasks without context bloat:
  - `gemini_advisor_search`: Maps repository structure, inspects directories, and finds file paths.
  - `gemini_advisor_grep`: Searches call sites, locates symbol definitions, and runs regex queries.
  - `gemini_advisor_docs`: Retrieves API reference documentation, specs, and Context7 materials.
- **JEV Micro-Router (System One Engine)**: Resolves fast deterministic forks (tool selection, path ranking, error loop detection) in sub-millisecond time (<0.02ms) with zero token cost.

## 3. The Three Golden Advisor Triggers
The Frontier Advisor must be consulted at three critical moments:
1. **Trigger 1: Plan Lock (`plan_lock`)**: Consult the Advisor before locking any architectural plan or 5-part contract to verify safety, blast radius, and edge case coverage.
2. **Trigger 2: Error Loop (`error_loop`)**: When JEV detects the **identical normalized error signature twice in succession**, the Builder must HALT execution immediately and consult the Advisor for root-cause diagnosis.
3. **Trigger 3: Task Done (`task_done`)**: Before marking any task complete or committing changes, a fresh read-only Reviewer/Advisor must audit the accumulated git diff and test evidence.

## 4. Zero-Maintenance Model Auto-Allocation
- Model selection is never hardcoded to a legacy generation. `scripts/model_allocator.sh` automatically discovers, scores, checks, and allocates newly released models across environment overrides, live Antigravity transcripts, and the Gemini API so new frontier models outrank older ones automatically.

## 5. Evidence-First Verification
- No task is complete based on an agent's claim alone.
- Every code change must be accompanied by concrete verification output (compiler logs, test suite runs, or linters).
- If the reviewer returns `FIX-FIRST`, remediate the specified issues and request a new review until `SHIP` is granted.

## 6. Token Frugality
- Never paste entire multi-hundred line files when a unified diff or targeted line range is sufficient.
- Keep subagent prompts structured and scoped.
- Isolate trial-and-error logs inside subagent sessions rather than ballooning the primary conversation context.
