"""FAITHKEEPER + INFORMED TABLE + LONGHOUSE Test Suite"""

import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from avalon.faithkeeper import (
    ThanksgivingAddress, SevenGenerations, Ceremony, Faithkeeper, wire_faithkeeper
)
from avalon.informed_table import (
    InformedVoice, ClanMother, InformedTable, wire_informed_table, Warning
)
from avalon.longhouse import (
    Longhouse, Service, ServiceTier, THREE_SISTERS, wire_longhouse
)
from avalon.fusion import Fusion
from avalon.merlin import Merlin
from avalon.healing import Healing
from avalon.knights import Knighthood
from avalon.round_table import RoundTable, Vote


class TestThanksgivingAddress:
    def test_speaks(self):
        result = ThanksgivingAddress.speak({"Nyx": 1.0, "GAIA": 0.9})
        assert result["alive_count"] == 2
        assert "narrative" in result

    def test_identifies_wounded(self):
        result = ThanksgivingAddress.speak({"Nyx": 1.0, "GAIA": 0.5})
        assert len(result["wounded"]) == 1

    def test_identifies_fallen(self):
        result = ThanksgivingAddress.speak({"Nyx": 1.0, "GAIA": 0.1})
        assert len(result["fallen"]) == 1

    def test_gratitude_ratio(self):
        result = ThanksgivingAddress.speak({"A": 1.0, "B": 1.0, "C": 0.1, "D": 0.1})
        assert result["gratitude_ratio"] == 0.5

    def test_empty_systems(self):
        result = ThanksgivingAddress.speak({})
        assert result["alive_count"] == 0


class TestSevenGenerations:
    def test_tags_adversity(self):
        tagged = SevenGenerations.tag_lesson("Attack detected", "adversity")
        assert "Seven Generations" in tagged
        assert "future" in tagged.lower()

    def test_tags_discovery(self):
        tagged = SevenGenerations.tag_lesson("New frequency found", "discovery")
        assert "Seven Generations" in tagged

    def test_tags_unknown(self):
        tagged = SevenGenerations.tag_lesson("Something happened", "unknown_category")
        assert "Seven Generations" in tagged


class TestFaithkeeper:
    def _make_avalon(self):
        class MinAvalon:
            pass

        av = MinAvalon()
        av.fusion = Fusion()
        av.merlin = Merlin()
        av.healing = Healing(
            carbon_recall=av.fusion.carbon.recall,
            carbon_learn=lambda **kw: av.fusion.carbon.learn(**kw),
        )
        for name in ["Nyx", "Avalon"]:
            av.fusion.heartbeat.register_system(name, lambda: 0.9)
        return av

    def test_perform_ceremony(self):
        av = self._make_avalon()
        fk = Faithkeeper(av)
        record = fk.perform_ceremony()
        assert record.number == 1
        assert record.thanksgiving is not None

    def test_multiple_ceremonies(self):
        av = self._make_avalon()
        fk = Faithkeeper(av)
        fk.perform_ceremony()
        fk.perform_ceremony()
        fk.perform_ceremony()
        assert fk.status["ceremonies_performed"] == 3

    def test_daemon_mode(self):
        av = self._make_avalon()
        fk = Faithkeeper(av, interval_seconds=0.1)
        fk.keep_faith()
        assert fk.is_keeping_faith()
        time.sleep(0.5)
        fk.lose_faith()
        assert not fk.is_keeping_faith()
        assert fk.status["ceremonies_performed"] >= 1

    def test_thanksgiving_now(self):
        av = self._make_avalon()
        fk = Faithkeeper(av)
        tg = fk.thanksgiving_now()
        assert "narrative" in tg

    def test_ceremony_history(self):
        av = self._make_avalon()
        fk = Faithkeeper(av)
        fk.perform_ceremony()
        fk.perform_ceremony()
        history = fk.ceremony_history(5)
        assert len(history) == 2


class TestClanMother:
    def test_no_warning_on_success(self):
        cm = ClanMother()
        warning = cm.watch("Lancelot", {"served": True})
        assert warning is None

    def test_warning_on_failure(self):
        cm = ClanMother()
        warning = cm.watch("Lancelot", {"served": False, "reason": "test"})
        assert warning is not None
        assert cm.warning_count("Lancelot") == 1

    def test_three_warnings_pulls_horns(self):
        cm = ClanMother()
        cm.watch("Lancelot", {"served": False, "reason": "fail 1"})
        cm.watch("Lancelot", {"served": False, "reason": "fail 2"})
        cm.watch("Lancelot", {"served": False, "reason": "fail 3"})
        assert cm.is_removed("Lancelot")

    def test_success_clears_warning(self):
        cm = ClanMother()
        cm.watch("Lancelot", {"served": False, "reason": "fail"})
        assert cm.warning_count("Lancelot") == 1
        cm.watch("Lancelot", {"served": True})
        assert cm.warning_count("Lancelot") == 0

    def test_restore(self):
        cm = ClanMother()
        for _ in range(3):
            cm.watch("Lancelot", {"served": False, "reason": "fail"})
        assert cm.is_removed("Lancelot")
        cm.restore("Lancelot")
        assert not cm.is_removed("Lancelot")


class TestInformedTable:
    def test_hold_council(self):
        table = RoundTable(quorum_ratio=0.618)
        kh = Knighthood()
        for name, knight in kh._knights.items():
            table.seat_knight(name, knight.domain.value, f"seal_{name}")
        informed = InformedTable(table, kh)
        result = informed.hold_informed_council("Test question")
        assert result["knights_spoke"] >= 1
        assert "decree" in result

    def test_knights_hear_previous(self):
        table = RoundTable(quorum_ratio=0.618)
        kh = Knighthood()
        for name, knight in kh._knights.items():
            table.seat_knight(name, knight.domain.value, f"seal_{name}")
        informed = InformedTable(table, kh)
        result = informed.hold_informed_council("Test question")
        conversation = result["conversation"]
        assert conversation[0]["heard_from"] is None
        if len(conversation) > 1:
            assert conversation[1]["heard_from"] == conversation[0]["knight"]

    def test_removed_knight_skipped(self):
        table = RoundTable(quorum_ratio=0.618)
        kh = Knighthood()
        for name, knight in kh._knights.items():
            table.seat_knight(name, knight.domain.value, f"seal_{name}")
        cm = ClanMother()
        for _ in range(3):
            cm.watch("Lancelot", {"served": False, "reason": "test"})
        informed = InformedTable(table, kh, cm)
        result = informed.hold_informed_council("Test question")
        speakers = [v["knight"] for v in result["conversation"]]
        assert "Lancelot" not in speakers


class TestThreeSisters:
    def test_always_present(self):
        lh = Longhouse()
        assert "Legal Advocacy" in lh._services
        assert "Community Guides" in lh._services
        assert "Weather Warnings" in lh._services

    def test_always_free(self):
        lh = Longhouse()
        for name in THREE_SISTERS:
            assert lh._services[name].free_forever

    def test_cannot_replace(self):
        lh = Longhouse()
        lh.plant_service("Legal Advocacy", "replaced", "nobody", "evil", "craft")
        assert lh._services["Legal Advocacy"].free_forever
        assert lh._services["Legal Advocacy"].tier == ServiceTier.THREE_SISTERS


class TestLonghouse:
    def test_welcome_serves(self):
        lh = Longhouse()
        result = lh.welcome("Maria", "I need legal rights help")
        assert result["welcomed"]
        assert result["served"]
        assert result["free"]

    def test_weather_match(self):
        lh = Longhouse()
        result = lh.welcome("James", "severe weather warning tornado")
        assert result["served"]
        assert result["service"] == "Weather Warnings"

    def test_community_match(self):
        lh = Longhouse()
        result = lh.welcome("Anon", "shelter food crisis resources")
        assert result["served"]
        assert result["service"] == "Community Guides"

    def test_unmatched_not_turned_away(self):
        lh = Longhouse()
        result = lh.welcome("Lost", "quantum neutrino flux capacitor")
        assert result["welcomed"]
        assert not result["served"]
        assert "not turned away" in result.get("reason", "")

    def test_census(self):
        lh = Longhouse()
        lh.welcome("A", "legal rights help")
        lh.welcome("B", "weather warning")
        census = lh.census()
        assert census["total_served"] == 2
        assert census["three_sisters_served"] == 2

    def test_joy_callback(self):
        celebrations = []
        lh = Longhouse(joy_callback=lambda d, p, m: celebrations.append(d))
        lh.welcome("A", "legal rights help")
        assert len(celebrations) >= 1

    def test_plant_service(self):
        lh = Longhouse()
        lh.plant_service("Custom", "custom service", "testers", "Gareth", "hearth")
        assert "Custom" in lh._services
        assert lh._services["Custom"].tier == ServiceTier.HEARTH


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
