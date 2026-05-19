/** Static Queen-centric constellation — Hive Control V4 design reference. */
export function HiveMindConstellationGraph(): JSX.Element {
  const edges: [number, number, number, number][] = [
    [200, 120, 80, 60],
    [200, 120, 320, 60],
    [200, 120, 80, 180],
    [200, 120, 320, 180],
    [200, 120, 140, 200],
    [200, 120, 260, 200],
    [80, 60, 140, 200],
    [320, 60, 260, 200],
    [80, 60, 60, 130],
    [320, 60, 340, 130],
  ];

  const satellites: [number, number, string][] = [
    [80, 60, "S"],
    [320, 60, "E"],
    [80, 180, "A"],
    [320, 180, "M"],
    [140, 200, "R"],
    [260, 200, "D"],
    [60, 130, "P"],
    [340, 130, "O"],
  ];

  return (
    <svg viewBox="0 0 400 240" className="v4-hivemind-svg" aria-hidden>
      <defs>
        <radialGradient id="hm-node-glow">
          <stop offset="0%" stopColor="#FDB927" stopOpacity="0.4" />
          <stop offset="100%" stopColor="#FDB927" stopOpacity="0" />
        </radialGradient>
      </defs>
      {edges.map((coords, index) => (
        <line
          key={`edge-${index}`}
          x1={coords[0]}
          y1={coords[1]}
          x2={coords[2]}
          y2={coords[3]}
          stroke="rgba(126,63,190,0.45)"
          strokeWidth="1"
        />
      ))}
      <circle cx="200" cy="120" r="32" fill="url(#hm-node-glow)" />
      <circle cx="200" cy="120" r="14" fill="#FDB927" stroke="#FFD24D" strokeWidth="2" />
      <text x="200" y="124" textAnchor="middle" fontSize="9" fill="#1A0E2E" fontWeight="700">
        Q
      </text>
      {satellites.map(([cx, cy, label]) => (
        <g key={`node-${label}`}>
          <circle cx={cx} cy={cy} r="9" fill="rgba(126,63,190,0.4)" stroke="#7E3FBE" strokeWidth="1.5" />
          <text x={cx} y={cy + 3} textAnchor="middle" fontSize="8" fill="#F5F1FF" fontWeight="600">
            {label}
          </text>
        </g>
      ))}
    </svg>
  );
}
