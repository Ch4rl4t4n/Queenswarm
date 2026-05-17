import type { SectionDensity } from "./section-hub";

export const SECTION_DENSITY_STORAGE_KEY = "queenswarm:section-density";

interface DensityStorageReader {
  getItem: (key: string) => string | null;
}

interface DensityStorageWriter {
  setItem: (key: string, value: string) => void;
}

export function resolveSectionDensity(raw: string | null): SectionDensity {
  return raw === "compact" || raw === "comfortable" ? raw : "comfortable";
}

export function readStoredSectionDensity(storage: DensityStorageReader | null | undefined): SectionDensity {
  if (!storage) {
    return "comfortable";
  }
  try {
    return resolveSectionDensity(storage.getItem(SECTION_DENSITY_STORAGE_KEY));
  } catch {
    return "comfortable";
  }
}

export function saveStoredSectionDensity(
  storage: DensityStorageWriter | null | undefined,
  density: SectionDensity,
): void {
  if (!storage) {
    return;
  }
  try {
    storage.setItem(SECTION_DENSITY_STORAGE_KEY, density);
  } catch {
    // Ignore storage write errors (privacy mode / blocked storage).
  }
}

function resolveBrowserStorage(): DensityStorageReader & DensityStorageWriter | null {
  try {
    if (typeof window === "undefined") {
      return null;
    }
    return window.localStorage;
  } catch {
    return null;
  }
}

export function readStoredSectionDensityFromBrowser(): SectionDensity {
  return readStoredSectionDensity(resolveBrowserStorage());
}

export function saveStoredSectionDensityFromBrowser(density: SectionDensity): void {
  saveStoredSectionDensity(resolveBrowserStorage(), density);
}
