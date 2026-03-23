"""
WEST-OS Autonomic State (Homeostasis / Metabolism Layer)
Manages internal body state: load, sensor health, attention budget.
Answers: "How stressed is the body? How much should we trust each sense?"

Copyright © 2025-2026 Jennifer Leigh West. All Rights Reserved.
"""

import time
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class AutonomicState:
    """The body's internal vital signs."""

    regime: str = "NORMAL"  # NORMAL / ELEVATED / STRESSED / CRITICAL
    system_load: float = 0.0
    sensor_health: Dict[str, float] = field(default_factory=dict)
    uncertainty: float = 0.0
    attention_budget: float = 1.0
    fallback_count: int = 0
    recovery_pressure: float = 0.0
    survival_probability: float = 1.0
    recent_convergence_count: int = 0
    war_score_trend: float = 0.0
    updated_at: float = field(default_factory=time.time)


class AutonomicLayer:
    """
    Computes the body's internal state from engine outputs.
    Sits between raw sensing and final governance.
    """

    def __init__(self):
        self.state = AutonomicState()
        self.convergence_history: list = []
        self.war_score_history: list = []

    def update(
        self,
        engine_weights: Dict[str, float],
        engine_variances: Dict[str, float],
        fallback_count: int,
        convergence_fired: bool,
        war_score: float,
        threat_score: float,
    ) -> AutonomicState:
        """Update autonomic state from current event data."""
        self.state.updated_at = time.time()

        self.state.sensor_health = dict(engine_weights)
        self.state.fallback_count = fallback_count

        self.convergence_history.append(1 if convergence_fired else 0)
        if len(self.convergence_history) > 50:
            self.convergence_history.pop(0)
        self.state.recent_convergence_count = sum(self.convergence_history[-20:])
        convergence_rate = self.state.recent_convergence_count / 20.0

        self.war_score_history.append(war_score)
        if len(self.war_score_history) > 50:
            self.war_score_history.pop(0)
        if len(self.war_score_history) >= 5:
            recent = self.war_score_history[-5:]
            older = self.war_score_history[-10:-5] if len(self.war_score_history) >= 10 else recent
            self.state.war_score_trend = sum(recent) / len(recent) - sum(older) / len(older)

        total_engines = max(len(engine_weights), 1)
        fallback_ratio = fallback_count / total_engines
        self.state.system_load = max(0.0, min(1.0,
            0.3 * threat_score + 0.3 * fallback_ratio + 0.4 * convergence_rate
        ))

        if engine_variances:
            mean_var = sum(engine_variances.values()) / len(engine_variances)
            self.state.uncertainty = max(0.0, min(1.0, 1.0 - mean_var * 10))
        else:
            self.state.uncertainty = 1.0

        load = self.state.system_load
        if load > 0.8 or fallback_count > 3:
            self.state.regime = "CRITICAL"
        elif load > 0.6 or convergence_fired:
            self.state.regime = "STRESSED"
        elif load > 0.4:
            self.state.regime = "ELEVATED"
        else:
            self.state.regime = "NORMAL"

        regime_budgets = {
            "NORMAL": 0.5,
            "ELEVATED": 0.75,
            "STRESSED": 1.0,
            "CRITICAL": 1.0,
        }
        self.state.attention_budget = regime_budgets.get(self.state.regime, 1.0)

        return self.state

    def should_run_full_stack(self) -> bool:
        """Should we run all engines or take the cheap path?"""
        return self.state.attention_budget >= 0.75

    def should_escalate_caution(self) -> bool:
        """Should the governor be extra cautious right now?"""
        return self.state.regime in ("STRESSED", "CRITICAL")

    def get_weight_modifier(self, engine_name: str) -> float:
        """Get autonomic weight modifier for an engine."""
        health = self.state.sensor_health.get(engine_name, 1.0)
        if health < 0.3:
            return 0.5
        return 1.0
