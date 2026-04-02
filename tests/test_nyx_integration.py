"""
NYX Integration Test
Full lifecycle: create -> bless -> verify -> revoke -> die
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapters.colony_bridge import ColonyBridge
from adapters.fence_bridge import FenceBridge
from nyx.core import Nyx


class TestNyxIntegration:
    def test_full_lifecycle(self):
        nyx = Nyx(master_secret="integration_test_secret")
        assert nyx.root.is_alive

        blessings = {}
        for name in ["West-OS", "GAIA", "Alfred", "Colony"]:
            blessings[name] = nyx.bless_system(name, {"born": "test", "system": name})

        for name, blessing in blessings.items():
            assert nyx.root.verify_blessing(name, blessing), f"{name} blessing should be valid"

        bridge = ColonyBridge(nyx)
        for name, blessing in blessings.items():
            assessment = bridge.combined_assessment(name, blessing, "FULL")
            assert assessment["combined_tier"] == "FULL", f"{name} should be FULL"

        fence = FenceBridge(nyx)
        preflight = fence.pre_flight_nyx_check()
        assert preflight["passed"], "Fence should pass with healthy Nyx"

        nyx.revoke_system("Colony")
        assert not nyx.root.verify_blessing("Colony", blessings["Colony"])
        assert nyx.root.verify_blessing("West-OS", blessings["West-OS"])

        assessment = bridge.combined_assessment("Colony", blessings["Colony"], "FULL")
        assert assessment["combined_tier"] == "RESTRICTED"

        nyx.dead_hand.arm()
        result = nyx.kill_all()
        assert result["fired"]

        for name, blessing in blessings.items():
            assert not nyx.root.verify_blessing(name, blessing), f"{name} should be dead"

        for name, blessing in blessings.items():
            assessment = bridge.combined_assessment(name, blessing, "FULL")
            assert assessment["combined_tier"] == "RESTRICTED"

    def test_shapeshifter_under_probe(self):
        nyx = Nyx(master_secret="test")
        shapes = []
        for i in range(10):
            nyx.watcher.detect_probe("fingerprint", f"scanner_{i}")
            shape = nyx.who_am_i()
            shapes.append(shape["shape"])

        unique = len(set(shapes))
        assert unique >= 7, f"Expected at least 7 unique shapes, got {unique}"

    def test_dead_hand_tripwire(self):
        nyx = Nyx(master_secret="test")
        nyx.bless_system("Test", {"id": 1})

        nyx.dead_hand.arm()
        nyx.dead_hand.add_tripwire("always_trip", lambda: True, "test tripwire")

        status = nyx.dead_hand.check()
        assert status["should_fire"]
        assert "always_trip" in status["tripwires_tripped"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
