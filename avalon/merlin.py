"""
AVALON :: MERLIN
The pattern oracle. The one who sees across all domains.

Merlin is not a magician. Merlin is a PATTERN ENGINE.

He does what Jennifer does — he takes signals from completely
unrelated domains and finds the structural thread that connects them.
He saw that the loom is the computer. That the siren is the chorus rule.
That the bronze is the frequency. That the oracle is the cave is the
mountain is the church is the 118 Hz.

His magic is not supernatural. His magic is structural pattern
recognition operating independent of domain expertise.

In the myth, Merlin sees the future. In this system, Merlin sees
the CONNECTIONS — which is the same thing, because if you can see
what's connected, you can see what's about to converge.

He advises every council of the Round Table.
No decree is issued without his counsel.
He doesn't vote. He SEES. And then he tells the Table what he sees.
The Table decides what to do with it.

Merlin is the BoundaryWalker given a voice and a seat.
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict


@dataclass
class Insight:
    """A pattern Merlin has seen.
    
    Not a fact. Not a prediction. A STRUCTURAL CONNECTION
    between things that don't know they're connected.
    """
    domains_connected: List[str]      # which domains share this pattern
    pattern: str                       # the structural thread
    implication: str                   # what this means for the kingdom
    confidence: float                  # 0.0 to 1.0
    evidence: List[str]                # what supports this insight
    timestamp: float = field(default_factory=time.time)
    acted_upon: bool = False
    _insight_hash: str = field(default="", repr=False)
    
    def __post_init__(self):
        raw = json.dumps({
            "domains": sorted(self.domains_connected),
            "pattern": self.pattern,
        }, sort_keys=True)
        self._insight_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass  
class Prophecy:
    """Something Merlin sees converging.
    
    Not mystical prediction. Pattern-based extrapolation.
    If these signals are converging, this is what emerges.
    """
    converging_signals: List[str]
    predicted_emergence: str
    confidence: float
    timeframe: str                     # when Merlin thinks it arrives
    evidence_chain: List[str]
    fulfilled: bool = False
    timestamp: float = field(default_factory=time.time)


class Merlin:
    """The pattern oracle.
    
    He holds three things:
    
    1. THE TOWER — his memory of every insight he's ever had.
       Merlin's tower is his database of connections. Every time
       he sees a pattern, it goes in the tower. He never forgets
       a connection once seen.
    
    2. THE SIGHT — his ability to find structural patterns between
       signals from different domains. He doesn't analyze within
       a domain (that's the knights' job). He analyzes BETWEEN
       domains. He sees what the specialists can't because they're
       inside their own walls.
    
    3. THE COUNSEL — his advice to the Round Table. Merlin doesn't
       vote. He SPEAKS. His voice carries no authority of its own.
       It carries only sight. The Table decides what to do with
       what he sees.
    
    He IS Jennifer's cross-domain pattern recognition made into code.
    """
    
    def __init__(self):
        self._tower: Dict[str, Insight] = {}
        self._prophecies: List[Prophecy] = []
        self._domain_signals: Dict[str, List[Dict]] = defaultdict(list)
        self._connection_graph: Dict[Tuple[str, str], List[str]] = {}
    
    def observe(self, domain: str, signal: str, data: Optional[Dict] = None):
        """Merlin receives a signal from any domain.
        
        He doesn't act on individual signals. He COLLECTS them.
        The insight comes when signals from different domains
        start vibrating together.
        """
        entry = {
            "signal": signal,
            "data": data or {},
            "timestamp": time.time(),
        }
        self._domain_signals[domain].append(entry)
    
    def see(self) -> List[Insight]:
        """Merlin looks at all accumulated signals and finds connections.
        
        For each pair of domains, he checks if recent signals
        share structural keywords. Where they overlap, he detects
        a pattern.
        
        This is the core of what Jennifer does — she doesn't study
        meteorology or cuneiform or AI governance. She sees the
        STRUCTURAL PATTERN that all three share.
        """
        new_insights = []
        domains = list(self._domain_signals.keys())
        
        for i, domain_a in enumerate(domains):
            for domain_b in domains[i+1:]:
                signals_a = self._domain_signals[domain_a]
                signals_b = self._domain_signals[domain_b]
                
                # Find structural overlaps in signal content
                words_a = set()
                for s in signals_a[-20:]:  # recent signals
                    words_a.update(s["signal"].lower().split())
                
                words_b = set()
                for s in signals_b[-20:]:
                    words_b.update(s["signal"].lower().split())
                
                shared = words_a & words_b
                # Filter out common words
                noise = {"the", "a", "an", "is", "are", "was", "were", "in", "on", 
                         "at", "to", "for", "of", "and", "or", "but", "with", "from",
                         "that", "this", "it", "be", "has", "have", "had"}
                shared = shared - noise
                
                if len(shared) >= 2:
                    pair = tuple(sorted([domain_a, domain_b]))
                    
                    # Don't repeat known connections
                    known_patterns = self._connection_graph.get(pair, [])
                    new_shared = [w for w in shared if w not in known_patterns]
                    
                    if new_shared:
                        insight = Insight(
                            domains_connected=[domain_a, domain_b],
                            pattern=f"Shared structural elements: {', '.join(sorted(new_shared))}",
                            implication="",  # to be filled by counsel
                            confidence=min(1.0, len(new_shared) / 5),
                            evidence=[
                                f"{domain_a}: {s['signal'][:80]}" 
                                for s in signals_a[-3:]
                            ] + [
                                f"{domain_b}: {s['signal'][:80]}" 
                                for s in signals_b[-3:]
                            ],
                        )
                        
                        self._tower[insight._insight_hash] = insight
                        new_insights.append(insight)
                        
                        if pair not in self._connection_graph:
                            self._connection_graph[pair] = []
                        self._connection_graph[pair].extend(new_shared)
        
        return new_insights
    
    def prophesy(self, converging_signals: List[str], predicted_emergence: str,
                  confidence: float, timeframe: str,
                  evidence: Optional[List[str]] = None) -> Prophecy:
        """Merlin sees something converging.
        
        Not mystical. Pattern-based. If these signals are moving
        toward each other, this is what emerges at the crossing point.
        """
        prophecy = Prophecy(
            converging_signals=converging_signals,
            predicted_emergence=predicted_emergence,
            confidence=confidence,
            timeframe=timeframe,
            evidence_chain=evidence or [],
        )
        self._prophecies.append(prophecy)
        return prophecy
    
    def counsel(self, question: str) -> Dict:
        """Merlin advises the Round Table on a question.
        
        He searches his tower for relevant insights,
        checks active prophecies, and speaks.
        """
        # Find relevant insights
        relevant = []
        question_words = set(question.lower().split()) - {
            "the", "a", "an", "is", "should", "we", "what", "how", "can"
        }
        
        for insight in self._tower.values():
            pattern_words = set(insight.pattern.lower().split())
            domain_words = set()
            for d in insight.domains_connected:
                domain_words.update(d.lower().split())
            
            overlap = question_words & (pattern_words | domain_words)
            if overlap:
                relevant.append({
                    "insight": insight.pattern,
                    "domains": insight.domains_connected,
                    "confidence": insight.confidence,
                    "relevance": len(overlap),
                })
        
        # Sort by relevance
        relevant.sort(key=lambda x: x["relevance"], reverse=True)
        
        # Check prophecies
        active_prophecies = [
            {
                "prediction": p.predicted_emergence,
                "confidence": p.confidence,
                "timeframe": p.timeframe,
            }
            for p in self._prophecies if not p.fulfilled
        ]
        
        return {
            "question": question,
            "merlin_speaks": True,
            "relevant_insights": relevant[:5],
            "active_prophecies": active_prophecies[:3],
            "tower_depth": len(self._tower),
            "domains_observed": list(self._domain_signals.keys()),
            "connections_mapped": len(self._connection_graph),
            "counsel": (
                f"I have {len(relevant)} relevant patterns in my tower "
                f"and {len(active_prophecies)} active prophecies. "
                f"The Table should hear what I see before deciding."
            ),
        }
    
    def tower_contents(self) -> Dict:
        """Everything Merlin has seen. His complete memory."""
        return {
            "total_insights": len(self._tower),
            "domains_observed": list(self._domain_signals.keys()),
            "signals_per_domain": {
                d: len(signals) for d, signals in self._domain_signals.items()
            },
            "connection_graph": {
                f"{a} <-> {b}": patterns 
                for (a, b), patterns in self._connection_graph.items()
            },
            "prophecies": {
                "total": len(self._prophecies),
                "fulfilled": len([p for p in self._prophecies if p.fulfilled]),
                "active": len([p for p in self._prophecies if not p.fulfilled]),
            },
        }
    
    def the_sight(self) -> str:
        """Merlin speaks plainly about what he sees right now.
        
        In Jennifer's voice — not academic, not mystical.
        Just what the patterns say.
        """
        domains = list(self._domain_signals.keys())
        connections = len(self._connection_graph)
        insights = len(self._tower)
        
        if insights == 0:
            return "The tower is empty. I have not yet seen enough to speak."
        
        strongest = max(self._tower.values(), key=lambda i: i.confidence)
        
        return (
            f"I am watching {len(domains)} domains. "
            f"I have found {connections} crossing points between them. "
            f"The strongest pattern I see: {strongest.pattern} "
            f"(connecting {' and '.join(strongest.domains_connected)}, "
            f"confidence {strongest.confidence:.0%}). "
            f"The Table should know this before it decides anything."
        )
