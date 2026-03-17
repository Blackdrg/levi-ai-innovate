const CACHE_NAME = 'levi-v2';
const ASSETS = [
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

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
  );
});

self.addEventListener('fetch', (e) => {
  e.respondWith(
    caches.match(e.request).then((res) => res || fetch(e.request))
  );
});
