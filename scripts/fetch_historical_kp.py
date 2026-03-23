"""
GAIA: Fetch Historical Kp Index Data (FIXED)

The previous version used wrong GFZ URLs (404). This version uses:
1. GFZ JSON API (preferred): date-ranged queries, clean JSON output
2. GFZ master text file (backup): ALL data since 1932 in one file
3. NOAA SWPC (last 30 days only): recent data supplement

Run on a machine with network access:
    cd ~/gaia
    python scripts/fetch_historical_kp.py

Creates tests/fixtures/historical_kp.json covering 2020-2026.

© 2026 Jennifer Leigh West | The Forgotten Code Research Institute
"""

import json
import os
import sys
from datetime import datetime, timedelta


def fetch_kp_gfz_json_api(start_date, end_date):
    """
    Fetch Kp via GFZ official JSON web service API.
    
    Documented at: https://kp.gfz.de/en/data
    URL pattern: https://kp.gfz.de/app/json/?start=...&end=...&index=Kp
    
    Returns 3-hourly Kp values as JSON.
    """
    import urllib.request
    
    url = (f"https://kp.gfz.de/app/json/"
           f"?start={start_date}T00:00:00Z"
           f"&end={end_date}T23:59:59Z"
           f"&index=Kp")
    
    print(f"  Fetching GFZ JSON API: {start_date} to {end_date}...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GAIA/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        return data
    except Exception as e:
        print(f"    GFZ JSON API failed: {e}")
        return None


def fetch_kp_gfz_master_file():
    """
    Fetch the GFZ master text file containing ALL Kp since 1932.
    
    URL: https://www-app3.gfz-potsdam.de/kp_index/Kp_ap_since_1932.txt
    
    Format (after 30 header lines starting with #):
    YYYY MM DD hh.h hh._m days days_m Kp ap D
    2024 01 01 00.0 01.50 33603.00000 33603.06250 2.000 7 1
    """
    import urllib.request
    
    url = "https://www-app3.gfz-potsdam.de/kp_index/Kp_ap_since_1932.txt"
    print(f"  Fetching GFZ master file (ALL data since 1932)...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GAIA/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            text = resp.read().decode('utf-8', errors='replace')
        return text
    except Exception as e:
        print(f"    GFZ master file failed: {e}")
        return None


def fetch_kp_gfz_nowcast():
    """
    Fetch last 30 days from GFZ nowcast file.
    URL: https://kp.gfz.de/app/files/Kp_ap_nowcast.txt
    Same format as master file.
    """
    import urllib.request
    
    url = "https://kp.gfz.de/app/files/Kp_ap_nowcast.txt"
    print(f"  Fetching GFZ nowcast (last 30 days)...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GAIA/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            text = resp.read().decode('utf-8', errors='replace')
        return text
    except Exception as e:
        print(f"    GFZ nowcast failed: {e}")
        return None


def fetch_kp_swpc():
    """Fetch last 30 days from NOAA SWPC JSON API."""
    import urllib.request
    
    url = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
    print(f"  Fetching NOAA SWPC (last 30 days)...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GAIA/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        result = {}
        for row in data[1:]:  # skip header
            try:
                date_str = row[0][:10]
                kp = float(row[1])
                if date_str not in result:
                    result[date_str] = []
                result[date_str].append(kp)
            except (IndexError, ValueError):
                continue
        output = {}
        for date_str, kps in result.items():
            output[date_str] = {
                "kp_max": round(max(kps), 2),
                "kp_avg": round(sum(kps) / len(kps), 2),
                "kp_count": len(kps),
                "source": "SWPC",
            }
        return output
    except Exception as e:
        print(f"    SWPC failed: {e}")
        return {}


def parse_gfz_json(data):
    """Parse GFZ JSON API response into date-keyed dict."""
    if not data:
        return {}
    
    result = {}
    # GFZ JSON format varies — handle both list and dict formats
    entries = data if isinstance(data, list) else data.get("data", data.get("Kp", []))
    
    for entry in entries:
        try:
            # Could be {"datetime": "2024-01-01T00:00:00", "Kp": 2.0}
            # or [datetime_str, kp_value]
            if isinstance(entry, dict):
                dt_str = entry.get("datetime", entry.get("time_tag", ""))[:10]
                kp = float(entry.get("Kp", entry.get("kp", entry.get("value", 0))))
            elif isinstance(entry, list):
                dt_str = str(entry[0])[:10]
                kp = float(entry[1]) if len(entry) > 1 else 0
            else:
                continue
            
            if not dt_str or len(dt_str) < 10:
                continue
                
            if dt_str not in result:
                result[dt_str] = []
            result[dt_str].append(kp)
        except (ValueError, TypeError, IndexError):
            continue
    
    output = {}
    for date_str, kps in result.items():
        output[date_str] = {
            "kp_max": round(max(kps), 2),
            "kp_avg": round(sum(kps) / len(kps), 2),
            "kp_count": len(kps),
            "source": "GFZ_API",
        }
    return output


def parse_gfz_text(text, min_year=2020):
    """
    Parse GFZ text file format (master file or nowcast).
    
    Format after header lines (starting with #):
    YYYY MM DD hh.h hh._m days days_m Kp ap D
    2024 01 01 00.0 01.50 33603.00000 33603.06250 2.000 7 1
    """
    if not text:
        return {}
    
    result = {}
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split()
        if len(parts) < 9:
            continue
        try:
            year = int(parts[0])
            if year < min_year:
                continue
            month = int(parts[1])
            day = int(parts[2])
            kp = float(parts[7])  # Kp is column 8 (index 7)
            
            if kp < 0:  # -1 indicates missing data
                continue
                
            date_str = f"{year:04d}-{month:02d}-{day:02d}"
            if date_str not in result:
                result[date_str] = []
            result[date_str].append(kp)
        except (ValueError, IndexError):
            continue
    
    output = {}
    for date_str, kps in result.items():
        output[date_str] = {
            "kp_max": round(max(kps), 2),
            "kp_avg": round(sum(kps) / len(kps), 2),
            "kp_count": len(kps),
            "source": "GFZ_TXT",
        }
    return output


def main():
    print("=" * 60)
    print("GAIA: Fetching Historical Kp Index Data (2020-2026)")
    print("=" * 60)
    
    all_data = {}
    
    # Strategy 1: GFZ JSON API (query in 6-month chunks to stay under limits)
    print("\n[1/3] GFZ JSON API...")
    for year in range(2020, 2027):
        for half in [(f"{year}-01-01", f"{year}-06-30"),
                     (f"{year}-07-01", f"{year}-12-31")]:
            data = fetch_kp_gfz_json_api(half[0], half[1])
            if data:
                parsed = parse_gfz_json(data)
                print(f"    {half[0]} to {half[1]}: {len(parsed)} days")
                all_data.update(parsed)
    
    api_count = len(all_data)
    print(f"  Total from JSON API: {api_count} days")
    
    # Strategy 2: GFZ master text file (backup/supplement)
    if api_count < 1000:
        print(f"\n[2/3] GFZ master text file (API returned {api_count}, need more)...")
        text = fetch_kp_gfz_master_file()
        if text:
            parsed = parse_gfz_text(text, min_year=2020)
            print(f"  Parsed {len(parsed)} days from master file")
            # Master file takes precedence where API failed
            for k, v in parsed.items():
                if k not in all_data:
                    all_data[k] = v
    else:
        print(f"\n[2/3] Skipping master file (API provided {api_count} days)")
    
    # Strategy 3: GFZ nowcast + NOAA SWPC for most recent data
    print(f"\n[3/3] Recent data (nowcast + SWPC)...")
    nowcast_text = fetch_kp_gfz_nowcast()
    if nowcast_text:
        parsed = parse_gfz_text(nowcast_text, min_year=2025)
        print(f"  Nowcast: {len(parsed)} days")
        for k, v in parsed.items():
            all_data[k] = v  # Most recent data takes precedence
    
    swpc = fetch_kp_swpc()
    print(f"  SWPC: {len(swpc)} days")
    for k, v in swpc.items():
        if k not in all_data:
            all_data[k] = v
    
    # Save fixture
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    fixture_dir = os.path.join(project_root, "tests", "fixtures")
    os.makedirs(fixture_dir, exist_ok=True)
    fixture_path = os.path.join(fixture_dir, "historical_kp.json")
    
    with open(fixture_path, 'w') as f:
        json.dump(all_data, f, indent=2, sort_keys=True)
    
    # Report
    print(f"\n{'=' * 60}")
    print(f"SAVED: {len(all_data)} days to {fixture_path}")
    if all_data:
        dates = sorted(all_data.keys())
        print(f"Range: {dates[0]} to {dates[-1]}")
        
        # Year breakdown
        years = {}
        for d in dates:
            y = d[:4]
            years[y] = years.get(y, 0) + 1
        print(f"By year: {json.dumps(years, sort_keys=True)}")
        
        # Storm days
        storms = {k: v for k, v in all_data.items() if v.get("kp_max", 0) >= 5}
        print(f"\nGeomagnetic storm days (Kp ≥ 5): {len(storms)}")
        
        g_counts = {"G1": 0, "G2": 0, "G3": 0, "G4": 0, "G5": 0}
        for d, v in storms.items():
            kp = v["kp_max"]
            if kp >= 9: g_counts["G5"] += 1
            elif kp >= 8: g_counts["G4"] += 1
            elif kp >= 7: g_counts["G3"] += 1
            elif kp >= 6: g_counts["G2"] += 1
            else: g_counts["G1"] += 1
        print(f"  {json.dumps(g_counts)}")
        
        # Show most recent 5 storm days
        recent_storms = sorted(storms.keys())[-5:]
        for d in recent_storms:
            v = storms[d]
            print(f"  {d}: Kp max = {v['kp_max']}")
    
    print(f"\nCelestial engine can now score historical events in backtest.")
    print(f"Load with: celestial_engine.load_fixture('{fixture_path}')")


if __name__ == "__main__":
    main()
