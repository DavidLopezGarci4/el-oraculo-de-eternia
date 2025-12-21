const CACHE_NAME = "oraculo-eternia-v1";
const ASSETS_TO_CACHE = [
    "./",
    "./static/manifest.json",
    "./static/logo_masters_192.png",
    "./static/logo_masters_512.png"
];

// Install Event
self.addEventListener("install", (event) => {
    console.log("[Service Worker] Install");
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log("[Service Worker] Caching files");
            return cache.addAll(ASSETS_TO_CACHE);
        })
    );
    self.skipWaiting();
});

// Activate Event
self.addEventListener("activate", (event) => {
    console.log("[Service Worker] Activate");
    event.waitUntil(
        caches.keys().then((keyList) => {
            return Promise.all(
                keyList.map((key) => {
                    if (key !== CACHE_NAME) {
                        console.log("[Service Worker] Removing old cache", key);
                        return caches.delete(key);
                    }
                })
            );
        })
    );
    return self.clients.claim();
});

// Fetch Event
self.addEventListener("fetch", (event) => {
    // Only cache GET requests
    if (event.request.method !== "GET") return;

    // Streamlit uses WSS for updates, ignore those
    if (event.request.url.includes("_stcore/stream")) return;

    event.respondWith(
        caches.match(event.request).then((response) => {
            return response || fetch(event.request).then((networkResponse) => {
                // Check if valid response
                if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== 'basic') {
                    return networkResponse;
                }

                // Clone response to cache it (streams can be consumed once)
                const responseToCache = networkResponse.clone();

                // Cache dynamic content (stale-while-revalidate strategy sorta)
                caches.open(CACHE_NAME).then((cache) => {
                    // Limit cache size? not for now
                    cache.put(event.request, responseToCache);
                });

                return networkResponse;
            }).catch(() => {
                // Offline fallback logic could go here
                console.log("[Service Worker] Use Offline Fallback if available");
            });
        })
    );
});
