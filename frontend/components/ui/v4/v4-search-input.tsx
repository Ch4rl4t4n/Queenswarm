import { Search } from "lucide-react";

import { cn } from "@/lib/utils";

interface V4SearchInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  "aria-label"?: string;
}

/** Dashboard search bar — Hive Control V4. */
export function V4SearchInput({
  value,
  onChange,
  placeholder = "Search…",
  className,
  "aria-label": ariaLabel = "Search",
}: V4SearchInputProps) {
  return (
    <div className={cn("v4-search-input", className)}>
      <Search className="v4-search-input-icon h-4 w-4" aria-hidden />
      <input
        type="search"
        className="v4-input"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label={ariaLabel}
      />
    </div>
  );
}
