export type HubSection = "overview" | "execution" | "knowledge" | "integrations";

export function hubFallbackTarget(section: HubSection): string {
  if (section === "overview") {
    return "/";
  }
  if (section === "execution") {
    return "/tasks";
  }
  if (section === "knowledge") {
    return "/hive-mind";
  }
  return "/connectors";
}
