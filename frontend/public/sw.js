/** Queenswarm PWA shell — mobile/tablet offline fallback (no API cache). */
const CACHE = "queenswarm-shell-v1";
const PRECACHE = ["/offline", "/manifest.webmanifest"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))))
      .then(() => self.clients.claim()),
  );
});

function isHtmlNavigation(request) {
  return (
    request.mode === "navigate" ||
    (request.headers.get("accept") || "").includes("text/html")
  );
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") {
    return;
  }

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) {
    return;
  }

  if (url.pathname.startsWith("/api/")) {
    return;
  }

  if (url.pathname.startsWith("/_next/static/")) {
    event.respondWith(
      caches.match(request).then(
        (cached) =>
          cached ||
          fetch(request).then((response) => {
            if (response.ok) {
              const clone = response.clone();
              void caches.open(CACHE).then((cache) => cache.put(request, clone));
            }
            return response;
          }),
      ),
    );
    return;
  }

  if (
    url.pathname === "/manifest.webmanifest" ||
    url.pathname === "/icon" ||
    url.pathname === "/apple-icon" ||
    url.pathname === "/sw.js" ||
    url.pathname === "/offline"
  ) {
    event.respondWith(
      caches.match(request).then((cached) => cached || fetch(request)),
    );
    return;
  }

  if (isHtmlNavigation(request)) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response.ok) {
            const clone = response.clone();
            void caches.open(CACHE).then((cache) => cache.put(request, clone));
          }
          return response;
        })
        .catch(async () => {
          const cachedPage = await caches.match(request);
          if (cachedPage) {
            return cachedPage;
          }
          const offline = await caches.match("/offline");
          if (offline) {
            return offline;
          }
          return caches.match("/login");
        }),
    );
  }
});
