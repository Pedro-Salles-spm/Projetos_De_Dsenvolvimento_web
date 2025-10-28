const CACHE_NAME = "yt-downloader-cache-v1";
const FILES_TO_CACHE = [
  "/index.html",
  "/manifest.json",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png"
];

// Instalando e cacheando arquivos
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(FILES_TO_CACHE);
    })
  );
  self.skipWaiting();
});

// Ativando o Service Worker e limpando caches antigos
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) return caches.delete(key);
        })
      )
    )
  );
  self.clients.claim();
});

// Interceptando requests
self.addEventListener("fetch", (event) => {
  const requestUrl = new URL(event.request.url);

  // Requests para backend.py vão direto para a rede
  if (requestUrl.pathname.includes("backend.py")) {
    event.respondWith(fetch(event.request));
  } else {
    // Cache First para os arquivos estáticos
    event.respondWith(
      caches.match(event.request).then((response) => {
        return response || fetch(event.request);
      })
    );
  }
});
