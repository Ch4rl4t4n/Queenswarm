import type { ReactNode } from "react";
import type { Viewport } from "next";
import { JetBrains_Mono, Poppins, Space_Grotesk } from "next/font/google";
import { cookies } from "next/headers";

import "./globals.css";
import { Providers } from "@/app/providers";
import { UI_LANG_COOKIE, coerceUiLanguage } from "@/lib/ui-language";

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  weight: ["400", "500"],
});

/** Display typeface — headings, section titles, numeric callouts (Bee-Hive Neon-Dark). */
const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

/** Body / UI typeface — referenced across components as `--font-poppins`. */
const poppins = Poppins({
  subsets: ["latin"],
  variable: "--font-poppins",
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

export const metadata = {
  title: "Queenswarm · Bee-Hive Neon Dashboard",
  description: "Decentralized agent swarms, verified simulations, pollen rewards.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#07030f",
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  const cookieStore = await cookies();
  const lang = coerceUiLanguage(cookieStore.get(UI_LANG_COOKIE)?.value);
  return (
    <html lang={lang}>
      <body
        className={`${spaceGrotesk.variable} ${poppins.variable} ${jetbrainsMono.variable} min-h-screen bg-hive-bg antialiased`}
      >
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
