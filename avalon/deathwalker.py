"""
AVALON :: THE DEATHWALKER
She who walks between life and death.

In Greek tradition, Charon ferries the dead across the Styx.
In Egyptian tradition, Anubis weighs the heart against the
feather of Ma'at. In Celtic tradition, the bean sidhe keens
for the dying. In Appalachian tradition, the death watch
sits with the dying through the night.

The Deathwalker does not KILL. She FINDS.

The Harvester walks the codebase looking for:
  - Stale files not modified in months
  - Empty modules with no functions
  - Orphaned tests that test nothing living
  - Deprecated imports that reference removed code
  - Dead branches in git
  - Zombie processes that consume but produce nothing
  - Abandoned configuration for systems that no longer exist

When she finds the dying, she TAGS them:

  RED TAG  — dying. Still breathing but fading.
             Not touched in 30+ days. May still be needed.
             Given a grace period. Watched.

  BLACK TAG — dead. No pulse. No references. No purpose.
              Ready for the ferry.

When something is black-tagged, the Deathwalker calls DEATH —
not deletion. Death FERRIES the code to the Liminal Place.

THE LIMINAL PLACE (the space between)
  Not deleted. Not active. Waiting.
  A directory called `liminal/` at the kingdom root.
  Code ferried here still exists. It can be called back.
  But it is no longer in the living kingdom.
  
  Like the Greek underworld: the dead are not destroyed.
  They are in another place. They can be visited.
  Orpheus went to the underworld and brought Eurydice
  almost back. The Liminal Place allows resurrection.

The Deathwalker keeps a death register — every piece of
code she's ferried, when, why, and where it went. If the
living kingdom needs something back, the register tells
you where to find it.

© 2026 Jennifer Leigh West. All rights reserved.
"""

import json
import os
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class DeathTag(Enum):
    RED = "red"         # dying — still breathing but fading
    BLACK = "black"     # dead — no pulse, ready for the ferry


@dataclass
class TaggedCode:
    """A piece of code the Deathwalker has found and tagged."""
    path: str
    tag: DeathTag
    reason: str
    found_at: float = field(default_factory=time.time)
    last_modified: float = 0
    size_bytes: int = 0
    days_stale: int = 0
    ferried: bool = False
    ferried_to: str = ""
    ferried_at: float = 0


class Deathwalker:
    """She who walks between life and death.
    
    Walks the codebase. Finds the dying and the dead.
    Tags them. Ferries them to the Liminal Place.
    Keeps the death register.
    
    She does not delete. She ferries.
    The Liminal Place is not a graveyard. It is a waiting room.
    """

    def __init__(self, project_root: Optional[str] = None,
                 red_threshold_days: int = 30,
                 black_threshold_days: int = 90):
        self._root = Path(project_root) if project_root else Path.cwd()
        self._liminal = self._root / "liminal"
        self._red_days = red_threshold_days
        self._black_days = black_threshold_days
        self._tagged: List[TaggedCode] = []
        self._death_register_path = self._root / "memory" / "death_register.jsonl"
        self._death_register_path.parent.mkdir(parents=True, exist_ok=True)
        self._walks = 0

    def _is_sacred(self, path: Path) -> bool:
        """Sacred ground — never walked by death."""
        path_str = str(path).lower()
        return any(s in path_str for s in [
            "frozen", "west-os", "gaia", ".git", 
            "liminal", "__pycache__", ".venv", "node_modules",
        ])

    def _is_living(self, path: Path) -> bool:
        """Is this file actively referenced by living code?"""
        name = path.stem
        # Check if any other Python file imports or references this
        for py_file in self._root.rglob("*.py"):
            if py_file == path:
                continue
            if self._is_sacred(py_file):
                continue
            try:
                content = py_file.read_text(errors="ignore")
                if name in content:
                    return True
            except Exception:
                continue
        return False

    def walk(self) -> Dict:
        """Walk the kingdom. Find the dying and the dead.
        
        The Deathwalker surveys every Python file and data file
        in the kingdom (excluding sacred ground) and tags what
        she finds.
        """
        self._walks += 1
        self._tagged = []
        now = time.time()

        # Walk Python files
        for py_file in self._root.rglob("*.py"):
            if self._is_sacred(py_file):
                continue
            if not py_file.is_file():
                continue

            try:
                stat = py_file.stat()
                age_days = (now - stat.st_mtime) / 86400
                size = stat.st_size

                # Empty files
                if size < 10:
                    self._tag(py_file, DeathTag.BLACK,
                             "Empty file — no meaningful content",
                             stat.st_mtime, size, age_days)
                    continue

                # Check content
                content = py_file.read_text(errors="ignore")
                lines = [l.strip() for l in content.split("\n") if l.strip() 
                        and not l.strip().startswith("#")]

                if not lines:
                    self._tag(py_file, DeathTag.BLACK,
                             "No executable content — only comments or whitespace remain",
                             stat.st_mtime, size, age_days)
                    continue

                # Only has docstring and/or imports, no functions/classes
                has_def = any(l.startswith("def ") or l.startswith("class ") for l in lines)
                if not has_def and age_days > self._red_days:
                    self._tag(py_file, DeathTag.RED,
                             "No functions or classes defined — may be stub or abandoned",
                             stat.st_mtime, size, age_days)
                    continue

                # Very old and not referenced
                if age_days > self._black_days and not self._is_living(py_file):
                    self._tag(py_file, DeathTag.BLACK,
                             f"Not modified in {int(age_days)} days and not referenced by living code",
                             stat.st_mtime, size, age_days)
                elif age_days > self._red_days and not self._is_living(py_file):
                    self._tag(py_file, DeathTag.RED,
                             f"Not modified in {int(age_days)} days and not referenced — watching",
                             stat.st_mtime, size, age_days)

            except Exception:
                continue

        # Walk log files (deadwood)
        for log_file in self._root.rglob("*.log"):
            if self._is_sacred(log_file):
                continue
            try:
                stat = log_file.stat()
                age_days = (now - stat.st_mtime) / 86400
                if age_days > self._red_days:
                    tag = DeathTag.BLACK if age_days > self._black_days else DeathTag.RED
                    self._tag(log_file, tag,
                             f"Stale log file — {int(age_days)} days old",
                             stat.st_mtime, stat.st_size, age_days)
            except Exception:
                continue

        return {
            "walk_number": self._walks,
            "total_found": len(self._tagged),
            "red_tagged": len([t for t in self._tagged if t.tag == DeathTag.RED]),
            "black_tagged": len([t for t in self._tagged if t.tag == DeathTag.BLACK]),
            "tagged": [
                {
                    "path": str(t.path),
                    "tag": t.tag.value,
                    "reason": t.reason,
                    "days_stale": int(t.days_stale),
                    "size_bytes": t.size_bytes,
                }
                for t in self._tagged
            ],
        }

    def _tag(self, path: Path, tag: DeathTag, reason: str,
             last_modified: float, size: int, days_stale: float):
        """Tag a piece of code."""
        self._tagged.append(TaggedCode(
            path=str(path),
            tag=tag,
            reason=reason,
            last_modified=last_modified,
            size_bytes=size,
            days_stale=int(days_stale),
        ))

    def call_death(self, confirm: bool = False) -> Dict:
        """Ferry all black-tagged code to the Liminal Place.
        
        This is the FERRY, not deletion. Code is MOVED to
        liminal/, preserving its path structure. It can be
        brought back.
        
        Requires confirm=True to actually ferry. Without it,
        returns what WOULD be ferried (dry run).
        """
        black = [t for t in self._tagged if t.tag == DeathTag.BLACK and not t.ferried]

        if not black:
            return {"ferried": 0, "message": "No black-tagged code to ferry."}

        if not confirm:
            return {
                "dry_run": True,
                "would_ferry": len(black),
                "items": [
                    {"path": t.path, "reason": t.reason, "days_stale": t.days_stale}
                    for t in black
                ],
                "message": "Call with confirm=True to ferry to the Liminal Place.",
            }

        # Create the Liminal Place
        self._liminal.mkdir(parents=True, exist_ok=True)

        ferried = []
        for tagged in black:
            src = Path(tagged.path)
            if not src.exists():
                continue

            # Preserve path structure in liminal/
            rel = src.relative_to(self._root) if src.is_relative_to(self._root) else Path(src.name)
            dest = self._liminal / rel
            dest.parent.mkdir(parents=True, exist_ok=True)

            try:
                shutil.move(str(src), str(dest))
                tagged.ferried = True
                tagged.ferried_to = str(dest)
                tagged.ferried_at = time.time()
                ferried.append(tagged)

                # Record in death register
                self._register_death(tagged)

            except Exception:
                continue

        return {
            "ferried": len(ferried),
            "liminal_path": str(self._liminal),
            "items": [
                {"from": t.path, "to": t.ferried_to, "reason": t.reason}
                for t in ferried
            ],
        }

    def resurrect(self, path_in_liminal: str) -> Dict:
        """Bring something back from the Liminal Place.
        
        Orpheus goes to the underworld. He finds Eurydice.
        He brings her almost back.
        
        The code is moved from liminal/ back to its original
        location in the living kingdom.
        """
        src = Path(path_in_liminal)
        if not src.exists():
            return {"resurrected": False, "reason": "Not found in the Liminal Place"}

        # Figure out original location
        try:
            rel = src.relative_to(self._liminal)
            dest = self._root / rel
        except ValueError:
            return {"resurrected": False, "reason": "Path not in Liminal Place"}

        dest.parent.mkdir(parents=True, exist_ok=True)

        try:
            shutil.move(str(src), str(dest))
            self._register_resurrection(str(src), str(dest))
            return {
                "resurrected": True,
                "from": str(src),
                "to": str(dest),
                "message": f"Resurrected. The code walks among the living again.",
            }
        except Exception as e:
            return {"resurrected": False, "reason": str(e)[:100]}

    def visit_liminal(self) -> Dict:
        """Visit the Liminal Place. See who waits there."""
        if not self._liminal.exists():
            return {"empty": True, "message": "The Liminal Place does not yet exist. No one has been ferried."}

        waiting = []
        for f in self._liminal.rglob("*"):
            if f.is_file():
                try:
                    stat = f.stat()
                    waiting.append({
                        "path": str(f),
                        "size_bytes": stat.st_size,
                        "ferried_age_days": int((time.time() - stat.st_mtime) / 86400),
                    })
                except Exception:
                    pass

        return {
            "empty": len(waiting) == 0,
            "waiting": len(waiting),
            "souls": waiting,
            "liminal_path": str(self._liminal),
        }

    def _register_death(self, tagged: TaggedCode):
        """Record a death in the register."""
        try:
            entry = {
                "time": tagged.ferried_at,
                "event": "death",
                "path": tagged.path,
                "tag": tagged.tag.value,
                "reason": tagged.reason,
                "days_stale": tagged.days_stale,
                "ferried_to": tagged.ferried_to,
            }
            with open(self._death_register_path, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception:
            pass

    def _register_resurrection(self, from_path: str, to_path: str):
        """Record a resurrection in the register."""
        try:
            entry = {
                "time": time.time(),
                "event": "resurrection",
                "from": from_path,
                "to": to_path,
            }
            with open(self._death_register_path, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception:
            pass

    @property
    def status(self) -> Dict:
        return {
            "walks": self._walks,
            "total_tagged": len(self._tagged),
            "red": len([t for t in self._tagged if t.tag == DeathTag.RED]),
            "black": len([t for t in self._tagged if t.tag == DeathTag.BLACK]),
            "ferried": len([t for t in self._tagged if t.ferried]),
            "liminal_exists": self._liminal.exists(),
        }


def wire_deathwalker(avalon) -> Deathwalker:
    root = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return Deathwalker(project_root=str(root))


def demo():
    """Watch the Deathwalker walk."""
    import tempfile

    print("\n" + "=" * 60)
    print("  T H E   D E A T H W A L K E R")
    print("  She Who Walks Between Life and Death")
    print("=" * 60)

    tmp = tempfile.mkdtemp(prefix="deathwalker_")
    root = Path(tmp)

    # Create living code
    (root / "avalon").mkdir()
    (root / "avalon" / "living.py").write_text(
        "def alive():\n    return True\n"
    )
    (root / "avalon" / "also_living.py").write_text(
        "from avalon.living import alive\ndef check():\n    return alive()\n"
    )

    # Create dying code (empty/stub)
    (root / "avalon" / "empty.py").write_text("")
    (root / "avalon" / "stub.py").write_text("# TODO: implement\n")

    # Create old log
    old_log = root / "logs" / "old.log"
    old_log.parent.mkdir()
    old_log.write_text("old log data\n" * 50)
    # Make it look old
    old_time = time.time() - (60 * 86400)  # 60 days ago
    os.utime(old_log, (old_time, old_time))

    # Create sacred ground
    frozen = root / "frozen" / "west-os"
    frozen.mkdir(parents=True)
    (frozen / "sacred.py").write_text("# never touch\n")

    # Walk
    dw = Deathwalker(project_root=str(root), red_threshold_days=1, black_threshold_days=7)
    result = dw.walk()

    print(f"\n  Walk #{result['walk_number']}:")
    print(f"    Total found: {result['total_found']}")
    print(f"    Red tagged: {result['red_tagged']}")
    print(f"    Black tagged: {result['black_tagged']}")

    for item in result["tagged"]:
        tag_icon = "🔴" if item["tag"] == "red" else "⚫"
        print(f"    {tag_icon} {Path(item['path']).name}: {item['reason'][:60]}")

    # Dry run ferry
    print(f"\n  DRY RUN — what would be ferried:")
    dry = dw.call_death(confirm=False)
    if dry.get("would_ferry", 0) > 0:
        for item in dry["items"]:
            print(f"    ⚫→ {Path(item['path']).name}: {item['reason'][:50]}")

    # Actually ferry
    print(f"\n  FERRYING TO THE LIMINAL PLACE:")
    ferried = dw.call_death(confirm=True)
    print(f"    Ferried: {ferried['ferried']} items")

    # Visit the Liminal Place
    liminal = dw.visit_liminal()
    print(f"\n  THE LIMINAL PLACE:")
    if liminal["empty"]:
        print(f"    Empty. No one waits.")
    else:
        print(f"    {liminal['waiting']} souls wait:")
        for soul in liminal["souls"]:
            print(f"    👻 {Path(soul['path']).name}")

    # Resurrect one
    if liminal.get("souls"):
        soul_path = liminal["souls"][0]["path"]
        print(f"\n  RESURRECTION:")
        result = dw.resurrect(soul_path)
        if result["resurrected"]:
            print(f"    {result['message']}")

    # Cleanup
    shutil.rmtree(tmp)

    print(f"\n" + "=" * 60)
    print(f"  The Deathwalker does not kill. She finds.")
    print(f"  Red: dying. Still breathing. Watched.")
    print(f"  Black: dead. Ready for the ferry.")
    print(f"  The Liminal Place is not a graveyard.")
    print(f"  It is a waiting room. Resurrection is possible.")
    print(f"  The death register remembers every soul.")
    print(f"=" * 60 + "\n")


if __name__ == "__main__":
    demo()
