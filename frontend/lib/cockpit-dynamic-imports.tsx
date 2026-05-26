import type { ComponentType } from "react";
import nextDynamic from "next/dynamic";

import { RoutePulseLoading } from "@/components/hive/route-pulse-loading";

/** Hot routes — minimal loading chrome for instant perceived navigation. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any -- next/dynamic loader variance across page props
export function cockpitDynamic(loader: () => Promise<{ default: ComponentType<any> }>): ComponentType<any> {
  return nextDynamic(loader, { loading: () => <RoutePulseLoading /> });
}

/** Settings-sized panels — spinner only when chunk is cold. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function settingsDynamic(loader: () => Promise<{ default: ComponentType<any> }>): ComponentType<any> {
  return nextDynamic(loader, { loading: () => <RoutePulseLoading /> });
}
