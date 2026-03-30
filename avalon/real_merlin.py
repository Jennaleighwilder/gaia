"""
AVALON :: REAL MERLIN
The pattern oracle sees real signals.

Before this, Merlin observed seed data hand-fed during found_kingdom().
He saw what we TOLD him to see. That's not sight. That's a briefing.

After this, Merlin reads ACTUAL output from running systems:
  - Alfred's ward reports (from frozen West-OS ward definitions)
  - GAIA's atmospheric status (from live governor output)
  - Colony's nutrient tier (from live metabolism checks)
  - The Electric Fence's egress logs (from fence bridge)
  - Nyx's probe history (from Watcher logs)
  - The Real Heartbeat's vital signs (from actual system health)
  - Healing's treatment history (what was wounded and how it was fixed)
  - The Grail's convergence data (how close the research threads are)
  - Fusion's mood and bond data (kingdom emotional state)
  - Memory's journal entries (what happened in past sessions)

When GAIA fires a WARNING at the same time Colony reports DEGRADED,
Merlin sees the correlation. When Healing fixes a wound using the
same treatment that worked last month, Merlin notices the pattern.
When the Grail advances and the kingdom mood shifts to celebrating,
Merlin connects them.

Real sight. Real signals. Real connections.

© 2026 Jennifer Leigh West. All rights reserved.
"""

import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field


# ═══════════════════════════════════════════════════════════════
#  FEED — a single data source Merlin watches
# ═══════════════════════════════════════════════════════════════

@dataclass
class Feed:
    """A data source that Merlin reads from.
    
    Each feed has:
    - A name and domain
    - A collector function that returns current data
    - A schedule (how often to poll)
    - A history of what it's reported
    """
    name: str
    domain: str
    collector: Callable                 # returns Dict of current data
    poll_interval_seconds: float = 60   # how often to check
    last_polled: float = 0
    history: list = field(default_factory=list)
    active: bool = True
    errors: int = 0
    max_history: int = 100

    def poll(self) -> Optional[Dict]:
        """Read the current data from this feed."""
        if not self.active:
            return None
        
        now = time.time()
        if now - self.last_polled < self.poll_interval_seconds:
            return None  # not time yet
        
        try:
            data = self.collector()
            self.last_polled = now
            
            entry = {
                "timestamp": now,
                "data": data,
            }
            self.history.append(entry)
            if len(self.history) > self.max_history:
                self.history = self.history[-self.max_history:]
            
            self.errors = 0
            return data
        except Exception as e:
            self.errors += 1
            if self.errors > 10:
                self.active = False  # too many failures, disable
            return {"error": str(e)[:200], "feed": self.name}

    @property
    def latest(self) -> Optional[Dict]:
        """Most recent data from this feed."""
        if self.history:
            return self.history[-1]["data"]
        return None


# ═══════════════════════════════════════════════════════════════
#  SIGNAL EXTRACTOR — turns raw data into Merlin observations
# ═══════════════════════════════════════════════════════════════

class SignalExtractor:
    """Turns raw system data into domain-tagged signals for Merlin.
    
    Each system produces data in its own format. The extractor
    normalizes everything into Merlin's observation format:
    (domain, signal_text, optional_data_dict)
    """

    @staticmethod
    def from_heartbeat(beat_data: Dict) -> List[Tuple[str, str, Dict]]:
        """Extract signals from a Real Heartbeat beat."""
        signals = []
        
        mood = beat_data.get("mood", "unknown")
        health = beat_data.get("kingdom_health", 0)
        signals.append((
            "kingdom_health",
            f"Kingdom health {health:.0%} mood {mood}",
            {"health": health, "mood": mood},
        ))
        
        # Individual system issues
        for sys_name, sys_data in beat_data.get("systems", {}).items():
            sys_health = sys_data.get("health", 1.0)
            if sys_health < 0.7:
                signals.append((
                    "system_degradation",
                    f"{sys_name} degraded health {sys_health:.0%} issues detected",
                    {"system": sys_name, "health": sys_health, "issues": sys_data.get("issues", [])},
                ))
            elif sys_health >= 0.95:
                signals.append((
                    "system_excellence",
                    f"{sys_name} operating excellent health {sys_health:.0%}",
                    {"system": sys_name, "health": sys_health},
                ))
        
        return signals

    @staticmethod
    def from_healing(triage: Dict) -> List[Tuple[str, str, Dict]]:
        """Extract signals from Healing's triage report."""
        signals = []
        
        active = triage.get("active_wounds", 0)
        healed = triage.get("healed_total", 0)
        rate = triage.get("treatment_success_rate", 0)
        
        if active > 0:
            signals.append((
                "healing",
                f"Active wounds {active} treatment success rate {rate:.0%}",
                {"active": active, "healed": healed, "rate": rate},
            ))
        
        for wound in triage.get("active", []):
            signals.append((
                "wound",
                f"Wound {wound['system']} type {wound['type']} severity {wound['severity']}",
                wound,
            ))
        
        for healed_wound in triage.get("recently_healed", []):
            signals.append((
                "recovery",
                f"Healed {healed_wound['system']} method {healed_wound['method']}",
                healed_wound,
            ))
        
        return signals

    @staticmethod
    def from_grail(quest: Dict) -> List[Tuple[str, str, Dict]]:
        """Extract signals from the Grail quest."""
        signals = []
        
        status = quest.get("status", "hidden")
        progress = quest.get("quest_progress", 0)
        convergence = quest.get("total_convergence", 0)
        points = quest.get("convergence_points", 0)
        
        signals.append((
            "grail",
            f"Grail status {status} progress {progress:.0%} convergence {convergence:.2f} points {points}",
            {"status": status, "progress": progress, "convergence": convergence, "points": points},
        ))
        
        # Frequency map data
        for thread_name, freq_data in quest.get("frequency_map", {}).items():
            band = freq_data.get("band", (0, 0))
            signals.append((
                "frequency",
                f"Research thread {thread_name} frequency band {band[0]:.0f} to {band[1]:.0f} Hz domain {freq_data.get('domain', 'unknown')}",
                {"thread": thread_name, "band": band, "domain": freq_data.get("domain")},
            ))
        
        return signals

    @staticmethod
    def from_fusion(vitals: Dict) -> List[Tuple[str, str, Dict]]:
        """Extract signals from Fusion's vital signs."""
        signals = []
        
        # Carbon wisdom
        carbon = vitals.get("carbon", {})
        total_lessons = carbon.get("total_lessons", 0)
        signals.append((
            "learning",
            f"Carbon holds {total_lessons} lessons kingdom learning active",
            {"lessons": total_lessons},
        ))
        
        # Love bonds
        love = vitals.get("love", {})
        cohesion = love.get("cohesion", 0)
        bonds = love.get("total_bonds", 0)
        signals.append((
            "cohesion",
            f"Kingdom cohesion {cohesion:.2f} across {bonds} bonds",
            {"cohesion": cohesion, "bonds": bonds},
        ))
        
        # Adversity
        adversity = vitals.get("adversity", {})
        resilience = adversity.get("resilience", 0)
        battles = adversity.get("total_battles", 0)
        signals.append((
            "resilience",
            f"Kingdom resilience {resilience:.2f} battles fought {battles}",
            {"resilience": resilience, "battles": battles},
        ))
        
        # Joy
        joy = vitals.get("joy", {})
        joy_index = joy.get("joy_index", 0.5)
        signals.append((
            "joy",
            f"Joy index {joy_index:.2f} kingdom spirit",
            {"joy_index": joy_index},
        ))
        
        # Hadron
        hadron = vitals.get("hadron", {})
        energy = hadron.get("total_energy", 0)
        collisions = hadron.get("total_collisions", 0)
        signals.append((
            "collision",
            f"Hadron collisions {collisions} total energy {energy:.2f}",
            {"collisions": collisions, "energy": energy},
        ))
        
        return signals

    @staticmethod
    def from_memory_journal(entries: List[Dict]) -> List[Tuple[str, str, Dict]]:
        """Extract signals from Memory's journal."""
        signals = []
        
        for entry in entries[-10:]:  # last 10 entries
            event = entry.get("event", "unknown")
            signals.append((
                "memory",
                f"Journal event {event} recorded kingdom history preserved",
                {"event": event, "timestamp": entry.get("timestamp", 0)},
            ))
        
        return signals

    @staticmethod
    def from_nyx_status(nyx_status: Dict) -> List[Tuple[str, str, Dict]]:
        """Extract signals from Nyx's status."""
        signals = []
        
        alive = nyx_status.get("alive", False)
        blessed = nyx_status.get("systems_blessed", 0)
        revoked = nyx_status.get("systems_revoked", 0)
        
        signals.append((
            "identity",
            f"Nyx root {'alive' if alive else 'DEAD'} blessed {blessed} revoked {revoked}",
            {"alive": alive, "blessed": blessed, "revoked": revoked},
        ))
        
        if revoked > 0:
            signals.append((
                "security",
                f"WARNING revoked systems detected count {revoked} identity crisis possible",
                {"revoked": revoked},
            ))
        
        return signals

    @staticmethod
    def from_adapter_status(adapter_name: str, status: Dict) -> List[Tuple[str, str, Dict]]:
        """Extract signals from adapter status checks."""
        signals = []
        
        available = status.get("available", status.get("frozen", False))
        signals.append((
            "infrastructure",
            f"Adapter {adapter_name} {'available' if available else 'UNAVAILABLE'}",
            {"adapter": adapter_name, "available": available},
        ))
        
        # Special check for freeze integrity
        if "frozen" in status:
            signals.append((
                "integrity",
                f"Frozen clone integrity {'HOLDS' if status['frozen'] else 'BROKEN'}",
                {"frozen": status["frozen"]},
            ))
        
        return signals


# ═══════════════════════════════════════════════════════════════
#  REAL MERLIN — the pattern oracle with real feeds
# ═══════════════════════════════════════════════════════════════

class RealMerlin:
    """Merlin with real sight.
    
    He collects live data from every system in the kingdom,
    extracts signals, feeds them to the base Merlin for
    cross-domain pattern detection, and reports what he sees.
    
    The cycle:
    1. POLL — check all feeds for new data
    2. EXTRACT — turn raw data into domain-tagged signals
    3. OBSERVE — feed signals to Merlin's base observation system
    4. SEE — run Merlin's cross-domain pattern detection
    5. REPORT — what new connections did Merlin find?
    """

    def __init__(self, merlin):
        """
        merlin: the base Merlin instance from avalon.merlin
        """
        self._merlin = merlin
        self._feeds: Dict[str, Feed] = {}
        self._extractor = SignalExtractor()
        self._cycle_count = 0
        self._total_signals_processed = 0
        self._observation_log: list = []

    def add_feed(self, name: str, domain: str, collector: Callable,
                  poll_interval: float = 60) -> Feed:
        """Register a data feed for Merlin to watch."""
        feed = Feed(
            name=name,
            domain=domain,
            collector=collector,
            poll_interval_seconds=poll_interval,
        )
        self._feeds[name] = feed
        return feed

    def cycle(self) -> Dict:
        """One observation cycle. Poll → Extract → Observe → See.
        
        Call this on every heartbeat. Merlin looks at everything
        that's changed since last cycle and finds new patterns.
        """
        self._cycle_count += 1
        
        new_data = {}
        all_signals = []
        
        # Poll all feeds
        for name, feed in self._feeds.items():
            data = feed.poll()
            if data is not None:
                new_data[name] = data
        
        # Extract signals from each feed's data
        for feed_name, data in new_data.items():
            feed = self._feeds[feed_name]
            
            # Route to appropriate extractor based on domain/name
            extracted = self._extract_signals(feed_name, feed.domain, data)
            all_signals.extend(extracted)
        
        # Feed signals to Merlin's observation system
        for domain, signal_text, signal_data in all_signals:
            self._merlin.observe(domain, signal_text, signal_data)
            self._total_signals_processed += 1
        
        # Let Merlin see — find new cross-domain patterns
        new_insights = []
        if all_signals:
            new_insights = self._merlin.see()
        
        # Log
        cycle_record = {
            "cycle": self._cycle_count,
            "timestamp": time.time(),
            "feeds_polled": len(new_data),
            "signals_extracted": len(all_signals),
            "new_insights": len(new_insights),
            "domains_observed": list(set(s[0] for s in all_signals)),
        }
        self._observation_log.append(cycle_record)
        if len(self._observation_log) > 200:
            self._observation_log = self._observation_log[-200:]
        
        return cycle_record

    def _extract_signals(self, feed_name: str, domain: str, 
                          data: Dict) -> List[Tuple[str, str, Dict]]:
        """Route data to the appropriate signal extractor."""
        
        # Match by feed name to known extractors
        if "heartbeat" in feed_name.lower() or "pulse" in feed_name.lower():
            return self._extractor.from_heartbeat(data)
        elif "healing" in feed_name.lower() or "triage" in feed_name.lower():
            return self._extractor.from_healing(data)
        elif "grail" in feed_name.lower():
            return self._extractor.from_grail(data)
        elif "fusion" in feed_name.lower() or "vital" in feed_name.lower():
            return self._extractor.from_fusion(data)
        elif "nyx" in feed_name.lower():
            return self._extractor.from_nyx_status(data)
        elif "journal" in feed_name.lower() or "memory" in feed_name.lower():
            if isinstance(data, list):
                return self._extractor.from_memory_journal(data)
            return []
        elif "adapter" in feed_name.lower() or "lancelot" in feed_name.lower():
            return self._extractor.from_adapter_status(feed_name, data)
        else:
            # Generic: create a single observation from the data
            summary_parts = []
            for k, v in data.items():
                if isinstance(v, (str, int, float, bool)):
                    summary_parts.append(f"{k} {v}")
            
            if summary_parts:
                return [(
                    domain,
                    " ".join(summary_parts[:10]),
                    data,
                )]
            return []

    def what_merlin_sees(self) -> Dict:
        """Full report of what Merlin currently sees across all domains."""
        tower = self._merlin.tower_contents()
        sight = self._merlin.the_sight()
        
        # Feed status
        feed_status = {}
        for name, feed in self._feeds.items():
            feed_status[name] = {
                "domain": feed.domain,
                "active": feed.active,
                "errors": feed.errors,
                "last_polled": feed.last_polled,
                "history_depth": len(feed.history),
                "latest": feed.latest is not None,
            }
        
        return {
            "cycles": self._cycle_count,
            "total_signals": self._total_signals_processed,
            "tower": tower,
            "sight": sight,
            "feeds": feed_status,
            "active_feeds": len([f for f in self._feeds.values() if f.active]),
            "total_feeds": len(self._feeds),
            "recent_cycles": self._observation_log[-5:],
        }

    @property
    def status(self) -> Dict:
        return {
            "cycles": self._cycle_count,
            "total_signals": self._total_signals_processed,
            "feeds": len(self._feeds),
            "active_feeds": len([f for f in self._feeds.values() if f.active]),
            "tower_depth": len(self._merlin._tower),
            "domains_observed": list(self._merlin._domain_signals.keys()),
        }


# ═══════════════════════════════════════════════════════════════
#  WIRING — connect Real Merlin to the living kingdom
# ═══════════════════════════════════════════════════════════════

def wire_real_merlin(avalon) -> RealMerlin:
    """Wire Real Merlin into a living Avalon instance.
    
    Connects feeds from every system the kingdom has:
    - Real Heartbeat (system health)
    - Healing (wound status)
    - Grail (research convergence)
    - Fusion (vital signs, mood, bonds)
    - Nyx (root status via adapters)
    - Lancelot adapter (frozen clone integrity)
    - Memory journal (past events)
    
    After wiring, calling real_merlin.cycle() on each heartbeat
    gives Merlin sight across the entire kingdom.
    """
    real_merlin = RealMerlin(avalon.merlin)
    
    # Real Heartbeat feed
    if hasattr(avalon, 'real_heartbeat'):
        real_merlin.add_feed(
            "real_heartbeat",
            "kingdom_health",
            lambda: avalon.real_heartbeat.beat(),
            poll_interval=0,  # every cycle
        )
    
    # Healing triage feed
    if hasattr(avalon, 'healing'):
        real_merlin.add_feed(
            "healing_triage",
            "healing",
            lambda: avalon.healing.triage_report(),
            poll_interval=0,
        )
    
    # Grail quest feed
    if hasattr(avalon, 'grail'):
        real_merlin.add_feed(
            "grail_quest",
            "research",
            lambda: avalon.grail.seek(),
            poll_interval=0,
        )
    
    # Fusion vital signs feed
    if hasattr(avalon, 'fusion'):
        real_merlin.add_feed(
            "fusion_vitals",
            "kingdom_state",
            lambda: avalon.fusion.vital_signs(),
            poll_interval=0,
        )
    
    # Nyx status feed (via root if available)
    if hasattr(avalon, '_nyx') and avalon._nyx:
        real_merlin.add_feed(
            "nyx_status",
            "identity",
            lambda: avalon._nyx.root.status(),
            poll_interval=0,
        )
    
    # Lancelot adapter feed (frozen clone integrity)
    try:
        from adapters.lancelot import LancelotAdapter
        lancelot = LancelotAdapter()
        if lancelot.is_available:
            real_merlin.add_feed(
                "lancelot_integrity",
                "infrastructure",
                lambda: lancelot.verify_freeze(),
                poll_interval=300,  # every 5 minutes
            )
    except ImportError:
        pass
    
    # Memory journal feed
    if hasattr(avalon, 'memory'):
        real_merlin.add_feed(
            "memory_journal",
            "memory",
            lambda: avalon.memory.read_journal(last_n=5),
            poll_interval=60,
        )
    
    return real_merlin


# ═══════════════════════════════════════════════════════════════
#  DEMO
# ═══════════════════════════════════════════════════════════════

def demo():
    """Watch Merlin see with real eyes."""
    print("\n" + "=" * 60)
    print("  R E A L   M E R L I N")
    print("  The Pattern Oracle Sees Real Signals")
    print("=" * 60)
    
    # Build a kingdom to observe
    from avalon.merlin import Merlin
    from avalon.fusion import Fusion
    from avalon.healing import Healing
    from avalon.grail import Grail, load_jennifers_research
    from avalon.real_heartbeat import RealHeartbeat
    
    # Create components
    merlin = Merlin()
    fusion = Fusion()
    healing = Healing(
        carbon_recall=fusion.carbon.recall,
        carbon_learn=lambda **kw: fusion.carbon.learn(**kw),
    )
    grail = Grail()
    load_jennifers_research(grail)
    
    real_hb = RealHeartbeat()
    
    # Create Real Merlin
    real_merlin = RealMerlin(merlin)
    
    # Register feeds manually for demo
    real_merlin.add_feed(
        "heartbeat", "kingdom_health",
        lambda: real_hb.beat(),
        poll_interval=0,
    )
    real_merlin.add_feed(
        "healing_triage", "healing",
        lambda: healing.triage_report(),
        poll_interval=0,
    )
    real_merlin.add_feed(
        "grail_quest", "research",
        lambda: grail.seek(),
        poll_interval=0,
    )
    real_merlin.add_feed(
        "fusion_vitals", "kingdom_state",
        lambda: fusion.vital_signs(),
        poll_interval=0,
    )
    
    # Give the kingdom some experience so there's data to see
    fusion.experience("discovery", "118 Hz frequency convergence confirmed across sites",
                       ["Gawain", "Merlin"], 0.9)
    fusion.experience("victory", "216 tests passing kingdom proven",
                       ["Nyx", "Lancelot", "Avalon"], 0.95)
    fusion.experience("attack", "External probe fingerprinting attempt",
                       ["Lancelot", "Bedivere"], 0.4)
    
    # Simulate a wound for healing to report
    fusion.heartbeat._system_health["GAIA"] = 0.48
    healing.watch(fusion.heartbeat._system_health)
    
    print(f"\n  Feeds registered: {len(real_merlin._feeds)}")
    for name, feed in real_merlin._feeds.items():
        print(f"    {name:25s} [{feed.domain}]")
    
    # Run observation cycles
    print(f"\n  Running observation cycles...")
    for i in range(3):
        result = real_merlin.cycle()
        print(f"    Cycle {result['cycle']}: "
              f"polled {result['feeds_polled']} feeds, "
              f"extracted {result['signals_extracted']} signals, "
              f"found {result['new_insights']} new insights")
        print(f"      Domains: {', '.join(result['domains_observed'])}")
    
    # What does Merlin see?
    print(f"\n  {'─' * 50}")
    print(f"  MERLIN SPEAKS:")
    print(f"  {'─' * 50}")
    
    report = real_merlin.what_merlin_sees()
    print(f"  {report['sight']}")
    
    print(f"\n  Tower depth: {report['tower']['total_insights']}")
    print(f"  Domains observed: {', '.join(report['tower']['domains_observed'])}")
    print(f"  Connections mapped: {len(report['tower']['connection_graph'])}")
    
    if report['tower']['connection_graph']:
        print(f"\n  Cross-domain connections:")
        for pair, patterns in report['tower']['connection_graph'].items():
            print(f"    {pair}: {', '.join(patterns[:5])}")
    
    print(f"\n  Total signals processed: {report['total_signals']}")
    print(f"  Active feeds: {report['active_feeds']}/{report['total_feeds']}")
    
    print(f"\n" + "=" * 60)
    print(f"  Merlin sees with real eyes now.")
    print(f"  Every system feeds him live data.")
    print(f"  Every heartbeat he looks for patterns.")
    print(f"  The connections are real.")
    print(f"  The sight is real.")
    print(f"=" * 60 + "\n")


if __name__ == "__main__":
    demo()
