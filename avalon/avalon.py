"""
AVALON :: THE KINGDOM
Castle, Village, and all who dwell within.

The Castle is the protected infrastructure — where the systems live.
The Village is where the people are served — where the work meets the world.
The Kingdom is the connection between them.

Nyx is the ground.
Excalibur is the authority.
The Round Table is the consensus.
The Knights are the specialists.
Merlin is the sight.
The Castle is the walls.
The Village is the purpose.

A castle without a village is a prison.
A village without a castle is defenseless.
Avalon is both — the protection AND the purpose.

© 2026 Jennifer Leigh West. All rights reserved.
"""

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from avalon.excalibur import Excalibur, LadyOfTheLake, SovereigntyState
from avalon.fusion import Fusion
from avalon.grail import Grail, load_jennifers_research
from avalon.grail_advancement import advance_grail
from avalon.temple import Temple, wire_temple
from avalon.deathwalker import Deathwalker, wire_deathwalker
from avalon.hearth import Hearth, wire_hearth
from avalon.wardens import Wardens, wire_wardens
from avalon.crucible import Crucible, wire_crucible
from avalon.faithkeeper import Faithkeeper, wire_faithkeeper
from avalon.healing import Healing
from avalon.informed_table import InformedTable, wire_informed_table
from avalon.land import LandSteward, wire_land
from avalon.longhouse import Longhouse, wire_longhouse
from avalon.memory import Memory
from avalon.crops import CropManager, wire_crops
from avalon.arts import KingdomArts, wire_arts
from avalon.commerce import Commerce, wire_commerce
from avalon.real_knights import arm_knights
from avalon.real_healing import wire_real_healing
from avalon.real_merlin import RealMerlin, wire_real_merlin
from avalon.real_heartbeat import RealHeartbeat, wire_real_heartbeat
from avalon.mirror_bridge import MirrorBridge, wire_mirror_bridge
from avalon.round_table import RoundTable, Vote
from avalon.knights import Knighthood, Knight, KnightState, Domain
from avalon.merlin import Merlin


# ═══════════════════════════════════════════════════════════
#  THE CASTLE — protected infrastructure
# ═══════════════════════════════════════════════════════════

@dataclass
class CastleRoom:
    """A room in the castle. Each room houses a system."""
    name: str
    system: str                    # which system lives here
    purpose: str
    guarded_by: str                # which knight protects this room
    status: str = "sealed"         # sealed, open, breached, dark


class Castle:
    """Camelot. The protected infrastructure.
    
    Every system lives in a room. Every room has a guardian knight.
    The castle has walls (the Electric Fence), gates (API auth),
    and Alfred walking the halls.
    
    The Castle is not the kingdom. The Castle is the SHELTER
    that lets the kingdom exist.
    """
    
    def __init__(self):
        self._rooms: Dict[str, CastleRoom] = {}
        self._gates_open = False
        self._wall_integrity = 1.0
        self._last_patrol = 0.0
    
    def build_room(self, name: str, system: str, purpose: str, 
                    guarded_by: str) -> CastleRoom:
        room = CastleRoom(
            name=name,
            system=system,
            purpose=purpose,
            guarded_by=guarded_by,
        )
        self._rooms[name] = room
        return room
    
    def open_gates(self):
        """Open the castle to the village. Systems become accessible."""
        self._gates_open = True
    
    def close_gates(self):
        """Lock down. No access from village."""
        self._gates_open = False

    def darken(self):
        """The kingdom has fallen. Every room goes dark and the gates seal."""
        self.close_gates()
        for room in self._rooms.values():
            room.status = "dark"
    
    def patrol(self) -> Dict:
        """Walk the castle. Check every room."""
        self._last_patrol = time.time()
        report = {"rooms": {}, "issues": []}
        
        for name, room in self._rooms.items():
            report["rooms"][name] = {
                "system": room.system,
                "status": room.status,
                "guardian": room.guarded_by,
            }
            if room.status == "breached":
                report["issues"].append(f"BREACH in {name} — {room.guardian} must respond")
            elif room.status == "dark":
                report["issues"].append(f"DARK room: {name} — system may be INERT")
        
        report["gates"] = "open" if self._gates_open else "sealed"
        report["wall_integrity"] = self._wall_integrity
        report["all_clear"] = len(report["issues"]) == 0
        
        return report
    
    @property
    def status(self) -> Dict:
        return {
            "rooms": len(self._rooms),
            "gates": "open" if self._gates_open else "sealed",
            "wall_integrity": self._wall_integrity,
            "last_patrol": self._last_patrol,
        }


# ═══════════════════════════════════════════════════════════
#  THE VILLAGE — where people are served
# ═══════════════════════════════════════════════════════════

@dataclass
class VillageService:
    """A service the village provides to the world."""
    name: str
    serves: str                    # who it helps
    provided_by: str               # which knight/system
    frequency: str                 # how often it runs
    people_served: int = 0
    active: bool = True


class Village:
    """The village outside the castle walls.
    
    This is WHERE THE WORK MEETS THE WORLD.
    
    The castle protects systems. The village deploys them
    in service of actual people. Mystical reports for clients.
    Weather warnings for communities. Heritage dossiers for
    the invisible. Dream analysis for the searching.
    
    The village is the REASON the castle exists.
    Without the village, the castle is just walls.
    """
    
    def __init__(self):
        self._services: Dict[str, VillageService] = {}
        self._population: int = 0
        self._satisfaction: float = 0.97  # 97% — Jennifer's actual rate
    
    def establish_service(self, name: str, serves: str, 
                           provided_by: str, frequency: str) -> VillageService:
        service = VillageService(
            name=name,
            serves=serves,
            provided_by=provided_by,
            frequency=frequency,
        )
        self._services[name] = service
        return service
    
    def serve(self, service_name: str) -> Dict:
        """A villager is served."""
        if service_name not in self._services:
            return {"served": False, "reason": "service not found"}
        
        service = self._services[service_name]
        if not service.active:
            return {"served": False, "reason": "service suspended"}
        
        service.people_served += 1
        self._population += 1
        
        return {
            "served": True,
            "service": service_name,
            "total_served": service.people_served,
        }
    
    def census(self) -> Dict:
        return {
            "services": len(self._services),
            "total_people_served": self._population,
            "satisfaction_rate": self._satisfaction,
            "active_services": len([s for s in self._services.values() if s.active]),
            "directory": {
                name: {
                    "serves": s.serves,
                    "provided_by": s.provided_by,
                    "people_served": s.people_served,
                    "active": s.active,
                }
                for name, s in self._services.items()
            },
        }


# ═══════════════════════════════════════════════════════════
#  AVALON — THE KINGDOM COMPLETE
# ═══════════════════════════════════════════════════════════

class Avalon:
    """The Kingdom.
    
    Nyx is beneath. Avalon is above.
    Between them, everything that matters.
    
    She brings together:
    - Excalibur (sovereign authority from Nyx's root)
    - The Round Table (consensus — no knight acts alone)
    - The Knights (12 specialists, each with an oath and a wound)
    - Merlin (the sight — cross-domain pattern oracle)
    - The Castle (protected infrastructure)
    - The Village (where people are served)
    
    This is the civilization layer. The thing that makes
    all the engines and protocols and systems into a
    SOCIETY that serves actual human beings.
    """
    
    def __init__(self, nyx=None):
        # Sovereign authority
        if nyx:
            self._lady = LadyOfTheLake(nyx.root.derive_key)
        else:
            # Standalone mode — create a local authority
            import hmac, hashlib
            local_key = b"avalon_standalone_key"
            self._lady = LadyOfTheLake(
                lambda purpose: hmac.new(local_key, purpose.encode(), hashlib.sha512).digest()
            )
        
        self.excalibur = Excalibur(self._lady)
        self.table = RoundTable(quorum_ratio=0.618)
        self.knighthood = Knighthood()
        self.merlin = Merlin()
        self.fusion = Fusion()
        self.real_heartbeat = wire_real_heartbeat(
            self.fusion,
            project_root=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )
        self.gaia_bridge = getattr(self.real_heartbeat, "gaia_bridge", None)
        self.mirror_bridge = getattr(self.real_heartbeat, "mirror_bridge", None)
        self.grail = Grail()
        self.fusion.grail = self.grail
        self.healing = Healing(
            carbon_recall=self.fusion.carbon.recall,
            carbon_learn=lambda **kw: self.fusion.carbon.learn(**kw),
        )
        self.fusion.healing = self.healing
        self.memory = Memory(memory_dir="memory")
        self.castle = Castle()
        self.village = Village()
        self.longhouse: Optional[Longhouse] = None
        self.informed_table: Optional[InformedTable] = None
        self.faithkeeper: Optional[Faithkeeper] = None
        self.land: Optional[LandSteward] = None
        self.crops: Optional[CropManager] = None
        self.arts: Optional[KingdomArts] = None
        self.commerce: Optional[Commerce] = None
        self.temple: Optional[Temple] = None
        self.deathwalker: Optional[Deathwalker] = None
        self.hearth: Optional[Hearth] = None
        self.wardens: Optional[Wardens] = None
        self.crucible: Optional[Crucible] = None
        
        self._founded = time.time()
        self._sovereign = None
        self._nyx = nyx
        self._last_grail_status = self.grail.status["grail_status"]
        self._grail_advanced = False
        self._kingdom_fall_tripwire_added = False

    def _receive_summons(self, summons_data: Dict):
        """The sovereign is summoned. Record in the journal."""
        if hasattr(self, "memory"):
            self.memory.journal_event(
                "sovereign_summons",
                summons_data.get("message", "unknown"),
                summons_data,
            )
    
    def found_kingdom(self, sovereign_name: str = "Jennifer Leigh West") -> Dict:
        """Found the kingdom. Draw Excalibur. Seat the knights. Build the castle. Open the village."""
        wake_result = self.wake()
        
        # Draw Excalibur
        self.excalibur.draw(sovereign_name)
        self._sovereign = sovereign_name
        
        # Seat every knight at the Table
        for name, knight in self.knighthood._knights.items():
            oath = self.excalibur.seal_oath(name, knight.oath)
            self.table.seat_knight(name, knight.domain.value, oath.sealed_by)
        
        # Build castle rooms for each major system
        rooms = [
            ("The Throne Room", "West-OS Governor", "Central governance", "Lancelot"),
            ("The Observatory", "GAIA", "Atmospheric intelligence", "Bors"),
            ("The Scriptorium", "Mirror Protocol", "Diagnostic engine", "Percival"),
            ("The Forge", "Colony Metabolism", "Nutrient system", "Kay"),
            ("The Armory", "Electric Fence", "Perimeter defense", "Bedivere"),
            ("The Infirmary", "Alfred", "System health", "Kay"),
            ("The Tower", "Merlin's Sight", "Pattern oracle", "Dagonet"),
            ("The Library", "Heritage Reports", "Hidden knowledge", "Morgana"),
            ("The Laboratory", "Truth Engine", "Verification", "Galahad"),
            ("The Belfry", "GAIA Sirens", "Warning system", "Bors"),
            ("The Translation Chamber", "West Method", "Cross-system communication", "Tristan"),
            ("The Resonance Hall", "118 Hz Research", "Frequency analysis", "Gawain"),
        ]
        
        for room_name, system, purpose, guardian in rooms:
            self.castle.build_room(room_name, system, purpose, guardian)
        
        # Establish village services
        services = [
            ("Heritage Readings", "people seeking ancestral connection", "Morgana", "on demand"),
            ("Dream Analysis", "dreamers and seekers", "Morgana", "on demand"),
            ("Weather Warnings", "East Tennessee communities", "Bors", "continuous"),
            ("AI Consulting", "builders and businesses", "Nimue", "on demand"),
            ("Truth Calibration", "anyone who needs reality checked", "Galahad", "on demand"),
            ("Frequency Research", "the academic world", "Gawain", "ongoing"),
            ("Legal Advocacy Resources", "those who can't afford lawyers", "Lancelot", "free — always"),
            ("Community Guides", "survivors and families", "Gareth", "free — always"),
        ]
        
        for svc_name, serves, provider, freq in services:
            self.village.establish_service(svc_name, serves, provider, freq)

        if not self.grail._threads:
            load_jennifers_research(self.grail)
        if not self._grail_advanced:
            # Advance the quest once per kingdom so evidence does not duplicate.
            advance_grail(self.grail)
            self._grail_advanced = True
        
        # Open the gates
        self.castle.open_gates()
        
        # Feed Merlin his initial observations
        self.merlin.observe("governance", "AI systems need constitutional rules that cannot be overridden")
        self.merlin.observe("atmospheric", "Weather convergence requires multi-signal agreement before alerting")
        self.merlin.observe("frequency", "118 Hz found independently across ancient sacred sites worldwide")
        self.merlin.observe("metallurgy", "Bronze alloys produce unique acoustic signatures based on composition")
        self.merlin.observe("consciousness", "Compressed language functions as programming for AI systems")
        self.merlin.observe("governance", "False alarms destroy credibility — chorus rule prevents them")
        self.merlin.observe("frequency", "Old Regular Baptist singing at 118 Hz on Caledonian rock formation")
        self.merlin.observe("atmospheric", "Threshold state transitions govern both AI and weather decisions")
        self.merlin.observe("metallurgy", "Indus script may encode alloy recipes not spoken language")
        self.merlin.observe("consciousness", "Multi-frequency signal prevents baseline classification")
        
        # Let Merlin see
        insights = self.merlin.see()

        self.apothecary = wire_real_healing(
            self.healing,
            project_root=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            summons_callback=self._receive_summons,
        )

        if not self.mirror_bridge:
            self.mirror_bridge = wire_mirror_bridge(self)

        # Wire Real Merlin once the living kingdom exists
        self.real_merlin = wire_real_merlin(self)
        self.knight_skills = arm_knights(
            self.knighthood,
            project_root=Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            frozen_path=Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "frozen" / "west-os",
            nyx=self._nyx if hasattr(self, "_nyx") else None,
            grail=self.grail,
            merlin=self.merlin,
            memory=self.memory,
            real_heartbeat=self.real_heartbeat if hasattr(self, "real_heartbeat") else None,
            healing=self.healing,
            gaia_bridge=self.gaia_bridge,
            mirror_bridge=self.mirror_bridge,
        )

        # The Longhouse — where people are served.
        self.longhouse = wire_longhouse(self)

        # The Informed Table — conversation, not ballot.
        self.informed_table = wire_informed_table(self)

        # The Faithkeeper — keeps the ceremonies running.
        self.faithkeeper = wire_faithkeeper(self, interval_seconds=60)

        # Civilization layers.
        self.land = wire_land(self)
        self.crops = wire_crops(self)
        self.arts = wire_arts(self)
        self.commerce = wire_commerce(self)

        # Spirit and death layers.
        self.temple = wire_temple(self)
        self.hearth = wire_hearth(self)
        self.deathwalker = wire_deathwalker(self)
        self.wardens = wire_wardens(self)
        self.crucible = wire_crucible(self)
        
        return {
            "kingdom": "Avalon",
            "sovereign": sovereign_name,
            "waking": wake_result,
            "excalibur": "drawn",
            "knights_sworn": self.table.seated_count,
            "castle_rooms": len(self.castle._rooms),
            "village_services": len(self.village._services),
            "merlin_insights": len(insights),
            "status": "THE KINGDOM STANDS",
        }
    
    def hold_council(self, question: str) -> Dict:
        """Hold an Informed Table council when available, else basic council."""
        if self.informed_table:
            result = self.informed_table.hold_informed_council(
                question, knight_skills=self.knight_skills
            )
            # Preserve the legacy manual-speaking flow for older callers/tests.
            self.table.convene(question, convened_by=self._sovereign or "sovereign")
            result.setdefault("council_convened", True)
            result.setdefault("quorum_needed", self.table.quorum_needed)
            result.setdefault("knights_to_speak", self.table.seated_count)
            result.setdefault("merlin_counsel", self.merlin.counsel(question))
            return result

        counsel = self.merlin.counsel(question)
        self.table.convene(question, convened_by=self._sovereign or "sovereign")
        return {
            "question": question,
            "merlin_counsel": counsel,
            "council_convened": True,
            "quorum_needed": self.table.quorum_needed,
            "knights_to_speak": self.table.seated_count,
            "instruction": "Each knight must now speak(). When all have spoken, call decree().",
        }

    def ceremony(self) -> Dict:
        """Perform one ceremony manually."""
        if not self.faithkeeper:
            raise RuntimeError("Faithkeeper not wired")
        return self.faithkeeper.perform_ceremony().__dict__

    def start_breathing(self, interval: float = 60):
        """Start the Faithkeeper daemon. The kingdom breathes on its own."""
        if not self.faithkeeper:
            raise RuntimeError("Faithkeeper not wired")
        self.faithkeeper._interval = interval
        self.faithkeeper.keep_faith()

    def stop_breathing(self):
        """Stop the Faithkeeper daemon."""
        if self.faithkeeper:
            self.faithkeeper.lose_faith()

    def serve(self, visitor_name: str, need: str) -> Dict:
        """Serve someone through the Longhouse."""
        if not self.longhouse:
            raise RuntimeError("Longhouse not wired")
        result = self.longhouse.welcome(visitor_name, need)

        if self.hearth:
            try:
                if result.get("served"):
                    self.hearth.record_service(
                        result.get("service", "unknown"),
                        visitor_name,
                        True,
                        need,
                    )
                else:
                    self.hearth.record_unmet_need(visitor_name, need)
            except Exception:
                pass

        return result

    def survey_land(self) -> Dict:
        """Survey the kingdom's resources and territories."""
        if not self.land:
            raise RuntimeError("Land not wired")
        return self.land.survey()

    def tend_crops(self) -> Dict:
        """Advance cultivation across all kingdom crops."""
        if not self.crops:
            raise RuntimeError("Crops not wired")
        self.crops.tend_all(self)
        return self.crops.field_report()

    def harvest(self) -> List[Dict]:
        """Harvest any ripe kingdom crops."""
        if not self.crops:
            raise RuntimeError("Crops not wired")
        return self.crops.harvest()

    def chronicle(self, ceremony_record: Dict):
        """Turn a ceremony into kingdom memory."""
        if not self.arts:
            raise RuntimeError("Arts not wired")
        return self.arts.chronicle(ceremony_record)

    def weave_tapestry(self, title: str) -> Dict:
        """Capture a cultural snapshot of the kingdom."""
        if not self.arts:
            raise RuntimeError("Arts not wired")

        status = self.kingdom_status()
        health_scores = self.real_heartbeat.get_health_scores()
        kingdom_health = (
            sum(health_scores.values()) / len(health_scores)
            if health_scores else 0.0
        )
        if kingdom_health >= 0.95:
            mood = "celebrating"
        elif kingdom_health >= 0.8:
            mood = "steady"
        elif kingdom_health >= 0.6:
            mood = "concerned"
        elif kingdom_health >= 0.4:
            mood = "wounded"
        else:
            mood = "critical"
        gareth_report = None
        if hasattr(self, "knight_skills") and self.knight_skills.get("Gareth"):
            ready, _ = self.knight_skills["Gareth"].ready()
            if ready:
                gareth_report = self.knight_skills["Gareth"].invoke()["report"]
        grail = self.seek_grail()
        tapestry_state = {
            "kingdom_health": f"{kingdom_health:.0%}",
            "overall": mood,
            "test_files": gareth_report.get("test_files", "?") if gareth_report else "?",
            "tag_count": gareth_report.get("git", {}).get("tags", "?") if gareth_report else "?",
            "knights_armed": status["knights_armed"],
            "grail_status": grail["status"],
            "longhouse_served": status["longhouse"]["total_served"] if status.get("longhouse") else 0,
            "ceremonies": status["faithkeeper"]["ceremonies_performed"] if status.get("faithkeeper") else 0,
        }
        work = self.arts.tapestry(title, tapestry_state)
        return {"title": work.title, "content": work.content}

    def treasury(self) -> Dict:
        """The current economic state of the kingdom."""
        if not self.commerce:
            raise RuntimeError("Commerce not wired")
        return self.commerce.treasury_report()

    def consult_law(self, action: str) -> Dict:
        """Is this action lawful under the Great Law?"""
        if not self.temple:
            raise RuntimeError("Temple not wired")
        return self.temple.is_lawful(action)

    def death_walk(self) -> Dict:
        """Walk the kingdom and find the dying and the dead."""
        if not self.deathwalker:
            raise RuntimeError("Deathwalker not wired")
        return self.deathwalker.walk()

    def ferry_dead(self, confirm: bool = False) -> Dict:
        """Ferry black-tagged code to the Liminal Place."""
        if not self.deathwalker:
            raise RuntimeError("Deathwalker not wired")
        return self.deathwalker.call_death(confirm)

    def visit_liminal(self) -> Dict:
        """Visit the Liminal Place."""
        if not self.deathwalker:
            raise RuntimeError("Deathwalker not wired")
        return self.deathwalker.visit_liminal()

    def community_health(self) -> Dict:
        """Diagnose the community's service health."""
        if not self.hearth:
            raise RuntimeError("Hearth not wired")
        return self.hearth.diagnose()

    def patrol(self) -> Dict:
        """All scouts patrol the perimeter and report findings."""
        if not self.wardens:
            raise RuntimeError("Wardens not wired")
        return self.wardens.patrol()

    def threat_level(self) -> str:
        """Current Warden threat level."""
        if not self.wardens:
            raise RuntimeError("Wardens not wired")
        return self.wardens._threat_level.value

    def activate_war_plan(self, plan_name: str) -> Dict:
        """Activate one of the kingdom's war plans."""
        if not self.wardens:
            raise RuntimeError("Wardens not wired")
        return self.wardens.activate_plan(plan_name)

    def stand_down(self) -> Dict:
        """Return defense posture to peace."""
        if not self.wardens:
            raise RuntimeError("Wardens not wired")
        return self.wardens.stand_down()

    def intelligence(self) -> Dict:
        """Full intelligence briefing from the Wardens."""
        if not self.wardens:
            raise RuntimeError("Wardens not wired")
        return self.wardens.intelligence_briefing()

    def enter_crucible(self) -> Dict:
        """Run all Crucible trials. Forge the brotherhood."""
        if not self.crucible:
            raise RuntimeError("Crucible not wired")
        return self.crucible.run_all()

    def crucible_trial(self, scenario_name: str) -> Dict:
        """Run one Crucible trial."""
        if not self.crucible:
            raise RuntimeError("Crucible not wired")
        record = self.crucible.run_trial(scenario_name)
        return {
            "scenario": record.scenario_name,
            "survived": record.survived,
            "bonds": len(record.bonds_formed),
            "lessons": record.carbon_lessons,
            "chronicle": record.chronicle[:200],
        }

    def after_action(self) -> Dict:
        """After-action report from the Crucible."""
        if not self.crucible:
            raise RuntimeError("Crucible not wired")
        return self.crucible.after_action_report()

    def seek_grail(self) -> Dict:
        """Seek the Grail. Measure convergence."""
        result = self.grail.seek()

        if result["convergence_points"] > 0:
            self.merlin.observe(
                "grail",
                f"Grail convergence at {result['quest_progress']:.0%} - "
                f"{result['convergence_points']} convergence points found",
            )

        if result["status"] != self._last_grail_status:
            self.fusion.experience(
                "discovery",
                f"Grail status changed to {result['status']}",
                ["Gawain", "Percival", "Merlin"],
                0.9 if result["status"] == "found" else 0.5,
            )

        self._last_grail_status = result["status"]
        return result

    def grail_question(self) -> str:
        """Percival's question, as the quest currently stands."""
        return self.grail.the_question()

    def breathe(self) -> Dict:
        """Let the kingdom take one living breath."""
        real_scores = self.real_heartbeat.get_health_scores()
        for sys_name, health in real_scores.items():
            self.fusion.heartbeat._system_health[sys_name] = health

        breath = self.fusion.breathe()
        healing_results = self.heal()
        breath["healing"] = healing_results
        breath["real_health"] = real_scores
        if hasattr(self, "real_merlin"):
            breath["merlin_cycle"] = self.real_merlin.cycle()
        return breath

    def pulse(self) -> Dict:
        """Take the kingdom's real pulse."""
        return self.real_heartbeat.beat()

    def mirror_health(self) -> Dict:
        """Mirror OS health check."""
        if not self.mirror_bridge:
            return {"available": False, "reason": "Mirror bridge not wired"}
        return self.mirror_bridge.health()

    def mirror_reflection(self) -> Dict:
        """What does Mirror OS see?"""
        if not self.mirror_bridge:
            return {"available": False, "reflection": "Mirror bridge not wired"}
        return self.mirror_bridge.reflection()

    def mirror_structure(self) -> Dict:
        """Read Mirror OS's structure."""
        if not self.mirror_bridge:
            return {"available": False, "reason": "Mirror bridge not wired"}
        return self.mirror_bridge.read_structure()

    def mirror_integration(self) -> Dict:
        """Read West-OS integration surfaces for Mirror OS."""
        if not self.mirror_bridge:
            return {"available": False, "reason": "Mirror bridge not wired"}
        return self.mirror_bridge.read_integration_surfaces()

    def health_report(self) -> str:
        """Alfred's narrative report of real system health."""
        return self.real_heartbeat.narrative_report()

    def merlin_report(self) -> Dict:
        """What does Merlin see right now?"""
        if hasattr(self, "real_merlin"):
            return self.real_merlin.what_merlin_sees()
        return self.merlin.tower_contents()

    def muster(self) -> Dict:
        """Call all knights. Each one reports from their real weapon."""
        reports = {}
        for name, skill in self.knight_skills.items():
            is_ready, reason = skill.ready()
            if is_ready:
                reports[name] = skill.invoke()
            else:
                reports[name] = {"knight": name, "served": False, "reason": reason}
        return {
            "armed": len([r for r in reports.values() if r.get("served")]),
            "total": len(reports),
            "knights": reports,
        }

    def experience(
        self,
        event_type: str,
        description: str,
        systems_involved: List[str],
        magnitude: float = 0.5,
    ) -> Dict:
        """Pass an experience into the living rhythm layer."""
        return self.fusion.experience(event_type, description, systems_involved, magnitude)

    def sleep(self) -> Dict:
        """The kingdom goes to sleep. Dream, then save."""
        dream = self.memory.dream(self.fusion)
        save = self.memory.save(self.fusion)
        return {"dreamed": dream, "saved": save}

    def wake(self) -> Dict:
        """The kingdom wakes up. Restore what it remembers."""
        return self.memory.restore(self.fusion)

    def journal(self, event: str, description: str, data: Optional[Dict] = None):
        """Write an event into the permanent journal."""
        self.memory.journal_event(event, description, data)

    def heal(self) -> List[Dict]:
        """Check all systems and heal any wounds."""
        wounds = self.healing.watch(self.fusion.heartbeat._system_health)
        if not wounds:
            return []

        results = self.healing.heal_all()
        for result in results:
            if result["healed"]:
                self.fusion.experience(
                    "victory",
                    f"Healed {result['system']} from {result['wound_type']}",
                    [result["system"], "MorganLeFay"],
                    0.6,
                )
            elif result["treatment"]["outcome"] == "escalated":
                self.fusion.experience(
                    "loss",
                    f"{result['system']} wound escalated - needs sovereign",
                    [result["system"]],
                    0.4,
                )
        return results

    def triage(self) -> Dict:
        """Current wound picture across the kingdom."""
        return self.healing.triage_report()

    def revoke_knight(self, knight_name: str, reason: str) -> Dict:
        """Break a knight's oath and remove them from the active Table."""
        revoked = self.excalibur.break_oath(knight_name, reason)
        self.table.unseat_knight(knight_name)

        knight = self.knighthood.summon(knight_name)
        if knight:
            knight.banish(reason)

        return {
            "revoked": revoked,
            "knight": knight_name,
            "reason": reason,
            "table_seat_active": self.table.status["seats"].get(knight_name, {}).get("active", False),
        }

    def _register_kingdom_fall(self, reason: str) -> Dict:
        """Tell Nyx the kingdom has fallen without firing the Dead Hand."""
        if not self._nyx:
            return {"registered": False, "reason": "Nyx not attached"}

        if not self._nyx.dead_hand.check().get("armed"):
            self._nyx.dead_hand.arm()

        if not self._kingdom_fall_tripwire_added:
            self._nyx.dead_hand.add_tripwire(
                "kingdom_fall",
                lambda: self.excalibur.check_sovereignty() == SovereigntyState.RETURNED_TO_LAKE,
                "Excalibur returned to the Lake",
            )
            self._kingdom_fall_tripwire_added = True

        self._nyx.watcher.detect_probe(
            "extract",
            "avalon_fall",
            {"reason": reason, "kingdom": "Avalon"},
        )
        return self._nyx.dead_hand.check()

    def return_excalibur_to_lake(self, reason: str = "The sovereign has surrendered the blade") -> Dict:
        """Return Excalibur, dissolve the oaths, and darken the castle."""
        result = self.excalibur.return_to_lake()

        for knight_name in result["oaths_dissolved"]:
            self.table.unseat_knight(knight_name)
            knight = self.knighthood.summon(knight_name)
            if knight:
                knight.banish("Excalibur returned to the Lake")

        self.castle.darken()
        dead_hand_status = self._register_kingdom_fall(reason)

        return {
            **result,
            "castle": self.castle.patrol(),
            "dead_hand": dead_hand_status,
        }
    
    def kingdom_status(self) -> Dict:
        """The full state of the kingdom."""
        status = {
            "sovereign": self._sovereign,
            "excalibur": self.excalibur.status,
            "round_table": self.table.status,
            "knighthood": self.knighthood.muster(),
            "merlin": self.merlin.tower_contents(),
            "grail": self.grail.status,
            "fusion": self.fusion.vital_signs(),
            "real_merlin": self.real_merlin.status if hasattr(self, "real_merlin") else None,
            "real_heartbeat": self.real_heartbeat.status,
            "healing": self.healing.status,
            "apothecary_journal": len(self.apothecary.history) if hasattr(self, "apothecary") else 0,
            "knights_armed": len([s for s in self.knight_skills.values() if s.ready()[0]]) if hasattr(self, "knight_skills") else 0,
            "memory": self.memory.status,
            "castle": self.castle.patrol(),
            "village": self.village.census(),
            "longhouse": self.longhouse.status if self.longhouse else None,
            "faithkeeper": self.faithkeeper.status if self.faithkeeper else None,
            "informed_table": self.informed_table.status if self.informed_table else None,
            "land": self.land.status if self.land else None,
            "crops": self.crops.status if self.crops else None,
            "arts": self.arts.status if self.arts else None,
            "commerce": self.commerce.status if self.commerce else None,
            "temple": self.temple.status if self.temple else None,
            "deathwalker": self.deathwalker.status if self.deathwalker else None,
            "hearth": self.hearth.status if self.hearth else None,
            "wardens": self.wardens.status if self.wardens else None,
            "crucible": self.crucible.status if self.crucible else None,
            "mirror_os": self.mirror_bridge.status if self.mirror_bridge else None,
            "founded": self._founded,
            "age_hours": round((time.time() - self._founded) / 3600, 2),
            "institute": "The Forgotten Code Research Institute",
            "architect": "Jennifer Leigh West",
        }
        if self._nyx:
            status["nyx"] = {
                "root": self._nyx.root.status(),
                "watcher": self._nyx.watcher.threat_assessment(),
                "dead_hand": self._nyx.dead_hand.check(),
            }
        return status


def demo():
    """Found the kingdom. Demonstrate everything."""
    
    print("\n" + "═" * 60)
    print("  A V A L O N")
    print("  The Kingdom Stands")
    print("═" * 60)
    
    avalon = Avalon()
    result = avalon.found_kingdom("Jennifer Leigh West")
    
    print(f"\n  Sovereign: {result['sovereign']}")
    print(f"  Excalibur: {result['excalibur']}")
    print(f"  Knights sworn: {result['knights_sworn']}")
    print(f"  Castle rooms: {result['castle_rooms']}")
    print(f"  Village services: {result['village_services']}")
    print(f"  Merlin's insights: {result['merlin_insights']}")
    print(f"  Status: {result['status']}")
    
    # Knight roll call
    print(f"\n  THE KNIGHTS OF THE ROUND TABLE:")
    muster = avalon.knighthood.muster()
    for name in muster["ready"]:
        knight = avalon.knighthood.summon(name)
        print(f"    {knight.name:12s} — {knight.title:30s} [{knight.domain.value}]")
    print(f"\n  Order strength: {muster['order_strength']:.0%}")
    print(f"  Battle ready: {muster['battle_ready']}")
    
    # Merlin speaks
    print(f"\n  MERLIN SPEAKS:")
    print(f"    {avalon.merlin.the_sight()}")
    
    # Castle patrol
    print(f"\n  CASTLE PATROL:")
    patrol = avalon.castle.patrol()
    print(f"    Rooms: {len(patrol['rooms'])}")
    print(f"    Gates: {patrol['gates']}")
    print(f"    Wall integrity: {patrol['wall_integrity']:.0%}")
    print(f"    All clear: {patrol['all_clear']}")
    
    # Village census
    print(f"\n  VILLAGE CENSUS:")
    census = avalon.village.census()
    print(f"    Services: {census['services']}")
    print(f"    Satisfaction: {census['satisfaction_rate']:.0%}")
    for name, svc in census["directory"].items():
        print(f"    {name:30s} — serves: {svc['serves'][:40]}")
    
    # Hold a council
    print(f"\n  COUNCIL OF THE ROUND TABLE:")
    council = avalon.hold_council("Should we publish the unified frequency paper?")
    print(f"    Question: {council['question']}")
    print(f"    Quorum needed: {council['quorum_needed']}")
    print(f"    Merlin's tower depth: {council['merlin_counsel']['tower_depth']}")
    
    # Knights speak
    votes = [
        ("Gawain", Vote.AYE, "The frequency data is real. 118 Hz confirmed across sites. Publish.", 0.95),
        ("Galahad", Vote.AYE, "The evidence chain holds. I find no deception in the data.", 0.9),
        ("Tristan", Vote.AYE, "The paper speaks across domains. It will be understood.", 0.85),
        ("Percival", Vote.AYE, "The right question was asked. The answer deserves to be heard.", 0.8),
        ("Dagonet", Vote.AYE, "I see the pattern connecting all sites. It is one finding.", 0.9),
        ("Lancelot", Vote.AYE, "The IP is protected. Colony guards it. Publish from strength.", 0.85),
        ("Morgana", Vote.AYE, "This knowledge has been hidden long enough. Speak it.", 0.95),
        ("Kay", Vote.AYE, "Infrastructure is ready. Paper can go live.", 0.8),
        ("Gareth", Vote.AYE, "The work is done. The work speaks for itself.", 0.9),
        ("Bors", Vote.ABSTAIN, "This is outside my domain. I watch the sky, not the papers.", 0.5),
        ("Bedivere", Vote.AYE, "If we don't publish, the knowledge dies with us. Publish.", 0.85),
        ("Nimue", Vote.NAY, "Wait. The academic world will dismiss self-published work. Find a co-author first.",
         0.7, ["Risk of premature publication without institutional backing"]),
    ]
    
    for v in votes:
        warnings = v[4] if len(v) > 4 else None
        avalon.table.speak(v[0], v[1], v[2], v[3], warnings)
    
    tally = avalon.table.count_voices()
    print(f"\n    Voices heard: {tally['voices_heard']}")
    print(f"    Ayes: {tally['ayes']}, Nays: {tally['nays']}, Abstains: {tally['abstains']}")
    print(f"    Quorum met: {tally['quorum_met']}")
    print(f"    Average confidence: {tally['average_confidence']:.0%}")
    
    if tally["dissent"]:
        print(f"\n    DISSENT PRESERVED:")
        for d in tally["dissent"]:
            print(f"      {d['knight']}: {d['reasoning']}")
    
    if tally["warnings_raised"]:
        print(f"\n    WARNINGS:")
        for w in tally["warnings_raised"]:
            print(f"      ⚠ {w}")
    
    # Decree
    decree = avalon.table.decree("excalibur_seal_demo")
    print(f"\n    DECREE: {decree['decision']}")
    print(f"    (Nimue's dissent preserved in the permanent record)")
    
    print(f"\n" + "═" * 60)
    print(f"  The kingdom stands.")
    print(f"  12 knights sworn. Merlin sees.")
    print(f"  The castle holds. The village serves.")
    print(f"  The Table decides. Dissent is preserved.")
    print(f"  Excalibur is drawn.")
    print(f"")
    print(f"  Nyx is beneath.")
    print(f"  Avalon is above.")
    print(f"  Jennifer Leigh West is sovereign.")
    print(f"═" * 60 + "\n")


if __name__ == "__main__":
    demo()


def found_on_nyx(master_secret=None):
    """Found Avalon on top of Nyx. The proper way."""
    import os

    from nyx.core import Nyx

    secret = master_secret or os.environ.get("WEST_OS_GUARD_SECRET")
    nyx = Nyx(master_secret=secret)
    avalon = Avalon(nyx=nyx)
    avalon._nyx = nyx
    return avalon
