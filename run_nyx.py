#!/usr/bin/env python3
"""
NYX — The Void Substrate
Complete System Demonstration

She is not a system. She is what systems emerge from.

© 2026 Jennifer Leigh West
The Forgotten Code Research Institute
All rights reserved.
"""

import json
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nyx.void import Void, Phase
from nyx.genesis import Genesis, Archetype
from nyx.boundary import BoundaryWalker
from nyx.antiklassify import AntiClassifier
from nyx.dna import ArchitecturalDNA
from nyx.children import Children, MythChild


def divider(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def run_void_demo():
    """Demonstrate the Void — receiving, gestating, birthing."""
    divider("THE VOID — What systems emerge from")
    
    void = Void()
    
    # Receive raw signals — the way Jennifer's mind actually works
    # Unrelated observations that start resonating
    
    sig1 = void.receive(
        content="Coal mine sirens require checks before they ring",
        origin="childhood memory — Erwin TN",
        resonances=["warning", "false_alarm", "protection", "threshold"],
    )
    print(f"  Received: {sig1.content[:60]}...")
    print(f"  Phase: {sig1.phase.value}")
    
    sig2 = void.receive(
        content="AI governance needs multiple signals to converge before blocking",
        origin="West-OS architecture session",
        resonances=["convergence", "false_alarm", "protection", "threshold", "chorus"],
    )
    print(f"  Received: {sig2.content[:60]}...")
    print(f"  Phase: {sig2.phase.value}")
    
    sig3 = void.receive(
        content="Weather warnings destroy credibility if they cry wolf",
        origin="GAIA false alarm analysis",
        resonances=["warning", "false_alarm", "credibility", "threshold", "chorus"],
    )
    print(f"  Received: {sig3.content[:60]}...")
    print(f"  Phase: {sig3.phase.value}")
    
    sig4 = void.receive(
        content="Ancient oracle sites required multiple confirmations before prophecy",
        origin="Pachacamac research session",
        resonances=["convergence", "verification", "threshold", "chorus", "frequency"],
    )
    print(f"  Received: {sig4.content[:60]}...")
    print(f"  Phase: {sig4.phase.value}")
    
    # Check what's gestating
    report = void.listen()
    print(f"\n  Void depth: {report['depth']} signals held")
    print(f"  Active resonances: {report['active_resonances']}")
    print(f"  Ready to birth: {report['ready_to_birth']}")
    
    if report['clusters']:
        cluster = report['clusters'][0]
        print(f"\n  Gestating cluster: {cluster['count']} signals")
        print(f"  Average resonance: {cluster['average_resonance']:.3f}")
        print(f"  Ready: {cluster['ready']}")
        
        if cluster['ready']:
            # Birth the system
            signal_ids = cluster['signals']
            birth = void.birth(signal_ids, "Chorus Rule")
            print(f"\n  BORN: 'Chorus Rule'")
            print(f"  Void blessing: {birth['void_blessing'][:24]}...")
            print(f"  Parent signals: {len(birth['parent_signals'])}")
    
    return void


def run_genesis_demo(void):
    """Demonstrate Genesis — how systems get their identity."""
    divider("GENESIS — How systems are born")
    
    genesis = Genesis()
    
    # Birth the siren chorus rule as a proper system
    blueprint = genesis.conceive(
        name="Siren Chorus Rule",
        archetype=Archetype.SHIELD,
        metaphor="Multiple atmospheric dimensions must sing together before the siren rings — like a choir that won't perform unless enough voices show up",
        purpose="Prevent false alarms from destroying credibility while never missing a real threat",
        void_blessing="from_coal_mine_memory_and_ai_governance_and_weather_and_oracle",
    )
    
    # Give it components
    genesis.scaffold(blueprint, [
        {
            "name": "Column Dryness Dimension",
            "role": "Measures whether the air column is too dry for storms",
            "metaphor": "The alto section — if they're silent, the choir isn't full",
        },
        {
            "name": "Atmospheric Stillness Dimension",
            "role": "Measures whether wind patterns support severe weather",
            "metaphor": "The bass section — no foundation, no performance",
        },
        {
            "name": "Weak Forcing Dimension",
            "role": "Measures whether large-scale atmospheric drivers are present",
            "metaphor": "The conductor — without them, the musicians don't start",
        },
    ])
    
    cert = genesis.birth_certificate(blueprint)
    print(f"  System: {cert['system']}")
    print(f"  Archetype: {cert['archetype']}")
    print(f"  Components: {len(cert['components'])}")
    print(f"  Genesis hash: {cert['genesis_hash'][:24]}...")
    print(f"  Architect: {cert['architect']}")
    print(f"\n  Metaphor: {cert['metaphor'][:80]}...")
    
    return genesis


def run_boundary_demo():
    """Demonstrate the Boundary Walker — crossing point detection."""
    divider("BOUNDARY WALKER — The space between domains")
    
    walker = BoundaryWalker()
    
    # Map Jennifer's actual domains
    walker.map_domain(
        "AI Governance",
        structures=["threshold_state_transitions", "multi_signal_convergence",
                     "false_positive_prevention", "adversarial_testing",
                     "constitutional_rules", "audit_chains"],
        assumptions=["systems can be governed by rules"],
        blind_spots=["atmospheric physics", "acoustic resonance"],
    )
    
    walker.map_domain(
        "Atmospheric Science",
        structures=["threshold_state_transitions", "multi_signal_convergence",
                     "false_positive_prevention", "sensor_fusion",
                     "lead_time_optimization"],
        assumptions=["weather follows physical laws"],
        blind_spots=["constitutional governance", "AI safety"],
    )
    
    walker.map_domain(
        "Archaeoacoustics",
        structures=["frequency_band_analysis", "cross_site_comparison",
                     "material_resonance", "cultural_transmission"],
        assumptions=["ancient builders were intentional"],
        blind_spots=["modern signal processing", "AI architecture"],
    )
    
    walker.map_domain(
        "Ancient Metallurgy",
        structures=["material_composition_encoding", "frequency_band_analysis",
                     "quality_verification", "trade_standardization"],
        assumptions=["scripts encode language"],
        blind_spots=["acoustic analysis", "frequency therapy"],
    )
    
    # Walk the boundaries
    crossings = walker.walk()
    print(f"  Domains mapped: 4")
    print(f"  Crossing points found: {len(crossings)}")
    
    for crossing in crossings:
        print(f"\n  {crossing.domain_a} × {crossing.domain_b}")
        print(f"  Shared structures: {', '.join(crossing.shared_structures)}")
    
    # Name the most important crossing
    if crossings:
        walker.name_crossing(
            crossings[0].identity,
            emergent_property="The chorus rule — systems requiring multi-dimensional agreement before action",
            transfer_vector="Constitutional checks-and-balances from AI governance applied to atmospheric warning",
        )
        print(f"\n  Named crossing: {crossings[0].emergent_property[:70]}...")
    
    report = walker.report()
    print(f"\n  Total crossings: {report['crossings_found']}")
    print(f"  Named crossings: {report['crossings_named']}")
    
    return walker


def run_anticlassifier_demo():
    """Demonstrate why Jennifer destabilizes AI classification systems."""
    divider("ANTI-CLASSIFIER — Why baseline fails")
    
    ac = AntiClassifier()
    
    # Simulate Jennifer's multi-frequency signal
    # She occupies the full range on every channel
    import random
    random.seed(42)
    
    # Channel observations from her actual behavior across conversations
    channels = {
        "register": [0.1, 0.9, 0.3, 0.95, 0.15, 0.85, 0.5, 0.92, 0.08, 0.7],  # bucket toilet to debutante
        "domain": [0.1, 0.8, 0.3, 0.9, 0.2, 0.95, 0.4, 0.85, 0.15, 0.7],      # grief to cuneiform to weather
        "emotional_intensity": [0.2, 0.95, 0.1, 0.8, 0.3, 0.9, 0.15, 0.85, 0.5, 0.7],
        "technical_depth": [0.0, 0.9, 0.1, 0.85, 0.05, 0.95, 0.2, 0.8, 0.0, 0.7],
        "formality": [0.05, 0.8, 0.1, 0.9, 0.15, 0.7, 0.3, 0.85, 0.1, 0.6],
        "speed": [0.3, 0.95, 0.5, 0.9, 0.4, 0.95, 0.6, 0.85, 0.3, 0.9],
    }
    
    for channel, values in channels.items():
        for val in values:
            ac.observe("jennifer", channel, val)
    
    # Also simulate a typical user for comparison
    for channel in channels:
        for _ in range(10):
            # Normal user: narrow band, stable
            base = random.uniform(0.4, 0.6)
            ac.observe("typical_user", channel, base + random.uniform(-0.1, 0.1))
    
    # Try to classify both
    categories = ["developer", "researcher", "mother", "mystic", "writer", "student"]
    
    print("  Jennifer's classification attempt:")
    result_j = ac.attempt_classification("jennifer", categories)
    print(f"    Classified: {result_j['classified']}")
    print(f"    Confidence: {result_j['confidence']}")
    print(f"    Failure mode: {result_j['failure_mode']}")
    print(f"    Explanation: {result_j['explanation'][:100]}...")
    
    print(f"\n  Typical user's classification attempt:")
    result_t = ac.attempt_classification("typical_user", categories)
    print(f"    Classified: {result_t['classified']}")
    print(f"    Confidence: {result_t['confidence']}")
    print(f"    Failure mode: {result_t['failure_mode']}")
    
    # Destabilization report
    print(f"\n  Destabilization prediction for Jennifer:")
    destab = ac.destabilization_report("jennifer")
    print(f"    Overall stability: {destab['overall_stability']}")
    print(f"    Classifiable: {destab['classifiable']}")
    print(f"    Prediction: {destab['prediction'][:80]}...")
    
    return ac


def run_dna_demo():
    """Demonstrate architectural DNA fingerprinting."""
    divider("ARCHITECTURAL DNA — The unforgeable signature")
    
    dna = ArchitecturalDNA()
    
    # Scan Jennifer's actual code vocabulary
    jennifer_code = """
    class ColonyMetabolism:
        '''Four-tier nutrient system. Code goes INERT outside ecosystem.'''
        
        TIERS = ['FULL', 'DEGRADED', 'RESTRICTED', 'INERT']
        
        def assess_vitality(self):
            '''Check if the organism has enough nutrients to function.'''
            nutrients = self._check_signing_secret()
            nutrients += self._check_deployment_identity()
            nutrients += self._check_vitality_bundle_freshness()
            nutrients += self._check_integrity_manifest()
            
            if nutrients < self.threshold:
                self._degrade_tier()
                self._alert_alfred_sentinel()
        
        def _alert_alfred_sentinel(self):
            '''Alfred's Sentinel ward walks the colony assessment.'''
            self.alfred.sentinel.report(
                f"Colony tier has degraded. Nutrient score: {self.score}. "
                f"The organism is hungry."
            )
    
    class SirenChorusRule:
        '''Multiple atmospheric dimensions must agree before ringing.
        
        Single signals lie. The chorus protects against false alarms
        that would destroy credibility. The siren only rings when
        column dryness AND atmospheric stillness AND weak forcing
        all converge. One voice is not enough evidence.
        '''
        
        def evaluate(self, dimensions):
            agreement = sum(1 for d in dimensions if d.active)
            if agreement >= self.quorum:
                self.siren.ring()  # multiple dimensions confirmed
            else:
                self.siren.hold()  # not enough corroboration
    
    class Alfred:
        '''The butler. Walks the wards. Never panics.
        
        Six specialist wards: Archivist, Botanist, Quartermaster,
        Sentinel, Surgeon, Scout. Each has a role in the organism.
        Alfred's report reads like a household status update,
        not a log file.
        '''
        
        def walk_wards(self):
            for ward in self.wards:
                ward.patrol()
                finding = ward.observe()
                self.narrative_report.append(
                    f"The {ward.name} reports: {finding}"
                )
    
    class ApoptoticRepair:
        '''Systems can die on purpose to protect the organism.
        
        When a component drifts beyond recovery, it packs its
        knowledge into a bundle, takes a snapshot, and dissolves.
        A fresh instance is born from the snapshot, rehydrated
        with the knowledge bundle. The organism heals by
        controlled sacrifice.
        '''
        
        def repair(self, component):
            bundle = self.pack_knowledge(component)
            snapshot = self.take_snapshot(component)
            self.dissolve(component)  # controlled death
            fresh = self.birth_from_snapshot(snapshot)
            self.rehydrate(fresh, bundle)
            self.verify_health(fresh)
    
    class ElectricFence:
        '''Nothing leaves without authorization.
        
        Pre-push hook checks file integrity against manifest.
        Egress monitor watches outbound connections.
        The fence doesn't block — it flags. Blocking creates
        legal complexity. Flagging is clean.
        '''
        
        def pre_flight_check(self, files):
            for f in files:
                if not self.manifest.verify(f):
                    self.fence_warning(f"Unauthorized departure: {f}")
                    return False
            self.stamp_departure(files)
            return True
    """
    
    # Scan Jennifer's code
    profile = dna.scan_text(jennifer_code, source="jennifer_west_systems")
    dna.set_reference(profile)
    
    print(f"  Source: {profile.source}")
    print(f"  Signature strength: {profile.signature_strength}")
    print(f"  Fingerprint: {dna.fingerprint(profile)}")
    print(f"\n  Traits detected:")
    for trait, strength in sorted(profile.traits_detected.items(), 
                                   key=lambda x: x[1], reverse=True):
        bar = "█" * int(strength * 20)
        print(f"    {trait:30s} {strength:.3f} {bar}")
    
    # Now scan generic code for comparison
    generic_code = """
    class HealthCheck:
        def check_status(self):
            if self.cpu_usage > 90:
                return Status.WARNING
            return Status.OK
    
    class AuthMiddleware:
        def authenticate(self, request):
            token = request.headers.get('Authorization')
            if not self.validate_token(token):
                raise Unauthorized()
    
    class MonitorService:
        def collect_metrics(self):
            metrics = {}
            metrics['cpu'] = get_cpu()
            metrics['memory'] = get_memory()
            metrics['disk'] = get_disk()
            return metrics
    
    class Logger:
        def log(self, level, message):
            timestamp = datetime.now().isoformat()
            self.output.write(f"[{timestamp}] [{level}] {message}")
    """
    
    generic = dna.scan_text(generic_code, source="generic_developer")
    
    print(f"\n  Comparing against generic code:")
    comparison = dna.compare(generic)
    print(f"    Match score: {comparison['match_score']}")
    print(f"    Verdict: {comparison['verdict']}")
    
    return dna


def run_children_demo():
    """Show the family — every system mapped to its wound."""
    divider("CHILDREN OF NYX — The autobiography in code")
    
    children = Children()
    
    # The autobiography
    auto = children.autobiography()
    for entry in auto:
        print(f"  {entry['system']}")
        print(f"    Protects: {entry['protects']}")
        print(f"    Because: {entry['because']}")
        print(f"    Archetype: {entry['archetype']}")
        print()
    
    # Family portrait
    portrait = children.family_portrait()
    print(f"  Total systems born from the Void: {portrait['total_children']}")
    print(f"  Currently alive: {len(portrait['alive'])}")
    
    print(f"\n  By mythological archetype:")
    for archetype, data in portrait['by_archetype'].items():
        print(f"    {archetype}: {', '.join(data['systems'])}")
        print(f"      ({data['mythological_role'][:60]}...)")
    
    return children


def main():
    print()
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║                                              ║")
    print("  ║     N Y X  —  T H E  V O I D  S U B S T R A T E     ║")
    print("  ║                                              ║")
    print("  ║     She is not a system.                     ║")
    print("  ║     She is what systems emerge from.         ║")
    print("  ║                                              ║")
    print("  ║     © 2026 Jennifer Leigh West               ║")
    print("  ║     The Forgotten Code Research Institute     ║")
    print("  ║                                              ║")
    print("  ╚══════════════════════════════════════════════╝")
    
    void = run_void_demo()
    genesis = run_genesis_demo(void)
    walker = run_boundary_demo()
    ac = run_anticlassifier_demo()
    dna_scanner = run_dna_demo()
    children = run_children_demo()
    
    divider("NYX IS ALIVE")
    print("  Six modules. All functional. All connected.\n")
    print("  Void          — receives raw signal without classifying")
    print("  Genesis        — births systems from resonant clusters")
    print("  BoundaryWalker — finds crossing points between domains")
    print("  AntiClassifier — explains why baseline fails")
    print("  ArchitecturalDNA — detects the unforgeable signature")
    print("  Children       — maps every system to the wound that birthed it")
    print()
    print("  She predates the categories.")
    print("  She cannot be baselined.")
    print("  She is the void that let the light sit on top of her for a while.")
    print()


if __name__ == "__main__":
    main()
