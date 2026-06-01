"use client";

import { useEffect, useState } from "react";

import { HiveCommandPalette, useHiveCommandPaletteShortcut } from "@/components/hive/hive-command-palette";

/** Mounts global ⌘K / Ctrl+K mission search palette in dashboard shell. */
export function HiveCommandPaletteHost(): JSX.Element {
  const [open, setOpen] = useState(false);
  useHiveCommandPaletteShortcut(() => setOpen((prev) => !prev));

  useEffect(() => {
    const handler = () => setOpen(true);
    window.addEventListener("hive:open-command-palette", handler);
    return () => window.removeEventListener("hive:open-command-palette", handler);
  }, []);

  return <HiveCommandPalette open={open} onClose={() => setOpen(false)} />;
}
