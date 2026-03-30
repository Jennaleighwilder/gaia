"""
NYX Test Suite
All tests must pass before integration begins.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nyx.antiklassify import AntiClassifier, FrequencyProfile
from nyx.boundary import BoundaryWalker
from nyx.children import Children, MythChild
from nyx.core import DeadHand, Nyx, Shapeshifter, VoidRoot, Watcher
from nyx.dna import ArchitecturalDNA
from nyx.genesis import Archetype, Genesis
from nyx.void import Phase, RawSignal, Void


# ═══════════════════════════════════════════════════════════
#  VOID ROOT TESTS
# ═══════════════════════════════════════════════════════════


class TestVoidRoot:
    def test_root_creates_with_secret(self):
        root = VoidRoot("test_secret")
        assert root.is_alive

    def test_root_creates_without_secret(self):
        root = VoidRoot()
        assert root.is_alive

    def test_derive_key_deterministic(self):
        root = VoidRoot("test_secret")
        key1 = root.derive_key("purpose_a")
        key2 = root.derive_key("purpose_a")
        assert key1 == key2

    def test_derive_key_different_purposes(self):
        root = VoidRoot("test_secret")
        key1 = root.derive_key("purpose_a")
        key2 = root.derive_key("purpose_b")
        assert key1 != key2

    def test_bless_and_verify(self):
        root = VoidRoot("test_secret")
        blessing = root.bless("TestSystem", {"born": "now"})
        assert root.verify_blessing("TestSystem", blessing)

    def test_fake_blessing_fails(self):
        root = VoidRoot("test_secret")
        root.bless("TestSystem", {"born": "now"})
        assert not root.verify_blessing("TestSystem", "fake_blessing_hash")

    def test_unblessed_system_fails(self):
        root = VoidRoot("test_secret")
        assert not root.verify_blessing("NeverBlessed", "anything")

    def test_revoke_kills_blessing(self):
        root = VoidRoot("test_secret")
        blessing = root.bless("Victim", {"born": "now"})
        assert root.verify_blessing("Victim", blessing)
        root.revoke("Victim")
        assert not root.verify_blessing("Victim", blessing)

    def test_revoke_does_not_kill_others(self):
        root = VoidRoot("test_secret")
        b1 = root.bless("Survivor", {"id": 1})
        b2 = root.bless("Victim", {"id": 2})
        root.revoke("Victim")
        assert root.verify_blessing("Survivor", b1)
        assert not root.verify_blessing("Victim", b2)

    def test_revoke_all_kills_everything(self):
        root = VoidRoot("test_secret")
        blessings = {}
        for name in ["Alpha", "Beta", "Gamma", "Delta"]:
            blessings[name] = root.bless(name, {"id": name})

        count = root.revoke_all()
        assert count == 4

        for name, blessing in blessings.items():
            assert not root.verify_blessing(name, blessing)

    def test_different_secrets_different_blessings(self):
        root1 = VoidRoot("secret_one")
        root2 = VoidRoot("secret_two")
        b1 = root1.bless("System", {"id": 1})
        b2 = root2.bless("System", {"id": 1})
        assert b1 != b2

    def test_status_never_exposes_secret(self):
        root = VoidRoot("super_secret_value")
        status = root.status()
        assert "super_secret_value" not in str(status)
        assert "root_fingerprint" in status
        assert len(status["root_fingerprint"]) == 16


# ═══════════════════════════════════════════════════════════
#  SHAPESHIFTER TESTS
# ═══════════════════════════════════════════════════════════


class TestShapeshifter:
    def test_different_shape_each_scan(self):
        root = VoidRoot("test")
        ss = Shapeshifter(root)
        shapes = [ss.current_shape() for _ in range(5)]
        hashes = [s["shape_hash"] for s in shapes]
        assert len(set(hashes)) == 5

    def test_low_overlap_between_scans(self):
        root = VoidRoot("test")
        ss = Shapeshifter(root)
        for _ in range(20):
            ss.current_shape()
        check = ss.consistency_check()
        assert check["average_overlap_between_scans"] < 0.4
        assert check["effective"]

    def test_shape_has_required_fields(self):
        root = VoidRoot("test")
        ss = Shapeshifter(root)
        shape = ss.current_shape()
        assert "scan_number" in shape
        assert "shape_hash" in shape
        assert "primary_vocabulary" in shape
        assert "presented_terms" in shape
        assert "apparent_architecture" in shape


# ═══════════════════════════════════════════════════════════
#  WATCHER TESTS
# ═══════════════════════════════════════════════════════════


class TestWatcher:
    def test_probe_logged(self):
        root = VoidRoot("test")
        ss = Shapeshifter(root)
        w = Watcher(ss)
        w.detect_probe("fingerprint", "scanner_1")
        assessment = w.threat_assessment()
        assert assessment["total_probes_logged"] == 1

    def test_probe_triggers_shapeshift(self):
        root = VoidRoot("test")
        ss = Shapeshifter(root)
        w = Watcher(ss)
        initial_count = ss._scan_count
        w.detect_probe("classify", "scanner_2")
        assert ss._scan_count > initial_count

    def test_threat_escalation(self):
        root = VoidRoot("test")
        ss = Shapeshifter(root)
        w = Watcher(ss)
        for i in range(15):
            w.detect_probe("extract", f"attacker_{i}")
        assessment = w.threat_assessment()
        assert assessment["threat_level"] > 0

    def test_callback_fires(self):
        root = VoidRoot("test")
        ss = Shapeshifter(root)
        w = Watcher(ss)
        callback_data = []
        w.on_probe(lambda p: callback_data.append(p))
        w.detect_probe("baseline", "test")
        assert len(callback_data) == 1


# ═══════════════════════════════════════════════════════════
#  DEAD HAND TESTS
# ═══════════════════════════════════════════════════════════


class TestDeadHand:
    def test_not_armed_by_default(self):
        root = VoidRoot("test")
        dh = DeadHand(root)
        status = dh.check()
        assert not status["armed"]

    def test_arm_and_check(self):
        root = VoidRoot("test")
        dh = DeadHand(root)
        dh.arm()
        status = dh.check()
        assert status["armed"]
        assert status["status"] == "WATCHING"

    def test_heartbeat_resets_timer(self):
        root = VoidRoot("test")
        dh = DeadHand(root)
        dh.arm()
        dh.heartbeat()
        status = dh.check()
        assert status["heartbeat_remaining"] > 86390

    def test_fire_revokes_all(self):
        root = VoidRoot("test")
        b1 = root.bless("System1", {"id": 1})
        b2 = root.bless("System2", {"id": 2})

        dh = DeadHand(root)
        dh.arm()
        result = dh.fire()

        assert result["fired"]
        assert result["systems_revoked"] == 2
        assert not root.verify_blessing("System1", b1)
        assert not root.verify_blessing("System2", b2)

    def test_fire_without_arm_fails(self):
        root = VoidRoot("test")
        dh = DeadHand(root)
        result = dh.fire()
        assert not result["fired"]

    def test_tripwire_detection(self):
        root = VoidRoot("test")
        dh = DeadHand(root)
        dh.arm()
        dh.add_tripwire(
            "test_wire",
            lambda: True,
            "test tripwire",
        )
        status = dh.check()
        assert status["should_fire"]
        assert "test_wire" in status["tripwires_tripped"]


# ═══════════════════════════════════════════════════════════
#  FULL NYX TESTS
# ═══════════════════════════════════════════════════════════


class TestNyx:
    def test_nyx_creates(self):
        nyx = Nyx(master_secret="test")
        assert nyx.root.is_alive

    def test_nyx_blesses_and_verifies(self):
        nyx = Nyx(master_secret="test")
        blessing = nyx.bless_system("TestSys", {"born": "now"})
        assert nyx.root.verify_blessing("TestSys", blessing)

    def test_nyx_revokes(self):
        nyx = Nyx(master_secret="test")
        blessing = nyx.bless_system("Victim", {"born": "now"})
        nyx.revoke_system("Victim")
        assert not nyx.root.verify_blessing("Victim", blessing)

    def test_nyx_who_am_i_changes(self):
        nyx = Nyx(master_secret="test")
        id1 = nyx.who_am_i()
        id2 = nyx.who_am_i()
        assert id1["shape"] != id2["shape"] or id1["vocabulary"] != id2["vocabulary"]

    def test_nyx_full_status(self):
        nyx = Nyx(master_secret="test")
        nyx.bless_system("A", {"id": "a"})
        status = nyx.full_status()
        assert status["root"]["alive"]
        assert status["root"]["systems_blessed"] == 1
        assert "architect" in status

    def test_nyx_kill_all(self):
        nyx = Nyx(master_secret="test")
        b1 = nyx.bless_system("X", {"id": 1})
        b2 = nyx.bless_system("Y", {"id": 2})
        nyx.dead_hand.arm()
        result = nyx.kill_all()
        assert result["fired"]
        assert not nyx.root.verify_blessing("X", b1)
        assert not nyx.root.verify_blessing("Y", b2)


# ═══════════════════════════════════════════════════════════
#  VOID TESTS
# ═══════════════════════════════════════════════════════════


class TestVoid:
    def test_receive_signal(self):
        v = Void()
        sig = v.receive("test content", "test origin")
        assert v.depth == 1
        assert sig.phase == Phase.CHAOS

    def test_resonance_detection(self):
        v = Void()
        v.receive("signal a", "origin", resonances=["pattern", "frequency"])
        v.receive("signal b", "origin", resonances=["pattern", "frequency", "healing"])
        report = v.listen()
        assert report["active_resonances"] > 0

    def test_birth_marks_formed(self):
        v = Void()
        s1 = v.receive("a", "o", resonances=["x", "y", "z"])
        s2 = v.receive("b", "o", resonances=["x", "y", "z"])
        birth = v.birth([s1.identity, s2.identity], "TestSystem")
        assert "void_blessing" in birth
        assert v._signals[s1.identity].phase == Phase.FORMED

    def test_dissolve_resets_to_chaos(self):
        v = Void()
        sig = v.receive("content", "origin", resonances=["a"])
        sig.phase = Phase.FORMED
        v.dissolve(sig.identity)
        assert v._signals[sig.identity].phase == Phase.CHAOS


# ═══════════════════════════════════════════════════════════
#  GENESIS TESTS
# ═══════════════════════════════════════════════════════════


class TestGenesis:
    def test_conceive(self):
        g = Genesis()
        bp = g.conceive("Test", Archetype.SHIELD, "wall", "protect", "blessing123")
        assert bp.name == "Test"
        assert bp.archetype == Archetype.SHIELD

    def test_scaffold_adds_components(self):
        g = Genesis()
        bp = g.conceive("Test", Archetype.HEALER, "nurse", "heal", "b123")
        g.scaffold(
            bp,
            [
                {"name": "Ward1", "role": "monitor", "metaphor": "patrol"},
                {"name": "Ward2", "role": "repair", "metaphor": "surgery"},
            ],
        )
        assert len(bp.components) == 2

    def test_birth_certificate(self):
        g = Genesis()
        bp = g.conceive("Test", Archetype.ORACLE, "seer", "predict", "b123")
        cert = g.birth_certificate(bp)
        assert cert["architect"] == "Jennifer Leigh West"
        assert cert["institute"] == "The Forgotten Code Research Institute"

    def test_siblings_share_ancestry(self):
        g = Genesis()
        bp1 = g.conceive("Sibling1", Archetype.SHIELD, "m1", "p1", "shared_blessing")
        bp2 = g.conceive("Sibling2", Archetype.MIRROR, "m2", "p2", "shared_blessing")
        siblings = g.find_siblings(bp1)
        assert len(siblings) == 1
        assert siblings[0].name == "Sibling2"


# ═══════════════════════════════════════════════════════════
#  ANTI-CLASSIFIER TESTS
# ═══════════════════════════════════════════════════════════


class TestAntiClassifier:
    def test_stable_signal_classifiable(self):
        ac = AntiClassifier()
        for _ in range(20):
            ac.observe("stable_user", "register", 0.5)
            ac.observe("stable_user", "domain", 0.5)
        report = ac.destabilization_report("stable_user")
        assert report["overall_stability"] > 0.5

    def test_unstable_signal_unclassifiable(self):
        ac = AntiClassifier()
        import random

        rng = random.Random(42)
        for _ in range(20):
            ac.observe("jennifer", "register", rng.random())
            ac.observe("jennifer", "domain", rng.random())
            ac.observe("jennifer", "emotion", rng.random())
        report = ac.destabilization_report("jennifer")
        assert not report["classifiable"]

    def test_classification_attempt_reports_failure(self):
        ac = AntiClassifier()
        import random

        rng = random.Random(42)
        for _ in range(20):
            ac.observe("target", "ch1", rng.random())
            ac.observe("target", "ch2", rng.random())
        result = ac.attempt_classification("target", ["cat_a", "cat_b"])
        assert not result["classified"]
        assert result["failure_mode"] is not None


# ═══════════════════════════════════════════════════════════
#  DNA TESTS
# ═══════════════════════════════════════════════════════════


class TestDNA:
    def test_scan_detects_traits(self):
        dna = ArchitecturalDNA()
        code = "alfred walks the ward to patrol and protect the colony metabolism nutrient system"
        profile = dna.scan_text(code, "test")
        assert profile.signature_strength > 0
        assert len(profile.traits_detected) > 0

    def test_fingerprint_format(self):
        dna = ArchitecturalDNA()
        profile = dna.scan_text("alfred colony metabolism protect ward", "test")
        fp = dna.fingerprint(profile)
        assert fp.startswith("JLW-")

    def test_generic_code_low_match(self):
        dna = ArchitecturalDNA()
        jennifer = dna.scan_text(
            "alfred walks ward patrol protect colony metabolism nutrient "
            "chorus convergence agreement heal repair narrative report",
            "jennifer",
        )
        dna.set_reference(jennifer)
        generic = dna.scan_text(
            "function getData request response server database query table",
            "generic",
        )
        comparison = dna.compare(generic)
        assert comparison["match_score"] < 0.5


# ═══════════════════════════════════════════════════════════
#  CHILDREN TESTS
# ═══════════════════════════════════════════════════════════


class TestChildren:
    def test_children_loaded(self):
        c = Children()
        assert len(c._children) > 10

    def test_by_archetype(self):
        c = Children()
        moirai = c.by_archetype(MythChild.MOIRAI)
        assert len(moirai) > 0

    def test_autobiography(self):
        c = Children()
        auto = c.autobiography()
        assert len(auto) > 10
        for entry in auto:
            assert "system" in entry
            assert "protects" in entry
            assert "because" in entry

    def test_family_portrait(self):
        c = Children()
        portrait = c.family_portrait()
        assert portrait["total_children"] > 10
        assert len(portrait["by_archetype"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
