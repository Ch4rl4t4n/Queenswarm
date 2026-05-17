export interface SectionFilterableItem {
  title: string;
  description: string;
}

export type SectionDensity = "comfortable" | "compact";

export function filterSectionNavItems<T extends SectionFilterableItem>(items: T[], query: string): T[] {
  const normalized = query.trim().toLowerCase();
  if (!normalized) {
    return items;
  }
  return items.filter((item) => {
    const haystack = `${item.title} ${item.description}`.toLowerCase();
    return haystack.includes(normalized);
  });
}

export function sectionDensityClass(density: SectionDensity): string {
  return density === "compact" ? "p-3" : "p-4";
}
