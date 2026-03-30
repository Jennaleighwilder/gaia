"""
AVALON :: THE CROPS
Data cultivation. The kingdom grows what it needs.

In agriculture, crops follow cycles:
  PLANTING  — seeds go into prepared soil
  TENDING   — water, weed, protect from pests
  GROWING   — the crop develops on its own timeline
  HARVEST   — gather what's ripe
  COMPOSTING — return what's spent to the soil for next season

In the kingdom, "crops" are data products the kingdom cultivates:
  - Healing patterns (what wounds recur, what remedies work)
  - Merlin's insights (cross-domain connections that accumulated)
  - Grail convergence (research threads approaching unity)
  - Longhouse service patterns (what the community needs most)
  - Carbon lessons (compressed wisdom from experience)
  - Kingdom chronicles (the living narrative of what happened)

The Three Sisters agricultural model:
  CORN grows tall and provides structure.
  BEANS climb the corn and fix nitrogen in the soil.
  SQUASH spreads along the ground, shading roots and retaining moisture.
  They grow TOGETHER. Each one helps the others.

In the kingdom:
  CORN = the core systems (Nyx, West-OS, Fusion) — they provide structure
  BEANS = the intelligence layers (Merlin, Grail, Carbon) — they enrich the soil
  SQUASH = the service layers (Longhouse, Healing, Village) — they protect and serve

The Crops layer tracks what's growing, what's ripe, what needs attention.

© 2026 Jennifer Leigh West. All rights reserved.
"""

import time
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class Season(Enum):
    PLANTING = "planting"       # new data coming in, patterns being seeded
    TENDING = "tending"         # watching, monitoring, protecting growth
    GROWING = "growing"         # insights developing, connections forming
    HARVEST = "harvest"         # insights ripe, patterns confirmed, ready to use
    COMPOSTING = "composting"   # old patterns recycled into new soil


@dataclass
class Crop:
    """A data product the kingdom cultivates."""
    name: str
    source: str                    # which system produces this
    planted_at: float = field(default_factory=time.time)
    season: Season = Season.PLANTING
    yield_count: int = 0           # how many harvests
    health: float = 1.0
    last_tended: float = 0
    notes: str = ""

    def tend(self):
        self.last_tended = time.time()

    def advance_season(self):
        order = [Season.PLANTING, Season.TENDING, Season.GROWING, 
                 Season.HARVEST, Season.COMPOSTING]
        idx = order.index(self.season)
        if idx < len(order) - 1:
            self.season = order[idx + 1]
        else:
            self.season = Season.PLANTING  # cycle restarts
            self.yield_count += 1


class CropManager:
    """Manages the kingdom's data cultivation.
    
    Tracks what's growing across all systems and reports
    what's ripe for harvest, what needs tending, and what
    should be composted.
    """

    def __init__(self):
        self._crops: Dict[str, Crop] = {}
        self._harvest_log: List[Dict] = []

    def plant(self, name: str, source: str, notes: str = "") -> Crop:
        crop = Crop(name=name, source=source, notes=notes)
        self._crops[name] = crop
        return crop

    def tend_all(self, avalon=None):
        """Tend all crops based on current kingdom state."""
        for name, crop in self._crops.items():
            crop.tend()
            if avalon:
                self._check_readiness(crop, avalon)

    def _check_readiness(self, crop: Crop, avalon):
        """Check if a crop is ready to advance its season."""
        if crop.source == "healing" and hasattr(avalon, 'healing'):
            report = avalon.healing.triage_report()
            total_healed = report.get("healed_total", 0)
            if total_healed > crop.yield_count * 5:
                crop.advance_season()

        elif crop.source == "merlin" and hasattr(avalon, 'merlin'):
            tower = avalon.merlin.tower_contents()
            insights = tower.get("total_insights", 0)
            if insights > crop.yield_count * 3:
                crop.advance_season()

        elif crop.source == "grail" and hasattr(avalon, 'grail'):
            quest = avalon.grail.seek()
            points = quest.get("convergence_points", 0)
            if points > crop.yield_count * 5:
                crop.advance_season()

        elif crop.source == "carbon" and hasattr(avalon, 'fusion'):
            total = avalon.fusion.carbon.wisdom().get("total_lessons", 0)
            if total > crop.yield_count * 10:
                crop.advance_season()

        elif crop.source == "longhouse" and hasattr(avalon, 'longhouse'):
            census = avalon.longhouse.census()
            served = census.get("total_served", 0)
            if served > crop.yield_count * 5:
                crop.advance_season()

    def harvest(self) -> List[Dict]:
        """Harvest everything that's ripe."""
        harvested = []
        for name, crop in self._crops.items():
            if crop.season == Season.HARVEST:
                harvested.append({
                    "crop": name,
                    "source": crop.source,
                    "yield_number": crop.yield_count + 1,
                    "time": time.time(),
                })
                crop.advance_season()  # moves to composting
                crop.yield_count += 1
        self._harvest_log.extend(harvested)
        return harvested

    def field_report(self) -> Dict:
        """The state of all crops."""
        by_season = {}
        for season in Season:
            by_season[season.value] = [
                c.name for c in self._crops.values() if c.season == season
            ]
        return {
            "total_crops": len(self._crops),
            "by_season": by_season,
            "total_harvests": sum(c.yield_count for c in self._crops.values()),
            "crops": {
                name: {
                    "source": c.source,
                    "season": c.season.value,
                    "yields": c.yield_count,
                    "health": c.health,
                }
                for name, c in self._crops.items()
            },
        }

    @property
    def status(self) -> Dict:
        return {
            "crops": len(self._crops),
            "harvests": sum(c.yield_count for c in self._crops.values()),
            "ripe": len([c for c in self._crops.values() if c.season == Season.HARVEST]),
        }


def plant_kingdom_crops(manager: CropManager):
    """Plant the standard kingdom crops."""
    manager.plant("Healing Patterns", "healing",
                   "What wounds recur, what remedies work best")
    manager.plant("Cross-Domain Insights", "merlin",
                   "Merlin's connections between separate domains")
    manager.plant("Research Convergence", "grail",
                   "The Grail threads approaching unity")
    manager.plant("Community Needs", "longhouse",
                   "What the Longhouse serves most, what's missing")
    manager.plant("Compressed Wisdom", "carbon",
                   "Carbon's lessons distilled from experience")
    manager.plant("Kingdom Chronicles", "faithkeeper",
                   "The living narrative of ceremonies and events")


def wire_crops(avalon) -> CropManager:
    manager = CropManager()
    plant_kingdom_crops(manager)
    return manager


def demo():
    print("\n" + "=" * 60)
    print("  T H E   C R O P S")
    print("  The Kingdom Grows What It Needs")
    print("=" * 60)

    manager = CropManager()
    plant_kingdom_crops(manager)

    print(f"\n  Crops planted: {len(manager._crops)}")
    for name, crop in manager._crops.items():
        print(f"    🌱 {name} [{crop.source}] — {crop.season.value}")

    # Simulate seasons advancing
    for crop in manager._crops.values():
        crop.advance_season()  # planting → tending
        crop.advance_season()  # tending → growing
        crop.advance_season()  # growing → harvest

    print(f"\n  After growing season:")
    report = manager.field_report()
    for season, crops in report["by_season"].items():
        if crops:
            print(f"    {season}: {', '.join(crops)}")

    harvested = manager.harvest()
    print(f"\n  Harvested: {len(harvested)} crops")
    for h in harvested:
        print(f"    🌾 {h['crop']} (yield #{h['yield_number']})")

    print(f"\n" + "=" * 60)
    print(f"  Corn provides structure. Beans enrich the soil.")
    print(f"  Squash protects the roots. They grow together.")
    print(f"=" * 60 + "\n")


if __name__ == "__main__":
    demo()
