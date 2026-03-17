const CACHE_NAME = 'levi-v4-final';
// Last Updated: 2026-03-18 00:20:00
const ASSETS = [
  './',
  'index.html',
  'chat.html',
  'quotes.html',
  'my-gallery.html',
  'auth.html',
  'terms.html',
  'privacy.html',
  'css/styles.css',
  'css/animations.css',
  'js/ui.js',
  'js/api.js',
  'js/chat.js',
  'js/quotes.js',
  'js/my-gallery.js',
  'js/auth.js',
  'manifest.json'
];

// Network-First Strategy: Try to fetch from network first, fall back to cache
self.addEventListener('fetch', (event) => {
  // Only handle GET requests for our assets
  if (event.request.method !== 'GET') return;
  
  // Don't cache API calls (we want fresh wisdom!)
  if (event.request.url.includes('/api/') || event.request.url.includes(':8000')) {
    event.respondWith(fetch(event.request));
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // If the request was successful, clone the response and put it in the cache
        if (response.status === 200) {
          const responseToCache = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });
        }
        return response;
      })
      .catch(() => {
        // If the network request failed, try to get it from the cache
        return caches.match(event.request);
      })
  );
});

// Clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('[SW] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});
