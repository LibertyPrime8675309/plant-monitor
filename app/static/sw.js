/* Plant record service worker (1.24.0): lets the app open and show what this device has saved when there is no connection.
   - The app's own files: from the network when it answers, else the saved copy.
   - /api/ answers (GET): from the network when it answers within a few seconds (and saved), else the saved copy, marked with
     the X-Offline-Saved header so the page can say it is showing what was saved, and when.
   - Photos: the saved copy first (they never change once added), else the network (and saved).
   Changes made while offline are not handled here: the page keeps them in its outbox and sends them when it is back online. */
const VERSION = '__VERSION__';
const SHELL = 'plantdb-shell-' + VERSION, API = 'plantdb-api', PICS = 'plantdb-photos', LIBPICS = 'plantdb-library-photos';
const SHELL_FILES = ['/', '/js/core.js', '/js/gallery.js', '/js/plant.js', '/js/care.js', '/js/edit.js', '/js/weather.js', '/js/frostdates.js', '/js/ui.js', '/js/lights.js', '/js/events.js', '/js/discover.js', '/js/offline.js', '/js/notify.js', '/js/sensors.js', '/js/review.js', '/js/main.js', '/style.css', '/prefs.js', '/card.html', '/card.js', '/manifest.webmanifest', '/icon.svg', '/icon-192.png', '/icon-512.png'];
const NO_SAVE = /^\/api\/(people|backups|ingest|weather\/job|backups\/job|audit|library\/prefetch|library\/local|offline\/|identify\/settings|calendar\/settings|me$)/;
const WAIT_MS = 5000;
let downUntil = 0;                           // after the server fails to answer, use saved copies at once for a while (weak signal)
const quick = () => Date.now() < downUntil;   // 1.38.0: navigator.onLine is not trusted here: on phones it can stay wrong after a VPN comes back
const wentDown = () => { downUntil = Date.now() + 30000; };
async function tryNet(req) {
  if (req.headers.get('X-Probe')) {          // 1.38.0: the page asking whether the server is back: always ask it, and forget the failures if it answers
    try { const r = await timeout(fetch(req), 8000); downUntil = 0; return r; } catch (e) { wentDown(); throw e; }
  }
  if (quick()) { fetch(req).then(() => { downUntil = 0; }, () => {}); throw new Error('offline'); }   // see if it is back, without waiting
  try { const r = await timeout(fetch(req), WAIT_MS); downUntil = 0; return r; } catch (e) { wentDown(); throw e; }
}

self.addEventListener('install', e => {
  e.waitUntil(caches.open(SHELL).then(c => Promise.all(SHELL_FILES.map(u => c.add(new Request(u, { cache: 'reload' })).catch(() => null)))).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k.startsWith('plantdb-shell-') && k !== SHELL).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});

function timeout(p, ms) { return new Promise((ok, no) => { const t = setTimeout(() => no(new Error('timeout')), ms); p.then(v => { clearTimeout(t); ok(v); }, e => { clearTimeout(t); no(e); }); }); }
function stamp(resp) {                       // a copy of the answer that remembers when it was saved
  const h = new Headers(resp.headers); h.set('X-Saved-At', new Date().toISOString());
  return resp.clone().blob().then(b => new Response(b, { status: resp.status, statusText: resp.statusText, headers: h }));
}
function offlineAnswer(saved) {
  const h = new Headers(saved.headers); h.set('X-Offline-Saved', saved.headers.get('X-Saved-At') || '');
  return saved.blob().then(b => new Response(b, { status: saved.status, statusText: saved.statusText, headers: h }));
}
const notSaved = () => new Response(JSON.stringify({ error: 'You are offline, and this was not saved on this device.', offline: true }),
  { status: 503, headers: { 'Content-Type': 'application/json', 'X-Offline-Saved': 'none' } });

async function apiGet(req) {
  const url = new URL(req.url), c = await caches.open(API), save = !NO_SAVE.test(url.pathname) && !url.searchParams.has('nosave');
  try {
    const r = await tryNet(req);
    if (r.ok && save) c.put(req, await stamp(r));
    return r;
  } catch (e) {
    const saved = (await c.match(req)) || (await c.match(req, { ignoreSearch: true }));
    return saved ? offlineAnswer(saved) : notSaved();
  }
}
async function picture(req, name) {
  const c = await caches.open(name), hit = await c.match(req);
  if (hit) return hit;
  try { const r = await fetch(req); if (r.ok) c.put(req, r.clone()); return r; }
  catch (e) { return new Response('', { status: 504 }); }
}
async function shell(req) {
  const c = await caches.open(SHELL);
  try {
    const r = await tryNet(req);
    if (r.ok) c.put(req.mode === 'navigate' ? '/' : req, r.clone());
    return r;
  } catch (e) {
    return (await c.match(req.mode === 'navigate' ? '/' : req, { ignoreSearch: true })) || new Response('Offline, and the app is not saved on this device yet.', { status: 503 });
  }
}
// 1.37.0: the share sheet ("Share → Plants") posts the pictures here; keep them in a cache and open the page that adds them
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'POST' || url.pathname !== '/share') return;
  e.respondWith((async () => {
    try {
      const fd = await e.request.formData(), c = await caches.open('plantdb-share'), files = fd.getAll('photos');
      let i = 0;
      for (const f of files) {
        if (!f || !f.size) continue;
        const name = (f.name || ('photo-' + (i + 1) + '.jpg')).replace(/[^\w.\-]+/g, '_');
        await c.put(new Request('/shared/' + String(Date.now() + i).padStart(16, '0') + '-' + name), new Response(f, { headers: { 'Content-Type': f.type || 'image/jpeg', 'X-Name': name } }));
        i++;
      }
    } catch (err) { /* nothing shared after all */ }
    return Response.redirect('/#/share', 303);
  })());
});

self.addEventListener('fetch', e => {
  const req = e.request, url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== self.location.origin) return;
  if (url.pathname.startsWith('/api/')) return e.respondWith(apiGet(req));
  if (url.pathname.startsWith('/photos/') || url.pathname.startsWith('/thumbs/')) return e.respondWith(picture(req, PICS));
  if (url.pathname.startsWith('/library-photos/')) return e.respondWith(picture(req, LIBPICS));
  if (req.mode === 'navigate' || SHELL_FILES.includes(url.pathname) || url.pathname.startsWith('/fonts/') || url.pathname.startsWith('/lights/')) return e.respondWith(shell(req));
});
self.addEventListener('message', e => {
  if (e.data === 'forget') e.waitUntil(Promise.all([API, PICS, LIBPICS].map(n => caches.delete(n))));
});

// 1.33.0: notifications pushed by the plant record (cold nights, Shopping alerts, what is due, requests from Claude)
self.addEventListener('push', e => {
  let d = {}; try { d = e.data ? e.data.json() : {}; } catch (err) { d = { title: 'Plant record', body: e.data ? e.data.text() : '' }; }
  e.waitUntil(self.registration.showNotification(d.title || 'Plant record', { body: d.body || '', tag: d.tag || 'plantdb', renotify: !!d.tag, icon: '/icon-192.png', badge: '/icon-192.png', data: { url: d.url || '#/' } }));
});
self.addEventListener('notificationclick', e => {
  e.notification.close();
  const url = new URL(((e.notification.data || {}).url || '#/'), self.location.origin).href;
  e.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(cs => {
    const c = cs.find(x => x.url.startsWith(self.location.origin));
    if (c) return c.focus().then(w => (w && 'navigate' in w ? w.navigate(url) : null));
    return self.clients.openWindow(url);
  }));
});
