import Link from "next/link";

interface SectionNavItem {
  href: string;
  title: string;
  description: string;
}

interface SectionNavGridProps {
  items: SectionNavItem[];
}

export function SectionNavGrid({ items }: SectionNavGridProps): JSX.Element {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {items.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className="group rounded-2xl border border-cyan/20 bg-black/25 p-4 transition hover:border-pollen/40 hover:bg-black/35"
          prefetch
        >
          <p className="font-[family-name:var(--font-poppins)] text-sm font-semibold text-zinc-100 group-hover:text-pollen">
            {item.title}
          </p>
          <p className="mt-1 text-xs text-zinc-400">{item.description}</p>
        </Link>
      ))}
    </div>
  );
}
