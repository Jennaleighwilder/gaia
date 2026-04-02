#!/usr/bin/env python3
"""
NYX HEARTBEAT
Run daily. Keeps the Dead Hand from firing.
Checks all tripwires. Reports kingdom status.
"""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapters.colony_bridge import ColonyBridge
from adapters.fence_bridge import FenceBridge
from adapters.kay import KayAdapter
from adapters.lancelot import LancelotAdapter
from nyx.core import Nyx


def main() -> int:
    secret = os.environ.get("WEST_OS_GUARD_SECRET")
    if not secret:
        print("WARNING: WEST_OS_GUARD_SECRET not set. Using demo mode.")
        secret = "demo_heartbeat_key"

    nyx = Nyx(master_secret=secret)
    nyx.dead_hand.arm()
    nyx.dead_hand.heartbeat()

    lancelot = LancelotAdapter()
    kay = KayAdapter()
    colony = ColonyBridge(nyx)
    fence = FenceBridge(nyx)

    print()
    print("=" * 50)
    print("  NYX HEARTBEAT")
    print("=" * 50)
    print()

    root = nyx.root.status()
    print(f"  Root alive:        {root['alive']}")
    print(f"  Root fingerprint:  {root['root_fingerprint']}")
    print(f"  Systems blessed:   {root['systems_blessed']}")
    print(f"  Systems revoked:   {root['systems_revoked']}")

    dead_hand = nyx.dead_hand.check()
    print(f"\n  Dead Hand:         {dead_hand['status']}")
    print(f"  Heartbeat sent:    {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Next deadline:     {dead_hand['heartbeat_remaining']:.0f}s")
    print(f"  Tripwires:         {dead_hand['tripwires_checked']}")
    print(f"  Tripped:           {len(dead_hand.get('tripwires_tripped', []))}")

    for _ in range(5):
        nyx.shapeshifter.current_shape()
    consistency = nyx.shapeshifter.consistency_check()
    print(f"\n  Shapeshifter:      {'EFFECTIVE' if consistency['effective'] else 'WEAK'}")
    print(f"  Scan overlap:      {consistency['average_overlap_between_scans']:.1%}")

    threat = nyx.watcher.threat_assessment()
    print(f"\n  Watcher:           {threat['status']}")
    print(f"  Probes logged:     {threat['total_probes_logged']}")

    print("\n  ADAPTERS:")
    print(f"    Lancelot (West-OS):  {'CONNECTED' if lancelot.is_available else 'NOT FOUND'}")
    print(f"    Kay (Alfred):        {'CONNECTED' if kay.is_available else 'NOT FOUND'}")
    print(f"    Colony Bridge:       {'CONNECTED' if colony.is_available else 'NOT FOUND'}")
    print(f"    Fence Bridge:        {'CONNECTED' if fence.is_available else 'NOT FOUND'}")

    if lancelot.is_available:
        freeze = lancelot.verify_freeze()
        print(f"    Lancelot freeze:     {freeze.get('status', 'UNKNOWN')}")

    if fence.is_available:
        fence_check = fence.pre_flight_nyx_check()
        print(f"\n  Fence pre-flight:  {fence_check['verdict']}")

    all_good = (
        root["alive"]
        and root["systems_revoked"] == 0
        and dead_hand["status"] == "WATCHING"
        and len(dead_hand.get("tripwires_tripped", [])) == 0
    )

    print(f"\n  {'=' * 50}")
    if all_good:
        print("  ALL CLEAR - Nyx is alive. The void holds.")
    else:
        print("  WARNING - Issues detected. Review above.")
    print(f"  {'=' * 50}")
    print()

    return 0 if all_good else 1


if __name__ == "__main__":
    raise SystemExit(main())
