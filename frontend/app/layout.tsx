import type { ReactNode } from "react";
import { JetBrains_Mono } from "next/font/google";
import { cookies } from "next/headers";

import "./globals.css";
import { Providers } from "@/app/providers";
import { UI_LANG_COOKIE, coerceUiLanguage } from "@/lib/ui-language";

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  weight: ["400", "500"],
});

export const metadata = {
  title: "Queenswarm · Bee-Hive Neon Dashboard",
  description: "Decentralized agent swarms, verified simulations, pollen rewards.",
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  const cookieStore = await cookies();
  const lang = coerceUiLanguage(cookieStore.get(UI_LANG_COOKIE)?.value);
  return (
    <html lang={lang}>
      <body className={`${jetbrainsMono.variable} min-h-screen bg-hive-bg antialiased`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
