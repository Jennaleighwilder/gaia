"""
GAIA Saddle Engine
Detects multi-engine approach to threshold before visible convergence.
"""

from __future__ import annotations

from runtime.engines.common import clamp


class SaddleEngine:
    def __init__(self):
        self.history = {}
        self.max_history = 120

    def ingest(self, station_id, timestamp, **data):
        row = {"timestamp": timestamp, **data}
        self.history.setdefault(station_id, []).append(row)
        if len(self.history[station_id]) > self.max_history:
            self.history[station_id] = self.history[station_id][-self.max_history:]

    def detect_saddle(self, engine_scores_history):
        if len(engine_scores_history) < 3:
            return 0.0, 0, 0.0
        approaching_count = 0
        total_velocity = 0.0
        latest = engine_scores_history[-1]
        prev = engine_scores_history[-2]
        prev2 = engine_scores_history[-3]
        for engine_name in latest:
            if engine_name in ("timestamp", "region"):
                continue
            current = latest.get(engine_name, 0.0)
            previous = prev.get(engine_name, 0.0)
            before_that = prev2.get(engine_name, 0.0)
            if current is None or previous is None or before_that is None:
                continue
            velocity = current - previous
            acceleration = velocity - (previous - before_that)
            below_threshold = current < 0.6
            rising = velocity > 0.02
            accelerating = acceleration > 0
            if below_threshold and rising and accelerating:
                approaching_count += 1
                total_velocity += velocity
        if approaching_count < 2:
            return 0.0, approaching_count, total_velocity
        count_score = min(1.0, approaching_count / 6.0)
        velocity_score = min(1.0, total_velocity / 0.5)
        saddle_score = (count_score * 0.6) + (velocity_score * 0.4)
        return round(min(1.0, saddle_score), 4), approaching_count, total_velocity

    def score(self, station_id, **current_data):
        history = list(self.history.get(station_id, []))
        current_scores = current_data.get("engine_scores")
        if current_scores:
            history.append(current_scores)
        saddle_score, approaching_count, total_velocity = self.detect_saddle(history)
        return {
            "engine": "saddle",
            "score": saddle_score,
            "approaching_count": approaching_count,
            "total_velocity": round(total_velocity, 4),
        }
