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
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from avalon.excalibur import Excalibur, LadyOfTheLake, SovereigntyState
from avalon.fusion import Fusion
from avalon.memory import Memory
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
        self.memory = Memory(memory_dir="memory")
        self.castle = Castle()
        self.village = Village()
        
        self._founded = time.time()
        self._sovereign = None
        self._nyx = nyx
        self._kingdom_fall_tripwire_added = False
    
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
            self.fusion.heartbeat.register_system(name, lambda k=knight: k.strength)
        
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
        """The sovereign calls a council of the Round Table.
        
        Merlin advises. Knights speak. The Table decides.
        """
        # Get Merlin's counsel first
        counsel = self.merlin.counsel(question)
        
        # Convene the table
        council = self.table.convene(question, convened_by=self._sovereign or "sovereign")
        
        return {
            "question": question,
            "merlin_counsel": counsel,
            "council_convened": True,
            "quorum_needed": self.table.quorum_needed,
            "knights_to_speak": self.table.seated_count,
            "instruction": "Each knight must now speak(). When all have spoken, call decree().",
        }

    def breathe(self) -> Dict:
        """Let the kingdom take one living breath."""
        return self.fusion.breathe()

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
            "fusion": self.fusion.vital_signs(),
            "memory": self.memory.status,
            "castle": self.castle.patrol(),
            "village": self.village.census(),
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
