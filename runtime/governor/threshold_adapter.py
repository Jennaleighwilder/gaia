"""
Adaptive Threshold Engine

Tracks outcomes of ALLOW vs DEFER decisions and adjusts governor
thresholds based on empirical evidence.

The core idea:
- If the governor ALLOWED an action and instability ROSE afterward → threshold should be LOWER
- If the governor DEFERRED and instability FELL afterward → deferral was correct, keep threshold
- If the governor DEFERRED and instability stayed LOW → threshold might be too aggressive
- Learning rate is slow (0.01 per adjustment) to prevent oscillation

State is stored in ~/west-os/runtime/state/threshold_state.json
"""

import json
import os
import time
from pathlib import Path

STATE_PATH = os.environ.get(
    "GAIA_STATE_PATH",
    os.path.expanduser("~/gaia/runtime/state/threshold_state.json"),
)

# Defaults
DEFAULT_STATE = {
    "review_threshold": 0.7,
    "defer_threshold": 0.9,
    "decisions": [],
    "adjustments": [],
    "total_allows": 0,
    "total_defers": 0,
    "total_reviews": 0,
    "allow_regret_count": 0,
    "defer_vindicated_count": 0,
    "defer_regret_count": 0,
    "review_vindicated_count": 0,
    "review_regret_count": 0,
    "override_events": [],
    "last_updated": None,
}

LEARNING_RATE = 0.01
MAX_DECISIONS = 200
MIN_DECISIONS_BEFORE_ADAPTING = 20


def load_state() -> dict:
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH) as f:
                raw = f.read().strip()
                if raw:
                    return json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            pass
    return DEFAULT_STATE.copy()


def save_state(state: dict):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    state["last_updated"] = time.time()
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def record_decision(verdict: str, instability_at_decision: float,
                    claim_id: str = "", actor: str = ""):
    """Record a governor decision for later outcome tracking."""
    state = load_state()

    decision = {
        "verdict": verdict,
        "instability_at_decision": instability_at_decision,
        "claim_id": claim_id,
        "actor": actor,
        "timestamp": time.time(),
        "outcome_instability": None,
        "outcome_recorded": False,
    }

    state["decisions"].append(decision)

    if verdict == "ALLOW":
        state["total_allows"] = state.get("total_allows", 0) + 1
    elif verdict == "DEFER":
        state["total_defers"] = state.get("total_defers", 0) + 1
    elif verdict == "REVIEW":
        state["total_reviews"] = state.get("total_reviews", 0) + 1

    if len(state["decisions"]) > MAX_DECISIONS:
        state["decisions"] = state["decisions"][-MAX_DECISIONS:]

    save_state(state)


def record_outcome(current_instability: float):
    """
    Called periodically to record outcomes for recent decisions.
    A decision's outcome is the instability level 30-60 seconds after the decision.
    """
    state = load_state()
    now = time.time()
    changed = False

    for decision in state["decisions"]:
        if decision.get("outcome_recorded"):
            continue

        age = now - decision["timestamp"]

        if 30 <= age <= 120:
            decision["outcome_instability"] = current_instability
            decision["outcome_recorded"] = True
            changed = True

            before = decision["instability_at_decision"]
            after = current_instability
            verdict = decision["verdict"]

            if verdict == "ALLOW" and after > before + 0.1:
                state["allow_regret_count"] = state.get("allow_regret_count", 0) + 1
            elif verdict in ("DEFER", "BUS_DEFER") and after >= 0.7:
                state["defer_vindicated_count"] = state.get("defer_vindicated_count", 0) + 1
            elif verdict in ("DEFER", "BUS_DEFER") and after < 0.4:
                state["defer_regret_count"] = state.get("defer_regret_count", 0) + 1

    if changed:
        save_state(state)


def adapt_thresholds() -> dict:
    """
    Adjust thresholds based on accumulated outcomes.
    Returns the current thresholds.
    """
    state = load_state()

    total_allows = state.get("total_allows", 0)
    total_defers = state.get("total_defers", 0)
    total_reviews = state.get("total_reviews", 0)
    total_decided = total_allows + total_defers + total_reviews

    if total_decided < MIN_DECISIONS_BEFORE_ADAPTING:
        return {
            "review_threshold": state.get("review_threshold", 0.7),
            "defer_threshold": state.get("defer_threshold", 0.9),
            "adapted": False,
            "reason": f"Need {MIN_DECISIONS_BEFORE_ADAPTING} decisions, have {total_decided}",
        }

    old_review = state.get("review_threshold", 0.7)
    old_defer = state.get("defer_threshold", 0.9)

    if total_allows > 0:
        allow_regret_rate = state.get("allow_regret_count", 0) / total_allows
        if allow_regret_rate > 0.3:
            state["review_threshold"] = max(0.3, old_review - LEARNING_RATE)
            state["defer_threshold"] = max(0.5, old_defer - LEARNING_RATE)

    total_defers_with_outcome = state.get("defer_vindicated_count", 0) + state.get("defer_regret_count", 0)
    if total_defers_with_outcome > 0:
        defer_regret_rate = state.get("defer_regret_count", 0) / total_defers_with_outcome
        if defer_regret_rate > 0.4:
            state["review_threshold"] = min(0.9, old_review + LEARNING_RATE)
            state["defer_threshold"] = min(0.98, old_defer + LEARNING_RATE)

    if state.get("review_threshold", 0.7) >= state.get("defer_threshold", 0.9):
        state["defer_threshold"] = state["review_threshold"] + 0.1

    if state.get("review_threshold") != old_review or state.get("defer_threshold") != old_defer:
        state.setdefault("adjustments", []).append({
            "timestamp": time.time(),
            "old_review": old_review,
            "new_review": state["review_threshold"],
            "old_defer": old_defer,
            "new_defer": state["defer_threshold"],
            "allow_regret_rate": state.get("allow_regret_count", 0) / max(1, total_allows),
            "defer_regret_rate": state.get("defer_regret_count", 0) / max(1, total_defers_with_outcome),
        })

    save_state(state)

    return {
        "review_threshold": round(state.get("review_threshold", 0.7), 4),
        "defer_threshold": round(state.get("defer_threshold", 0.9), 4),
        "adapted": state.get("review_threshold") != old_review or state.get("defer_threshold") != old_defer,
        "total_decisions": total_decided,
        "allow_regret_rate": round(state.get("allow_regret_count", 0) / max(1, total_allows), 3),
        "defer_regret_rate": round(state.get("defer_regret_count", 0) / max(1, total_defers_with_outcome), 3),
        "adjustments_made": len(state.get("adjustments", [])),
    }


def get_current_thresholds() -> dict:
    """Get current thresholds without adapting."""
    state = load_state()
    return {
        "review_threshold": state.get("review_threshold", 0.7),
        "defer_threshold": state.get("defer_threshold", 0.9),
        "total_decisions": state.get("total_allows", 0) + state.get("total_defers", 0) + state.get("total_reviews", 0),
        "adjustments_made": len(state.get("adjustments", [])),
    }


def record_override_feedback(
    original_verdict: str,
    override_verdict: str,
    instability_at_decision: float,
    claim_id: str = "",
    actor: str = "",
    reason: str = "",
) -> dict:
    """
    Record human override feedback and map to regret/reinforcement counters.

    This does not create the original decision row; callers should call
    record_decision(...) first so totals/denominators stay consistent.
    """
    state = load_state()

    original = str(original_verdict or "").upper()
    override = str(override_verdict or "").upper()
    now = time.time()
    mapped = "neutral"

    # Human moved from permissive -> cautious: ALLOW was likely a miss.
    if original == "ALLOW" and override in ("REVIEW", "DEFER", "BUS_DEFER", "DENY"):
        state["allow_regret_count"] = state.get("allow_regret_count", 0) + 1
        mapped = "allow_regret"
    # Human moved from DEFER to ALLOW: likely over-conservative defer.
    elif original in ("DEFER", "BUS_DEFER") and override == "ALLOW":
        state["defer_regret_count"] = state.get("defer_regret_count", 0) + 1
        mapped = "defer_regret"
    # Human kept/strengthened caution from DEFER family.
    elif original in ("DEFER", "BUS_DEFER") and override in ("REVIEW", "DEFER", "BUS_DEFER"):
        state["defer_vindicated_count"] = state.get("defer_vindicated_count", 0) + 1
        mapped = "defer_vindicated"
    # REVIEW channel bookkeeping (informational for now; not in threshold math yet).
    elif original == "REVIEW" and override in ("REVIEW", "DEFER", "BUS_DEFER"):
        state["review_vindicated_count"] = state.get("review_vindicated_count", 0) + 1
        mapped = "review_vindicated"
    elif original == "REVIEW" and override == "ALLOW":
        state["review_regret_count"] = state.get("review_regret_count", 0) + 1
        mapped = "review_regret"

    state.setdefault("override_events", []).append({
        "timestamp": now,
        "claim_id": claim_id,
        "actor": actor,
        "original_verdict": original,
        "override_verdict": override,
        "instability_at_decision": float(instability_at_decision or 0.0),
        "reason": reason,
        "mapped_feedback": mapped,
    })
    if len(state["override_events"]) > MAX_DECISIONS:
        state["override_events"] = state["override_events"][-MAX_DECISIONS:]

    save_state(state)
    return {
        "mapped_feedback": mapped,
        "allow_regret_count": state.get("allow_regret_count", 0),
        "defer_vindicated_count": state.get("defer_vindicated_count", 0),
        "defer_regret_count": state.get("defer_regret_count", 0),
        "review_vindicated_count": state.get("review_vindicated_count", 0),
        "review_regret_count": state.get("review_regret_count", 0),
    }
