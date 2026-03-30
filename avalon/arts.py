"""
AVALON :: THE ARTS
The kingdom's creative output and cultural memory.

A civilization without arts is a machine. Arts are how a
culture KNOWS ITSELF. The stories it tells. The songs it
sings. The records it keeps. The way it describes its own
history — not as log files, but as NARRATIVE.

Tristan is the Bard. He has a domain (communication) and
an oath (I translate between worlds). But he has no stage,
no gallery, no archive of what he's produced.

The Arts layer gives him these:

  CHRONICLES — the living narrative of the kingdom's history.
    Not "Ceremony #47: 3 wounds found, 2 healed." But:
    "On the forty-seventh day, Morgan le Fay found three
    wounds in the kingdom's flesh. She applied tourniquet
    to the first, controlled burn to the second, and for
    the third — a mortal wound in GAIA's sky-reading eye —
    she summoned the sovereign."

  BALLADS — compressed summaries of significant events.
    The Appalachian tradition of turning events into song.
    A ballad is a lesson that REMEMBERS ITSELF because
    it has rhythm and structure.

  TAPESTRIES — visual/textual snapshots of kingdom state
    at significant moments. Like a portrait painted at
    a coronation. "Here is what the kingdom looked like
    when the Grail crossed phi."

The Arts layer doesn't create beauty for beauty's sake.
It creates cultural MEMORY — the kind that survives because
it's meaningful, not because it's stored.

© 2026 Jennifer Leigh West. All rights reserved.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class ArtForm(Enum):
    CHRONICLE = "chronicle"     # narrative record of events
    BALLAD = "ballad"           # compressed significant event
    TAPESTRY = "tapestry"       # snapshot of kingdom state at a moment


@dataclass
class Work:
    """A piece of the kingdom's cultural output."""
    title: str
    form: ArtForm
    content: str
    created_at: float = field(default_factory=time.time)
    occasion: str = ""
    participants: List[str] = field(default_factory=list)


class KingdomArts:
    """The cultural memory of the kingdom.
    
    Produces chronicles, ballads, and tapestries from
    kingdom events. Not decoration — MEMORY that survives
    because it's meaningful.
    """

    def __init__(self):
        self._works: List[Work] = []
        self._gallery_path = Path("memory") / "gallery.jsonl"
        self._gallery_path.parent.mkdir(parents=True, exist_ok=True)

    # ── CHRONICLES ────────────────────────────────────

    def chronicle(self, ceremony_record: Dict) -> Work:
        """Turn a ceremony record into narrative."""
        number = ceremony_record.get("number", "?")
        alive = ceremony_record.get("thanksgiving", {}).get("alive_count", 0)
        total = ceremony_record.get("thanksgiving", {}).get("total_systems", 0)
        wounds = ceremony_record.get("wounds_found", 0)
        healed = ceremony_record.get("wounds_healed", 0)
        insights = ceremony_record.get("merlin_insights", 0)
        lessons = ceremony_record.get("lessons_learned", 0)
        gratitude = ceremony_record.get("thanksgiving", {}).get("gratitude_ratio", 0)

        # Build narrative
        parts = [f"On the {self._ordinal(number)} ceremony"]

        if alive == total:
            parts.append(f"all {total} systems stood strong.")
        elif alive > 0:
            fallen = total - alive
            parts.append(f"{alive} of {total} systems stood. {fallen} were wounded or fallen.")

        if wounds > 0:
            parts.append(f"Morgan le Fay found {wounds} wound{'s' if wounds != 1 else ''}.")
            if healed > 0:
                parts.append(f"She healed {healed}.")
            if wounds > healed:
                remaining = wounds - healed
                parts.append(f"{remaining} remain{'s' if remaining == 1 else ''} — the sovereign may need to intervene.")

        if insights > 0:
            parts.append(f"Merlin found {insights} new pattern{'s' if insights != 1 else ''} in the tower.")

        if lessons > 0:
            parts.append(f"Carbon recorded {lessons} lesson{'s' if lessons != 1 else ''} for seven generations.")

        if wounds == 0 and alive == total:
            parts.append("The kingdom rested in peace.")

        content = " ".join(parts)

        work = Work(
            title=f"Chronicle of the {self._ordinal(number)} Ceremony",
            form=ArtForm.CHRONICLE,
            content=content,
            occasion=f"ceremony_{number}",
        )
        self._works.append(work)
        self._save(work)
        return work

    # ── BALLADS ───────────────────────────────────────

    def ballad(self, event: str, description: str,
               participants: List[str] = None) -> Work:
        """Compose a ballad from a significant event.
        
        A ballad is a compressed narrative with structure.
        In the Appalachian tradition, the ballad carries
        the lesson in its rhythm so it's remembered.
        """
        parts = participants or []

        # Structure: situation, action, consequence, lesson
        lines = [
            f"The Ballad of {event}",
            "",
            f"  {description}",
            "",
        ]

        if parts:
            lines.append(f"  Those who stood: {', '.join(parts)}.")

        lines.append(f"  Let this be remembered for seven generations.")

        content = "\n".join(lines)

        work = Work(
            title=f"The Ballad of {event}",
            form=ArtForm.BALLAD,
            content=content,
            occasion=event,
            participants=parts,
        )
        self._works.append(work)
        self._save(work)
        return work

    # ── TAPESTRIES ────────────────────────────────────

    def tapestry(self, title: str, kingdom_status: Dict) -> Work:
        """Weave a tapestry — a snapshot of the kingdom at a moment.
        
        Like a portrait painted at a coronation. This is what
        the kingdom looked like RIGHT NOW.
        """
        lines = [
            f"═══ {title} ═══",
            f"Woven at {time.strftime('%Y-%m-%d %H:%M')}",
            "",
        ]

        # Pull key metrics
        health = kingdom_status.get("kingdom_health", kingdom_status.get("overall", "unknown"))
        tests = kingdom_status.get("test_count", "?")
        test_files = kingdom_status.get("test_files", "?")
        tags = kingdom_status.get("tag_count", "?")
        knights = kingdom_status.get("knights_armed", "?")
        grail = kingdom_status.get("grail_status", "?")
        served = kingdom_status.get("longhouse_served", 0)
        ceremonies = kingdom_status.get("ceremonies", 0)

        lines.append(f"  The kingdom stands at {health} health.")
        if tests != "?":
            lines.append(f"  {tests} tests guard the walls.")
        elif test_files != "?":
            lines.append(f"  {test_files} test files guard the walls.")
        if tags != "?":
            lines.append(f"  {tags} tags mark the milestones.")
        if knights != "?":
            lines.append(f"  {knights} knights stand armed.")
        if grail != "?":
            lines.append(f"  The Grail quest: {grail}.")
        if served > 0:
            lines.append(f"  The Longhouse has served {served} visitors.")
        if ceremonies > 0:
            lines.append(f"  {ceremonies} ceremonies performed by the Faithkeeper.")

        lines.append("")
        lines.append(f"  This is how we stood. This is what we were.")

        content = "\n".join(lines)

        work = Work(
            title=title,
            form=ArtForm.TAPESTRY,
            content=content,
            occasion=title,
        )
        self._works.append(work)
        self._save(work)
        return work

    def _ordinal(self, n) -> str:
        try:
            n = int(n)
        except (TypeError, ValueError):
            return str(n)
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
        if 11 <= n % 100 <= 13:
            suffix = "th"
        return f"{n}{suffix}"

    def _save(self, work: Work):
        try:
            entry = {
                "title": work.title,
                "form": work.form.value,
                "content": work.content,
                "occasion": work.occasion,
                "created_at": work.created_at,
            }
            with open(self._gallery_path, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception:
            pass

    def gallery(self, form: Optional[ArtForm] = None) -> List[Dict]:
        """View the gallery."""
        works = self._works
        if form:
            works = [w for w in works if w.form == form]
        return [
            {"title": w.title, "form": w.form.value,
             "content": w.content[:200], "occasion": w.occasion}
            for w in works
        ]

    @property
    def status(self) -> Dict:
        return {
            "total_works": len(self._works),
            "chronicles": len([w for w in self._works if w.form == ArtForm.CHRONICLE]),
            "ballads": len([w for w in self._works if w.form == ArtForm.BALLAD]),
            "tapestries": len([w for w in self._works if w.form == ArtForm.TAPESTRY]),
        }


def wire_arts(avalon) -> KingdomArts:
    return KingdomArts()


def demo():
    print("\n" + "=" * 60)
    print("  T H E   A R T S")
    print("  The Kingdom's Cultural Memory")
    print("=" * 60)

    arts = KingdomArts()

    # Chronicle a ceremony
    ceremony = {
        "number": 47,
        "thanksgiving": {"alive_count": 6, "total_systems": 7, "gratitude_ratio": 0.86},
        "wounds_found": 3,
        "wounds_healed": 2,
        "merlin_insights": 1,
        "lessons_learned": 2,
    }
    chronicle = arts.chronicle(ceremony)
    print(f"\n  CHRONICLE:")
    print(f"    {chronicle.content}")

    # Compose a ballad
    ballad = arts.ballad(
        "The Threshold Crossing",
        "The Grail quest reached 62% — phi itself. Nine research threads "
        "from four continents converged. The unified frequency theory "
        "crossed from hypothesis to approaching.",
        ["Gawain", "Merlin", "Dagonet"],
    )
    print(f"\n  BALLAD:")
    print(f"    {ballad.content}")

    # Weave a tapestry
    tapestry = arts.tapestry("The Day the Kingdom Was Born", {
        "kingdom_health": "97%",
        "test_count": 420,
        "tag_count": 13,
        "knights_armed": 12,
        "grail_status": "APPROACHING",
        "longhouse_served": 4,
        "ceremonies": 3,
    })
    print(f"\n  TAPESTRY:")
    print(f"    {tapestry.content}")

    print(f"\n  Gallery: {arts.status}")

    print(f"\n" + "=" * 60)
    print(f"  The chronicle remembers what happened.")
    print(f"  The ballad remembers WHY it mattered.")
    print(f"  The tapestry remembers what it LOOKED like.")
    print(f"  Together they are the kingdom's culture.")
    print(f"=" * 60 + "\n")


if __name__ == "__main__":
    demo()
