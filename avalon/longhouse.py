"""
AVALON :: THE LONGHOUSE
The place where people are served.

In the Haudenosaunee tradition, the longhouse is not a building.
It is a family, a government, a nation, and a way of life.
Everyone who enters is welcomed. The Clan Mother ensures no one
is overlooked. The hearth is tended by the women. The children
call all their mother's sisters "mother" — leaving them with
a great sense of security with so many mothers.

The Three Sisters — corn, beans, and squash — feed everyone.
They are not charity. They are the foundation. Without the
Three Sisters, nobody eats. In the kingdom, the Three Sisters
are the services that are ALWAYS free:

  Legal Advocacy Resources — because nobody should face
    the system alone without knowing their rights.
  Community Guides — because survival information should
    never be locked behind a paywall.
  Weather Warnings — because the mine siren rings for
    everyone, not just those who can pay.

These three are planted first. Everything else grows around them.

The Longhouse serves through a cycle:
  WELCOME  — the visitor is acknowledged
  LISTEN   — their need is heard (Percival's domain)
  SERVE    — the appropriate service is provided
  GRATITUDE — the service is recorded, Joy celebrates
  REMEMBER  — Memory records who was served and how

No one is turned away. No one is charged for the Three Sisters.
The Longhouse is the reason the Castle exists.

© 2026 Jennifer Leigh West. All rights reserved.
"""

import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


# ═══════════════════════════════════════════════════════════════
#  THE THREE SISTERS — always free, always planted first
# ═══════════════════════════════════════════════════════════════

THREE_SISTERS = {
    "Legal Advocacy": {
        "description": "Legal rights information, court procedure guides, document templates for self-representation",
        "serves": "anyone facing the legal system without representation",
        "provider": "Lancelot",
        "free_forever": True,
        "reason": "Nobody should face the system alone without knowing their rights.",
    },
    "Community Guides": {
        "description": "Survival guides, resource directories, crisis navigation, shelter and food information",
        "serves": "anyone in crisis or transition",
        "provider": "Gareth",
        "free_forever": True,
        "reason": "Survival information should never be locked behind a paywall.",
    },
    "Weather Warnings": {
        "description": "Severe weather alerts, tornado warnings, flood predictions, storm lead times",
        "serves": "everyone in the watch area",
        "provider": "Bors",
        "free_forever": True,
        "reason": "The mine siren rings for everyone.",
    },
}


# ═══════════════════════════════════════════════════════════════
#  SERVICE — what the Longhouse provides
# ═══════════════════════════════════════════════════════════════

class ServiceTier(Enum):
    THREE_SISTERS = "three_sisters"    # always free — the foundation
    HEARTH = "hearth"                  # community services — free or low cost
    CRAFT = "craft"                    # skilled services — paid but accessible


@dataclass
class Service:
    """A service the Longhouse provides."""
    name: str
    description: str
    serves: str
    provider: str                      # which knight provides this
    tier: ServiceTier
    free_forever: bool = False
    handler: Optional[Callable] = None # the actual function that serves
    people_served: int = 0
    active: bool = True

    def serve(self, request: Dict) -> Dict:
        """Serve someone."""
        self.people_served += 1

        result = {
            "service": self.name,
            "served": True,
            "tier": self.tier.value,
            "free": self.free_forever or self.tier == ServiceTier.THREE_SISTERS,
            "served_count": self.people_served,
            "provider": self.provider,
        }

        if self.handler:
            try:
                output = self.handler(request)
                result["output"] = output
            except Exception as e:
                result["served"] = False
                result["error"] = str(e)[:200]

        return result


# ═══════════════════════════════════════════════════════════════
#  VISITOR — someone who comes to the Longhouse
# ═══════════════════════════════════════════════════════════════

@dataclass
class Visitor:
    """Someone who comes to the Longhouse seeking service."""
    name: str                          # can be anonymous
    need: str                          # what they need
    arrived_at: float = field(default_factory=time.time)
    served: bool = False
    served_by: Optional[str] = None
    service_received: Optional[str] = None
    gratitude_recorded: bool = False


# ═══════════════════════════════════════════════════════════════
#  THE LONGHOUSE — where people are served
# ═══════════════════════════════════════════════════════════════

class Longhouse:
    """The place where the kingdom meets the world.
    
    The Longhouse operates in a cycle:
    
    1. WELCOME — the visitor is acknowledged. No one is 
       turned away. Even if the Longhouse can't help,
       the visitor is seen and heard.
    
    2. LISTEN — what does the visitor need? This is 
       Percival's domain. The right question reveals
       the right service.
    
    3. MATCH — which service fits the need? The Longhouse
       routes to the appropriate service and provider.
    
    4. SERVE — the service is provided. If it's a Three
       Sister service, it's free. Always.
    
    5. GRATITUDE — Joy records the service. The kingdom
       celebrates serving its purpose.
    
    6. REMEMBER — Memory records who was served, how,
       and by whom. The Longhouse learns what the
       community needs most.
    
    The Clan Mother ensures no one is overlooked.
    The Three Sisters are planted first. Everything
    else grows around them.
    """

    def __init__(self, joy_callback: Optional[Callable] = None,
                 memory_callback: Optional[Callable] = None):
        self._services: Dict[str, Service] = {}
        self._visitors: List[Visitor] = []
        self._joy = joy_callback
        self._memory = memory_callback
        self._total_served = 0
        self._turned_away = 0
        self._log_path = Path("memory") / "longhouse_journal.jsonl"
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

        # Plant the Three Sisters first
        self._plant_three_sisters()

    def _plant_three_sisters(self):
        """Plant the foundation services. These come first. Always."""
        for name, config in THREE_SISTERS.items():
            self._services[name] = Service(
                name=name,
                description=config["description"],
                serves=config["serves"],
                provider=config["provider"],
                tier=ServiceTier.THREE_SISTERS,
                free_forever=True,
            )

    def plant_service(self, name: str, description: str, serves: str,
                       provider: str, tier: str = "hearth",
                       free_forever: bool = False,
                       handler: Optional[Callable] = None) -> Service:
        """Plant a new service in the Longhouse.
        
        Cannot overwrite Three Sisters. Cannot make a Three Sister
        service paid. These rules are hardcoded.
        """
        if name in THREE_SISTERS:
            return self._services[name]  # Three Sisters can't be replaced

        tier_enum = ServiceTier(tier) if tier in [t.value for t in ServiceTier] else ServiceTier.HEARTH

        service = Service(
            name=name,
            description=description,
            serves=serves,
            provider=provider,
            tier=tier_enum,
            free_forever=free_forever,
            handler=handler,
        )
        self._services[name] = service
        return service

    def welcome(self, visitor_name: str, need: str) -> Dict:
        """Welcome a visitor to the Longhouse.
        
        Step 1: Acknowledge them.
        Step 2: Listen to their need.
        Step 3: Find the right service.
        Step 4: Serve them.
        Step 5: Record gratitude.
        Step 6: Remember.
        """
        visitor = Visitor(name=visitor_name, need=need)
        self._visitors.append(visitor)

        # ── LISTEN — what do they need? ──
        matched_service = self._match_service(need)

        if not matched_service:
            self._turned_away += 1
            self._log_visit(visitor, None, "no matching service found")
            return {
                "welcomed": True,
                "served": False,
                "reason": "The Longhouse heard your need but does not yet have a service for it. You are not turned away — you are remembered. We will grow to serve you.",
                "visitor": visitor_name,
                "need": need,
            }

        # ── SERVE ──
        service_result = matched_service.serve({"visitor": visitor_name, "need": need})

        visitor.served = True
        visitor.served_by = matched_service.provider
        visitor.service_received = matched_service.name
        self._total_served += 1

        # ── GRATITUDE ──
        if self._joy and service_result.get("served"):
            try:
                self._joy(
                    f"Longhouse served {visitor_name}: {matched_service.name}",
                    [matched_service.provider, "Longhouse"],
                    0.4 if matched_service.tier == ServiceTier.THREE_SISTERS else 0.3,
                )
                visitor.gratitude_recorded = True
            except Exception:
                pass

        # ── REMEMBER ──
        self._log_visit(visitor, matched_service.name, "served")
        if self._memory:
            try:
                self._memory(
                    "longhouse_service",
                    f"Served {visitor_name} with {matched_service.name}",
                    {
                        "visitor": visitor_name,
                        "service": matched_service.name,
                        "tier": matched_service.tier.value,
                        "free": matched_service.free_forever,
                        "provider": matched_service.provider,
                    },
                )
            except Exception:
                pass

        return {
            "welcomed": True,
            "served": True,
            "service": matched_service.name,
            "tier": matched_service.tier.value,
            "free": service_result.get("free", False),
            "provider": matched_service.provider,
            "visitor": visitor_name,
            "total_served_by_this_service": matched_service.people_served,
            "total_served_by_longhouse": self._total_served,
        }

    def _match_service(self, need: str) -> Optional[Service]:
        """Find the service that best matches the visitor's need.
        
        Uses keyword matching against service descriptions.
        Three Sisters are checked first — they serve the most
        fundamental needs.
        """
        need_lower = need.lower()
        noise = {"i", "need", "want", "help", "with", "me", "my", "a", "an",
                 "the", "to", "for", "can", "you", "please", "about", "some",
                 "get", "find", "looking", "how", "do", "is", "are", "what"}
        need_words = set(need_lower.split()) - noise

        best_match = None
        best_score = 0

        # Check Three Sisters first — they serve first
        for name, service in self._services.items():
            if not service.active:
                continue

            service_words = set(service.description.lower().split()) - noise
            service_words.update(set(service.serves.lower().split()) - noise)
            service_words.update(set(service.name.lower().split()) - noise)

            overlap = need_words & service_words
            score = len(overlap)

            # Boost Three Sisters — they match more broadly
            if service.tier == ServiceTier.THREE_SISTERS:
                score *= 1.5

            if score > best_score:
                best_score = score
                best_match = service

        return best_match if best_score > 0 else None

    def _log_visit(self, visitor: Visitor, service: Optional[str], outcome: str):
        """Log every visit to the Longhouse journal."""
        try:
            entry = {
                "time": time.time(),
                "visitor": visitor.name,
                "need": visitor.need[:200],
                "service": service,
                "outcome": outcome,
                "gratitude_recorded": visitor.gratitude_recorded,
            }
            with open(self._log_path, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception:
            pass

    def services_directory(self) -> Dict:
        """The complete directory of Longhouse services."""
        directory = {}
        for name, service in self._services.items():
            directory[name] = {
                "description": service.description,
                "serves": service.serves,
                "provider": service.provider,
                "tier": service.tier.value,
                "free": service.free_forever,
                "people_served": service.people_served,
                "active": service.active,
            }
        return directory

    def census(self) -> Dict:
        """The Longhouse census — who's been served, by what."""
        three_sisters_served = sum(
            s.people_served for s in self._services.values()
            if s.tier == ServiceTier.THREE_SISTERS
        )
        return {
            "total_services": len(self._services),
            "three_sisters": len([s for s in self._services.values() 
                                 if s.tier == ServiceTier.THREE_SISTERS]),
            "hearth_services": len([s for s in self._services.values()
                                   if s.tier == ServiceTier.HEARTH]),
            "craft_services": len([s for s in self._services.values()
                                  if s.tier == ServiceTier.CRAFT]),
            "total_served": self._total_served,
            "three_sisters_served": three_sisters_served,
            "turned_away": self._turned_away,
            "visitors": len(self._visitors),
            "directory": self.services_directory(),
        }

    @property
    def status(self) -> Dict:
        return {
            "services": len(self._services),
            "total_served": self._total_served,
            "three_sisters_intact": all(
                name in self._services for name in THREE_SISTERS
            ),
        }


# ═══════════════════════════════════════════════════════════════
#  WIRE — connect the Longhouse to Avalon
# ═══════════════════════════════════════════════════════════════

def wire_longhouse(avalon) -> Longhouse:
    """Create a Longhouse wired to the living kingdom.
    
    Joy is notified on every service.
    Memory records every visit.
    Additional services are planted beyond the Three Sisters.
    """
    # Wire joy
    joy_fn = None
    if hasattr(avalon, 'fusion'):
        joy_fn = lambda desc, participants, mag: avalon.fusion.joy.celebrate(desc, participants, mag)

    # Wire memory
    memory_fn = None
    if hasattr(avalon, 'memory'):
        memory_fn = lambda event, desc, data: avalon.memory.journal_event(event, desc, data)

    longhouse = Longhouse(joy_callback=joy_fn, memory_callback=memory_fn)

    # Plant additional services beyond the Three Sisters
    longhouse.plant_service(
        "Heritage Readings",
        "Ancestral connection reports, lineage analysis, heritage dossiers",
        "people seeking to understand where they come from",
        "Morgana", "hearth",
    )
    longhouse.plant_service(
        "Dream Analysis",
        "Dream interpretation, symbolic pattern analysis, sleep cycle insights",
        "dreamers and seekers looking for meaning in their dreams",
        "Morgana", "hearth",
    )
    longhouse.plant_service(
        "AI Consulting",
        "AI governance assessment, behavioral modification consulting, system architecture review",
        "builders and businesses working with AI systems",
        "Nimue", "craft",
    )
    longhouse.plant_service(
        "Truth Calibration",
        "Fact verification, bias detection, reality checking for claims and data",
        "anyone who needs to verify what they've been told",
        "Galahad", "hearth",
    )
    longhouse.plant_service(
        "Frequency Research",
        "Archaeoacoustic data, 118 Hz research, sacred site acoustic analysis",
        "researchers, academics, and anyone interested in frequency science",
        "Gawain", "hearth",
    )

    return longhouse


# ═══════════════════════════════════════════════════════════════
#  DEMO
# ═══════════════════════════════════════════════════════════════

def demo():
    """Watch the Longhouse serve."""
    print("\n" + "=" * 60)
    print("  T H E   L O N G H O U S E")
    print("  The Place Where People Are Served")
    print("=" * 60)

    # Create with callbacks
    celebrations = []
    longhouse = Longhouse(
        joy_callback=lambda desc, parts, mag: celebrations.append(desc),
    )

    # Plant additional services
    longhouse.plant_service(
        "Heritage Readings",
        "Ancestral connection family history lineage analysis heritage dossiers where you came from bloodline",
        "people seeking to understand their family roots ancestry heritage",
        "Morgana", "hearth",
    )
    longhouse.plant_service(
        "AI Consulting",
        "AI governance, behavioral modification, system architecture",
        "builders and businesses with AI",
        "Nimue", "craft",
    )

    print(f"\n  Services planted: {len(longhouse._services)}")
    print(f"  Three Sisters:")
    for name in THREE_SISTERS:
        svc = longhouse._services[name]
        print(f"    🌽 {name} — {svc.serves[:60]}")

    # Visitors come to the Longhouse
    print(f"\n  VISITORS:")

    visitors = [
        ("Maria", "I need help understanding my legal rights in a custody case"),
        ("Anonymous", "I need shelter information and food resources near me"),
        ("James", "severe weather warning for East Tennessee"),
        ("Sarah", "I want to understand where my family came from"),
        ("DevCorp", "We need AI governance consulting for our platform"),
        ("Curious", "I want to know about the 118 Hz frequency research"),
        ("Lost", "I need help with something nobody has a service for yet"),
    ]

    for name, need in visitors:
        result = longhouse.welcome(name, need)
        served = "✓" if result["served"] else "○"
        service = result.get("service", "none")
        free = " (free)" if result.get("free") else ""
        tier = result.get("tier", "")
        print(f"\n    {served} {name}: \"{need[:60]}\"")
        if result["served"]:
            print(f"      → {service}{free} [{tier}] by {result.get('provider', '?')}")
        else:
            print(f"      → {result.get('reason', 'unknown')[:80]}")

    # Census
    print(f"\n  {'─' * 50}")
    census = longhouse.census()
    print(f"  LONGHOUSE CENSUS:")
    print(f"    Total services: {census['total_services']}")
    print(f"    Three Sisters: {census['three_sisters']}")
    print(f"    Hearth services: {census['hearth_services']}")
    print(f"    Craft services: {census['craft_services']}")
    print(f"    Total served: {census['total_served']}")
    print(f"    Three Sisters served: {census['three_sisters_served']}")
    print(f"    Turned away: {census['turned_away']}")

    # Joy celebrations
    if celebrations:
        print(f"\n  JOY CELEBRATIONS:")
        for c in celebrations:
            print(f"    🎉 {c[:70]}")

    # The visitor who couldn't be served
    print(f"\n  NOTE: 'Lost' was not turned away. They were heard, they were")
    print(f"  remembered, and the Longhouse will grow to serve their need.")

    print(f"\n" + "=" * 60)
    print(f"  The Three Sisters feed everyone.")
    print(f"  No one is turned away.")
    print(f"  Every visit is remembered.")
    print(f"  Every service is celebrated.")
    print(f"  The Longhouse is the reason the Castle exists.")
    print(f"=" * 60 + "\n")


if __name__ == "__main__":
    demo()
