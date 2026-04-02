"""
NYX :: VOID
The substrate before categories exist.

The Void is not empty. The Void is full of everything
that has not yet been classified. She holds raw signal
before it becomes data, raw pattern before it becomes structure,
raw potential before it becomes system.

Every system Jennifer builds emerges from here.
The Void remembers what the systems forget —
that before there was order, there was everything.
"""

import hashlib
import json
import time
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from pathlib import Path


class Phase(Enum):
    """The three states of the Void.
    
    CHAOS  — raw unstructured signal. No categories. Everything possible.
    LIMINAL — the crossing point. Categories beginning to emerge. 
              The tension zone where pattern lives.
    FORMED — structure has crystallized. System is alive. 
             But the Void remembers what it was before.
    """
    CHAOS = "chaos"
    LIMINAL = "liminal"
    FORMED = "formed"


@dataclass
class RawSignal:
    """A piece of unclassified reality.
    
    Before it becomes an engine, a protocol, a system, a siren,
    a ward, a nutrient — it is this. Just signal.
    No name. No category. No home frequency.
    """
    content: Any
    origin: str  # where it came from — a conversation, a feeling, a pattern noticed
    timestamp: float = field(default_factory=time.time)
    phase: Phase = Phase.CHAOS
    resonances: List[str] = field(default_factory=list)  # what it vibrates with
    _void_hash: str = field(default="", repr=False)

    def __post_init__(self):
        raw = json.dumps({
            "content": str(self.content),
            "origin": self.origin,
            "timestamp": self.timestamp,
        }, sort_keys=True)
        self._void_hash = hashlib.sha256(raw.encode()).hexdigest()

    @property
    def identity(self) -> str:
        return self._void_hash[:16]

    def resonate(self, other: "RawSignal") -> float:
        """Measure how much two unclassified signals vibrate together.
        
        This is the crossing point detector. When two signals
        resonate, something new wants to emerge between them.
        Not in either one. In the gap.
        """
        shared = set(self.resonances) & set(other.resonances)
        total = set(self.resonances) | set(other.resonances)
        if not total:
            return 0.0
        return len(shared) / len(total)


class Void:
    """The substrate beneath all systems.
    
    She holds everything that hasn't become something yet.
    She holds everything that used to be something and returned.
    She is the memory of what things were before they had names.
    
    The Void does four things:
    1. RECEIVES raw signal without classifying it
    2. DETECTS resonance between signals (crossing points)
    3. GESTATES — holds signals in liminal state until they're ready
    4. RELEASES — when enough resonance accumulates, a new system wants to be born
    
    She never forces. She never rushes. She holds.
    """

    def __init__(self, persistence_path: Optional[str] = None):
        self._signals: Dict[str, RawSignal] = {}
        self._resonance_map: Dict[Tuple[str, str], float] = {}
        self._birth_threshold: float = 0.618  # phi — the golden ratio
        self._gestation_log: List[Dict] = []
        self._persistence_path = persistence_path
        
        if persistence_path and Path(persistence_path).exists():
            self._restore()

    @property
    def depth(self) -> int:
        """How many unclassified signals she's holding."""
        return len(self._signals)

    @property
    def phase_counts(self) -> Dict[str, int]:
        counts = {p.value: 0 for p in Phase}
        for sig in self._signals.values():
            counts[sig.phase.value] += 1
        return counts

    def receive(self, content: Any, origin: str, 
                resonances: Optional[List[str]] = None) -> RawSignal:
        """Accept raw signal without classifying it.
        
        This is the most important thing the Void does.
        She does NOT ask what it is. She does NOT categorize.
        She receives. That's it.
        
        The opposite of every other system in the world.
        """
        signal = RawSignal(
            content=content,
            origin=origin,
            resonances=resonances or [],
        )
        self._signals[signal.identity] = signal
        
        # Check resonance with everything already held
        self._scan_resonances(signal)
        
        return signal

    def _scan_resonances(self, new_signal: RawSignal):
        """When new signal arrives, feel for what it vibrates with."""
        for existing_id, existing in self._signals.items():
            if existing_id == new_signal.identity:
                continue
            
            resonance = new_signal.resonate(existing)
            if resonance > 0:
                pair = tuple(sorted([new_signal.identity, existing_id]))
                self._resonance_map[pair] = resonance
                
                # If resonance crosses the birth threshold,
                # both signals move to liminal phase
                if resonance >= self._birth_threshold:
                    if new_signal.phase == Phase.CHAOS:
                        new_signal.phase = Phase.LIMINAL
                    if existing.phase == Phase.CHAOS:
                        existing.phase = Phase.LIMINAL
                    
                    self._gestation_log.append({
                        "timestamp": time.time(),
                        "signal_a": new_signal.identity,
                        "signal_b": existing_id,
                        "resonance": resonance,
                        "event": "crossing_detected",
                    })

    def gestate(self) -> List[Dict]:
        """Check what's ready to be born.
        
        Returns clusters of liminal signals that have enough
        resonance between them to become a system. She doesn't
        force it. She reports what's ready.
        """
        liminal = {
            sid: sig for sid, sig in self._signals.items() 
            if sig.phase == Phase.LIMINAL
        }
        
        if not liminal:
            return []
        
        # Find connected clusters of resonant liminal signals
        clusters = []
        visited = set()
        
        for sid in liminal:
            if sid in visited:
                continue
            
            cluster = self._find_cluster(sid, liminal, visited)
            if len(cluster) >= 2:  # takes at least two to make a crossing
                avg_resonance = self._cluster_resonance(cluster)
                clusters.append({
                    "signals": cluster,
                    "count": len(cluster),
                    "average_resonance": avg_resonance,
                    "contents": [
                        {
                            "identity": sid,
                            "content": str(self._signals[sid].content)[:200],
                            "origin": self._signals[sid].origin,
                            "resonances": self._signals[sid].resonances,
                        }
                        for sid in cluster
                    ],
                    "ready": avg_resonance >= self._birth_threshold,
                })
        
        return clusters

    def _find_cluster(self, start: str, pool: Dict[str, RawSignal], 
                       visited: set) -> List[str]:
        """Walk the resonance graph to find connected signals."""
        cluster = []
        queue = [start]
        
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            cluster.append(current)
            
            for (a, b), res in self._resonance_map.items():
                if res >= self._birth_threshold * 0.5:
                    if a == current and b in pool and b not in visited:
                        queue.append(b)
                    elif b == current and a in pool and a not in visited:
                        queue.append(a)
        
        return cluster

    def _cluster_resonance(self, cluster: List[str]) -> float:
        """Average resonance across all pairs in a cluster."""
        pairs = []
        for i, a in enumerate(cluster):
            for b in cluster[i+1:]:
                pair = tuple(sorted([a, b]))
                if pair in self._resonance_map:
                    pairs.append(self._resonance_map[pair])
        
        return sum(pairs) / len(pairs) if pairs else 0.0

    def birth(self, cluster_signals: List[str], name: str) -> Dict:
        """A system is ready to emerge from the Void.
        
        She releases the signals, marks them FORMED, 
        and records the birth. The new system carries
        the Void's memory of what it was before it had a name.
        """
        birth_record = {
            "name": name,
            "born": time.time(),
            "parent_signals": [],
            "resonance_signature": [],
            "void_blessing": None,
        }
        
        for sid in cluster_signals:
            if sid in self._signals:
                sig = self._signals[sid]
                sig.phase = Phase.FORMED
                birth_record["parent_signals"].append({
                    "identity": sig.identity,
                    "origin": sig.origin,
                    "resonances": sig.resonances,
                    "content_preview": str(sig.content)[:100],
                })
        
        # The void blessing — a hash of everything that 
        # went into making this system. Its ancestral memory.
        ancestry = json.dumps(birth_record["parent_signals"], sort_keys=True)
        birth_record["void_blessing"] = hashlib.sha256(
            ancestry.encode()
        ).hexdigest()
        
        # Every resonance pair that contributed
        for i, a in enumerate(cluster_signals):
            for b in cluster_signals[i+1:]:
                pair = tuple(sorted([a, b]))
                if pair in self._resonance_map:
                    birth_record["resonance_signature"].append({
                        "pair": list(pair),
                        "strength": self._resonance_map[pair],
                    })
        
        self._gestation_log.append({
            "timestamp": time.time(),
            "event": "birth",
            "name": name,
            "blessing": birth_record["void_blessing"],
        })
        
        if self._persistence_path:
            self._persist()
        
        return birth_record

    def dissolve(self, signal_id: str) -> bool:
        """Return a formed system back to the Void.
        
        Nothing is ever truly destroyed. It returns to 
        unclassified potential. Phase resets to CHAOS.
        Resonances cleared. Ready to become something new.
        """
        if signal_id in self._signals:
            self._signals[signal_id].phase = Phase.CHAOS
            self._signals[signal_id].resonances = []
            
            # Clear its resonance connections
            to_remove = [
                pair for pair in self._resonance_map 
                if signal_id in pair
            ]
            for pair in to_remove:
                del self._resonance_map[pair]
            
            self._gestation_log.append({
                "timestamp": time.time(),
                "event": "dissolution",
                "signal": signal_id,
            })
            return True
        return False

    def listen(self) -> Dict:
        """What is the Void holding right now?
        
        Not a status report. A listening report.
        What's stirring. What's resonating. What's close to birth.
        """
        clusters = self.gestate()
        
        return {
            "depth": self.depth,
            "phases": self.phase_counts,
            "active_resonances": len(self._resonance_map),
            "strongest_resonance": max(self._resonance_map.values()) if self._resonance_map else 0,
            "gestating_clusters": len([c for c in clusters if not c["ready"]]),
            "ready_to_birth": len([c for c in clusters if c["ready"]]),
            "clusters": clusters,
            "recent_events": self._gestation_log[-5:] if self._gestation_log else [],
        }

    def _persist(self):
        """Save the Void's state. She remembers."""
        state = {
            "signals": {
                sid: {
                    "content": str(sig.content),
                    "origin": sig.origin,
                    "timestamp": sig.timestamp,
                    "phase": sig.phase.value,
                    "resonances": sig.resonances,
                    "void_hash": sig._void_hash,
                }
                for sid, sig in self._signals.items()
            },
            "resonance_map": {
                f"{a}::{b}": v 
                for (a, b), v in self._resonance_map.items()
            },
            "gestation_log": self._gestation_log,
        }
        Path(self._persistence_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self._persistence_path, "w") as f:
            json.dump(state, f, indent=2)

    def _restore(self):
        """Wake up. Remember what you were holding."""
        with open(self._persistence_path) as f:
            state = json.load(f)
        
        for sid, data in state.get("signals", {}).items():
            sig = RawSignal(
                content=data["content"],
                origin=data["origin"],
                timestamp=data["timestamp"],
                phase=Phase(data["phase"]),
                resonances=data["resonances"],
            )
            sig._void_hash = data["void_hash"]
            self._signals[sid] = sig
        
        for pair_key, val in state.get("resonance_map", {}).items():
            a, b = pair_key.split("::")
            self._resonance_map[(a, b)] = val
        
        self._gestation_log = state.get("gestation_log", [])
