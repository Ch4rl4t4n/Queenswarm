import { NextRequest, NextResponse } from "next/server";

const METHODS_WITH_BODY = new Set(["POST", "PATCH", "PUT"]);

function forbidSegments(segments: string[]): boolean {
  return segments.some((s) => s.includes("..") || s.includes("\\"));
}

async function relay(
  request: NextRequest,
  segments: string[],
  method: string,
): Promise<NextResponse> {
  const origin = process.env.INTERNAL_BACKEND_ORIGIN;
  const token = process.env.HIVE_PROXY_JWT;
  if (!origin || !token || token === "unset") {
    return NextResponse.json({ detail: "Hive proxy JWT is not configured." }, { status: 503 });
  }
  if (forbidSegments(segments)) {
    return NextResponse.json({ detail: "Unsafe path segments." }, { status: 400 });
  }

  const path = segments.join("/");
  const target = new URL(`${origin}/api/v1/${path}`);
  target.search = request.nextUrl.search;

  const hdrs: Record<string, string> = { Authorization: `Bearer ${token}` };
  const payload = METHODS_WITH_BODY.has(method) ? await request.arrayBuffer() : undefined;
  if (payload !== undefined && payload.byteLength > 0) {
    const ct = request.headers.get("content-type");
    if (ct) {
      hdrs["Content-Type"] = ct;
    }
  }

  const res = await fetch(target, {
    method,
    headers: hdrs,
    ...(payload !== undefined && payload.byteLength > 0 ? { body: payload } : {}),
    cache: "no-store",
  });

  const resBody = Buffer.from(await res.arrayBuffer());
  const contentType = res.headers.get("content-type") ?? "application/octet-stream";
  return new NextResponse(resBody, {
    status: res.status,
    headers: { "Content-Type": contentType },
  });
}

type Params = Promise<{ path: string[] | undefined }>;

export async function GET(request: NextRequest, ctx: { params: Params }): Promise<NextResponse> {
  const path = ((await ctx.params).path ?? []).filter(Boolean);
  return relay(request, path, "GET");
}

export async function POST(request: NextRequest, ctx: { params: Params }): Promise<NextResponse> {
  const path = ((await ctx.params).path ?? []).filter(Boolean);
  return relay(request, path, "POST");
}

export async function PATCH(request: NextRequest, ctx: { params: Params }): Promise<NextResponse> {
  const path = ((await ctx.params).path ?? []).filter(Boolean);
  return relay(request, path, "PATCH");
}

export async function PUT(request: NextRequest, ctx: { params: Params }): Promise<NextResponse> {
  const path = ((await ctx.params).path ?? []).filter(Boolean);
  return relay(request, path, "PUT");
}

export async function DELETE(
  request: NextRequest,
  ctx: { params: Params },
): Promise<NextResponse> {
  const path = ((await ctx.params).path ?? []).filter(Boolean);
  return relay(request, path, "DELETE");
}
