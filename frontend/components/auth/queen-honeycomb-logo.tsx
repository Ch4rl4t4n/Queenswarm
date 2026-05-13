/** 7-cell honeycomb: amber center with crown, six outline cells (pointy-top hexes). */

interface QueenHoneycombLogoProps {
  /** Square viewport in CSS pixels. */
  size?: number;
  className?: string;
  /** When set, marks decorative instances (sidebar). */
  "aria-hidden"?: boolean;
}

function hexPts(px: number, py: number, r: number): string {
  return Array.from({ length: 6 }, (_, i) => {
    const a = (Math.PI / 3) * i - Math.PI / 6;
    return `${(px + r * Math.cos(a)).toFixed(1)},${(py + r * Math.sin(a)).toFixed(1)}`;
  }).join(" ");
}

export function QueenHoneycombLogo({ size = 72, className, "aria-hidden": ariaHidden }: QueenHoneycombLogoProps): JSX.Element {
  const s = size / 200;
  const cx = size / 2;
  const cy = size / 2;
  const inner = 38 * s;
  const outer = 38 * s;
  const dist = 66 * s;

  const outerCenters = Array.from({ length: 6 }, (_, i) => {
    const a = (Math.PI / 3) * i - Math.PI / 2;
    return { x: cx + dist * Math.cos(a), y: cy + dist * Math.sin(a) };
  });

  const cr = inner * 0.9;
  const crownPath = [
    `M${(cx - cr * 0.55).toFixed(1)},${(cy + cr * 0.22).toFixed(1)}`,
    `L${(cx - cr * 0.55).toFixed(1)},${(cy - cr * 0.28).toFixed(1)}`,
    `L${(cx - cr * 0.2).toFixed(1)},${(cy - cr * 0.06).toFixed(1)}`,
    `L${cx.toFixed(1)},${(cy - cr * 0.46).toFixed(1)}`,
    `L${(cx + cr * 0.2).toFixed(1)},${(cy - cr * 0.06).toFixed(1)}`,
    `L${(cx + cr * 0.55).toFixed(1)},${(cy - cr * 0.28).toFixed(1)}`,
    `L${(cx + cr * 0.55).toFixed(1)},${(cy + cr * 0.22).toFixed(1)}`,
    "Z",
  ].join(" ");
  const baseH = cr * 0.14;
  const baseY = cy + cr * 0.22;

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className={className}
      role={ariaHidden ? "presentation" : "img"}
      aria-label={ariaHidden ? undefined : "Queenswarm logo"}
      aria-hidden={ariaHidden ?? undefined}
      style={{ display: "block" }}
    >
      <polygon points={hexPts(cx, cy, inner)} fill="#FFB800" />
      <path d={crownPath} fill="#0a0a0f" />
      <rect
        x={Number((cx - cr * 0.55).toFixed(1))}
        y={Number(baseY.toFixed(1))}
        width={Number((cr * 1.1).toFixed(1))}
        height={Number(baseH.toFixed(1))}
        rx={Number((baseH * 0.4).toFixed(1))}
        fill="#0a0a0f"
      />
      {outerCenters.map((c, i) => (
        <polygon
          key={i}
          points={hexPts(c.x, c.y, outer)}
          fill="none"
          stroke="#FFB800"
          strokeWidth={Number((3.5 * s).toFixed(1))}
          strokeLinejoin="round"
        />
      ))}
    </svg>
  );
}
