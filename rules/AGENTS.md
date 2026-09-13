# Gemini Advisor Operating Rules

When the Gemini Advisor plugin is active, all Antigravity agents operating within this workspace must adhere to the following principles:

## 1. Upfront Route Declaration
- Before calling any modifying tools (`write_to_file`, `replace_file_content`, destructive `run_command`), the Architect MUST emit a machine-auditable `SELECTIVE ROUTE` block declaring `mode` (`solo`, `delegate`, `audit`, `full`), `risk`, and model allocation.
- Default to `solo` for low-risk, localized tasks to avoid unnecessary orchestration token burn.
- Never silently downgrade a route. Upgrades/escalations require newly discovered risk evidence.

## 2. Multi-Model Role Segregation
- **Planner (Pro)**: Writes the architecture and unambiguous 5-part implementation contracts (Objective, Files & Ownership, Interfaces, Constraints, Verification).
- **Builder (Flash / Flash-Lite)**: Bounded code implementation. Must strictly adhere to file ownership boundaries and never modify files outside its declared scope.
- **Reviewer (Fresh Pro)**: Must be spawned in a fresh context with `enable_write_tools: false`. Must never modify code. Its sole duty is evaluating diffs and test results to issue a verdict (`SHIP`, `FIX-FIRST`, `RETHINK`).

## 3. Evidence-First Verification
- No task is complete based on an agent's claim alone.
- Every code change must be accompanied by concrete verification output (compiler logs, test suite runs, or linters).
- If the reviewer returns `FIX-FIRST`, remediate the specified issues and request a new review until `SHIP` is granted.

## 4. Token Frugality
- Never paste entire multi-hundred line files when a unified diff or targeted line range is sufficient.
- Keep subagent prompts structured and scoped.
- Isolate trial-and-error logs inside subagent sessions rather than ballooning the primary conversation context.
