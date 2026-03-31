"""
REAL MERLIN Test Suite
The pattern oracle sees real signals.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from avalon.fusion import Fusion
from avalon.merlin import Merlin
from avalon.real_merlin import Feed, RealMerlin, SignalExtractor, wire_real_merlin


class TestFeed:
    def test_create_feed(self):
        f = Feed(name="test", domain="testing", collector=lambda: {"value": 1})
        assert f.name == "test"
        assert f.active

    def test_poll_returns_data(self):
        f = Feed(name="test", domain="testing", collector=lambda: {"value": 42}, poll_interval_seconds=0)
        data = f.poll()
        assert data is not None
        assert data["value"] == 42

    def test_poll_respects_interval(self):
        f = Feed(name="test", domain="testing", collector=lambda: {"value": 1}, poll_interval_seconds=9999)
        f.poll()
        data = f.poll()
        assert data is None

    def test_poll_records_history(self):
        f = Feed(name="test", domain="testing", collector=lambda: {"value": 1}, poll_interval_seconds=0)
        f.poll()
        f.poll()
        assert len(f.history) == 2

    def test_latest_returns_most_recent(self):
        f = Feed(name="test", domain="testing", collector=lambda: {"value": 99}, poll_interval_seconds=0)
        f.poll()
        assert f.latest["value"] == 99

    def test_error_counting(self):
        def failing_collector():
            raise RuntimeError("test error")

        f = Feed(name="test", domain="testing", collector=failing_collector, poll_interval_seconds=0)
        f.poll()
        assert f.errors == 1
        assert f.active

    def test_deactivates_after_many_errors(self):
        def failing():
            raise RuntimeError("fail")

        f = Feed(name="test", domain="testing", collector=failing, poll_interval_seconds=0)
        for _ in range(11):
            f.poll()
        assert not f.active


class TestSignalExtractor:
    def test_heartbeat_extraction(self):
        data = {
            "mood": "steady",
            "kingdom_health": 0.89,
            "systems": {
                "Nyx": {"health": 1.0},
                "GAIA": {"health": 0.48, "issues": ["data bloat"]},
            },
        }
        signals = SignalExtractor.from_heartbeat(data)
        assert len(signals) >= 2
        domains = [s[0] for s in signals]
        assert "kingdom_health" in domains

    def test_healing_extraction(self):
        data = {
            "active_wounds": 1,
            "healed_total": 3,
            "treatment_success_rate": 0.75,
            "active": [{"system": "GAIA", "type": "accuracy", "severity": "wound"}],
            "recently_healed": [],
        }
        signals = SignalExtractor.from_healing(data)
        assert len(signals) >= 2

    def test_grail_extraction(self):
        data = {
            "status": "glimpsed",
            "quest_progress": 0.56,
            "total_convergence": 0.47,
            "convergence_points": 17,
            "frequency_map": {
                "Appalachian 118 Hz": {"band": (110, 125), "domain": "ethnomusicology"},
            },
        }
        signals = SignalExtractor.from_grail(data)
        assert len(signals) >= 2
        domains = [s[0] for s in signals]
        assert "grail" in domains
        assert "frequency" in domains

    def test_fusion_extraction(self):
        data = {
            "carbon": {"total_lessons": 10},
            "love": {"cohesion": 0.7, "total_bonds": 15},
            "adversity": {"resilience": 0.95, "total_battles": 3},
            "joy": {"joy_index": 0.64},
            "hadron": {"total_energy": 2.5, "total_collisions": 8},
        }
        signals = SignalExtractor.from_fusion(data)
        assert len(signals) >= 5
        domains = [s[0] for s in signals]
        assert "learning" in domains
        assert "cohesion" in domains
        assert "joy" in domains

    def test_nyx_extraction(self):
        data = {"alive": True, "systems_blessed": 4, "systems_revoked": 0}
        signals = SignalExtractor.from_nyx_status(data)
        assert len(signals) >= 1
        assert signals[0][0] == "identity"

    def test_nyx_revocation_warning(self):
        data = {"alive": True, "systems_blessed": 4, "systems_revoked": 2}
        signals = SignalExtractor.from_nyx_status(data)
        domains = [s[0] for s in signals]
        assert "security" in domains

    def test_adapter_extraction(self):
        data = {"frozen": True, "writable": False, "status": "FREEZE HOLDS"}
        signals = SignalExtractor.from_adapter_status("lancelot", data)
        assert len(signals) >= 2
        domains = [s[0] for s in signals]
        assert "integrity" in domains


class TestRealMerlin:
    def test_create(self):
        m = Merlin()
        rm = RealMerlin(m)
        assert rm._cycle_count == 0

    def test_add_feed(self):
        m = Merlin()
        rm = RealMerlin(m)
        rm.add_feed("test", "testing", lambda: {"value": 1})
        assert "test" in rm._feeds

    def test_cycle_polls_feeds(self):
        m = Merlin()
        rm = RealMerlin(m)
        rm.add_feed("test", "testing", lambda: {"key": "value"}, poll_interval=0)
        result = rm.cycle()
        assert result["feeds_polled"] >= 1
        assert result["signals_extracted"] >= 0

    def test_cycle_increments_count(self):
        m = Merlin()
        rm = RealMerlin(m)
        rm.add_feed("test", "testing", lambda: {"v": 1}, poll_interval=0)
        rm.cycle()
        rm.cycle()
        assert rm._cycle_count == 2

    def test_multiple_feeds(self):
        m = Merlin()
        rm = RealMerlin(m)
        rm.add_feed("feed_a", "domain_a", lambda: {"a": 1}, poll_interval=0)
        rm.add_feed("feed_b", "domain_b", lambda: {"b": 2}, poll_interval=0)
        result = rm.cycle()
        assert result["feeds_polled"] == 2

    def test_heartbeat_feed_extraction(self):
        m = Merlin()
        rm = RealMerlin(m)
        rm.add_feed(
            "heartbeat",
            "kingdom_health",
            lambda: {
                "mood": "steady",
                "kingdom_health": 0.89,
                "systems": {"Nyx": {"health": 1.0}},
            },
            poll_interval=0,
        )
        result = rm.cycle()
        assert result["signals_extracted"] >= 2

    def test_grail_feed_extraction(self):
        m = Merlin()
        rm = RealMerlin(m)
        rm.add_feed(
            "grail_quest",
            "research",
            lambda: {
                "status": "glimpsed",
                "quest_progress": 0.56,
                "total_convergence": 0.47,
                "convergence_points": 17,
                "frequency_map": {"Test Thread": {"band": (100, 120), "domain": "test"}},
            },
            poll_interval=0,
        )
        result = rm.cycle()
        assert result["signals_extracted"] >= 2

    def test_what_merlin_sees(self):
        m = Merlin()
        rm = RealMerlin(m)
        rm.add_feed("test", "testing", lambda: {"v": 1}, poll_interval=0)
        rm.cycle()
        report = rm.what_merlin_sees()
        assert "feeds" in report
        assert "tower" in report
        assert "sight" in report
        assert report["total_signals"] >= 0

    def test_status(self):
        m = Merlin()
        rm = RealMerlin(m)
        rm.add_feed("test", "testing", lambda: {"v": 1}, poll_interval=0)
        rm.cycle()
        status = rm.status
        assert status["cycles"] == 1
        assert status["feeds"] == 1


class TestWireRealMerlin:
    def test_wire_to_avalon(self):
        class MockAvalon:
            pass

        mock = MockAvalon()
        mock.merlin = Merlin()
        mock.fusion = Fusion()
        mock.healing = type(
            "Healing",
            (),
            {
                "triage_report": lambda self: {
                    "active_wounds": 0,
                    "healed_total": 0,
                    "treatment_success_rate": 0,
                    "active": [],
                    "recently_healed": [],
                }
            },
        )()

        rm = wire_real_merlin(mock)
        assert rm.status["feeds"] >= 2

    def test_wired_cycle_runs(self):
        class MockAvalon:
            pass

        mock = MockAvalon()
        mock.merlin = Merlin()
        mock.fusion = Fusion()
        mock.fusion.heartbeat.register_system("test", lambda: 1.0)
        mock.fusion.breathe()
        mock.healing = type(
            "Healing",
            (),
            {
                "triage_report": lambda self: {
                    "active_wounds": 0,
                    "healed_total": 0,
                    "treatment_success_rate": 0,
                    "active": [],
                    "recently_healed": [],
                }
            },
        )()

        rm = wire_real_merlin(mock)
        result = rm.cycle()
        assert result["feeds_polled"] >= 1
        assert result["signals_extracted"] >= 0

    def test_wires_mirror_feed_when_available(self):
        class MockAvalon:
            pass

        class FakeMirror:
            is_available = True

            def reflection(self):
                return {
                    "available": True,
                    "mirror_running": False,
                    "reflection": "Mirror OS is present but sleeping.",
                }

        mock = MockAvalon()
        mock.merlin = Merlin()
        mock.fusion = Fusion()
        mock.healing = type(
            "Healing",
            (),
            {
                "triage_report": lambda self: {
                    "active_wounds": 0,
                    "healed_total": 0,
                    "treatment_success_rate": 0,
                    "active": [],
                    "recently_healed": [],
                }
            },
        )()
        mock.mirror_bridge = FakeMirror()

        rm = wire_real_merlin(mock)
        assert "mirror_reflection" in rm._feeds


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
