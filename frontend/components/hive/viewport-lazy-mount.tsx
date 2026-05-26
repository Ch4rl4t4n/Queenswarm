"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

interface ViewportLazyMountProps {
  children: ReactNode;
  /** Placeholder height before the child mounts (avoids layout shift). */
  minHeight?: string;
  /** Preload when within this margin of the viewport. */
  rootMargin?: string;
}

/** Mount children only when near the viewport — defers heavy charts and panels. */
export function ViewportLazyMount({
  children,
  minHeight = "14rem",
  rootMargin = "240px 0px",
}: ViewportLazyMountProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el || visible) {
      return undefined;
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [rootMargin, visible]);

  return (
    <div ref={ref} style={visible ? undefined : { minHeight }}>
      {visible ? children : null}
    </div>
  );
}
