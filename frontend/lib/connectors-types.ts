/** Shared Dynamic Connector Hub payloads mirrored from FastAPI ``DynamicConnectorPublic``. */

export interface DynamicConnectorPayload {
  id: string;
  slug: string;
  display_name: string;
  base_url: string | null;
  auth_type: string;
  mcp_manifest: Record<string, unknown> | null;
  allowed_manager_slugs: string[];
  is_active: boolean;
  is_builtin: boolean;
  builtin_kind: string | null;
  last_tested_at: string | null;
}
