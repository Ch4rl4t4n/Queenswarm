"use client";

import { HierarchyPageConsole } from "@/components/hive/hierarchy-page-console";
import { CollapsibleLazyPanel } from "@/components/hive/collapsible-lazy-panel";
import { sectionHintNode } from "@/components/hive/inline-section-hint";
import { V4CardHeader } from "@/components/ui/v4";

interface HierarchyGraphCollapsibleProps {
  readonly beeCount: number;
  /** Static panel — graph mounts immediately (Ecosystem sub-tab). */
  readonly expanded?: boolean;
}

/** Collapsed hierarchy tab — graph mounts only after expand (or `#hierarchy` hash). */
export function HierarchyGraphCollapsible({ beeCount, expanded = false }: HierarchyGraphCollapsibleProps): JSX.Element {
  return (
    <CollapsibleLazyPanel
      id="hierarchy"
      hashKey={expanded ? undefined : "hierarchy"}
      title="Hierarchy graph"
      hint="Queen → managers → workers"
      meta={`${beeCount} bees`}
      expanded={expanded}
      lazyContent={() => (
        <>
          <V4CardHeader
            title="Hierarchy graph"
            description="Queen → managers → workers topology with grouped swarm lanes."
            hint={sectionHintNode("agentsHierarchy")}
            as="h3"
            actions={
              <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm" onClick={() => window.location.reload()}>
                Re-layout
              </button>
            }
          />
          <HierarchyPageConsole showHeader={false} enabled />
        </>
      )}
    />
  );
}
