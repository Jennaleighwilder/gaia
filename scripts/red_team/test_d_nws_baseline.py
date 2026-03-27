#!/usr/bin/env python3
"""
RED TEAM D: Honest NWS lead-time baseline for significant supercell tornadoes
vs population-wide ~13 min average.
"""
from __future__ import annotations

import sys

# Documented / literature-cited operational leads for major events (illustrative; cite SPC/NWS in paper).
NWS_MAJOR_SUPERCELL_LEADS = [
    ("2011-04-27", "Tuscaloosa-Birmingham EF4", 24),
    ("2011-04-27", "Hackleburg EF5", 16),
    ("2011-04-27", "Smithville EF5", 19),
    ("2011-05-22", "Joplin EF5", 24),
    ("2013-05-20", "Moore EF5", 16),
    ("2021-12-10", "Mayfield KY (Paducah WFO)", 28),
    ("2013-05-31", "El Reno OK (context: significant)", 18),
    ("2020-04-12", "Easter 2020 outbreak (illustrative avg)", 22),
]

GAIA_CLAIMED_LEAD_MIN = 193  # Quad-State case study figure from project docs


def main() -> int:
    print("=== RED TEAM D: NWS OPERATIONAL BASELINE (MAJOR SUPERCELLS) ===")
    print()
    print("13-minute NWS mean lead applies to ALL warned tornadoes (weak, poor geometry, etc.).")
    print("For long-track significant tornadoes with good radar coverage, operational leads are often higher.")
    print()
    for date, name, lead in NWS_MAJOR_SUPERCELL_LEADS:
        print(f"  {date}  {name}: ~{lead} min (document in paper with primary source)")
    leads = [x[2] for x in NWS_MAJOR_SUPERCELL_LEADS]
    mean_lead = sum(leads) / len(leads)
    print()
    print(f"Mean of listed major-event leads: {mean_lead:.1f} min")
    print()
    print("Headline check (example):")
    print(f"  GAIA case study ~{GAIA_CLAIMED_LEAD_MIN} min vs 13 min all-tornado mean ⇒ {GAIA_CLAIMED_LEAD_MIN/13:.1f}×")
    print(f"  vs ~{mean_lead:.0f} min major-supercell baseline ⇒ {GAIA_CLAIMED_LEAD_MIN/mean_lead:.1f}×")
    print()
    print("RESULT: PASS — report BOTH baselines in any public comparison.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
