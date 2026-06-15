"use client";

import "@/styles/marketing-base.css";
import "@/styles/marketing.css";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { LacIcon } from "@/components/marketing/lac-icons";
import { LacWordmark } from "@/components/marketing/lac-wordmark";

interface MarketingShellProps {
  readonly children: ReactNode;
}

const NAV = [
  { key: "home", label: "Home", route: "/" },
  { key: "skills", label: "Catalog", route: "/skills" },
  { key: "eval", label: "Free eval", route: "/skills/eval" },
  { key: "how", label: "How it works", route: "/how-it-works" },
  { key: "verify", label: "Verify-first", route: "/verify-first" },
] as const;

function isNavActive(pathname: string, route: string): boolean {
  if (route === "/skills/eval") {
    return pathname === "/skills/eval";
  }
  if (route === "/skills") {
    return (
      pathname === "/skills" ||
      (pathname.startsWith("/skills/") && !pathname.startsWith("/skills/eval"))
    );
  }
  return pathname === route;
}

function MarketingFooter(): JSX.Element {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);

  return (
    <footer className="mk-footer">
      <div className="mk-wrap">
        <div className="mk-news">
          <div>
            <h3>Get notified when new skills drop</h3>
            <p>Occasional emails about verified releases and bundles. No spam, unsubscribe anytime.</p>
          </div>
          <form
            className="mk-news-form"
            onSubmit={(event) => {
              event.preventDefault();
              if (email.trim()) {
                setSent(true);
              }
            }}
          >
            {sent ? (
              <div className="row gap-2" style={{ color: "oklch(0.85 0.14 155)", fontWeight: 600, padding: "13px 0" }}>
                <LacIcon name="check" size={18} />
                You&apos;re on the list.
              </div>
            ) : (
              <>
                <input
                  type="email"
                  required
                  placeholder="you@email.com"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
                <button className="btn btn-gold" type="submit">
                  Notify me
                </button>
              </>
            )}
          </form>
        </div>

        <div className="mk-foot-grid">
          <div className="mk-foot-col">
            <LacWordmark showTagline={false} />
            <p className="text-3 fs-13" style={{ marginTop: 14, maxWidth: 280, lineHeight: 1.55 }}>
              A curated marketplace of verified agent skills and content packs. Every listing is simulate-first and
              quality-scored before it ships.
            </p>
          </div>
          <div className="mk-foot-col">
            <h5>Browse</h5>
            <Link href="/skills">All skills</Link>
            <Link href="/skills">Verified skills</Link>
            <Link href="/skills">Content packs</Link>
            <Link href="/skills">Featured</Link>
          </div>
          <div className="mk-foot-col">
            <h5>Learn</h5>
            <Link href="/how-it-works">How it works</Link>
            <Link href="/verify-first">Verify-first</Link>
            <span style={{ opacity: 0.55, display: "block", padding: "5px 0", fontSize: 14 }}>Free eval checklist</span>
            <span style={{ opacity: 0.55, display: "block", padding: "5px 0", fontSize: 14 }}>Categories</span>
          </div>
          <div className="mk-foot-col">
            <h5>Marketplaces</h5>
            <a href="https://gumroad.com" target="_blank" rel="noopener noreferrer">
              Gumroad
            </a>
            <span style={{ opacity: 0.55, display: "block", padding: "5px 0", fontSize: 14 }}>More — coming soon</span>
          </div>
        </div>

        <div className="mk-foot-bar">
          <span>© 2026 Let Agents Cook. All skills independently verified.</span>
          <span className="row gap-4">
            <Link href="/terms" className="text-4">
              Terms
            </Link>
            <Link href="/privacy" className="text-4">
              Privacy
            </Link>
          </span>
        </div>
      </div>
    </footer>
  );
}

export function MarketingShell({ children }: MarketingShellProps): JSX.Element {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  return (
    <div className="mk-shell">
      <header className="mk-nav">
        <div className="mk-wrap mk-nav-inner">
          <LacWordmark />
          <nav className="mk-links">
            {NAV.map((item) => (
              <Link
                key={item.key}
                href={item.route}
                className={`mk-link${isNavActive(pathname, item.route) ? " active" : ""}`}
              >
                {item.label}
              </Link>
            ))}
            <span className="mk-link" title="Coming soon" style={{ opacity: 0.75 }}>
              Free eval checklist
              <span className="soon-dot">soon</span>
            </span>
          </nav>
          <div className="mk-nav-cta">
            <Link href="/skills" className="btn btn-primary">
              Browse skills
            </Link>
            <button
              type="button"
              className="mk-burger"
              onClick={() => setMenuOpen((open) => !open)}
              aria-label="Menu"
            >
              <LacIcon name={menuOpen ? "close" : "menu"} size={20} />
            </button>
          </div>
        </div>
        <div className={`mk-mobile-menu${menuOpen ? " open" : ""}`}>
          {NAV.map((item) => (
            <Link
              key={item.key}
              href={item.route}
              className={`mk-link${isNavActive(pathname, item.route) ? " active" : ""}`}
            >
              {item.label}
            </Link>
          ))}
          <span className="mk-link" style={{ opacity: 0.6 }}>
            Free eval checklist
            <span className="soon-dot">soon</span>
          </span>
          <Link href="/skills" className="btn btn-primary btn-block mt-4">
            Browse skills
          </Link>
        </div>
      </header>

      <main style={{ flex: 1 }}>{children}</main>

      <MarketingFooter />
    </div>
  );
}
