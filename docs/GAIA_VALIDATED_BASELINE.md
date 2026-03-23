# GAIA Validated Performance Baseline

**Date:** 2026-03-23  
**Corpus:** 460 East TN severe weather events (1996–2025)  
**Quiet corpus:** 200 days  

## Metrics

| Metric | Value |
|-------|-------|
| **Detection** | 386/460 (83.9%) |
| **False alarm rate** | 37/200 (18.5%) |
| **Average lead time** | 176 minutes |

## By Event Type

| Type | Rate |
|------|------|
| Thunderstorm wind | 82.6% |
| Hail | 87.1% |
| Tornado | 76.2% |
| Flash flood | 100% |
| Heavy snow | 100% |
| Winter storm | 100% |

## Architecture

- **Engines:** 14 surface engines + 8 sirens
- **Tier 1:** GOES, NEXRAD, GLM, terrain, soil
- **Seasonal overlay:** Spring / Summer / Fall / Winter (East TN)
- **TRI facilities:** 87 East TN hazmat locations

## Key Engines

- 14 surface engines + 8 sirens
- Tier 1: GOES, NEXRAD, GLM, terrain, soil
- Seasonal overlay: spring / summer / fall / winter
- TRI facilities: 87 East TN hazmat locations

## NWS Comparison

| Metric | NWS | GAIA |
|--------|-----|------|
| Tornado false alarm rate | 75% | 18.5% |
| Average lead time | 13 min | 176 min |

---

*Validated baseline. Do not change detection thresholds without re-validation.*
