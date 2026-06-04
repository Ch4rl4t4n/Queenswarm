import type { ReactNode } from "react";

interface AppsToolsLayoutProps {
  children: ReactNode;
}

/** Passthrough — integrated shell lives in `(integrated)/layout.tsx`; module workspaces keep own HivePageShell. */
export default function AppsToolsLayout({ children }: AppsToolsLayoutProps): JSX.Element {
  return <>{children}</>;
}
