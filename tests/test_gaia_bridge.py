"""
GAIA Bridge Test Suite
Read-only bridge from Avalon into GAIA.
"""

import json
from pathlib import Path

import pytest

from avalon.gaia_bridge import GaiaBridge


class TestGaiaBridgeHTTP:
    def test_http_mode_health_and_sky(self, tmp_path, monkeypatch):
        bridge = GaiaBridge(gaia_path=tmp_path, timeout=1.0)

        def fake_http_json(url, payload=None):
            if "health" in url:
                return {"ok": True, "data": {"status": "ok", "service": "gaia"}}
            return {
                "ok": True,
                "data": {
                    "decision": "CLEAR",
                    "convergence_count": 1,
                    "engine_scores": {"pressure": 0.2},
                },
            }

        monkeypatch.setattr(bridge, "_http_json", fake_http_json)
        health = bridge.health()
        sky = bridge.sky_reading()
        assert health["available"]
        assert health["mode"] == "http"
        assert sky["available"]
        assert sky["decision"] == "CLEAR"


class TestGaiaBridgeDirectImport:
    def test_direct_import_mode(self, tmp_path):
        runtime = tmp_path / "runtime"
        governor_dir = runtime / "governor"
        engines_dir = runtime / "engines"
        governor_dir.mkdir(parents=True)
        engines_dir.mkdir(parents=True)
        (runtime / "__init__.py").write_text("")
        (governor_dir / "__init__.py").write_text("")
        (engines_dir / "__init__.py").write_text("")
        (engines_dir / "pressure.py").write_text("class PressureEngine:\n    pass\n")
        (governor_dir / "governor.py").write_text(
            "ENGINE_ORDER = ['pressure', 'thermal']\n"
            "LAST_STATUS = {'decision': 'CLEAR', 'engine_scores': {}}\n"
            "def reset_runtime_state():\n"
            "    raise RuntimeError('should never be called')\n"
            "def compute_decision_for_payload(payload):\n"
            "    return {'decision': 'WATCH', 'convergence_count': 2, 'engine_scores': {'pressure': 0.7}}\n"
        )
        bridge = GaiaBridge(gaia_path=tmp_path, timeout=1.0)
        health = bridge.health()
        sky = bridge.sky_reading()
        engines = bridge.engines()
        assert health["available"]
        assert health["mode"] == "import"
        assert health["has_compute"]
        assert sky["available"]
        assert sky["decision"] == "WATCH"
        assert engines["engines_found"] == 1

    def test_never_calls_reset_runtime_state(self, tmp_path):
        runtime = tmp_path / "runtime"
        governor_dir = runtime / "governor"
        governor_dir.mkdir(parents=True)
        (runtime / "__init__.py").write_text("")
        (governor_dir / "__init__.py").write_text("")
        (governor_dir / "governor.py").write_text(
            "def reset_runtime_state():\n"
            "    raise RuntimeError('should never be called')\n"
            "def compute_decision_for_payload(payload):\n"
            "    return {'decision': 'CLEAR', 'convergence_count': 0, 'engine_scores': {}}\n"
        )
        bridge = GaiaBridge(gaia_path=tmp_path)
        script = bridge._build_import_script("analyze")
        assert "reset_runtime_state" not in script


class TestGaiaBridgeFallback:
    def test_unavailable_bridge_reports_cleanly(self, tmp_path):
        bridge = GaiaBridge(gaia_path=tmp_path / "missing", timeout=0.2)
        health = bridge.health()
        sky = bridge.sky_reading()
        assert not health["available"]
        assert not sky["available"]

    def test_benchmarks_always_available(self):
        bridge = GaiaBridge(gaia_path=Path("/definitely/not/here"))
        benchmarks = bridge.benchmarks()
        assert benchmarks["detection_rate"] == "99.7%"
        assert benchmarks["events_tested"] == 14110
