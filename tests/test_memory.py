"""
MEMORY Test Suite
The kingdom remembers.
"""

import json
import os
import shutil
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from avalon.memory import Memory
from avalon.fusion import Fusion


@pytest.fixture
def tmp_memory():
    tmp = tempfile.mkdtemp(prefix="test_memory_")
    yield tmp
    shutil.rmtree(tmp)


@pytest.fixture
def living_kingdom(tmp_memory):
    fusion = Fusion()
    fusion.heartbeat.register_system("Nyx", lambda: 1.0)
    fusion.heartbeat.register_system("Lancelot", lambda: 1.0)
    for _ in range(3):
        fusion.breathe()
    fusion.experience("discovery", "test pattern found", ["Merlin", "Gawain"])
    fusion.experience("victory", "tests passed", ["Nyx", "Lancelot"], 0.8)
    fusion.experience("attack", "probe detected", ["Lancelot"], 0.3)
    memory = Memory(memory_dir=tmp_memory)
    return fusion, memory


class TestSave:
    def test_save_creates_file(self, living_kingdom):
        fusion, memory = living_kingdom
        result = memory.save(fusion)
        assert result["saved"]
        assert os.path.exists(result["path"])

    def test_save_captures_lessons(self, living_kingdom):
        fusion, memory = living_kingdom
        result = memory.save(fusion)
        assert result["lessons_saved"] >= 2

    def test_save_captures_bonds(self, living_kingdom):
        fusion, memory = living_kingdom
        result = memory.save(fusion)
        assert result["bonds_saved"] >= 1

    def test_save_has_checksum(self, living_kingdom):
        fusion, memory = living_kingdom
        result = memory.save(fusion)
        assert len(result["checksum"]) == 24

    def test_save_creates_backup_on_second_save(self, living_kingdom):
        fusion, memory = living_kingdom
        memory.save(fusion)
        fusion.experience("discovery", "second lesson", ["Merlin"])
        memory.save(fusion)
        backups = list(memory._backup_dir.glob("kingdom_memory_*.json"))
        assert len(backups) >= 1


class TestRestore:
    def test_restore_from_nothing(self, tmp_memory):
        fusion = Fusion()
        memory = Memory(memory_dir=tmp_memory)
        result = memory.restore(fusion)
        assert not result["restored"]
        assert "first morning" in result["reason"]

    def test_restore_brings_back_lessons(self, living_kingdom):
        fusion1, memory = living_kingdom
        memory.save(fusion1)

        fusion2 = Fusion()
        result = memory.restore(fusion2)
        assert result["restored"]
        assert result["lessons_restored"] >= 2
        assert len(fusion2.carbon._lessons) >= 2

    def test_restore_brings_back_bonds(self, living_kingdom):
        fusion1, memory = living_kingdom
        memory.save(fusion1)

        fusion2 = Fusion()
        result = memory.restore(fusion2)
        assert result["bonds_restored"] >= 1
        assert fusion2.love.kingdom_cohesion() > 0

    def test_restore_brings_back_joy(self, living_kingdom):
        fusion1, memory = living_kingdom
        memory.save(fusion1)

        fusion2 = Fusion()
        result = memory.restore(fusion2)
        assert result["joy_index"] > 0.5

    def test_restore_brings_back_resilience(self, living_kingdom):
        fusion1, memory = living_kingdom
        memory.save(fusion1)

        fusion2 = Fusion()
        result = memory.restore(fusion2)
        assert result["resilience"] > 0

    def test_corrupted_memory_detected(self, living_kingdom):
        fusion1, memory = living_kingdom
        memory.save(fusion1)

        with open(memory._state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["carbon"]["lessons"].append(
            {
                "content": "INJECTED",
                "source_system": "attacker",
                "context": "hack",
                "category": "attack",
                "confidence": 0,
                "applied_count": 0,
                "timestamp": 0,
                "identity": "fake",
            }
        )
        with open(memory._state_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        fusion2 = Fusion()
        result = memory.restore(fusion2)
        assert not result["restored"]
        assert "CORRUPTED" in result["reason"]

    def test_recall_works_after_restore(self, living_kingdom):
        fusion1, memory = living_kingdom
        memory.save(fusion1)

        fusion2 = Fusion()
        memory.restore(fusion2)
        recalled = fusion2.carbon.recall("pattern found")
        assert len(recalled) >= 1


class TestDream:
    def test_dream_creates_meta_lesson(self, living_kingdom):
        fusion, memory = living_kingdom
        fusion.experience("discovery", "frequency convergence detected", ["Gawain"])
        fusion.experience("discovery", "cross domain pattern transfer", ["Dagonet"])

        result = memory.dream(fusion)
        assert result["dreamed"]
        assert result["dominant_theme"]
        assert len(result["recurring_words"]) > 0

    def test_dream_needs_minimum_lessons(self, tmp_memory):
        fusion = Fusion()
        memory = Memory(memory_dir=tmp_memory)
        result = memory.dream(fusion)
        assert not result["dreamed"]


class TestJournal:
    def test_journal_records_save(self, living_kingdom):
        fusion, memory = living_kingdom
        memory.save(fusion)
        journal = memory.read_journal()
        events = [e["event"] for e in journal]
        assert "kingdom_saved" in events

    def test_journal_records_restore(self, living_kingdom):
        fusion1, memory = living_kingdom
        memory.save(fusion1)
        fusion2 = Fusion()
        memory.restore(fusion2)
        journal = memory.read_journal()
        events = [e["event"] for e in journal]
        assert "kingdom_restored" in events

    def test_journal_records_dream(self, living_kingdom):
        fusion, memory = living_kingdom
        fusion.experience("discovery", "extra lesson one", ["Merlin"])
        fusion.experience("discovery", "extra lesson two", ["Gawain"])
        memory.dream(fusion)
        journal = memory.read_journal()
        events = [e["event"] for e in journal]
        assert "kingdom_dreamed" in events

    def test_journal_is_append_only(self, living_kingdom):
        fusion, memory = living_kingdom
        memory.save(fusion)
        count1 = len(memory.read_journal())
        memory.save(fusion)
        count2 = len(memory.read_journal())
        assert count2 > count1

    def test_custom_journal_event(self, living_kingdom):
        fusion, memory = living_kingdom
        memory.journal_event("custom", "something special happened", {"detail": "test"})
        journal = memory.read_journal()
        customs = [e for e in journal if e["event"] == "custom"]
        assert len(customs) == 1


class TestIdentity:
    def test_identity_first_session(self, living_kingdom):
        _, memory = living_kingdom
        identity = memory.identity_across_time()
        assert identity["continuity"] == "first session"

    def test_identity_after_save_restore(self, living_kingdom):
        fusion1, memory = living_kingdom
        memory.save(fusion1)
        fusion2 = Fusion()
        memory.restore(fusion2)
        identity = memory.identity_across_time()
        assert identity["sessions_lived"] >= 2
        assert identity["continuity"] == "intact"


class TestStatus:
    def test_status_before_save(self, tmp_memory):
        memory = Memory(memory_dir=tmp_memory)
        status = memory.status
        assert not status["has_memory"]

    def test_status_after_save(self, living_kingdom):
        fusion, memory = living_kingdom
        memory.save(fusion)
        status = memory.status
        assert status["has_memory"]
        assert status["memory_size_bytes"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
