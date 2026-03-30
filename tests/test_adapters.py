"""
Adapter Test Suite
Verify all bridges read correctly from frozen West-OS.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapters.colony_bridge import ColonyBridge
from adapters.fence_bridge import FenceBridge
from adapters.kay import KayAdapter
from adapters.lancelot import LancelotAdapter
from nyx.core import Nyx


class TestLancelotAdapter:
    def test_creates(self):
        la = LancelotAdapter()
        assert isinstance(la, LancelotAdapter)

    def test_inventory(self):
        la = LancelotAdapter()
        inv = la.inventory()
        assert "available" in inv

    def test_benchmarks(self):
        la = LancelotAdapter()
        bm = la.read_benchmarks()
        assert bm["golden_canonical"] == "30/30"
        assert bm["operation_carbon"] == "65/65"

    def test_verify_freeze(self):
        la = LancelotAdapter()
        if la.is_available:
            freeze = la.verify_freeze()
            assert freeze["frozen"]
            assert not freeze["writable"]


class TestKayAdapter:
    def test_creates(self):
        ka = KayAdapter()
        assert isinstance(ka, KayAdapter)

    def test_inventory(self):
        ka = KayAdapter()
        inv = ka.inventory()
        assert "count" in inv


class TestColonyBridge:
    def test_creates_without_nyx(self):
        cb = ColonyBridge()
        assert isinstance(cb, ColonyBridge)

    def test_nyx_nutrient_without_nyx(self):
        cb = ColonyBridge()
        result = cb.check_nyx_nutrient("test", "fake")
        assert result["score"] == 0.0

    def test_nyx_nutrient_with_valid_blessing(self):
        nyx = Nyx(master_secret="test")
        blessing = nyx.root.bless("TestSystem", {"id": 1})
        cb = ColonyBridge(nyx)
        result = cb.check_nyx_nutrient("TestSystem", blessing)
        assert result["score"] == 1.0
        assert result["valid"]

    def test_nyx_nutrient_with_revoked_blessing(self):
        nyx = Nyx(master_secret="test")
        blessing = nyx.root.bless("TestSystem", {"id": 1})
        nyx.root.revoke("TestSystem")
        cb = ColonyBridge(nyx)
        result = cb.check_nyx_nutrient("TestSystem", blessing)
        assert result["score"] == 0.0
        assert not result["valid"]

    def test_combined_assessment_healthy(self):
        nyx = Nyx(master_secret="test")
        blessing = nyx.root.bless("TestSystem", {"id": 1})
        cb = ColonyBridge(nyx)
        result = cb.combined_assessment("TestSystem", blessing, "FULL")
        assert result["combined_tier"] == "FULL"

    def test_combined_assessment_nyx_revoked(self):
        nyx = Nyx(master_secret="test")
        blessing = nyx.root.bless("TestSystem", {"id": 1})
        nyx.root.revoke("TestSystem")
        cb = ColonyBridge(nyx)
        result = cb.combined_assessment("TestSystem", blessing, "FULL")
        assert result["combined_tier"] == "RESTRICTED"


class TestFenceBridge:
    def test_creates_without_nyx(self):
        fb = FenceBridge()
        result = fb.pre_flight_nyx_check()
        assert not result["passed"]

    def test_pre_flight_with_healthy_nyx(self):
        nyx = Nyx(master_secret="test")
        fb = FenceBridge(nyx)
        result = fb.pre_flight_nyx_check()
        assert result["passed"]
        assert result["root_alive"]

    def test_departure_stamp(self):
        nyx = Nyx(master_secret="test")
        fb = FenceBridge(nyx)
        stamp = fb.departure_stamp()
        assert stamp["stamped"]
        assert "nyx_fingerprint" in stamp


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
