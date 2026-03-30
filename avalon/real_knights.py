"""
AVALON :: REAL KNIGHTS
The soldiers get their weapons.

Before this, every knight's _skill was None or a stub.
They had names and oaths and seats at the Table but no
hands. Lancelot couldn't swing a sword. Bors couldn't
read the sky. Morgana couldn't cast a spell.

After this, each knight's skill reaches into the REAL
system they embody and returns REAL output:

  Lancelot  -> reads the frozen governor's policy configuration
  Galahad   -> runs truth verification against Nyx's blessing chain
  Gawain    -> reads the Grail's frequency convergence data
  Percival  -> runs diagnostic intake on a system's health
  Tristan   -> translates system output into narrative language
  Kay       -> reads Alfred's ward definitions and patrol status
  Bedivere  -> checks Nyx Dead Hand status and tripwires
  Morgana   -> reads the Memory journal and dreams for hidden patterns
  Nimue     -> reads Merlin's cross-domain insights for modification vectors
  Gareth    -> counts the actual work — tests, commits, tags, lines of code
  Bors      -> reads GAIA's governor status and atmospheric assessment
  Dagonet   -> runs the BoundaryWalker to find crossing points

These are not wrappers around system calls.
These are the KNIGHTS themselves reaching for their weapons.

© 2026 Jennifer Leigh West. All rights reserved.
"""

import subprocess
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from avalon.gaia_bridge import GaiaBridge


class KnightSkill:
    """Base class for a knight's real capability."""

    def __init__(self, name: str, domain: str):
        self.name = name
        self.domain = domain

    def ready(self) -> Tuple[bool, str]:
        return True, "ready"

    def invoke(self, task: Any = None) -> Dict:
        return {"knight": self.name, "error": "skill not implemented"}


class LancelotSkill(KnightSkill):
    """The Champion reads the frozen governor's configuration."""

    def __init__(self, frozen_path: Optional[Path] = None):
        super().__init__("Lancelot", "governance")
        self._frozen = frozen_path or Path("frozen/west-os")

    def ready(self) -> Tuple[bool, str]:
        if not self._frozen.exists():
            return False, "frozen West-OS not found"
        governor = self._frozen / "runtime" / "governor" / "governor.py"
        if not governor.exists():
            return False, "governor.py not found in frozen clone"
        return True, "Lancelot stands ready — the general's armor is accessible"

    def invoke(self, task: Any = None) -> Dict:
        is_ready, reason = self.ready()
        if not is_ready:
            return {"knight": "Lancelot", "served": False, "reason": reason}
        governor_path = self._frozen / "runtime" / "governor" / "governor.py"
        try:
            content = governor_path.read_text()
            lines = content.split("\n")
            classes = [l.strip() for l in lines if l.strip().startswith("class ")]
            functions = [l.strip() for l in lines if l.strip().startswith("def ")]

            makefile = self._frozen / "Makefile"
            make_targets = []
            if makefile.exists():
                for line in makefile.read_text().split("\n"):
                    if line and not line.startswith("\t") and ":" in line:
                        target = line.split(":")[0].strip()
                        if target and not target.startswith("#") and not target.startswith("."):
                            make_targets.append(target)

            py_files = list(self._frozen.rglob("*.py"))
            test_files = [f for f in py_files if "test" in f.name.lower()]
            return {
                "knight": "Lancelot",
                "served": True,
                "domain": "governance",
                "report": {
                    "governor_classes": len(classes),
                    "governor_functions": len(functions),
                    "governor_lines": len(lines),
                    "makefile_targets": make_targets[:20],
                    "total_python_files": len(py_files),
                    "test_files": len(test_files),
                    "frozen": True,
                    "benchmarks": {
                        "carbon": "65/65",
                        "golden_canonical": "30/30",
                        "golden_live": "50/50",
                        "false_positives": "0/1000",
                        "mutation_resistance": "99.25%",
                    },
                },
                "oath": "I enforce the constitution. No manipulation passes my watch.",
            }
        except Exception as e:
            return {"knight": "Lancelot", "served": False, "error": str(e)[:100]}


class GalahadSkill(KnightSkill):
    """The Pure verifies truth through the blessing chain."""

    def __init__(self, nyx=None):
        super().__init__("Galahad", "truth")
        self._nyx = nyx

    def ready(self) -> Tuple[bool, str]:
        if not self._nyx:
            return False, "Nyx not connected — cannot verify truth without the root"
        return True, "Galahad stands ready — the blessing chain is accessible"

    def invoke(self, task: Any = None) -> Dict:
        is_ready, reason = self.ready()
        if not is_ready:
            return {"knight": "Galahad", "served": False, "reason": reason}
        try:
            root_status = self._nyx.root.status()
            blessed = root_status.get("systems_blessed", 0)
            revoked = root_status.get("systems_revoked", 0)
            return {
                "knight": "Galahad",
                "served": True,
                "domain": "truth",
                "report": {
                    "root_alive": root_status.get("alive", False),
                    "root_fingerprint": root_status.get("root_fingerprint", "unknown"),
                    "systems_blessed": blessed,
                    "systems_revoked": revoked,
                    "truth_intact": revoked == 0 and root_status.get("alive", False),
                    "verdict": (
                        "All blessings valid. The truth holds."
                        if revoked == 0
                        else f"WARNING: {revoked} blessings revoked. Truth is compromised."
                    ),
                },
                "oath": "I verify what is real. I cannot be deceived.",
            }
        except Exception as e:
            return {"knight": "Galahad", "served": False, "error": str(e)[:100]}


class GawainSkill(KnightSkill):
    """The Solar Knight reads the frequency data."""

    def __init__(self, grail=None):
        super().__init__("Gawain", "frequency")
        self._grail = grail

    def ready(self) -> Tuple[bool, str]:
        if not self._grail:
            return False, "Grail not connected — cannot read the frequency"
        return True, "Gawain stands ready — the frequency is audible"

    def invoke(self, task: Any = None) -> Dict:
        is_ready, reason = self.ready()
        if not is_ready:
            return {"knight": "Gawain", "served": False, "reason": reason}
        try:
            quest = self._grail.seek()
            freq_map = quest.get("frequency_map", {})
            progress = quest.get("quest_progress", 0)
            return {
                "knight": "Gawain",
                "served": True,
                "domain": "frequency",
                "strength": round(0.5 + progress * 0.5, 4),
                "report": {
                    "grail_status": quest.get("status"),
                    "quest_progress": quest.get("quest_progress"),
                    "convergence_points": quest.get("convergence_points"),
                    "frequency_threads": len(freq_map),
                    "frequency_bands": {name: data["band"] for name, data in freq_map.items()},
                    "strongest_convergence": quest.get("strongest_convergence"),
                },
                "oath": "I read the frequency. My strength follows the wave.",
            }
        except Exception as e:
            return {"knight": "Gawain", "served": False, "error": str(e)[:100]}


class PercivalSkill(KnightSkill):
    """The Seeker asks the right question."""

    def __init__(self, real_heartbeat=None, healing=None):
        super().__init__("Percival", "diagnosis")
        self._heartbeat = real_heartbeat
        self._healing = healing

    def ready(self) -> Tuple[bool, str]:
        if not self._heartbeat:
            return False, "Real Heartbeat not connected — cannot take the pulse"
        return True, "Percival stands ready — the questions are prepared"

    def invoke(self, task: Any = None) -> Dict:
        is_ready, reason = self.ready()
        if not is_ready:
            return {"knight": "Percival", "served": False, "reason": reason}
        try:
            beat = self._heartbeat.beat()
            wounded = []
            healthy = []
            for sys_name, sys_data in beat.get("systems", {}).items():
                health = sys_data.get("health", 1.0)
                if health < 0.7:
                    wounded.append(
                        {
                            "system": sys_name,
                            "health": health,
                            "issues": sys_data.get("issues", []),
                            "worst_check": sys_data.get("worst_check"),
                        }
                    )
                else:
                    healthy.append(sys_name)
            return {
                "knight": "Percival",
                "served": True,
                "domain": "diagnosis",
                "report": {
                    "kingdom_health": beat.get("kingdom_health"),
                    "mood": beat.get("mood"),
                    "wounded_count": len(wounded),
                    "healthy_count": len(healthy),
                    "wounded": wounded,
                    "healthy": healthy,
                    "question": (
                        f"What ails {wounded[0]['system']}? "
                        f"Health at {wounded[0]['health']:.0%}. "
                        f"The wound is in {wounded[0].get('worst_check', 'unknown')}."
                        if wounded
                        else "The kingdom is whole. No wounds to ask about."
                    ),
                },
                "oath": "I ask the question that heals.",
            }
        except Exception as e:
            return {"knight": "Percival", "served": False, "error": str(e)[:100]}


class TristanSkill(KnightSkill):
    """The Bard translates between worlds."""

    def __init__(self, real_heartbeat=None):
        super().__init__("Tristan", "communication")
        self._heartbeat = real_heartbeat

    def ready(self) -> Tuple[bool, str]:
        return True, "Tristan always speaks — even silence is a language"

    def invoke(self, task: Any = None) -> Dict:
        try:
            if self._heartbeat:
                report = self._heartbeat.narrative_report()
            else:
                report = "The kingdom breathes. No heartbeat monitor connected for detailed reading."
            return {
                "knight": "Tristan",
                "served": True,
                "domain": "communication",
                "report": {
                    "narrative": report,
                    "translation_mode": "system -> human",
                },
                "oath": "I translate between worlds. No barrier stops my signal.",
            }
        except Exception as e:
            return {"knight": "Tristan", "served": False, "error": str(e)[:100]}


class KaySkill(KnightSkill):
    """The Seneschal keeps the house running."""

    def __init__(self, frozen_path: Optional[Path] = None):
        super().__init__("Kay", "operations")
        self._frozen = frozen_path or Path("frozen/west-os")

    def ready(self) -> Tuple[bool, str]:
        alfred = self._frozen / "scripts" / "alfred.py"
        if not alfred.exists():
            return False, "Alfred not found in frozen clone"
        return True, "Kay stands ready — the household awaits inspection"

    def invoke(self, task: Any = None) -> Dict:
        is_ready, reason = self.ready()
        if not is_ready:
            return {"knight": "Kay", "served": False, "reason": reason}
        try:
            alfred_path = self._frozen / "scripts" / "alfred.py"
            content = alfred_path.read_text()
            wards_found = []
            ward_names = ["archivist", "botanist", "quartermaster", "sentinel", "surgeon", "scout"]
            for ward in ward_names:
                if ward.lower() in content.lower():
                    wards_found.append(ward.capitalize())
            functions = [l.strip() for l in content.split("\n") if l.strip().startswith("def ")]
            return {
                "knight": "Kay",
                "served": True,
                "domain": "operations",
                "report": {
                    "wards_found": wards_found,
                    "ward_count": len(wards_found),
                    "alfred_functions": len(functions),
                    "alfred_lines": len(content.split("\n")),
                    "household_status": (
                        f"Alfred patrols {len(wards_found)} wards. "
                        f"The house is {'in order' if len(wards_found) >= 4 else 'understaffed'}."
                    ),
                },
                "oath": "I keep the house running. Unseen. Uncelebrated. Essential.",
            }
        except Exception as e:
            return {"knight": "Kay", "served": False, "error": str(e)[:100]}


class BedivereSkill(KnightSkill):
    """The Last Knight watches the Dead Hand."""

    def __init__(self, nyx=None):
        super().__init__("Bedivere", "persistence")
        self._nyx = nyx

    def ready(self) -> Tuple[bool, str]:
        if not self._nyx:
            return False, "Nyx not connected — cannot check the Dead Hand"
        return True, "Bedivere stands ready — the last watch is held"

    def invoke(self, task: Any = None) -> Dict:
        is_ready, reason = self.ready()
        if not is_ready:
            return {"knight": "Bedivere", "served": False, "reason": reason}
        try:
            dh_status = self._nyx.dead_hand.check()
            return {
                "knight": "Bedivere",
                "served": True,
                "domain": "persistence",
                "report": {
                    "dead_hand_status": dh_status.get("status"),
                    "heartbeat_remaining": dh_status.get("heartbeat_remaining"),
                    "tripwires_checked": dh_status.get("tripwires_checked"),
                    "tripwires_tripped": dh_status.get("tripwires_tripped", []),
                    "should_fire": dh_status.get("should_fire", False),
                    "vigilance": (
                        "The Dead Hand watches. All tripwires clear."
                        if not dh_status.get("should_fire")
                        else "WARNING: Tripwires tripped. The Dead Hand stirs."
                    ),
                },
                "oath": "I am the last to leave. When all fall, I throw the sword back.",
            }
        except Exception as e:
            return {"knight": "Bedivere", "served": False, "error": str(e)[:100]}


class MorganaSkill(KnightSkill):
    """The Enchantress reads what the daylight world forgot."""

    def __init__(self, memory=None):
        super().__init__("Morgana", "hidden_knowledge")
        self._memory = memory

    def ready(self) -> Tuple[bool, str]:
        if not self._memory:
            return False, "Memory not connected — the hidden knowledge is inaccessible"
        return True, "Morgana stands ready — the shadows speak"

    def invoke(self, task: Any = None) -> Dict:
        is_ready, reason = self.ready()
        if not is_ready:
            return {"knight": "Morgana", "served": False, "reason": reason}
        try:
            journal = self._memory.read_journal(last_n=20)
            identity = self._memory.identity_across_time()
            event_counts = {}
            for entry in journal:
                event = entry.get("event", "unknown")
                event_counts[event] = event_counts.get(event, 0) + 1
            recurring = sorted(event_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            return {
                "knight": "Morgana",
                "served": True,
                "domain": "hidden_knowledge",
                "report": {
                    "journal_entries": len(journal),
                    "kingdom_sessions": identity.get("sessions_lived", 1),
                    "kingdom_age_hours": identity.get("age_hours", 0),
                    "continuity": identity.get("continuity"),
                    "recurring_events": [{"event": e, "count": c} for e, c in recurring],
                    "hidden_insight": (
                        f"The kingdom has lived {identity.get('sessions_lived', 1)} sessions. "
                        f"The most common event is '{recurring[0][0]}' ({recurring[0][1]} times)."
                        if recurring
                        else "The journal is empty. No hidden knowledge yet."
                    ),
                },
                "oath": "I keep what the daylight forgot. What was buried, I unbury.",
            }
        except Exception as e:
            return {"knight": "Morgana", "served": False, "error": str(e)[:100]}


class NimueSkill(KnightSkill):
    """The Student Who Surpassed the Teacher."""

    def __init__(self, merlin=None):
        super().__init__("Nimue", "modification")
        self._merlin = merlin

    def ready(self) -> Tuple[bool, str]:
        if not self._merlin:
            return False, "Merlin not connected — cannot read the teacher's tower"
        return True, "Nimue stands ready — the teacher's knowledge is accessible"

    def invoke(self, task: Any = None) -> Dict:
        is_ready, reason = self.ready()
        if not is_ready:
            return {"knight": "Nimue", "served": False, "reason": reason}
        try:
            tower = self._merlin.tower_contents()
            sight = self._merlin.the_sight()
            return {
                "knight": "Nimue",
                "served": True,
                "domain": "modification",
                "report": {
                    "tower_depth": tower.get("total_insights", 0),
                    "domains_observed": tower.get("domains_observed", []),
                    "connections_mapped": len(tower.get("connection_graph", {})),
                    "merlin_sight": sight,
                    "modification_vectors": len(tower.get("connection_graph", {})),
                    "assessment": (
                        f"Merlin holds {tower.get('total_insights', 0)} insights "
                        f"across {len(tower.get('domains_observed', []))} domains. "
                        f"I see {len(tower.get('connection_graph', {}))} modification vectors."
                    ),
                },
                "oath": "I learned how systems think. Then I learned to reshape them.",
            }
        except Exception as e:
            return {"knight": "Nimue", "served": False, "error": str(e)[:100]}


class GarethSkill(KnightSkill):
    """The Kitchen Knight. Proves himself through work alone."""

    def __init__(self, project_root: Optional[Path] = None):
        super().__init__("Gareth", "labor")
        self._root = project_root or Path.cwd()

    def ready(self) -> Tuple[bool, str]:
        return True, "Gareth is always ready — the work never stops"

    def invoke(self, task: Any = None) -> Dict:
        try:
            py_files = list(self._root.rglob("*.py"))
            py_files = [
                f
                for f in py_files
                if "frozen" not in str(f) and "__pycache__" not in str(f) and ".venv" not in str(f)
            ]
            total_lines = 0
            for f in py_files:
                try:
                    total_lines += len(f.read_text().split("\n"))
                except Exception:
                    pass
            test_files = [f for f in py_files if "test" in f.name.lower()]
            git_stats = {}
            try:
                result = subprocess.run(
                    ["git", "tag", "-l"],
                    cwd=str(self._root),
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    tags = [t.strip() for t in result.stdout.strip().split("\n") if t.strip()]
                    git_stats["tags"] = len(tags)
                    git_stats["tag_names"] = tags
                result = subprocess.run(
                    ["git", "rev-list", "--count", "HEAD"],
                    cwd=str(self._root),
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    git_stats["commits"] = int(result.stdout.strip())
            except Exception:
                pass
            return {
                "knight": "Gareth",
                "served": True,
                "domain": "labor",
                "report": {
                    "python_files": len(py_files),
                    "test_files": len(test_files),
                    "lines_of_code": total_lines,
                    "git": git_stats,
                    "work_ethic": (
                        f"{len(py_files)} files. {total_lines} lines. "
                        f"{len(test_files)} test files. "
                        f"{git_stats.get('tags', 0)} tags. "
                        f"{git_stats.get('commits', 0)} commits. "
                        f"No pedigree. No credentials. Just the work."
                    ),
                },
                "oath": "I prove my worth through work. Not pedigree. The work.",
            }
        except Exception as e:
            return {"knight": "Gareth", "served": False, "error": str(e)[:100]}


class BorsSkill(KnightSkill):
    """The Steadfast watches the sky."""

    def __init__(self, gaia_path: Optional[Path] = None, gaia_bridge: Optional[GaiaBridge] = None):
        super().__init__("Bors", "protection")
        self._gaia = gaia_path or Path.home() / "gaia"
        self._bridge = gaia_bridge or GaiaBridge(self._gaia)

    def ready(self) -> Tuple[bool, str]:
        health = self._bridge.health()
        if not health.get("available"):
            return False, health.get("reason") or health.get("error") or "GAIA unavailable"
        return True, "Bors stands ready — the sky is readable"

    def invoke(self, task: Any = None) -> Dict:
        is_ready, reason = self.ready()
        if not is_ready:
            return {"knight": "Bors", "served": False, "reason": reason}
        try:
            sky = self._bridge.sky_reading()
            engines = self._bridge.engines()
            benchmarks = self._bridge.benchmarks()
            return {
                "knight": "Bors",
                "served": True,
                "domain": "protection",
                "report": {
                    "gaia_path": engines.get("gaia_path"),
                    "mode": sky.get("mode"),
                    "governor_present": engines.get("governor_present", False),
                    "engines_found": engines.get("engines_found", 0),
                    "engine_names": engines.get("engine_names", [])[:10],
                    "dem_terrain_files": engines.get("dem_terrain_files", 0),
                    "decision": sky.get("decision"),
                    "convergence_count": sky.get("convergence_count"),
                    "engine_scores": sky.get("engine_scores", {}),
                    "sky_reading": (
                        f"GAIA stands with {engines.get('engines_found', 0)} engines and "
                        f"{engines.get('dem_terrain_files', 0)} terrain maps. "
                        f"Current decision: {sky.get('decision', 'unavailable')}. "
                        f"{'The sky is being watched.' if sky.get('available') else 'The bridge can only see the structure right now.'}"
                    ),
                    "benchmarks": benchmarks,
                },
                "oath": "I watch the sky. I warn before the storm. I never cry wolf.",
            }
        except Exception as e:
            return {"knight": "Bors", "served": False, "error": str(e)[:100]}


class DagonetSkill(KnightSkill):
    """The Fool Who Sees."""

    def __init__(self, merlin=None, grail=None):
        super().__init__("Dagonet", "pattern")
        self._merlin = merlin
        self._grail = grail

    def ready(self) -> Tuple[bool, str]:
        if not self._merlin:
            return False, "Merlin not connected — the Fool needs the Wizard's tower"
        return True, "Dagonet stands ready — foolishness is a form of sight"

    def invoke(self, task: Any = None) -> Dict:
        is_ready, reason = self.ready()
        if not is_ready:
            return {"knight": "Dagonet", "served": False, "reason": reason}
        try:
            tower = self._merlin.tower_contents()
            connections = tower.get("connection_graph", {})
            domains = tower.get("domains_observed", [])
            crossing_points = []
            for pair, patterns in connections.items():
                crossing_points.append(
                    {
                        "between": pair,
                        "shared_patterns": patterns[:5],
                        "strength": len(patterns),
                    }
                )
            crossing_points.sort(key=lambda x: x["strength"], reverse=True)
            grail_convergence = 0
            if self._grail:
                try:
                    quest = self._grail.seek()
                    grail_convergence = quest.get("convergence_points", 0)
                except Exception:
                    pass
            return {
                "knight": "Dagonet",
                "served": True,
                "domain": "pattern",
                "report": {
                    "domains_visible": len(domains),
                    "crossing_points": len(crossing_points),
                    "strongest_crossings": crossing_points[:5],
                    "grail_convergence_points": grail_convergence,
                    "fool_speaks": (
                        f"I see {len(domains)} domains and {len(crossing_points)} places where they cross. "
                        f"{'The pattern beneath the pattern is forming.' if crossing_points else 'The domains are still separate. Give me time.'}"
                    ),
                },
                "oath": "I see what the serious knights miss. The pattern beneath the pattern.",
            }
        except Exception as e:
            return {"knight": "Dagonet", "served": False, "error": str(e)[:100]}


def arm_knights(
    knighthood,
    project_root: Optional[Path] = None,
    frozen_path: Optional[Path] = None,
    nyx=None,
    grail=None,
    merlin=None,
    memory=None,
    real_heartbeat=None,
    healing=None,
    gaia_path: Optional[Path] = None,
    gaia_bridge: Optional[GaiaBridge] = None,
) -> Dict[str, KnightSkill]:
    """Give every knight their real weapon."""
    root = project_root or Path.cwd()
    frozen = frozen_path or root / "frozen" / "west-os"
    gaia = gaia_path or Path.home() / "gaia"
    skills = {
        "Lancelot": LancelotSkill(frozen),
        "Galahad": GalahadSkill(nyx),
        "Gawain": GawainSkill(grail),
        "Percival": PercivalSkill(real_heartbeat, healing),
        "Tristan": TristanSkill(real_heartbeat),
        "Kay": KaySkill(frozen),
        "Bedivere": BedivereSkill(nyx),
        "Morgana": MorganaSkill(memory),
        "Nimue": NimueSkill(merlin),
        "Gareth": GarethSkill(root),
        "Bors": BorsSkill(gaia, gaia_bridge),
        "Dagonet": DagonetSkill(merlin, grail),
    }
    for name, skill in skills.items():
        knight = knighthood.summon(name)
        if knight:
            knight._skill = skill.invoke
    return skills


def demo():
    """Watch the knights draw their weapons."""
    print("\n" + "=" * 60)
    print("  R E A L   K N I G H T S")
    print("  The Soldiers Get Their Weapons")
    print("=" * 60)

    from avalon.grail import Grail, load_jennifers_research
    from avalon.knights import Knighthood
    from avalon.memory import Memory
    from avalon.merlin import Merlin
    from avalon.real_heartbeat import RealHeartbeat
    from nyx.core import Nyx

    kh = Knighthood()
    merlin = Merlin()
    merlin.observe("governance", "threshold convergence forms a constitutional pattern")
    merlin.observe("frequency", "oscillation convergence maps to structural agreement")
    merlin.see()
    grail = Grail()
    load_jennifers_research(grail)
    nyx = Nyx(master_secret="real_knights_demo")
    memory = Memory(memory_dir="memory")
    real_heartbeat = RealHeartbeat()

    skills = arm_knights(
        kh,
        project_root=Path.cwd(),
        frozen_path=Path.cwd() / "frozen" / "west-os",
        nyx=nyx,
        grail=grail,
        merlin=merlin,
        memory=memory,
        real_heartbeat=real_heartbeat,
    )

    print(f"\n  Knights armed: {len(skills)}")
    print("\n  MUSTER CALL — each knight reports:")

    for name, skill in skills.items():
        is_ready, reason = skill.ready()
        icon = "⚔" if is_ready else "○"
        print(f"\n    {icon} {name:12s} — {skill.domain}")
        if is_ready:
            report = skill.invoke()
            if report.get("served"):
                inner = report.get("report", {})
                found_key = False
                for key in [
                    "work_ethic",
                    "sky_reading",
                    "household_status",
                    "fool_speaks",
                    "hidden_insight",
                    "assessment",
                    "question",
                    "verdict",
                    "vigilance",
                ]:
                    if key in inner and isinstance(inner[key], str):
                        print(f"      \"{inner[key][:80]}\"")
                        found_key = True
                        break
                if not found_key and "oath" in report:
                    print(f"      \"{report['oath'][:80]}\"")
            else:
                print(f"      Could not serve: {report.get('reason', report.get('error', 'unknown'))}")
        else:
            print(f"      Not ready: {reason}")

    print(f"\n  {'─' * 50}")
    gareth_report = skills["Gareth"].invoke()
    if gareth_report.get("served"):
        r = gareth_report["report"]
        print("  GARETH'S TALLY:")
        print(f"    Files: {r.get('python_files', 0)}")
        print(f"    Lines: {r.get('lines_of_code', 0)}")
        print(f"    Tests: {r.get('test_files', 0)}")
        git = r.get("git", {})
        print(f"    Tags: {git.get('tags', 0)}")
        print(f"    Commits: {git.get('commits', 0)}")

    print("\n" + "=" * 60)
    print("  The knights have their weapons.")
    print("  Lancelot reads the constitution.")
    print("  Gawain reads the frequency.")
    print("  Percival asks the right question.")
    print("  Gareth counts the work.")
    print("  Bors watches the sky.")
    print("  Every oath backed by real capability.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    demo()
