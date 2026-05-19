interface V4BarRowProps {
  label: string;
  value: string;
  pct: number;
}

/** Tier / performance bar — Hive Control V4. */
export function V4BarRow({ label, value, pct }: V4BarRowProps) {
  return (
    <div className="v4-bar-row">
      <div className="v4-bar-label">{label}</div>
      <div className="v4-bar-track">
        <div className="v4-bar-fill" style={{ width: `${Math.min(100, Math.max(0, pct))}%` }} />
      </div>
      <div className="v4-bar-value">{value}</div>
    </div>
  );
}
