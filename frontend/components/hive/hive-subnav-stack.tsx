"use client";

import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

interface HiveSubnavStackProps {
  children: ReactNode;
  className?: string;
}

/** Uniform vertical gap between menu / sub-menu / sub-sub-menu pill rows. */
export function HiveSubnavStack({ children, className }: HiveSubnavStackProps): JSX.Element {
  return <div className={cn("hive-subnav-stack", className)}>{children}</div>;
}

interface HiveSubnavContentProps {
  children: ReactNode;
  className?: string;
}

/** Panel content below a nav stack — larger offset than inter-nav gap. */
export function HiveSubnavContent({ children, className }: HiveSubnavContentProps): JSX.Element {
  return <div className={cn("hive-subnav-content min-w-0", className)}>{children}</div>;
}
