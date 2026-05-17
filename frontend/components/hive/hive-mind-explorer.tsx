"use client";

import "@xyflow/react/dist/style.css";

import type { Edge, Node } from "@xyflow/react";
import { Background, Controls, MiniMap, ReactFlow, ReactFlowProvider, useEdgesState, useNodesState } from "@xyflow/react";
import { Brain, Download, Loader2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { InfoHint } from "@/components/hive/info-hint";
import { HivePageHeader } from "@/components/hive/hive-page-header";
import { NeonButton } from "@/components/ui/neon-button";
import { HiveApiError, hiveFetchRaw, hiveGet, hivePostJson } from "@/lib/api";
import { cn } from "@/lib/utils";

const DELIVERABLE_ID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

interface HiveGraphNodePayload {
  id: string;
  graph_kind?: string;
  label: string;
  summary?: string;
  tags?: string[];
}

interface HiveGraphPayload {
  nodes: HiveGraphNodePayload[];
  edges: { source: string; target: string; kind?: string }[];
}

interface DeliverablePayload {
  id: string;
  title: string;
  markdown_body: string;
}

interface SemanticHitPreview {
  key: string;
  deliverableId: string | null;
  snippet: string;
}

interface HiveMindExplorerProps {
  readonly showHeader?: boolean;
}

function latticePosition(index: number): { x: number; y: number } {
  const col = index % 5;
  const row = Math.floor(index / 5);
  return { x: col * 220 + 80, y: row * 150 + 40 };
}

/** Cockpit constellation explorer — JWT `/hive-mind/*` + lightweight React Flow canvas. */
export function HiveMindExplorer({ showHeader = true }: HiveMindExplorerProps): JSX.Element {
  const [graph, setGraph] = useState<HiveGraphPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQ, setSearchQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [searchHits, setSearchHits] = useState<SemanticHitPreview[]>([]);

  const [inspect, setInspect] = useState<DeliverablePayload | null>(null);
  const [inspectBusy, setInspectBusy] = useState(false);
  const [recallPreview, setRecallPreview] = useState("");

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  const hydrateDeliverable = useCallback(async (deliverableId: string): Promise<void> => {
    setInspectBusy(true);
    setError(null);
    try {
      const row = await hiveGet<DeliverablePayload>(`hive-mind/deliverables/${encodeURIComponent(deliverableId)}`);
      setInspect(row);
    } catch (e) {
      setError(e instanceof HiveApiError ? e.message : "Could not hydrate deliverable.");
    } finally {
      setInspectBusy(false);
    }
  }, []);

  const loadGraph = useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const body = await hiveGet<HiveGraphPayload>("hive-mind/graph?limit_nodes=92");
      setGraph(body);
      const mappedNodes = body.nodes.map((node, idx) => ({
        id: node.id,
        position: latticePosition(idx),
        data: { label: node.label, subtitle: node.summary ?? "", tags: node.tags ?? [], kind: node.graph_kind ?? "Node" },
      }));
      const mappedEdges: Edge[] = body.edges.map((edge, ei) => ({
        id: `e-${ei}-${edge.source}-${edge.target}`,
        source: edge.source,
        target: edge.target,
        label: edge.kind ?? "",
        animated: Boolean(edge.kind?.includes("CORRELATES")),
      }));
      setNodes(mappedNodes);
      setEdges(mappedEdges);
    } catch (e) {
      setError(e instanceof HiveApiError ? e.message : "Graph snapshot unavailable.");
    } finally {
      setLoading(false);
    }
  }, [setEdges, setNodes]);

  useEffect(() => {
    void loadGraph();
  }, [loadGraph]);

  const graphStats = useMemo(() => `${graph?.nodes.length ?? 0} nodes · ${graph?.edges.length ?? 0} ribs`, [graph]);

  const handleNodeActivate = useCallback(
    (_: unknown, node: { id: string }) => {
      const nodeId = String(node.id);
      if (DELIVERABLE_ID_RE.test(nodeId)) {
        void hydrateDeliverable(nodeId);
      }
    },
    [hydrateDeliverable],
  );

  async function submitSearch(ev: React.FormEvent): Promise<void> {
    ev.preventDefault();
    const q = searchQ.trim();
    setBusy(true);
    setError(null);
    try {
      if (q.length < 2) {
        setSearchHits([]);
      } else {
        const hits = await hiveGet<{
          items: { metadata?: Record<string, string>; document?: string | null }[];
        }>(`hive-mind/search?q=${encodeURIComponent(q)}&limit=10`);
        const rows: SemanticHitPreview[] = hits.items.map((row, idx) => {
          const did = typeof row.metadata?.deliverable_id === "string" ? row.metadata?.deliverable_id : null;
          const snippet = typeof row.document === "string" ? row.document.slice(0, 360) : "(empty payload)";
          return { key: `hit-${did ?? idx}-${idx}`, deliverableId: did, snippet };
        });
        setSearchHits(rows);
      }
    } catch (e) {
      setError(e instanceof HiveApiError ? e.message : "Search failed.");
    } finally {
      setBusy(false);
    }
  }

  async function runRecallSimulation(): Promise<void> {
    setBusy(true);
    setError(null);
    try {
      const payload = await hivePostJson<{ hive_mind_prompt_block?: string }>("hive-mind/query", {
        relevance_to_current_task: searchQ.trim().length >= 3 ? searchQ.trim() : "Ballroom ballroom orchestrator synthesis",
      });
      setRecallPreview(payload.hive_mind_prompt_block ?? "");
    } catch (e) {
      setError(e instanceof HiveApiError ? e.message : "Query preview failed.");
    } finally {
      setBusy(false);
    }
  }

  async function handleExportZip(): Promise<void> {
    try {
      const res = await hiveFetchRaw("hive-mind/export");
      if (!res.ok) {
        throw new HiveApiError(`Export HTTP ${res.status}`, res.status, await res.text());
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `queenswarm-hive-mind-${Date.now()}.zip`;
      anchor.rel = "noopener";
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof HiveApiError ? e.message : "ZIP export unavailable.");
    }
  }

  return (
    <div className="space-y-8">
      {showHeader ? (
        <HivePageHeader
          title="HiveMind Galaxy"
          subtitle="Neo4j constellations, HiveMind vector lane, Markdown vault (/app/hive-mind/vault) — Ballroom attaches recall automatically."
          info={{
            title: { en: "HiveMind Galaxy", sk: "HiveMind Galaxy" },
            description: {
              en: "Memory explorer for graph navigation, semantic retrieval, and deliverable inspection.",
              sk: "Pamäťový explorer pre graph navigáciu, semantické vyhľadávanie a inšpekciu deliverables.",
            },
            options: {
              en: ["Graph refresh", "Semantic search", "Recall preview", "Deliverable hydration", "ZIP export"],
              sk: ["Obnovenie graphu", "Semantické vyhľadávanie", "Recall preview", "Načítanie deliverable", "ZIP export"],
            },
          }}
          actions={
            <>
              <NeonButton type="button" variant="ghost" className="uppercase tracking-[0.12em]" onClick={() => void loadGraph()}>
                Refresh graph
              </NeonButton>
              <NeonButton type="button" variant="primary" className="uppercase tracking-[0.12em]" onClick={() => void handleExportZip()}>
                <Download className="mr-2 inline h-4 w-4" aria-hidden /> Export ZIP
              </NeonButton>
            </>
          }
        />
      ) : (
        <div className="flex flex-wrap gap-2">
          <NeonButton type="button" variant="ghost" className="uppercase tracking-[0.12em]" onClick={() => void loadGraph()}>
            Refresh graph
          </NeonButton>
          <NeonButton type="button" variant="primary" className="uppercase tracking-[0.12em]" onClick={() => void handleExportZip()}>
            <Download className="mr-2 inline h-4 w-4" aria-hidden /> Export ZIP
          </NeonButton>
        </div>
      )}

      <form onSubmit={(e) => void submitSearch(e)} className="flex flex-col gap-3 md:flex-row md:items-end">
        <div className="flex-1 space-y-1">
          <label htmlFor="hm-search" className="sr-only">
            Semantic HiveMind search
          </label>
          <div className="flex items-center gap-2">
            <input
              id="hm-search"
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              placeholder="Global semantic probe (hive_mind Chroma lane)…"
              className="w-full rounded-xl border border-cyan/[0.14] bg-hive-card/90 px-4 py-2.5 font-[family-name:var(--font-poppins)] text-sm text-[#fafafa] placeholder:text-zinc-500 focus:border-pollen/35 focus:outline-none"
            />
            <InfoHint
              title={{ en: "HiveMind semantic search", sk: "HiveMind semantické vyhľadávanie" }}
              description={{
                en: "Searches similar content in the vector lane (Chroma) and returns top relevant snippets.",
                sk: "Vyhľadáva podobný obsah vo vector lane (Chroma) a vracia najrelevantnejšie úryvky.",
              }}
              options={{
                en: ["Query length >=2", "Returns top 10 hits", "Hits can include deliverable_id for inspection"],
                sk: ["Dĺžka query >=2", "Vracia top 10 hitov", "Hity môžu obsahovať deliverable_id pre inšpekciu"],
              }}
            />
          </div>
          <p className="text-[11px] text-muted-foreground">
            Recall clip budget mirrors ballroom defaults — tuned for ≤16 GB hosts.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <NeonButton type="submit" variant="ghost" disabled={busy}>
            Search
          </NeonButton>
          <NeonButton type="button" variant="ghost" disabled={busy} onClick={() => void runRecallSimulation()}>
            Recall preview
          </NeonButton>
        </div>
      </form>

      {error ? (
        <p className="rounded-xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">{error}</p>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[1fr_minmax(320px,0.42fr)]">
        <ReactFlowProvider>
          <section className="relative h-[min(68vh,640px)] rounded-3xl border border-cyan/[0.1] bg-hive-card/65 p-2 shadow-inner">
            {loading ? (
              <div className="absolute inset-0 z-10 flex items-center justify-center gap-3 bg-black/50 text-[10px] uppercase tracking-[0.35em] text-pollen backdrop-blur">
                <Loader2 className="h-5 w-5 animate-spin" aria-hidden />
                Warping constellation…
              </div>
            ) : null}
            <div className="pointer-events-none absolute left-6 top-4 z-20 rounded-full border border-pollen/30 bg-black/65 px-3 py-1 text-[10px] text-pollen backdrop-blur">
              <Brain className="mr-2 inline h-4 w-4 align-text-bottom text-pollen" aria-hidden /> {graphStats}
            </div>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onNodeClick={(event, node) => handleNodeActivate(event, node)}
              fitView
              panOnDrag
            >
              <Background gap={36} />
              <Controls />
              <MiniMap pannable zoomable className="border border-white/10 bg-black/50" />
            </ReactFlow>
          </section>
          <aside className="space-y-4">
            <div className="rounded-2xl border border-cyan/[0.09] bg-hive-card/90 p-4">
              <h2 className="font-[family-name:var(--font-poppins)] text-sm font-semibold text-[#fafafa]">
                Embedding hits ({searchHits.length})
              </h2>
              <div className="mt-3 space-y-2">
                {searchHits.map((hit) => (
                  <button
                    key={hit.key}
                    type="button"
                    className={cn(
                      "block w-full rounded-xl border border-cyan/[0.08] bg-black/35 px-3 py-2 text-left text-[12px] text-zinc-200 transition hover:border-pollen/35",
                      !hit.deliverableId && "opacity-60",
                    )}
                    disabled={!hit.deliverableId}
                    title={hit.deliverableId ? "Open Postgres mirror" : "No deliverable id on vector row"}
                    onClick={() => {
                      if (hit.deliverableId) void hydrateDeliverable(hit.deliverableId);
                    }}
                  >
                    <span className="line-clamp-4">{hit.snippet}</span>
                  </button>
                ))}
                {!searchHits.length ? <p className="text-xs text-muted-foreground">Run search to hydrate matches.</p> : null}
              </div>
            </div>

            <div className="rounded-2xl border border-cyan/[0.08] bg-black/55 p-4">
              <h3 className="text-[11px] uppercase tracking-[0.25em] text-data">Recall appendix preview</h3>
              <pre className="mt-3 max-h-48 overflow-auto whitespace-pre-wrap font-[family-name:var(--font-jetbrains)] text-[11px] leading-relaxed text-zinc-300">
                {recallPreview.trim() ? recallPreview : "Hit “Recall preview” to mirror Ballroom injection budget."}
              </pre>
            </div>

            <div className="rounded-2xl border border-pollen/25 bg-black/65 p-4">
              <div className="flex items-center gap-2">
                <h3 className="text-[11px] uppercase tracking-[0.25em] text-pollen">
                  Deliverable prism {inspectBusy ? "· fetching" : ""}
                </h3>
                <InfoHint
                  title={{ en: "Deliverable prism", sk: "Deliverable prism" }}
                  description={{
                    en: "Detailed view of the selected deliverable document from the HiveMind mirror.",
                    sk: "Detailný náhľad vybraného deliverable dokumentu z HiveMind mirroru.",
                  }}
                  options={{
                    en: ["Click graph node or hit", "Fetches markdown body", "Supports long-form inspection"],
                    sk: ["Klikni na graph node alebo hit", "Načíta markdown body", "Podporuje dlhý dokument pre inšpekciu"],
                  }}
                />
              </div>
              {inspect ? (
                <article className="mt-4 space-y-3">
                  <p className="font-[family-name:var(--font-poppins)] text-lg text-[#fafafa]">{inspect.title}</p>
                  <pre className="max-h-[420px] overflow-auto whitespace-pre-wrap rounded-xl bg-[#050510]/90 p-3 font-[family-name:var(--font-jetbrains)] text-[12px] leading-relaxed text-zinc-200">
                    {inspect.markdown_body.slice(0, 160_000)}
                  </pre>
                </article>
              ) : (
                <p className="mt-4 text-[12px] text-muted-foreground">
                  Tap a constellation glyph with a Ballroom deliverable UUID or pick a semantic row with metadata.
                </p>
              )}
            </div>
          </aside>
        </ReactFlowProvider>
      </div>
    </div>
  );
}
