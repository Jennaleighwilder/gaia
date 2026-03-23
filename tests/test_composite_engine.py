import sys

sys.path.insert(0, ".")

from runtime.engines.composite_engine import CompositeEngine


ENGINE = CompositeEngine()


def test_stable_profile():
    result = ENGINE.score(
        {
            "sbcape_jkg": 0.0,
            "significant_tornado_parameter": 0.0,
            "supercell_composite": 0.0,
            "energy_helicity_index_0_1km": 0.0,
            "lcl_height_agl_m": 2232,
            "bulk_shear_0_6km_kts": 34.0,
            "srh_0_1km_m2s2": 20.9,
        }
    )
    assert result["score"] < 0.2, result
    print(f"PASS: stable profile scores {result['score']}")


def test_tornado_environment():
    result = ENGINE.score(
        {
            "sbcape_jkg": 2500,
            "significant_tornado_parameter": 3.5,
            "supercell_composite": 8.0,
            "energy_helicity_index_0_1km": 2.5,
            "lcl_height_agl_m": 800,
            "bulk_shear_0_6km_kts": 45,
            "srh_0_1km_m2s2": 250,
        }
    )
    assert result["score"] > 0.7, result
    print(f"PASS: tornado environment scores {result['score']}")


def test_elevated_but_not_severe():
    result = ENGINE.score(
        {
            "sbcape_jkg": 3000,
            "significant_tornado_parameter": 0.3,
            "supercell_composite": 0.8,
            "energy_helicity_index_0_1km": 0.4,
            "lcl_height_agl_m": 2000,
            "bulk_shear_0_6km_kts": 15,
            "srh_0_1km_m2s2": 30,
        }
    )
    assert result["score"] < 0.4, result
    print(f"PASS: elevated but not severe scores {result['score']}")


def test_no_upper_air():
    result = ENGINE.score({})
    assert result["score"] == 0.0, result
    result = ENGINE.score(None)
    assert result["score"] == 0.0, result
    print("PASS: no data returns 0.0 gracefully")


if __name__ == "__main__":
    test_stable_profile()
    test_tornado_environment()
    test_elevated_but_not_severe()
    test_no_upper_air()
    print("ALL COMPOSITE ENGINE TESTS PASSED")
