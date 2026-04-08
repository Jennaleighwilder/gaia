import { useEffect, useState } from "react";
import { fetchComplianceMatchRatio } from "../../api.js";

/**
 * Grant-level match share vs federal (documented match only) — same logic as GET /compliance/match-ratio.
 */
export function ComplianceCard() {
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const j = await fetchComplianceMatchRatio();
        if (!cancelled) setData(j);
      } catch (e) {
        if (!cancelled) setErr(String(e.message || e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (err) {
    return (
      <div className="compliance-card error">
        <h3>Match ratio</h3>
        <p className="track-hint">{err}</p>
      </div>
    );
  }
  if (!data) {
    return (
      <div className="compliance-card">
        <h3>Match ratio</h3>
        <p className="track-hint">Loading…</p>
      </div>
    );
  }

  const ok = data.compliant;
  const ratio = data.ratio_percent;

  return (
    <div className={`compliance-card ${ok ? "ok" : "warn"}`}>
      <h3>Match ratio (grant)</h3>
      <p className="compliance-stat">
        Federal total: <strong>${Number(data.federal_spend_total).toLocaleString()}</strong>
      </p>
      <p className="compliance-stat">
        Match (documented): <strong>${Number(data.match_documented_total).toLocaleString()}</strong>
      </p>
      <p className="compliance-stat">
        Match share:{" "}
        <strong>{ratio != null ? `${ratio.toFixed(2)}%` : "—"}</strong> (min{" "}
        {data.match_ratio_required_percent}%)
      </p>
      <p className={`compliance-badge ${ok ? "good" : "bad"}`}>{ok ? "Compliant" : "Below minimum"}</p>
    </div>
  );
}
