# Gemini Advisor Rules (GEMINI.md)

This file ensures compatibility with Antigravity environments that discover `GEMINI.md`.

Please refer to [AGENTS.md](./AGENTS.md) for the authoritative rules:
- Check active model tiers dynamically (`scripts/model_allocator.sh --check`) and declare `SELECTIVE ROUTE` before modifying files.
- Default to `solo`; delegate bounded code implementation to economical Gemini Flash / Flash-Lite (`gemini_advisor_builder`).
- Route diffs to a fresh, unbiased read-only reviewer (`gemini_advisor_reviewer`) using `Model: "inherit"` (preserving Frontier tier e.g., Gemini 4 Argon) or `"pro"` fallback.
- Auto-allocate models without manual package updates (`scripts/model_allocator.sh`).
- Enforce evidence-based test verification before declaring completion.
- Maximize token efficiency through strict context pruning and diff distillation.
