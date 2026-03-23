// DEPLOY: 2026-03-23 — bump this string on every deploy
const CACHE_NAME = 'levi-v5.2-20260323';

const ASSETS = [
  './',
  'index.html',
  'chat.html',
  'quotes.html',
  'studio.html',
  'feed.html',
  'my-gallery.html',
  'auth.html',
  'terms.html',
  'privacy.html',
  'css/output.css?v=' + Date.now(),
  'css/animations.css?v=' + Date.now(),
  'js/ui.js?v=' + Date.now(),
  'js/api.js?v=' + Date.now(),
  'js/chat.js?v=' + Date.now(),
  'js/quotes.js?v=' + Date.now(),
  'js/studio.js?v=' + Date.now(),
  'js/my-gallery.js?v=' + Date.now(),
  'manifest.json'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(key => key !== CACHE_NAME)
          .map(key => caches.delete(key))
      );
    })
  );
});

self.addEventListener('fetch', event => {
  // Simple cache-first for assets, network-first for API
  if (event.request.url.includes('/api/')) {
    event.respondWith(
      fetch(event.request).catch(() => caches.match(event.request))
    );
  } else {
    event.respondWith(
      caches.match(event.request)
        .then(response => response || fetch(event.request))
    );
  }
});

/* 
  ── Push Notifications ──
  NOTE: This is a placeholder. Server-side subscription management 
  is not yet implemented in the backend.
*/
self.addEventListener('push', event => {
  const options = {
    body: event.data ? event.data.text() : 'New wisdom awaits...',
    icon: '/icon-192.png',
    badge: '/badge.png',
    actions: [{action: 'share', title: 'Share Quote'}]
  };
  event.waitUntil(self.registration.showNotification('LEVI Daily Quote', options));
});
