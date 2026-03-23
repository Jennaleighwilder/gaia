"""
GAIA Correlation Miner
Finds repeated precursor sequences that precede warnings or emergencies.
"""

from __future__ import annotations

from collections import Counter, defaultdict


class CorrelationMiner:
    def __init__(self):
        self.history = []

    def ingest(self, station_id, timestamp, **data):
        self.history.append({"station_id": station_id, "timestamp": timestamp, **data})
        if len(self.history) > 5000:
            self.history = self.history[-5000:]

    def mine(self, event_history):
        sequence_counts = Counter()
        success_counts = defaultdict(int)
        for idx, event in enumerate(event_history):
            if event.get("event_type") != "gaia_decision":
                continue
            if event.get("decision") not in {"WARNING", "EMERGENCY"}:
                continue
            prior = tuple(e["event_type"] for e in event_history[max(0, idx - 3):idx])
            if not prior:
                continue
            sequence_counts[prior] += 1
            success_counts[prior] += 1
        proposals = []
        for sequence, count in sequence_counts.items():
            confidence = success_counts[sequence] / count
            if count >= 2 and confidence >= 0.5:
                proposals.append(
                    {
                        "sequence": list(sequence),
                        "occurrences": count,
                        "confidence": round(confidence, 4),
                        "proposal": f"When {sequence} occurs, elevate pre-convergence monitoring",
                    }
                )
        return proposals

    def score(self, station_id="network", **current_data):
        event_history = current_data.get("event_history", [])
        proposals = self.mine(event_history)
        return {"engine": "correlation_miner", "score": None, "proposals": proposals}

