"""
GAIA Dashboard — real-time status page.
Flask: /status, /alerts, /alert/{id}, /facilities, /health.
"""

from __future__ import annotations

import json
import os
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
from runtime.dashboard.public_api import register_public_routes
register_public_routes(app)



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


@app.route("/tess")
def tess():
    """Live TESS multi-layer convergence score."""
    tess_path = ROOT / "runs" / "live_tess.json"
    if tess_path.exists():
        return jsonify(json.loads(tess_path.read_text()))
    return jsonify({"error": "Run live_tess_score.py first"}), 404


@app.route("/surface")
def surface():
    """Live surface observations."""
    surf_path = ROOT / "runs" / "live_surface.json"
    if surf_path.exists():
        return jsonify(json.loads(surf_path.read_text()))
    return jsonify({"error": "No surface data yet"}), 404


@app.route("/soundings")
def soundings():
    """Live upper-air sounding data."""
    snd_path = ROOT / "runs" / "live_soundings.json"
    if snd_path.exists():
        return jsonify(json.loads(snd_path.read_text()))
    return jsonify({"error": "Run fetch_soundings.py first"}), 404


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


LIVE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>GAIA — Live Multi-Layer Hazard Awareness</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:system-ui,-apple-system,sans-serif;background:#0a0e14;color:#c8d1dc;min-height:100vh}
    .header{padding:20px 24px;border-bottom:1px solid #1c2333;display:flex;align-items:center;gap:16px}
    .header h1{font-size:1.3rem;color:#58a6ff;font-weight:600}
    .header .live{background:#238636;color:#fff;padding:3px 10px;border-radius:12px;font-size:.7rem;font-weight:700;letter-spacing:.5px;animation:pulse 2s infinite}
    @keyframes pulse{0%,100%{opacity:1}50%{opacity:.6}}
    .main{display:grid;grid-template-columns:1fr 1fr;gap:20px;padding:20px 24px;max-width:1200px}
    @media(max-width:768px){.main{grid-template-columns:1fr}}
    .card{background:#111827;border:1px solid #1e2d3d;border-radius:12px;padding:20px}
    .card h2{font-size:1rem;color:#8b949e;margin-bottom:14px;font-weight:500;text-transform:uppercase;letter-spacing:1px;font-size:.75rem}
    .tess-banner{grid-column:1/-1;text-align:center;padding:28px}
    .tess-score{font-size:3.5rem;font-weight:700;font-variant-numeric:tabular-nums}
    .tess-label{font-size:.85rem;color:#8b949e;margin-top:4px}
    .risk-low{color:#238636}
    .risk-moderate{color:#d29922}
    .risk-elevated{color:#f85149}
    .layer{display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid #1c2333}
    .layer:last-child{border-bottom:none}
    .layer-name{font-weight:600;font-size:.9rem}
    .layer-detail{color:#8b949e;font-size:.8rem}
    .layer-score{font-size:1.1rem;font-weight:700;font-variant-numeric:tabular-nums}
    .bar{height:6px;border-radius:3px;background:#1c2333;margin-top:6px;overflow:hidden}
    .bar-fill{height:100%;border-radius:3px;transition:width .5s}
    .signal{display:inline-block;padding:3px 8px;margin:3px;border-radius:4px;font-size:.7rem;font-weight:600;background:#1c2333;border:1px solid #30363d}
    .signal.active{background:#f8514922;border-color:#f85149;color:#f85149}
    .station{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #1c2333;font-size:.85rem}
    .station:last-child{border-bottom:none}
    .station .id{font-weight:600;color:#58a6ff}
    .station .metar{color:#8b949e;font-size:.75rem;font-family:monospace}
    .sounding-table{width:100%;border-collapse:collapse;font-size:.78rem;font-variant-numeric:tabular-nums}
    .sounding-table th{text-align:left;padding:6px 8px;border-bottom:2px solid #30363d;color:#8b949e;font-weight:500;font-size:.7rem;text-transform:uppercase;letter-spacing:.5px}
    .sounding-table td{padding:6px 8px;border-bottom:1px solid #1c2333}
    .sounding-table tr:hover{background:#161b2288}
    .stp-extreme{color:#f85149;font-weight:700}
    .stp-significant{color:#d29922;font-weight:700}
    .stp-moderate{color:#e3b341;font-weight:600}
    .stp-low{color:#238636}
    .sounding-banner{display:flex;align-items:center;gap:14px;margin-bottom:14px}
    .sounding-risk{font-size:1.3rem;font-weight:700;padding:4px 14px;border-radius:6px}
    .risk-bg-extreme{background:#f8514933;color:#f85149}
    .risk-bg-significant{background:#d2992233;color:#d29922}
    .risk-bg-moderate{background:#e3b34133;color:#e3b341}
    .risk-bg-low{background:#23863633;color:#238636}
    .footer{text-align:center;padding:20px;color:#484f58;font-size:.75rem}
  </style>
</head>
<body>
  <div class="header">
    <h1>GAIA Multi-Layer Hazard Awareness</h1>
    <span class="live">LIVE</span>
  </div>
  <div class="main">
    <div class="card tess-banner" id="tess-card">
      <div class="tess-score" id="tess-score">—</div>
      <div class="tess-label">TESS Convergence Score</div>
      <div id="risk-level" style="font-size:.9rem;margin-top:8px;font-weight:600">Loading...</div>
      <div id="signals" style="margin-top:12px"></div>
    </div>
    <div class="card">
      <h2>Global Layers (UVRK-1)</h2>
      <div id="layers"></div>
    </div>
    <div class="card">
      <h2>Surface Observations</h2>
      <div id="surface"></div>
    </div>
    <div class="card" style="grid-column:1/-1">
      <h2>Upper-Air Soundings (Phase 2)</h2>
      <div id="sounding-banner"></div>
      <div id="sounding-table"></div>
    </div>
  </div>
  <div class="footer">
    GAIA — Jennifer Leigh West — The Forgotten Code Research Institute<br>
    Data: NOAA CPC, PSL, Mesonet, UWyo Soundings | Updated <span id="ts">—</span>
  </div>
  <script>
    function barColor(s){if(s>=0.7)return'#f85149';if(s>=0.4)return'#d29922';return'#238636'}
    function riskClass(r){return'risk-'+(r||'low').toLowerCase()}
    async function loadTess(){
      try{
        const t=await fetch('/tess').then(r=>r.json());
        document.getElementById('tess-score').textContent=t.tess_score.toFixed(3);
        document.getElementById('tess-score').className='tess-score '+riskClass(t.risk_level);
        document.getElementById('risk-level').textContent=t.risk_level+' — '+t.layers_firing+'/3 layers firing';
        document.getElementById('risk-level').className=riskClass(t.risk_level);
        const sigs=t.signals||[];
        document.getElementById('signals').innerHTML=sigs.map(s=>'<span class="signal active">'+s+'</span>').join('')||'<span class="signal">QUIET</span>';
        const layers=[
          {name:'Origin',sub:'Pacific SST / ENSO / PDO',key:'origin',detail:'MEI '+(t.layers.origin.mei??'?')+' | PDO '+(t.layers.origin.pdo??'?')},
          {name:'Transport',sub:'Jet Stream / AO / PNA',key:'transport',detail:'AO '+(t.layers.transport.ao??'?')+' | PNA '+(t.layers.transport.pna??'?')},
          {name:'Loading',sub:'Gulf Moisture / SST Gradient',key:'loading',detail:'Nino3.4a '+(t.layers.loading.nino34_anom??'?')}
        ];
        document.getElementById('layers').innerHTML=layers.map(l=>{
          const s=t.layers[l.key].score;
          return '<div class="layer"><div><div class="layer-name">'+l.name+'</div><div class="layer-detail">'+l.sub+'</div><div class="layer-detail">'+l.detail+'</div><div class="bar" style="width:200px"><div class="bar-fill" style="width:'+Math.round(s*100)+'%;background:'+barColor(s)+'"></div></div></div><div class="layer-score" style="color:'+barColor(s)+'">'+s.toFixed(3)+'</div></div>';
        }).join('');
        document.getElementById('ts').textContent=t.timestamp;
      }catch(e){document.getElementById('tess-score').textContent='ERR'}
    }
    async function loadSurface(){
      try{
        const d=await fetch('/surface').then(r=>r.json());
        document.getElementById('surface').innerHTML=(d.stations||[]).map(s=>{
          if(s.error)return '<div class="station"><span class="id">'+s.station+'</span><span>'+s.error+'</span></div>';
          return '<div class="station"><div><span class="id">'+s.station+'</span> '+s.temp_f+'F dew='+s.dewpoint_f+'F '+s.pressure_mb+'mb w='+s.wind_mph+'mph</div></div><div class="station"><div class="metar">'+s.metar+'</div></div>';
        }).join('')||'<div>No data</div>';
      }catch(e){}
    }
    async function loadSoundings(){
      try{
        const d=await fetch('/soundings').then(r=>r.json());
        if(d.error){document.getElementById('sounding-table').innerHTML='<div style="color:#8b949e">'+d.error+'</div>';return}
        const risk=d.sounding_risk||'LOW';
        const rc=risk.toLowerCase();
        document.getElementById('sounding-banner').innerHTML=
          '<span class="sounding-risk risk-bg-'+rc+'">'+risk+'</span>'+
          '<span style="color:#8b949e">Max STP: <b style="color:#e6edf3">'+d.regional_max_stp.toFixed(2)+'</b> | Max CAPE: <b style="color:#e6edf3">'+d.regional_max_cape+'</b> J/kg | Max SRH: <b style="color:#e6edf3">'+d.regional_max_srh+'</b> m\u00B2/s\u00B2 | Stations: '+d.station_count+' | '+d.time+'</span>';
        const ss=d.stations||[];
        ss.sort((a,b)=>(b.significant_tornado_parameter||0)-(a.significant_tornado_parameter||0));
        let html='<table class="sounding-table"><thead><tr><th>Station</th><th>STP</th><th>SBCAPE</th><th>MUCAPE</th><th>SRH 3km</th><th>SRH 1km</th><th>Shear</th><th>LCL</th><th>T</th><th>Td</th></tr></thead><tbody>';
        ss.forEach(s=>{
          const stp=s.significant_tornado_parameter||0;
          let cls='stp-low';
          if(stp>=3)cls='stp-extreme';else if(stp>=1)cls='stp-significant';else if(stp>=0.5)cls='stp-moderate';
          html+='<tr><td><b>'+(s.station_name||s.station_id)+'</b></td>';
          html+='<td class="'+cls+'">'+stp.toFixed(2)+'</td>';
          html+='<td>'+s.sbcape_jkg+'</td><td>'+s.mucape_jkg+'</td>';
          html+='<td>'+s.srh_0_3km_m2s2+'</td><td>'+(s.srh_0_1km_m2s2||'—')+'</td>';
          html+='<td>'+s.bulk_shear_0_6km_kts+'</td><td>'+s.lcl_height_agl_m+'m</td>';
          html+='<td>'+s.sfc_temp_c+'\u00B0C</td><td>'+s.sfc_dewpoint_c+'\u00B0C</td></tr>';
        });
        html+='</tbody></table>';
        document.getElementById('sounding-table').innerHTML=html;
      }catch(e){document.getElementById('sounding-table').innerHTML='<div style="color:#484f58">No sounding data</div>'}
    }
    loadTess();loadSurface();loadSoundings();setInterval(()=>{loadTess();loadSurface();loadSoundings()},120000);
  </script>
</body>
</html>
"""


@app.route("/public")
@app.route("/live")
def public():
    """Live TESS dashboard — real-time multi-layer hazard awareness."""
    return render_template_string(LIVE_HTML)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5001"))
    app.run(host="0.0.0.0", port=port, debug=False)
