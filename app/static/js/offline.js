/* Plant record front end: offline use and the calendar file. One of the files app.js was split into in 1.32.0; they load in order (index.html) and share one scope,
   so a function here may call any other. Plain JavaScript, no inline handlers (the server's content policy forbids them). */
'use strict';

// ---------- 1.24.0: offline use (phones and tablets out of reach of the server) ----------
// sw.js keeps the app's files, the answers its pages asked for and the photos. This part keeps changes made without a connection
// in an outbox (IndexedDB, on this device only) and sends them when the server can be reached again, each with its own id so that
// it is made only once. Mushroom finds added offline get a temporary code (NEW-…) until the server gives them their F- code.
const OFF = { online: navigator.onLine, sending: false, n: 0, failed: 0, conflicts: 0, saved: null, queuedAt: 0, k: 0, dl: null, idq: 0 };
const OFF_OK = [                              // the changes that can wait for a connection
  ['POST', /^\/api\/care$/], ['DELETE', /^\/api\/care\/\d+$/],
  ['PUT', /^\/api\/plants\/[^/]+$/], ['POST', /^\/api\/plants\/[^/]+\/(site|status|photos)$/],
  ['POST', /^\/api\/fungi$/], ['PUT', /^\/api\/fungi\/[^/]+$/], ['POST', /^\/api\/fungi\/[^/]+\/(status|photos)$/], ['PATCH', /^\/api\/fungi\/photos\/\d+$/], ['DELETE', /^\/api\/fungi\/photos\/\d+$/],
  ['PUT', /^\/api\/library\/notes$/], ['PUT', /^\/api\/wishlist$/], ['DELETE', /^\/api\/wishlist$/]];
const offQueueable = (m, url) => OFF_OK.some(([mm, re]) => mm === m && re.test(url.split('?')[0]));
const offId = () => Date.now().toString(36) + '-' + Array.from(crypto.getRandomValues(new Uint8Array(8)), b => b.toString(16).padStart(2, '0')).join('');
let OFFDB = null;
function idb() {
  if (!OFFDB) OFFDB = new Promise((ok, no) => {
    const r = indexedDB.open('plantdb-offline', 1);
    r.onupgradeneeded = () => { const d = r.result; d.createObjectStore('outbox', { keyPath: 'id' }); d.createObjectStore('finds', { keyPath: 'code' }); d.createObjectStore('idq', { keyPath: 'id' }); d.createObjectStore('kv'); };
    r.onsuccess = () => ok(r.result); r.onerror = () => no(r.error);
  });
  return OFFDB;
}
async function idbDo(store, mode, fn) {
  const d = await idb();
  return new Promise((ok, no) => { const t = d.transaction(store, mode), req = fn(t.objectStore(store)); t.oncomplete = () => ok(req ? req.result : undefined); t.onerror = () => no(t.error); t.onabort = () => no(t.error); });
}
const idbAll = st => idbDo(st, 'readonly', s => s.getAll()).catch(() => []);
const idbGet = (st, k) => idbDo(st, 'readonly', s => s.get(k)).catch(() => undefined);
const idbPut = (st, v, k) => idbDo(st, 'readwrite', s => (k === undefined ? s.put(v) : s.put(v, k)));
const idbDel = (st, k) => idbDo(st, 'readwrite', s => s.delete(k));
const offKv = async (k, d) => { const v = await idbGet('kv', k); return v === undefined ? d : v; };
function offGuessDevice() {
  const u = navigator.userAgent;
  return /iPhone/.test(u) ? 'iPhone' : /iPad|Macintosh.*Mobile/.test(u) || (/Macintosh/.test(u) && navigator.maxTouchPoints > 1) ? 'iPad' : /Android/.test(u) ? (/Mobile/.test(u) ? 'Android phone' : 'Android tablet') : /Windows/.test(u) ? 'Windows PC' : /Macintosh/.test(u) ? 'Mac' : 'This device';
}
let OFFDEV = null;
const offDevice = () => OFFDEV || offGuessDevice();
async function offOps() { return (await idbAll('outbox')).sort((a, b) => a.seq - b.seq); }
function offWords(op) {                       // what a waiting change is, in words
  const u = op.url.split('?')[0], b = op.body || {}, code = (u.match(/\/(P-\d+|F-\d+|NEW-[a-z0-9-]+)/i) || [])[1] || '';
  const KIND = { water: 'Watered', check: 'Checked: still moist', note: 'Note' };
  if (u === '/api/care') return `${KIND[b.kind] || 'Care logged'}${b.note ? ': ' + b.note : ''} for ${(b.plants || [b.plant]).join(', ')} (${b.done_on})`;
  if (/^\/api\/care\//.test(u)) return 'A care log entry removed';
  if (/\/site$/.test(u)) return `${code}: moved to ${b.site}`;
  if (/\/status$/.test(u)) return `${code}: ${b.archived ? 'archived' : 'brought back'}`;
  if (/\/photos$/.test(u)) { const n = (op.form || []).filter(p => p.blob).length; return `${code}: ${n} photo${n === 1 ? '' : 's'} added`; }
  if (/^\/api\/plants\//.test(u)) return `${code}: edited ${Object.keys(b.fields || {}).join(', ') || 'details'}`;
  if (u === '/api/fungi') return `New mushroom find ${op.temp}${b.fields && b.fields.name ? ': ' + b.fields.name : ''}`;
  if (/^\/api\/fungi\/photos\//.test(u)) return 'A mushroom photo changed';
  if (/^\/api\/fungi\//.test(u)) return `${code}: edited ${Object.keys(b.fields || {}).join(', ') || 'details'}`;
  if (u === '/api/library/notes') return `Notes and tags for ${b.name}`;
  if (u === '/api/wishlist') return op.method === 'DELETE' ? `${b.name} taken off the wishlist` : `${b.name} on the wishlist`;
  return op.method + ' ' + u;
}
async function offSavedJson(url) {
  try { const c = await caches.open('plantdb-api'), r = await c.match(url); return r ? await r.json() : null; } catch (e) { return null; }
}
async function offPatch(url, fn) {            // so the page shows a change made offline before it is sent
  try {
    const c = await caches.open('plantdb-api'), r = await c.match(url); if (!r) return;
    const j = await r.json(); fn(j);
    await c.put(url, new Response(JSON.stringify(j), { status: 200, headers: r.headers }));
  } catch (e) { /* only for show */ }
}
async function offFormParts(form) { return [...form.entries()].map(([k, v]) => (v instanceof Blob ? { k, blob: v, name: v.name || 'photo.jpg' } : { k, v: String(v) })); }
async function offQueue(method, url, body, form) {
  if (ME().role === 'viewer') { const e = new Error('You can only view, so nothing can be saved.'); e.status = 403; throw e; }
  const op = { id: offId(), seq: Date.now() + (OFF.k++) / 1000, method, url, body: body === undefined ? null : JSON.parse(JSON.stringify(body)), form: form ? await offFormParts(form) : null,
    who: cleanName(viaTS() ? ME().name : getName()) || 'Unknown', made: new Date().toISOString(), device: offDevice(), place: PLACE || null };
  const path = url.split('?')[0];
  let shim = { offline: true };
  if (path === '/api/care' && method === 'POST') { if (!op.body.done_on) op.body.done_on = todayStr(); shim = { ids: [], skipped: [], water: [], offline: true }; }
  const pend = path.match(/^\/api\/fungi\/(NEW-[a-z0-9-]+)(\/[a-z]+)?$/i);
  if (pend) {                                  // a find that has not been sent yet: change the waiting record itself
    const f = await idbGet('finds', pend[1]); if (!f) throw new Error('That find is not on this device any more.');
    if (method === 'PUT' && !pend[2]) { Object.assign(f.fields, op.body.fields || {}); const cr = (await offOps()).find(o => o.temp === f.code); if (cr) { Object.assign(cr.body.fields, op.body.fields || {}); await idbPut('outbox', cr); } }
    else if (pend[2] === '/photos') { op.form.filter(p => p.blob).forEach(p => f.photos.push({ id: 'p' + offId(), blob: p.blob, caption: '' })); await idbPut('outbox', op); }
    else if (pend[2] === '/status') { f.status = op.body.archived ? 'archived' : 'active'; await idbPut('outbox', op); }
    f.version++; await idbPut('finds', f);
    OFF.queuedAt = Date.now(); offPaint();
    return Object.assign(await offFindDict(f), { offline: true, added: [] });
  }
  if (path === '/api/fungi' && method === 'POST') {
    op.temp = 'NEW-' + offId().slice(-10);
    await idbPut('finds', { code: op.temp, fields: Object.assign({}, op.body.fields || {}), photos: [], status: 'active', version: 1, made: op.made, who: op.who });
    shim = { code: op.temp, version: 1, offline: true };
  }
  if ((method === 'PUT') && /^\/api\/(plants|fungi)\/[^/]+$/.test(path)) {
    const saw = await offSavedJson(path), fields = op.body.fields || {};
    if (saw) {
      op.body.base_values = {};
      for (const k of Object.keys(fields)) {
        const a = saw[k] == null ? '' : String(saw[k]).trim(), b = fields[k] == null ? '' : String(fields[k]).trim();
        if (a === b) delete fields[k]; else op.body.base_values[k] = saw[k] == null ? null : saw[k];
      }
      op.body.base_version = op.body.base_version || saw.version;
      shim = Object.assign({}, saw, fields, { changed: Object.keys(fields).length > 0, offline: true });
    }
    await offPatch(path, j => Object.assign(j, fields));
  }
  if (/\/site$/.test(path)) await offPatch(path.replace(/\/site$/, ''), j => { j.site = op.body.site; });
  if (/\/status$/.test(path) && /^\/api\/plants\//.test(path)) await offPatch(path.replace(/\/status$/, ''), j => { j.status = op.body.archived ? 'archived' : 'active'; });
  await idbPut('outbox', op);
  OFF.queuedAt = Date.now();
  offPaint();
  return shim;
}
async function offFindDict(f) {                // a waiting find, in the shape the mushroom pages use
  const meta = (await offSavedJson('/api/fungi?status=none')) || (await offSavedJson('/api/fungi?status=active')) || { fields: [], enums: {} };
  const photos = f.photos.map((p, i) => ({ id: p.id, file: null, url: URL.createObjectURL(p.blob), caption: p.caption || '', is_primary: i === 0 ? 1 : 0, gps_lat: null, gps_lon: null, taken_at: null }));
  const d = Object.assign({ code: f.code, status: f.status, version: f.version, created_by: f.who, created_at: f.made, updated_by: f.who, updated_at: f.made, plant: null, pending: true },
    Object.fromEntries((meta.fields || []).map(x => [x.name, null])), f.fields, { photos, photo: null, photo_url: photos[0] ? photos[0].url : null, photo_count: photos.length,
      fields: meta.fields || [], enums: meta.enums || {} });
  if (!d.found_on) d.found_on = f.made.slice(0, 10);
  if (!d.id_status) d.id_status = 'Not identified yet';
  return d;
}
async function offPendingFinds() { return Promise.all((await idbAll('finds')).map(offFindDict)); }
async function offIdQueue(url, form) {
  const parts = await offFormParts(form), img = parts.find(p => p.blob);
  if (!img) throw new Error('No picture to keep.');
  const scope = new URLSearchParams(url.split('?')[1] || '').get('scope') || 'common';
  await idbPut('idq', { id: offId(), made: new Date().toISOString(), scope, blob: img.blob, ref: MUCUR && location.hash.startsWith('#/fungi/') ? MUCUR.code : null, result: null });
  OFF.idq++; offPaint();
  const e = new Error('You are offline. The picture is kept on this device and will be checked when you are back online; the answer will be on the Offline page.'); e.queued = true; throw e;
}
function offSeen(h) { if (h && h !== 'none') OFF.saved = h; }          // route() clears it; any saved answer marks the page
async function offCount() {
  const ops = await offOps(); OFF.n = ops.filter(o => !o.failed).length; OFF.failed = ops.filter(o => o.failed).length;
  OFF.idq = (await idbAll('idq')).filter(x => !x.result).length;
}
async function offPaint() {
  await offCount();
  const b = document.getElementById('net'); if (!b) return;
  const on = navigator.onLine && !OFF.forced;
  const bits = [OFF.sending === true ? `Sending ${OFF.n}…` : on ? 'Online' : 'Offline'];
  if (OFF.sending !== true && OFF.n) bits.push(`${OFF.n} to send`);
  if (OFF.failed) bits.push(`${OFF.failed} not sent`);
  if (OFF.conflicts) bits.push(`${OFF.conflicts} to decide`);
  b.textContent = bits.join(' · ');
  b.dataset.state = OFF.sending === true ? 'sending' : on ? (OFF.n || OFF.failed || OFF.conflicts ? 'waiting' : 'online') : 'offline';
  document.documentElement.toggleAttribute('data-offline', !on);
}
async function offSync() {
  if (OFF.sending || !navigator.onLine) return;
  OFF.sending = 'checking';                    // one at a time: the online event, the timer and the page can all ask
  let st;
  try { const r = await fetch('/api/offline/status', { cache: 'no-store' }); if (!r.ok || r.headers.get('X-Offline-Saved')) { OFF.sending = false; return; } st = await r.json(); } catch (e) { OFF.sending = false; return; }
  OFF.conflicts = st.conflicts || 0;
  const ops = (await offOps()).filter(o => !o.failed);
  if (!ops.length && !(await idbAll('idq')).some(x => !x.result)) { OFF.sending = false; offPaint(); return; }
  OFF.sending = true; offPaint();
  const map = await offKv('idmap', {});
  let sent = 0, problems = 0;
  try {
    for (const op of ops) {
      const url = op.url.replace(/NEW-[a-z0-9-]+/gi, m => map[m] || m);
      if (/NEW-/i.test(url)) { op.failed = true; op.error = 'The find it belongs to could not be sent.'; await idbPut('outbox', op); problems++; continue; }
      const h = { 'X-Editor': op.who, 'X-Offline-Op': op.id, 'X-Offline-Made': op.made, 'X-Offline-Device': op.device };
      if (op.place) h['X-Place'] = op.place;
      let body;
      if (op.form) { body = new FormData(); op.form.forEach(p => (p.blob ? body.append(p.k, p.blob, p.name) : body.append(p.k, p.v))); }
      else if (op.body != null) { h['Content-Type'] = 'application/json'; body = JSON.stringify(op.body); }
      let r;
      try { r = await fetch(url, { method: op.method, headers: h, body }); } catch (e) { break; }      // the connection dropped: try again later
      let d = null; try { d = await r.json(); } catch (e) { /* no answer */ }
      if (r.ok) {
        if (op.temp && d && d.code) { map[op.temp] = d.code; await idbPut('kv', map, 'idmap'); await idbDel('finds', op.temp); }
        await idbDel('outbox', op.id); sent++;
      } else if (r.status >= 500) break;
      else { op.failed = true; op.error = (d && d.error) || `Refused (${r.status})`; await idbPut('outbox', op); problems++; }
    }
    var checked = await offIdRun();
    try { const r2 = await fetch('/api/offline/status', { cache: 'no-store' }); if (r2.ok && !r2.headers.get('X-Offline-Saved')) OFF.conflicts = (await r2.json()).conflicts || 0; } catch (e) { /* later */ }
  } finally { OFF.sending = false; await offPaint(); }
  if (sent || problems || checked) {
    toast(`${sent ? `${sent} change${sent === 1 ? '' : 's'} made offline ${sent === 1 ? 'was' : 'were'} sent.` : ''}${checked ? ` ${checked} picture${checked === 1 ? ' was' : 's were'} checked with Identify; see the Offline page.` : ''}${problems ? ` ${problems} could not be sent; see the Offline page.` : ''}${OFF.conflicts ? ` ${OFF.conflicts} need${OFF.conflicts === 1 ? 's' : ''} your decision.` : ''}`.trim(), problems > 0);
    if (!document.querySelector('main form[data-form]') || location.hash.startsWith('#/offline')) route();
    if (await offKv('keep', false)) setTimeout(() => offDownload(true), 1500);
  }
}
async function offIdRun() {                    // pictures taken for Identify while offline
  let n = 0;
  for (const x of await idbAll('idq')) {
    if (x.result) continue;
    const fd = new FormData(); fd.append('image', x.blob, 'picture.jpg');
    let r; try { r = await fetch('/api/identify?scope=' + enc(x.scope), { method: 'POST', headers: { 'X-Editor': cleanName(viaTS() ? ME().name : getName()) || 'Unknown' }, body: fd }); } catch (e) { break; }
    if (!r.ok) { if (r.status >= 500) break; x.result = { error: ((await r.json().catch(() => ({}))).error) || 'Could not be checked.' }; }
    else x.result = await r.json();
    x.checked = new Date().toISOString(); await idbPut('idq', x); n++;
  }
  return n;
}
async function offDownload(quick) {            // "Keep a copy on this device": the answers the pages use, and every photo
  if (OFF.dl || !navigator.onLine) return;
  OFF.dl = { done: 0, total: 1, step: 'Finding what to save' }; offDlPaint();
  try {
    const m = await (await fetch('/api/offline/manifest', { cache: 'no-store' })).json();
    const pics = await caches.open('plantdb-photos');
    const want = [];
    for (const f of m.photos) for (const u of ['/photos/' + enc(f), '/thumbs/' + enc(f)]) if (!(await pics.match(u))) want.push(u);
    const lib = (await offKv('keeplib', false)) ? ['/api/library/offline-index'] : [];
    const jobs = m.urls.concat(lib, want);
    OFF.dl = { done: 0, total: jobs.length, step: 'Saving', bytes: m.photo_bytes, failed: 0 };
    const head = PLACE ? { 'X-Place': PLACE } : {};
    let i = 0;
    const worker = async () => { while (i < jobs.length) { const u = jobs[i++]; try { const r = await fetch(u, { headers: head }); if (!r.ok) OFF.dl.failed++; } catch (e) { OFF.dl.failed++; } OFF.dl.done++; if (OFF.dl.done % 10 === 0) offDlPaint(); } };
    await Promise.all([worker(), worker(), worker(), worker()]);
    if (lib.length) await offLibPhotos();
    await idbPut('kv', new Date().toISOString(), 'downloaded');
    OFF.dl.step = 'Done';
  } catch (e) { OFF.dl = Object.assign(OFF.dl || {}, { step: 'Stopped: ' + e.message }); }
  const fin = OFF.dl; OFF.dl = null; offDlPaint(fin);
}
async function offLibPhotos() {                // the library's Texas list photos, when asked for
  const idx = await offSavedJson('/api/library/offline-index'); if (!idx) return;
  const c = await caches.open('plantdb-library-photos'), urls = idx.species.map(s => s.p).filter(Boolean);
  OFF.dl = Object.assign(OFF.dl, { step: 'Saving library photos', done: 0, total: urls.length });
  let i = 0;
  const worker = async () => { while (i < urls.length) { const u = urls[i++]; if (!(await c.match(u))) { try { await fetch(u); } catch (e) { /* later */ } } OFF.dl.done++; if (OFF.dl.done % 20 === 0) offDlPaint(); } };
  await Promise.all([worker(), worker(), worker()]);
}
function offDlPaint(fin) {
  const box = document.getElementById('off-dl'); if (!box) return;
  const d = OFF.dl || fin;
  box.textContent = !d ? '' : OFF.dl ? `${d.step}: ${d.done.toLocaleString()} of ${d.total.toLocaleString()}…` : `${d.step}.${d.failed ? ` ${d.failed} could not be saved; they are tried again next time.` : ''}`;
  if (!OFF.dl && fin) offPagePaint();
}
function offNotice(parts) {                    // on a plant or find page: its changes that are still waiting
  const code = (parts[0] === 'plant' || parts[0] === 'fungi') && parts[1] ? decodeURIComponent(parts[1]) : null;
  if (!code) return;
  offOps().then(ops => {
    const mine = ops.filter(o => o.url.includes('/' + code) || (o.body && (o.body.plant === code || (o.body.plants || []).includes(code))) || o.temp === code);
    if (!mine.length || !document.getElementById('app')) return;
    document.getElementById('app').insertAdjacentHTML('afterbegin', rend(html`<div class="notice off-note noprint" role="note"><strong>Not sent yet:</strong> ${mine.map(offWords).join('; ')}. ${navigator.onLine ? 'Sending soon.' : 'They will be sent when this device is back online.'} <a href="#/offline">Offline page</a></div>`));
  });
}
// the Offline page
async function viewOffline() {
  const [keep, keeplib, dl, ops, idq] = await Promise.all([offKv('keep', false), offKv('keeplib', false), offKv('downloaded', null), offOps(), idbAll('idq')]);
  let est = null; try { est = navigator.storage && navigator.storage.estimate ? await navigator.storage.estimate() : null; } catch (e) { /* not told */ }
  let persisted = null; try { persisted = navigator.storage && navigator.storage.persisted ? await navigator.storage.persisted() : null; } catch (e) { /* not told */ }
  if (navigator.onLine) { try { const s = await (await fetch('/api/offline/status', { cache: 'no-store' })).json(); OFF.conflicts = s.conflicts || 0; } catch (e) { /* offline */ } }
  const mb = b => (b / 1048576).toLocaleString(undefined, { maximumFractionDigits: b < 10485760 ? 1 : 0 }) + ' MB';
  const wait = ops.filter(o => !o.failed), bad = ops.filter(o => o.failed);
  const ios = /iPhone|iPad/.test(navigator.userAgent) || (/Macintosh/.test(navigator.userAgent) && navigator.maxTouchPoints > 1);
  return {
    title: 'Offline use', after: () => { offDlPaint(); },
    html: html`<h1>Offline use</h1>
    <p>This device: <strong>${navigator.onLine ? 'online' : 'offline'}</strong>${OFF.saved && !navigator.onLine ? '' : ''}. Changes you make without a connection are kept on this device and sent to the plant record as soon as it can be reached again.</p>
    ${OFF.conflicts ? html`<p class="notice bad" role="status"><strong>${OFF.conflicts} change${OFF.conflicts === 1 ? '' : 's'} need${OFF.conflicts === 1 ? 's' : ''} your decision:</strong> the same thing was changed on two devices. <a href="#/decisions">Choose which to keep</a>.</p>` : ''}
    <section aria-labelledby="off-copy-h"><h2 id="off-copy-h">Keep a copy on this device</h2>
      <div class="off-opts"><label class="chk"><input type="checkbox" data-f="offkeep" ${keep ? raw('checked') : ''}>Keep a copy of every plant, mushroom find, care log and photo (full size) on this device, so it works without a connection</label>
      <label class="chk"><input type="checkbox" data-f="offkeeplib" ${keeplib ? raw('checked') : ''}>Also keep the library's download areas (their plant lists and photos, from the Library page) on this device</label></div>
      <p>${dl ? `Last saved ${when(dl)}.` : 'Not saved on this device yet.'} ${keep ? 'It is saved again by itself when it is a few hours old and the device is online.' : ''}</p>
      <p id="off-dl" role="status" aria-live="polite"></p>
      ${keep ? html`<p class="row"><button class="btn" type="button" data-act="offdl" ${navigator.onLine ? '' : raw('disabled')}>Save it again now</button></p>` : ''}
      ${est ? html`<p class="hint">This device is using ${mb(est.usage || 0)} for the plant record${est.quota ? `, of the ${mb(est.quota)} the browser allows` : ''}.${persisted === false ? ' The browser may clear it if the device runs short of space.' : persisted ? ' The browser has agreed to keep it.' : ''}</p>` : ''}
      <p class="hint">${ios ? html`On an iPhone or iPad, add the plant record to the Home Screen (Share, then <strong>Add to Home Screen</strong>) and open it from there: Safari clears saved copies of sites that are not on the Home Screen after a few weeks.`
        : html`On Android, choose <strong>Install app</strong> (or <strong>Add to Home screen</strong>) in the browser's menu, and open it from there.`} Open it once while online after each update, so the new version is saved too.</p>
      <label class="f off-dev">This device's name<small>Shown in the Audit log and on decisions, so you know where a change came from</small><input type="text" data-f="offdev" value="${offDevice()}" maxlength="40" autocomplete="off"></label>
    </section>
    <section aria-labelledby="off-out-h"><h2 id="off-out-h">Waiting to be sent (${wait.length})</h2>
      ${wait.length ? html`<ol class="off-list">${wait.map(o => html`<li>${offWords(o)} <span class="muted">(${when(o.made)}, ${o.who})</span> <button class="btn ghost small" type="button" data-act="offrm" data-id="${o.id}">Don't send this</button></li>`)}</ol>
        <p class="row"><button class="btn" type="button" data-act="offsend" ${navigator.onLine ? '' : raw('disabled')}>Send them now</button></p>` : html`<p class="muted">Nothing is waiting.</p>`}
      ${bad.length ? html`<h3>Could not be sent (${bad.length})</h3><ol class="off-list">${bad.map(o => html`<li>${offWords(o)} <span class="muted">(${when(o.made)})</span>: <strong>${o.error}</strong>
        <span class="row"><button class="btn ghost small" type="button" data-act="offretry" data-id="${o.id}">Try again</button><button class="btn ghost small" type="button" data-act="offrm" data-id="${o.id}">Remove it</button></span></li>`)}</ol>` : ''}
    </section>
    <section aria-labelledby="off-id-h"><h2 id="off-id-h">Pictures to identify</h2>
      ${idq.length ? html`<ul class="off-list">${idq.map(x => html`<li><img class="off-pic" src="${URL.createObjectURL(x.blob)}" alt="Picture taken ${when(x.made)}"> Taken ${when(x.made)}${x.ref ? html` for <a href="#/fungi/${enc(x.ref)}">${x.ref}</a>` : ''}.
          ${!x.result ? html`<span>Waiting for a connection.</span>` : x.result.error ? html`<span>${x.result.error}</span>`
            : html`<span>It looks most like: ${(x.result.species || []).slice(0, 3).map((s, i) => html`${i ? '; ' : ''}<a href="#/species/${enc(s.scientific_name)}"><i>${s.scientific_name}</i></a>${s.common_name ? ` (${s.common_name})` : ''} ${pct(s.probability)}`)}${(x.result.matches || [])[0] && (x.result.matches[0].confidence || 0) >= 0.5 ? html`. Your plant ${x.result.matches[0].code}?` : ''}</span>`}
          <button class="btn ghost small" type="button" data-act="offidrm" data-id="${x.id}" aria-label="Remove this waiting picture">Remove</button></li>`)}</ul>` : html`<p class="muted">None. Pictures taken for Identify without a connection wait here and are checked when you're back online.</p>`}
    </section>
    ${keep || dl ? html`<section aria-labelledby="off-forget-h"><h2 id="off-forget-h">Forget the copy</h2><p>Deletes what this device saved (not the changes waiting to be sent, and nothing on the plant record itself).</p>
      <p class="row"><button class="btn danger" type="button" data-act="offforget">Delete the saved copy on this device</button></p></section>` : ''}`,
  };
}
function offPagePaint() { if (location.hash.startsWith('#/offline') && !document.querySelector('#app input:focus')) route(); }
// the Needs your decision page
async function viewDecisions() {
  const d = await api('GET', '/api/conflicts?all=1');
  const open = d.conflicts.filter(x => x.open), done = d.conflicts.filter(x => !x.open).slice(0, 30);
  const v = x => (x == null || x === '' ? '(empty)' : x);
  const href = x => x.kind === 'plant' ? `#/plant/${enc(x.code)}` : `#/fungi/${enc(x.code)}`;
  return {
    title: 'Needs your decision',
    html: html`<h1>Needs your decision</h1>
    <p>When the same thing was changed on a device without a connection and on the plant record, both versions are kept here until someone chooses. Everything else from the device has already been saved.</p>
    ${open.length ? html`<ul class="dec-list">${open.map(x => html`<li class="dec"><h2><a href="${href(x)}">${x.code}</a>: ${x.label}</h2>
        <div class="dec-sides"><div><h3>Changed on ${x.device || 'a device'}</h3><p class="dec-v">${v(x.phone_value)}</p><p class="hint">By ${x.phone_by}, ${when(x.phone_made_at)}</p>
          ${canChange() ? html`<button class="btn" type="button" data-act="decide" data-id="${x.id}" data-choice="phone">Keep this: ${String(v(x.phone_value)).slice(0, 40)}</button>` : ''}</div>
        <div><h3>On the plant record</h3><p class="dec-v">${v(x.server_value)}</p><p class="hint">${x.server_by ? `By ${x.server_by}, ${when(x.server_at)}` : ''}</p>
          ${canChange() ? html`<button class="btn ghost" type="button" data-act="decide" data-id="${x.id}" data-choice="server">Keep this: ${String(v(x.server_value)).slice(0, 40)}</button>` : ''}</div></div>
        <p class="hint">Before either change it was: ${v(x.base)}.</p></li>`)}</ul>` : html`<p class="muted">Nothing to decide.</p>`}
    ${done.length ? html`<h2>Decided</h2><ul class="off-list">${done.map(x => html`<li><a href="${href(x)}">${x.code}</a> ${x.label}: kept ${x.choice === 'phone' ? `the change from ${x.device || 'the device'} (${v(x.phone_value)})` : `the plant record's value (${v(x.server_value)})`}, chosen by ${x.resolved_by}.</li>`)}</ul>` : ''}`,
  };
}
Object.assign(acts, {
  offdl: () => offDownload(false),
  offsend: async () => { await offSync(); route(); },
  async offrm(el) {
    if (!(await confirmBox('Don\'t send this change?', 'It is deleted from this device and never reaches the plant record.', 'Delete it', true))) return;
    const op = (await offOps()).find(o => o.id === el.dataset.id);
    if (op && op.temp) { await idbDel('finds', op.temp); for (const o of await offOps()) if (o.url.includes(op.temp)) await idbDel('outbox', o.id); }
    await idbDel('outbox', el.dataset.id); await offPaint(); route();
  },
  async offretry(el) { const op = (await offOps()).find(o => o.id === el.dataset.id); if (op) { delete op.failed; delete op.error; await idbPut('outbox', op); } await offSync(); route(); },
  async offidrm(el) { await idbDel('idq', el.dataset.id); await offPaint(); route(); },
  async offforget() {
    if (!(await confirmBox('Delete the saved copy?', 'This device will need a connection to show the plant record until it is saved again. Changes waiting to be sent are kept.', 'Delete the saved copy', true))) return;
    await Promise.all(['plantdb-api', 'plantdb-photos', 'plantdb-library-photos'].map(n => caches.delete(n)));
    await idbPut('kv', false, 'keep'); await idbPut('kv', false, 'keeplib'); await idbDel('kv', 'downloaded'); toast('The saved copy is deleted'); route();
  },
  async decide(el) {
    if (!(await needName())) return;
    await guard(async () => { await api('POST', '/api/conflicts/' + el.dataset.id, { choice: el.dataset.choice }); OFF.conflicts = Math.max(0, OFF.conflicts - 1); toast('Kept'); offPaint(); await route(); });
  },
});
async function offChange(el) {                 // the Offline page's settings
  const f = el.dataset.f;
  if (f === 'offkeep') {
    await idbPut('kv', el.checked, 'keep');
    if (el.checked) { try { if (navigator.storage && navigator.storage.persist) await navigator.storage.persist(); } catch (e) { /* asked */ } offDownload(false); }
    route(); return true;
  }
  if (f === 'offkeeplib') { await idbPut('kv', el.checked, 'keeplib'); if (el.checked && (await offKv('keep', false))) offDownload(false); return true; }
  if (f === 'offdev') { OFFDEV = el.value.trim().slice(0, 40) || null; await idbPut('kv', OFFDEV, 'device'); toast('Saved: this device is ' + offDevice()); return true; }
  return false;
}
async function offStart() {
  if ('serviceWorker' in navigator && (location.protocol === 'https:' || location.hostname === 'localhost' || location.hostname === '127.0.0.1')) {
    try { await navigator.serviceWorker.register('/sw.js', { scope: '/' }); } catch (e) { console.warn('Offline use is not available here: ' + e.message); }
  }
  OFFDEV = await offKv('device', null);
  window.addEventListener('online', () => { offPaint(); offSync(); });
  window.addEventListener('offline', () => offPaint());
  setInterval(() => { offSync(); }, 60000);
  await offPaint();
  setTimeout(async () => {
    await offSync();
    const keep = await offKv('keep', false), dl = await offKv('downloaded', null);
    if (keep && navigator.onLine && (!dl || Date.now() - new Date(dl).getTime() > 3 * 3600 * 1000)) offDownload(true);
  }, 2500);
}

document.addEventListener('click', e => {
  const el = e.target.closest('[data-act]');
  if (!el || el.tagName === 'INPUT') return;
  const fn = acts[el.dataset.act];
  if (fn) { e.preventDefault(); fn(el); }
});
document.addEventListener('change', e => {
  const el = e.target;
  if (el.dataset && el.dataset.act && changeActs[el.dataset.act]) { changeActs[el.dataset.act](el); return; }
  if (el.dataset && /^off(keep|keeplib|dev)$/.test(el.dataset.f || '')) { offChange(el); return; }
  if (el.dataset && el.dataset.plc) {        // Location window: switch straight away, as Display settings do
    placeChanged(el.dataset.plc);
    route().then(() => { const m = document.getElementById('plc-msg'); if (m) m.textContent = `Now using the weather for ${placeName()}.`; const h = document.getElementById('plc-home'); if (h) h.innerHTML = rend(plcHomeRow()); });
    return;
  }
  if (el.dataset && el.dataset.dbg) {
    const k = el.dataset.dbg; DBG[k] = el.type === 'checkbox' ? (el.checked ? '1' : '0') : el.value; dbgSave(); conApply();
    const m = document.getElementById('dbg-msg');      // the usual pop-up notes are hidden while this window is open
    if (m) m.textContent = k === 'console' ? (el.checked ? 'The console is on, at the bottom of the screen.' : 'The console is off.') : k === 'lines' ? `It now shows ${el.value} changes before you scroll.` : el.checked ? 'Screen readers will announce new changes.' : 'Screen readers will not announce new changes.';
    return;
  }
  if (el.dataset && el.dataset.f === 'phome') {        // 1.31.0: the home a person starts on
    const m = document.getElementById('who-msg'), label = el.options[el.selectedIndex].text;
    api('PUT', '/api/people', { login: el.dataset.login, home_id: el.value }).then(r => { peoplePaint(r); if (m) m.textContent = `Saved: starts on ${label}.`; })
      .catch(e => { if (m) m.textContent = e.message; });
    return;
  }
  if (el.dataset && el.dataset.f === 'prole') {
    const m = document.getElementById('who-msg'), login = el.dataset.login, label = el.options[el.selectedIndex].text;
    api('PUT', '/api/people', { login, role: el.value }).then(r => { peoplePaint(r); if (r.me) { META.me = r.me; paintWho(); } if (m) m.textContent = `Saved: ${label}.`; })
      .catch(e => { if (m) m.textContent = e.message; api('GET', '/api/people').then(peoplePaint).catch(() => {}); });
    return;
  }
  if (el.dataset && el.dataset.f === 'aud') { AUD.f[el.name] = el.value; AUD.offset = 0; audSave(); audLoad(`[name="${el.name}"][data-f=aud]`); return; }
  if (el.dataset && el.dataset.pref) { window.PlantPrefs.set(el.dataset.pref, el.value); if (el.dataset.pref === 'layout' && document.querySelector('.plant')) route(); return; }
  if (el.id === 'mu-place_kind') { muPlaceShow(); return; }
  if (el.name === 'csrc') { const mf = document.getElementById('manual-fields'); if (mf) mf.hidden = el.value !== 'manual'; return; }
  const f = el.dataset && el.dataset.f;
  if (!f) return;
  if (f.startsWith('mu') && f !== 'muq') {   // 1.22.0: the mushroom finds' filters
    MU[f.slice(2)] = el.value;
    if (f === 'mustatus') { muSave(); route(); } else muDraw();
    return;
  }
  if (f.startsWith('lib')) {             // 1.21.0: the library's filters
    const k = f.slice(3);
    if (k === 'online') { api('PUT', '/api/library/settings', { online: el.checked }).then(() => { LIB.photos = {}; toast(el.checked ? 'Library photos from iNaturalist are on' : 'Library photos are off: nothing is looked up online'); }).catch(e => toast(e.message, true)); return; }
    if (k === 'q') return;               // typing is handled as you type
    LIB[k] = el.type === 'checkbox' ? el.checked : el.value.trim();
    if (k === 'view') { libSave(); libDraw(0); return; }
    libChanged(k === 'scope');
    return;
  }
  if (f === 'wxperiod') {
    WX.period = el.value; if (/^\d+$/.test(el.value)) WX.days = +el.value;
    const d = document.getElementById('wx-dates'); if (d) d.hidden = el.value !== 'custom';
    if (el.value === 'custom' && !WX.from) { WX.to = ymd(new Date()); WX.from = addDays(WX.to, -30); document.querySelector('[data-f=wxfrom]').value = WX.from; document.querySelector('[data-f=wxto]').value = WX.to; }
    wxSave(); loadWxCharts();
  }
  else if (f === 'wxfrom' || f === 'wxto') { WX[f === 'wxfrom' ? 'from' : 'to'] = el.value; wxSave(); loadWxCharts(); }
  else if (f === 'wxsrc') { WX.src = el.value; loadWxCharts(); }
  else if (f === 'wxplace') { setPlace(el.value); }
  else if (f === 'wxcmp') {
    const k = el.dataset.key, i = WX.compare.indexOf(k);
    if (el.checked && WX.compare.length >= 5) { el.checked = false; toast('Up to 6 places on one chart. Untick one first.', true); return; }
    if (el.checked && i < 0) WX.compare.push(k); if (!el.checked && i >= 0) WX.compare.splice(i, 1);
    wxSave(); clearTimeout(WX.t); WX.t = setTimeout(loadWxCharts, 600);
  }
  else if (f === 'wxcols') { WX.cols = +el.value; wxSave(); const c = document.getElementById('wx-charts'); if (c) { c.className = 'cols-' + WX.cols; paintAllCharts(); } }
  else if (f === 'wxgoto') { const h = document.getElementById(el.value); if (h) { const card = h.closest('.chart-card'); card.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' }); card.setAttribute('tabindex', '-1'); card.focus({ preventScroll: true }); } el.value = ''; }
  else if (f === 'wxplant') { WX.plant = el.value; loadWxCharts(); }
  else if (f === 'wxshow' || f === 'wxvar') {
    const list = f === 'wxshow' ? WX.show : WX.vars, k = el.dataset.key;
    const i = list.indexOf(k); if (el.checked && i < 0) list.push(k); if (!el.checked && i >= 0) list.splice(i, 1);
    const n = document.getElementById('wx-pickcount'); if (n) n.textContent = WX.show.length + WX.vars.length;
    wxSave(); clearTimeout(WX.t); WX.t = setTimeout(loadWxCharts, 600);       // wait a moment so several ticks load once
  }
  else if (f === 'wtkind') { WT.kind = el.value; WT.page = 1; WT.hide = null; loadWxTable(); }
  else if (f === 'wtfrom') { WT.from = el.value; WT.page = 1; loadWxTable(); }
  else if (f === 'wtto') { WT.to = el.value; WT.page = 1; loadWxTable(); }
  else if (f === 'wtorder') { WT.order = el.value; WT.page = 1; loadWxTable(); }
  else if (f === 'wtper') {
    const n = Math.round(+el.value);
    if (!(n >= 10 && n <= 1000)) { toast('Rows per page must be between 10 and 1,000.', true); el.value = WT.per; return; }
    const firstRow = (WT.page - 1) * WT.per;                 // keep the same rows in view
    WT.per = n; WT.page = Math.floor(firstRow / n) + 1;
    try { localStorage.setItem('plantdb.wxper', String(n)); } catch (e) { /* ignore */ }
    loadWxTable();
  }
  else if (f === 'wtcol') { const h = wtHidden(); if (el.checked) h.delete(el.dataset.key); else h.add(el.dataset.key); wtSave(); const d = document.querySelector('.colpick'); const open = d && d.open; loadWxTable().then(() => { const n = document.querySelector('.colpick'); if (n && open) n.open = true; }); }
  else if (f === 'histsrc') { HS[el.dataset.kind].source = el.value; histCal(el.dataset.kind); }
  else if (f === 'health') { G.health = el.value; drawGrid(); }
  else if (f === 'group') { G.group = el.value; drawGrid(); }
  else if (f === 'pnplan') { G.plan = el.value; drawGrid(); }
  else if (f === 'pnneeds') { G.needs = el.checked; drawGrid(); }
  else if (f === 'sort') { G.sort = el.value; drawGrid(); }
  else if (f === 'low') { G.low = el.checked; drawGrid(); }
  else if (f === 'status') { G.status = el.value; drawGrid(); }
  else if (f === 'site') { G.site = el.value; drawGrid(); }
  else if (f === 'home') { G.home = el.value; drawGrid(); }
  else if (f === 'ctmat') { const o = document.querySelector(`[data-other="${el.dataset.id}"]`), t = o && o.querySelector('input');
    if (el.value === '__other') { o.hidden = false; t.dataset.was = t.value; t.focus(); }
    else { if (o) o.hidden = true; if (t) { t.dataset.was = t.value; t.value = el.value; edSave(t); } } }
  else if (f === 'wherehome' || f === 'whereside') { const fm = el.closest('form'); if (fm) whereRefresh(fm); }
  else if (f === 'wherearea') { const fm = el.closest('form'); if (fm) whereRefresh(fm, 'area'); }
  else if (f === 'sevset') { SEV[el.dataset.k] = el.value; }
  else if (f === 'sevadd') { const P = SEV.plants[+el.dataset.g]; P.add = el.checked; el.closest('fieldset').classList.toggle('sev-off', !el.checked); const b = document.querySelector('[data-act=sevsave]'), k = SEV.plants.filter(p => p.add).length; if (b) { b.textContent = `Add ${k} plant${k === 1 ? '' : 's'}`; b.disabled = !k; } }
  else if (f === 'sevpick') { const P = SEV.plants[+el.dataset.g]; P.pick = +el.value; P.typed = new Set(); sevFill(P); sevDraw(`[data-f=sevpick][data-g="${el.dataset.g}"][value="${el.value}"]`); }
  else if (f === 'sevmove') { const ph = SEV.photos[+el.dataset.p], n = SEV.plants.length;
    ph.group = el.value === 'out' ? 'out' : el.value === 'new' ? n : +el.value;
    const used = [...new Set(SEV.photos.map(p => p.group).filter(g => g !== 'out'))].sort((a, b) => a - b), map = Object.fromEntries(used.map((g, k) => [g, k]));
    const keepP = used.map(g => SEV.plants[g]).map(P => P && { ...P, key: '' });
    SEV.photos.forEach(p => { if (p.group !== 'out') p.group = map[p.group]; });
    const typed = keepP.map(P => P && { add: P.add, pick: P.pick, fields: P.fields, typed: P.typed });
    sevPlants(used.length);
    SEV.plants.forEach((P, k) => { if (typed[k] && typed[k].typed.size) Object.assign(P, typed[k]); });
    toast(el.value === 'out' ? 'Photo left out' : 'Photo moved'); sevDraw(); }
  else if (f === 'idphnone') { IDPH.none = el.checked; drawIdPhotos(); }
  else if (f === 'more') { G[el.dataset.key] = el.value; if (el.dataset.key === 'care' && el.value && !CAREDUE) loadCareDue().then(drawGrid); drawGrid(); }
});
document.addEventListener('toggle', e => { const d = e.target; if (d.classList && d.classList.contains('histbox') && d.open) histOpen(d.dataset.hist); }, true);
document.addEventListener('keydown', e => {
  const b = e.target.closest && e.target.closest('table.cal .day'); if (!b) return;
  const k = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 }[e.key];
  const id = b.dataset.cal;
  if (k) { e.preventDefault(); calGo(id, addDays(b.dataset.date, k), true); }
  else if (e.key === 'PageUp' || e.key === 'PageDown') { e.preventDefault(); const [Y, M, D] = b.dataset.date.split('-').map(Number), n = new Date(Y, M - 1 + (e.key === 'PageUp' ? -1 : 1), 1, 12), last = new Date(n.getFullYear(), n.getMonth() + 1, 0).getDate(); calGo(id, ymd(new Date(n.getFullYear(), n.getMonth(), Math.min(D, last), 12)), true); }
  else if (e.key === 'Home' || e.key === 'End') { e.preventDefault(); const [Y, M] = b.dataset.date.split('-').map(Number); calGo(id, ymd(new Date(Y, e.key === 'Home' ? M - 1 : M, e.key === 'Home' ? 1 : 0, 12)), true); }
});
document.addEventListener('input', e => {
  if (e.target.dataset && e.target.dataset.f === 'sevfield') { const P = SEV.plants[+e.target.dataset.g]; P.fields[e.target.dataset.k] = e.target.value; P.typed.add(e.target.dataset.k);
    if (e.target.dataset.k === 'common_name') { const lg = e.target.closest('fieldset.sev-plant').querySelector('legend'); lg.textContent = lg.textContent.replace(/(: .*)?$/, e.target.value ? ': ' + e.target.value : ''); } }
  if (e.target.closest && e.target.closest('form[data-spot]')) spotPreview();
  if (e.target.closest && e.target.closest('form[data-fert]')) {
    if (e.target.name === 'product') { const x = FERT.products.find(q => q.product.toLowerCase() === e.target.value.trim().toLowerCase()); const f = e.target.form; if (x && !f.elements.n.value && !f.elements.amount.value) { ['form', 'n', 'p', 'k', 'amount', 'amount_unit', 'water_amount', 'water_unit', 'method'].forEach(k => { if (x[k] != null && f.elements[k]) f.elements[k].value = x[k]; }); } }
    fertPreview();
  }
  if (e.target.name === 'rv' || (e.target.closest && e.target.closest('.rule-row'))) rulePreview();
  if (e.target.dataset && e.target.dataset.tickfind) {      // narrow a long list of plants to tick
    const q = e.target.value.trim().toLowerCase();
    e.target.closest('fieldset').querySelectorAll('li').forEach(li => { li.hidden = !!q && !li.textContent.toLowerCase().includes(q); });
  }
  const f = e.target.dataset && e.target.dataset.f;
  if (f === 'muq') { MU.q = e.target.value.trim(); muDraw(); }
  if (f === 'libq') { LIB.q = e.target.value.trim(); clearTimeout(LIB.t); LIB.t = setTimeout(() => libChanged(false), 300); }
  if (f === 'q') { G.q = e.target.value; drawGrid(); }
  else if (f === 'audq') { AUD.f.q = e.target.value; AUD.offset = 0; audSave(); clearTimeout(AUD.t); AUD.t = setTimeout(() => audLoad(), 400); }
});
document.addEventListener('submit', e => {
  const form = e.target.closest('form[data-form]');
  if (!form) return;
  e.preventDefault();
  const fn = formActs[form.dataset.form];
  if (fn) guard(() => fn(form));
});

document.addEventListener('prefs', () => { if (document.documentElement.dataset.narrow !== '1') NAVSESSION = null; navLayout(); conLayout(); fitPanes(); paintAllCharts(); Object.keys(CALS).forEach(id => calRender(id)); });
let rzT = null;
window.addEventListener('resize', () => { clearTimeout(rzT); rzT = setTimeout(() => { navLayout(); conLayout(); fitPanes(); paintAllCharts(); Object.keys(CALS).forEach(id => calRender(id)); }, 120); });
paintWho();
conApply();
// photo preview for plant links: pointer hover or keyboard focus
const pop = document.createElement('div'); pop.id = 'plink-pop'; pop.setAttribute('role', 'tooltip'); pop.hidden = true; document.body.appendChild(pop);
let popFor = null, popT = null;
function showPop(a) {
  const p = PCODES.get(a.dataset.code); if (!p) return;
  popFor = a;
  pop.innerHTML = rend(html`${p.photo ? html`<img src="${thumbUrl(p.photo)}" alt="">` : html`<div class="nophoto">No photo yet</div>`}<div class="pp-t"><b>${p.code}</b> ${p.common_name}</div>${p.health_rating ? html`<div class="pp-s">Health: ${p.health_rating}</div>` : ''}`);
  pop.hidden = false;
  placePop();
  a.setAttribute('aria-describedby', 'plink-pop');
}
function placePop() {
  if (!popFor) return;
  const r = popFor.getBoundingClientRect(), w = pop.offsetWidth, h = pop.offsetHeight, pad = 10;
  if (r.bottom < 0 || r.top > window.innerHeight || !popFor.isConnected) { hidePop(); return; }
  let x = Math.min(Math.max(pad, r.left), window.innerWidth - w - pad), y = r.bottom + 8;
  if (y + h > window.innerHeight - pad) y = Math.max(pad, r.top - h - 8);
  pop.style.left = x + 'px'; pop.style.top = y + 'px';
}
function hidePop() { clearTimeout(popT); if (popFor) popFor.removeAttribute('aria-describedby'); popFor = null; pop.hidden = true; }
document.addEventListener('mouseover', e => { const a = e.target.closest && e.target.closest('a.plink'); if (a && a !== popFor) { clearTimeout(popT); popT = setTimeout(() => showPop(a), 150); } });
document.addEventListener('mouseout', e => { const a = e.target.closest && e.target.closest('a.plink'); if (a && !a.contains(e.relatedTarget)) hidePop(); });
document.addEventListener('focusin', e => { if (e.target.matches && e.target.matches('a.plink')) showPop(e.target); });
document.addEventListener('focusout', e => { if (e.target.matches && e.target.matches('a.plink')) hidePop(); });
document.addEventListener('keydown', e => { if (e.key === 'Escape' && !pop.hidden) hidePop(); });
window.addEventListener('scroll', () => { if (!pop.hidden) placePop(); }, { capture: true, passive: true });
window.addEventListener('hashchange', hidePop);
// ---------- calendar file: feeding days and cold nights (prototype, proto/calendar-file) ----------
// A section at the foot of the Today, Fertilizer and Cold-night checklist pages opens a window that makes a .ics file
// (GET /api/calendar.ics) or gives a link to subscribe to (/cal/<token>.ics). The choices are saved on the server
// (GET/PUT /api/calendar/settings), so the file and the subscribed calendar match. The preview comes from GET /api/calendar.
const ICS = { o: null, links: null, days: [], data: null };
const icsSay = msg => { const s = document.getElementById('ics-status'); if (s) s.textContent = msg; };
const ICS_PAGES = ['today', 'fertilizer', 'frost'];
const icsTime = t => { const [h, m] = t.split(':').map(Number); return new Date(2000, 0, 1, h, m).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }); };
function icsSection() {
  return html`<section class="blk noprint" id="ics-box"><h2>Add to your calendar</h2>
    <p>Put feeding days and cold nights in the calendar on your phone or computer, with a reminder, so you hear about them without opening Plant record.</p>
    <p><button class="btn" type="button" data-act="icsopen">Set up your calendar</button></p></section>`;
}
new MutationObserver(() => {
  const page = (location.hash.replace(/^#\/?/, '').split('/')[0]) || 'today';
  if (!ICS_PAGES.includes(page) || document.getElementById('ics-box') || !app.querySelector('h1')) return;
  app.insertAdjacentHTML('beforeend', rend(icsSection()));
}).observe(app, { childList: true });
function icsPreview(D) {
  if (!D) return html`<p class="loading">Working out the dates</p>`;
  const o = ICS.o, n = D.counts, list = D.events.slice(0, 8), what = [];
  if (o.feed) what.push(`${n.feed} ${o.weekly ? 'weekly feeding day' : 'feeding day'}${n.feed === 1 ? '' : 's'} up to ${midDay(D.until)}`);
  if (o.cold) what.push(`${n.cold} cold night${n.cold === 1 ? '' : 's'} in the 7-day forecast`);
  if (!what.length) return html`<p class="notice bad">Choose feeding days, cold nights or both.</p>`;
  const rem = [o.feed && o.feed_remind ? `at ${icsTime(o.feed_at)} on feeding days` : '', o.cold && o.cold_remind ? `at ${icsTime(o.cold_at)} the day before a cold night` : ''].filter(Boolean);
  return html`<p><strong>Your calendar will have ${what.join(' and ')}</strong>, for ${D.place}.${rem.length ? ' Reminders ' + rem.join(' and ') + '.' : ' No reminders.'}</p>
    ${list.length ? html`<ul class="ics-list">${list.map(e => html`<li><span class="ics-k ${e.kind === 'cold' ? 'k-cold' : 'k-feed'}">${e.kind === 'cold' ? '❄ Cold night' : '● Feeding'}</span>
      <span><b>${e.kind === 'cold' ? 'Night before ' + midDay(e.date) : midDay(e.date)}</b><br>${e.title}</span></li>`)}</ul>
      ${D.events.length > list.length ? html`<p class="hint">And ${D.events.length - list.length} more.</p>` : ''}`
      : html`<p class="notice ok">Nothing to add right now${o.cold && !o.feed ? ': no cold nights in the forecast' : ''}.</p>`}`;
}
async function icsLoad() {
  const b = document.getElementById('ics-prev');
  try { ICS.data = await api('GET', '/api/calendar'); }
  catch (e) { if (b) b.innerHTML = rend(html`<p class="notice bad">Could not work out the dates: ${e.message}</p>`); return; }
  ICS.links = ICS.data.links;
  if (b) b.innerHTML = rend(icsPreview(ICS.data));
  icsPaintLink();
}
const icsLink = () => (ICS.links && (ICS.links.public || ICS.links.local)) || '';
function icsPaintLink() {
  const l = document.getElementById('ics-link'); if (l) l.value = icsLink();
  const w = document.getElementById('ics-linkwhere');
  if (w) w.textContent = ICS.links && ICS.links.public ? 'This link uses the internet address below, so calendar services such as Google and Outlook.com can reach it.'
    : 'This link only works on your home network until the internet address below is filled in. Google Calendar, Outlook.com and iCloud need that address: see "Get an internet address with Tailscale Funnel" below.';
}
const ck = (k) => ICS.o[k] ? raw('checked') : '';
function icsForm() {
  const o = ICS.o;
  return html`<form method="dialog" class="ics"><h2>Add to your calendar</h2>
    <p>Your feeding days and cold nights as calendar events. Subscribe to keep them up to date by themselves, or save a file to add them once.</p>
    <fieldset><legend>What to put in it</legend>
      <label class="chk"><input type="checkbox" data-act="icsopt" name="feed" autofocus ${ck('feed')}> Feeding days</label>
      <label class="chk"><input type="checkbox" data-act="icsopt" name="cold" ${ck('cold')}> Cold nights that would hurt plants that are outside (6 in the evening to 8 the next morning)</label>
      <label class="chk"><input type="checkbox" data-act="icsopt" name="close" ${ck('close')}> Include close calls (a night within a few degrees of a plant's damage point)</label>
    </fieldset>
    <fieldset><legend>Feeding days</legend>
      <label class="chk"><input type="radio" data-act="icsopt" name="weekly" value="1" ${o.weekly ? raw('checked') : ''}> One feeding day a week, listing every plant due by then</label>
      <label class="f ics-sub">Day of the week<select data-act="icsopt" name="day">${ICS.days.map((d, i) => html`<option value="${i}" ${o.day === i ? raw('selected') : ''}>${d}</option>`)}</select></label>
      <label class="chk"><input type="radio" data-act="icsopt" name="weekly" value="0" ${o.weekly ? '' : raw('checked')}> Each day a plant is due, following its own schedule</label>
      <label class="f">How far ahead to list feeding days<select data-act="icsopt" name="months">
        ${[1, 3, 6, 12].map(m => html`<option value="${m}" ${o.months === m ? raw('selected') : ''}>${m} month${m === 1 ? '' : 's'}</option>`)}</select></label>
    </fieldset>
    <fieldset><legend>Reminders</legend>
      <div class="ics-rem"><label class="chk"><input type="checkbox" data-act="icsopt" name="feed_remind" ${ck('feed_remind')}> On feeding days</label>
        <label class="f">Time<input type="time" data-act="icsopt" name="feed_at" value="${o.feed_at}" required></label></div>
      <div class="ics-rem"><label class="chk"><input type="checkbox" data-act="icsopt" name="cold_remind" ${ck('cold_remind')}> The day before a cold night</label>
        <label class="f">Time<input type="time" data-act="icsopt" name="cold_at" value="${o.cold_at}" required></label></div>
      <p class="hint">Apple Calendar, Outlook and Samsung Calendar use these times. Google Calendar uses its own reminder settings for a subscribed calendar: on a computer, open Google Calendar's Settings, choose Plant record under "Other calendars" and set its notifications there.</p>
    </fieldset>
    <div id="ics-prev" class="ics-prev" aria-live="polite">${icsPreview(null)}</div>
    <p id="ics-status" class="fc-status" role="status" aria-live="polite"></p>
    <section class="ics-part"><h3>Subscribe (updates by itself)</h3>
      <p>Your calendar checks this link now and then (Apple and Outlook every few hours, Google about once a day) and picks up new feeding days and cold nights. Your PC needs to be on for that; while it is off, the calendar keeps what it last saw.</p>
      <label class="f">Calendar link<input type="text" id="ics-link" readonly value="${icsLink()}" spellcheck="false"></label>
      <p class="hint" id="ics-linkwhere"></p>
      <div class="row"><button class="btn" type="button" data-act="icscopy">Copy calendar link</button><button class="btn ghost" type="button" data-act="icsnewlink">Make a new link</button></div>
      <p class="hint">Anyone with the link can see your feeding days and cold nights (not the rest of Plant record), so keep it private. Make a new link stops the old one working.</p>
      <label class="f">Internet address of this PC<input type="url" id="ics-pub" value="${o.public_base}" placeholder="https://your-pc.tail1234.ts.net:8443" spellcheck="false" autocomplete="off"></label>
      <p><button class="btn small ghost" type="button" data-act="icspub">Save address</button></p>
      <details class="ics-how"><summary>Get an internet address with Tailscale Funnel</summary>
        <p>Funnel lets the internet reach the calendar link only, not the rest of Plant record. It uses port 8443, so anything you already share in your tailnet with Tailscale Serve stays private.</p>
        <ol><li>Open a terminal on the PC that runs Plant record and turn on Funnel for the calendar. The command is the same in Windows cmd.exe, PowerShell and bash:
            <pre class="ics-cmd">tailscale funnel --bg --https=8443 --set-path=/cal http://127.0.0.1:8080/cal</pre>
            If Tailscale says Funnel or HTTPS is not turned on for your tailnet, open the link it shows, turn it on, and run the command again.
            If Windows says tailscale is not recognized, use the full path. In cmd.exe:
            <pre class="ics-cmd">"C:\\Program Files\\Tailscale\\tailscale.exe" funnel --bg --https=8443 --set-path=/cal http://127.0.0.1:8080/cal</pre>
            In PowerShell:
            <pre class="ics-cmd">&amp; "C:\\Program Files\\Tailscale\\tailscale.exe" funnel --bg --https=8443 --set-path=/cal http://127.0.0.1:8080/cal</pre></li>
          <li>See the address it made:
            <pre class="ics-cmd">tailscale funnel status</pre>
            It looks like https://your-pc.tail1234.ts.net:8443. Type that into "Internet address of this PC" above and press Save address.</li>
          <li>Check it: on your phone, turn Wi-Fi off and open the calendar link in the browser. It should show or download a calendar file.</li>
          <li>Subscribe with that link in each calendar (steps below).</li></ol>
        <p>Funnel keeps running after a restart. To turn it off:</p>
        <pre class="ics-cmd">tailscale funnel --https=8443 --set-path=/cal off</pre></details>
      <details class="ics-how"><summary>How to subscribe in each calendar</summary>
        <ul><li><b>Google Calendar</b> (also shows in Samsung Calendar when your Google account syncs to it): on a computer, open calendar.google.com, press the plus next to "Other calendars", choose From URL, paste the link and press Add calendar.</li>
          <li><b>Apple Calendar on iPhone:</b> Settings, Apps, Calendar, Calendar Accounts, Add Account, Other, Add Subscribed Calendar, then paste the link.</li>
          <li><b>Outlook</b> (Outlook.com or the new Outlook on the PC): Add calendar, Subscribe from web, paste the link and press Import. Outlook on your phone then shows it too.</li>
          <li><b>Samsung Calendar</b> on its own: it shows calendars from your Google or Samsung account, so subscribe in Google Calendar as above.</li></ul></details>
    </section>
    <section class="ics-part"><h3>Or save a file</h3>
      <p>Adds the events as they are today. It does not update, so save a new one now and then.</p>
      <p><button class="btn ghost" type="button" data-act="icssave">Save calendar file</button></p></section>
    <div class="row"><button class="btn ghost" value="close">Close</button></div>
  </form>`;
}
async function icsDialog() {
  try { const r = await api('GET', '/api/calendar/settings'); ICS.o = r.options; ICS.links = r.links; ICS.days = r.days; }
  catch (e) { toast('Could not open the calendar choices: ' + e.message, true); return; }
  ICS.data = null;
  const p = modal(icsForm(), 'ics-dlg');
  icsPaintLink(); icsLoad();
  await p;
}
async function icsPut(change, msg) {
  try { const r = await api('PUT', '/api/calendar/settings', change); ICS.o = r.options; ICS.links = r.links; }
  catch (e) { icsSay('Not saved: ' + e.message); return false; }
  icsSay(msg || 'Saved. Your subscribed calendar picks this up the next time it checks.');
  icsLoad();
  return true;
}
Object.assign(acts, {
  icsopen() { icsDialog(); },
  icssave() {
    if (!ICS.o.feed && !ICS.o.cold) { icsSay('Choose feeding days, cold nights or both first.'); return; }
    const a = document.createElement('a');
    a.href = '/api/calendar.ics' + (PLACE ? '?place=' + enc(PLACE) : ''); a.download = ''; document.body.appendChild(a); a.click(); a.remove();
    icsSay('Saved to your Downloads folder. Open it to add the events to your calendar.');
  },
  async icscopy() {
    const t = document.getElementById('ics-link'); if (!t) return;
    let ok = false;
    try { await navigator.clipboard.writeText(t.value); ok = true; }
    catch (e) { t.focus(); t.select(); try { ok = document.execCommand('copy'); } catch (e2) { ok = false; } }
    icsSay(ok ? 'Link copied. Paste it into your calendar app; "How to subscribe in each calendar" has the steps.' : 'This browser would not copy it. The link is selected: press Ctrl+C to copy it.');
  },
  async icsnewlink() {
    try { const r = await api('POST', '/api/calendar/new-link'); ICS.links = r.links; }
    catch (e) { icsSay('No new link made: ' + e.message); return; }
    icsPaintLink(); icsSay('New link made. The old one has stopped working, so subscribe again with this one.');
  },
  async icspub() {
    const v = (document.getElementById('ics-pub') || {}).value || '';
    if (await icsPut({ public_base: v.trim() }, v.trim() ? 'Address saved. The calendar link now uses it.' : 'Address removed. The link only works on your home network now.')) icsPaintLink();
  },
});
Object.assign(changeActs, {
  icsopt(el) {
    let v;
    if (el.type === 'checkbox') v = el.checked;
    else if (el.type === 'radio') v = el.value === '1';
    else if (el.type === 'time') { if (!el.value) return; v = el.value; }
    else v = +el.value;
    icsPut({ [el.name]: v });
  },
});
