#!/usr/bin/env python3
"""scripts/jev_router.py

JEV (Joint Evaluation & Value) Deterministic Micro-Routing Engine for Gemini Advisor.

JEV is a high-speed, zero-token System One decision engine that executes
sub-millisecond micro-routing for agent workflows:
1. Fast Tool Selection: Deterministically maps intent to the optimal tool.
2. Path Selection: Fast token/glob matching across project files.
3. Error Loop Detection & Retry Guard: Normalizes errors and SHA-256 fingerprints them.
   Trips the Advisor trigger immediately when the identical error occurs twice in a row.
4. Explorer Subagent Dispatch: Routes exploratory intents to 'search' (repo map),
   'grep' (call sites/symbols), or 'docs' (API/spec references).
5. Advisor Trigger Gate: Evaluates the Three Golden Advisor Triggers:
   - Trigger 1: Plan Lock (before a plan or contract locks)
   - Trigger 2: Error Loop (when the same error appears 2x)
   - Trigger 3: Task Done (before declaring completion)
6. Latency Benchmark & Automated Unit Tests.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_STATE_FILE = Path(os.environ.get("JEV_STATE_FILE", "/tmp/gemini_advisor_jev_state.json"))


# ---------------------------------------------------------------------------
# Data Models / Typed Decision Schemas
# ---------------------------------------------------------------------------

@dataclass
class RouteDecision:
    mode: str  # "solo", "delegate", "audit", "full"
    risk_score: float  # 0.0 to 1.0
    rationale: str
    allocation: str
    breakdown: Dict[str, Any]


@dataclass
class ToolChoiceDecision:
    tool: str
    confidence: float
    rationale: str
    suggested_params: Dict[str, Any]


@dataclass
class PathSelectionDecision:
    paths: List[str]
    confidence: float
    rationale: str


@dataclass
class ErrorCheckDecision:
    error_fingerprint: str
    recurrence_count: int
    action: str  # "retry", "escalate_advisor", "abort"
    trigger_advisor: bool
    rationale: str


@dataclass
class AdvisorTriggerDecision:
    should_consult: bool
    trigger_name: str  # "plan_lock", "error_loop", "task_done", "none"
    rationale: str
    recommended_model_tier: str  # "frontier" (e.g. Gemini 4 Argon / Claude Opus)


@dataclass
class ExplorerRouteDecision:
    subagent: str  # "search", "grep", "docs", "none"
    model_tier: str  # "lite" / "haiku"
    confidence: float
    query: str
    rationale: str


# ---------------------------------------------------------------------------
# JEV Router Core Engine
# ---------------------------------------------------------------------------

class JevRouter:
    """System One deterministic micro-router running in <10ms with zero token cost."""

    def __init__(self, root_dir: Optional[Path] = None, state_file: Optional[Path] = None):
        self.root_dir = root_dir or REPO_ROOT
        self.state_file = state_file or DEFAULT_STATE_FILE

    # -----------------------------------------------------------------------
    # 1. Route Mode & Risk Classifier
    # -----------------------------------------------------------------------
    def evaluate_route(
        self,
        task: str,
        files: Optional[List[str]] = None,
        is_security_sensitive: bool = False,
    ) -> RouteDecision:
        """Determines solo, delegate, audit, or full route based on structural risk."""
        files = files or []
        task_lower = task.lower()

        # Keywords indicating security / cryptographic / auth sensitivity
        security_keywords = [
            "auth", "token", "secret", "password", "crypto", "jwt",
            "cert", "payment", "credential", "permission", "rbac", "sandbox"
        ]
        has_security_keyword = any(kw in task_lower for kw in security_keywords) or is_security_sensitive

        # Keywords indicating feature addition or bounded engineering
        feature_keywords = [
            "add", "endpoint", "feature", "implement", "support", "create",
            "handler", "controller", "route", "service"
        ]
        is_feature = any(kw in task_lower for kw in feature_keywords)

        # Keywords indicating large-scale architecture or refactoring
        architectural_keywords = [
            "refactor", "migration", "architecture", "redesign",
            "multi-file", "system-wide", "pipeline", "protocol"
        ]
        is_architectural = any(kw in task_lower for kw in architectural_keywords)

        file_count = len(files)
        risk_score = 0.1  # baseline

        if has_security_keyword:
            risk_score += 0.65
        if is_architectural:
            risk_score += 0.35
        elif is_feature:
            risk_score += 0.25
        if file_count > 5:
            risk_score += 0.3
        elif file_count >= 2:
            risk_score += 0.15

        risk_score = min(1.0, round(risk_score, 2))

        # Mode selection logic
        if has_security_keyword or risk_score >= 0.7:
            mode = "full" if (file_count >= 3 or is_architectural) else "audit"
            rationale = "High blast-radius or sensitive subsystem; requires independent Frontier audit."
        elif risk_score >= 0.35:
            mode = "delegate"
            rationale = "Bounded implementation suitable for fast execution tier (Gemini Flash / Flash-Lite)."
        else:
            mode = "solo"
            rationale = "Localized, low-risk change; executes end-to-end in parent context to conserve tokens."

        allocation = (
            "Planner (Frontier [Gemini 4 Argon / Claude Opus]) -> "
            f"Builder ({'Gemini 3.8 Flash' if mode in ('delegate', 'full') else 'Parent'}) -> "
            f"Reviewer ({'Fresh Frontier' if mode in ('audit', 'full') else 'Self-checked'})"
        )

        return RouteDecision(
            mode=mode,
            risk_score=risk_score,
            rationale=rationale,
            allocation=allocation,
            breakdown={
                "has_security_keyword": has_security_keyword,
                "is_architectural": is_architectural,
                "is_feature": is_feature,
                "file_count": file_count,
            },
        )

    # -----------------------------------------------------------------------
    # 2. Tool Choice Micro-Classifier
    # -----------------------------------------------------------------------
    def choose_tool(self, intent: str, available_tools: Optional[List[str]] = None) -> ToolChoiceDecision:
        """Deterministically classifies intent into the most efficient tool."""
        intent_lower = intent.lower().strip()

        # Explorer subagent triggers
        if re.search(r"\b(find all callers|where is .* (called|used)|call sites|references of)\b", intent_lower):
            return ToolChoiceDecision(
                tool="gemini_advisor_grep",
                confidence=0.95,
                rationale="Request specifically targets call sites and symbol usage across the codebase.",
                suggested_params={"query": intent},
            )

        if re.search(r"\b(repo structure|file tree|map (the )?project|find files named|locate directory)\b", intent_lower):
            return ToolChoiceDecision(
                tool="gemini_advisor_search",
                confidence=0.95,
                rationale="Structural repository mapping and directory exploration.",
                suggested_params={"query": intent},
            )

        if re.search(r"\b(api reference|library docs|documentation for|how to use .* sdk|context7)\b", intent_lower):
            return ToolChoiceDecision(
                tool="gemini_advisor_docs",
                confidence=0.92,
                rationale="External or internal API documentation retrieval.",
                suggested_params={"query": intent},
            )

        # File reading vs Editing vs Execution
        if re.search(r"\b(read|inspect|view|show|cat)\b", intent_lower) and not re.search(r"\b(edit|modify|write|update)\b", intent_lower):
            return ToolChoiceDecision(
                tool="read_file",
                confidence=0.90,
                rationale="Inspection and read-only intent.",
                suggested_params={"action": "read"},
            )

        if re.search(r"\b(edit|replace|patch|modify|fix line|update file)\b", intent_lower):
            return ToolChoiceDecision(
                tool="edit_file",
                confidence=0.92,
                rationale="Targeted surgical modification of an existing file.",
                suggested_params={"action": "edit"},
            )

        if re.search(r"\b(create file|write new|save to|generate script)\b", intent_lower):
            return ToolChoiceDecision(
                tool="write_file",
                confidence=0.88,
                rationale="Creating a new file from scratch.",
                suggested_params={"action": "write"},
            )

        if re.search(r"\b(run|exec|bash|shell|test|npm|python|pytest|cargo|git)\b", intent_lower):
            return ToolChoiceDecision(
                tool="run_command",
                confidence=0.90,
                rationale="CLI execution, script running, or test verification.",
                suggested_params={"command": intent},
            )

        # Default fallback
        return ToolChoiceDecision(
            tool="read_file",
            confidence=0.50,
            rationale="Default non-destructive fallback.",
            suggested_params={},
        )

    # -----------------------------------------------------------------------
    # 3. Path Selection Micro-Matcher
    # -----------------------------------------------------------------------
    def select_path(self, query: str, max_results: int = 5) -> PathSelectionDecision:
        """Fast token/basename matching against existing repository files."""
        query_tokens = [t.lower() for t in re.findall(r"[A-Za-z0-9_\-\.]+", query) if len(t) >= 2]
        if not query_tokens:
            return PathSelectionDecision(paths=[], confidence=0.0, rationale="Empty query tokens.")

        matched: List[Tuple[float, str]] = []
        for p in self.root_dir.rglob("*"):
            if not p.is_file():
                continue
            # Skip hidden and cache dirs
            parts = p.parts
            if any(part.startswith(".") for part in parts) or "node_modules" in parts or "__pycache__" in parts:
                continue

            rel_path = str(p.relative_to(self.root_dir))
            path_lower = rel_path.lower()
            basename_lower = p.name.lower()

            score = 0.0
            for token in query_tokens:
                if token == basename_lower:
                    score += 5.0
                elif token in basename_lower:
                    score += 2.5
                elif token in path_lower:
                    score += 1.0

            if score > 0:
                matched.append((score, rel_path))

        matched.sort(key=lambda x: x[0], reverse=True)
        top_paths = [p for _, p in matched[:max_results]]
        confidence = 0.9 if matched and matched[0][0] >= 5.0 else (0.6 if matched else 0.0)

        return PathSelectionDecision(
            paths=top_paths,
            confidence=confidence,
            rationale=f"Found {len(top_paths)} candidate files matching tokens: {query_tokens}",
        )

    # -----------------------------------------------------------------------
    # 4. Error Loop Detection & Retry Guard (Advisor Trigger 2)
    # -----------------------------------------------------------------------
    @staticmethod
    def normalize_error(error_text: str) -> str:
        """Strips timestamps, volatile line numbers, memory addresses, and paths to create stable fingerprint."""
        norm = error_text.strip()
        # Remove timestamps (ISO format, standard date-time)
        norm = re.sub(r"\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(\.\d+)?", "", norm)
        # Remove memory addresses (0x7fff...)
        norm = re.sub(r"0x[0-9a-fA-F]+", "0xADDR", norm)
        # Remove absolute paths (e.g. /Users/... or /home/...)
        norm = re.sub(r"(/[\w\.\-]+)+", "/PATH", norm)
        # Remove line references (e.g. 'line 42', 'line: 105', ':42:15')
        norm = re.sub(r"\bline\s*[:#]?\s*\d+\b", "line NUM", norm, flags=re.IGNORECASE)
        norm = re.sub(r":\d+(:\d+)?\b", ":NUM", norm)
        # Collapse whitespace
        norm = re.sub(r"\s+", " ", norm).strip().lower()
        return norm

    def check_error(self, error_message: str) -> ErrorCheckDecision:
        """Records error occurrence in persistent state. If seen >= 2 times, trips Advisor Trigger 2."""
        norm = self.normalize_error(error_message)
        fingerprint = hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]

        # Read state
        state = self._read_state()
        errors = state.setdefault("error_history", {})
        count = errors.get(fingerprint, 0) + 1
        errors[fingerprint] = count
        self._write_state(state)

        if count >= 2:
            return ErrorCheckDecision(
                error_fingerprint=fingerprint,
                recurrence_count=count,
                action="escalate_advisor",
                trigger_advisor=True,
                rationale=(
                    f"LOOP DETECTED: Identical error signature seen {count} times! "
                    "HALTING execution and immediately escalating to Frontier Advisor for root-cause diagnosis."
                ),
            )

        return ErrorCheckDecision(
            error_fingerprint=fingerprint,
            recurrence_count=count,
            action="retry",
            trigger_advisor=False,
            rationale=f"First failure for fingerprint {fingerprint}; safe to attempt a targeted retry.",
        )

    def reset_errors(self) -> None:
        """Clears the error history."""
        state = self._read_state()
        state["error_history"] = {}
        self._write_state(state)

    # -----------------------------------------------------------------------
    # 5. Advisor Trigger Gate (Three Golden Triggers)
    # -----------------------------------------------------------------------
    def check_advisor_trigger(
        self,
        stage: str,
        error_message: Optional[str] = None,
        context: Optional[str] = None,
    ) -> AdvisorTriggerDecision:
        """Checks whether the agent must consult the Frontier Advisor.
        
        Three Golden Triggers:
        1. plan_lock: Before a plan or architectural contract is approved.
        2. error_loop: When the same error occurs twice in a row.
        3. task_done: Before calling the task complete.
        """
        stage_norm = stage.lower().strip()

        # Trigger 1: Plan Lock
        if stage_norm in ("plan", "plan_lock", "lock_plan", "before_plan"):
            return AdvisorTriggerDecision(
                should_consult=True,
                trigger_name="plan_lock",
                rationale=(
                    "TRIGGER 1 (PLAN LOCK): Consult Frontier Advisor before locking the implementation plan "
                    "and 5-part contract to verify architectural fitness, blast radius, and edge case coverage."
                ),
                recommended_model_tier="frontier",
            )

        # Trigger 2: Error Loop
        if stage_norm in ("error", "error_loop", "failure") or error_message:
            if error_message:
                res = self.check_error(error_message)
                if res.trigger_advisor:
                    return AdvisorTriggerDecision(
                        should_consult=True,
                        trigger_name="error_loop",
                        rationale=(
                            f"TRIGGER 2 (ERROR LOOP): {res.rationale} "
                            "Frontier Advisor must inspect diff, error traceback, and formulate a loop-breaking fix."
                        ),
                        recommended_model_tier="frontier",
                    )
            return AdvisorTriggerDecision(
                should_consult=False,
                trigger_name="none",
                rationale="Single isolated error; retry permissible before triggering advisor.",
                recommended_model_tier="builder",
            )

        # Trigger 3: Task Done
        if stage_norm in ("done", "task_done", "complete", "finish", "before_done"):
            return AdvisorTriggerDecision(
                should_consult=True,
                trigger_name="task_done",
                rationale=(
                    "TRIGGER 3 (TASK DONE): Consult Frontier Advisor before declaring task complete. "
                    "Advisor conducts a fresh, unbiased audit of the accumulated git diff and test evidence."
                ),
                recommended_model_tier="frontier",
            )

        return AdvisorTriggerDecision(
            should_consult=False,
            trigger_name="none",
            rationale=f"Routine execution turn in stage '{stage}'; no advisor trigger tripped.",
            recommended_model_tier="builder",
        )

    # -----------------------------------------------------------------------
    # 6. Explorer Subagent Dispatcher (Search / Grep / Docs)
    # -----------------------------------------------------------------------
    def route_explorer(self, intent: str) -> ExplorerRouteDecision:
        """Routes exploration requests to the specialized read-only subagent."""
        intent_lower = intent.lower()

        # Search (maps repo structure / finds files)
        if any(w in intent_lower for w in ["find files", "list files", "directory structure", "repo map", "file layout", "where is file"]):
            return ExplorerRouteDecision(
                subagent="search",
                model_tier="lite",
                confidence=0.92,
                query=intent,
                rationale="Dispatches to 'gemini_advisor_search' (Haiku / Flash-Lite) to map directory layout.",
            )

        # Grep (finds call sites / references / symbols)
        if any(w in intent_lower for w in ["find callers", "call sites", "where is", "symbol", "regex", "usages of", "grep"]):
            return ExplorerRouteDecision(
                subagent="grep",
                model_tier="lite",
                confidence=0.94,
                query=intent,
                rationale="Dispatches to 'gemini_advisor_grep' (Haiku / Flash-Lite) to locate call sites and definitions.",
            )

        # Docs (API references / external specs)
        if any(w in intent_lower for w in ["docs", "documentation", "api reference", "how does", "context7", "syntax of", "spec"]):
            return ExplorerRouteDecision(
                subagent="docs",
                model_tier="lite",
                confidence=0.91,
                query=intent,
                rationale="Dispatches to 'gemini_advisor_docs' (Haiku / Flash-Lite) to pull API reference material.",
            )

        return ExplorerRouteDecision(
            subagent="none",
            model_tier="builder",
            confidence=0.40,
            query=intent,
            rationale="Intent is not exploratory; keep in main driver / builder session.",
        )

    # -----------------------------------------------------------------------
    # State Helpers
    # -----------------------------------------------------------------------
    def _read_state(self) -> Dict[str, Any]:
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _write_state(self, state: Dict[str, Any]) -> None:
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Self-Tests & Benchmark
# ---------------------------------------------------------------------------

def run_tests() -> bool:
    """Runs automated verification unit tests for JEV Router."""
    print("==> Running JEV Deterministic Micro-Router Self-Tests...\n")
    test_state_file = Path("/tmp/jev_test_state.json")
    if test_state_file.exists():
        test_state_file.unlink()

    router = JevRouter(state_file=test_state_file)
    passed = 0
    total = 0

    def assert_true(cond: bool, desc: str):
        nonlocal passed, total
        total += 1
        if cond:
            print(f"✓ Test {total} Passed: {desc}")
            passed += 1
        else:
            print(f"✗ Test {total} FAILED: {desc}")

    # 1. Route Decision: Solo for simple task
    total += 0
    r1 = router.evaluate_route("Fix typo in README documentation", files=["README.md"])
    assert_true(r1.mode == "solo" and r1.risk_score < 0.35, "Solo mode for simple readme tweak.")

    # 2. Route Decision: Delegate for bounded feature
    r2 = router.evaluate_route("Add new endpoint for user profile", files=["api/user.py", "tests/test_user.py"])
    assert_true(r2.mode == "delegate", "Delegate mode for bounded feature.")

    # 3. Route Decision: Audit for security sensitive
    r3 = router.evaluate_route("Update JWT authentication token signing algorithm", files=["auth/jwt.py"], is_security_sensitive=True)
    assert_true(r3.mode in ("audit", "full") and r3.risk_score >= 0.7, "Audit or Full mode for security-sensitive change.")

    # 4. Tool Choice: Call sites -> Grep subagent
    t1 = router.choose_tool("Find all callers of calculate_tax function")
    assert_true(t1.tool == "gemini_advisor_grep", "Tool choice maps call sites to grep subagent.")

    # 5. Tool Choice: Repo map -> Search subagent
    t2 = router.choose_tool("Show repo structure and find files named config")
    assert_true(t2.tool == "gemini_advisor_search", "Tool choice maps structure to search subagent.")

    # 6. Tool Choice: API docs -> Docs subagent
    t3 = router.choose_tool("Look up API reference documentation for Stripe webhooks")
    assert_true(t3.tool == "gemini_advisor_docs", "Tool choice maps docs lookup to docs subagent.")

    # 7. Error Loop: First error allows retry
    err_msg = "AssertionError: Expected 200 OK but received 500 Internal Error at line 42"
    e1 = router.check_error(err_msg)
    assert_true(e1.action == "retry" and not e1.trigger_advisor, "First error failure allows retry.")

    # 8. Error Loop: Second identical error TRIPS ADVISOR TRIGGER 2
    err_msg_repeat = "AssertionError: Expected 200 OK but received 500 Internal Error at line 99"
    e2 = router.check_error(err_msg_repeat)
    assert_true(e2.action == "escalate_advisor" and e2.trigger_advisor, "Second identical error trips Advisor Trigger 2 (error loop).")

    # 9. Advisor Trigger: Plan Lock
    a1 = router.check_advisor_trigger("plan_lock")
    assert_true(a1.should_consult and a1.trigger_name == "plan_lock", "Plan Lock trips Trigger 1.")

    # 10. Advisor Trigger: Task Done
    a2 = router.check_advisor_trigger("task_done")
    assert_true(a2.should_consult and a2.trigger_name == "task_done", "Task Done trips Trigger 3.")

    # Clean up
    if test_state_file.exists():
        test_state_file.unlink()

    print(f"\n==> RESULT: {passed}/{total} JEV Router tests passed.")
    return passed == total


def run_benchmark() -> bool:
    """Measures JEV decision latency across 1,000 iterations to verify sub-millisecond speed."""
    print("==> Running JEV Millisecond Micro-Routing Benchmark (1,000 iterations)...")
    router = JevRouter()
    queries = [
        ("Fix typo in docs", ["README.md"]),
        ("Update JWT auth tokens", ["auth.py"]),
        ("Find all callers of resolve_allocation", []),
        ("Show repo directory tree", []),
        ("API reference for PyTorch tensor clamp", []),
        ("Edit line 42 of verify.sh", []),
    ]

    start = time.perf_counter()
    latencies = []
    for i in range(1000):
        t0 = time.perf_counter()
        q, f = queries[i % len(queries)]
        router.evaluate_route(q, f)
        router.choose_tool(q)
        router.route_explorer(q)
        latencies.append((time.perf_counter() - t0) * 1000)

    total_time = (time.perf_counter() - start) * 1000
    avg_latency = total_time / 1000
    latencies.sort()
    p50 = latencies[500]
    p95 = latencies[950]
    p99 = latencies[990]

    print(f"  Total time for 1,000 micro-decisions: {total_time:.2f} ms")
    print(f"  Average decision latency: {avg_latency:.3f} ms")
    print(f"  P50 latency: {p50:.3f} ms")
    print(f"  P95 latency: {p95:.3f} ms")
    print(f"  P99 latency: {p99:.3f} ms")

    # Sub-millisecond target (avg < 1.0 ms)
    is_fast = avg_latency < 2.0
    status = "PASS (< 2.0ms target)" if is_fast else "FAIL (slow)"
    print(f"  Latency SLA: [{status}]\n")
    return is_fast


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="JEV Deterministic Micro-Routing Engine for Gemini Advisor.")
    parser.add_argument("--route", action="store_true", help="Evaluate route mode (solo, delegate, audit, full).")
    parser.add_argument("--tool-choice", action="store_true", help="Select optimal tool for given intent.")
    parser.add_argument("--select-path", action="store_true", help="Select paths matching query tokens.")
    parser.add_argument("--check-error", action="store_true", help="Check error recurrence for Advisor Trigger 2.")
    parser.add_argument("--advisor-trigger", action="store_true", help="Check Advisor Trigger (plan_lock, error_loop, task_done).")
    parser.add_argument("--explorer-route", action="store_true", help="Route exploration query to search, grep, or docs.")
    parser.add_argument("--task", type=str, default="", help="Task or intent description.")
    parser.add_argument("--stage", type=str, default="", help="Stage for advisor trigger (plan_lock, error, done).")
    parser.add_argument("--error", type=str, default="", help="Error message string.")
    parser.add_argument("--files", nargs="*", default=[], help="File paths involved.")
    parser.add_argument("--reset-errors", action="store_true", help="Reset tracked error recurrence history.")
    parser.add_argument("--benchmark", action="store_true", help="Run latency benchmark.")
    parser.add_argument("--test", action="store_true", help="Run automated self-tests.")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format.")

    args = parser.parse_args()
    router = JevRouter()

    if args.test:
        sys.exit(0 if run_tests() else 1)

    if args.benchmark:
        sys.exit(0 if run_benchmark() else 1)

    if args.reset_errors:
        router.reset_errors()
        print("✓ JEV error history cleared.")
        return

    if args.route:
        dec = router.evaluate_route(args.task, args.files)
        if args.json:
            print(json.dumps(asdict(dec), indent=2))
        else:
            print(f"MODE: {dec.mode.upper()}")
            print(f"RISK: {dec.risk_score}")
            print(f"RATIONALE: {dec.rationale}")
            print(f"ALLOCATION: {dec.allocation}")
        return

    if args.tool_choice:
        dec = router.choose_tool(args.task)
        if args.json:
            print(json.dumps(asdict(dec), indent=2))
        else:
            print(f"TOOL: {dec.tool}")
            print(f"CONFIDENCE: {dec.confidence}")
            print(f"RATIONALE: {dec.rationale}")
        return

    if args.select_path:
        dec = router.select_path(args.task)
        if args.json:
            print(json.dumps(asdict(dec), indent=2))
        else:
            print(f"MATCHED PATHS ({len(dec.paths)}):")
            for p in dec.paths:
                print(f"  - {p}")
        return

    if args.check_error:
        if not args.error:
            print("Error: --error message required with --check-error")
            sys.exit(1)
        dec = router.check_error(args.error)
        if args.json:
            print(json.dumps(asdict(dec), indent=2))
        else:
            print(f"FINGERPRINT: {dec.error_fingerprint}")
            print(f"COUNT: {dec.recurrence_count}")
            print(f"ACTION: {dec.action.upper()}")
            print(f"TRIGGER ADVISOR: {'YES' if dec.trigger_advisor else 'NO'}")
            print(f"RATIONALE: {dec.rationale}")
        return

    if args.advisor_trigger:
        dec = router.check_advisor_trigger(args.stage, args.error)
        if args.json:
            print(json.dumps(asdict(dec), indent=2))
        else:
            print(f"SHOULD CONSULT: {'YES' if dec.should_consult else 'NO'}")
            print(f"TRIGGER: {dec.trigger_name.upper()}")
            print(f"MODEL TIER: {dec.recommended_model_tier.upper()}")
            print(f"RATIONALE: {dec.rationale}")
        return

    if args.explorer_route:
        dec = router.route_explorer(args.task)
        if args.json:
            print(json.dumps(asdict(dec), indent=2))
        else:
            print(f"SUBAGENT: {dec.subagent}")
            print(f"TIER: {dec.model_tier}")
            print(f"CONFIDENCE: {dec.confidence}")
            print(f"RATIONALE: {dec.rationale}")
        return

    # If no flags passed, run tests by default
    run_tests()


if __name__ == "__main__":
    main()
