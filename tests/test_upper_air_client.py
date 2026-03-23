import sys

sys.path.insert(0, ".")

from runtime.ingest.upper_air_client import UpperAirClient


def test_parse_legacy_ruc_text():
    client = UpperAirClient()
    raw = """
72403 ABQ 2026032200
1000 110 19.0 15.0 180 12
925 770 14.0 10.0 195 18
850 1520 8.0 3.0 210 25
700 3090 -4.0 -10.0 230 40
500 5700 -18.0 -26.0 245 55
"""
    df = client._parse_legacy_ruc_text(raw)
    assert len(df) == 5, df
    assert "u_wind" in df.columns and "v_wind" in df.columns, df.columns
    print("PASS: legacy RAP text parser")


def test_model_failure_returns_structured_error():
    class BrokenModelClient(UpperAirClient):
        def _request_model_text(self, station: str, valid_time):
            raise RuntimeError("legacy endpoint unavailable")

    client = BrokenModelClient()
    result = client.get_latest_model_sounding("KTRI", publish=False)
    assert result["source"] == "legacy_ruc_model", result
    assert result["station"] == "KTRI", result
    assert "error" in result and "legacy endpoint unavailable" in result["error"], result
    print("PASS: model failure is structured")


if __name__ == "__main__":
    test_parse_legacy_ruc_text()
    test_model_failure_returns_structured_error()
    print("ALL UPPER AIR CLIENT TESTS PASSED")
