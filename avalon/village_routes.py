"""
AVALON :: VILLAGE ROUTES
Client-facing service routes for the kingdom.

Every route is guarded by the Castle gates.
Every successful request increments the Village census.
The free paths remain free by sovereign decree.

© 2026 Jennifer Leigh West. All rights reserved.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from fastapi import FastAPI, HTTPException
except ImportError:  # pragma: no cover
    FastAPI = None  # type: ignore
    HTTPException = RuntimeError  # type: ignore

from avalon.avalon import Avalon, found_on_nyx


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DATA = REPO_ROOT / "docs" / "data"


class _StubApp:
    def get(self, *args, **kwargs):
        def decorator(fn):
            return fn

        return decorator


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


class VillageGateway:
    """Guarded entry to the Village services."""

    def __init__(self, avalon: Optional[Avalon] = None):
        self.avalon = avalon or found_on_nyx(
            os.environ.get("WEST_OS_GUARD_SECRET") or "avalon_village_demo"
        )
        if self.avalon._sovereign is None:
            self.avalon.found_kingdom()

    def _ensure_gates_open(self):
        if self.avalon.castle.status["gates"] != "open":
            raise HTTPException(status_code=503, detail="Castle gates are sealed")

    def service_status(self) -> Dict[str, Any]:
        census = self.avalon.village.census()
        return {
            "gates": self.avalon.castle.status["gates"],
            "services": census["services"],
            "people_served": census["total_people_served"],
            "satisfaction_rate": census["satisfaction_rate"],
            "directory": census["directory"],
        }

    def heritage_reading(self, subject: str, question: str = "Heritage reading request") -> Dict[str, Any]:
        self._ensure_gates_open()
        service = self.avalon.village.serve("Heritage Readings")
        result = self.avalon.knighthood.summon("Morgana").serve(
            {"subject": subject, "text": question}
        )
        return {
            "service": service,
            "subject": subject,
            "report": result.get("output", {}).get("report", {}),
        }

    def weather_warnings(self) -> Dict[str, Any]:
        self._ensure_gates_open()
        service = self.avalon.village.serve("Weather Warnings")
        return {
            "service": service,
            "alerts": _read_json(DOCS_DATA / "dashboard_alerts.json"),
            "tess": _read_json(DOCS_DATA / "live_tess.json"),
        }

    def ai_consulting(self) -> Dict[str, Any]:
        self._ensure_gates_open()
        service = self.avalon.village.serve("AI Consulting")
        return {
            "service": service,
            "portfolio": [
                {"name": "GAIA", "focus": "atmospheric intelligence and warning systems"},
                {"name": "West-OS", "focus": "governance and constitutional AI enforcement"},
                {"name": "Nyx", "focus": "root authority, blessing, and ecosystem integrity"},
                {"name": "Avalon", "focus": "multi-system orchestration and consensus"},
            ],
        }

    def community_guides(self) -> Dict[str, Any]:
        self._ensure_gates_open()
        service = self.avalon.village.serve("Community Guides")
        return {
            "service": service,
            "free": True,
            "resources": [
                {"title": "GAIA System Summary", "path": str(REPO_ROOT / "docs" / "GAIA_SYSTEM_SUMMARY.md")},
                {"title": "GAIA Press Summary", "path": str(REPO_ROOT / "docs" / "GAIA_PRESS_SUMMARY.md")},
                {"title": "Whiteboard Build Spec", "path": str(REPO_ROOT / "docs" / "WHITEBOARD_BUILD_SPEC.md")},
            ],
            "decree": "These guides remain free to the village.",
        }


def build_app(avalon: Optional[Avalon] = None):
    gateway = VillageGateway(avalon)
    app = FastAPI(title="Avalon Village", version="1.0.0") if FastAPI is not None else _StubApp()

    @app.get("/village/status")
    def village_status():
        return gateway.service_status()

    @app.get("/village/heritage")
    def heritage(subject: str = "the seeker", question: str = "What lineage is calling?"):
        return gateway.heritage_reading(subject, question)

    @app.get("/village/weather")
    def weather():
        return gateway.weather_warnings()

    @app.get("/village/consulting")
    def consulting():
        return gateway.ai_consulting()

    @app.get("/village/community-guides")
    def community_guides():
        return gateway.community_guides()

    app.gateway = gateway  # type: ignore[attr-defined]
    return app


app = build_app()


def main() -> int:
    status = app.gateway.service_status()  # type: ignore[attr-defined]
    print()
    print("=" * 60)
    print("  VILLAGE STATUS")
    print("=" * 60)
    print()
    print(f"  Gates:              {status['gates']}")
    print(f"  Services:           {status['services']}")
    print(f"  People served:      {status['people_served']}")
    print(f"  Satisfaction rate:  {status['satisfaction_rate']:.0%}")
    print()
    for name, details in status["directory"].items():
        state = "active" if details["active"] else "suspended"
        print(f"  {name:22s} {state:10s} served={details['people_served']}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
