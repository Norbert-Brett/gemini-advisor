#!/usr/bin/env python3
"""scripts/model_allocator.py

Dynamic Model Discovery, Capability Scoring & Tier Allocation Engine for Gemini Advisor.

Key capabilities:
1. Dynamic Model Discovery:
   - Environment variables (GEMINI_ADVISOR_FRONTIER_MODEL, GEMINI_MODEL, etc.)
   - Active Antigravity session transcripts (<USER_SETTINGS_CHANGE> Model Selection)
   - Antigravity state (~/.gemini/antigravity/antigravity_state.pbtxt)
   - Google Gemini REST API (when GEMINI_API_KEY or GOOGLE_API_KEY is present)
   - Local plugin cache (~/.gemini/antigravity/plugin_data/gemini-advisor/allocated_models.json)
   - Built-in registry (config/model_tiers.json)
2. Future-Proof Capability Scoring:
   - Algorithmic scoring based on model generation, reasoning tier keywords (argon, xenon, krypton, etc.),
     effort modifiers (High, Medium), and execution categories (flash, lite).
   - Strictly filters out non-text/non-coding models (imagen, veo, embedding, image).
3. Tier Allocation:
   - Allocates the highest-capability Frontier model for Planning / Independent Review.
   - Allocates high-velocity Builder models (Flash / Flash-Lite) for code execution.
   - Resolves subagent parameters ("inherit" for Reviewer when active session is Frontier, preventing
     unwanted downgrades to Pro; "pro" fallback when parent is Flash).
4. CLI Commands:
   - --check: Verifies allocation invariants and displays status table.
   - --allocate: Emits exact SELECTIVE ROUTE allocation line.
   - --discover: Displays all discovered models across discovery sources.
   - --score <name>: Scores and classifies any model string.
   - --test: Runs comprehensive automated self-tests.
   - --json: Formats outputs in structured JSON.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Path resolution
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
CONFIG_PATH = REPO_ROOT / "config" / "model_tiers.json"
CACHE_PATH = Path.home() / ".gemini" / "antigravity" / "plugin_data" / "gemini-advisor" / "allocated_models.json"
ANTIGRAVITY_STATE_PATH = Path.home() / ".gemini" / "antigravity" / "antigravity_state.pbtxt"
TRANSCRIPT_GLOB = str(Path.home() / ".gemini" / "antigravity" / "brain" / "*" / ".system_generated" / "logs" / "transcript.jsonl")

# Fallback defaults if config/model_tiers.json is unavailable
DEFAULT_CONFIG: Dict[str, Any] = {
    "schema_version": "2.0",
    "allocation_policy": "dynamic_capability_tiering",
    "tiers": {
        "frontier": {
            "role": "Architect / Planner & Independent Reviewer",
            "description": "Most advanced high-reasoning model for architectural planning, contract drafting, and zero-bias diff auditing.",
            "default_model": "gemini-4-argon",
            "display_name": "Gemini 4 Argon",
            "subagent_model_when_parent_is_frontier": "inherit",
            "subagent_model_fallback": "pro",
            "pricing_per_1m_usd": {"input": 2.50, "output": 10.00},
        },
        "pro": {
            "role": "High-Reasoning Fallback",
            "description": "Secondary high-reasoning tier when frontier Argon/Apex is unavailable or when escalating from a Flash parent.",
            "default_model": "gemini-3.5-pro",
            "display_name": "Gemini Pro",
            "subagent_model": "pro",
            "pricing_per_1m_usd": {"input": 1.25, "output": 5.00},
        },
        "builder": {
            "role": "Builder / Routine Code Implementer",
            "description": "Fast, economical model for bounded code execution, file modifications, and unit test runs.",
            "default_model": "gemini-3.8-flash",
            "display_name": "Gemini Flash",
            "subagent_model": "flash",
            "pricing_per_1m_usd": {"input": 0.075, "output": 0.30},
        },
        "lite": {
            "role": "Mechanical / Boilerplate Implementer",
            "description": "Ultra-low-cost model for repetitive fixtures, schema conversions, and mechanical boilerplate.",
            "default_model": "gemini-3.1-flash-lite",
            "display_name": "Gemini Flash-Lite",
            "subagent_model": "flash_lite",
            "pricing_per_1m_usd": {"input": 0.0375, "output": 0.15},
        },
    },
    "heuristics": {
        "frontier_keywords": [
            "argon", "xenon", "krypton", "radon", "oganesson", "neon",
            "ultra", "apex", "frontier", "titan", "opus", "deep-think", "thinking", "max"
        ],
        "pro_keywords": ["pro", "advanced"],
        "builder_keywords": ["flash"],
        "lite_keywords": ["flash-lite", "flash_lite", "lite", "8b", "nano", "mini"],
        "excluded_keywords": ["embedding", "imagen", "veo", "aqa", "tts", "audio", "vision-only", "image", "placeholder"],
    },
    "known_models": [
        {"id": "gemini-4-argon", "display_name": "Gemini 4 Argon", "tier": "frontier", "generation": 4.0, "capability_score": 96.0, "subagent_model": "inherit", "pricing_per_1m_usd": {"input": 2.50, "output": 10.00}},
        {"id": "gemini-3.5-pro", "display_name": "Gemini 3.5 Pro", "tier": "pro", "generation": 3.5, "capability_score": 74.2, "subagent_model": "pro", "pricing_per_1m_usd": {"input": 1.25, "output": 5.00}},
        {"id": "gemini-2.5-pro", "display_name": "Gemini 2.5 Pro", "tier": "pro", "generation": 2.5, "capability_score": 73.0, "subagent_model": "pro", "pricing_per_1m_usd": {"input": 1.25, "output": 5.00}},
        {"id": "gemini-3.8-flash", "display_name": "Gemini 3.8 Flash", "tier": "builder", "generation": 3.8, "capability_score": 48.8, "subagent_model": "flash", "pricing_per_1m_usd": {"input": 0.075, "output": 0.30}},
        {"id": "gemini-2.5-flash", "display_name": "Gemini 2.5 Flash", "tier": "builder", "generation": 2.5, "capability_score": 47.5, "subagent_model": "flash", "pricing_per_1m_usd": {"input": 0.075, "output": 0.30}},
        {"id": "gemini-3.1-flash-lite", "display_name": "Gemini 3.1 Flash-Lite", "tier": "lite", "generation": 3.1, "capability_score": 22.48, "subagent_model": "flash_lite", "pricing_per_1m_usd": {"input": 0.0375, "output": 0.15}},
        {"id": "gemini-2.5-flash-lite", "display_name": "Gemini 2.5 Flash-Lite", "tier": "lite", "generation": 2.5, "capability_score": 22.0, "subagent_model": "flash_lite", "pricing_per_1m_usd": {"input": 0.0375, "output": 0.15}},
    ],
}


def load_config() -> Dict[str, Any]:
    """Load configuration from config/model_tiers.json with graceful fallback."""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_CONFIG


def normalize_token_stream(text: str) -> str:
    """Normalize model string into space-separated lowercase tokens."""
    cleaned = re.sub(r"[^a-zA-Z0-9.]+", " ", text.lower())
    return f" {cleaned.strip()} "


def matches_keyword(normalized_stream: str, kw: str) -> bool:
    """Check if keyword matches within normalized token stream, avoiding substring false positives."""
    clean_kw = re.sub(r"[^a-zA-Z0-9.]+", " ", kw.lower()).strip()
    return f" {clean_kw} " in normalized_stream


def extract_generation(name: str) -> float:
    """Extract model generation version number (e.g. 4.0, 3.5, 5.5)."""
    norm = normalize_token_stream(name)
    gen_match = re.search(r"(?:gemini\s+)?(\d+(?:\.\d+)?)", norm)
    if gen_match:
        try:
            val = float(gen_match.group(1))
            if val <= 20.0:
                return val
        except ValueError:
            pass
    return 2.5


def format_display_name(model_name: str, tier: str) -> str:
    """Produce clean human-readable display name."""
    clean = model_name.strip()
    if clean.startswith("models/"):
        clean = clean[len("models/"):]

    # Remove extra parenthetical reasoning markers for display if already clean
    base = re.sub(r"\s*\((?:High|Medium|Low)\)", "", clean, flags=re.IGNORECASE).strip()

    # If it's already well-formatted like "Gemini 4 Argon"
    if base.lower().startswith("gemini ") and len(base.split()) >= 3:
        return base

    # Format kebab-case like "gemini-4-argon" -> "Gemini 4 Argon"
    parts = re.split(r"[-_ ]+", base)
    capitalized = []
    for p in parts:
        if p.lower() == "gemini":
            capitalized.append("Gemini")
        elif re.match(r"^\d+(?:\.\d+)?$", p):
            capitalized.append(p)
        else:
            capitalized.append(p.capitalize())
    formatted = " ".join(capitalized)

    # If it's simply "gemini-3.8-flash", make sure it reflects display name
    return formatted


def score_model(name: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Classify and score any model identifier or display name."""
    cfg = config or load_config()
    heuristics = cfg.get("heuristics", DEFAULT_CONFIG["heuristics"])
    tiers_cfg = cfg.get("tiers", DEFAULT_CONFIG["tiers"])

    raw_name = name.strip()
    norm = normalize_token_stream(raw_name)

    # 1. Exclusion filter: non-text / non-coding models
    excluded_keywords = heuristics.get("excluded_keywords", [])
    for kw in excluded_keywords:
        if matches_keyword(norm, kw) or (kw in ["embedding", "imagen", "veo", "aqa", "tts", "audio"] and kw in raw_name.lower()):
            return {
                "id": raw_name,
                "display_name": raw_name,
                "tier": "excluded",
                "generation": 0.0,
                "capability_score": 0.0,
                "subagent_model": "none",
                "pricing_per_1m_usd": {"input": 0.0, "output": 0.0},
                "excluded": True,
            }

    # 2. Tier Classification
    frontier_kws = heuristics.get("frontier_keywords", [])
    lite_kws = heuristics.get("lite_keywords", [])
    builder_kws = heuristics.get("builder_keywords", [])
    pro_kws = heuristics.get("pro_keywords", [])

    tier = "pro"
    if any(matches_keyword(norm, k) for k in frontier_kws):
        tier = "frontier"
    elif any(matches_keyword(norm, k) for k in lite_kws):
        tier = "lite"
    elif any(matches_keyword(norm, k) for k in builder_kws):
        tier = "builder"
    elif any(matches_keyword(norm, k) for k in pro_kws):
        tier = "pro"
    else:
        # Fallback based on generation: frontier if >= 4.0, else pro
        gen = extract_generation(raw_name)
        tier = "frontier" if gen >= 4.0 else "pro"

    # 3. Generation extraction
    gen = extract_generation(raw_name)

    # 4. Capability scoring formula
    base_scores = {"frontier": 90.0, "pro": 70.0, "builder": 45.0, "lite": 20.0}
    gen_multipliers = {"frontier": 1.5, "pro": 1.2, "builder": 1.0, "lite": 0.8}

    score = base_scores.get(tier, 70.0) + (gen * gen_multipliers.get(tier, 1.0))

    # Effort / Variant modifiers
    if " high " in norm:
        score += 0.5
    elif " medium " in norm:
        score += 0.2
    if " ultra " in norm:
        score += 0.5
    if " max " in norm:
        score += 0.5
    if " thinking " in norm or " deep think " in norm:
        score += 0.3

    score = round(score, 2)

    # 5. Pricing and subagent parameters from tier config
    tier_info = tiers_cfg.get(tier, tiers_cfg.get("pro", {}))
    pricing = tier_info.get("pricing_per_1m_usd", {"input": 1.25, "output": 5.00})

    if tier == "frontier":
        subagent = tier_info.get("subagent_model_when_parent_is_frontier", "inherit")
    else:
        subagent = tier_info.get("subagent_model", "pro" if tier == "pro" else ("flash" if tier == "builder" else "flash_lite"))

    display_name = format_display_name(raw_name, tier)

    return {
        "id": raw_name,
        "display_name": display_name,
        "tier": tier,
        "generation": gen,
        "capability_score": score,
        "subagent_model": subagent,
        "pricing_per_1m_usd": pricing,
        "excluded": False,
    }


def parse_antigravity_transcripts() -> Optional[Dict[str, Any]]:
    """Scan Antigravity brain transcripts for active Model Selection setting changes."""
    transcript_files = glob.glob(TRANSCRIPT_GLOB)
    if not transcript_files:
        return None

    # Sort transcripts by file modification time (most recent first)
    transcript_files.sort(key=lambda p: os.path.getmtime(p), reverse=True)

    setting_pattern = re.compile(
        r"Model Selection[`'\"]?\s+from\s+.*?\s+to\s+([^.\n]+)",
        re.IGNORECASE,
    )

    for tf in transcript_files:
        try:
            with open(tf, "r", encoding="utf-8", errors="ignore") as f:
                # Read lines in reverse or scan all to get latest change
                latest_model = None
                for line in f:
                    if "<USER_SETTINGS_CHANGE>" in line:
                        match = setting_pattern.search(line)
                        if match:
                            latest_model = match.group(1).strip()
                if latest_model:
                    return {
                        "model_string": latest_model,
                        "transcript_path": tf,
                        "source": "antigravity_transcript",
                    }
        except Exception:
            continue

    return None


def parse_antigravity_state() -> Optional[Dict[str, Any]]:
    """Inspect ~/.gemini/antigravity/antigravity_state.pbtxt."""
    if not ANTIGRAVITY_STATE_PATH.exists():
        return None
    try:
        content = ANTIGRAVITY_STATE_PATH.read_text(encoding="utf-8", errors="ignore")
        match = re.search(r'last_selected_agent_model:\s*"?([^"\n\r]+)"?', content)
        if match:
            raw = match.group(1).strip()
            if not raw.startswith("MODEL_PLACEHOLDER") and raw.lower() not in ("none", "null"):
                return {"model_string": raw, "source": "antigravity_state"}
    except Exception:
        pass
    return None


def fetch_gemini_api_models(api_key: str) -> List[Dict[str, Any]]:
    """Query live Google Gemini API for available models."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    models: List[Dict[str, Any]] = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Gemini-Advisor-Allocator/2.0"}, method="GET")
        with urllib.request.urlopen(req, timeout=4.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for item in data.get("models", []):
                name = item.get("name", "")
                display_name = item.get("displayName", "")
                supported = item.get("supportedGenerationMethods", [])
                if "generateContent" in supported:
                    models.append({
                        "id": name,
                        "display_name": display_name or name,
                        "source": "gemini_api",
                    })
    except Exception:
        pass
    return models


def load_cache() -> Optional[Dict[str, Any]]:
    """Read local allocated models cache."""
    if CACHE_PATH.exists():
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def save_cache(data: Dict[str, Any]) -> None:
    """Save allocation results to local cache."""
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


class ModelAllocator:
    """Dynamic discovery and allocation engine."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or load_config()

    def discover_all(self) -> Dict[str, Any]:
        """Gather models from all discovery sources."""
        sources_summary: Dict[str, Any] = {}
        all_candidates: List[Dict[str, Any]] = []

        # 1. Environment overrides
        env_frontier = os.environ.get("GEMINI_ADVISOR_FRONTIER_MODEL") or os.environ.get("GEMINI_FRONTIER_MODEL")
        env_builder = os.environ.get("GEMINI_ADVISOR_BUILDER_MODEL") or os.environ.get("GEMINI_FLASH_MODEL")
        env_lite = os.environ.get("GEMINI_ADVISOR_LITE_MODEL")
        env_gemini = os.environ.get("GEMINI_MODEL")
        env_agy = os.environ.get("AGY_MODEL")

        env_found = {}
        for var, val in [
            ("GEMINI_ADVISOR_FRONTIER_MODEL", env_frontier),
            ("GEMINI_ADVISOR_BUILDER_MODEL", env_builder),
            ("GEMINI_ADVISOR_LITE_MODEL", env_lite),
            ("GEMINI_MODEL", env_gemini),
            ("AGY_MODEL", env_agy),
        ]:
            if val:
                env_found[var] = val
                all_candidates.append({"id": val, "source": f"env:{var}"})
        sources_summary["environment"] = env_found

        # 2. Antigravity session transcript
        active_transcript = parse_antigravity_transcripts()
        if active_transcript:
            sources_summary["active_transcript"] = active_transcript
            all_candidates.append({
                "id": active_transcript["model_string"],
                "source": "transcript",
            })
        else:
            sources_summary["active_transcript"] = None

        # 3. Antigravity state
        agy_state = parse_antigravity_state()
        if agy_state:
            sources_summary["antigravity_state"] = agy_state
            all_candidates.append({
                "id": agy_state["model_string"],
                "source": "antigravity_state",
            })
        else:
            sources_summary["antigravity_state"] = None

        # 4. Google Gemini API
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if api_key:
            api_models = fetch_gemini_api_models(api_key)
            sources_summary["gemini_api_count"] = len(api_models)
            all_candidates.extend(api_models)
        else:
            sources_summary["gemini_api_count"] = 0

        # 5. Local cache
        cache = load_cache()
        if cache:
            sources_summary["cached_discovery_available"] = True
            for m in cache.get("discovered_models", []):
                all_candidates.append({"id": m.get("id"), "source": "cache"})
        else:
            sources_summary["cached_discovery_available"] = False

        # 6. Built-in registry
        known = self.config.get("known_models", DEFAULT_CONFIG["known_models"])
        sources_summary["builtin_count"] = len(known)
        for m in known:
            all_candidates.append({
                "id": m["id"],
                "display_name": m.get("display_name"),
                "source": "builtin",
            })

        # Score and deduplicate all candidates
        scored_models: Dict[str, Dict[str, Any]] = {}
        for cand in all_candidates:
            cid = cand.get("id")
            if not cid:
                continue
            scored = score_model(cid, self.config)
            if scored["excluded"]:
                continue
            # Keep highest score if duplicates exist
            existing = scored_models.get(scored["id"])
            if not existing or scored["capability_score"] > existing["capability_score"]:
                scored["source"] = cand.get("source", "discovered")
                scored_models[scored["id"]] = scored

        discovered_list = sorted(
            scored_models.values(),
            key=lambda x: x["capability_score"],
            reverse=True,
        )

        return {
            "sources": sources_summary,
            "discovered_models": discovered_list,
        }

    def resolve_allocation(self, persist_cache: bool = True) -> Dict[str, Any]:
        """Resolve optimal model allocation across Frontier, Pro, Builder, Lite."""
        discovery = self.discover_all()
        discovered = discovery["discovered_models"]
        tiers_cfg = self.config.get("tiers", DEFAULT_CONFIG["tiers"])

        # Check environment overrides first
        env_frontier = os.environ.get("GEMINI_ADVISOR_FRONTIER_MODEL") or os.environ.get("GEMINI_FRONTIER_MODEL")
        env_builder = os.environ.get("GEMINI_ADVISOR_BUILDER_MODEL") or os.environ.get("GEMINI_FLASH_MODEL")
        env_lite = os.environ.get("GEMINI_ADVISOR_LITE_MODEL")

        # Active parent detection:
        # Environment overrides have highest precedence, followed by active transcript, then state
        active_parent_str = os.environ.get("GEMINI_MODEL") or os.environ.get("AGY_MODEL")
        if not active_parent_str:
            active_trans = discovery["sources"].get("active_transcript")
            if active_trans:
                active_parent_str = active_trans["model_string"]
            elif discovery["sources"].get("antigravity_state"):
                active_parent_str = discovery["sources"]["antigravity_state"].get("model_string")

        active_parent_model = None
        if active_parent_str:
            active_parent_model = score_model(active_parent_str, self.config)

        # 1. Frontier Selection
        frontier_selected = None
        if env_frontier:
            frontier_selected = score_model(env_frontier, self.config)
        elif active_parent_model and active_parent_model["tier"] == "frontier":
            frontier_selected = active_parent_model
        else:
            # Pick highest-scoring frontier model
            frontier_candidates = [m for m in discovered if m["tier"] == "frontier"]
            if frontier_candidates:
                frontier_selected = frontier_candidates[0]
            else:
                default_id = tiers_cfg.get("frontier", {}).get("default_model", "gemini-4-argon")
                frontier_selected = score_model(default_id, self.config)

        # 2. Builder Selection
        builder_selected = None
        if env_builder:
            builder_selected = score_model(env_builder, self.config)
        else:
            builder_candidates = [m for m in discovered if m["tier"] == "builder"]
            if builder_candidates:
                builder_selected = builder_candidates[0]
            else:
                default_id = tiers_cfg.get("builder", {}).get("default_model", "gemini-3.8-flash")
                builder_selected = score_model(default_id, self.config)

        # 3. Lite Selection
        lite_selected = None
        if env_lite:
            lite_selected = score_model(env_lite, self.config)
        else:
            lite_candidates = [m for m in discovered if m["tier"] == "lite"]
            if lite_candidates:
                lite_selected = lite_candidates[0]
            else:
                default_id = tiers_cfg.get("lite", {}).get("default_model", "gemini-3.1-flash-lite")
                lite_selected = score_model(default_id, self.config)

        # 4. Pro Fallback Selection
        pro_candidates = [m for m in discovered if m["tier"] == "pro"]
        pro_selected = pro_candidates[0] if pro_candidates else score_model(
            tiers_cfg.get("pro", {}).get("default_model", "gemini-3.5-pro"), self.config
        )

        # Subagent Parameter Mapping
        # If parent active session is Frontier (e.g. Gemini 4 Argon), Reviewer uses "inherit"
        # so it stays on Argon without downgrading to "pro".
        # If active parent is Builder / Flash, Reviewer escalates to "pro".
        parent_is_frontier = (
            active_parent_model is None or active_parent_model["tier"] == "frontier"
        )
        if parent_is_frontier:
            reviewer_subagent = "inherit"
            reviewer_display = frontier_selected["display_name"]
        else:
            reviewer_subagent = "pro"
            reviewer_display = pro_selected["display_name"]

        builder_subagent = "flash"
        lite_subagent = "flash_lite"

        # Route Allocation String
        route_line = (
            f"Planner ({frontier_selected['display_name']} [Frontier]) -> "
            f"Builder ({builder_selected['display_name']} [{builder_subagent}]) -> "
            f"Reviewer (Fresh {reviewer_display} [{reviewer_subagent}])"
        )

        allocation_result = {
            "active_parent": active_parent_model,
            "parent_is_frontier": parent_is_frontier,
            "tiers": {
                "frontier": frontier_selected,
                "pro": pro_selected,
                "builder": builder_selected,
                "lite": lite_selected,
            },
            "subagent_parameters": {
                "reviewer": reviewer_subagent,
                "builder": builder_subagent,
                "lite": lite_subagent,
            },
            "route_allocation": route_line,
            "discovered_models": discovered,
        }

        # Cache allocation
        if persist_cache:
            save_cache(allocation_result)

        return allocation_result

    def verify_invariants(self, allocation: Dict[str, Any]) -> List[Tuple[bool, str]]:
        """Verify allocation invariants."""
        tiers = allocation["tiers"]
        f = tiers["frontier"]
        b = tiers["builder"]
        l = tiers["lite"]

        checks = []

        # 1. Capability Score: Frontier > Builder > Lite
        score_ok = f["capability_score"] > b["capability_score"] > l["capability_score"]
        checks.append((
            score_ok,
            f"Capability Hierarchy: Frontier ({f['capability_score']}) > Builder ({b['capability_score']}) > Lite ({l['capability_score']})",
        ))

        # 2. Pricing Hierarchy: Frontier >= Builder >= Lite
        cost_ok = (
            f["pricing_per_1m_usd"]["input"] >= b["pricing_per_1m_usd"]["input"] >= l["pricing_per_1m_usd"]["input"]
        )
        checks.append((
            cost_ok,
            f"Cost Hierarchy: Frontier (${f['pricing_per_1m_usd']['input']:.3f}) >= Builder (${b['pricing_per_1m_usd']['input']:.3f}) >= Lite (${l['pricing_per_1m_usd']['input']:.3f})",
        ))

        # 3. Subagent Mapping Check
        subagents = allocation["subagent_parameters"]
        active_parent = allocation.get("active_parent")
        if active_parent and active_parent["tier"] != "frontier":
            expected_rev = "pro"
        else:
            expected_rev = "inherit"

        rev_ok = (subagents["reviewer"] == expected_rev)
        checks.append((
            rev_ok,
            f"Subagent Mapping (Reviewer): {subagents['reviewer']} (expected '{expected_rev}')",
        ))

        b_ok = (subagents["builder"] == "flash")
        checks.append((b_ok, f"Subagent Mapping (Builder): {subagents['builder']} (expected 'flash')"))

        l_ok = (subagents["lite"] == "flash_lite")
        checks.append((l_ok, f"Subagent Mapping (Lite): {subagents['lite']} (expected 'flash_lite')"))

        return checks


# --- Self-Test Suite ---
def run_tests() -> bool:
    """Run comprehensive automated self-tests for the Dynamic Model Allocator."""
    print("==> Running Gemini Advisor Dynamic Model Allocator Self-Tests...\n")
    passed = 0
    total = 0
    config = load_config()

    # Test 1: Classification and scoring of Gemini 4 Argon as frontier outranking 3.5-pro and 2.5-pro
    total += 1
    argon_med = score_model("Gemini 4 Argon (Medium)", config)
    argon_raw = score_model("gemini-4-argon", config)
    pro_35 = score_model("gemini-3.5-pro", config)
    pro_25 = score_model("gemini-2.5-pro", config)

    assert argon_med["tier"] == "frontier", f"Expected frontier for Argon (Medium), got {argon_med['tier']}"
    assert argon_raw["tier"] == "frontier", f"Expected frontier for gemini-4-argon, got {argon_raw['tier']}"
    assert pro_35["tier"] == "pro", f"Expected pro for gemini-3.5-pro, got {pro_35['tier']}"
    assert pro_25["tier"] == "pro", f"Expected pro for gemini-2.5-pro, got {pro_25['tier']}"
    assert argon_med["capability_score"] > pro_35["capability_score"] > pro_25["capability_score"], (
        f"Argon score ({argon_med['capability_score']}) must outrank 3.5-pro ({pro_35['capability_score']}) and 2.5-pro ({pro_25['capability_score']})"
    )
    passed += 1
    print("✓ Test 1 Passed: Gemini 4 Argon classified as frontier outranking 3.5-pro and 2.5-pro.")

    # Test 2: Future-proof classification of unseen future models outranking Gemini 4 Argon without code changes
    total += 1
    xenon_5 = score_model("Gemini 5 Xenon", config)
    krypton_ultra = score_model("gemini-5.5-krypton-ultra", config)
    argon_max = score_model("gemini-6.0-argon-max", config)

    assert xenon_5["tier"] == "frontier", f"Gemini 5 Xenon should be frontier, got {xenon_5['tier']}"
    assert krypton_ultra["tier"] == "frontier", f"gemini-5.5-krypton-ultra should be frontier, got {krypton_ultra['tier']}"
    assert argon_max["tier"] == "frontier", f"gemini-6.0-argon-max should be frontier, got {argon_max['tier']}"
    assert xenon_5["capability_score"] > argon_raw["capability_score"], "Gemini 5 Xenon should outrank Gemini 4 Argon"
    assert krypton_ultra["capability_score"] > argon_raw["capability_score"], "Krypton Ultra should outrank Gemini 4 Argon"
    assert argon_max["capability_score"] > argon_raw["capability_score"], "Argon Max should outrank Gemini 4 Argon"
    passed += 1
    print("✓ Test 2 Passed: Unseen future frontier models (Xenon 5, Krypton Ultra, Argon Max) outrank Gemini 4 Argon.")

    # Test 3: Future-proof classification of unseen cheaper execution models outranking older flash/lite
    total += 1
    flash_45 = score_model("gemini-4.5-flash", config)
    flash_50 = score_model("gemini-5.0-flash", config)
    flash_38 = score_model("gemini-3.8-flash", config)
    flash_25 = score_model("gemini-2.5-flash", config)
    lite_50 = score_model("gemini-5.0-flash-lite", config)
    lite_31 = score_model("gemini-3.1-flash-lite", config)

    assert flash_45["tier"] == "builder", f"gemini-4.5-flash should be builder, got {flash_45['tier']}"
    assert flash_50["tier"] == "builder", f"gemini-5.0-flash should be builder, got {flash_50['tier']}"
    assert lite_50["tier"] == "lite", f"gemini-5.0-flash-lite should be lite, got {lite_50['tier']}"
    assert flash_50["capability_score"] > flash_45["capability_score"] > flash_38["capability_score"] > flash_25["capability_score"]
    assert lite_50["capability_score"] > lite_31["capability_score"]
    passed += 1
    print("✓ Test 3 Passed: Future execution models (Flash 4.5/5.0, Flash-Lite 5.0) outrank older generations.")

    # Test 4: Filtering out non-text/non-coding models
    total += 1
    for non_model in ["imagen-3", "veo-2.0", "text-embedding-004", "gemini-3.1-flash-lite-image"]:
        sc = score_model(non_model, config)
        assert sc["excluded"] is True, f"{non_model} should be excluded, got {sc}"
        assert sc["capability_score"] == 0.0
    passed += 1
    print("✓ Test 4 Passed: Non-text and non-coding models (imagen, veo, embedding, image) correctly excluded.")

    # Test 5: Transcript parsing of <USER_SETTINGS_CHANGE>
    total += 1
    sample_transcript_line = (
        '{"step_index":1,"source":"USER_EXPLICIT","type":"USER_INPUT","status":"DONE",'
        '"content":"<USER_SETTINGS_CHANGE>\\n'
        'The user changed setting `Model Selection` from None to Gemini 4 Argon (Medium). '
        'No need to comment on this change if the user doesn\'t ask about it.\\n'
        '</USER_SETTINGS_CHANGE>"}'
    )
    setting_pattern = re.compile(r"Model Selection[`'\"]?\s+from\s+.*?\s+to\s+([^.\n]+)", re.IGNORECASE)
    match = setting_pattern.search(sample_transcript_line)
    assert match is not None, "Failed to match Model Selection pattern"
    extracted_model = match.group(1).strip()
    assert extracted_model == "Gemini 4 Argon (Medium)", f"Extracted '{extracted_model}' instead of 'Gemini 4 Argon (Medium)'"
    parsed_score = score_model(extracted_model, config)
    assert parsed_score["tier"] == "frontier"
    passed += 1
    print("✓ Test 5 Passed: Successfully parsed transcript <USER_SETTINGS_CHANGE> to Gemini 4 Argon (Medium).")

    # Test 6: Subagent parameter resolution
    total += 1
    # Case A: Parent is Gemini 4 Argon
    allocator_argon = ModelAllocator(config)
    os.environ["GEMINI_MODEL"] = "Gemini 4 Argon (Medium)"
    alloc_argon = allocator_argon.resolve_allocation(persist_cache=False)
    assert alloc_argon["subagent_parameters"]["reviewer"] == "inherit", (
        f"Expected 'inherit' for Argon parent, got {alloc_argon['subagent_parameters']['reviewer']}"
    )

    # Case B: Parent is Gemini Flash
    allocator_flash = ModelAllocator(config)
    os.environ["GEMINI_MODEL"] = "Gemini 3.8 Flash (Medium)"
    alloc_flash = allocator_flash.resolve_allocation(persist_cache=False)
    assert alloc_flash["subagent_parameters"]["reviewer"] == "pro", (
        f"Expected 'pro' escalation for Flash parent, got {alloc_flash['subagent_parameters']['reviewer']}"
    )
    assert alloc_flash["subagent_parameters"]["builder"] == "flash"
    assert alloc_flash["subagent_parameters"]["lite"] == "flash_lite"

    # Clean up test env
    os.environ.pop("GEMINI_MODEL", None)
    passed += 1
    print("✓ Test 6 Passed: Subagent parameter mapping correctly uses 'inherit' for Argon and escalates to 'pro' for Flash.")

    # Test 7: Allocation invariants verification
    total += 1
    allocator_default = ModelAllocator(config)
    default_alloc = allocator_default.resolve_allocation(persist_cache=False)
    checks = allocator_default.verify_invariants(default_alloc)
    for ok, msg in checks:
        assert ok, f"Invariant failed: {msg}"
    passed += 1
    print("✓ Test 7 Passed: Allocation invariants verified (Frontier > Builder > Lite score and cost).")

    # Test 8: End-to-end JSON output structure validation
    total += 1
    assert "tiers" in default_alloc
    assert "frontier" in default_alloc["tiers"]
    assert "builder" in default_alloc["tiers"]
    assert "lite" in default_alloc["tiers"]
    assert "route_allocation" in default_alloc
    assert default_alloc["tiers"]["frontier"]["pricing_per_1m_usd"]["input"] == 2.50
    assert default_alloc["tiers"]["frontier"]["pricing_per_1m_usd"]["output"] == 10.00
    json_str = json.dumps(default_alloc)
    assert len(json_str) > 100
    passed += 1
    print("✓ Test 8 Passed: End-to-end JSON output schema and pricing fields validated.\n")

    print(f"==> ALL {passed}/{total} SELF-TESTS PASSED SUCCESSFULLY!\n")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Dynamic Model Discovery, Capability Scoring & Tier Allocation Engine for Gemini Advisor."
    )
    parser.add_argument("--check", action="store_true", help="Run discovery, check invariants, and display summary table")
    parser.add_argument("--allocate", action="store_true", help="Output exact SELECTIVE ROUTE allocation line")
    parser.add_argument("--discover", action="store_true", help="List all discovered models across discovery sources")
    parser.add_argument("--score", type=str, metavar="MODEL_NAME", help="Score and classify a specific model name")
    parser.add_argument("--json", action="store_true", help="Format output as structured JSON")
    parser.add_argument("--test", action="store_true", help="Run automated verification self-test suite")

    args = parser.parse_args()
    config = load_config()
    allocator = ModelAllocator(config)

    # 1. Test Mode
    if args.test:
        success = run_tests()
        sys.exit(0 if success else 1)

    # 2. Score Mode
    if args.score:
        result = score_model(args.score, config)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Model Evaluation: '{args.score}'")
            print(f"  • Classified Tier:    {result['tier']}")
            print(f"  • Generation:         {result['generation']}")
            print(f"  • Capability Score:   {result['capability_score']}")
            p_in = result["pricing_per_1m_usd"]["input"]
            p_out = result["pricing_per_1m_usd"]["output"]
            print(f"  • Estimated Pricing:  Input: ${p_in:.4f} / 1M, Output: ${p_out:.4f} / 1M USD")
            print(f"  • Subagent Parameter: {result['subagent_model']}")
            print(f"  • Excluded:           {result['excluded']}")
        return

    # 3. Discover Mode
    if args.discover:
        discovery = allocator.discover_all()
        if args.json:
            print(json.dumps(discovery, indent=2))
        else:
            print("================================================================================")
            print("                GEMINI ADVISOR: DISCOVERED MODELS REPORT                       ")
            print("================================================================================")
            sources = discovery["sources"]
            print("Discovery Sources:")
            print(f"  • Environment Overrides: {sources.get('environment') or 'None'}")
            act = sources.get('active_transcript')
            print(f"  • Active Transcript:     {act['model_string'] if act else 'None detected'}")
            agy = sources.get('antigravity_state')
            print(f"  • Antigravity State:     {agy.get('model_string') if agy else 'None'}")
            print(f"  • Gemini API Models:     {sources.get('gemini_api_count', 0)} models fetched")
            print(f"  • Built-in Models:       {sources.get('builtin_count', 0)} models registered")
            print("--------------------------------------------------------------------------------")
            print(f"{'Tier':<10} {'Score':>6}  {'Display Name':<28} {'Model Identifier'}")
            print("--------------------------------------------------------------------------------")
            for m in discovery["discovered_models"]:
                print(f"{m['tier']:<10} {m['capability_score']:>6.2f}  {m['display_name']:<28} {m['id']}")
            print("================================================================================")
        return

    # 4. Allocate Mode
    if args.allocate:
        allocation = allocator.resolve_allocation()
        if args.json:
            print(json.dumps({
                "route_allocation": allocation["route_allocation"],
                "planner": allocation["tiers"]["frontier"],
                "builder": allocation["tiers"]["builder"],
                "reviewer": {
                    "model": allocation["tiers"]["frontier" if allocation["parent_is_frontier"] else "pro"],
                    "subagent_model": allocation["subagent_parameters"]["reviewer"],
                },
            }, indent=2))
        else:
            print(allocation["route_allocation"])
        return

    # 5. Check Mode (Default when --check or no args specified)
    allocation = allocator.resolve_allocation()
    checks = allocator.verify_invariants(allocation)
    all_ok = all(ok for ok, _ in checks)

    if args.json:
        out = {
            "status": "PASS" if all_ok else "FAIL",
            "active_parent": allocation.get("active_parent"),
            "tiers": allocation["tiers"],
            "subagent_parameters": allocation["subagent_parameters"],
            "route_allocation": allocation["route_allocation"],
            "checks": [{"passed": ok, "message": msg} for ok, msg in checks],
        }
        print(json.dumps(out, indent=2))
    else:
        print("================================================================================")
        print("            GEMINI ADVISOR: DYNAMIC MODEL ALLOCATION & TIER CHECK               ")
        print("================================================================================")
        parent = allocation.get("active_parent")
        if parent:
            print(f"Active Parent Context: {parent['display_name']} [Tier: {parent['tier']}]")
        else:
            print("Active Parent Context: Default Frontier Baseline [Gemini 4 Argon]")

        print("\nTIER ALLOCATION SUMMARY:")
        print("-" * 80)
        print(f"{'Tier':<10} {'Role':<26} {'Allocated Model':<20} {'Score':>6}  {'Subagent':<10} {'Pricing (In/Out 1M)'}")
        print("-" * 80)
        tiers = allocation["tiers"]
        subparams = allocation["subagent_parameters"]

        f = tiers["frontier"]
        p = tiers["pro"]
        b = tiers["builder"]
        l = tiers["lite"]

        print(f"{'Frontier':<10} {'Architect / Reviewer':<26} {f['display_name']:<20} {f['capability_score']:>6.2f}  {subparams['reviewer']:<10} ${f['pricing_per_1m_usd']['input']:.2f} / ${f['pricing_per_1m_usd']['output']:.2f}")
        print(f"{'Pro':<10} {'High-Reasoning Fallback':<26} {p['display_name']:<20} {p['capability_score']:>6.2f}  {'pro':<10} ${p['pricing_per_1m_usd']['input']:.2f} / ${p['pricing_per_1m_usd']['output']:.2f}")
        print(f"{'Builder':<10} {'Code Execution':<26} {b['display_name']:<20} {b['capability_score']:>6.2f}  {subparams['builder']:<10} ${b['pricing_per_1m_usd']['input']:.3f} / ${b['pricing_per_1m_usd']['output']:.2f}")
        print(f"{'Lite':<10} {'Boilerplate Implementer':<26} {l['display_name']:<20} {l['capability_score']:>6.2f}  {subparams['lite']:<10} ${l['pricing_per_1m_usd']['input']:.4f} / ${l['pricing_per_1m_usd']['output']:.2f}")
        print("-" * 80)

        print("\nSELECTIVE ROUTE:")
        print(f"  {allocation['route_allocation']}")

        print("\nINVARIANT VERIFICATION:")
        for ok, msg in checks:
            mark = "[PASS]" if ok else "[FAIL]"
            print(f"  {mark} {msg}")

        print("--------------------------------------------------------------------------------")
        if all_ok:
            print("STATUS: ALL INVARIANTS PASS (Gemini Advisor is fully aligned and ready).")
        else:
            print("STATUS: INVARIANT FAILURE DETECTED!")
        print("================================================================================")

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
