/* Run우리 service worker — 정적 자산은 캐시, html·데이터는 network-first(오프라인이면 캐시 → 오프라인 안내 페이지) */
const VER = 'rw-v1';
const C_STATIC = VER + '-static', C_PAGES = VER + '-pages', C_DATA = VER + '-data';
const PRECACHE = ['/offline.html', '/site.css', '/components.css', '/design-tokens.css', '/app.js', '/data.js',
  '/assets/logo/runwoori-wordmark-light-small.svg', '/assets/logo/icon-any-192.png', '/assets/logo/favicon.svg'];
const FONT_HOSTS = ['fonts.googleapis.com', 'fonts.gstatic.com', 'cdn.jsdelivr.net'];
const MAX_PAGES = 60;

self.addEventListener('install', e => {
  e.waitUntil(caches.open(C_STATIC).then(c => Promise.all(PRECACHE.map(u => c.add(new Request(u, { cache: 'reload' })).catch(() => {})))).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k.startsWith('rw-') && !k.startsWith(VER)).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});

function trim(cache, max) { return cache.keys().then(ks => ks.length > max ? cache.delete(ks[0]).then(() => trim(cache, max)) : null); }
function networkFirst(req, cacheName, timeoutMs) {
  return caches.open(cacheName).then(cache => {
    const net = fetch(req).then(res => { if (res && res.ok) { cache.put(req, res.clone()).then(() => trim(cache, cacheName === C_PAGES ? MAX_PAGES : 40)); } return res; });
    const guarded = timeoutMs ? Promise.race([net, new Promise((_, rej) => setTimeout(() => rej(new Error('timeout')), timeoutMs))]) : net;
    return guarded.catch(() => cache.match(req).then(hit => hit || net.catch(() => null)));
  });
}
function staleWhileRevalidate(req) {
  return caches.open(C_STATIC).then(cache => cache.match(req).then(hit => {
    const net = fetch(req).then(res => { if (res && (res.ok || res.type === 'opaque')) cache.put(req, res.clone()); return res; }).catch(() => null);
    return hit || net.then(r => r || Response.error());
  }));
}

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  const same = url.origin === self.location.origin;
  if (!same && !FONT_HOSTS.includes(url.hostname)) return;          /* 광고·통계 등 외부 요청은 건드리지 않는다 */
  if (!same) { e.respondWith(staleWhileRevalidate(req)); return; }
  if (url.pathname === '/sw.js') return;

  if (req.mode === 'navigate' || (req.headers.get('accept') || '').includes('text/html')) {
    e.respondWith(networkFirst(req, C_PAGES, 5000).then(res => res || caches.match('/offline.html')));
    return;
  }
  if (url.pathname.startsWith('/data/') || url.pathname.endsWith('.json')) {
    e.respondWith(networkFirst(req, C_DATA, 6000).then(res => res || Response.error()));
    return;
  }
  e.respondWith(staleWhileRevalidate(req));
});
