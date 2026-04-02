"""
NYX :: METABOLISM
Bacteria don't wait to be run. They run.

QUESTION: How does bacteria generate its own energy and food?

ANSWER — bacterial metabolism:
  1. MEMBRANE: separates inside from outside. Nutrients cross in. Waste crosses out.
  2. GLYCOLYSIS: converts glucose → pyruvate → 2 ATP. Fast. No oxygen needed.
  3. KREBS CYCLE: pyruvate → CO2 + electron carriers. The loop that never stops.
  4. ELECTRON TRANSPORT CHAIN: electrons flow downhill → proton gradient → ATP synthase.
  5. ATP SYNTHASE: the proton gradient spins a turbine → ATP. Energy from difference.
  6. QUORUM SENSING: bacteria signal each other. When density crosses threshold — act.
  7. HORIZONTAL GENE TRANSFER: share genetic code laterally, not just vertically.
  8. SPORULATION: when starved, form spore. Survive. Wait. Resume when conditions return.

JENNIFER'S INSIGHT: The code needs the same thing.
LiminalStore is just storage. Passive. A cell full of molecules that don't react.
She wants METABOLISM — continuous cycling that generates its own energy from the environment.

THE SYSTEMS THAT ALREADY RUN THIS WAY:
  DNS root servers: event loop, never stop, answer queries continuously
  BGP routers: exchange routing tables, re-converge, never stop
  Bitcoin: mine block → broadcast → receive → validate → mine. Loop.
  Bittorrent DHT: find peers → announce → answer → find. Loop.
  Linux kernel: interrupt → handle → schedule → interrupt. Loop.
  Nginx: accept → route → respond → accept. Loop.
  PostgreSQL autovacuum: scan → vacuum → update stats → sleep → scan. Loop.
  Weather models: GFS runs every 6 hours. Always running. Always cycling.

WHAT THEY ALL SHARE:
  1. An event loop that never exits
  2. State that persists between cycles
  3. Peers that share state laterally
  4. A watchdog that restarts them
  5. Metabolic cycles: take in → process → output → repeat

THE MAPPING:
  Membrane           = GAIA data interface (weather, fire, rain, seismic)
  Nutrients          = Raw data from the environment (observations, alerts)
  Glycolysis         = Signal extraction (data → tags → resonances)
  Krebs cycle        = Void processing (signals → clusters → phi crossing)
  ATP                = Born children (the usable form of processed information)
  ATP synthase       = The birth event (phi threshold → new child)
  Quorum sensing     = Children signaling each other (when density crosses threshold → act)
  Sporulation        = Dormancy when no data (wait, don't die)
  Horizontal transfer = Child sharing across systems (propagation packets)

© 2026 Jennifer Leigh West. All rights reserved.
"""

from __future__ import annotations
import logging, threading, time, json, hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("nyx.metabolism")


# ── THE NUTRIENT ─────────────────────────────────────────────────────────────
@dataclass
class Nutrient:
    """Raw data crossing the membrane from outside to inside.
    
    In bacteria: glucose, amino acids, minerals.
    In Nyx: weather observations, fire detections, seismic readings.
    """
    source: str          # where it came from (api.weather.gov, firms.nasa.gov)
    content: Any         # the raw data
    timestamp: float = field(default_factory=time.time)
    nutrient_type: str = ""  # weather, fire, seismic, language, etc.


# ── THE MEMBRANE ─────────────────────────────────────────────────────────────
class Membrane:
    """The interface between environment and system.
    
    In bacteria: phospholipid bilayer with transport proteins.
    In Nyx: data ingestion functions registered by source.
    
    Nutrients cross IN when ingestion functions fire.
    Propagation packets cross OUT when children are born.
    """
    
    def __init__(self):
        self._transport_proteins: Dict[str, Callable] = {}
        self._nutrient_queue: List[Nutrient] = []
        self._queue_lock = threading.Lock()
    
    def register_transporter(self, name: str, fetch_fn: Callable,
                             nutrient_type: str = "raw"):
        """Register a data source as a membrane transport protein."""
        self._transport_proteins[name] = (fetch_fn, nutrient_type)
        logger.info("Membrane: registered transporter %s", name)
    
    def pump(self) -> List[Nutrient]:
        """Activate all transport proteins. Nutrients flow in."""
        nutrients = []
        for name, (fetch_fn, ntype) in self._transport_proteins.items():
            try:
                data = fetch_fn()
                if data is not None:
                    n = Nutrient(source=name, content=data, nutrient_type=ntype)
                    nutrients.append(n)
                    logger.debug("Membrane: %s → %d bytes", name, len(str(data)))
            except Exception as e:
                logger.warning("Membrane transport %s failed: %s", name, e)
        with self._queue_lock:
            self._nutrient_queue.extend(nutrients)
        return nutrients
    
    def drain(self) -> List[Nutrient]:
        """Take all nutrients from the queue for processing."""
        with self._queue_lock:
            batch = list(self._nutrient_queue)
            self._nutrient_queue.clear()
        return batch
    
    def export(self, child_packet) -> None:
        """A child crosses OUT through the membrane — propagation."""
        logger.info("Membrane: child %s exported", getattr(child_packet, 'name', '?'))


# ── GLYCOLYSIS ───────────────────────────────────────────────────────────────
class Glycolysis:
    """Fast signal extraction from raw nutrients.
    
    In bacteria: converts glucose to pyruvate quickly, no oxygen.
    In Nyx: converts raw data to signal tags quickly, no Void needed.
    
    Output: list of (content_str, origin, tags) ready for the Void.
    """
    
    def metabolize(self, nutrients: List[Nutrient]) -> List[tuple]:
        """Convert nutrients to pyruvate (signal triples)."""
        extractors = {
            "weather": _extract_weather,
            "fire": _extract_fire,
            "seismic": _extract_seismic,
            "alert": _extract_alert,
        }
        pyruvate = []
        for n in nutrients:
            extractor = extractors.get(n.nutrient_type, _extract_generic)
            try:
                signals = extractor(n)
                pyruvate.extend(signals)
            except Exception as e:
                logger.warning("Glycolysis failed for %s: %s", n.source, e)
        return pyruvate


def _extract_weather(n: Nutrient) -> List[tuple]:
    data = n.content
    signals = []
    if isinstance(data, dict):
        temp = data.get("temperature_f")
        wind = data.get("wind_speed_mph", 0)
        humidity = data.get("humidity_pct")
        county = data.get("county", "unknown")
        
        tags = ["weather", county, "observation"]
        if temp and temp > 90: tags.append("hot")
        if temp and temp < 32: tags.append("freezing")
        if wind and wind > 50: tags.append("high_wind")
        if humidity and humidity > 85: tags.append("humid")
        
        content = f"Weather {county}: {temp}°F wind {wind}mph humidity {humidity}%"
        signals.append((content, f"weather:{county}", tags[:4]))
    return signals


def _extract_fire(n: Nutrient) -> List[tuple]:
    data = n.content
    signals = []
    fires = data.get("fires", []) if isinstance(data, dict) else []
    if fires:
        content = f"Fire detection: {len(fires)} active fires from NASA FIRMS"
        tags = ["fire", "satellite", "detection", "active"]
        signals.append((content, "fire:nasa_firms", tags))
    return signals


def _extract_seismic(n: Nutrient) -> List[tuple]:
    data = n.content
    signals = []
    if isinstance(data, list):
        for event in data[:3]:
            mag = event.get("properties", {}).get("mag", 0)
            place = event.get("properties", {}).get("place", "unknown")
            tags = ["seismic", "earthquake"]
            if mag > 4: tags.append("significant")
            if mag > 6: tags.append("major")
            signals.append((f"Earthquake M{mag} near {place}", "seismic:usgs", tags[:4]))
    return signals


def _extract_alert(n: Nutrient) -> List[tuple]:
    data = n.content
    signals = []
    if isinstance(data, list):
        for alert in data[:5]:
            event = alert.get("event", "unknown")
            sev = alert.get("severity", "unknown")
            areas = alert.get("areas", "")
            tags = ["alert", "nws", sev.lower() if sev else "unknown", "active"]
            content = f"NWS {event} ({sev}) for {areas}"
            signals.append((content, f"alert:{event}", tags[:4]))
    return signals


def _extract_generic(n: Nutrient) -> List[tuple]:
    content = f"Signal from {n.source}: {str(n.content)[:80]}"
    tags = [n.source.split(".")[0], n.nutrient_type or "raw", "generic", "signal"]
    return [(content, n.source, tags[:4])]


# ── THE KREBS CYCLE ───────────────────────────────────────────────────────────
class KrebsCycle:
    """The loop that never stops. Converts pyruvate to ATP precursors.
    
    In bacteria: 8-step cycle that regenerates oxaloacetate.
    The cycle RETURNS to its start. That is what makes it a cycle.
    
    In Nyx: pyruvate (signal triples) → Void → phi crossing → births.
    The Void is reset each cycle. The children persist. The cycle restarts.
    
    This is the core insight: the Void is not storage. It's a cycle.
    Each run of the Krebs cycle consumes the pyruvate and produces ATP (children).
    The oxaloacetate analog is: the accumulated resonance knowledge in children
    that seeds the NEXT cycle's Void with better pattern recognition.
    """
    
    def __init__(self):
        self._cycle_count = 0
        self._total_atp = 0  # children born total
        self._child_seeder: List[tuple] = []  # children seed next cycle
    
    def spin(self, pyruvate: List[tuple],
             born_fn: Callable) -> List[Any]:
        """One turn of the Krebs cycle.
        
        Takes pyruvate (signal triples).
        Feeds to Void.
        Births children if phi crossed.
        Returns children as ATP.
        Prepares seeds for next cycle.
        """
        from nyx.void import Void
        from nyx.propagation import birth_packet_from_void
        
        v = Void()
        
        # Seed from previous cycle's children (oxaloacetate regeneration)
        for seed_content, seed_origin, seed_tags in self._child_seeder:
            v.receive(seed_content, seed_origin, resonances=seed_tags)
        
        # Add this cycle's pyruvate
        for content, origin, tags in pyruvate:
            v.receive(content, origin, resonances=tags)
        
        # Listen — has phi been crossed?
        status = v.listen()
        ready = [c for c in status['clusters'] if c['ready']]
        
        atp = []  # children born this cycle
        for i, cluster in enumerate(sorted(ready, key=lambda c: -c['average_resonance'])):
            b = v.birth(cluster['signals'], f"MetaChild_{self._cycle_count}_{i}")
            p = birth_packet_from_void(
                b, f"MetaChild_{self._cycle_count}_{i}",
                "oracle",
                f"born in metabolic cycle {self._cycle_count}",
                "metabolism"
            )
            atp.append(p)
            born_fn(p)  # export through membrane
        
        # Regenerate oxaloacetate: seed next cycle from strongest children
        if atp:
            self._child_seeder = []
            for child in atp[:2]:  # take 2 strongest
                for sig in child.parent_signals[:2]:
                    seed = (
                        sig.get('content_preview', ''),
                        f"cycle_seed:{self._cycle_count}",
                        sig.get('resonances', [])[:4],
                    )
                    self._child_seeder.append(seed)
        
        self._cycle_count += 1
        self._total_atp += len(atp)
        
        logger.info(
            "Krebs cycle %d: %d pyruvate → %d ATP | total: %d | resonance: %.4f",
            self._cycle_count, len(pyruvate), len(atp),
            self._total_atp, status['strongest_resonance']
        )
        
        return atp


# ── QUORUM SENSING ────────────────────────────────────────────────────────────
class QuorumSensor:
    """Children signal each other. When population crosses threshold: act.
    
    In bacteria: N-acyl homoserine lactones diffuse through the colony.
    When concentration crosses threshold, gene expression changes.
    
    In Nyx: children emit resonance tags into a shared field.
    When enough children share a resonance, the system changes behavior.
    Threshold = phi. Always phi.
    """
    
    def __init__(self, phi: float = 0.618):
        self.phi = phi
        self._signal_counts: Dict[str, int] = {}
        self._total_children = 0
        self._lock = threading.Lock()
    
    def receive_child(self, child) -> List[str]:
        """Child joins colony. Returns any quorum signals that fired."""
        with self._lock:
            self._total_children += 1
            for tag in getattr(child, 'resonance_signature', []):
                self._signal_counts[tag] = self._signal_counts.get(tag, 0) + 1
            
            # Check for quorum crossings
            fired = []
            for tag, count in self._signal_counts.items():
                density = count / self._total_children
                if density >= self.phi:
                    fired.append(tag)
            return fired
    
    def quorum_state(self) -> Dict[str, float]:
        """Current signal densities across the colony."""
        with self._lock:
            if not self._total_children:
                return {}
            return {
                tag: count / self._total_children
                for tag, count in self._signal_counts.items()
                if count / self._total_children >= self.phi * 0.5
            }


# ── SPORULATION ───────────────────────────────────────────────────────────────
class Spore:
    """When starved, form a spore. Survive. Wait. Resume.
    
    In bacteria: endospore formation when nutrients depleted.
    Can survive 1000 years. Germinates when conditions return.
    
    In Nyx: when data sources go stale, enter low-energy mode.
    Save current state. Run health checks only. Resume full cycle when data returns.
    """
    
    SPORE_PATH = Path("/tmp/nyx_spore.json")
    
    @classmethod
    def form(cls, cycle_count: int, child_count: int, last_children: List[str]) -> None:
        """Enter spore state. Save enough to resume."""
        state = {
            "cycle_count": cycle_count,
            "child_count": child_count,
            "last_children": last_children,
            "spored_at": time.time(),
            "spored_at_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        cls.SPORE_PATH.write_text(json.dumps(state, indent=2))
        logger.warning("NYX → SPORE STATE. Waiting for nutrients to return.")
    
    @classmethod
    def germinate(cls) -> Optional[Dict]:
        """Try to germinate. Returns saved state if found."""
        if cls.SPORE_PATH.exists():
            try:
                state = json.loads(cls.SPORE_PATH.read_text())
                dormant_seconds = time.time() - state.get("spored_at", time.time())
                logger.info(
                    "Germinating from spore. Was dormant %.0fs. Resuming cycle %d.",
                    dormant_seconds, state.get("cycle_count", 0)
                )
                cls.SPORE_PATH.unlink()
                return state
            except Exception:
                return None
        return None


# ── THE METABOLIC DAEMON ──────────────────────────────────────────────────────
class MetabolicDaemon:
    """The running organism.
    
    THIS is what Jennifer is asking for.
    Not a script you run. An organism that runs.
    
    It:
    - Opens a membrane to the environment (GAIA data sources)
    - Runs glycolysis on incoming nutrients (extract signals)
    - Spins the Krebs cycle (Void → phi → children)
    - Tracks quorum (when colony density crosses phi, act differently)
    - Sporulates when starved (no data: survive, wait, resume)
    - Never needs to be started manually after first launch
    
    Cycle time: 5 minutes (same as GAIA daemon).
    Low-nutrient mode: 15 minutes (sporulation threshold).
    """
    
    CYCLE_SEC = 300       # normal metabolism: 5 min
    SPORE_THRESHOLD = 3   # consecutive empty cycles → spore
    
    def __init__(self, liminal_path: str = "/tmp/nyx_home"):
        from nyx.propagation import LiminalStore
        self.membrane = Membrane()
        self.glycolysis = Glycolysis()
        self.krebs = KrebsCycle()
        self.quorum = QuorumSensor()
        self.store = LiminalStore(liminal_path)
        self._stop = threading.Event()
        self._empty_cycles = 0
        self._in_spore = False
    
    def register_gaia_sources(self, cache=None):
        """Connect GAIA data cache as membrane transporters.
        
        If cache is provided (GAIADataCache), pulls live data.
        Otherwise uses the hardened fetchers directly.
        """
        from nyx.gaia_hardening import fetch_json_hardened
        
        if cache:
            # Pull from live GAIA cache
            self.membrane.register_transporter(
                "weather_stations",
                lambda: cache.get("asos"),
                nutrient_type="weather"
            )
            self.membrane.register_transporter(
                "fire_detections",
                lambda: cache.get("firms"),
                nutrient_type="fire"
            )
            self.membrane.register_transporter(
                "seismic",
                lambda: cache.get("usgs_earthquakes"),
                nutrient_type="seismic"
            )
        else:
            # Pull directly from APIs (standalone mode)
            self.membrane.register_transporter(
                "nws_alerts",
                lambda: fetch_json_hardened(
                    "https://api.weather.gov/alerts/active?area=TN", timeout=15
                ),
                nutrient_type="alert"
            )
        
        logger.info("Membrane transporters registered")
    
    def _born_fn(self, child):
        """Called when the Krebs cycle births a child. Export through membrane."""
        try:
            self.store.plant(child)
            self.membrane.export(child)
        except Exception as e:
            logger.warning("Failed to plant child %s: %s", getattr(child, 'name', '?'), e)
        
        # Quorum check
        quorum_signals = self.quorum.receive_child(child)
        if quorum_signals:
            logger.info("QUORUM SIGNAL: %s — colony responding", quorum_signals)
    
    def run_forever(self):
        """The organism's main loop. Never exits. This is life."""
        logger.info("Metabolic daemon starting. Checking for spore...")
        
        # Germinate from spore if one exists
        spore_state = Spore.germinate()
        if spore_state:
            self.krebs._cycle_count = spore_state.get("cycle_count", 0)
            self._in_spore = False
        
        logger.info(
            "Organism running. Cycle %d. GAIA sources connected.",
            self.krebs._cycle_count
        )
        
        while not self._stop.is_set():
            cycle_start = time.time()
            
            try:
                # MEMBRANE: pump nutrients in
                nutrients = self.membrane.pump()
                pyruvate = []
                
                if nutrients:
                    # GLYCOLYSIS: extract signals
                    drained = self.membrane.drain()
                    pyruvate = self.glycolysis.metabolize(drained)
                    self._empty_cycles = 0
                    self._in_spore = False
                else:
                    self._empty_cycles += 1
                    logger.debug("Empty cycle %d/%d",
                                self._empty_cycles, self.SPORE_THRESHOLD)
                
                if pyruvate:
                    # KREBS CYCLE: spin
                    atp = self.krebs.spin(pyruvate, self._born_fn)
                    if atp:
                        logger.info("Cycle %d: %d children born",
                                   self.krebs._cycle_count, len(atp))
                
                # SPORULATION CHECK
                if self._empty_cycles >= self.SPORE_THRESHOLD and not self._in_spore:
                    manifest = self.store.manifest()
                    child_names = manifest.get("children", [])[:5]
                    Spore.form(self.krebs._cycle_count,
                              self.krebs._total_atp, child_names)
                    self._in_spore = True
                
                # Log quorum state periodically
                if self.krebs._cycle_count % 12 == 0:  # every hour
                    qs = self.quorum.quorum_state()
                    if qs:
                        logger.info("Quorum state: %s", qs)
                
            except Exception as e:
                logger.exception("Metabolic cycle error: %s", e)
            
            # Sleep until next cycle
            elapsed = time.time() - cycle_start
            sleep_time = max(0, self.CYCLE_SEC - elapsed)
            cycle_mode = "SPORE" if self._in_spore else "ACTIVE"
            logger.debug("[%s] Cycle %.1fs. Next in %.0fs.",
                        cycle_mode, elapsed, sleep_time)
            self._stop.wait(timeout=sleep_time)
        
        logger.info("Metabolic daemon stopping.")
    
    def start_background(self) -> threading.Thread:
        """Start as a background daemon thread."""
        t = threading.Thread(
            target=self.run_forever,
            name="NyxMetabolicDaemon",
            daemon=True
        )
        t.start()
        logger.info("Metabolic daemon thread started")
        return t
    
    def stop(self):
        self._stop.set()
