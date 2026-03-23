# GAIA System Summary

**Geospatial Atmospheric Intelligence for Alerts**

A severe weather early-warning system for East Tennessee, built by The Forgotten Code Research Institute.

---

## What GAIA Is

GAIA combines satellite data, radar, lightning detection, terrain modeling, soil moisture, and hazmat facility awareness into a single decision engine. It issues WATCH, WARNING, and EMERGENCY alerts with **hours of lead time**—before storms form—at a fraction of the false alarm rate of traditional tornado warnings.

GAIA was validated against 460 historical severe weather events (1996–2025) and 200 quiet days across East Tennessee. No institutional backing, no research budget, no formal meteorology training—just pattern recognition, physics, and refusing to accept that the floor was a floor.

---

## How It Works (Plain Language)

1. **Data ingestion** — GAIA pulls live data from GOES-16 (satellite moisture/precip), NEXRAD (radar), GLM (lightning), Iowa Mesonet (surface obs), USGS (streamflow), and more. When live data is unavailable, it uses terrain, seasonal context, and TRI facility locations.

2. **Scoring engines** — 14 surface engines and 8 “sirens” (pattern detectors) each produce a 0–1 risk score. Engines include radar rotation, shear, terrain orographic lift, soil saturation, pressure trends, moisture, thermal stress, and infrastructure proximity.

3. **Seasonal overlay** — East Tennessee has distinct spring (tornado/wind), summer (heat/convection), fall (transition), and winter (snow/ice) profiles. GAIA modulates sensitivity by season.

4. **Convergence** — The governor requires multiple engines to agree before escalating to WARNING or EMERGENCY. This suppresses false alarms.

5. **TRI awareness** — 87 hazmat facilities (Toxics Release Inventory) in the region. When severe weather threatens, GAIA flags proximity to chemical plants for emergency services.

6. **Outputs** — Decisions are written to SQLite, served via the dashboard, and can trigger SMS (Twilio), webhooks, and email when configured.

---

## Performance vs NWS

| Metric | NWS | GAIA |
|--------|-----|------|
| Tornado false alarm rate | 75% | 18.5% |
| Average lead time | 13 min | 176 min |

**Validated baseline (locked):**

- **Detection:** 386/460 (83.9%)
- **False alarm rate:** 37/200 (18.5%)
- **Average lead time:** 176 minutes

**By event type:** Thunderstorm wind 82.6%, Hail 87.1%, Tornado 76.2%, Flash flood 100%, Heavy snow 100%, Winter storm 100%.

---

## Data Sources

- **Tier 1:** GOES-16 (TPW, convection), NEXRAD (radar), GLM (lightning), terrain (DEM), soil (SMAP when available)
- **Surface:** Iowa Mesonet (ASOS), USGS streamflow, NOAA SWPC (solar/geomag)
- **Context:** EPA TRI (hazmat), NOAA MEI (ENSO), seasonal profiles

---

## Coverage Area

**10 East Tennessee counties:** Knox, Sevier, Blount, Greene, Hamblen, Hawkins, Washington, Grainger, Sullivan, Anderson.

**87 TRI hazmat facilities** are monitored. GAIA factors distance when issuing warnings.

---

## How to Expand to New Counties

1. Add the county name to `EAST_TN_COUNTIES` in `runtime/gaia_daemon.py`.
2. Ensure `runtime/engines/terrain_engine.py` has a centroid for the county in `COUNTY_CENTROIDS` (or add it).
3. Run `scripts/populate_tri_fixture.py` if you need updated TRI data for the expanded region.
4. Restart the daemon.

---

## How to Set Up Alerts

### SMS (Twilio)

Set environment variables:

```
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_FROM=+1xxxxxxxxxx
GAIA_ALERT_PHONE=+1xxxxxxxxxx
```

Or the `GAIA_TWILIO_*` variants. SMS format is fixed at ≤160 characters:

```
GAIA ALERT: TORNADO WARNING KNOX TN
Lead: 187 min | HAZMAT: Nyrstar 4.2mi
theforgottencode.com
```

### Webhook

```
GAIA_WEBHOOK_URL=https://your-server.com/webhook
```

### Email

```
GAIA_ALERT_EMAIL=you@example.com
GAIA_SMTP_HOST=smtp.example.com
GAIA_SMTP_USER=...
GAIA_SMTP_PASS=...
```

---

## Running GAIA

- **Daemon:** `python3 -m runtime.gaia_daemon` — evaluates 10 counties every 5 minutes.
- **Dashboard:** `python3 -m runtime.dashboard.app` — serves status at http://127.0.0.1:5001 (or 5000 if available).

---

## Architecture Summary

- **Engines:** 14 surface engines + 8 sirens
- **Tier 1:** GOES, NEXRAD, GLM, terrain, soil
- **Seasonal overlay:** Spring / Summer / Fall / Winter
- **TRI facilities:** 87 East TN hazmat locations

---

## Credit

**The Forgotten Code Research Institute**

Contact: theforgottencode780@gmail.com  
Web: theforgottencode.com
