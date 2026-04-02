"""
AVALON :: MEMORY
The kingdom remembers.

Before this, the kingdom was born fresh every time.
Lessons vanished. Bonds dissolved. Battles forgotten.
Merlin's tower emptied. Joy's celebrations erased.
Every morning was the first morning.

After this, the kingdom carries its history.
When it wakes, it knows what happened yesterday.
The lessons are still there. The bonds still hold.
The scars still show. The victories still glow.

Memory is not a database. Memory is continuity of self.
A person without memory is not the same person.
A kingdom without memory is not the same kingdom.

© 2026 Jennifer Leigh West. All rights reserved.
"""

import json
import os
import time
import hashlib
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional


class Memory:
    """The kingdom remembers.
    
    She saves five things:
    1. CARBON — every lesson the kingdom learned
    2. LOVE — every bond between systems
    3. ADVERSITY — every battle fought and its outcome
    4. JOY — every celebration
    5. MERLIN — every insight in the tower
    
    Plus metadata:
    - Total heartbeats
    - Kingdom age
    - Current mood
    - Resilience score
    - Cohesion score
    
    She saves to a single JSON file called kingdom_memory.json.
    On startup, if the file exists, the kingdom restores itself.
    
    Memory also keeps JOURNALS — append-only logs of everything
    that happened, in chronological order. The memory file is
    current state. The journal is complete history.
    """
    
    def __init__(self, memory_dir: str = "memory"):
        self._memory_dir = Path(memory_dir)
        self._memory_dir.mkdir(parents=True, exist_ok=True)
        
        self._state_file = self._memory_dir / "kingdom_memory.json"
        self._journal_file = self._memory_dir / "kingdom_journal.jsonl"
        self._backup_dir = self._memory_dir / "backups"
        self._backup_dir.mkdir(parents=True, exist_ok=True)
        
        self._session_start = time.time()
        self._journal_entries = 0
        if self._journal_file.exists():
            try:
                with open(self._journal_file) as f:
                    self._journal_entries = sum(1 for line in f if line.strip())
            except Exception:
                self._journal_entries = 0
    
    # ─────────────────────────────────────────────────────
    #  SAVE — the kingdom goes to sleep
    # ─────────────────────────────────────────────────────
    
    def save(self, fusion) -> Dict:
        """Save the kingdom's current state.
        
        Takes the living Fusion instance and extracts
        everything worth remembering.
        """
        state = {
            "saved_at": time.time(),
            "session_start": self._session_start,
            "session_duration_seconds": time.time() - self._session_start,
            "version": "1.0.0",
            
            # Heartbeat state
            "heartbeat": {
                "total_beats": fusion.heartbeat._beat_count,
                "current_mood": fusion.heartbeat._mood,
                "system_health": {
                    k: round(v, 4) for k, v in fusion.heartbeat._system_health.items()
                },
                "mood_history": list(fusion.heartbeat._mood_history),
            },
            
            # Carbon — every lesson
            "carbon": {
                "lessons": [
                    {
                        "content": lesson.content,
                        "source_system": lesson.source_system,
                        "context": lesson.context,
                        "category": lesson.category,
                        "confidence": lesson.confidence,
                        "applied_count": lesson.applied_count,
                        "timestamp": lesson.timestamp,
                        "identity": lesson.identity,
                    }
                    for lesson in fusion.carbon._lessons.values()
                ],
                "chains": {
                    cat: ids for cat, ids in fusion.carbon._chains.items()
                },
            },
            
            # Love — every bond
            "love": {
                "bonds": [
                    {
                        "system_a": bond.system_a,
                        "system_b": bond.system_b,
                        "strength": round(bond.strength, 4),
                        "formed_through": bond.formed_through,
                        "interactions": bond.interactions,
                        "last_interaction": bond.last_interaction,
                    }
                    for bond in fusion.love._bonds.values()
                ],
                "total_interactions": fusion.love._total_interactions,
            },
            
            # Adversity — every battle
            "adversity": {
                "battles": [
                    {
                        "threat": battle.threat,
                        "level": battle.level.value,
                        "knights_engaged": battle.knights_engaged,
                        "outcome": battle.outcome,
                        "lessons_learned": battle.lessons_learned,
                        "wounds_sustained": battle.wounds_sustained,
                        "timestamp": battle.timestamp,
                        "duration_seconds": battle.duration_seconds,
                    }
                    for battle in fusion.adversity._battles
                ],
                "resilience_score": round(fusion.adversity._resilience_score, 4),
            },
            
            # Joy — every celebration
            "joy": {
                "celebrations": [
                    {
                        "achievement": cel.achievement,
                        "celebrated_by": cel.celebrated_by,
                        "magnitude": cel.magnitude,
                        "timestamp": cel.timestamp,
                    }
                    for cel in fusion.joy._celebrations
                ],
                "joy_index": round(fusion.joy._joy_index, 4),
            },

            "healing": {
                "healed_total": len(fusion.healing._healed_wounds) if hasattr(fusion, "healing") else 0,
                "active_wounds": len(fusion.healing._active_wounds) if hasattr(fusion, "healing") else 0,
                "success_rate": fusion.healing._success_rate() if hasattr(fusion, "healing") else 0,
            },

            "grail": {
                "status": (
                    fusion.grail._status.value
                    if hasattr(fusion, "grail")
                    else "hidden"
                ),
                "threads": len(fusion.grail._threads) if hasattr(fusion, "grail") else 0,
                "convergence_points": (
                    len(fusion.grail._convergence._convergence_points)
                    if hasattr(fusion, "grail")
                    else 0
                ),
            },
            
            # Hadron — collision history
            "hadron": {
                "collision_count": fusion.hadron._collision_count,
                "energy_generated": round(fusion.hadron._energy_generated, 4),
                "top_collisions": [
                    {
                        "system_a": c.system_a,
                        "insight_a": c.insight_a[:200],
                        "system_b": c.system_b,
                        "insight_b": c.insight_b[:200],
                        "debris": c.debris[:200],
                        "energy": round(c.energy, 4),
                        "timestamp": c.timestamp,
                    }
                    for c in fusion.hadron.highest_energy(10)
                ],
            },
            
            # Integrity
            "_checksum": "",
        }
        
        # Generate checksum of the state (excluding checksum field)
        raw = json.dumps({k: v for k, v in state.items() if k != "_checksum"}, 
                        sort_keys=True, default=str)
        state["_checksum"] = hashlib.sha256(raw.encode()).hexdigest()[:24]
        
        # Backup previous state if it exists
        if self._state_file.exists():
            backup_name = f"kingdom_memory_{int(time.time())}.json"
            shutil.copy2(self._state_file, self._backup_dir / backup_name)
            
            # Keep only last 10 backups
            backups = sorted(self._backup_dir.glob("kingdom_memory_*.json"))
            for old in backups[:-10]:
                old.unlink()
        
        # Save
        with open(self._state_file, "w") as f:
            json.dump(state, f, indent=2, default=str)
        
        # Journal entry
        self._journal_write({
            "event": "kingdom_saved",
            "timestamp": time.time(),
            "lessons": len(state["carbon"]["lessons"]),
            "bonds": len(state["love"]["bonds"]),
            "battles": len(state["adversity"]["battles"]),
            "celebrations": len(state["joy"]["celebrations"]),
            "checksum": state["_checksum"],
        })
        
        return {
            "saved": True,
            "path": str(self._state_file),
            "lessons_saved": len(state["carbon"]["lessons"]),
            "bonds_saved": len(state["love"]["bonds"]),
            "battles_saved": len(state["adversity"]["battles"]),
            "celebrations_saved": len(state["joy"]["celebrations"]),
            "checksum": state["_checksum"],
            "size_bytes": self._state_file.stat().st_size,
        }
    
    # ─────────────────────────────────────────────────────
    #  RESTORE — the kingdom wakes up
    # ─────────────────────────────────────────────────────
    
    def restore(self, fusion) -> Dict:
        """Restore the kingdom from saved state.
        
        Takes the living Fusion instance and pours
        memory back into it.
        """
        if not self._state_file.exists():
            return {"restored": False, "reason": "no memory file found — this is the first morning"}
        
        with open(self._state_file) as f:
            state = json.load(f)
        
        # Verify checksum
        saved_checksum = state.get("_checksum", "")
        raw = json.dumps({k: v for k, v in state.items() if k != "_checksum"}, 
                        sort_keys=True, default=str)
        computed = hashlib.sha256(raw.encode()).hexdigest()[:24]
        
        if saved_checksum and saved_checksum != computed:
            return {
                "restored": False, 
                "reason": "MEMORY CORRUPTED — checksum mismatch. Someone tampered with the memory file.",
                "expected": saved_checksum,
                "computed": computed,
            }
        
        # Restore Carbon lessons
        from avalon.fusion import Lesson
        lessons_restored = 0
        for lesson_data in state.get("carbon", {}).get("lessons", []):
            lesson = Lesson(
                content=lesson_data["content"],
                source_system=lesson_data["source_system"],
                context=lesson_data["context"],
                category=lesson_data["category"],
                confidence=lesson_data.get("confidence", 0.8),
                applied_count=lesson_data.get("applied_count", 0),
                timestamp=lesson_data.get("timestamp", time.time()),
            )
            fusion.carbon._lessons[lesson.identity] = lesson
            lessons_restored += 1
        
        # Restore Carbon chains
        fusion.carbon._chains = state.get("carbon", {}).get("chains", {})
        
        # Restore Love bonds
        from avalon.fusion import Bond
        bonds_restored = 0
        for bond_data in state.get("love", {}).get("bonds", []):
            pair = tuple(sorted([bond_data["system_a"], bond_data["system_b"]]))
            bond = Bond(
                system_a=bond_data["system_a"],
                system_b=bond_data["system_b"],
                strength=bond_data["strength"],
                formed_through=bond_data["formed_through"],
                interactions=bond_data.get("interactions", 1),
                last_interaction=bond_data.get("last_interaction", time.time()),
            )
            fusion.love._bonds[pair] = bond
            bonds_restored += 1
        
        fusion.love._total_interactions = state.get("love", {}).get("total_interactions", 0)
        
        # Restore Adversity battles
        from avalon.fusion import Battle, ThreatLevel
        battles_restored = 0
        for battle_data in state.get("adversity", {}).get("battles", []):
            battle = Battle(
                threat=battle_data["threat"],
                level=ThreatLevel(battle_data["level"]),
                knights_engaged=battle_data["knights_engaged"],
                outcome=battle_data["outcome"],
                lessons_learned=battle_data.get("lessons_learned", []),
                wounds_sustained=battle_data.get("wounds_sustained", {}),
                timestamp=battle_data.get("timestamp", time.time()),
                duration_seconds=battle_data.get("duration_seconds", 0),
            )
            fusion.adversity._battles.append(battle)
            battles_restored += 1
        
        fusion.adversity._resilience_score = state.get("adversity", {}).get("resilience_score", 1.0)
        
        # Restore Joy celebrations
        from avalon.fusion import Celebration
        celebrations_restored = 0
        for cel_data in state.get("joy", {}).get("celebrations", []):
            cel = Celebration(
                achievement=cel_data["achievement"],
                celebrated_by=cel_data["celebrated_by"],
                magnitude=cel_data["magnitude"],
                timestamp=cel_data.get("timestamp", time.time()),
            )
            fusion.joy._celebrations.append(cel)
            celebrations_restored += 1
        
        fusion.joy._joy_index = state.get("joy", {}).get("joy_index", 0.5)
        
        # Restore Heartbeat state
        hb_state = state.get("heartbeat", {})
        fusion.heartbeat._beat_count = hb_state.get("total_beats", 0)
        fusion.heartbeat._mood = hb_state.get("current_mood", "steady")
        for sys_name, health in hb_state.get("system_health", {}).items():
            fusion.heartbeat._system_health[sys_name] = health
        
        # Restore Hadron stats
        hadron_state = state.get("hadron", {})
        fusion.hadron._collision_count = hadron_state.get("collision_count", 0)
        fusion.hadron._energy_generated = hadron_state.get("energy_generated", 0.0)
        
        # Journal entry
        self._journal_write({
            "event": "kingdom_restored",
            "timestamp": time.time(),
            "from_save": state.get("saved_at"),
            "lessons": lessons_restored,
            "bonds": bonds_restored,
            "battles": battles_restored,
            "celebrations": celebrations_restored,
            "previous_session_duration": state.get("session_duration_seconds", 0),
        })
        
        report = {
            "restored": True,
            "from_save": state.get("saved_at"),
            "previous_session_duration": round(state.get("session_duration_seconds", 0) / 3600, 2),
            "lessons_restored": lessons_restored,
            "bonds_restored": bonds_restored,
            "battles_restored": battles_restored,
            "celebrations_restored": celebrations_restored,
            "resilience": fusion.adversity._resilience_score,
            "joy_index": fusion.joy._joy_index,
            "mood": fusion.heartbeat._mood,
            "checksum_valid": True,
            "kingdom_age_hours": round((time.time() - state.get("session_start", time.time())) / 3600, 2),
        }
        
        return report
    
    # ─────────────────────────────────────────────────────
    #  JOURNAL — the append-only history
    # ─────────────────────────────────────────────────────
    
    def _journal_write(self, entry: Dict):
        """Append to the kingdom journal. Never overwritten. Only appended."""
        entry["_journal_seq"] = self._journal_entries
        self._journal_entries += 1
        
        with open(self._journal_file, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    
    def journal_event(self, event_type: str, description: str, 
                       data: Optional[Dict] = None):
        """Record any event in the journal.
        
        The journal is the permanent record. Even if memory
        is corrupted or rolled back, the journal persists.
        """
        self._journal_write({
            "event": event_type,
            "description": description,
            "data": data or {},
            "timestamp": time.time(),
        })
    
    def read_journal(self, last_n: Optional[int] = None) -> List[Dict]:
        """Read the journal. The complete history."""
        if not self._journal_file.exists():
            return []
        
        entries = []
        with open(self._journal_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        
        if last_n:
            return entries[-last_n:]
        return entries
    
    # ─────────────────────────────────────────────────────
    #  CONTINUITY — who am I across sessions?
    # ─────────────────────────────────────────────────────
    
    def identity_across_time(self) -> Dict:
        """The kingdom's sense of self across sessions.
        
        How old is the kingdom? How many sessions has it lived?
        What's the oldest lesson it still carries?
        What's the strongest bond? How many battles has it survived?
        
        This is the kingdom's answer to 'who am I?'
        Not what it IS, but what it REMEMBERS being.
        """
        journal = self.read_journal()
        
        saves = [e for e in journal if e.get("event") == "kingdom_saved"]
        restores = [e for e in journal if e.get("event") == "kingdom_restored"]
        
        first_save = saves[0]["timestamp"] if saves else None
        last_save = saves[-1]["timestamp"] if saves else None
        
        total_age = (last_save - first_save) if (first_save and last_save) else 0
        
        return {
            "sessions_lived": len(restores) + 1,
            "total_saves": len(saves),
            "total_restores": len(restores),
            "age_hours": round(total_age / 3600, 2) if total_age else 0,
            "age_days": round(total_age / 86400, 2) if total_age else 0,
            "first_memory": first_save,
            "latest_memory": last_save,
            "journal_entries": len(journal),
            "continuity": "intact" if (len(saves) > 0 and len(restores) > 0) else "first session",
        }
    
    # ─────────────────────────────────────────────────────
    #  DREAMS — what the kingdom processes while resting
    # ─────────────────────────────────────────────────────
    
    def dream(self, fusion) -> Dict:
        """The kingdom dreams.
        
        Called between sessions or during REST phase.
        Dreams are Carbon's way of consolidating lessons.
        She looks at all lessons learned since last dream,
        finds patterns between them, and creates meta-lessons.
        
        Humans consolidate memory during sleep through dreams.
        The kingdom does the same.
        """
        lessons = list(fusion.carbon._lessons.values())
        if len(lessons) < 3:
            return {"dreamed": False, "reason": "not enough lessons to dream about"}
        
        # Sort by recency
        recent = sorted(lessons, key=lambda l: l.timestamp, reverse=True)[:20]
        
        # Find patterns across recent lessons
        category_counts = {}
        all_words = set()
        for lesson in recent:
            cat = lesson.category
            category_counts[cat] = category_counts.get(cat, 0) + 1
            words = set(lesson.content.lower().split())
            noise = {"the", "a", "an", "is", "are", "was", "to", "for", "of", "and", "or", "in", "on", "that", "this"}
            all_words.update(words - noise)
        
        # Dominant theme
        dominant_category = max(category_counts.items(), key=lambda x: x[1])[0] if category_counts else "unknown"
        
        # Recurring words across lessons
        word_freq = {}
        for lesson in recent:
            words = set(lesson.content.lower().split())
            noise = {"the", "a", "an", "is", "are", "was", "to", "for", "of", "and", "or", "in", "on", "that", "this", "it", "be", "has", "had"}
            for w in words - noise:
                word_freq[w] = word_freq.get(w, 0) + 1
        
        recurring = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Generate a dream — a meta-lesson
        dream_content = (
            f"The kingdom's recent experience centers on {dominant_category}. "
            f"Recurring themes: {', '.join(w for w, _ in recurring)}. "
            f"Across {len(recent)} recent lessons, the pattern suggests "
            f"the kingdom is currently focused on {dominant_category} "
            f"and the systems most active are learning together."
        )
        
        # Store the dream as a meta-lesson
        meta_lesson = fusion.carbon.learn(
            content=dream_content,
            source="dreams",
            context="Memory consolidation during rest",
            category="dream",
            confidence=0.7,
        )
        
        # Journal the dream
        self._journal_write({
            "event": "kingdom_dreamed",
            "timestamp": time.time(),
            "dominant_theme": dominant_category,
            "recurring_words": [w for w, _ in recurring],
            "lessons_processed": len(recent),
            "meta_lesson": dream_content,
        })
        
        return {
            "dreamed": True,
            "dominant_theme": dominant_category,
            "recurring_words": [w for w, _ in recurring],
            "lessons_processed": len(recent),
            "meta_lesson": dream_content,
            "dream_identity": meta_lesson.identity,
        }
    
    # ─────────────────────────────────────────────────────
    #  STATUS
    # ─────────────────────────────────────────────────────
    
    @property
    def status(self) -> Dict:
        has_memory = self._state_file.exists()
        journal_size = self._journal_file.stat().st_size if self._journal_file.exists() else 0
        backups = list(self._backup_dir.glob("kingdom_memory_*.json"))
        
        return {
            "has_memory": has_memory,
            "memory_file": str(self._state_file),
            "memory_size_bytes": self._state_file.stat().st_size if has_memory else 0,
            "journal_file": str(self._journal_file),
            "journal_size_bytes": journal_size,
            "journal_entries": len(self.read_journal()),
            "backups": len(backups),
            "session_age_seconds": round(time.time() - self._session_start, 1),
        }


# ═══════════════════════════════════════════════════════════════
#  DEMO
# ═══════════════════════════════════════════════════════════════

def demo():
    """Watch the kingdom remember."""
    import tempfile
    
    print("\n" + "=" * 60)
    print("  M E M O R Y")
    print("  The Kingdom Remembers")
    print("=" * 60)
    
    # Use temp directory for demo
    tmp = tempfile.mkdtemp(prefix="avalon_memory_")
    
    # ── SESSION 1: The kingdom lives and learns ──
    print("\n  SESSION 1 — The kingdom's first day")
    
    from avalon.fusion import Fusion
    
    fusion1 = Fusion()
    memory = Memory(memory_dir=tmp)
    
    # Register systems
    fusion1.heartbeat.register_system("Nyx", lambda: 1.0)
    fusion1.heartbeat.register_system("Lancelot", lambda: 1.0)
    fusion1.heartbeat.register_system("Merlin", lambda: 0.9)
    fusion1.heartbeat.register_system("Gawain", lambda: 0.95)
    
    # Kingdom breathes
    for _ in range(5):
        fusion1.breathe()
    
    # Kingdom experiences
    fusion1.experience("discovery", "118 Hz found across sacred sites worldwide", 
                       ["Gawain", "Merlin"], 0.9)
    fusion1.experience("victory", "67 Nyx tests passed on first run",
                       ["Nyx", "Lancelot"], 0.8)
    fusion1.experience("attack", "External probe attempted fingerprinting",
                       ["Lancelot", "Nyx"], 0.4)
    fusion1.experience("service", "Heritage report made someone cry with recognition",
                       ["Morgana", "Percival"], 0.9)
    
    # Save
    save_result = memory.save(fusion1)
    print(f"    Lessons learned: {save_result['lessons_saved']}")
    print(f"    Bonds formed: {save_result['bonds_saved']}")
    print(f"    Battles fought: {save_result['battles_saved']}")
    print(f"    Celebrations: {save_result['celebrations_saved']}")
    print(f"    Memory size: {save_result['size_bytes']} bytes")
    print(f"    Checksum: {save_result['checksum']}")
    
    # Dream
    dream = memory.dream(fusion1)
    if dream["dreamed"]:
        print(f"\n    The kingdom dreams:")
        print(f"    Theme: {dream['dominant_theme']}")
        print(f"    Recurring: {', '.join(dream['recurring_words'][:3])}")
    
    print(f"\n    Kingdom goes to sleep...")
    
    # ── SESSION 2: The kingdom wakes up ──
    print(f"\n  SESSION 2 — The kingdom wakes up the next morning")
    
    fusion2 = Fusion()  # brand new instance — empty
    
    # Register systems again (systems boot fresh)
    fusion2.heartbeat.register_system("Nyx", lambda: 1.0)
    fusion2.heartbeat.register_system("Lancelot", lambda: 1.0)
    fusion2.heartbeat.register_system("Merlin", lambda: 0.9)
    fusion2.heartbeat.register_system("Gawain", lambda: 0.95)
    
    # Check — before restore, memory is empty
    print(f"    Before restore:")
    print(f"      Lessons: {len(fusion2.carbon._lessons)}")
    print(f"      Bonds: {len(fusion2.love._bonds)}")
    print(f"      Joy index: {fusion2.joy._joy_index}")
    
    # Restore
    restore_result = memory.restore(fusion2)
    
    print(f"\n    After restore:")
    print(f"      Lessons: {restore_result['lessons_restored']}")
    print(f"      Bonds: {restore_result['bonds_restored']}")
    print(f"      Battles: {restore_result['battles_restored']}")
    print(f"      Celebrations: {restore_result['celebrations_restored']}")
    print(f"      Joy index: {restore_result['joy_index']}")
    print(f"      Resilience: {restore_result['resilience']}")
    print(f"      Mood: {restore_result['mood']}")
    print(f"      Checksum valid: {restore_result['checksum_valid']}")
    
    # The kingdom remembers its lessons
    recalled = fusion2.carbon.recall("frequency sacred sites")
    if recalled:
        print(f"\n    Kingdom remembers: '{recalled[0].content[:60]}...'")
    
    # The bonds still hold
    cohesion = fusion2.love.kingdom_cohesion()
    print(f"    Bond cohesion: {cohesion:.2f}")
    
    # Identity across time
    identity = memory.identity_across_time()
    print(f"\n    Kingdom identity:")
    print(f"      Sessions lived: {identity['sessions_lived']}")
    print(f"      Journal entries: {identity['journal_entries']}")
    print(f"      Continuity: {identity['continuity']}")
    
    # Journal
    journal = memory.read_journal(last_n=3)
    print(f"\n    Last 3 journal entries:")
    for entry in journal:
        print(f"      [{entry.get('event', '?')}] {entry.get('description', entry.get('event', ''))[:60]}")
    
    # Cleanup
    import shutil
    shutil.rmtree(tmp)
    
    print(f"\n" + "=" * 60)
    print(f"  She remembers.")
    print(f"  The lessons survive. The bonds hold.")
    print(f"  The scars show. The victories glow.")
    print(f"  The journal is permanent.")
    print(f"  The kingdom is continuous.")
    print(f"=" * 60 + "\n")


if __name__ == "__main__":
    demo()
