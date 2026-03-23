"""
GAIA Oscillation Engine
Scores the slow background climate state from persisted index phases.
When timestamp is provided, uses historical MEI lookup (date-aware).
Real-time falls back to static oscillation_state.json.
"""

from __future__ import annotations

import json
import os

from runtime.engines.common import clamp

DEFAULT_STATE_PATH = os.path.expanduser("~/gaia/runtime/state/oscillation_state.json")


class OscillationEngine:
    def __init__(self, state_path: str = DEFAULT_STATE_PATH):
        self.state_path = state_path

    def ingest(self, station_id, timestamp, **data):
        return None

    def _load_state(self):
        with open(self.state_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def score(self, station_id="east_tn", **current_data):
        # Date-aware: use historical MEI when timestamp provided (backtest)
        timestamp = current_data.get("timestamp")
        parsed = None
        if timestamp:
            from runtime.data.oscillation_historical import parse_date, get_enso_score

            parsed = parse_date(timestamp)
        if parsed:
            year, month = parsed
            enso_score = get_enso_score(year, month)
            return {
                "engine": "oscillation",
                "score": round(clamp(enso_score), 4),
                "channels": {"enso": enso_score, "nao": 0.5, "pna": 0.5, "mjo": 0.5},
            }

        # Real-time: use static state file
        state = current_data.get("state") or self._load_state()
        enso_phase = state["enso"]["phase"]
        nao_phase = state["nao"]["phase"]
        pna_phase = state["pna"]["phase"]
        mjo_phase = int(state["mjo"]["phase"])
        mjo_amp = float(state["mjo"].get("amplitude", 1.0))

        enso_score = {"la_nina": 0.85, "neutral": 0.20, "el_nino": 0.10}.get(enso_phase, 0.2)
        nao_score = {"negative": 0.8, "neutral": 0.20, "positive": 0.10}.get(nao_phase, 0.2)
        pna_score = {"positive": 0.75, "neutral": 0.20, "negative": 0.10}.get(pna_phase, 0.2)
        if mjo_phase in (2, 3):
            mjo_score = 0.9
        elif mjo_phase in (6, 7):
            mjo_score = 0.05
        else:
            mjo_score = 0.25
        mjo_score = clamp(mjo_score * min(1.0, mjo_amp))

        score = 0.01 + (enso_score * 0.35) + (nao_score * 0.25) + (pna_score * 0.20) + (mjo_score * 0.20)
        return {
            "engine": "oscillation",
            "score": round(clamp(score), 4),
            "channels": {"enso": enso_score, "nao": nao_score, "pna": pna_score, "mjo": mjo_score},
        }
