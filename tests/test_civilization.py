"""CIVILIZATION Test Suite — Land, Crops, Arts, Commerce"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from avalon.land import LandSteward, SoilHealth, Territory, wire_land
from avalon.crops import CropManager, Season, Crop, plant_kingdom_crops, wire_crops
from avalon.arts import KingdomArts, ArtForm, wire_arts
from avalon.commerce import Commerce, Channel, establish_kingdom_routes, wire_commerce


class TestLand:
    def test_survey(self):
        steward = LandSteward()
        survey = steward.survey()
        assert "soil" in survey
        assert "water" in survey
        assert "sun" in survey

    def test_disk_health(self):
        steward = LandSteward()
        survey = steward.survey()
        assert survey["soil"]["health"] in [s.value for s in SoilHealth] + ["unknown"]

    def test_overall_health(self):
        steward = LandSteward()
        survey = steward.survey()
        assert survey["overall_health"] in ["thriving", "sustaining", "struggling", "barren", "unknown"]

    def test_can_plant(self):
        steward = LandSteward()
        can, reason = steward.can_plant(1)
        assert isinstance(can, bool)
        assert isinstance(reason, str)

    def test_sacred_territories(self):
        steward = LandSteward(sacred_paths=["/sacred/path"])
        assert "/sacred/path" in steward._sacred

    def test_territory_health(self):
        t = Territory("test", "/tmp", total_bytes=1000, used_bytes=100, available_bytes=900)
        assert t.health == SoilHealth.FERTILE

    def test_territory_exhausted(self):
        t = Territory("test", "/tmp", total_bytes=1000, used_bytes=950, available_bytes=50)
        assert t.health == SoilHealth.EXHAUSTED


class TestCrops:
    def test_plant(self):
        mgr = CropManager()
        crop = mgr.plant("Test Crop", "test")
        assert crop.name == "Test Crop"
        assert crop.season == Season.PLANTING

    def test_advance_season(self):
        crop = Crop("Test", "test")
        assert crop.season == Season.PLANTING
        crop.advance_season()
        assert crop.season == Season.TENDING
        crop.advance_season()
        assert crop.season == Season.GROWING
        crop.advance_season()
        assert crop.season == Season.HARVEST

    def test_season_cycles(self):
        crop = Crop("Test", "test")
        for _ in range(5):
            crop.advance_season()
        assert crop.season == Season.PLANTING
        assert crop.yield_count == 1

    def test_harvest(self):
        mgr = CropManager()
        crop = mgr.plant("Test", "test")
        crop.season = Season.HARVEST
        harvested = mgr.harvest()
        assert len(harvested) == 1
        assert crop.yield_count == 1

    def test_field_report(self):
        mgr = CropManager()
        plant_kingdom_crops(mgr)
        report = mgr.field_report()
        assert report["total_crops"] == 6

    def test_kingdom_crops(self):
        mgr = CropManager()
        plant_kingdom_crops(mgr)
        assert "Healing Patterns" in mgr._crops
        assert "Cross-Domain Insights" in mgr._crops
        assert "Research Convergence" in mgr._crops


class TestArts:
    def test_chronicle(self):
        arts = KingdomArts()
        work = arts.chronicle({
            "number": 1,
            "thanksgiving": {"alive_count": 6, "total_systems": 7, "gratitude_ratio": 0.86},
            "wounds_found": 2, "wounds_healed": 1,
            "merlin_insights": 0, "lessons_learned": 1,
        })
        assert work.form == ArtForm.CHRONICLE
        assert "1st" in work.title
        assert "Morgan le Fay" in work.content

    def test_ballad(self):
        arts = KingdomArts()
        work = arts.ballad("Test Event", "Something happened", ["Lancelot"])
        assert work.form == ArtForm.BALLAD
        assert "seven generations" in work.content.lower()

    def test_tapestry(self):
        arts = KingdomArts()
        work = arts.tapestry("Birth of the Kingdom", {"kingdom_health": "97%", "test_count": 420})
        assert work.form == ArtForm.TAPESTRY
        assert "420" in work.content

    def test_gallery(self):
        arts = KingdomArts()
        arts.chronicle({"number": 1, "thanksgiving": {"alive_count": 5, "total_systems": 5, "gratitude_ratio": 1.0},
                        "wounds_found": 0, "wounds_healed": 0, "merlin_insights": 0, "lessons_learned": 0})
        arts.ballad("Test", "Desc")
        gallery = arts.gallery()
        assert len(gallery) == 2

    def test_filter_by_form(self):
        arts = KingdomArts()
        arts.chronicle({"number": 1, "thanksgiving": {"alive_count": 5, "total_systems": 5, "gratitude_ratio": 1.0},
                        "wounds_found": 0, "wounds_healed": 0, "merlin_insights": 0, "lessons_learned": 0})
        arts.ballad("Test", "Desc")
        chronicles = arts.gallery(form=ArtForm.CHRONICLE)
        assert len(chronicles) == 1

    def test_status(self):
        arts = KingdomArts()
        arts.ballad("A", "B")
        arts.ballad("C", "D")
        assert arts.status["ballads"] == 2


class TestCommerce:
    def test_establish_route(self):
        commerce = Commerce()
        route = commerce.establish_route("Test", "market", "Test service", "Gareth")
        assert route.name == "Test"
        assert route.channel == Channel.MARKET

    def test_transact(self):
        commerce = Commerce()
        commerce.establish_route("Test", "market", "Test", "Gareth")
        result = commerce.transact("Test", 100, "Sale", "Alice")
        assert result["success"]
        assert result["value"] == 100

    def test_transact_invalid_route(self):
        commerce = Commerce()
        result = commerce.transact("Nonexistent", 100)
        assert not result["success"]

    def test_treasury_report(self):
        commerce = Commerce()
        establish_kingdom_routes(commerce)
        commerce.transact("Heritage Readings", 150, "Test sale")
        report = commerce.treasury_report()
        assert report["total_transactions"] == 1
        assert report["total_value"] == 150

    def test_kingdom_routes(self):
        commerce = Commerce()
        establish_kingdom_routes(commerce)
        assert len(commerce._routes) >= 12

    def test_three_channels_exist(self):
        commerce = Commerce()
        establish_kingdom_routes(commerce)
        channels = set(r.channel for r in commerce._routes.values())
        assert Channel.COMMONS in channels
        assert Channel.MARKET in channels
        assert Channel.GUILD in channels

    def test_commons_free(self):
        commerce = Commerce()
        establish_kingdom_routes(commerce)
        commerce.transact("Legal Advocacy", 0, "Free service")
        report = commerce.treasury_report()
        assert report["by_channel"]["commons"]["transactions"] == 1

    def test_guild_high_value(self):
        commerce = Commerce()
        establish_kingdom_routes(commerce)
        commerce.transact("Mirror Protocol License", 5000, "License")
        report = commerce.treasury_report()
        assert report["by_channel"]["guild"]["total_value"] == 5000


class TestWiring:
    def test_wire_land(self):
        class Dummy:
            pass
        steward = wire_land(Dummy())
        assert isinstance(steward, LandSteward)

    def test_wire_crops(self):
        class Dummy:
            pass
        manager = wire_crops(Dummy())
        assert isinstance(manager, CropManager)
        assert len(manager._crops) == 6

    def test_wire_arts(self):
        class Dummy:
            pass
        arts = wire_arts(Dummy())
        assert isinstance(arts, KingdomArts)

    def test_wire_commerce(self):
        class Dummy:
            pass
        commerce = wire_commerce(Dummy())
        assert isinstance(commerce, Commerce)
        assert len(commerce._routes) >= 12


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
