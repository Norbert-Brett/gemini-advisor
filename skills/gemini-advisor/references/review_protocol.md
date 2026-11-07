# Unbiased Review Protocol

This protocol defines the inspection guidelines, audit rubric, and verdict taxonomy for the independent **Gemini Advisor Reviewer**.

---

## 1. Why an Isolated Reviewer?

In traditional agent workflows, the agent that writes the code also checks the code. This introduces two major problems:
1. **Confirmation Bias**: The model tends to justify its own mistakes or believe its implementation works even when subtle flaws exist.
2. **Context Window Contamination**: The long conversation history filled with previous trial-and-error attempts clutters the model's attention, causing it to overlook regressions.

**The Gemini Advisor Solution**:
The Reviewer is launched as a brand-new subagent (`gemini_advisor_reviewer`) with:
- **Clean context**: Only receives the objective, git diff, and test run logs without conversational baggage.
- **`enable_write_tools: false`**: Physical enforcement that the reviewer cannot introduce untested edits or attempt quick-and-dirty patches.
- **Frontier-tier reasoning (`Gemini 4 Argon` via `inherit` or `pro` fallback)**: Applies state-of-the-art analytical capabilities solely to critique and verification in an isolated, read-only context. Using `Model: "inherit"` ensures that when the parent session runs on Gemini 4 Argon, the auditor audits with matching Frontier intelligence rather than downgrading to `pro`.

---

## 2. Review Package Assembly

The parent session prepares the review package using this standard prompt structure:

```text
OBJECTIVE:
<The user's original goal and acceptance requirements.>

SPECIFICATION CONTRACT:
<Declared interfaces, file boundaries, and constraints provided to builder.>

CHANGED FILES & DIFF:
<Output from git diff or scripts/diff_summary.sh>

VERIFICATION EVIDENCE:
<Commands executed by parent/builder and actual test outputs.>

INSTRUCTIONS:
Conduct an independent, unbiased review against the rubric. Output:
1. AUDIT REPORT (SUMMARY, FINDINGS with severity, CHECKLIST)
2. FINAL VERDICT: SHIP | FIX-FIRST | RETHINK
```

---

## 3. Four-Pillar Audit Rubric

The Reviewer inspects every proposed change across four distinct pillars:

### Pillar 1: Contract & Boundary Compliance
- Did the builder modify any files outside its declared ownership?
- Are all function signatures, return types, public API schemas, and CLI arguments compatible with the contract?
- Were unintended modifications made to unrelated files?

### Pillar 2: Correctness & Logic Flaws
- Are there off-by-one errors, unhandled `null`/`undefined` cases, or missing error branches?
- Does the code handle edge cases (empty inputs, network timeouts, concurrency)?
- Are async/await promises properly caught and resolved?

### Pillar 3: Security & Resource Safety
- Are there secret leaks, unvalidated user inputs (SQL injection, XSS, shell command injection)?
- Are database transactions properly rolled back on failure?
- Are memory leaks, unclosed file descriptors, or zombie background tasks introduced?

### Pillar 4: Test Coverage & Verification Integrity
- Were actual automated tests executed, or did the builder simply claim "verified"?
- Do the tests genuinely assert the expected behavior or are they trivial/tautological assertions?

---

## 4. Verdicts & Actions

| Verdict | Meaning | Next Action for Architect |
| :--- | :--- | :--- |
| **`SHIP`** | All checks pass without blocker or warning findings. Code meets all criteria. | The Architect accepts the changes, performs final commit/walkthrough, and reports completion to the user. |
| **`FIX-FIRST`** | Code has localized bugs, edge cases, missing test cases, or style issues that must be addressed. | The Architect packages the findings into a targeted remediation contract for the Builder (Flash) or fixes directly, then reruns verification and requests a fresh review. |
| **`RETHINK`** | The fundamental design or architectural premise is flawed, breaking core constraints or interfaces. | The Architect stops implementation, discards invalid changes, re-evaluates the technical plan, and realigns with the user. |
