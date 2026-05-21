import { HiveApiError } from "@/lib/api";

/** Normalize roster/summary fetch failures for operator-facing banners. */
export function formatAgentsFetchError(error: unknown): string | null {
  if (!error) {
    return null;
  }
  if (error instanceof HiveApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Agents data unavailable";
}
