var CACHE_NAME = 'vyayam-v2';
var OFFLINE_URL = '/offline/';

self.addEventListener('install', function(e) {
  // R2-U9: pre-cache the offline page so a dead connection shows an
  // honest "you're offline" screen instead of a broken fetch.
  e.waitUntil(
    caches.open(CACHE_NAME).then(function(cache) {
      return cache.add(OFFLINE_URL).catch(function() {});
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', function(e) {
  e.waitUntil(
    caches.keys().then(function(names) {
      return Promise.all(
        names.filter(function(n) { return n !== CACHE_NAME; })
             .map(function(n) { return caches.delete(n); })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', function(e) {
  if (e.request.method !== 'GET') return;

  // R2-U9: page navigations fall back to the offline screen
  if (e.request.mode === 'navigate') {
    e.respondWith(
      fetch(e.request).catch(function() {
        return caches.match(OFFLINE_URL);
      })
    );
    return;
  }

  // Static assets: network first, cache fallback
  if (e.request.url.indexOf('/static/') === -1) return;
  e.respondWith(
    fetch(e.request).then(function(response) {
      var clone = response.clone();
      caches.open(CACHE_NAME).then(function(cache) {
        cache.put(e.request, clone);
      });
      return response;
    }).catch(function() {
      return caches.match(e.request);
    })
  );
});
