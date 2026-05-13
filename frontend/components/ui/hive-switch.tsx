"use client";

import type { ButtonHTMLAttributes } from "react";

import { Toggle } from "@/components/ui/toggle";

interface HiveSwitchProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "onClick" | "onChange"> {
  /** Current on/off state. */
  checked: boolean;
  /** Fires when toggle is pressed. */
  onCheckedChange: (next: boolean) => void;
}

export function HiveSwitch({ checked, onCheckedChange, className, ...props }: HiveSwitchProps) {
  return <Toggle checked={checked} className={className} onChange={onCheckedChange} {...props} />;
}
