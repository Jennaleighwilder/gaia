# SMAP Soil Moisture — NASA Earthdata Setup

## 1. Register for NASA Earthdata

1. Go to **https://urs.earthdata.nasa.gov/**
2. Create a free account
3. Under "My Profile" → "Approve Applications", authorize:
   - **NASA GESDISC DATA ARCHIVE**
   - **NSIDC ECS** (for SMAP data)

## 2. Set Environment Variables

```bash
export EARTHDATA_USER=your_username
export EARTHDATA_PASS=your_password
```

Or add to `~/.netrc`:
```
machine urs.earthdata.nasa.gov login YOUR_USERNAME password YOUR_PASSWORD
```
(Then: `chmod 600 ~/.netrc`)

## 3. Fetch SMAP Soil Moisture

```bash
python3 scripts/fetch_smap_soil_moisture.py \
  --lat 36.3 --lon -83.9 \
  --start 2020-01-01 --end 2025-12-31
```

**Note:** The current script is a placeholder. Full implementation requires:
- `pip install earthaccess`
- `earthaccess login` (interactive)
- Or use `requests` with `.netrc` for programmatic auth

Output is written to `data/soil/`.
