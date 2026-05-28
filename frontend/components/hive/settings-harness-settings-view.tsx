"use client";

import { BookOpen, Brain, Sparkles } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { HiveSectionSubnav } from "@/components/hive/hive-section-subnav";
import { HiveSubnavContent } from "@/components/hive/hive-subnav-stack";
import { PatternExplorerSettingsPanel } from "@/components/hive/pattern-explorer-card";
import { SettingsHarnessPanel } from "@/components/hive/settings-harness-panel";
import { SettingsOperatorHubPanel } from "@/components/hive/settings-operator-hub-panel";
import { scrollBehaviorForMotion } from "@/lib/motion-preferences";
import {
  harnessSectionFromHash,
  harnessSectionHref,
  parseHarnessLocation,
  type HarnessSection,
} from "@/lib/settings-harness-routes";
import {
  HARNESS_RULES_SECTIONS,
  harnessRulesSectionHref,
  resolveHarnessRulesSection,
  type HarnessRulesSection,
} from "@/lib/settings-harness-rules-routes";

const SECTIONS: { id: HarnessSection; label: string; icon: typeof Brain }[] = [
  { id: "operator", label: "Operator hub", icon: Sparkles },
  { id: "rules", label: "Rules & skills", icon: Brain },
  { id: "patterns", label: "Pattern telemetry", icon: BookOpen },
];

/** Harness settings section — tabbed sub-views for operator hub, rules, patterns. */
export function SettingsHarnessSettingsView(): JSX.Element {
  const [section, setSection] = useState<HarnessSection>(() =>
    typeof window !== "undefined" ? parseHarnessLocation(window.location.hash).tab : "operator",
  );
  const [rulesSection, setRulesSection] = useState<HarnessRulesSection>(() =>
    typeof window !== "undefined" ? parseHarnessLocation(window.location.hash).rulesSection : "overview",
  );

  const syncFromLocation = useCallback((): void => {
    const hash = window.location.hash;
    const parsed = parseHarnessLocation(hash);
    setSection(parsed.tab);
    setRulesSection(parsed.rulesSection);
    if (!harnessSectionFromHash(hash)) {
      window.history.replaceState(
        null,
        "",
        parsed.tab === "rules"
          ? harnessRulesSectionHref(parsed.rulesSection)
          : harnessSectionHref(parsed.tab),
      );
    }
  }, []);

  const selectSection = useCallback((next: HarnessSection) => {
    setSection(next);
    if (next === "rules") {
      const rulesDefault = resolveHarnessRulesSection({});
      setRulesSection(rulesDefault);
      window.history.replaceState(null, "", harnessRulesSectionHref(rulesDefault));
      return;
    }
    window.history.replaceState(null, "", harnessSectionHref(next));
  }, []);

  const selectRulesSection = useCallback((next: HarnessRulesSection) => {
    setSection("rules");
    setRulesSection(next);
    window.history.replaceState(null, "", harnessRulesSectionHref(next));
  }, []);

  useEffect(() => {
    syncFromLocation();
    window.addEventListener("hashchange", syncFromLocation);
    return () => window.removeEventListener("hashchange", syncFromLocation);
  }, [syncFromLocation]);

  useEffect(() => {
    if (section !== "operator") {
      return;
    }
    const hash = typeof window !== "undefined" ? window.location.hash.replace(/^#/, "").trim().toLowerCase() : "";
    if (hash !== "operator-hub") {
      return;
    }
    const behavior = scrollBehaviorForMotion();
    const attemptScroll = (retries: number): void => {
      const el = document.getElementById("operator-hub");
      if (el) {
        el.scrollIntoView({ behavior, block: "start" });
        return;
      }
      if (retries > 0) {
        window.setTimeout(() => attemptScroll(retries - 1), 100);
      }
    };
    window.setTimeout(() => attemptScroll(24), 80);
  }, [section]);

  const rulesNavItems = HARNESS_RULES_SECTIONS.map(({ id, label, icon }) => ({
    id,
    label,
    icon,
    href: harnessRulesSectionHref(id),
  }));

  return (
    <>
      <HiveSectionSubnav
        primary={SECTIONS.map(({ id, label, icon }) => ({ id, label, icon }))}
        activePrimary={section}
        onPrimaryChange={(id) => selectSection(id as HarnessSection)}
        primaryAriaLabel="Harness sections"
        primaryMenuKey="settings-harness"
        tertiary={section === "rules" ? rulesNavItems : undefined}
        activeTertiary={section === "rules" ? rulesSection : undefined}
        onTertiaryChange={(id) => selectRulesSection(id as HarnessRulesSection)}
        tertiaryAriaLabel="Rules and skills sections"
        tertiaryMenuKey="settings-harness-rules"
      />

      <HiveSubnavContent>
        {section === "operator" ? (
          <div id="operator" className="scroll-mt-28">
            <SettingsOperatorHubPanel />
          </div>
        ) : null}

        {section === "rules" ? (
          <div id="rules" className="scroll-mt-28">
            <SettingsHarnessPanel section={rulesSection} />
          </div>
        ) : null}

        {section === "patterns" ? (
          <div id="patterns" className="scroll-mt-28">
            <PatternExplorerSettingsPanel />
          </div>
        ) : null}
      </HiveSubnavContent>
    </>
  );
}
