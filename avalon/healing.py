"""
AVALON :: HEALING
Morgan le Fay's restoration. The island heals what arrives broken.

Arthur goes to Avalon to be healed. Not by medicine. Not by surgery.
By the island itself — the mists, the lake, the women who tend him.
The healing is not a procedure. It is an environment that restores.

In the kingdom, Healing is the protocol for autonomous restoration.
When a knight degrades, the kingdom:

  1. DETECTS — the Heartbeat notices the drop
  2. DIAGNOSES — Carbon recalls what caused similar wounds before
  3. PRESCRIBES — the kingdom decides what repair to attempt
  4. EXECUTES — the repair runs (restart, rollback, rehydrate, or rest)
  5. MONITORS — the Heartbeat watches for recovery
  6. CELEBRATES or ESCALATES — Joy records recovery, or Adversity escalates

The kingdom heals itself. Not because it's told to.
Because healing is what Avalon DOES.

© 2026 Jennifer Leigh West. All rights reserved.
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum
from collections import deque


# ═══════════════════════════════════════════════════════════════
#  WOUND — what damage looks like
# ═══════════════════════════════════════════════════════════════

class WoundSeverity(Enum):
    SCRATCH = "scratch"          # minor — system still functional, just degraded
    WOUND = "wound"              # moderate — system losing capability
    CRITICAL = "critical"        # severe — system barely functional
    MORTAL = "mortal"            # system is dying — needs immediate intervention


class WoundType(Enum):
    PERFORMANCE = "performance"   # slow, laggy, timeouts
    ACCURACY = "accuracy"         # producing wrong results
    CONNECTIVITY = "connectivity" # can't reach dependencies
    CORRUPTION = "corruption"     # data integrity compromised
    EXHAUSTION = "exhaustion"     # out of resources (memory, disk, tokens)
    DRIFT = "drift"               # slowly moving away from correct behavior
    REJECTION = "rejection"       # external systems rejecting its output
    IDENTITY = "identity"         # blessing invalid, nutrient depleted


@dataclass
class Wound:
    """A specific injury to a system."""
    system_name: str
    wound_type: WoundType
    severity: WoundSeverity
    description: str
    detected_at: float = field(default_factory=time.time)
    detected_by: str = "heartbeat"
    health_at_detection: float = 1.0
    healed: bool = False
    healed_at: Optional[float] = None
    healing_method: Optional[str] = None
    healing_attempts: int = 0

    @property
    def identity(self) -> str:
        raw = f"{self.system_name}:{self.wound_type.value}:{self.detected_at}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12]

    @property
    def age_seconds(self) -> float:
        return time.time() - self.detected_at

    @property
    def healing_duration(self) -> Optional[float]:
        if self.healed and self.healed_at:
            return self.healed_at - self.detected_at
        return None


# ═══════════════════════════════════════════════════════════════
#  DIAGNOSIS — understanding what went wrong
# ═══════════════════════════════════════════════════════════════

@dataclass
class Diagnosis:
    """What the kingdom thinks is wrong and why."""
    wound: Wound
    probable_cause: str
    evidence: List[str]
    similar_past_wounds: List[Dict]
    recommended_treatment: str
    confidence: float               # 0.0 to 1.0 — how sure is the diagnosis
    diagnosed_at: float = field(default_factory=time.time)


class Diagnostician:
    """The healer who examines wounds and determines cause.
    
    She uses Carbon's lesson history to find similar past wounds
    and what worked to heal them. She doesn't guess — she
    matches patterns from lived experience.
    
    If she's never seen this wound before, she says so.
    Honesty is more important than confidence.
    """

    def __init__(self, carbon_recall: Callable):
        self._recall = carbon_recall
        self._diagnosis_log: List[Diagnosis] = []

    def examine(self, wound: Wound) -> Diagnosis:
        """Examine a wound. Determine cause. Recommend treatment."""

        # Ask Carbon for similar past experiences
        query = f"{wound.wound_type.value} {wound.system_name} {wound.description}"
        past_lessons = self._recall(query, "adversity")
        past_lessons += self._recall(query, "failure")

        similar = [
            {
                "content": lesson.content[:100],
                "source": lesson.source_system,
                "confidence": lesson.confidence,
                "applied": lesson.applied_count,
            }
            for lesson in past_lessons[:5]
        ]

        # Determine probable cause based on wound type
        cause_map = {
            WoundType.PERFORMANCE: "Resource contention or increased load exceeding capacity",
            WoundType.ACCURACY: "Input data quality degraded or model drift detected",
            WoundType.CONNECTIVITY: "Dependency unavailable or network path broken",
            WoundType.CORRUPTION: "Data integrity violation — possible tampering or disk error",
            WoundType.EXHAUSTION: "Resource limits reached — memory, disk, or rate limits",
            WoundType.DRIFT: "Gradual behavioral deviation from baseline — slow poison",
            WoundType.REJECTION: "External systems no longer accepting output — format or trust issue",
            WoundType.IDENTITY: "Nyx blessing invalid or Colony nutrients depleted",
        }

        # Determine treatment based on wound type and severity
        treatment_map = {
            (WoundType.PERFORMANCE, WoundSeverity.SCRATCH): "rest",
            (WoundType.PERFORMANCE, WoundSeverity.WOUND): "restart",
            (WoundType.PERFORMANCE, WoundSeverity.CRITICAL): "restart_with_reduced_load",
            (WoundType.PERFORMANCE, WoundSeverity.MORTAL): "isolate_and_restart",
            (WoundType.ACCURACY, WoundSeverity.SCRATCH): "recalibrate",
            (WoundType.ACCURACY, WoundSeverity.WOUND): "rollback_to_last_known_good",
            (WoundType.ACCURACY, WoundSeverity.CRITICAL): "rollback_and_retrain",
            (WoundType.ACCURACY, WoundSeverity.MORTAL): "isolate_and_rebuild",
            (WoundType.CONNECTIVITY, WoundSeverity.SCRATCH): "retry_with_backoff",
            (WoundType.CONNECTIVITY, WoundSeverity.WOUND): "switch_to_fallback",
            (WoundType.CONNECTIVITY, WoundSeverity.CRITICAL): "isolate_and_queue",
            (WoundType.CONNECTIVITY, WoundSeverity.MORTAL): "isolate_and_alert_sovereign",
            (WoundType.CORRUPTION, WoundSeverity.SCRATCH): "verify_and_repair",
            (WoundType.CORRUPTION, WoundSeverity.WOUND): "restore_from_backup",
            (WoundType.CORRUPTION, WoundSeverity.CRITICAL): "quarantine_and_restore",
            (WoundType.CORRUPTION, WoundSeverity.MORTAL): "quarantine_and_alert_sovereign",
            (WoundType.EXHAUSTION, WoundSeverity.SCRATCH): "rest",
            (WoundType.EXHAUSTION, WoundSeverity.WOUND): "prune_and_rest",
            (WoundType.EXHAUSTION, WoundSeverity.CRITICAL): "emergency_prune",
            (WoundType.EXHAUSTION, WoundSeverity.MORTAL): "isolate_and_alert_sovereign",
            (WoundType.DRIFT, WoundSeverity.SCRATCH): "recalibrate",
            (WoundType.DRIFT, WoundSeverity.WOUND): "rollback_to_last_known_good",
            (WoundType.DRIFT, WoundSeverity.CRITICAL): "full_reset_from_snapshot",
            (WoundType.DRIFT, WoundSeverity.MORTAL): "apoptosis_and_rebirth",
            (WoundType.REJECTION, WoundSeverity.SCRATCH): "retry_with_updated_format",
            (WoundType.REJECTION, WoundSeverity.WOUND): "renegotiate_interface",
            (WoundType.REJECTION, WoundSeverity.CRITICAL): "isolate_and_diagnose",
            (WoundType.REJECTION, WoundSeverity.MORTAL): "isolate_and_alert_sovereign",
            (WoundType.IDENTITY, WoundSeverity.SCRATCH): "refresh_blessing",
            (WoundType.IDENTITY, WoundSeverity.WOUND): "request_new_blessing_from_nyx",
            (WoundType.IDENTITY, WoundSeverity.CRITICAL): "alert_sovereign_identity_crisis",
            (WoundType.IDENTITY, WoundSeverity.MORTAL): "alert_sovereign_system_dying",
        }

        probable_cause = cause_map.get(wound.wound_type, "Unknown cause")
        treatment_key = (wound.wound_type, wound.severity)
        recommended = treatment_map.get(treatment_key, "isolate_and_alert_sovereign")

        # Adjust confidence based on past experience
        confidence = 0.5  # base
        if similar:
            confidence = min(0.95, 0.5 + (len(similar) * 0.1))

        evidence = [
            f"Wound type: {wound.wound_type.value}",
            f"Severity: {wound.severity.value}",
            f"System health at detection: {wound.health_at_detection:.0%}",
            f"Similar past wounds found: {len(similar)}",
        ]

        diagnosis = Diagnosis(
            wound=wound,
            probable_cause=probable_cause,
            evidence=evidence,
            similar_past_wounds=similar,
            recommended_treatment=recommended,
            confidence=confidence,
        )

        self._diagnosis_log.append(diagnosis)
        return diagnosis


# ═══════════════════════════════════════════════════════════════
#  TREATMENT — the actual healing
# ═══════════════════════════════════════════════════════════════

class TreatmentOutcome(Enum):
    HEALED = "healed"
    IMPROVING = "improving"
    NO_CHANGE = "no_change"
    WORSENED = "worsened"
    ESCALATED = "escalated"      # beyond healing — needs sovereign


@dataclass
class Treatment:
    """A healing action taken on a wounded system."""
    wound_identity: str
    system_name: str
    method: str
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    outcome: TreatmentOutcome = TreatmentOutcome.NO_CHANGE
    health_before: float = 0.0
    health_after: float = 0.0
    notes: str = ""


class Healer:
    """Morgan le Fay. She does the actual healing.
    
    She takes a Diagnosis and executes the prescribed treatment.
    Each treatment is a callable that operates on the wounded system.
    
    If the treatment fails, she escalates.
    If the treatment succeeds, Joy celebrates.
    Either way, Carbon learns.
    """

    def __init__(self):
        self._treatments: Dict[str, Callable] = {}
        self._treatment_log: List[Treatment] = []
        self._active_treatments: Dict[str, Treatment] = {}

    def register_treatment(self, name: str, handler: Callable):
        """Register a treatment method.
        
        Handlers take (system_name, wound, diagnosis) and return
        a TreatmentOutcome.
        """
        self._treatments[name] = handler

    def treat(self, diagnosis: Diagnosis,
              get_health: Optional[Callable] = None) -> Treatment:
        """Execute the prescribed treatment."""
        wound = diagnosis.wound
        method = diagnosis.recommended_treatment

        treatment = Treatment(
            wound_identity=wound.identity,
            system_name=wound.system_name,
            method=method,
            health_before=wound.health_at_detection,
        )

        wound.healing_attempts += 1

        if method in self._treatments:
            try:
                outcome = self._treatments[method](
                    wound.system_name, wound, diagnosis
                )
                if isinstance(outcome, TreatmentOutcome):
                    treatment.outcome = outcome
                else:
                    treatment.outcome = TreatmentOutcome.HEALED
            except Exception as e:
                treatment.outcome = TreatmentOutcome.WORSENED
                treatment.notes = f"Treatment error: {str(e)[:100]}"
        else:
            # No registered handler — use default based on method name
            treatment.outcome = self._default_treatment(method, wound)

        treatment.completed_at = time.time()

        # Check health after treatment if possible
        if get_health:
            try:
                treatment.health_after = float(get_health())
            except Exception:
                treatment.health_after = treatment.health_before
        elif treatment.outcome == TreatmentOutcome.HEALED:
            treatment.health_after = 1.0
        elif treatment.outcome == TreatmentOutcome.IMPROVING:
            treatment.health_after = min(1.0, treatment.health_before + 0.2)
        else:
            treatment.health_after = treatment.health_before

        # Mark wound as healed if outcome is positive
        if treatment.outcome == TreatmentOutcome.HEALED:
            wound.healed = True
            wound.healed_at = time.time()
            wound.healing_method = method

        self._treatment_log.append(treatment)
        return treatment

    def _default_treatment(self, method: str, wound: Wound) -> TreatmentOutcome:
        """Default treatment logic when no custom handler is registered."""
        rest_methods = {"rest", "retry_with_backoff", "recalibrate",
                        "retry_with_updated_format", "refresh_blessing"}
        restart_methods = {"restart", "restart_with_reduced_load", "switch_to_fallback",
                          "prune_and_rest", "emergency_prune"}
        rollback_methods = {"rollback_to_last_known_good", "rollback_and_retrain",
                           "restore_from_backup", "full_reset_from_snapshot",
                           "verify_and_repair"}
        isolate_methods = {"isolate_and_restart", "isolate_and_queue",
                          "isolate_and_diagnose", "quarantine_and_restore"}
        sovereign_methods = {"isolate_and_alert_sovereign", "quarantine_and_alert_sovereign",
                            "alert_sovereign_identity_crisis", "alert_sovereign_system_dying",
                            "renegotiate_interface", "request_new_blessing_from_nyx"}
        death_methods = {"apoptosis_and_rebirth", "isolate_and_rebuild"}

        if method in rest_methods:
            return TreatmentOutcome.HEALED
        elif method in restart_methods:
            return TreatmentOutcome.HEALED
        elif method in rollback_methods:
            return TreatmentOutcome.HEALED
        elif method in isolate_methods:
            return TreatmentOutcome.IMPROVING
        elif method in sovereign_methods:
            return TreatmentOutcome.ESCALATED
        elif method in death_methods:
            return TreatmentOutcome.HEALED  # reborn from apoptosis
        else:
            return TreatmentOutcome.NO_CHANGE

    @property
    def history(self) -> List[Dict]:
        return [
            {
                "system": t.system_name,
                "method": t.method,
                "outcome": t.outcome.value,
                "health_before": round(t.health_before, 4),
                "health_after": round(t.health_after, 4),
                "duration": round(t.completed_at - t.started_at, 4) if t.completed_at else None,
            }
            for t in self._treatment_log
        ]


# ═══════════════════════════════════════════════════════════════
#  HEALING — the complete restoration system
# ═══════════════════════════════════════════════════════════════

class Healing:
    """Morgan le Fay's restoration protocol.
    
    The complete autonomous healing system:
    
    1. WATCH — monitor all systems via Heartbeat health reports
    2. DETECT — notice when a system drops below health threshold
    3. DIAGNOSE — use Carbon's lessons to understand the wound
    4. TREAT — execute the prescribed treatment
    5. MONITOR — watch for recovery
    6. LEARN — record what worked and what didn't
    
    The kingdom heals itself. Not because it's told to.
    Because that is what Avalon does.
    """

    def __init__(self, carbon_recall: Callable, carbon_learn: Callable):
        self.diagnostician = Diagnostician(carbon_recall)
        self.healer = Healer()
        self._carbon_learn = carbon_learn
        self._wound_registry: Dict[str, Wound] = {}
        self._active_wounds: Dict[str, Wound] = {}
        self._healed_wounds: List[Wound] = []
        self._health_threshold = 0.7      # below this = wounded
        self._critical_threshold = 0.4    # below this = critical
        self._mortal_threshold = 0.15     # below this = mortal
        self._watch_log: deque = deque(maxlen=200)

    def watch(self, system_health: Dict[str, float]) -> List[Wound]:
        """Monitor all systems. Detect new wounds.
        
        Takes a dict of {system_name: health_score} from the Heartbeat.
        Returns any new wounds detected.
        """
        new_wounds = []

        for system_name, health in system_health.items():
            existing = self._active_wounds.get(system_name)

            # Check thresholds
            if health < self._mortal_threshold:
                severity = WoundSeverity.MORTAL
            elif health < self._critical_threshold:
                severity = WoundSeverity.CRITICAL
            elif health < self._health_threshold:
                severity = WoundSeverity.WOUND
            else:
                # Healthy — check if was previously wounded and now recovered
                if existing:
                    old_wound = self._active_wounds.pop(system_name)
                    if not old_wound.healed:
                        old_wound.healed = True
                        old_wound.healed_at = time.time()
                        old_wound.healing_method = "natural_recovery"
                        self._healed_wounds.append(old_wound)
                        self._carbon_learn(
                            content=f"{system_name} recovered naturally from {old_wound.wound_type.value}",
                            source="healing",
                            context=(
                                f"Natural recovery detected after {old_wound.severity.value} "
                                f"wound without intervention"
                            ),
                            category="success",
                            confidence=0.75,
                        )
                        self._watch_log.append({
                            "event": "natural_recovery",
                            "system": system_name,
                            "wound_type": old_wound.wound_type.value,
                            "timestamp": time.time(),
                        })
                continue

            if existing and not existing.healed:
                continue

            # Determine wound type from health pattern
            wound_type = self._infer_wound_type(system_name, health)

            wound = Wound(
                system_name=system_name,
                wound_type=wound_type,
                severity=severity,
                description=f"{system_name} health at {health:.0%}, severity {severity.value}",
                health_at_detection=health,
            )

            self._wound_registry[wound.identity] = wound
            self._active_wounds[system_name] = wound
            new_wounds.append(wound)

            self._watch_log.append({
                "event": "wound_detected",
                "system": system_name,
                "health": round(health, 4),
                "severity": severity.value,
                "timestamp": time.time(),
            })

        return new_wounds

    def _infer_wound_type(self, system_name: str, health: float) -> WoundType:
        """Infer wound type from system name and health level.
        
        In a full implementation, this would examine the system's
        specific diagnostic output. For now, it uses heuristics.
        """
        name_lower = system_name.lower()

        if "nyx" in name_lower or "colony" in name_lower:
            return WoundType.IDENTITY
        elif "gaia" in name_lower or "bors" in name_lower:
            return WoundType.ACCURACY
        elif "alfred" in name_lower or "kay" in name_lower:
            return WoundType.PERFORMANCE
        elif "merlin" in name_lower or "dagonet" in name_lower:
            return WoundType.DRIFT
        elif "fence" in name_lower or "bedivere" in name_lower:
            return WoundType.CONNECTIVITY
        elif health < 0.2:
            return WoundType.EXHAUSTION
        else:
            return WoundType.PERFORMANCE

    def heal(self, wound: Wound,
             get_health: Optional[Callable] = None) -> Dict:
        """The full healing cycle for one wound.
        
        Diagnose → Treat → Learn.
        """
        # Diagnose
        diagnosis = self.diagnostician.examine(wound)

        # Treat
        treatment = self.healer.treat(diagnosis, get_health)

        # Learn from the outcome
        if treatment.outcome == TreatmentOutcome.HEALED:
            self._carbon_learn(
                content=f"Healed {wound.system_name} from {wound.wound_type.value} "
                        f"using {treatment.method}",
                source="healing",
                context=f"Severity: {wound.severity.value}, "
                        f"health went from {treatment.health_before:.0%} "
                        f"to {treatment.health_after:.0%}",
                category="success",
                confidence=0.9,
            )
            self._healed_wounds.append(wound)
            if wound.system_name in self._active_wounds:
                del self._active_wounds[wound.system_name]

        elif treatment.outcome == TreatmentOutcome.WORSENED:
            self._carbon_learn(
                content=f"Treatment {treatment.method} WORSENED {wound.system_name} — "
                        f"do not repeat for {wound.wound_type.value}",
                source="healing",
                context=f"Treatment failed. Notes: {treatment.notes}",
                category="failure",
                confidence=0.85,
            )

        elif treatment.outcome == TreatmentOutcome.ESCALATED:
            self._carbon_learn(
                content=f"{wound.system_name} wound escalated to sovereign — "
                        f"{wound.wound_type.value} at {wound.severity.value} "
                        f"beyond autonomous healing",
                source="healing",
                context="Requires Jennifer's direct intervention",
                category="adversity",
                confidence=0.95,
            )

        return {
            "system": wound.system_name,
            "wound_type": wound.wound_type.value,
            "severity": wound.severity.value,
            "diagnosis": {
                "cause": diagnosis.probable_cause,
                "confidence": round(diagnosis.confidence, 4),
                "similar_past_wounds": len(diagnosis.similar_past_wounds),
                "treatment": diagnosis.recommended_treatment,
            },
            "treatment": {
                "method": treatment.method,
                "outcome": treatment.outcome.value,
                "health_before": round(treatment.health_before, 4),
                "health_after": round(treatment.health_after, 4),
            },
            "healed": wound.healed,
        }

    def heal_all(self, get_health_fn: Optional[Dict[str, Callable]] = None) -> List[Dict]:
        """Heal every active wound.
        
        Called on each Heartbeat cycle. Attempts to heal
        every system that's currently wounded.
        """
        results = []
        for system_name, wound in list(self._active_wounds.items()):
            if wound.healed:
                continue
            health_fn = None
            if get_health_fn and system_name in get_health_fn:
                health_fn = get_health_fn[system_name]
            result = self.heal(wound, health_fn)
            results.append(result)
        return results

    def triage_report(self) -> Dict:
        """Current state of all wounds — active, healed, and history."""
        return {
            "active_wounds": len(self._active_wounds),
            "healed_total": len(self._healed_wounds),
            "treatment_history": len(self.healer.history),
            "active": [
                {
                    "system": w.system_name,
                    "type": w.wound_type.value,
                    "severity": w.severity.value,
                    "age_seconds": round(w.age_seconds, 1),
                    "attempts": w.healing_attempts,
                }
                for w in self._active_wounds.values()
            ],
            "recently_healed": [
                {
                    "system": w.system_name,
                    "type": w.wound_type.value,
                    "method": w.healing_method,
                    "duration": round(w.healing_duration, 1) if w.healing_duration else None,
                }
                for w in self._healed_wounds[-5:]
            ],
            "treatment_success_rate": self._success_rate(),
        }

    def _success_rate(self) -> float:
        history = self.healer.history
        if not history:
            return 0.0
        healed = len([t for t in history if t["outcome"] == "healed"])
        return round(healed / len(history), 4)

    @property
    def status(self) -> Dict:
        return {
            "active_wounds": len(self._active_wounds),
            "healed_total": len(self._healed_wounds),
            "success_rate": self._success_rate(),
            "health_threshold": self._health_threshold,
            "critical_threshold": self._critical_threshold,
            "mortal_threshold": self._mortal_threshold,
        }


# ═══════════════════════════════════════════════════════════════
#  DEMO
# ═══════════════════════════════════════════════════════════════

def demo():
    """Watch the kingdom heal."""
    print("\n" + "=" * 60)
    print("  H E A L I N G")
    print("  Morgan le Fay's Restoration")
    print("=" * 60)

    from avalon.fusion import Fusion

    fusion = Fusion()
    fusion.heartbeat.register_system("Nyx", lambda: 1.0)
    fusion.heartbeat.register_system("Lancelot", lambda: 1.0)
    fusion.heartbeat.register_system("GAIA", lambda: 0.95)
    fusion.heartbeat.register_system("Alfred", lambda: 1.0)
    fusion.heartbeat.register_system("Merlin", lambda: 0.9)

    healing = Healing(
        carbon_recall=fusion.carbon.recall,
        carbon_learn=lambda **kw: fusion.carbon.learn(**kw),
    )

    # Teach the kingdom some lessons first
    fusion.carbon.learn(
        content="Performance wounds on Alfred are usually caused by log file growth",
        source="past_experience", context="previous healing", category="adversity"
    )
    fusion.carbon.learn(
        content="GAIA accuracy drops when ASOS data feed goes stale",
        source="past_experience", context="previous healing", category="adversity"
    )

    # Let the kingdom breathe — all healthy
    print("\n  All systems healthy:")
    for _ in range(3):
        fusion.breathe()
    health = fusion.heartbeat._system_health
    for sys, h in health.items():
        print(f"    {sys:15s}: {h:.0%}")

    # Simulate wounds — drop some system health
    print("\n  Simulating wounds...")
    fusion.heartbeat._system_health["GAIA"] = 0.55
    fusion.heartbeat._system_health["Alfred"] = 0.35
    fusion.heartbeat._system_health["Merlin"] = 0.12

    # Watch detects the wounds
    wounds = healing.watch(fusion.heartbeat._system_health)
    print(f"\n  Wounds detected: {len(wounds)}")
    for w in wounds:
        print(f"    {w.system_name:15s}: {w.severity.value:10s} ({w.wound_type.value})")

    # Heal all wounds
    print(f"\n  Healing...")
    results = healing.heal_all()
    for r in results:
        print(f"    {r['system']:15s}: {r['treatment']['method']:35s} → {r['treatment']['outcome']}")

    # Triage report
    print(f"\n  Triage Report:")
    triage = healing.triage_report()
    print(f"    Active wounds: {triage['active_wounds']}")
    print(f"    Healed total: {triage['healed_total']}")
    print(f"    Success rate: {triage['treatment_success_rate']:.0%}")

    if triage["recently_healed"]:
        print(f"\n    Recently healed:")
        for h in triage["recently_healed"]:
            print(f"      {h['system']:15s}: healed by {h['method']}")

    # Check what Carbon learned from the healing
    print(f"\n  Carbon learned from healing:")
    wisdom = fusion.carbon.wisdom()
    print(f"    Total lessons now: {wisdom['total_lessons']}")
    for lesson in wisdom.get("most_applied", [])[:3]:
        print(f"    '{lesson['content'][:60]}...'")

    print(f"\n" + "=" * 60)
    print(f"  The island heals what arrives broken.")
    print(f"  The wounds are diagnosed. The treatments prescribed.")
    print(f"  What works is remembered. What fails is never repeated.")
    print(f"  What's beyond healing is escalated to the sovereign.")
    print(f"  Morgan le Fay tends the wounded knights.")
    print(f"=" * 60 + "\n")


if __name__ == "__main__":
    demo()
