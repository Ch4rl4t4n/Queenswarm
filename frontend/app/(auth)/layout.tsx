import type { ReactNode } from "react";

import { AuthHexBackground } from "@/components/auth/auth-hex-background";

/**
 * Auth route group — full-bleed hive void with no dashboard nav, sidebar, or HiveNav top bar.
 */

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="relative isolate min-h-screen w-full overflow-hidden bg-hive-bg text-[#fafafa]">
      <AuthHexBackground />
      <div className="relative z-10 flex min-h-screen flex-col items-center justify-center px-4 py-12">
        {children}
      </div>
    </div>
  );
}
