#!/usr/bin/env bash
# Download NOAA Storm Events for Tennessee (1996-2025)
# Fetches index first to get correct filename per year (c-date varies).
# Saves to tests/fixtures/noaa_storm_events/

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATA_DIR="${ROOT}/tests/fixtures/noaa_storm_events"
INDEX_URL="https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/"

mkdir -p "${DATA_DIR}"

# Resolve filenames from index (year -> filename)
echo "Resolving filenames from NCEI index..."
python3 -c "
import re, urllib.request
req = urllib.request.Request('$INDEX_URL', headers={'User-Agent':'GAIA/1.0'})
with urllib.request.urlopen(req, timeout=30) as r:
    html = r.read().decode('utf-8', errors='replace')
pat = re.compile(r'StormEvents_details-ftp_v1\.0_d(\d{4})_c\d{8}\.csv\.gz')
by_year = {}
for m in pat.finditer(html):
    by_year[int(m.group(1))] = m.group(0)
for y in sorted(by_year.keys()):
    if 1996 <= y <= 2025:
        print(f'{y}\t{by_year[y]}')
" > "${DATA_DIR}/.index_resolved" 2>/dev/null || true

while IFS=$'\t' read -r year filename; do
  [[ -z "$filename" ]] && continue
  target="${DATA_DIR}/details_${year}.csv"
  if [[ -f "${target}" ]] && [[ -s "${target}" ]]; then
    echo "Skip ${year} (exists)"
    continue
  fi
  echo "Downloading ${year}: ${filename}"
  if curl -fsSL "${INDEX_URL}${filename}" | gunzip > "${target}" 2>/dev/null; then
    echo "  OK: $(wc -l < "${target}") lines"
  else
    echo "  Failed: ${year}"
    rm -f "${target}"
  fi
  sleep 1
done < "${DATA_DIR}/.index_resolved" 2>/dev/null || {
  echo "Index resolution failed. Using fallback c20260316..."
  for year in $(seq 1996 2025); do
    target="${DATA_DIR}/details_${year}.csv"
    [[ -f "$target" ]] && [[ -s "$target" ]] && { echo "Skip ${year}"; continue; }
    url="${INDEX_URL}StormEvents_details-ftp_v1.0_d${year}_c20260316.csv.gz"
    echo "Downloading ${year}..."
    curl -fsSL "$url" | gunzip > "$target" 2>/dev/null || rm -f "$target"
    sleep 1
  done
}

echo
echo "Download complete. Run: python3 scripts/filter_east_tn_storm_events.py"
