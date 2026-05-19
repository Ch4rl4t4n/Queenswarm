import { ImageResponse } from "next/og";

export const size = { width: 512, height: 512 };
export const contentType = "image/png";

/** Hex hive mark for favicon + PWA manifest. */
export default function Icon() {
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
            width: 360,
            height: 360,
            border: "8px solid #FFB800",
            background: "#0a0a1a",
            clipPath:
              "polygon(50% 0%, 93% 25%, 93% 75%, 50% 100%, 7% 75%, 7% 25%)",
            fontSize: 180,
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
