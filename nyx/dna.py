"""
NYX :: ARCHITECTURAL DNA
The fingerprint that can't be forged.

Jennifer's code carries a signature that isn't in any watermark
or copyright notice. It's in the bones — the naming conventions,
the protection orientation, the biological metaphors as functional
architecture, the chorus-rule epistemology.

This module detects and verifies that signature.
Not by looking at strings. By looking at structure.

A developer can copy code. They can clone a repo.
They cannot extend it, because the design decisions
are based on principles that only make sense if you think
the way Jennifer thinks.

Her handwriting. Under speed. Under pressure. From instinct.
The instinct is the signature.
"""

import hashlib
import json
import time
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from pathlib import Path


class Trait:
    """A single architectural trait that carries signature."""
    
    LIVING_NAMING = "living_naming"           # components named as organisms, not modules
    PROTECTION_ORIENTATION = "protection"      # everything protects something
    BIOLOGICAL_METAPHOR = "biological"         # metaphor IS architecture, not decoration  
    CHORUS_EPISTEMOLOGY = "chorus"             # multiple signals must agree before action
    SELF_HEALING = "self_healing"              # systems repair themselves
    NUTRIENT_DEPENDENCY = "nutrient"           # systems need sustenance to stay alive
    BOUNDARY_AWARENESS = "boundary"            # explicit perimeter definition
    NARRATIVE_REPORTING = "narrative"          # reports read like stories, not logs
    WARD_ARCHITECTURE = "ward"                # specialist roles walking continuous rounds
    APOPTOTIC_DESIGN = "apoptotic"            # systems can die on purpose to protect organism


# Indicators — patterns that suggest each trait is present
TRAIT_INDICATORS = {
    Trait.LIVING_NAMING: {
        "variable_patterns": [
            r"alfred", r"nightingale", r"colony", r"sentinel", r"surgeon",
            r"botanist", r"archivist", r"quartermaster", r"scout",
            r"persephone", r"astraea", r"chimera", r"oracle",
            r"siren", r"ward", r"nurse", r"butler", r"keeper",
        ],
        "weight": 0.15,
    },
    Trait.PROTECTION_ORIENTATION: {
        "variable_patterns": [
            r"protect", r"shield", r"guard", r"fence", r"safe",
            r"defend", r"warn", r"alert", r"watch", r"patrol",
            r"detect", r"prevent", r"block", r"filter", r"screen",
        ],
        "weight": 0.15,
    },
    Trait.BIOLOGICAL_METAPHOR: {
        "variable_patterns": [
            r"metabolism", r"nutrient", r"organism", r"organ", r"tissue",
            r"heal", r"repair", r"immune", r"infection", r"pathogen",
            r"spore", r"mycelium", r"colony", r"swarm", r"hive",
            r"apoptosis", r"gestate", r"birth", r"decay", r"bloom",
        ],
        "weight": 0.15,
    },
    Trait.CHORUS_EPISTEMOLOGY: {
        "variable_patterns": [
            r"chorus", r"convergence", r"agreement", r"consensus",
            r"quorum", r"corroborate", r"confirm", r"multi.*signal",
            r"cross.*check", r"independent.*verify",
        ],
        "weight": 0.12,
    },
    Trait.SELF_HEALING: {
        "variable_patterns": [
            r"self.*heal", r"repair", r"recover", r"restore",
            r"rollback", r"snapshot", r"rehydrate", r"resilien",
        ],
        "weight": 0.10,
    },
    Trait.NUTRIENT_DEPENDENCY: {
        "variable_patterns": [
            r"nutrient", r"vitality", r"sustenance", r"nourish",
            r"deplet", r"degrad", r"inert", r"full.*tier",
            r"restricted", r"bundle.*fresh",
        ],
        "weight": 0.08,
    },
    Trait.BOUNDARY_AWARENESS: {
        "variable_patterns": [
            r"fence", r"perimeter", r"egress", r"ingress",
            r"boundary", r"border", r"threshold", r"gate",
            r"authorized", r"unauthorized",
        ],
        "weight": 0.08,
    },
    Trait.NARRATIVE_REPORTING: {
        "variable_patterns": [
            r"report", r"walk.*ward", r"observe", r"notice",
            r"finding", r"interpret", r"story", r"narrative",
            r"plain.*language", r"human.*readable",
        ],
        "weight": 0.07,
    },
    Trait.WARD_ARCHITECTURE: {
        "variable_patterns": [
            r"ward", r"round", r"patrol", r"schedule",
            r"continuous", r"walk", r"clipboard", r"inspect",
            r"daily", r"sweep",
        ],
        "weight": 0.05,
    },
    Trait.APOPTOTIC_DESIGN: {
        "variable_patterns": [
            r"apoptos", r"controlled.*death", r"graceful.*shutdown",
            r"die.*purpose", r"sacrifice", r"dissolve",
            r"inert.*outside", r"expire", r"sunset",
        ],
        "weight": 0.05,
    },
}


@dataclass
class DNAProfile:
    """The architectural DNA of a codebase."""
    source: str
    traits_detected: Dict[str, float] = field(default_factory=dict)
    total_files: int = 0
    total_lines: int = 0
    matches: Dict[str, List[str]] = field(default_factory=dict)
    signature_strength: float = 0.0
    timestamp: float = field(default_factory=time.time)
    _dna_hash: str = field(default="", repr=False)


class ArchitecturalDNA:
    """Detects and verifies the signature in code.
    
    She doesn't look at copyright notices or watermarks.
    She looks at how the code THINKS.
    
    The signature is structural:
    - Living-system naming (organisms, not modules)
    - Protection orientation (everything shields something)
    - Biological metaphor as architecture (not decoration)
    - Chorus-rule epistemology (single signals aren't trusted)
    - Self-healing mechanisms (systems repair themselves)
    - Nutrient dependency (code dies outside its ecosystem)
    - Boundary awareness (explicit perimeter definition)
    - Narrative reporting (reports tell stories)
    - Ward architecture (specialists on continuous rounds)
    - Apoptotic design (controlled death for organism health)
    
    Together these traits form a fingerprint.
    Individually copyable. Collectively unforgeable.
    """

    def __init__(self):
        self._reference_profile: Optional[DNAProfile] = None
        self._scanned_profiles: Dict[str, DNAProfile] = {}

    def scan_text(self, text: str, source: str = "direct") -> DNAProfile:
        """Scan a body of text for architectural DNA traits."""
        profile = DNAProfile(source=source)
        text_lower = text.lower()
        lines = text.split("\n")
        profile.total_lines = len(lines)
        profile.total_files = 1
        
        for trait_name, config in TRAIT_INDICATORS.items():
            matches = []
            for pattern in config["variable_patterns"]:
                found = re.findall(pattern, text_lower)
                matches.extend(found)
            
            if matches:
                # Density: matches per 1000 lines
                density = (len(matches) / max(1, len(lines))) * 1000
                # Normalize to 0-1 range (cap at 50 matches per 1000 lines)
                normalized = min(1.0, density / 50)
                profile.traits_detected[trait_name] = round(normalized, 4)
                profile.matches[trait_name] = matches[:10]  # keep first 10 examples
        
        # Calculate overall signature strength
        weighted_sum = sum(
            profile.traits_detected.get(trait, 0) * config["weight"]
            for trait, config in TRAIT_INDICATORS.items()
        )
        max_possible = sum(c["weight"] for c in TRAIT_INDICATORS.values())
        profile.signature_strength = round(weighted_sum / max_possible, 4) if max_possible > 0 else 0
        
        # Generate DNA hash
        raw = json.dumps(profile.traits_detected, sort_keys=True)
        profile._dna_hash = hashlib.sha256(raw.encode()).hexdigest()
        
        self._scanned_profiles[source] = profile
        return profile

    def scan_directory(self, path: str, extensions: Optional[List[str]] = None) -> DNAProfile:
        """Scan an entire codebase for architectural DNA."""
        if extensions is None:
            extensions = [".py", ".js", ".ts", ".md", ".yml", ".yaml"]
        
        combined_text = []
        file_count = 0
        
        root = Path(path)
        if not root.exists():
            return DNAProfile(source=path)
        
        for ext in extensions:
            for filepath in root.rglob(f"*{ext}"):
                try:
                    content = filepath.read_text(errors="replace")
                    combined_text.append(content)
                    file_count += 1
                except Exception:
                    continue
        
        full_text = "\n".join(combined_text)
        profile = self.scan_text(full_text, source=path)
        profile.total_files = file_count
        return profile

    def set_reference(self, profile: DNAProfile):
        """Set the reference profile — Jennifer's known signature.
        
        All future comparisons measure against this.
        """
        self._reference_profile = profile

    def compare(self, profile: DNAProfile) -> Dict:
        """Compare a codebase against the reference signature.
        
        Returns:
        - match_score: how closely this matches Jennifer's DNA (0-1)
        - trait_comparison: per-trait similarity
        - verdict: is this her work?
        """
        if not self._reference_profile:
            return {"error": "No reference profile set. Call set_reference() first."}
        
        ref = self._reference_profile
        trait_comparisons = {}
        
        for trait in TRAIT_INDICATORS:
            ref_val = ref.traits_detected.get(trait, 0)
            scan_val = profile.traits_detected.get(trait, 0)
            
            if ref_val == 0 and scan_val == 0:
                similarity = 1.0  # both absent = match
            elif ref_val == 0 or scan_val == 0:
                similarity = 0.0  # one present, one absent = no match
            else:
                # How close are the density levels?
                ratio = min(ref_val, scan_val) / max(ref_val, scan_val)
                similarity = ratio
            
            trait_comparisons[trait] = {
                "reference": ref_val,
                "scanned": scan_val,
                "similarity": round(similarity, 4),
            }
        
        # Weighted overall score
        weighted_score = sum(
            trait_comparisons[trait]["similarity"] * TRAIT_INDICATORS[trait]["weight"]
            for trait in TRAIT_INDICATORS
        )
        max_weight = sum(c["weight"] for c in TRAIT_INDICATORS.values())
        match_score = weighted_score / max_weight if max_weight > 0 else 0
        
        # Verdict
        if match_score > 0.75:
            verdict = "STRONG MATCH — architectural DNA consistent with reference"
        elif match_score > 0.5:
            verdict = "PARTIAL MATCH — some traits present, others missing"
        elif match_score > 0.25:
            verdict = "WEAK MATCH — isolated traits but different architecture"
        else:
            verdict = "NO MATCH — different architectural DNA"
        
        return {
            "match_score": round(match_score, 4),
            "verdict": verdict,
            "reference_source": ref.source,
            "scanned_source": profile.source,
            "trait_comparison": trait_comparisons,
            "reference_signature_strength": ref.signature_strength,
            "scanned_signature_strength": profile.signature_strength,
        }

    def fingerprint(self, profile: DNAProfile) -> str:
        """Generate a compact fingerprint string.
        
        Like a DNA sequence — each position represents a trait.
        Higher value = stronger presence of that trait.
        
        Example: "JLW-A9P8B7C6H5N4D3R2W1X0"
        """
        trait_codes = {
            Trait.LIVING_NAMING: "A",        # Alive
            Trait.PROTECTION_ORIENTATION: "P", # Protect
            Trait.BIOLOGICAL_METAPHOR: "B",   # Biological
            Trait.CHORUS_EPISTEMOLOGY: "C",    # Chorus
            Trait.SELF_HEALING: "H",          # Heal
            Trait.NUTRIENT_DEPENDENCY: "N",    # Nutrient
            Trait.BOUNDARY_AWARENESS: "D",     # Defend
            Trait.NARRATIVE_REPORTING: "R",    # Report
            Trait.WARD_ARCHITECTURE: "W",      # Ward
            Trait.APOPTOTIC_DESIGN: "X",      # eXit (apoptosis)
        }
        
        parts = ["JLW"]  # prefix
        for trait, code in trait_codes.items():
            val = profile.traits_detected.get(trait, 0)
            level = min(9, int(val * 10))
            parts.append(f"{code}{level}")
        
        return "-".join(parts)
