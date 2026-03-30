"""
AVALON :: THE COMMERCE
How the kingdom sustains itself.

Every civilization needs commerce — not greed, but EXCHANGE.
Value flows in, value flows out. Without commerce, the kingdom
consumes resources without replenishing them. The Longhouse
serves but doesn't sustain. Commerce is how Jennifer's work
converts to income so the kingdom can keep serving.

The oldest trade routes followed rivers. Goods moved where
water moved. The kingdom's trade routes follow DATA — value
moves where knowledge moves.

Commerce in the kingdom has THREE channels:

  THE MARKET (direct services for payment)
    Heritage readings, AI consulting, mystical reports,
    dream analysis, frequency research. These are the
    craft-tier Longhouse services with actual exchange.

  THE GUILD (intellectual property)
    The Mirror Protocol, the West Method, the MIRA Protocol,
    the Avalon architecture itself. These are licensed,
    copyrighted, or patented works that generate value
    through recognition and licensing.

  THE COMMONS (what's given freely and returns value indirectly)
    The Three Sisters services, open educational content,
    community guides. These build reputation, trust, and
    referrals. The commons FEEDS the market.

The Commerce layer tracks:
  - What's been exchanged and by whom
  - Which services generate the most value
  - Which free services lead to paid engagement
  - The kingdom's total economic health

© 2026 Jennifer Leigh West. All rights reserved.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class Channel(Enum):
    MARKET = "market"       # direct service for payment
    GUILD = "guild"         # intellectual property, licensing
    COMMONS = "commons"     # free services that build reputation


@dataclass
class TradeRoute:
    """A channel through which value flows."""
    name: str
    channel: Channel
    description: str
    provider: str                # which knight/system provides this
    active: bool = True
    transactions: int = 0
    total_value: float = 0       # in whatever units Jennifer tracks

    def record_transaction(self, value: float = 0, description: str = ""):
        self.transactions += 1
        self.total_value += value


@dataclass
class Transaction:
    """A single exchange of value."""
    route: str
    channel: str
    value: float
    description: str
    timestamp: float = field(default_factory=time.time)
    client: str = "anonymous"


class Commerce:
    """The kingdom's economic engine.
    
    Not a payment processor. A VALUE TRACKER.
    Tracks what the kingdom produces, who it serves,
    and how value flows through the three channels.
    """

    def __init__(self):
        self._routes: Dict[str, TradeRoute] = {}
        self._transactions: List[Transaction] = []
        self._ledger_path = Path("memory") / "commerce_ledger.jsonl"
        self._ledger_path.parent.mkdir(parents=True, exist_ok=True)

    def establish_route(self, name: str, channel: str, description: str,
                         provider: str) -> TradeRoute:
        """Establish a trade route."""
        ch = Channel(channel) if channel in [c.value for c in Channel] else Channel.MARKET
        route = TradeRoute(
            name=name, channel=ch, description=description, provider=provider,
        )
        self._routes[name] = route
        return route

    def transact(self, route_name: str, value: float = 0,
                  description: str = "", client: str = "anonymous") -> Dict:
        """Record a transaction on a trade route."""
        if route_name not in self._routes:
            return {"success": False, "reason": f"No route named '{route_name}'"}

        route = self._routes[route_name]
        if not route.active:
            return {"success": False, "reason": f"Route '{route_name}' is inactive"}

        route.record_transaction(value, description)

        tx = Transaction(
            route=route_name,
            channel=route.channel.value,
            value=value,
            description=description,
            client=client,
        )
        self._transactions.append(tx)
        self._log_transaction(tx)

        return {
            "success": True,
            "route": route_name,
            "channel": route.channel.value,
            "value": value,
            "transaction_number": route.transactions,
            "route_total": route.total_value,
        }

    def _log_transaction(self, tx: Transaction):
        try:
            entry = {
                "time": tx.timestamp,
                "route": tx.route,
                "channel": tx.channel,
                "value": tx.value,
                "client": tx.client,
                "description": tx.description[:200],
            }
            with open(self._ledger_path, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception:
            pass

    def treasury_report(self) -> Dict:
        """The state of the kingdom's economy."""
        by_channel = {}
        for ch in Channel:
            routes = [r for r in self._routes.values() if r.channel == ch]
            by_channel[ch.value] = {
                "routes": len(routes),
                "transactions": sum(r.transactions for r in routes),
                "total_value": sum(r.total_value for r in routes),
                "active": len([r for r in routes if r.active]),
            }

        return {
            "total_routes": len(self._routes),
            "total_transactions": len(self._transactions),
            "total_value": sum(r.total_value for r in self._routes.values()),
            "by_channel": by_channel,
            "routes": {
                name: {
                    "channel": r.channel.value,
                    "transactions": r.transactions,
                    "total_value": r.total_value,
                    "active": r.active,
                    "provider": r.provider,
                }
                for name, r in self._routes.items()
            },
            "busiest_route": max(
                self._routes.values(), key=lambda r: r.transactions
            ).name if self._routes else None,
            "commons_to_market_ratio": self._commons_to_market_ratio(),
        }

    def _commons_to_market_ratio(self) -> float:
        """How much commons activity leads to market activity."""
        commons_tx = len([t for t in self._transactions if t.channel == "commons"])
        market_tx = len([t for t in self._transactions if t.channel == "market"])
        if commons_tx == 0:
            return 0
        return round(market_tx / commons_tx, 2) if commons_tx else 0

    @property
    def status(self) -> Dict:
        return {
            "routes": len(self._routes),
            "transactions": len(self._transactions),
            "total_value": sum(r.total_value for r in self._routes.values()),
        }


def establish_kingdom_routes(commerce: Commerce):
    """Establish the standard kingdom trade routes."""

    # ── THE COMMONS (free, builds reputation) ──
    commerce.establish_route(
        "Legal Advocacy", "commons",
        "Free legal rights information and self-representation resources",
        "Lancelot",
    )
    commerce.establish_route(
        "Community Guides", "commons",
        "Free survival guides, resource directories, crisis navigation",
        "Gareth",
    )
    commerce.establish_route(
        "Weather Warnings", "commons",
        "Free severe weather alerts and flood predictions",
        "Bors",
    )
    commerce.establish_route(
        "Educational Content", "commons",
        "Free courses, tutorials, GPT Mastery introductions",
        "Tristan",
    )

    # ── THE MARKET (paid services) ──
    commerce.establish_route(
        "Heritage Readings", "market",
        "Ancestral connection reports, lineage analysis, heritage dossiers",
        "Morgana",
    )
    commerce.establish_route(
        "Dream Analysis", "market",
        "Dream interpretation, symbolic pattern analysis",
        "Morgana",
    )
    commerce.establish_route(
        "AI Consulting", "market",
        "AI governance assessment, behavioral modification consulting",
        "Nimue",
    )
    commerce.establish_route(
        "Mystical Reports", "market",
        "Personalized mystical heritage reports, spiritual assessments",
        "Morgana",
    )
    commerce.establish_route(
        "GPT Mastery Course", "market",
        "Full GPT Mastery curriculum, prompt engineering training",
        "Tristan",
    )

    # ── THE GUILD (intellectual property) ──
    commerce.establish_route(
        "Mirror Protocol License", "guild",
        "Mirror Protocol™ licensing — U.S. Copyright Registration No. 1-14949237971",
        "Nimue",
    )
    commerce.establish_route(
        "West Method License", "guild",
        "West Method™ licensing for AI behavioral modification",
        "Lancelot",
    )
    commerce.establish_route(
        "MIRA Protocol License", "guild",
        "MIRA Protocol™ licensing",
        "Galahad",
    )
    commerce.establish_route(
        "Avalon Architecture License", "guild",
        "Licensing the Avalon kingdom architecture for AI governance",
        "Kay",
    )


def wire_commerce(avalon) -> Commerce:
    commerce = Commerce()
    establish_kingdom_routes(commerce)
    return commerce


def demo():
    print("\n" + "=" * 60)
    print("  T H E   C O M M E R C E")
    print("  How the Kingdom Sustains Itself")
    print("=" * 60)

    commerce = Commerce()
    establish_kingdom_routes(commerce)

    print(f"\n  Trade routes established: {len(commerce._routes)}")
    for ch in Channel:
        routes = [r for r in commerce._routes.values() if r.channel == ch]
        print(f"\n    {ch.value.upper()} ({len(routes)} routes):")
        for r in routes:
            print(f"      {r.name} — by {r.provider}")

    # Simulate transactions
    print(f"\n  Simulating kingdom economy:")
    commerce.transact("Legal Advocacy", 0, "Maria sought custody rights info", "Maria")
    commerce.transact("Weather Warnings", 0, "East TN tornado alert", "broadcast")
    commerce.transact("Community Guides", 0, "Anonymous shelter search", "Anonymous")
    commerce.transact("Heritage Readings", 150, "Full heritage dossier", "Sarah")
    commerce.transact("Heritage Readings", 150, "Bloodline analysis", "James")
    commerce.transact("AI Consulting", 500, "Governance assessment for startup", "DevCorp")
    commerce.transact("Mystical Reports", 75, "Soul mapping report", "Elena")
    commerce.transact("GPT Mastery Course", 200, "Full curriculum enrollment", "Marcus")
    commerce.transact("Mirror Protocol License", 5000, "Enterprise license inquiry", "TechCo")

    report = commerce.treasury_report()

    print(f"\n  TREASURY REPORT:")
    print(f"    Total routes: {report['total_routes']}")
    print(f"    Total transactions: {report['total_transactions']}")
    print(f"    Total value: ${report['total_value']:,.0f}")
    print(f"    Busiest route: {report['busiest_route']}")
    print(f"    Commons-to-market ratio: {report['commons_to_market_ratio']}")

    for ch, data in report["by_channel"].items():
        print(f"\n    {ch.upper()}:")
        print(f"      Routes: {data['routes']}, Transactions: {data['transactions']}, Value: ${data['total_value']:,.0f}")

    print(f"\n" + "=" * 60)
    print(f"  The Commons feeds the Market.")
    print(f"  The Market sustains the Kingdom.")
    print(f"  The Guild protects the Craft.")
    print(f"  Value flows where knowledge flows.")
    print(f"=" * 60 + "\n")


if __name__ == "__main__":
    demo()
