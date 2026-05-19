import { NextResponse } from "next/server";

/** Edge health for login hive probe in dev; prod nginx still proxies ``/health`` to backend. */
export async function GET(): Promise<NextResponse> {
  const origin = process.env.INTERNAL_BACKEND_ORIGIN?.trim() || "http://127.0.0.1:8000";
  try {
    const upstream = await fetch(`${origin.replace(/\/$/, "")}/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });
    const body = await upstream.text();
    return new NextResponse(body, {
      status: upstream.status,
      headers: { "Content-Type": upstream.headers.get("Content-Type") ?? "application/json" },
    });
  } catch {
    return NextResponse.json({ status: "degraded", detail: "Backend health unreachable from frontend." }, { status: 503 });
  }
}
