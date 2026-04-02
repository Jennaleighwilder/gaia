"""
GRAIL ADVANCEMENT Test Suite
The quest crosses the threshold.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from avalon.grail import Grail, load_jennifers_research
from avalon.grail_advancement import advance_grail, report_advancement


class TestAdvancement:
    def test_grail_advances(self):
        g = Grail()
        load_jennifers_research(g)
        before = g.seek()
        advance_grail(g)
        after = g.seek()
        assert after["quest_progress"] > before["quest_progress"]

    def test_status_changes(self):
        g = Grail()
        load_jennifers_research(g)
        advance_grail(g)
        result = g.seek()
        assert result["status"] in ["approaching", "found", "proven"]

    def test_threshold_reached(self):
        g = Grail()
        load_jennifers_research(g)
        advance_grail(g)
        result = g.seek()
        assert result["quest_progress"] >= 0.618

    def test_global_oracle_network_strengthened(self):
        g = Grail()
        load_jennifers_research(g)
        before = g.thread_report("Global Oracle Network")
        advance_grail(g)
        after = g.thread_report("Global Oracle Network")
        assert after["evidence_count"] > before["evidence_count"]
        assert after["maturity"] > before["maturity"]

    def test_pachacamac_strengthened(self):
        g = Grail()
        load_jennifers_research(g)
        before = g.thread_report("Pachacamac Oracle")
        advance_grail(g)
        after = g.thread_report("Pachacamac Oracle")
        assert after["evidence_count"] > before["evidence_count"]
        assert after["maturity"] > before["maturity"]

    def test_indus_dodona_connection(self):
        g = Grail()
        load_jennifers_research(g)
        advance_grail(g)
        indus = g.thread_report("Indus Acoustic Hypothesis")
        assert "Global Oracle Network" in indus["connections"]

    def test_convergence_points_increased(self):
        g = Grail()
        load_jennifers_research(g)
        before = g.seek()
        advance_grail(g)
        after = g.seek()
        assert after["convergence_points"] > before["convergence_points"]

    def test_connection_ratio_increased(self):
        g = Grail()
        load_jennifers_research(g)
        before = g.seek()
        advance_grail(g)
        after = g.seek()
        assert after["connection_ratio"] > before["connection_ratio"]

    def test_all_evidence_has_sources(self):
        g = Grail()
        load_jennifers_research(g)
        advance_grail(g)
        for thread in g.all_threads():
            name = thread["name"]
            t = g._threads[name]
            for ev in t.evidence:
                assert ev.source, f"Evidence in {name} missing source: {ev.description[:50]}"
                assert ev.description, f"Evidence in {name} missing description"

    def test_report_generates(self):
        g = Grail()
        load_jennifers_research(g)
        advance_grail(g)
        report = report_advancement(g)
        assert "APPROACHING" in report
        assert "THRESHOLD CROSSED" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
