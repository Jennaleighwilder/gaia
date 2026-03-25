#!/usr/bin/env bash
# Run in Terminal.app (or iTerm), NOT the Cursor agent shell — Cursor injects a
# localhost HTTPS proxy that returns 403 for S3 CONNECT; this clears it.
set -euo pipefail
cd "$(dirname "$0")/.."
export GAIA_NO_PROXY=1
# Strip Cursor/IDE proxy so urllib/curl use your real internet
unset https_proxy http_proxy HTTPS_PROXY HTTP_PROXY all_proxy ALL_PROXY no_proxy NO_PROXY

echo "=== KTLX file count (unidata-nexrad-level2, today UTC) ==="
if [[ -x .venv/bin/python ]]; then
  PY=.venv/bin/python
else
  PY=python3
fi
exec "$PY" -c "
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import urlencode

now = datetime.now(timezone.utc)
station = 'KTLX'
prefix = f'{now.year}/{now.month:02d}/{now.day:02d}/{station}/'
url = (
    'https://unidata-nexrad-level2.s3.amazonaws.com'
    + '?' + urlencode({'list-type': '2', 'prefix': prefix, 'max-keys': '100'})
)
req = urllib.request.Request(url, headers={'User-Agent': 'GAIA/1.0'})
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open(req, timeout=30) as r:
    text = r.read().decode()
root = ET.fromstring(text)
ns = {'s3': 'http://s3.amazonaws.com/doc/2006-03-01/'}
keys = [c.find('s3:Key', ns).text for c in root.findall('s3:Contents', ns)]
print(f'KTLX files today: {len(keys)}')
if keys:
    print(f'Latest: {keys[-1]}')
"
