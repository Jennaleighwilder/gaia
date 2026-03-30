"""
APOTHECARY Test Suite
Morgan le Fay's real remedies.
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from avalon.fusion import Fusion
from avalon.healing import Healing, TreatmentOutcome, Wound, WoundSeverity, WoundType
from avalon.real_healing import Apothecary, wire_real_healing


@pytest.fixture
def tmp_root():
    tmp = tempfile.mkdtemp(prefix="test_apothecary_")
    (Path(tmp) / "memory").mkdir()
    (Path(tmp) / "logs").mkdir()
    yield tmp
    shutil.rmtree(tmp)


@pytest.fixture
def apothecary(tmp_root):
    summons_received = []
    a = Apothecary(
        project_root=tmp_root,
        summons_callback=lambda s: summons_received.append(s),
    )
    a._summons_received = summons_received
    return a


@pytest.fixture
def wired_kingdom(tmp_root):
    fusion = Fusion()
    healing = Healing(
        carbon_recall=fusion.carbon.recall,
        carbon_learn=lambda **kw: fusion.carbon.learn(**kw),
    )
    summons_received = []
    apothecary = wire_real_healing(
        healing,
        tmp_root,
        lambda s: summons_received.append(s),
    )
    apothecary._summons_received = summons_received
    return fusion, healing, apothecary


def wound(
    system="Test",
    wtype=WoundType.PERFORMANCE,
    severity=WoundSeverity.WOUND,
):
    return Wound(system, wtype, severity, f"test wound on {system}")


class TestTourniquet:
    def test_returns_improving(self, apothecary):
        w = wound()
        result = apothecary.tourniquet("Test", w, None)
        assert result == TreatmentOutcome.IMPROVING

    def test_logs_action(self, apothecary):
        w = wound()
        apothecary.tourniquet("Test", w, None)
        assert any(e["remedy"] == "tourniquet" for e in apothecary.history)


class TestFever:
    def test_creates_fever_log(self, apothecary, tmp_root):
        w = wound()
        apothecary.fever("TestSys", w, None)
        fever_log = Path(tmp_root) / "memory" / "fever_testsys.jsonl"
        assert fever_log.exists()

    def test_returns_improving(self, apothecary):
        w = wound()
        result = apothecary.fever("Test", w, None)
        assert result == TreatmentOutcome.IMPROVING


class TestSuture:
    def test_heals(self, apothecary):
        w = wound(wtype=WoundType.CONNECTIVITY)
        result = apothecary.suture("Test", w, None)
        assert result == TreatmentOutcome.HEALED


class TestSplint:
    def test_sets_flag(self, apothecary):
        w = wound()
        apothecary.splint("TestSys", w, None)
        assert os.environ.get("AVALON_SPLINT_TESTSYS") == "1"
        apothecary.remove_splint("TestSys")
        assert "AVALON_SPLINT_TESTSYS" not in os.environ


class TestControlledBurn:
    def test_burns_logs(self, apothecary, tmp_root):
        log_dir = Path(tmp_root) / "logs"
        for i in range(3):
            (log_dir / f"test_{i}.log").write_text("data")
        w = wound(wtype=WoundType.EXHAUSTION)
        apothecary.controlled_burn("Test", w, None)
        assert len(list(log_dir.glob("*.log"))) == 0

    def test_burns_pycache(self, apothecary, tmp_root):
        cache = Path(tmp_root) / "mymod" / "__pycache__"
        cache.mkdir(parents=True)
        (cache / "x.pyc").write_text("bytecode")
        w = wound(wtype=WoundType.EXHAUSTION)
        apothecary.controlled_burn("Test", w, None)
        assert not cache.exists()

    def test_never_burns_frozen(self, apothecary, tmp_root):
        sacred = Path(tmp_root) / "frozen" / "west-os" / "__pycache__"
        sacred.mkdir(parents=True)
        (sacred / "x.pyc").write_text("bytecode")
        w = wound(wtype=WoundType.EXHAUSTION)
        apothecary.controlled_burn("Test", w, None)
        assert sacred.exists(), "BURN MUST NEVER TOUCH FROZEN"


class TestScorchedEarth:
    def test_trims_backups(self, apothecary, tmp_root):
        backup_dir = Path(tmp_root) / "memory" / "backups"
        backup_dir.mkdir(parents=True)
        for i in range(6):
            (backup_dir / f"kingdom_memory_{i}.json").write_text("{}")
        w = wound(wtype=WoundType.EXHAUSTION, severity=WoundSeverity.CRITICAL)
        apothecary.scorched_earth("Test", w, None)
        assert len(list(backup_dir.glob("kingdom_memory_*.json"))) <= 3


class TestBoneSetting:
    def test_refuses_sacred_ground(self, tmp_root):
        frozen_path = os.path.join(tmp_root, "frozen")
        a = Apothecary(project_root=frozen_path, summons_callback=lambda s: None)
        w = wound(wtype=WoundType.ACCURACY)
        result = a.bone_setting("Test", w, None)
        assert result == TreatmentOutcome.ESCALATED

    def test_escalates_without_git(self, apothecary):
        w = wound(wtype=WoundType.DRIFT)
        result = apothecary.bone_setting("Test", w, None)
        assert result in (TreatmentOutcome.ESCALATED, TreatmentOutcome.WORSENED)


class TestHibernation:
    def test_sets_flag(self, apothecary):
        w = wound(wtype=WoundType.EXHAUSTION)
        apothecary.hibernation("TestSys", w, None)
        assert os.environ.get("AVALON_HIBERNATE_TESTSYS") == "1"
        apothecary.wake_from_hibernation("TestSys")
        assert "AVALON_HIBERNATE_TESTSYS" not in os.environ


class TestMetamorphosis:
    def test_clears_cache(self, apothecary, tmp_root):
        cache = Path(tmp_root) / ".cache" / "testsys"
        cache.mkdir(parents=True)
        (cache / "state.json").write_text("{}")
        w = wound(severity=WoundSeverity.MORTAL)
        result = apothecary.metamorphosis("testsys", w, None)
        assert result == TreatmentOutcome.HEALED
        assert not cache.exists()

    def test_clears_env_flags(self, apothecary):
        os.environ["AVALON_SPLINT_TESTSYS"] = "1"
        os.environ["AVALON_HIBERNATE_TESTSYS"] = "1"
        w = wound(severity=WoundSeverity.MORTAL)
        apothecary.metamorphosis("testsys", w, None)
        assert "AVALON_SPLINT_TESTSYS" not in os.environ
        assert "AVALON_HIBERNATE_TESTSYS" not in os.environ


class TestQuarantine:
    def test_sets_flag(self, apothecary):
        w = wound(wtype=WoundType.CORRUPTION)
        apothecary.quarantine("TestSys", w, None)
        assert os.environ.get("AVALON_QUARANTINE_TESTSYS") == "1"
        apothecary.lift_quarantine("TestSys")
        assert "AVALON_QUARANTINE_TESTSYS" not in os.environ


class TestSummons:
    def test_writes_file(self, apothecary, tmp_root):
        w = wound(severity=WoundSeverity.MORTAL)
        apothecary.summons("Test", w, None)
        assert (Path(tmp_root) / "memory" / "sovereign_summons.jsonl").exists()

    def test_calls_callback(self, apothecary):
        w = wound(severity=WoundSeverity.MORTAL)
        apothecary.summons("Test", w, None)
        assert len(apothecary._summons_received) >= 1

    def test_message_contains_patient(self, apothecary):
        w = wound(severity=WoundSeverity.MORTAL)
        apothecary.summons("TestPatient", w, None)
        msg = apothecary._summons_received[0]["message"]
        assert "TestPatient" in msg


class TestJournal:
    def test_journal_file_created(self, apothecary, tmp_root):
        w = wound()
        apothecary.antivenom("Test", w, None)
        assert apothecary._log_path.exists()

    def test_journal_entries_valid(self, apothecary, tmp_root):
        w = wound()
        apothecary.antivenom("Test", w, None)
        with open(apothecary._log_path) as f:
            for line in f:
                entry = json.loads(line)
                assert "time" in entry
                assert "remedy" in entry
                assert "patient" in entry


class TestWiring:
    def test_registers_all_remedies(self, wired_kingdom):
        _, healing, _ = wired_kingdom
        registered = healing.healer._treatments
        assert len(registered) >= 30
        assert "tourniquet" in registered
        assert "fever" in registered
        assert "controlled_burn" in registered
        assert "metamorphosis" in registered
        assert "summons" in registered
        assert "restart" in registered
        assert "apoptosis_and_rebirth" in registered

    def test_real_burn_via_wiring(self, wired_kingdom, tmp_root):
        _, healing, _ = wired_kingdom
        log_dir = Path(tmp_root) / "logs"
        log_dir.mkdir(exist_ok=True)
        (log_dir / "test.log").write_text("data")
        w = Wound("Test", WoundType.EXHAUSTION, WoundSeverity.WOUND, "disk")
        diagnosis = healing.diagnostician.examine(w)
        diagnosis.recommended_treatment = "controlled_burn"
        treatment = healing.healer.treat(diagnosis)
        assert treatment.outcome == TreatmentOutcome.HEALED
        assert len(list(log_dir.glob("*.log"))) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
