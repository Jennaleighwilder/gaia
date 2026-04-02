"""WARDENS Test Suite — Scouts, Honeypots, Canaries, War Plans"""

import os
import stat
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from avalon.wardens import ThreatLevel, Wardens, wire_wardens


class TestWardens:
    @pytest.fixture
    def tmp_root(self):
        with tempfile.TemporaryDirectory(prefix="wardens_test_") as tmp:
            root = Path(tmp)
            (root / "memory").mkdir()
            (root / "avalon").mkdir()
            (root / "avalon" / "avalon.py").write_text("def living():\n    return True\n")
            (root / "avalon" / "faithkeeper.py").write_text("def keep():\n    return True\n")
            (root / "avalon" / "temple.py").write_text("def law():\n    return True\n")
            frozen = root / "frozen" / "west-os"
            frozen.mkdir(parents=True)
            (frozen / "governor.py").write_text("# sacred\n")
            try:
                frozen.chmod(stat.S_IREAD | stat.S_IEXEC)
            except Exception:
                pass
            yield root

    def test_scout_patrol_returns_results(self, tmp_root):
        wardens = Wardens(str(tmp_root))
        wardens.recruit_scout("Scout", "sector", lambda: {"finding": "all clear", "threat": False, "severity": 0})
        result = wardens.patrol()
        assert len(result["scout_reports"]) == 1

    def test_honeypot_records_interactions(self, tmp_root):
        wardens = Wardens(str(tmp_root))
        hp = wardens.deploy_honeypot("fake_api_key", "credential")
        hp.touch("scanner", "read")
        briefing = wardens.intelligence_briefing()
        assert briefing["honeypot_intel"]["fake_api_key"]["interactions"] == 1

    def test_canary_triggers_on_violation(self, tmp_root):
        wardens = Wardens(str(tmp_root))
        state = {"alive": True}
        wardens.place_canary("critical", "file", lambda: {"alive": state["alive"], "detail": "critical file changed"})
        wardens.patrol()
        state["alive"] = False
        result = wardens.patrol()
        assert result["dead_canaries"] == 1

    def test_sacred_ground_scout_detects_writable_frozen(self, tmp_root):
        root = Path(tmp_root)
        frozen = root / "frozen" / "west-os"
        try:
            frozen.chmod(stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
        except Exception:
            pass
        class Dummy:
            pass
        dummy = Dummy()
        wardens = wire_wardens(dummy, project_root=str(root))
        result = wardens.patrol()
        assert any(report["scout"] == "Guardian" and report["threat"] for report in result["scout_reports"])

    def test_war_plan_activation_changes_threat_level(self, tmp_root):
        wardens = Wardens(str(tmp_root))
        result = wardens.activate_plan("Probe Response")
        assert result["activated"]
        assert result["threat_level"] == ThreatLevel.VIGILANCE.value

    def test_stand_down_returns_to_peace(self, tmp_root):
        wardens = Wardens(str(tmp_root))
        wardens.activate_plan("Probe Response")
        result = wardens.stand_down()
        assert result["stood_down"]
        assert result["threat_level"] == ThreatLevel.PEACE.value

    def test_intelligence_briefing_includes_all_data(self, tmp_root):
        wardens = Wardens(str(tmp_root))
        wardens.recruit_scout("Scout", "sector", lambda: {"finding": "all clear", "threat": False, "severity": 0})
        wardens.deploy_honeypot("fake_admin", "admin")
        wardens.place_canary("memory", "dir", lambda: {"alive": True, "detail": "ok"})
        wardens.patrol()
        briefing = wardens.intelligence_briefing()
        assert briefing["scouts"] == 1
        assert briefing["honeypots"] == 1
        assert briefing["canaries"] == 1
        assert briefing["war_plans"] >= 7

    def test_multiple_scouts_report_simultaneously(self, tmp_root):
        wardens = Wardens(str(tmp_root))
        wardens.recruit_scout("A", "one", lambda: {"finding": "one", "threat": False, "severity": 0})
        wardens.recruit_scout("B", "two", lambda: {"finding": "two", "threat": True, "severity": 0.5})
        result = wardens.patrol()
        assert len(result["scout_reports"]) == 2
        assert result["threats_found"] == 1

    def test_dead_canary_escalates_to_alert(self, tmp_root):
        wardens = Wardens(str(tmp_root))
        wardens.place_canary("trip", "dir", lambda: {"alive": False, "detail": "dead"})
        result = wardens.patrol()
        assert result["threat_level"] == ThreatLevel.ALERT.value


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
