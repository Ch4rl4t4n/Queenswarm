"use client";

import { usePathname } from "next/navigation";
import { Suspense, useEffect, useMemo, useState, type ComponentType } from "react";

import { HiveSubnavContent } from "@/components/hive/hive-subnav-stack";
import { RoutePulseLoading } from "@/components/hive/route-pulse-loading";
import {
  DEFAULT_SETTINGS_PANEL,
  parseSettingsPanelSlug,
  SETTINGS_PANEL_LOADERS,
  warmAllSettingsPanelChunks,
  type SettingsPanelSlug,
} from "@/lib/settings-panel-registry";
import { cn } from "@/lib/utils";

function LoadedPanel({ Panel }: { Panel: ComponentType<object> }) {
  return <Panel />;
}

function SettingsPanelSlot({ slug }: { slug: SettingsPanelSlug }) {
  const [Panel, setPanel] = useState<ComponentType<object> | null>(null);

  useEffect(() => {
    let alive = true;
    void SETTINGS_PANEL_LOADERS[slug]().then((mod) => {
      if (alive) {
        setPanel(() => mod.default);
      }
    });
    return () => {
      alive = false;
    };
  }, [slug]);

  if (!Panel) {
    return <RoutePulseLoading />;
  }

  return (
    <Suspense fallback={<RoutePulseLoading />}>
      <LoadedPanel Panel={Panel} />
    </Suspense>
  );
}

/**
 * Keep-alive settings panels — tab switches stay in one client tree (dashboard-layout modal pattern).
 * URLs remain `/settings/{slug}` via optional catch-all route.
 */
export function SettingsPanelHost() {
  const pathname = usePathname();
  const active = parseSettingsPanelSlug(pathname) ?? DEFAULT_SETTINGS_PANEL;
  const [mounted, setMounted] = useState<SettingsPanelSlug[]>(() => [active]);

  useEffect(() => {
    setMounted((prev) => (prev.includes(active) ? prev : [...prev, active]));
  }, [active]);

  useEffect(() => {
    const schedule =
      typeof window.requestIdleCallback === "function"
        ? window.requestIdleCallback.bind(window)
        : (cb: IdleRequestCallback) => window.setTimeout(() => cb({ didTimeout: false, timeRemaining: () => 0 }), 800);

    const cancel =
      typeof window.cancelIdleCallback === "function"
        ? window.cancelIdleCallback.bind(window)
        : window.clearTimeout.bind(window);

    const handle = schedule(() => warmAllSettingsPanelChunks());
    return () => cancel(handle);
  }, []);

  const slots = useMemo(() => mounted, [mounted]);

  return (
    <>
      {slots.map((slug) => (
        <div
          key={slug}
          className={cn(slug === active ? "block min-w-0" : "hidden")}
          aria-hidden={slug !== active}
          data-settings-panel={slug}
        >
          {slug === "harness" ? (
            <SettingsPanelSlot slug={slug} />
          ) : (
            <HiveSubnavContent>
              <SettingsPanelSlot slug={slug} />
            </HiveSubnavContent>
          )}
        </div>
      ))}
    </>
  );
}
