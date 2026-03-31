"""MATURATION Test Suite"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from avalon.arts import KingdomArts
from avalon.faithkeeper import Faithkeeper
from avalon.fusion import Fusion
from avalon.grail import Grail, load_jennifers_research
from avalon.grail_advancement import advance_grail
from avalon.healing import Healing
from avalon.informed_table import ClanMother
from avalon.land import LandSteward
from avalon.longhouse import Longhouse
from avalon.maturation import Maturation, STAGE_ORDER, Stage, wire_maturation
from avalon.memory import Memory
from avalon.merlin import Merlin


def make_avalon(tmp_path):
    class MinAvalon:
        pass

    av = MinAvalon()
    av.fusion = Fusion()
    av.merlin = Merlin()
    av.healing = Healing(
        carbon_recall=av.fusion.carbon.recall,
        carbon_learn=lambda **kw: av.fusion.carbon.learn(**kw),
    )
    av.memory = Memory(memory_dir=str(tmp_path / "memory"))
    av.arts = KingdomArts()
    av.longhouse = Longhouse()
    av.land = LandSteward(project_root=str(tmp_path))
    av.grail = Grail()
    load_jennifers_research(av.grail)
    advance_grail(av.grail)
    av.informed_table = type("InformedTableStub", (), {"_clan_mother": ClanMother()})()
    av.faithkeeper = Faithkeeper(av)

    for name in ["Nyx", "Avalon", "Memory"]:
        av.fusion.heartbeat.register_system(name, lambda: 0.95)

    return av


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestStages:
    def test_seven_stages_exist(self):
        assert len(STAGE_ORDER) == 7

    def test_starts_at_seedling(self, sandbox):
        av = make_avalon(sandbox)
        m = Maturation(av)
        assert m._current_stage == Stage.SEEDLING

    def test_twenty_one_milestones(self, sandbox):
        av = make_avalon(sandbox)
        m = Maturation(av)
        assert len(m._milestones) == 21


class TestSeedling:
    def test_first_breath(self, sandbox):
        av = make_avalon(sandbox)
        m = Maturation(av)
        av.faithkeeper.perform_ceremony()
        assessment = m.assess()
        assert assessment["milestones"]["seedling_first_breath"]["passed"]

    def test_first_bond(self, sandbox):
        av = make_avalon(sandbox)
        m = Maturation(av)
        av.fusion.experience("discovery", "test", ["Nyx", "Avalon"], 0.8)
        assessment = m.assess()
        assert assessment["milestones"]["seedling_first_bond"]["passed"]

    def test_first_memory(self, sandbox):
        av = make_avalon(sandbox)
        m = Maturation(av)
        av.memory.journal_event("test", "something happened")
        assessment = m.assess()
        assert assessment["milestones"]["seedling_first_memory"]["passed"]


class TestSapling:
    def test_first_lesson(self, sandbox):
        av = make_avalon(sandbox)
        m = Maturation(av)
        av.fusion.carbon.learn(
            content="test lesson",
            source="test",
            context="test",
            category="discovery",
            confidence=0.9,
        )
        assessment = m.assess()
        assert assessment["milestones"]["sapling_first_lesson"]["passed"]


class TestBlooming:
    def test_first_service(self, sandbox):
        av = make_avalon(sandbox)
        m = Maturation(av)
        av.longhouse.welcome("Test", "legal rights help")
        assessment = m.assess()
        assert assessment["milestones"]["blooming_first_service"]["passed"]

    def test_first_chronicle(self, sandbox):
        av = make_avalon(sandbox)
        m = Maturation(av)
        av.arts.chronicle(
            {
                "number": 1,
                "thanksgiving": {"alive_count": 3, "total_systems": 3, "gratitude_ratio": 1.0},
                "wounds_found": 0,
                "wounds_healed": 0,
                "merlin_insights": 0,
                "lessons_learned": 0,
            }
        )
        assessment = m.assess()
        assert assessment["milestones"]["blooming_first_chronicle"]["passed"]

    def test_three_sisters_served(self, sandbox):
        av = make_avalon(sandbox)
        m = Maturation(av)
        av.longhouse.welcome("A", "legal rights help")
        av.longhouse.welcome("B", "weather warning tornado")
        av.longhouse.welcome("C", "shelter food crisis resources")
        assessment = m.assess()
        assert assessment["milestones"]["blooming_three_sisters_served"]["passed"]


class TestRootedAndElder:
    def test_self_survey(self, sandbox):
        av = make_avalon(sandbox)
        m = Maturation(av)
        av.land.survey()
        assessment = m.assess()
        assert assessment["milestones"]["rooted_self_survey"]["passed"]

    def test_grail_approaching(self, sandbox):
        av = make_avalon(sandbox)
        m = Maturation(av)
        assessment = m.assess()
        assert assessment["milestones"]["elder_grail_approaching"]["passed"]

    def test_nyx_empathy(self, sandbox):
        av = make_avalon(sandbox)
        m = Maturation(av)
        clan_mother = av.informed_table._clan_mother
        for i in range(3):
            clan_mother.watch("Lancelot", {"served": False, "reason": f"fail {i}"})
        clan_mother.restore("Lancelot")
        assessment = m.assess()
        assert assessment["milestones"]["elder_nyx_empathy"]["passed"]


class TestAssessment:
    def test_assess_returns_all_fields(self, sandbox):
        av = make_avalon(sandbox)
        m = Maturation(av)
        assessment = m.assess()
        assert "current_stage" in assessment
        assert "stage_progress" in assessment
        assert "milestones" in assessment
        assert "total_milestones" in assessment

    def test_progress_advances(self, sandbox):
        av = make_avalon(sandbox)
        m = Maturation(av)
        before = m.assess()["passed_milestones"]
        av.faithkeeper.perform_ceremony()
        av.fusion.experience("discovery", "test", ["Nyx", "Avalon"], 0.8)
        av.longhouse.welcome("V", "legal rights help")
        after = m.assess()["passed_milestones"]
        assert after > before

    def test_growth_narrative(self, sandbox):
        av = make_avalon(sandbox)
        m = Maturation(av)
        narrative = m.growth_narrative()
        assert "seedling" in narrative.lower()
        assert "milestones" in narrative.lower()

    def test_wire(self, sandbox):
        av = make_avalon(sandbox)
        m = wire_maturation(av)
        assert isinstance(m, Maturation)


class TestStatus:
    def test_status(self, sandbox):
        av = make_avalon(sandbox)
        m = Maturation(av)
        status = m.status
        assert status["stage"] == "seedling"
        assert status["total_milestones"] == 21


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
