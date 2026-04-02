"""
MIRROR Bridge Test Suite
Read-only bridge from Avalon into Mirror OS / East OS.
"""

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from avalon.mirror_bridge import MirrorBridge


def build_mirror_fixture(root: Path):
    (root / "lib").mkdir(parents=True)
    (root / "scripts").mkdir()
    (root / "data").mkdir()
    (root / "README.md").write_text(
        "# Mirror OS Software\n\n"
        "External product name:\n\n"
        "**East Runtime Governor**\n\n"
        "Mirror is a constitutional and human-impact governance runtime.\n"
    )
    (root / "lib" / "mirror-engine.js").write_text(
        "function composeReflection() { return {}; }\n"
        "const buildKernel = () => ({ ok: true });\n"
        "module.exports = { composeReflection, buildKernel };\n"
    )
    (root / "server.js").write_text(
        "const PORT = Number(process.env.PORT || 3030);\n"
        "console.log(PORT);\n"
    )
    (root / "package.json").write_text(
        json.dumps(
            {
                "name": "mirror-os-software",
                "version": "0.2.0",
                "scripts": {"start": "node server.js", "test": "node scripts/test-mirror.js"},
                "dependencies": {"fastify": "^4.0.0"},
            }
        )
    )
    (root / "scripts" / "test-mirror.js").write_text("console.log('ok');\n")


class TestMirrorBridgeStructure:
    def test_unavailable_bridge_reports_cleanly(self, tmp_path):
        bridge = MirrorBridge(mirror_path=tmp_path / "missing")
        health = bridge.health()
        reflection = bridge.reflection()
        assert not health["available"]
        assert not reflection["available"]

    def test_reads_structure_without_writing(self, tmp_path):
        build_mirror_fixture(tmp_path)
        before = {
            str(path.relative_to(tmp_path)): path.stat().st_mtime_ns
            for path in tmp_path.rglob("*")
            if path.is_file()
        }
        bridge = MirrorBridge(mirror_path=tmp_path)
        structure = bridge.read_structure()
        after = {
            str(path.relative_to(tmp_path)): path.stat().st_mtime_ns
            for path in tmp_path.rglob("*")
            if path.is_file()
        }
        assert structure["available"]
        assert structure["engine"]["lines"] >= 2
        assert structure["server"]["port"] == 3030
        assert structure["package"]["name"] == "mirror-os-software"
        assert structure["js_files"] >= 2
        assert before == after

    def test_reflection_reports_sleeping_when_not_running(self, tmp_path):
        build_mirror_fixture(tmp_path)
        bridge = MirrorBridge(mirror_path=tmp_path)
        reflection = bridge.reflection()
        assert reflection["available"]
        assert not reflection["mirror_running"]
        assert "sleeping" in reflection["reflection"].lower()


class TestMirrorBridgeHTTP:
    def test_http_health_and_reflection(self, tmp_path, monkeypatch):
        build_mirror_fixture(tmp_path)
        bridge = MirrorBridge(mirror_path=tmp_path)

        def fake_http_json(endpoint):
            if endpoint == "/api/health":
                return {"ok": True, "port": 3030, "data": {"ok": True, "boot": {"port": 3030}}}
            if endpoint == "/api/deployment-posture":
                return {"ok": True, "port": 3030, "data": {"deploymentMode": "local-founder"}}
            if endpoint == "/api/bootstrap":
                return {
                    "ok": True,
                    "port": 3030,
                    "data": {"sessionCount": 3, "bridgeCount": 2, "kernelEventCount": 5},
                }
            if endpoint == "/api/proof-bundle":
                return {"ok": True, "port": 3030, "data": {"proofs": 7}}
            return {"ok": False, "error": "unexpected endpoint"}

        monkeypatch.setattr(bridge, "_http_json", fake_http_json)
        health = bridge.health()
        reflection = bridge.reflection()
        assert health["running"]
        assert health["mode"] == "http"
        assert reflection["mirror_running"]
        assert reflection["bootstrap"]["sessionCount"] == 3

    def test_http_probe_handles_failure_gracefully(self, tmp_path, monkeypatch):
        build_mirror_fixture(tmp_path)
        bridge = MirrorBridge(mirror_path=tmp_path)
        monkeypatch.setattr(bridge, "_http_json", lambda endpoint: {"ok": False, "error": "connection refused"})
        health = bridge.health()
        assert health["available"]
        assert not health["running"]
        assert health["mode"] == "structure"


class TestMirrorBridgeIntegration:
    def test_reads_frozen_integration_surfaces(self, tmp_path):
        build_mirror_fixture(tmp_path / "mirror")
        frozen = tmp_path / "frozen" / "west-os" / "runtime"
        (frozen / "governor").mkdir(parents=True)
        (frozen / "services").mkdir(parents=True)
        (frozen / "governor" / "mirror_shadow_bridge.py").write_text(
            "def shadow_enabled():\n    return True\n"
        )
        (frozen / "services" / "mirror_protocol_service.py").write_text(
            "class MirrorProtocolService:\n    pass\n"
        )
        bridge = MirrorBridge(
            mirror_path=tmp_path / "mirror",
            frozen_west_os_path=tmp_path / "frozen" / "west-os",
        )
        surfaces = bridge.read_integration_surfaces()
        assert surfaces["available"]
        assert surfaces["files"]["mirror_shadow_bridge"]["exists"]
        assert surfaces["files"]["mirror_protocol_service"]["exists"]

    def test_status_reports_port(self, tmp_path, monkeypatch):
        build_mirror_fixture(tmp_path)
        bridge = MirrorBridge(mirror_path=tmp_path)
        monkeypatch.setattr(bridge, "_http_health", lambda: {"available": True, "port": 3030, "details": {}})
        status = bridge.status
        assert status["available"]
        assert status["port"] == 3030
