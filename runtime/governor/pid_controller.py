"""
PID Controller for West-OS Governor
====================================
Proportional: already exists (regime detection scales thresholds)
Derivative: back off when threat recedes, lean in when growing
Integral: escalate strategy if stuck in REVIEW too long

Returns a threshold multiplier:
  > 1.0 = more lenient (threat receding or system stable)
  < 1.0 = more aggressive (threat growing or stuck in limbo)
  = 1.0 = neutral
"""

# Per-claim state storage
_pid_state = {}  # claim_id -> {"conv_history": [...], "decision_history": [...]}

MAX_HISTORY = 10


def _get_state(claim_id):
    if claim_id not in _pid_state:
        _pid_state[claim_id] = {
            "conv_history": [],
            "decision_history": []
        }
    return _pid_state[claim_id]


def record_event(claim_id, convergence_score, decision):
    """Call after each event to update PID state."""
    state = _get_state(claim_id)
    state["conv_history"].append(convergence_score or 0.0)
    state["decision_history"].append(decision or "ALLOW")
    # Trim to max history
    if len(state["conv_history"]) > MAX_HISTORY:
        state["conv_history"] = state["conv_history"][-MAX_HISTORY:]
    if len(state["decision_history"]) > MAX_HISTORY:
        state["decision_history"] = state["decision_history"][-MAX_HISTORY:]


def compute_pid_modifier(claim_id):
    """
    Compute threshold multiplier from derivative + integral.

    Derivative: trend of convergence_score over last 3 events.
      Positive trend (growing threat) -> aggressive (0.85)
      Negative trend (receding threat) -> lenient (1.2)

    Integral: consecutive REVIEWs.
      5+ consecutive REVIEWs -> force action (0.75)

    Returns float multiplier for threshold.
    """
    state = _get_state(claim_id)
    modifier = 1.0

    # === DERIVATIVE ===
    conv = state["conv_history"]
    if len(conv) >= 3:
        recent = conv[-3:]
        # Linear trend: last - first over the window
        trend = recent[-1] - recent[0]

        if trend > 0.1:
            # Threat GROWING — get aggressive
            modifier *= 0.85
        elif trend < -0.1:
            # Threat RECEDING — back off
            modifier *= 1.2
        # else: stable, no change

    # === INTEGRAL ===
    decisions = state["decision_history"]
    if len(decisions) >= 5:
        # Count consecutive REVIEWs from the end
        consecutive_reviews = 0
        for d in reversed(decisions):
            if d == "REVIEW":
                consecutive_reviews += 1
            else:
                break

        if consecutive_reviews >= 5:
            # Stuck in REVIEW limbo — force escalation
            modifier *= 0.75

    return round(modifier, 4)


def reset_claim(claim_id):
    """Clear state for a claim (e.g., on run reset)."""
    if claim_id in _pid_state:
        del _pid_state[claim_id]


def reset_all():
    """Clear all PID state."""
    _pid_state.clear()


# =============================================================
# UNIT TESTS
# =============================================================

def _test_derivative_growing():
    reset_all()
    cid = "TEST-GROW"
    record_event(cid, 0.3, "ALLOW")
    record_event(cid, 0.5, "REVIEW")
    record_event(cid, 0.7, "REVIEW")
    m = compute_pid_modifier(cid)
    assert m < 1.0, f"Growing threat should be aggressive, got {m}"
    print(f"  PASS: derivative growing -> {m}")


def _test_derivative_receding():
    reset_all()
    cid = "TEST-RECEDE"
    record_event(cid, 0.7, "REVIEW")
    record_event(cid, 0.5, "REVIEW")
    record_event(cid, 0.3, "ALLOW")
    m = compute_pid_modifier(cid)
    assert m > 1.0, f"Receding threat should be lenient, got {m}"
    print(f"  PASS: derivative receding -> {m}")


def _test_derivative_stable():
    reset_all()
    cid = "TEST-STABLE"
    record_event(cid, 0.4, "ALLOW")
    record_event(cid, 0.42, "ALLOW")
    record_event(cid, 0.41, "ALLOW")
    m = compute_pid_modifier(cid)
    assert m == 1.0, f"Stable should be neutral, got {m}"
    print(f"  PASS: derivative stable -> {m}")


def _test_integral_stuck():
    reset_all()
    cid = "TEST-STUCK"
    for i in range(6):
        record_event(cid, 0.5, "REVIEW")
    m = compute_pid_modifier(cid)
    assert m < 0.8, f"Stuck in REVIEW should force action, got {m}"
    print(f"  PASS: integral stuck -> {m}")


def _test_integral_not_stuck():
    reset_all()
    cid = "TEST-NOTSTUCK"
    record_event(cid, 0.5, "REVIEW")
    record_event(cid, 0.5, "ALLOW")
    record_event(cid, 0.5, "REVIEW")
    record_event(cid, 0.5, "REVIEW")
    record_event(cid, 0.5, "ALLOW")
    m = compute_pid_modifier(cid)
    # Not 5 consecutive REVIEWs, so no integral kick
    assert m >= 0.8, f"Not stuck should not force action, got {m}"
    print(f"  PASS: integral not stuck -> {m}")


def _test_combined():
    reset_all()
    cid = "TEST-COMBINED"
    # Growing threat AND stuck in review
    record_event(cid, 0.3, "REVIEW")
    record_event(cid, 0.4, "REVIEW")
    record_event(cid, 0.5, "REVIEW")
    record_event(cid, 0.6, "REVIEW")
    record_event(cid, 0.7, "REVIEW")
    m = compute_pid_modifier(cid)
    # Both derivative (aggressive) and integral (force action)
    assert m < 0.7, f"Combined should be very aggressive, got {m}"
    print(f"  PASS: combined growing + stuck -> {m}")


def _test_empty():
    reset_all()
    m = compute_pid_modifier("NONEXISTENT")
    assert m == 1.0, f"Empty state should be neutral, got {m}"
    print(f"  PASS: empty state -> {m}")


if __name__ == "__main__":
    print("PID Controller Tests:")
    _test_derivative_growing()
    _test_derivative_receding()
    _test_derivative_stable()
    _test_integral_stuck()
    _test_integral_not_stuck()
    _test_combined()
    _test_empty()
    print("ALL PASSED")
