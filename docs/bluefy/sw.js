"use strict";
const CACHE_NAME = "wsprrypico-bluefy-9f4272fa74579119965beb55257d33368915499b21d08c3f25055d6b01e55523";
const CACHE_PREFIX = "wsprrypico-bluefy-";
const ASSETS = Object.freeze([
  "./", "./index.html", "./app.js", "./bluefy.js", "./manifest.webmanifest",
  "./release-manifest.json", "./style.css", "./sw.js"
]);
const ASSET_NAMES = new Set(ASSETS.map((name) => name.replace(/^\.\//, "")));

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (event) => {
  event.waitUntil(caches.keys().then((names) => Promise.all(names
    .filter((name) => name.startsWith(CACHE_PREFIX) && name !== CACHE_NAME)
    .map((name) => caches.delete(name)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  const scope = new URL(self.registration.scope);
  if (url.origin !== scope.origin || !url.pathname.startsWith(scope.pathname) || url.search)
    return;
  const relative = url.pathname.slice(scope.pathname.length);
  if (request.mode === "navigate") {
    event.respondWith(fetch(request).catch(() => caches.match("./index.html")));
    return;
  }
  if (!ASSET_NAMES.has(relative)) return;
  event.respondWith(caches.open(CACHE_NAME).then((cache) =>
    cache.match(request).then((cached) => cached || fetch(request))));
});
