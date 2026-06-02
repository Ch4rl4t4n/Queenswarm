import { describe, expect, it } from "vitest";
import { Zap } from "lucide-react";

import {
  buildCanonicalNavGroups,
  CANONICAL_PRIMARY_CP_HREFS,
  CANONICAL_MORE_ONLY_HREFS,
  shouldRenderIaZoneDivider,
  toHiveNavItems,
  WHOLE_APP_IA_VERSION,
} from "@/lib/hive-ia-canonical";
import { buildHiveNavPrimary } from "@/lib/hive-nav-primary";
import { OPERATOR_CONTROL_PLANE_ENABLED } from "@/lib/feature-flags";

describe("hive-ia-canonical", () => {
  it("exposes stable IA version", () => {
    expect(WHOLE_APP_IA_VERSION).toMatch(/^2026\./);
  });

  it("orders CP primary rail per blueprint zones", () => {
    if (!OPERATOR_CONTROL_PLANE_ENABLED) {
      return;
    }
    const hrefs = buildHiveNavPrimary(true).map((item) => item.href);
    expect(hrefs).toEqual([...CANONICAL_PRIMARY_CP_HREFS]);
  });

  it("places Factory in More menu only for CP (Foragers on primary rail)", () => {
    if (!OPERATOR_CONTROL_PLANE_ENABLED) {
      return;
    }
    const primary = new Set(buildHiveNavPrimary(true).map((item) => item.href));
    expect(primary.has("/factory")).toBe(false);
    expect(primary.has("/foragers")).toBe(true);
    const groups = buildCanonicalNavGroups({
      consolidatedEnabled: true,
      operatorControlPlane: true,
      advancedMonitoring: false,
      simulationsEnabled: false,
      recipesEnabled: false,
    });
    const moreHrefs = new Set(groups.flatMap((g) => g.items.map((i) => i.href)));
    for (const href of CANONICAL_MORE_ONLY_HREFS) {
      expect(moreHrefs.has(href), `expected ${href} in More menu`).toBe(true);
    }
  });

  it("renders zone dividers between product layers", () => {
    const items = toHiveNavItems([
      {
        href: "/agentic-os",
        label: "Agentic OS",
        Icon: Zap,
        iaZone: "agentic_os",
        section: "overview",
      },
      {
        href: "/apps-tools",
        label: "Apps & Tools",
        Icon: Zap,
        iaZone: "apps_tools",
        section: "integrations",
      },
    ]);
    expect(shouldRenderIaZoneDivider(items, 0)).toBe(false);
    expect(shouldRenderIaZoneDivider(items, 1)).toBe(true);
  });

  it("dedupes duplicate Swarms entries in Agentic OS More group", () => {
    const groups = buildCanonicalNavGroups({
      consolidatedEnabled: true,
      operatorControlPlane: true,
      advancedMonitoring: false,
      simulationsEnabled: false,
      recipesEnabled: false,
    });
    const agentic = groups.find((g) => g.title === "Agentic OS")!;
    const swarmsLinks = agentic.items.filter((i) => i.href === "/swarms");
    expect(swarmsLinks).toHaveLength(1);
  });
});
