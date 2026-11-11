# Gemini Advisor Rules (GEMINI.md)

This file ensures compatibility with Antigravity and Gemini environments that discover `GEMINI.md`.

Please refer to [AGENTS.md](./AGENTS.md) for authoritative rules:
- Run JEV pre-flight checks (`scripts/jev_router.sh --route`) and emit `SELECTIVE ROUTE` before modifying files.
- Organize tasks across the **4-Tier Cognitive Hierarchy**:
  1. **On-Call Frontier Advisor** (`gemini-4-argon` / `inherit`): Consulted strictly at the **Three Golden Triggers** (Plan Lock, Error Loop 2x, Task Done).
  2. **Main Builder** (`gemini-3.8-flash` / `flash`): High-speed bounded code implementation.
  3. **Parallel Read-Only Scouts** (`gemini-3.1-flash-lite` / `flash_lite`): `search` (maps repo), `grep` (finds call sites), `docs` (pulls API references).
  4. **JEV Micro-Router** (`scripts/jev_router.sh`): Sub-millisecond deterministic micro-forks (< 0.02ms, 0 tokens).
- Route diffs to a fresh, unbiased read-only reviewer (`gemini_advisor_reviewer`) using `Model: "inherit"` (preserving Frontier tier e.g., Gemini 4 Argon) or `"pro"` fallback.
- Auto-allocate models without manual package updates (`scripts/model_allocator.sh`).
- Enforce evidence-based test verification before declaring completion.
- Cross-platform support for Claude Code via [CLAUDE.md](./CLAUDE.md).
