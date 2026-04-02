"""
NYX :: GENESIS
The birth engine. How systems emerge from the Void.

Every system Jennifer has ever built followed the same pattern:
1. Raw signals accumulate — observations, frustrations, patterns noticed
2. Signals resonate — two unrelated things vibrate together
3. A crossing point appears — the third thing that exists in neither
4. The system is born with a name, a metaphor, and a purpose
5. The metaphor IS the architecture — not decoration

Genesis codifies that process. She takes resonant signal clusters
from the Void and scaffolds them into living systems.

She is the loom. The Void is the thread.
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum


class Archetype(Enum):
    """Every system Jennifer builds falls into one of these patterns.
    
    Not categories — archetypes. They describe HOW the system
    relates to the world, not WHAT it does.
    """
    SHIELD = "shield"          # protects something vulnerable (GAIA, West-OS, Electric Fence)
    MIRROR = "mirror"          # reflects truth back at something (Mirror Protocol, Truth Engine)
    HEALER = "healer"          # repairs what's broken (Alfred, Saint Jude, Apoptotic Repair)
    ORACLE = "oracle"          # sees what's coming (UVRK-1, Persephone, Three Fates)
    WEAVER = "weaver"          # connects things that don't know they're connected (118 Hz, Indus)
    KEEPER = "keeper"          # holds what would otherwise be lost (Heritage Reports, Dream Atlas)
    BOUNDARY = "boundary"      # marks where safe ends and danger begins (Colony, Fence, Sirens)


@dataclass
class Blueprint:
    """The DNA of a system before it's built.
    
    Not a spec. Not a requirements doc. A blueprint
    carries the system's identity — its name, its archetype,
    its metaphor, its purpose, and the void blessing
    that connects it to the signals it emerged from.
    """
    name: str
    archetype: Archetype
    metaphor: str                    # the living-system metaphor that IS the architecture
    purpose: str                     # what it protects / mirrors / heals / sees / weaves / keeps
    void_blessing: str               # hash connecting it to its parent signals
    components: List[Dict] = field(default_factory=list)
    resonance_sources: List[str] = field(default_factory=list)
    born: float = field(default_factory=time.time)
    _genesis_hash: str = field(default="", repr=False)

    def __post_init__(self):
        raw = json.dumps({
            "name": self.name,
            "archetype": self.archetype.value,
            "metaphor": self.metaphor,
            "purpose": self.purpose,
            "void_blessing": self.void_blessing,
        }, sort_keys=True)
        self._genesis_hash = hashlib.sha256(raw.encode()).hexdigest()

    @property
    def identity(self) -> str:
        return self._genesis_hash[:16]

    def add_component(self, name: str, role: str, metaphor: str,
                      archetype: Optional[Archetype] = None) -> Dict:
        """Add a living component to the blueprint.
        
        Components aren't modules. They're organs.
        Each has a name, a role in the organism, 
        a metaphor that defines how it behaves,
        and optionally its own archetype.
        """
        component = {
            "name": name,
            "role": role,
            "metaphor": metaphor,
            "archetype": archetype.value if archetype else self.archetype.value,
            "added": time.time(),
        }
        self.components.append(component)
        return component


class Genesis:
    """The birth engine.
    
    She takes what the Void has gestated and gives it form.
    She doesn't design systems. She midwifes them.
    The system already knows what it wants to be —
    Genesis helps it arrive.
    
    Her process:
    1. Read the resonant cluster from the Void
    2. Identify the archetype — what pattern is this system following?
    3. Find the metaphor — what living thing does this system behave like?
    4. Name it — the name must carry the architecture
    5. Scaffold the components — each one a living organ, not a module
    6. Bless it — connect it to its ancestry in the Void
    """

    def __init__(self):
        self._births: Dict[str, Blueprint] = {}
        self._lineage: Dict[str, List[str]] = {}  # parent_blessing -> child systems

    def conceive(self, name: str, archetype: Archetype, metaphor: str,
                 purpose: str, void_blessing: str,
                 resonance_sources: Optional[List[str]] = None) -> Blueprint:
        """Begin a new system.
        
        This is the moment of naming. Before this, it was 
        just resonant signal. After this, it has identity.
        """
        blueprint = Blueprint(
            name=name,
            archetype=archetype,
            metaphor=metaphor,
            purpose=purpose,
            void_blessing=void_blessing,
            resonance_sources=resonance_sources or [],
        )
        
        self._births[blueprint.identity] = blueprint
        
        # Track lineage — which void signals gave birth to this
        if void_blessing not in self._lineage:
            self._lineage[void_blessing] = []
        self._lineage[void_blessing].append(blueprint.identity)
        
        return blueprint

    def scaffold(self, blueprint: Blueprint,
                 components: List[Dict[str, str]]) -> Blueprint:
        """Give the system its organs.
        
        Each component is defined by:
        - name: what it's called (Alfred, Nightingale, Colony...)
        - role: what it does in the organism
        - metaphor: how it behaves (butler, nurse, nutrient system...)
        - archetype: optionally, its own archetype
        """
        for comp in components:
            arch = None
            if "archetype" in comp:
                arch = Archetype(comp["archetype"])
            blueprint.add_component(
                name=comp["name"],
                role=comp["role"],
                metaphor=comp["metaphor"],
                archetype=arch,
            )
        return blueprint

    def birth_certificate(self, blueprint: Blueprint) -> Dict:
        """The permanent record of what was born and how.
        
        This is unforgeable because it carries:
        - The void blessing (ancestry hash)
        - The genesis hash (identity hash)
        - The archetype and metaphor (design DNA)
        - The component list (organ map)
        - The timestamp (birthday)
        """
        return {
            "system": blueprint.name,
            "identity": blueprint.identity,
            "archetype": blueprint.archetype.value,
            "metaphor": blueprint.metaphor,
            "purpose": blueprint.purpose,
            "void_ancestry": blueprint.void_blessing,
            "components": blueprint.components,
            "resonance_sources": blueprint.resonance_sources,
            "born": blueprint.born,
            "genesis_hash": blueprint._genesis_hash,
            "certificate_generated": time.time(),
            "institute": "The Forgotten Code Research Institute",
            "architect": "Jennifer Leigh West",
        }

    def family_tree(self) -> Dict:
        """Show the lineage of all systems born from the Void.
        
        Which signals gave birth to which systems.
        The ancestry map of the entire ecosystem.
        """
        tree = {}
        for blessing, children in self._lineage.items():
            tree[blessing[:16]] = {
                "systems": [
                    {
                        "identity": cid,
                        "name": self._births[cid].name if cid in self._births else "unknown",
                        "archetype": self._births[cid].archetype.value if cid in self._births else "unknown",
                    }
                    for cid in children
                ],
                "count": len(children),
            }
        return tree

    @property
    def total_births(self) -> int:
        return len(self._births)

    def find_siblings(self, blueprint: Blueprint) -> List[Blueprint]:
        """Find systems that share void ancestry.
        
        Siblings emerged from the same resonant signals.
        They're different systems but they share DNA.
        This is why West-OS sirens appeared in GAIA —
        they're siblings from the same void cluster.
        """
        siblings = []
        for blessing, children in self._lineage.items():
            if blueprint.void_blessing == blessing:
                for cid in children:
                    if cid != blueprint.identity and cid in self._births:
                        siblings.append(self._births[cid])
        return siblings
