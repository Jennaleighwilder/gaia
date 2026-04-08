"""
Round Table JSONL Instrumenter
-------------------------------
Drop this next to your round_table.py inside gaia/avalon/.

It wraps the Round Table's deliberate() and decree() methods to
automatically emit JSONL training pairs after every council session.

KnightVoice objects (reasoning + confidence + vote) are the gold.
The DEFER case and minority reasoning are MORE valuable than the AYE.

Usage — two options:

OPTION A: Import and wrap at runtime (no modification to round_table.py)
    from round_table_instrumenter import instrument_round_table
    from round_table import RoundTable
    RoundTable = instrument_round_table(RoundTable)

OPTION B: Run standalone to replay any saved council JSON logs
    python round_table_instrumenter.py --logs ~/west-os/logs/councils/ --out ./training_data/

Output format per JSONL line:
{
    "proposal": "...",
    "knight_votes": [
        {"knight": "Galahad", "vote": "AYE", "reasoning": "...", "confidence": 0.91}
    ],
    "outcome": "DECREED|DEFERRED|QUORUM_FAILED",
    "quorum_met": true,
    "minority_reasoning": "...",   # the most valuable field
    "dissenting_knights": ["Percival"],
    "confidence_avg": 0.84,
    "vote_distribution": {"AYE": 5, "NAY": 1, "DEFER": 1, "ABSTAIN": 0},
    "label": "council_reasoning",
    "session_id": "sha256:...",
    "timestamp": "2026-04-07T..."
}
"""

import json
import hashlib
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from functools import wraps

DEFAULT_COUNCIL_LOG = Path.home() / "west-os" / "training_data" / "council_traces"


# ── Formatting ────────────────────────────────────────────────────────────────

def format_knight_voice(voice: Any) -> dict:
    """
    Convert a KnightVoice dataclass (or dict) to a clean training record.
    Handles both dataclass and dict representations.
    """
    if hasattr(voice, "__dataclass_fields__"):
        return {
            "knight": getattr(voice, "knight_name", getattr(voice, "name", str(voice))),
            "vote": getattr(voice, "vote", "").value if hasattr(getattr(voice, "vote", ""), "value") else str(getattr(voice, "vote", "")),
            "reasoning": getattr(voice, "reasoning", ""),
            "confidence": float(getattr(voice, "confidence", 0.0)),
            "domain": getattr(voice, "domain", getattr(voice, "role", "")),
        }
    elif isinstance(voice, dict):
        vote = voice.get("vote", "")
        if hasattr(vote, "value"):
            vote = vote.value
        return {
            "knight": voice.get("knight_name", voice.get("name", "")),
            "vote": str(vote),
            "reasoning": voice.get("reasoning", ""),
            "confidence": float(voice.get("confidence", 0.0)),
            "domain": voice.get("domain", voice.get("role", "")),
        }
    return {"raw": str(voice)}


def compute_vote_distribution(knight_voices: list) -> dict:
    dist = {"AYE": 0, "NAY": 0, "ABSTAIN": 0, "DEFER": 0}
    for v in knight_voices:
        vote_str = v.get("vote", "").upper()
        if vote_str in dist:
            dist[vote_str] += 1
    return dist


def extract_minority_reasoning(knight_voices: list, outcome: str) -> str:
    """
    Extract reasoning from dissenting knights.
    If outcome is DECREED (AYE won), minority = NAY + DEFER voices.
    If outcome is DEFERRED, minority = NAY voices.
    The minority reasoning is the most training-valuable field.
    """
    if outcome in ("DECREED", "QUORUM_MET"):
        dissent_votes = {"NAY", "DEFER"}
    else:
        dissent_votes = {"NAY"}

    minority = [
        v for v in knight_voices
        if v.get("vote", "").upper() in dissent_votes and v.get("reasoning")
    ]
    if not minority:
        return ""
    parts = [f"{v['knight']}: {v['reasoning']}" for v in minority]
    return " | ".join(parts)


def build_council_record(
    proposal: Any,
    knight_voices: list,
    outcome: str,
    quorum_met: bool,
    session_id: Optional[str] = None,
) -> dict:
    """Build the complete JSONL training record for one council session."""
    votes = [format_knight_voice(v) for v in knight_voices]
    confidences = [v["confidence"] for v in votes if v.get("confidence", 0) > 0]
    confidence_avg = sum(confidences) / len(confidences) if confidences else 0.0

    minority = extract_minority_reasoning(votes, outcome)
    vote_dist = compute_vote_distribution(votes)

    dissenting = [
        v["knight"] for v in votes
        if v.get("vote", "").upper() in {"NAY", "DEFER"}
    ]

    # Proposal might be a string, dict, or object
    if hasattr(proposal, "__dict__"):
        proposal_text = str(proposal)
    elif isinstance(proposal, dict):
        proposal_text = proposal.get("matter", proposal.get("text", json.dumps(proposal)))
    else:
        proposal_text = str(proposal)

    ts = datetime.now(timezone.utc).isoformat()
    if not session_id:
        session_id = hashlib.sha256(
            f"{proposal_text}{ts}".encode()
        ).hexdigest()[:16]

    return {
        "proposal": proposal_text,
        "knight_votes": votes,
        "outcome": outcome,
        "quorum_met": quorum_met,
        "minority_reasoning": minority,
        "dissenting_knights": dissenting,
        "confidence_avg": round(confidence_avg, 4),
        "vote_distribution": vote_dist,
        "label": "council_reasoning",
        "session_id": session_id,
        "timestamp": ts,
    }


def write_record(record: dict, out_dir: Path = DEFAULT_COUNCIL_LOG):
    """Append one JSONL record to today's council log file."""
    out_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    out_file = out_dir / f"council_traces_{today}.jsonl"
    with open(out_file, "a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ── Runtime wrapper ───────────────────────────────────────────────────────────

def instrument_round_table(RoundTableClass, out_dir: Path = DEFAULT_COUNCIL_LOG):
    """
    Wraps RoundTable to auto-emit JSONL after every council.

    Usage:
        from round_table_instrumenter import instrument_round_table
        from round_table import RoundTable
        RoundTable = instrument_round_table(RoundTable)
        # Now every council session auto-logs to JSONL
    """
    original_decree = getattr(RoundTableClass, "decree", None)
    original_deliberate = getattr(RoundTableClass, "deliberate", None)

    def _capture_council(instance):
        """Extract and write the council record after deliberation."""
        try:
            # Try common attribute names for proposal and voices
            active_council = getattr(instance, "_active_council", None)
            proposal = (
                getattr(active_council, "question", None) or
                getattr(instance, "current_matter", None) or
                getattr(instance, "proposal", None) or
                getattr(instance, "_matter", None) or
                "unknown proposal"
            )
            voices = (
                list(getattr(active_council, "voices", {}).values()) if active_council else
                getattr(instance, "voices", None) or
                getattr(instance, "votes", None) or
                getattr(instance, "_voices", None) or
                []
            )
            state = getattr(active_council, "state", None) or getattr(instance, "state", None)
            if hasattr(state, "value"):
                state_str = state.value
            else:
                state_str = str(state)

            quorum_met = "QUORUM_MET" in state_str or "DECREED" in state_str

            record = build_council_record(
                proposal=proposal,
                knight_voices=list(voices),
                outcome=state_str,
                quorum_met=quorum_met,
            )
            write_record(record, out_dir)
            return record
        except Exception as e:
            # Never break the council — just log the failure
            print(f"[round_table_instrumenter] Warning: could not capture council: {e}")
            return None

    if original_decree:
        @wraps(original_decree)
        def patched_decree(self, *args, **kwargs):
            result = original_decree(self, *args, **kwargs)
            _capture_council(self)
            return result
        RoundTableClass.decree = patched_decree

    elif original_deliberate:
        @wraps(original_deliberate)
        def patched_deliberate(self, *args, **kwargs):
            result = original_deliberate(self, *args, **kwargs)
            _capture_council(self)
            return result
        RoundTableClass.deliberate = patched_deliberate

    return RoundTableClass


# ── Standalone replay from saved council logs ─────────────────────────────────

def replay_council_logs(logs_dir: Path, out_dir: Path):
    """
    Replay saved council JSON log files and re-export as training JSONL.
    Useful if your Round Table already has log files but in a different format.
    """
    log_files = list(logs_dir.glob("**/*.json")) + list(logs_dir.glob("**/*.jsonl"))
    if not log_files:
        print(f"No .json or .jsonl files found in {logs_dir}")
        return 0

    count = 0
    for log_file in log_files:
        print(f"  Processing {log_file.name}...")
        try:
            with open(log_file) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        raw = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    # Try to extract council structure from various log formats
                    proposal = raw.get("proposal", raw.get("matter", raw.get("text", "")))
                    voices = raw.get("voices", raw.get("votes", raw.get("knight_voices", [])))
                    outcome = raw.get("outcome", raw.get("state", raw.get("decree", "")))
                    quorum = raw.get("quorum_met", "DECREED" in str(outcome))

                    if proposal or voices:
                        record = build_council_record(proposal, voices, str(outcome), bool(quorum))
                        write_record(record, out_dir)
                        count += 1
        except Exception as e:
            print(f"    Error processing {log_file}: {e}")
            continue

    return count


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Instrument Round Table to emit JSONL training pairs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Replay existing council logs
  python round_table_instrumenter.py --logs ~/west-os/logs/councils/ --out ./training_data/council_traces/

  # Test with a synthetic council (verifies output format)
  python round_table_instrumenter.py --test

  # Check what council logs exist
  python round_table_instrumenter.py --logs ~/west-os/logs/ --dry-run
        """
    )
    parser.add_argument("--logs", type=Path, help="Directory of existing council log files to replay")
    parser.add_argument("--out", type=Path, default=DEFAULT_COUNCIL_LOG, help="Output directory for JSONL")
    parser.add_argument("--test", action="store_true", help="Write one synthetic test record to verify output")
    parser.add_argument("--dry-run", action="store_true", help="List log files found without processing")
    args = parser.parse_args()

    if args.test:
        print("Writing synthetic test council record...")
        test_voices = [
            {"name": "Galahad", "vote": "AYE", "reasoning": "GAIA chain is stable, Nyx metabolism nominal.", "confidence": 0.94, "domain": "nyx_chain"},
            {"name": "Bors", "vote": "AYE", "reasoning": "GAIA readings within threshold.", "confidence": 0.88, "domain": "gaia"},
            {"name": "Percival", "vote": "DEFER", "reasoning": "TESS signal ambiguous — one data point is insufficient for this conviction level.", "confidence": 0.61, "domain": "tess"},
            {"name": "Bedivere", "vote": "AYE", "reasoning": "Dead-hand check passed.", "confidence": 0.91, "domain": "dead_hand"},
        ]
        record = build_council_record(
            proposal="Allow TESS HIGH conviction M&A signal to publish externally.",
            knight_voices=test_voices,
            outcome="DECREED",
            quorum_met=True,
            session_id="test_session_001",
        )
        write_record(record, args.out)
        print(f"Test record written to {args.out}")
        print(json.dumps(record, indent=2))
        return

    if args.dry_run and args.logs:
        files = list(args.logs.glob("**/*.json")) + list(args.logs.glob("**/*.jsonl"))
        print(f"Found {len(files)} log files in {args.logs}:")
        for f in files[:20]:
            print(f"  {f}")
        if len(files) > 20:
            print(f"  ... and {len(files) - 20} more")
        return

    if args.logs:
        count = replay_council_logs(args.logs, args.out)
        print(f"\nDone. {count} council records written to {args.out}")
    else:
        print("For runtime instrumentation, import into your code:")
        print("  from round_table_instrumenter import instrument_round_table")
        print("  from round_table import RoundTable")
        print("  RoundTable = instrument_round_table(RoundTable)")
        print()
        print("For replay of existing logs:")
        print("  python round_table_instrumenter.py --logs ~/west-os/logs/councils/")
        print()
        print("To test output format:")
        print("  python round_table_instrumenter.py --test")


if __name__ == "__main__":
    main()
