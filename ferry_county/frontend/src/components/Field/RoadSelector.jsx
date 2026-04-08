export function RoadSelector({ roads, value, onChange, disabled }) {
  return (
    <label className="field-label">
      Road
      <select
        className="field-input"
        value={value ?? ""}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
      >
        <option value="">— select —</option>
        {(roads || []).map((r) => (
          <option key={r.id} value={r.id}>
            {r.road_name}
            {r.road_number ? ` (#${r.road_number})` : ""} · {r.source_feature_id?.slice(0, 12)}…
          </option>
        ))}
      </select>
    </label>
  );
}
