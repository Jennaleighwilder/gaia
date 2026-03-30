"""
REAL HEARTBEAT Test Suite
The kingdom feels its own pulse.
"""

import os
import shutil
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from avalon.real_heartbeat import (
    RealHeartbeat,
    SystemMonitor,
    VitalCheck,
    wire_real_heartbeat,
)


class TestVitalCheckDisk:
    def test_disk_returns_health(self):
        health, details = VitalCheck.disk_space("/")
        assert 0.0 <= health <= 1.0
        assert "free_gb" in details

    def test_disk_returns_status(self):
        health, details = VitalCheck.disk_space("/")
        assert details["status"] in ["healthy", "warning", "critical"]


class TestVitalCheckMemory:
    def test_memory_returns_health(self):
        health, details = VitalCheck.memory_usage()
        assert 0.0 <= health <= 1.0

    def test_memory_has_details(self):
        health, details = VitalCheck.memory_usage()
        assert "used_pct" in details or "note" in details


class TestVitalCheckCPU:
    def test_cpu_returns_health(self):
        health, details = VitalCheck.cpu_usage()
        assert 0.0 <= health <= 1.0


class TestVitalCheckFile:
    def test_existing_file(self):
        health, details = VitalCheck.file_exists(__file__)
        assert health == 1.0
        assert details["exists"]

    def test_missing_file(self):
        health, details = VitalCheck.file_exists("/nonexistent/file.xyz")
        assert health == 0.0
        assert not details["exists"]


class TestVitalCheckFreshness:
    def test_fresh_file(self):
        health, details = VitalCheck.file_freshness(__file__, max_age_seconds=86400)
        assert health > 0.0
        assert "age_seconds" in details

    def test_missing_file_freshness(self):
        health, details = VitalCheck.file_freshness("/no/such/file", max_age_seconds=3600)
        assert health == 0.0


class TestVitalCheckDirectorySize:
    def test_small_directory(self):
        tmp = tempfile.mkdtemp()
        try:
            health, details = VitalCheck.directory_size(tmp, 500, 2000)
            assert health == 1.0
            assert details["size_mb"] < 1
        finally:
            shutil.rmtree(tmp)

    def test_nonexistent_directory(self):
        health, details = VitalCheck.directory_size("/no/such/dir")
        assert health == 1.0


class TestVitalCheckEnvironment:
    def test_set_variable(self):
        os.environ["TEST_HEARTBEAT_VAR"] = "test_value"
        health, details = VitalCheck.environment_variable("TEST_HEARTBEAT_VAR")
        assert health == 1.0
        assert details["set"]
        assert "test_value" not in str(details)
        del os.environ["TEST_HEARTBEAT_VAR"]

    def test_unset_variable(self):
        health, details = VitalCheck.environment_variable("DEFINITELY_NOT_SET_XYZ")
        assert health == 0.0
        assert not details["set"]


class TestVitalCheckFrozenIntegrity:
    def test_frozen_directory(self):
        tmp = tempfile.mkdtemp()
        try:
            os.chmod(tmp, 0o555)
            health, details = VitalCheck.frozen_integrity(tmp)
            assert health == 1.0
            assert details["frozen"]
        finally:
            os.chmod(tmp, 0o755)
            shutil.rmtree(tmp)

    def test_writable_directory(self):
        tmp = tempfile.mkdtemp()
        try:
            health, details = VitalCheck.frozen_integrity(tmp)
            assert health == 0.0
            assert not details["frozen"]
        finally:
            shutil.rmtree(tmp)

    def test_nonexistent_directory(self):
        health, details = VitalCheck.frozen_integrity("/no/such/frozen")
        assert health == 0.0


class TestSystemMonitor:
    def test_single_check(self):
        mon = SystemMonitor("test")
        mon.add_check("always_healthy", lambda: (1.0, {"ok": True}))
        vitals = mon.check()
        assert vitals.health == 1.0
        assert vitals.name == "test"

    def test_weighted_checks(self):
        mon = SystemMonitor("test")
        mon.add_check("healthy", lambda: (1.0, {}), weight=1.0)
        mon.add_check("dead", lambda: (0.0, {}), weight=1.0)
        vitals = mon.check()
        assert 0.4 <= vitals.health <= 0.6

    def test_issues_detected(self):
        mon = SystemMonitor("test")
        mon.add_check("broken", lambda: (0.1, {"status": "critical"}))
        vitals = mon.check()
        assert len(vitals.issues) >= 1

    def test_worst_check_identified(self):
        mon = SystemMonitor("test")
        mon.add_check("good", lambda: (0.9, {}))
        mon.add_check("bad", lambda: (0.2, {}))
        vitals = mon.check()
        assert vitals.worst_check == "bad"


class TestRealHeartbeat:
    def test_creates_with_defaults(self):
        hb = RealHeartbeat()
        assert hb.status["monitors"] >= 5

    def test_beat_returns_health(self):
        hb = RealHeartbeat()
        beat = hb.beat()
        assert "kingdom_health" in beat
        assert "mood" in beat
        assert 0.0 <= beat["kingdom_health"] <= 1.0

    def test_mood_reflects_health(self):
        hb = RealHeartbeat()
        beat = hb.beat()
        assert beat["mood"] in ["celebrating", "steady", "concerned", "wounded", "critical"]

    def test_get_health_scores(self):
        hb = RealHeartbeat()
        scores = hb.get_health_scores()
        assert len(scores) >= 5
        for name, score in scores.items():
            assert 0.0 <= score <= 1.0

    def test_narrative_report(self):
        hb = RealHeartbeat()
        report = hb.narrative_report()
        assert "Kingdom Health Report" in report
        assert "mood:" in report

    def test_add_custom_monitor(self):
        hb = RealHeartbeat()
        custom = SystemMonitor("CustomSystem")
        custom.add_check("custom_check", lambda: (0.75, {"test": True}))
        hb.add_monitor("CustomSystem", custom)
        assert "CustomSystem" in hb._monitors


class TestWireFusion:
    def test_wire_replaces_stubs(self):
        from avalon.fusion import Fusion

        fusion = Fusion()
        wire_real_heartbeat(fusion)

        assert len(fusion.heartbeat._listeners) >= 5

        breath = fusion.breathe()
        assert 0.0 <= breath["health"] <= 1.0

    def test_wired_health_is_real(self):
        from avalon.fusion import Fusion

        fusion = Fusion()
        real_hb = wire_real_heartbeat(fusion)

        scores = real_hb.get_health_scores()
        infra_health = scores.get("Infrastructure", 0)
        assert infra_health > 0, "Infrastructure should have real health data"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
