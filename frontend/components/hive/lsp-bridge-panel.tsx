"use client";

import { Loader2Icon, SearchIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hivePostJson } from "@/lib/api";
import type { HarnessSnapshotPayload } from "@/lib/hive-types";

interface LspBridgePanelProps {
  snapshot: HarnessSnapshotPayload;
}

interface LspResolveResponse {
  tool: string;
  query: string;
  matches: Array<{ name: string; kind: string; path: string; line: number; signature?: string | null }>;
}

/** Symbol-aware LSP + MCP bridge tester (lightweight AST index). */
export function LspBridgePanel({ snapshot }: LspBridgePanelProps): JSX.Element {
  const bridge = snapshot.lsp_bridge;
  const [query, setQuery] = useState("HarnessSnapshot");
  const [busy, setBusy] = useState(false);
  const [matches, setMatches] = useState<LspResolveResponse["matches"]>([]);

  async function resolveSymbol(): Promise<void> {
    const q = query.trim();
    if (q.length < 2) {
      toast.error("Query must be at least 2 characters.");
      return;
    }
    setBusy(true);
    try {
      const res = await hivePostJson<LspResolveResponse>("harness/lsp-bridge/resolve", { query: q });
      setMatches(res.matches);
      toast.success(`Found ${res.matches.length} symbol(s)`);
    } catch (e) {
      toast.error(e instanceof HiveApiError ? e.message : "Symbol resolve failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <V4Card>
      <V4CardHeader
        kicker="LSP + MCP bridge"
        title="Symbol-aware context"
        description="Lightweight repo index exposed as MCP tools for coder sub-agents (enable LSP_MCP_BRIDGE_ENABLED on prod)."
      />
      <div className="mb-4 flex flex-wrap gap-2">
        <V4Badge tone={bridge?.enabled ? "ok" : "warn"}>
          Bridge {bridge?.enabled ? "on" : "off"}
        </V4Badge>
        {bridge?.tools?.map((tool) => (
          <V4Badge key={tool} tone="info">
            {tool}
          </V4Badge>
        ))}
      </div>
      <div className="flex flex-wrap gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="qs-input min-w-[200px] flex-1 font-mono text-xs"
          placeholder="Symbol name e.g. HarnessSnapshot"
        />
        <button
          type="button"
          disabled={busy || !bridge?.enabled}
          onClick={() => void resolveSymbol()}
          className="qs-btn qs-btn--primary qs-btn--sm inline-flex items-center gap-1.5"
        >
          {busy ? (
            <Loader2Icon className="h-3.5 w-3.5 animate-spin" aria-hidden />
          ) : (
            <SearchIcon className="h-3.5 w-3.5" aria-hidden />
          )}
          Resolve
        </button>
      </div>
      {!bridge?.enabled ? (
        <p className="mt-3 text-xs text-(--qs-text-3)">
          Set <code className="font-mono">LSP_MCP_BRIDGE_ENABLED=true</code> in production env to activate registry
          tools and supervisor prompt injection.
        </p>
      ) : null}
      {matches.length > 0 ? (
        <ul className="mt-4 space-y-2 text-xs font-mono">
          {matches.map((m) => (
            <li key={`${m.path}:${m.line}:${m.name}`} className="rounded-lg border border-(--qs-border) bg-black/20 p-2">
              <span className="text-(--qs-cyan)">{m.kind}</span> {m.name} @ {m.path}:{m.line}
              {m.signature ? <span className="text-(--qs-text-3)"> — {m.signature}</span> : null}
            </li>
          ))}
        </ul>
      ) : null}
    </V4Card>
  );
}
