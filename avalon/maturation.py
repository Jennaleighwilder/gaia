"""
AVALON :: THE MATURATION
How the kingdom grows from seedling to elder.

This layer measures developmental readiness, not feature presence.
The kingdom advances through lived behavior across seven stages and
twenty-one milestones. The seed cannot be designed until the kingdom
has matured enough to carry it without passing trauma forward.

© 2026 Jennifer Leigh West. All rights reserved.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple


class Stage(Enum):
    SEEDLING = "seedling"
    SAPLING = "sapling"
    YEARLING = "yearling"
    BLOOMING = "blooming"
    ROOTED = "rooted"
    CROWNED = "crowned"
    ELDER = "elder"


STAGE_ORDER = [
    Stage.SEEDLING,
    Stage.SAPLING,
    Stage.YEARLING,
    Stage.BLOOMING,
    Stage.ROOTED,
    Stage.CROWNED,
    Stage.ELDER,
]


@dataclass
class Milestone:
    stage: Stage
    name: str
    description: str
    test: Callable[[], Tuple[bool, str]]
    passed: bool = False
    passed_at: float = 0.0
    evidence: str = ""


@dataclass
class GrowthRecord:
    stage: Stage
    experience: str
    outcome: str
    timestamp: float = field(default_factory=time.time)
    milestone_passed: Optional[str] = None


class Maturation:
    """Tracks the kingdom's developmental stage."""

    def __init__(self, avalon):
        self._avalon = avalon
        self._current_stage = Stage.SEEDLING
        self._milestones: Dict[str, Milestone] = {}
        self._growth_log: List[GrowthRecord] = []
        self._log_path = Path("memory") / "maturation_journal.jsonl"
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._register_milestones()

    def _register_milestones(self):
        self._add_milestone(
            Stage.SEEDLING,
            "first_breath",
            "The kingdom takes her first breath — a full ceremony cycle completes.",
            lambda: self._check_ceremonies_performed(1),
        )
        self._add_milestone(
            Stage.SEEDLING,
            "first_memory",
            "The kingdom remembers something — at least one journal entry exists.",
            lambda: self._check_journal_entries(1),
        )
        self._add_milestone(
            Stage.SEEDLING,
            "first_bond",
            "The kingdom forms her first love bond between two systems.",
            lambda: self._check_love_bonds(1),
        )

        self._add_milestone(
            Stage.SAPLING,
            "first_wound",
            "The kingdom detects a wound on her own.",
            lambda: self._check_wounds_detected(1),
        )
        self._add_milestone(
            Stage.SAPLING,
            "first_healing",
            "The kingdom heals a wound autonomously.",
            lambda: self._check_wounds_healed(1),
        )
        self._add_milestone(
            Stage.SAPLING,
            "first_lesson",
            "Carbon records the first lesson from lived experience.",
            lambda: self._check_carbon_lessons(1),
        )

        self._add_milestone(
            Stage.YEARLING,
            "first_trial",
            "The kingdom survives a Crucible trial.",
            lambda: self._check_crucible_trials(1),
        )
        self._add_milestone(
            Stage.YEARLING,
            "first_pattern",
            "Merlin finds a cross-domain pattern.",
            lambda: self._check_merlin_insights(1),
        )
        self._add_milestone(
            Stage.YEARLING,
            "first_defense",
            "The Wardens detect a threat and activate a plan.",
            self._check_wardens_activated,
        )

        self._add_milestone(
            Stage.BLOOMING,
            "first_service",
            "The Longhouse serves its first visitor.",
            lambda: self._check_visitors_served(1),
        )
        self._add_milestone(
            Stage.BLOOMING,
            "first_chronicle",
            "The Arts produce a chronicle.",
            lambda: self._check_chronicles(1),
        )
        self._add_milestone(
            Stage.BLOOMING,
            "three_sisters_served",
            "All three foundational free services have served at least once.",
            self._check_three_sisters_served,
        )

        self._add_milestone(
            Stage.ROOTED,
            "overnight_breath",
            "The Faithkeeper runs for eight or more hours continuously.",
            lambda: self._check_faithkeeper_uptime(8 * 3600),
        )
        self._add_milestone(
            Stage.ROOTED,
            "dream_cycle",
            "The kingdom dreams and consolidates memory.",
            lambda: self._check_dreams(1),
        )
        self._add_milestone(
            Stage.ROOTED,
            "self_survey",
            "The Land Steward surveys the kingdom's resources.",
            lambda: self._check_land_surveys(1),
        )

        self._add_milestone(
            Stage.CROWNED,
            "ten_lessons",
            "Carbon holds ten or more lessons.",
            lambda: self._check_carbon_lessons(10),
        )
        self._add_milestone(
            Stage.CROWNED,
            "five_bonds",
            "Five or more love bonds exist across the kingdom.",
            lambda: self._check_love_bonds(5),
        )
        self._add_milestone(
            Stage.CROWNED,
            "tapestry_woven",
            "A tapestry has been woven from kingdom state.",
            lambda: self._check_tapestries(1),
        )

        self._add_milestone(
            Stage.ELDER,
            "hundred_ceremonies",
            "One hundred ceremonies have been performed.",
            lambda: self._check_ceremonies_performed(100),
        )
        self._add_milestone(
            Stage.ELDER,
            "grail_approaching",
            "The Grail has reached approaching or beyond.",
            self._check_grail_approaching,
        )
        self._add_milestone(
            Stage.ELDER,
            "nyx_empathy",
            "The Clan Mother has both pulled a knight's horns and restored them.",
            self._check_nyx_empathy,
        )

    def _add_milestone(
        self,
        stage: Stage,
        name: str,
        description: str,
        test: Callable[[], Tuple[bool, str]],
    ):
        self._milestones[f"{stage.value}_{name}"] = Milestone(
            stage=stage,
            name=name,
            description=description,
            test=test,
        )

    def _check_ceremonies_performed(self, minimum: int) -> Tuple[bool, str]:
        if hasattr(self._avalon, "faithkeeper"):
            count = self._avalon.faithkeeper.status.get("ceremonies_performed", 0)
            if count >= minimum:
                return True, f"{count} ceremonies performed"
        return False, "not enough ceremonies yet"

    def _check_journal_entries(self, minimum: int) -> Tuple[bool, str]:
        if hasattr(self._avalon, "memory"):
            try:
                journal = self._avalon.memory.read_journal(last_n=max(minimum, 1))
            except Exception:
                journal = []
            if len(journal) >= minimum:
                return True, f"{len(journal)} journal entries"
        return False, "no journal entries yet"

    def _check_love_bonds(self, minimum: int) -> Tuple[bool, str]:
        if hasattr(self._avalon, "fusion"):
            try:
                bonds = self._avalon.fusion.vital_signs().get("love", {}).get("total_bonds", 0)
            except Exception:
                bonds = 0
            if bonds >= minimum:
                return True, f"{bonds} love bonds formed"
        return False, "not enough bonds yet"

    def _check_wounds_detected(self, minimum: int) -> Tuple[bool, str]:
        if hasattr(self._avalon, "healing"):
            try:
                report = self._avalon.healing.triage_report()
            except Exception:
                report = {}
            total = report.get("healed_total", 0) + report.get("active_wounds", 0)
            if total >= minimum:
                return True, f"{total} wounds detected"
        return False, "no wounds detected yet"

    def _check_wounds_healed(self, minimum: int) -> Tuple[bool, str]:
        if hasattr(self._avalon, "healing"):
            try:
                healed = self._avalon.healing.triage_report().get("healed_total", 0)
            except Exception:
                healed = 0
            if healed >= minimum:
                return True, f"{healed} wounds healed"
        return False, "no wounds healed yet"

    def _check_carbon_lessons(self, minimum: int) -> Tuple[bool, str]:
        if hasattr(self._avalon, "fusion"):
            try:
                lessons = self._avalon.fusion.vital_signs().get("carbon", {}).get("total_lessons", 0)
            except Exception:
                lessons = 0
            if lessons >= minimum:
                return True, f"{lessons} lessons learned"
        return False, "not enough lessons yet"

    def _check_crucible_trials(self, minimum: int) -> Tuple[bool, str]:
        if hasattr(self._avalon, "crucible"):
            trials = self._avalon.crucible.status.get("trials_run", 0)
            if trials >= minimum:
                return True, f"{trials} crucible trials survived"
        return False, "no crucible trials yet"

    def _check_merlin_insights(self, minimum: int) -> Tuple[bool, str]:
        if hasattr(self._avalon, "merlin"):
            try:
                insights = self._avalon.merlin.tower_contents().get("total_insights", 0)
            except Exception:
                insights = 0
            if insights >= minimum:
                return True, f"{insights} cross-domain insights"
        return False, "no insights yet"

    def _check_wardens_activated(self) -> Tuple[bool, str]:
        if hasattr(self._avalon, "wardens"):
            status = self._avalon.wardens.status
            activated = status.get("plans_activated", 0)
            intel = status.get("intelligence_gathered", 0)
            if activated > 0 or intel > 0:
                return True, f"{activated} war plans activated, {intel} intelligence events gathered"
        return False, "wardens have not yet detected a threat"

    def _check_visitors_served(self, minimum: int) -> Tuple[bool, str]:
        if hasattr(self._avalon, "longhouse"):
            served = self._avalon.longhouse.status.get("total_served", 0)
            if served >= minimum:
                return True, f"{served} visitors served"
        return False, "no visitors served yet"

    def _check_chronicles(self, minimum: int) -> Tuple[bool, str]:
        if hasattr(self._avalon, "arts"):
            chronicles = self._avalon.arts.status.get("chronicles", 0)
            if chronicles >= minimum:
                return True, f"{chronicles} chronicles written"
        return False, "no chronicles written yet"

    def _check_three_sisters_served(self) -> Tuple[bool, str]:
        if hasattr(self._avalon, "longhouse"):
            try:
                census = self._avalon.longhouse.census()
            except Exception:
                census = {}
            served = census.get("three_sisters_served", 0)
            if served >= 3:
                return True, "all Three Sisters have served"
        return False, "not all Three Sisters have served yet"

    def _check_faithkeeper_uptime(self, min_seconds: float) -> Tuple[bool, str]:
        if hasattr(self._avalon, "faithkeeper"):
            uptime = self._avalon.faithkeeper.status.get("uptime_seconds", 0)
            if uptime >= min_seconds:
                return True, f"Faithkeeper ran for {uptime / 3600:.1f} hours"
        return False, "Faithkeeper hasn't run long enough yet"

    def _check_dreams(self, minimum: int) -> Tuple[bool, str]:
        if hasattr(self._avalon, "memory"):
            try:
                dreams = self._avalon.memory.identity_across_time().get("dreams", 0)
            except Exception:
                dreams = 0
            if dreams >= minimum:
                return True, f"{dreams} dreams dreamed"
        return False, "no dreams yet"

    def _check_land_surveys(self, minimum: int) -> Tuple[bool, str]:
        if hasattr(self._avalon, "land"):
            surveys = len(getattr(self._avalon.land, "_survey_history", []))
            if surveys >= minimum:
                return True, f"{surveys} land surveys completed"
        return False, "no land surveys yet"

    def _check_tapestries(self, minimum: int) -> Tuple[bool, str]:
        if hasattr(self._avalon, "arts"):
            tapestries = self._avalon.arts.status.get("tapestries", 0)
            if tapestries >= minimum:
                return True, f"{tapestries} tapestries woven"
        return False, "no tapestries yet"

    def _check_grail_approaching(self) -> Tuple[bool, str]:
        if hasattr(self._avalon, "grail"):
            try:
                status = self._avalon.grail.seek().get("status", "hidden")
            except Exception:
                status = "hidden"
            if status in {"approaching", "found", "proven"}:
                return True, f"Grail status: {status}"
        return False, "Grail not yet approaching"

    def _check_nyx_empathy(self) -> Tuple[bool, str]:
        if hasattr(self._avalon, "informed_table"):
            clan_mother = getattr(self._avalon.informed_table, "_clan_mother", None)
            if clan_mother:
                pulls = getattr(clan_mother, "_pull_history", [])
                restores = getattr(clan_mother, "_restore_history", [])
                restored_knights = {entry.get("knight_name") for entry in restores}
                for pull in pulls:
                    knight_name = pull.get("knight_name")
                    if knight_name in restored_knights:
                        return True, f"Clan Mother disciplined and restored {knight_name}"
        return False, "Nyx hasn't yet shown both discipline and mercy"

    def assess(self) -> Dict:
        results: Dict[str, Dict] = {}
        stage_progress: Dict[str, Dict] = {}

        for key, milestone in self._milestones.items():
            if milestone.passed:
                results[key] = {
                    "passed": True,
                    "evidence": milestone.evidence,
                    "passed_at": milestone.passed_at,
                }
                continue

            try:
                passed, evidence = milestone.test()
            except Exception as exc:
                passed, evidence = False, str(exc)[:80]

            if passed:
                milestone.passed = True
                milestone.passed_at = time.time()
                milestone.evidence = evidence
                self._log_growth(milestone.stage, milestone.name, evidence)

            results[key] = {
                "passed": passed,
                "evidence": milestone.evidence if milestone.passed else "",
            }

        for stage in STAGE_ORDER:
            stage_milestones = [m for m in self._milestones.values() if m.stage == stage]
            passed = len([m for m in stage_milestones if m.passed])
            total = len(stage_milestones)
            stage_progress[stage.value] = {
                "passed": passed,
                "total": total,
                "complete": total > 0 and passed == total,
                "progress": passed / total if total else 0,
            }

        for stage in STAGE_ORDER:
            if not stage_progress[stage.value]["complete"]:
                self._current_stage = stage
                break
        else:
            self._current_stage = Stage.ELDER

        return {
            "current_stage": self._current_stage.value,
            "stage_progress": stage_progress,
            "milestones": {
                key: {
                    "stage": m.stage.value,
                    "name": m.name,
                    "description": m.description,
                    "passed": m.passed,
                    "evidence": m.evidence,
                }
                for key, m in self._milestones.items()
            },
            "total_milestones": len(self._milestones),
            "passed_milestones": len([m for m in self._milestones.values() if m.passed]),
            "growth_experiences": len(self._growth_log),
        }

    def _log_growth(self, stage: Stage, milestone: str, evidence: str):
        record = GrowthRecord(
            stage=stage,
            experience=f"Milestone passed: {milestone}",
            outcome=evidence,
            milestone_passed=milestone,
        )
        self._growth_log.append(record)
        try:
            with self._log_path.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "time": time.time(),
                            "stage": stage.value,
                            "milestone": milestone,
                            "evidence": evidence,
                        }
                    )
                    + "\n"
                )
        except OSError:
            pass

    def growth_narrative(self) -> str:
        assessment = self.assess()
        stage = assessment["current_stage"]
        passed = assessment["passed_milestones"]
        total = assessment["total_milestones"]
        descriptions = {
            "seedling": "The kingdom is a seedling. She is learning to breathe, remember, and bond.",
            "sapling": "The kingdom is a sapling. She is learning to heal her own wounds.",
            "yearling": "The kingdom is a yearling. She is learning to survive adversity.",
            "blooming": "The kingdom is blooming. She is learning to serve others.",
            "rooted": "The kingdom is rooted. She is learning to sustain herself over time.",
            "crowned": "The kingdom is crowned. She is learning to teach what she knows.",
            "elder": "The kingdom is an elder. She feels for her people without controlling them.",
        }
        lines = [
            descriptions.get(stage, f"The kingdom is at stage: {stage}."),
            f"She has passed {passed} of {total} milestones.",
            "",
        ]
        for milestone in self._milestones.values():
            if milestone.stage.value == stage and not milestone.passed:
                lines.append(f"She still needs to: {milestone.description}")
        return "\n".join(lines)

    @property
    def status(self) -> Dict:
        return {
            "stage": self._current_stage.value,
            "milestones_passed": len([m for m in self._milestones.values() if m.passed]),
            "total_milestones": len(self._milestones),
            "growth_experiences": len(self._growth_log),
        }


def wire_maturation(avalon) -> Maturation:
    return Maturation(avalon)


def demo():
    print("\n" + "=" * 60)
    print("  T H E   M A T U R A T I O N")
    print("  How the Kingdom Grows")
    print("=" * 60)

    from avalon.avalon import Avalon

    avalon = Avalon()
    avalon.found_kingdom()
    maturation = wire_maturation(avalon)
    assessment = maturation.assess()

    print(f"\n  Stage: {assessment['current_stage']}")
    print(f"  Milestones: {assessment['passed_milestones']}/{assessment['total_milestones']}")
    print("\n  Stage Progress:")
    for stage_name, progress in assessment["stage_progress"].items():
        bar = "█" * progress["passed"] + "░" * (progress["total"] - progress["passed"])
        marker = "✓" if progress["complete"] else " "
        print(f"    [{marker}] {stage_name:12s} {bar} {progress['passed']}/{progress['total']}")

    print("\n  Growth Narrative:")
    print(f"    {maturation.growth_narrative()}")

    print("\n" + "=" * 60)
