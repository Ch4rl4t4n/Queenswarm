import { HivePageHeader } from "@/components/hive/hive-page-header";
import { SectionNavGrid } from "@/components/hive/section-nav-grid";

export default function IntegrationsPage(): JSX.Element {
  return (
    <div className="space-y-8">
      <HivePageHeader
        title="Integrations"
        subtitle="Unified integration surface for connectors, external projects, and plugin extensions."
      />
      <SectionNavGrid
        items={[
          { href: "/connectors", title: "Connectors", description: "Provider catalog, auth flows, and vault-backed access." },
          { href: "/external-projects", title: "External projects", description: "Bridge third-party apps and endpoint automation." },
          { href: "/plugins", title: "Plugins", description: "Built-in and operator plugin catalog controls." },
          { href: "/settings/llm-keys", title: "LLM keys", description: "Provider secrets and runtime credential posture." },
        ]}
      />
    </div>
  );
}
