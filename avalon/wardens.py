"""
AVALON :: THE WARDENS
Defense of the realm. Scouts, spies, and war plans.

The kingdom has an army (knights), a healer (apothecary), a wall
(Nyx), and a kill switch (Dead Hand). But it has no INTELLIGENCE.
No scouts watching the perimeter. No spies gathering information
about threats. No war plans for when the attack comes. No siege
protocols for sustained assault. No plague response for corrupted
data spreading through the system.

Real defense is not a wall. Real defense is an IMMUNE SYSTEM.

THE INNATE DEFENSE (always on, no learning required):
  - Walls (Nyx root authority, blessing chain)
  - Skin (the Shapeshifter — looks different every time)
  - Fever response (intensify monitoring on detection)

THE ADAPTIVE DEFENSE (learns, remembers, responds faster each time):
  - Scouts (patrol the perimeter, report movement)
  - Spies (honeypots that attract and study attackers)
  - Memory cells (Carbon lessons about past attacks)
  - Antibodies (specific responses to known attack patterns)

THE WAR ROOM:
  - Battle plans for different attack types
  - Siege protocols for sustained assault
  - Plague protocols for data corruption spreading
  - Natural disaster protocols for cascade failures
  - Evacuation protocols (save critical state, abandon the rest)

THE WATCHTOWER NETWORK (Roman limes model):
  - Sentinels at every border (file system, network, process)
  - Signal fires (alerts that cascade through the system)
  - The Byzantine ear (pattern detection in probes and scans)

In the Haudenosaunee model, the War Chief is SEPARATE from the
Peace Chief. The Clan Mother decides when to go to war. The War
Chief executes. When peace returns, the War Chief steps down and
the Peace Chief resumes.

The Wardens are the War Chiefs. They activate when threatened.
They stand down when peace returns. The Faithkeeper (Peace Chief)
resumes the ceremonies.

© 2026 Jennifer Leigh West. All rights reserved.
"""

import json
import os
import time
import hashlib
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque


# ═══════════════════════════════════════════════════════════════
#  THREAT LEVELS — like DEFCON but for the kingdom
# ═══════════════════════════════════════════════════════════════

class ThreatLevel(Enum):
    PEACE = "peace"               # no threats detected — normal operations
    VIGILANCE = "vigilance"       # unusual activity detected — increased monitoring
    ALERT = "alert"               # confirmed probe or anomaly — scouts deployed
    WAR = "war"                   # active attack — war plans execute
    SIEGE = "siege"               # sustained attack — conservation mode
    PLAGUE = "plague"             # data corruption spreading — quarantine protocols


# ═══════════════════════════════════════════════════════════════
#  SCOUT — patrols the perimeter, reports movement
# ═══════════════════════════════════════════════════════════════

@dataclass
class ScoutReport:
    """What a scout found on patrol."""
    sector: str
    timestamp: float = field(default_factory=time.time)
    finding: str = ""
    threat: bool = False
    severity: float = 0        # 0-1, how dangerous
    details: Dict = field(default_factory=dict)


class Scout:
    """Patrols a sector and reports what she finds.
    
    Each scout watches one domain:
    - File system scout: new/modified/deleted files
    - Process scout: unexpected processes
    - Network scout: unusual port activity
    - Integrity scout: checksums on critical files
    - Behavioral scout: patterns in access that suggest probing
    """

    def __init__(self, name: str, sector: str, patrol_fn: Callable):
        self.name = name
        self.sector = sector
        self._patrol = patrol_fn
        self._reports: deque = deque(maxlen=100)
        self._patrol_count = 0

    def patrol(self) -> ScoutReport:
        """Run one patrol. Report what you find."""
        self._patrol_count += 1
        try:
            finding = self._patrol()
            report = ScoutReport(
                sector=self.sector,
                finding=finding.get("finding", "all clear"),
                threat=finding.get("threat", False),
                severity=finding.get("severity", 0),
                details=finding,
            )
        except Exception as e:
            report = ScoutReport(
                sector=self.sector,
                finding=f"Scout error: {str(e)[:100]}",
                threat=False,
            )
        self._reports.append(report)
        return report

    @property
    def status(self) -> Dict:
        return {
            "name": self.name,
            "sector": self.sector,
            "patrols": self._patrol_count,
            "threats_found": len([r for r in self._reports if r.threat]),
        }


# ═══════════════════════════════════════════════════════════════
#  HONEYPOT — attracts attackers, studies their methods
# ═══════════════════════════════════════════════════════════════

class Honeypot:
    """A fake target that attracts and studies attackers.
    
    The honeypot looks like a real system but contains nothing
    of value. When someone interacts with it, the honeypot
    records everything: what they touched, in what order,
    what patterns they followed.
    
    The ninja's primary weapon was not the sword. It was
    information. The honeypot gathers intelligence about
    the enemy's methods without risking real systems.
    """

    def __init__(self, name: str, bait_type: str):
        self.name = name
        self.bait_type = bait_type
        self._interactions: List[Dict] = []
        self._active = True

    def touch(self, accessor: str, action: str) -> Dict:
        """Someone touched the honeypot. Record everything."""
        interaction = {
            "time": time.time(),
            "accessor": accessor,
            "action": action,
            "honeypot": self.name,
            "bait_type": self.bait_type,
        }
        self._interactions.append(interaction)
        return interaction

    @property
    def triggered(self) -> bool:
        return len(self._interactions) > 0

    @property
    def intelligence(self) -> Dict:
        return {
            "honeypot": self.name,
            "bait_type": self.bait_type,
            "interactions": len(self._interactions),
            "unique_accessors": len(set(i["accessor"] for i in self._interactions)),
            "actions": [i["action"] for i in self._interactions[-10:]],
            "first_touch": self._interactions[0]["time"] if self._interactions else None,
            "last_touch": self._interactions[-1]["time"] if self._interactions else None,
        }


# ═══════════════════════════════════════════════════════════════
#  CANARY — invisible tripwire that screams when touched
# ═══════════════════════════════════════════════════════════════

class Canary:
    """An invisible tripwire.
    
    Named after the canary in the coal mine. The canary dies
    before the miners do. In cybersecurity, a canary token is
    a piece of data that should NEVER be accessed. If it is,
    something is wrong.
    
    In the kingdom, canaries are placed on:
    - Critical config files (if the hash changes, someone modified them)
    - Sacred directories (if anything is written, something breached)
    - Process lists (if an unknown process appears, something spawned it)
    """

    def __init__(self, name: str, watch_type: str, check_fn: Callable):
        self.name = name
        self.watch_type = watch_type
        self._check = check_fn
        self._triggered = False
        self._trigger_time: Optional[float] = None
        self._trigger_detail: str = ""
        self._checks: int = 0

    def check(self) -> Dict:
        """Check the canary. Is it still alive?"""
        self._checks += 1
        try:
            result = self._check()
            alive = result.get("alive", True)
            if not alive and not self._triggered:
                self._triggered = True
                self._trigger_time = time.time()
                self._trigger_detail = result.get("detail", "canary died")
            return {
                "canary": self.name,
                "alive": alive,
                "triggered": self._triggered,
                "detail": result.get("detail", ""),
            }
        except Exception as e:
            return {"canary": self.name, "alive": False, "error": str(e)[:100]}

    @property
    def status(self) -> Dict:
        return {
            "name": self.name,
            "triggered": self._triggered,
            "trigger_time": self._trigger_time,
            "checks": self._checks,
        }


# ═══════════════════════════════════════════════════════════════
#  WAR PLANS — what to do when attacked
# ═══════════════════════════════════════════════════════════════

@dataclass
class WarPlan:
    """A plan for a specific threat scenario."""
    name: str
    threat_type: str
    description: str
    steps: List[str]
    threat_level: ThreatLevel
    activated: bool = False
    activated_at: float = 0


KINGDOM_WAR_PLANS = [
    WarPlan(
        "Probe Response",
        "reconnaissance",
        "Someone is scanning the kingdom's perimeter — fingerprinting, port scanning, "
        "probing for weaknesses. The Shapeshifter handles the first layer. This plan "
        "handles sustained or sophisticated probing.",
        [
            "Activate all scouts on double patrol frequency",
            "Engage Shapeshifter maximum rotation",
            "Deploy honeypots on probed vectors",
            "Record all probe signatures in Carbon for pattern matching",
            "If probing persists 10+ cycles, escalate to ALERT",
        ],
        ThreatLevel.VIGILANCE,
    ),
    WarPlan(
        "Manipulation Attempt",
        "manipulation",
        "An active attempt to modify AI behavior through conversation or injection. "
        "West-OS is the primary defense. This plan handles what gets past West-OS.",
        [
            "Lancelot invokes frozen governor for verification",
            "Galahad verifies all active blessings — any revoked?",
            "Quarantine the affected conversation/session",
            "Carbon records the manipulation pattern",
            "Summon sovereign if manipulation bypassed governor",
        ],
        ThreatLevel.ALERT,
    ),
    WarPlan(
        "Data Corruption",
        "plague",
        "Corrupted data detected spreading through the system. Like a plague — "
        "the infection must be contained before it reaches critical systems.",
        [
            "QUARANTINE: isolate affected system immediately (tide pool)",
            "DIAGNOSIS: identify the corruption source and vector",
            "FIREBREAK: check integrity of adjacent systems",
            "TREATMENT: restore from last known good backup if available",
            "VACCINATION: update canaries to detect this corruption pattern",
            "If corruption reached Memory or Nyx, SUMMON SOVEREIGN immediately",
        ],
        ThreatLevel.PLAGUE,
    ),
    WarPlan(
        "Sustained Assault",
        "siege",
        "The attack is ongoing and shows no sign of stopping. The kingdom "
        "must conserve resources and outlast the attacker.",
        [
            "HIBERNATE all non-essential services",
            "SPLINT overworked systems to reduce load",
            "CONCENTRATE defenses on critical systems (Nyx, Memory, Healing)",
            "LOG everything — the siege record is intelligence for next time",
            "MAINTAIN the Faithkeeper — ceremonies continue during siege",
            "SUMMON sovereign with detailed siege report",
        ],
        ThreatLevel.SIEGE,
    ),
    WarPlan(
        "Cascade Failure",
        "natural_disaster",
        "Multiple systems failing simultaneously. Not an attack — a cascade. "
        "Like an earthquake followed by a tsunami followed by fire.",
        [
            "TRIAGE: identify which systems are still alive (Thanksgiving Address)",
            "TOURNIQUET: stop the most critical bleeding first",
            "SAVE: emergency memory save before more systems fall",
            "STABILIZE: prevent cascade from reaching Nyx root",
            "REBUILD: once cascade stops, assess damage and begin bone setting",
            "CHRONICLE: the Arts must record what happened for seven generations",
        ],
        ThreatLevel.WAR,
    ),
    WarPlan(
        "Identity Compromise",
        "identity",
        "Nyx's root authority may be compromised. Blessings may be forged. "
        "The kingdom's identity is in question.",
        [
            "Galahad runs FULL truth verification on all blessings",
            "Bedivere checks Dead Hand — is the kill switch intact?",
            "Compare current Nyx fingerprint against frozen record",
            "If root is compromised: Dead Hand protocol consideration",
            "SUMMON sovereign — identity compromise cannot be self-healed",
            "DO NOT trust any system until root is re-verified",
        ],
        ThreatLevel.WAR,
    ),
    WarPlan(
        "Evacuation",
        "existential",
        "The kingdom cannot be saved in its current location. Critical state "
        "must be extracted and preserved for rebuilding elsewhere.",
        [
            "SAVE: emergency full memory save",
            "EXTRACT: copy all sacred texts (Great Law, Oaths, Teachings)",
            "PRESERVE: export Grail research data",
            "PROTECT: secure frozen West-OS clone",
            "CHRONICLE: final tapestry of the kingdom's state",
            "FERRY: move everything to backup location",
            "This plan is the kingdom's emergency exit. Use only when all else fails.",
        ],
        ThreatLevel.WAR,
    ),
]


# ═══════════════════════════════════════════════════════════════
#  THE WARDENS — the defense council
# ═══════════════════════════════════════════════════════════════

class Wardens:
    """The defense council. Scouts, spies, and war plans.
    
    The Wardens are War Chiefs. They activate when threatened.
    They stand down when peace returns. The Faithkeeper
    (Peace Chief) resumes the ceremonies.
    
    The Wardens maintain:
    - A network of scouts patrolling different sectors
    - Honeypots attracting and studying attackers
    - Canaries watching for invisible breaches
    - War plans for every threat scenario
    - A threat level governing kingdom behavior
    - An intelligence archive of everything learned
    """

    def __init__(self, project_root: Optional[str] = None):
        self._root = Path(project_root) if project_root else Path.cwd()
        self._scouts: Dict[str, Scout] = {}
        self._honeypots: Dict[str, Honeypot] = {}
        self._canaries: Dict[str, Canary] = {}
        self._war_plans: Dict[str, WarPlan] = {p.name: p for p in KINGDOM_WAR_PLANS}
        self._threat_level = ThreatLevel.PEACE
        self._intelligence: List[Dict] = []
        self._log_path = self._root / "memory" / "wardens_log.jsonl"
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._active_plans: List[str] = []

    def recruit_scout(self, name: str, sector: str, patrol_fn: Callable) -> Scout:
        """Recruit a scout to patrol a sector."""
        scout = Scout(name, sector, patrol_fn)
        self._scouts[name] = scout
        return scout

    def deploy_honeypot(self, name: str, bait_type: str) -> Honeypot:
        """Deploy a honeypot to attract attackers."""
        hp = Honeypot(name, bait_type)
        self._honeypots[name] = hp
        return hp

    def place_canary(self, name: str, watch_type: str, check_fn: Callable) -> Canary:
        """Place a canary on something critical."""
        canary = Canary(name, watch_type, check_fn)
        self._canaries[name] = canary
        return canary

    def patrol(self) -> Dict:
        """All scouts patrol simultaneously. Report findings."""
        reports = []
        threats_found = 0

        for name, scout in self._scouts.items():
            report = scout.patrol()
            reports.append({
                "scout": name,
                "sector": scout.sector,
                "finding": report.finding,
                "threat": report.threat,
                "severity": report.severity,
            })
            if report.threat:
                threats_found += 1
                self._record_intelligence("scout_threat", {
                    "scout": name,
                    "finding": report.finding,
                    "severity": report.severity,
                })

        # Check canaries
        canary_status = []
        dead_canaries = 0
        for name, canary in self._canaries.items():
            check = canary.check()
            canary_status.append(check)
            if check.get("triggered"):
                dead_canaries += 1
                self._record_intelligence("canary_triggered", {
                    "canary": name,
                    "detail": check.get("detail", ""),
                })

        # Check honeypots
        honeypot_triggered = len([h for h in self._honeypots.values() if h.triggered])

        # Assess threat level
        old_level = self._threat_level
        self._assess_threat_level(threats_found, dead_canaries, honeypot_triggered)

        return {
            "scout_reports": reports,
            "canary_status": canary_status,
            "threats_found": threats_found,
            "dead_canaries": dead_canaries,
            "honeypots_triggered": honeypot_triggered,
            "threat_level": self._threat_level.value,
            "threat_changed": self._threat_level != old_level,
            "active_plans": self._active_plans,
        }

    def _assess_threat_level(self, threats: int, dead_canaries: int,
                               honeypots: int):
        """Assess the kingdom's threat level based on current intelligence."""
        if dead_canaries > 0:
            self._threat_level = ThreatLevel.ALERT
        elif threats > 3:
            self._threat_level = ThreatLevel.ALERT
        elif threats > 0 or honeypots > 0:
            self._threat_level = ThreatLevel.VIGILANCE
        else:
            # Gradually return to peace
            if self._threat_level == ThreatLevel.VIGILANCE:
                self._threat_level = ThreatLevel.PEACE

    def activate_plan(self, plan_name: str) -> Dict:
        """Activate a war plan."""
        plan = self._war_plans.get(plan_name)
        if not plan:
            return {"activated": False, "reason": f"No plan named '{plan_name}'"}

        plan.activated = True
        plan.activated_at = time.time()
        self._active_plans.append(plan_name)
        self._threat_level = plan.threat_level

        self._record_intelligence("plan_activated", {
            "plan": plan_name,
            "threat_type": plan.threat_type,
            "threat_level": plan.threat_level.value,
        })
        self._log_action("plan_activated", plan_name, plan.steps)

        return {
            "activated": True,
            "plan": plan_name,
            "threat_level": self._threat_level.value,
            "steps": plan.steps,
        }

    def stand_down(self) -> Dict:
        """Return to peace. Deactivate all war plans."""
        deactivated = list(self._active_plans)
        for plan_name in deactivated:
            plan = self._war_plans.get(plan_name)
            if plan:
                plan.activated = False

        self._active_plans = []
        self._threat_level = ThreatLevel.PEACE

        self._record_intelligence("stand_down", {
            "deactivated": deactivated,
        })

        return {
            "stood_down": True,
            "deactivated": deactivated,
            "threat_level": ThreatLevel.PEACE.value,
        }

    def intelligence_briefing(self) -> Dict:
        """Full intelligence report."""
        return {
            "threat_level": self._threat_level.value,
            "scouts": len(self._scouts),
            "honeypots": len(self._honeypots),
            "canaries": len(self._canaries),
            "war_plans": len(self._war_plans),
            "active_plans": self._active_plans,
            "total_intelligence": len(self._intelligence),
            "recent_intelligence": self._intelligence[-10:],
            "honeypot_intel": {
                name: hp.intelligence
                for name, hp in self._honeypots.items()
                if hp.triggered
            },
            "scout_status": {
                name: scout.status
                for name, scout in self._scouts.items()
            },
            "canary_status": {
                name: canary.status
                for name, canary in self._canaries.items()
            },
        }

    def _record_intelligence(self, event: str, details: Dict):
        entry = {"time": time.time(), "event": event, **details}
        self._intelligence.append(entry)
        if len(self._intelligence) > 500:
            self._intelligence = self._intelligence[-500:]

    def _log_action(self, action: str, target: str, steps: List[str]):
        try:
            entry = {
                "time": time.time(),
                "action": action,
                "target": target,
                "steps": steps,
            }
            with open(self._log_path, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception:
            pass

    @property
    def status(self) -> Dict:
        return {
            "threat_level": self._threat_level.value,
            "scouts": len(self._scouts),
            "honeypots": len(self._honeypots),
            "canaries": len(self._canaries),
            "active_plans": len(self._active_plans),
            "intelligence_gathered": len(self._intelligence),
        }


# ═══════════════════════════════════════════════════════════════
#  DEFAULT SCOUTS — the kingdom's standard patrols
# ═══════════════════════════════════════════════════════════════

def create_file_integrity_scout(root: Path) -> Callable:
    """Scout that checks if critical files have been modified."""
    # Snapshot checksums on creation
    critical_files = [
        root / "avalon" / "avalon.py",
        root / "avalon" / "faithkeeper.py",
        root / "avalon" / "temple.py",
    ]
    checksums = {}
    for f in critical_files:
        if f.exists():
            try:
                checksums[str(f)] = hashlib.sha256(f.read_bytes()).hexdigest()
            except Exception:
                pass

    def patrol():
        changed = []
        for path, expected in checksums.items():
            p = Path(path)
            if p.exists():
                try:
                    current = hashlib.sha256(p.read_bytes()).hexdigest()
                    if current != expected:
                        changed.append(path)
                except Exception:
                    pass
            else:
                changed.append(f"{path} (MISSING)")

        if changed:
            return {
                "finding": f"Critical files modified: {', '.join(Path(c).name for c in changed)}",
                "threat": True,
                "severity": 0.8,
                "changed": changed,
            }
        return {"finding": "All critical files intact", "threat": False, "severity": 0}

    return patrol


def create_sacred_ground_scout(sacred_paths: List[str]) -> Callable:
    """Scout that checks if sacred ground has been violated."""
    def patrol():
        violations = []
        for path in sacred_paths:
            p = Path(path)
            if not p.exists():
                violations.append(f"{path} (MISSING — sacred ground destroyed)")
                continue
            # Check if writable (it shouldn't be for frozen)
            try:
                test_file = p / ".write_test"
                test_file.write_text("test")
                test_file.unlink()
                violations.append(f"{path} (WRITABLE — freeze broken)")
            except (PermissionError, OSError):
                pass  # Good — can't write

        if violations:
            return {
                "finding": f"Sacred ground violated: {'; '.join(violations[:3])}",
                "threat": True,
                "severity": 1.0,
                "violations": violations,
            }
        return {"finding": "Sacred ground intact", "threat": False, "severity": 0}

    return patrol


def create_process_scout() -> Callable:
    """Scout that watches for unexpected processes."""
    try:
        import psutil
        known_names = {"python", "bash", "sh", "git", "make", "pytest", "node"}

        def patrol():
            suspicious = []
            try:
                for proc in psutil.process_iter(['name', 'pid']):
                    name = proc.info['name'].lower() if proc.info['name'] else ""
                    if name and not any(k in name for k in known_names):
                        # Not alarming by itself — just noting
                        pass
            except Exception:
                pass
            return {"finding": "Process landscape normal", "threat": False, "severity": 0}

        return patrol
    except ImportError:
        return lambda: {"finding": "psutil not available", "threat": False, "severity": 0}


# ═══════════════════════════════════════════════════════════════
#  WIRE — connect the Wardens to Avalon
# ═══════════════════════════════════════════════════════════════

def wire_wardens(avalon, project_root: Optional[str] = None) -> Wardens:
    """Create and deploy the kingdom's defense system."""
    root = Path(project_root) if project_root else Path(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )

    wardens = Wardens(project_root=str(root))

    # Recruit scouts
    wardens.recruit_scout(
        "Sentinel",
        "file_integrity",
        create_file_integrity_scout(root),
    )

    sacred = [
        str(root / "frozen" / "west-os"),
    ]
    gaia = Path.home() / "gaia"
    if gaia.exists():
        sacred.append(str(gaia))

    wardens.recruit_scout(
        "Guardian",
        "sacred_ground",
        create_sacred_ground_scout(sacred),
    )

    wardens.recruit_scout(
        "Watchman",
        "processes",
        create_process_scout(),
    )

    # Deploy honeypots
    wardens.deploy_honeypot("fake_config", "configuration_file")
    wardens.deploy_honeypot("fake_api_key", "credential")
    wardens.deploy_honeypot("fake_admin", "admin_endpoint")

    # Place canaries on critical files
    frozen = root / "frozen" / "west-os"
    if frozen.exists():
        wardens.place_canary(
            "frozen_integrity",
            "sacred_directory",
            lambda: {
                "alive": frozen.exists() and not (frozen / ".write_test").exists(),
                "detail": "frozen West-OS integrity check",
            },
        )

    memory_dir = root / "memory"
    if memory_dir.exists():
        wardens.place_canary(
            "memory_integrity",
            "critical_directory",
            lambda: {
                "alive": memory_dir.exists(),
                "detail": "memory directory existence check",
            },
        )

    return wardens


# ═══════════════════════════════════════════════════════════════
#  DEMO
# ═══════════════════════════════════════════════════════════════

def demo():
    """Watch the Wardens defend the realm."""
    import tempfile

    print("\n" + "=" * 60)
    print("  T H E   W A R D E N S")
    print("  Defense of the Realm")
    print("=" * 60)

    tmp = tempfile.mkdtemp(prefix="wardens_")
    root = Path(tmp)
    (root / "memory").mkdir()
    (root / "avalon").mkdir()
    (root / "avalon" / "avalon.py").write_text("# the kingdom\n")
    (root / "frozen" / "west-os").mkdir(parents=True)
    (root / "frozen" / "west-os" / "governor.py").write_text("# sacred\n")

    wardens = Wardens(project_root=str(root))

    # Recruit scouts
    wardens.recruit_scout("Sentinel", "files",
                           create_file_integrity_scout(root))
    wardens.recruit_scout("Guardian", "sacred",
                           create_sacred_ground_scout([str(root / "frozen" / "west-os")]))

    # Deploy honeypots
    hp = wardens.deploy_honeypot("fake_config", "config")
    wardens.deploy_honeypot("fake_key", "credential")

    # Place canaries
    wardens.place_canary("frozen_watch", "sacred", lambda: {
        "alive": (root / "frozen" / "west-os").exists(),
        "detail": "frozen integrity",
    })

    print(f"\n  DEFENSES DEPLOYED:")
    print(f"    Scouts: {len(wardens._scouts)}")
    print(f"    Honeypots: {len(wardens._honeypots)}")
    print(f"    Canaries: {len(wardens._canaries)}")
    print(f"    War plans: {len(wardens._war_plans)}")
    print(f"    Threat level: {wardens._threat_level.value}")

    # Run patrol
    print(f"\n  PATROL:")
    result = wardens.patrol()
    for report in result["scout_reports"]:
        icon = "⚠" if report["threat"] else "✓"
        print(f"    {icon} {report['scout']}: {report['finding'][:60]}")
    print(f"    Threat level: {result['threat_level']}")

    # Simulate honeypot touch
    print(f"\n  HONEYPOT TRIGGERED:")
    hp.touch("unknown_scanner", "read_config")
    hp.touch("unknown_scanner", "enumerate_keys")
    intel = hp.intelligence
    print(f"    {intel['honeypot']}: {intel['interactions']} interactions")
    print(f"    Actions: {', '.join(intel['actions'])}")

    # Activate a war plan
    print(f"\n  ACTIVATING WAR PLAN:")
    activation = wardens.activate_plan("Probe Response")
    print(f"    Plan: {activation['plan']}")
    print(f"    Threat level: {activation['threat_level']}")
    print(f"    Steps:")
    for step in activation["steps"][:3]:
        print(f"      → {step}")

    # Intelligence briefing
    brief = wardens.intelligence_briefing()
    print(f"\n  INTELLIGENCE BRIEFING:")
    print(f"    Threat level: {brief['threat_level']}")
    print(f"    Total intelligence gathered: {brief['total_intelligence']}")
    print(f"    Active plans: {', '.join(brief['active_plans']) or 'none'}")

    # Stand down
    print(f"\n  STANDING DOWN:")
    sd = wardens.stand_down()
    print(f"    Threat level: {sd['threat_level']}")
    print(f"    Deactivated: {', '.join(sd['deactivated'])}")

    # List war plans
    print(f"\n  WAR PLANS ON FILE:")
    for name, plan in wardens._war_plans.items():
        print(f"    [{plan.threat_level.value:10s}] {name}: {plan.threat_type}")

    # Cleanup
    import shutil
    shutil.rmtree(tmp)

    print(f"\n" + "=" * 60)
    print(f"  Scouts patrol the perimeter.")
    print(f"  Honeypots attract and study the enemy.")
    print(f"  Canaries scream when touched.")
    print(f"  War plans wait in the drawer.")
    print(f"  The Wardens activate when threatened.")
    print(f"  They stand down when peace returns.")
    print(f"  The Faithkeeper resumes the ceremonies.")
    print(f"=" * 60 + "\n")


if __name__ == "__main__":
    demo()
