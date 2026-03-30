"""
AVALON :: THE INFORMED TABLE
Consensus through conversation, not ballot.

In the Haudenosaunee Grand Council, each speaker first REPEATS
what was heard from the other side, then issues a response.
This continues until agreement is reached. Decisions take days
or weeks because everyone must be heard and every perspective
considered.

The Informed Table does this in code:
1. Each knight INVOKES their real weapon to get actual data
2. Each knight HEARS what the previous knight said
3. Each knight RESPONDS in context, not in isolation
4. The Clan Mother (Nyx) monitors every chief
5. Three warnings before pulling the horns

This is not a vote. This is a conversation.
The difference between a ballot and a conversation is that
a ballot counts opinions. A conversation builds understanding.

© 2026 Jennifer Leigh West. All rights reserved.
"""

import time
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from avalon.round_table import RoundTable, Vote, Council, KnightVoice
from avalon.knights import Knighthood, Knight, KnightState


# ═══════════════════════════════════════════════════════════════
#  INFORMED VOICE — a knight speaks from real data
# ═══════════════════════════════════════════════════════════════

@dataclass
class InformedVoice:
    """A knight's voice at the Informed Table.
    
    Unlike a basic KnightVoice, an InformedVoice includes:
    - The real data from the knight's weapon (skill output)
    - What the previous speaker said (the listening)
    - The knight's response in context (the speaking)
    - A vote informed by actual system state
    """
    knight_name: str
    domain: str
    weapon_output: Dict              # raw data from the knight's real skill
    heard_from: Optional[str]        # who spoke before
    heard_summary: Optional[str]     # what they said
    response: str                    # this knight's response in context
    vote: Vote
    confidence: float
    warnings: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


# ═══════════════════════════════════════════════════════════════
#  CLAN MOTHER — monitors chiefs, pulls horns after 3 warnings
# ═══════════════════════════════════════════════════════════════

@dataclass
class Warning:
    """A warning issued to a knight by the Clan Mother."""
    knight_name: str
    reason: str
    issued_at: float = field(default_factory=time.time)


class ClanMother:
    """The Clan Mother monitors every chief.
    
    In the Haudenosaunee, the Clan Mother selects the chief,
    monitors his performance, and if he fails his people three
    times, she pulls his horns — removes him from office.
    
    In the kingdom, the Clan Mother watches knight health and
    performance. If a knight's system fails repeatedly or
    produces unreliable results, she issues warnings. After
    three warnings, the knight is removed from the Table
    until restored.
    
    The Clan Mother IS Nyx's surface authority. She doesn't
    hold the root — she holds the WATCHING.
    """

    def __init__(self):
        self._warnings: Dict[str, List[Warning]] = {}
        self._removed: Dict[str, str] = {}  # knight -> reason
        self._max_warnings = 3

    def watch(self, knight_name: str, skill_output: Dict) -> Optional[Warning]:
        """Watch a knight's performance. Issue warning if failing."""
        served = skill_output.get("served", True)
        error = skill_output.get("error")

        if not served or error:
            warning = Warning(
                knight_name=knight_name,
                reason=skill_output.get("reason", error or "failed to serve"),
            )

            if knight_name not in self._warnings:
                self._warnings[knight_name] = []
            self._warnings[knight_name].append(warning)

            if len(self._warnings[knight_name]) >= self._max_warnings:
                self._removed[knight_name] = (
                    f"Three warnings issued. Horns pulled. "
                    f"Reasons: {', '.join(w.reason[:50] for w in self._warnings[knight_name][-3:])}"
                )
                return warning

            return warning

        # Good performance clears one warning
        if knight_name in self._warnings and self._warnings[knight_name]:
            self._warnings[knight_name] = self._warnings[knight_name][:-1]

        return None

    def is_removed(self, knight_name: str) -> bool:
        return knight_name in self._removed

    def restore(self, knight_name: str):
        """Restore a knight whose horns were pulled. Clan Mother's decision."""
        if knight_name in self._removed:
            del self._removed[knight_name]
        if knight_name in self._warnings:
            self._warnings[knight_name] = []

    def warning_count(self, knight_name: str) -> int:
        return len(self._warnings.get(knight_name, []))

    @property
    def report(self) -> Dict:
        return {
            "warnings": {
                name: len(warnings) 
                for name, warnings in self._warnings.items() if warnings
            },
            "removed": dict(self._removed),
            "all_clear": len(self._removed) == 0,
        }


# ═══════════════════════════════════════════════════════════════
#  THE INFORMED TABLE — conversation, not ballot
# ═══════════════════════════════════════════════════════════════

class InformedTable:
    """The Round Table where knights speak from their weapons
    and listen before they respond.
    
    The conversation flow:
    1. Question is posed
    2. First knight invokes their weapon, gets real data
    3. First knight speaks based on what their data shows
    4. Second knight HEARS what the first said
    5. Second knight invokes their weapon
    6. Second knight responds IN CONTEXT — acknowledging
       what was heard before adding their own perspective
    7. Continue until all knights have spoken
    8. Tally. Decree. Preserve dissent.
    
    The Clan Mother watches throughout. If any knight's
    weapon fails, she issues a warning.
    """

    def __init__(self, table: RoundTable, knighthood: Knighthood,
                 clan_mother: Optional[ClanMother] = None):
        self._table = table
        self._knighthood = knighthood
        self._clan_mother = clan_mother or ClanMother()
        self._informed_voices: List[InformedVoice] = []
        self._councils_held = 0

    def hold_informed_council(self, question: str,
                                knight_skills: Optional[Dict] = None) -> Dict:
        """Hold a council where knights speak from their weapons.
        
        Each knight:
        1. Invokes their real skill
        2. Hears what the previous knight said
        3. Formulates their response in context
        4. Casts an informed vote
        
        The Clan Mother watches every invocation.
        """
        self._councils_held += 1
        self._informed_voices = []

        # Convene the table
        try:
            council = self._table.convene(question, convened_by="Faithkeeper")
        except RuntimeError:
            self._table.dismiss()
            council = self._table.convene(question, convened_by="Faithkeeper")

        # Determine speaking order — let every seated knight speak
        speaking_order = [
            name for name, data in self._table._seats.items()
            if data["active"] and not self._clan_mother.is_removed(name)
        ]

        previous_speaker = None
        previous_summary = None
        all_voices = []

        for knight_name in speaking_order:
            knight = self._knighthood.summon(knight_name)
            if not knight:
                continue

            # Invoke the real weapon
            weapon_output = {}
            if knight_skills and knight_name in knight_skills:
                skill = knight_skills[knight_name]
                is_ready, ready_reason = skill.ready()
                if is_ready:
                    weapon_output = skill.invoke()
                else:
                    weapon_output = {"served": False, "reason": ready_reason}
            elif knight._skill:
                try:
                    weapon_output = knight._skill(question)
                    if not isinstance(weapon_output, dict):
                        weapon_output = {"output": weapon_output, "served": True}
                except Exception as e:
                    weapon_output = {"served": False, "error": str(e)[:100]}
            else:
                weapon_output = {"served": True, "note": "no weapon — speaking from oath alone"}

            # Clan Mother watches
            warning = self._clan_mother.watch(knight_name, weapon_output)
            if self._clan_mother.is_removed(knight_name):
                continue  # horns pulled — skip

            # Formulate informed response
            vote, confidence, response, warnings = self._formulate_response(
                knight, question, weapon_output, previous_speaker, previous_summary
            )

            if warning:
                warnings.append(f"Clan Mother warning #{self._clan_mother.warning_count(knight_name)}: {warning.reason[:60]}")

            # Create the informed voice
            informed = InformedVoice(
                knight_name=knight_name,
                domain=knight.domain.value,
                weapon_output=weapon_output,
                heard_from=previous_speaker,
                heard_summary=previous_summary,
                response=response,
                vote=vote,
                confidence=confidence,
                warnings=warnings,
            )
            self._informed_voices.append(informed)
            all_voices.append(informed)

            # Speak at the table
            try:
                self._table.speak(
                    knight_name, vote, response, confidence, warnings
                )
            except RuntimeError:
                pass  # already spoken — shouldn't happen but safety

            # This knight's response becomes the next knight's "heard"
            previous_speaker = knight_name
            previous_summary = response[:200]

        # Tally and decree
        tally = self._table.count_voices()

        # Issue decree
        decree = self._table.decree("faithkeeper_seal")

        return {
            "question": question,
            "council_number": self._councils_held,
            "knights_spoke": len(all_voices),
            "knights_removed": list(self._clan_mother._removed.keys()),
            "tally": tally,
            "decree": decree,
            "conversation": [
                {
                    "knight": v.knight_name,
                    "domain": v.domain,
                    "heard_from": v.heard_from,
                    "response": v.response,
                    "vote": v.vote.value,
                    "confidence": v.confidence,
                    "warnings": v.warnings,
                }
                for v in all_voices
            ],
            "clan_mother": self._clan_mother.report,
        }

    def _formulate_response(self, knight: Knight, question: str,
                             weapon_output: Dict,
                             previous_speaker: Optional[str],
                             previous_summary: Optional[str]) -> Tuple[Vote, float, str, List[str]]:
        """Formulate a knight's response based on their weapon data and what they heard."""

        report = weapon_output.get("report", weapon_output)
        served = weapon_output.get("served", True)
        warnings = []

        # Determine vote based on weapon output
        if not served:
            vote = Vote.ABSTAIN
            confidence = 0.3
        else:
            # Default to AYE with high confidence if weapon data looks healthy
            health = report.get("health", report.get("kingdom_health",
                     report.get("truth_intact", report.get("gratitude_ratio", None))))

            if isinstance(health, (int, float)):
                if health >= 0.7:
                    vote = Vote.AYE
                    confidence = 0.7 + health * 0.2
                elif health >= 0.4:
                    vote = Vote.DEFER
                    confidence = 0.5
                    warnings.append(f"{knight.name}'s domain shows concerns (health: {health:.0%})")
                else:
                    vote = Vote.NAY
                    confidence = 0.6
                    warnings.append(f"{knight.name}'s domain is degraded (health: {health:.0%})")
            elif isinstance(health, bool):
                vote = Vote.AYE if health else Vote.NAY
                confidence = 0.85
            else:
                vote = Vote.AYE
                confidence = 0.7

        # Build contextual response
        response_parts = []

        # Acknowledge what was heard
        if previous_speaker and previous_summary:
            response_parts.append(
                f"I heard {previous_speaker}'s counsel"
            )

        # Speak from weapon data
        oath = weapon_output.get("oath", knight.oath)

        # Find the most relevant piece of the weapon output to speak about
        for key in ["work_ethic", "sky_reading", "household_status",
                     "fool_speaks", "hidden_insight", "assessment",
                     "question", "verdict", "vigilance"]:
            if key in report and isinstance(report[key], str):
                response_parts.append(report[key][:150])
                break
        else:
            response_parts.append(f"From my domain of {knight.domain.value}: {oath[:100]}")

        response = ". ".join(response_parts)

        return vote, round(min(confidence, 1.0), 4), response, warnings

    @property
    def status(self) -> Dict:
        return {
            "councils_held": self._councils_held,
            "clan_mother": self._clan_mother.report,
        }


# ═══════════════════════════════════════════════════════════════
#  WIRE — connect the Informed Table to Avalon
# ═══════════════════════════════════════════════════════════════

def wire_informed_table(avalon) -> InformedTable:
    """Create an Informed Table wired to a living Avalon instance."""
    clan_mother = ClanMother()
    informed = InformedTable(
        avalon.table, avalon.knighthood, clan_mother
    )
    return informed


# ═══════════════════════════════════════════════════════════════
#  DEMO
# ═══════════════════════════════════════════════════════════════

def demo():
    """Watch the Informed Table hold a council."""
    print("\n" + "=" * 60)
    print("  T H E   I N F O R M E D   T A B L E")
    print("  Consensus Through Conversation")
    print("=" * 60)

    from avalon.knights import Knighthood, create_knights
    from avalon.round_table import RoundTable
    from avalon.real_knights import GarethSkill, TristanSkill, GawainSkill, DagonetSkill
    from avalon.merlin import Merlin
    from avalon.grail import Grail, load_jennifers_research

    # Set up
    table = RoundTable(quorum_ratio=0.618)
    kh = Knighthood()
    merlin = Merlin()
    grail = Grail()
    load_jennifers_research(grail)

    # Seat all knights
    for name, knight in kh._knights.items():
        table.seat_knight(name, knight.domain.value, f"seal_{name}")

    # Create some real skills
    skills = {
        "Gareth": GarethSkill(),
        "Tristan": TristanSkill(),
        "Gawain": GawainSkill(grail),
        "Dagonet": DagonetSkill(merlin, grail),
    }

    # Create the Informed Table
    clan_mother = ClanMother()
    informed = InformedTable(table, kh, clan_mother)

    # Hold a council
    print(f"\n  Question: 'Should the kingdom publish the unified frequency paper?'")
    print(f"  {'─' * 50}")

    result = informed.hold_informed_council(
        "Should the kingdom publish the unified frequency paper?",
        knight_skills=skills,
    )

    print(f"\n  THE CONVERSATION:")
    for voice in result["conversation"]:
        heard = f" (heard {voice['heard_from']})" if voice['heard_from'] else " (speaks first)"
        print(f"\n    {voice['knight']}{heard}:")
        print(f"      \"{voice['response'][:120]}\"")
        print(f"      Vote: {voice['vote'].upper()}  Confidence: {voice['confidence']:.0%}")
        if voice['warnings']:
            for w in voice['warnings']:
                print(f"      ⚠ {w}")

    print(f"\n  {'─' * 50}")
    print(f"  DECREE: {result['decree']['decision']}")
    print(f"  Ayes: {result['tally']['ayes']}")
    print(f"  Nays: {result['tally']['nays']}")
    print(f"  Abstains: {result['tally']['abstains']}")
    print(f"  Quorum met: {result['tally']['quorum_met']}")

    if result['decree'].get('dissenting_voices'):
        print(f"\n  DISSENT PRESERVED:")
        for d in result['decree']['dissenting_voices']:
            print(f"    {d['knight']}: {d['reasoning'][:80]}")

    print(f"\n  Clan Mother: {'All clear' if result['clan_mother']['all_clear'] else 'Warnings issued'}")

    print(f"\n" + "=" * 60)
    print(f"  Each knight heard what came before.")
    print(f"  Each knight spoke from their real weapon.")
    print(f"  The Clan Mother watched every invocation.")
    print(f"  Dissent is preserved. The conversation is the record.")
    print(f"=" * 60 + "\n")


if __name__ == "__main__":
    demo()
