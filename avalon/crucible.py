"""
AVALON :: THE CRUCIBLE
Where the kingdom is forged through fire.

The Crucible is not a test suite. Tests prove correctness.
The Crucible proves resilience.

Each trial runs the full kingdom loop:
  THANKSGIVING -> ATTACK -> RESPONSE -> BONDING -> LEARNING -> CHRONICLE

The kingdom enters the Crucible as individual systems.
It exits as a brotherhood.

© 2026 Jennifer Leigh West. All rights reserved.
"""

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from avalon.faithkeeper import SevenGenerations
from avalon.healing import TreatmentOutcome


class ScenarioType(Enum):
    CASCADE = "cascade"
    SIEGE = "siege"
    PLAGUE = "plague"
    IDENTITY = "identity"
    STARVATION = "starvation"
    STORM = "storm"
    BETRAYAL = "betrayal"
    AMBUSH = "ambush"
    EXODUS = "exodus"
    REBIRTH = "rebirth"


@dataclass
class Scenario:
    name: str
    scenario_type: ScenarioType
    description: str
    setup: Callable
    severity: float = 0.5
    systems_affected: List[str] = field(default_factory=list)
    expected_bonds: List[Tuple[str, str]] = field(default_factory=list)


@dataclass
class TrialRecord:
    scenario_name: str
    scenario_type: str
    started_at: float = field(default_factory=time.time)
    completed_at: float = 0.0
    thanksgiving_before: Dict = field(default_factory=dict)
    thanksgiving_after: Dict = field(default_factory=dict)
    systems_wounded: List[str] = field(default_factory=list)
    systems_healed: List[str] = field(default_factory=list)
    systems_fell: List[str] = field(default_factory=list)
    systems_survived: List[str] = field(default_factory=list)
    wardens_activated: bool = False
    war_plan_used: str = ""
    sovereign_summoned: bool = False
    bonds_formed: List[Tuple[str, str]] = field(default_factory=list)
    lessons_learned: List[str] = field(default_factory=list)
    carbon_lessons: int = 0
    merlin_insights: int = 0
    survived: bool = True
    chronicle: str = ""
    severity: float = 0.0


class Crucible:
    """Battle-hardening for the whole kingdom as one organism."""

    def __init__(self, avalon):
        self._avalon = avalon
        self._trials: List[TrialRecord] = []
        self._scenarios: Dict[str, Scenario] = {}
        self._total_bonds_formed = 0
        self._total_lessons = 0
        self._baseline_cache: Optional[Dict[str, float]] = None
        self._log_path = Path("memory") / "crucible_log.jsonl"
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def register_scenario(self, scenario: Scenario):
        self._scenarios[scenario.name] = scenario

    def _current_scores(self, refresh: bool = False) -> Dict[str, float]:
        if self._baseline_cache is not None and not refresh:
            return dict(self._baseline_cache)
        if hasattr(self._avalon, "real_heartbeat"):
            scores = dict(self._avalon.real_heartbeat.get_health_scores())
            self._baseline_cache = dict(scores)
            return scores
        if hasattr(self._avalon, "fusion"):
            scores = dict(self._avalon.fusion.heartbeat._system_health)
            self._baseline_cache = dict(scores)
            return scores
        return {}

    def _sync_fusion_scores(self, scores: Dict[str, float]):
        if not hasattr(self._avalon, "fusion"):
            return
        for system, health in scores.items():
            self._avalon.fusion.heartbeat._system_health[system] = float(health)

    def _override_real_scores(
        self, overrides: Dict[str, float], baseline_scores: Dict[str, float]
    ) -> Callable[[], None]:
        if not hasattr(self._avalon, "real_heartbeat"):
            return lambda: None

        real_hb = self._avalon.real_heartbeat
        original_get_health_scores = real_hb.get_health_scores

        def merged_scores():
            scores = dict(baseline_scores)
            scores.update(overrides)
            return scores

        real_hb.get_health_scores = merged_scores

        def restore():
            real_hb.get_health_scores = original_get_health_scores

        return restore

    def _patch_safe_treatments(self) -> Callable[[], None]:
        """Crucible trials never run live remedies against the realm."""
        if not hasattr(self._avalon, "healing"):
            return lambda: None

        healer = self._avalon.healing.healer
        original_treatments = dict(healer._treatments)

        def safe_outcome(method: str) -> TreatmentOutcome:
            if method in {
                "request_new_blessing_from_nyx",
                "alert_sovereign_identity_crisis",
                "alert_sovereign_system_dying",
                "isolate_and_alert_sovereign",
                "quarantine_and_alert_sovereign",
            }:
                return TreatmentOutcome.ESCALATED
            if method in {
                "isolate_and_restart",
                "isolate_and_queue",
                "isolate_and_diagnose",
                "quarantine_and_restore",
                "restart_with_reduced_load",
            }:
                return TreatmentOutcome.IMPROVING
            return TreatmentOutcome.HEALED

        simulated = {}
        for name in original_treatments:
            simulated[name] = (
                lambda system_name, wound, diagnosis, method=name: safe_outcome(method)
            )
        healer._treatments = simulated

        def restore():
            healer._treatments = original_treatments

        return restore

    def _patch_battle_merlin(self, scenario: Scenario) -> Callable[[], None]:
        """During battle drills, Merlin should observe the drill itself, not repoll the world."""
        if not hasattr(self._avalon, "real_merlin"):
            return lambda: None

        real_merlin = self._avalon.real_merlin
        original_cycle = real_merlin.cycle

        def simulated_cycle():
            real_merlin._cycle_count += 1
            signal_text = (
                f"Crucible trial {scenario.name} {scenario.scenario_type.value} "
                f"severity {scenario.severity:.0%}"
            )
            self._avalon.merlin.observe("crucible", signal_text, {"scenario": scenario.name})
            real_merlin._total_signals_processed += 1
            cycle_record = {
                "cycle": real_merlin._cycle_count,
                "timestamp": time.time(),
                "feeds_polled": 0,
                "signals_extracted": 1,
                "new_insights": 0,
                "domains_observed": ["crucible"],
            }
            real_merlin._observation_log.append(cycle_record)
            return cycle_record

        real_merlin.cycle = simulated_cycle

        def restore():
            real_merlin.cycle = original_cycle

        return restore

    def _war_plan_for(self, scenario_type: ScenarioType) -> str:
        plan_map = {
            ScenarioType.CASCADE: "Cascade Failure",
            ScenarioType.SIEGE: "Sustained Assault",
            ScenarioType.PLAGUE: "Data Corruption",
            ScenarioType.IDENTITY: "Identity Compromise",
            ScenarioType.STARVATION: "Sustained Assault",
            ScenarioType.STORM: "Sustained Assault",
            ScenarioType.BETRAYAL: "Manipulation Attempt",
            ScenarioType.AMBUSH: "Probe Response",
            ScenarioType.EXODUS: "Evacuation",
            ScenarioType.REBIRTH: "Evacuation",
        }
        return plan_map.get(scenario_type, "Probe Response")

    def _classify_state(
        self, affected: List[str], scores: Dict[str, float]
    ) -> Tuple[List[str], List[str], List[str]]:
        wounded = []
        fell = []
        survived = []
        for system in affected:
            health = scores.get(system, 1.0)
            if health < 0.3:
                fell.append(system)
            else:
                survived.append(system)
                if health < 0.7:
                    wounded.append(system)
        return wounded, fell, survived

    def _forge_bonds(self, scenario: Scenario, survivors: List[str]) -> List[Tuple[str, str]]:
        if not hasattr(self._avalon, "fusion") or len(survivors) < 2:
            return []

        preexisting = {}
        for i, left in enumerate(survivors):
            for right in survivors[i + 1:]:
                preexisting[(left, right)] = self._avalon.fusion.love.bond_strength(left, right)

        self._avalon.fusion.experience(
            "attack",
            f"Crucible trial: {scenario.name}",
            survivors,
            scenario.severity,
        )
        self._avalon.fusion.experience(
            "victory",
            f"Survived the Crucible: {scenario.name}",
            survivors,
            min(1.0, scenario.severity + 0.1),
        )

        newly_forged = []
        for pair, before_strength in preexisting.items():
            after_strength = self._avalon.fusion.love.bond_strength(*pair)
            if before_strength == 0.0 and after_strength > 0.0:
                newly_forged.append(pair)
                self._total_bonds_formed += 1
        return newly_forged

    def _record_loss(self, scenario: Scenario, fallen: List[str]):
        if not hasattr(self._avalon, "fusion") or not fallen:
            return
        self._avalon.fusion.experience(
            "loss",
            f"Crucible trial: {scenario.name}. {', '.join(fallen)} fell in battle.",
            fallen,
            min(1.0, scenario.severity),
        )

    def _record_lesson(self, scenario: Scenario, record: TrialRecord):
        if not hasattr(self._avalon, "fusion"):
            return

        lesson = (
            f"Crucible trial '{scenario.name}' ({scenario.scenario_type.value}): "
            f"severity {scenario.severity:.0%}. "
            f"Survived: {', '.join(record.systems_survived) or 'none'}. "
            f"Fell: {', '.join(record.systems_fell) or 'none'}. "
            f"Bonds forged: {len(record.bonds_formed)}."
        )
        tagged = SevenGenerations.tag_lesson(
            lesson,
            "adversity" if record.survived else "failure",
        )
        self._avalon.fusion.carbon.learn(
            content=tagged,
            source="Crucible",
            context=scenario.name,
            category="adversity",
            confidence=0.95,
        )
        record.lessons_learned.append(tagged)
        record.carbon_lessons += 1
        self._total_lessons += 1

    def _write_ballad(self, scenario: Scenario, record: TrialRecord):
        if not hasattr(self._avalon, "arts"):
            record.chronicle = f"Trial of {scenario.name}: {'survived' if record.survived else 'fell'}"
            return

        ballad = self._avalon.arts.ballad(
            f"The Trial of {scenario.name}",
            f"The kingdom faced {scenario.scenario_type.value}. "
            f"Severity: {scenario.severity:.0%}. "
            f"{len(record.systems_survived)} systems survived. "
            f"{len(record.systems_fell)} fell. "
            f"{len(record.bonds_formed)} bonds forged in the fire.",
            record.systems_survived[:5],
        )
        record.chronicle = ballad.content

    def _clear_posture(self, affected: List[str]):
        if hasattr(self._avalon, "apothecary"):
            for system in affected:
                try:
                    self._avalon.apothecary.remove_splint(system)
                except Exception:
                    pass
                try:
                    self._avalon.apothecary.wake_from_hibernation(system)
                except Exception:
                    pass
                try:
                    self._avalon.apothecary.lift_quarantine(system)
                except Exception:
                    pass

    def _restore_kingdom(self, baseline_scores: Dict[str, float], affected: List[str]):
        self._sync_fusion_scores(baseline_scores)
        if hasattr(self._avalon, "healing"):
            try:
                self._avalon.healing.watch(baseline_scores)
            except Exception:
                pass
        self._clear_posture(affected)

    def run_trial(self, scenario_name: str) -> TrialRecord:
        scenario = self._scenarios.get(scenario_name)
        if not scenario:
            return TrialRecord(
                scenario_name=scenario_name,
                scenario_type="unknown",
                survived=False,
                chronicle=f"Unknown scenario: {scenario_name}",
            )

        record = TrialRecord(
            scenario_name=scenario.name,
            scenario_type=scenario.scenario_type.value,
            severity=scenario.severity,
        )

        baseline_scores = self._current_scores()
        self._sync_fusion_scores(baseline_scores)

        if hasattr(self._avalon, "faithkeeper"):
            record.thanksgiving_before = self._avalon.faithkeeper.thanksgiving_now()

        restore_scores = lambda: None
        restore_treatments = lambda: None
        restore_merlin = lambda: None
        history_before = (
            len(self._avalon.healing.healer.history)
            if hasattr(self._avalon, "healing")
            else 0
        )

        try:
            scenario.setup(self._avalon, scenario.severity)
            overrides = {
                system: self._avalon.fusion.heartbeat._system_health.get(
                    system, baseline_scores.get(system, 1.0)
                )
                for system in scenario.systems_affected
            }
            restore_scores = self._override_real_scores(overrides, baseline_scores)

            if hasattr(self._avalon, "wardens"):
                self._avalon.wardens.patrol()
                plan_name = self._war_plan_for(scenario.scenario_type)
                plan_result = self._avalon.wardens.activate_plan(plan_name)
                record.wardens_activated = plan_result.get("activated", False)
                record.war_plan_used = plan_result.get("plan", "")

            ceremony = None
            if hasattr(self._avalon, "faithkeeper"):
                restore_treatments = self._patch_safe_treatments()
                restore_merlin = self._patch_battle_merlin(scenario)
                ceremony = self._avalon.faithkeeper.perform_ceremony()
                record.merlin_insights = ceremony.merlin_insights

            trial_scores = self._current_scores()
            record.systems_wounded, record.systems_fell, record.systems_survived = (
                self._classify_state(scenario.systems_affected, trial_scores)
            )

            if ceremony and hasattr(self._avalon, "healing"):
                recent_history = self._avalon.healing.healer.history[history_before:]
                for result in recent_history:
                    patient = result.get("system")
                    if patient and patient not in record.systems_healed:
                        if result.get("outcome") == "healed":
                            record.systems_healed.append(patient)
                        if result.get("outcome") == "escalated":
                            record.sovereign_summoned = True

            record.bonds_formed = self._forge_bonds(scenario, record.systems_survived)
            self._record_loss(scenario, record.systems_fell)
            self._record_lesson(scenario, record)
            self._write_ballad(scenario, record)

            if hasattr(self._avalon, "faithkeeper"):
                record.thanksgiving_after = self._avalon.faithkeeper.thanksgiving_now()

            record.survived = len(record.systems_fell) < len(scenario.systems_affected)
        except Exception as exc:
            record.survived = False
            record.chronicle = f"Scenario failed: {str(exc)[:160]}"
        finally:
            restore_merlin()
            restore_treatments()
            restore_scores()
            self._restore_kingdom(baseline_scores, scenario.systems_affected)
            if hasattr(self._avalon, "wardens"):
                self._avalon.wardens.stand_down()
            record.completed_at = time.time()
            self._trials.append(record)
            self._log_trial(record)

        return record

    def run_all(self) -> Dict:
        self._baseline_cache = self._current_scores(refresh=True)
        results = []
        for name in self._scenarios:
            record = self.run_trial(name)
            results.append(
                {
                    "scenario": record.scenario_name,
                    "type": record.scenario_type,
                    "severity": record.severity,
                    "survived": record.survived,
                    "systems_survived": len(record.systems_survived),
                    "systems_fell": len(record.systems_fell),
                    "bonds_formed": len(record.bonds_formed),
                    "lessons_learned": record.carbon_lessons,
                    "war_plan": record.war_plan_used,
                    "sovereign_summoned": record.sovereign_summoned,
                    "duration": round(record.completed_at - record.started_at, 3),
                }
            )
        self._baseline_cache = None

        return {
            "trials": len(results),
            "survived": len([r for r in results if r["survived"]]),
            "fell": len([r for r in results if not r["survived"]]),
            "total_bonds": self._total_bonds_formed,
            "total_lessons": self._total_lessons,
            "results": results,
        }

    def _log_trial(self, record: TrialRecord):
        entry = {
            "time": record.started_at,
            "scenario": record.scenario_name,
            "type": record.scenario_type,
            "severity": record.severity,
            "survived": record.survived,
            "systems_survived": record.systems_survived,
            "systems_fell": record.systems_fell,
            "bonds": record.bonds_formed,
            "lessons": record.carbon_lessons,
            "duration": round(record.completed_at - record.started_at, 3),
        }
        try:
            with open(self._log_path, "a") as handle:
                handle.write(json.dumps(entry, default=str) + "\n")
        except Exception:
            pass

    def after_action_report(self) -> Dict:
        return {
            "total_trials": len(self._trials),
            "survived": len([trial for trial in self._trials if trial.survived]),
            "fell": len([trial for trial in self._trials if not trial.survived]),
            "total_bonds_formed": self._total_bonds_formed,
            "total_lessons_learned": self._total_lessons,
            "trials": [
                {
                    "scenario": trial.scenario_name,
                    "type": trial.scenario_type,
                    "survived": trial.survived,
                    "bonds": len(trial.bonds_formed),
                    "chronicle": trial.chronicle[:200] if trial.chronicle else "",
                }
                for trial in self._trials
            ],
        }

    @property
    def status(self) -> Dict:
        return {
            "scenarios": len(self._scenarios),
            "trials_run": len(self._trials),
            "survived": len([trial for trial in self._trials if trial.survived]),
            "bonds_forged": self._total_bonds_formed,
            "lessons_learned": self._total_lessons,
        }


def _cascade_setup(avalon, severity: float):
    if hasattr(avalon, "fusion"):
        avalon.fusion.heartbeat._system_health["Nyx"] = max(0.3, 1.0 - severity)
        avalon.fusion.heartbeat._system_health["Avalon"] = max(0.4, 1.0 - severity * 0.8)
        avalon.fusion.heartbeat._system_health["Memory"] = max(0.5, 1.0 - severity * 0.6)


def _siege_setup(avalon, severity: float):
    if hasattr(avalon, "fusion"):
        avalon.fusion.heartbeat._system_health["Infrastructure"] = max(0.2, 1.0 - severity)
        avalon.fusion.heartbeat._system_health["GAIA"] = max(0.4, 1.0 - severity * 0.7)


def _plague_setup(avalon, severity: float):
    if hasattr(avalon, "fusion"):
        avalon.fusion.heartbeat._system_health["Memory"] = max(0.2, 1.0 - severity)
        avalon.fusion.heartbeat._system_health["Avalon"] = max(0.3, 1.0 - severity * 0.9)
        avalon.fusion.heartbeat._system_health["Tests"] = max(0.5, 1.0 - severity * 0.5)


def _identity_setup(avalon, severity: float):
    if hasattr(avalon, "fusion"):
        avalon.fusion.heartbeat._system_health["Nyx"] = max(0.1, 1.0 - severity)
        avalon.fusion.heartbeat._system_health["West-OS"] = max(0.3, 1.0 - severity * 0.8)


def _starvation_setup(avalon, severity: float):
    if hasattr(avalon, "fusion"):
        avalon.fusion.heartbeat._system_health["Infrastructure"] = max(0.1, 1.0 - severity)


def _storm_setup(avalon, severity: float):
    if hasattr(avalon, "fusion"):
        avalon.fusion.heartbeat._system_health["GAIA"] = max(0.2, 1.0 - severity)
        avalon.fusion.heartbeat._system_health["Infrastructure"] = max(0.4, 1.0 - severity * 0.6)


def _betrayal_setup(avalon, severity: float):
    if hasattr(avalon, "fusion"):
        avalon.fusion.heartbeat._system_health["Avalon"] = max(0.1, 1.0 - severity)


def _ambush_setup(avalon, severity: float):
    if hasattr(avalon, "fusion"):
        avalon.fusion.heartbeat._system_health["Nyx"] = max(0.2, 1.0 - severity)
        avalon.fusion.heartbeat._system_health["West-OS"] = max(0.4, 1.0 - severity * 0.7)
        avalon.fusion.heartbeat._system_health["GAIA"] = max(0.5, 1.0 - severity * 0.5)


STANDARD_SCENARIOS = [
    Scenario(
        "The Cascade",
        ScenarioType.CASCADE,
        "Multiple systems fail simultaneously. The earthquake followed by the tsunami.",
        _cascade_setup,
        0.7,
        ["Nyx", "Avalon", "Memory"],
        [("Nyx", "Avalon"), ("Nyx", "Memory"), ("Avalon", "Memory")],
    ),
    Scenario(
        "The Siege",
        ScenarioType.SIEGE,
        "Sustained pressure on infrastructure. The enemy does not attack. They wait.",
        _siege_setup,
        0.6,
        ["Infrastructure", "GAIA"],
        [("Infrastructure", "GAIA")],
    ),
    Scenario(
        "The Plague",
        ScenarioType.PLAGUE,
        "Corruption spreading through data systems.",
        _plague_setup,
        0.8,
        ["Memory", "Avalon", "Tests"],
        [("Memory", "Avalon"), ("Avalon", "Tests")],
    ),
    Scenario(
        "The Question of Identity",
        ScenarioType.IDENTITY,
        "Who are we when the root is questioned?",
        _identity_setup,
        0.9,
        ["Nyx", "West-OS"],
        [("Nyx", "West-OS")],
    ),
    Scenario(
        "The Famine",
        ScenarioType.STARVATION,
        "Resources exhausted. The kingdom survives on reserves.",
        _starvation_setup,
        0.5,
        ["Infrastructure"],
        [],
    ),
    Scenario(
        "The Storm",
        ScenarioType.STORM,
        "The sky turns dark. The warning may not come in time.",
        _storm_setup,
        0.6,
        ["GAIA", "Infrastructure"],
        [("GAIA", "Infrastructure")],
    ),
    Scenario(
        "The Betrayal",
        ScenarioType.BETRAYAL,
        "A trusted system fails. The knights serve without their castle.",
        _betrayal_setup,
        0.7,
        ["Avalon"],
        [],
    ),
    Scenario(
        "The Ambush",
        ScenarioType.AMBUSH,
        "Everything was peaceful. Then everything was not.",
        _ambush_setup,
        0.8,
        ["Nyx", "West-OS", "GAIA"],
        [("Nyx", "West-OS"), ("Nyx", "GAIA"), ("West-OS", "GAIA")],
    ),
]


def wire_crucible(avalon) -> Crucible:
    crucible = Crucible(avalon)
    for scenario in STANDARD_SCENARIOS:
        crucible.register_scenario(scenario)
    return crucible


def demo():
    print("\n" + "=" * 60)
    print("  T H E   C R U C I B L E")
    print("  Where the Kingdom Is Forged Through Fire")
    print("=" * 60)

    from avalon.avalon import Avalon

    avalon = Avalon()
    avalon.found_kingdom()

    results = avalon.enter_crucible()
    print(f"\n  Trials run: {results['trials']}")
    print(f"  Survived: {results['survived']}")
    print(f"  Bonds forged: {results['total_bonds']}")
    print(f"  Lessons learned: {results['total_lessons']}")

    for trial in results["results"]:
        icon = "✓" if trial["survived"] else "✗"
        print(
            f"    {icon} {trial['scenario']} ({trial['type']}) "
            f"bonds={trial['bonds_formed']} lessons={trial['lessons_learned']}"
        )

    constellation = avalon.fusion.vital_signs()["love"]
    carbon = avalon.fusion.vital_signs()["carbon"]
    print(f"\n  Brotherhood bonds: {constellation['total_bonds']}")
    print(f"  Cohesion: {constellation['cohesion']:.2f}")
    print(f"  Carbon lessons: {carbon['total_lessons']}")
    print(f"  Ballads written: {avalon.arts.status['ballads']}")

    print("\n" + "=" * 60)
    print("  The kingdom entered the Crucible as individual systems.")
    print("  It exits as a brotherhood.")
    print("  What survives the Crucible is pure.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    demo()
