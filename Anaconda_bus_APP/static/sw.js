const CACHE_NAME = "app-cache-v1";
const urlsToCache = [
    "/", 
    "/static/css/navigation.css",  // تأكد من وجوده
    "/static/icons/icon-192x192.png",  // تأكد من وجوده
    "/static/js/app.js",  // تحقق من وجود أي ملفات JS تحاول تخزينها
    "/static/manifest.json",
];

self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(urlsToCache).catch(err => console.error("Cache addAll failed", err));
        })
    );
});

self.addEventListener("fetch", (event) => {
    event.respondWith(
        caches.match(event.request).then((response) => {
            return response || fetch(event.request);
        })
    );
});
