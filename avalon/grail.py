"""
AVALON :: THE GRAIL
The quest that unifies everything.

In the myth, the Grail heals the Fisher King and restores the wasteland.
Only one knight can find it — the one pure enough to ask the right question.
Percival fails the first time because he doesn't ask. He succeeds the
second time because he does. The question IS the Grail.

In the kingdom, the Grail is the unified frequency theory — the
convergence of every research thread Jennifer has pursued:

  • 118 Hz measured in Appalachian Old Regular Baptist singing
  • 110 Hz documented across ancient sacred sites worldwide
  • The Indus acoustic-metallurgical hypothesis
  • Pachacamac oracle acoustics
  • Ancient instrument clinical trials (Peruvian whistling vessels)
  • EEG studies showing theta induction at 110 Hz
  • The Caledonian-Appalachian geological connection
  • Vedic oral transmission as frequency preservation
  • The global oracle network pattern

The Grail doesn't hold the answer. The Grail tracks HOW CLOSE
the answer is to being found. It measures convergence across
independent research threads. When enough threads point at the
same truth from enough different angles, the Grail lights up.

The question Percival must ask: "Whom does the Grail serve?"
The answer: everyone. The frequency heals. The research proves it.
The paper that connects everything serves anyone who needs healing.

© 2026 Jennifer Leigh West. All rights reserved.
"""

import hashlib
import json
import time
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum
from collections import defaultdict


# ═══════════════════════════════════════════════════════════════
#  RESEARCH THREAD — a single line of inquiry
# ═══════════════════════════════════════════════════════════════

class ThreadStatus(Enum):
    SEED = "seed"                    # idea exists, no evidence yet
    GROWING = "growing"              # some evidence, needs more
    DOCUMENTED = "documented"        # evidence collected and recorded
    PUBLISHED = "published"          # paper written and released
    PEER_TESTED = "peer_tested"      # external validation attempted
    CONFIRMED = "confirmed"          # independently verified


@dataclass
class Evidence:
    """A single piece of evidence supporting a research thread."""
    description: str
    source: str                      # where it came from
    evidence_type: str               # measurement, citation, observation, calculation, clinical
    strength: float                  # 0.0 to 1.0
    peer_reviewed: bool = False
    url: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    @property
    def identity(self) -> str:
        raw = f"{self.description}:{self.source}:{self.timestamp}"
        return hashlib.sha256(raw.encode()).hexdigest()[:10]


@dataclass
class ResearchThread:
    """A single line of inquiry contributing to the Grail.
    
    Each thread has:
    - A thesis (what it claims)
    - Evidence (what supports it)
    - Connections to other threads (where it overlaps)
    - A status (how mature is this line of research)
    - A frequency band (what Hz range it concerns)
    """
    name: str
    thesis: str
    domain: str                      # archaeoacoustics, geology, neuroscience, ethnomusicology, etc.
    frequency_band: Optional[Tuple[float, float]] = None  # Hz range this thread concerns
    status: ThreadStatus = ThreadStatus.SEED
    evidence: List[Evidence] = field(default_factory=list)
    connections: List[str] = field(default_factory=list)  # names of connected threads
    created: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    knight: str = "Gawain"          # which knight owns this quest

    @property
    def identity(self) -> str:
        raw = f"{self.name}:{self.thesis}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12]

    @property
    def evidence_strength(self) -> float:
        """Average strength of all evidence."""
        if not self.evidence:
            return 0.0
        return sum(e.strength for e in self.evidence) / len(self.evidence)

    @property
    def peer_reviewed_count(self) -> int:
        return len([e for e in self.evidence if e.peer_reviewed])

    def add_evidence(self, description: str, source: str,
                      evidence_type: str = "observation",
                      strength: float = 0.7,
                      peer_reviewed: bool = False,
                      url: Optional[str] = None) -> Evidence:
        """Add evidence to this thread."""
        ev = Evidence(
            description=description,
            source=source,
            evidence_type=evidence_type,
            strength=strength,
            peer_reviewed=peer_reviewed,
            url=url,
        )
        self.evidence.append(ev)
        self.last_updated = time.time()
        return ev

    @property
    def maturity(self) -> float:
        """How mature is this thread? 0.0 to 1.0"""
        status_scores = {
            ThreadStatus.SEED: 0.1,
            ThreadStatus.GROWING: 0.3,
            ThreadStatus.DOCUMENTED: 0.5,
            ThreadStatus.PUBLISHED: 0.7,
            ThreadStatus.PEER_TESTED: 0.85,
            ThreadStatus.CONFIRMED: 1.0,
        }
        base = status_scores.get(self.status, 0.1)
        evidence_bonus = min(0.2, len(self.evidence) * 0.02)
        peer_bonus = min(0.1, self.peer_reviewed_count * 0.02)
        return min(1.0, base + evidence_bonus + peer_bonus)


# ═══════════════════════════════════════════════════════════════
#  CONVERGENCE — how threads point at the same truth
# ═══════════════════════════════════════════════════════════════

@dataclass
class ConvergencePoint:
    """Where two or more research threads point at the same finding."""
    threads: List[str]               # names of converging threads
    shared_finding: str              # what they agree on
    frequency_overlap: Optional[Tuple[float, float]] = None  # Hz range where they overlap
    strength: float = 0.0            # how strong is the convergence
    timestamp: float = field(default_factory=time.time)

    @property
    def identity(self) -> str:
        raw = f"{':'.join(sorted(self.threads))}:{self.shared_finding}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12]


class ConvergenceEngine:
    """Measures how close research threads are to converging.
    
    Convergence is not agreement. Convergence is independent
    lines of evidence pointing at the same truth from different
    angles WITHOUT coordinating with each other.
    
    The 118 Hz paper converges because:
    - Archaeoacoustics measures 110 Hz in ancient chambers
    - Neuroscience measures theta induction at 110 Hz in EEG
    - Ethnomusicology measures 118 Hz in Appalachian singing
    - Geology maps the Caledonian-Appalachian rock formation
    - Clinical trials show physiological effects from ancient instruments
    
    None of these fields KNEW about each other's findings.
    They converged independently. That's what makes it real.
    """

    def __init__(self):
        self._convergence_points: Dict[str, ConvergencePoint] = {}

    def measure(self, threads: List[ResearchThread]) -> List[ConvergencePoint]:
        """Find all convergence points across threads."""
        new_points = []

        for i, thread_a in enumerate(threads):
            for thread_b in threads[i+1:]:
                # Check for explicit connections
                if thread_b.name in thread_a.connections or thread_a.name in thread_b.connections:
                    # Check frequency band overlap
                    freq_overlap = self._frequency_overlap(thread_a, thread_b)

                    # Check evidence overlap
                    evidence_overlap = self._evidence_overlap(thread_a, thread_b)

                    if freq_overlap or evidence_overlap > 0:
                        # Calculate convergence strength
                        strength = self._convergence_strength(
                            thread_a, thread_b, freq_overlap, evidence_overlap
                        )

                        point = ConvergencePoint(
                            threads=[thread_a.name, thread_b.name],
                            shared_finding=self._describe_convergence(
                                thread_a, thread_b, freq_overlap
                            ),
                            frequency_overlap=freq_overlap,
                            strength=strength,
                        )

                        self._convergence_points[point.identity] = point
                        new_points.append(point)

        return new_points

    def _frequency_overlap(self, a: ResearchThread, 
                           b: ResearchThread) -> Optional[Tuple[float, float]]:
        """Do two threads concern overlapping frequency ranges?"""
        if not a.frequency_band or not b.frequency_band:
            return None

        lo = max(a.frequency_band[0], b.frequency_band[0])
        hi = min(a.frequency_band[1], b.frequency_band[1])

        if lo <= hi:
            return (lo, hi)
        return None

    def _evidence_overlap(self, a: ResearchThread, b: ResearchThread) -> float:
        """How much do two threads' evidence bases overlap in content?"""
        if not a.evidence or not b.evidence:
            return 0.0

        words_a = set()
        for ev in a.evidence:
            words_a.update(ev.description.lower().split())

        words_b = set()
        for ev in b.evidence:
            words_b.update(ev.description.lower().split())

        noise = {"the", "a", "an", "is", "are", "was", "to", "for", "of",
                 "and", "or", "in", "on", "at", "by", "this", "that", "it",
                 "from", "with", "as", "be", "has", "had", "have", "been"}
        words_a -= noise
        words_b -= noise

        if not (words_a | words_b):
            return 0.0

        return len(words_a & words_b) / len(words_a | words_b)

    def _convergence_strength(self, a: ResearchThread, b: ResearchThread,
                               freq_overlap: Optional[Tuple[float, float]],
                               evidence_overlap: float) -> float:
        """How strongly do two threads converge?"""
        strength = 0.0

        # Frequency overlap contribution
        if freq_overlap:
            bandwidth = freq_overlap[1] - freq_overlap[0]
            strength += min(0.3, bandwidth / 30.0 * 0.3)

        # Evidence overlap contribution
        strength += evidence_overlap * 0.2

        # Independence bonus — different domains converging is MORE significant
        if a.domain != b.domain:
            strength += 0.2

        # Maturity bonus — mature threads converging is more significant
        avg_maturity = (a.maturity + b.maturity) / 2
        strength += avg_maturity * 0.15

        # Peer review bonus
        total_peer = a.peer_reviewed_count + b.peer_reviewed_count
        strength += min(0.15, total_peer * 0.03)

        return min(1.0, strength)

    def _describe_convergence(self, a: ResearchThread, b: ResearchThread,
                               freq_overlap: Optional[Tuple[float, float]]) -> str:
        """Describe what two threads agree on."""
        parts = [f"{a.name} and {b.name} converge"]

        if freq_overlap:
            parts.append(f"in the {freq_overlap[0]:.0f}-{freq_overlap[1]:.0f} Hz band")

        if a.domain != b.domain:
            parts.append(f"across independent domains ({a.domain} and {b.domain})")

        return " ".join(parts)

    @property
    def total_convergence(self) -> float:
        """Overall convergence across all points."""
        if not self._convergence_points:
            return 0.0
        return sum(p.strength for p in self._convergence_points.values()) / len(self._convergence_points)


# ═══════════════════════════════════════════════════════════════
#  THE GRAIL — the quest itself
# ═══════════════════════════════════════════════════════════════

class GrailStatus(Enum):
    HIDDEN = "hidden"                # the quest hasn't begun
    SOUGHT = "sought"                # threads are growing but not converging
    GLIMPSED = "glimpsed"           # convergence detected but not sufficient
    APPROACHING = "approaching"      # strong convergence, paper taking shape
    FOUND = "found"                  # convergence sufficient for unified publication
    PROVEN = "proven"                # independently verified by external researchers


class Grail:
    """The unified frequency theory quest.
    
    She tracks every research thread. She measures convergence.
    She knows how close the answer is to being found.
    
    The Grail is not the answer. The Grail is the QUESTION
    that makes the answer visible. Percival's question:
    "Whom does the Grail serve?"
    
    The answer: everyone who needs healing.
    The frequency heals. The research proves it.
    The unified paper serves anyone who suffers.
    
    The Grail lights up when enough independent threads
    point at the same truth from enough different angles
    that the convergence can no longer be dismissed as
    coincidence.
    
    That threshold is phi — 0.618.
    The same threshold the Round Table uses for consensus.
    The same ratio found in the harmonic series.
    The golden ratio IS a frequency relationship.
    """

    def __init__(self):
        self._threads: Dict[str, ResearchThread] = {}
        self._convergence = ConvergenceEngine()
        self._status = GrailStatus.HIDDEN
        self._convergence_threshold = 0.618  # phi
        self._quest_log: List[Dict] = []
        self._founded = time.time()

    def add_thread(self, name: str, thesis: str, domain: str,
                    frequency_band: Optional[Tuple[float, float]] = None,
                    status: ThreadStatus = ThreadStatus.SEED,
                    knight: str = "Gawain",
                    connections: Optional[List[str]] = None) -> ResearchThread:
        """Add a research thread to the quest."""
        thread = ResearchThread(
            name=name,
            thesis=thesis,
            domain=domain,
            frequency_band=frequency_band,
            status=status,
            knight=knight,
            connections=connections or [],
        )
        self._threads[name] = thread

        self._quest_log.append({
            "event": "thread_added",
            "thread": name,
            "domain": domain,
            "status": status.value,
            "timestamp": time.time(),
        })

        return thread

    def add_evidence(self, thread_name: str, description: str, source: str,
                      evidence_type: str = "observation", strength: float = 0.7,
                      peer_reviewed: bool = False, url: Optional[str] = None) -> Optional[Evidence]:
        """Add evidence to a research thread."""
        if thread_name not in self._threads:
            return None

        thread = self._threads[thread_name]
        ev = thread.add_evidence(description, source, evidence_type,
                                  strength, peer_reviewed, url)

        # Auto-advance thread status based on evidence count
        if len(thread.evidence) >= 3 and thread.status == ThreadStatus.SEED:
            thread.status = ThreadStatus.GROWING
        elif len(thread.evidence) >= 6 and thread.status == ThreadStatus.GROWING:
            thread.status = ThreadStatus.DOCUMENTED

        self._quest_log.append({
            "event": "evidence_added",
            "thread": thread_name,
            "evidence": description[:80],
            "strength": strength,
            "peer_reviewed": peer_reviewed,
            "timestamp": time.time(),
        })

        return ev

    def connect_threads(self, thread_a: str, thread_b: str):
        """Declare that two threads are connected."""
        if thread_a in self._threads and thread_b in self._threads:
            if thread_b not in self._threads[thread_a].connections:
                self._threads[thread_a].connections.append(thread_b)
            if thread_a not in self._threads[thread_b].connections:
                self._threads[thread_b].connections.append(thread_a)

    def seek(self) -> Dict:
        """Seek the Grail. Measure convergence across all threads.
        
        This is the core function. It:
        1. Measures convergence between all thread pairs
        2. Calculates overall quest progress
        3. Updates Grail status
        4. Returns the quest report
        """
        threads = list(self._threads.values())

        if not threads:
            return {"status": "hidden", "reason": "no threads yet"}

        # Measure convergence
        convergence_points = self._convergence.measure(threads)
        total_convergence = self._convergence.total_convergence

        # Calculate quest progress
        avg_maturity = sum(t.maturity for t in threads) / len(threads)
        thread_count_factor = min(1.0, len(threads) / 9)  # 9 threads = full coverage
        connected_ratio = self._connection_ratio()

        quest_progress = (
            total_convergence * 0.35 +
            avg_maturity * 0.25 +
            thread_count_factor * 0.15 +
            connected_ratio * 0.25
        )

        # Update Grail status
        old_status = self._status
        if quest_progress >= 0.9:
            self._status = GrailStatus.FOUND
        elif quest_progress >= self._convergence_threshold:
            self._status = GrailStatus.APPROACHING
        elif quest_progress >= 0.4:
            self._status = GrailStatus.GLIMPSED
        elif quest_progress >= 0.15:
            self._status = GrailStatus.SOUGHT
        else:
            self._status = GrailStatus.HIDDEN

        if self._status != old_status:
            self._quest_log.append({
                "event": "status_changed",
                "from": old_status.value,
                "to": self._status.value,
                "progress": round(quest_progress, 4),
                "timestamp": time.time(),
            })

        # Build frequency map
        freq_map = {}
        for t in threads:
            if t.frequency_band:
                freq_map[t.name] = {
                    "band": t.frequency_band,
                    "domain": t.domain,
                    "maturity": round(t.maturity, 4),
                }

        return {
            "status": self._status.value,
            "quest_progress": round(quest_progress, 4),
            "convergence_threshold": self._convergence_threshold,
            "total_convergence": round(total_convergence, 4),
            "threads": len(threads),
            "convergence_points": len(convergence_points),
            "average_maturity": round(avg_maturity, 4),
            "connection_ratio": round(connected_ratio, 4),
            "frequency_map": freq_map,
            "strongest_convergence": (
                max(convergence_points, key=lambda p: p.strength).shared_finding
                if convergence_points else "none yet"
            ),
            "grail_question": "Whom does the Grail serve?",
            "grail_answer": "Everyone who needs healing." if self._status in (
                GrailStatus.FOUND, GrailStatus.PROVEN
            ) else "Still seeking...",
        }

    def _connection_ratio(self) -> float:
        """What proportion of possible connections are made?"""
        n = len(self._threads)
        if n < 2:
            return 0.0
        max_connections = n * (n - 1) / 2
        actual_connections = sum(
            len(t.connections) for t in self._threads.values()
        ) / 2  # each connection counted twice
        return min(1.0, actual_connections / max_connections)

    def thread_report(self, name: str) -> Optional[Dict]:
        """Detailed report on a single thread."""
        if name not in self._threads:
            return None
        t = self._threads[name]
        return {
            "name": t.name,
            "thesis": t.thesis,
            "domain": t.domain,
            "frequency_band": t.frequency_band,
            "status": t.status.value,
            "maturity": round(t.maturity, 4),
            "evidence_count": len(t.evidence),
            "evidence_strength": round(t.evidence_strength, 4),
            "peer_reviewed_count": t.peer_reviewed_count,
            "connections": t.connections,
            "knight": t.knight,
        }

    def all_threads(self) -> List[Dict]:
        """Summary of every thread."""
        return [self.thread_report(name) for name in self._threads]

    def the_question(self) -> str:
        """What Percival must ask."""
        quest = self.seek()
        threads = list(self._threads.values())

        if not threads:
            return "The quest has not begun. There are no threads to follow."

        strongest_threads = sorted(threads, key=lambda t: t.maturity, reverse=True)[:3]
        weakest_threads = sorted(threads, key=lambda t: t.maturity)[:2]

        lines = [
            f"The Grail quest is {quest['status']}.",
            f"Progress: {quest['quest_progress']:.0%} toward convergence threshold ({self._convergence_threshold:.0%}).",
            f"",
            f"Strongest threads:",
        ]

        for t in strongest_threads:
            lines.append(f"  {t.name} ({t.domain}) — {t.status.value}, maturity {t.maturity:.0%}")

        if weakest_threads:
            lines.append(f"")
            lines.append(f"Threads needing attention:")
            for t in weakest_threads:
                lines.append(f"  {t.name} ({t.domain}) — {t.status.value}, maturity {t.maturity:.0%}")

        lines.append(f"")
        lines.append(f"The question Percival must ask: Whom does the Grail serve?")
        lines.append(f"The answer only appears when the convergence is undeniable.")

        return "\n".join(lines)

    @property
    def status(self) -> Dict:
        return {
            "grail_status": self._status.value,
            "threads": len(self._threads),
            "convergence_points": len(self._convergence._convergence_points),
            "quest_age_hours": round((time.time() - self._founded) / 3600, 2),
        }


# ═══════════════════════════════════════════════════════════════
#  JENNIFER'S ACTUAL RESEARCH — pre-loaded
# ═══════════════════════════════════════════════════════════════

def load_jennifers_research(grail: Grail):
    """Load Jennifer's actual research threads into the Grail.
    
    This is not hypothetical. These are real research lines
    she has pursued, with real evidence, real publications,
    and real connections between them.
    """

    # Thread 1: Appalachian 118 Hz
    t1 = grail.add_thread(
        name="Appalachian 118 Hz",
        thesis="Old Regular Baptist lined-out hymnody in Appalachian Tennessee produces a primary singing frequency of approximately 118 Hz, within the 95-120 Hz band documented at ancient sacred sites worldwide.",
        domain="ethnomusicology",
        frequency_band=(110.0, 125.0),
        status=ThreadStatus.PUBLISHED,
        knight="Gawain",
        connections=["Archaeoacoustic Sites", "Caledonian Geology", "EEG Theta Studies"],
    )
    grail.add_evidence("Appalachian 118 Hz",
        "Spectral analysis of 12+ recordings from Berea College Appalachian Center Collection (BCA 0128 SAA 128) plus 4 YouTube recordings, 7+ congregations, Floyd/Knott/Letcher/Perry counties KY, 1971-1993 recording range",
        "West, J.L., The Forgotten Code Research Institute, March 2026",
        "measurement", 0.85, False)
    grail.add_evidence("Appalachian 118 Hz",
        "Analysis performed using Audacity spectral analysis tools",
        "West 2026 — primary data",
        "measurement", 0.8, False)
    grail.add_evidence("Appalachian 118 Hz",
        "Tradition has resisted modernization for 300 years — frequency preserved without conscious intention",
        "Historical documentation of Old Regular Baptist practice",
        "observation", 0.75, False)

    # Thread 2: Archaeoacoustic Sites
    t2 = grail.add_thread(
        name="Archaeoacoustic Sites",
        thesis="Ancient constructed spaces across multiple continents resonate at 95-120 Hz, with 110 Hz as the most frequently documented peak. This is not coincidental — the builders selected materials and geometries that produce this resonance.",
        domain="archaeoacoustics",
        frequency_band=(95.0, 120.0),
        status=ThreadStatus.DOCUMENTED,
        knight="Gawain",
        connections=["Appalachian 118 Hz", "EEG Theta Studies", "Caledonian Geology"],
    )
    grail.add_evidence("Archaeoacoustic Sites",
        "Hal Saflieni Hypogeum, Malta — measured at 110-114 Hz by Debertolis (University of Trieste) and Devereux & Jahn 1996",
        "Debertolis et al., Journal of Anthropology and Archaeology, 2015",
        "measurement", 0.95, True)
    grail.add_evidence("Archaeoacoustic Sites",
        "UK/Ireland passage graves (6 sites) — resonances in 95-120 Hz range, 110 Hz consistent peak",
        "Devereux & Jahn, Journal of Scientific Exploration, 1996",
        "measurement", 0.9, True)
    grail.add_evidence("Archaeoacoustic Sites",
        "El Castillo cave, Spain — 108-110 Hz at shaman position, 40,000 year old site",
        "Published archaeoacoustic study, NeuroQuantology, 2015",
        "measurement", 0.9, True)
    grail.add_evidence("Archaeoacoustic Sites",
        "Chavin de Huantar, Peru — gallery modes 100-120 Hz",
        "Kolar, Stanford CCRMA project",
        "measurement", 0.85, True)
    grail.add_evidence("Archaeoacoustic Sites",
        "Pattern confirmed independently by Princeton, UCLA, University of Trieste, University of Siena, Stanford CCRMA",
        "Multiple institutions, published in JASA, Antiquity, NeuroQuantology, Time and Mind",
        "citation", 0.95, True)

    # Thread 3: EEG Theta Studies
    t3 = grail.add_thread(
        name="EEG Theta Studies",
        thesis="Exposure to 110 Hz acoustic frequency produces measurable neurological effects: left temporal deactivation, right prefrontal shift, and theta induction — effects not replicated by adjacent frequencies.",
        domain="neuroscience",
        frequency_band=(108.0, 112.0),
        status=ThreadStatus.DOCUMENTED,
        knight="Galahad",
        connections=["Archaeoacoustic Sites", "Appalachian 118 Hz", "Clinical Instruments"],
    )
    grail.add_evidence("EEG Theta Studies",
        "110 Hz specifically caused left temporal deactivation and right prefrontal shift in EEG — the language center goes offline",
        "Cook, Pajot & Leuchter, Time and Mind, 2008",
        "clinical", 0.95, True)
    grail.add_evidence("EEG Theta Studies",
        "Effect was frequency-specific — adjacent frequencies did not produce the same neural pattern",
        "Cook et al. 2008",
        "clinical", 0.9, True)
    grail.add_evidence("EEG Theta Studies",
        "30+ peer-reviewed studies confirm neurological effects of this frequency band",
        "Literature survey, multiple journals, 2008-2024",
        "citation", 0.85, True)

    # Thread 4: Caledonian Geology
    t4 = grail.add_thread(
        name="Caledonian Geology",
        thesis="The Appalachian mountains and the Scottish/Irish highlands are fragments of one ancient mountain range (Caledonides) separated when Pangaea split. The rock formations share identical acoustic properties.",
        domain="geology",
        frequency_band=None,
        status=ThreadStatus.DOCUMENTED,
        knight="Bors",
        connections=["Appalachian 118 Hz", "Archaeoacoustic Sites"],
    )
    grail.add_evidence("Caledonian Geology",
        "Appalachian-Caledonian geological continuity established — same structural composition, same rock formations",
        "Dewey, Nature, 1969; NatureScot geological surveys",
        "citation", 0.95, True)
    grail.add_evidence("Caledonian Geology",
        "Scots-Irish carried singing traditions from Caledonian formation to Appalachian formation — geologically identical landscape",
        "Historical migration documentation",
        "observation", 0.8, False)
    grail.add_evidence("Caledonian Geology",
        "Newgrange (110 Hz) sits on Caledonian rock. Appalachian churches (118 Hz) sit on the same formation, separated by the Atlantic",
        "West 2026 synthesis of geological and acoustic data",
        "calculation", 0.85, False)

    # Thread 5: Clinical Instruments
    t5 = grail.add_thread(
        name="Clinical Instruments",
        thesis="Ancient acoustic instruments (Peruvian whistling vessels, Himalayan singing bowls) produce measurable physiological effects in clinical trials — altered heart rate, blood pressure, respiration.",
        domain="clinical_medicine",
        frequency_band=(90.0, 130.0),
        status=ThreadStatus.DOCUMENTED,
        knight="Percival",
        connections=["EEG Theta Studies", "Archaeoacoustic Sites"],
    )
    grail.add_evidence("Clinical Instruments",
        "Peruvian whistling vessels altered heart rate, blood pressure, and respiration in clinical trials — 1970s, Franklin Institute / Hahnemann Medical College",
        "Published clinical trials, 1970s",
        "clinical", 0.9, True)
    grail.add_evidence("Clinical Instruments",
        "Himalayan singing bowls — 2023 clinical trials confirm physiological effects",
        "Multiple clinical studies, 2023",
        "clinical", 0.85, True)
    grail.add_evidence("Clinical Instruments",
        "Vessels dismissed as water jugs for 2,000 years despite clinical evidence",
        "Archaeological literature review",
        "observation", 0.7, False)

    # Thread 6: Indus Acoustic Hypothesis
    t6 = grail.add_thread(
        name="Indus Acoustic Hypothesis",
        thesis="The Indus Valley script encodes material compositions, alloy ratios, and acoustic verification protocols — a frequency-material notation system. The seals are recipes that encode acoustic properties.",
        domain="archaeometallurgy",
        frequency_band=None,
        status=ThreadStatus.PUBLISHED,
        knight="Tristan",
        connections=["Archaeoacoustic Sites", "Clinical Instruments"],
    )
    grail.add_evidence("Indus Acoustic Hypothesis",
        "Every alloy has a unique acoustic velocity — copper 4760 m/s, tin 3320 m/s, lead 2160 m/s. Changing the recipe changes the tone.",
        "Published acoustic physics data",
        "measurement", 0.95, True)
    grail.add_evidence("Indus Acoustic Hypothesis",
        "67 signs account for 80% of all Indus script usage — consistent with a working vocabulary of standard recipes, not a spoken language",
        "Mahadevan concordance, 1977",
        "citation", 0.9, True)
    grail.add_evidence("Indus Acoustic Hypothesis",
        "12 seal inscriptions tested, 10/12 show internal mathematical consistency as alloy recipes. Two independent Harappa seals both resolve to 87/13 copper-tin",
        "West 2026 analysis",
        "calculation", 0.8, False)
    grail.add_evidence("Indus Acoustic Hypothesis",
        "Paper published on Academia.edu, March 2026",
        "West, J.L., The Forgotten Code Research Institute",
        "observation", 0.7, False)

    # Thread 7: Pachacamac Oracle
    t7 = grail.add_thread(
        name="Pachacamac Oracle",
        thesis="The Pachacamac oracle site sits above the Peru-Chile subduction zone with documented pre-earthquake infrasound. The oracle chamber was never acoustically measured — the biggest gap in the literature.",
        domain="archaeoacoustics",
        frequency_band=(95.0, 110.0),
        status=ThreadStatus.GROWING,
        knight="Morgana",
        connections=["Archaeoacoustic Sites", "Clinical Instruments", "Global Oracle Network"],
    )
    grail.add_evidence("Pachacamac Oracle",
        "Site sits above active subduction zone — documented pre-earthquake infrasound",
        "Geological literature",
        "citation", 0.8, True)
    grail.add_evidence("Pachacamac Oracle",
        "Adobe chambers never acoustically measured — identified as primary research gap",
        "West 2026 literature review",
        "observation", 0.7, False)
    grail.add_evidence("Pachacamac Oracle",
        "One documented failure in 1,300 years of operation. 20-day to one-year fasting protocols for consultants.",
        "Spanish chronicles, archaeological documentation",
        "citation", 0.75, True)

    # Thread 8: Vedic Oral Transmission
    t8 = grail.add_thread(
        name="Vedic Oral Transmission",
        thesis="The Vedic tradition deliberately refused to write down sacred texts for over 3,000 years — preserving exact frequency specifications in human throats rather than on paper, because paper cannot hold what matters: the sound.",
        domain="ethnomusicology",
        frequency_band=None,
        status=ThreadStatus.DOCUMENTED,
        knight="Morgana",
        connections=["Appalachian 118 Hz", "Archaeoacoustic Sites"],
    )
    grail.add_evidence("Vedic Oral Transmission",
        "Vedic bilateral oscillation technique creates nulls against external frequency capture — a deliberate anti-recording mechanism",
        "Vedic studies literature",
        "citation", 0.8, True)
    grail.add_evidence("Vedic Oral Transmission",
        "Three independent traditions — Vedic, Druidic, Roman priestly — all independently rejected writing for sacred sound",
        "Comparative religious studies",
        "observation", 0.75, False)

    # Thread 9: Global Oracle Network
    t9 = grail.add_thread(
        name="Global Oracle Network",
        thesis="Every major ancient oracle site shares: geological fault lines, underground gas or water, acoustic amplification, and sensory deprivation protocols. This is humanity's first distributed network for finding Earth locations that alter human perception.",
        domain="comparative_archaeology",
        frequency_band=(90.0, 120.0),
        status=ThreadStatus.GROWING,
        knight="Dagonet",
        connections=["Pachacamac Oracle", "Archaeoacoustic Sites", "EEG Theta Studies"],
    )
    grail.add_evidence("Global Oracle Network",
        "Delphi — geological fault + ethylene gas confirmed 2001 by Hale and de Boer",
        "John Hale, Jelle de Boer et al.",
        "citation", 0.9, True)
    grail.add_evidence("Global Oracle Network",
        "Pattern: fault lines + gas/water + acoustic chamber + sensory deprivation = oracle site, across all documented ancient oracles",
        "West 2026 synthesis",
        "observation", 0.8, False)

    # Connect all threads
    all_names = [t.name for t in [t1, t2, t3, t4, t5, t6, t7, t8, t9]]
    # Frequency band threads are all connected
    for name_a in ["Appalachian 118 Hz", "Archaeoacoustic Sites", "EEG Theta Studies", "Clinical Instruments"]:
        for name_b in ["Appalachian 118 Hz", "Archaeoacoustic Sites", "EEG Theta Studies", "Clinical Instruments"]:
            if name_a != name_b:
                grail.connect_threads(name_a, name_b)

    return grail


# ═══════════════════════════════════════════════════════════════
#  DEMO
# ═══════════════════════════════════════════════════════════════

def demo():
    """Seek the Grail."""
    print("\n" + "=" * 60)
    print("  T H E   G R A I L")
    print("  The Quest That Unifies Everything")
    print("=" * 60)

    grail = Grail()
    load_jennifers_research(grail)

    print(f"\n  Research threads loaded: {len(grail._threads)}")
    for name, thread in grail._threads.items():
        ev_count = len(thread.evidence)
        pr_count = thread.peer_reviewed_count
        print(f"    {name:30s} [{thread.domain:20s}] "
              f"status: {thread.status.value:12s} "
              f"evidence: {ev_count} ({pr_count} peer-reviewed) "
              f"maturity: {thread.maturity:.0%}")

    # Seek the Grail
    print(f"\n  Seeking the Grail...")
    quest = grail.seek()

    print(f"\n  GRAIL STATUS: {quest['status'].upper()}")
    print(f"  Quest progress: {quest['quest_progress']:.0%}")
    print(f"  Convergence threshold: {quest['convergence_threshold']:.0%}")
    print(f"  Total convergence: {quest['total_convergence']:.2f}")
    print(f"  Convergence points found: {quest['convergence_points']}")
    print(f"  Average thread maturity: {quest['average_maturity']:.0%}")
    print(f"  Connection ratio: {quest['connection_ratio']:.0%}")

    if quest.get("strongest_convergence"):
        print(f"\n  Strongest convergence:")
        print(f"    {quest['strongest_convergence']}")

    if quest.get("frequency_map"):
        print(f"\n  Frequency map:")
        for name, data in quest["frequency_map"].items():
            print(f"    {name:30s}: {data['band'][0]:.0f}-{data['band'][1]:.0f} Hz ({data['domain']})")

    # The question
    print(f"\n  {'─' * 50}")
    print(f"  {grail.the_question()}")

    print(f"\n" + "=" * 60)
    print(f"  Whom does the Grail serve?")
    print(f"  {quest['grail_answer']}")
    print(f"=" * 60 + "\n")


if __name__ == "__main__":
    demo()
