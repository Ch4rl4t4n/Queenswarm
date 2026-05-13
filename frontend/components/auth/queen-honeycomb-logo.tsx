/** 7-cell honeycomb: amber center with crown, six outline cells (pointy-top hexes). */

interface QueenHoneycombLogoProps {
  /** Square viewport in CSS pixels. */
  size?: number;
  className?: string;
  /** When set, marks decorative instances (sidebar). */
  "aria-hidden"?: boolean;
}

const VIEWBOX = 220;
const CX = 110;
const CY = 110;
const INNER_R = 38;
const OUTER_R = 38;
const OUTER_DIST = 66;

function hexPts(px: number, py: number, r: number): string {
  return Array.from({ length: 6 }, (_, i) => {
    const a = (Math.PI / 3) * i - Math.PI / 6;
    return `${(px + r * Math.cos(a)).toFixed(1)},${(py + r * Math.sin(a)).toFixed(1)}`;
  }).join(" ");
}

export function QueenHoneycombLogo({ size = 72, className, "aria-hidden": ariaHidden }: QueenHoneycombLogoProps): JSX.Element {
  const cx = CX;
  const cy = CY;
  const inner = INNER_R;
  const outer = OUTER_R;
  const dist = OUTER_DIST;

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
  const strokeW = 3.5;

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${VIEWBOX} ${VIEWBOX}`}
      overflow="visible"
      className={className}
      role={ariaHidden ? "presentation" : "img"}
      aria-label={ariaHidden ? undefined : "Queenswarm logo"}
      aria-hidden={ariaHidden ?? undefined}
      style={{ display: "block", overflow: "visible" }}
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
          strokeWidth={strokeW}
          strokeLinejoin="round"
        />
      ))}
    </svg>
  );
}
