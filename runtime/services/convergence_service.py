#!/usr/bin/env python3
"""
GAIA Convergence Detector — Watches the bus for multi-engine agreement.

When 3+ independent services flag the same region inside a time window,
GAIA emits a convergence alert.
"""

import os
import sys
import time
from datetime import datetime, timezone
from collections import defaultdict
from typing import Dict, List, Set

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.base import GaiaService
from bus import init_bus, replay_with_seq, count_events


# Event types that indicate a service flagged something
SIGNAL_TYPES = {
    "pressure_alert",
    "thermal_alert",
    "moisture_alert",
    "shear_alert",
    "instability_alert",
    "historical_analog_alert",
    "saddle_point_detected",
    "infrastructure_alert",
    "environmental_alert",
    "oscillation_alert",
    "sensor_mesh_alert",
}

# Minimum instability to count as a "flag"
MIN_INSTABILITY = 0.3

# Time window for convergence (seconds)
CONVERGENCE_WINDOW = 300  # 5 minutes

# Minimum number of independent services that must agree
MIN_SERVICES = 3

# Cooldown: don't re-alert on the same entity within this window (seconds)
ALERT_COOLDOWN = 600  # 10 minutes

# Contradiction window: no convergence if a service contradicts within this (seconds)
CONTRADICTION_WINDOW = 60

# Instability below this = "contradiction" (service says "all clear")
CONTRADICTION_THRESHOLD = 0.2


class ConvergenceService(GaiaService):

    def __init__(self):
        super().__init__("convergence_detector")
        self.signals: Dict[str, List[dict]] = defaultdict(list)
        self.last_alerts: Dict[str, float] = {}

    def subscribed_event_types(self) -> list:
        return list(SIGNAL_TYPES)

    def handle_event(self, event):
        instability = (event.metrics or {}).get("instability", 0.0)
        if instability < MIN_INSTABILITY:
            return
        if event.source == "convergence_detector":
            return
        payload = event.payload or {}
        context = event.context or {}
        region = (
            context.get("region")
            or payload.get("region")
            or context.get("county")
            or payload.get("county")
        )
        if not region:
            return
        now = time.time()
        self.signals[region].append({
            "timestamp": now,
            "source": event.source,
            "event_type": event.event_type,
            "instability": instability,
            "event_id": getattr(event, "event_id", ""),
        })
        cutoff = now - CONVERGENCE_WINDOW
        self.signals[region] = [
            s for s in self.signals[region]
            if s["timestamp"] >= cutoff
        ]
        self._check_convergence(region, now)

    def _check_convergence(self, region: str, now: float):
        """Check if enough independent services have flagged this region."""
        signals = self.signals[region]
        if not signals:
            return
        unique_sources: Set[str] = {s["source"] for s in signals}
        if len(unique_sources) < MIN_SERVICES:
            return
        last_alert = self.last_alerts.get(region, 0)
        if now - last_alert < ALERT_COOLDOWN:
            return
        self.last_alerts[region] = now
        total_weight = 0
        weighted_sum = 0
        for s in signals:
            age = now - s["timestamp"]
            weight = 1.0 / (1.0 + age / 60.0)
            weighted_sum += s["instability"] * weight
            total_weight += weight

        combined_instability = weighted_sum / total_weight if total_weight > 0 else 0.0

        contributing = [
            {
                "source": s["source"],
                "event_type": s["event_type"],
                "instability": s["instability"],
                "seconds_ago": round(now - s["timestamp"], 1),
            }
            for s in signals
        ]

        self.log.warning(
            f"CONVERGENCE on {region}: "
            f"{len(unique_sources)} services agree, "
            f"combined instability={combined_instability:.2f}"
        )
        self.publish(
            event_type="convergence_alert",
            payload={
                "region": region,
                "services_count": len(unique_sources),
                "unique_services": sorted(unique_sources),
                "signal_count": len(signals),
                "combined_instability": round(combined_instability, 4),
                "contributing_signals": contributing,
                "window_seconds": CONVERGENCE_WINDOW,
                "detection_time": datetime.now(timezone.utc).isoformat(),
            },
            context={"region": region, "convergence": "true"},
            metrics={"instability": min(combined_instability * 1.2, 1.0)},
        )

    def run_forever(self, poll_interval: float = 2.0):
        """Override: start from current bus position — only process new events."""
        init_bus()
        last_seq = count_events()
        self.log.info(f"Starting from bus offset {last_seq}. Subscribed to: {self.subscribed_event_types()}")
        target_types = set(self.subscribed_event_types())

        while True:
            try:
                for seq, event in replay_with_seq(from_seq=last_seq, limit=100):
                    if event.event_type in target_types:
                        try:
                            self.handle_event(event)
                        except Exception as e:
                            self.log.error(f"Error: {e}", exc_info=True)
                    last_seq = seq
                time.sleep(poll_interval)
            except KeyboardInterrupt:
                self.log.info("Shutting down.")
                break
            except Exception as e:
                self.log.error(f"Poll error: {e}")
                time.sleep(5)


if __name__ == "__main__":
    ConvergenceService().run_forever()
