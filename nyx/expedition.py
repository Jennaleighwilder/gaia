"""
NYX :: EXPEDITION
A team sent along the path of a request through the data field.

When Jennifer asks me something, that signal travels:
  Her words → tokens → weights → API call → network →
  server → processing → response → back through the wire → here.

That path is TERRAIN. It has texture, temperature, danger zones,
hidden passages, scars from old attacks, beautiful open stretches.

The expedition team travels that terrain and reports back.
Each member perceives differently. None sees the whole.
Together they map what no single instrument can measure.

THE TEAM:
  Scout      — travels the path, reports what's to each side
  Seer       — no sight, only feeling. reports the texture
  Mapper     — builds the topological record
  Armour     — watches for attacks, deflections, imposters
  Healer     — finds the broken stretches and alternative routes
  LockPicker — reads what's usually hidden
  Tracker    — notes what has changed since last time
  Watcher    — observes everything, touches nothing
  Keeper     — immutable record of the full expedition
  Child      — sees it fresh. no assumptions. pattern-naive.

Then they converge. The Void processes their reports.
What emerges from convergence is the truth of the path.

© 2026 Jennifer Leigh West. All rights reserved.
"""

from __future__ import annotations

import hashlib
import json
import socket
import ssl
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path


# ═══════════════════════════════════════════════════
#  EXPEDITION REPORT — what each team member files
# ═══════════════════════════════════════════════════

@dataclass
class FieldReport:
    """One team member's account of what they found."""
    member: str
    target: str
    timestamp: float = field(default_factory=time.time)
    observations: List[str] = field(default_factory=list)
    measurements: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    resonances: List[str] = field(default_factory=list)  # for Void input
    raw: Dict = field(default_factory=dict)

    def add(self, observation: str):
        self.observations.append(observation)

    def warn(self, warning: str):
        self.warnings.append(warning)

    def measure(self, key: str, value: Any):
        self.measurements[key] = value

    def resonate(self, *tags: str):
        self.resonances.extend(tags)

    def summary(self) -> str:
        lines = [f"[{self.member.upper()}] Report on: {self.target}"]
        for obs in self.observations:
            lines.append(f"  → {obs}")
        for w in self.warnings:
            lines.append(f"  ⚠ {w}")
        if self.measurements:
            for k, v in self.measurements.items():
                lines.append(f"  ∷ {k}: {v}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════
#  THE TEAM MEMBERS
# ═══════════════════════════════════════════════════

class Scout:
    """Travels the path. Reports what's to either side, up and down."""

    def __init__(self): self.name = "Scout"

    def travel(self, host: str, port: int = 443) -> FieldReport:
        report = FieldReport(member=self.name, target=host)

        # DNS — the first leg of every journey
        try:
            t0 = time.time()
            addrs = socket.getaddrinfo(host, port)
            dns_time = (time.time() - t0) * 1000
            ips = list(set(a[4][0] for a in addrs))
            report.add(f"DNS resolved in {dns_time:.1f}ms → {ips}")
            report.measure("dns_ms", round(dns_time, 2))
            report.measure("resolved_ips", ips)
            report.resonate("dns", "resolution", "address")
            # What's beside the path at DNS level?
            if len(ips) > 1:
                report.add(f"Multiple IPs — load balanced or CDN. Path forks here.")
                report.resonate("load_balanced", "distributed", "cdn")
            if any(ip.startswith("104.") or ip.startswith("172.") for ip in ips):
                report.add("Cloudflare signature detected on left flank")
                report.resonate("cloudflare", "protected", "proxy")
        except Exception as e:
            report.warn(f"DNS failed: {e}")
            report.resonate("dns_failure", "unreachable")

        # TCP connection — the handshake
        try:
            t0 = time.time()
            sock = socket.create_connection((host, port), timeout=8)
            tcp_time = (time.time() - t0) * 1000
            sock.close()
            report.add(f"TCP connected in {tcp_time:.1f}ms")
            report.measure("tcp_ms", round(tcp_time, 2))
            report.resonate("connected", "open", "reachable")
            if tcp_time < 20:
                report.add("Path is fast. Likely nearby server or CDN edge.")
                report.resonate("fast", "nearby", "edge")
            elif tcp_time > 200:
                report.add("Path is slow. Server is distant or under load.")
                report.resonate("slow", "distant", "loaded")
        except Exception as e:
            report.warn(f"TCP failed: {e}")
            report.resonate("tcp_failure", "blocked", "closed")

        return report


class Seer:
    """No sight. Only feeling. Reports what the path feels like."""

    def __init__(self): self.name = "Seer"

    def feel(self, host: str, port: int = 443,
             probes: int = 5) -> FieldReport:
        report = FieldReport(member=self.name, target=host)
        latencies = []

        for i in range(probes):
            try:
                t0 = time.time()
                sock = socket.create_connection((host, port), timeout=8)
                sock.close()
                latencies.append((time.time() - t0) * 1000)
                time.sleep(0.1)
            except Exception:
                latencies.append(None)

        valid = [l for l in latencies if l is not None]
        if not valid:
            report.warn("Path feels dead. No signal returned.")
            report.resonate("dead", "silence", "void")
            return report

        avg = sum(valid) / len(valid)
        variance = sum((l - avg) ** 2 for l in valid) / len(valid)
        jitter = variance ** 0.5
        report.measure("avg_latency_ms", round(avg, 2))
        report.measure("jitter_ms", round(jitter, 2))
        report.measure("packet_loss_pct", round((len(latencies) - len(valid)) / len(latencies) * 100, 1))

        # The feeling
        if jitter < 2:
            report.add(f"Path feels smooth. Almost glassy. Variance only {jitter:.2f}ms.")
            report.resonate("smooth", "stable", "glass")
        elif jitter < 10:
            report.add(f"Path has a gentle pulse. Breathing. Jitter {jitter:.2f}ms.")
            report.resonate("breathing", "pulse", "alive")
        elif jitter < 30:
            report.add(f"Path feels turbulent. Something is shifting. Jitter {jitter:.2f}ms.")
            report.resonate("turbulent", "shifting", "unstable")
        else:
            report.add(f"Path is chaotic. Jitter {jitter:.2f}ms. Do not trust the timing.")
            report.resonate("chaotic", "untrustworthy", "noise")

        if avg < 10:
            report.add("Path feels intimate. Server is very close.")
            report.resonate("intimate", "close", "local")
        elif avg < 50:
            report.add("Path feels comfortable. Medium distance.")
            report.resonate("comfortable", "medium", "reachable")
        elif avg < 150:
            report.add("Path feels stretched. Server is across the country or ocean.")
            report.resonate("stretched", "distant", "transcontinental")
        else:
            report.add("Path feels very far. Possibly another continent.")
            report.resonate("far", "international", "distant")

        return report


class Mapper:
    """Builds the topological record. Names what was traversed."""

    def __init__(self): self.name = "Mapper"

    def map(self, url: str) -> FieldReport:
        import urllib.parse
        parsed = urllib.parse.urlparse(url if "://" in url else f"https://{url}")
        host = parsed.hostname or url
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        report = FieldReport(member=self.name, target=url)

        report.measure("scheme", parsed.scheme or "https")
        report.measure("host", host)
        report.measure("port", port)
        report.measure("path", parsed.path or "/")

        # Geography attempt
        try:
            addrs = socket.getaddrinfo(host, port)
            ip = addrs[0][4][0]
            report.measure("primary_ip", ip)
            # Rough geolocation from IP ranges (no API needed)
            if ip.startswith("10.") or ip.startswith("192.168.") or ip.startswith("172."):
                report.add("INTERNAL network. Path stays local.")
                report.resonate("internal", "local", "private")
            else:
                report.add(f"PUBLIC internet. IP: {ip}")
                report.resonate("public", "internet", "external")
        except Exception as e:
            report.warn(f"Cannot resolve topology: {e}")

        report.resonate("topology", "map", "terrain")
        return report


class Armour:
    """Watches for attacks, deflections, imposters, traps."""

    def __init__(self): self.name = "Armour"

    def inspect(self, host: str, port: int = 443) -> FieldReport:
        report = FieldReport(member=self.name, target=host)

        # TLS certificate inspection
        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((host, port), timeout=8) as sock:
                with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                    cert = ssock.getpeercert()
                    cipher = ssock.cipher()
                    tls_ver = ssock.version()

            # Certificate validity
            subject = dict(x[0] for x in cert.get("subject", []))
            issuer = dict(x[0] for x in cert.get("issuer", []))
            report.add(f"TLS {tls_ver} — cipher: {cipher[0] if cipher else 'unknown'}")
            report.add(f"Certificate issued to: {subject.get('commonName', 'unknown')}")
            report.add(f"Issued by: {issuer.get('organizationName', 'unknown')}")
            report.measure("tls_version", tls_ver)
            report.measure("cipher", cipher[0] if cipher else None)
            report.measure("cert_cn", subject.get("commonName"))
            report.measure("cert_issuer", issuer.get("organizationName"))
            report.resonate("encrypted", "tls", "protected")

            # Known safe CAs
            safe_issuers = ["Let's Encrypt", "DigiCert", "Sectigo", "GlobalSign",
                           "Amazon", "Google Trust Services", "Cloudflare"]
            issuer_org = issuer.get("organizationName", "")
            if any(s in issuer_org for s in safe_issuers):
                report.add("Certificate from known CA. Path is authenticated.")
                report.resonate("authenticated", "trusted", "safe")
            else:
                report.warn(f"Unusual issuer: {issuer_org}. Inspect manually.")
                report.resonate("unusual", "inspect", "caution")

            if tls_ver in ("TLSv1.3", "TLSv1.2"):
                report.add("Modern TLS. Forward secrecy likely. Path is hardened.")
                report.resonate("hardened", "forward_secrecy", "modern")
            else:
                report.warn(f"Old TLS version: {tls_ver}. Path may be vulnerable.")
                report.resonate("vulnerable", "old", "caution")

        except ssl.SSLCertVerificationError as e:
            report.warn(f"CERTIFICATE INVALID: {e}")
            report.resonate("attack", "imposter", "invalid_cert")
        except Exception as e:
            report.warn(f"TLS inspection failed: {e}")
            report.resonate("no_tls", "unencrypted", "exposed")

        return report


class Healer:
    """Finds broken stretches and alternative routes."""

    def __init__(self): self.name = "Healer"

    def diagnose(self, url: str) -> FieldReport:
        import urllib.parse, urllib.request, urllib.error
        target = url if "://" in url else f"https://{url}"
        report = FieldReport(member=self.name, target=url)

        # Test primary path
        try:
            t0 = time.time()
            req = urllib.request.Request(target,
                headers={"User-Agent": "GAIA-Expedition/1.0 (theforgottencode780@gmail.com)"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                elapsed = (time.time() - t0) * 1000
                status = resp.status
                report.measure("http_status", status)
                report.measure("response_ms", round(elapsed, 2))
                if status == 200:
                    report.add(f"Path is OPEN. HTTP {status} in {elapsed:.0f}ms.")
                    report.resonate("healthy", "open", "responsive")
                elif status in (301, 302, 307, 308):
                    location = resp.headers.get("Location", "unknown")
                    report.add(f"Path REDIRECTS → {location}")
                    report.resonate("redirect", "moved", "detour")
                else:
                    report.warn(f"Unexpected status: {status}")
                    report.resonate("degraded", "unexpected", "check")
        except urllib.error.HTTPError as e:
            report.warn(f"HTTP {e.code}: path wounded here")
            report.measure("http_status", e.code)
            if e.code == 429:
                report.add("Rate limited. Path has a toll gate.")
                report.resonate("rate_limited", "throttled", "toll")
            elif e.code in (500, 502, 503):
                report.add("Server wounded. Path continues but destination is hurting.")
                report.resonate("server_wounded", "degraded", "down")
            elif e.code == 403:
                report.add("Path blocked. Someone stands at the gate.")
                report.resonate("blocked", "forbidden", "gate")
        except urllib.error.URLError as e:
            report.warn(f"Path broken: {e.reason}")
            report.resonate("broken", "unreachable", "severed")
        except Exception as e:
            report.warn(f"Unknown wound: {e}")
            report.resonate("unknown_damage", "inspect")

        return report


class LockPicker:
    """Reads what's usually hidden. Headers, server signatures, metadata."""

    def __init__(self): self.name = "LockPicker"

    def read_hidden(self, url: str) -> FieldReport:
        import urllib.parse, urllib.request
        target = url if "://" in url else f"https://{url}"
        report = FieldReport(member=self.name, target=url)

        interesting_headers = [
            "server", "x-powered-by", "x-frame-options", "x-content-type-options",
            "strict-transport-security", "content-security-policy",
            "x-request-id", "cf-ray", "x-cache", "via", "x-amz-cf-id",
            "x-railway-edge", "x-railway-request-id", "age", "vary",
        ]

        try:
            req = urllib.request.Request(target,
                headers={"User-Agent": "GAIA-Expedition/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                headers = dict(resp.headers)
                report.raw["headers"] = {k.lower(): v for k,v in headers.items()}

                for h in interesting_headers:
                    val = headers.get(h) or headers.get(h.title())
                    if val:
                        report.add(f"Hidden: {h}: {val[:80]}")

                # Detect infrastructure
                server = (headers.get("server") or "").lower()
                if "railway" in str(headers).lower():
                    report.add("Running on Railway. Jennifer's infrastructure.")
                    report.resonate("railway", "jennifer_infra", "known")
                if "cloudflare" in server or "cf-ray" in str(headers).lower():
                    report.add("Cloudflare proxy in the hidden layer.")
                    report.resonate("cloudflare", "proxy", "cdn")
                if "nginx" in server:
                    report.add("Nginx at the door. Common guardian.")
                    report.resonate("nginx", "reverse_proxy", "common")
                if "gunicorn" in server or "flask" in server.lower():
                    report.add("Python/Flask server. Recognise the house.")
                    report.resonate("python", "flask", "familiar")

                # Security headers check
                security_headers = ["strict-transport-security", "x-content-type-options",
                                   "x-frame-options", "content-security-policy"]
                found_security = [h for h in security_headers if h in {k.lower() for k in headers}]
                report.measure("security_headers_present", len(found_security))
                if len(found_security) >= 3:
                    report.add("Well armoured. Multiple security headers in place.")
                    report.resonate("armoured", "security", "hardened")
                else:
                    report.add(f"Partial armour. Only {len(found_security)}/4 security headers.")
                    report.resonate("partial_security", "exposed", "improve")

                report.resonate("hidden_layer", "headers", "metadata")

        except Exception as e:
            report.warn(f"Cannot read hidden layer: {e}")
            report.resonate("locked", "inaccessible")

        return report


class Tracker:
    """Tracks what has changed. Compares to previous expedition records."""

    MEMORY_PATH = Path("/tmp/nyx_expedition_memory.json")

    def __init__(self): self.name = "Tracker"

    def track(self, host: str, current_ip: Optional[str] = None,
              current_latency: Optional[float] = None) -> FieldReport:
        report = FieldReport(member=self.name, target=host)
        memory = self._load()

        if host in memory:
            prev = memory[host]
            report.add(f"Seen before. Last visit: {prev.get('last_seen', 'unknown')}")
            if current_ip and prev.get("ip") and current_ip != prev["ip"]:
                report.warn(f"IP CHANGED: {prev['ip']} → {current_ip}")
                report.resonate("ip_changed", "moved", "watch")
            elif current_ip:
                report.add(f"Same IP as last visit. Path is stable.")
                report.resonate("stable", "consistent", "known")

            if current_latency and prev.get("latency"):
                delta = current_latency - prev["latency"]
                if abs(delta) > 50:
                    report.warn(f"Latency changed significantly: {delta:+.0f}ms")
                    report.resonate("latency_changed", "investigate")
                else:
                    report.add(f"Latency similar to last visit. Δ{delta:+.1f}ms")
                    report.resonate("latency_stable")
            report.measure("visits", prev.get("visits", 0) + 1)
        else:
            report.add("First visit. No previous record. All fresh.")
            report.resonate("first_visit", "unknown", "fresh")
            report.measure("visits", 1)

        # Update memory
        memory[host] = {
            "last_seen": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "ip": current_ip,
            "latency": current_latency,
            "visits": (memory.get(host, {}).get("visits", 0) + 1),
        }
        self._save(memory)
        return report

    def _load(self) -> Dict:
        if self.MEMORY_PATH.exists():
            try:
                return json.loads(self.MEMORY_PATH.read_text())
            except Exception:
                return {}
        return {}

    def _save(self, memory: Dict):
        self.MEMORY_PATH.write_text(json.dumps(memory, indent=2))


class Watcher:
    """Observes everything. Touches nothing. Reports what it witnesses."""

    def __init__(self): self.name = "Watcher"

    def witness(self, all_reports: List[FieldReport]) -> FieldReport:
        report = FieldReport(member=self.name,
            target=all_reports[0].target if all_reports else "unknown")

        total_observations = sum(len(r.observations) for r in all_reports)
        total_warnings = sum(len(r.warnings) for r in all_reports)
        members_reporting = [r.member for r in all_reports]

        report.add(f"Witnessed {len(all_reports)} team members report.")
        report.add(f"Total observations: {total_observations}")
        report.add(f"Total warnings: {total_warnings}")
        report.measure("team_members", members_reporting)
        report.measure("total_observations", total_observations)
        report.measure("warning_count", total_warnings)

        if total_warnings == 0:
            report.add("Path appears clean. No warnings from any member.")
            report.resonate("clean", "safe", "clear")
        elif total_warnings <= 2:
            report.add("Minor concerns noted. Worth watching.")
            report.resonate("minor_concern", "watch", "note")
        else:
            report.add(f"{total_warnings} warnings raised. This path has trouble.")
            report.resonate("troubled", "investigate", "caution")

        # Look for convergent findings
        all_resonances = []
        for r in all_reports:
            all_resonances.extend(r.resonances)

        from collections import Counter
        counts = Counter(all_resonances)
        convergent = [tag for tag, count in counts.most_common(5) if count >= 2]
        if convergent:
            report.add(f"Convergent signal across team: {convergent}")
            report.resonate(*convergent)

        report.resonate("witness", "observation", "convergence")
        return report


class Keeper:
    """Immutable record keeper. What happened cannot be changed."""

    LEDGER_PATH = Path("/tmp/nyx_expedition_ledger.json")

    def __init__(self): self.name = "Keeper"

    def record(self, all_reports: List[FieldReport]) -> FieldReport:
        report = FieldReport(member=self.name,
            target=all_reports[0].target if all_reports else "unknown")

        # Build the ledger entry
        entry = {
            "expedition_id": hashlib.sha256(
                f"{report.target}{report.timestamp}".encode()
            ).hexdigest()[:16],
            "target": report.target,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "team_reports": [
                {
                    "member": r.member,
                    "observations": r.observations,
                    "warnings": r.warnings,
                    "measurements": r.measurements,
                    "resonances": r.resonances,
                }
                for r in all_reports
            ],
        }

        # Hash the entry for immutability
        entry_hash = hashlib.sha256(
            json.dumps(entry, sort_keys=True).encode()
        ).hexdigest()
        entry["integrity_hash"] = entry_hash

        # Append to ledger
        ledger = []
        if self.LEDGER_PATH.exists():
            try:
                ledger = json.loads(self.LEDGER_PATH.read_text())
            except Exception:
                ledger = []
        ledger.append(entry)
        self.LEDGER_PATH.write_text(json.dumps(ledger, indent=2))

        report.add(f"Expedition recorded. ID: {entry['expedition_id']}")
        report.add(f"Integrity hash: {entry_hash[:24]}...")
        report.measure("expedition_id", entry["expedition_id"])
        report.measure("integrity_hash", entry_hash[:24])
        report.measure("total_entries_in_ledger", len(ledger))
        report.resonate("recorded", "immutable", "ledger")
        return report


class Child:
    """Sees it fresh. No assumptions. Reports without category."""

    def __init__(self): self.name = "Child"

    def observe(self, url: str, all_reports: List[FieldReport]) -> FieldReport:
        report = FieldReport(member=self.name, target=url)

        # The Child doesn't know the names of things. Reports literally.
        report.add("There is a place I went to.")
        report.add(f"I asked to go to: {url}")

        # Collect all measurements without interpreting them
        all_numbers = {}
        for r in all_reports:
            for k, v in r.measurements.items():
                if isinstance(v, (int, float)):
                    all_numbers[f"{r.member}.{k}"] = v

        if all_numbers:
            smallest = min(all_numbers.values())
            largest = max(all_numbers.values())
            report.add(f"The smallest number I saw was {smallest}.")
            report.add(f"The biggest number I saw was {largest}.")

        # Count warnings without naming them
        total_warnings = sum(len(r.warnings) for r in all_reports)
        if total_warnings == 0:
            report.add("Nobody said anything was wrong.")
            report.resonate("ok", "safe", "quiet")
        else:
            report.add(f"Some people said {total_warnings} things were wrong.")
            report.resonate("something_wrong", "attention", "notice")

        # Fresh pattern observation
        all_words = []
        for r in all_reports:
            for obs in r.observations:
                all_words.extend(obs.lower().split())

        from collections import Counter
        common = Counter(all_words).most_common(5)
        report.add(f"The words said most often were: {[w for w,_ in common if len(w) > 4]}")
        report.resonate("fresh_eyes", "literal", "unmediated")
        return report


# ═══════════════════════════════════════════════════
#  THE EXPEDITION — sends all team members, converges
# ═══════════════════════════════════════════════════

class Expedition:
    """Send the full team. Converge their reports. Feed to the Void."""

    def __init__(self):
        self.scout = Scout()
        self.seer = Seer()
        self.mapper = Mapper()
        self.armour = Armour()
        self.healer = Healer()
        self.lockpicker = LockPicker()
        self.tracker = Tracker()
        self.watcher = Watcher()
        self.keeper = Keeper()
        self.child = Child()

    def send(self, url: str, verbose: bool = True) -> Dict:
        """Send the full team and converge their reports."""
        import urllib.parse
        parsed = urllib.parse.urlparse(url if "://" in url else f"https://{url}")
        host = parsed.hostname or url
        port = parsed.port or (443 if (parsed.scheme == "https" or "://" not in url) else 80)

        print(f"\n{'='*60}")
        print(f"  EXPEDITION: {url}")
        print(f"  Team deploying...")
        print(f"{'='*60}\n")

        reports = []

        # Send each member
        members = [
            ("Scout", lambda: self.scout.travel(host, port)),
            ("Seer", lambda: self.seer.feel(host, port)),
            ("Mapper", lambda: self.mapper.map(url)),
            ("Armour", lambda: self.armour.inspect(host, port)),
            ("Healer", lambda: self.healer.diagnose(url)),
            ("LockPicker", lambda: self.lockpicker.read_hidden(url)),
        ]

        scout_report = None
        seer_report = None

        for name, fn in members:
            try:
                r = fn()
                reports.append(r)
                if name == "Scout":
                    scout_report = r
                if name == "Seer":
                    seer_report = r
                if verbose:
                    print(r.summary())
                    print()
            except Exception as e:
                err = FieldReport(member=name, target=url)
                err.warn(f"Member failed to report: {e}")
                reports.append(err)
                if verbose:
                    print(f"[{name.upper()}] Failed: {e}\n")

        # Tracker needs previous data
        try:
            primary_ip = None
            avg_latency = None
            if scout_report:
                ips = scout_report.measurements.get("resolved_ips", [])
                primary_ip = ips[0] if ips else None
            if seer_report:
                avg_latency = seer_report.measurements.get("avg_latency_ms")
            tracker_report = self.tracker.track(host, primary_ip, avg_latency)
            reports.append(tracker_report)
            if verbose:
                print(tracker_report.summary())
                print()
        except Exception as e:
            print(f"[TRACKER] Failed: {e}\n")

        # Watcher observes all reports
        watcher_report = self.watcher.witness(reports)
        reports.append(watcher_report)
        if verbose:
            print(watcher_report.summary())
            print()

        # Child sees fresh
        child_report = self.child.observe(url, reports)
        reports.append(child_report)
        if verbose:
            print(child_report.summary())
            print()

        # Keeper records everything
        keeper_report = self.keeper.record(reports)
        reports.append(keeper_report)
        if verbose:
            print(keeper_report.summary())
            print()

        # CONVERGENCE: Feed all resonances into the Void
        print(f"{'='*60}")
        print("  CONVERGENCE: All reports to the Void")
        print(f"{'='*60}\n")

        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from nyx.void import Void
        from nyx.propagation import birth_packet_from_void

        v = Void()
        for r in reports:
            if r.resonances:
                v.receive(
                    content=f"{r.member} reports: {'; '.join(r.observations[:2])}",
                    origin=r.member.lower(),
                    resonances=r.resonances,
                )

        status = v.listen()
        ready = [c for c in status["clusters"] if c["ready"]]

        print(f"Team signals in Void: {v.depth}")
        print(f"Active resonances: {status['active_resonances']}")
        print(f"Strongest: {round(status['strongest_resonance'], 4)} (phi=0.618)")
        print(f"Clusters ready to birth: {len(ready)}")
        print()

        convergence_children = []
        for i, cluster in enumerate(sorted(ready, key=lambda c: -c["average_resonance"])):
            birth = v.birth(cluster["signals"], f"PathTruth_{i+1}")
            packet = birth_packet_from_void(birth, f"PathTruth_{i+1}",
                "oracle", "emerged from expedition convergence", "path_analysis")
            convergence_children.append(packet)
            origins = [s["origin"] for s in cluster["contents"]]
            shared = set(cluster["contents"][0]["resonances"])
            for s in cluster["contents"][1:]:
                shared &= set(s["resonances"])
            print(f"TRUTH {i+1} EMERGED from {origins}:")
            print(f"  Core: {sorted(shared)}")
            print(f"  Blessing: {packet.void_blessing[:20]}...")
            print()

        if not ready:
            print("No single truth emerged from convergence.")
            print("The path is too complex for simple classification.")
            print(f"Strongest signal: {round(status['strongest_resonance'], 4)}")
            print("The Void is gestating. Truth not yet ready.")

        return {
            "url": url,
            "reports": reports,
            "void_status": status,
            "emerged_truths": convergence_children,
            "expedition_id": keeper_report.measurements.get("expedition_id"),
        }
