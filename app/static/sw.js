/* Plant record service worker (1.24.0): lets the app open and show what this device has saved when there is no connection.
   - The app's own files: from the network when it answers, else the saved copy.
   - /api/ answers (GET): from the network when it answers within a few seconds (and saved), else the saved copy, marked with
     the X-Offline-Saved header so the page can say it is showing what was saved, and when.
   - Photos: the saved copy first (they never change once added), else the network (and saved).
   Changes made while offline are not handled here: the page keeps them in its outbox and sends them when it is back online. */
const VERSION = '__VERSION__';
const SHELL = 'plantdb-shell-' + VERSION, API = 'plantdb-api', PICS = 'plantdb-photos', LIBPICS = 'plantdb-library-photos';
const SHELL_FILES = ['/', '/app.js', '/style.css', '/prefs.js', '/card.html', '/card.js', '/manifest.webmanifest', '/icon.svg', '/icon-192.png', '/icon-512.png'];
const NO_SAVE = /^\/api\/(people|backups|ingest|weather\/job|backups\/job|audit|library\/prefetch|library\/local|offline\/|identify\/settings|calendar\/settings|me$)/;
const WAIT_MS = 5000;
let downUntil = 0;                           // after the server fails to answer, use saved copies at once for a while (weak signal)
const quick = () => !self.navigator.onLine || Date.now() < downUntil;
const wentDown = () => { downUntil = Date.now() + 30000; };
async function tryNet(req) {
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
