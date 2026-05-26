/** Minimal route transition indicator — avoids heavy skeleton flash on navigation. */
export function RoutePulseLoading() {
  return (
    <div className="route-pulse-loading" role="status" aria-label="Loading">
      <span className="route-pulse-loading-bar" aria-hidden />
    </div>
  );
}
