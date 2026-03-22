// ─────────────────────────────────────────────────────────────────────────────
// SERVICE WORKER · Pollenflug PWA
// Cache-first for static assets, Network-first for data.json
// ─────────────────────────────────────────────────────────────────────────────
const CACHE_VERSION = "pollen-v12";
const STATIC_CACHE  = `${CACHE_VERSION}-static`;
const DATA_CACHE    = `${CACHE_VERSION}-data`;

const STATIC_ASSETS = [
  "./",
  "./index.html",
  "./manifest.json",
  "./apple-touch-icon.png",
  "./icon.svg",
];

// ── INSTALL ──────────────────────────────────────────────────────────────────
self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then(cache => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

// ── ACTIVATE ─────────────────────────────────────────────────────────────────
self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(k => k.startsWith("pollen-") && k !== STATIC_CACHE && k !== DATA_CACHE)
          .map(k => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

// ── FETCH ────────────────────────────────────────────────────────────────────
self.addEventListener("fetch", event => {
  const url = new URL(event.request.url);

  // Network-first for data.json (fresh pollen data matters)
  if (url.pathname.endsWith("data.json") || url.pathname.endsWith("data.json/")) {
    event.respondWith(networkFirstData(event.request));
    return;
  }

  // Network-first for index.html (always serve latest app version)
  if (url.origin === self.location.origin &&
      (url.pathname === "/" || url.pathname.endsWith("/index.html") || url.pathname.endsWith("/"))) {
    event.respondWith(networkFirstData(event.request));
    return;
  }

  // Cache-first for other static assets (icons, manifest, …)
  if (url.origin === self.location.origin) {
    event.respondWith(cacheFirstStatic(event.request));
    return;
  }

  // For external APIs (Open-Meteo, ipwho.is) — network only, no caching
  event.respondWith(fetch(event.request).catch(() => new Response("", { status: 503 })));
});

// Network-first strategy with data cache fallback
async function networkFirstData(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(DATA_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;
    return new Response(JSON.stringify({ error: "offline", regions: [] }), {
      headers: { "Content-Type": "application/json" }
    });
  }
}

// Cache-first strategy with network fallback and offline page
async function cacheFirstStatic(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    // Offline fallback: serve index.html for navigation requests
    if (request.mode === "navigate") {
      const fallback = await caches.match("./index.html");
      if (fallback) return fallback;
    }
    return new Response("Offline", { status: 503 });
  }
}
