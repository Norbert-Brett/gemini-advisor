# The Three Golden Advisor Triggers

In the Gemini Advisor architecture, the Frontier model (e.g. **Gemini 4 Argon** or **Claude Opus 5.5**) is the most capable and reasoning-intensive model in the fleet. To prevent unnecessary token burn and latency on routine turns, **the Advisor does NOT run routine code edits or exploratory lookups**.

Instead, the Advisor stays **on-call** and steps in strictly at **Three Golden Trigger Moments**:

```
                       ┌─────────────────────────┐
                       │   Routine Session Turn  │
                       │ (Builder / Main Driver) │
                       └────────────┬────────────┘
                                    │
               ┌────────────────────┴────────────────────┐
               │         JEV Micro-Router Check          │
               │        (Evaluated in < 0.05 ms)         │
               └────────────────────┬────────────────────┘
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         ▼                          ▼                          ▼
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│    TRIGGER 1     │      │    TRIGGER 2     │      │    TRIGGER 3     │
│    PLAN LOCK     │      │    ERROR LOOP    │      │    TASK DONE     │
│ (Before a plan   │      │ (Same error seen │      │ (Before calling  │
│  or contract is  │      │  2x in a row)    │      │  a task done or  │
│  locked/started) │      │                  │      │  shipping code)  │
└────────┬─────────┘      └────────┬─────────┘      └────────┬─────────┘
         │                         │                         │
         └─────────────────────────┼─────────────────────────┘
                                   │
                                   ▼
                     ┌───────────────────────────┐
                     │   FRONTIER ADVISOR CALL   │
                     │  (Gemini 4 Argon / Opus)  │
                     │  Full Transcript / Audit  │
                     └───────────────────────────┘
```

---

## 1. Trigger 1: Before a Plan Locks (`plan_lock`)

### When It Fires
- The Architect or Main Driver has analyzed the problem and drafted an architectural approach or 5-part implementation contract.
- **Before** any file mutations, code edits, or subagent builder handoffs occur.

### Why It Matters
A flawed architectural assumption caught at minute 1 costs 1,000 tokens to fix. The same flaw caught after 500 lines of code have been written costs 50,000 tokens and 30 minutes of debugging. The Advisor's superior reasoning catches:
- Missed edge cases and subtle API breaking changes.
- Unnecessary complexity or overly broad blast radius.
- Opportunities for reuse vs. reinventing existing utilities.

### Advisor Input Package
```text
ADVISOR CONSULTATION REQUEST: PLAN LOCK
OBJECTIVE: <What the user requested>
PROPOSED PLAN: <The drafted steps, architecture, and file ownership>
PLANNED INTERFACES: <New/modified function signatures, schemas, flags>
VERIFICATION STRATEGY: <Commands and criteria to prove correctness>
REASON FOR CONSULTATION: Trigger 1 (Plan Lock) - Verify architectural soundess before code generation.
```

### Expected Advisor Verdict
- `APPROVE_PLAN`: Plan is sound, scoped, and safe to execute.
- `REVISE_PLAN`: Actionable objections and structural revisions required before implementation.

---

## 2. Trigger 2: When the Same Error Shows Up Twice (`error_loop`)

### When It Fires
- JEV's error fingerprinting engine (`scripts/jev_router.py --check-error`) detects that an identical normalized error hash has occurred **twice in succession**.
- Fires across test failures, compiler/type errors, linter violations, or runtime exceptions.

### Why It Matters
When smaller execution models (Flash / Sonnet / Haiku) encounter an error, they can usually fix simple typos on the first retry. However, if the exact same error recurs on attempt 2, the model has fallen into an **assumption trap / hallucination loop**. Letting the builder retry a third or fourth time burns tokens and usually compounds the bug.
- **Rule**: On the 2nd identical error, **HALT ALL BUILDER MUTATIONS IMMEDIATELY**.
- Pass the full traceback, diff, and both attempts to the Frontier Advisor.

### Advisor Input Package
```text
ADVISOR CONSULTATION REQUEST: ERROR LOOP TRIPPED
RECURRENCE COUNT: 2 (Identical normalized error signature detected by JEV)
ERROR SIGNATURE: <Normalized error message & traceback>
FAILED COMMAND: <Exact command executed, e.g. pytest or bash scripts/verify.sh>
ATTEMPT 1 SUMMARY: <What was changed in attempt 1>
ATTEMPT 2 SUMMARY: <What was changed in attempt 2>
CURRENT GIT DIFF: <Diff of current changes>
REASON FOR CONSULTATION: Trigger 2 (Error Loop) - Break hallucination loop and determine root cause.
```

### Expected Advisor Diagnosis
- **Root Cause**: Identifies the fundamental misconception (e.g. wrong mock, unhandled async timing, circular import, stale cache).
- **Prescription**: Exact, unambiguous instruction on how to fix the underlying issue.

---

## 3. Trigger 3: Before Calling It Done (`task_done`)

### When It Fires
- Implementation is complete, all builder verification commands report passing exit codes, and the driver is ready to report completion or commit.
- **Before** notifying the user that the task is finished.

### Why It Matters
Builders suffer from confirmation bias: they test what they wrote, not what might have broken elsewhere. The Frontier Advisor conducts a **fresh, unbiased, zero-tolerance review**:
- Scrutinizes the entire accumulated `git diff`.
- Checks for security oversights, accidental credential leakage, or deleted comments.
- Verifies backward compatibility of existing public APIs.
- Confirms evidence-first proof (real test output, not assertions of success).

### Advisor Input Package
```text
ADVISOR CONSULTATION REQUEST: TASK COMPLETION AUDIT
OBJECTIVE: <Original task requirement>
FULL GIT DIFF: <git diff output or scripts/diff_summary.sh output>
VERIFICATION EVIDENCE: <Actual test suite / linter / compiler logs>
CHECKLIST:
- Did we fulfill the user's explicit objective?
- Are there regressions, security flaws, or style violations?
REASON FOR CONSULTATION: Trigger 3 (Task Done) - Final acceptance signoff.
```

### Expected Advisor Verdict
- `VERDICT: SHIP`: All criteria met, evidence verified, code ready for production.
- `VERDICT: FIX-FIRST`: Concrete list of blockers or missing tests to resolve before signoff.
- `VERDICT: RETHINK`: Changes violate fundamental constraints; plan must be revisited.

---

## JEV Integration

JEV evaluates whether any of the Three Golden Triggers are active in sub-millisecond time:

```bash
# Check if current stage trips Trigger 1 (Plan Lock)
python3 scripts/jev_router.py --advisor-trigger --stage plan_lock

# Check if an error trips Trigger 2 (Error Loop)
python3 scripts/jev_router.py --advisor-trigger --stage error --error "AssertionError: expected 200 got 500"

# Check if current stage trips Trigger 3 (Task Done)
python3 scripts/jev_router.py --advisor-trigger --stage task_done
```
