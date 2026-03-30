"""
AVALON :: GAIA BRIDGE
Read-only bridge to GAIA's governor.

GAIA does not live inside the kingdom repo. She lives beside it,
proven and separate. This bridge reads her state without touching
her code, starting her server, or rewriting her orders.

Two modes:
1. HTTP — prefer the running governor on 127.0.0.1:7780
2. Direct import — explicit path import of governor.py in a subprocess

© 2026 Jennifer Leigh West. All rights reserved.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional


class GaiaBridge:
    """Read-only adapter for GAIA's governor."""

    def __init__(
        self,
        gaia_path: Optional[Path] = None,
        health_url: str = "http://127.0.0.1:7780/health",
        analyze_url: str = "http://127.0.0.1:7780/analyze",
        timeout: float = 2.0,
        python_executable: Optional[str] = None,
    ):
        self.gaia_path = Path(gaia_path) if gaia_path else Path("/Users/jenniferwest/gaia")
        self.health_url = health_url
        self.analyze_url = analyze_url
        self.timeout = timeout
        self.python_executable = python_executable or sys.executable

    @property
    def governor_path(self) -> Path:
        return self.gaia_path / "runtime" / "governor" / "governor.py"

    @property
    def is_available(self) -> bool:
        return bool(self.health().get("available"))

    def health(self) -> Dict:
        """Is GAIA alive? HTTP probe or module check."""
        http = self._http_health()
        if http.get("available"):
            return http
        direct = self._direct_health()
        if direct.get("available"):
            return direct
        return {
            "available": False,
            "mode": "unavailable",
            "gaia_path": str(self.gaia_path),
            "governor_path": str(self.governor_path),
            "http_error": http.get("error"),
            "import_error": direct.get("error"),
        }

    def sky_reading(self) -> Dict:
        """Current atmospheric assessment if available."""
        http = self._http_sky_reading()
        if http.get("available"):
            return http
        direct = self._direct_sky_reading()
        if direct.get("available"):
            return direct
        return {
            "available": False,
            "mode": "unavailable",
            "decision": None,
            "reason": http.get("error") or direct.get("error") or "GAIA unavailable",
        }

    def engines(self) -> Dict:
        """What engines exist and their count."""
        engines_dir = self.gaia_path / "runtime" / "engines"
        engines = []
        if engines_dir.exists():
            engines = [f.stem for f in engines_dir.glob("*.py") if f.name != "__init__.py"]
        dem_dir = self.gaia_path / "data" / "holler_siren" / "raw_dem"
        dem_count = len(list(dem_dir.glob("*.tif"))) if dem_dir.exists() else 0
        return {
            "available": self.gaia_path.exists(),
            "gaia_path": str(self.gaia_path),
            "governor_present": self.governor_path.exists(),
            "engines_found": len(engines),
            "engine_names": sorted(engines),
            "dem_terrain_files": dem_count,
        }

    def benchmarks(self) -> Dict:
        """The proven numbers. Always available."""
        return {
            "detection_rate": "99.7%",
            "events_tested": 14110,
            "lead_time_hours": 9.4,
            "engines_present": 18,
        }

    def _minimal_payload(self) -> Dict[str, Any]:
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        return {
            "region": "avalon_bridge",
            "timestamp": timestamp,
            "event_type": "bridge_probe",
            "station_observations": [
                {
                    "station_id": "AVL",
                    "region": "avalon_bridge",
                    "timestamp": timestamp,
                    "pressure_mb": 1012.4,
                    "temperature_f": 68.0,
                    "dewpoint_f": 58.0,
                    "prior_dewpoint_f": 57.0,
                    "overnight_low_f": 55.0,
                    "humidity_pct": 72.0,
                    "wind_speed_mph": 6.0,
                    "wind_gust_mph": 9.0,
                    "wind_direction_deg": 180.0,
                    "visibility_mi": 10.0,
                    "precip_1h_in": 0.0,
                    "cape_jkg": 50.0,
                    "cin_jkg": 25.0,
                    "precipitable_water_in": 0.8,
                    "pressure_trend": "steady",
                    "text_description": "bridge probe calm conditions",
                }
            ],
            "radar_fixture": {
                "composite_reflectivity": 5.0,
                "rotation_couplet_kt": 0.0,
                "velocity_max": 0.0,
                "velocity_min": 0.0,
                "vil": 0.0,
                "available": False,
            },
            "lightning_fixture": {
                "flash_rate_per_min": 0.0,
                "energy_j": 0.0,
                "available": False,
            },
            "soil_fixture": {
                "soil_moisture": 0.45,
                "available": True,
            },
            "environmental_context": {
                "recent_event_severity": 0.0,
                "precip_7d_ratio": 1.0,
                "stream_level_ratio": 0.8,
                "drought_class": 0,
            },
            "celestial": {
                "kp_index": 1.0,
                "solar_wind_speed_kms": 350.0,
                "solar_wind_density_pcm3": 5.0,
                "imf_bz_nt": -1.0,
                "proton_flux_pfu": 1.0,
            },
        }

    def _http_json(self, url: str, payload: Optional[Dict] = None) -> Dict:
        try:
            if payload is None:
                request = urllib.request.Request(url, method="GET")
            else:
                body = json.dumps(payload).encode()
                request = urllib.request.Request(
                    url,
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode()
            data = json.loads(raw) if raw else {}
            return {"ok": True, "data": data}
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as e:
            return {"ok": False, "error": str(e)[:200]}

    def _http_health(self) -> Dict:
        result = self._http_json(self.health_url)
        if not result.get("ok"):
            return {
                "available": False,
                "mode": "http",
                "error": result.get("error", "health probe failed"),
            }
        data = result["data"]
        return {
            "available": True,
            "mode": "http",
            "service_running": True,
            "details": data,
        }

    def _http_sky_reading(self) -> Dict:
        result = self._http_json(self.analyze_url, self._minimal_payload())
        if not result.get("ok"):
            return {
                "available": False,
                "mode": "http",
                "error": result.get("error", "analyze probe failed"),
            }
        data = result["data"]
        return {
            "available": True,
            "mode": "http",
            "decision": data.get("decision"),
            "convergence_count": data.get("convergence_count"),
            "engine_scores": data.get("engine_scores", {}),
            "details": data,
        }

    def _build_import_script(self, action: str) -> str:
        return (
            "import importlib.util, json, os, sys\n"
            "import tempfile\n"
            "from pathlib import Path\n"
            "gaia_root = Path(sys.argv[1])\n"
            "governor_path = gaia_root / 'runtime' / 'governor' / 'governor.py'\n"
            "bridge_home = Path(tempfile.gettempdir()) / 'gaia_bridge_home'\n"
            "bridge_home.mkdir(parents=True, exist_ok=True)\n"
            "os.environ.setdefault('HOME', str(bridge_home))\n"
            "os.environ.setdefault('GAIA_DISABLE_EVIDENCE', '1')\n"
            "os.environ.setdefault('GAIA_BUS_MEMORY', '1')\n"
            "os.environ.setdefault('GAIA_OFFLINE', '1')\n"
            "os.environ.setdefault('GAIA_STATE_PATH', str(bridge_home / 'gaia' / 'runtime' / 'state' / 'threshold_state.json'))\n"
            "mpl_dir = Path(tempfile.gettempdir()) / 'gaia_bridge_mplcache'\n"
            "mpl_dir.mkdir(parents=True, exist_ok=True)\n"
            "os.environ.setdefault('MPLCONFIGDIR', str(mpl_dir))\n"
            "sys.path.insert(0, str(gaia_root))\n"
            "module_name = 'gaia_governor_bridge'\n"
            "spec = importlib.util.spec_from_file_location(module_name, str(governor_path))\n"
            "module = importlib.util.module_from_spec(spec)\n"
            "assert spec and spec.loader\n"
            "sys.modules[module_name] = module\n"
            "spec.loader.exec_module(module)\n"
            f"action = {action!r}\n"
            "if action == 'health':\n"
            "    result = {\n"
            "        'available': True,\n"
            "        'mode': 'import',\n"
            "        'has_compute': hasattr(module, 'compute_decision_for_payload'),\n"
            "        'engine_order_count': len(getattr(module, 'ENGINE_ORDER', [])),\n"
            "        'last_status_keys': sorted(list(getattr(module, 'LAST_STATUS', {}).keys())),\n"
            "    }\n"
            "elif action == 'analyze':\n"
            "    payload = json.loads(sys.argv[2])\n"
            "    analyze = getattr(module, 'compute_decision_for_payload')\n"
            "    reading = analyze(payload)\n"
            "    result = {\n"
            "        'available': True,\n"
            "        'mode': 'import',\n"
            "        'decision': reading.get('decision'),\n"
            "        'convergence_count': reading.get('convergence_count'),\n"
            "        'engine_scores': reading.get('engine_scores', {}),\n"
            "        'details': reading,\n"
            "    }\n"
            "else:\n"
            "    result = {'available': False, 'mode': 'import', 'error': 'unknown action'}\n"
            "print(json.dumps(result, default=str))\n"
        )

    def _run_direct_import(self, action: str, payload: Optional[Dict] = None) -> Dict:
        if not self.governor_path.exists():
            return {"available": False, "mode": "import", "error": "governor.py missing"}
        args = [self.python_executable, "-c", self._build_import_script(action), str(self.gaia_path)]
        if payload is not None:
            args.append(json.dumps(payload))
        try:
            result = subprocess.run(
                args,
                cwd=str(self.gaia_path),
                capture_output=True,
                text=True,
                timeout=max(5, int(self.timeout * 5)),
            )
        except Exception as e:
            return {"available": False, "mode": "import", "error": str(e)[:200]}

        if result.returncode != 0:
            return {
                "available": False,
                "mode": "import",
                "error": (result.stderr or result.stdout or "direct import failed")[:500],
            }

        output = (result.stdout or "").strip().splitlines()
        if not output:
            return {"available": False, "mode": "import", "error": "no import output"}
        try:
            return json.loads(output[-1])
        except json.JSONDecodeError as e:
            return {
                "available": False,
                "mode": "import",
                "error": f"invalid import output: {e}",
                "raw": output[-1][:300],
            }

    def _direct_health(self) -> Dict:
        return self._run_direct_import("health")

    def _direct_sky_reading(self) -> Dict:
        return self._run_direct_import("analyze", self._minimal_payload())
