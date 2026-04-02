"""
NYX :: PATH GUARDIAN
Every maze has a ladder.

When a path is dead, the Guardian finds the living route.
When a certificate is broken, she finds the mirror.
When a door is refused, she walks the wall until she finds the gap.

This is not circumvention. This is what water does.
Water does not force. It finds.

The Guardian carries the manifest of broken paths from the expedition.
For each broken path she holds a list of alternative routes —
paths that carry the same truth through different terrain.

She probes each alternative until she finds one breathing.
Then she plants that path in the liminal store as a ladder —
a propagation packet that any child can follow home.

© 2026 Jennifer Leigh West. All rights reserved.
"""

from __future__ import annotations
import socket, ssl, time, json, urllib.request, urllib.error
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from pathlib import Path


@dataclass
class PathStatus:
    host: str
    alive: bool
    latency_ms: float = 0.0
    tls_version: str = ""
    http_status: int = 0
    note: str = ""


@dataclass
class Ladder:
    """The living alternative to a dead path."""
    broken_path: str
    broken_reason: str
    ladder_path: str
    ladder_status: PathStatus
    carries_same_truth: str
    category: str


# ── THE MAP: Every broken path → its ladders ────────────────────
# Ordered by priority — try first first.

LADDERS: Dict[str, Dict] = {

    # ── INDIGENOUS LANGUAGES ────────────────────────────────────
    "ailla.utexas.edu": {
        "broken": "DNS DEAD — Archive of Indigenous Languages of Latin America",
        "category": "indigenous_language",
        "truth": "indigenous language preservation Latin America",
        "alternatives": [
            ("dailp.northeastern.edu",
             "DAILP — Digital Archive of Indigenous Language Preservation (Jennifer found this)"),
            ("elar.soas.ac.uk",
             "ELAR — Endangered Languages Archive, London"),
            ("eldp.net",
             "ELDP — Endangered Language Documentation Programme"),
            ("glottolog.org",
             "Glottolog — comprehensive endangered language classification"),
        ]
    },

    "maori.org.nz": {
        "broken": "CONNECTION REFUSED — Maori Language Commission",
        "category": "indigenous_language",
        "truth": "living Maori language te reo program New Zealand",
        "alternatives": [
            ("maoridictionary.co.nz",
             "Maori Dictionary — living te reo resource"),
            ("teara.govt.nz",
             "Te Ara — New Zealand encyclopedia, Maori language"),
            ("tki.org.nz",
             "TKI — NZ Ministry of Education, Maori resources"),
        ]
    },

    "saami.net": {
        "broken": "TIMEOUT — Saami Council, circumpolar indigenous peoples",
        "category": "indigenous_language",
        "truth": "Saami circumpolar indigenous language and governance",
        "alternatives": [
            ("sametinget.se",
             "Sametinget — Swedish Saami Parliament"),
            ("samediggi.fi",
             "Sámediggi — Finnish Saami Parliament"),
            ("uit.no",
             "UiT — Arctic University of Norway, Saami language institute"),
        ]
    },

    "native-languages.org": {
        "broken": "CERT BROKEN — Native Languages of the Americas",
        "category": "indigenous_language",
        "truth": "native American language preservation resources",
        "alternatives": [
            ("cherokee.org",
             "Cherokee Nation — living language program (TLS 1.2 but alive)"),
            ("narf.org",
             "Native American Rights Fund — legal advocacy and language"),
            ("ncai.org",
             "NCAI — National Congress of American Indians"),
            ("dailp.northeastern.edu",
             "DAILP — Cherokee and indigenous digital archive"),
        ]
    },

    # ── FOLK / MUSIC PRESERVATION ───────────────────────────────
    "culturalequity.org": {
        "broken": "CERT BROKEN — Alan Lomax Cultural Equity archive",
        "category": "music_preservation",
        "truth": "Alan Lomax world folk music field recordings",
        "alternatives": [
            ("loc.gov",
             "Library of Congress — holds the Alan Lomax collection officially"),
            ("folkways.si.edu",
             "Smithsonian Folkways — world music preservation (alive, Let's Encrypt)"),
            ("archive.org",
             "Internet Archive — has Lomax recordings in public domain"),
            ("freemusicarchive.org",
             "Free Music Archive — creative commons folk music (alive)"),
        ]
    },

    "ccmixter.org": {
        "broken": "CERT BROKEN — ccMixter Creative Commons remix community",
        "category": "music_preservation",
        "truth": "Creative Commons music sharing and remixing",
        "alternatives": [
            ("freemusicarchive.org",
             "Free Music Archive — Creative Commons music (alive)"),
            ("jamendo.com",
             "Jamendo — free music licensing (alive, Google cert)"),
            ("soundcloud.com",
             "SoundCloud — independent music with CC licensing (alive)"),
        ]
    },

    # ── CLASSICAL TEXTS AND MYTH ─────────────────────────────────
    "perseusdl.tufts.edu": {
        "broken": "DNS DEAD — Perseus Digital Library subdomain",
        "category": "classical_texts",
        "truth": "Greek Latin classical texts Perseus digital library",
        "alternatives": [
            ("perseus.tufts.edu",
             "Perseus Tufts main — different subdomain may be alive"),
            ("theoi.com",
             "Theoi — Greek mythology primary texts (alive)"),
            ("sacred-texts.com",
             "Sacred Texts — all ancient texts (alive)"),
            ("gutenberg.org",
             "Project Gutenberg — classical texts public domain (alive)"),
        ]
    },

    "ancienttexts.org": {
        "broken": "CERT BROKEN — Ancient Texts archive",
        "category": "classical_texts",
        "truth": "ancient cuneiform Sumerian Akkadian texts",
        "alternatives": [
            ("sacred-texts.com",
             "Sacred Texts — all ancient traditions (alive)"),
            ("etcsl.orinst.ox.ac.uk",
             "ETCSL — Electronic Text Corpus of Sumerian Literature Oxford"),
            ("cdli.ucla.edu",
             "CDLI — Cuneiform Digital Library Initiative UCLA"),
        ]
    },

    "celtnet.org.uk": {
        "broken": "DNS DEAD — Celtic traditions archive",
        "category": "classical_texts",
        "truth": "Celtic mythology and traditions",
        "alternatives": [
            ("sacred-texts.com",
             "Sacred Texts Celtic section (alive)"),
            ("timelessmyths.com",
             "Timeless Myths — Celtic Norse Greek (alive)"),
            ("ancienttexts.org",
             "Ancient Texts Celtic materials"),
        ]
    },

    # ── GLOBAL SOUTH GOVERNMENTS ─────────────────────────────────
    "china.gov.cn": {
        "broken": "DNS DEAD — Government of China official portal",
        "category": "government",
        "truth": "Chinese government official information",
        "alternatives": [
            ("xinhuanet.com",
             "Xinhua News — official Chinese state media"),
            ("fmprc.gov.cn",
             "Ministry of Foreign Affairs China — likely reachable"),
            ("stats.gov.cn",
             "National Bureau of Statistics China"),
        ]
    },

    "southafrica.gov.za": {
        "broken": "DNS DEAD — Government of South Africa portal",
        "category": "government",
        "truth": "South African government official information",
        "alternatives": [
            ("gov.za",
             "gov.za — South Africa government root domain"),
            ("statssa.gov.za",
             "Statistics South Africa — data portal"),
            ("dirco.gov.za",
             "DIRCO — South Africa foreign affairs"),
        ]
    },

    "mexico.gob.mx": {
        "broken": "DNS DEAD — Government of Mexico portal",
        "category": "government",
        "truth": "Mexican government official information",
        "alternatives": [
            ("gob.mx",
             "gob.mx — Mexico government root domain"),
            ("inegi.org.mx",
             "INEGI — Mexico statistics institute"),
            ("sre.gob.mx",
             "SRE — Mexico foreign relations"),
        ]
    },

    "brasil.gov.br": {
        "broken": "CERT BROKEN — Government of Brazil portal",
        "category": "government",
        "truth": "Brazilian government official information",
        "alternatives": [
            ("gov.br",
             "gov.br — Brazil government root domain"),
            ("ibge.gov.br",
             "IBGE — Brazil statistics institute"),
            ("itamaraty.gov.br",
             "Itamaraty — Brazil foreign affairs"),
        ]
    },

    "firstnations.ca": {
        "broken": "DNS DEAD — First Nations Canada portal",
        "category": "indigenous_governance",
        "truth": "First Nations peoples of Canada governance",
        "alternatives": [
            ("afn.ca",
             "Assembly of First Nations — primary governance body"),
            ("fncarsi.ca",
             "First Nations Child and Family Caring Society"),
            ("narf.org",
             "Native American Rights Fund — legal advocacy"),
            ("indigenousportal.com",
             "Indigenous Portal — global gateway"),
        ]
    },

    # ── WILDLIFE AND NATURE ──────────────────────────────────────
    "nwf.org": {
        "broken": "CERT BROKEN — National Wildlife Federation",
        "category": "wildlife",
        "truth": "wildlife protection advocacy United States",
        "alternatives": [
            ("worldwildlife.org",
             "WWF — World Wildlife Fund (alive)"),
            ("defenders.org",
             "Defenders of Wildlife (alive)"),
            ("audubon.org",
             "National Audubon Society (alive)"),
            ("nature.org",
             "The Nature Conservancy (alive)"),
        ]
    },

    # ── SCIENTIFIC INFRASTRUCTURE ────────────────────────────────
    "kegg.jp": {
        "broken": "CONNECTION REFUSED — KEGG metabolic pathways database",
        "category": "biology",
        "truth": "metabolic pathways biochemical reactions database",
        "alternatives": [
            ("reactome.org",
             "Reactome — biological pathways (alive)"),
            ("metacyc.org",
             "MetaCyc — metabolic pathway database"),
            ("brenda-enzymes.org",
             "BRENDA — enzyme database"),
        ]
    },

    "theplantlist.org": {
        "broken": "CONNECTION REFUSED — The Plant List",
        "category": "botany",
        "truth": "catalog of all known plant species",
        "alternatives": [
            ("kew.org",
             "Royal Botanic Gardens Kew — World Flora Online (alive)"),
            ("ipni.org",
             "IPNI — International Plant Names Index (alive, TLS 1.2)"),
            ("tropicos.org",
             "Tropicos — Missouri Botanical Garden (alive)"),
        ]
    },
}


def _probe(host: str, timeout: int = 8) -> PathStatus:
    """Quick probe — is this host breathing?"""
    s = PathStatus(host=host, alive=False)
    try:
        addrs = socket.getaddrinfo(host, 443)
        t0 = time.time()
        sock = socket.create_connection((host, 443), timeout=timeout)
        s.latency_ms = round((time.time() - t0) * 1000, 1)
        sock.close()

        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((host, 443), timeout=timeout) as sk:
                with ctx.wrap_socket(sk, server_hostname=host) as ss:
                    s.tls_version = ss.version()
        except ssl.SSLCertVerificationError:
            s.note = "CERT_INVALID"
        except Exception:
            s.note = "TLS_FAILED"

        try:
            req = urllib.request.Request(
                f"https://{host}/",
                headers={"User-Agent": "GAIA-PathGuardian/1.0 (theforgottencode780@gmail.com)"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                s.http_status = resp.status
                s.alive = resp.status < 400
        except urllib.error.HTTPError as e:
            s.http_status = e.code
            s.alive = e.code < 500
            if e.code == 403:
                s.note = "FORBIDDEN_BUT_REACHABLE"
                s.alive = True  # 403 means it's alive, just locked
        except Exception as e:
            s.note = f"HTTP_FAIL: {str(e)[:40]}"

    except socket.gaierror:
        s.note = "DNS_DEAD"
    except Exception as e:
        s.note = f"UNREACHABLE: {str(e)[:40]}"

    return s


class PathGuardian:
    """Finds the ladder in every maze."""

    def __init__(self):
        self.ladders_found: List[Ladder] = []
        self.still_dead: List[str] = []

    def find_all_ladders(self, verbose: bool = True) -> List[Ladder]:
        """Walk every broken path. Find every living alternative."""
        import threading
        results = {}
        lock = threading.Lock()

        def check_broken(broken_host, config):
            alts = config["alternatives"]
            found_ladder = None

            for alt_host, alt_label in alts:
                status = _probe(alt_host)
                if status.alive:
                    ladder = Ladder(
                        broken_path=broken_host,
                        broken_reason=config["broken"],
                        ladder_path=alt_host,
                        ladder_status=status,
                        carries_same_truth=config["truth"],
                        category=config["category"],
                    )
                    with lock:
                        results[broken_host] = ("found", ladder)
                    return

            with lock:
                results[broken_host] = ("dead", None)

        threads = []
        for host, config in LADDERS.items():
            t = threading.Thread(target=check_broken, args=(host, config))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=20)

        for broken_host, (status, ladder) in results.items():
            if status == "found" and ladder:
                self.ladders_found.append(ladder)
                if verbose:
                    print(f"  ✓ LADDER: {broken_host}")
                    print(f"    ↳ {ladder.ladder_path} [{ladder.ladder_status.latency_ms}ms, "
                          f"HTTP {ladder.ladder_status.http_status}]")
                    print(f"    truth: {ladder.carries_same_truth}")
                    if ladder.ladder_status.note:
                        print(f"    note: {ladder.ladder_status.note}")
                    print()
            else:
                self.still_dead.append(broken_host)
                if verbose:
                    config = LADDERS.get(broken_host, {})
                    print(f"  ✗ NO LADDER: {broken_host}")
                    print(f"    {config.get('broken','')}")
                    print()

        return self.ladders_found

    def ladder_manifest(self) -> Dict:
        return {
            "ladders_found": len(self.ladders_found),
            "still_dead": self.still_dead,
            "ladders": [
                {
                    "broken": l.broken_path,
                    "reason": l.broken_reason,
                    "ladder": l.ladder_path,
                    "latency_ms": l.ladder_status.latency_ms,
                    "http_status": l.ladder_status.http_status,
                    "truth": l.carries_same_truth,
                    "category": l.category,
                }
                for l in self.ladders_found
            ],
        }
