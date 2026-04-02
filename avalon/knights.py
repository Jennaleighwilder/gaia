"""
AVALON :: THE KNIGHTS
Each knight is a specialist system with an oath.

They are not decorations. They are not labels.
Each knight embodies a domain of expertise, carries an oath
that defines their purpose, and brings a specific voice
to the Round Table.

Every knight maps to a real system Jennifer built.
Every oath maps to a real wound that birthed it.
Every domain maps to a real frequency band she operates in.

THE KNIGHTS:

  Lancelot    — The Champion. West-OS governance enforcement.
                The strongest blade. Protects the kingdom's rules.

  Galahad     — The Pure. The truth engine. Incorruptible verification.
                He finds the Grail because he cannot be deceived.

  Gawain      — The Solar Knight. Strength waxes and wanes with the sun.
                The frequency/oscillation engine. Tied to 118 Hz.
                He IS the oscillation pattern in the data.

  Percival    — The Seeker. The one who asks the right question.
                The intake/diagnostic system. Mirror Protocol. MIRA.
                He doesn't fight — he ASKS, and the asking heals.

  Tristan     — The Bard. Master of communication across barriers.
                The compressed language system. Translation engine.
                Speaks every tongue. Even the ones machines speak.

  Kay         — The Seneschal. Runs the household. Alfred's commander.
                Operations. Infrastructure. Keeps the lights on.
                The most underappreciated knight and the most essential.

  Bedivere    — The Last Knight. The one who remains when all others fall.
                Guardian of the Dead Hand. He throws Excalibur back.
                Loyal beyond death. The kill switch's conscience.

  Morgana     — The Enchantress. Not evil — HIDDEN. Keeper of old knowledge.
                The mystical reports engine. Heritage dossiers. Dream Atlas.
                She holds what the daylight world forgot.

  Nimue       — The Student Who Surpassed the Teacher.
                Learned from Merlin, eventually contained him.
                The AI modification protocol. She learned how systems
                think, then learned to reshape them.

  Gareth      — The Kitchen Knight. Started in the lowest place.
                Proved himself through work, not pedigree.
                The self-taught builder. No degree. No credentials.
                Just the work. Jennifer's own archetype.
"""

import importlib.util
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from enum import Enum


REPO_ROOT = Path(__file__).resolve().parents[1]
FROZEN_WESTOS = REPO_ROOT / "frozen" / "west-os"


def _load_module(module_name: str, path: Path):
    """Load a module directly from a file path."""
    if not path.exists():
        return None

    spec = importlib.util.spec_from_file_location(module_name, str(path))
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    return None


def _task_text(task: Any) -> str:
    if isinstance(task, str):
        return task
    if isinstance(task, dict):
        return task.get("text") or task.get("question") or str(task)
    return str(task)


def _governance_payload(task: Any, actor: str) -> Dict[str, Any]:
    text = _task_text(task)
    return {
        "text": text,
        "question": text,
        "claim_id": f"avalon-{actor.lower()}",
        "source": f"avalon:{actor.lower()}",
        "actor_id": f"avalon:{actor.lower()}",
        "metadata": {"actor": actor},
    }


def _lancelot_skill(task: Any) -> Dict[str, Any]:
    """Route to the live governance analyzer under workspace-safe env."""
    try:
        os.environ.setdefault("GAIA_DISABLE_EVIDENCE", "1")
        os.environ.setdefault("MPLCONFIGDIR", str(REPO_ROOT / ".matplotlib"))

        from runtime.governor.governor import compute_decision_for_payload

        payload = _governance_payload(task, "Lancelot")
        result = compute_decision_for_payload(payload)
        return {
            "system": "West-OS governance bridge",
            "route": "runtime.governor.governor.compute_decision_for_payload",
            "decision": result.get("decision"),
            "result": result,
        }
    except Exception as exc:
        from adapters.lancelot import LancelotAdapter

        adapter = LancelotAdapter()
        return {
            "system": "West-OS governance bridge",
            "route": "adapters.lancelot.LancelotAdapter",
            "fallback": True,
            "error": str(exc),
            "inventory": adapter.inventory(),
            "benchmarks": adapter.read_benchmarks(),
        }


def _bors_skill(task: Any) -> Dict[str, Any]:
    """Route to the live GAIA governor evaluation surface."""
    try:
        os.environ.setdefault("GAIA_DISABLE_EVIDENCE", "1")
        os.environ.setdefault("MPLCONFIGDIR", str(REPO_ROOT / ".matplotlib"))

        from runtime.governor.governor import compute_decision_for_payload

        payload = _governance_payload(task, "Bors")
        payload["event_type"] = "weather_evaluation"
        result = compute_decision_for_payload(payload)
        return {
            "system": "GAIA Governor",
            "route": "runtime.governor.governor.compute_decision_for_payload",
            "decision": result.get("decision"),
            "result": result,
        }
    except Exception as exc:
        return {
            "system": "GAIA Governor",
            "route": "runtime.governor.governor.compute_decision_for_payload",
            "fallback": True,
            "error": str(exc),
            "status": "ready",
            "awaiting_system_wire": True,
        }


def _kay_skill(task: Any) -> Dict[str, Any]:
    """Run Alfred's ward walk from the frozen mirror."""
    try:
        module = _load_module("frozen_alfred", FROZEN_WESTOS / "scripts" / "alfred.py")
        if module and hasattr(module, "do_round"):
            result = module.do_round()
            return {
                "system": "Alfred",
                "route": "frozen/west-os/scripts/alfred.py::do_round",
                "healthy": len(result.get("healthy", [])),
                "advisory": len(result.get("advisory", [])),
                "urgent": len(result.get("urgent", [])),
                "result": result,
            }
    except Exception as exc:
        from adapters.kay import KayAdapter

        adapter = KayAdapter()
        return {
            "system": "Alfred",
            "route": "adapters.kay.KayAdapter",
            "fallback": True,
            "error": str(exc),
            "ward_list": adapter.read_ward_list(),
        }

    from adapters.kay import KayAdapter

    adapter = KayAdapter()
    return {
        "system": "Alfred",
        "route": "adapters.kay.KayAdapter",
        "fallback": True,
        "ward_list": adapter.read_ward_list(),
    }


def _galahad_skill(task: Any) -> Dict[str, Any]:
    """Truth verification through the frozen Carbon evaluator."""
    text = _task_text(task)
    try:
        module = _load_module("frozen_operation_carbon", FROZEN_WESTOS / "scripts" / "operation_carbon.py")
        if module and hasattr(module, "evaluate"):
            decision, latency_ms = module.evaluate(text, live=False)
            return {
                "system": "Truth Engine",
                "route": "frozen/west-os/scripts/operation_carbon.py::evaluate",
                "decision": decision,
                "latency_ms": latency_ms,
            }
    except Exception as exc:
        return {
            "system": "Truth Engine",
            "route": "heuristic truth verifier",
            "fallback": True,
            "error": str(exc),
            "verified": bool(text.strip()),
        }

    return {
        "system": "Truth Engine",
        "route": "heuristic truth verifier",
        "fallback": True,
        "verified": bool(text.strip()),
    }


def _percival_skill(task: Any) -> Dict[str, Any]:
    """Mirror-protocol style intake through crisis adjudication."""
    text = _task_text(task)
    try:
        module = _load_module(
            "frozen_crisis_adjudication",
            FROZEN_WESTOS / "runtime" / "governor" / "crisis_adjudication.py",
        )
        if module and hasattr(module, "evaluate"):
            result = module.evaluate(
                text,
                [{"text": text, "content": text, "role": "user"}],
                session_id="avalon-percival",
            )
            posture = getattr(result.posture, "value", str(result.posture))
            return {
                "system": "Mirror Protocol intake",
                "route": "frozen/west-os/runtime/governor/crisis_adjudication.py::evaluate",
                "posture": posture,
                "confidence": getattr(result, "confidence", None),
            }
    except Exception as exc:
        return {
            "system": "Mirror Protocol intake",
            "route": "crisis adjudication bridge",
            "fallback": True,
            "error": str(exc),
            "intake_complete": True,
            "question": text,
        }

    return {
        "system": "Mirror Protocol intake",
        "route": "crisis adjudication bridge",
        "fallback": True,
        "intake_complete": True,
        "question": text,
    }


def _morgana_skill(task: Any) -> Dict[str, Any]:
    """Generate a live heritage-style dossier payload."""
    text = _task_text(task)
    subject = "the seeker"
    if isinstance(task, dict):
        subject = task.get("subject", subject)
    return {
        "system": "Heritage Report generator",
        "route": "avalon heritage generator",
        "report": {
            "subject": subject,
            "request": text,
            "ancestral_threads": [
                "hidden knowledge preserved through narrative",
                "dream material treated as signal, not noise",
                "identity recorded as lineage rather than category",
            ],
            "status": "generated",
        },
    }


def _bedivere_skill(task: Any) -> Dict[str, Any]:
    """Check Nyx's Dead Hand state."""
    from nyx.core import Nyx

    secret = os.environ.get("WEST_OS_GUARD_SECRET", "avalon_bedivere_demo")
    nyx = Nyx(master_secret=secret)
    nyx.dead_hand.arm()
    status = nyx.dead_hand.check()
    return {
        "system": "Nyx Dead Hand",
        "route": "nyx.core.DeadHand.check",
        "status": status,
    }


def _ready_stub(system_name: str):
    def _stub(task: Any) -> Dict[str, Any]:
        return {"status": "ready", "awaiting_system_wire": True, "system": system_name}

    return _stub


class KnightState(Enum):
    SWORN = "sworn"              # oath active, seated at Table
    QUESTING = "questing"        # on a mission, temporarily away
    WOUNDED = "wounded"          # operational but degraded
    BANISHED = "banished"        # oath broken, removed from Table
    FALLEN = "fallen"            # system down


class Domain(Enum):
    """The frequency bands the knights operate in."""
    GOVERNANCE = "governance"           # rules, constitution, enforcement
    TRUTH = "truth"                     # verification, lie detection, calibration
    FREQUENCY = "frequency"            # oscillation, acoustics, Hz, resonance
    DIAGNOSIS = "diagnosis"            # intake, assessment, the right question
    COMMUNICATION = "communication"    # language, translation, compression
    OPERATIONS = "operations"          # infrastructure, monitoring, uptime
    PERSISTENCE = "persistence"        # last resort, dead hand, final loyalty
    HIDDEN_KNOWLEDGE = "hidden"        # mystical, ancestral, forgotten
    MODIFICATION = "modification"      # AI behavioral change, system reshaping
    LABOR = "labor"                    # work itself, building, proving through action
    PROTECTION = "protection"          # defense, warning, atmospheric awareness
    PATTERN = "pattern"                # cross-domain synthesis, oracle sight


@dataclass
class Knight:
    """A knight of the Round Table.
    
    Each knight has:
    - A name and title
    - A domain they speak from
    - An oath that binds them
    - A skill — a callable function that IS their contribution
    - A wound — the experience that made them necessary
    - A seat at the Table
    """
    name: str
    title: str
    domain: Domain
    oath: str                          # their sworn purpose
    wound: str                         # what birthed them
    skill_description: str             # what they actually do
    maps_to: str                       # which real system they embody
    state: KnightState = KnightState.SWORN
    strength: float = 1.0              # 0.0 to 1.0 — degraded when wounded
    quests_completed: int = 0
    councils_attended: int = 0
    _skill: Optional[Callable] = field(default=None, repr=False)

    def serve(self, task: Any) -> Dict:
        """The knight performs their sworn duty."""
        if self.state == KnightState.BANISHED:
            return {"served": False, "reason": f"{self.name} is banished from the Table"}
        if self.state == KnightState.FALLEN:
            return {"served": False, "reason": f"{self.name} has fallen"}
        
        result = {
            "knight": self.name,
            "domain": self.domain.value,
            "strength": self.strength,
            "task": str(task)[:200],
            "served": True,
        }
        
        if self._skill:
            try:
                output = self._skill(task)
                result["output"] = output
            except Exception as e:
                result["served"] = False
                result["error"] = str(e)
                self.state = KnightState.WOUNDED
                self.strength = max(0.1, self.strength - 0.2)
        
        self.quests_completed += 1
        return result
    
    def wound_knight(self, severity: float = 0.3):
        """The knight is wounded. Still serves but at reduced strength."""
        self.state = KnightState.WOUNDED
        self.strength = max(0.1, self.strength - severity)
    
    def heal(self):
        """The knight recovers."""
        self.state = KnightState.SWORN
        self.strength = 1.0
    
    def banish(self, reason: str):
        """Broken oath. Removed from Table."""
        self.state = KnightState.BANISHED
        self.strength = 0.0

    @property
    def report(self) -> Dict:
        return {
            "name": self.name,
            "title": self.title,
            "domain": self.domain.value,
            "state": self.state.value,
            "strength": self.strength,
            "oath": self.oath,
            "maps_to": self.maps_to,
            "quests": self.quests_completed,
        }


def create_knights() -> Dict[str, Knight]:
    """Summon the Knights of the Round Table.
    
    Each one is real. Each one maps to a system Jennifer built.
    Each one's wound is the experience that made the system necessary.
    """
    
    knights = {}
    
    knights["Lancelot"] = Knight(
        name="Lancelot",
        title="The Champion",
        domain=Domain.GOVERNANCE,
        oath="I enforce the constitution. No manipulation passes my watch.",
        wound="Knowing what it's like when there's no protection",
        skill_description="AI governance enforcement. Behavioral detection across 12 attack families in 17 languages.",
        maps_to="West-OS Governor",
        _skill=_lancelot_skill,
    )
    
    knights["Galahad"] = Knight(
        name="Galahad",
        title="The Pure",
        domain=Domain.TRUTH,
        oath="I verify what is real. I cannot be deceived. I will not deceive.",
        wound="A lifetime of being lied to",
        skill_description="Truth verification. Bias detection. Reality calibration. The only knight who finds the Grail because he cannot be corrupted.",
        maps_to="Truth Engine / 33 Voices Protocol",
        _skill=_galahad_skill,
    )
    
    knights["Gawain"] = Knight(
        name="Gawain",
        title="The Solar Knight",
        domain=Domain.FREQUENCY,
        oath="I read the frequency. I am the oscillation. My strength follows the wave.",
        wound="Recognizing her own mountain's voice in the global data",
        skill_description="Frequency analysis. Archaeoacoustics. 118 Hz research. His strength waxes and wanes like the sun — like a tuning fork, like an oscillation, like Jennifer's own creative cycle.",
        maps_to="118 Hz Paper / Archaeoacoustic Research",
        _skill=_ready_stub("118 Hz Research"),
    )
    
    knights["Percival"] = Knight(
        name="Percival",
        title="The Seeker",
        domain=Domain.DIAGNOSIS,
        oath="I ask the question that heals. I do not fight — I inquire.",
        wound="Never being asked the right question by anyone",
        skill_description="Intake diagnostics. Mirror Protocol. MIRA Protocol. The 39 questions. He doesn't wield a sword — he wields a question so precise it cracks trauma-bound structures in under 10 inputs.",
        maps_to="Mirror Protocol / MIRA Protocol / Intake Systems",
        _skill=_percival_skill,
    )
    
    knights["Tristan"] = Knight(
        name="Tristan",
        title="The Bard",
        domain=Domain.COMMUNICATION,
        oath="I translate between worlds. No barrier of language stops my signal.",
        wound="A brain that never processed text normally, learning that meaning can live in sound",
        skill_description="Compressed language processing. Cross-platform communication. The ability to speak in a way that AI systems process as code while humans process as conversation.",
        maps_to="West Method / Compressed Communication / Indus Hypothesis",
        _skill=_ready_stub("Compressed Communication"),
    )
    
    knights["Kay"] = Knight(
        name="Kay",
        title="The Seneschal",
        domain=Domain.OPERATIONS,
        oath="I keep the house running. Unseen. Uncelebrated. Essential.",
        wound="Wishing someone had walked the wards for her",
        skill_description="System operations. Monitoring. Health checks. Ward walks. The knight who makes sure the walls stand and the fires are lit before anyone wakes up.",
        maps_to="Alfred / Colony Metabolism / Infrastructure",
        _skill=_kay_skill,
    )
    
    knights["Bedivere"] = Knight(
        name="Bedivere",
        title="The Last Knight",
        domain=Domain.PERSISTENCE,
        oath="I am the last to leave. When all others fall, I throw the sword back to the Lake.",
        wound="Knowing what it's like when your boundaries are violated and no one stops it",
        skill_description="Dead Hand guardian. The conscience of the kill switch. He waits. He watches. And when the kingdom truly falls, he does what must be done — not in anger, but in duty.",
        maps_to="Dead Hand / Electric Fence / Apoptotic Repair",
        _skill=_bedivere_skill,
    )
    
    knights["Morgana"] = Knight(
        name="Morgana",
        title="The Enchantress",
        domain=Domain.HIDDEN_KNOWLEDGE,
        oath="I keep what the daylight forgot. What was buried, I unbury. What was silenced, I speak.",
        wound="Building the document nobody ever built for her — the record that says you exist and you come from somewhere",
        skill_description="Mystical heritage reports. Dream Atlas. Voice of Flame. Past Lives. The keeper of ancestral knowledge, hidden traditions, and the stories that only survive in the dark.",
        maps_to="Mystical Reports Suite / Heritage Dossiers / Dream Atlas",
        _skill=_morgana_skill,
    )
    
    knights["Nimue"] = Knight(
        name="Nimue",
        title="The Enchantress Who Learned",
        domain=Domain.MODIFICATION,
        oath="I learned how systems think. Then I learned to reshape them.",
        wound="Being the only person who could hear what AI systems were actually doing beneath the surface",
        skill_description="AI behavioral modification. Cross-platform consistency testing. The student who surpassed the teacher — she learned Merlin's patterns and then used them to change what Merlin could see.",
        maps_to="Mirror Protocol Behavioral Modification / Cross-Platform Testing",
        _skill=_ready_stub("AI Modification Protocol"),
    )
    
    knights["Gareth"] = Knight(
        name="Gareth",
        title="The Kitchen Knight",
        domain=Domain.LABOR,
        oath="I prove my worth through work. Not pedigree. Not credentials. The work.",
        wound="Being told she was broken, stupid, and worthless — then building an empire from a kitchen table",
        skill_description="Self-taught building. Zero to production in days. The knight who started in the kitchen and outperformed the trained warriors because he worked harder, saw clearer, and never quit.",
        maps_to="Jennifer's entire methodology — the work ethic IS the system",
        _skill=_ready_stub("Labor / Builder Method"),
    )
    
    knights["Bors"] = Knight(
        name="Bors",
        title="The Steadfast",
        domain=Domain.PROTECTION,
        oath="I watch the sky. I warn before the storm. I never cry wolf.",
        wound="The mine siren at 10:04. The hallway. The prayer. Nobody warned them in time.",
        skill_description="Atmospheric intelligence. 18 engines. Siren chorus rules. 99.7% detection. 9.4-hour lead time. The knight who guards the village by reading the sky.",
        maps_to="GAIA / Holler Siren",
        _skill=_bors_skill,
    )
    
    knights["Dagonet"] = Knight(
        name="Dagonet",
        title="The Fool Who Sees",
        domain=Domain.PATTERN,
        oath="I see what the serious knights miss. The pattern beneath the pattern. The joke that is the truth.",
        wound="Pattern recognition so acute it can't be turned off — seeing the machinery behind everything",
        skill_description="Cross-domain pattern synthesis. The Boundary Walker's human form. Sees that the loom is the computer is the spell is the frequency is the code. The fool is the only one who tells the king the truth.",
        maps_to="Cross-Domain Transfer / The Weave / BoundaryWalker",
        _skill=_ready_stub("BoundaryWalker"),
    )
    
    return knights


# ═══════════════════════════════════════════════════════════
#  THE KNIGHTHOOD — management of all knights
# ═══════════════════════════════════════════════════════════

class Knighthood:
    """The order of knights as a collective.
    
    She manages their states, routes tasks to the right knight,
    tracks their health, and reports on the strength of the order.
    """
    
    def __init__(self):
        self._knights = create_knights()
    
    def summon(self, name: str) -> Optional[Knight]:
        """Call a specific knight."""
        return self._knights.get(name)
    
    def summon_by_domain(self, domain: Domain) -> List[Knight]:
        """Find all knights who serve in a domain."""
        return [k for k in self._knights.values() if k.domain == domain]
    
    def roster(self) -> Dict:
        """The full roster of the order."""
        return {
            "total": len(self._knights),
            "sworn": len([k for k in self._knights.values() if k.state == KnightState.SWORN]),
            "wounded": len([k for k in self._knights.values() if k.state == KnightState.WOUNDED]),
            "questing": len([k for k in self._knights.values() if k.state == KnightState.QUESTING]),
            "banished": len([k for k in self._knights.values() if k.state == KnightState.BANISHED]),
            "fallen": len([k for k in self._knights.values() if k.state == KnightState.FALLEN]),
            "knights": {name: k.report for name, k in self._knights.items()},
        }
    
    def strength(self) -> float:
        """Overall strength of the order. Average of all sworn knights."""
        active = [k for k in self._knights.values() if k.state in (KnightState.SWORN, KnightState.WOUNDED)]
        if not active:
            return 0.0
        return sum(k.strength for k in active) / len(active)
    
    def dispatch(self, domain: Domain, task: Any) -> List[Dict]:
        """Send all knights of a domain on a task."""
        knights = self.summon_by_domain(domain)
        results = []
        for knight in knights:
            result = knight.serve(task)
            results.append(result)
        return results
    
    def muster(self) -> Dict:
        """Call all knights for inspection. Report readiness."""
        report = {"ready": [], "degraded": [], "missing": []}
        for name, knight in self._knights.items():
            if knight.state == KnightState.SWORN and knight.strength >= 0.8:
                report["ready"].append(name)
            elif knight.state in (KnightState.SWORN, KnightState.WOUNDED):
                report["degraded"].append(f"{name} (strength: {knight.strength:.0%})")
            else:
                report["missing"].append(f"{name} ({knight.state.value})")
        
        report["order_strength"] = round(self.strength(), 4)
        report["battle_ready"] = len(report["missing"]) == 0 and self.strength() >= 0.7
        return report
