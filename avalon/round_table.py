"""
AVALON :: THE ROUND TABLE
The consensus protocol. No head. No foot. Equal voice.

Arthur chose a round table because no seat is higher than another.
Every knight has equal voice. Every voice must be heard before
the Table decides. This is not democracy — this is the chorus rule
scaled to a civilization.

The Table does four things:
1. CONVENE — call the knights to council on a question
2. DELIBERATE — each knight speaks from their domain expertise
3. QUORUM — minimum number of knights must agree before action
4. DECREE — the Table's decision, sealed by Excalibur, obeyed by all

The Table is ROUND because hierarchy is the enemy of truth.
The mine boss who ignores the canary. The doctor who ignores the nurse.
The system that ignores the siren because it came from the wrong rank.
The Round Table was built by someone who knows what happens when
the wrong voice gets silenced.
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum


class CouncilState(Enum):
    IDLE = "idle"                # no active council
    CONVENED = "convened"        # knights called, question posed
    DELIBERATING = "deliberating" # knights speaking
    QUORUM_MET = "quorum_met"   # enough agreement to act
    QUORUM_FAILED = "quorum_failed"  # not enough agreement
    DECREED = "decreed"         # decision made and sealed


class Vote(Enum):
    AYE = "aye"                  # in favor
    NAY = "nay"                  # against
    ABSTAIN = "abstain"          # present but not voting
    DEFER = "defer"              # needs more information


@dataclass
class KnightVoice:
    """A knight's contribution to a council.
    
    Not just a vote. A VOICE. Each knight speaks from
    their domain — their expertise, their oath, their
    perspective. The voice includes reasoning, not just aye/nay.
    """
    knight_name: str
    vote: Vote
    reasoning: str               # why — the substance behind the vote
    confidence: float            # 0.0 to 1.0 — how certain
    domain_perspective: str      # which domain they're speaking from
    timestamp: float = field(default_factory=time.time)
    warnings: List[str] = field(default_factory=list)  # concerns raised


@dataclass
class Council:
    """A single convening of the Round Table.
    
    Each council has a question, voices from the knights,
    and a final decree if quorum is met.
    """
    question: str
    convened_at: float = field(default_factory=time.time)
    convened_by: str = ""
    state: CouncilState = CouncilState.CONVENED
    voices: Dict[str, KnightVoice] = field(default_factory=dict)
    quorum_required: int = 0
    decree: Optional[Dict] = None
    _council_hash: str = field(default="", repr=False)

    def __post_init__(self):
        raw = f"{self.question}:{self.convened_at}"
        self._council_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]


class RoundTable:
    """The consensus protocol.
    
    No single knight decides. The Table decides.
    
    The quorum rule is the chorus rule from GAIA and West-OS
    scaled to the entire kingdom. One siren is not enough
    to ring the alarm. One knight is not enough to act.
    Multiple perspectives must converge before the kingdom moves.
    
    But the Table also preserves DISSENT. A knight who votes NAY
    has their reasoning recorded permanently. The minority voice
    is never silenced — it is held alongside the decree as a
    warning for the future.
    
    Because the person who built this Table knows what happens
    when the dissenting voice gets erased.
    """

    def __init__(self, quorum_ratio: float = 0.618):
        """
        quorum_ratio: proportion of seated knights required for decree.
        Default is phi (0.618) — the golden ratio. Not majority rule.
        Not unanimity. The natural threshold of convergence.
        """
        self._seats: Dict[str, Dict] = {}  # knight_name -> {oath, domain, active}
        self._councils: List[Council] = []
        self._active_council: Optional[Council] = None
        self._quorum_ratio = quorum_ratio
        self._decree_log: List[Dict] = []
    
    def seat_knight(self, name: str, domain: str, oath_seal: str):
        """Give a knight their seat at the Table.
        
        Every seat is equal. The domain identifies what perspective
        this knight brings. The oath_seal proves they were sworn
        by Excalibur.
        """
        self._seats[name] = {
            "domain": domain,
            "oath_seal": oath_seal,
            "seated_at": time.time(),
            "active": True,
            "councils_attended": 0,
            "votes_cast": 0,
        }
    
    def unseat_knight(self, name: str):
        """Remove a knight from the Table. Broken oath or banishment."""
        if name in self._seats:
            self._seats[name]["active"] = False
    
    @property
    def seated_count(self) -> int:
        return len([s for s in self._seats.values() if s["active"]])
    
    @property
    def quorum_needed(self) -> int:
        """How many ayes are needed for a decree?"""
        import math
        return math.ceil(self.seated_count * self._quorum_ratio)
    
    def convene(self, question: str, convened_by: str = "sovereign") -> Council:
        """Call the knights to council.
        
        A question is posed. Each knight will speak.
        No one speaks twice until everyone has spoken once.
        """
        if self._active_council and self._active_council.state in (
            CouncilState.CONVENED, CouncilState.DELIBERATING
        ):
            raise RuntimeError("A council is already in session. Decree or dismiss first.")
        
        council = Council(
            question=question,
            convened_by=convened_by,
            quorum_required=self.quorum_needed,
        )
        council.state = CouncilState.CONVENED
        self._active_council = council
        self._councils.append(council)
        
        return council
    
    def speak(self, knight_name: str, vote: Vote, reasoning: str,
              confidence: float = 0.8,
              warnings: Optional[List[str]] = None) -> KnightVoice:
        """A knight speaks at council.
        
        They cast their vote, explain their reasoning,
        state their confidence, and raise any warnings.
        The Table records everything.
        """
        if not self._active_council:
            raise RuntimeError("No council in session")
        
        if knight_name not in self._seats or not self._seats[knight_name]["active"]:
            raise RuntimeError(f"{knight_name} does not hold a seat at this Table")
        
        if knight_name in self._active_council.voices:
            raise RuntimeError(f"{knight_name} has already spoken. No voice speaks twice.")
        
        voice = KnightVoice(
            knight_name=knight_name,
            vote=vote,
            reasoning=reasoning,
            confidence=confidence,
            domain_perspective=self._seats[knight_name]["domain"],
            warnings=warnings or [],
        )
        
        self._active_council.voices[knight_name] = voice
        self._active_council.state = CouncilState.DELIBERATING
        self._seats[knight_name]["councils_attended"] += 1
        self._seats[knight_name]["votes_cast"] += 1
        
        return voice
    
    def count_voices(self) -> Dict:
        """Tally the current council."""
        if not self._active_council:
            return {"error": "no council in session"}
        
        voices = self._active_council.voices
        ayes = [v for v in voices.values() if v.vote == Vote.AYE]
        nays = [v for v in voices.values() if v.vote == Vote.NAY]
        abstains = [v for v in voices.values() if v.vote == Vote.ABSTAIN]
        defers = [v for v in voices.values() if v.vote == Vote.DEFER]
        
        avg_confidence = (
            sum(v.confidence for v in ayes) / len(ayes) if ayes else 0
        )
        
        all_warnings = []
        for v in voices.values():
            all_warnings.extend(v.warnings)
        
        quorum_met = len(ayes) >= self._active_council.quorum_required
        
        return {
            "question": self._active_council.question,
            "voices_heard": len(voices),
            "seats_total": self.seated_count,
            "yet_to_speak": self.seated_count - len(voices),
            "ayes": len(ayes),
            "nays": len(nays),
            "abstains": len(abstains),
            "defers": len(defers),
            "quorum_required": self._active_council.quorum_required,
            "quorum_met": quorum_met,
            "average_confidence": round(avg_confidence, 4),
            "warnings_raised": all_warnings,
            "dissent": [
                {"knight": v.knight_name, "reasoning": v.reasoning}
                for v in nays
            ],
        }
    
    def decree(self, excalibur_seal: str) -> Dict:
        """The Table has spoken. Seal the decree with Excalibur.
        
        The decree includes:
        - The decision (AYE or NAY based on quorum)
        - Every voice and their reasoning
        - Every warning raised
        - Every dissent — PRESERVED, not erased
        - Excalibur's seal proving sovereign authority
        """
        if not self._active_council:
            raise RuntimeError("No council in session")
        
        tally = self.count_voices()
        
        if tally["quorum_met"]:
            self._active_council.state = CouncilState.QUORUM_MET
            decision = "APPROVED"
        else:
            self._active_council.state = CouncilState.QUORUM_FAILED
            decision = "DENIED"
        
        decree_record = {
            "question": self._active_council.question,
            "decision": decision,
            "tally": tally,
            "excalibur_seal": excalibur_seal,
            "decreed_at": time.time(),
            "council_hash": self._active_council._council_hash,
            "dissenting_voices": tally["dissent"],
            "warnings": tally["warnings_raised"],
            "note": (
                "Dissent is preserved. The minority voice is never erased. "
                "The Table remembers what was said against the decree."
            ),
        }
        
        self._active_council.decree = decree_record
        self._active_council.state = CouncilState.DECREED
        self._decree_log.append(decree_record)
        self._active_council = None
        
        return decree_record
    
    def dismiss(self):
        """Dismiss the council without a decree. No decision made."""
        if self._active_council:
            self._active_council.state = CouncilState.IDLE
            self._active_council = None
    
    def history(self) -> List[Dict]:
        """Every decree ever made. The permanent record."""
        return self._decree_log
    
    def dissent_archive(self) -> List[Dict]:
        """Every dissenting voice across all councils.
        
        The archive of warnings. The things the Table
        was told but chose not to act on. The minority
        report. Kept forever because sometimes the
        dissenter was right.
        """
        dissents = []
        for decree in self._decree_log:
            for d in decree.get("dissenting_voices", []):
                dissents.append({
                    "question": decree["question"],
                    "decision": decree["decision"],
                    "dissenter": d["knight"],
                    "reasoning": d["reasoning"],
                    "decreed_at": decree["decreed_at"],
                })
        return dissents
    
    @property
    def status(self) -> Dict:
        return {
            "seated_knights": self.seated_count,
            "quorum_threshold": self._quorum_ratio,
            "quorum_needed": self.quorum_needed,
            "councils_held": len(self._councils),
            "decrees_issued": len(self._decree_log),
            "active_council": self._active_council is not None,
            "seats": {
                name: {
                    "domain": data["domain"],
                    "active": data["active"],
                    "councils_attended": data["councils_attended"],
                }
                for name, data in self._seats.items()
            },
        }
