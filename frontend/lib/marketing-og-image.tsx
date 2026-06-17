import { ImageResponse } from "next/og";

/** 16:9 OG size aligned with Gumroad `cover.html` assets (M5). */
export const marketingOgSize = { width: 1200, height: 630 } as const;

export interface MarketingOgCoverInput {
  title: string;
  hook: string;
  kindLabel: string;
  priceLabel: string;
  badge?: string;
}

function truncate(value: string, max: number): string {
  const trimmed = value.trim();
  if (trimmed.length <= max) {
    return trimmed;
  }
  return `${trimmed.slice(0, max - 1).trim()}…`;
}

/** Render neon-dark hex cover matching `gumroad_cover_asset.py` / `cover.html`. */
export function marketingCoverImageResponse(input: MarketingOgCoverInput): ImageResponse {
  const title = truncate(input.title, 72);
  const hook = truncate(input.hook, 140);
  const kindLabel = truncate(input.kindLabel, 32);
  const priceLabel = truncate(input.priceLabel || "Launch pack", 28);
  const badge = truncate(input.badge ?? "SIMULATE-FIRST", 24);

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background:
            "radial-gradient(circle at 20% 10%, rgba(255, 184, 0, 0.25), transparent 28%), radial-gradient(circle at 80% 20%, rgba(0, 255, 255, 0.18), transparent 30%), linear-gradient(135deg, #050510 0%, #0B1028 100%)",
          fontFamily: "Inter, system-ui, sans-serif",
        }}
      >
        <div
          style={{
            width: 1080,
            height: 608,
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            padding: "56px 64px",
            border: "2px solid rgba(255, 184, 0, 0.45)",
            background: "rgba(5, 5, 16, 0.88)",
            boxShadow: "0 0 80px rgba(255, 184, 0, 0.22), inset 0 0 50px rgba(0, 255, 255, 0.08)",
            color: "#F8FAFC",
          }}
        >
          <div
            style={{
              display: "flex",
              alignSelf: "flex-start",
              color: "#050510",
              background: "#FFB800",
              borderRadius: 999,
              padding: "10px 18px",
              fontSize: 18,
              fontWeight: 700,
              letterSpacing: "0.08em",
            }}
          >
            {badge}
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
            <div
              style={{
                fontSize: 52,
                fontWeight: 700,
                lineHeight: 1.08,
                letterSpacing: "-0.02em",
              }}
            >
              {title}
            </div>
            <div
              style={{
                fontSize: 24,
                lineHeight: 1.35,
                color: "#B8C0D9",
                maxWidth: 920,
              }}
            >
              {hook}
            </div>
          </div>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              fontSize: 20,
              fontWeight: 600,
            }}
          >
            <span style={{ color: "#00FFFF" }}>{kindLabel}</span>
            <span style={{ color: "#00FF88" }}>{priceLabel}</span>
          </div>
        </div>
      </div>
    ),
    { ...marketingOgSize },
  );
}
