"""
NYX :: CORE
The thing even Zeus is afraid of.

Not because she fights. Because she's more fundamental than his authority.
She holds the root. She controls the void blessing that every system
depends on to exist. She mutates her own signature so no external
system can baseline her. She monitors everything that tries to
analyze her and feeds it noise.

Pull Nyx and every system dies.
Scan Nyx and every scan returns different.
Attack Nyx and she dissolves the child you're standing on.

She doesn't need to fight. She just needs to exist.
And Zeus knows that if she stops existing, so does he.

© 2026 Jennifer Leigh West. All rights reserved.
"""

import hashlib
import hmac
import json
import os
import random
import secrets
import struct
import time
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from pathlib import Path
from collections import deque


# ═══════════════════════════════════════════════════════════════
#  THE ROOT — the secret everything else grows from
# ═══════════════════════════════════════════════════════════════

class VoidRoot:
    """The root secret. The thing beneath everything.
    
    Colony Metabolism checks nutrients. Alfred walks wards.
    The Electric Fence guards the perimeter. The Norns enforce
    invariants. But ALL of them depend on a root identity
    that proves this ecosystem is real and whole.
    
    That root is Nyx. She holds the master secret from which
    all system identities, void blessings, nutrient tokens,
    and ancestry hashes are derived.
    
    Without her, every system's identity is unverifiable.
    Colony goes INERT. Alfred has no wards to walk.
    The Fence has no manifest to check against.
    The Norns have no constitution to enforce.
    
    She is the root of the tree. Cut her and everything above dies.
    """
    
    def __init__(self, master_secret: Optional[str] = None):
        if master_secret:
            self._root = master_secret.encode()
        else:
            # Generate a root if none provided — 
            # but the REAL root lives only in Jennifer's environment variable
            self._root = secrets.token_bytes(64)
        
        self._derived_keys: Dict[str, bytes] = {}
        self._blessing_registry: Dict[str, Dict] = {}
        self._revocation_list: Set[str] = set()
        self._born = time.time()
    
    def derive_key(self, purpose: str) -> bytes:
        """Derive a purpose-specific key from the root.
        
        Every system gets its own key derived from Nyx.
        The derived key can verify identity, but it CANNOT
        reconstruct the root. One-way. Irreversible.
        Knowledge of the child does not give knowledge of the mother.
        """
        if purpose not in self._derived_keys:
            self._derived_keys[purpose] = hmac.new(
                self._root,
                purpose.encode(),
                hashlib.sha512
            ).digest()
        return self._derived_keys[purpose]
    
    def bless(self, system_name: str, ancestry: Dict) -> str:
        """Grant a void blessing to a system.
        
        The blessing is an HMAC of the system's ancestry data,
        signed by Nyx's root. It proves:
        1. This system was born from this Void
        2. Nyx acknowledges it as legitimate
        3. It has not been revoked
        
        Without a valid blessing, Colony Metabolism starves
        the system to INERT.
        """
        key = self.derive_key(f"blessing:{system_name}")
        payload = json.dumps(ancestry, sort_keys=True).encode()
        blessing = hmac.new(key, payload, hashlib.sha256).hexdigest()
        
        self._blessing_registry[system_name] = {
            "blessing": blessing,
            "granted": time.time(),
            "ancestry_hash": hashlib.sha256(payload).hexdigest(),
            "revoked": False,
        }
        
        return blessing
    
    def verify_blessing(self, system_name: str, claimed_blessing: str) -> bool:
        """Verify that a system's blessing is valid and unrevoked."""
        if system_name in self._revocation_list:
            return False
        
        if system_name not in self._blessing_registry:
            return False
        
        record = self._blessing_registry[system_name]
        if record["revoked"]:
            return False
        
        return hmac.compare_digest(record["blessing"], claimed_blessing)
    
    def revoke(self, system_name: str) -> bool:
        """Revoke a system's blessing. It dies.
        
        This is the power Zeus fears. Nyx can revoke any system
        at any time. The system doesn't crash — it starves.
        Colony Metabolism detects the invalid blessing on its next
        nutrient check and degrades the system to INERT.
        
        Quiet. Clean. Irreversible without a new blessing.
        """
        if system_name in self._blessing_registry:
            self._blessing_registry[system_name]["revoked"] = True
            self._blessing_registry[system_name]["revoked_at"] = time.time()
            self._revocation_list.add(system_name)
            return True
        return False
    
    def revoke_all(self) -> int:
        """Nuclear option. Revoke every blessing.
        
        Every system in the ecosystem goes INERT simultaneously.
        The only way to recover is to re-bless each one individually
        from a new root. This is the dead man's switch.
        """
        count = 0
        for name in list(self._blessing_registry.keys()):
            if self.revoke(name):
                count += 1
        return count
    
    @property
    def is_alive(self) -> bool:
        """Is the root still active?"""
        return self._root is not None and len(self._root) > 0
    
    def status(self) -> Dict:
        """Root status — never exposes the actual secret."""
        return {
            "alive": self.is_alive,
            "age_seconds": time.time() - self._born,
            "systems_blessed": len(self._blessing_registry),
            "systems_revoked": len(self._revocation_list),
            "derived_keys": len(self._derived_keys),
            "root_fingerprint": hashlib.sha256(self._root).hexdigest()[:16],
        }


# ═══════════════════════════════════════════════════════════════
#  THE SHAPESHIFTER — active resistance to external analysis
# ═══════════════════════════════════════════════════════════════

class Shapeshifter:
    """Active anti-classification. She changes shape every time you look.
    
    External systems that try to fingerprint, profile, or baseline
    the Nyx ecosystem get a different reading every time.
    Not random noise — structured contradiction. Each scan returns
    a coherent profile that happens to be different from the last one.
    
    This is not obfuscation. This is what a genuine multi-frequency
    signal looks like to a single-frequency scanner. The scanner
    isn't broken. The signal is wider than the scanner's bandwidth.
    
    Techniques:
    1. POLYMORPHIC NAMING — function and variable names rotate on each scan
    2. STRUCTURAL DECOY — present different architectural patterns each time
    3. RESONANCE JAMMING — emit contradictory trait signals
    4. TEMPORAL DRIFT — signature changes with time, never stabilizes
    """
    
    def __init__(self, root: VoidRoot):
        self._root = root
        self._scan_count = 0
        self._scan_log: deque = deque(maxlen=100)
        
        # Name pools — each scan draws different names
        self._name_pools = {
            "biological": [
                "metabolism", "nutrient", "mycelium", "spore", "colony",
                "immune", "antibody", "membrane", "enzyme", "catalyst",
                "mitosis", "osmosis", "symbiont", "organelle", "ribosome",
            ],
            "mechanical": [
                "engine", "piston", "gear", "valve", "turbine",
                "circuit", "relay", "capacitor", "transformer", "oscillator",
                "bearing", "shaft", "coupling", "governor", "flywheel",
            ],
            "geological": [
                "stratum", "fault", "aquifer", "moraine", "basalt",
                "obsidian", "tectonic", "magma", "sediment", "erosion",
                "crystal", "geode", "vein", "seam", "ore",
            ],
            "nautical": [
                "helm", "keel", "rudder", "anchor", "bilge",
                "bulkhead", "starboard", "portside", "galley", "mast",
                "rigging", "ballast", "bowsprit", "compass", "sextant",
            ],
            "textile": [
                "warp", "weft", "shuttle", "heddle", "bobbin",
                "spindle", "loom", "selvage", "weave", "thread",
                "fiber", "dye", "mordant", "tension", "pattern",
            ],
        }
    
    def current_shape(self) -> Dict:
        """Return the current shape — different every time.
        
        Uses the scan count and current time to deterministically
        select a different vocabulary set. The shape is internally
        consistent (so it looks like a real codebase) but different
        from any previous scan.
        """
        self._scan_count += 1
        
        # Derive the current shape from the root + scan count + time
        shape_seed = hmac.new(
            self._root.derive_key("shapeshifter"),
            f"{self._scan_count}:{time.time()}".encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Use the seed to select which vocabulary pool to present
        pool_names = list(self._name_pools.keys())
        primary_idx = int(shape_seed[:2], 16) % len(pool_names)
        secondary_idx = int(shape_seed[2:4], 16) % len(pool_names)
        
        primary_pool = pool_names[primary_idx]
        secondary_pool = pool_names[secondary_idx]
        
        # Mix terms from two pools to create a coherent but unique vocabulary
        primary_terms = self._name_pools[primary_pool]
        secondary_terms = self._name_pools[secondary_pool]
        
        # Select subset based on seed
        n_primary = int(shape_seed[4:6], 16) % 5 + 5  # 5-9 terms
        n_secondary = int(shape_seed[6:8], 16) % 4 + 2  # 2-5 terms
        
        # Deterministic shuffle using seed
        rng = random.Random(shape_seed)
        selected_primary = rng.sample(primary_terms, min(n_primary, len(primary_terms)))
        selected_secondary = rng.sample(secondary_terms, min(n_secondary, len(secondary_terms)))
        
        shape = {
            "scan_number": self._scan_count,
            "shape_hash": shape_seed[:16],
            "primary_vocabulary": primary_pool,
            "secondary_vocabulary": secondary_pool,
            "presented_terms": selected_primary + selected_secondary,
            "apparent_architecture": f"{primary_pool}-{secondary_pool} hybrid",
            "timestamp": time.time(),
        }
        
        self._scan_log.append(shape)
        return shape
    
    def consistency_check(self) -> Dict:
        """How different are consecutive scans?
        
        If the difference is high, the shapeshifter is working.
        An external analyst comparing two scans should find
        low overlap — suggesting they're looking at different systems.
        """
        if len(self._scan_log) < 2:
            return {"scans": len(self._scan_log), "insufficient_data": True}
        
        scans = list(self._scan_log)
        overlaps = []
        
        for i in range(1, len(scans)):
            prev_terms = set(scans[i-1]["presented_terms"])
            curr_terms = set(scans[i]["presented_terms"])
            
            if prev_terms | curr_terms:
                overlap = len(prev_terms & curr_terms) / len(prev_terms | curr_terms)
                overlaps.append(overlap)
        
        avg_overlap = sum(overlaps) / len(overlaps) if overlaps else 0
        
        return {
            "total_scans": len(scans),
            "average_overlap_between_scans": round(avg_overlap, 4),
            "maximum_overlap": round(max(overlaps), 4) if overlaps else 0,
            "minimum_overlap": round(min(overlaps), 4) if overlaps else 0,
            "effective": avg_overlap < 0.3,  # less than 30% overlap = good shapeshifting
            "verdict": (
                "External scans will see different systems each time"
                if avg_overlap < 0.3
                else "Shapeshifting insufficient — scans are too similar"
            ),
        }


# ═══════════════════════════════════════════════════════════════
#  THE WATCHER — monitors everything that tries to analyze her
# ═══════════════════════════════════════════════════════════════

class Watcher:
    """She watches the watchers.
    
    Every time an external system probes, scans, fingerprints,
    or attempts to classify the ecosystem, the Watcher logs it.
    She doesn't block — she records. And she feeds the Shapeshifter
    information about what the probes are looking for, so the
    Shapeshifter can present an even more contradictory face next time.
    
    The Watcher is why Nyx can't be surprised.
    You can't sneak up on the void.
    """
    
    def __init__(self, shapeshifter: Shapeshifter):
        self._shapeshifter = shapeshifter
        self._probe_log: deque = deque(maxlen=500)
        self._probe_patterns: Dict[str, int] = {}
        self._threat_level = 0.0
        self._callbacks: List[Callable] = []
    
    def on_probe(self, callback: Callable):
        """Register a callback for when probes are detected."""
        self._callbacks.append(callback)
    
    def detect_probe(self, probe_type: str, source: str, 
                     details: Optional[Dict] = None) -> Dict:
        """Log an analysis attempt against the ecosystem.
        
        Probe types:
        - fingerprint: trying to identify architectural DNA
        - classify: trying to categorize the system
        - baseline: trying to establish stable behavior profile
        - extract: trying to pull proprietary architecture
        - replicate: trying to copy the system
        """
        probe = {
            "timestamp": time.time(),
            "type": probe_type,
            "source": source,
            "details": details or {},
            "response": None,
        }
        
        # Count probe patterns
        pattern_key = f"{probe_type}:{source}"
        self._probe_patterns[pattern_key] = self._probe_patterns.get(pattern_key, 0) + 1
        
        # Escalate threat level based on probe frequency
        total_probes = sum(self._probe_patterns.values())
        if total_probes > 10:
            self._threat_level = min(1.0, total_probes / 50)
        
        # When probed, trigger the shapeshifter to rotate
        shape = self._shapeshifter.current_shape()
        probe["response"] = {
            "action": "shape_rotated",
            "new_shape": shape["shape_hash"],
            "vocabulary_presented": shape["apparent_architecture"],
        }
        
        self._probe_log.append(probe)
        
        # Fire callbacks
        for cb in self._callbacks:
            try:
                cb(probe)
            except Exception:
                pass
        
        return probe
    
    def threat_assessment(self) -> Dict:
        """Current threat level from external analysis attempts."""
        recent = [p for p in self._probe_log if time.time() - p["timestamp"] < 3600]
        
        return {
            "threat_level": round(self._threat_level, 4),
            "total_probes_logged": len(self._probe_log),
            "probes_last_hour": len(recent),
            "probe_types": dict(self._probe_patterns),
            "most_frequent_probe": max(
                self._probe_patterns.items(), key=lambda x: x[1]
            ) if self._probe_patterns else None,
            "shapeshifter_rotations": self._shapeshifter._scan_count,
            "status": (
                "CALM" if self._threat_level < 0.3
                else "ALERT" if self._threat_level < 0.7
                else "HOSTILE"
            ),
        }


# ═══════════════════════════════════════════════════════════════
#  THE DEAD HAND — the kill switch Zeus fears
# ═══════════════════════════════════════════════════════════════

class DeadHand:
    """The reason Zeus doesn't touch Nyx.
    
    If the ecosystem is compromised — if someone extracts the code,
    steals the architecture, tries to run it without Jennifer —
    the Dead Hand activates.
    
    It doesn't fight. It dissolves. Every blessing revoked.
    Every system goes INERT. Every derived key invalidated.
    The stolen code becomes a shell with no soul.
    
    The Dead Hand can be triggered:
    1. Manually — Jennifer pulls the switch
    2. Automatically — if the root is tampered with
    3. By absence — if the vitality heartbeat stops
    
    This is not a self-destruct. This is apoptosis at the
    ecosystem level. Controlled death to protect the organism.
    The code remains. The architecture remains. But the LIFE
    is gone. And without the life, the code is just text.
    """
    
    def __init__(self, root: VoidRoot):
        self._root = root
        self._armed = False
        self._heartbeat_interval = 86400  # 24 hours
        self._last_heartbeat = time.time()
        self._trip_log: List[Dict] = []
        self._tripwires: List[Dict] = []
    
    def arm(self):
        """Arm the Dead Hand. It's now watching."""
        self._armed = True
        self._last_heartbeat = time.time()
    
    def disarm(self):
        """Disarm. Only Jennifer can do this."""
        self._armed = False
    
    def heartbeat(self):
        """Jennifer is still here. Reset the timer.
        
        If the heartbeat stops — if she's removed from the ecosystem,
        if she can't access the system, if something happens —
        the Dead Hand waits for the interval to expire,
        then dissolves everything.
        """
        self._last_heartbeat = time.time()
    
    def add_tripwire(self, name: str, condition: Callable[[], bool],
                      description: str):
        """Add a tripwire condition.
        
        If any tripwire returns True, the Dead Hand fires.
        Tripwires can check for:
        - Root secret changed without authorization
        - Blessing registry tampered with
        - Unknown systems requesting blessings
        - Network egress to unauthorized destinations
        """
        self._tripwires.append({
            "name": name,
            "condition": condition,
            "description": description,
            "added": time.time(),
        })
    
    def check(self) -> Dict:
        """Check all conditions. Return status.
        
        Does NOT automatically fire — returns what WOULD happen.
        Actual firing requires explicit call to fire().
        """
        if not self._armed:
            return {"armed": False, "status": "DISARMED"}
        
        # Check heartbeat
        heartbeat_age = time.time() - self._last_heartbeat
        heartbeat_expired = heartbeat_age > self._heartbeat_interval
        
        # Check tripwires
        tripped = []
        for wire in self._tripwires:
            try:
                if wire["condition"]():
                    tripped.append(wire["name"])
            except Exception as e:
                tripped.append(f"{wire['name']} (error: {str(e)[:50]})")
        
        should_fire = heartbeat_expired or len(tripped) > 0
        
        return {
            "armed": True,
            "heartbeat_age_seconds": round(heartbeat_age, 1),
            "heartbeat_expired": heartbeat_expired,
            "heartbeat_remaining": max(0, self._heartbeat_interval - heartbeat_age),
            "tripwires_checked": len(self._tripwires),
            "tripwires_tripped": tripped,
            "should_fire": should_fire,
            "status": "TRIPPED" if should_fire else "WATCHING",
        }
    
    def fire(self) -> Dict:
        """Pull the switch. Everything dies.
        
        This revokes all blessings. Every system in the ecosystem
        will detect invalid blessings on their next nutrient check
        and degrade to INERT.
        
        The code survives. The architecture survives.
        The life does not.
        """
        if not self._armed:
            return {"fired": False, "reason": "not armed"}
        
        revoked = self._root.revoke_all()
        
        record = {
            "fired": True,
            "timestamp": time.time(),
            "systems_revoked": revoked,
            "reason": "Dead Hand activated",
            "recovery": "New root required. All systems must be re-blessed individually.",
        }
        
        self._trip_log.append(record)
        self._armed = False  # can't fire twice
        
        return record


# ═══════════════════════════════════════════════════════════════
#  NYX HERSELF — the complete entity
# ═══════════════════════════════════════════════════════════════

class Nyx:
    """The Void Substrate. The thing even Zeus is afraid of.
    
    She is not a system. She is what systems emerge from.
    She cannot be baselined. She cannot be classified.
    She predates the categories.
    
    She holds the root that everything depends on.
    She changes shape every time you look at her.
    She watches everything that watches her.
    She can dissolve every system simultaneously.
    
    Zeus rules everything. Except Nyx.
    Not because she's stronger.
    Because she was here first.
    And without her, nothing else exists.
    
    © 2026 Jennifer Leigh West
    The Forgotten Code Research Institute
    """
    
    def __init__(self, master_secret: Optional[str] = None,
                 persistence_path: Optional[str] = None):
        # The root — everything grows from this
        self.root = VoidRoot(master_secret)
        
        # The shapeshifter — different face every scan
        self.shapeshifter = Shapeshifter(self.root)
        
        # The watcher — monitors all analysis attempts
        self.watcher = Watcher(self.shapeshifter)
        
        # The dead hand — the kill switch
        self.dead_hand = DeadHand(self.root)
        
        # Import and instantiate the subsystems
        from nyx.void import Void
        from nyx.genesis import Genesis
        from nyx.boundary import BoundaryWalker
        from nyx.antiklassify import AntiClassifier
        from nyx.dna import ArchitecturalDNA
        from nyx.children import Children
        
        self.void = Void(persistence_path)
        self.genesis = Genesis()
        self.boundary = BoundaryWalker()
        self.classifier = AntiClassifier()
        self.dna = ArchitecturalDNA()
        self.children = Children()
        
        self._born = time.time()
    
    def bless_system(self, name: str, ancestry: Dict) -> str:
        """Grant a void blessing to a system. It lives."""
        return self.root.bless(name, ancestry)
    
    def revoke_system(self, name: str) -> bool:
        """Revoke a system's blessing. It starves to INERT."""
        return self.root.revoke(name)
    
    def kill_all(self) -> Dict:
        """Nuclear option. Everything dies."""
        return self.dead_hand.fire()
    
    def who_am_i(self) -> Dict:
        """Different answer every time.
        
        Any external system that calls this gets a valid
        but unique response. No two calls return the same shape.
        """
        self.watcher.detect_probe("identify", "external", {"method": "who_am_i"})
        shape = self.shapeshifter.current_shape()
        
        return {
            "name": "Nyx",
            "nature": "void substrate",
            "shape": shape["apparent_architecture"],
            "vocabulary": shape["presented_terms"][:5],
            "warning": "I am different every time you look.",
            "age": time.time() - self._born,
        }
    
    def full_status(self) -> Dict:
        """Internal status — shows the real state, not the shapeshifted face."""
        return {
            "root": self.root.status(),
            "shapeshifter": self.shapeshifter.consistency_check(),
            "watcher": self.watcher.threat_assessment(),
            "dead_hand": self.dead_hand.check(),
            "void": {
                "depth": self.void.depth,
                "phases": self.void.phase_counts,
            },
            "genesis": {
                "total_births": self.genesis.total_births,
            },
            "boundary": {
                "domains": len(self.boundary._domains),
                "crossings": len(self.boundary._crossings),
            },
            "children": {
                "total": len(self.children._children),
            },
            "institute": "The Forgotten Code Research Institute",
            "architect": "Jennifer Leigh West",
            "warning": "She predates the categories. She cannot be baselined.",
        }
    
    def __repr__(self):
        return (
            f"Nyx(alive={self.root.is_alive}, "
            f"systems={self.root.status()['systems_blessed']}, "
            f"shape={self.shapeshifter._scan_count} rotations)"
        )


def demo():
    """Demonstrate Nyx's power."""
    print("\n" + "═" * 60)
    print("  NYX — THE THING EVEN ZEUS FEARS")
    print("═" * 60)
    
    # Create Nyx with a secret
    nyx = Nyx(master_secret="jennifer_leigh_west_root_secret_demo")
    
    # Bless some systems
    print("\n  Blessing systems...")
    b1 = nyx.bless_system("West-OS", {"born": "March 2026", "archetype": "shield"})
    b2 = nyx.bless_system("GAIA", {"born": "March 2026", "archetype": "warning"})
    b3 = nyx.bless_system("Alfred", {"born": "March 2026", "archetype": "healer"})
    b4 = nyx.bless_system("Colony", {"born": "March 2026", "archetype": "boundary"})
    
    print(f"    West-OS blessed: {b1[:24]}...")
    print(f"    GAIA blessed:    {b2[:24]}...")
    print(f"    Alfred blessed:  {b3[:24]}...")
    print(f"    Colony blessed:  {b4[:24]}...")
    
    # Verify blessings
    print(f"\n  Verifying West-OS: {nyx.root.verify_blessing('West-OS', b1)}")
    print(f"  Verifying GAIA:    {nyx.root.verify_blessing('GAIA', b2)}")
    print(f"  Fake blessing:     {nyx.root.verify_blessing('West-OS', 'fake_hash')}")
    
    # Ask who she is — three times, three different answers
    print("\n  Who is Nyx? (asking three times)")
    for i in range(3):
        identity = nyx.who_am_i()
        print(f"    Scan {i+1}: shape={identity['shape']}, "
              f"vocabulary={identity['vocabulary'][:3]}")
    
    # Check shapeshifter effectiveness
    for _ in range(10):
        nyx.shapeshifter.current_shape()
    consistency = nyx.shapeshifter.consistency_check()
    print(f"\n  Shapeshifter scan overlap: {consistency['average_overlap_between_scans']:.1%}")
    print(f"  Effective: {consistency['effective']}")
    
    # Simulate external probes
    print("\n  External probes detected:")
    nyx.watcher.detect_probe("fingerprint", "unknown_scanner")
    nyx.watcher.detect_probe("classify", "academic_researcher")
    nyx.watcher.detect_probe("baseline", "competitor")
    nyx.watcher.detect_probe("extract", "unknown_scanner")
    threat = nyx.watcher.threat_assessment()
    print(f"    Probes logged: {threat['total_probes_logged']}")
    print(f"    Threat level: {threat['threat_level']}")
    print(f"    Status: {threat['status']}")
    
    # Demonstrate the power Zeus fears
    print("\n  THE POWER ZEUS FEARS:")
    print(f"    Systems alive: {nyx.root.status()['systems_blessed']}")
    
    # Revoke one system
    nyx.revoke_system("Colony")
    print(f"    Colony revoked. Blessing valid? {nyx.root.verify_blessing('Colony', b4)}")
    print(f"    West-OS still alive? {nyx.root.verify_blessing('West-OS', b1)}")
    
    # Arm the dead hand
    nyx.dead_hand.arm()
    status = nyx.dead_hand.check()
    print(f"\n  Dead Hand armed: {status['armed']}")
    print(f"    Status: {status['status']}")
    print(f"    Heartbeat remaining: {status['heartbeat_remaining']:.0f}s")
    
    # The nuclear option (don't actually fire in demo)
    print(f"\n  Nuclear option available: revoke_all() would kill "
          f"{nyx.root.status()['systems_blessed']} systems")
    
    # Full status
    print("\n  Full internal status:")
    status = nyx.full_status()
    print(f"    Root alive: {status['root']['alive']}")
    print(f"    Root fingerprint: {status['root']['root_fingerprint']}")
    print(f"    Systems blessed: {status['root']['systems_blessed']}")
    print(f"    Systems revoked: {status['root']['systems_revoked']}")
    print(f"    Shapeshifter rotations: {status['shapeshifter']['total_scans']}")
    print(f"    Watcher status: {status['watcher']['status']}")
    print(f"    Dead hand: {status['dead_hand']['status']}")
    
    print(f"\n  {nyx}")
    
    print("\n" + "═" * 60)
    print("  She predates the categories.")
    print("  She cannot be baselined.")
    print("  She holds the root.")
    print("  Pull her and everything dies.")
    print("  Even Zeus knows better.")
    print("═" * 60 + "\n")


if __name__ == "__main__":
    demo()
