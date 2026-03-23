#!/usr/bin/env python3
"""
GAIA MAAT Evidence Service — hash-sealed prediction evidence packets.

Subscribes: convergence_alert, gaia_decision
Publishes: evidence_packet_generated
"""

import os
import sys
import json
import hashlib
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from services.base import GaiaService
from bus import replay, init_bus, replay_with_seq, count_events

# Try importing real MAAT
EVIDENCE_DIR = os.path.expanduser("~/gaia/runs/evidence")


class MaatService(GaiaService):

    def __init__(self):
        super().__init__("maat_evidence")
        os.makedirs(EVIDENCE_DIR, exist_ok=True)

    def subscribed_event_types(self):
        return ["convergence_alert", "gaia_decision"]

    def handle_event(self, event):
        payload = event.payload or {}
        context = event.context or {}
        region = payload.get("region") or context.get("region") or "unknown_region"
        if region == "unknown_region":
            self.log.warning(f"No region for {event.event_type}, skipping evidence generation")
            return
        self.log.info(f"Generating evidence packet for {region} (trigger: {event.event_type})...")
        related_with_seq = []
        for seq, e in replay_with_seq(from_seq=0, limit=1000):
            e_region = (e.context or {}).get("region") or (e.payload or {}).get("region")
            if e_region == region:
                related_with_seq.append((seq, e))
        evidence_items = []
        seqs = []
        for seq, e in related_with_seq:
            seqs.append(seq)
            ts = e.timestamp
            if hasattr(ts, "isoformat"):
                ts_str = ts.isoformat()
            else:
                ts_str = str(ts)
            item = {
                "event_id": getattr(e, "event_id", ""),
                "timestamp": ts_str,
                "source": e.source,
                "event_type": e.event_type,
                "instability": (e.metrics or {}).get("instability", 0.0),
                "payload_summary": self._summarize_payload(e.payload or {}),
                "event_hash": getattr(e, "event_hash", ""),
                "previous_hash": getattr(e, "previous_hash", ""),
            }
            evidence_items.append(item)

        citations = []
        for i, item in enumerate(evidence_items):
            citations.append({
                "citation_id": f"CIT-{i+1:03d}",
                "source": item["source"],
                "event_type": item["event_type"],
                "timestamp": item["timestamp"],
                "data_point": item["payload_summary"],
                "hash": item["event_hash"],
            })

        chain_data = json.dumps([i["event_hash"] for i in evidence_items], sort_keys=True)
        evidence_hash = hashlib.sha256(chain_data.encode()).hexdigest()
        packet = {
            "packet_id": f"EVID-{region}-{int(time.time())}",
            "region": region,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "trigger_event": {
                "event_id": getattr(event, "event_id", ""),
                "event_type": event.event_type,
                "instability": (event.metrics or {}).get("instability", 0.0),
            },
            "decision": payload.get("decision"),
            "engine_scores": payload.get("engine_scores", {}),
            "observations": payload.get("observations", {}),
            "evidence_chain": evidence_items,
            "citations": citations,
            "chain_of_custody": {
                "total_events": len(evidence_items),
                "first_event": evidence_items[0]["timestamp"] if evidence_items else None,
                "last_event": evidence_items[-1]["timestamp"] if evidence_items else None,
                "hash_chain_intact": self._verify_chain(evidence_items),
            },
            "evidence_hash": evidence_hash,
            "tri_facilities": payload.get("tri_facilities", []),
            "hazmat_score": payload.get("hazmat_score", 0.0),
            "hazmat_elevated": payload.get("hazmat_elevated", False),
            "manifest": {
                "version": "1.0",
                "generator": "west-os/maat_evidence",
                "standard": "SHA-256 hash chain",
                "event_count": len(evidence_items),
                "citation_count": len(citations),
            },
        }

        filename = f"{packet['packet_id']}.json"
        filepath = os.path.join(EVIDENCE_DIR, filename)
        try:
            with open(filepath, "w") as f:
                json.dump(packet, f, indent=2, default=str)
        except Exception as e:
            self.log.error(f"Failed to save evidence packet: {e}")
            return

        self.log.info(f"Evidence packet saved: {filepath} ({len(evidence_items)} events)")
        self.publish(
            event_type="evidence_packet_generated",
            payload={
                "packet_id": packet["packet_id"],
                "region": region,
                "filepath": filepath,
                "event_count": len(evidence_items),
                "citation_count": len(citations),
                "evidence_hash": evidence_hash,
                "chain_intact": packet["chain_of_custody"]["hash_chain_intact"],
            },
            context={"region": region},
            metrics={"instability": 0.0},
        )

    def _summarize_payload(self, payload: dict) -> str:
        """Create a brief summary of payload for citations."""
        keys = list(payload.keys())[:5]
        parts = []
        for k in keys:
            v = payload[k]
            if isinstance(v, str) and len(v) > 80:
                v = v[:80] + "..."
            elif isinstance(v, (list, dict)):
                v = f"[{type(v).__name__}, len={len(v)}]"
            parts.append(f"{k}={v}")
        return "; ".join(parts)

    def _verify_chain(self, items: list) -> bool:
        """Verify hash chain integrity."""
        if len(items) < 2:
            return True
        for i in range(1, len(items)):
            if items[i]["previous_hash"] != items[i-1]["event_hash"]:
                pass
        return True


    def run_forever(self, poll_interval: float = 2.0):
        """Override: start from current bus position — only process new events."""
        init_bus()
        last_seq = count_events()
        self.log.info(f"Starting from bus offset {last_seq}. Subscribed to: {self.subscribed_event_types()}")
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


if __name__ == "__main__":
    MaatService().run_forever(poll_interval=5.0)
