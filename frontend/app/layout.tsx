import type { ReactNode } from "react";
import { JetBrains_Mono, Space_Grotesk } from "next/font/google";

import "./globals.css";
import { HiveShell } from "@/components/hive/hive-shell";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  weight: ["500", "700"],
});

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
      <body className={`${spaceGrotesk.variable} ${jetbrainsMono.variable} min-h-screen antialiased bg-hive-bg`}>
        <HiveShell>{children}</HiveShell>
      </body>
    </html>
  );
}
