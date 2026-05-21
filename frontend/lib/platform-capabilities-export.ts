import {
  LIVE_PLATFORM_CAPABILITIES,
  PLANNED_PLATFORM_CAPABILITIES,
  PLATFORM_ARCHITECTURE_LAYERS,
  groupCapabilitiesBySection,
  groupPlannedByRolloutPhase,
  type PlatformCapability,
  type PlannedCapability,
} from "@/lib/platform-capabilities-catalog";

const GENERATED_AT = (): string => new Date().toISOString();

function capabilityBlockMarkdown(cap: PlatformCapability): string {
  const lines = [
    `### ${cap.name} (${cap.status})`,
    "",
    cap.summary,
    "",
    `**Ako funguje:** ${cap.howItWorks}`,
    "",
    `**Prínos:** ${cap.value}`,
    "",
    `**Oproti konkurencii:** ${cap.competitiveEdge}`,
  ];
  if (cap.routes?.length) {
    lines.push("", `**Routes:** ${cap.routes.join(", ")}`);
  }
  if (cap.stack?.frontend?.length || cap.stack?.backend?.length) {
    lines.push(
      "",
      `**Stack:** FE ${cap.stack.frontend?.join(", ") ?? "—"} · BE ${cap.stack.backend?.join(", ") ?? "—"}`,
    );
  }
  return lines.join("\n");
}

function plannedBlockMarkdown(item: PlannedCapability): string {
  const lines = [
    `### ${item.name} — ${item.priority} · dopad ${item.impact}`,
    "",
    item.summary,
    "",
    `**Prečo:** ${item.rationale}`,
    "",
    `**Edge:** ${item.competitiveEdge}`,
  ];
  if (item.hints) {
    lines.push("", `**Hint:** ${item.hints}`);
  }
  if (item.week) {
    lines.push("", `**Týždeň (Fáza 0):** ${item.week}`);
  }
  if (item.owner) {
    lines.push("", `**Owner:** ${item.owner}`);
  }
  if (item.auditGate) {
    lines.push("", `**Audit:** ${item.auditGate}`);
  }
  if (item.targetPhase) {
    lines.push("", `**Fáza:** ${item.targetPhase}`);
  }
  return lines.join("\n");
}

/** Full platform atlas as Markdown. */
export function buildCapabilitiesMarkdown(): string {
  const sections = groupCapabilitiesBySection(LIVE_PLATFORM_CAPABILITIES);
  const parts: string[] = [
    "# Queenswarm — Platform Capabilities Atlas",
    "",
    `Generované: ${GENERATED_AT()}`,
    "",
    "## Architektúra",
    "",
    ...PLATFORM_ARCHITECTURE_LAYERS.flatMap((layer) => [
      `### ${layer.label}`,
      ...layer.nodes.map((n) => `- **${n.label}** — ${n.detail}`),
      "",
    ]),
    "## Live features",
    "",
    ...sections.flatMap(({ section, items }) => [
      `## ${section}`,
      "",
      ...items.map((c) => capabilityBlockMarkdown(c)),
      "",
    ]),
    "## Plánované features (roadmap)",
    "",
    ...groupPlannedByRolloutPhase(PLANNED_PLATFORM_CAPABILITIES).flatMap(({ label, items }) => [
      `### ${label}`,
      "",
      ...items.map((p) => plannedBlockMarkdown(p)),
      "",
    ]),
    "",
  ];
  return parts.join("\n");
}

/** Plain-text export (no markdown emphasis). */
export function buildCapabilitiesPlainText(): string {
  return buildCapabilitiesMarkdown()
    .replace(/^#+\s/gm, "")
    .replace(/\*\*/g, "")
    .replace(/^- /gm, "• ");
}

function escapeHtml(raw: string): string {
  return raw
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Printable HTML document for Save as PDF via browser print. */
export function buildCapabilitiesPrintHtml(): string {
  const sections = groupCapabilitiesBySection(LIVE_PLATFORM_CAPABILITIES);
  const archHtml = PLATFORM_ARCHITECTURE_LAYERS.map(
    (layer) => `
    <section class="layer">
      <h3>${escapeHtml(layer.label)}</h3>
      <ul>${layer.nodes.map((n) => `<li><strong>${escapeHtml(n.label)}</strong> — ${escapeHtml(n.detail)}</li>`).join("")}</ul>
    </section>`,
  ).join("");

  const liveHtml = sections
    .map(
      ({ section, items }) => `
    <h2>${escapeHtml(section)}</h2>
    ${items
      .map(
        (c) => `
      <article class="cap">
        <h3>${escapeHtml(c.name)} <span class="tag">${escapeHtml(c.status)}</span></h3>
        <p>${escapeHtml(c.summary)}</p>
        <p><strong>Ako funguje:</strong> ${escapeHtml(c.howItWorks)}</p>
        <p><strong>Prínos:</strong> ${escapeHtml(c.value)}</p>
        <p><strong>Edge:</strong> ${escapeHtml(c.competitiveEdge)}</p>
      </article>`,
      )
      .join("")}`,
    )
    .join("");

  const plannedHtml = groupPlannedByRolloutPhase(PLANNED_PLATFORM_CAPABILITIES)
    .map(
      ({ label, items }) => `
    <h2>${escapeHtml(label)}</h2>
    ${items
      .map(
        (p) => `
    <article class="planned">
      <h3>${escapeHtml(p.name)} <span class="pri">${escapeHtml(p.priority)}</span> · ${escapeHtml(p.impact)}</h3>
      <p>${escapeHtml(p.summary)}</p>
      <p><strong>Prečo:</strong> ${escapeHtml(p.rationale)}</p>
      <p><strong>Edge:</strong> ${escapeHtml(p.competitiveEdge)}</p>
    </article>`,
      )
      .join("")}`,
    )
    .join("");

  return `<!DOCTYPE html>
<html lang="sk">
<head>
  <meta charset="utf-8" />
  <title>Queenswarm Capabilities Atlas</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 820px; margin: 24px auto; color: #111; line-height: 1.5; }
    h1 { font-size: 22px; border-bottom: 2px solid #FFB800; padding-bottom: 8px; }
    h2 { font-size: 16px; margin-top: 24px; color: #333; text-transform: uppercase; letter-spacing: 0.06em; }
    h3 { font-size: 14px; margin-bottom: 4px; }
    .tag, .pri { font-size: 11px; background: #eee; padding: 2px 6px; border-radius: 4px; }
    .cap, .planned, .layer { margin: 12px 0; padding: 12px; border: 1px solid #ddd; border-radius: 8px; }
    p { margin: 6px 0; font-size: 13px; }
    @media print { body { margin: 12mm; } }
  </style>
</head>
<body>
  <h1>Queenswarm — Platform Capabilities Atlas</h1>
  <p><em>Generované: ${escapeHtml(GENERATED_AT())}</em></p>
  <h2>Architektúra</h2>
  ${archHtml}
  <h2>Live features</h2>
  ${liveHtml}
  <h2>Plánované</h2>
  ${plannedHtml}
</body>
</html>`;
}

export async function downloadTextFile(content: string, filename: string, mime: string): Promise<void> {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

/** Trigger browser print dialog (Save as PDF). */
export function printCapabilitiesPdf(): boolean {
  const html = buildCapabilitiesPrintHtml();
  const win = window.open("", "_blank", "noopener,noreferrer,width=900,height=700");
  if (!win) {
    return false;
  }
  win.document.write(html);
  win.document.close();
  win.focus();
  win.onload = () => {
    win.print();
  };
  return true;
}

/** Export single capability snippet. */
export function buildSingleCapabilityMarkdown(cap: PlatformCapability): string {
  return [`# ${cap.name}`, "", capabilityBlockMarkdown(cap)].join("\n");
}

export function buildSingleCapabilityPlainText(cap: PlatformCapability): string {
  return buildSingleCapabilityMarkdown(cap)
    .replace(/^#+\s/gm, "")
    .replace(/\*\*/g, "");
}

export function buildSinglePlannedMarkdown(item: PlannedCapability): string {
  return [`# ${item.name} (plánované)`, "", plannedBlockMarkdown(item)].join("\n");
}
