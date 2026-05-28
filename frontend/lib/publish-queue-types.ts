/** Publish Queue API types for Execution Studio. */

export interface PublishQueueItem {
  id: string;
  title: string;
  channel: string;
  body: string;
  body_preview: string;
  hashtags: string[];
  cta: string;
  media_url: string | null;
  media_kind: string | null;
  status: "pending" | "approved" | "rejected";
  created_at: string;
  supervisor_session_id: string | null;
  tags: string[];
  hook_variants?: { id: string; style: string; hook: string; rationale?: string }[];
}

export interface PublishQueueSnapshot {
  enabled: boolean;
  count: number;
  pending_count: number;
  approved_count: number;
  rejected_count: number;
  items: PublishQueueItem[];
}
