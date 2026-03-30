"""
COLONY BRIDGE
Nyx Blessing <-> Colony Metabolism Nutrients

This bridge does not modify frozen Colony code.
It adds Nyx blessing verification as a fifth local nutrient signal.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, Optional


FROZEN_WESTOS = Path(__file__).parent.parent / "frozen" / "west-os"


class ColonyBridge:
    """Nyx blessing as a Colony nutrient source."""

    def __init__(self, nyx_instance=None):
        self._nyx = nyx_instance
        self._frozen_path = FROZEN_WESTOS
        self._colony_path = None

        candidates = list(self._frozen_path.rglob("colony_metabolism.py"))
        if candidates:
            self._colony_path = candidates[0]

    @property
    def is_available(self) -> bool:
        return self._colony_path is not None

    def check_nyx_nutrient(self, system_name: str, claimed_blessing: str) -> Dict[str, Any]:
        """Check whether Nyx's blessing is valid for a system."""
        if not self._nyx:
            return {
                "nutrient": "nyx_blessing",
                "score": 0.0,
                "valid": False,
                "reason": "Nyx not connected",
                "weight": 0.30,
            }

        valid = self._nyx.root.verify_blessing(system_name, claimed_blessing)
        return {
            "nutrient": "nyx_blessing",
            "score": 1.0 if valid else 0.0,
            "valid": valid,
            "weight": 0.30,
            "checked_at": time.time(),
            "reason": "blessing verified" if valid else "blessing invalid or revoked",
        }

    def combined_assessment(
        self,
        system_name: str,
        claimed_blessing: str,
        colony_tier: str = "UNKNOWN",
    ) -> Dict[str, Any]:
        """Combine frozen Colony assessment with Nyx blessing state."""
        nyx_nutrient = self.check_nyx_nutrient(system_name, claimed_blessing)

        if not nyx_nutrient.get("valid", False):
            combined_tier = "RESTRICTED"
            reason = "Nyx blessing invalid - system restricted regardless of Colony status"
        elif colony_tier == "INERT":
            combined_tier = "INERT"
            reason = "Colony reports INERT - system has no nutrients"
        elif colony_tier == "DEGRADED":
            combined_tier = "DEGRADED"
            reason = "Colony reports DEGRADED - Nyx blessing valid but Colony nutrients low"
        else:
            combined_tier = colony_tier if colony_tier != "UNKNOWN" else "FULL"
            reason = "All nutrients healthy"

        return {
            "system": system_name,
            "colony_tier": colony_tier,
            "nyx_blessing": nyx_nutrient,
            "combined_tier": combined_tier,
            "reason": reason,
            "assessed_at": time.time(),
        }

    def inventory(self) -> Dict[str, Any]:
        """What Colony files exist in the frozen clone."""
        colony_files = list(self._frozen_path.rglob("*colony*"))
        return {
            "colony_found": self._colony_path is not None,
            "path": (
                str(self._colony_path.relative_to(self._frozen_path))
                if self._colony_path
                else None
            ),
            "related_files": [str(f.relative_to(self._frozen_path)) for f in colony_files],
        }
