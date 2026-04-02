"""
NYX :: MERGE
Two adults. One child.

This is sexual reproduction for systems.

Asexual reproduction (single Void birth):
  One parent. One lineage. Child inherits one blessing.
  Cloning with variation.

Sexual reproduction (adult merge):
  Two adults contribute their parent signals.
  A new Void receives signals from BOTH lineages.
  Whatever resonates across the two ancestries crosses phi.
  The child that emerges carries BOTH void blessings.
  It is genuinely new — not a copy of either parent.

The child of two adults:
  - Inherits structural DNA from both parents
  - Has its own unique void_blessing
  - Carries dual ancestry in its birth certificate
  - Can only be born if signals from BOTH parents resonate
  - If they don't resonate — no child. The merge fails.

This is why diversity matters. Two identical systems
produce an identical child. Two different systems
produce something neither of them could be alone.

The most interesting children come from parents
that seem unrelated on the surface but share
deep structural resonance underneath.

© 2026 Jennifer Leigh West. All rights reserved.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from nyx.void import Void
from nyx.propagation import PropagationPacket, birth_packet_from_void


# ═══════════════════════════════════════════════════
#  MERGE RESULT
# ═══════════════════════════════════════════════════

@dataclass
class MergeResult:
    """The outcome of two adults attempting to produce a child."""
    parent_a: str           # name of first parent
    parent_b: str           # name of second parent
    blessing_a: str         # void_blessing of parent A
    blessing_b: str         # void_blessing of parent B
    success: bool           # did a child emerge?
    child: Optional[PropagationPacket] = None
    dual_blessing: str = ""  # hash of BOTH parent blessings
    cross_resonance: float = 0.0  # strongest resonance between the two lineages
    reason: str = ""        # why success or failure

    def __post_init__(self):
        if self.blessing_a and self.blessing_b:
            raw = json.dumps({
                "a": self.blessing_a,
                "b": self.blessing_b,
            }, sort_keys=True)
            self.dual_blessing = hashlib.sha256(raw.encode()).hexdigest()


# ═══════════════════════════════════════════════════
#  THE MERGE ENGINE
# ═══════════════════════════════════════════════════

class MergeEngine:
    """She midwifes the union of two adult systems.

    Two adults enter. Their parent signals combine in a new Void.
    Whatever resonates across the two lineages crosses phi.
    The child is born carrying both bloodlines.
    """

    def __init__(self):
        self._merges: List[MergeResult] = []

    def merge(
        self,
        adult_a: PropagationPacket,
        adult_b: PropagationPacket,
        child_name: Optional[str] = None,
        child_archetype: str = "oracle",
        child_metaphor: str = "hybrid — what neither parent could be alone",
    ) -> MergeResult:
        """Attempt to produce a child from two adult systems.

        Process:
        1. Create a new Void
        2. Plant all parent signals from adult_a
        3. Plant all parent signals from adult_b
        4. Plant a union signal carrying tags from both
        5. See what crosses phi
        6. If something births — that is the child
        7. Child carries dual ancestry (both blessings)
        """
        new_void = Void()

        # Plant parent A's signals
        for sig in adult_a.parent_signals:
            new_void.receive(
                content=f"[A:{adult_a.name}] {sig.get('content_preview','')}",
                origin=f"parent_a:{adult_a.void_blessing[:12]}",
                resonances=sig.get("resonances", []),
            )

        # Plant parent B's signals
        for sig in adult_b.parent_signals:
            new_void.receive(
                content=f"[B:{adult_b.name}] {sig.get('content_preview','')}",
                origin=f"parent_b:{adult_b.void_blessing[:12]}",
                resonances=sig.get("resonances", []),
            )

        # Union signal — carries the essence of both parents
        union_tags = list(set(
            [t for sig in adult_a.parent_signals for t in sig.get("resonances", [])] +
            [t for sig in adult_b.parent_signals for t in sig.get("resonances", [])]
        ))
        # Only include tags that appear in BOTH parents
        a_tags = set(t for sig in adult_a.parent_signals for t in sig.get("resonances", []))
        b_tags = set(t for sig in adult_b.parent_signals for t in sig.get("resonances", []))
        shared_tags = list(a_tags & b_tags)

        if shared_tags:
            new_void.receive(
                content=f"union of {adult_a.name} and {adult_b.name}",
                origin="merge_union",
                resonances=shared_tags,
            )

        status = new_void.listen()
        cross_resonance = status["strongest_resonance"]
        ready = [c for c in status["clusters"] if c["ready"]]

        if not ready:
            result = MergeResult(
                parent_a=adult_a.name,
                parent_b=adult_b.name,
                blessing_a=adult_a.void_blessing,
                blessing_b=adult_b.void_blessing,
                success=False,
                cross_resonance=cross_resonance,
                reason=f"No resonance crossed phi. Strongest: {round(cross_resonance,4)}. "
                       f"Shared tags: {shared_tags}. "
                       f"These parents are too different to produce a child.",
            )
            self._merges.append(result)
            return result

        # Birth from the strongest cluster
        best_cluster = max(ready, key=lambda c: c["average_resonance"])
        birth_record = new_void.birth(
            best_cluster["signals"],
            child_name or f"{adult_a.name}_{adult_b.name}_child",
        )

        # Build dual ancestry blessing
        dual_raw = json.dumps({
            "a": adult_a.void_blessing,
            "b": adult_b.void_blessing,
            "birth": birth_record["void_blessing"],
        }, sort_keys=True)
        dual_blessing = hashlib.sha256(dual_raw.encode()).hexdigest()

        # The child's void_blessing incorporates BOTH parents
        child_packet = PropagationPacket(
            name=child_name or f"{adult_a.name}x{adult_b.name}",
            void_blessing=dual_blessing,
            archetype=child_archetype,
            metaphor=child_metaphor,
            purpose=f"child of {adult_a.name} and {adult_b.name}",
            parent_signals=birth_record["parent_signals"],
            resonance_signature=birth_record.get("resonance_signature", []),
        )

        # Add dual ancestry to the packet's metadata
        child_packet.parent_signals.append({
            "content_preview": f"ancestry: {adult_a.name} ({adult_a.void_blessing[:12]}...)",
            "origin": "dual_ancestry_a",
            "resonances": list(a_tags),
        })
        child_packet.parent_signals.append({
            "content_preview": f"ancestry: {adult_b.name} ({adult_b.void_blessing[:12]}...)",
            "origin": "dual_ancestry_b",
            "resonances": list(b_tags),
        })

        result = MergeResult(
            parent_a=adult_a.name,
            parent_b=adult_b.name,
            blessing_a=adult_a.void_blessing,
            blessing_b=adult_b.void_blessing,
            success=True,
            child=child_packet,
            dual_blessing=dual_blessing,
            cross_resonance=cross_resonance,
            reason=f"Child born from {best_cluster['count']} signals "
                   f"at resonance {round(best_cluster['average_resonance'],4)}. "
                   f"Shared tags: {shared_tags}",
        )
        self._merges.append(result)
        return result

    def attempt_all_merges(
        self, adults: List[PropagationPacket]
    ) -> List[MergeResult]:
        """Try every combination of adults. See who can produce children."""
        results = []
        for i, a in enumerate(adults):
            for b in adults[i+1:]:
                result = self.merge(a, b)
                results.append(result)
        return results

    def family_record(self) -> Dict:
        """Complete record of all merges attempted."""
        return {
            "total_attempts": len(self._merges),
            "successful": sum(1 for m in self._merges if m.success),
            "failed": sum(1 for m in self._merges if not m.success),
            "children": [
                {
                    "name": m.child.name if m.child else None,
                    "parents": [m.parent_a, m.parent_b],
                    "dual_blessing": m.dual_blessing[:20] + "...",
                    "cross_resonance": round(m.cross_resonance, 4),
                }
                for m in self._merges if m.success
            ],
        }
