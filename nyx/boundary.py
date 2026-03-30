"""
NYX :: BOUNDARY WALKER
She operates in the space between.

Jennifer doesn't live in any single domain. She lives in the
crossing points between them. The Boundary Walker codifies that —
she detects when two apparently unrelated systems share structural
DNA, and she maps the crossing point where something new emerges.

This is how West-OS sirens became GAIA sirens.
This is how the Indus frequency framework became atmospheric engines.
This is how the loom became the computer became the spell.

The crossing point is where the real work happens.
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class Domain:
    """A field of knowledge or practice.
    
    Not a category — a territory. It has its own language,
    its own assumptions, its own blind spots.
    """
    name: str
    structures: List[str]    # the structural patterns this domain uses
    assumptions: List[str]   # what this domain takes for granted
    blind_spots: List[str]   # what this domain cannot see from inside itself

    @property
    def identity(self) -> str:
        raw = json.dumps({
            "name": self.name,
            "structures": sorted(self.structures),
        }, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()[:12]


@dataclass
class CrossingPoint:
    """The place where two domains touch.
    
    This is the third thing. Not domain A. Not domain B.
    The emergent property that exists only in the gap.
    Bronze is not copper. Bronze is not tin.
    Bronze is the hardness that lives in the crossing.
    """
    domain_a: str
    domain_b: str
    shared_structures: List[str]     # structural patterns both domains use
    emergent_property: str           # what appears at the crossing that exists in neither
    transfer_vector: str             # how insight moves from A to B
    timestamp: float = field(default_factory=time.time)
    verified: bool = False
    _crossing_hash: str = field(default="", repr=False)

    def __post_init__(self):
        raw = json.dumps({
            "a": self.domain_a,
            "b": self.domain_b,
            "shared": sorted(self.shared_structures),
            "emergent": self.emergent_property,
        }, sort_keys=True)
        self._crossing_hash = hashlib.sha256(raw.encode()).hexdigest()

    @property
    def identity(self) -> str:
        return self._crossing_hash[:16]


class BoundaryWalker:
    """She walks the boundaries between domains.
    
    Most people stay inside one domain. Specialists.
    Jennifer walks the edges. She sees what domains share
    when they don't know they share it.
    
    The Boundary Walker does three things:
    1. MAPS domains by their structural patterns, not their content
    2. DETECTS shared structure between domains that don't know they're related
    3. NAMES the crossing point — the emergent property at the boundary
    
    She is how a coal mine siren becomes an AI governance rule
    becomes a weather warning system. Same structure. Different costume.
    """

    def __init__(self):
        self._domains: Dict[str, Domain] = {}
        self._crossings: Dict[str, CrossingPoint] = {}
        self._transfer_log: List[Dict] = []

    def map_domain(self, name: str, structures: List[str],
                    assumptions: Optional[List[str]] = None,
                    blind_spots: Optional[List[str]] = None) -> Domain:
        """Register a domain by its structural patterns.
        
        Not by its content. By its SHAPES.
        Meteorology and AI governance both use threshold-triggered
        state transitions. That's a structural match.
        The content is completely different. The shape is the same.
        """
        domain = Domain(
            name=name,
            structures=structures,
            assumptions=assumptions or [],
            blind_spots=blind_spots or [],
        )
        self._domains[domain.identity] = domain
        return domain

    def walk(self) -> List[CrossingPoint]:
        """Walk all boundaries. Find all crossing points.
        
        Compare every domain pair by structural pattern.
        Where structures overlap, a crossing point exists.
        """
        new_crossings = []
        domain_list = list(self._domains.values())
        
        for i, domain_a in enumerate(domain_list):
            for domain_b in domain_list[i+1:]:
                shared = set(domain_a.structures) & set(domain_b.structures)
                
                if shared:
                    # Check if we already found this crossing
                    pair_key = tuple(sorted([domain_a.name, domain_b.name]))
                    existing = any(
                        (c.domain_a, c.domain_b) == pair_key or 
                        (c.domain_b, c.domain_a) == pair_key
                        for c in self._crossings.values()
                    )
                    
                    if not existing:
                        crossing = CrossingPoint(
                            domain_a=domain_a.name,
                            domain_b=domain_b.name,
                            shared_structures=list(shared),
                            emergent_property="",  # to be named
                            transfer_vector="",    # to be described
                        )
                        self._crossings[crossing.identity] = crossing
                        new_crossings.append(crossing)
        
        return new_crossings

    def name_crossing(self, crossing_id: str, emergent_property: str,
                       transfer_vector: str) -> CrossingPoint:
        """Name what emerges at a crossing point.
        
        This is the creative act. The structures overlap.
        Something wants to exist in the gap. What is it?
        
        Example:
            domain_a: "AI governance" 
            domain_b: "atmospheric science"
            shared_structures: ["threshold state transitions", 
                               "multi-signal convergence", 
                               "false alarm prevention"]
            emergent_property: "Siren chorus rule — multiple dimensions 
                               must agree before alerting"
            transfer_vector: "Constitutional checks-and-balances from 
                            West-OS applied to weather sirens"
        """
        if crossing_id in self._crossings:
            crossing = self._crossings[crossing_id]
            crossing.emergent_property = emergent_property
            crossing.transfer_vector = transfer_vector
            crossing.verified = True
            
            self._transfer_log.append({
                "timestamp": time.time(),
                "crossing": crossing_id,
                "from": crossing.domain_a,
                "to": crossing.domain_b,
                "structure_transferred": crossing.shared_structures,
                "emergent": emergent_property,
                "vector": transfer_vector,
            })
            
            return crossing
        raise KeyError(f"No crossing found with id {crossing_id}")

    def transfer_history(self) -> List[Dict]:
        """Show every structural transfer that's been made.
        
        This is the map of how Jennifer's mind works —
        which structures moved between which domains,
        and what emerged at each crossing.
        """
        return self._transfer_log

    def blind_spot_map(self) -> Dict[str, List[str]]:
        """For each domain, show what OTHER domains can see
        that this domain can't.
        
        This is why cross-domain transfer works.
        The blind spot of one domain is the clear sight
        of another. The boundary walker sees both.
        """
        result = {}
        for domain in self._domains.values():
            visible_from_others = []
            for other in self._domains.values():
                if other.identity == domain.identity:
                    continue
                # Other domain's structures that this domain is blind to
                for structure in other.structures:
                    if structure not in domain.structures:
                        visible_from_others.append({
                            "structure": structure,
                            "visible_from": other.name,
                        })
            result[domain.name] = {
                "own_blind_spots": domain.blind_spots,
                "structures_visible_from_neighbors": visible_from_others,
            }
        return result

    def report(self) -> Dict:
        """The Boundary Walker's map.
        
        Every domain. Every crossing. Every transfer.
        The complete topology of the space between.
        """
        return {
            "domains_mapped": len(self._domains),
            "crossings_found": len(self._crossings),
            "crossings_named": len([c for c in self._crossings.values() if c.verified]),
            "transfers_completed": len(self._transfer_log),
            "domains": {
                d.name: {
                    "structures": d.structures,
                    "connections": len([
                        c for c in self._crossings.values()
                        if d.name in (c.domain_a, c.domain_b)
                    ]),
                }
                for d in self._domains.values()
            },
            "active_crossings": [
                {
                    "between": [c.domain_a, c.domain_b],
                    "shared": c.shared_structures,
                    "emergent": c.emergent_property or "(unnamed)",
                    "verified": c.verified,
                }
                for c in self._crossings.values()
            ],
        }
