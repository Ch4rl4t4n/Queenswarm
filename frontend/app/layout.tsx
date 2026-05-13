import type { ReactNode } from "react";
import { JetBrains_Mono } from "next/font/google";

import "./globals.css";
import { Providers } from "@/app/providers";

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  weight: ["400", "500"],
});

export const metadata = {
  title: "Queenswarm · Bee-Hive Neon Dashboard",
  description: "Decentralized agent swarms, verified simulations, pollen rewards.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className={`${jetbrainsMono.variable} min-h-screen bg-hive-bg antialiased`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
