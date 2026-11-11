# Claude Code Advisor & JEV Operating Rules

When operating Claude Code with the Gemini Advisor framework:

## 1. Launch Command & Model Split
Launch Claude Code using the multi-model advisor architecture:
```bash
claude --model sonnet --advisor opus
```

### The Split
- **Sonnet 5.5**: Runs the main interactive session, edits code, runs builds, and implements features.
- **Haiku 5.5**: Three parallel read-only subagents for exploration:
  - `search`: Maps repository structure and locates relevant files.
  - `grep`: Finds symbol call sites, definitions, and regex occurrences.
  - `docs`: Pulls API references, documentation, and external specifications.
- **Opus 5.5**: On-call Advisor for apex judgment calls. Reads the full transcript/diff only when summoned.
- **JEV**: Micro-routing engine running locally in milliseconds for deterministic micro-forks (tool choice, path matching, loop breaking).

---

## 2. The Three Golden Advisor Triggers
Consult the Opus 5.5 advisor strictly at these three moments:
1. **Before a Plan Locks (`plan_lock`)**: Verify architecture, blast radius, and 5-part contract before code editing begins.
2. **When the Same Error Shows Up Twice (`error_loop`)**: Halt execution immediately when JEV detects an identical normalized error hash 2x. Consult Advisor to diagnose root cause and break the hallucination loop.
3. **Before Calling It Done (`task_done`)**: Request an unbiased audit of the accumulated git diff and verification evidence before completing the task.

---

## 3. Fast Deterministic Forks Through JEV
Before making exploratory or tool choices, route fast deterministic forks through JEV:
```bash
# Determine delivery mode (solo, delegate, audit, full)
python3 scripts/jev_router.py --route --task "<task description>"

# Map intent to tool signature
python3 scripts/jev_router.py --tool-choice --task "<intent>"

# Track error recurrence
python3 scripts/jev_router.py --check-error --error "<error string>"
```

---

## 4. Verification & Clean Diffs
- Always run local test commands (`pytest`, `npm test`, `bash scripts/verify.sh`) before consulting the advisor on Trigger 3.
- Never paste entire multi-hundred-line files to the advisor; supply targeted unified diffs and execution evidence.
