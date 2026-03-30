"""
HEALING Test Suite
Morgan le Fay's restoration.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from avalon.fusion import Fusion
from avalon.healing import (
    Healing,
    Wound,
    WoundSeverity,
    WoundType,
    Diagnostician,
    Healer,
    TreatmentOutcome,
)


@pytest.fixture
def kingdom():
    fusion = Fusion()
    fusion.heartbeat.register_system("Nyx", lambda: 1.0)
    fusion.heartbeat.register_system("Lancelot", lambda: 1.0)
    fusion.heartbeat.register_system("GAIA", lambda: 0.95)
    fusion.heartbeat.register_system("Alfred", lambda: 1.0)
    fusion.heartbeat.register_system("Merlin", lambda: 0.9)
    for _ in range(3):
        fusion.breathe()
    healing = Healing(
        carbon_recall=fusion.carbon.recall,
        carbon_learn=lambda **kw: fusion.carbon.learn(**kw),
    )
    return fusion, healing


class TestWound:
    def test_wound_has_identity(self):
        w = Wound("TestSys", WoundType.PERFORMANCE, WoundSeverity.WOUND, "test wound")
        assert len(w.identity) == 12

    def test_wound_tracks_age(self):
        w = Wound("TestSys", WoundType.DRIFT, WoundSeverity.SCRATCH, "test")
        assert w.age_seconds >= 0

    def test_wound_healing_duration(self):
        import time
        w = Wound("TestSys", WoundType.ACCURACY, WoundSeverity.WOUND, "test")
        w.healed = True
        w.healed_at = time.time() + 5
        assert w.healing_duration is not None


class TestDiagnostician:
    def test_diagnose_produces_result(self, kingdom):
        _, healing = kingdom
        wound = Wound("GAIA", WoundType.ACCURACY, WoundSeverity.WOUND, "test")
        diagnosis = healing.diagnostician.examine(wound)
        assert diagnosis.probable_cause
        assert diagnosis.recommended_treatment
        assert 0 <= diagnosis.confidence <= 1

    def test_diagnose_uses_carbon_lessons(self, kingdom):
        fusion, healing = kingdom
        fusion.carbon.learn(
            content="GAIA accuracy fixed by rollback",
            source="past", context="test", category="adversity"
        )
        wound = Wound("GAIA", WoundType.ACCURACY, WoundSeverity.WOUND, "accuracy dropped")
        diagnosis = healing.diagnostician.examine(wound)
        assert diagnosis.confidence > 0.5

    def test_severity_affects_treatment(self, kingdom):
        _, healing = kingdom
        scratch = Wound("GAIA", WoundType.ACCURACY, WoundSeverity.SCRATCH, "minor")
        mortal = Wound("GAIA", WoundType.ACCURACY, WoundSeverity.MORTAL, "dying")
        d_scratch = healing.diagnostician.examine(scratch)
        d_mortal = healing.diagnostician.examine(mortal)
        assert d_scratch.recommended_treatment != d_mortal.recommended_treatment


class TestHealer:
    def test_treat_returns_outcome(self, kingdom):
        _, healing = kingdom
        wound = Wound("Alfred", WoundType.PERFORMANCE, WoundSeverity.WOUND, "slow")
        diagnosis = healing.diagnostician.examine(wound)
        treatment = healing.healer.treat(diagnosis)
        assert treatment.outcome in TreatmentOutcome

    def test_custom_handler(self, kingdom):
        _, healing = kingdom
        called = []
        healing.healer.register_treatment(
            "custom_fix",
            lambda sys, wound, diag: (called.append(sys), TreatmentOutcome.HEALED)[1]
        )
        wound = Wound("Test", WoundType.PERFORMANCE, WoundSeverity.SCRATCH, "test")
        wound_diag = healing.diagnostician.examine(wound)
        wound_diag.recommended_treatment = "custom_fix"
        treatment = healing.healer.treat(wound_diag)
        assert treatment.outcome == TreatmentOutcome.HEALED
        assert "Test" in called

    def test_treatment_history(self, kingdom):
        _, healing = kingdom
        wound = Wound("GAIA", WoundType.ACCURACY, WoundSeverity.WOUND, "test")
        diagnosis = healing.diagnostician.examine(wound)
        healing.healer.treat(diagnosis)
        assert len(healing.healer.history) == 1


class TestWatch:
    def test_detects_wound(self, kingdom):
        fusion, healing = kingdom
        fusion.heartbeat._system_health["GAIA"] = 0.5
        wounds = healing.watch(fusion.heartbeat._system_health)
        assert len(wounds) >= 1
        assert any(w.system_name == "GAIA" for w in wounds)

    def test_healthy_system_no_wound(self, kingdom):
        fusion, healing = kingdom
        wounds = healing.watch(fusion.heartbeat._system_health)
        assert len(wounds) == 0

    def test_severity_scales_with_health(self, kingdom):
        fusion, healing = kingdom
        fusion.heartbeat._system_health["GAIA"] = 0.1
        wounds = healing.watch(fusion.heartbeat._system_health)
        gaia_wound = [w for w in wounds if w.system_name == "GAIA"][0]
        assert gaia_wound.severity == WoundSeverity.MORTAL

    def test_natural_recovery_detected(self, kingdom):
        fusion, healing = kingdom
        fusion.heartbeat._system_health["GAIA"] = 0.5
        healing.watch(fusion.heartbeat._system_health)
        assert "GAIA" in healing._active_wounds
        fusion.heartbeat._system_health["GAIA"] = 0.95
        healing.watch(fusion.heartbeat._system_health)
        assert "GAIA" not in healing._active_wounds
        assert len(healing._healed_wounds) >= 1


class TestHealingCycle:
    def test_full_cycle(self, kingdom):
        fusion, healing = kingdom
        fusion.heartbeat._system_health["Alfred"] = 0.3
        wounds = healing.watch(fusion.heartbeat._system_health)
        assert len(wounds) == 1
        results = healing.heal_all()
        assert len(results) == 1
        assert results[0]["treatment"]["outcome"] in ["healed", "improving", "escalated"]

    def test_carbon_learns_from_healing(self, kingdom):
        fusion, healing = kingdom
        initial_lessons = len(fusion.carbon._lessons)
        fusion.heartbeat._system_health["Alfred"] = 0.3
        healing.watch(fusion.heartbeat._system_health)
        healing.heal_all()
        assert len(fusion.carbon._lessons) > initial_lessons

    def test_mortal_wound_healing(self, kingdom):
        fusion, healing = kingdom
        fusion.heartbeat._system_health["Merlin"] = 0.1
        wounds = healing.watch(fusion.heartbeat._system_health)
        merlin_wound = [w for w in wounds if w.system_name == "Merlin"][0]
        assert merlin_wound.severity == WoundSeverity.MORTAL
        result = healing.heal(merlin_wound)
        assert result["treatment"]["method"] in [
            "apoptosis_and_rebirth", "isolate_and_alert_sovereign",
            "full_reset_from_snapshot"
        ]

    def test_identity_wound_detected(self, kingdom):
        fusion, healing = kingdom
        fusion.heartbeat._system_health["Nyx"] = 0.5
        wounds = healing.watch(fusion.heartbeat._system_health)
        nyx_wound = [w for w in wounds if w.system_name == "Nyx"][0]
        assert nyx_wound.wound_type == WoundType.IDENTITY


class TestTriageReport:
    def test_empty_triage(self, kingdom):
        _, healing = kingdom
        triage = healing.triage_report()
        assert triage["active_wounds"] == 0
        assert triage["healed_total"] == 0

    def test_triage_after_healing(self, kingdom):
        fusion, healing = kingdom
        fusion.heartbeat._system_health["Alfred"] = 0.3
        healing.watch(fusion.heartbeat._system_health)
        healing.heal_all()
        triage = healing.triage_report()
        assert triage["healed_total"] >= 1
        assert triage["treatment_success_rate"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
