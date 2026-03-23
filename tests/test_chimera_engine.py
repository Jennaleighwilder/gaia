import os
import sys
import tempfile

sys.path.insert(0, ".")

from runtime.engines.chimera_engine import ChimeraCoreEngine


def test_known_capability():
    engine = ChimeraCoreEngine(output_dir=tempfile.gettempdir(), quiet=True)
    result = engine.execute_capability("basic_stats", [1, 2, 3, 4])
    assert result["success"] is True, result
    assert "average" in result["result"], result
    print("PASS: chimera known capability")


def test_unknown_capability_generation_and_persistence():
    with tempfile.TemporaryDirectory() as tmp:
        engine = ChimeraCoreEngine(output_dir=tmp, quiet=True)
        generated = engine.generate_capability("analyze_ice_storm_signature", "Analyze ice storm weather signatures")
        assert generated["success"] is True, generated
        state_path = engine.save_state(os.path.join(tmp, "chimera_state.json"))
        restored = ChimeraCoreEngine(output_dir=tmp, quiet=True)
        assert restored.load_state(state_path) is True
        result = restored.execute_capability("analyze_ice_storm_signature", {"dewpoint_f": 31, "temp_f": 30})
        assert result["success"] is True, result
        print("PASS: chimera unknown capability generation and persistence")


if __name__ == "__main__":
    test_known_capability()
    test_unknown_capability_generation_and_persistence()
    print("ALL CHIMERA TESTS PASSED")

