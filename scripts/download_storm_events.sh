#!/usr/bin/env bash

set -euo pipefail

ROOT="${HOME}/gaia"
DATA_DIR="${ROOT}/data/storm_events"
INDEX_URL="https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/"

mkdir -p "${DATA_DIR}"

tmp_index="$(mktemp)"
trap 'rm -f "${tmp_index}"' EXIT

echo "Fetching NOAA Storm Events index..."
curl -fsSL "${INDEX_URL}" -o "${tmp_index}"

for year in $(seq 2015 2025); do
  match="$(
    grep -o "StormEvents_details-ftp_v1.0_d${year}_c[0-9]\{8\}\.csv\.gz" "${tmp_index}" \
      | sort -u \
      | tail -n 1 || true
  )"
  if [[ -z "${match}" ]]; then
    echo "No details file found for ${year}"
    continue
  fi

  target="${DATA_DIR}/details_${year}.csv.gz"
  echo "Downloading ${year}: ${match}"
  curl -fsSL "${INDEX_URL}${match}" -o "${target}" || {
    echo "  Failed: ${year}"
    continue
  }
  sleep 2
done

echo "Decompressing..."
find "${DATA_DIR}" -maxdepth 1 -name 'details_*.csv.gz' -print0 | while IFS= read -r -d '' file; do
  gunzip -f "${file}"
done

echo
echo "Download complete. Files in ${DATA_DIR}:"
ls -lh "${DATA_DIR}"
