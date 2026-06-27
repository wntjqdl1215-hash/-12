// 서비스워커: 앱 셸 캐시(오프라인에서도 화면이 뜨도록).
// 뉴스 데이터(/api/*)는 항상 네트워크 우선 — 캐시된 옛 뉴스를 보여주지 않기 위함.
const CACHE = "stock-news-v1";
const SHELL = ["/", "/index.html", "/style.css", "/app.js", "/manifest.json",
  "/icons/icon-192.png", "/icons/icon-512.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const { request } = e;
  const url = new URL(request.url);

  // API는 네트워크 우선
  if (url.pathname.startsWith("/api/")) {
    e.respondWith(fetch(request).catch(() => new Response("{}", { headers: { "Content-Type": "application/json" } })));
    return;
  }
  // 정적 셸은 캐시 우선
  e.respondWith(
    caches.match(request).then((cached) => cached || fetch(request).then((res) => {
      const copy = res.clone();
      caches.open(CACHE).then((c) => c.put(request, copy)).catch(() => {});
      return res;
    }).catch(() => caches.match("/index.html")))
  );
});
