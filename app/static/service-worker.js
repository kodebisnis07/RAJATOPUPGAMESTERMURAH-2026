const CACHE_NAME = 'raja-topup-cachefix-20260729-1';
const STATIC_ASSETS = [
  '/static/img/pwa/icon-192.png',
  '/static/img/pwa/icon-512.png',
  '/manifest.webmanifest?v=cachefix-20260729-1'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(STATIC_ASSETS))
      .catch(() => null)
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
    ))
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  const accept = req.headers.get('accept') || '';

  // Halaman HTML selalu dari jaringan agar perubahan layout langsung terlihat.
  if (req.mode === 'navigate' || accept.includes('text/html')) {
    event.respondWith(fetch(req, { cache: 'no-store' }));
    return;
  }

  // CSS dan JavaScript memakai network-first supaya deploy baru tidak tertahan cache lama.
  if (url.origin === self.location.origin && /\.(?:css|js)$/.test(url.pathname)) {
    event.respondWith(
      fetch(req, { cache: 'no-cache' }).then(response => {
        if (response && response.ok) {
          const copy = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(req, copy)).catch(() => null);
        }
        return response;
      }).catch(() => caches.match(req))
    );
    return;
  }

  // Ikon PWA boleh cache-first karena nama cache berubah setiap deploy.
  if (url.origin === self.location.origin && url.pathname.startsWith('/static/img/pwa/')) {
    event.respondWith(caches.match(req).then(cached => cached || fetch(req)));
  }
});
