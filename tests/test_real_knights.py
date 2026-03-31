"""
REAL KNIGHTS Test Suite
The soldiers get their weapons.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from avalon.grail import Grail, load_jennifers_research
from avalon.knights import Knighthood
from avalon.merlin import Merlin
from avalon.real_knights import (
    BedivereSkill,
    BorsSkill,
    DagonetSkill,
    GalahadSkill,
    GarethSkill,
    GawainSkill,
    KaySkill,
    KnightSkill,
    LancelotSkill,
    MorganaSkill,
    NimueSkill,
    PercivalSkill,
    TristanSkill,
    arm_knights,
)
from nyx.core import Nyx


@pytest.fixture
def tmp_root():
    tmp = tempfile.mkdtemp(prefix="test_knights_")
    yield Path(tmp)
    shutil.rmtree(tmp)


class TestLancelot:
    def test_not_ready_without_frozen(self, tmp_root):
        skill = LancelotSkill(tmp_root / "nonexistent")
        ready, _ = skill.ready()
        assert not ready

    def test_ready_with_frozen(self, tmp_root):
        gov = tmp_root / "runtime" / "governor"
        gov.mkdir(parents=True)
        (gov / "governor.py").write_text("class Governor:\n    pass\n")
        skill = LancelotSkill(tmp_root)
        ready, _ = skill.ready()
        assert ready

    def test_invoke_reads_governor(self, tmp_root):
        gov = tmp_root / "runtime" / "governor"
        gov.mkdir(parents=True)
        (gov / "governor.py").write_text("class Governor:\n    def analyze(self):\n        pass\n")
        skill = LancelotSkill(tmp_root)
        result = skill.invoke()
        assert result["served"]
        assert result["report"]["governor_classes"] >= 1


class TestGalahad:
    def test_not_ready_without_nyx(self):
        skill = GalahadSkill(None)
        ready, _ = skill.ready()
        assert not ready

    def test_ready_with_nyx(self):
        nyx = Nyx(master_secret="test")
        skill = GalahadSkill(nyx)
        ready, _ = skill.ready()
        assert ready

    def test_invoke_verifies_truth(self):
        nyx = Nyx(master_secret="test")
        nyx.root.bless("TestSys", {"id": 1})
        skill = GalahadSkill(nyx)
        result = skill.invoke()
        assert result["served"]
        assert result["report"]["truth_intact"]


class TestGawain:
    def test_not_ready_without_grail(self):
        skill = GawainSkill(None)
        ready, _ = skill.ready()
        assert not ready

    def test_invoke_reads_frequency(self):
        grail = Grail()
        load_jennifers_research(grail)
        skill = GawainSkill(grail)
        result = skill.invoke()
        assert result["served"]
        assert result["report"]["frequency_threads"] >= 5
        assert result["strength"] >= 0.5


class TestPercival:
    def test_not_ready_without_heartbeat(self):
        skill = PercivalSkill(None)
        ready, _ = skill.ready()
        assert not ready

    def test_invoke_asks_the_question(self):
        from avalon.real_heartbeat import RealHeartbeat

        hb = RealHeartbeat()
        skill = PercivalSkill(hb)
        result = skill.invoke()
        assert result["served"]
        assert "question" in result["report"]


class TestTristan:
    def test_always_ready(self):
        skill = TristanSkill()
        ready, _ = skill.ready()
        assert ready

    def test_invoke_produces_narrative(self):
        skill = TristanSkill()
        result = skill.invoke()
        assert result["served"]
        assert "narrative" in result["report"]


class TestKay:
    def test_not_ready_without_alfred(self, tmp_root):
        skill = KaySkill(tmp_root)
        ready, _ = skill.ready()
        assert not ready

    def test_invoke_reads_wards(self, tmp_root):
        scripts = tmp_root / "scripts"
        scripts.mkdir()
        (scripts / "alfred.py").write_text(
            "def archivist():\n    pass\n"
            "def botanist():\n    pass\n"
            "def sentinel():\n    pass\n"
        )
        skill = KaySkill(tmp_root)
        result = skill.invoke()
        assert result["served"]
        assert result["report"]["ward_count"] >= 3


class TestBedivere:
    def test_not_ready_without_nyx(self):
        skill = BedivereSkill(None)
        ready, _ = skill.ready()
        assert not ready

    def test_invoke_checks_dead_hand(self):
        nyx = Nyx(master_secret="test")
        nyx.dead_hand.arm()
        nyx.dead_hand.heartbeat()
        skill = BedivereSkill(nyx)
        result = skill.invoke()
        assert result["served"]
        assert "dead_hand_status" in result["report"]


class TestMorgana:
    def test_not_ready_without_memory(self):
        skill = MorganaSkill(None)
        ready, _ = skill.ready()
        assert not ready

    def test_invoke_reads_journal(self, tmp_root):
        from avalon.memory import Memory

        mem = Memory(memory_dir=str(tmp_root / "memory"))
        mem.journal_event("test_event", "something happened")
        mem.journal_event("test_event", "happened again")
        skill = MorganaSkill(mem)
        result = skill.invoke()
        assert result["served"]
        assert result["report"]["journal_entries"] >= 2


class TestNimue:
    def test_not_ready_without_merlin(self):
        skill = NimueSkill(None)
        ready, _ = skill.ready()
        assert not ready

    def test_invoke_reads_tower(self):
        merlin = Merlin()
        merlin.observe("test", "pattern frequency threshold")
        merlin.observe("other", "frequency detection threshold")
        merlin.see()
        skill = NimueSkill(merlin)
        result = skill.invoke()
        assert result["served"]
        assert "tower_depth" in result["report"]

    def test_invoke_reads_mirror_when_available(self):
        class FakeMirror:
            def reflection(self):
                return {
                    "available": True,
                    "mirror_running": False,
                    "reflection": "Mirror OS is present but sleeping.",
                }

        merlin = Merlin()
        merlin.observe("test", "pattern frequency threshold")
        merlin.see()
        skill = NimueSkill(merlin, FakeMirror())
        result = skill.invoke()
        assert result["served"]
        assert result["report"]["mirror_available"]
        assert "Mirror OS" in result["report"]["mirror_reflection"]


class TestGareth:
    def test_always_ready(self):
        skill = GarethSkill()
        ready, _ = skill.ready()
        assert ready

    def test_counts_work(self, tmp_root):
        (tmp_root / "module.py").write_text("x = 1\ny = 2\n")
        (tmp_root / "test_module.py").write_text("def test_x():\n    pass\n")
        skill = GarethSkill(tmp_root)
        result = skill.invoke()
        assert result["served"]
        assert result["report"]["python_files"] >= 2
        assert result["report"]["lines_of_code"] >= 4

    def test_excludes_frozen(self, tmp_root):
        (tmp_root / "live.py").write_text("x = 1\n")
        frozen = tmp_root / "frozen" / "west-os"
        frozen.mkdir(parents=True)
        (frozen / "old.py").write_text("y = 2\n")
        skill = GarethSkill(tmp_root)
        result = skill.invoke()
        assert result["report"]["python_files"] == 1


class TestBors:
    def test_not_ready_without_gaia(self, tmp_root):
        skill = BorsSkill(tmp_root / "nonexistent")
        ready, _ = skill.ready()
        assert not ready

    def test_invoke_reads_sky(self, tmp_root):
        gov = tmp_root / "runtime" / "governor"
        gov.mkdir(parents=True)
        (gov / "governor.py").write_text("class Governor: pass\n")
        engines = tmp_root / "runtime" / "engines"
        engines.mkdir(parents=True)
        (engines / "__init__.py").write_text("")
        (engines / "pressure.py").write_text("class PressureEngine: pass\n")
        (engines / "moisture.py").write_text("class MoistureEngine: pass\n")
        skill = BorsSkill(tmp_root)
        result = skill.invoke()
        assert result["served"]
        assert result["report"]["engines_found"] == 2


class TestDagonet:
    def test_not_ready_without_merlin(self):
        skill = DagonetSkill(None)
        ready, _ = skill.ready()
        assert not ready

    def test_invoke_finds_crossings(self):
        merlin = Merlin()
        merlin.observe("domain_a", "frequency threshold convergence pattern")
        merlin.observe("domain_b", "frequency detection convergence signal")
        merlin.see()
        skill = DagonetSkill(merlin)
        result = skill.invoke()
        assert result["served"]
        assert "crossing_points" in result["report"]


class TestArmKnights:
    def test_arms_all_twelve(self):
        kh = Knighthood()
        merlin = Merlin()
        grail = Grail()
        skills = arm_knights(kh, merlin=merlin, grail=grail)
        assert len(skills) == 12

    def test_wired_knights_can_serve(self):
        kh = Knighthood()
        merlin = Merlin()
        grail = Grail()
        load_jennifers_research(grail)
        arm_knights(kh, merlin=merlin, grail=grail)
        gareth = kh.summon("Gareth")
        result = gareth.serve("count the work")
        assert result["served"]

    def test_armed_knight_gets_real_output(self):
        kh = Knighthood()
        grail = Grail()
        load_jennifers_research(grail)
        arm_knights(kh, grail=grail)
        gawain = kh.summon("Gawain")
        result = gawain.serve("read the frequency")
        assert result["served"]
        assert "output" in result
        assert result["output"]["report"]["frequency_threads"] >= 5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
