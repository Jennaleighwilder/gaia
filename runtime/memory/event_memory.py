"""
GAIA Event Memory.

Append-only persistent memory of predictions, outcomes, and learned lessons.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class EventMemory:
    def __init__(self, path: str = "data/memory/event_memory.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record_prediction(self, prediction: dict) -> None:
        entry = {
            "type": "prediction",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "region": prediction.get("region", ""),
            "decision": prediction.get("decision", ""),
            "convergence_count": prediction.get("convergence_count", 0),
            "engine_scores": prediction.get("engine_scores", {}),
            "saddle_active": prediction.get("saddle_active", False),
            "correlation": prediction.get("motion_correlation", prediction.get("correlation", 0.0)),
            "upper_air_available": prediction.get("upper_air_available", False),
            "composite_stp": prediction.get("composite_stp"),
        }
        self._append(entry)

    def record_outcome(self, prediction_timestamp: str, outcome: dict) -> None:
        entry = {
            "type": "outcome",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "prediction_timestamp": prediction_timestamp,
            "event_occurred": outcome.get("event_occurred", False),
            "event_type": outcome.get("event_type"),
            "event_severity": outcome.get("event_severity"),
            "was_correct": outcome.get("was_correct"),
            "was_false_alarm": outcome.get("was_false_alarm"),
            "was_miss": outcome.get("was_miss"),
        }
        self._append(entry)

    def record_lesson(self, lesson: dict) -> None:
        entry = {
            "type": "lesson",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "pattern": lesson.get("pattern"),
            "confidence": lesson.get("confidence"),
            "sample_size": lesson.get("sample_size"),
            "description": lesson.get("description"),
        }
        self._append(entry)

    def get_all_predictions(self) -> list:
        return self._load_type("prediction")

    def get_all_outcomes(self) -> list:
        return self._load_type("outcome")

    def get_all_lessons(self) -> list:
        return self._load_type("lesson")

    def compute_calibration(self) -> dict:
        predictions = self.get_all_predictions()
        outcomes = self.get_all_outcomes()
        if not predictions or not outcomes:
            return {"status": "insufficient_data"}

        correct = sum(1 for item in outcomes if item.get("was_correct"))
        false_alarms = sum(1 for item in outcomes if item.get("was_false_alarm"))
        misses = sum(1 for item in outcomes if item.get("was_miss"))

        return {
            "total_predictions": len(predictions),
            "total_outcomes": len(outcomes),
            "correct": correct,
            "false_alarms": false_alarms,
            "misses": misses,
            "detection_rate": correct / max(correct + misses, 1),
            "false_alarm_rate": false_alarms / max(correct + false_alarms, 1),
        }

    def _append(self, entry: dict) -> None:
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")

    def _load_type(self, entry_type: str) -> list:
        if not self.path.exists():
            return []
        entries = []
        with open(self.path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if obj.get("type") == entry_type:
                    entries.append(obj)
        return entries
