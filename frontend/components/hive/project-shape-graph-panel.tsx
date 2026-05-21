"use client";

import "@xyflow/react/dist/style.css";

import type { Edge, Node } from "@xyflow/react";
import { Background, Controls, ReactFlow, ReactFlowProvider, useEdgesState, useNodesState } from "@xyflow/react";
import { FolderTree, Loader2Icon, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { usePlatform } from "@/components/hive/platform-context";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
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

const KIND_TONE: Record<string, string> = {
  GraphifyBatch: "border-pollen/50 bg-pollen/10",
  VaultFolder: "border-cyan/40 bg-cyan/5",
  VaultDocument: "border-(--qs-green)/35 bg-(--qs-green)/5",
  Tag: "border-(--qs-magenta)/30 bg-(--qs-magenta)/5",
};

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

/** Project folder tree viz — Auto-Graphify VaultFolder → VaultDocument graph lane. */
export function ProjectShapeGraphPanel(): JSX.Element | null {
  const { hasFeature } = usePlatform();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [payload, setPayload] = useState<ProjectShapePayload | null>(null);
  const [selected, setSelected] = useState<ProjectShapeNode | null>(null);
  const [flowNodes, setFlowNodes, onNodesChange] = useNodesState<Node>([]);
  const [flowEdges, setFlowEdges, onEdgesChange] = useEdgesState<Edge>([]);

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
          position: positions.get(node.id) ?? { x: 0, y: 0 },
          data: {
            label: node.label,
            subtitle: node.summary ?? node.rel_path ?? "",
            kind: node.graph_kind ?? "Node",
          },
          className: cn(
            "rounded-lg border px-2 py-1 text-[10px] font-medium shadow-sm",
            KIND_TONE[node.graph_kind ?? ""] ?? "border-white/15 bg-black/40",
          ),
        })),
      );
      setFlowEdges(
        body.edges.map((edge, idx) => ({
          id: `ps-${idx}-${edge.source}-${edge.target}`,
          source: edge.source,
          target: edge.target,
          label: edge.kind ?? "",
          animated: edge.kind === "CONTAINS",
        })),
      );
    } catch (e) {
      setError(e instanceof HiveApiError ? e.message : "Project shape graph unavailable.");
    } finally {
      setLoading(false);
    }
  }, [setFlowEdges, setFlowNodes]);

  useEffect(() => {
    void load();
  }, [load]);

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

  return (
    <V4Card className="v4-card-interactive border-(--qs-green)/25">
      <V4CardHeader
        title="Project shape map"
        description="Folder hierarchy from Auto-Graphify — vault folders, documents, and ingest batches in Neo4j."
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

      {error ? <p className="text-sm text-(--qs-red)">{error}</p> : null}

      {!loading && !error && (payload?.nodes.length ?? 0) === 0 ? (
        <p className="text-sm text-(--qs-text-3)">
          No project shape yet — upload a folder via Auto-Graphify above to populate vault + graph nodes.
        </p>
      ) : null}

      <div className="relative min-h-[280px] h-[min(42vh,360px)] rounded-xl border border-cyan/15 bg-black/30">
        {loading ? (
          <div className="absolute inset-0 z-10 flex items-center justify-center gap-2 text-sm text-(--qs-text-3)">
            <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> Loading project shape…
          </div>
        ) : null}
        <ReactFlowProvider>
          <ReactFlow
            nodes={flowNodes}
            edges={flowEdges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={(_, node) => {
              const match = payload?.nodes.find((n) => n.id === node.id) ?? null;
              setSelected(match);
            }}
            fitView
            panOnDrag
            minZoom={0.35}
            maxZoom={1.4}
          >
            <Background gap={28} />
            <Controls />
          </ReactFlow>
        </ReactFlowProvider>
      </div>

      {selected ? (
        <div className="mt-3 rounded-lg border border-white/10 bg-black/25 p-3 text-sm">
          <p className="font-medium text-(--qs-text)">{selected.label}</p>
          <p className="text-xs uppercase tracking-wide text-(--qs-text-3)">{selected.graph_kind}</p>
          {selected.summary ? <p className="mt-2 text-(--qs-text-2)">{selected.summary}</p> : null}
          {selected.rel_path ? (
            <p className="mt-1 font-mono text-xs text-cyan">{selected.rel_path}</p>
          ) : null}
          {selected.tags && selected.tags.length > 0 ? (
            <p className="mt-2 text-xs text-(--qs-text-3)">Tags: {selected.tags.join(", ")}</p>
          ) : null}
        </div>
      ) : null}
    </V4Card>
  );
}
