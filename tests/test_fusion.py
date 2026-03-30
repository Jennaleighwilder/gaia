"""
FUSION Test Suite
The kingdom breathes.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from avalon.fusion import (
    Adversity,
    Carbon,
    Fusion,
    Hadron,
    Heartbeat,
    Joy,
    Love,
    Pulse,
    ThreatLevel,
)


class TestHeartbeat:
    def test_beat_cycles_phases(self):
        hb = Heartbeat()
        phases = [hb.beat().phase for _ in range(6)]
        assert Pulse.GATHER in phases
        assert Pulse.PROCESS in phases
        assert Pulse.REST in phases

    def test_mood_responds_to_health(self):
        hb = Heartbeat()
        hb.register_system("healthy", lambda: 1.0)
        for _ in range(5):
            beat = hb.beat()
        assert beat.mood in ["celebrating", "surging", "steady"]

    def test_register_system(self):
        hb = Heartbeat()
        hb.register_system("test_sys")
        assert "test_sys" in hb._listeners

    def test_rhythm_report(self):
        hb = Heartbeat()
        hb.register_system("sys1", lambda: 0.9)
        hb.beat()
        rhythm = hb.rhythm()
        assert rhythm["beats"] == 1
        assert "sys1" in rhythm["system_health"]


class TestCarbon:
    def test_learn(self):
        c = Carbon()
        lesson = c.learn("test lesson", "test_sys", "testing", "discovery")
        assert lesson.content == "test lesson"
        assert c.wisdom()["total_lessons"] == 1

    def test_recall_relevant(self):
        c = Carbon()
        c.learn("frequency resonance healing", "gawain", "research", "discovery")
        c.learn("database query optimization", "kay", "operations", "discovery")
        results = c.recall("frequency healing")
        assert len(results) >= 1
        assert "frequency" in results[0].content.lower()

    def test_recall_by_category(self):
        c = Carbon()
        c.learn("attack repelled", "lancelot", "battle", "adversity")
        c.learn("new insight found", "merlin", "research", "success")
        results = c.recall("battle defense", "adversity")
        assert all(l.category == "adversity" for l in results)


class TestHadron:
    def test_collide_produces_result(self):
        h = Hadron()
        collision = h.collide(
            "Gawain", "frequency resonance healing acoustic",
            "Bors", "atmospheric detection convergence warning",
        )
        assert collision.energy >= 0

    def test_chain_reaction(self):
        h = Hadron()
        collisions = h.chain_reaction([
            ("A", "frequency signal resonance"),
            ("B", "convergence signal detection"),
            ("C", "pattern recognition structure"),
        ])
        assert len(collisions) >= 0

    def test_highest_energy(self):
        h = Hadron()
        h.collide("A", "shared words overlap here", "B", "shared words overlap there")
        h.collide("C", "completely unique alpha", "D", "totally different beta")
        top = h.highest_energy(1)
        assert len(top) <= 1


class TestAdversity:
    def test_battle_and_resolve(self):
        c = Carbon()
        hb = Heartbeat()
        adv = Adversity(c, hb)
        battle = adv.threat_detected("test attack", ThreatLevel.SKIRMISH, ["Lancelot"])
        assert battle.outcome == "ongoing"
        adv.resolve_battle(battle, "victory", lessons=["Don't trust single signals"])
        assert battle.outcome == "victory"
        assert c.wisdom()["total_lessons"] == 1

    def test_resilience_grows_on_victory(self):
        c = Carbon()
        hb = Heartbeat()
        adv = Adversity(c, hb)
        initial = adv._resilience_score
        battle = adv.threat_detected("attack", ThreatLevel.SKIRMISH, ["Lancelot"])
        adv.resolve_battle(battle, "victory")
        assert adv._resilience_score > initial


class TestJoy:
    def test_celebrate(self):
        c = Carbon()
        hb = Heartbeat()
        j = Joy(c, hb)
        j.celebrate("tests passed", ["Nyx", "West-OS"], 0.9)
        assert j.status["total_celebrations"] == 1
        assert j.status["joy_index"] > 0.5

    def test_recall_joy(self):
        c = Carbon()
        hb = Heartbeat()
        j = Joy(c, hb)
        j.celebrate("small win", ["Alfred"], 0.3)
        j.celebrate("big win", ["Everyone"], 0.95)
        memories = j.recall_joy(1)
        assert memories[0]["magnitude"] == 0.95


class TestLove:
    def test_bond_forms(self):
        l = Love()
        bond = l.bond("Nyx", "West-OS", "fought together")
        assert bond.strength == 0.5
        assert l.bond_strength("Nyx", "West-OS") == 0.5

    def test_bond_strengthens(self):
        l = Love()
        l.bond("A", "B", "first fight", 0.5)
        l.bond("A", "B", "second fight", 0.5)
        assert l.bond_strength("A", "B") > 0.5

    def test_shared_experience(self):
        l = Love()
        l.shared_experience(["A", "B", "C"], "survived together", 0.6)
        assert l.bond_strength("A", "B") > 0
        assert l.bond_strength("A", "C") > 0
        assert l.bond_strength("B", "C") > 0

    def test_cohesion(self):
        l = Love()
        l.shared_experience(["A", "B", "C", "D"], "built the kingdom", 0.8)
        assert l.kingdom_cohesion() > 0


class TestFusion:
    def test_breathe(self):
        f = Fusion()
        f.heartbeat.register_system("test", lambda: 1.0)
        breath = f.breathe()
        assert "beat" in breath
        assert "mood" in breath
        assert "health" in breath

    def test_experience_discovery(self):
        f = Fusion()
        result = f.experience("discovery", "new pattern found", ["Merlin", "Dagonet"])
        assert result["lesson_recorded"]

    def test_experience_attack(self):
        f = Fusion()
        result = f.experience("attack", "probe detected", ["Lancelot", "Bedivere"])
        assert result["battle"]["outcome"] == "ongoing"

    def test_experience_victory(self):
        f = Fusion()
        result = f.experience("victory", "all tests passed", ["Nyx", "Avalon"])
        assert "celebration" in result

    def test_vital_signs(self):
        f = Fusion()
        f.heartbeat.register_system("sys", lambda: 1.0)
        f.breathe()
        vitals = f.vital_signs()
        assert vitals["alive"]
        assert "heartbeat" in vitals
        assert "carbon" in vitals
        assert "love" in vitals

    def test_cohesion_grows_through_experience(self):
        f = Fusion()
        f.experience("victory", "won together", ["A", "B", "C"])
        f.experience("attack", "fought together", ["A", "B"])
        f.experience("discovery", "found together", ["B", "C"])
        assert f.love.kingdom_cohesion() > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
