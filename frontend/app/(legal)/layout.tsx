import type { ReactNode } from "react";

/** Minimal layout for public legal pages (no dashboard chrome). */
export default function LegalLayout({ children }: { children: ReactNode }): JSX.Element {
  return (
    <div className="min-h-screen bg-[#07030f] text-[#fafafa]">
      {children}
    </div>
  );
}
