import { ImageResponse } from "next/og";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

/** Apple touch icon — same hive mark, smaller canvas. */
export default function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#050510",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: 140,
            height: 140,
            border: "6px solid #FFB800",
            background: "#0a0a1a",
            clipPath:
              "polygon(50% 0%, 93% 25%, 93% 75%, 50% 100%, 7% 75%, 7% 25%)",
            fontSize: 72,
            fontWeight: 900,
            color: "#FFB800",
          }}
        >
          Q
        </div>
      </div>
    ),
    { ...size },
  );
}
