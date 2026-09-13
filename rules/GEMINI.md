# Gemini Advisor Rules (GEMINI.md)

This file ensures compatibility with Antigravity environments that discover `GEMINI.md`.

Please refer to [AGENTS.md](./AGENTS.md) for the authoritative rules:
- Declare `SELECTIVE ROUTE` before modifying files.
- Default to `solo`; delegate bounded implementation to Gemini Flash (`gemini_advisor_builder`).
- Route diffs to a fresh, unbiased read-only reviewer (`gemini_advisor_reviewer`) using Gemini Pro.
- Enforce evidence-based test verification before declaring completion.
- Maximize token efficiency through strict context pruning and diff distillation.
