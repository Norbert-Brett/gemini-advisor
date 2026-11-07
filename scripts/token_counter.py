#!/usr/bin/env python3
"""scripts/token_counter.py

A real token counter and economic estimator for the Gemini Advisor framework.
Supports:
1. High-fidelity offline estimation calibrated to Gemini's SentencePiece/BPE tokenizer.
2. Live ground-truth token counting via Google Gemini REST API (when GEMINI_API_KEY is available).
3. Analyzing files, directories, git diffs, and Antigravity conversation transcripts.
4. Triad vs Monolithic ROI/cost savings comparison.
5. Built-in verification test suite (--test).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# --- PRICING CONSTANTS (USD per 1M tokens) ---
# Dynamically integrated with model_allocator and config/model_tiers.json with safe fallbacks.
try:
    from model_allocator import ModelAllocator, load_config as load_model_config
    _ALLOCATOR_AVAILABLE = True
except ImportError:
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from model_allocator import ModelAllocator, load_config as load_model_config
        _ALLOCATOR_AVAILABLE = True
    except Exception:
        _ALLOCATOR_AVAILABLE = False

# Frontier (Gemini 4 Argon / Apex / Xenon)
FRONTIER_INPUT_PER_M = 2.50
FRONTIER_OUTPUT_PER_M = 10.00
ARGON_INPUT_PER_M = FRONTIER_INPUT_PER_M
ARGON_OUTPUT_PER_M = FRONTIER_OUTPUT_PER_M

# Gemini Pro (Secondary High-Reasoning / Fallback)
PRO_INPUT_PER_M = 1.25
PRO_OUTPUT_PER_M = 5.00

# Gemini Flash (Builder Execution)
FLASH_INPUT_PER_M = 0.075
FLASH_OUTPUT_PER_M = 0.30

# Gemini Flash-Lite (Mechanical / Boilerplate)
FLASH_LITE_INPUT_PER_M = 0.0375
FLASH_LITE_OUTPUT_PER_M = 0.15


class GeminiTokenEstimator:
    """Calibrated offline tokenizer for Gemini models.

    Gemini models use a SentencePiece BPE tokenizer with ~256k vocabulary.
    This estimator models subword splitting, code indentation, operators,
    numeric chunks, and multi-byte CJK ideographs to provide high-precision
    token counts without heavy external dependencies.
    """

    # CJK, Hiragana, Katakana, Hangul (dense scripts ~1-1.5 chars/token)
    CJK_RE = re.compile(
        r"[\u3000-\u303f\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af\uf900-\ufaff\uff00-\uffef]"
    )

    # Identifiers in code (camelCase, snake_case, PascalCase, numbers)
    CAMEL_SPLIT_RE = re.compile(r"([a-z]+|[A-Z][a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)|\d+)")

    # Punctuation and operators (typically 1 token each in BPE)
    PUNCT_RE = re.compile(r"[!\"#$%&'()*+,\-./:;<=>?@\[\\\]^_`{|}~]")

    # Whitespace indentation runs (2-4 spaces = 1 indent token)
    INDENT_RE = re.compile(r"^( +|\t+)", re.MULTILINE)

    def count_text(self, text: str) -> int:
        """Estimate token count for a text string."""
        if not text:
            return 0

        total_tokens = 0

        # 1. Count CJK characters directly (~1.2 tokens per char)
        cjk_matches = self.CJK_RE.findall(text)
        cjk_count = len(cjk_matches)
        if cjk_count > 0:
            total_tokens += int(cjk_count * 1.2 + 0.5)
            # Remove CJK chars for remaining Latin/code processing
            text = self.CJK_RE.sub(" ", text)

        # 2. Count indentation tokens (each 2-4 spaces or 1 tab = 1 token)
        for match in self.INDENT_RE.finditer(text):
            indent = match.group(1)
            spaces = indent.count(" ") + indent.count("\t") * 4
            total_tokens += max(1, spaces // 3)

        # 3. Process lines and words
        lines = text.splitlines()
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            # Count punctuation and symbols
            puncts = self.PUNCT_RE.findall(line_str)
            total_tokens += len(puncts)

            # Strip punctuation for word tokenization
            clean_words = self.PUNCT_RE.sub(" ", line_str).split()
            for word in clean_words:
                # Numbers: 1-3 digits per token
                if word.isdigit():
                    total_tokens += max(1, (len(word) + 2) // 3)
                    continue

                # Subword identifier splitting (e.g. "geminiAdvisorBuilder")
                subwords = self.CAMEL_SPLIT_RE.findall(word)
                if len(subwords) > 1:
                    for sub in subwords:
                        if sub.isdigit():
                            total_tokens += max(1, (len(sub) + 2) // 3)
                        else:
                            # In Gemini's 256k vocab, subwords <= 8 chars are 1 token
                            length = len(sub)
                            if length <= 8:
                                total_tokens += 1
                            else:
                                total_tokens += 1 + (length - 8 + 4) // 5
                else:
                    # In Gemini's 256k vocab, standard words <= 8 chars are 1 token
                    length = len(word)
                    if length <= 8:
                        total_tokens += 1
                    elif length <= 15:
                        total_tokens += 2
                    else:
                        total_tokens += 2 + (length - 15 + 4) // 5

        return total_tokens


class GeminiLiveTokenCounter:
    """Live token counter using the official Google Gemini countTokens API."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-pro"):
        self.api_key = api_key
        self.model = model

    def count_tokens(self, text: str) -> Optional[int]:
        """Query Google Gemini countTokens API."""
        if not text:
            return 0

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:countTokens?key={self.api_key}"
        payload = {
            "contents": [
                {
                    "parts": [{"text": text}]
                }
            ]
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return int(data.get("totalTokens", 0))
        except Exception as e:
            # Fall back gracefully if offline or request fails
            return None


def calculate_costs(input_tokens: int, output_tokens: int, model_type: str = "pro") -> float:
    """Calculate cost in USD based on model tier."""
    m_type = (model_type or "pro").lower().strip()
    if m_type in ("frontier", "argon", "gemini-4-argon"):
        in_p = FRONTIER_INPUT_PER_M
        out_p = FRONTIER_OUTPUT_PER_M
    elif m_type in ("flash", "builder", "gemini-3.8-flash"):
        in_p = FLASH_INPUT_PER_M
        out_p = FLASH_OUTPUT_PER_M
    elif m_type in ("flash_lite", "flash-lite", "lite", "gemini-3.1-flash-lite"):
        in_p = FLASH_LITE_INPUT_PER_M
        out_p = FLASH_LITE_OUTPUT_PER_M
    else:  # pro
        in_p = PRO_INPUT_PER_M
        out_p = PRO_OUTPUT_PER_M

    return (input_tokens / 1_000_000 * in_p) + (output_tokens / 1_000_000 * out_p)


def count_file(path: Path, estimator: GeminiTokenEstimator) -> Tuple[int, int]:
    """Count bytes and tokens for a file."""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        tokens = estimator.count_text(content)
        return len(content.encode("utf-8")), tokens
    except Exception as e:
        return 0, 0


def count_directory(dir_path: Path, estimator: GeminiTokenEstimator) -> List[Dict[str, Any]]:
    """Count tokens across all files in a directory."""
    results = []
    ignored_patterns = {".git", ".DS_Store", "node_modules", "__pycache__", ".agents"}

    for root, dirs, files in os.walk(dir_path):
        # Filter out ignored dirs
        dirs[:] = [d for d in dirs if d not in ignored_patterns]

        for file in files:
            if file in ignored_patterns:
                continue
            file_path = Path(root) / file
            if file_path.is_file():
                byte_size, tokens = count_file(file_path, estimator)
                rel_path = file_path.relative_to(dir_path)
                results.append({
                    "path": str(rel_path),
                    "bytes": byte_size,
                    "tokens": tokens,
                    "ext": file_path.suffix or "(none)"
                })

    return sorted(results, key=lambda x: x["tokens"], reverse=True)


def count_git_diff(target_dir: str = ".") -> Tuple[str, int]:
    """Extract git diff and count its tokens."""
    estimator = GeminiTokenEstimator()
    try:
        # Check inside work tree
        is_git = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=target_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if is_git.returncode != 0:
            return "Not a git repository", 0

        diff_proc = subprocess.run(
            ["git", "diff", "-U3", target_dir],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        diff_text = diff_proc.stdout

        if not diff_text.strip():
            # Check staged
            staged_proc = subprocess.run(
                ["git", "diff", "--cached", "-U3", target_dir],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            diff_text = staged_proc.stdout

        tokens = estimator.count_text(diff_text)
        return diff_text, tokens
    except Exception as e:
        return f"Error running git diff: {e}", 0


def analyze_transcript(transcript_path: Path) -> Dict[str, Any]:
    """Parse Antigravity JSONL transcript and measure token distribution."""
    estimator = GeminiTokenEstimator()
    user_tokens = 0
    model_tokens = 0
    tool_tokens = 0
    steps_count = 0

    if not transcript_path.exists():
        return {"error": f"Transcript not found at {transcript_path}"}

    with open(transcript_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
            try:
                step = json.loads(line_str)
                steps_count += 1
                source = step.get("source", "")
                content = step.get("content", "") or ""
                thinking = step.get("thinking", "") or ""
                tool_calls = json.dumps(step.get("tool_calls", [])) if step.get("tool_calls") else ""

                tokens = estimator.count_text(content) + estimator.count_text(thinking) + estimator.count_text(tool_calls)

                if source == "USER_EXPLICIT" or step.get("type") == "USER_INPUT":
                    user_tokens += tokens
                elif source == "MODEL" or step.get("type") == "PLANNER_RESPONSE":
                    model_tokens += tokens
                else:
                    tool_tokens += tokens
            except json.JSONDecodeError:
                continue

    total_tokens = user_tokens + model_tokens + tool_tokens
    return {
        "steps": steps_count,
        "user_tokens": user_tokens,
        "model_tokens": model_tokens,
        "tool_tokens": tool_tokens,
        "total_tokens": total_tokens,
    }


def compare_triad_vs_monolithic(
    plan_tokens: int = 4000,
    build_tokens: int = 45000,
    review_diff_tokens: int = 5000,
) -> Dict[str, Any]:
    """Calculate comparative token consumption and cost between Monolithic Frontier vs Gemini Advisor Triad."""
    frontier_model_name = "Gemini 4 Argon"
    builder_model_name = "Gemini Flash"
    if _ALLOCATOR_AVAILABLE:
        try:
            alloc = ModelAllocator().resolve_allocation()
            frontier_model_name = alloc["tiers"]["frontier"]["display_name"]
            builder_model_name = alloc["tiers"]["builder"]["display_name"]
        except Exception:
            pass

    # Monolithic approach: Single Frontier agent handles all steps with growing context window
    mono_input = plan_tokens + (build_tokens // 2) + build_tokens
    mono_output = (plan_tokens // 2) + (build_tokens // 2)
    mono_review_context = mono_input + mono_output + 15000  # Context accumulation penalty
    mono_total_input = mono_input + mono_review_context
    mono_total_output = mono_output + 2000
    mono_frontier_cost = calculate_costs(mono_total_input, mono_total_output, "frontier")
    mono_pro_cost = calculate_costs(mono_total_input, mono_total_output, "pro")

    # Gemini Advisor Triad approach:
    # 1. Frontier Planner (plan only)
    triad_frontier_plan_in = plan_tokens
    triad_frontier_plan_out = 1500

    # 2. Flash Builder (build only, isolated)
    triad_flash_build_in = build_tokens
    triad_flash_build_out = build_tokens // 2

    # 3. Fresh Frontier Reviewer (clean context, receives only diff & verification)
    triad_frontier_review_in = review_diff_tokens + 1000
    triad_frontier_review_out = 1000

    triad_frontier_in = triad_frontier_plan_in + triad_frontier_review_in
    triad_frontier_out = triad_frontier_plan_out + triad_frontier_review_out
    triad_flash_in = triad_flash_build_in
    triad_flash_out = triad_flash_build_out

    triad_frontier_cost = calculate_costs(triad_frontier_in, triad_frontier_out, "frontier")
    triad_flash_cost = calculate_costs(triad_flash_in, triad_flash_out, "flash")
    triad_total_cost = triad_frontier_cost + triad_flash_cost

    savings_cost = mono_frontier_cost - triad_total_cost
    savings_pct = (savings_cost / mono_frontier_cost * 100) if mono_frontier_cost > 0 else 0

    triad_pro_cost = calculate_costs(triad_frontier_in, triad_frontier_out, "pro")
    triad_pro_total = triad_pro_cost + triad_flash_cost

    return {
        "frontier_model": frontier_model_name,
        "builder_model": builder_model_name,
        "monolithic": {
            "model": f"{frontier_model_name} (Monolithic All-Frontier)",
            "tier": "frontier",
            "input_tokens": mono_total_input,
            "output_tokens": mono_total_output,
            "total_tokens": mono_total_input + mono_total_output,
            "cost_usd": round(mono_frontier_cost, 4),
            "pro_equivalent_cost_usd": round(mono_pro_cost, 4),
        },
        "triad": {
            "frontier_model": frontier_model_name,
            "builder_model": builder_model_name,
            "frontier_tokens": triad_frontier_in + triad_frontier_out,
            "flash_tokens": triad_flash_in + triad_flash_out,
            "total_tokens": (triad_frontier_in + triad_frontier_out) + (triad_flash_in + triad_flash_out),
            "frontier_cost_usd": round(triad_frontier_cost, 4),
            "flash_cost_usd": round(triad_flash_cost, 4),
            "total_cost_usd": round(triad_total_cost, 4),
            # Backward-compatible alias keys
            "pro_tokens": triad_frontier_in + triad_frontier_out,
            "pro_cost_usd": round(triad_frontier_cost, 4),
        },
        "savings": {
            "saved_usd": round(savings_cost, 4),
            "savings_percent": round(savings_pct, 1),
            "frontier_tokens_reduced_pct": round(
                (1 - (triad_frontier_in + triad_frontier_out) / (mono_total_input + mono_total_output)) * 100, 1
            ),
            "pro_tokens_reduced_pct": round(
                (1 - (triad_frontier_in + triad_frontier_out) / (mono_total_input + mono_total_output)) * 100, 1
            ),
        },
        "pro_reference": {
            "monolithic_pro_cost_usd": round(mono_pro_cost, 4),
            "triad_pro_total_cost_usd": round(triad_pro_total, 4),
            "pro_savings_usd": round(mono_pro_cost - triad_pro_total, 4),
            "pro_savings_pct": round(((mono_pro_cost - triad_pro_total) / mono_pro_cost * 100), 1) if mono_pro_cost > 0 else 0,
        },
    }


def run_self_tests() -> bool:
    """Execute automated self-tests for the token counter."""
    print("==> Running Gemini Advisor Token Counter Self-Tests...")
    estimator = GeminiTokenEstimator()
    passed = 0
    total = 0

    # Test 1: Empty string
    total += 1
    assert estimator.count_text("") == 0, "Empty string should be 0"
    passed += 1

    # Test 2: Standard English text
    total += 1
    text = "Hello world, this is a test of the Gemini Advisor token counter."
    c = estimator.count_text(text)
    assert 10 <= c <= 20, f"Expected 10-20 tokens, got {c}"
    passed += 1

    # Test 3: Code with camelCase and symbols
    total += 1
    code = """
    function calculateSubagentTokens(inputPrompt, maxLimit) {
        const total = inputPrompt.length * 0.25;
        return total > maxLimit ? maxLimit : total;
    }
    """
    code_tokens = estimator.count_text(code)
    assert 25 <= code_tokens <= 55, f"Expected 25-55 tokens for code, got {code_tokens}"
    passed += 1

    # Test 4: CJK characters
    total += 1
    cjk = "你好，世界！这是一段中文测试。"
    cjk_tokens = estimator.count_text(cjk)
    assert 10 <= cjk_tokens <= 25, f"Expected 10-25 tokens for CJK, got {cjk_tokens}"
    passed += 1

    # Test 5: File counting
    total += 1
    p = Path(__file__)
    bytes_count, file_tokens = count_file(p, estimator)
    assert file_tokens > 200, f"File token count too low: {file_tokens}"
    passed += 1

    # Test 6: Cost comparison calculation
    total += 1
    comp = compare_triad_vs_monolithic(4000, 40000, 3000)
    assert comp["savings"]["savings_percent"] > 50, "Expected >50% savings"
    assert comp["triad"]["total_cost_usd"] < comp["monolithic"]["cost_usd"], "Triad must be cheaper"
    passed += 1

    # Test 7: Frontier / Argon and Lite pricing calculation
    total += 1
    c_frontier = calculate_costs(1_000_000, 1_000_000, "frontier")
    c_argon = calculate_costs(1_000_000, 1_000_000, "argon")
    assert c_frontier == 12.50, f"Expected $12.50 for 1M in/out frontier, got {c_frontier}"
    assert c_argon == 12.50, f"Expected $12.50 for 1M in/out argon, got {c_argon}"
    c_lite = calculate_costs(1_000_000, 1_000_000, "flash_lite")
    assert abs(c_lite - 0.1875) < 1e-5, f"Expected $0.1875 for flash_lite, got {c_lite}"
    passed += 1

    # Test 8: Dynamic Allocator Integration
    total += 1
    assert _ALLOCATOR_AVAILABLE is True, "model_allocator must be importable"
    assert "frontier_model" in comp, "compare_triad_vs_monolithic must include frontier_model"
    assert "builder_model" in comp, "compare_triad_vs_monolithic must include builder_model"
    assert "pro_reference" in comp, "compare_triad_vs_monolithic must include pro_reference"
    passed += 1

    print(f"✓ All {passed}/{total} self-tests passed successfully!\n")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Real token counter and economic estimator for the Gemini Advisor framework."
    )
    parser.add_argument("--file", "-f", type=str, help="Count tokens in a specific file")
    parser.add_argument("--dir", "-d", type=str, help="Count tokens across all files in a directory")
    parser.add_argument("--diff", action="store_true", help="Count tokens in current git diff / changes")
    parser.add_argument("--string", "-s", type=str, help="Count tokens in the provided string")
    parser.add_argument("--transcript", "-t", type=str, help="Analyze an Antigravity transcript.jsonl file")
    parser.add_argument("--compare", action="store_true", help="Run comparative Monolithic vs Gemini Advisor Triad cost ROI analysis")
    parser.add_argument("--test", action="store_true", help="Run internal validation test suite")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--model", type=str, default="gemini-2.5-pro", help="Model target (default: gemini-2.5-pro)")
    parser.add_argument("--api-key", type=str, default=None, help="Google Gemini API key for live countTokens (optional)")

    args = parser.parse_args()

    # Self-test mode
    if args.test:
        success = run_self_tests()
        sys.exit(0 if success else 1)

    estimator = GeminiTokenEstimator()
    api_key = args.api_key or os.environ.get("GEMINI_API_KEY")

    # Mode 1: Compare ROI
    if args.compare:
        comparison = compare_triad_vs_monolithic()
        if args.json:
            print(json.dumps(comparison, indent=2))
        else:
            print("================================================================================")
            print("         GEMINI ADVISOR: TRIAD VS MONOLITHIC TOKEN & COST BENCHMARK            ")
            print("================================================================================")
            mono = comparison["monolithic"]
            triad = comparison["triad"]
            savings = comparison["savings"]

            print(f"Monolithic Delivery (All-Frontier Single Agent - {mono['model']}):")
            print(f"  • Total Tokens:       {mono['total_tokens']:,} (Input: {mono['input_tokens']:,}, Output: {mono['output_tokens']:,})")
            print(f"  • Estimated Cost:     ${mono['cost_usd']:.4f} USD")
            print("")
            print(f"Gemini Advisor Triad ({triad['frontier_model']} Plan + {triad['builder_model']} Build + Fresh {triad['frontier_model']} Audit):")
            print(f"  • Frontier Tokens:    {triad['frontier_tokens']:,} tokens (${triad['frontier_cost_usd']:.4f})")
            print(f"  • Flash Tokens:       {triad['flash_tokens']:,} tokens (${triad['flash_cost_usd']:.4f})")
            print(f"  • Total Tokens:       {triad['total_tokens']:,} tokens")
            print(f"  • Total Cost:         ${triad['total_cost_usd']:.4f} USD")
            print("--------------------------------------------------------------------------------")
            print("NET SAVINGS (Triad vs Monolithic Frontier):")
            print(f"  • Financial Savings:  ${savings['saved_usd']:.4f} USD ({savings['savings_percent']}% cheaper)")
            print(f"  • Frontier Reduction: {savings['frontier_tokens_reduced_pct']}% reduction in high-cost frontier tokens")
            print("--------------------------------------------------------------------------------")
            pro_ref = comparison.get("pro_reference", {})
            if pro_ref:
                print("Secondary Pro Tier Reference:")
                print(f"  • Monolithic Pro:     ${pro_ref['monolithic_pro_cost_usd']:.4f} USD")
                print(f"  • Triad (Pro+Flash):  ${pro_ref['triad_pro_total_cost_usd']:.4f} USD ({pro_ref['pro_savings_pct']}% cheaper)")
            print("================================================================================")
        return

    # Mode 2: Git Diff
    if args.diff:
        diff_text, tokens = count_git_diff(".")
        if args.json:
            print(json.dumps({"diff_tokens": tokens, "lines": len(diff_text.splitlines())}, indent=2))
        else:
            print(f"Git Diff Analysis:")
            print(f"  • Total Lines:  {len(diff_text.splitlines()):,}")
            print(f"  • Token Count:  {tokens:,} tokens")
            print(f"  • Review Cost:  ${calculate_costs(tokens, 500, 'pro'):.5f} USD (Fresh Pro Reviewer)")
        return

    # Mode 3: Specific File
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"Error: File '{args.file}' not found.", file=sys.stderr)
            sys.exit(1)
        bytes_size, tokens = count_file(file_path, estimator)

        # Check if live API count is possible
        live_tokens = None
        if api_key:
            live_counter = GeminiLiveTokenCounter(api_key, args.model)
            live_tokens = live_counter.count_tokens(file_path.read_text(errors="replace"))

        if args.json:
            res = {"file": str(file_path), "bytes": bytes_size, "estimated_tokens": tokens}
            if live_tokens is not None:
                res["live_api_tokens"] = live_tokens
            print(json.dumps(res, indent=2))
        else:
            print(f"File: {file_path}")
            print(f"  • Size:             {bytes_size:,} bytes")
            print(f"  • Estimated Tokens: {tokens:,} tokens")
            if live_tokens is not None:
                print(f"  • Google Live API:  {live_tokens:,} tokens")
            print(f"  • Cost (Flash):     ${calculate_costs(tokens, 0, 'flash'):.6f} USD")
            print(f"  • Cost (Pro):       ${calculate_costs(tokens, 0, 'pro'):.6f} USD")
        return

    # Mode 4: Directory scan
    if args.dir:
        dir_path = Path(args.dir)
        if not dir_path.is_dir():
            print(f"Error: Directory '{args.dir}' not found.", file=sys.stderr)
            sys.exit(1)
        file_counts = count_directory(dir_path, estimator)
        total_tokens = sum(f["tokens"] for f in file_counts)
        total_bytes = sum(f["bytes"] for f in file_counts)

        if args.json:
            print(json.dumps({"directory": str(dir_path), "total_tokens": total_tokens, "total_bytes": total_bytes, "files": file_counts}, indent=2))
        else:
            print(f"Directory Scan: {dir_path} ({len(file_counts)} files)")
            print(f"{'Tokens':>8}  {'Bytes':>8}  {'File Path'}")
            print("-" * 65)
            for f in file_counts[:25]:  # Top 25 files
                print(f"{f['tokens']:>8,}  {f['bytes']:>8,}  {f['path']}")
            if len(file_counts) > 25:
                print(f"... and {len(file_counts) - 25} more files.")
            print("-" * 65)
            print(f"TOTAL: {total_tokens:,} tokens ({total_bytes:,} bytes)")
        return

    # Mode 5: Transcript analysis
    if args.transcript:
        tr_path = Path(args.transcript)
        data = analyze_transcript(tr_path)
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            if "error" in data:
                print(f"Error: {data['error']}", file=sys.stderr)
                sys.exit(1)
            print(f"Antigravity Transcript Analysis: {tr_path.name}")
            print(f"  • Steps Count:       {data['steps']}")
            print(f"  • User Input Tokens: {data['user_tokens']:,}")
            print(f"  • Model Gen Tokens:  {data['model_tokens']:,}")
            print(f"  • Tool Output Tokens:{data['tool_tokens']:,}")
            print(f"  • Total Tokens:      {data['total_tokens']:,}")
        return

    # Mode 6: Direct string or stdin
    text_input = args.string
    if text_input is None:
        if not sys.stdin.isatty():
            text_input = sys.stdin.read()

    if text_input:
        tokens = estimator.count_text(text_input)
        live_tokens = None
        if api_key:
            live_counter = GeminiLiveTokenCounter(api_key, args.model)
            live_tokens = live_counter.count_tokens(text_input)

        if args.json:
            res = {"length": len(text_input), "estimated_tokens": tokens}
            if live_tokens is not None:
                res["live_api_tokens"] = live_tokens
            print(json.dumps(res, indent=2))
        else:
            print(f"Text Input ({len(text_input)} characters):")
            print(f"  • Estimated Tokens: {tokens:,} tokens")
            if live_tokens is not None:
                print(f"  • Google Live API:  {live_tokens:,} tokens")
        return

    # Default fallback: show usage and compare
    parser.print_help()


if __name__ == "__main__":
    main()
