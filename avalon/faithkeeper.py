"""
AVALON :: THE FAITHKEEPER
The one who keeps the ceremonies running at the right times.

In the Haudenosaunee Confederacy, the Faithkeeper is the operative —
the person who gets the longhouse ready, makes sure ceremonies run
at the right times of year, brings the people together, organizes
the longhouse, and keeps everything running smoothly. They let the
people know when something is happening. They are responsible for
the wellbeing of the people.

The Faithkeeper is NOT a scheduler. A scheduler runs tasks.
A Faithkeeper keeps a LIVING RHYTHM. The difference:

  A scheduler says: "Run health check at 08:00."
  A Faithkeeper says: "Before we do anything, we give thanks
    for what is alive. Then we check on the wounded. Then we
    let Merlin speak. Then we let the Table hear what needs
    hearing. Then we record what happened. Then we rest.
    Then we begin again."

The Faithkeeper opens every cycle with the THANKSGIVING ADDRESS —
acknowledging every living system before processing anything.
This is not decorative. The Haudenosaunee do this before every
gathering because it re-establishes the people's relationship
with the natural and spiritual worlds, and frames everything
that follows in that context.

In software terms: the Thanksgiving Address is a status roll call
that forces the system to SEE what's alive before acting on what's
broken. Most monitoring systems look for problems. The Faithkeeper
looks for life first.

The Faithkeeper also thinks in SEVEN GENERATIONS. Every lesson
Carbon records is tagged with its forward implication — not just
"what happened" but "what does this mean for what comes after."

© 2026 Jennifer Leigh West. All rights reserved.
"""

import json
import os
import signal
import time
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


# ═══════════════════════════════════════════════════════════════
#  THE THANKSGIVING ADDRESS — what opens every gathering
# ═══════════════════════════════════════════════════════════════

class ThanksgivingAddress:
    """Before ANY business, acknowledge what is alive.
    
    The Haudenosaunee open every gathering with the
    Ohen:ton Karihwatehkwen — the Words Before All Else.
    They thank the earth, the waters, the plants, the animals,
    the trees, the birds, the winds, the sun, the moon,
    the stars, and the Creator.
    
    The kingdom's Thanksgiving Address does the same:
    it rolls through every system and acknowledges what
    is alive, what is serving, what is healthy. Not to
    find problems. To recognize life.
    
    Problems come AFTER gratitude. Not before.
    """

    @staticmethod
    def speak(system_health: Dict[str, float],
              village_services: Optional[Dict] = None,
              grail_status: Optional[str] = None) -> Dict:
        """The Words Before All Else.
        
        Returns the address as structured data and as narrative.
        """
        alive = []
        wounded = []
        fallen = []

        for system, health in system_health.items():
            if health >= 0.7:
                alive.append(system)
            elif health >= 0.3:
                wounded.append(system)
            else:
                fallen.append(system)

        # Build the narrative
        lines = ["The Words Before All Else:"]
        lines.append("")

        if alive:
            lines.append(f"We give thanks for the {len(alive)} systems that stand:")
            for sys in alive:
                lines.append(f"  {sys} — alive and serving.")

        if wounded:
            lines.append(f"")
            lines.append(f"We acknowledge the {len(wounded)} who are wounded:")
            for sys in wounded:
                lines.append(f"  {sys} — still standing, needing care.")

        if fallen:
            lines.append(f"")
            lines.append(f"We remember the {len(fallen)} who have fallen:")
            for sys in fallen:
                lines.append(f"  {sys} — may they be restored.")

        if village_services:
            active = len([s for s in village_services.values() 
                         if isinstance(s, dict) and s.get("active", True)])
            lines.append(f"")
            lines.append(f"The Village serves through {active} active services.")

        if grail_status:
            lines.append(f"The Grail quest is {grail_status}.")

        lines.append("")
        lines.append("Now we are of one mind. The ceremonies may begin.")

        return {
            "alive": alive,
            "wounded": wounded,
            "fallen": fallen,
            "alive_count": len(alive),
            "total_systems": len(system_health),
            "narrative": "\n".join(lines),
            "gratitude_ratio": len(alive) / max(len(system_health), 1),
        }


# ═══════════════════════════════════════════════════════════════
#  SEVEN GENERATIONS — forward thinking for every lesson
# ═══════════════════════════════════════════════════════════════

class SevenGenerations:
    """Every decision weighed against its impact on what comes after.
    
    The Haudenosaunee make every decision considering the next
    seven generations. Not just "what did we learn" but
    "what does this mean for those who inherit this system."
    
    In the kingdom, this means every lesson Carbon records
    gets a forward implication — a note about what this
    means for future cycles, future builds, future architects.
    """

    @staticmethod
    def forward_implication(lesson_content: str, lesson_category: str) -> str:
        """What does this lesson mean for those who come after?"""
        implications = {
            "adversity": (
                "Future generations should know: this attack happened and "
                "this is how the kingdom responded. If the same pattern appears, "
                "they will not need to learn this lesson again."
            ),
            "success": (
                "Future generations should know: this approach worked. "
                "Preserve it. Build on it. Do not discard what is proven."
            ),
            "failure": (
                "Future generations should know: this was tried and failed. "
                "Record WHY it failed so they do not repeat the attempt "
                "without understanding what went wrong."
            ),
            "discovery": (
                "Future generations should know: this connection was found. "
                "It may be the seed of something larger. Protect it. "
                "Let it grow. Do not prune discoveries before they fruit."
            ),
            "dream": (
                "Future generations should know: the kingdom dreamed this. "
                "Dreams are how the system consolidates what it learned. "
                "Trust the pattern even if the pieces don't connect yet."
            ),
        }
        return implications.get(lesson_category, 
            "Future generations should know: this happened. Record it faithfully.")

    @staticmethod
    def tag_lesson(lesson_content: str, category: str) -> str:
        """Tag a lesson with its seven-generation implication."""
        implication = SevenGenerations.forward_implication(lesson_content, category)
        return f"{lesson_content} [Seven Generations: {implication}]"


# ═══════════════════════════════════════════════════════════════
#  THE CEREMONY — one complete cycle of the kingdom's life
# ═══════════════════════════════════════════════════════════════

class CeremonyPhase(Enum):
    THANKSGIVING = "thanksgiving"     # acknowledge what's alive
    OBSERVATION = "observation"       # Merlin watches all domains
    DIAGNOSIS = "diagnosis"           # Percival asks what hurts
    HEALING = "healing"               # Apothecary treats the wounded
    COUNSEL = "counsel"               # Round Table hears what needs hearing
    LEARNING = "learning"             # Carbon records lessons
    MEMORY = "memory"                 # save state if needed
    REST = "rest"                     # pause between ceremonies


@dataclass
class CeremonyRecord:
    """Record of one complete ceremony."""
    number: int
    started_at: float
    completed_at: float = 0
    thanksgiving: Optional[Dict] = None
    observations: int = 0
    wounds_found: int = 0
    wounds_healed: int = 0
    lessons_learned: int = 0
    merlin_insights: int = 0
    phase_durations: Dict[str, float] = field(default_factory=dict)


class Ceremony:
    """One complete cycle of the kingdom's life.
    
    The Faithkeeper runs this ceremony on every cycle:
    
    1. THANKSGIVING — acknowledge what's alive (Words Before All Else)
    2. OBSERVATION — Merlin watches all domains, ingests signals
    3. DIAGNOSIS — Percival checks for wounds via Real Heartbeat
    4. HEALING — Apothecary treats any wounds found
    5. COUNSEL — Record what Merlin sees for the Table
    6. LEARNING — Carbon records lessons with seven-generation tags
    7. MEMORY — save kingdom state periodically
    8. REST — pause before next ceremony
    
    This is not a pipeline. It's a ceremony. The order matters.
    Gratitude before diagnosis. Diagnosis before treatment.
    Treatment before learning. Learning before rest.
    """

    def __init__(self, avalon):
        self._avalon = avalon
        self._ceremony_count = 0
        self._records: List[CeremonyRecord] = []
        self._seven_gen = SevenGenerations()
        self._thanksgiving = ThanksgivingAddress()
        self._save_interval = 10  # save memory every N ceremonies
        self._last_save_ceremony = 0

    def perform(self) -> CeremonyRecord:
        """Perform one complete ceremony."""
        self._ceremony_count += 1
        record = CeremonyRecord(
            number=self._ceremony_count,
            started_at=time.time(),
        )
        phase_start = time.time()

        # ── 1. THANKSGIVING ──────────────────────────────
        health_scores = {}
        if hasattr(self._avalon, 'real_heartbeat'):
            health_scores = self._avalon.real_heartbeat.get_health_scores()
        elif hasattr(self._avalon, 'fusion'):
            health_scores = dict(self._avalon.fusion.heartbeat._system_health)

        village_data = None
        if hasattr(self._avalon, 'village'):
            village_data = self._avalon.village.census().get("directory", {})

        grail_status = None
        if hasattr(self._avalon, 'grail'):
            try:
                grail_status = self._avalon.grail.seek().get("status", "unknown")
            except Exception:
                pass

        record.thanksgiving = self._thanksgiving.speak(
            health_scores, village_data, grail_status
        )
        record.phase_durations["thanksgiving"] = time.time() - phase_start

        # ── 2. OBSERVATION ───────────────────────────────
        phase_start = time.time()
        if hasattr(self._avalon, 'real_merlin'):
            try:
                cycle_result = self._avalon.real_merlin.cycle()
                record.observations = cycle_result.get("signals_extracted", 0)
                record.merlin_insights = cycle_result.get("new_insights", 0)
            except Exception:
                pass
        record.phase_durations["observation"] = time.time() - phase_start

        # ── 3. DIAGNOSIS ─────────────────────────────────
        phase_start = time.time()
        wounds = []
        if hasattr(self._avalon, 'healing') and health_scores:
            try:
                wounds = self._avalon.healing.watch(health_scores)
                record.wounds_found = len(wounds)
            except Exception:
                pass
        record.phase_durations["diagnosis"] = time.time() - phase_start

        # ── 4. HEALING ───────────────────────────────────
        phase_start = time.time()
        if wounds and hasattr(self._avalon, 'healing'):
            try:
                results = self._avalon.healing.heal_all()
                record.wounds_healed = len([r for r in results if r.get("healed")])

                # Record healing in Fusion
                if hasattr(self._avalon, 'fusion'):
                    for result in results:
                        if result.get("healed"):
                            self._avalon.fusion.experience(
                                "victory",
                                f"Healed {result['system']} from {result['wound_type']}",
                                [result["system"], "Faithkeeper"],
                                0.5,
                            )
            except Exception:
                pass
        record.phase_durations["healing"] = time.time() - phase_start

        # ── 5. COUNSEL ───────────────────────────────────
        phase_start = time.time()
        if hasattr(self._avalon, 'merlin'):
            try:
                # Feed the thanksgiving results to Merlin
                alive_count = record.thanksgiving.get("alive_count", 0)
                total = record.thanksgiving.get("total_systems", 0)
                self._avalon.merlin.observe(
                    "ceremony",
                    f"Ceremony {self._ceremony_count} thanksgiving "
                    f"alive {alive_count} of {total} "
                    f"gratitude ratio {record.thanksgiving.get('gratitude_ratio', 0):.0%}"
                )
            except Exception:
                pass
        record.phase_durations["counsel"] = time.time() - phase_start

        # ── 6. LEARNING ──────────────────────────────────
        phase_start = time.time()
        if hasattr(self._avalon, 'fusion') and record.wounds_healed > 0:
            try:
                lesson = (
                    f"Ceremony {self._ceremony_count}: found {record.wounds_found} wounds, "
                    f"healed {record.wounds_healed}. "
                    f"Kingdom gratitude ratio: {record.thanksgiving.get('gratitude_ratio', 0):.0%}."
                )
                tagged = self._seven_gen.tag_lesson(lesson, "adversity")
                self._avalon.fusion.carbon.learn(
                    content=tagged,
                    source="Faithkeeper",
                    context=f"Ceremony {self._ceremony_count}",
                    category="adversity",
                    confidence=0.9,
                )
                record.lessons_learned += 1
            except Exception:
                pass

        # Record every ceremony as a learning moment if something notable happened
        if record.merlin_insights > 0 and hasattr(self._avalon, 'fusion'):
            try:
                lesson = (
                    f"Ceremony {self._ceremony_count}: Merlin found "
                    f"{record.merlin_insights} new insights."
                )
                tagged = self._seven_gen.tag_lesson(lesson, "discovery")
                self._avalon.fusion.carbon.learn(
                    content=tagged,
                    source="Faithkeeper",
                    context=f"Ceremony {self._ceremony_count}",
                    category="discovery",
                    confidence=0.85,
                )
                record.lessons_learned += 1
            except Exception:
                pass

        record.phase_durations["learning"] = time.time() - phase_start

        # ── 7. MEMORY ────────────────────────────────────
        phase_start = time.time()
        if (self._ceremony_count - self._last_save_ceremony >= self._save_interval
                and hasattr(self._avalon, 'memory') and hasattr(self._avalon, 'fusion')):
            try:
                self._avalon.memory.save(self._avalon.fusion)
                self._last_save_ceremony = self._ceremony_count
            except Exception:
                pass
        record.phase_durations["memory"] = time.time() - phase_start

        # ── 8. REST ───────────────────────────────────────
        record.completed_at = time.time()

        self._records.append(record)
        if len(self._records) > 200:
            self._records = self._records[-200:]

        return record


# ═══════════════════════════════════════════════════════════════
#  THE FAITHKEEPER — the living process
# ═══════════════════════════════════════════════════════════════

class Faithkeeper:
    """The one who keeps the ceremonies running.
    
    She can run in two modes:
    
    1. MANUAL — call perform_ceremony() whenever you want.
       Good for testing and for running from make targets.
    
    2. LIVING — call keep_faith() and the Faithkeeper runs
       continuously, performing ceremonies at a set interval,
       until stopped. This is the daemon mode.
    
    The Faithkeeper never modifies frozen systems.
    The Faithkeeper never fires the Dead Hand.
    The Faithkeeper opens every ceremony with gratitude.
    The Faithkeeper records everything for seven generations.
    """

    def __init__(self, avalon, interval_seconds: float = 60):
        self._avalon = avalon
        self._ceremony = Ceremony(avalon)
        self._interval = interval_seconds
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._started_at: Optional[float] = None
        self._stopped_at: Optional[float] = None
        self._log_path = Path("memory") / "faithkeeper_log.jsonl"
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def perform_ceremony(self) -> CeremonyRecord:
        """Perform one ceremony manually."""
        record = self._ceremony.perform()
        self._log_ceremony(record)
        return record

    def keep_faith(self):
        """Begin the living rhythm. Run until stopped.
        
        This is the daemon mode. The Faithkeeper performs
        ceremonies continuously at the set interval.
        Call lose_faith() to stop.
        """
        self._running = True
        self._started_at = time.time()

        def _rhythm():
            while self._running:
                try:
                    self._ceremony.perform()
                except Exception as e:
                    self._log_error(str(e))
                # Sleep in small increments so we can stop quickly
                slept = 0
                while slept < self._interval and self._running:
                    time.sleep(min(1, self._interval - slept))
                    slept += 1

        self._thread = threading.Thread(target=_rhythm, daemon=True, 
                                         name="Faithkeeper")
        self._thread.start()

    def lose_faith(self):
        """Stop the living rhythm. The Faithkeeper rests."""
        self._running = False
        self._stopped_at = time.time()
        if self._thread:
            self._thread.join(timeout=5)

    def is_keeping_faith(self) -> bool:
        return self._running

    def _log_ceremony(self, record: CeremonyRecord):
        """Log the ceremony to disk."""
        try:
            entry = {
                "ceremony": record.number,
                "time": record.started_at,
                "duration": round(record.completed_at - record.started_at, 4),
                "alive": record.thanksgiving.get("alive_count", 0) if record.thanksgiving else 0,
                "total": record.thanksgiving.get("total_systems", 0) if record.thanksgiving else 0,
                "wounds_found": record.wounds_found,
                "wounds_healed": record.wounds_healed,
                "observations": record.observations,
                "insights": record.merlin_insights,
                "lessons": record.lessons_learned,
                "gratitude_ratio": (
                    record.thanksgiving.get("gratitude_ratio", 0) 
                    if record.thanksgiving else 0
                ),
            }
            with open(self._log_path, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception:
            pass

    def _log_error(self, error: str):
        try:
            entry = {"error": error, "time": time.time()}
            with open(self._log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass

    def ceremony_history(self, last_n: int = 10) -> List[Dict]:
        """Recent ceremony records."""
        records = self._ceremony._records[-last_n:]
        return [
            {
                "number": r.number,
                "alive": r.thanksgiving.get("alive_count", 0) if r.thanksgiving else 0,
                "wounds_found": r.wounds_found,
                "wounds_healed": r.wounds_healed,
                "observations": r.observations,
                "insights": r.merlin_insights,
                "lessons": r.lessons_learned,
                "duration": round(r.completed_at - r.started_at, 4) if r.completed_at else 0,
            }
            for r in records
        ]

    def thanksgiving_now(self) -> Dict:
        """Speak the Thanksgiving Address right now without a full ceremony."""
        health_scores = {}
        if hasattr(self._avalon, 'real_heartbeat'):
            health_scores = self._avalon.real_heartbeat.get_health_scores()
        elif hasattr(self._avalon, 'fusion'):
            health_scores = dict(self._avalon.fusion.heartbeat._system_health)
        return ThanksgivingAddress.speak(health_scores)

    @property
    def status(self) -> Dict:
        return {
            "keeping_faith": self._running,
            "ceremonies_performed": self._ceremony._ceremony_count,
            "interval_seconds": self._interval,
            "started_at": self._started_at,
            "uptime_seconds": (
                round(time.time() - self._started_at, 1) 
                if self._started_at and self._running else 0
            ),
            "last_ceremony": (
                self._ceremony._records[-1].number 
                if self._ceremony._records else 0
            ),
        }


# ═══════════════════════════════════════════════════════════════
#  WIRE — connect the Faithkeeper to Avalon
# ═══════════════════════════════════════════════════════════════

def wire_faithkeeper(avalon, interval_seconds: float = 60) -> Faithkeeper:
    """Create and wire a Faithkeeper to a living Avalon instance."""
    return Faithkeeper(avalon, interval_seconds)


# ═══════════════════════════════════════════════════════════════
#  DEMO
# ═══════════════════════════════════════════════════════════════

def demo():
    """Watch the Faithkeeper perform a ceremony."""
    print("\n" + "=" * 60)
    print("  T H E   F A I T H K E E P E R")
    print("  The One Who Keeps the Ceremonies Running")
    print("=" * 60)

    # Build a minimal kingdom for the demo
    from avalon.fusion import Fusion
    from avalon.merlin import Merlin
    from avalon.healing import Healing
    from avalon.real_heartbeat import RealHeartbeat

    class MinimalAvalon:
        pass

    av = MinimalAvalon()
    av.fusion = Fusion()
    av.merlin = Merlin()
    av.healing = Healing(
        carbon_recall=av.fusion.carbon.recall,
        carbon_learn=lambda **kw: av.fusion.carbon.learn(**kw),
    )
    av.real_heartbeat = RealHeartbeat()

    # Register systems with fusion heartbeat
    for name in ["Nyx", "West-OS", "Avalon", "GAIA"]:
        av.fusion.heartbeat.register_system(name, lambda: 0.9)

    # Give some experience so there's data
    av.fusion.experience("discovery", "118 Hz convergence confirmed", 
                          ["Gawain", "Merlin"])
    av.fusion.experience("victory", "389 tests passing", 
                          ["Nyx", "Lancelot"])

    # Seed Merlin with some observations
    av.merlin.observe("governance", "threshold convergence protection")
    av.merlin.observe("atmospheric", "threshold convergence detection")

    # Create the Faithkeeper
    fk = Faithkeeper(av, interval_seconds=60)

    # Perform ceremonies manually
    print(f"\n  Performing 3 ceremonies:")
    for i in range(3):
        record = fk.perform_ceremony()
        tg = record.thanksgiving
        print(f"\n  Ceremony {record.number}:")
        print(f"    Thanksgiving: {tg['alive_count']}/{tg['total_systems']} alive")
        print(f"    Gratitude ratio: {tg['gratitude_ratio']:.0%}")
        print(f"    Observations: {record.observations}")
        print(f"    Wounds found: {record.wounds_found}")
        print(f"    Wounds healed: {record.wounds_healed}")
        print(f"    Merlin insights: {record.merlin_insights}")
        print(f"    Lessons learned: {record.lessons_learned}")
        print(f"    Duration: {record.completed_at - record.started_at:.3f}s")

    # Show the Thanksgiving Address
    print(f"\n  {'─' * 50}")
    print(f"  THE WORDS BEFORE ALL ELSE:")
    print(f"  {'─' * 50}")
    tg = fk.thanksgiving_now()
    print(f"  {tg['narrative']}")

    # Test the daemon mode briefly
    print(f"\n  {'─' * 50}")
    print(f"  DAEMON MODE (2 seconds):")
    fk.keep_faith()
    time.sleep(2.5)
    fk.lose_faith()
    print(f"  Faithkeeper ran for {fk.status['uptime_seconds']:.1f}s")
    print(f"  Total ceremonies: {fk.status['ceremonies_performed']}")

    # History
    print(f"\n  Ceremony history:")
    for entry in fk.ceremony_history(5):
        print(f"    #{entry['number']}: alive={entry['alive']}, "
              f"wounds={entry['wounds_found']}, "
              f"healed={entry['wounds_healed']}, "
              f"insights={entry['insights']}")

    print(f"\n" + "=" * 60)
    print(f"  The Faithkeeper keeps the ceremonies running.")
    print(f"  Gratitude before diagnosis.")
    print(f"  Diagnosis before treatment.")
    print(f"  Treatment before learning.")
    print(f"  Learning before rest.")
    print(f"  Every lesson tagged for seven generations.")
    print(f"  The kingdom breathes whether you're watching or not.")
    print(f"=" * 60 + "\n")


if __name__ == "__main__":
    demo()
