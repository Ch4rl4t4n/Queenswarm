"use client";

import { CopyIcon, ExternalLinkIcon, Loader2Icon, MegaphoneIcon } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { usePlatform } from "@/components/hive/platform-context";
import { V4Badge, V4Card, V4Chip } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";
import type { LeadMagnetCatalogItem, LeadMagnetSharePackResponse } from "@/lib/hive-types";
import { cn } from "@/lib/utils";

interface LeadMagnetPanelProps {
  readonly compact?: boolean;
}

/** UGC content engine — share cards + landing links for swarm templates. */
export function LeadMagnetPanel({ compact = false }: LeadMagnetPanelProps): JSX.Element | null {
  const { hasFeature } = usePlatform();
  const [catalog, setCatalog] = useState<LeadMagnetCatalogItem[]>([]);
  const [selectedId, setSelectedId] = useState("exec-assistant");
  const [sharePack, setSharePack] = useState<LeadMagnetSharePackResponse | null>(null);
  const [channelId, setChannelId] = useState("tiktok");
  const [loading, setLoading] = useState(true);
  const [packBusy, setPackBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void hiveGet<LeadMagnetCatalogItem[]>("marketing/lead-magnets")
      .then((rows) => {
        if (!cancelled) {
          setCatalog(rows);
          if (rows[0]?.template_id) setSelectedId(rows[0].template_id);
        }
      })
      .catch(() => {
        if (!cancelled) setCatalog([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const loadSharePack = useCallback(async (templateId: string) => {
    setPackBusy(true);
    try {
      const pack = await hiveGet<LeadMagnetSharePackResponse>(
        `marketing/lead-magnets/${encodeURIComponent(templateId)}/share-pack?window_days=30`,
      );
      setSharePack(pack);
      setChannelId(pack.share_channels[0]?.id ?? "tiktok");
    } catch (e) {
      setSharePack(null);
      toast.error(e instanceof HiveApiError ? e.message : "Share pack unavailable.");
    } finally {
      setPackBusy(false);
    }
  }, []);

  useEffect(() => {
    if (!selectedId || !hasFeature("ugc_content_engine")) return;
    void loadSharePack(selectedId);
  }, [hasFeature, loadSharePack, selectedId]);

  const copyChannel = useCallback(async () => {
    const channel = sharePack?.share_channels.find((c) => c.id === channelId);
    if (!channel) return;
    try {
      await navigator.clipboard.writeText(channel.text);
      toast.success(`${channel.label} copy ready.`);
    } catch {
      toast.error("Clipboard unavailable.");
    }
  }, [channelId, sharePack]);

  if (!hasFeature("ugc_content_engine")) {
    return null;
  }

  if (loading) {
    return (
      <p className="flex items-center gap-2 text-sm text-(--qs-text-3)">
        <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> Loading lead magnets…
      </p>
    );
  }

  const activeChannel = sharePack?.share_channels.find((c) => c.id === channelId);

  return (
    <V4Card className={cn("border-magenta/25 bg-magenta/5", compact && "p-4")}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <MegaphoneIcon className="h-4 w-4 text-magenta" aria-hidden />
            <p className="text-sm font-semibold text-(--qs-text)">Lead magnets · share cards</p>
            <V4Badge tone="info">UGC engine</V4Badge>
          </div>
          <p className="mt-1 max-w-2xl text-xs text-(--qs-text-3)">
            Swarm output → TikTok / X copy + public landing. Verified hours overlay when your hive has ROI data.
          </p>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {catalog.map((item) => (
          <V4Chip key={item.template_id} active={selectedId === item.template_id} onClick={() => setSelectedId(item.template_id)}>
            {item.name}
          </V4Chip>
        ))}
      </div>

      {packBusy ? (
        <p className="mt-4 flex items-center gap-2 text-xs text-(--qs-text-3)">
          <Loader2Icon className="h-3.5 w-3.5 animate-spin" aria-hidden /> Generating share pack…
        </p>
      ) : null}

      {sharePack ? (
        <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
          <article
            className="rounded-xl border p-4"
            style={{
              borderColor: `${sharePack.accent_hex}55`,
              boxShadow: `0 0 24px ${sharePack.accent_hex}22`,
            }}
          >
            <p className="text-[10px] uppercase tracking-wider text-(--qs-text-3)">Share card preview</p>
            <h3 className="mt-2 text-lg font-semibold text-(--qs-text)">{sharePack.headline}</h3>
            <p className="mt-1 text-xs text-(--qs-text-2)">{sharePack.tagline}</p>
            <ul className="mt-3 space-y-1 text-xs text-(--qs-text-3)">
              {sharePack.bullets.map((b) => (
                <li key={b}>→ {b}</li>
              ))}
            </ul>
            <p className="mt-3 text-xs text-pollen">{sharePack.hours_attribution_line}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Link href={sharePack.landing_url.replace(/^https:\/\/[^/]+/, "")} className="qs-btn qs-btn--ghost qs-btn--sm gap-1" target="_blank">
                <ExternalLinkIcon className="h-3.5 w-3.5" aria-hidden /> Landing
              </Link>
              <Link href={sharePack.cta_url.replace(/^https:\/\/[^/]+/, "")} className="qs-btn qs-btn--primary qs-btn--sm">
                Wizard CTA
              </Link>
            </div>
          </article>

          <div className="space-y-3">
            <div className="flex flex-wrap gap-2">
              {sharePack.share_channels.map((ch) => (
                <V4Chip key={ch.id} active={channelId === ch.id} onClick={() => setChannelId(ch.id)}>
                  {ch.label}
                </V4Chip>
              ))}
            </div>
            <pre className="max-h-52 overflow-auto rounded-xl border border-(--qs-border) bg-black/40 p-3 font-mono text-[11px] text-(--qs-text-2) whitespace-pre-wrap">
              {activeChannel?.text ?? ""}
            </pre>
            <button type="button" className="qs-btn qs-btn--ghost qs-btn--sm gap-2" onClick={() => void copyChannel()}>
              <CopyIcon className="h-3.5 w-3.5" aria-hidden /> Copy {activeChannel?.label ?? "text"}
            </button>
          </div>
        </div>
      ) : null}
    </V4Card>
  );
}
