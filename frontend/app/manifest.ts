import type { MetadataRoute } from "next";

/** Web app manifest — mobile/tablet install + theme (desktop unchanged). */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Queenswarm Hive",
    short_name: "Queenswarm",
    description: "Decentralized agent swarms, verified simulations, pollen rewards.",
    start_url: "/",
    display: "standalone",
    background_color: "#050510",
    theme_color: "#07030f",
    orientation: "any",
    icons: [
      {
        src: "/icon",
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/apple-icon",
        sizes: "180x180",
        type: "image/png",
        purpose: "any",
      },
    ],
  };
}
