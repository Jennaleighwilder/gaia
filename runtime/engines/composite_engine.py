"""
GAIA Composite Engine (Engine 14)

Scores SPC-style composite severe weather parameters supplied by the
upper-air client. This engine is intentionally domain-specific: it does
not derive CAPE/shear/helicity itself, it only interprets the already
computed upper-air parameters.
"""

from __future__ import annotations


class CompositeEngine:
    def score(self, upper_air: dict | None) -> dict:
        if not upper_air:
            return {
                "engine": "composite",
                "score": 0.0,
                "channels": {},
                "note": "no upper air data available",
            }

        channels: dict[str, float] = {}

        stp = upper_air.get("significant_tornado_parameter", 0.0) or 0.0
        if stp <= 0:
            channels["stp"] = 0.0
        elif stp < 0.5:
            channels["stp"] = 0.1
        elif stp < 1.0:
            channels["stp"] = 0.3
        elif stp < 3.0:
            channels["stp"] = 0.7
        elif stp < 6.0:
            channels["stp"] = 0.9
        else:
            channels["stp"] = 1.0

        scp = upper_air.get("supercell_composite", 0.0) or 0.0
        if scp <= 0:
            channels["scp"] = 0.0
        elif scp < 1.0:
            channels["scp"] = 0.15
        elif scp < 4.0:
            channels["scp"] = 0.5
        elif scp < 8.0:
            channels["scp"] = 0.8
        else:
            channels["scp"] = 1.0

        ehi = upper_air.get("energy_helicity_index_0_1km", 0.0) or 0.0
        if ehi <= 0:
            channels["ehi"] = 0.0
        elif ehi < 1.0:
            channels["ehi"] = 0.2
        elif ehi < 2.0:
            channels["ehi"] = 0.5
        elif ehi < 4.0:
            channels["ehi"] = 0.75
        else:
            channels["ehi"] = 1.0

        lcl = upper_air.get("lcl_height_agl_m", 3000) or 3000
        if lcl > 2000:
            channels["lcl"] = 0.05
        elif lcl > 1500:
            channels["lcl"] = 0.2
        elif lcl > 1000:
            channels["lcl"] = 0.5
        elif lcl > 500:
            channels["lcl"] = 0.75
        else:
            channels["lcl"] = 0.95

        shear = upper_air.get("bulk_shear_0_6km_kts", 0.0) or 0.0
        if shear < 15:
            channels["deep_shear"] = 0.05
        elif shear < 25:
            channels["deep_shear"] = 0.2
        elif shear < 35:
            channels["deep_shear"] = 0.45
        elif shear < 50:
            channels["deep_shear"] = 0.7
        else:
            channels["deep_shear"] = 0.95

        srh = upper_air.get("srh_0_1km_m2s2", 0.0) or 0.0
        if srh < 50:
            channels["srh"] = 0.05
        elif srh < 100:
            channels["srh"] = 0.2
        elif srh < 200:
            channels["srh"] = 0.5
        elif srh < 300:
            channels["srh"] = 0.75
        else:
            channels["srh"] = 0.95

        weights = {
            "stp": 0.35,
            "scp": 0.20,
            "ehi": 0.15,
            "lcl": 0.08,
            "deep_shear": 0.12,
            "srh": 0.10,
        }
        total = sum(channels.get(name, 0.0) * weight for name, weight in weights.items())
        if stp >= 1.0:
            total = max(total, 0.5)

        return {
            "engine": "composite",
            "score": round(min(1.0, total), 4),
            "channels": channels,
            "raw": {
                "stp": round(stp, 3),
                "scp": round(scp, 3),
                "shear_0_6km_kts": round(shear, 1),
                "srh_0_1km": round(srh, 1),
                "lcl_m": round(lcl, 0),
            },
        }
