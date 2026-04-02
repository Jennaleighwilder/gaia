"""
AVALON :: THE HEARTH
Town healer and farms. Where the community is tended.

The Apothecary heals SYSTEMS. The Hearth heals the COMMUNITY.
Broken service connections, unmet needs, gaps between what
the Longhouse offers and what people ask for.

The Farm is where Crops actually grow. Not the tracking of
crops (that's the CropManager) — the SOIL where they're
planted. The Farm monitors which services are healthy,
which are overworked, which are neglected.

In a real village:
  The healer tends the sick AND tends the garden.
  The garden feeds the village AND provides medicine.
  The healer knows which herbs grow where because she
  planted them. She knows which ones are running low
  because she uses them.

The Hearth combines:
  TOWN HEALER — monitors service health, visitor satisfaction,
    unmet needs, and service gaps. Prescribes new services
    when patterns emerge.
  FARM — monitors resource usage per service, identifies
    which services are starving (need more resources) and
    which are overfed (consuming without producing).

© 2026 Jennifer Leigh West. All rights reserved.
"""

import time
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class ServiceHealth(Enum):
    THRIVING = "thriving"     # serving well, good ratio of effort to impact
    GROWING = "growing"       # new, building up capacity
    STABLE = "stable"         # serving steadily, not growing
    WILTING = "wilting"       # fewer visitors, may need attention
    FALLOW = "fallow"         # resting, not actively serving


@dataclass
class ServicePlot:
    """A plot in the Farm where a service grows."""
    service_name: str
    planted_at: float = field(default_factory=time.time)
    health: ServiceHealth = ServiceHealth.GROWING
    visitors_served: int = 0
    resources_consumed: float = 0
    last_served: float = 0
    unmet_needs: List[str] = field(default_factory=list)

    @property
    def efficiency(self) -> float:
        """How efficiently does this service use resources?"""
        if self.resources_consumed == 0:
            return 1.0
        return min(1.0, self.visitors_served / max(self.resources_consumed, 1))


class Hearth:
    """The town healer and farm. Tends the community.
    
    The Hearth watches:
    - Which services are healthy
    - Which services have unmet needs (people asked for something they couldn't provide)
    - Which services are overworked or neglected
    - What NEW services the community needs based on patterns
    
    The Hearth prescribes:
    - New services when patterns of unmet need emerge
    - Rest for overworked services
    - Attention for neglected services
    - Composting for services nobody uses
    """

    def __init__(self):
        self._plots: Dict[str, ServicePlot] = {}
        self._unmet_log: List[Dict] = []
        self._prescriptions: List[Dict] = []

    def plant_plot(self, service_name: str) -> ServicePlot:
        """Plant a service plot in the farm."""
        plot = ServicePlot(service_name=service_name)
        self._plots[service_name] = plot
        return plot

    def record_service(self, service_name: str, visitor: str, served: bool,
                        need: str = ""):
        """Record a service event."""
        if service_name not in self._plots:
            self.plant_plot(service_name)

        plot = self._plots[service_name]
        if served:
            plot.visitors_served += 1
            plot.last_served = time.time()
            plot.resources_consumed += 1
        else:
            plot.unmet_needs.append(need)
            self._unmet_log.append({
                "time": time.time(),
                "service": service_name,
                "visitor": visitor,
                "need": need,
            })

    def record_unmet_need(self, visitor: str, need: str):
        """Record a need the Longhouse couldn't meet."""
        self._unmet_log.append({
            "time": time.time(),
            "service": None,
            "visitor": visitor,
            "need": need,
        })

    def diagnose(self) -> Dict:
        """Diagnose the community's health.
        
        Looks at service patterns and prescribes interventions.
        """
        now = time.time()

        thriving = []
        wilting = []
        fallow = []
        overworked = []

        for name, plot in self._plots.items():
            days_since_served = (now - plot.last_served) / 86400 if plot.last_served else 999
            days_since_planted = (now - plot.planted_at) / 86400

            if plot.visitors_served == 0 and days_since_planted < 30:
                plot.health = ServiceHealth.GROWING
            elif plot.visitors_served == 0 and days_since_planted > 90:
                plot.health = ServiceHealth.FALLOW
                fallow.append(name)
            elif plot.visitors_served > 10 and days_since_served < 7:
                plot.health = ServiceHealth.THRIVING
                thriving.append(name)
            elif plot.visitors_served > 0 and days_since_served < 30:
                plot.health = ServiceHealth.STABLE
            elif days_since_served > 90:
                plot.health = ServiceHealth.FALLOW
                fallow.append(name)
            elif days_since_served > 30:
                plot.health = ServiceHealth.WILTING
                wilting.append(name)

            if plot.visitors_served > 50 and plot.efficiency < 0.5:
                overworked.append(name)

        # Analyze unmet needs for patterns
        need_patterns = {}
        noise = {
            "need", "needs", "help", "please", "information", "info", "support",
            "resources", "resource", "with", "for", "the", "and", "that", "this",
            "have", "from",
        }
        for entry in self._unmet_log:
            need = entry["need"].lower()
            for word in need.split():
                if len(word) > 3 and word not in noise:
                    need_patterns[word] = need_patterns.get(word, 0) + 1

        recurring_needs = sorted(
            [(word, count) for word, count in need_patterns.items() if count >= 2],
            key=lambda x: x[1], reverse=True,
        )[:5]

        # Prescribe
        prescriptions = []
        for name in wilting:
            prescriptions.append({
                "service": name,
                "prescription": "attention",
                "note": f"{name} is wilting — hasn't served recently. Needs promotion or revision.",
            })
        for name in overworked:
            prescriptions.append({
                "service": name,
                "prescription": "rest",
                "note": f"{name} is overworked — high volume, low efficiency. Needs support.",
            })
        if recurring_needs:
            prescriptions.append({
                "service": "NEW SERVICE NEEDED",
                "prescription": "plant",
                "note": f"Recurring unmet needs: {', '.join(w for w, c in recurring_needs)}. Consider new service.",
                "patterns": recurring_needs,
            })

        self._prescriptions = prescriptions

        return {
            "total_plots": len(self._plots),
            "thriving": thriving,
            "wilting": wilting,
            "fallow": fallow,
            "overworked": overworked,
            "unmet_needs_total": len(self._unmet_log),
            "recurring_need_patterns": recurring_needs,
            "prescriptions": prescriptions,
        }

    def farm_report(self) -> Dict:
        """Full farm status."""
        return {
            "plots": {
                name: {
                    "health": plot.health.value,
                    "visitors_served": plot.visitors_served,
                    "efficiency": round(plot.efficiency, 2),
                    "unmet_needs": len(plot.unmet_needs),
                }
                for name, plot in self._plots.items()
            },
            "total_served": sum(p.visitors_served for p in self._plots.values()),
            "total_unmet": len(self._unmet_log),
        }

    @property
    def status(self) -> Dict:
        return {
            "plots": len(self._plots),
            "total_served": sum(p.visitors_served for p in self._plots.values()),
            "unmet_needs": len(self._unmet_log),
        }


def wire_hearth(avalon) -> Hearth:
    hearth = Hearth()
    # Plant plots for existing Longhouse services
    if hasattr(avalon, 'longhouse'):
        for name in avalon.longhouse._services:
            hearth.plant_plot(name)
    return hearth


def demo():
    print("\n" + "=" * 60)
    print("  T H E   H E A R T H")
    print("  Town Healer and Farm")
    print("=" * 60)

    hearth = Hearth()

    # Plant service plots
    for name in ["Legal Advocacy", "Weather Warnings", "Heritage Readings", "AI Consulting"]:
        hearth.plant_plot(name)

    # Simulate service activity
    for i in range(15):
        hearth.record_service("Legal Advocacy", f"visitor_{i}", True)
    for i in range(3):
        hearth.record_service("Weather Warnings", f"visitor_{i}", True)
    hearth.record_service("Heritage Readings", "Sarah", True)

    # Simulate unmet needs
    hearth.record_unmet_need("Alice", "I need help with childcare resources")
    hearth.record_unmet_need("Bob", "I need childcare information")
    hearth.record_unmet_need("Carol", "mental health support resources")

    # Diagnose
    diagnosis = hearth.diagnose()

    print(f"\n  DIAGNOSIS:")
    print(f"    Thriving: {', '.join(diagnosis['thriving']) or 'none'}")
    print(f"    Wilting: {', '.join(diagnosis['wilting']) or 'none'}")
    print(f"    Unmet needs: {diagnosis['unmet_needs_total']}")

    if diagnosis["recurring_need_patterns"]:
        print(f"\n    Recurring patterns in unmet needs:")
        for word, count in diagnosis["recurring_need_patterns"]:
            print(f"      '{word}' appeared {count} times")

    if diagnosis["prescriptions"]:
        print(f"\n    PRESCRIPTIONS:")
        for rx in diagnosis["prescriptions"]:
            print(f"      [{rx['prescription']}] {rx['note'][:70]}")

    print(f"\n  FARM:")
    report = hearth.farm_report()
    for name, data in report["plots"].items():
        print(f"    {name}: {data['health']} — served {data['visitors_served']}, efficiency {data['efficiency']}")

    print(f"\n" + "=" * 60)
    print(f"  The healer tends the sick AND tends the garden.")
    print(f"  The garden feeds the village AND provides medicine.")
    print(f"  What the community asks for, the farm learns to grow.")
    print(f"=" * 60 + "\n")


if __name__ == "__main__":
    demo()
