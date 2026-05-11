import type { ReactNode } from "react";
import "./globals.css";

export const metadata = {
  title: "Queenswarm",
  description: "Bee-hive cognitive OS — queenswarm.love",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="hive-body">{children}</body>
    </html>
  );
}
