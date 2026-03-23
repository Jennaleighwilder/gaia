"""
GAIA Service — Base class for all reactive components.
Pattern: subscribe to bus event types -> handle -> publish results back to bus.
"""

import os
import sys
import time
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any

# Ensure bus is importable from services/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bus import init_bus, publish_simple, replay_with_seq
from bus.normalize import normalize_instability


class GaiaService(ABC):

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.log = logging.getLogger(service_name)
        logging.basicConfig(
            level=logging.INFO,
            format=f"%(asctime)s [{service_name}] %(message)s",
        )

    @abstractmethod
    def subscribed_event_types(self) -> List[str]:
        """Event types this service listens to."""
        pass

    @abstractmethod
    def handle_event(self, event) -> None:
        """Process an event. Publish results via self.publish()."""
        pass

    def publish(self, event_type: str, payload: Dict[str, Any],
                context: Optional[Dict[str, str]] = None,
                metrics: Optional[Dict[str, float]] = None) -> int:
        return publish_simple(
            source=self.service_name,
            event_type=event_type,
            payload=payload,
            context=context or {},
            metrics=metrics,
        )

    def run_forever(self, poll_interval: float = 2.0):
        """Start and block. Poll bus for subscribed event types."""
        init_bus()
        self.log.info(f"Starting. Subscribed to: {self.subscribed_event_types()}")
        last_seq = 0
        target_types = set(self.subscribed_event_types())

        while True:
            try:
                for seq, event in replay_with_seq(from_seq=last_seq, limit=50):
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
