import { LacIcon } from "@/components/marketing/lac-icons";
import type { MarketingProductView } from "@/lib/marketing-catalog-view";

interface CoverArtProps {
  readonly product: MarketingProductView;
  readonly className?: string;
}

export function CoverArt({ product, className = "mk-card-cover" }: CoverArtProps): JSX.Element {
  const isSkill = product.type === "skill";
  const glyph = isSkill ? "shield" : "doc";
  const hue = isSkill ? "295" : "195";
  const seed = product.slug.length * 47 % 60;

  return (
    <div
      className={className}
      style={{
        background: `radial-gradient(ellipse 120% 90% at ${30 + seed}% 20%, oklch(0.42 0.18 ${hue} / 0.55), transparent 60%), radial-gradient(ellipse 90% 80% at 80% 90%, oklch(0.4 0.14 ${isSkill ? "330" : "160"} / 0.4), transparent 55%), linear-gradient(160deg, #0d1230, #0a0e23)`,
      }}
    >
      <div className="cover-glyph" style={{ position: "relative", color: `oklch(0.85 0.12 ${hue})` }}>
        <LacIcon name={glyph} size={46} />
      </div>
    </div>
  );
}
