"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

function VerifyRedirectInner(): null {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextPath =
    searchParams.get("next") && searchParams.get("next")!.startsWith("/") ? searchParams.get("next")! : "/";

  useEffect(() => {
    const params = new URLSearchParams();
    params.set("otp", "1");
    if (nextPath !== "/") {
      params.set("next", nextPath);
    }
    router.replace(`/login?${params.toString()}`);
  }, [router, nextPath]);

  return null;
}

export default function Verify2FAPage(): JSX.Element {
  return (
    <Suspense fallback={null}>
      <VerifyRedirectInner />
    </Suspense>
  );
}
