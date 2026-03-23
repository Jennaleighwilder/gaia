"""
GAIA Dashboard — real-time status page.
Flask: /status, /alerts, /alert/{id}, /facilities, /health.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

try:
    from flask import Flask, jsonify, render_template_string
except ImportError:
    print("Install: pip install flask")
    sys.exit(1)

app = Flask(__name__)

ALERTS_DB = ROOT / "runs" / "alerts" / "alerts.db"
DECISIONS_DB = ROOT / "runs" / "gaia_decisions.db"
ALERTS_DIR = ROOT / "runs" / "alerts"


def _county_status() -> dict:
    """Current conditions per county from decisions DB."""
    status = {}
    if not DECISIONS_DB.exists():
        for c in ["knox", "sevier", "blount", "greene", "hamblen", "hawkins", "washington", "grainger", "sullivan", "anderson"]:
            status[c] = {"decision": "CLEAR", "confidence": 0, "timestamp": ""}
        return status
    conn = sqlite3.connect(str(DECISIONS_DB))
    try:
        rows = conn.execute("""
            SELECT county, decision, confidence, timestamp FROM decisions d
            WHERE d.id = (SELECT MAX(id) FROM decisions dd WHERE dd.county = d.county)
        """).fetchall()
        for county, decision, conf, ts in rows:
            status[county] = {"decision": decision, "confidence": conf or 0, "timestamp": ts}
    finally:
        conn.close()
    return status


@app.route("/status")
def status():
    """Current conditions all counties."""
    return jsonify(_county_status())


@app.route("/alerts")
def alerts():
    """Last 24 hours of alerts."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    alerts_list = []
    for day_dir in sorted(ALERTS_DIR.iterdir(), reverse=True)[:2]:
        if not day_dir.is_dir():
            continue
        for f in day_dir.glob("*.json"):
            try:
                a = json.loads(f.read_text())
                if a.get("issued", "") >= cutoff:
                    alerts_list.append(a)
            except Exception:
                pass
    alerts_list.sort(key=lambda x: x.get("issued", ""), reverse=True)
    return jsonify(alerts_list[:50])


@app.route("/alert/<alert_id>")
def alert_detail(alert_id):
    """Full alert with evidence."""
    for day_dir in ALERTS_DIR.iterdir():
        if not day_dir.is_dir():
            continue
        for f in day_dir.glob("*.json"):
            if alert_id in f.name:
                return jsonify(json.loads(f.read_text()))
    return jsonify({"error": "not found"}), 404


@app.route("/facilities")
def facilities():
    """TRI facilities map placeholder."""
    return jsonify({"facilities": [], "note": "TRI lookup from governor"})


@app.route("/health")
def health():
    """System health, cache staleness."""
    staleness = {}
    try:
        from runtime.cache.data_cache import GAIADataCache
        cache = GAIADataCache()
        staleness = cache.get_staleness()
    except Exception:
        staleness = {"cache": "not_running"}
    return jsonify({
        "status": "ok",
        "cache_staleness": staleness,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


INDEX_HTML = """
<!DOCTYPE html>
<html>
<head><title>GAIA Status</title>
<style>
  body { font-family: system-ui; margin: 20px; background: #0d1117; color: #e6edf3; }
  h1 { color: #58a6ff; }
  .grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; max-width: 600px; }
  .county { padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; }
  .clear { background: #238636; }
  .watch { background: #9e6a03; }
  .warning { background: #da3633; }
  .emergency { background: #a371f7; }
  .alerts { margin-top: 24px; }
  .alert { padding: 12px; margin: 8px 0; background: #161b22; border-radius: 8px; border-left: 4px solid #da3633; }
  .meta { color: #8b949e; font-size: 0.9em; margin-top: 12px; }
</style>
</head>
<body>
  <h1>GAIA East TN Status</h1>
  <h2>County Grid</h2>
  <div class="grid" id="county-grid"></div>
  <h2>Active Alerts</h2>
  <div class="alerts" id="alerts"></div>
  <div class="meta">Last updated: <span id="updated"></span></div>
  <script>
    async function load() {
      const status = await fetch('/status').then(r=>r.json());
      const grid = document.getElementById('county-grid');
      grid.innerHTML = Object.entries(status).map(([c, v]) =>
        `<div class="county ${(v.decision||'clear').toLowerCase()}">${c}<br><small>${v.decision||'CLEAR'}</small></div>`
      ).join('');
      const alerts = await fetch('/alerts').then(r=>r.json());
      document.getElementById('alerts').innerHTML = alerts.slice(0,10).map(a =>
        `<div class="alert"><b>${a.alert_type||'ALERT'}</b> ${a.counties||a.county||''} - ${a.issued||''}</div>`
      ).join('') || '<p>No alerts</p>';
      document.getElementById('updated').textContent = new Date().toISOString();
    }
    load(); setInterval(load, 60000);
  </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(INDEX_HTML)


PUBLIC_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>GAIA East TN Weather Status</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    * { box-sizing: border-box; }
    body { font-family: system-ui, -apple-system, sans-serif; margin: 0; padding: 20px; background: #0d1117; color: #e6edf3; }
    h1 { color: #58a6ff; font-size: 1.5rem; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 10px; max-width: 600px; }
    .county { padding: 12px; border-radius: 8px; text-align: center; font-weight: 600; }
    .county .name { font-size: 0.95rem; text-transform: capitalize; }
    .county .level { font-size: 0.75rem; margin-top: 4px; opacity: 0.9; }
    .clear { background: #238636; }
    .watch { background: #9e6a03; }
    .warning { background: #da3633; }
    .emergency { background: #a371f7; }
    .unknown { background: #30363d; }
    .alerts { margin-top: 24px; }
    .alert { padding: 12px; margin: 8px 0; background: #161b22; border-radius: 8px; border-left: 4px solid #da3633; }
    .meta { color: #8b949e; font-size: 0.85rem; margin-top: 24px; }
    .footer { margin-top: 32px; color: #8b949e; font-size: 0.8rem; }
  </style>
</head>
<body>
  <h1>GAIA East TN Weather Status</h1>
  <p>Current alert level by county. Updates every 5 minutes.</p>
  <div class="grid" id="county-grid"></div>
  <h2 style="margin-top: 24px;">Active Warnings</h2>
  <div class="alerts" id="alerts"></div>
  <div class="meta">Last updated: <span id="updated">—</span></div>
  <div class="footer">Powered by GAIA — The Forgotten Code Research Institute</div>
  <script>
    async function load() {
      try {
        const status = await fetch('/status').then(r => r.json());
        const grid = document.getElementById('county-grid');
        grid.innerHTML = Object.entries(status).map(([c, v]) => {
          const dec = (v.decision || 'clear').toLowerCase();
          return '<div class="county ' + dec + '"><span class="name">' + c + '</span><br><span class="level">' + (v.decision || 'CLEAR') + '</span></div>';
        }).join('');
        const alerts = await fetch('/alerts').then(r => r.json());
        document.getElementById('alerts').innerHTML = (alerts.slice(0, 10) || []).map(a =>
          '<div class="alert"><b>' + (a.alert_type || 'ALERT') + '</b> ' + (a.counties || [a.county] || []).join(', ') + ' — ' + (a.issued || '') + '</div>'
        ).join('') || '<p>No active warnings</p>';
        document.getElementById('updated').textContent = new Date().toISOString();
      } catch (e) { document.getElementById('county-grid').innerHTML = '<p>Loading...</p>'; }
    }
    load(); setInterval(load, 60000);
  </script>
</body>
</html>
"""


@app.route("/public")
def public():
    """Public status page — no login, color-coded county grid."""
    return render_template_string(PUBLIC_HTML)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
