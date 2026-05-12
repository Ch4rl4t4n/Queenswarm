/**
 * WebSocket helpers for the hive UI.
 *
 * URL construction is isomorphic (`buildHiveWebsocketHref`); connection logic
 * lives in components/hooks (`useEffect` + `Reconnecting WebSocket`).
 */

export { buildHiveWebsocketHref } from "./hive-ws-url";

/** Conservative defaults when implementing auto-reconnect in client hooks. */
export const HIVE_WS_RECONNECT_MS = [1000, 2000, 5000, 10000] as const;
