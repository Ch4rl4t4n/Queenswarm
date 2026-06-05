import { LacIcon } from "@/components/marketing/lac-icons";
import type { MarketingProductView } from "@/lib/marketing-catalog-view";

interface CoverArtProps {
  readonly product: MarketingProductView;
  readonly className?: string;
}

export function CoverArt({ product, className = "mk-card-cover" }: CoverArtProps): JSX.Element {
  const isSkill = product.type === "skill";
  const glyph = isSkill ? "hexagon" : "doc";
  const hue = isSkill ? "295" : "195";
  const seed = product.slug.length * 47 % 60;

  return (
    <div
      className={className}
      style={{
        background: `radial-gradient(ellipse 120% 90% at ${30 + seed}% 20%, oklch(0.42 0.18 ${hue} / 0.55), transparent 60%), radial-gradient(ellipse 90% 80% at 80% 90%, oklch(0.4 0.14 ${isSkill ? "330" : "160"} / 0.4), transparent 55%), linear-gradient(160deg, #0d1230, #0a0e23)`,
      }}
    >
      <svg
        width="100%"
        height="100%"
        viewBox="0 0 200 132"
        preserveAspectRatio="xMidYMid slice"
        style={{ position: "absolute", inset: 0, opacity: 0.5 }}
        aria-hidden
      >
        <defs>
          <pattern id={`grid-${product.slug}`} width="22" height="22" patternUnits="userSpaceOnUse">
            <path d="M22 0H0V22" fill="none" stroke="oklch(0.7 0.1 280 / 0.12)" strokeWidth="1" />
          </pattern>
        </defs>
        <rect width="200" height="132" fill={`url(#grid-${product.slug})`} />
      </svg>
      <div className="cover-glyph" style={{ position: "relative", color: `oklch(0.85 0.12 ${hue})` }}>
        <LacIcon name={glyph} size={46} />
      </div>
    </div>
  );
}
