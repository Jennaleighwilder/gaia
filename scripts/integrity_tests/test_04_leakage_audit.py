#!/usr/bin/env python3
"""
4. Data leakage audit: any observation timestamp after event_time => FAIL.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import scripts.integrity_tests._paths  # noqa: F401

ROOT = scripts.integrity_tests._paths.ROOT
CANDIDATES = [
    ROOT / "runs" / "backtest_results.json",
    ROOT / "runs" / "forward_test_results.json",
]


def parse_ts(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def audit_obj(obj: dict, path: Path) -> tuple[int, list[str]]:
    """Return (violation_count, messages)."""
    msgs: list[str] = []
    bad = 0

    def walk(x, prefix: str = "") -> None:
        nonlocal bad
        if isinstance(x, dict):
            et = x.get("event_time") or x.get("eventTime")
            obs_list = x.get("observation_timestamps") or x.get("observationTimestamps")
            if et and obs_list:
                et_dt = parse_ts(str(et)) if not isinstance(et, datetime) else et
                if et_dt is None:
                    return
                for o in obs_list:
                    odt = parse_ts(str(o)) if not isinstance(o, datetime) else o
                    if odt and odt > et_dt:
                        bad += 1
                        msgs.append(f"{prefix}obs after event: {odt} > {et_dt}")
            for k, v in x.items():
                walk(v, f"{prefix}{k}.")
        elif isinstance(x, list):
            for i, v in enumerate(x):
                walk(v, f"{prefix}[{i}].")

    walk(obj)
    return bad, msgs


def main() -> int:
    chosen: Path | None = None
    for p in CANDIDATES:
        if p.exists():
            chosen = p
            break
    if chosen is None:
        print(
            "RESULT: WARN — no backtest/forward JSON at runs/backtest_results.json "
            "or runs/forward_test_results.json; leakage audit skipped"
        )
        return 0
    try:
        data = json.loads(chosen.read_text())
    except json.JSONDecodeError as e:
        print(f"RESULT: FAIL — invalid JSON in {chosen.name}: {e}")
        return 1
    n, msgs = audit_obj(data if isinstance(data, dict) else {"items": data}, chosen)
    if n == 0:
        print(f"RESULT: PASS — zero post-event observations in {chosen.relative_to(ROOT)}")
        return 0
    print(f"RESULT: FAIL — {n} post-event observation timestamp(s) in {chosen.name}")
    for m in msgs[:20]:
        print(f"  {m}")
    if len(msgs) > 20:
        print(f"  ... and {len(msgs) - 20} more")
    return 1


if __name__ == "__main__":
    sys.exit(main())
