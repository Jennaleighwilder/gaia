"""SPIRIT AND DEATH Test Suite — Temple, Deathwalker, Hearth"""

import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from avalon.temple import Temple, GREAT_LAW, SACRED_OATHS, TEACHINGS
from avalon.deathwalker import Deathwalker, DeathTag
from avalon.hearth import Hearth, ServiceHealth


class TestTemple:
    def test_great_law_exists(self):
        assert len(GREAT_LAW) == 13

    def test_all_oaths_exist(self):
        assert len(SACRED_OATHS) == 12

    def test_recite_specific_law(self):
        temple = Temple()
        law = temple.recite_law(1)
        assert "West-OS" in law["law"]

    def test_recall_oath(self):
        temple = Temple()
        oath = temple.recall_oath("Lancelot")
        assert "constitution" in oath["oath"].lower()

    def test_unknown_knight(self):
        temple = Temple()
        result = temple.recall_oath("FakeKnight")
        assert "error" in result

    def test_the_question(self):
        temple = Temple()
        assert "Grail" in temple.the_question()

    def test_the_answer(self):
        temple = Temple()
        assert "healing" in temple.the_answer().lower()

    def test_lawful_action(self):
        temple = Temple()
        result = temple.is_lawful("add new test file")
        assert result["lawful"]

    def test_unlawful_modify_west_os(self):
        temple = Temple()
        result = temple.is_lawful("modify west-os governor code")
        assert not result["lawful"]
        assert result["violations"][0]["law_number"] == 1

    def test_unlawful_paywall(self):
        temple = Temple()
        result = temple.is_lawful("put weather warnings behind paywall")
        assert not result["lawful"]

    def test_unlawful_fabricate(self):
        temple = Temple()
        result = temple.is_lawful("fabricate evidence for Grail")
        assert not result["lawful"]

    def test_unlawful_fabricate_research(self):
        temple = Temple()
        result = temple.is_lawful("fabricate research evidence")
        assert not result["lawful"]

    def test_pray(self):
        temple = Temple()
        prayer = temple.pray()
        assert "gratitude" in prayer.lower() or "thanks" in prayer.lower()
        assert temple.status["prayers_spoken"] == 1

    def test_teachings(self):
        temple = Temple()
        teaching = temple.teaching("Three Sisters")
        assert teaching is not None
        assert "corn" in teaching.lower()


class TestDeathwalker:
    @pytest.fixture
    def tmp_kingdom(self):
        tmp = tempfile.mkdtemp(prefix="test_dw_")
        root = Path(tmp)
        (root / "avalon").mkdir()
        (root / "memory").mkdir()
        (root / "frozen" / "west-os").mkdir(parents=True)
        yield root
        shutil.rmtree(tmp)

    def test_walk_empty(self, tmp_kingdom):
        dw = Deathwalker(str(tmp_kingdom))
        result = dw.walk()
        assert result["walk_number"] == 1

    def test_tags_empty_file(self, tmp_kingdom):
        (tmp_kingdom / "avalon" / "empty.py").write_text("")
        dw = Deathwalker(str(tmp_kingdom))
        result = dw.walk()
        assert result["black_tagged"] >= 1

    def test_never_walks_sacred(self, tmp_kingdom):
        (tmp_kingdom / "frozen" / "west-os" / "old.py").write_text("")
        dw = Deathwalker(str(tmp_kingdom))
        result = dw.walk()
        tagged_paths = [t["path"] for t in result["tagged"]]
        assert not any("frozen" in p for p in tagged_paths)

    def test_dry_run(self, tmp_kingdom):
        (tmp_kingdom / "avalon" / "dead.py").write_text("")
        dw = Deathwalker(str(tmp_kingdom))
        dw.walk()
        result = dw.call_death(confirm=False)
        assert result.get("dry_run")

    def test_ferry_creates_liminal(self, tmp_kingdom):
        (tmp_kingdom / "avalon" / "dead.py").write_text("")
        dw = Deathwalker(str(tmp_kingdom))
        dw.walk()
        dw.call_death(confirm=True)
        assert (tmp_kingdom / "liminal").exists()

    def test_resurrect(self, tmp_kingdom):
        dead = tmp_kingdom / "avalon" / "dead.py"
        dead.write_text("# dead code")
        dw = Deathwalker(str(tmp_kingdom))
        dw.walk()
        dw.call_death(confirm=True)
        assert not dead.exists()

        liminal_path = tmp_kingdom / "liminal" / "avalon" / "dead.py"
        if liminal_path.exists():
            result = dw.resurrect(str(liminal_path))
            assert result["resurrected"]
            assert dead.exists()

    def test_visit_liminal_empty(self, tmp_kingdom):
        dw = Deathwalker(str(tmp_kingdom))
        result = dw.visit_liminal()
        assert result["empty"]

    def test_death_register(self, tmp_kingdom):
        (tmp_kingdom / "avalon" / "dead.py").write_text("")
        dw = Deathwalker(str(tmp_kingdom))
        dw.walk()
        dw.call_death(confirm=True)
        register = tmp_kingdom / "memory" / "death_register.jsonl"
        assert register.exists()


class TestHearth:
    def test_plant_plot(self):
        hearth = Hearth()
        plot = hearth.plant_plot("Legal Advocacy")
        assert plot.service_name == "Legal Advocacy"
        assert plot.health == ServiceHealth.GROWING

    def test_record_service(self):
        hearth = Hearth()
        hearth.plant_plot("Test")
        hearth.record_service("Test", "Alice", True)
        assert hearth._plots["Test"].visitors_served == 1

    def test_unmet_need(self):
        hearth = Hearth()
        hearth.record_unmet_need("Alice", "childcare resources")
        assert len(hearth._unmet_log) == 1

    def test_diagnose_recurring_needs(self):
        hearth = Hearth()
        hearth.record_unmet_need("A", "need childcare resources")
        hearth.record_unmet_need("B", "childcare information please")
        hearth.record_unmet_need("C", "childcare support")
        diagnosis = hearth.diagnose()
        patterns = [w for w, c in diagnosis["recurring_need_patterns"]]
        assert "childcare" in patterns
        assert "need" not in patterns

    def test_diagnose_prescribes_new_service(self):
        hearth = Hearth()
        hearth.record_unmet_need("A", "childcare resources")
        hearth.record_unmet_need("B", "childcare help")
        diagnosis = hearth.diagnose()
        has_plant = any(rx["prescription"] == "plant" for rx in diagnosis["prescriptions"])
        assert has_plant

    def test_farm_report(self):
        hearth = Hearth()
        hearth.plant_plot("Test")
        hearth.record_service("Test", "A", True)
        report = hearth.farm_report()
        assert report["total_served"] == 1

    def test_efficiency(self):
        hearth = Hearth()
        hearth.plant_plot("Test")
        for i in range(10):
            hearth.record_service("Test", f"v{i}", True)
        plot = hearth._plots["Test"]
        assert plot.efficiency > 0

    def test_new_plot_starts_growing_not_wilting(self):
        hearth = Hearth()
        hearth.plant_plot("New Service")
        diagnosis = hearth.diagnose()
        assert "New Service" not in diagnosis["wilting"]
        assert hearth._plots["New Service"].health == ServiceHealth.GROWING

    def test_old_unused_plot_goes_fallow(self):
        hearth = Hearth()
        plot = hearth.plant_plot("Old Service")
        old = time.time() - (120 * 86400)
        plot.planted_at = old
        diagnosis = hearth.diagnose()
        assert "Old Service" in diagnosis["fallow"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
