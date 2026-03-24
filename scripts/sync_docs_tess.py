#!/usr/bin/env python3
"""
Refresh embedded TESS + dashboard alert copy in docs/index.html.

Run after: python scripts/live_tess_score.py
Writes: docs/data/live_tess.json, docs/data/dashboard_alerts.json
Patches: window.__GAIA_TESS__ / window.__GAIA_ALERTS__ inline blobs in docs/index.html
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
TESS_PATH = ROOT / "runs" / "live_tess.json"
INDEX = DOCS / "index.html"


def main() -> int:
    if "--fetch" in sys.argv:
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "live_tess_score.py")],
            cwd=str(ROOT),
            check=False,
        )
    if not TESS_PATH.exists():
        print("Missing runs/live_tess.json — run: python scripts/live_tess_score.py", file=sys.stderr)
        return 1
    tess = json.loads(TESS_PATH.read_text())
    alerts = {
        "banner_headline": (
            f"TESS {tess['tess_score']:.3f} ({tess['risk_level']}) — "
            "3 global layers firing; regional soundings may still be quiet."
        ),
        "banner_sub": (
            f"Live CPC/PSL indices as of {tess['timestamp'][:19]}Z — "
            f"MEI {tess['layers']['origin']['mei']}, AO {tess['layers']['transport']['ao']}, "
            f"Niño3.4a {tess['layers']['loading']['nino34_anom']}. Not a government warning."
        ),
        "ticker_extra": (
            f"TESS {tess['tess_score']:.3f} {tess['risk_level']} · "
            f"AO {tess['layers']['transport']['ao']} · MEI {tess['layers']['origin']['mei']} · "
            f"{len(tess.get('signals', []))} climate signals active"
        ),
    }
    (DOCS / "data").mkdir(parents=True, exist_ok=True)
    (DOCS / "data" / "live_tess.json").write_text(json.dumps(tess, indent=2) + "\n", encoding="utf-8")
    (DOCS / "data" / "dashboard_alerts.json").write_text(
        json.dumps(alerts, indent=2) + "\n", encoding="utf-8"
    )

    html = INDEX.read_text(encoding="utf-8")
    tess_js = json.dumps(tess, separators=(",", ":"))
    alerts_js = json.dumps(alerts, separators=(",", ":"))

    def replace_assign(html: str, var: str, rhs: str) -> tuple[str, bool]:
        pat = f"window.{var} = "
        i = html.find(pat)
        if i < 0:
            return html, False
        start = i + len(pat)
        if start >= len(html) or html[start] != "{":
            return html, False
        depth = 0
        k = start
        while k < len(html):
            c = html[k]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    end = k + 1
                    if end < len(html) and html[end] == ";":
                        end += 1
                    return html[:i] + pat + rhs + html[end:], True
            k += 1
        return html, False

    html, ok1 = replace_assign(html, "__GAIA_TESS__", tess_js + ";")
    html, ok2 = replace_assign(html, "__GAIA_ALERTS__", alerts_js + ";")
    if not ok1 or not ok2:
        print("Could not patch TESS blobs in docs/index.html.", file=sys.stderr)
        return 1
    INDEX.write_text(html, encoding="utf-8")
    print("Updated docs/data/*.json and embedded TESS in docs/index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
