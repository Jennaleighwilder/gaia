"""
AVALON Test Suite
All tests must pass before integration begins.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from avalon.avalon import Avalon, Castle, Village
from avalon.excalibur import Excalibur, LadyOfTheLake, SovereigntyState
from avalon.knights import Domain, Knight, KnightState, Knighthood, create_knights
from avalon.merlin import Merlin
from avalon.round_table import CouncilState, RoundTable, Vote


class TestExcalibur:
    def test_draw(self):
        import hashlib
        import hmac

        key = b"test"
        lady = LadyOfTheLake(lambda p: hmac.new(key, p.encode(), hashlib.sha512).digest())
        exc = Excalibur(lady)
        assert exc.draw("Arthur")
        assert exc.check_sovereignty() == SovereigntyState.WIELDED

    def test_seal_oath(self):
        import hashlib
        import hmac

        key = b"test"
        lady = LadyOfTheLake(lambda p: hmac.new(key, p.encode(), hashlib.sha512).digest())
        exc = Excalibur(lady)
        exc.draw("Arthur")
        oath = exc.seal_oath("Lancelot", "protect the realm")
        assert oath.knight_name == "Lancelot"
        assert not oath.broken

    def test_return_to_lake(self):
        import hashlib
        import hmac

        key = b"test"
        lady = LadyOfTheLake(lambda p: hmac.new(key, p.encode(), hashlib.sha512).digest())
        exc = Excalibur(lady)
        exc.draw("Arthur")
        exc.seal_oath("Lancelot", "protect")
        result = exc.return_to_lake()
        assert result["returned"]
        assert "Lancelot" in result["oaths_dissolved"]
        assert exc.check_sovereignty() == SovereigntyState.RETURNED_TO_LAKE

    def test_command_requires_wielding(self):
        import hashlib
        import hmac

        key = b"test"
        lady = LadyOfTheLake(lambda p: hmac.new(key, p.encode(), hashlib.sha512).digest())
        exc = Excalibur(lady)
        result = exc.command("attack")
        assert not result["executed"]


class TestRoundTable:
    def test_seat_and_count(self):
        rt = RoundTable()
        rt.seat_knight("Lancelot", "governance", "seal1")
        rt.seat_knight("Galahad", "truth", "seal2")
        assert rt.seated_count == 2

    def test_quorum_calculation(self):
        rt = RoundTable(quorum_ratio=0.618)
        for i in range(10):
            rt.seat_knight(f"Knight{i}", "domain", f"seal{i}")
        assert rt.quorum_needed == 7

    def test_convene_and_speak(self):
        rt = RoundTable()
        rt.seat_knight("Lancelot", "governance", "seal1")
        rt.convene("Should we attack?")
        voice = rt.speak("Lancelot", Vote.AYE, "The enemy is weak", 0.9)
        assert voice.vote == Vote.AYE

    def test_no_double_speaking(self):
        rt = RoundTable()
        rt.seat_knight("Lancelot", "governance", "seal1")
        rt.convene("Question?")
        rt.speak("Lancelot", Vote.AYE, "reason", 0.9)
        with pytest.raises(RuntimeError):
            rt.speak("Lancelot", Vote.NAY, "changed mind", 0.5)

    def test_decree_with_quorum(self):
        rt = RoundTable(quorum_ratio=0.5)
        rt.seat_knight("A", "d", "s1")
        rt.seat_knight("B", "d", "s2")
        rt.convene("Question?")
        rt.speak("A", Vote.AYE, "yes", 0.9)
        rt.speak("B", Vote.AYE, "yes", 0.8)
        decree = rt.decree("excalibur_seal")
        assert decree["decision"] == "APPROVED"

    def test_decree_without_quorum(self):
        rt = RoundTable(quorum_ratio=0.8)
        rt.seat_knight("A", "d", "s1")
        rt.seat_knight("B", "d", "s2")
        rt.seat_knight("C", "d", "s3")
        rt.convene("Question?")
        rt.speak("A", Vote.AYE, "yes", 0.9)
        rt.speak("B", Vote.NAY, "no", 0.9)
        rt.speak("C", Vote.NAY, "no", 0.8)
        decree = rt.decree("seal")
        assert decree["decision"] == "DENIED"

    def test_dissent_preserved(self):
        rt = RoundTable(quorum_ratio=0.5)
        rt.seat_knight("A", "d", "s1")
        rt.seat_knight("B", "d", "s2")
        rt.convene("Question?")
        rt.speak("A", Vote.AYE, "yes", 0.9)
        rt.speak("B", Vote.NAY, "I disagree because X", 0.9)
        decree = rt.decree("seal")
        assert len(decree["dissenting_voices"]) == 1
        assert decree["dissenting_voices"][0]["knight"] == "B"


class TestKnights:
    def test_all_12_created(self):
        knights = create_knights()
        assert len(knights) == 12

    def test_each_has_required_fields(self):
        knights = create_knights()
        for _, knight in knights.items():
            assert knight.name
            assert knight.title
            assert knight.domain
            assert knight.oath
            assert knight.wound
            assert knight.maps_to

    def test_knighthood_muster(self):
        kh = Knighthood()
        muster = kh.muster()
        assert muster["battle_ready"]
        assert muster["order_strength"] == 1.0

    def test_wound_reduces_strength(self):
        kh = Knighthood()
        lancelot = kh.summon("Lancelot")
        lancelot.wound_knight(0.5)
        assert lancelot.strength < 1.0
        assert lancelot.state == KnightState.WOUNDED

    def test_heal_restores(self):
        kh = Knighthood()
        lancelot = kh.summon("Lancelot")
        lancelot.wound_knight(0.5)
        lancelot.heal()
        assert lancelot.strength == 1.0
        assert lancelot.state == KnightState.SWORN


class TestMerlin:
    def test_observe_and_see(self):
        merlin = Merlin()
        merlin.observe("governance", "threshold state transitions protect against false alarms")
        merlin.observe("atmospheric", "threshold state transitions trigger weather warnings")
        insights = merlin.see()
        assert len(insights) > 0

    def test_counsel(self):
        merlin = Merlin()
        merlin.observe("governance", "AI safety needs convergence rules")
        merlin.observe("frequency", "118 Hz appears at sacred sites")
        merlin.see()
        counsel = merlin.counsel("What connects our systems?")
        assert counsel["merlin_speaks"]

    def test_prophesy(self):
        merlin = Merlin()
        prophecy = merlin.prophesy(
            ["118 Hz data", "Indus frequency hypothesis", "archaeoacoustic literature"],
            "Unified frequency paper connecting all three",
            0.85,
            "2026",
        )
        assert not prophecy.fulfilled

    def test_the_sight(self):
        merlin = Merlin()
        empty = merlin.the_sight()
        assert "empty" in empty.lower()
        merlin.observe("test", "pattern recognition frequency threshold")
        merlin.observe("other", "frequency analysis threshold detection")
        merlin.see()
        full = merlin.the_sight()
        assert "empty" not in full.lower()


class TestAvalon:
    def test_found_kingdom(self):
        av = Avalon()
        result = av.found_kingdom()
        assert result["sovereign"] == "Jennifer Leigh West"
        assert result["knights_sworn"] == 12
        assert result["status"] == "THE KINGDOM STANDS"

    def test_kingdom_status(self):
        av = Avalon()
        av.found_kingdom()
        status = av.kingdom_status()
        assert status["sovereign"] == "Jennifer Leigh West"
        assert status["castle"]["all_clear"]
        assert status["village"]["satisfaction_rate"] == 0.97

    def test_hold_council(self):
        av = Avalon()
        av.found_kingdom()
        council = av.hold_council("Should we proceed?")
        assert council["council_convened"]
        assert council["quorum_needed"] == 8


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
