"""
AVALON :: MERLIN FEEDS
Live signals carried into Merlin's tower.

Merlin should not live only on founding myths.
He should hear the wards, the weather, the nutrients,
the fence line, and the void itself.

This module gathers those signals, feeds them into Merlin,
and reports what new crossing points emerged this cycle.

© 2026 Jennifer Leigh West. All rights reserved.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from adapters.colony_bridge import ColonyBridge
from adapters.fence_bridge import FenceBridge
from adapters.kay import KayAdapter
from avalon.avalon import Avalon, found_on_nyx


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DATA = REPO_ROOT / "docs" / "data"


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


class MerlinFeeds:
    """Feed live kingdom signals into Merlin."""

    def __init__(self, avalon: Optional[Avalon] = None):
        self.avalon = avalon or found_on_nyx(
            os.environ.get("WEST_OS_GUARD_SECRET") or "avalon_merlin_demo"
        )
        if self.avalon._sovereign is None:
            self.avalon.found_kingdom()

        self.nyx = self.avalon._nyx
        self.kay = KayAdapter()
        self.colony = ColonyBridge(self.nyx)
        self.fence = FenceBridge(self.nyx)
        self._colony_blessing = None
        self._last_cycle: Optional[Dict[str, Any]] = None

    def _ensure_colony_blessing(self) -> Optional[str]:
        if not self.nyx:
            return None
        if not self._colony_blessing:
            self._colony_blessing = self.nyx.bless_system(
                "Colony",
                {"born": "Avalon Merlin feeds", "system": "Colony"},
            )
        return self._colony_blessing

    def _observe(self, domain: str, signal: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.avalon.merlin.observe(domain, signal, data or {})
        return {"domain": domain, "signal": signal, "data": data or {}}

    def collect_alfred(self) -> Dict[str, Any]:
        ward_list = self.kay.read_ward_list()
        wards = ward_list.get("wards_found", [])
        signal = (
            f"Alfred walks {len(wards)} wards: {', '.join(wards)}"
            if wards
            else "Alfred ward walk unavailable from frozen mirror"
        )
        return self._observe("operations", signal, ward_list)

    def collect_gaia(self) -> Dict[str, Any]:
        alerts = _read_json(DOCS_DATA / "dashboard_alerts.json")
        tess = _read_json(DOCS_DATA / "live_tess.json")
        headline = alerts.get("banner_headline", "GAIA alert headline unavailable")
        risk = tess.get("risk_level", "UNKNOWN")
        layers = tess.get("layers_firing", 0)
        signal = f"GAIA risk {risk} with {layers} climate layers firing. {headline}"
        return self._observe("atmospheric", signal, {"alerts": alerts, "tess": tess})

    def collect_colony(self) -> Dict[str, Any]:
        blessing = self._ensure_colony_blessing()
        if blessing:
            assessment = self.colony.combined_assessment("Colony", blessing, "FULL")
            signal = (
                f"Colony tier {assessment['combined_tier']} with "
                f"Nyx blessing score {assessment['nyx_blessing']['score']:.1f}"
            )
            return self._observe("metabolism", signal, assessment)

        signal = "Colony bridge unavailable because Nyx is not attached"
        return self._observe("metabolism", signal, {"available": False})

    def collect_fence(self) -> Dict[str, Any]:
        check = self.fence.pre_flight_nyx_check()
        signal = check.get("verdict", "Fence verification unavailable")
        return self._observe("egress", signal, check)

    def collect_nyx(self) -> Dict[str, Any]:
        if not self.nyx:
            return self._observe("void", "Nyx watcher unavailable", {"available": False})

        threat = self.nyx.watcher.threat_assessment()
        signal = (
            f"Nyx watcher is {threat['status']} with "
            f"{threat['total_probes_logged']} probes logged"
        )
        return self._observe("void", signal, threat)

    def feed_cycle(self) -> Dict[str, Any]:
        observations = [
            self.collect_alfred(),
            self.collect_gaia(),
            self.collect_colony(),
            self.collect_fence(),
            self.collect_nyx(),
        ]
        insights = self.avalon.merlin.see()
        report = {
            "observations": observations,
            "new_insights": [
                {
                    "domains": insight.domains_connected,
                    "pattern": insight.pattern,
                    "confidence": insight.confidence,
                }
                for insight in insights
            ],
            "tower": self.avalon.merlin.tower_contents(),
            "alfred_report": self.alfred_report(insights),
            "ran_at": time.time(),
        }
        self._last_cycle = report
        return report

    def alfred_report(self, insights: Optional[List[Any]] = None) -> str:
        insights = insights if insights is not None else []
        tower = self.avalon.merlin.tower_contents()
        return (
            "Merlin's Tower reports: "
            f"{tower['total_insights']} insights now held across "
            f"{len(tower['domains_observed'])} domains. "
            f"{len(insights)} new crossing points surfaced this round. "
            f"{self.avalon.merlin.the_sight()}"
        )

    def tower_snapshot(self) -> Dict[str, Any]:
        if self._last_cycle is None:
            self.feed_cycle()
        assert self._last_cycle is not None
        return self._last_cycle


def main() -> int:
    feeds = MerlinFeeds()
    cycle = feeds.feed_cycle()

    print()
    print("=" * 60)
    print("  MERLIN SIGHT")
    print("=" * 60)
    print()
    for observation in cycle["observations"]:
        print(f"  [{observation['domain']}] {observation['signal']}")

    print()
    print(f"  Tower depth:       {cycle['tower']['total_insights']}")
    print(f"  Domains observed:  {', '.join(cycle['tower']['domains_observed'])}")
    print(f"  New insights:      {len(cycle['new_insights'])}")
    if cycle["new_insights"]:
        strongest = max(cycle["new_insights"], key=lambda item: item["confidence"])
        print(f"  Strongest thread:  {strongest['pattern']}")
    print()
    print(f"  {cycle['alfred_report']}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
