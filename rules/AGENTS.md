# Gemini Advisor Operating Rules

When the Gemini Advisor plugin is active, all Antigravity agents operating within this workspace must adhere to the following principles:

## 1. Upfront Route Declaration & Dynamic Model Check
- Before calling any modifying tools (`write_to_file`, `replace_file_content`, `write_file`, `edit_file`, destructive `run_command`), the Architect MUST verify active model tiers (via `scripts/model_allocator.sh --check` or session inspection) and emit a machine-auditable `SELECTIVE ROUTE` block declaring `mode` (`solo`, `delegate`, `audit`, `full`), `risk`, and dynamic `allocation`.
- Default to `solo` for low-risk, localized tasks to avoid unnecessary orchestration token burn.
- Never silently downgrade a route. Upgrades/escalations require newly discovered risk evidence.

## 2. Dynamic Multi-Model Role Segregation (Frontier Plan -> Cheap Execute -> Fresh Frontier Audit)
- **Planner / Architect (Frontier Thinking Tier — e.g., Gemini 4 Argon)**: Always uses the most advanced, highest-reasoning model available for thinking, architectural decomposition, and writing unambiguous 5-part implementation contracts.
- **Builder / Executor (Economical Execution Tier — Gemini Flash / Flash-Lite)**: Invoked via `gemini_advisor_builder` with `Model: "flash"` (or `"flash_lite"` for mechanical boilerplate) to execute the plan and write code at 10–30x lower token cost. Must strictly adhere to file ownership boundaries and never modify files outside its declared scope.
- **Reviewer / Auditor (Fresh Frontier Tier — e.g., Fresh Gemini 4 Argon)**: Spawned in a fresh context with `enable_write_tools: false`. Uses `Model: "inherit"` when the parent session is on a Frontier model (`Gemini 4 Argon` or newer) so it never downgrades to `pro`, or `Model: "pro"` if the parent is on a lower tier. Evaluates only diffs and test evidence to issue a verdict (`SHIP`, `FIX-FIRST`, `RETHINK`). Must never modify code.

## 3. Zero-Maintenance Model Auto-Allocation
- Model selection is never hardcoded to a legacy generation. `scripts/model_allocator.sh` automatically discovers, scores, checks, and allocates newly released models across environment overrides, live Antigravity transcripts, and the Gemini API so new frontier models outrank older ones automatically.

## 4. Evidence-First Verification
- No task is complete based on an agent's claim alone.
- Every code change must be accompanied by concrete verification output (compiler logs, test suite runs, or linters).
- If the reviewer returns `FIX-FIRST`, remediate the specified issues and request a new review until `SHIP` is granted.

## 5. Token Frugality
- Never paste entire multi-hundred line files when a unified diff or targeted line range is sufficient.
- Keep subagent prompts structured and scoped.
- Isolate trial-and-error logs inside subagent sessions rather than ballooning the primary conversation context.
