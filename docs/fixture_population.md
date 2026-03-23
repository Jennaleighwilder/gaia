# GAIA Fixture Population — GPS-PW & Surface Ozone

Populate `gps_pw.json` and `surface_ozone.json` with real historical data for channel separation diagnostics.

## Prerequisites

```bash
# Create venv (optional but recommended)
python3 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install optional deps (netCDF4 for GPS-PW primary path)
pip install -r requirements.txt
```

## GPS-PW (Precipitable Water)

**Source:** UCAR COSMIC Suominet  
**Nearest station:** P778 Huntsville AL (~150 km from Knoxville) — or regional ASCII fallback

```bash
python3 scripts/populate_gps_pw_fixture.py
```

- **With netCDF4:** Uses daily netCDF from `ncConus`, extracts PWV (mm) by station
- **Without netCDF4:** Falls back to ASCII `pwvConus` — same daily PWV, slower per-date fetch
- Writes `tests/fixtures/gps_pw.json`: `{"YYYY-MM-DD": {"TYS": mm, "TRI": mm, ...}}`

## Surface Ozone

**Source:** EPA AQS AirData — daily ozone (44201)  
**Region:** East TN counties (Knox, Blount, Washington, Sullivan, Greene, Hawkins, Hamblen, Grainger, Sevier, Anderson)

```bash
python3 scripts/populate_surface_ozone_fixture.py
```

- Downloads `daily_44201_{year}.zip` per year (each ~130 MB)
- Filters Tennessee (47) + East TN counties, uses Arithmetic Mean (ppb)
- Writes `tests/fixtures/surface_ozone.json`: `{"YYYY-MM-DD": ppb}`

**Note:** First run can take 5–10 minutes (fetches 2020–2025).

## Channel Separation Diagnostic

After fixtures are populated:

```bash
python3 scripts/channel_separation_diagnostic.py
```

If GPS-PW or surface_ozone show **separation > 0.15** between severe-event and false-alarm days, that channel is a candidate for the next veto.
