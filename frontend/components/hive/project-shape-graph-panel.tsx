"use client";

import "@xyflow/react/dist/style.css";

import type { Edge, Node, NodeProps } from "@xyflow/react";
import {
  Background,
  Controls,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
} from "@xyflow/react";
import {
  Database,
  FileText,
  FolderOpen,
  FolderTree,
  Hash,
  Loader2Icon,
  RefreshCw,
} from "lucide-react";
import { memo, useCallback, useMemo, useRef, useState } from "react";
import type { LucideIcon } from "lucide-react";

import { CollapsibleLazyPanel } from "@/components/hive/collapsible-lazy-panel";
import { usePlatform } from "@/components/hive/platform-context";
import { V4Badge, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";
import { cn } from "@/lib/utils";

interface ProjectShapeNode {
  id: string;
  graph_kind?: string;
  label: string;
  summary?: string;
  tags?: string[];
  rel_path?: string;
}

interface ProjectShapePayload {
  nodes: ProjectShapeNode[];
  edges: { source: string; target: string; kind?: string }[];
  shape?: string;
  degraded?: boolean;
}

interface ShapeNodeData extends Record<string, unknown> {
  label: string;
  subtitle: string;
  kind: string;
}

interface NodeKindVisual {
  icon: LucideIcon;
  accent: string;
  border: string;
  bg: string;
  glow: string;
  badge: string;
}

const NODE_KIND_VISUAL: Record<string, NodeKindVisual> = {
  GraphifyBatch: {
    icon: Database,
    accent: "#fdb927",
    border: "rgba(253, 185, 39, 0.65)",
    bg: "rgba(253, 185, 39, 0.12)",
    glow: "0 0 22px rgba(253, 185, 39, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.08)",
    badge: "BATCH",
  },
  VaultFolder: {
    icon: FolderOpen,
    accent: "#6fd6ff",
    border: "rgba(111, 214, 255, 0.55)",
    bg: "rgba(111, 214, 255, 0.1)",
    glow: "0 0 20px rgba(111, 214, 255, 0.28), inset 0 1px 0 rgba(255, 255, 255, 0.06)",
    badge: "FOLDER",
  },
  VaultDocument: {
    icon: FileText,
    accent: "#5be3b2",
    border: "rgba(91, 227, 178, 0.5)",
    bg: "rgba(91, 227, 178, 0.1)",
    glow: "0 0 18px rgba(91, 227, 178, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.06)",
    badge: "DOC",
  },
  Tag: {
    icon: Hash,
    accent: "#e879f9",
    border: "rgba(232, 121, 249, 0.55)",
    bg: "rgba(232, 121, 249, 0.12)",
    glow: "0 0 16px rgba(232, 121, 249, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.06)",
    badge: "TAG",
  },
};

const DEFAULT_NODE_VISUAL: NodeKindVisual = {
  icon: FolderTree,
  accent: "#877ba8",
  border: "rgba(255, 255, 255, 0.2)",
  bg: "rgba(255, 255, 255, 0.06)",
  glow: "0 0 12px rgba(255, 255, 255, 0.08)",
  badge: "NODE",
};

const EDGE_KIND_STYLE: Record<string, { stroke: string; animated?: boolean }> = {
  ROOTED_IN: { stroke: "#fdb927", animated: true },
  CONTAINS: { stroke: "#6fd6ff", animated: true },
  TAGGED_AS: { stroke: "#e879f9", animated: false },
};

function nodeVisual(kind: string): NodeKindVisual {
  return NODE_KIND_VISUAL[kind] ?? DEFAULT_NODE_VISUAL;
}

const ShapeFlowNode = memo(function ShapeFlowNode({ data, selected }: NodeProps<Node<ShapeNodeData>>) {
  const visual = nodeVisual(data.kind);
  const Icon = visual.icon;

  return (
    <>
      <Handle
        type="target"
        position={Position.Top}
        className="!h-2 !w-2 !border-2 !bg-[#07030f]"
        style={{ borderColor: visual.accent }}
      />
      <div
        className={cn(
          "min-w-[132px] max-w-[200px] rounded-xl border px-3 py-2 transition-all duration-200",
          selected && "scale-[1.03]",
        )}
        style={{
          borderColor: visual.border,
          background: `linear-gradient(145deg, ${visual.bg} 0%, rgba(7, 3, 15, 0.92) 100%)`,
          boxShadow: selected ? `${visual.glow}, 0 0 0 2px ${visual.accent}` : visual.glow,
        }}
      >
        <div className="mb-1.5 flex items-center gap-1.5">
          <span
            className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-md"
            style={{ backgroundColor: `${visual.accent}22`, color: visual.accent }}
          >
            <Icon className="h-3 w-3" aria-hidden />
          </span>
          <span
            className="rounded px-1 py-0.5 font-mono text-[8px] font-semibold uppercase tracking-wider"
            style={{ color: visual.accent, backgroundColor: `${visual.accent}18` }}
          >
            {visual.badge}
          </span>
        </div>
        <p className="truncate text-[11px] font-semibold leading-tight text-[#f5f1ff]">{data.label}</p>
        {data.subtitle ? (
          <p className="mt-1 truncate font-mono text-[9px] leading-tight text-[#c7bee2]">{data.subtitle}</p>
        ) : null}
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        className="!h-2 !w-2 !border-2 !bg-[#07030f]"
        style={{ borderColor: visual.accent }}
      />
    </>
  );
});

const nodeTypes = { shapeNode: ShapeFlowNode };

function layoutProjectShape(nodes: ProjectShapeNode[]): Map<string, { x: number; y: number }> {
  const positions = new Map<string, { x: number; y: number }>();
  const batches = nodes.filter((n) => n.graph_kind === "GraphifyBatch");
  const folders = nodes.filter((n) => n.graph_kind === "VaultFolder");
  const documents = nodes.filter((n) => n.graph_kind === "VaultDocument");
  const tags = nodes.filter((n) => n.graph_kind === "Tag");

  batches.forEach((node, idx) => {
    positions.set(node.id, { x: 280 + idx * 40, y: 20 });
  });

  folders.forEach((node, idx) => {
    positions.set(node.id, { x: 40 + idx * 260, y: 120 });
  });

  const docsByFolder = new Map<string, ProjectShapeNode[]>();
  for (const doc of documents) {
    const path = doc.rel_path ?? "";
    const folderKey = path.includes("/") ? path.split("/").slice(0, -1).join("/") : "__root__";
    const bucket = docsByFolder.get(folderKey) ?? [];
    bucket.push(doc);
    docsByFolder.set(folderKey, bucket);
  }

  let folderIdx = 0;
  for (const [, docs] of docsByFolder) {
    docs.forEach((doc, docIdx) => {
      positions.set(doc.id, { x: 40 + folderIdx * 260 + (docIdx % 2) * 120, y: 240 + Math.floor(docIdx / 2) * 90 });
    });
    folderIdx += 1;
  }

  documents
    .filter((doc) => !positions.has(doc.id))
    .forEach((doc, idx) => {
      positions.set(doc.id, { x: 60 + (idx % 4) * 140, y: 260 + Math.floor(idx / 4) * 80 });
    });

  tags.forEach((node, idx) => {
    positions.set(node.id, { x: 520 + (idx % 3) * 90, y: 380 + Math.floor(idx / 3) * 60 });
  });

  nodes.forEach((node, idx) => {
    if (!positions.has(node.id)) {
      positions.set(node.id, { x: 80 + (idx % 5) * 150, y: 420 + Math.floor(idx / 5) * 70 });
    }
  });

  return positions;
}

function buildFlowEdges(edges: ProjectShapePayload["edges"]): Edge[] {
  return edges.map((edge, idx) => {
    const kind = edge.kind ?? "";
    const edgeStyle = EDGE_KIND_STYLE[kind] ?? { stroke: "#877ba8", animated: false };
    return {
      id: `ps-${idx}-${edge.source}-${edge.target}`,
      source: edge.source,
      target: edge.target,
      label: kind,
      animated: edgeStyle.animated,
      style: { stroke: edgeStyle.stroke, strokeWidth: 2.5 },
      markerEnd: { type: MarkerType.ArrowClosed, color: edgeStyle.stroke, width: 18, height: 18 },
      labelStyle: { fill: edgeStyle.stroke, fontSize: 9, fontWeight: 700, letterSpacing: "0.04em" },
      labelBgStyle: { fill: "#1d1140", fillOpacity: 0.95, stroke: edgeStyle.stroke, strokeWidth: 0.5 },
      labelBgPadding: [6, 4] as [number, number],
      labelBgBorderRadius: 6,
    };
  });
}

/** Project folder tree viz — Auto-Graphify VaultFolder → VaultDocument graph lane. */
export function ProjectShapeGraphPanel(): JSX.Element | null {
  const { hasFeature } = usePlatform();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [payload, setPayload] = useState<ProjectShapePayload | null>(null);
  const [selected, setSelected] = useState<ProjectShapeNode | null>(null);
  const [flowNodes, setFlowNodes, onNodesChange] = useNodesState<Node<ShapeNodeData>>([]);
  const [flowEdges, setFlowEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const loadedRef = useRef(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const body = await hiveGet<ProjectShapePayload>("hive-mind/project-shape?limit_nodes=96");
      setPayload(body);
      const positions = layoutProjectShape(body.nodes);
      setFlowNodes(
        body.nodes.map((node) => ({
          id: node.id,
          type: "shapeNode",
          position: positions.get(node.id) ?? { x: 0, y: 0 },
          data: {
            label: node.label,
            subtitle: node.summary ?? node.rel_path ?? "",
            kind: node.graph_kind ?? "Node",
          },
        })),
      );
      setFlowEdges(buildFlowEdges(body.edges));
    } catch (e) {
      setError(e instanceof HiveApiError ? e.message : "Project shape graph unavailable.");
    } finally {
      setLoading(false);
    }
  }, [setFlowEdges, setFlowNodes]);

  function handlePanelOpen(open: boolean): void {
    if (open && !loadedRef.current) {
      loadedRef.current = true;
      void load();
    }
  }

  const stats = useMemo(() => {
    const nodes = payload?.nodes ?? [];
    const folders = nodes.filter((n) => n.graph_kind === "VaultFolder").length;
    const docs = nodes.filter((n) => n.graph_kind === "VaultDocument").length;
    const batches = nodes.filter((n) => n.graph_kind === "GraphifyBatch").length;
    return { folders, docs, batches, edges: payload?.edges.length ?? 0 };
  }, [payload]);

  if (!hasFeature("auto_graphify")) {
    return null;
  }

  const metaLabel =
    payload != null
      ? `${stats.batches} batches · ${stats.folders} folders · ${stats.docs} docs`
      : undefined;

  return (
    <CollapsibleLazyPanel
      id="project-shape"
      title="Project shape map"
      hint="Auto-Graphify · vault · Neo4j"
      meta={metaLabel}
      hashKey="project-shape"
      onOpenChange={handlePanelOpen}
      className={cn(
        "v4-card-interactive relative overflow-hidden",
        "border-(--qs-green)/30 bg-gradient-to-br from-[#0a0618] via-[#07030f] to-[#0d0820]",
      )}
      lazyContent={() => (
        <>
      <div
        className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full opacity-30 blur-3xl"
        style={{ background: "radial-gradient(circle, var(--qs-green) 0%, transparent 70%)" }}
        aria-hidden
      />
      <div
        className="pointer-events-none absolute -bottom-20 -left-12 h-56 w-56 rounded-full opacity-25 blur-3xl"
        style={{ background: "radial-gradient(circle, var(--qs-cyan) 0%, transparent 70%)" }}
        aria-hidden
      />

      <V4CardHeader
        title="Project shape map"
        description="Folder hierarchy from Auto-Graphify — vault folders, documents, and ingest batches in Neo4j."
        as="h3"
        actions={
          <div className="flex items-center gap-2">
            <FolderTree className="h-4 w-4 text-(--qs-green)" aria-hidden />
            <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm gap-1" disabled={loading} onClick={() => void load()}>
              <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} aria-hidden />
              Refresh
            </button>
          </div>
        }
      />

      <div className="mb-3 flex flex-wrap gap-2">
        <V4Badge tone="info">{stats.batches} batches</V4Badge>
        <V4Badge tone="warn">{stats.folders} folders</V4Badge>
        <V4Badge tone="ok">{stats.docs} documents</V4Badge>
        <V4Badge tone="info">{stats.edges} edges</V4Badge>
      </div>

      <div className="mb-3 flex flex-wrap gap-3 text-[10px] uppercase tracking-wide text-(--qs-text-3)">
        {Object.entries(NODE_KIND_VISUAL).map(([kind, visual]) => (
          <span key={kind} className="inline-flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: visual.accent, boxShadow: `0 0 8px ${visual.accent}` }} />
            {visual.badge.toLowerCase()}
          </span>
        ))}
        {Object.entries(EDGE_KIND_STYLE).map(([kind, style]) => (
          <span key={kind} className="inline-flex items-center gap-1.5">
            <span className="h-0.5 w-4 rounded" style={{ backgroundColor: style.stroke }} />
            {kind.replace("_", " ").toLowerCase()}
          </span>
        ))}
      </div>

      {error ? <p className="text-sm text-(--qs-red)">{error}</p> : null}

      {!loading && !error && (payload?.nodes.length ?? 0) === 0 ? (
        <p className="text-sm text-(--qs-text-3)">
          No project shape yet — upload a folder via Auto-Graphify above to populate vault + graph nodes.
        </p>
      ) : null}

      <div
        className={cn(
          "project-shape-flow relative min-h-[280px] h-[min(42vh,360px)] overflow-hidden rounded-xl",
          "border border-cyan/20 bg-[#050510]/80",
          "[&_.react-flow\_\_node]:!border-0 [&_.react-flow\_\_node]:!bg-transparent [&_.react-flow\_\_node]:!p-0 [&_.react-flow\_\_node]:!shadow-none",
          "[&_.react-flow\_\_controls-button]:!border-white/10 [&_.react-flow\_\_controls-button]:!bg-[#1d1140] [&_.react-flow\_\_controls-button]:!text-[#f5f1ff]",
          "[&_.react-flow\_\_controls-button:hover]:!bg-[#2a1850]",
        )}
      >
        {loading ? (
          <div className="absolute inset-0 z-10 flex items-center justify-center gap-2 text-sm text-(--qs-text-3)">
            <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> Loading project shape…
          </div>
        ) : null}
        <ReactFlowProvider>
          <ReactFlow
            nodes={flowNodes}
            edges={flowEdges}
            nodeTypes={nodeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={(_, node) => {
              const match = payload?.nodes.find((n) => n.id === node.id) ?? null;
              setSelected(match);
            }}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            panOnDrag
            minZoom={0.35}
            maxZoom={1.4}
            proOptions={{ hideAttribution: true }}
          >
            <Background gap={24} size={1.2} color="rgba(126, 63, 190, 0.35)" />
            <Controls showInteractive={false} />
          </ReactFlow>
        </ReactFlowProvider>
      </div>

      {selected ? (
        <div
          className="mt-3 rounded-lg border p-3 text-sm"
          style={{
            borderColor: nodeVisual(selected.graph_kind ?? "").border,
            background: `linear-gradient(135deg, ${nodeVisual(selected.graph_kind ?? "").bg}, rgba(7, 3, 15, 0.95))`,
            boxShadow: nodeVisual(selected.graph_kind ?? "").glow,
          }}
        >
          <p className="font-medium text-(--qs-text)">{selected.label}</p>
          <p className="text-xs uppercase tracking-wide" style={{ color: nodeVisual(selected.graph_kind ?? "").accent }}>
            {selected.graph_kind}
          </p>
          {selected.summary ? <p className="mt-2 text-(--qs-text-2)">{selected.summary}</p> : null}
          {selected.rel_path ? (
            <p className="mt-1 font-mono text-xs text-cyan">{selected.rel_path}</p>
          ) : null}
          {selected.tags && selected.tags.length > 0 ? (
            <p className="mt-2 text-xs text-(--qs-text-3)">Tags: {selected.tags.join(", ")}</p>
          ) : null}
        </div>
      ) : null}
        </>
      )}
    />
  );
}
