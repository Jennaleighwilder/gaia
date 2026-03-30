"""
KAY ADAPTER
Nyx <-> Alfred

Reads Alfred's ward walk results from the frozen clone.
Can inspect Alfred's patrol logic in read-only mode.
Kay is the seneschal - keeps the house running.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


FROZEN_WESTOS = Path(__file__).parent.parent / "frozen" / "west-os"


class KayAdapter:
    """Read-only bridge to Alfred's ward system."""

    def __init__(self):
        self._frozen_path = FROZEN_WESTOS
        self._alfred_path = None

        candidates = list(self._frozen_path.rglob("alfred.py"))
        if candidates:
            self._alfred_path = candidates[0]

    @property
    def is_available(self) -> bool:
        return self._alfred_path is not None

    def read_ward_list(self) -> Dict[str, Any]:
        """Read which wards Alfred patrols."""
        if not self._alfred_path:
            return {"available": False, "wards": []}

        try:
            content = self._alfred_path.read_text()
        except Exception as exc:
            return {"available": False, "error": str(exc)}

        wards = []
        for line in content.splitlines():
            lower = line.lower()
            for ward_name in [
                "archivist",
                "botanist",
                "quartermaster",
                "sentinel",
                "surgeon",
                "scout",
            ]:
                if ward_name in lower and ward_name not in wards:
                    wards.append(ward_name)

        return {
            "available": True,
            "alfred_path": str(self._alfred_path.relative_to(self._frozen_path)),
            "wards_found": wards,
            "frozen": True,
        }

    def inventory(self) -> Dict[str, Any]:
        """What Alfred-related files exist in the frozen clone."""
        alfred_files = list(self._frozen_path.rglob("*alfred*"))
        return {
            "files": [str(f.relative_to(self._frozen_path)) for f in alfred_files],
            "count": len(alfred_files),
        }
