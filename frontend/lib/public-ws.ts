"use client";

/**
 * Builds a websocket URL sibling to the REST API base (`NEXT_PUBLIC_API_BASE`).
 */
export function buildHiveWebsocketHref(
  httpApiRoot: string,
  restSubpathFromV1Root: string,
): string | null {
  try {
    const resolvedRoot =
      httpApiRoot.startsWith("http://") || httpApiRoot.startsWith("https://")
        ? httpApiRoot
        : `${typeof window !== "undefined" ? window.location.origin : "http://localhost:3000"}${httpApiRoot.startsWith("/") ? httpApiRoot : `/${httpApiRoot}`}`;

    const u = new URL(resolvedRoot);
    u.protocol = u.protocol === "https:" ? "wss:" : "ws:";
    const basePath = u.pathname.replace(/\/$/, "");
    const suffix = restSubpathFromV1Root.startsWith("/")
      ? restSubpathFromV1Root.slice(1)
      : restSubpathFromV1Root;
    u.pathname = `${basePath}/${suffix}`;
    return u.toString();
  } catch {
    return null;
  }
}
