import type { ReactNode } from "react";

interface PublicLayoutProps {
  children: ReactNode;
}

export default function PublicLayout({ children }: PublicLayoutProps) {
  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4 py-12">
      <div aria-hidden className="hive-bg-pattern absolute inset-0 opacity-80" />
      <div aria-hidden className="absolute inset-x-0 top-0 h-[420px] bg-[radial-gradient(ellipse_at_50%_-20%,rgb(255_184_0/0.09),transparent_58%)]" />
      <div className="relative z-[1] w-full max-w-md">{children}</div>
    </div>
  );
}
