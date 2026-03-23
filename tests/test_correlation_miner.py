import sys

sys.path.insert(0, ".")

from runtime.engines.correlation_miner import CorrelationMiner


def test_detects_precursor_pattern():
    miner = CorrelationMiner()
    history = []
    for _ in range(10):
        history.extend(
            [
                {"event_type": "pressure_alert"},
                {"event_type": "moisture_alert"},
                {"event_type": "shear_alert"},
                {"event_type": "gaia_decision", "decision": "WARNING"},
            ]
        )
    proposals = miner.mine(history)
    assert proposals, proposals
    print("PASS: correlation miner detects precursor pattern")


def test_random_noise_finds_nothing():
    miner = CorrelationMiner()
    history = [
        {"event_type": "foo"},
        {"event_type": "bar"},
        {"event_type": "gaia_decision", "decision": "CLEAR"},
        {"event_type": "baz"},
    ]
    proposals = miner.mine(history)
    assert proposals == [], proposals
    print("PASS: correlation miner ignores noise")


if __name__ == "__main__":
    test_detects_precursor_pattern()
    test_random_noise_finds_nothing()
    print("ALL CORRELATION MINER TESTS PASSED")

