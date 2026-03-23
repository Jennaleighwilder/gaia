"""
Base Siren — checks and balances for every atmospheric element watcher.

No siren can ring alone. Every siren needs:
1. Its own signal is strong (what it watches)
2. At least one other independent siren confirms (corroboration)

Each siren has:
- Confidence score (consecutive obs, signal strengthening, data freshness)
- Corroboration requirement (cannot SCREAM without another siren at ALERT+)
- Siren-specific veto conditions (silence even when signal looks strong)
- Audit trail (accountability for every decision)
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

SIREN_STATUS = ("SCREAMING", "ALERT", "WATCHING", "SILENT")


@dataclass
class SirenAudit:
    """Audit trail for accountability."""

    siren_name: str
    timestamp: str
    raw_signal_value: Any
    raw_status: str  # Before confidence/corroboration
    confidence_score: float
    veto_checked: bool
    veto_triggered: bool
    corroboration_available: bool
    final_status: str
    reason: str


@dataclass
class SirenResult:
    """Result from a siren evaluation."""

    status: str  # SCREAMING | ALERT | WATCHING | SILENT
    confidence: float
    audit: SirenAudit


class BaseSiren:
    """
    Base class for all sirens. Handles confidence, corroboration, veto, audit.
    Subclasses define: name, get_raw_signal(), thresholds, check_veto().
    """

    name: str = "BASE"
    history_len: int = 10

    def __init__(self):
        self.signal_history: deque = deque(maxlen=self.history_len)
        self.audit_log: list[SirenAudit] = []

    def get_raw_signal(self, observation: dict, payload: dict) -> Any:
        """Override: return the raw signal value this siren watches."""
        return None

    def signal_to_status(self, raw_signal: Any, payload: dict | None = None) -> str:
        """Override: map raw signal to SCREAMING/ALERT/WATCHING/SILENT."""
        return "SILENT"

    def check_veto(self, observation: dict, payload: dict, raw_status: str = "") -> bool:
        """
        Override: return True if this siren must stay SILENT despite strong signal.
        E.g. moisture siren: if GPS_PW < 10mm, cannot scream.
        raw_status: status from signal_to_status (for consecutive-obs checks).
        """
        return False

    def _compute_confidence(
        self,
        raw_signal: Any,
        raw_status: str,
        observation: dict,
    ) -> float:
        """
        Confidence from: consecutive obs with signal, signal strengthening, data freshness.
        SCREAMING requires confidence >= 0.7. Single spike = ALERT max.
        """
        confidence = 0.0

        # Consecutive observations with signal (ALERT or above)
        self.signal_history.append((raw_signal, raw_status))
        consecutive = 0
        for _, status in reversed(self.signal_history):
            if status in ("SCREAMING", "ALERT"):
                consecutive += 1
            else:
                break
        if consecutive >= 3:
            confidence += 0.4
        elif consecutive >= 1:
            confidence += 0.2

        # Signal strengthening (getting worse not better)
        if len(self.signal_history) >= 3:
            recent = [s for _, s in list(self.signal_history)[-3:]]
            if recent.count("SCREAMING") + recent.count("ALERT") >= 2:
                confidence += 0.3

        # Data freshness (timestamp within 30 min of "now" is idealized; we use obs recency)
        ts = observation.get("timestamp", "")
        if ts:
            try:
                obs_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                age_min = (datetime.now(timezone.utc) - obs_dt).total_seconds() / 60.0
                if age_min < 30:
                    confidence += 0.3
                elif age_min < 60:
                    confidence += 0.2
                elif age_min < 120:
                    confidence += 0.1
            except (ValueError, TypeError):
                pass

        return min(1.0, confidence)

    def evaluate(
        self,
        observation: dict,
        payload: dict,
        other_siren_states: dict[str, str],
    ) -> SirenResult:
        """
        Full evaluation: signal -> veto -> status -> confidence -> corroboration -> audit.
        """
        raw_signal = self.get_raw_signal(observation, payload)
        raw_status = self.signal_to_status(raw_signal, payload)

        # Veto check
        veto_triggered = self.check_veto(observation, payload, raw_status)
        if veto_triggered:
            raw_status = "SILENT"

        confidence = self._compute_confidence(raw_signal, raw_status, observation)

        # SCREAMING requires confidence >= 0.7; single spike = ALERT max
        if raw_status == "SCREAMING" and confidence < 0.7:
            raw_status = "ALERT"

        # Corroboration: cannot SCREAM alone
        corroboration = any(
            s in ("SCREAMING", "ALERT") for name, s in other_siren_states.items() if name != self.name
        )
        final_status = raw_status
        if raw_status == "SCREAMING" and not corroboration:
            final_status = "ALERT"
            reason = "No other siren alerting — cannot scream alone"
        else:
            reason = "OK"

        audit = SirenAudit(
            siren_name=self.name,
            timestamp=datetime.now(timezone.utc).isoformat(),
            raw_signal_value=raw_signal,
            raw_status=raw_status,
            confidence_score=confidence,
            veto_checked=True,
            veto_triggered=veto_triggered,
            corroboration_available=corroboration,
            final_status=final_status,
            reason=reason,
        )
        self.audit_log.append(audit)
        if len(self.audit_log) > 100:
            self.audit_log = self.audit_log[-100:]

        return SirenResult(status=final_status, confidence=confidence, audit=audit)

    def reset(self) -> None:
        """Clear history for new backtest/run."""
        self.signal_history.clear()
        self.audit_log.clear()

    @staticmethod
    def apply_corroboration(results: dict[str, "SirenResult"]) -> dict[str, "SirenResult"]:
        """
        Post-process: no siren can SCREAM alone.
        If status is SCREAMING but no other siren is ALERT or SCREAMING, downgrade to ALERT.
        """
        out: dict[str, SirenResult] = {}
        for name, r in results.items():
            if r.status == "SCREAMING":
                others_alerting = any(
                    res.status in ("SCREAMING", "ALERT")
                    for n, res in results.items()
                    if n != name
                )
                if not others_alerting:
                    out[name] = SirenResult(status="ALERT", confidence=r.confidence, audit=r.audit)
                    continue
            out[name] = r
        return out
