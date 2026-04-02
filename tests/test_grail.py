"""
GRAIL Test Suite
The quest that unifies everything.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from avalon.grail import (
    ConvergenceEngine,
    ConvergencePoint,
    Evidence,
    Grail,
    GrailStatus,
    ResearchThread,
    ThreadStatus,
    load_jennifers_research,
)


class TestResearchThread:
    def test_create_thread(self):
        t = ResearchThread(name="Test", thesis="Test thesis", domain="test")
        assert t.name == "Test"
        assert t.status == ThreadStatus.SEED
        assert t.maturity > 0

    def test_add_evidence(self):
        t = ResearchThread(name="Test", thesis="Test", domain="test")
        ev = t.add_evidence("finding", "source", "measurement", 0.8)
        assert len(t.evidence) == 1
        assert ev.strength == 0.8

    def test_evidence_strength(self):
        t = ResearchThread(name="Test", thesis="Test", domain="test")
        t.add_evidence("a", "s", "m", 0.6)
        t.add_evidence("b", "s", "m", 0.8)
        assert 0.6 < t.evidence_strength < 0.8

    def test_maturity_increases_with_status(self):
        seed = ResearchThread(name="A", thesis="T", domain="d", status=ThreadStatus.SEED)
        pub = ResearchThread(name="B", thesis="T", domain="d", status=ThreadStatus.PUBLISHED)
        assert pub.maturity > seed.maturity

    def test_peer_reviewed_count(self):
        t = ResearchThread(name="Test", thesis="T", domain="d")
        t.add_evidence("a", "s", "m", 0.8, peer_reviewed=True)
        t.add_evidence("b", "s", "m", 0.7, peer_reviewed=False)
        assert t.peer_reviewed_count == 1

    def test_identity_is_stable(self):
        t = ResearchThread(name="Test", thesis="Thesis", domain="d")
        assert t.identity == t.identity
        assert len(t.identity) == 12


class TestConvergenceEngine:
    def test_frequency_overlap_detected(self):
        ce = ConvergenceEngine()
        a = ResearchThread(
            name="A",
            thesis="T",
            domain="d1",
            frequency_band=(95, 120),
            connections=["B"],
        )
        b = ResearchThread(
            name="B",
            thesis="T",
            domain="d2",
            frequency_band=(110, 130),
            connections=["A"],
        )
        points = ce.measure([a, b])
        assert len(points) >= 1
        assert points[0].frequency_overlap is not None

    def test_no_overlap_no_convergence(self):
        ce = ConvergenceEngine()
        a = ResearchThread(name="A", thesis="T", domain="d1", frequency_band=(10, 20))
        b = ResearchThread(name="B", thesis="T", domain="d2", frequency_band=(200, 300))
        points = ce.measure([a, b])
        assert len(points) == 0

    def test_different_domains_boost_strength(self):
        ce = ConvergenceEngine()
        a = ResearchThread(
            name="A",
            thesis="T",
            domain="neuroscience",
            frequency_band=(100, 120),
            connections=["B"],
        )
        b = ResearchThread(
            name="B",
            thesis="T",
            domain="archaeology",
            frequency_band=(100, 120),
            connections=["A"],
        )
        same = ResearchThread(
            name="C",
            thesis="T",
            domain="neuroscience",
            frequency_band=(100, 120),
            connections=["A"],
        )

        a.connections = ["B", "C"]
        b.connections = ["A"]
        same.connections = ["A"]

        points_diff = ce.measure([a, b])
        ce2 = ConvergenceEngine()
        points_same = ce2.measure([a, same])

        if points_diff and points_same:
            assert points_diff[0].strength >= points_same[0].strength


class TestGrail:
    def test_create_empty(self):
        g = Grail()
        assert g._status == GrailStatus.HIDDEN
        assert len(g._threads) == 0

    def test_add_thread(self):
        g = Grail()
        t = g.add_thread("Test", "Thesis", "domain")
        assert "Test" in g._threads
        assert t.name == "Test"

    def test_add_evidence(self):
        g = Grail()
        g.add_thread("Test", "Thesis", "domain")
        ev = g.add_evidence("Test", "finding", "source", "measurement", 0.8)
        assert ev is not None
        assert len(g._threads["Test"].evidence) == 1

    def test_evidence_to_nonexistent_thread(self):
        g = Grail()
        ev = g.add_evidence("NoSuchThread", "finding", "source")
        assert ev is None

    def test_connect_threads(self):
        g = Grail()
        g.add_thread("A", "T", "d")
        g.add_thread("B", "T", "d")
        g.connect_threads("A", "B")
        assert "B" in g._threads["A"].connections
        assert "A" in g._threads["B"].connections

    def test_auto_advance_status(self):
        g = Grail()
        g.add_thread("Test", "T", "d")
        for i in range(3):
            g.add_evidence("Test", f"evidence {i}", "source", "measurement", 0.8)
        assert g._threads["Test"].status == ThreadStatus.GROWING

    def test_seek_empty(self):
        g = Grail()
        result = g.seek()
        assert result["status"] == "hidden"

    def test_seek_with_threads(self):
        g = Grail()
        g.add_thread("A", "T", "d1", frequency_band=(100, 120), connections=["B"])
        g.add_thread("B", "T", "d2", frequency_band=(110, 130), connections=["A"])
        result = g.seek()
        assert "quest_progress" in result
        assert result["threads"] == 2

    def test_thread_report(self):
        g = Grail()
        g.add_thread("Test", "Thesis", "domain", frequency_band=(100, 120))
        report = g.thread_report("Test")
        assert report["name"] == "Test"
        assert report["frequency_band"] == (100, 120)

    def test_all_threads(self):
        g = Grail()
        g.add_thread("A", "T", "d")
        g.add_thread("B", "T", "d")
        all_t = g.all_threads()
        assert len(all_t) == 2

    def test_the_question(self):
        g = Grail()
        g.add_thread("A", "T", "d")
        q = g.the_question()
        assert "Percival" in q

    def test_quest_log_records_events(self):
        g = Grail()
        g.add_thread("A", "T", "d")
        g.add_evidence("A", "evidence", "source")
        assert len(g._quest_log) >= 2


class TestJennifersResearch:
    def test_loads_nine_threads(self):
        g = Grail()
        load_jennifers_research(g)
        assert len(g._threads) == 9

    def test_threads_have_evidence(self):
        g = Grail()
        load_jennifers_research(g)
        for name, thread in g._threads.items():
            assert len(thread.evidence) >= 2, f"{name} has too few evidence"

    def test_threads_are_connected(self):
        g = Grail()
        load_jennifers_research(g)
        total_connections = sum(len(t.connections) for t in g._threads.values())
        assert total_connections >= 10

    def test_convergence_found(self):
        g = Grail()
        load_jennifers_research(g)
        result = g.seek()
        assert result["convergence_points"] > 0

    def test_status_is_glimpsed_or_better(self):
        g = Grail()
        load_jennifers_research(g)
        result = g.seek()
        assert result["status"] in ["glimpsed", "approaching", "found", "proven"]

    def test_frequency_map_populated(self):
        g = Grail()
        load_jennifers_research(g)
        result = g.seek()
        assert len(result["frequency_map"]) >= 5

    def test_strongest_convergence_found(self):
        g = Grail()
        load_jennifers_research(g)
        result = g.seek()
        assert result["strongest_convergence"] != "none yet"

    def test_quest_progress_above_50(self):
        g = Grail()
        load_jennifers_research(g)
        result = g.seek()
        assert result["quest_progress"] >= 0.5

    def test_appalachian_118_is_published(self):
        g = Grail()
        load_jennifers_research(g)
        assert g._threads["Appalachian 118 Hz"].status == ThreadStatus.PUBLISHED

    def test_indus_is_published(self):
        g = Grail()
        load_jennifers_research(g)
        assert g._threads["Indus Acoustic Hypothesis"].status == ThreadStatus.PUBLISHED


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
