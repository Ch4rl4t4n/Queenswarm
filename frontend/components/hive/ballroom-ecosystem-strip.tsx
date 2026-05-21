"use client";

import type { JSX } from "react";

import { HubEcosystemStrip } from "@/components/hive/hub-ecosystem-strip";

/** Cross-linked ecosystem shortcuts on the Ballroom page. */
export function BallroomEcosystemStrip(): JSX.Element {
  return <HubEcosystemStrip preset="ballroom" id="ballroom-ecosystem" />;
}
