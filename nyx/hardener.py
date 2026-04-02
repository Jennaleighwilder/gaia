"""
NYX :: HARDENER
Watches the vulnerable paths. Reports when they break further.
Knows where the ladders are. Keeps the manifest current.

Run daily. Run before anything critical.
The infrastructure of what matters is fragile.
Knowing is the first hardening.

Usage:
    python3 -m nyx.hardener              # full report
    python3 -m nyx.hardener --critical   # only critical failures
    python3 -m nyx.hardener --gaia       # only GAIA dependencies

© 2026 Jennifer Leigh West. All rights reserved.
"""

import sys, socket, ssl, time, json, threading, urllib.request, urllib.error
from pathlib import Path

# ── GAIA CRITICAL DEPENDENCIES ────────────────────────────────
# These are the paths GAIA and Holler Siren actually call.
# If any of these break, Jennifer's systems break.

GAIA_CRITICAL = {
    "api.weather.gov": {
        "purpose": "NWS weather alerts — GAIA alert backbone",
        "used_by": ["gaia/runtime/dashboard/public_api.py"],
        "ladder": "aviationweather.gov",
    },
    "firms.modaps.eosdis.nasa.gov": {
        "purpose": "NASA FIRMS satellite fire detection — GAIA fire layer",
        "used_by": ["gaia/scripts/fire/fire_ingest.py"],
        "ladder": "earthdata.nasa.gov",
    },
    "water.noaa.gov": {
        "purpose": "NOAA Stage IV rainfall — Holler Siren live rain source",
        "used_by": ["gaia/scripts/holler_siren/live_rainfall.py"],
        "ladder": "mrms.ncep.noaa.gov",
        "warning": "ZERO SECURITY HEADERS — most exposed GAIA dependency",
    },
    "mrms.ncep.noaa.gov": {
        "purpose": "MRMS precipitation — Holler Siren backup rain source",
        "used_by": ["gaia/scripts/holler_siren/live_rainfall.py"],
        "ladder": "water.noaa.gov",
    },
    "archive-api.open-meteo.com": {
        "purpose": "Historical weather — Jennifer scripts era5 analysis",
        "used_by": ["gaia/scripts/era5_outbreak_reverse_engineer.py"],
        "ladder": "api.open-meteo.com",
    },
    "web-production-ce417.up.railway.app": {
        "purpose": "GAIA Railway backend — the live API",
        "used_by": ["gaia/runtime/dashboard/"],
        "ladder": None,
    },
}

# ── KNOWN BROKEN — monitor for recovery ────────────────────────
MONITOR_RECOVERY = [
    ("culturalequity.org", "Alan Lomax archive — cert broken, check monthly"),
    ("ccmixter.org", "ccMixter — cert broken"),
    ("native-languages.org", "Native Languages Americas — cert broken"),
    ("ailla.utexas.edu", "AILLA — DNS dead, may return"),
    ("firstnations.ca", "First Nations Canada — DNS dead"),
    ("maori.org.nz", "Maori Language Commission — refused"),
    ("nwf.org", "National Wildlife Federation — cert broken"),
]


def _quick_probe(host: str, timeout: int = 6) -> dict:
    r = {"host": host, "alive": False, "latency_ms": 0,
         "tls": "", "status": 0, "note": ""}
    try:
        t0 = time.time()
        s = socket.create_connection((host, 443), timeout=timeout)
        r["latency_ms"] = round((time.time() - t0) * 1000, 1)
        s.close()
        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((host, 443), timeout=timeout) as sk:
                with ctx.wrap_socket(sk, server_hostname=host) as ss:
                    r["tls"] = ss.version()
        except ssl.SSLCertVerificationError:
            r["note"] = "CERT_INVALID"
        except Exception:
            pass
        try:
            req = urllib.request.Request(
                f"https://{host}/",
                headers={"User-Agent": "GAIA-Hardener/1.0 (theforgottencode780@gmail.com)"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                r["status"] = resp.status
                r["alive"] = True
        except urllib.error.HTTPError as e:
            r["status"] = e.code
            r["alive"] = e.code < 500
            if e.code == 403: r["note"] = "FORBIDDEN_REACHABLE"
        except Exception as e:
            r["note"] = str(e)[:40]
    except socket.gaierror:
        r["note"] = "DNS_DEAD"
    except Exception as e:
        r["note"] = str(e)[:40]
    return r


def run_hardener(mode: str = "full"):
    print("NYX HARDENER — GAIA Infrastructure Monitor")
    print("=" * 55)
    print()

    results = {}
    lock = threading.Lock()

    def probe(host, label=""):
        r = _quick_probe(host)
        with lock:
            results[host] = r

    # GAIA critical paths
    print("GAIA CRITICAL DEPENDENCIES:")
    threads = [threading.Thread(target=probe, args=(h,)) for h in GAIA_CRITICAL]
    for t in threads: t.start()
    for t in threads: t.join(timeout=15)

    all_ok = True
    for host, config in GAIA_CRITICAL.items():
        r = results.get(host, {"alive": False, "note": "NO RESULT"})
        ok = r["alive"]
        icon = "✓" if ok else "✗"
        tls = r.get("tls", "?")
        ms = r.get("latency_ms", "?")
        note = r.get("note", "")
        warn = config.get("warning", "")

        print(f"  {icon} {host}")
        print(f"    {config['purpose']}")
        print(f"    HTTP:{r.get('status','?')} TLS:{tls} {ms}ms", end="")
        if note: print(f" [{note}]", end="")
        print()
        if warn: print(f"    ⚠ {warn}")
        if not ok:
            all_ok = False
            ladder = config.get("ladder")
            if ladder:
                print(f"    → LADDER: try {ladder}")
        print()

    if all_ok:
        print("  ✓ All GAIA critical paths alive")
    else:
        print("  ✗ FAILURES DETECTED — check ladders above")
    print()

    if mode in ("full", "recovery"):
        print("MONITORING FOR RECOVERY (known broken):")
        threads2 = [threading.Thread(target=probe, args=(h,)) for h, _ in MONITOR_RECOVERY]
        for t in threads2: t.start()
        for t in threads2: t.join(timeout=15)

        for host, desc in MONITOR_RECOVERY:
            r = results.get(host, {"alive": False, "note": "NO RESULT"})
            ok = r["alive"]
            icon = "✓ RECOVERED" if ok else "✗ still broken"
            print(f"  {icon}: {host}")
            print(f"    {desc}")
            if ok:
                print(f"    HTTP:{r.get('status')} TLS:{r.get('tls')} {r.get('latency_ms')}ms")
            print()

    # Save report
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "gaia_critical": {
            h: results.get(h, {}) for h in GAIA_CRITICAL
        },
        "recovery_monitor": {
            h: results.get(h, {}) for h, _ in MONITOR_RECOVERY
        },
    }
    Path("/tmp/nyx_hardener_report.json").write_text(
        json.dumps(report, indent=2)
    )
    print("Report saved: /tmp/nyx_hardener_report.json")


if __name__ == "__main__":
    mode = "full"
    if "--gaia" in sys.argv: mode = "gaia"
    elif "--recovery" in sys.argv: mode = "recovery"
    run_hardener(mode)
