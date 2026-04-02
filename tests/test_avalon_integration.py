"""
AVALON Integration Test
Full lifecycle: found -> convene -> decree -> revoke -> darken.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from avalon.avalon import found_on_nyx
from avalon.round_table import Vote
from avalon.excalibur import SovereigntyState


class TestAvalonIntegration:
    def test_full_kingdom_lifecycle(self):
        avalon = found_on_nyx("avalon_integration_secret")
        founded = avalon.found_kingdom("Jennifer Leigh West")

        assert founded["status"] == "THE KINGDOM STANDS"
        assert avalon.table.seated_count == 12

        council = avalon.hold_council("Should Avalon proceed with the kingdom build?")
        assert council["council_convened"]

        aye_knights = [
            "Lancelot",
            "Galahad",
            "Gawain",
            "Percival",
            "Tristan",
            "Kay",
            "Bedivere",
            "Morgana",
        ]
        nay_knights = ["Nimue"]
        abstain_knights = ["Gareth", "Bors", "Dagonet"]

        for knight_name in aye_knights:
            avalon.table.speak(
                knight_name,
                Vote.AYE,
                f"{knight_name} affirms the kingdom can proceed.",
                0.9,
            )

        avalon.table.speak(
            "Nimue",
            Vote.NAY,
            "The build is sound, but I want a stricter modification audit first.",
            0.7,
            ["Preserve a path for revision before release."],
        )

        for knight_name in abstain_knights:
            avalon.table.speak(
                knight_name,
                Vote.ABSTAIN,
                f"{knight_name} yields the question to other domains.",
                0.5,
            )

        decree = avalon.table.decree("integration_test_seal")
        assert decree["decision"] == "APPROVED"
        assert len(decree["dissenting_voices"]) == 1
        assert decree["dissenting_voices"][0]["knight"] == "Nimue"

        revocation = avalon.revoke_knight("Nimue", "Integration revocation")
        assert revocation["revoked"]
        assert not avalon.table.status["seats"]["Nimue"]["active"]

        returned = avalon.return_excalibur_to_lake("Integration kingdom fall")
        assert returned["returned"]
        assert avalon.excalibur.check_sovereignty() == SovereigntyState.RETURNED_TO_LAKE
        assert avalon.table.seated_count == 0
        assert returned["castle"]["gates"] == "sealed"
        assert all(room["status"] == "dark" for room in returned["castle"]["rooms"].values())
        assert returned["dead_hand"]["armed"]
        assert returned["dead_hand"]["should_fire"]
        assert "kingdom_fall" in returned["dead_hand"]["tripwires_tripped"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
