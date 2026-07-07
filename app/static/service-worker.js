const CACHE_NAME = 'raja-topup-cache-v10-banner-20260707';
const STATIC_ASSETS = [
  '/static/css/style.css?v=fix-sosmed-20260701',
  '/static/img/pwa/icon-192.png',
  '/static/img/pwa/icon-512.png',
  '/manifest.webmanifest'
];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS)).catch(() => null));
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(keys.map(k => caches.delete(k))))
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;

  // Jangan cache halaman HTML/form auth agar /auth/daftar tidak ketukar dengan homepage lama.
  const accept = req.headers.get('accept') || '';
  if (req.mode === 'navigate' || accept.includes('text/html')) {
    event.respondWith(fetch(req));
    return;
  }

  // Cache hanya asset static.
  if (new URL(req.url).pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(req).then(cached => cached || fetch(req).then(response => {
        const copy = response.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(req, copy)).catch(() => null);
        return response;
      }))
    );
  }
});
