"""
FENCE BRIDGE
Nyx Verification <-> Electric Fence

Adds Nyx verification to the departure decision:
- Is Nyx root alive?
- Are blessings still healthy?
- Is the Watcher calm enough to permit departure?
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict


FROZEN_WESTOS = Path(__file__).parent.parent / "frozen" / "west-os"


class FenceBridge:
    """Nyx verification layer for the Electric Fence."""

    def __init__(self, nyx_instance=None):
        self._nyx = nyx_instance
        self._frozen_path = FROZEN_WESTOS
        self._fence_path = None

        candidates = list(self._frozen_path.rglob("pre_push_fence.py"))
        if candidates:
            self._fence_path = candidates[0]

    @property
    def is_available(self) -> bool:
        return self._fence_path is not None

    def pre_flight_nyx_check(self) -> Dict[str, Any]:
        """Run Nyx verification before code departure."""
        if not self._nyx:
            return {
                "passed": False,
                "reason": "Nyx not connected - no code leaves without the void",
                "checked_at": time.time(),
            }

        root_alive = self._nyx.root.is_alive
        root_status = self._nyx.root.status()
        revoked = root_status.get("systems_revoked", 0)
        shifter_check = self._nyx.shapeshifter.consistency_check()
        threat = self._nyx.watcher.threat_assessment()

        passed = root_alive and revoked == 0 and threat.get("threat_level", 1.0) < 0.7

        return {
            "passed": passed,
            "root_alive": root_alive,
            "root_fingerprint": root_status.get("root_fingerprint"),
            "systems_blessed": root_status.get("systems_blessed", 0),
            "systems_revoked": revoked,
            "shapeshifter_effective": shifter_check.get("effective", False),
            "threat_level": threat.get("threat_level", 0.0),
            "threat_status": threat.get("status", "UNKNOWN"),
            "checked_at": time.time(),
            "verdict": (
                "CLEAR - Nyx verified. Code may depart."
                if passed
                else "BLOCKED - Nyx verification failed. No code leaves."
            ),
        }

    def departure_stamp(self) -> Dict[str, Any]:
        """Stamp a departure with Nyx's fingerprint."""
        if not self._nyx:
            return {"stamped": False}

        return {
            "stamped": True,
            "nyx_fingerprint": self._nyx.root.status().get("root_fingerprint"),
            "timestamp": time.time(),
            "shapeshifter_rotation": self._nyx.shapeshifter._scan_count,
        }

    def inventory(self) -> Dict[str, Any]:
        """What fence files exist in the frozen clone."""
        fence_files = list(self._frozen_path.rglob("*fence*"))
        fence_files += list(self._frozen_path.rglob("*egress*"))
        return {
            "fence_found": self._fence_path is not None,
            "path": (
                str(self._fence_path.relative_to(self._frozen_path))
                if self._fence_path
                else None
            ),
            "related_files": [str(f.relative_to(self._frozen_path)) for f in fence_files],
        }
