import { HivePageShellSkeleton } from "@/components/hive/hive-page-shell-skeleton";

/** App Router loading segment for routes with HivePageShell subnav. */
export default function HivePageSubnavRouteLoadingPage() {
  return <HivePageShellSkeleton withSubnav />;
}
