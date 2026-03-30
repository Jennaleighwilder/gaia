import pytest

from avalon.avalon import Avalon
from avalon.crucible import Scenario, ScenarioType


@pytest.fixture
def kingdom():
    avalon = Avalon()
    avalon.found_kingdom()
    return avalon


class TestCrucible:
    def test_all_eight_scenarios_registered(self, kingdom):
        assert kingdom.crucible is not None
        assert len(kingdom.crucible._scenarios) == 8

    def test_all_scenarios_run_without_error(self, kingdom):
        result = kingdom.enter_crucible()
        assert result["trials"] == 8
        assert result["survived"] == 8
        assert result["fell"] == 0

    def test_love_bonds_form_between_survivors(self, kingdom):
        before = kingdom.fusion.vital_signs()["love"]["total_bonds"]
        trial = kingdom.crucible.run_trial("The Cascade")
        after = kingdom.fusion.vital_signs()["love"]["total_bonds"]
        assert trial.survived
        assert len(trial.bonds_formed) >= 1
        assert after > before

    def test_carbon_records_one_explicit_lesson_per_trial(self, kingdom):
        result = kingdom.enter_crucible()
        assert result["total_lessons"] == 8
        assert kingdom.fusion.vital_signs()["carbon"]["total_lessons"] >= 8

    def test_ballads_written_for_each_trial(self, kingdom):
        before = kingdom.arts.status["ballads"]
        kingdom.enter_crucible()
        after = kingdom.arts.status["ballads"]
        assert after - before == 8

    def test_wardens_activate_then_stand_down(self, kingdom):
        trial = kingdom.crucible.run_trial("The Plague")
        assert trial.wardens_activated
        assert trial.war_plan_used == "Data Corruption"
        assert kingdom.threat_level() == "peace"

    def test_kingdom_restores_between_trials(self, kingdom):
        baseline = kingdom.real_heartbeat.get_health_scores()
        kingdom.crucible.run_trial("The Ambush")
        restored = kingdom.fusion.heartbeat._system_health
        for system in ["Nyx", "West-OS", "GAIA"]:
            assert restored[system] == pytest.approx(baseline[system], rel=0, abs=1e-6)
        assert kingdom.healing.status["active_wounds"] == 0

    def test_after_action_report_contains_all_trials(self, kingdom):
        kingdom.enter_crucible()
        report = kingdom.after_action()
        assert report["total_trials"] == 8
        assert len(report["trials"]) == 8
        assert all("chronicle" in trial for trial in report["trials"])

    def test_custom_scenario_registration_works(self, kingdom):
        def custom_setup(avalon, severity):
            avalon.fusion.heartbeat._system_health["Avalon"] = 0.65
            avalon.fusion.heartbeat._system_health["Memory"] = 0.65

        kingdom.crucible.register_scenario(
            Scenario(
                "The Lantern Test",
                ScenarioType.STORM,
                "A small trial to prove dynamic registration.",
                custom_setup,
                0.35,
                ["Avalon", "Memory"],
            )
        )
        result = kingdom.crucible.run_trial("The Lantern Test")
        assert result.scenario_name == "The Lantern Test"
        assert result.survived
        assert result.carbon_lessons == 1
