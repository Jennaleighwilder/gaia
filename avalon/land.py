"""
AVALON :: THE LAND
The kingdom's territory and resources.

Every civilization needs land. Not just awareness of land —
STEWARDSHIP of it. The Real Heartbeat reads disk, memory, CPU.
The Land layer manages them. It knows what's fertile (plenty),
what's fallow (near capacity), what's sacred (frozen, never
touched), and what's wild (unmanaged, needs taming).

In agricultural societies, the land isn't just dirt. It's the
foundation of everything. The Three Sisters grow IN the land.
The Longhouse stands ON the land. The Crops feed FROM the land.
Without healthy land, nothing thrives.

In the kingdom, "land" is:
  - Disk space (the soil — where everything grows)
  - Memory (the water — flows through everything, limited)
  - CPU (the sunlight — powers all activity, shared)
  - File system (the terrain — where things are planted)
  - Ports (the roads — how systems connect)

The Land Steward surveys, allocates, and protects.
She knows what can be planted where.
She knows when the soil is exhausted.
She knows what's sacred and must not be plowed.

© 2026 Jennifer Leigh West. All rights reserved.
"""

import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class SoilHealth(Enum):
    FERTILE = "fertile"       # >50% available — plant freely
    ADEQUATE = "adequate"     # 25-50% available — plant carefully
    FALLOW = "fallow"         # 10-25% available — rest the land
    EXHAUSTED = "exhausted"   # <10% available — emergency


@dataclass
class Territory:
    """A piece of land the kingdom manages."""
    name: str
    path: str
    sacred: bool = False          # frozen, never modified
    total_bytes: int = 0
    used_bytes: int = 0
    available_bytes: int = 0

    @property
    def health(self) -> SoilHealth:
        if self.total_bytes == 0:
            return SoilHealth.ADEQUATE
        ratio = self.available_bytes / self.total_bytes
        if ratio > 0.50:
            return SoilHealth.FERTILE
        elif ratio > 0.25:
            return SoilHealth.ADEQUATE
        elif ratio > 0.10:
            return SoilHealth.FALLOW
        return SoilHealth.EXHAUSTED

    @property
    def usage_ratio(self) -> float:
        if self.total_bytes == 0:
            return 0
        return self.used_bytes / self.total_bytes


class LandSteward:
    """Surveys, allocates, and protects the kingdom's resources.

    The Land Steward knows:
    - How much disk, memory, CPU the kingdom has
    - Which directories are sacred (frozen, GAIA)
    - Which directories are wild (unmanaged)
    - What can be planted where
    - When the soil is exhausted
    """

    def __init__(self, project_root: Optional[str] = None,
                 sacred_paths: Optional[List[str]] = None):
        self._root = Path(project_root) if project_root else Path.cwd()
        self._sacred = set(sacred_paths or [])
        self._territories: Dict[str, Territory] = {}
        self._survey_history: List[Dict] = []

    def survey(self) -> Dict:
        """Survey all the land. Returns the complete territory map."""
        self._territories = {}

        # ── DISK (the soil) ──
        disk = self._survey_disk()

        # ── MEMORY (the water) ──
        water = self._survey_memory()

        # ── CPU (the sunlight) ──
        sun = self._survey_cpu()

        # ── TERRITORIES (individual plots) ──
        territories = self._survey_territories()

        survey = {
            "time": time.time(),
            "soil": disk,
            "water": water,
            "sun": sun,
            "territories": territories,
            "sacred_count": len([t for t in self._territories.values() if t.sacred]),
            "overall_health": self._overall_health(disk, water, sun),
        }

        self._survey_history.append(survey)
        if len(self._survey_history) > 50:
            self._survey_history = self._survey_history[-50:]

        return survey

    def _survey_disk(self) -> Dict:
        """Survey the soil — disk space."""
        try:
            usage = shutil.disk_usage(str(self._root))
            health = SoilHealth.FERTILE
            ratio = usage.free / usage.total
            if ratio < 0.10:
                health = SoilHealth.EXHAUSTED
            elif ratio < 0.25:
                health = SoilHealth.FALLOW
            elif ratio < 0.50:
                health = SoilHealth.ADEQUATE

            return {
                "total_gb": round(usage.total / (1024**3), 1),
                "used_gb": round(usage.used / (1024**3), 1),
                "free_gb": round(usage.free / (1024**3), 1),
                "usage_percent": round(usage.used / usage.total * 100, 1),
                "health": health.value,
            }
        except Exception:
            return {"health": "unknown", "error": "could not read disk"}

    def _survey_memory(self) -> Dict:
        """Survey the water — RAM."""
        if not HAS_PSUTIL:
            return {"health": "unknown", "error": "psutil not available"}
        try:
            mem = psutil.virtual_memory()
            health = SoilHealth.FERTILE
            if mem.percent > 90:
                health = SoilHealth.EXHAUSTED
            elif mem.percent > 75:
                health = SoilHealth.FALLOW
            elif mem.percent > 50:
                health = SoilHealth.ADEQUATE

            return {
                "total_gb": round(mem.total / (1024**3), 1),
                "available_gb": round(mem.available / (1024**3), 1),
                "used_percent": round(mem.percent, 1),
                "health": health.value,
            }
        except Exception:
            return {"health": "unknown"}

    def _survey_cpu(self) -> Dict:
        """Survey the sunlight — CPU."""
        if not HAS_PSUTIL:
            return {"health": "unknown", "error": "psutil not available"}
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            health = SoilHealth.FERTILE
            if cpu_percent > 90:
                health = SoilHealth.EXHAUSTED
            elif cpu_percent > 75:
                health = SoilHealth.FALLOW
            elif cpu_percent > 50:
                health = SoilHealth.ADEQUATE

            return {
                "cores": psutil.cpu_count(),
                "usage_percent": round(cpu_percent, 1),
                "health": health.value,
            }
        except Exception:
            return {"health": "unknown"}

    def _survey_territories(self) -> Dict:
        """Survey individual territories — key directories."""
        plots = {}

        # Kingdom root
        plots["kingdom"] = self._measure_territory(
            "kingdom", str(self._root), sacred=False
        )

        # Sacred territories
        frozen = self._root / "frozen" / "west-os"
        if frozen.exists():
            plots["frozen_west_os"] = self._measure_territory(
                "frozen_west_os", str(frozen), sacred=True
            )

        # GAIA
        gaia = Path.home() / "gaia"
        if gaia.exists():
            plots["gaia"] = self._measure_territory(
                "gaia", str(gaia), sacred=True
            )

        # Memory
        memory = self._root / "memory"
        if memory.exists():
            plots["memory"] = self._measure_territory(
                "memory", str(memory), sacred=False
            )

        # Tests
        tests = self._root / "tests"
        if tests.exists():
            plots["tests"] = self._measure_territory(
                "tests", str(tests), sacred=False
            )

        return plots

    def _measure_territory(self, name: str, path: str, sacred: bool) -> Dict:
        """Measure a single territory."""
        p = Path(path)
        if not p.exists():
            return {"name": name, "exists": False}

        total_size = 0
        file_count = 0
        try:
            for f in p.rglob("*"):
                if f.is_file():
                    try:
                        total_size += f.stat().st_size
                        file_count += 1
                    except (PermissionError, OSError):
                        pass
        except (PermissionError, OSError):
            pass

        territory = Territory(
            name=name, path=path, sacred=sacred,
            total_bytes=total_size, used_bytes=total_size,
        )
        self._territories[name] = territory

        return {
            "name": name,
            "path": path,
            "sacred": sacred,
            "size_mb": round(total_size / (1024*1024), 1),
            "files": file_count,
            "exists": True,
        }

    def _overall_health(self, disk: Dict, memory: Dict, cpu: Dict) -> str:
        """Overall land health based on all resources."""
        healths = []
        for resource in [disk, memory, cpu]:
            h = resource.get("health", "unknown")
            if h == "exhausted":
                healths.append(0)
            elif h == "fallow":
                healths.append(1)
            elif h == "adequate":
                healths.append(2)
            elif h == "fertile":
                healths.append(3)

        if not healths:
            return "unknown"

        avg = sum(healths) / len(healths)
        if avg >= 2.5:
            return "thriving"
        elif avg >= 1.5:
            return "sustaining"
        elif avg >= 0.5:
            return "struggling"
        return "barren"

    def can_plant(self, needed_mb: float = 100) -> Tuple[bool, str]:
        """Can we plant something new? Is there room?"""
        survey = self.survey()
        free_gb = survey["soil"].get("free_gb", 0)
        needed_gb = needed_mb / 1024

        if free_gb > needed_gb * 2:
            return True, f"Fertile soil. {free_gb:.1f}GB free. Plant freely."
        elif free_gb > needed_gb:
            return True, f"Adequate soil. {free_gb:.1f}GB free. Plant carefully."
        else:
            return False, f"Soil exhausted. Only {free_gb:.1f}GB free. Clear deadwood first."

    @property
    def status(self) -> Dict:
        if self._survey_history:
            latest = self._survey_history[-1]
            return {
                "overall": latest.get("overall_health", "unknown"),
                "disk_health": latest["soil"].get("health", "unknown"),
                "memory_health": latest["water"].get("health", "unknown"),
                "cpu_health": latest["sun"].get("health", "unknown"),
                "territories": len(self._territories),
                "sacred_territories": len([t for t in self._territories.values() if t.sacred]),
            }
        return {"overall": "unsurveyed"}


def wire_land(avalon) -> LandSteward:
    """Create a Land Steward for the kingdom."""
    root = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sacred = [
        str(root / "frozen" / "west-os"),
        str(Path.home() / "gaia"),
    ]
    return LandSteward(project_root=str(root), sacred_paths=sacred)


def demo():
    print("\n" + "=" * 60)
    print("  T H E   L A N D")
    print("  The Kingdom's Territory and Resources")
    print("=" * 60)

    steward = LandSteward()
    survey = steward.survey()

    print(f"\n  SOIL (Disk):")
    s = survey["soil"]
    print(f"    Total: {s.get('total_gb', '?')}GB")
    print(f"    Free: {s.get('free_gb', '?')}GB")
    print(f"    Health: {s.get('health', '?')}")

    print(f"\n  WATER (Memory):")
    w = survey["water"]
    print(f"    Total: {w.get('total_gb', '?')}GB")
    print(f"    Available: {w.get('available_gb', '?')}GB")
    print(f"    Health: {w.get('health', '?')}")

    print(f"\n  SUNLIGHT (CPU):")
    c = survey["sun"]
    print(f"    Cores: {c.get('cores', '?')}")
    print(f"    Usage: {c.get('usage_percent', '?')}%")
    print(f"    Health: {c.get('health', '?')}")

    print(f"\n  TERRITORIES:")
    for name, data in survey["territories"].items():
        sacred = " [SACRED]" if data.get("sacred") else ""
        print(f"    {name}: {data.get('size_mb', 0):.1f}MB, {data.get('files', 0)} files{sacred}")

    print(f"\n  Overall: {survey['overall_health']}")

    can, reason = steward.can_plant(100)
    print(f"  Can plant: {reason}")

    print(f"\n" + "=" * 60)
    print(f"  The Land Steward knows the soil, the water, the sun.")
    print(f"  She knows what's sacred and what can be plowed.")
    print(f"  She knows when to plant and when to rest.")
    print(f"=" * 60 + "\n")


if __name__ == "__main__":
    demo()
