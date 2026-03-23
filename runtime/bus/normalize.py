"""
West Bus — Metric normalization.
Maps module-native metrics to a shared 0.0–1.0 instability scale.
0.0 = fully stable, 1.0 = maximum instability.
"""

from typing import Optional

# Registry: (source, metric_name) → normalization function
# Each lambda takes a raw value and returns 0.0–1.0
_NORMALIZERS = {
    # Governor metrics
    ("governor", "recovery_pressure"): lambda v: min(v / 10.0, 1.0),
    ("governor", "survival_probability"): lambda v: 1.0 - v,  # high survival = low instability

    # Decision Ledger
    ("decision_ledger", "drift_index"): lambda v: min(max(v, 0.0), 1.0),  # already 0–1

    # Hyperintelligence — Twelve Deviations
    ("twelve_deviations", "deviation_count"): lambda v: min(v / 12.0, 1.0),
    ("twelve_deviations", "max_deviation_score"): lambda v: min(max(v, 0.0), 1.0),

    # Hyperintelligence — Saddle Detection (CEREBRO)
    ("saddle_detection", "signal_velocity"): lambda v: 1.0 - min(abs(v) / 100.0, 1.0),
    # velocity → 0 means phase transition (high instability)

    # Hyperintelligence — Mirror Protocol
    ("mirror_protocol", "coherence_score"): lambda v: 1.0 - min(max(v, 0.0), 1.0),
    # high coherence = low instability

    # Hyperintelligence — Persephone
    ("persephone", "flower_distortion"): lambda v: min(max(v, 0.0), 1.0),
    # high distortion = high instability

    # Hyperintelligence — Alexandria
    ("alexandria", "identity_drift"): lambda v: min(max(v, 0.0), 1.0),

    # Crypto-verification — Drift Monitor
    ("drift_monitor", "drift_score"): lambda v: min(max(v, 0.0), 1.0),

    # Saint Jude
    ("saint_jude", "abandonment_drift"): lambda v: min(max(v, 0.0), 1.0),
    ("saint_jude", "uncertainty_score"): lambda v: min(max(v, 0.0), 1.0),
    ("saint_jude", "care_effort"): lambda v: 1.0 - min(max(v, 0.0), 1.0),
    # low care effort = high instability
}


def normalize_instability(source: str, metric_name: str, raw_value: float) -> float:
    """
    Convert a module-native metric to the shared 0.0–1.0 instability scale.

    Args:
        source: The component name (e.g. "governor", "twelve_deviations")
        metric_name: The native metric name (e.g. "recovery_pressure", "deviation_count")
        raw_value: The raw metric value from the source

    Returns:
        Float 0.0–1.0 where 0.0 = fully stable, 1.0 = maximum instability.
        Returns raw_value clamped to [0,1] if no normalizer is registered.
    """
    key = (source, metric_name)
    normalizer = _NORMALIZERS.get(key)
    if normalizer is not None:
        return normalizer(raw_value)
    # Unknown source/metric: clamp to [0,1] as fallback
    return min(max(float(raw_value), 0.0), 1.0)


def register_normalizer(source: str, metric_name: str, fn):
    """
    Register a new normalizer at runtime.
    fn: callable(raw_value) → float 0.0–1.0
    """
    _NORMALIZERS[(source, metric_name)] = fn


def list_normalizers():
    """Return list of registered (source, metric_name) pairs."""
    return list(_NORMALIZERS.keys())
