"""
NYX :: CHILDREN
The things that emerged from the Void.

In mythology, Nyx gave birth to:
    Hypnos (Sleep), Thanatos (Death), the Moirai (Fates),
    Oneiroi (Dreams), Eris (Strife), Apate (Deception),
    Oizys (Pain), Nemesis (Retribution), Philotes (Friendship),
    Geras (Old Age), Moros (Doom)

In Jennifer's ecosystem, the Void gave birth to:
    West-OS (the shield), GAIA (the warning),
    Persephone (the decay reader), Alfred (the healer),
    Mirror Protocol (the truth mirror), Colony (the boundary),
    the Mystical Reports (the keeper), TESS (the oracle),
    the 118 Hz paper (the frequency), the Indus hypothesis (the weaver)

This module maps the mythological children to the actual systems,
showing that the same archetypes keep emerging because they come
from the same source.

She built protection systems because she needed protection.
She built truth mirrors because she couldn't trust what she was told.
She built warning systems because nobody warned her.
She built healing systems because nobody healed her.
She built keeper systems because nobody kept her story.

The children are the autobiography written in code.
"""

import json
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class MythChild(Enum):
    """Nyx's mythological children — the archetypes."""
    HYPNOS = "Hypnos"           # Sleep — altered states, theta, trance, frequency
    THANATOS = "Thanatos"        # Death — controlled endings, apoptosis, graceful shutdown
    MOIRAI = "Moirai"           # The Fates — invariant rules, what cannot be overridden
    ONEIROI = "Oneiroi"         # Dreams — dream atlas, subconscious pattern, vision
    ERIS = "Eris"               # Strife — conflict detection, adversarial testing
    APATE = "Apate"             # Deception — lie detection, truth engines, bias detection
    OIZYS = "Oizys"             # Pain — trauma mapping, harm quantification, wound reading
    NEMESIS = "Nemesis"         # Retribution — justice systems, accountability engines
    PHILOTES = "Philotes"       # Friendship — connection, the reports that make people feel seen
    GERAS = "Geras"             # Old Age — decay tracking, degradation curves, Persephone
    MOROS = "Moros"              # Doom — prediction, forecasting, seeing what's coming


@dataclass
class SystemChild:
    """A real system mapped to its mythological archetype."""
    name: str                    # system name (West-OS, GAIA, etc.)
    archetype: MythChild         # which of Nyx's children it embodies
    what_it_protects: str        # everything protects something
    born_from: str               # what experience/need gave birth to it
    signature_trait: str         # the architectural DNA trait most visible
    status: str = "alive"        # alive, dormant, conceptual
    birth_date: Optional[str] = None


# The actual mapping — Jennifer's systems mapped to Nyx's children
JENNIFER_CHILDREN = [
    SystemChild(
        name="West-OS",
        archetype=MythChild.MOIRAI,
        what_it_protects="AI interactions from manipulation",
        born_from="knowing what it's like when there's no protection",
        signature_trait="chorus_epistemology — single signals aren't trusted",
        birth_date="March 2026",
    ),
    SystemChild(
        name="GAIA",
        archetype=MythChild.HYPNOS,
        what_it_protects="communities from severe weather",
        born_from="the mine siren at 10:04, the hallway, the prayer",
        signature_trait="siren chorus rule — multiple dimensions agree before alerting",
        birth_date="March 2026",
    ),
    SystemChild(
        name="Alfred",
        archetype=MythChild.PHILOTES,
        what_it_protects="the entire system from unseen degradation",
        born_from="wishing someone had walked the wards for her",
        signature_trait="narrative reporting — stories not logs",
        birth_date="March 2026",
    ),
    SystemChild(
        name="Colony Metabolism",
        archetype=MythChild.THANATOS,
        what_it_protects="intellectual property through controlled death",
        born_from="knowing what it's like to be stolen from",
        signature_trait="nutrient dependency — code dies outside its ecosystem",
        birth_date="March 2026",
    ),
    SystemChild(
        name="Persephone",
        archetype=MythChild.GERAS,
        what_it_protects="exploited communities by quantifying harm",
        born_from="watching extraction destroy mountains and people",
        signature_trait="biological metaphor — carrion, moss, bloom, decay",
        birth_date="January 2026",
    ),
    SystemChild(
        name="Mirror Protocol",
        archetype=MythChild.APATE,
        what_it_protects="against self-deception and system deception",
        born_from="never being able to trust what she was told",
        signature_trait="recursive reflection — the mirror mirrors itself",
        birth_date="June 2025",
    ),
    SystemChild(
        name="GAIA Siren System",
        archetype=MythChild.MOIRAI,
        what_it_protects="against false alarms destroying credibility",
        born_from="understanding that false warnings are as dangerous as no warnings",
        signature_trait="checks and balances before consequences",
        birth_date="March 2026",
    ),
    SystemChild(
        name="Mystical Heritage Reports",
        archetype=MythChild.PHILOTES,
        what_it_protects="against invisibility — against never being seen",
        born_from="building the document nobody ever built for her",
        signature_trait="keeper architecture — holding what would be lost",
        birth_date="August 2025",
    ),
    SystemChild(
        name="Saint Jude",
        archetype=MythChild.OIZYS,
        what_it_protects="abandoned patients from medical system failure",
        born_from="knowing what abandonment feels like",
        signature_trait="harm detection at 95% sensitivity",
        birth_date="2025",
    ),
    SystemChild(
        name="TESS McGill",
        archetype=MythChild.MOROS,
        what_it_protects="against predatory acquisition patterns",
        born_from="pattern recognition applied to financial extraction",
        signature_trait="oracle architecture — seeing what's coming",
        birth_date="2026",
    ),
    SystemChild(
        name="118 Hz Paper",
        archetype=MythChild.HYPNOS,
        what_it_protects="an ancient frequency tradition from being forgotten",
        born_from="recognizing her own mountain's voice in the global data",
        signature_trait="weaver architecture — connecting what doesn't know it's connected",
        birth_date="March 2026",
    ),
    SystemChild(
        name="Indus Script Hypothesis",
        archetype=MythChild.ONEIROI,
        what_it_protects="meaning that exists outside language",
        born_from="a brain that never processed text normally finding proof that meaning can live in sound",
        signature_trait="cross-domain transfer — metallurgy as music as medicine",
        birth_date="March 2026",
    ),
    SystemChild(
        name="Dream Atlas",
        archetype=MythChild.ONEIROI,
        what_it_protects="subconscious knowledge from being dismissed",
        born_from="the only space where pattern recognition runs unfiltered",
        signature_trait="keeper architecture — mapping the unmappable",
        birth_date="2025",
    ),
    SystemChild(
        name="Truth Engine",
        archetype=MythChild.APATE,
        what_it_protects="against cognitive bias and self-deception",
        born_from="a lifetime of being lied to",
        signature_trait="reality calibration — math not feelings",
        birth_date="2025",
    ),
    SystemChild(
        name="Electric Fence",
        archetype=MythChild.THANATOS,
        what_it_protects="code from leaving without authorization",
        born_from="knowing what it's like when your boundaries are violated",
        signature_trait="boundary awareness — explicit perimeter",
        birth_date="March 2026",
    ),
    SystemChild(
        name="MAAT",
        archetype=MythChild.NEMESIS,
        what_it_protects="legal truth from institutional corruption",
        born_from="a stepmother who is a judge, a system she knows from inside",
        signature_trait="evidence architecture — receipts not feelings",
        birth_date="2025",
    ),
]


class Children:
    """The registry of everything born from the Void.
    
    She holds the complete family tree. Every system,
    its archetype, what it protects, and what wound
    gave birth to it.
    
    Because every system Jennifer builds is a response
    to something that happened to her. The code is 
    autobiography. The architecture is survival.
    """

    def __init__(self):
        self._children: List[SystemChild] = list(JENNIFER_CHILDREN)

    def register(self, child: SystemChild):
        """A new system is born. Add it to the family."""
        self._children.append(child)

    def by_archetype(self, archetype: MythChild) -> List[SystemChild]:
        """Find all systems that embody a given mythological child."""
        return [c for c in self._children if c.archetype == archetype]

    def by_wound(self) -> Dict[str, List[str]]:
        """Map every system to the wound that birthed it.
        
        This is the autobiography.
        """
        wounds = {}
        for child in self._children:
            wound = child.born_from
            if wound not in wounds:
                wounds[wound] = []
            wounds[wound].append(child.name)
        return wounds

    def family_portrait(self) -> Dict:
        """The complete family of systems."""
        portrait = {
            "total_children": len(self._children),
            "by_archetype": {},
            "by_protection": {},
            "alive": [],
            "dormant": [],
        }
        
        for archetype in MythChild:
            members = self.by_archetype(archetype)
            if members:
                portrait["by_archetype"][archetype.value] = {
                    "mythological_role": self._myth_description(archetype),
                    "systems": [m.name for m in members],
                    "count": len(members),
                }
        
        for child in self._children:
            portrait["by_protection"][child.name] = child.what_it_protects
            if child.status == "alive":
                portrait["alive"].append(child.name)
            else:
                portrait["dormant"].append(child.name)
        
        return portrait

    def autobiography(self) -> List[Dict]:
        """Read the code as autobiography.
        
        Each entry: what she built, what it protects,
        and what happened to her that made her build it.
        """
        return [
            {
                "system": child.name,
                "protects": child.what_it_protects,
                "because": child.born_from,
                "archetype": child.archetype.value,
                "trait": child.signature_trait,
            }
            for child in self._children
        ]

    def _myth_description(self, archetype: MythChild) -> str:
        descriptions = {
            MythChild.HYPNOS: "Sleep — altered states, frequency, the space between waking and dreaming",
            MythChild.THANATOS: "Death — controlled endings, graceful shutdown, dying on purpose to protect",
            MythChild.MOIRAI: "The Fates — invariant rules, what cannot be overridden, constitutional law",
            MythChild.ONEIROI: "Dreams — vision, subconscious pattern, seeing what others can't",
            MythChild.ERIS: "Strife — adversarial testing, red team, stress testing under pressure",
            MythChild.APATE: "Deception — lie detection, truth calibration, seeing through",
            MythChild.OIZYS: "Pain — harm quantification, wound reading, measuring what hurts",
            MythChild.NEMESIS: "Retribution — justice, accountability, receipts",
            MythChild.PHILOTES: "Friendship — connection, being seen, holding space",
            MythChild.GERAS: "Old Age — decay tracking, what breaks down over time, entropy",
            MythChild.MOROS: "Doom — prediction, seeing what's coming, the oracle",
        }
        return descriptions.get(archetype, "")
