/* Plant record front end. Plain JavaScript, no inline handlers (the server's content policy forbids them). */
(function () {
'use strict';

// ---------- helpers ----------
const app = document.getElementById('app');
class Raw { constructor(s) { this.s = s; } }
const raw = s => new Raw(String(s));
const ESC = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
const esc = s => String(s).replace(/[&<>"']/g, c => ESC[c]);
function rend(v) {
  if (v == null || v === false) return '';
  if (v instanceof Raw) return v.s;
  if (Array.isArray(v)) return v.map(rend).join('');
  return esc(v);
}
function html(strs, ...vals) {
  let out = '';
  strs.forEach((s, i) => { out += s; if (i < vals.length) out += rend(vals[i]); });
  return new Raw(out);
}
const enc = encodeURIComponent;
// ---------- plant codes in text become links with a photo preview ----------
let PCODES = new Map(), PCODES_AT = 0;
async function loadCodes(force) {
  if (!force && Date.now() - PCODES_AT < 15000) return;
  try { const list = await api('GET', '/api/plants?status=all'); PCODES = new Map(list.map(p => [p.code, p])); PCODES_AT = Date.now(); } catch (e) { /* links just stay plain text */ }
}
function linkify(text) {
  const t = String(text == null ? '' : text);
  let out = '', last = 0;
  t.replace(/\bP-\d{3,4}\b/g, (m, i) => {
    out += esc(t.slice(last, i));
    const p = PCODES.get(m);
    out += p ? `<a class="plink" href="#/plant/${enc(m)}" data-code="${esc(m)}" aria-label="${esc(m + ' ' + p.common_name)}">${esc(m)}</a>` : esc(m);
    last = i + m.length; return m;
  });
  return raw(out + esc(t.slice(last)));
}
const lines = s => String(s || '').split('\n').map(x => x.trim()).filter(Boolean);
const paras = s => lines(s).length ? html`<p class="pl">${linkify(String(s).trim())}</p>` : '';
const ul = s => lines(s).length ? html`<ul>${lines(s).map(x => html`<li>${linkify(x)}</li>`)}</ul>` : '';
const ol = s => lines(s).length ? html`<ol>${lines(s).map(x => html`<li>${linkify(x)}</li>`)}</ol>` : '';
const deg = n => (n == null || n === '') ? 'not set' : n + '°F';
function when(ts) {
  if (!ts) return '';
  const d = new Date(ts);
  if (isNaN(d)) return ts;
  return d.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
}
const timeEl = ts => ts ? html`<time datetime="${ts}" title="${ts} (UTC)">${when(ts)}</time>` : '';
const photoUrl = f => '/photos/' + enc(f);
const thumbUrl = f => '/thumbs/' + enc(f);
const r1 = n => Math.round(n * 10) / 10;           // avoids 3.7000000000000003
const clamp = (n, a, b) => Math.max(a, Math.min(b, n));

const PLAN_CLASS = { 'Move indoors': 'p-move', 'Protect outside': 'p-protect', 'Hardy outside': 'p-hardy', 'Seasonal die-back': 'p-die', 'Annual': 'p-annual' };
const PLAN_COLOR = { 'Move indoors': 'var(--cyan)', 'Protect outside': 'var(--ochre)', 'Hardy outside': 'var(--moss)', 'Seasonal die-back': 'var(--ink-2)', 'Annual': 'var(--ink-2)' };
const HEALTH_CLASS = { Good: 'h-good', Fair: 'h-fair', Poor: 'h-poor', Critical: 'h-critical' };
const HEALTH_COLOR = { Good: 'var(--moss)', Fair: 'var(--ochre)', Poor: 'var(--madder)', Critical: 'var(--critical)' };
const HEALTH_ORDER = { Critical: 0, Poor: 1, Fair: 2, Good: 3 };
const planTag = p => html`<span class="tag ${PLAN_CLASS[p] || ''}">${p}</span>`;
const healthTag = h => html`<span class="tag ${HEALTH_CLASS[h] || ''}">Health: ${h}</span>`;
const confColor = n => n == null ? 'var(--line)' : n >= 80 ? 'var(--moss)' : n >= 55 ? 'var(--ochre)' : 'var(--madder)';

// ---------- state ----------
let META = null, token = 0, lastPath = null;
let memName = '';
function getName() { try { return localStorage.getItem('plantdb.editor') || memName; } catch (e) { return memName; } }
function setName(n) { memName = n; try { localStorage.setItem('plantdb.editor', n); } catch (e) { /* storage blocked */ } paintWho(); }
const cleanName = n => String(n || '').replace(/[^\w .\-@]/g, '').trim().slice(0, 40);
// 1.12.0: people who open the app through Tailscale are signed in by it; on this computer the name is typed in as before
const ME = () => (META && META.me) || { via: 'local', role: 'owner', name: '', login: null, owner_name: '' };
const viaTS = () => ME().via === 'tailscale';
function paintWho() {
  const n = viaTS() ? ME().name : getName(), el = document.getElementById('who-name');
  if (el) el.textContent = viaTS() ? 'Signed in as ' + n : n ? 'Editing as ' + n : 'Set your name';
  document.documentElement.dataset.role = ME().role;
}

// ---------- api ----------
// the place this browser uses for weather, frost, watering and "today" (1.11.0); null = the home place
let PLACE = null;
try { PLACE = localStorage.getItem('plantdb.place') || null; } catch (e) { /* ignore */ }
async function api(method, url, body, form) {
  if (method === 'GET' && /^\/api\/fungi\/NEW-/i.test(url)) {        // 1.24.0: a find made offline that is not sent yet
    const f = await idbGet('finds', decodeURIComponent(url.split('/')[3].split('?')[0]));
    if (!f) { const e = new Error('That find was sent to the plant record. Open the Mushrooms page to see it with its new code.'); e.status = 404; throw e; }
    return offFindDict(f);
  }
  const opts = { method, headers: {} };
  if (PLACE) opts.headers['X-Place'] = PLACE;
  if (method !== 'GET') opts.headers['X-Editor'] = cleanName(viaTS() ? ME().name : getName()) || 'Unknown';
  if (method !== 'GET' && ME().role === 'viewer' && url !== '/api/me' && !url.startsWith('/api/identify?')) {      // the server refuses these too; this just says so sooner
    const e = new Error(`You can look at everything, but changes are turned off for you. Ask ${ME().owner_name || 'the owner'} if you would like to edit.`); e.status = 403; throw e;
  }
  if (form) opts.body = form;
  else if (body !== undefined) { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
  // 1.24.0: changes that can wait are kept on this device when the server can't be reached, and sent later (offSync)
  const q = method !== 'GET' && offQueueable(method, url);
  if (q && (!navigator.onLine || /\/NEW-/i.test(url))) return offQueue(method, url, body, form);
  if (q) opts.headers['X-Offline-Op'] = offId();          // so a retry after a dropped answer is made only once
  let r;
  try { r = await fetch(url, opts); } catch (e) {
    if (q) return offQueue(method, url, body, form);
    if (method === 'POST' && url.startsWith('/api/identify?') && form) return offIdQueue(url, form);
    throw new Error(navigator.onLine ? 'Cannot reach the plant server. Check that the container is running.' : 'You are offline. This needs a connection to the plant server.');
  }
  if (method === 'GET') offSeen(r.headers.get('X-Offline-Saved'));
  let data = null;
  try { data = await r.json(); } catch (e) { /* not json */ }
  if (!r.ok) {
    const off = r.status === 503 && data && data.offline;
    const e = new Error(off ? 'You are offline, and this page was not saved on this device. Turn on "Keep a copy on this device" on the Offline page while you are online.' : (data && data.error) || ('Request failed (' + r.status + ')'));
    e.status = r.status; e.data = data; e.offline = off; throw e;
  }
  if (method === 'GET' && /^\/api\/fungi\?status=(active|all)/.test(url) && data && data.finds) data.finds = (await offPendingFinds()).concat(data.finds);
  return data;
}

// ---------- location: the place whose weather this browser uses (1.11.0) ----------
const placeName = () => (META && META.place && META.place.name) || 'your location';
const placeShort = () => placeName().split(',')[0].trim();
function savePlace(id) {
  PLACE = id ? String(id) : null;
  try { if (PLACE) localStorage.setItem('plantdb.place', PLACE); else localStorage.removeItem('plantdb.place'); } catch (e) { /* this visit only */ }
}
function placeChanged(id) {         // choosing the home place stores nothing, so the browser follows home if home changes later
  const P = ((META && META.places) || []).find(x => String(x.id) === String(id));
  savePlace(P && P.is_home ? null : id);
  META = null; COND = null; FROST = null; FROST_AT = 0;          // all of these depend on the place
  if (typeof WT !== 'undefined') WT.page = 1;
  if (typeof WX !== 'undefined') WX.compare = WX.compare.filter(x => String(x) !== String(id));
}
function paintPlace() {
  if (!META || !META.place) return;
  if (PLACE && String(META.place.id) !== String(PLACE)) savePlace(null);   // the chosen place was removed: back to home
  const n = document.getElementById('place-name'); if (n) n.textContent = META.place.name;
  const b = document.getElementById('place-btn');
  if (b) b.setAttribute('aria-label', `Location: ${META.place.name}${META.place.is_home ? ' (home)' : ''}. Choose another place`);
}
function placeDialog() {
  const cur = META && META.place, list = (META && META.places) || [];
  modal(html`<form method="dialog" class="plc"><h2>Location</h2>
    <p class="muted">Weather, frost warnings, watering reminders, the Winter plan and "today" on every page use this place. This browser remembers it; other computers and phones keep their own.</p>
    <fieldset class="opt-group"><legend>Use the weather for</legend><div class="plc-list">
      ${list.map(p => html`<label class="plc-opt"><input type="radio" name="plc" data-plc="${p.id}" value="${p.id}" ${cur && String(cur.id) === String(p.id) ? raw('checked') : ''}>
        <span><strong>${p.name}</strong>${p.is_home ? html`<span class="tag-home">Home</span>` : ''}${p.enabled ? '' : html`<span class="hint"> Hourly updates are off, so its weather may be old.</span>`}</span></label>`)}</div>
      <p id="plc-msg" class="dbg-msg" role="status" aria-live="polite"></p><div id="plc-home">${plcHomeRow()}</div></fieldset>
    <fieldset class="opt-group"><legend>Add a place</legend>
      <div class="todo-add plc-search"><label class="f">Town or city<input type="text" name="plcq" placeholder="For example, Denver" autocomplete="off" enterkeyhint="search"></label>
        <button class="btn" type="button" data-act="plcsearch">Search</button></div>
      <div id="plc-results" aria-live="polite"></div>
      <p class="hint">A new place gets its last 3 months of weather and its forecast straight away. To rename, remove or stop updating a place, use <a href="#/weather" data-act="plcweather">the Weather page</a>.</p></fieldset>
    <div class="row"><button class="btn" value="ok" autofocus>Done</button></div></form>`, 'plc-dlg');
}
function plcHomeRow() {         // the home place is where a new browser starts, and what the hourly updates and backups use
  const cur = META && META.place, home = ((META && META.places) || []).find(x => x.is_home);
  if (!cur) return '';
  if (cur.is_home) return html`<p class="hint">${cur.name} is the home place: other computers and phones use it until they choose their own location.</p>`;
  return html`<p class="hint">Other computers and phones still use the home place${home ? `, ${home.name}` : ''}, until they choose their own.</p>
    <p><button class="btn ghost small" type="button" data-act="plchome">Make ${cur.name} the home place for everyone</button></p>`;
}
async function placeSearch() {
  const q = (dlg.querySelector('[name=plcq]') || {}).value || '', box = document.getElementById('plc-results'); if (!box) return;
  if (q.trim().length < 2) { box.innerHTML = rend(html`<p class="bad-text">Type at least 2 letters.</p>`); return; }
  box.innerHTML = rend(html`<p class="loading">Searching</p>`);
  try {
    const res = await api('GET', '/api/places/search?q=' + enc(q.trim()));
    PLCRES = res;
    box.innerHTML = rend(res.length ? html`<ul class="place-res">${res.map((r, i) => html`<li><span>${r.label}<span class="hint"> ${r.lat}, ${r.lon}</span></span>
      <button class="btn small" type="button" data-act="plcadd" data-i="${i}">Add and use ${r.name}</button></li>`)}</ul>` : html`<p class="muted">No town by that name. Try another spelling, or add it on the Weather page by latitude and longitude.</p>`);
    const first = box.querySelector('button'); if (first) first.focus();
  } catch (e) { box.innerHTML = rend(html`<p class="bad-text">${e.message}</p>`); }
}
let PLCRES = [];
async function placeAdd(i) {
  const r = PLCRES[i]; if (!r || !(await needName())) return;
  const m = document.getElementById('plc-msg');
  try {
    let res;
    try { res = await api('POST', '/api/places', { name: r.name, lat: r.lat, lon: r.lon, tz: r.tz }); }
    catch (e) { if (e.status === 409) res = await api('POST', '/api/places', { name: r.name, lat: r.lat, lon: r.lon, tz: r.tz, force: true }); else throw e; }
    placeChanged(String(res.place.id));
    await route();
    if (dlg.open) dlg.close();
    toast(`${res.place.name} added and in use. Fetching its weather now; it takes about a minute.`);
    document.body.dataset.job = '1'; if (typeof wxPoll === 'function') wxPoll();
  } catch (e) { if (m) m.textContent = e.message; else toast(e.message, true); }
}

// ---------- you, and the people who can use the app (1.12.0) ----------
async function whoDialog() {
  const me = ME(), ts = viaTS(), owner = me.role === 'owner';
  let P = null;
  if (owner) { try { P = await api('GET', '/api/people'); } catch (e) { P = null; } }
  modal(html`<form method="dialog" class="who-dlg"><h2>${ts ? 'You' : 'Who is editing?'}</h2>
    ${ts ? html`<p>You are signed in through Tailscale as <strong>${me.login}</strong>. ${me.role === 'owner' ? 'You can do everything, including backups and choosing who can use the app.' : me.role === 'editor' ? 'You can look at everything and make changes.' : `You can look at everything, but not make changes. Ask ${me.owner_name} if you would like to edit.`}</p>`
      : html`<p>On this computer you have full access. Your name goes into the audit log next to every change; it is typed in, not checked.</p>`}
    <div class="todo-add who-name"><label class="f">${ts ? 'Your name in the audit log' : 'Your name'}<input type="text" name="n" maxlength="40" autocomplete="name" value="${ts ? me.name : getName()}"></label>
      <button class="btn" type="button" data-act="whosave">Save name</button></div>
    <p id="who-msg" class="dbg-msg" role="status" aria-live="polite"></p>
    ${owner ? html`<fieldset class="opt-group"><legend>People who can use the app</legend><div id="people-box">${peopleRows(P)}</div>
      <p class="hint"><strong>Can view only:</strong> sees everything, changes nothing. <strong>Can edit:</strong> also changes plants, care, photos and answers. <strong>Owner:</strong> also backups, settings and this list.</p>
      <p class="hint">To let someone in from outside your home, share the plants device with them in Tailscale (README: "Using the app away from home"). They appear here the first time they open the app, as "Can view only". On this computer everything stays open.</p></fieldset>` : ''}
    <div class="row"><button class="btn ghost" value="ok" autofocus>Done</button></div></form>`, 'who-dialog');
}
function peopleRows(P) {
  if (!P) return html`<p class="muted">The list could not be loaded.</p>`;
  if (!P.people.length) return html`<p class="muted">Nobody has opened the app through Tailscale yet.</p>`;
  const self = ME().login;
  return html`<ul class="people">${P.people.map(p => html`<li><span><strong>${p.name}</strong>${p.login === self ? ' (you)' : ''}<br><span class="hint">${p.login}. Last here ${when(p.last_seen)}.</span></span>
    <label class="f">What ${p.name} can do<select data-f="prole" data-login="${p.login}">${P.roles.map(r => html`<option value="${r.key}" ${r.key === p.role ? raw('selected') : ''}>${r.label}</option>`)}</select></label>
    ${p.login === self ? '' : html`<button class="btn small danger" type="button" data-act="pdel" data-login="${p.login}" data-name="${p.name}">Remove</button>`}</li>`)}</ul>`;
}
function peoplePaint(P) { const b = document.getElementById('people-box'); if (b) b.innerHTML = rend(peopleRows(P)); }

// ---------- toast, dialog ----------
function toast(msg, isErr) {
  if (!isErr && Date.now() - OFF.queuedAt < 2500) { msg = String(msg).replace(/\.$/, '') + '. Kept on this device; it will be sent when you are back online.'; OFF.queuedAt = 0; }
  const t = document.createElement('div');
  t.className = 'toast' + (isErr ? ' err' : '');
  t.textContent = msg;
  document.getElementById('toasts').appendChild(t);
  setTimeout(() => t.remove(), isErr ? 7000 : 3500);
}
const dlg = document.getElementById('dlg');
function modal(content, cls) {
  dlg.className = cls || '';
  dlg.innerHTML = rend(content);
  return new Promise(res => {
    const done = () => { dlg.removeEventListener('close', done); res(dlg.returnValue); };
    dlg.addEventListener('close', done);
    dlg.returnValue = '';
    dlg.showModal();
    const f = dlg.querySelector('[autofocus]') || dlg.querySelector('input,select,textarea');
    if (f) f.focus();
  });
}
async function confirmBox(title, text, okLabel, danger) {
  const r = await modal(html`<form method="dialog"><h2>${title}</h2><p>${text}</p>
    <div class="row"><button class="btn ${danger ? 'danger' : ''}" value="ok">${okLabel}</button>
    <button class="btn ghost" value="cancel" autofocus>Cancel</button></div></form>`);
  return r === 'ok';
}
async function askName(force) {
  if (viaTS()) { if (force) whoDialog(); return ME().role !== 'viewer'; }
  if (getName() && !force) return true;
  const r = await modal(html`<form method="dialog"><h2>Who is editing?</h2>
    <p>Your name goes into the change log next to every edit you make. It is typed in by you and is not checked, so it records who says they made the change.</p>
    <label class="f">Your name<input type="text" name="n" maxlength="40" autocomplete="name" value="${getName()}"></label>
    <div class="row"><button class="btn" value="ok">Save name</button><button class="btn ghost" value="cancel">Cancel</button></div></form>`);
  if (r !== 'ok') return !!getName();
  const n = cleanName(dlg.querySelector('[name=n]').value);
  if (!n) { toast('Enter a name to continue.', true); return !!getName(); }
  setName(n);
  return true;
}
const needName = () => askName(false);

async function guard(fn) {
  try { return await fn(); } catch (e) { toast(e.message, true); return undefined; }
}

// ---------- router ----------
function go(h) { if (location.hash === h) route(); else location.hash = h; }
window.addEventListener('hashchange', route);
async function route() {
  const my = ++token;
  OFF.saved = null;
  const h = location.hash.replace(/^#/, '') || '/';
  const [hp, hq] = h.split('?');                     // 1.18.0: #/library?q=... keeps the search in the address
  const parts = hp.split('/').filter(Boolean), qs = new URLSearchParams(hq || '');
  if (parts[0] !== 'identify') idStop();
  if (parts[0] !== 'new') NEWFILL = null;
  if (parts[0] !== 'fungi' || parts[1] !== 'new') MUFILL = null;
  const nav = parts[0] === 'winter' || parts[0] === 'frost' || parts[0] === 'inside' || parts[0] === 'outside' ? 'winter' : parts[0] === 'weather' ? 'weather' : parts[0] === 'fertilizer' ? 'fertilizer' : parts[0] === 'lights' ? 'lights' : parts[0] === 'photos' ? 'photos' : parts[0] === 'labels' ? 'labels' : parts[0] === 'history' || parts[0] === 'audit' ? 'history' : parts[0] === 'backups' ? 'backups' : parts[0] === 'groups' || parts[0] === 'group' ? 'groups' : parts[0] === 'identify' ? 'identify' : parts[0] === 'library' || parts[0] === 'species' || parts[0] === 'wishlist' || parts[0] === 'around' ? 'library' : parts[0] === 'fungi' ? 'fungi' : parts[0] === 'offline' || parts[0] === 'decisions' ? 'offline' : 'plants';
  document.querySelectorAll('[data-nav]').forEach(a => { if (a.dataset.nav === nav) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); });
  try {
    let view;
    await Promise.all([loadCodes(), loadFrost(), loadGroups(parts[0] === 'groups' || parts[0] === 'group' || !parts.length), G.care && !CAREDUE ? loadCareDue() : null]);
    if (!META) { META = await api('GET', '/api/meta'); const v = document.getElementById('app-ver'); if (v && META.version) v.textContent = 'v' + META.version; paintPlace(); paintWho(); }
    if (parts[0] === 'plant' && parts[1] && parts[2] === 'edit') view = await viewEdit(decodeURIComponent(parts[1]));
    else if (parts[0] === 'plant' && parts[1]) view = await viewPlant(decodeURIComponent(parts[1]));
    else if (parts[0] === 'new') view = viewForm(null);
    else if (parts[0] === 'winter') view = await viewWinter();
    else if (parts[0] === 'weather') view = await viewWeather();
    else if (parts[0] === 'today') view = await viewToday();
    else if (parts[0] === 'fertilizer') view = await viewFertilizer();
    else if (parts[0] === 'lights') view = await viewLights();
    else if (parts[0] === 'groups') view = await viewGroups();
    else if (parts[0] === 'group' && parts[1]) view = await viewGroup(parts[1]);
    else if (parts[0] === 'photos') view = await viewPhotos();
    else if (parts[0] === 'labels') view = await viewLabels();
    else if (parts[0] === 'history' || parts[0] === 'audit') view = await viewHistory();
    else if (parts[0] === 'backups') view = await viewBackups();
    else if (parts[0] === 'frost') view = await viewFrost();
    else if (parts[0] === 'inside') view = await viewInside();
    else if (parts[0] === 'outside') view = await viewOutside();
    else if (parts[0] === 'identify') view = await viewIdentify();
    else if (parts[0] === 'library') view = await viewLibrary(qs);
    else if (parts[0] === 'species' && parts[1]) view = await viewSpecies(decodeURIComponent(parts[1]));
    else if (parts[0] === 'wishlist') view = await viewWishlist();
    else if (parts[0] === 'offline') view = await viewOffline();
    else if (parts[0] === 'decisions') view = await viewDecisions();
    else if (parts[0] === 'around') view = await viewAround();
    else if (parts[0] === 'fungi' && !parts[1]) view = await viewFungi();
    else if (parts[0] === 'fungi' && parts[1] === 'safety') view = viewFungiSafety();
    else if (parts[0] === 'fungi' && parts[1] === 'new') view = await viewFindForm(null);
    else if (parts[0] === 'fungi' && parts[2] === 'edit') view = await viewFindForm(decodeURIComponent(parts[1]));
    else if (parts[0] === 'fungi') view = await viewFind(decodeURIComponent(parts[1]));
    else view = await viewGallery();
    if (my !== token) return;
    app.innerHTML = rend(view.html);
    if (parts[0] !== 'frost' && parts[0] !== 'plant') app.insertAdjacentHTML('afterbegin', rend(frostBanner()));   // plant pages have their own note
    if (OFF.saved && OFF.saved !== 'none') app.insertAdjacentHTML('afterbegin', rend(html`<p class="notice off-note noprint" role="note"><strong>Offline.</strong> This is what this device saved${OFF.saved ? ' on ' + when(OFF.saved) : ''}. Changes you make are kept here and sent when you are back online. <a href="#/offline">Offline page</a></p>`));
    offNotice(parts);
    if (ME().role === 'viewer') app.insertAdjacentHTML('afterbegin', rend(html`<p class="notice vw-note noprint" role="note"><strong>View only.</strong> You can look at everything here, but changes are turned off. Ask ${ME().owner_name} if you would like to edit.</p>`));
    if (view.title) document.title = view.title + ' | Plant record'; else document.title = 'Plant record';
    if (view.after) view.after();
    buildSideNav(); navLayout(); addReadButtons(); setTimeout(() => { buildSideNav(); navLayout(); addReadButtons(); }, 1200);
    if (h !== lastPath) { window.scrollTo(0, 0); app.focus({ preventScroll: true }); }
    lastPath = h;
  } catch (e) {
    if (my !== token) return;
    app.innerHTML = rend(html`<div class="notice bad" role="alert"><strong>${e.status === 404 ? 'Not found' : 'Something went wrong'}</strong><p>${e.message}</p>
      <a class="btn ghost" href="#/">Back to all plants</a></div>`);
  }
}


// ---------- section menu (left or right, can be folded away) ----------
let NAVSESSION = null;                // on narrow screens the menu starts folded; opening it there lasts until a link is chosen
function navOpen() { const P = window.PlantPrefs.get(), narrow = document.documentElement.dataset.narrow === '1'; return NAVSESSION != null ? NAVSESSION : (P.navopen === '1' && !narrow); }
function navLayout() {
  const r = document.documentElement, top = document.querySelector('.top');
  r.style.setProperty('--top-h', (r.dataset.narrow === '1' ? 0 : (top ? top.getBoundingClientRect().height : 64)) + 'px');   // on phones the top bar scrolls away
  const open = navOpen();
  r.dataset.navopen = open ? '1' : '0';
  const side = window.PlantPrefs.get().navside;
  const sb = document.getElementById('sn-side'); if (sb) sb.textContent = side === 'left' ? 'Move right' : 'Move left'; sb.title = side === 'left' ? 'Move this menu to the right side' : 'Move this menu to the left side';
  document.querySelectorAll('[data-act=navtoggle]').forEach(b => b.setAttribute('aria-expanded', open ? 'true' : 'false'));
  const tab = document.getElementById('nav-tab');
  r.dataset.tabgap = '0';
  if (!open && tab && r.dataset.narrow !== '1') {
    r.style.setProperty('--tab-w', tab.offsetWidth + 'px');
    const m = document.getElementById('app').getBoundingClientRect();
    const gap = side === 'left' ? m.left : window.innerWidth - m.right;
    if (gap < tab.offsetWidth + 8) r.dataset.tabgap = '1';
  }
  const bar = document.querySelector('.wx-bar'); if (bar) r.style.setProperty('--bar-h', bar.offsetHeight + 'px');
  const h2 = document.querySelector('main section.blk > h2'); if (h2) r.style.setProperty('--h2-h', h2.offsetHeight + 'px');
  document.querySelectorAll('.pane').forEach(p => { const j = p.querySelector('.jump'); p.style.setProperty('--jump-h', (j ? j.offsetHeight : 0) + 'px'); });
  pnavLayout();
}
document.addEventListener('toggle', e => { if (e.target && e.target.id === 'pn-filters') PNOPEN = e.target.open; if (e.target && e.target.id === 'more-f') MOREOPEN = e.target.open; }, true);
let NAVITEMS = [];
function buildSideNav() {
  const list = document.getElementById('sn-list'); if (!list) return;
  const app = document.getElementById('app'), used = new Set();
  const slug = t => { let b = 'sec-' + t.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40) || 'sec', k = b, i = 2; while (used.has(k) || (document.getElementById(k) && document.getElementById(k).dataset.navid !== '1')) k = b + '-' + i++; used.add(k); return k; };
  NAVITEMS = [];
  const h1 = app.querySelector('h1');
  if (h1) NAVITEMS.push({ el: h1, text: 'Top of the page', id: null, top: true });
  // 1.14.1: every section title (h2) plus any part marked data-section="Its name", in page order, so new sections join by themselves
  const seen = new Set();
  app.querySelectorAll('h2, [data-section]').forEach(h => {
    if (h.closest('dialog,.chart-card,#sidenav') || !h.offsetParent) return;
    const marked = h.matches("[data-section]"), sec = marked ? h : (h.closest('section') || h);
    if (seen.has(sec) || (!marked && sec.closest("[data-section]") && sec.closest("[data-section]") !== sec)) return;
    seen.add(sec);
    const text = marked ? h.dataset.section : h.textContent.trim();
    if (!sec.id) { sec.id = slug(text); sec.dataset.navid = '1'; }
    NAVITEMS.push({ el: sec, head: marked ? sec : h, text, id: sec.id });
  });
  buildJumpRow();
  list.innerHTML = rend(html`${NAVITEMS.map((it, i) => html`<li><a href="#${it.id || 'app'}" data-act="navgo" data-i="${i}">${it.text}</a></li>`)}`);
  if (!NAVITEMS.length) list.innerHTML = rend(html`<li class="muted">This page has no sections.</li>`);
  navActive();
}
// the row of section buttons on plant pages: the same sections as the menu, with shorter names where the title is long
const JUMP_SHORT = { 'Name and details': 'Details', 'Current conditions': 'Now', 'Needed from you': 'Needed', 'Requests (all answered)': 'Requests',
  'Getting this plant back in range': 'Back in range', 'In range': 'In range', 'Plant identification': 'Identification', 'About this plant': 'About',
  'Sunlight': 'Light', 'Getting ready to come inside': 'Coming inside', 'Pests and diseases': 'Pests', 'Page history': 'History' };
function buildJumpRow() {
  const row = document.getElementById('jumprow'), pane = document.getElementById('pane-r'); if (!row || !pane) return;
  const items = NAVITEMS.filter(it => !it.top && pane.contains(it.el) && !row.contains(it.el));
  const name = it => it.el.dataset.short || JUMP_SHORT[it.text] || (/^Winter in /.test(it.text) ? 'Winter' : it.text);
  const want = items.map(it => it.id + '|' + name(it)).join(',');
  if (row.dataset.built === want) return;          // unchanged: keep the buttons (and any focus on them)
  row.dataset.built = want;
  row.innerHTML = rend(html`${items.map(it => html`<button class="btn ghost small" type="button" data-act="jump" data-id="${it.id}">${name(it)}</button>`)}`);
}
function scrollToSection(t) {
  const beh = matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', pane = t.closest('.pane');
  const split = document.documentElement.dataset.layout !== 'single' && document.documentElement.dataset.narrow !== '1';
  if (pane && split) {   // scroll only this half, not the whole page
    const jb = pane.querySelector('.jump'), off = jb ? jb.offsetHeight + 8 : 8;
    pane.scrollTo({ top: pane.scrollTop + t.getBoundingClientRect().top - pane.getBoundingClientRect().top - off, behavior: beh });
  } else t.scrollIntoView({ behavior: beh, block: 'start' });
  const h = t.matches('h1,h2') ? t : (t.querySelector('h2,h1') || t);
  if (h) { if (!h.hasAttribute('tabindex')) h.setAttribute('tabindex', '-1'); h.focus({ preventScroll: true }); }
}
let navRaf = 0;
function navActive() {
  cancelAnimationFrame(navRaf);
  navRaf = requestAnimationFrame(() => {
    const th = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--top-h')) || 64, line = th + (window.innerHeight - th) * 0.35;
    let cur = 0;
    NAVITEMS.forEach((it, i) => { const r = it.el.getBoundingClientRect(); if (r.top <= line && r.bottom > 0) cur = i; });
    document.querySelectorAll('#sn-list a').forEach((a, i) => { if (i === cur) a.setAttribute('aria-current', 'true'); else a.removeAttribute('aria-current'); });
  });
}
window.addEventListener('scroll', navActive, { capture: true, passive: true });

// ---------- gallery ----------
const G = { q: '', plan: '', health: '', low: false, needs: false, sort: 'code', group: '', status: 'active', site: '',   // 1.16.2: status and site
  light: '', pets: '', hardy: '', care: '', grow: '', leaf: '', pot: '', photo: '' };                                      // 1.17.0: more filters
const MORE_KEYS = ['light', 'pets', 'hardy', 'care', 'grow', 'leaf', 'pot', 'photo'];     // the More filters (defined further down)
// the Plants page filters are remembered in this browser and also decide where Previous / Next plant go on plant pages
try { const s = JSON.parse(localStorage.getItem('plantdb.filters') || '{}'); for (const k of ['q', 'plan', 'health', 'low', 'needs', 'sort', 'group', 'status', 'site', ...MORE_KEYS]) if (k in s && typeof s[k] === typeof G[k]) G[k] = s[k]; } catch (e) { /* defaults */ }
function gSave() { try { localStorage.setItem('plantdb.filters', JSON.stringify({ q: G.q, plan: G.plan, health: G.health, low: G.low, needs: G.needs, sort: G.sort, group: G.group, status: G.status, site: G.site, ...Object.fromEntries(MORE_KEYS.map(k => [k, G[k]])) })); } catch (e) { /* not saved */ } }
const gActive = () => !!(G.q.trim() || G.plan || G.health || G.low || G.needs || (G.group && groupById(G.group)) || G.status !== 'active' || G.site || moreOn());
const STATUS_WORD = { active: 'Active only', all: 'Active and archived', archived: 'Archived only' };
const isArch = p => p.status === 'archived';
const statusOk = p => G.status === 'all' || (G.status === 'archived' ? isArch(p) : !isArch(p));
const needsYou = p => (p.requests_open || 0) > 0 || (p.id_confidence != null && p.id_confidence < 70);
let ALL = [];
const SORTS = { code: 'Code', health: 'Health, worst first', conf: 'ID confidence, lowest first', updated: 'Recently updated', name: 'Name A to Z', group: 'Group A to Z' };

function filteredPlants(list) {
  const q = G.q.trim().toLowerCase();
  let r = (list || ALL).filter(p =>
    statusOk(p) && (!G.site || (p.site || 'Outdoors') === G.site) && moreOk(p) &&
    (!G.plan || p.winter_plan === G.plan) && (!G.health || p.health_rating === G.health) &&
    (!G.low || (p.id_confidence != null && p.id_confidence < 70)) && (!G.needs || needsYou(p)) && inGroupFilter(p.code) &&
    (!q || [p.code, p.common_name, p.scientific_name, p.aliases, p.plant_type, p.location].join(' ').toLowerCase().includes(q)));
  return r.sort(plantCmp());
}
function plantCmp() {
  return {
    code: (a, b) => a.code.localeCompare(b.code),
    health: (a, b) => (HEALTH_ORDER[a.health_rating] - HEALTH_ORDER[b.health_rating]) || a.code.localeCompare(b.code),
    conf: (a, b) => ((a.id_confidence ?? 101) - (b.id_confidence ?? 101)) || a.code.localeCompare(b.code),
    updated: (a, b) => String(b.updated_at).localeCompare(String(a.updated_at)),
    name: (a, b) => a.common_name.localeCompare(b.common_name),
    group: (a, b) => { const x = groupNames(a.code)[0], y = groupNames(b.code)[0]; return (!x - !y) || (x || '').localeCompare(y || '') || a.code.localeCompare(b.code); },
  }[G.sort] || ((a, b) => a.code.localeCompare(b.code));
}
// 1.20.0: the card is no longer one big link, so it can hold buttons. The name is the link, and it stretches over the whole
// card (CSS), so the card still opens the plant from anywhere. The photo has its own Previous and Next buttons and can be swiped.
const GPIX = new Map();                       // plant code -> which of its photos the card shows (kept while the page is open)
function sheetPhotos(p) { return p.photos && p.photos.length ? p.photos : p.photo ? [p.photo] : []; }
function sheetMat(p) {
  const ph = sheetPhotos(p), n = ph.length, i = n ? ((GPIX.get(p.code) || 0) % n + n) % n : 0;
  return html`${n ? html`<img src="${thumbUrl(ph[i])}" alt="${n > 1 ? `Photo ${i + 1} of ${n}` : ''}" loading="lazy" decoding="async" width="520" height="650">` : html`<div class="nophoto">No photo yet</div>`}
      <span class="acc">${p.code}</span>
      ${n > 1 ? html`<div class="ph-nav noprint"><button type="button" class="ph-btn" data-act="gphoto" data-code="${p.code}" data-d="-1" aria-label="Previous photo of ${p.common_name}">‹</button>
        <span class="ph-n" aria-live="polite">${i + 1} of ${n}</span>
        <button type="button" class="ph-btn" data-act="gphoto" data-code="${p.code}" data-d="1" aria-label="Next photo of ${p.common_name}">›</button></div>` : ''}
      <div class="bar" style="--hb:${HEALTH_COLOR[p.health_rating] || 'var(--line)'}"></div>`;
}
function sheet(p) {
  return html`<article class="sheet" data-code="${p.code}">
    <div class="mat">${sheetMat(p)}</div>
    <h3 class="name"><a class="sheet-link" href="#/plant/${enc(p.code)}">${p.common_name}</a></h3>
    <p class="sci latin">${p.scientific_name || 'Scientific name not set'}</p>
    <div class="tags">${isArch(p) ? html`<span class="tag tag-arch">Archived</span>` : ''}${planTag(p.winter_plan)}${healthTag(p.health_rating)}</div>
    ${needsYou(p) ? html`<p class="needs-badge">Needs from you: ${[p.requests_open ? `${p.requests_open} request${p.requests_open === 1 ? '' : 's'}` : '', p.id_confidence != null && p.id_confidence < 70 ? 'ID info' : ''].filter(Boolean).join(', ')}</p>` : ''}
    <div class="meter"><span>ID ${p.id_confidence == null ? 'not rated' : p.id_confidence + '%'}</span><i style="--v:${p.id_confidence || 0}%;--mc:${confColor(p.id_confidence)}"></i></div>
  </article>`;
}
document.addEventListener('load', e => {       // 1.21.0: wide photos on cards get class "wide" (see the photofit Display setting)
  const im = e.target; if (!im || im.tagName !== 'IMG' || !im.closest('.mat')) return;
  im.classList.toggle('wide', im.naturalWidth > im.naturalHeight * 1.1);
}, true);
function sheetStep(code, d) {
  const p = ALL.find(x => x.code === code), card = document.querySelector(`#grid .sheet[data-code="${CSS.escape(code)}"]`);
  if (!p || !card) return;
  const n = sheetPhotos(p).length; if (n < 2) return;
  GPIX.set(code, (((GPIX.get(code) || 0) + d) % n + n) % n);
  const had = document.activeElement && document.activeElement.closest('.ph-btn') ? document.activeElement.dataset.d : null;
  card.querySelector('.mat').innerHTML = rend(sheetMat(p));
  if (had) { const b = card.querySelector(`.ph-btn[data-d="${had}"]`); if (b) b.focus(); }   // keep the keyboard on the same button
}
document.addEventListener('keydown', e => {          // Left and Right arrows on a photo button step through the photos too
  const b = e.target.closest && e.target.closest('#grid .ph-btn'); if (!b || (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight')) return;
  e.preventDefault(); const card = b.closest('.sheet'); sheetStep(card.dataset.code, e.key === 'ArrowRight' ? 1 : -1);
  const nb = card.querySelector(`.ph-btn[data-d="${e.key === 'ArrowRight' ? 1 : -1}"]`); if (nb) nb.focus();
});
// swipe left or right on a card's photo for the next or previous photo (phones and tablets)
const GSW = { x: 0, y: 0, code: null, t: 0, used: 0 };
document.addEventListener('touchstart', e => {
  GSW.code = null;
  const m = e.touches.length === 1 && e.target.closest && e.target.closest('#grid .sheet'); if (!m) return;
  const t = e.touches[0], r = m.querySelector('.mat').getBoundingClientRect();
  if (t.clientY < r.top || t.clientY > r.bottom || e.target.closest('.ph-btn')) return;
  Object.assign(GSW, { x: t.clientX, y: t.clientY, code: m.dataset.code, t: Date.now() });
}, { passive: true });
document.addEventListener('touchend', e => {
  if (!GSW.code) return;
  const t = e.changedTouches[0], dx = t.clientX - GSW.x, dy = t.clientY - GSW.y, code = GSW.code; GSW.code = null;
  if (Math.abs(dx) < 40 || Math.abs(dx) < Math.abs(dy) * 1.5 || Date.now() - GSW.t > 1000) return;
  GSW.used = Date.now();                       // the click that follows a swipe must not open the plant
  sheetStep(code, dx < 0 ? 1 : -1);
}, { passive: true });
document.addEventListener('click', e => { if (Date.now() - GSW.used < 500 && e.target.closest && e.target.closest('#grid .sheet')) { e.preventDefault(); e.stopPropagation(); } }, true);
function drawGrid() {
  gSave();
  if (!document.getElementById('grid')) { drawPnav(); return; }
  const r = filteredPlants();
  const pool = ALL.filter(statusOk).length;
  const led = document.querySelector('.ledger'); if (led) led.innerHTML = rend(ledger());
  const mf = document.querySelector('#more-f > summary'); if (mf) { const n = moreOn(); mf.textContent = 'More filters' + (n ? ` (${n} on)` : ''); }
  const gt = document.getElementById('g-title'); if (gt) gt.textContent = G.status === 'archived' ? 'Archived plants' : 'Outdoor plants';
  const wa = document.getElementById('wa-btn'); if (wa) { const n = r.filter(p => !isArch(p)).length; wa.textContent = `Water all ${n} shown`; wa.disabled = !n; }
  document.getElementById('count').textContent = `${r.length} of ${pool} ${G.status === 'archived' ? 'archived ' : G.status === 'all' ? '' : 'active '}plants shown`;
  document.getElementById('grid').innerHTML = r.length
    ? rend(r.map(sheet))
    : rend(html`<div class="empty" style="grid-column:1/-1"><p>No plants match these filters.</p><button class="btn ghost" type="button" data-act="clearfilters">Clear filters</button></div>`);
}
function ledger() {
  const n = pl => ALL.filter(p => statusOk(p) && p.winter_plan === pl).length;
  return html`${META.winter_plans.map(pl => html`<button type="button" data-act="plan" data-plan="${pl}" style="--bar:${PLAN_COLOR[pl]}" aria-pressed="${String(G.plan === pl)}"><b>${n(pl)}</b>${pl}</button>`)}`;
}
async function viewGallery() {
  ALL = await api('GET', '/api/plants?status=all');
  const ACT = ALL.filter(p => !isArch(p)), archN = ALL.length - ACT.length;
  const lowN = ACT.filter(p => p.id_confidence != null && p.id_confidence < 70).length;
  const needN = ACT.filter(needsYou).length;
  let todoN = 0, fcN = 0;
  await Promise.all([api('GET', '/api/to-photograph').then(t => { todoN = t.filter(x => !x.done).length; }).catch(() => {}),
    api('GET', '/api/for-claude?range=last').then(d => { fcN = d.counts.answers; }).catch(() => {})]);
  return {
    title: '',
    html: html`<div class="hero"><div><h1 id="g-title">${G.status === 'archived' ? 'Archived plants' : 'Outdoor plants'}</h1>
      <p class="muted">${META.counts.plants} plants and ${META.counts.photos} photos. Weather for ${placeName()}. Each plant has its own page, version number and change log.</p></div>
      <a class="btn" href="#/new">Add a plant</a></div>
    <div class="needs-bar" role="group" aria-label="What Claude needs from you">
      <button type="button" class="btn ${G.needs ? '' : 'ghost'}" data-act="needs" aria-pressed="${String(G.needs)}">${G.needs ? 'Showing plants that need something from you' : 'Show plants that need something from you'} (${needN})</button>
      <span class="hint">Questions, checks, photos and ID details I am waiting for. ${todoN ? html`Plus <a href="#/photos">${todoN} things to photograph</a> that are not in the database yet.` : ''}</span>
      <button type="button" class="btn ghost" data-act="forclaude"><span>Copy my answers for Claude${fcN ? html`<span class="fc-n"> (${fcN} new)</span>` : ''}</span></button></div>
    <div class="ledger" role="group" aria-label="Filter by winter plan">${ledger()}</div>
    <div class="filters">
      <label>Search<input type="search" data-f="q" value="${G.q}" placeholder="Name, code, location"></label>
      <label>Health<select data-f="health"><option value="">Any</option>${META.health.map(h => html`<option ${G.health === h ? raw('selected') : ''}>${h}</option>`)}</select></label>
      ${siteFilter()}${groupFilter()}${statusFilter()}
      <label>Sort by<select data-f="sort">${Object.entries(SORTS).map(([k, v]) => html`<option value="${k}" ${G.sort === k ? raw('selected') : ''}>${v}</option>`)}</select></label>
      <label class="chk"><input type="checkbox" data-f="low" ${G.low ? raw('checked') : ''}>ID confidence under 70% (${lowN})</label>
    </div>
    ${moreFilters()}
    <p id="count" class="muted" aria-live="polite"></p>
    <div class="water-all noprint"><button class="btn ghost" type="button" data-act="waterall" id="wa-btn">Water all</button>
      <span class="hint">Marks every plant shown (with the filters above) as watered today. Plants already watered today are skipped.</span></div>
    <div class="grid" id="grid"></div>
    ${archN ? html`<p class="hint" style="margin-top:2rem">${archN} archived plant${archN === 1 ? ' is' : 's are'} hidden from this list. Choose <strong>Show: Active and archived</strong> in the filters to see ${archN === 1 ? 'it' : 'them'} too.</p>` : ''}`,
    after: drawGrid,
  };
}

// ---------- groups of plants (added in 1.16.0) ----------
// A group is hand-picked (a list) or smart (a rule such as "Genus is Philodendron", so plants that fit join by themselves).
// The Plants page and Previous / Next can filter and sort by group. A group's page shows what suits every plant in it and
// does things to all of them at once: log care, move them, or change a setting (with a preview, and one press to undo).
let PGROUPS = null;
async function loadGroups(force) {
  if (PGROUPS && !force) return PGROUPS;
  try { PGROUPS = await api('GET', '/api/groups'); } catch (e) { PGROUPS = PGROUPS || { groups: [], suggestions: [], fields: [], ops: {}, values: {}, bulk_fields: [] }; }
  return PGROUPS;
}
const groupById = id => (PGROUPS && PGROUPS.groups.find(g => String(g.id) === String(id))) || null;
const groupsOf = code => (PGROUPS ? PGROUPS.groups.filter(g => g.codes.includes(code)) : []);
const groupNames = code => groupsOf(code).map(g => g.name).sort((a, b) => a.localeCompare(b));
function inGroupFilter(code) { const g = G.group && groupById(G.group); return !g || g.codes.includes(code); }
// ---------- 1.17.0: more filters (light needs, pets, winter, care today, grow light, leaf type, pot size, photos) ----------
const MORE = [
  { key: 'light', label: 'Light needs', opts: [['low', 'Low light'], ['indirect', 'Bright indirect light'], ['sun', 'Some direct sun'], ['full', 'Full sun']] },
  { key: 'pets', label: 'Pets', opts: [['safe', 'Safe for pets (ASPCA)'], ['notknown', 'Not known to be toxic'], ['mild', 'Mildly toxic to pets'], ['toxic', 'Toxic to pets'], ['unset', 'Pet safety not set']] },
  { key: 'hardy', label: 'Winter here', opts: [['hardy', 'Hardy here'], ['tender', 'Not hardy here'], ['nozone', 'Annual or no zone set']] },
  { key: 'care', label: 'Care today', opts: [['any', 'Water or feeding due'], ['water', 'Water due'], ['feed', 'Feeding due']] },
  { key: 'grow', label: 'Grow light', opts: [['yes', 'Under a grow light spot'], ['no', 'Not under a grow light']] },
  { key: 'leaf', label: 'Leaf type', opts: () => [...((META.enums || {}).leaf_type || []).map(x => [x, x]), ['unset', 'Leaf type not set']] },
  { key: 'pot', label: 'Pot size', opts: () => [...((META.enums || {}).pot_size || []).map(x => [x, x]), ['unset', 'Pot size not set']] },
  { key: 'photo', label: 'Photos', opts: [['none', 'No photo yet'], ['old', 'Newest photo over a month old']] },
];
const moreOpts = d => typeof d.opts === 'function' ? d.opts() : d.opts;
const moreOn = () => MORE_KEYS.filter(k => G[k]).length;
let MOREOPEN = false, CAREDUE = null;
function lightBand(p) { const d = p.dli_low; return d == null ? '' : d < 6 ? 'low' : d < 12 ? 'indirect' : d < 25 ? 'sun' : 'full'; }
const PET_KEY = { 'Toxic to pets': 'toxic', 'Mildly toxic to pets': 'mild', 'Not known to be toxic': 'notknown', 'Safe for pets (ASPCA)': 'safe' };
function hereZone() { const Z = META && META.zone; return !Z ? null : Z.zone ? zoneNum(Z.zone) : zoneNum(String(Z.map_zone || '').split(' ')[0]); }
function hardyKey(p) { const lo = zoneNum(p.zone_low), here = hereZone(); return lo == null || here == null ? 'nozone' : here >= lo ? 'hardy' : 'tender'; }
async function loadCareDue() {
  try {
    const [W] = await Promise.all([api('GET', '/api/water'), loadFertData(false)]);
    const t = todayStr(), m = new Map();
    for (const w of W.plants) m.set(w.code, { water: w.state === 'due', feed: false });
    for (const p of PCODES.values()) { const x = m.get(p.code) || { water: false, feed: false }; x.feed = fertState(p, entriesFor(p.code), t, fertCtx()).state === 'due'; m.set(p.code, x); }
    CAREDUE = m;
  } catch (e) { CAREDUE = new Map(); }
  return CAREDUE;
}
function moreOk(p) {
  const k = G;
  if (k.light && lightBand(p) !== k.light) return false;
  if (k.pets && (k.pets === 'unset' ? !!p.pet_safety : PET_KEY[p.pet_safety] !== k.pets)) return false;
  if (k.hardy && hardyKey(p) !== k.hardy) return false;
  if (k.care && CAREDUE) { const c = CAREDUE.get(p.code) || {}; if (k.care === 'water' ? !c.water : k.care === 'feed' ? !c.feed : !(c.water || c.feed)) return false; }
  if (k.grow && (k.grow === 'yes') !== !!p.light_spot) return false;
  if (k.leaf && (k.leaf === 'unset' ? !!p.leaf_type : p.leaf_type !== k.leaf)) return false;
  if (k.pot && (k.pot === 'unset' ? !!p.pot_size : p.pot_size !== k.pot)) return false;
  if (k.photo === 'none' && p.photo_count) return false;
  if (k.photo === 'old' && (!p.photo_count || (p.photo_at && Date.now() - Date.parse(p.photo_at) < 30 * 864e5))) return false;
  return true;
}
function moreSelects() {
  return html`${MORE.map(d => html`<label>${d.label}<select data-f="more" data-key="${d.key}"><option value="">Any</option>${moreOpts(d).map(([v, l]) => html`<option value="${v}" ${G[d.key] === v ? raw('selected') : ''}>${l}</option>`)}</select></label>`)}`;
}
function moreFilters() {
  const n = moreOn();
  return html`<details class="more-f" id="more-f" ${MOREOPEN || n ? raw('open') : ''}><summary>More filters${n ? ` (${n} on)` : ''}</summary>
    <div class="filters">${moreSelects()}</div>
    <p class="hint">Light needs come from each plant's daily light range. "Winter here" compares the plant's coldest zone with yours. Care today follows the Today page.</p></details>`;
}
function statusFilter() {
  return html`<label>Show<select data-f="status">${Object.entries(STATUS_WORD).map(([k, v]) => html`<option value="${k}" ${G.status === k ? raw('selected') : ''}>${v}</option>`)}</select></label>`;
}
function siteFilter() {
  return html`<label>Location<select data-f="site"><option value="">Any</option>${(META.sites || []).map(s => html`<option ${G.site === s ? raw('selected') : ''}>${s}</option>`)}</select></label>`;
}
function groupFilter() {
  const gs = (PGROUPS && PGROUPS.groups) || [];
  if (!gs.length) return '';
  return html`<label>Group<select data-f="group"><option value="">Any</option>${gs.map(g => html`<option value="${g.id}" ${String(G.group) === String(g.id) ? raw('selected') : ''}>${g.name} (${g.count})</option>`)}</select></label>`;
}
const plantName = code => (PCODES.get(code) || {}).common_name || code;
function nameList(codes, max = 6) {
  const names = codes.slice(0, max).map(plantName);
  return names.join(', ') + (codes.length > max ? `, and ${codes.length - max} more` : '');
}
const groupKindWords = g => g.kind === 'smart' ? `Smart group: plants join when ${g.rule_words}.` : 'Hand-picked group.';

async function viewGroups() {
  const G2 = await loadGroups(true), gs = G2.groups, sug = G2.suggestions;
  return {
    title: 'Groups',
    html: html`<h1>Groups</h1>
    <p class="muted">Groups gather plants that are alike or kept together, so you can see what suits all of them and look after them in one go. A plant can be in several groups.</p>
    <div class="row noprint grp-new"><button class="btn" type="button" data-act="grpnew" data-kind="smart">Make a smart group</button>
      <button class="btn ghost" type="button" data-act="grpnew" data-kind="picked">Make a hand-picked group</button></div>
    <section class="blk" id="grp-yours"><h2>Your groups (${gs.length})</h2>
      ${gs.length ? html`<ul class="grp-list">${gs.map(g => html`<li class="grp-card"><h3><a href="#/group/${g.id}">${g.name}</a></h3>
          <p>${groupKindWords(g)}</p><p><strong>${g.count} plant${g.count === 1 ? '' : 's'}</strong>${g.count ? ': ' + nameList(g.codes) : ''}</p></li>`)}</ul>`
        : html`<p>No groups yet. Start with a suggestion below, or make your own.</p>`}</section>
    ${sug.length ? html`<section class="blk" id="grp-suggest"><h2>Suggested groups (${sug.length})</h2>
      <p>Plants of the same family or genus, and plants under the same grow light. Each is a smart group, so new plants that fit join by themselves.</p>
      <p class="noprint"><button class="btn" type="button" data-act="grpaddall">Add all ${sug.length} suggested groups</button></p>
      <ul class="grp-list">${sug.map((x, i) => html`<li class="grp-card"><h3>${x.name}</h3><p>Plants join when ${x.rule_words}.</p>
        <p><strong>${x.count} plants</strong>: ${nameList(x.codes)}</p>
        <p class="noprint"><button class="btn small" type="button" data-act="grpaddsug" data-i="${i}" aria-label="Add the group ${x.name}">Add this group</button></p></li>`)}</ul></section>` : ''}
    <section class="blk" id="grp-how"><h2>How groups work</h2><ul>
      <li><strong>Smart groups</strong> have a rule, such as "Genus is Philodendron" or "Location is Indoors". Plants that fit join by themselves, and leave when they stop fitting.</li>
      <li><strong>Hand-picked groups</strong> hold the plants you choose. Add or take out plants on the group's page or on a plant's own page.</li>
      <li>On the <a href="#/">Plants page</a>, choose a group under <strong>Group</strong> to see only those plants, or sort by group. Previous and Next Plant follow the same choice.</li>
      <li>A group's page shows the conditions that suit every plant in it, and lets you log care, move the plants, or change a setting for all of them. A change to a setting shows each plant first, and can be undone.</li>
      <li>Removing a group never changes the plants in it.</li></ul></section>`,
  };
}

function fitItem(x) {
  const u = x.unit === '°F' || x.unit === '%' ? x.unit : x.unit ? ' ' + x.unit : '';
  let body;
  if (x.key === 'cold') body = html`<p><strong>${x.value}${u}</strong>, because ${x.by.map(b => b.name).join(', ')} ${x.by.length === 1 ? 'is' : 'are'} damaged below that.</p>`;
  else if (x.spread) body = html`<p><strong>Every ${x.lo === x.hi ? x.lo : x.lo + ' to ' + x.hi} ${x.unit}</strong>. ${x.lo === x.hi ? 'The same for all of them.' : 'Each plant keeps its own watering schedule.'}</p>`;
  else if (x.values) body = x.values.length === 1 ? html`<p><strong>The same for all ${x.n}:</strong> ${x.values[0].value}</p>`
    : html`<ul class="fit-vals">${x.values.map(v => html`<li><strong>${v.codes.length} plant${v.codes.length === 1 ? '' : 's'}:</strong> ${v.value}${v.codes.length < x.n ? html` <span class="muted">(${nameList(v.codes, 4)})</span>` : ''}</li>`)}</ul>`;
  else {
    const all = x.fits === x.n;
    body = html`<p><strong>${x.lo} to ${x.hi}${u}</strong>: ${all ? html`<span aria-hidden="true">✓ </span>suits all ${x.n}.` : html`<span aria-hidden="true">▲ </span>suits ${x.fits} of ${x.n}.`}
      ${x.odd.length ? html`Not right for ${x.odd.map((o, i) => html`${i ? '; ' : ''}<a href="#/plant/${enc(o.code)}">${o.name}</a> (${o.lo} to ${o.hi}${u})`)}.` : ''}
      ${x.missing ? html` <span class="muted">${x.missing} plant${x.missing === 1 ? ' has' : 's have'} no figures for this.</span>` : ''}</p>`;
  }
  return html`<div class="fit-item"><h3>${x.label}</h3>${body}</div>`;
}
async function viewGroup(id) {
  const d = await api('GET', '/api/groups/' + enc(id));
  CURG = d;
  const picked = d.kind === 'picked';
  return {
    title: d.name,
    html: html`<p class="crumb"><a href="#/groups">All groups</a></p>
    <h1>${d.name}</h1><p>${groupKindWords(d)}</p>${paras(d.notes)}
    <div class="row noprint"><button class="btn ghost" type="button" data-act="grpedit">${picked ? 'Change the name, notes or plants' : 'Change the name, notes or rule'}</button>
      <a class="btn ghost" href="#/" data-act="grpshow" data-id="${d.id}">Show them on the Plants page</a>
      <button class="btn ghost danger" type="button" data-act="grpdel">Remove this group</button></div>
    <section class="blk" id="g-plants"><h2>Plants in this group (${d.members.length})</h2>
      ${d.members.length ? html`<ul class="jobs">${d.members.map(m => html`<li class="job" data-code="${m.code}">${m.photo ? html`<img src="${thumbUrl(m.photo)}" alt="" loading="lazy" width="64" height="64">` : html`<span class="job-nophoto" aria-hidden="true"></span>`}
          <div class="job-txt"><a class="nm" href="#/plant/${enc(m.code)}">${m.common_name}</a> <span class="muted">${m.code}</span>
            <div>${m.site}${m.location ? ', ' + m.location : ''}${m.light_spot ? html`. Under the grow light spot ${m.light_spot}` : ''}.</div></div>
          ${picked ? html`<div class="job-acts noprint"><button class="btn small ghost" type="button" data-act="grprm" data-code="${m.code}" aria-label="Take ${m.common_name} out of this group">Take out</button></div>` : ''}</li>`)}</ul>`
        : html`<p>${picked ? 'No plants yet. Use "Change the name, notes or plants" to add some.' : 'No plants fit this rule at the moment.'}</p>`}</section>
    <section class="blk" id="g-fit"><h2>What suits all of them</h2>
      ${d.fit.length ? html`<p>From each plant's own page. Where the plants disagree, the range shown suits the most of them, and the odd ones out are named.</p>
        <div class="fit-list">${d.fit.map(fitItem)}</div>` : html`<p>There are no figures to compare yet.</p>`}</section>
    ${d.members.length ? html`<section class="blk noprint" id="g-do"><h2>Do something to all of them</h2>
      <ul class="grp-acts">
        <li><button class="btn" type="button" data-act="grpcare">Log care for all of them</button><p class="hint">Watered, fed, repotted, sprayed and so on, for every plant you tick, on one date.</p></li>
        <li><button class="btn" type="button" data-act="grpmove">Move them</button><p class="hint">Change their Location and Spot, or put them under a grow light spot.</p></li>
        <li><button class="btn" type="button" data-act="grpset">Change a setting for all of them</button><p class="hint">For example the potting mix or how often to water. You see each plant's current value first, and can undo it.</p></li></ul></section>` : ''}
    ${d.recent.length ? html`<section class="blk" id="g-recent"><h2>Recent changes to the whole group</h2><ul class="grp-recent">${d.recent.map(x => html`<li>
      <strong>${x.what}</strong>: ${x.count} plant${x.count === 1 ? '' : 's'}, by ${x.done_by}, ${when(x.done_at)}.
      ${x.undone_at ? html` <span class="muted">Undone by ${x.undone_by}, ${when(x.undone_at)}.</span>` : html` <button class="btn small ghost noprint" type="button" data-act="grpundo" data-id="${x.id}">Undo this change</button>`}</li>`)}</ul></section>` : ''}`,
  };
}
let CURG = null;

// a list of plants to tick, with "Tick all" and a search box
function tickList(codes, ticked, legend) {
  const on = new Set(ticked);
  return html`<fieldset class="tick-list"><legend>${legend}</legend>
    <div class="row"><button class="btn small ghost" type="button" data-act="tickall" data-on="1">Tick all</button><button class="btn small ghost" type="button" data-act="tickall" data-on="0">Untick all</button>
      ${codes.length > 12 ? html`<label class="f tick-find">Find a plant<input type="search" data-tickfind="1" placeholder="Name or code"></label>` : ''}</div>
    <ul>${codes.map(c => html`<li><label class="chk"><input type="checkbox" name="code" value="${c}" ${on.has(c) ? raw('checked') : ''}><span>${plantName(c)} <span class="muted">${c}</span></span></label></li>`)}</ul></fieldset>`;
}
const tickedCodes = f => [...f.querySelectorAll('input[name=code]:checked')].map(x => x.value);
function ruleRow(c, i) {
  const F = PGROUPS.fields, f = F.find(x => x.key === c.field) || F[0], vals = PGROUPS.values[f.key] || [];
  return html`<fieldset class="rule-row" data-row="${i}"><legend>Part ${i + 1}</legend>
    <label class="f">Look at<select name="rf" data-act="grprulefield">${F.map(x => html`<option value="${x.key}" ${x.key === f.key ? raw('selected') : ''}>${x.label}</option>`)}</select></label>
    <label class="f">How<select name="ro">${Object.entries(PGROUPS.ops).filter(([k]) => f.how === 'text' ? k.includes('contains') : true).map(([k, v]) => html`<option value="${k}" ${k === (c.op || (f.how === 'text' ? 'contains' : 'is')) ? raw('selected') : ''}>${v}</option>`)}</select></label>
    <label class="f">Value<input type="text" name="rv" value="${c.value || ''}" list="rv-${f.key}" autocomplete="off"></label>
    ${vals.length ? html`<datalist id="rv-${f.key}">${vals.map(v => html`<option value="${v}">`)}</datalist>` : ''}
    ${i ? html`<button class="btn small ghost" type="button" data-act="grprulerm" data-i="${i}">Remove this part</button>` : ''}</fieldset>`;
}
function readRule(f) {
  const conds = [...f.querySelectorAll('.rule-row')].map(r => ({ field: r.querySelector('[name=rf]').value, op: r.querySelector('[name=ro]').value, value: r.querySelector('[name=rv]').value.trim() })).filter(x => x.value);
  return { match: f.elements.match ? f.elements.match.value : 'all', conds };
}
let RULE_T = 0;
function rulePreview() {
  const f = dlg.querySelector('form[data-grp]'), out = document.getElementById('rule-prev'); if (!f || !out) return;
  const rule = readRule(f);
  clearTimeout(RULE_T);
  if (!rule.conds.length) { out.textContent = 'Fill in a value to see which plants fit.'; return; }
  RULE_T = setTimeout(() => api('POST', '/api/groups/match', { rule }).then(r => { out.textContent = r.codes.length ? `${r.codes.length} plant${r.codes.length === 1 ? ' fits' : 's fit'} now: ${nameList(r.codes, 8)}.` : 'No plants fit this rule at the moment.'; })
    .catch(e => { out.textContent = e.message; }), 350);
}
async function groupDialog(g, kind, preset) {
  if (!(await needName())) return;
  await loadGroups();
  kind = g ? g.kind : kind;
  const all = [...PCODES.values()].filter(p => !isArch(p)).map(p => p.code).sort();
  const conds = g && g.rule ? g.rule.conds : (preset && preset.conds) || [{ field: 'genus', op: 'is', value: '' }];
  const r = await modal(html`<form method="dialog" data-grp="1" class="grp-form"><h2>${g ? 'Change the group ' + g.name : kind === 'smart' ? 'Make a smart group' : 'Make a hand-picked group'}</h2>
    <label class="f">Name<input type="text" name="name" maxlength="60" required value="${g ? g.name : (preset && preset.name) || ''}" placeholder="${kind === 'smart' ? 'For example: Philodendrons' : 'For example: Tall Black Shelf'}"></label>
    <label class="f">Notes (optional)<textarea name="notes" rows="2" maxlength="500">${g ? g.notes : ''}</textarea></label>
    ${kind === 'smart' ? html`<label class="f">Plants join when<select name="match" data-act="grprulematch"><option value="all" ${!g || !g.rule || g.rule.match !== 'any' ? raw('selected') : ''}>every part below fits</option><option value="any" ${g && g.rule && g.rule.match === 'any' ? raw('selected') : ''}>any part below fits</option></select></label>
      <div id="rule-rows">${conds.map(ruleRow)}</div>
      <p><button class="btn small ghost" type="button" data-act="grprulerow">Add another part</button></p>
      <p id="rule-prev" class="rule-prev" aria-live="polite"></p>`
    : tickList(all, g ? g.codes : (preset && preset.codes) || [], 'Plants in this group')}
    <div class="row"><button class="btn" value="ok">${g ? 'Save changes' : 'Make the group'}</button><button class="btn ghost" value="cancel" formnovalidate>Cancel</button></div></form>`, 'wide');
  if (kind === 'smart') rulePreview();
  if (r !== 'ok') return;
  const f = dlg.querySelector('form');
  const body = { name: f.elements.name.value, notes: f.elements.notes.value };
  if (kind === 'smart') body.rule = readRule(f);
  return guard(async () => {
    if (g) {
      await api('PUT', '/api/groups/' + g.id, body);
      if (kind === 'picked') {
        const now = new Set(tickedCodes(f)), was = new Set(g.codes);
        await api('POST', `/api/groups/${g.id}/members`, { add: [...now].filter(c => !was.has(c)), remove: [...was].filter(c => !now.has(c)) });
      }
      toast('Saved: ' + body.name); await loadGroups(true); route();
    } else {
      const made = await api('POST', '/api/groups', { ...body, kind, codes: kind === 'picked' ? tickedCodes(f) : undefined });
      toast('Group made: ' + made.name); await loadGroups(true); go('#/group/' + made.id);
    }
  });
}
function careKinds() {
  return html`<optgroup label="Care">${Object.entries(CARE_WORD).filter(([k]) => !k.startsWith('prep_')).map(([k, v]) => html`<option value="${k}" ${k === 'water' ? raw('selected') : ''}>${v}</option>`)}</optgroup>
    <optgroup label="Getting ready to come inside">${Object.entries(CARE_WORD).filter(([k]) => k.startsWith('prep_')).map(([k, v]) => html`<option value="${k}">${v}</option>`)}</optgroup>`;
}
async function groupCare() {
  const d = CURG; if (!d || !(await needName())) return;
  const r = await modal(html`<form method="dialog"><h2>Log care for ${d.name}</h2>
    <label class="f">What did you do?<select name="kind">${careKinds()}</select></label>
    <label class="f">When<input type="date" name="day" value="${todayStr()}" max="${todayStr()}"></label>
    <label class="f">Note (optional)<input type="text" name="note" maxlength="500" placeholder="For example: repotted in the aroid mix"></label>
    ${tickList(d.codes, d.codes, 'For these plants')}
    <div class="row"><button class="btn" value="ok">Save for the ticked plants</button><button class="btn ghost" value="cancel">Cancel</button></div></form>`, 'wide');
  if (r !== 'ok') return;
  const f = dlg.querySelector('form'), codes = tickedCodes(f);
  if (!codes.length) { toast('Tick at least one plant.', true); return; }
  await guard(async () => { await api('POST', '/api/care', { plants: codes, kind: f.elements.kind.value, done_on: f.elements.day.value, note: f.elements.note.value });
    toast(`Saved for ${codes.length} plant${codes.length === 1 ? '' : 's'}: ${CARE_WORD[f.elements.kind.value]}`); route(); });
}
async function groupMove() {
  const d = CURG; if (!d || !(await needName())) return;
  let spots = [];
  try { spots = (await api('GET', '/api/lights')).spots || []; } catch (e) { /* no lights page data: leave the choice out */ }
  const r = await modal(html`<form method="dialog"><h2>Move plants in ${d.name}</h2>
    <label class="f">Location<select name="site"><option value="">Leave each plant where it is</option>${(META.sites || []).map(s => html`<option>${s}</option>`)}</select></label>
    <label class="f">Spot<small>For example "Tall Black Shelf". Leave empty to keep each plant's own spot.</small><input type="text" name="spot" maxlength="200"></label>
    ${spots.length ? html`<label class="f">Grow light spot<select name="light"><option value="">Do not change</option><option value="none">Take them out of their grow light spots</option>${spots.map(s => html`<option value="${s.id}">${s.name}</option>`)}</select></label>` : ''}
    ${tickList(d.codes, d.codes, 'Move these plants')}
    <div class="row"><button class="btn" value="ok">Move the ticked plants</button><button class="btn ghost" value="cancel">Cancel</button></div></form>`, 'wide');
  if (r !== 'ok') return;
  const f = dlg.querySelector('form'), codes = tickedCodes(f), set = {};
  if (f.elements.site.value) set.site = f.elements.site.value;
  if (f.elements.spot.value.trim()) set.location = f.elements.spot.value.trim();
  const light = f.elements.light ? f.elements.light.value : '';
  if (!codes.length) { toast('Tick at least one plant.', true); return; }
  if (!Object.keys(set).length && !light) { toast('Choose a Location, type a Spot or choose a grow light spot.', true); return; }
  await guard(async () => {
    let msg = [];
    if (Object.keys(set).length) { const a = await api('POST', `/api/groups/${d.id}/apply`, { set, codes }); msg.push(`${a.changed.length} moved`); }
    if (light) { await api('POST', `/api/groups/${d.id}/spot`, { spot: light === 'none' ? null : +light, codes }); msg.push(light === 'none' ? 'taken out of their grow light spots' : 'under the grow light spot'); }
    toast('Done: ' + msg.join(', ')); await loadCodes(true); route();
  });
}
async function groupSet(field) {
  const d = CURG; if (!d || !(await needName())) return;
  const F = Object.fromEntries(META.fields.map(x => [x.name, x])), list = PGROUPS.bulk_fields.filter(n => F[n]);
  field = field || list.find(n => n === 'soil_medium') || list[0];
  const r = await modal(html`<form method="dialog" data-gset="1"><h2>Change a setting for ${d.name}</h2>
    <label class="f">Setting<select name="field" data-act="grpsetfield">${list.map(n => html`<option value="${n}" ${n === field ? raw('selected') : ''}>${F[n].label}</option>`)}</select></label>
    <div id="gset-input">${fieldInput(F[field], '')}</div>
    <p class="hint">Next you see what each plant has now, and choose which plants to change.</p>
    <div class="row"><button class="btn" value="ok">Show each plant first</button><button class="btn ghost" value="cancel">Cancel</button></div></form>`, 'wide');
  if (r !== 'ok') return;
  const f = dlg.querySelector('form'), name = f.elements.field.value, val = f.elements[name].value;
  const pv = await guard(() => api('POST', `/api/groups/${d.id}/preview`, { set: { [name]: val } }));
  if (!pv) return;
  const show = v => v == null || v === '' ? html`<span class="muted">Not set</span>` : String(v);
  const r2 = await modal(html`<form method="dialog"><h2>${F[name].label}: check each plant</h2>
    <p>New value: <strong>${show(pv.set[name])}</strong>. Plants already set to it are not ticked. ${pv.rows.some(x => x.differs.length) ? 'Plants marked "Different from the rest" have their own value now: tick them only if the new one suits them too.' : ''}</p>
    <div class="tbl-wrap"><table class="tbl gset-tbl"><thead><tr><th scope="col">Change?</th><th scope="col">Plant</th><th scope="col">Now</th></tr></thead><tbody>
      ${pv.rows.map(x => html`<tr><td><input type="checkbox" name="code" value="${x.code}" aria-label="Change ${x.common_name}" ${x.same ? '' : raw('checked')}></td>
        <th scope="row">${x.common_name} <span class="muted">${x.code}</span></th>
        <td>${show(x.current[name])}${x.same ? html`<br><strong>Already this</strong>` : x.differs.length ? html`<br><strong><span aria-hidden="true">▲ </span>Different from the rest</strong>` : ''}</td></tr>`)}</tbody></table></div>
    <div class="row"><button class="btn" value="ok">Change the ticked plants</button><button class="btn ghost" value="cancel">Cancel</button></div></form>`, 'wide');
  if (r2 !== 'ok') return;
  const codes = tickedCodes(dlg.querySelector('form'));
  if (!codes.length) { toast('Nothing was ticked, so nothing changed.'); return; }
  const expect = Object.fromEntries(pv.rows.map(x => [x.code, x.current]));
  await guard(async () => {
    const a = await api('POST', `/api/groups/${d.id}/apply`, { set: pv.set, codes, expect });
    toast(`${F[name].label} changed for ${a.changed.length} plant${a.changed.length === 1 ? '' : 's'}` + (a.skipped.length ? `. ${a.skipped.length} skipped: changed by someone else since you looked` : '') + '. You can undo it under "Recent changes".');
    await loadCodes(true); route();
  });
}
async function plantGroupsDialog() {
  const p = CUR && CUR.p; if (!p || !(await needName())) return;
  await loadGroups(true);
  const picked = PGROUPS.groups.filter(g => g.kind === 'picked'), smart = groupsOf(p.code).filter(g => g.kind === 'smart');
  const r = await modal(html`<form method="dialog"><h2>Groups for ${p.common_name}</h2>
    ${picked.length ? html`<fieldset class="tick-list"><legend>Hand-picked groups</legend><ul>${picked.map(g => html`<li><label class="chk"><input type="checkbox" name="gid" value="${g.id}" ${g.codes.includes(p.code) ? raw('checked') : ''}><span>${g.name} <span class="muted">(${g.count})</span></span></label></li>`)}</ul></fieldset>`
      : html`<p>You have no hand-picked groups yet.</p>`}
    <label class="f">Make a new hand-picked group with this plant (optional)<input type="text" name="newg" maxlength="60" placeholder="Group name"></label>
    ${smart.length ? html`<p>It is also in ${smart.length === 1 ? 'the smart group' : 'these smart groups'} ${smart.map(g => g.name).join(', ')}, by ${smart.length === 1 ? 'its rule' : 'their rules'}.</p>` : ''}
    <div class="row"><button class="btn" value="ok">Save changes</button><button class="btn ghost" value="cancel">Cancel</button></div></form>`);
  if (r !== 'ok') return;
  const f = dlg.querySelector('form');
  await guard(async () => {
    await api('POST', `/api/plants/${enc(p.code)}/groups`, { picked: [...f.querySelectorAll('input[name=gid]:checked')].map(x => +x.value) });
    if (f.elements.newg.value.trim()) await api('POST', '/api/groups', { name: f.elements.newg.value, kind: 'picked', codes: [p.code] });
    toast('Groups saved'); await loadGroups(true); KEEP = PIDX; route();
  });
}

// ---------- current conditions ----------
let COND = null;
const has = v => v != null && v !== '';
async function loadCond() { try { COND = await api('GET', '/api/current'); } catch (e) { COND = null; } return COND; }
const fmt = (n, d = 0) => has(n) ? Number(n).toLocaleString(undefined, { maximumFractionDigits: d }) : '';
function ago(min) { if (min == null) return ''; if (min < 2) return 'just now'; if (min < 90) return min + ' minutes ago'; if (min < 48 * 60) return Math.round(min / 60) + ' hours ago'; return Math.round(min / 1440) + ' days ago'; }

// ---------- gauges ----------
const posLin = (v, mn, mx) => (clamp(v, mn, mx) - mn) / (mx - mn) * 100;
const posSqrt = (v, mn, mx) => Math.sqrt(clamp(v, mn, mx) / mx) * 100;
function nowMarker(pos, label) {
  const edge = pos < 16 ? 'left:0' : pos > 84 ? 'right:0' : `left:${pos}%;transform:translateX(-50%)`;
  return { line: html`<div class="now-line" style="left:${pos}%;bottom:2.1rem"></div>`, tag: html`<div class="now-tag" style="${edge}">Now ${label}</div>` };
}
function strip(zones, marks, ticks, now) {
  const n = now ? nowMarker(now.pos, now.label) : null;
  return html`<div class="strip-wrap"><div class="strip">${zones.map(z => html`<div class="z ${z[0]}" style="width:${z[1]}%"></div>`)}
    ${marks.map(m => html`<div class="mk" style="left:${m[0]}%"><span>${m[1]}</span></div>`)}</div>
    <div class="ticks" aria-hidden="true">${ticks.map(t => html`<span style="left:${t[0]}%">${t[1]}</span>`)}</div>
    ${n ? html`<div class="now-space"></div>${n.line}${n.tag}` : ''}</div>`;
}
function fitNowTags() {         // 1.11.0: keep each "Now" label inside its strip; with large text a label near either end ran off the screen
  document.querySelectorAll('.strip-wrap > .now-tag').forEach(t => {
    t.classList.remove('nt-l', 'nt-r');
    const w = t.parentElement.getBoundingClientRect(), r = t.getBoundingClientRect();
    if (r.right > w.right + 1) t.classList.add('nt-r'); else if (r.left < w.left - 1) t.classList.add('nt-l');
  });
}
new MutationObserver(() => requestAnimationFrame(fitNowTags)).observe(document.getElementById('app'), { childList: true, subtree: true });
new MutationObserver(() => {                      // 1.12.0: for people who can only view, menus and tick boxes that save straight away are switched off
  if (ME().role !== 'viewer') return;
  document.querySelectorAll('#app select[data-act=site], #app select[data-act=plan], #app [data-act=preptrait], #app [data-act=preppest], #app input[type=file]').forEach(el => { if (!el.disabled) el.disabled = true; });
}).observe(document.getElementById('app'), { childList: true, subtree: true });
window.addEventListener('resize', () => requestAnimationFrame(fitNowTags));
const keyOf = items => html`<div class="key" aria-hidden="true">${items.map(i => html`<span class="${i[0]}">${i[1]}</span>`)}</div>`;

// marks on the temperature and humidity strips: from the weather history of the place in use, when it has 3 years or more
function tempMarks() {
  const C = META && META.climate, here = placeShort();
  if (!C) return [['A', 20, 'Hard freeze'], ['B', 32, 'Freezing']];
  return [['A', C.winter_low, `Coldest night of a usual winter in ${here}`], ['B', 32, 'Freezing'], ['C', C.cold_month_low, `Usual ${MONTHN[C.cold_month - 1]} night in ${here}`]]
    .sort((a, b) => a[1] - b[1]).map((m, i) => ['ABC'[i], m[1], m[2]]);
}
function humMarks() {
  const C = META && META.climate, out = [];
  if (C && C.winter_rh != null) { const cm = C.cold_month; out.push(['D', C.winter_rh, `Outdoors in ${placeShort()}, ${MONTHN[(cm + 10) % 12]} to ${MONTHN[cm % 12]} (average)`]); }   // the coldest month and the ones either side
  out.push([out.length ? 'E' : 'D', 30, 'Indoors with the heater running']);
  return out;
}
const LIGHT_MARKS = [['F', 1800, 'Full sun at midday'], ['G', 400, 'Open shade or a roofed porch'], ['H', 200, 'Indoors by a bright window']];

function tempVerdict(p, t) {
  const L = p.temp_lethal_below, D = p.temp_damage_below, IL = p.temp_ideal_low, IH = p.temp_ideal_high, HA = p.temp_damage_above;
  if (t < L) return ['fatal', `Likely fatal. This plant dies below ${L}°F, so it must be inside or well covered.`];
  if (t < D) return ['damage', `Damage likely. Leaves and stems are hurt below ${D}°F, so protect it or bring it in.`];
  if (t < IL) return ['cool', `Cooler than ideal, but no damage expected. Comfortable starts at ${IL}°F.`];
  if (t <= IH) return ['ok', 'Comfortable.'];
  if (has(HA) && t >= HA) return ['damage', `Too hot. Leaves are likely to scorch at ${HA}°F and above.`];
  return ['hot', `Warmer than ideal (above ${IH}°F).`];
}
function tempBlock(p, cur) {
  const v = [p.temp_lethal_below, p.temp_damage_below, p.temp_ideal_low, p.temp_ideal_high];
  if (v.some(x => x == null)) return html`<p class="muted">Temperature limits are not filled in yet. Use Edit to add them.</p>`;
  const l = clamp(v[0], 0, 100), d = clamp(Math.max(v[1], v[0]), 0, 100), il = clamp(Math.max(v[2], v[1], v[0]), 0, 100), ih = clamp(Math.max(v[3], v[2], v[1], v[0]), 0, 100);
  const ha = has(p.temp_damage_above) && p.temp_damage_above > v[3] ? clamp(p.temp_damage_above, 0, 100) : null;
  const zones = [['z-fatal', l], ['z-damage', d - l], ['z-cool', il - d], ['z-ok', ih - il]];
  if (ha != null) { zones.push(['z-hot', ha - ih]); zones.push(['z-heat', 100 - ha]); } else zones.push(['z-hot', 100 - ih]);
  const t = cur && has(cur.temp_f) ? cur.temp_f : null;
  const now = t == null ? null : { pos: posLin(t, 0, 100), label: t + '°F' };
  const st = t == null ? '' : (() => { const [k, txt] = tempVerdict(p, t); return html`<p class="nowstate v-${k}"><strong>Now ${t}°F.</strong> ${txt}</p>`; })();
  return html`<p>Comfortable between <strong>${deg(p.temp_ideal_low)}</strong> and <strong>${deg(p.temp_ideal_high)}</strong>. Damage below ${deg(p.temp_damage_below)}. Dies below ${deg(p.temp_lethal_below)}.${has(p.temp_damage_above) ? html` Heat damage from ${deg(p.temp_damage_above)}.` : ''}</p>
    ${st}
    ${strip(zones, tempMarks().map(m => [m[1], m[0]]), [0, 20, 40, 60, 80, 100].map(x => [x, x + '°']), now)}
    ${keyOf([['z-fatal', 'Likely fatal'], ['z-damage', 'Damage'], ['z-cool', 'Cool but safe'], ['z-ok', 'Comfortable'], ['z-hot', 'Too hot'], ...(ha != null ? [['z-heat', 'Heat damage']] : []), ...(now ? [['z-now', 'Now']] : [])])}
    <ul class="verdicts">${tempMarks().map(m => { const [k, txt] = tempVerdict(p, m[1]); return html`<li class="v-${k}"><span class="k">${m[0]}</span><span><strong>${m[2]}, ${m[1]}°F.</strong> ${txt}</span></li>`; })}</ul>`;
}
function humBlock(p, cur) {
  const lo = p.humidity_low, hi = p.humidity_high;
  if (lo == null || hi == null) return html`<p class="muted">Humidity range is not filled in yet.</p>`;
  const a = clamp(lo, 0, 100), b = clamp(Math.max(hi, lo), 0, 100);
  const verdict = t => t < lo ? ['dry', 'Drier than this plant likes. Raise humidity or move it.'] : t > hi ? ['wet', 'More humid than ideal. Give it airflow and avoid watering late in the day.'] : ['ok', 'Comfortable.'];
  const h = cur && has(cur.humidity) ? cur.humidity : null;
  const kk = k => k === 'dry' ? 'hot' : k === 'wet' ? 'cool' : 'ok';
  return html`<p>Comfortable between <strong>${lo}%</strong> and <strong>${hi}%</strong> relative humidity.${has(p.vpd_low) && has(p.vpd_high) ? html` Ideal air dryness (VPD) is <strong>${p.vpd_low} to ${p.vpd_high} kPa</strong>. VPD is how hard the air pulls water out of leaves; it rises when the air is warm and dry.` : ''}</p>
    ${h == null ? '' : (() => { const [k, txt] = verdict(h); return html`<p class="nowstate v-${kk(k)}"><strong>Now ${h}%.</strong> ${txt}${cur.vpd != null && has(p.vpd_low) ? html` Air dryness now: ${cur.vpd} kPa.` : ''}</p>`; })()}
    ${strip([['z-dry', a], ['z-ok', b - a], ['z-wet', 100 - b]], humMarks().map(m => [m[1], m[0]]), [0, 25, 50, 75, 100].map(x => [x, x + '%']), h == null ? null : { pos: posLin(h, 0, 100), label: h + '%' })}
    ${keyOf([['z-dry', 'Too dry'], ['z-ok', 'Comfortable'], ['z-wet', 'Too humid'], ...(h != null ? [['z-now', 'Now']] : [])])}
    <ul class="verdicts">${humMarks().map(m => { const [k, txt] = verdict(m[1]); return html`<li class="v-${kk(k)}"><span class="k">${m[0]}</span><span><strong>${m[2]}, about ${m[1]}%.</strong> ${txt}</span></li>`; })}</ul>
    ${paras(p.humidity_notes)}`;
}
// ---------- 1.14.0: about this plant ----------
const ABOUT_FIELDS = ['growth_habit', 'kingdom', 'taxon_order', 'family', 'genus', 'height_ground', 'width_ground', 'height_pot', 'width_pot', 'growth_rate', 'lifespan',
  'zone_low', 'zone_high', 'zone_notes', 'native_range', 'conservation_status', 'invasive', 'bloom', 'fruit', 'danger_humans', 'danger_animals', 'pet_safety', 'propagation', 'sources'];
function zoneNum(z) { const m = /^\s*(\d{1,2})\s*([ab])?\s*$/i.exec(String(z || '')); return m ? +m[1] + ((m[2] || '').toLowerCase() === 'b' ? 0.5 : 0) : null; }
function zoneHere(p) {
  const Z = META && META.zone, lo = zoneNum(p.zone_low), here = !Z ? null : Z.zone ? zoneNum(Z.zone) : zoneNum(String(Z.map_zone || '').split(' ')[0]);   // no weather history yet: the colder end of the map zone
  const where = html`${Z && Z.zone ? html`<p>Where you are: the last ${Z.years} winters of weather at ${placeName()} averaged a coldest night of ${Z.winter_low}°F, which is <strong>zone ${Z.zone}</strong>.${Z.map_note ? ' ' + Z.map_note : ''} <a href="${Z.map_url}" target="_blank" rel="noopener noreferrer">Look up a ZIP code on the USDA map</a>.</p>`
    : Z && Z.map_zone ? html`<p>Where you are: zone ${Z.map_zone} on the 2023 USDA map. <a href="${Z.map_url}" target="_blank" rel="noopener noreferrer">Look up a ZIP code on the USDA map</a>.</p>` : ''}`;
  if (lo == null || here == null) return where;
  const ok = here >= lo, gap = Math.round((lo - here) * 2);
  return html`${where}<p class="nowstate ${ok ? 'v-ok' : 'v-cool'}"><strong>${ok ? '✓ Hardy here.' : '▼ Not hardy here.'}</strong> ${ok ? 'It can stay outside through a usual winter, though a rare hard freeze can still hurt it.'
    : `A usual winter is about ${gap * 5}°F colder than it can take (${gap} half-zone${gap === 1 ? '' : 's'}), so it needs to come inside or be protected.`}</p>`;
}
function srcList(v) {
  return lines(v).map(x => { const i = x.lastIndexOf('|'), t = i > 0 ? x.slice(0, i).trim() : x.trim(), u = i > 0 ? x.slice(i + 1).trim() : '';
    return /^https?:\/\//.test(u) ? html`<li><a href="${u}" target="_blank" rel="noopener noreferrer">${t}</a></li>` : html`<li>${x}</li>`; });
}
function aboutBlock(p) {
  if (!ABOUT_FIELDS.some(f => has(p[f]) && p[f] !== '')) return html`<p class="muted">Not filled in yet. Use Edit to add it, under "About this plant".</p>`;
  const row = (k, v) => has(v) && v !== '' ? html`<dt>${k}</dt><dd>${v}</dd>` : '';
  const size = [['In the ground', p.height_ground, p.width_ground], ['In a pot', p.height_pot, p.width_pot]].filter(r => r[1] || r[2]);
  const zones = p.zone_low || p.zone_high ? (p.zone_low && p.zone_high && p.zone_low !== p.zone_high ? `Zones ${p.zone_low} to ${p.zone_high}` : `Zone ${p.zone_low || p.zone_high}`) : '';
  const unsure = p.id_confidence != null && p.id_confidence < 85 ? html`<p class="hint">The identification is ${p.id_confidence}% sure, so these details are for the closest match. Some may change if the ID does.</p>` : '';
  return html`${unsure}<dl class="dl about-dl">${row('Type of plant', p.growth_habit)}${row('Kingdom', p.kingdom)}${row('Order', p.taxon_order)}${row('Family', p.family)}${row('Genus', p.genus)}
      ${row('Species', p.scientific_name)}${row('Growth rate', p.growth_rate)}${row('Lifespan', p.lifespan)}</dl>
    ${size.length ? html`<h3>Mature size</h3><div class="tbl-wrap"><table class="tbl"><thead><tr><th scope="col">Where</th><th scope="col">Height</th><th scope="col">Width</th></tr></thead>
      <tbody>${size.map(r => html`<tr><th scope="row">${r[0]}</th><td>${r[1] || ''}</td><td>${r[2] || ''}</td></tr>`)}</tbody></table></div>` : ''}
    ${zones || p.zone_notes ? html`<h3>Hardiness zones (USDA)</h3>${zones ? html`<p><strong>${zones}.</strong></p>` : ''}${paras(p.zone_notes)}${zoneHere(p)}` : ''}
    ${p.native_range ? html`<h3>Native range</h3>${paras(p.native_range)}` : ''}
    ${p.conservation_status ? html`<h3>Conservation status</h3>${paras(p.conservation_status)}` : ''}
    ${p.invasive ? html`<h3>Invasive risk</h3>${paras(p.invasive)}` : ''}
    ${p.bloom ? html`<h3>Flowers</h3>${paras(p.bloom)}` : ''}
    ${p.fruit ? html`<h3>Fruit</h3>${paras(p.fruit)}` : ''}
    ${p.danger_humans || p.danger_animals || p.pet_safety ? html`<div class="danger-box"><h3><span aria-hidden="true">⚠ </span>Dangers</h3>${p.danger_humans ? html`<h4>To people</h4>${paras(p.danger_humans)}` : ''}${p.danger_animals ? html`<h4>To pets and other animals</h4>${paras(p.danger_animals)}${p.pet_safety ? html`<p><strong>In short: ${p.pet_safety}.</strong></p>` : ''}` : ''}
      <p class="hint">If someone may have been poisoned, call Poison Control at 1-800-222-1222. For a pet, call your vet or the ASPCA Animal Poison Control Center at 888-426-4435.</p></div>` : ''}
    ${lines(p.propagation).length ? html`<h3>Propagation</h3>${ol(p.propagation)}` : ''}
    ${lines(p.sources).length ? html`<h3>Sources and further reading</h3><ul class="srcs">${srcList(p.sources)}</ul>` : ''}`;
}
function lightBlock(p, cur) {
  const lo = p.par_low, hi = p.par_high;
  const old = html`${p.light_summary ? html`<p><strong>${p.light_summary}</strong>${p.light_hours ? html`, about ${p.light_hours}` : ''}.</p>` : ''}${paras(p.light_notes)}`;
  if (!has(lo) || !has(hi)) return old;
  const MX = 2000, TICKS = [0, 100, 250, 500, 1000, 2000];
  const v = cur && has(cur.par) ? cur.par : null;
  const verdict = x => x < lo ? ['cool', 'Dimmer than this plant likes.'] : x > hi ? ['hot', 'Brighter than this plant likes.'] : ['ok', 'Comfortable.'];
  const lux = n => Math.round(n * 54 / 100) * 100;
  return html`<p>Comfortable light at the leaves is <strong>${fmt(lo)} to ${fmt(hi)} PAR</strong> (µmol/m²/s), roughly ${fmt(lux(lo))} to ${fmt(lux(hi))} lux.
      ${has(p.dli_low) && has(p.dli_high) ? html`Over a whole day that adds up to <strong>${p.dli_low} to ${p.dli_high} mol/m²/day</strong> (DLI).` : ''}</p>
    ${cur && has(cur.dli_today) ? html`<p>Light so far today: <strong>${cur.dli_today} mol/m²</strong>${has(p.dli_low) ? html` of the ${p.dli_low} to ${p.dli_high} this plant wants.` : '.'} ${cur.mode === 'weather' ? 'This is for open sky, so a plant under a roof or shade cloth gets less.' : ''}</p>` : ''}
    ${v == null ? '' : (() => { const [k, txt] = verdict(v); return html`<p class="nowstate v-${k}"><strong>Now ${fmt(v)} PAR.</strong> ${txt}${cur.mode === 'weather' ? ' This is open sky; under a roof it is much lower.' : ''}</p>`; })()}
    ${strip([['z-dim', posSqrt(lo, 0, MX)], ['z-ok', posSqrt(hi, 0, MX) - posSqrt(lo, 0, MX)], ['z-bright', 100 - posSqrt(hi, 0, MX)]], LIGHT_MARKS.map(m => [posSqrt(m[1], 0, MX), m[0]]), TICKS.map(x => [posSqrt(x, 0, MX), fmt(x)]), v == null ? null : { pos: posSqrt(v, 0, MX), label: fmt(v) + ' PAR' })}
    ${keyOf([['z-dim', 'Too dim'], ['z-ok', 'Comfortable'], ['z-bright', 'Too bright'], ...(v != null ? [['z-now', 'Now']] : [])])}
    <p class="hint">The scale stretches the dim end so low light is easy to read. Numbers are PAR in µmol/m²/s. 1 PAR is about 54 lux in sunlight.</p>
    <ul class="verdicts">${LIGHT_MARKS.map(m => { const [k, txt] = verdict(m[1]); return html`<li class="v-${k}"><span class="k">${m[0]}</span><span><strong>${m[2]}, about ${fmt(m[1])} PAR.</strong> ${txt}</span></li>`; })}</ul>
    ${old}`;
}
function rangeGauge(title, lo, hi, mn, mx, unit, now, names, ticks) {
  if (!has(lo) || !has(hi)) return '';
  const a = posLin(lo, mn, mx), b = posLin(hi, mn, mx);
  return html`<h3 class="gauge-title">${title}: ${lo} to ${hi}${unit}</h3>
    ${strip([[names[0][0], a], ['z-ok', b - a], [names[1][0], 100 - b]], [], ticks.map(x => [posLin(x, mn, mx), x + unit]), now == null ? null : { pos: posLin(now, mn, mx), label: now + unit })}
    ${keyOf([[names[0][0], names[0][1]], ['z-ok', 'Comfortable'], [names[1][0], names[1][1]], ...(now != null ? [['z-now', 'Now']] : [])])}`;
}
function soilBlock(p, cur) {
  const sm = cur && has(cur.soil_moisture) ? cur.soil_moisture : null, st = cur && has(cur.soil_temp_f) ? cur.soil_temp_f : null, ph = cur && has(cur.soil_ph) ? cur.soil_ph : null;
  return html`${paras(p.water_notes)}
    ${p.soil_medium ? html`<h3>Soil or potting mix</h3>${paras(p.soil_medium)}` : ''}
    ${rangeGauge('Soil moisture (a probe reading)', p.soil_moisture_low, p.soil_moisture_high, 0, 100, '%', sm, [['z-dry', 'Too dry'], ['z-wet', 'Too wet']], [0, 25, 50, 75, 100])}
    ${has(p.soil_moisture_low) ? html`<p class="hint">Probe readings depend on the sensor and the mix. Calibrate it: the reading in dry mix is 0% and in soaked mix is 100%.</p>` : ''}
    ${rangeGauge('Root-zone temperature', p.soil_temp_low, p.soil_temp_high, 30, 110, '°F', st, [['z-cool', 'Too cool'], ['z-hot', 'Too warm']], [30, 50, 70, 90, 110])}
    ${rangeGauge('Soil pH', p.soil_ph_low, p.soil_ph_high, 3, 9, '', ph, [['z-hot', 'Too acidic'], ['z-wet', 'Too alkaline']], [3, 4, 5, 6, 7, 8, 9])}`;
}

// ---------- is the plant in range, and what to do ----------
const LV = { ok: ['✔', 'In range'], near: ['▲', ''], bad: ['■', ''], danger: ['✖', ''] };
function winterTail(p, n) { const s = lines(p.winter_steps).slice(0, n); return s.length ? { title: 'From this plant\'s own winter steps', items: s } : null; }
function judge(p, cur) {
  const out = [];
  if (!cur) return out;
  const T = cur.temp_f, H = cur.humidity, L = cur.par, V = cur.vpd, SM = cur.soil_moisture, ST = cur.soil_temp_f, PH = cur.soil_ph;
  const openSky = cur.mode === 'weather' ? 'This reading is for open sky. Under a roof or shade cloth the plant gets less.' : '';
  const IL = p.temp_ideal_low, IH = p.temp_ideal_high;
  if (has(T) && has(IL) && has(IH)) {
    let level = 'ok', state = 'In range', detail = `${T}°F is inside the comfortable ${IL} to ${IH}°F.`, steps = [], tail = null;
    if (has(p.temp_lethal_below) && T < p.temp_lethal_below) {
      level = 'danger'; state = 'Far too cold: likely fatal'; detail = `${T}°F is ${r1(IL - T)}°F below the comfortable minimum of ${IL}°F, and below the ${p.temp_lethal_below}°F this plant dies at.`;
      steps = ['Bring it inside or into a heated room right now.', `Aim for at least ${IL}°F. Warm it up gradually, not next to a heater.`, 'Do not water it until it is back above ' + IL + '°F, then water lightly.', 'Do not prune, repot or fertilize while it is stressed.', 'Check it in the morning for black or mushy leaves and stems. Trim them only after it has warmed up.'];
      tail = winterTail(p, 4);
    } else if (has(p.temp_damage_below) && T < p.temp_damage_below) {
      level = 'bad'; state = 'Too cold: damage likely'; detail = `${T}°F is ${r1(IL - T)}°F below the comfortable minimum of ${IL}°F. Leaves and stems are hurt below ${p.temp_damage_below}°F.`;
      steps = ['Move it indoors, into the garage or under the porch roof now.', 'If it cannot move: cover it to the ground with frost cloth or a sheet over a frame. Plastic must not touch the leaves. Remove the cover once it is above 35°F.', 'Group pots against a south or east wall and pile mulch around the pots.', 'Water the day before a freeze, but not when the plant is already cold or the soil is frozen.', 'Hold off fertilizer until spring.'];
      tail = winterTail(p, 4);
    } else if (T < IL) {
      level = 'near'; state = 'A little cool'; detail = `${T}°F is ${r1(IL - T)}°F below the comfortable minimum of ${IL}°F. No damage is expected yet.`;
      steps = ['Move it close to the house wall or under the porch roof for the night.', 'Keep the mix on the dry side. Cold, wet roots are the main risk at this temperature.', 'No fertilizer while it is cool.', `It is comfortable again from ${IL}°F.`];
      if (p.winter_triggers) tail = { title: 'When to act, from this page', items: lines(p.winter_triggers) };
    } else if (has(p.temp_damage_above) && T >= p.temp_damage_above) {
      level = 'bad'; state = 'Too hot: heat damage likely'; detail = `${T}°F is ${r1(T - IH)}°F above the comfortable maximum of ${IH}°F. Leaves can scorch from ${p.temp_damage_above}°F.`;
      steps = ['Move it into shade now.', 'If the mix is dry, water slowly until it drains. If it is already wet, do not add water.', 'Use 50% shade cloth over the afternoon until temperatures fall.', 'Look for scorched, bleached or crispy leaves, and trim them only after it cools.', 'Move pots off hot concrete or metal.'];
    } else if (T > IH) {
      level = 'near'; state = 'A little warm'; detail = `${T}°F is ${r1(T - IH)}°F above the comfortable maximum of ${IH}°F.`;
      steps = ['Give it shade in the afternoon: 30 to 50% shade cloth, or move it under the porch roof or a tree.', 'Water in the morning. Check the mix daily and water when the top inch is dry.', 'Do not fertilize, repot or prune in the heat.', 'Move pots off hot concrete or metal and out of reflected heat.'];
    }
    out.push({ key: 'temp', label: 'Temperature', value: T + '°F', level, state, detail, steps, tail });
  }
  if (has(H) && has(p.humidity_low) && has(p.humidity_high)) {
    const lo = p.humidity_low, hi = p.humidity_high;
    let level = 'ok', state = 'In range', detail = `${H}% is inside the comfortable ${lo} to ${hi}%.`, steps = [];
    if (H < lo) {
      level = lo - H > 15 ? 'bad' : 'near'; state = 'Too dry'; detail = `${H}% is ${r1(lo - H)} points below the comfortable minimum of ${lo}%.`;
      steps = ['Group the plant with other plants; they raise the humidity around each other.', 'Set the pot on a tray of pebbles with water below the pebbles. The pot must not stand in the water.', `Run a humidifier nearby, aiming for ${lo} to ${hi}%.`, 'Keep it away from heater vents, fireplaces and drafts.', 'Water on schedule. Misting only helps for a few minutes and can spot the leaves.'];
    } else if (H > hi) {
      level = H - hi > 15 ? 'bad' : 'near'; state = 'Too humid'; detail = `${H}% is ${r1(H - hi)} points above the comfortable maximum of ${hi}%.`;
      steps = ['Increase airflow: a small fan on low, or more space between plants.', 'Water in the morning so leaves dry before night, and keep water off the leaves.', 'Remove dead leaves and flowers.', 'Watch for mildew, grey mould and rot. Let the top of the mix dry before watering again.', 'Indoors, run a dehumidifier. Outdoors, move it under cover from drizzle.'];
    }
    out.push({ key: 'hum', label: 'Humidity', value: H + '%', level, state, detail, steps });
  }
  if (has(L) && has(p.par_low) && has(p.par_high)) {
    const lo = p.par_low, hi = p.par_high;
    let level = 'ok', state = 'In range', detail = `${fmt(L)} PAR is inside the comfortable ${fmt(lo)} to ${fmt(hi)}.`, steps = [];
    if (L < lo) {
      level = L < lo * .6 ? 'bad' : 'near'; state = 'Too dim'; detail = `${fmt(L)} PAR is below the comfortable minimum of ${fmt(lo)}.`;
      steps = ['Move it to a brighter spot: a south or east window indoors, or the sunniest part of the porch outdoors.', 'Clean the window glass and keep the plant within about 3 ft (1 m) of it.', `Or add a full-spectrum LED grow light about 12 in (30 cm) above the plant for 12 to 14 hours a day on a timer. Aim for ${fmt(lo)} to ${fmt(hi)} PAR at the leaves.`, 'Turn the pot a quarter turn each week so it grows evenly.', 'Water less often. A plant in low light uses water slowly.'];
    } else if (L > hi) {
      level = L > hi * 1.5 ? 'bad' : 'near'; state = 'Too bright'; detail = `${fmt(L)} PAR is above the comfortable maximum of ${fmt(hi)}.`;
      steps = ['Move it into filtered light, or use 30 to 50% shade cloth, especially from noon to 4 pm.', 'Do not move a shaded plant straight into full sun. Step it up over 7 to 10 days.', 'Look for bleached, tan or crispy patches (sunburn). Trim them off later.', 'Water a little more often. Bright light dries the mix faster.'];
    }
    out.push({ key: 'light', label: 'Light', value: fmt(L) + ' PAR', level, state, detail, steps, note: openSky });
  }
  if (has(V) && has(p.vpd_low) && has(p.vpd_high)) {
    let level = 'ok', state = 'In range', detail = `${V} kPa is inside the comfortable ${p.vpd_low} to ${p.vpd_high}.`, steps = [];
    if (V > p.vpd_high) { level = V > p.vpd_high * 1.4 ? 'bad' : 'near'; state = 'Air too dry and warm'; detail = `${V} kPa is above ${p.vpd_high}. The air is pulling water out of the leaves faster than the roots can supply it.`;
      steps = ['Raise the humidity (see the humidity steps) or lower the temperature.', 'Shade the plant and shelter it from wind.', 'Check the mix and water if it is dry.']; }
    else if (V < p.vpd_low) { level = 'near'; state = 'Air too damp'; detail = `${V} kPa is below ${p.vpd_low}. The air is so damp that the plant barely transpires.`;
      steps = ['Add airflow with a small fan, or more space around the plant.', 'Keep the mix drier and water in the morning.', 'Watch for mildew and rot.']; }
    out.push({ key: 'vpd', label: 'Air dryness (VPD)', value: V + ' kPa', level, state, detail, steps });
  }
  if (has(SM) && has(p.soil_moisture_low) && has(p.soil_moisture_high)) {
    let level = 'ok', state = 'In range', detail = `${SM}% is inside the comfortable ${p.soil_moisture_low} to ${p.soil_moisture_high}%.`, steps = [];
    if (SM < p.soil_moisture_low) { level = SM < p.soil_moisture_low * .5 ? 'bad' : 'near'; state = 'Soil too dry'; detail = `${SM}% is below ${p.soil_moisture_low}%.`;
      steps = ['Water thoroughly until it drains from the bottom, then empty the saucer.', 'If water runs straight through, soak the pot in a bucket for 15 minutes, because the mix has dried and shrunk.', 'Check again in a few hours with the probe.']; }
    else if (SM > p.soil_moisture_high) { level = SM > p.soil_moisture_high * 1.3 ? 'bad' : 'near'; state = 'Soil too wet'; detail = `${SM}% is above ${p.soil_moisture_high}%.`;
      steps = ['Do not water until the reading falls back into range.', 'Empty the saucer and make sure the drainage holes are clear.', 'Move it somewhere airy and warm so the mix dries.', 'If leaves yellow or the base is soft, slide the plant out. Mushy, dark roots mean root rot: trim them and repot into fresh, dry mix.']; }
    out.push({ key: 'soil', label: 'Soil moisture', value: SM + '%', level, state, detail, steps });
  }
  if (has(ST) && has(p.soil_temp_low) && has(p.soil_temp_high)) {
    let level = 'ok', state = 'In range', detail = `${ST}°F is inside the comfortable ${p.soil_temp_low} to ${p.soil_temp_high}°F.`, steps = [];
    if (ST < p.soil_temp_low) { level = ST < p.soil_temp_low - 10 ? 'bad' : 'near'; state = 'Roots too cool'; detail = `${ST}°F is ${p.soil_temp_low - ST}°F below ${p.soil_temp_low}°F.`;
      steps = ['Lift the pot off cold ground or concrete onto feet or a board.', 'Wrap the pot in burlap or bubble wrap, or sink it into a larger pot of mulch.', 'Water only when the mix is dry; cold, wet roots rot.']; }
    else if (ST > p.soil_temp_high) { level = ST > p.soil_temp_high + 10 ? 'bad' : 'near'; state = 'Roots too warm'; detail = `${ST}°F is ${ST - p.soil_temp_high}°F above ${p.soil_temp_high}°F.`;
      steps = ['Shade the sides of the pot from the afternoon sun.', 'Stand the pot off hot concrete or metal, or double-pot it.', 'Water in the morning, and mulch the surface.']; }
    out.push({ key: 'soiltemp', label: 'Root-zone temperature', value: ST + '°F', level, state, detail, steps });
  }
  if (has(PH) && has(p.soil_ph_low) && has(p.soil_ph_high)) {
    let level = 'ok', state = 'In range', detail = `pH ${PH} is inside the comfortable ${p.soil_ph_low} to ${p.soil_ph_high}.`, steps = [];
    if (PH < p.soil_ph_low) { level = 'near'; state = 'Soil too acidic'; detail = `pH ${PH} is below ${p.soil_ph_low}.`; steps = ['Water with plain rain water or let tap water stand, and stop acid-type fertilizers.', 'Mix in a small amount of dolomitic lime (about 1 teaspoon per gallon of mix) and test again in 2 weeks.', 'Or repot into fresh mix.']; }
    else if (PH > p.soil_ph_high) { level = 'near'; state = 'Soil too alkaline'; detail = `pH ${PH} is above ${p.soil_ph_high}.`; steps = ['Water with rain water: tap water is often alkaline.', 'Feed with an acid-type fertilizer, and add chelated iron if new leaves are pale with green veins.', 'Or repot into fresh mix, with pine bark or peat added.']; }
    out.push({ key: 'ph', label: 'Soil pH', value: 'pH ' + PH, level, state, detail, steps });
  }
  return out;
}
function condCard(p, cur) {
  const res = p ? judge(p, cur) : [];
  const by = Object.fromEntries(res.map(r => [r.key, r]));
  const cell = (key, label, val, unit) => {
    if (!has(val)) return '';
    const r = by[key];
    return html`<div class="val"><span class="lab">${label}</span><span class="n">${fmt(val, 1)}${unit}</span>
      ${r ? html`<span class="st st-${r.level}">${LV[r.level][0]} ${r.state}</span>` : ''}</div>`;
  };
  const any = cur && ['temp_f', 'humidity', 'par', 'soil_moisture', 'soil_temp_f', 'soil_ph'].some(k => has(cur[k]));
  return html`<section class="cond" id="sec-now" aria-labelledby="cond-h"><header><h2 id="cond-h">Current conditions</h2>
      <button class="btn small noprint" type="button" data-act="setcond">${any ? 'Change' : 'Set current conditions'}</button></header>
    ${any ? html`<div class="vals">${cell('temp', 'Temperature', cur.temp_f, '°F')}${cell('hum', 'Humidity', cur.humidity, '%')}${cell('light', 'Light (PAR)', cur.par, '')}${cell('vpd', 'Air dryness (VPD)', cur.vpd, ' kPa')}
        ${cell('soil', 'Soil moisture', cur.soil_moisture, '%')}${cell('soiltemp', 'Root-zone temp', cur.soil_temp_f, '°F')}${cell('ph', 'Soil pH', cur.soil_ph, '')}</div>
      <p class="src">${cur.label}${cur.as_of ? html`, updated ${ago(cur.age_minutes)}` : ''}.${cur.stale ? html` <strong>This reading is old.</strong>` : ''}${cur.dli_today != null ? html` Light so far today: ${cur.dli_today} mol/m².` : ''}
        ${cur.mode === 'weather' ? ' Light is for open sky; plants under a roof get less.' : ''}</p>
      ${p && isInside(p) && cur.mode === 'weather' ? html`<p class="src"><strong>This plant is ${p.site.toLowerCase()}</strong>, so these outdoor readings do not apply to it. Use Change to type in the indoor temperature and humidity, or a sensor near it.</p>` : ''}`
      : html`<p class="src">Type in the temperature, humidity and light where this plant sits (or pick your sensor or the online weather). The bars below then show a "Now" marker, and this page says what to do if the plant is outside its comfortable range.</p>`}
  </section>`;
}
function adviceBlock(p, cur) {
  const res = judge(p, cur);
  if (!res.length) return '';
  const bad = res.filter(r => r.level !== 'ok');
  return html`<section class="advice" id="sec-advice" aria-labelledby="adv-h"><h2 id="adv-h">${bad.length ? 'Getting this plant back in range' : 'In range'}</h2>
    ${bad.length ? bad.map(r => html`<div class="issue"><h3 class="st-${r.level}">${LV[r.level][0]} ${r.label}: ${r.state} (${r.value})</h3><p>${r.detail}</p>
        <p><strong>What to do</strong></p><ol>${r.steps.map(x => html`<li>${x}</li>`)}</ol>
        ${r.tail ? html`<p><strong>${r.tail.title}</strong></p><ul>${r.tail.items.map(x => html`<li>${x}</li>`)}</ul>` : ''}
        ${r.note ? html`<p class="hint">${r.note}</p>` : ''}</div>`)
      : html`<p class="good">✔ Everything you have entered is inside this plant's comfortable range.</p>`}
    ${bad.length && res.length > bad.length ? html`<p class="src" style="padding:.6rem 1.1rem;color:var(--ink-2)">In range: ${res.filter(r => r.level === 'ok').map(r => r.label).join(', ')}.</p>` : ''}
  </section>`;
}

// ---------- plant page ----------
let CUR = null, PIDX = 0, KEEP = null;
function requestText(p) {
  const items = lines(p.id_improve);
  return `Plant ${p.code} (${p.common_name}${p.scientific_name ? ', ' + p.scientific_name : ''}). Claude's current ID confidence is ${p.id_confidence == null ? 'not rated' : p.id_confidence + '%'}.\n\n` +
    (items.length ? 'To raise it, I am sending:\n' + items.map(x => '- ' + x).join('\n') : 'Please tell me what else you need to identify this plant.') +
    `\n\n(Attach photos in the same message, then I will update the record.)`;
}
function photoPanel(p) {
  const ph = p.photos, i = clamp(PIDX, 0, Math.max(0, ph.length - 1)), cur = ph[i];
  return html`${cur ? html`<button type="button" class="main-photo" data-act="zoom" aria-label="Enlarge photo"><img src="${photoUrl(cur.file)}" alt="${cur.caption || p.common_name}"></button>
      <p class="cap">${cur.caption || 'No caption'}. Added ${when(cur.added_at)} by ${cur.added_by}.</p>
      ${ph.length > 1 ? html`<p class="main-note noprint">${cur.is_primary
        ? html`<strong>★ This is the main photo.</strong> It is the one shown on the Plants page, on care cards and in plant link previews.`
        : html`<button class="btn small" type="button" data-act="mainphoto">Make this the main photo</button> <span class="hint">The main photo is the one shown on the Plants page, on care cards and in plant link previews.</span>`}</p>` : ''}`
      : html`<div class="empty">No photos yet. Add one below.</div>`}
    ${ph.length > 1 ? html`<div class="thumbs">${ph.map((x, j) => html`<button type="button" data-act="pick" data-i="${j}" aria-label="Photo ${j + 1} of ${ph.length}${x.is_primary ? ', the main photo' : ''}" aria-current="${String(j === i)}"><img src="${thumbUrl(x.file)}" alt="">${x.is_primary ? html`<span class="th-main" aria-hidden="true">★ Main</span>` : ''}</button>`)}</div>` : ''}
    <div class="row noprint">
      ${cur ? html`<button class="btn ghost small" type="button" data-act="capedit">Edit caption</button>
        <button class="btn ghost small" type="button" data-act="movephoto">Move to another plant</button>
        <button class="btn danger small" type="button" data-act="rmphoto">Remove photo</button>` : ''}
    </div>
    <label class="f noprint" style="margin-top:1.2rem">Add photos<small>JPG or PNG. Location data is removed when the photo is saved.</small>
      <input type="file" accept="image/*" multiple data-act="addphotos"></label>`;
}
// ---------- plant timeline and photo comparison (added in 1.8.0) ----------
const TL = { code: null, data: null, a: null, b: null, hide: new Set() };
const TL_KINDS = [['photo', 'Photos'], ['change', 'Changes to the page'], ['care', 'Feeding and care'], ['request', 'Answers'], ['created', 'Page created']];
const TL_WORD = { photo: 'Photo', change: 'Changed', care: 'Care', request: 'Answer', created: 'Created' };
const tlDay = ts => new Date(ts).toLocaleDateString([], { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
const tlShort = ts => new Date(ts).toLocaleDateString([], { month: 'short', day: 'numeric' });
function tlChange(ch) {
  const set = x => x != null && x !== '', v = x => ch.field === 'id_confidence' ? x + '%' : x;
  const what = !set(ch.old) ? html`set to ${v(ch.new)}` : !set(ch.new) ? html`cleared (it was ${v(ch.old)})` : html`from ${v(ch.old)} to ${v(ch.new)}`;
  return html`<li><strong>${ch.label.replace(' (%)', '')}:</strong> ${what}</li>`;
}
function tlTrend(list, cur, word, order) {
  // "Critical until Oct 22, Poor now (getting better)": the first value the log knows, the day it first changed, and now.
  const set = x => x != null && x !== '';
  if (!list.length || !set(cur)) return '';
  const startsEmpty = !set(list[0].old), first = startsEmpty ? list[0].new : list[0].old, until = startsEmpty ? list[1] : list[0];
  if (!until || String(first) === String(cur)) return '';
  const a = order(first), b = order(cur), better = a < 0 || b < 0 || isNaN(a) || isNaN(b) || a === b ? null : b > a;
  const pc = x => word === 'ID confidence' ? x + '%' : x;
  const how = better == null ? '' : word === 'Health' ? (better ? ' (getting better)' : ' (getting worse)') : (better ? ' (more certain)' : ' (less certain)');
  return html`<li><strong>${word}:</strong> ${pc(first)} until ${tlShort(until.at)}, ${pc(cur)} now${how}</li>`;
}
function tlCompare(D) {
  const ps = D.photos; if (ps.length < 2) return '';
  const a = ps.find(x => x.file === TL.a) || ps[0], b = ps.find(x => x.file === TL.b) || ps[ps.length - 1];
  const opt = (sel, side) => html`<label class="f">${side === 'a' ? 'Left photo' : 'Right photo'}<select data-act="tlsel" data-side="${side}">${ps.map((x, i) => html`<option value="${x.file}" ${x.file === sel.file ? raw('selected') : ''}>${i + 1}. ${tlShort(x.added_at)}: ${x.caption || 'no caption'}</option>`)}</select></label>`;
  const fig = x => html`<figure class="tl-fig"><img src="${photoUrl(x.file)}" alt="${x.caption || 'Plant photo'}" loading="lazy"><figcaption><strong>${tlShort(x.added_at)}</strong>. ${x.caption || ''}</figcaption></figure>`;
  return html`<h3>Compare two photos</h3><p class="muted">The oldest and the newest photo, side by side. Pick others to compare.</p>
    <div class="tl-pick">${opt(a, 'a')}${opt(b, 'b')}</div><div class="tl-cmp">${fig(a)}${fig(b)}</div>`;
}
function tlRender() {
  const box = document.getElementById('tl-box'), D = TL.data; if (!box || !D) return;
  const ev = D.events.filter(e => !TL.hide.has(e.kind));
  const days = []; ev.forEach(e => { const d = tlDay(e.at); if (!days.length || days[days.length - 1].d !== d) days.push({ d, items: [] }); days[days.length - 1].items.push(e); });
  const trend = [tlTrend(D.health, D.current.health, 'Health', h => HEALTH_ORDER[h] ?? -1), tlTrend(D.confidence, D.current.id_confidence, 'ID confidence', n => +n)].filter(Boolean);
  box.innerHTML = rend(html`${trend.length ? html`<ul class="tl-trend">${trend}</ul>` : ''}
    ${tlCompare(D)}
    <h3>Everything that has happened</h3>
    <fieldset class="tl-filter"><legend>Show</legend>${TL_KINDS.map(([k, w]) => html`<label class="chk"><input type="checkbox" data-act="tlkind" value="${k}" ${TL.hide.has(k) ? '' : raw('checked')}>${w}</label>`)}</fieldset>
    ${days.length ? days.map(g => html`<h4 class="tl-day">${g.d}</h4><ul class="tl">${g.items.map(e => html`<li class="tl-item tl-${e.kind}">
      <span class="tl-kind">${e.kind === 'request' && !e.answer ? 'Done' : TL_WORD[e.kind]}</span><div class="tl-body">${e.kind === 'request'
        ? html`<div><strong>Asked:</strong> ${linkify(e.question || '')}</div><div class="tl-ans">${e.answer ? html`<strong>Answer:</strong> ${linkify(e.answer)}` : 'Marked done'}</div>`
        : html`<div>${linkify(e.title)}</div>`}
        ${e.changes.length || e.other ? html`<ul class="tl-ch">${e.changes.map(tlChange)}${e.other ? html`<li class="muted">and ${e.other} other detail${e.other === 1 ? '' : 's'}</li>` : ''}</ul>` : ''}
        ${e.photos.length ? html`<div class="tl-photos">${e.photos.map(x => html`<button type="button" class="tl-thumb" data-act="tlpick" data-file="${x.file}" title="Compare this photo"><img src="${thumbUrl(x.file)}" alt="${x.caption || 'Plant photo'}" loading="lazy"><span>Compare</span></button>`)}</div>` : ''}
        ${e.by ? html`<div class="tl-by muted">By ${e.by}</div>` : ''}</div></li>`)}</ul>`)
      : html`<p class="muted">Nothing to show with these choices.</p>`}`);
}
async function loadTimeline(box) {
  const code = box.dataset.code;
  try { TL.data = await api('GET', '/api/plants/' + enc(code) + '/timeline'); } catch (e) { box.innerHTML = rend(html`<p class="notice bad">Could not load the timeline: ${e.message}</p>`); return; }
  if (TL.code !== code) { TL.code = code; TL.a = TL.b = null; }
  tlRender();
}
new MutationObserver(() => { const b = document.getElementById('tl-box'); if (b && !b.dataset.loaded) { b.dataset.loaded = '1'; loadTimeline(b); } })
  .observe(document.getElementById('app'), { childList: true });
function slips(h) {
  const byV = {};
  h.audit.forEach(a => { (byV[a.version] = byV[a.version] || []).push(a); });
  return h.versions.map(v => {
    const rows = (byV[v.version] || []).filter(a => a.field);
    const cur = v.version === h.current;
    return html`<article class="slip ${cur ? 'cur' : ''}">
      <header><h3>Version ${v.version}${cur ? ' (current)' : ''}</h3><span class="when">${timeEl(v.changed_at)} by ${v.changed_by}</span></header>
      <p style="margin:.4rem 0">${v.summary || ''}</p>
      ${rows.length ? html`<table class="chg"><thead class="sr"><tr><th>Field</th><th>Before and after</th></tr></thead><tbody>${rows.map(a => html`<tr><th scope="row">${a.label || a.field}</th>
        <td>${a.old_value == null || a.old_value === '' ? html`<span class="muted">Before: empty</span>` : html`<div class="old">${a.old_value}</div>`}
        ${a.new_value == null || a.new_value === '' ? html`<div class="muted">After: empty</div>` : html`<div class="new">${a.new_value}</div>`}</td></tr>`)}</tbody></table>` : ''}
      <div class="row noprint"><button class="btn ghost small" type="button" data-act="viewver" data-v="${v.version}">View this version</button>
        ${cur ? '' : html`<button class="btn ghost small" type="button" data-act="restore" data-v="${v.version}">Restore its text</button>`}</div>
    </article>`;
  });
}
async function viewPlant(code) {
  const [p, h, cur, st] = await Promise.all([api('GET', '/api/plants/' + enc(code)), api('GET', '/api/plants/' + enc(code) + '/history'), loadCond(), api('GET', '/api/settings').catch(() => ({}))]);
  CUR = { p, h, base: st.base_url || location.origin };
  PIDX = KEEP != null ? KEEP : Math.max(0, p.photos.findIndex(x => x.is_primary));
  KEEP = null;
  const archived = p.status === 'archived';
  const dl = [['Also known as', p.aliases], ['Plant type', p.plant_type], ['Spot', p.location], ['Container', p.container]].filter(x => x[1]);
  const single = document.documentElement.dataset.layout === 'single';
  return {
    title: p.common_name,
    html: html`${pnavBlock(p.code)}<p class="crumb"><a href="#/">All plants</a>
      <button class="btn ghost small noprint" type="button" data-act="layout">${single ? 'Show photos and details side by side' : 'Switch to one column'}</button></p>
    ${archived ? html`<div class="notice">This record is archived. It is hidden from the main list.</div>` : ''}
    <div class="plant">
      <div class="pane" id="pane-l" tabindex="0" role="region" aria-label="Photos"><div id="photopanel" data-section="Photos">${photoPanel(p)}</div></div>
      <div class="pane" id="pane-r" tabindex="0" role="region" aria-label="Details">
        <nav class="jump noprint" id="jumprow" aria-label="Jump to a section"></nav>
        <div class="label" id="details" data-section="Name and details">
          <div class="l-top"><b>${p.code}</b><span>Page version ${p.version}</span><span>Updated ${timeEl(p.updated_at)} by ${p.updated_by}</span></div>
          <div class="l-body"><h1>${p.common_name}</h1><p class="sci latin">${p.scientific_name || 'Scientific name not set'}</p>
            <dl><dt id="site-lbl">Location</dt><dd>${sitePicker(p)}</dd>
              ${dl.map(x => html`<dt>${x[0]}</dt><dd>${x[1]}</dd>`)}
              <dt>ID confidence</dt><dd>${p.id_confidence == null ? 'Not rated' : p.id_confidence + '%'}</dd>
              <dt>Winter plan</dt><dd>${planTag(p.winter_plan)}</dd><dt>Health</dt><dd>${healthTag(p.health_rating)}</dd>
              <dt>Groups</dt><dd id="pl-groups">${groupsOf(p.code).length ? groupsOf(p.code).map((g, i) => html`${i ? ', ' : ''}<a href="#/group/${g.id}">${g.name}</a>`) : 'None yet'}
                <button class="btn small ghost noprint" type="button" data-act="plgroups">Change groups</button></dd></dl>
            <div class="row acts noprint"><a class="btn" href="#/plant/${enc(p.code)}/edit">Edit this page</a>
              <button class="btn ghost" type="button" data-act="archive" data-to="${archived ? '0' : '1'}">${archived ? 'Move back to the main list' : 'Archive'}</button></div></div>
        </div>
        ${careQuick(p)}

        ${frostNote(p)}${needsBox(p)}
        ${condCard(p, cur)}${adviceBlock(p, cur)}

        <section class="blk" id="ident"><h2>Plant identification</h2>
          <div class="big-meter"><span class="n">${p.id_confidence == null ? '?' : p.id_confidence + '%'}</span><i style="--v:${p.id_confidence || 0}%;--mc:${confColor(p.id_confidence)}" role="img" aria-label="ID confidence ${p.id_confidence || 0} percent"></i></div>
          ${paras(p.id_basis)}
          ${lines(p.id_alternatives).length ? html`<h3>Other possibilities</h3>${ul(p.id_alternatives)}` : ''}
          ${lines(p.id_improve).length ? html`<div class="ask"><h3 style="margin-top:0">To reach 100%, send</h3>${ul(p.id_improve)}
            <button class="btn small noprint" type="button" data-act="copyreq">Copy this as a request for Claude</button></div>` : ''}
        </section>

        <section class="blk" id="about"><h2>About this plant</h2>${aboutBlock(p)}</section>

        <section class="blk" id="temp"><h2>Temperature</h2>${tempBlock(p, cur)}${paras(p.temp_notes)}${histBlock('temp')}</section>
        <section class="blk" id="hum"><h2>Humidity</h2>${humBlock(p, cur)}${histBlock('hum')}</section>
        <section class="blk" id="light"><h2>Sunlight</h2>${lightBlock(p, cur)}<div id="pl-grow" class="pl-grow"></div>${histBlock('light')}</section>
        <section class="blk" id="soil"><h2>Water and soil</h2><div id="care-plant"><p class="loading">Loading the watering record</p></div>${soilBlock(p, cur)}${histBlock('soil')}</section>
        <section class="blk" id="nutrients"><h2>Nutrients</h2>
          ${p.fertilizer ? html`<p><strong>Fertilizer:</strong> ${p.fertilizer}</p>` : ''}${paras(p.nutrients)}
          ${!p.fertilizer && !p.nutrients ? html`<p class="muted">Not filled in yet. Use Edit to add it.</p>` : ''}
          <div id="fert-need"></div>
          <h3>Feeding schedule and log</h3><div id="fert-plant"><p class="loading">Loading</p></div></section>

        <section class="blk" id="winter"><h2>Winter in ${placeShort()}</h2>
          <p>${planTag(p.winter_plan)}</p>${paras(p.winter_summary)}
          ${p.winter_triggers ? html`<h3>When to act</h3>${paras(p.winter_triggers)}` : ''}
          ${lines(p.winter_steps).length ? html`<h3>Steps</h3>${ol(p.winter_steps)}` : ''}
          ${lines(p.indoor_setup).length ? html`<h3>Keeping it comfortable when the weather cannot</h3>${ul(p.indoor_setup)}` : ''}</section>

        <section class="blk" id="inside"><h2>Getting ready to come inside</h2><div id="prep-box" data-code="${p.code}"><p class="loading">Loading the pest check plan</p></div></section>

        <section class="blk" id="health"><h2>Health</h2>
          <p>${healthTag(p.health_rating)}</p>${paras(p.health_summary)}
          ${lines(p.health_observations).length ? html`<h3>What I can see</h3>${ul(p.health_observations)}` : ''}
          ${lines(p.health_steps).length ? html`<h3>Steps to improve</h3>${ol(p.health_steps)}` : ''}</section>

        <section class="blk" id="pests"><h2>Pests and diseases</h2>
          ${p.pests_current ? html`<h3 style="margin-top:0">Seen now</h3>${paras(p.pests_current)}` : ''}
          ${lines(p.pests_watch).length ? html`<h3>What to watch for</h3>${ul(p.pests_watch)}` : ''}
          ${lines(p.pest_steps).length ? html`<h3>Prevention and treatment</h3>${ol(p.pest_steps)}` : ''}
          ${!p.pests_current && !p.pests_watch ? html`<p class="muted">Not filled in yet. Use Edit to add it.</p>` : ''}</section>

        ${p.notes ? html`<section class="blk" id="notes"><h2>Notes</h2>${paras(p.notes)}</section>` : ''}

        <section class="blk" id="label"><h2>Label</h2>
          <p class="muted">The same label as on the Labels page. Scanning the code with a phone opens this page.</p>
          ${labelCard(p, CUR.base, false)}
          <p class="noprint"><button class="btn" type="button" data-act="printlabel">Print this label</button></p></section>

        <section class="blk" id="timeline"><h2>Timeline</h2><div id="tl-box" data-code="${p.code}"><p class="loading">Loading the timeline</p></div></section>

        <section class="blk" id="history"><h2>Page history</h2>
          <p class="muted">Created ${timeEl(p.created_at)} by ${p.created_by}. Every save makes a new version and keeps the old one.</p>
          ${slips(h)}</section>
      </div>
    </div>`,
    after: () => { fitPanes(); loadFertPlant(); loadCarePlant(); loadGrowPlant(p.code); pnavLayout(); setTimeout(pnavLayout, 300); },
  };
}
// where the plant is now: a plain-looking menu in the plant's label; choosing saves straight away
const isInside = p => (META.inside_sites || ['Indoors']).includes(p.site);
async function moveSite(el, site) {
  if (!(await needName())) return;
  const code = el.dataset.code, y = window.scrollY;
  await guard(async () => {
    await api('POST', '/api/plants/' + enc(code) + '/site', { site });
    toast(el.dataset.name + (site === 'Indoors' ? ' moved indoors' : ' moved back outside')); FROST_AT = 0;
    await route(); window.scrollTo(0, y);
    const back = document.querySelector(`[data-act="${site === 'Indoors' ? 'moveout' : 'movein'}"][data-code="${code}"]`);
    const next = document.querySelector('.winter-list [data-act="movein"]');
    (next || back || document.querySelector('main h1')).focus({ preventScroll: true });
  });
}
async function fzMark(el, what) {
  if (!(await needName())) return;
  const y = window.scrollY, code = el.dataset.code;
  await guard(async () => { await api('POST', '/api/frost/done', { date: el.dataset.date, code, what }); toast(what ? 'Marked as covered' : 'Tick removed'); await fzReload(y, code); });
}
async function fzReload(y, code) {
  await loadFrost(true); await loadCodes(true); await route(); window.scrollTo(0, y);
  const f = (code && document.querySelector(`.fz-row[data-code="${code}"] button`)) || document.querySelector('.fz-row:not(.is-done) button') || document.querySelector('main h1');
  if (f) f.focus({ preventScroll: true });
}
function sitePicker(p) {
  const v = p.site || 'Outdoors';
  return html`<select class="site-pick noprint" data-act="site" aria-labelledby="site-lbl" title="Change where this plant is">${(META.sites || ['Outdoors', 'Indoors']).map(o => html`<option ${o === v ? raw('selected') : ''}>${o}</option>`)}</select><span class="printonly">${v}</span>`;
}
// ---------- previous / next plant (follows the Plants page filters and sort) ----------
function pnavNeighbours(code) {
  const all = [...PCODES.values()], list = filteredPlants(all);
  let i = list.findIndex(p => p.code === code), inList = i >= 0;
  if (!inList) {                                   // this plant is filtered out: go to the plants either side of where it would sort
    const cur = PCODES.get(code) || { code, common_name: '', health_rating: '', id_confidence: null, updated_at: '' };
    const cmp = plantCmp(); i = list.findIndex(p => cmp(cur, p) < 0); if (i < 0) i = list.length;
    return { prev: list[i - 1] || null, next: list[i] || null, pos: null, n: list.length, total: all.length };
  }
  return { prev: list[i - 1] || null, next: list[i + 1] || null, pos: i + 1, n: list.length, total: all.length };
}
function pnavLink(p, dir) {
  const word = dir === 'prev' ? 'Previous Plant' : 'Next Plant', arrow = dir === 'prev' ? '←' : '→';
  if (!p) return html`<span class="pn pn-${dir} pn-none" aria-disabled="true"><span class="pn-dir">${dir === 'prev' ? arrow + ' ' + word : word + ' ' + arrow}</span><span class="pn-name">${dir === 'prev' ? 'This is the first plant in the list' : 'This is the last plant in the list'}</span></span>`;
  return html`<a class="pn pn-${dir}" href="#/plant/${enc(p.code)}" rel="${dir}" data-pncode="${p.code}">
    <span class="pn-dir">${dir === 'prev' ? arrow + ' ' + word : word + ' ' + arrow}</span><span class="pn-name">${p.common_name}</span><span class="pn-code">${p.code}</span></a>`;
}
function filterWords() {
  const w = [];
  if (G.needs) w.push('needs something from you'); if (G.plan) w.push(G.plan); if (G.health) w.push('health ' + G.health);
  if (G.low) w.push('ID under 70%'); if (G.q.trim()) w.push('"' + G.q.trim() + '"');
  if (G.group && groupById(G.group)) w.push('group ' + groupById(G.group).name);
  if (G.site) w.push(G.site.toLowerCase());
  if (G.status !== 'active') w.push(G.status === 'all' ? 'archived included' : 'archived only');
  for (const d of MORE) if (G[d.key]) { const o = moreOpts(d).find(x => x[0] === G[d.key]); if (o) w.push(o[1].toLowerCase()); }
  return (w.length ? w.join(', ') : 'all plants') + '; sorted by ' + (SORTS[G.sort] || 'code').toLowerCase();
}
function pnavBlock(code) {
  const N = pnavNeighbours(code);
  return html`<nav class="pnav noprint" id="pnav" aria-label="Previous and next plant" data-code="${code}">${pnavLink(N.prev, 'prev')}${pnavLink(N.next, 'next')}</nav>
    <details class="pn-filters noprint" id="pn-filters"${PNOPEN ? raw(' open') : ''}><summary>Filters for Previous / Next: <span id="pn-sum">${filterWords()}</span>
      <span class="pn-pos" id="pn-pos">${N.pos ? `plant ${N.pos} of ${N.n}` : `this plant is not in the filtered list (${N.n} of ${N.total})`}</span></summary>
      <div class="filters">
        <label>Search<input type="search" data-f="q" value="${G.q}" placeholder="Name, code, location"></label>
        <label>Winter plan<select data-f="pnplan"><option value="">Any</option>${META.winter_plans.map(pl => html`<option ${G.plan === pl ? raw('selected') : ''}>${pl}</option>`)}</select></label>
        <label>Health<select data-f="health"><option value="">Any</option>${META.health.map(h => html`<option ${G.health === h ? raw('selected') : ''}>${h}</option>`)}</select></label>
        ${siteFilter()}${groupFilter()}${statusFilter()}${moreSelects()}
        <label>Sort by<select data-f="sort">${Object.entries(SORTS).map(([k, v]) => html`<option value="${k}" ${G.sort === k ? raw('selected') : ''}>${v}</option>`)}</select></label>
        <label class="chk"><input type="checkbox" data-f="pnneeds" ${G.needs ? raw('checked') : ''}>Needs something from you</label>
        <label class="chk"><input type="checkbox" data-f="low" ${G.low ? raw('checked') : ''}>ID confidence under 70%</label>
        <button class="btn ghost small" type="button" data-act="clearfilters">Clear filters</button>
      </div><p class="hint">These are the same filters as on the Plants page; changing them here changes them there too.</p></details>`;
}
let PNOPEN = false;
function drawPnav() {
  const nav = document.getElementById('pnav'); if (!nav) return;
  const N = pnavNeighbours(nav.dataset.code);
  nav.innerHTML = rend(html`${pnavLink(N.prev, 'prev')}${pnavLink(N.next, 'next')}`);
  const sum = document.getElementById('pn-sum'); if (sum) sum.textContent = filterWords();
  const pos = document.getElementById('pn-pos'); if (pos) pos.textContent = N.pos ? `plant ${N.pos} of ${N.n}` : `this plant is not in the filtered list (${N.n} of ${N.total})`;
  pnavLayout();
}
// on wide screens the two buttons sit in the empty margins either side of the page, halfway down; otherwise in a row at the top
function pnavLayout() {
  const nav = document.getElementById('pnav'); if (!nav) return;
  const r = document.documentElement, main = document.getElementById('app'), cs = getComputedStyle(main), mb = main.getBoundingClientRect();
  const pl = document.querySelector('.plant'), pb = pl && pl.getBoundingClientRect();     // the page content can be narrower than <main>
  const m = pb && pb.width ? { left: pb.left, right: pb.right } : { left: mb.left + parseFloat(cs.paddingLeft), right: mb.right - parseFloat(cs.paddingRight) };
  let lo = 0, hi = window.innerWidth;
  for (const id of ['sidenav', 'nav-tab']) {
    const el = document.getElementById(id); if (!el || !el.offsetWidth) continue;
    const b = el.getBoundingClientRect(); if (b.width >= window.innerWidth * 0.6) continue;
    if (b.right <= m.left + 4) lo = Math.max(lo, b.right); else if (b.left >= m.right - 4) hi = Math.min(hi, b.left);
  }
  const left = m.left - lo, right = hi - m.right, need = 150;
  const side = left >= need && right >= need && r.dataset.narrow !== '1';
  nav.classList.toggle('pn-side', side);
  if (side) {
    const w = Math.min(260, left - 24, right - 24);
    nav.style.setProperty('--pn-w', w + 'px');
    nav.style.setProperty('--pn-l', (lo + (left - w) / 2) + 'px');
    nav.style.setProperty('--pn-r', (window.innerWidth - hi + (right - w) / 2) + 'px');
  }
}
window.addEventListener('resize', () => pnavLayout());
// ---------- watering, care log and the Today page (added in 1.8.0) ----------
const CARE_WORD = { water: 'Watered', check: 'Checked: still moist', repot: 'Repotted', prune: 'Pruned', pests: 'Treated for pests', note: 'Note' };
function relDay(d) {
  if (!d) return '';
  const t = todayStr(), n = daysBetween(d, t);
  if (n === 0) return 'today'; if (n === 1) return 'yesterday'; if (n === -1) return 'tomorrow';
  const name = parseYmd(d).toLocaleDateString([], { weekday: 'long' }), md = parseYmd(d).toLocaleDateString([], { month: 'short', day: 'numeric' });
  if (n > 1 && n < 7) return 'last ' + name + ' (' + md + ')';
  if (n < -1 && n > -7) return name + ' (' + md + ')';
  return md;
}
function waterWords(w) {
  if (!w) return '';
  if (w.state === 'unknown') return 'No watering logged yet. Press Watered when you water it, and reminders start from there.';
  const od = w.overdue, when = od > 0 ? `${od} day${od === 1 ? '' : 's'} overdue (due ${relDay(w.next)})` : od === 0 ? 'due today' : `next check ${relDay(w.next)}`;
  const rain = w.last_rain && (!w.last_water || w.last_rain > w.last_water) ? ` Rain of ${w.rain_in} in ${relDay(w.last_rain)} was counted as a watering.` : '';
  const chk = w.last_check && w.last_check >= (w.last_water || '') && w.last_check >= (w.last_rain || '') ? ` Checked ${relDay(w.last_check)}: still moist.` : '';
  return `${when[0].toUpperCase() + when.slice(1)}. ${w.last_water ? 'Last watered ' + relDay(w.last_water) + '.' : 'No watering logged yet.'}${rain}${chk} Check about every ${w.every} day${w.every === 1 ? '' : 's'}: it ${w.why === 'set on this page' ? 'is set on this page' : w.why}${w.weather ? '; ' + w.weather : ''}.`;
}
function careQuick(p) {
  return html`<div class="quick noprint" role="group" aria-label="Quick care for this plant">
    <p class="quick-status" id="quick-status">&nbsp;</p>
    <div class="quick-btns">
      <button class="btn" type="button" data-act="care" data-kind="water" data-code="${p.code}" data-name="${p.common_name}">Watered today</button>
      <button class="btn ghost" type="button" data-act="care" data-kind="check" data-code="${p.code}" data-name="${p.common_name}">Checked: still moist</button>
      <button class="btn ghost" type="button" data-act="fertlog" data-code="${p.code}">Log feeding</button>
      <label class="btn ghost quick-photo">Add a photo<input type="file" accept="image/*" capture="environment" data-act="addphotos" class="sr"></label>
      <button class="btn ghost" type="button" data-act="careother" data-code="${p.code}" data-name="${p.common_name}">Log other care</button>
    </div>
    <p class="hint" id="water-done-note" hidden>Already watered today, so "Watered today" is off until tomorrow. To take it back, use Undo in the message, or Remove in the care log.</p></div>`;
}
async function loadCarePlant() {
  const box = document.getElementById('care-plant'); if (!box || !CUR) return;
  const code = CUR.p.code;
  let W, log;
  try { [W, log] = await Promise.all([api('GET', '/api/water'), api('GET', '/api/care?n=12&plant=' + enc(code))]); }
  catch (e) { box.innerHTML = rend(html`<p class="notice bad">Could not load the watering record: ${e.message}</p>`); return; }
  if (!CUR || CUR.p.code !== code) return;
  const w = W.plants.find(x => x.code === code);
  const qs = document.getElementById('quick-status'); if (qs) qs.textContent = w ? 'Water: ' + waterWords(w) : '';
  // 1.21.0: once watered today, "Watered today" is switched off until tomorrow (Undo or Remove in the care log switch it back on)
  const wb = document.querySelector('.quick-btns [data-act=care][data-kind=water]'), wn = document.getElementById('water-done-note');
  const done = !!(w && w.last_water === W.today);
  if (wb) { wb.disabled = done; wb.classList.toggle('done-today', done); wb.textContent = done ? '✓ Watered today' : 'Watered today'; }
  if (wn) wn.hidden = !done;
  box.innerHTML = rend(html`<div class="verdict-box v-${w && w.state === 'due' ? 'due' : 'wait'}" role="status"><h3>Watering</h3><p>${w ? waterWords(w) : ''}</p>
      <p class="hint">Change the gap with "Check for water every (days)" in Edit this page. Rain of ${W.rain_counts_in} in or more counts as a watering for plants whose Location is Outdoors.</p></div>
    <h3>Care log</h3>${log.length ? html`<ul class="care-log">${log.map(e => html`<li><strong>${CARE_WORD[e.kind] || e.kind}</strong> ${relDay(e.done_on)}${e.note ? ': ' + e.note : ''} <span class="muted">(${e.created_by})</span>
      <button class="btn small ghost noprint" type="button" data-act="caredel" data-id="${e.id}" data-what="${(CARE_WORD[e.kind] || e.kind) + ' ' + relDay(e.done_on)}">Remove</button></li>`)}</ul>`
      : html`<p class="muted">Nothing logged yet. Use the buttons near the top of the page.</p>`}`);
}
async function careDialog(code, name) {
  if (!(await needName())) return;
  const r = await modal(html`<form method="dialog"><h2>Log care for ${name}</h2>
    <label class="f">What did you do?<select name="kind"><optgroup label="Care">${Object.entries(CARE_WORD).filter(([k]) => !k.startsWith('prep_')).map(([k, v]) => html`<option value="${k}" ${k === 'repot' ? raw('selected') : ''}>${v}</option>`)}</optgroup>
      <optgroup label="Getting ready to come inside">${Object.entries(CARE_WORD).filter(([k]) => k.startsWith('prep_')).map(([k, v]) => html`<option value="${k}">${v}</option>`)}</optgroup></select></label>
    <label class="f">When<input type="date" name="day" value="${todayStr()}" max="${todayStr()}"></label>
    <label class="f">Note (optional)<input type="text" name="note" maxlength="500" placeholder="For example: moved to a 10 inch pot"></label>
    <div class="row"><button class="btn" value="ok">Save</button><button class="btn ghost" value="cancel">Cancel</button></div></form>`);
  if (r !== 'ok') return;
  const f = dlg.querySelector('form');
  await guard(async () => { const x = await api('POST', '/api/care', { plant: code, kind: f.elements.kind.value, done_on: f.elements.day.value, note: f.elements.note.value }); careUndoToast('Saved: ' + CARE_WORD[f.elements.kind.value] + ' for ' + name, x && x.ids, code); await careRefresh(code); });
}
async function careRefresh(code) {
  if (document.getElementById('care-plant')) return loadCarePlant();
  const y = window.scrollY; await route(); window.scrollTo(0, y);
  const f = (code && document.querySelector(`.job[data-code="${code}"] button`)) || document.querySelector('.job button') || document.querySelector('main h1');
  if (f) f.focus({ preventScroll: true });
}
function jobRow(p, words, btns) {
  return html`<li class="job" data-code="${p.code}">${p.photo ? html`<img src="${thumbUrl(p.photo)}" alt="" loading="lazy" width="64" height="64">` : html`<span class="job-nophoto" aria-hidden="true"></span>`}
    <div class="job-txt"><a class="nm" href="#/plant/${enc(p.code)}">${p.common_name}</a> <span class="muted">${p.code}</span><div>${words}</div></div>
    <div class="job-acts">${btns}</div></li>`;
}
// ---------- undo right after a care button (prototype: proto/undo-care) ----------
// "Watered", "Still moist", "Mark all as watered" and "Log other care" show a message with an Undo button instead of a
// plain toast. Undo removes exactly the entries that press made (by id), so nothing else in the care log is touched.
// The message stays for UNDO_SECS, and the countdown stops while the pointer or keyboard focus is on it. U also undoes.
const UNDO_SECS = 30;
let UNDO = null;      // {el, ids, code, left, timer}
function careUndoClose() {
  if (!UNDO) return;
  clearInterval(UNDO.timer); const el = UNDO.el, hadFocus = el.contains(document.activeElement); UNDO = null; el.remove();
  if (hadFocus) { const m = document.querySelector('main h1'); if (m) { m.setAttribute('tabindex', '-1'); m.focus({ preventScroll: true }); } }
}
function careUndoToast(msg, ids, code) {
  careUndoClose();
  if (!Array.isArray(ids) || !ids.length) { toast(msg); return; }
  const n = ids.length, el = document.createElement('div');
  el.className = 'toast undo-toast'; el.setAttribute('role', 'group'); el.setAttribute('aria-label', 'Care saved');
  el.innerHTML = rend(html`<span class="undo-msg" id="undo-msg">${msg}.</span>
    <span class="undo-acts"><button class="btn small" type="button" data-undo="undo" aria-describedby="undo-msg">Undo</button>
    <button class="btn small ghost" type="button" data-undo="close" aria-label="Close this message">Close</button></span>
    <span class="undo-left" aria-hidden="true"></span>`);
  document.getElementById('toasts').appendChild(el);
  UNDO = { el, ids: ids.slice(), code, left: UNDO_SECS, paused: 0, timer: 0 };
  const left = el.querySelector('.undo-left'), keys = window.PlantPrefs.get().keys === '1' && matchMedia('(any-pointer: fine)').matches;     // no key hint on a phone
  const paint = () => { left.textContent = (n > 1 ? `Undo removes all ${n} entries. ` : '') + `Closes in ${UNDO.left} s${keys ? ' (U undoes it)' : ''}.`; };
  paint();
  const hold = on => { if (UNDO && UNDO.el === el) UNDO.paused = Math.max(0, UNDO.paused + (on ? 1 : -1)); };
  el.addEventListener('pointerenter', () => hold(true)); el.addEventListener('pointerleave', () => hold(false));
  el.addEventListener('focusin', () => hold(true)); el.addEventListener('focusout', () => hold(false));
  UNDO.timer = setInterval(() => {
    if (!UNDO || UNDO.el !== el) return;
    if (UNDO.paused) return;
    UNDO.left -= 1; if (UNDO.left <= 0) careUndoClose(); else paint();
  }, 1000);
}
async function careUndo() {
  if (!UNDO) return;
  const { ids, code } = UNDO, btn = UNDO.el.querySelector('[data-undo=undo]');
  if (btn) btn.disabled = true;
  if (!(await needName())) { if (btn) btn.disabled = false; return; }
  let gone = 0, missing = 0;
  for (const id of ids) {
    try { await api('DELETE', '/api/care/' + id + '?undo=1'); gone++; }
    catch (e) { if (e.status === 404) missing++; else { toast('Could not undo: ' + e.message, true); break; } }
  }
  careUndoClose();
  if (gone) toast(gone === 1 ? 'Undone. The entry was removed from the care log.' : `Undone. ${gone} entries were removed from the care log.`);
  else if (missing) toast('Nothing to undo: someone already removed that entry.');
  await careRefresh(code);
}
document.getElementById('toasts').addEventListener('click', e => {      // its own listener, so this block needs nothing in acts
  const b = e.target.closest && e.target.closest('.undo-toast button'); if (!b) return;
  if (b.dataset.undo === 'undo') careUndo(); else if (b.dataset.undo === 'close') careUndoClose();
});
document.addEventListener('keydown', e => {
  if (!UNDO || (e.key !== 'u' && e.key !== 'U')) return;
  if (e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey || window.PlantPrefs.get().keys !== '1') return;
  if (e.target.closest && e.target.closest('input,textarea,select,[contenteditable="true"],dialog[open]')) return;
  e.preventDefault(); careUndo();
});
// ---------- getting plants ready to come inside (added in 1.9.0) ----------
// Ten ways to keep outdoor pests out of the house. The server rates each one for each plant (from its leaf type, pot
// size, the pests found, its health and the weather); this draws the plant page section, the Coming inside page and
// the Today page jobs, and logs each step to the care log as a "prep_" entry.
const PREP_CARE = { prep_inspect: 'Inspected for pests', prep_potclean: 'Cleaned the pot and saucer', prep_rinse: 'Rinsed with water', prep_wipe: 'Wiped the leaves',
  prep_soap: 'Sprayed insecticidal soap', prep_oil: 'Sprayed horticultural oil', prep_alcohol: 'Dabbed pests with rubbing alcohol', prep_soak: 'Soaked the pot',
  prep_topsoil: 'Refreshed the top of the soil', prep_repot: 'Repotted in fresh soil' };
Object.assign(CARE_WORD, PREP_CARE);          // the care log and "Log other care" know these steps too
const PR_SIGN = { 'Best': '★', 'Good': '✓', 'Use with care': '!', 'Not needed': '–', 'Not for this plant': '✕' };
const prBadge = r => html`<span class="pr-badge pr-${r.toLowerCase().replace(/\s+/g, '-')}"><span aria-hidden="true">${PR_SIGN[r] || ''}</span> ${r}</span>`;
const PREP = { data: null };
function prepMethodItem(m, n, code) {
  return html`<li class="pm" id="pm-${m.key}"><div class="pm-head"><h4 class="pm-title"><span class="pm-n">${n}.</span> ${m.title}</h4>${prBadge(m.rating)}</div>
    <p class="pm-why">${m.reason}</p>
    ${m.done.length ? html`<p class="pm-done"><strong>Done ${m.done.map(relDay).join(' and ')}.</strong>${m.next_due ? html` Round ${m.done.length + 1} is due ${relDay(m.next_due)}.` : ''}</p>` : ''}
    ${m.steps ? html`<details class="pm-steps"><summary>How to do it</summary><ol>${m.steps.map(s => html`<li>${s}</li>`)}</ol></details>` : ''}
    <p class="row pm-acts"><button class="btn small ${m.rank >= 3 && !m.complete ? '' : 'ghost'}" type="button" data-act="prepdone" data-code="${code}" data-k="${m.key}" aria-label="${m.title}: done today">Done today</button>
      ${m.done.length ? html`<button class="btn small ghost" type="button" data-act="prepundo" data-code="${code}" data-k="${m.key}" aria-label="${m.title}: undo the last one">Undo the last one</button>` : ''}</p></li>`;
}
function prepRender() {
  const box = document.getElementById('prep-box'), D = PREP.data; if (!box || !D || box.dataset.code !== D.code) return;
  const o = D.options, main = D.methods.filter(m => m.rank >= 2), rest = D.methods.filter(m => m.rank < 2), num = m => D.methods.indexOf(m) + 1;
  box.innerHTML = rend(html`
    ${D.winter_plan !== 'Move indoors' ? html`<p class="hint">Its winter plan is ${D.winter_plan}, so it usually stays outside. If you do bring it in, this is how.</p>` : ''}
    <div class="verdict-box pr-status" role="status"><p><strong>${D.status_word}.</strong> ${D.next}</p></div>
    <fieldset class="pr-traits"><legend>About this plant</legend>
      <p class="hint">These decide which methods suit it. Claude filled in the leaf type from the photos; change anything that is wrong.</p>
      <div class="field-grid">
        <label class="f">Leaf type<select data-act="preptrait" data-k="leaf_type"><option value="">Not set</option>${o.leaf_types.map(x => html`<option ${x === D.leaf_type ? raw('selected') : ''}>${x}</option>`)}</select></label>
        <label class="f">Pot size<select data-act="preptrait" data-k="pot_size"><option value="">Not set</option>${o.pot_sizes.map(x => html`<option ${x === D.pot_size ? raw('selected') : ''}>${x}</option>`)}</select></label>
      </div>
      <fieldset class="pr-pests"><legend>Pests you found</legend>
        <p class="hint">Tick what you see when you inspect it. Leave them all unticked if you found nothing.</p>
        <div class="pr-checks">${o.pests.map(x => html`<label class="chk"><input type="checkbox" data-act="preppest" value="${x}" ${D.pests_found.includes(x) ? raw('checked') : ''}>${x}</label>`)}</div>
      </fieldset>
      ${D.watch.length ? html`<details class="pr-watch"><summary>What this plant often gets (${D.watch.length})</summary><ul>${D.watch.map(x => html`<li>${x}</li>`)}</ul></details>` : ''}
      </fieldset>
    ${D.best.length ? html`<p><strong>Best for this plant:</strong> ${D.best.join(', ')}.</p>` : ''}
    <h3>Methods, in the order to do them</h3>
    <ul class="pm-list">${main.map(m => prepMethodItem(m, num(m), D.code))}</ul>
    ${rest.length ? html`<details class="pm-rest"><summary>${rest.length} more ${rest.length === 1 ? 'method is' : 'methods are'} not needed or not suitable for this plant</summary>
      <ul class="pm-list">${rest.map(m => prepMethodItem(m, num(m), D.code))}</ul></details>` : ''}
    <p class="hint">After it comes inside, keep it apart from your other houseplants for 3 weeks and check it at every watering. <a href="#/inside">See every plant that is coming inside</a>.</p>`);
}
async function loadPrep(box) {
  try { PREP.data = await api('GET', '/api/plants/' + enc(box.dataset.code) + '/prep'); }
  catch (e) { box.innerHTML = rend(html`<p class="notice bad">Could not load this: ${e.message}</p>`); return; }
  prepRender();
  let jump = null; try { jump = sessionStorage.getItem('plantdb.toprep'); sessionStorage.removeItem('plantdb.toprep'); } catch (e) { /* none */ }
  if (jump === box.dataset.code) {          // from "Open its plan": go to this section, again once the page has settled
    const to = () => { const s = document.getElementById('inside'); if (s) scrollToSection(s); };
    to(); setTimeout(to, 600); setTimeout(to, 1500);
  }
}
new MutationObserver(() => { const b = document.getElementById('prep-box'); if (b && !b.dataset.loaded) { b.dataset.loaded = '1'; loadPrep(b); } })
  .observe(document.getElementById('app'), { childList: true });
async function prepAfterChange(code, focusSel) {      // redraw whatever page is showing, and put focus back where it was
  if (document.getElementById('prep-box')) {
    try { PREP.data = await api('GET', '/api/plants/' + enc(code) + '/prep'); } catch (e) { toast(e.message, true); return; }
    prepRender(); if (document.getElementById('care-plant')) loadCarePlant();
  } else { const y = window.scrollY; await route(); window.scrollTo(0, y); }
  const f = focusSel && document.querySelector(focusSel); if (f) f.focus({ preventScroll: true });
}
async function prepSaveTraits(body, focusSel, said) {
  if (!(await needName())) { prepRender(); return; }
  await guard(async () => {
    const r = await api('POST', '/api/plants/' + enc(PREP.data.code) + '/prep-traits', body);
    PREP.data = r; if (CUR && CUR.p && CUR.p.code === r.code) { CUR.p.version = r.version; Object.assign(CUR.p, { leaf_type: r.leaf_type, pot_size: r.pot_size }); }
    prepRender(); toast(said);
    const f = document.querySelector(focusSel); if (f) f.focus({ preventScroll: true });
  });
}
function prepWords(p) {
  const t = [p.leaf_type || 'leaf type not set', p.pot_size ? p.pot_size.split(':')[0].toLowerCase() + ' pot' : 'pot size not set',
    p.pests_found.length ? 'found: ' + p.pests_found.join(', ').toLowerCase() : ''].filter(Boolean).join('; ');
  return html`${p.next}<br><span class="pr-sub">${t.charAt(0).toUpperCase() + t.slice(1)}. Best: ${p.best.join(', ').toLowerCase()}.</span>`;
}
async function viewInside() {
  const D = await api('GET', '/api/prep');
  const c = D.counts, w = D.status_words;
  const groups = ['doing', 'todo', 'ready', 'apart', 'settled'].map(k => [k, D.plants.filter(p => p.status === k)]).filter(g => g[1].length);
  const open = p => html`<button class="btn small ghost" type="button" data-act="openprep" data-code="${p.code}">Open its plan</button>`;
  const say = ['todo', 'doing', 'ready', 'apart', 'settled'].filter(k => c[k]).map(k => `${c[k]} ${w[k].toLowerCase()}`).join(', ');
  return {
    title: 'Getting plants ready to come inside',
    html: html`<p class="crumb"><a href="#/winter">Winter plan</a></p><h1>Getting plants ready to come inside</h1>
    <p class="muted">Ten ways to keep ants, mites and other outdoor pests out of the house, and where each plant that is coming inside is up to. Each plant's page rates the methods for that plant, with the steps.</p>
    <div class="verdict-box" role="status"><p><strong>${D.plants.length} ${D.plants.length === 1 ? 'plant' : 'plants'} coming inside:</strong> ${say || 'none yet'}.</p>${D.weather.spray ? html`<p>${D.weather.spray}</p>` : ''}</div>
    <section class="blk" id="in-order"><h2>The order of work</h2><ol class="steps">
      <li>Outdoors, a week or two before the move, inspect each plant and tick what you find on its page.</li>
      <li>Clean its pot, then do the methods rated Best for it.</li>
      <li>If you found pests, spray again 5 to 7 days later. The Today page reminds you.</li>
      <li>Bring it inside and change its Location to Indoors (or press Moved indoors).</li>
      <li>Keep it apart from your other houseplants for ${D.keep_apart_days} days, with yellow sticky traps nearby, and check it at every watering.</li></ol></section>
    ${groups.map(([k, list]) => html`<section class="blk" id="in-${k}"><h2>${w[k]} (${list.length})</h2>
      <ul class="jobs">${list.map(p => jobRow({ code: p.code, common_name: p.name, photo: p.photo }, prepWords(p), open(p)))}</ul></section>`)}
    <section class="blk" id="in-methods"><h2>How to do each method</h2>
      <p class="hint">Not every method suits every plant: open a plant's plan to see which are best for it.</p>
      ${D.methods.map((m, i) => html`<details class="pm-steps pm-ref"><summary>${i + 1}. ${m.title}</summary><ol>${m.steps.map(s => html`<li>${s}</li>`)}</ol></details>`)}</section>
    <section class="blk" id="in-apart"><h2>Keeping them apart</h2>
      <p>Pests often show up a week or two after the first treatment, when eggs hatch. So keep the plants that came in away from your long-term houseplants for ${D.keep_apart_days} days, and for 2 weeks after the last treatment if you found pests.</p>
      <ul><li>Give any plant where you found pests its own "hospital" spot until two weekly checks come up clean.</li>
        <li>Put yellow sticky traps beside each group. They catch fungus gnats, whiteflies and thrips, and show whether there are more or fewer each week.</li>
        <li>Spider mites thrive in dry indoor air, so a humidifier helps the palms, calathea and alocasias.</li>
        <li>Water less indoors, and let the top of the soil dry between waterings, so fungus gnats have nowhere to breed.</li>
        <li>Predatory mites, sold online, eat spider mites indoors if they come back.</li></ul></section>`,
  };
}
function todayPrep(PR, t) {
  const again = [], free = [];
  PR.plants.forEach(p => { p.methods.forEach(m => { if (m.next_due && m.next_due <= t) again.push({ p, m }); }); if (p.status === 'apart' && p.keep_until && p.keep_until <= t) free.push(p); });
  const c = PR.counts, w = PR.status_words;
  const say = ['todo', 'doing', 'ready', 'apart'].filter(k => c[k]).map(k => `${c[k]} ${w[k].toLowerCase()}`).join(', ');
  const row = (p, words, btns) => jobRow({ code: p.code, common_name: p.name, photo: p.photo }, words, btns);
  return html`<section class="blk" id="today-inside"><h2>Getting ready to come inside (${again.length + free.length})</h2>
    <p>${PR.plants.length} coming inside${say ? ': ' + say : ''}. <a href="#/inside">Open the list</a></p>
    ${again.length ? html`<ul class="jobs">${again.map(({ p, m }) => row(p, html`${m.title}, round ${m.done.length + 1}. The last round was ${relDay(m.done[m.done.length - 1])}.`,
      html`<button class="btn small" type="button" data-act="prepdone" data-code="${p.code}" data-k="${m.key}" aria-label="${p.name}: ${m.title.toLowerCase()} done today">Done today</button>`))}</ul>` : ''}
    ${free.length ? html`<ul class="jobs">${free.map(p => row(p, 'Its 3 weeks apart end today. If you have seen no pests, it can join your other houseplants.', html`<a class="btn small ghost" href="#/plant/${enc(p.code)}">Open its page</a>`))}</ul>` : ''}
    ${!again.length && !free.length ? html`<p class="notice ok">No sprays due and nobody to move today.</p>` : ''}</section>`;
}
async function viewToday() {
  const [W, reqs, , PR] = await Promise.all([api('GET', '/api/water'), api('GET', '/api/requests?open=1'), loadFertData(true), api('GET', '/api/prep').catch(() => null)]);
  const by = Object.fromEntries(FERT.plants.map(p => [p.code, p])), t = todayStr();
  const ws = W.plants.filter(w => by[w.code]);
  const due = ws.filter(w => w.state === 'due').sort((a, b) => b.overdue - a.overdue), soon = ws.filter(w => w.state === 'soon'), unk = ws.filter(w => w.state === 'unknown');
  const feed = FERT.plants.map(p => ({ p, st: fertState(p, entriesFor(p.code), t, fertCtx()) })).filter(r => r.st.state === 'due');
  const needs = FERT.plants.filter(needsYou);
  const wbtn = w => html`<button class="btn small" type="button" data-act="care" data-kind="water" data-code="${w.code}" data-name="${by[w.code].common_name}">Watered</button>
    <button class="btn small ghost" type="button" data-act="care" data-kind="check" data-code="${w.code}" data-name="${by[w.code].common_name}">Still moist</button>`;
  const n = (k, one, many) => k + ' ' + (k === 1 ? one : many);
  return {
    title: 'Today',
    html: html`<h1>Today</h1><p class="muted">${longDay(t)}. Watering, feeding and anything Claude has asked you for, most urgent first.</p>
    <div class="verdict-box" role="status"><p><strong>${n(due.length, 'plant to water', 'plants to water')}, ${n(feed.length, 'to feed', 'to feed')}, and ${n(needs.length, 'plant that needs something from you', 'plants that need something from you')}.</strong>
      ${W.avg_high != null ? `Highs have been about ${W.avg_high}°F lately.` : ''} ${Object.keys(W.rain).length ? `Rain counted as watering for plants out in the open: ${Object.entries(W.rain).slice(-3).map(([d, i]) => relDay(d) + ', ' + i + ' in').join('; ')}.` : ''}</p></div>
    <section class="blk" id="today-water"><h2>Water (${due.length})</h2>
      ${due.length ? html`${due.length > 1 ? html`<p><button class="btn small ghost" type="button" data-act="careall" data-kind="water" data-codes="${due.map(w => w.code).join(',')}">Watered all ${due.length}</button></p>` : ''}
        <ul class="jobs">${due.map(w => jobRow(by[w.code], waterWords(w), wbtn(w)))}</ul>` : html`<p class="notice ok">Nothing is due for water today.</p>`}
      ${soon.length ? html`<details class="grp"><summary><h3>Check tomorrow (${soon.length})</h3></summary><ul class="jobs">${soon.map(w => jobRow(by[w.code], waterWords(w), wbtn(w)))}</ul></details>` : ''}
      ${unk.length ? html`<details class="grp"><summary><h3>No watering logged yet (${unk.length})</h3></summary>
        <p class="hint">These have no watering in the log and no rain counted, so there is no reminder for them yet. If you water everything on a round, press the button to start the clock for all of them at once.</p>
        <p><button class="btn small ghost" type="button" data-act="careall" data-kind="water" data-codes="${unk.map(w => w.code).join(',')}">I watered all ${unk.length} today</button></p>
        <ul class="jobs">${unk.map(w => jobRow(by[w.code], w.site !== 'Outdoors' ? w.site + '.' : 'Outdoors.', wbtn(w)))}</ul></details>` : ''}</section>
    <section class="blk" id="today-feed"><h2>Feed (${feed.length})</h2>
      ${feed.length ? html`${feed.length > 1 ? html`<p><button class="btn small ghost" type="button" data-act="fertlog" data-group="due">Log feeding for all ${feed.length}</button></p>` : ''}
        <ul class="jobs">${feed.map(r => jobRow(r.p, fertWords(r.p, r.st, t), html`<button class="btn small" type="button" data-act="fertlog" data-code="${r.p.code}">Log feeding</button>`))}</ul>`
        : html`<p class="notice ok">No plant is due for fertilizer today. The Fertilizer page has the calendar.</p>`}</section>
    ${PR && PR.plants.length ? todayPrep(PR, t) : ''}
    <section class="blk" id="today-needs"><h2>Needed from you (${needs.length})</h2>
      ${reqs.length ? html`<ul class="jobs">${reqs.slice(0, 8).map(q => { const p = by[q.plant_code] || { code: q.plant_code || '', common_name: q.plant_code || 'General' };
        return jobRow(p, linkify(q.text), p.code ? html`<a class="btn small ghost" href="#/plant/${enc(p.code)}">Answer on its page</a>` : ''); })}</ul>
        ${reqs.length > 8 ? html`<p class="hint">Showing 8 of ${reqs.length} open requests.</p>` : ''}` : ''}
      <p><button class="btn small ghost" type="button" data-act="todayneeds">Show all plants that need something from you</button></p></section>`,
    after: () => document.querySelectorAll('[data-nav]').forEach(a => { if (a.dataset.nav === 'today') a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); }),
  };
}
const KIND_WORD = { check: 'Check', question: 'Question', photo: 'Photo', info: 'Information' };
function needsBox(p) {
  const open = (p.requests || []).filter(r => !r.done), done = (p.requests || []).filter(r => r.done);
  const low = p.id_confidence != null && p.id_confidence < 70;
  if (!open.length && !low && !done.length) return '';
  return html`<section class="needs" id="needs" aria-labelledby="h-needs"><h2 id="h-needs">${open.length || low ? 'Needed from you' : 'Requests (all answered)'}</h2>
    ${open.length ? html`<ul class="needs-list">${open.map(r => html`<li><span class="kind">${KIND_WORD[r.kind] || 'Request'}</span><span class="txt">${linkify(r.text)}</span>
      <span class="row"><button class="btn small" type="button" data-act="reqanswer" data-id="${r.id}">Answer</button><button class="btn small ghost" type="button" data-act="reqdone" data-id="${r.id}">Mark done</button></span></li>`)}</ul>` : ''}
    ${low ? html`<p class="needs-id"><span class="kind">ID info</span> The identification is ${p.id_confidence}% sure. ${lines(p.id_improve).length ? html`To raise it, send: ${lines(p.id_improve).join('; ')}.` : 'A clear photo of the tag or a flower would help.'} <a href="#ident" data-act="jump" data-id="ident">See Plant identification</a></p>` : ''}
    ${done.length ? html`<details class="needs-done"><summary>${done.length} answered</summary><ul>${done.map(r => html`<li>${r.text}<br><span class="hint">${r.answer ? 'Answer: ' + r.answer + '. ' : ''}${r.done_by || ''} ${r.done_at ? when(r.done_at) : ''}</span>
      <button class="btn small ghost" type="button" data-act="reqreopen" data-id="${r.id}">Reopen</button></li>`)}</ul></details>` : ''}
    <p class="hint">Answers are saved on this page and in the change log. To send them to Claude, press Copy my answers for Claude and paste the message into the chat.</p>
    <p class="noprint"><button class="btn small" type="button" data-act="forclaude">Copy my answers for Claude</button></p></section>`;
}
// ---------- copy my answers for Claude (added in 1.8.0) ----------
const FC = { range: 'last', open: false, data: null };
const FC_RANGES = [['last', 'Since I last copied'], ['7', 'The last 7 days'], ['30', 'The last 30 days'], ['all', 'Everything']];
const fcPl = (n, one, many) => `${n} ${n === 1 ? one : many}`;
async function fcLoad() { FC.data = await api('GET', `/api/for-claude?range=${FC.range}&open=${FC.open ? 1 : 0}`); return FC.data; }
function fcWords(n) {
  const w = [];
  if (n.answers) w.push(fcPl(n.answers, 'answer', 'answers'));
  if (n.pages) w.push(fcPl(n.pages, 'change to a plant page', 'changes to plant pages'));
  if (n.photos) w.push('photo changes on ' + fcPl(n.photos, 'page', 'pages'));
  if (n.care) w.push(fcPl(n.care, 'feeding or care entry', 'feeding or care entries'));
  if (n.todo) w.push(fcPl(n.todo, 'change', 'changes') + ' to the "Still to photograph" list');
  return w.length ? w.join(', ') : 'nothing new in that time';
}
function fcBox(D) {
  const last = D.last_copied ? `Since I last copied (${D.last_copied_words})` : 'Since I last copied (never)';
  return html`<div class="fc-pick">
      <label class="f">What to include<select data-act="fcrange">${FC_RANGES.map(([k, w]) => html`<option value="${k}" ${FC.range === k ? raw('selected') : ''}>${k === 'last' ? last : w}</option>`)}</select></label>
      <label class="chk"><input type="checkbox" data-act="fcopen" ${FC.open ? raw('checked') : ''}>Also list what is still open</label></div>
    <p class="fc-sum"><strong>In this message:</strong> ${fcWords(D.counts)}.</p>
    <label class="f">The message<textarea id="fc-text" readonly rows="12" spellcheck="false">${D.text}</textarea></label>`;
}
const fcSay = msg => { const s = document.getElementById('fc-status'); if (s) s.textContent = msg; };
async function forClaudeDialog() {
  if (!(await needName())) return;                          // copying is noted in the change log, under your name
  FC.range = 'last';
  try { await fcLoad(); } catch (e) { toast('Could not gather your answers: ' + e.message, true); return; }
  await modal(html`<form method="dialog" class="fc"><h2>Copy my answers for Claude</h2>
    <p>One message with everything you have done in Plant record: your answers first, then changes to plant pages, photos, feeding and care. Copy it, then paste it into your chat with Claude.</p>
    <div id="fc-box">${fcBox(FC.data)}</div>
    <p id="fc-status" class="fc-status" role="status" aria-live="polite"></p>
    <div class="row"><button class="btn" type="button" data-act="fccopy" autofocus>Copy message</button>
      <button class="btn ghost" type="button" data-act="fcsave">Save as a text file</button>
      <button class="btn ghost" value="close">Close</button></div></form>`);
}
async function fcRefresh(focusSel) {
  const box = document.getElementById('fc-box'); if (!box) return;
  try { await fcLoad(); } catch (e) { fcSay('Could not gather your answers: ' + e.message); return; }
  box.innerHTML = rend(fcBox(FC.data)); fcSay('');
  const f = focusSel && box.querySelector(focusSel); if (f) f.focus();
}
async function fcMark() {
  if (!FC.data) return;
  try {
    const r = await api('POST', '/api/for-claude/copied', { until: FC.data.until });
    FC.data.last_copied = r.last_copied; FC.data.last_copied_words = r.last_copied_words;
    document.querySelectorAll('.fc-n').forEach(x => x.remove());          // the "(2 new)" on the Plants page
  } catch (e) { /* the message is copied either way */ }
}
function fitPanes() {
  const pl = document.querySelector('.plant');
  if (!pl) return;
  const r = document.documentElement;
  if (r.dataset.layout === 'single' || r.dataset.narrow === '1') { pl.style.removeProperty('--pane-h'); return; }
  const topAbs = pl.getBoundingClientRect().top + window.scrollY;
  const con = r.dataset.console === '1' ? (parseFloat(getComputedStyle(r).getPropertyValue('--console-space')) || 0) : 0;   // room for the audit log console
  const h = Math.max(window.innerHeight - topAbs - 12 - con, 360);      // the two halves fill the window exactly, so the page itself never scrolls
  pl.style.setProperty('--pane-h', h + 'px');
}
function repaintPhotos() { const el = document.getElementById('photopanel'); if (el) el.innerHTML = rend(photoPanel(CUR.p)); }
async function reloadPlant(idx) { KEEP = idx == null ? PIDX : idx; await route(); }
const curPhoto = () => CUR.p.photos[clamp(PIDX, 0, CUR.p.photos.length - 1)];

// ---------- plant page: the row of section buttons steps aside while the On this page menu is open (added in 1.8.0) ----------
// The CSS hides the row then; this keeps --jump-h (used by the sticky section titles) right when the menu opens or closes.
new MutationObserver(() => document.querySelectorAll('.pane').forEach(p => { const j = p.querySelector('.jump'); p.style.setProperty('--jump-h', (j ? j.offsetHeight : 0) + 'px'); }))
  .observe(document.documentElement, { attributes: true, attributeFilter: ['data-navopen', 'data-narrow', 'data-layout'] });
// ---------- dates ----------
const pad2 = n => String(n).padStart(2, '0');
const ymd = d => d.getFullYear() + '-' + pad2(d.getMonth() + 1) + '-' + pad2(d.getDate());
const parseYmd = s => { const [y, m, d] = s.split('-').map(Number); return new Date(y, m - 1, d, 12); };   // noon, so daylight-saving shifts never move the date
const addDays = (s, n) => { const d = parseYmd(s); d.setDate(d.getDate() + n); return ymd(d); };
const daysBetween = (a, b) => Math.round((parseYmd(b) - parseYmd(a)) / 86400000);
const longDay = s => parseYmd(s).toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
const midDay = s => parseYmd(s).toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' });
const MONTHN = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const MN = MONTHN.map(m => m.slice(0, 3));
const DOWN = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
function todayStr() {           // today at the place in use, not in the browser's time zone, so care dates match the server's
  try { if (META && META.home_tz) return new Intl.DateTimeFormat('en-CA', { timeZone: META.home_tz, year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date()); } catch (e) { /* unknown zone */ }
  return ymd(new Date());
}

// ---------- calendar (month grid, with a list version for narrow screens and big text) ----------
const CALS = {};
function calView() {
  let v = null; try { v = localStorage.getItem('plantdb.calview'); } catch (e) { /* ignore */ }
  return v === 'grid' || v === 'list' ? v : (document.documentElement.dataset.narrow === '1' ? 'list' : 'grid');
}
function calHtml(id) {
  const c = CALS[id], [Y, M] = c.month.split('-').map(Number), n = new Date(Y, M, 0).getDate(), dow = new Date(Y, M - 1, 1).getDay();
  const today = todayStr();
  const days = Array.from({ length: n }, (_, i) => Y + '-' + pad2(M) + '-' + pad2(i + 1));
  const focus = days.includes(c.sel) ? c.sel : days.includes(today) ? today : days[0];
  const info = Object.fromEntries(days.map(d => [d, c.cfg.cell(d, c)]));
  const label = d => `${longDay(d)}${d === today ? ', today' : ''}. ${info[d].aria || 'Nothing recorded.'}`;
  const cells = [...Array(dow).fill(null), ...days];
  while (cells.length % 7) cells.push(null);
  const weeks = []; for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7));
  const bad = (b, k) => html`<span class="bd ${b.cls || ''}">${b.text}</span>`;
  const view = c.view || calView();
  return html`<div class="cal-wrap" data-view="${view}">
    <div class="cal-nav noprint"><button type="button" class="btn ghost small" data-act="calnav" data-cal="${id}" data-d="-1" aria-label="Previous month">◀ Previous</button>
      <h3 id="calh-${id}" aria-live="polite">${MONTHN[M - 1]} ${Y}</h3>
      <button type="button" class="btn ghost small" data-act="calnav" data-cal="${id}" data-d="1" aria-label="Next month">Next ▶</button>
      <button type="button" class="btn ghost small" data-act="calnav" data-cal="${id}" data-d="0">Today</button>
      <button type="button" class="btn ghost small" data-act="calview" data-cal="${id}">${view === 'grid' ? 'Show as a list' : 'Show as a grid'}</button></div>
    ${c.loading ? html`<p class="loading">Loading</p>` : ''}
    <table class="cal" aria-labelledby="calh-${id}"><thead><tr>${DOWN.map(d => html`<th scope="col"><abbr title="${d}">${d.slice(0, 3)}</abbr></th>`)}</tr></thead>
      <tbody>${weeks.map(w => html`<tr>${w.map(d => d ? html`<td><button type="button" class="day ${info[d].cls || ''} ${d === c.sel ? 'sel' : ''} ${d === today ? 'today' : ''}" data-act="calpick" data-cal="${id}" data-date="${d}"
          tabindex="${d === focus ? 0 : -1}" aria-pressed="${String(d === c.sel)}" aria-label="${label(d)}">
          <span class="dn">${+d.slice(8)}${d === today ? html` <span class="tdy">today</span>` : ''}</span>${(info[d].badges || []).map(bad)}</button></td>` : html`<td></td>`)}</tr>`)}</tbody></table>
    <ul class="cal-list">${days.map(d => html`<li><button type="button" class="day ${info[d].cls || ''} ${d === c.sel ? 'sel' : ''} ${d === today ? 'today' : ''}" data-act="calpick" data-cal="${id}" data-date="${d}" aria-pressed="${String(d === c.sel)}" aria-label="${label(d)}">
        <span class="dn">${midDay(d)}${d === today ? ' (today)' : ''}</span><span class="bds">${(info[d].badges || []).map(bad)}</span></button></li>`)}</ul>
    ${c.cfg.legend ? html`<p class="hint cal-legend">${c.cfg.legend}</p>` : ''}</div>`;
}
function calRender(id, keepFocus) {
  const el = document.getElementById('cal-' + id); if (!el) return;
  el.innerHTML = rend(calHtml(id));
  if (keepFocus) { const b = el.querySelector(`.cal .day[data-date="${keepFocus}"]`); if (b) b.focus(); }
}
async function calMount(id, cfg, month, sel) {
  const c = CALS[id] = { id, cfg, month: month || (sel || todayStr()).slice(0, 7), sel: sel || null, data: {}, loading: false };
  await calLoad(id);
}
async function calLoad(id) {
  const c = CALS[id]; if (!c) return;
  if (c.cfg.load) { c.loading = true; calRender(id); try { await c.cfg.load(c.month, c); } catch (e) { toast(e.message, true); } c.loading = false; }
  calRender(id);
}
async function calGo(id, date, focus) {
  const c = CALS[id]; if (!c) return;
  const m = date.slice(0, 7);
  c.sel = date;
  if (m !== c.month) { c.month = m; await calLoad(id); } else calRender(id, focus ? date : null);
  if (focus) calRender(id, date);
  if (c.cfg.pick) c.cfg.pick(date, c);
}
function calNav(id, d) {
  const c = CALS[id]; if (!c) return;
  if (d === 0) { c.month = todayStr().slice(0, 7); c.sel = todayStr(); calLoad(id).then(() => c.cfg.pick && c.cfg.pick(c.sel, c)); return; }
  const [Y, M] = c.month.split('-').map(Number), n = new Date(Y, M - 1 + d, 1);
  c.month = n.getFullYear() + '-' + pad2(n.getMonth() + 1);
  calLoad(id);
}
const LEVELBD = { ok: ['s-ok', '✔ In range'], near: ['s-near', '▲ A little out'], bad: ['s-bad', '■ Out of range'], danger: ['s-danger', '✖ Danger'], info: ['s-none', 'No range set'] };

// ---------- feeding season and verdict ----------
const hasSeason = p => has(p.fert_from_month) && has(p.fert_to_month) && has(p.fert_every_days);
const monthIn = (p, m) => p.fert_from_month <= p.fert_to_month ? (m >= p.fert_from_month && m <= p.fert_to_month) : (m >= p.fert_from_month || m <= p.fert_to_month);
const seasonText = p => hasSeason(p) ? `${MONTHN[p.fert_from_month - 1]} to ${MONTHN[p.fert_to_month - 1]}, about every ${p.fert_every_days} days` : 'No feeding season set';
function nextSeasonStart(p, ds) {
  let d = ds;
  for (let i = 0; i < 14; i++) {
    if (monthIn(p, +d.slice(5, 7))) return d;
    const [Y, M] = d.split('-').map(Number), n = new Date(Y, M, 1, 12);
    d = ymd(n);
  }
  return ds;
}
const lastFed = (entries, ds) => entries.find(e => e.applied_on <= ds) || null;       // entries are newest first
function nextDue(p, entries) {
  if (!hasSeason(p)) return null;
  const last = entries[0], t = todayStr();
  let base = last ? addDays(last.applied_on, +p.fert_every_days) : t;
  if (base < t) base = t;
  return nextSeasonStart(p, base);
}
function holdReason(p, ds, ctx) {
  const t = todayStr();
  if (ds < t) return null;
  if (ds === t && (p.health_rating === 'Poor' || p.health_rating === 'Critical'))
    return `This plant's health is rated ${p.health_rating}. Fix the problem first (see Health below). Fertilizer on a stressed plant makes it worse.`;
  const lim = has(p.temp_damage_below) ? +p.temp_damage_below : 35;
  const fc = ((ctx && ctx.forecast) || []).filter(d => d.date >= ds && d.date <= addDays(ds, 2));
  const cold = fc.filter(d => d.low <= lim).sort((a, b) => a.low - b.low)[0];
  if (cold) return `A cold night is forecast (${cold.low}°F on ${midDay(cold.date)}), at or below the damage point for this plant (${lim}°F). Wait until it passes.`;
  return null;
}
function fertState(p, entries, ds, ctx) {
  if (!hasSeason(p)) return { state: 'unknown' };
  const every = +p.fert_every_days, last = lastFed(entries, ds), since = last ? daysBetween(last.applied_on, ds) : null;
  const nxt = last ? nextSeasonStart(p, addDays(last.applied_on, every)) : null;
  if (last && since === 0) return { state: 'fed', last, since, next: nxt };
  if (!monthIn(p, +ds.slice(5, 7))) return { state: 'rest', until: nextSeasonStart(p, ds), last, since };
  if (last && since < every) return { state: 'wait', last, since, next: nxt };
  const hold = holdReason(p, ds, ctx);
  const over = last ? since - every : null;
  return hold ? { state: 'hold', reason: hold, last, since } : { state: 'due', last, since, over };
}
const FS = { due: ['▲', 'Time to fertilize', 'st-near'], hold: ['■', 'Hold off', 'st-bad'], wait: ['✔', 'Fed recently', 'st-ok'], fed: ['✔', 'Fed today', 'st-ok'], rest: ['—', 'Resting, do not fertilize', 'st-mute'], unknown: ['?', 'No feeding season set', 'st-mute'] };
function fertWords(p, st, ds) {
  const day = ds === todayStr() ? 'today' : 'on this date', every = p.fert_every_days;
  const prod = st.last ? ` (${st.last.product})` : '';
  switch (st.state) {
    case 'rest': return `Growth is slow or stopped in these months, so fertilizer would only build up salts in the mix. Do not fertilize ${day}. This plant's feeding season is ${seasonText(p)}; it opens again ${longDay(st.until)}.`;
    case 'fed': return `Fed ${day}${prod}. The next feeding is about ${longDay(st.next)}.`;
    case 'wait': return `Last fed ${st.since} day${st.since === 1 ? '' : 's'} before this date${prod}. Feed about every ${every} days, so wait until ${longDay(st.next)}.`;
    case 'hold': return st.reason;
    case 'due': return `${st.last ? `Last fed ${st.since} days before this date${prod}, and this plant likes feeding about every ${every} days${st.over > 0 ? `, so it is ${st.over} day${st.over === 1 ? '' : 's'} overdue` : ''}.` : 'No feeding is recorded for it yet.'} Water lightly first if the mix is dry, then use the product at the strength on its label (half strength is safer).`;
    default: return 'Open Edit and fill in "Feed from month", "Feed through month" and "Feed every (days)" in the Nutrients group to get a calendar for this plant.';
  }
}
const verdictLine = (p, st) => html`<span class="${FS[st.state][2]}">${FS[st.state][0]} ${FS[st.state][1]}</span>`;

// ---------- fertilizer amount maths (same as the server) ----------
const WATER_L = { L: 1, gal: 3.78541, qt: 0.946353, cup: 0.236588 };
function fertCalc(form, n, p, k, amount, unit, water, wunit) {
  const out = { ppm_n: null, ppm_p2o5: null, ppm_k2o: null, n_grams: null, g: null };
  if (!amount || !unit) return out;
  const liquid = ['liquid', 'organic liquid', 'foliar spray'].includes(form);
  const g = { g: amount, oz: amount * 28.3495, ml: amount, 'fl oz': amount * 29.5735, tsp: amount * (liquid ? 4.92892 : 4), tbsp: amount * (liquid ? 14.7868 : 12) }[unit];
  if (g == null) return out;
  out.g = g;
  if (n != null) out.n_grams = Math.round(g * n / 100 * 1000) / 1000;
  const L = water && WATER_L[wunit] ? water * WATER_L[wunit] : null;
  if (L) for (const [key, pct] of [['ppm_n', n], ['ppm_p2o5', p], ['ppm_k2o', k]]) if (pct != null) out[key] = Math.round(g * pct / 100 * 1000 / L * 10) / 10;
  return out;
}
const npkText = e => ['n', 'p', 'k'].map(x => e[x] == null ? '?' : fmt(e[x], 2)).join('-');
const doseText = e => e.amount == null ? 'amount not noted' : `${fmt(e.amount, 2)} ${e.amount_unit}${e.water_amount ? ' in ' + fmt(e.water_amount, 2) + ' ' + e.water_unit + ' of water' : ''}`;
const ratioText = (n, p, k) => {
  const v = [n, p, k].map(x => +x || 0), m = Math.min(...v.filter(x => x > 0));
  return m && isFinite(m) ? v.map(x => (Math.round(x / m * 10) / 10)).join(' : ') : '';
};

// ---------- fertilizer data shared by the plant page and the Fertilizer page ----------
const FERT = { entries: [], products: [], plants: [], forecast: [], needs: {} };
async function loadFertData(withPlants) {
  const [entries, products, W] = await Promise.all([api('GET', '/api/fertilizer'), api('GET', '/api/fertilizer/products'), api('GET', '/api/weather').catch(() => null)]);
  FERT.entries = entries; FERT.products = products; FERT.forecast = (W && W.forecast && W.forecast.days) || [];
  if (withPlants) { FERT.needs = {}; await Promise.all([api('GET', '/api/plants').then(x => { FERT.plants = x; }), loadNeeds()]); }
}
const entriesFor = code => FERT.entries.filter(e => e.plant_code === code);
const fertCtx = () => ({ forecast: FERT.forecast });

function entryRows(list, plantsByCode, showPlant) {
  if (!list.length) return html`<p class="muted">Nothing logged yet.</p>`;
  return html`<div class="tbl-wrap"><table class="tbl"><caption class="sr">Fertilizer entries</caption><thead><tr><th>Date</th>${showPlant ? html`<th>Plant</th>` : ''}<th>Fertilizer</th><th>N-P-K</th><th>Amount</th><th class="num">About ppm N</th><th>How</th><th class="noprint"><span class="sr">Actions</span></th></tr></thead><tbody>
    ${list.map(e => html`<tr><th scope="row">${midDay(e.applied_on)}</th>${showPlant ? html`<td><a href="#/plant/${enc(e.plant_code)}">${(plantsByCode[e.plant_code] || {}).common_name || e.plant_code}</a></td>` : ''}
      <td>${e.product}${e.note ? html`<div class="hint">${e.note}</div>` : ''}</td><td>${npkText(e)}</td><td>${doseText(e)}</td><td class="num">${e.ppm_n == null ? '' : fmt(e.ppm_n, 0)}</td><td>${e.method}</td>
      <td class="noprint"><button class="btn ghost small" type="button" data-act="fertedit" data-id="${e.id}">Change</button> <button class="btn danger small" type="button" data-act="fertdel" data-id="${e.id}">Remove</button></td></tr>`)}</tbody></table></div>`;
}

// ---------- what each plant needs, and the closest fertilizer you have (1.11.0) ----------
const FZQ = { 'Matches': ['✔', 'q-good'], 'Close': ['✔', 'q-good'], 'Usable': ['▲', 'q-ok'], 'Not a good match': ['■', 'q-bad'] };
const STRENGTH_WORD = { 'Quarter strength': 'quarter strength', 'Quarter to half strength': 'quarter to half strength', 'Half strength': 'half strength', 'Full strength': 'full strength' };
function needLines(n, opts) {
  if (!n) return '';
  const o = opts || {}, m = n.match, none = n.strength === 'None needed';
  const need = n.ratio
    ? (none ? html`<strong>Needs little or no fertilizer.</strong> If you do feed it: N-P-K ratio <strong class="npk">${n.ratio_text}</strong>, lightly.`
            : html`Needs N-P-K ratio <strong class="npk">${n.ratio_text}</strong>${n.strength ? html`, at ${STRENGTH_WORD[n.strength]}` : ''}.`)
    : html`<span class="muted">${n.note}</span>`;
  let match = '';
  if (m) {
    const q = FZQ[m.quality] || ['', ''], d = m.dose;
    const dose = !d ? '' : d.kind === 'water' ? html` ${d.words}${d.ppm_n != null ? ` That is about ${fmt(d.ppm_n, 0)} ppm nitrogen.` : ''}` : html` ${d.words}`;
    const last = m.last ? html` <span class="muted">Last time you used ${fmt(m.last.amount, 2)} ${m.last.amount_unit}${m.last.water_amount ? ` in ${fmt(m.last.water_amount, 2)} ${m.last.water_unit}` : ''}.</span>` : '';
    match = html`<span class="fn-m">${m.quality === 'Not a good match' ? 'Closest you have' : 'Best match you have'}: <strong>${m.product}</strong> <span class="npk">${m.npk_text}</span>
      <span class="fn-q ${q[1]}">${q[0]} ${m.quality}</span>${m.why ? ` ${m.why}` : ''}${m.quality === 'Not a good match' ? ` Look for a fertilizer labelled about ${n.ratio_text}, or add one you have.` : ''}${none ? '' : dose}${m.strength_assumed && d && d.kind === 'water' ? ' (No strength is set for this plant, so this is for half strength.)' : ''}${last}</span>`;
  } else if (n.ratio && !none) match = html`<span class="fn-m muted">${n.note}</span>`;
  return html`<span class="fn-need${o.block ? ' blk-need' : ''}"><span class="fn-n">${need}</span>${match}</span>`;
}
async function loadNeeds(code) {
  try { const r = await api('GET', '/api/fertilizer/needs' + (code ? '?plant=' + enc(code) : '')); r.needs.forEach(n => { FERT.needs[n.code] = n; }); }
  catch (e) { /* the page works without it */ }
}

// ---------- your fertilizers: saved ones and logged ones (1.11.0) ----------
function productsBlock() {
  const P = FERT.products;
  return html`<p>The fertilizers you have. Each plant above is matched to the one whose N-P-K ratio is closest to what it needs. Add the ones in your shed even before you use them; ones you log are added by themselves.</p>
    <p class="row noprint"><button class="btn" type="button" data-act="fzadd">Add a fertilizer you have</button></p>
    ${P.length ? html`<div class="tbl-wrap"><table class="tbl fn-tbl"><caption class="sr">Your fertilizers</caption><thead><tr><th scope="col">Name</th><th scope="col">N-P-K</th><th scope="col">Type</th><th scope="col">Last used</th><th scope="col"><span class="sr">Actions</span></th></tr></thead><tbody>
      ${P.map((x, i) => html`<tr><th scope="row">${x.product}${x.note ? html`<div class="hint">${x.note}</div>` : ''}</th>
        <td>${npkText(x)}${ratioText(x.n, x.p, x.k) ? html`<div class="hint">ratio ${ratioText(x.n, x.p, x.k)}</div>` : ''}</td><td>${x.form}</td>
        <td>${x.last_used ? html`${midDay(x.last_used)}<div class="hint">${doseText(x)}${x.uses > 1 ? `, ${x.uses} times in all` : ''}</div>` : html`<span class="muted">Not used yet</span>`}</td>
        <td class="noprint"><div class="row" style="gap:.4rem"><button class="btn ghost small" type="button" data-act="fzedit" data-i="${i}">Change</button>${x.saved ? html`<button class="btn danger small" type="button" data-act="fzdel" data-i="${i}">Remove</button>` : ''}</div></td></tr>`)}</tbody></table></div>
      <p class="hint">Amounts aim for about 150 ppm of the strongest of N, P and K at full strength, 75 at half and 40 at a quarter, which is a usual rate for plants in pots. If the label says to use less, use the label.</p>`
    : html`<p class="muted">None yet.</p>`}`;
}
async function productDialog(x) {
  if (!(await needName())) return;
  const editing = x && x.saved, num = v => v == null ? '' : v;
  for (;;) {
    const r = await modal(html`<form method="dialog"><h2>${editing ? 'Change this fertilizer' : x ? 'Correct this fertilizer' : 'Add a fertilizer you have'}</h2>
      ${x && !x.saved ? html`<p class="muted">This one came from your feeding log. Saving keeps your log as it is and uses these details for matching.</p>` : ''}
      <label class="f">Name<input type="text" name="product" maxlength="80" value="${x ? x.product : ''}" required autofocus></label>
      <label class="f">Type<select name="form">${['liquid', 'powder', 'granular', 'slow-release', 'spikes', 'organic liquid', 'organic solid', 'foliar spray', 'other'].map(v => html`<option ${v === (x ? x.form : 'liquid') ? raw('selected') : ''}>${v}</option>`)}</select>
        <small>Liquid and powder are mixed into water. Granular, slow-release, spikes and organic solid go on or into the mix.</small></label>
      <fieldset class="opt-group"><legend>What is printed on the package (N-P-K, in percent)</legend>
        <div class="field-grid three"><label class="f">Nitrogen (N)<input type="number" step="any" min="0" max="100" name="n" value="${num(x && x.n)}" required></label>
          <label class="f">Phosphate (P)<input type="number" step="any" min="0" max="100" name="p" value="${num(x && x.p)}" required></label>
          <label class="f">Potash (K)<input type="number" step="any" min="0" max="100" name="k" value="${num(x && x.k)}" required></label></div>
        <p class="hint">A bottle labelled 24-8-16 is 24% nitrogen, 8% phosphate and 16% potash.</p></fieldset>
      <label class="f">Note<input type="text" name="note" maxlength="300" value="${x ? x.note || '' : ''}"><small>For example where it is kept, or "with iron".</small></label>
      <div class="row"><button class="btn" value="ok">${editing ? 'Save changes' : 'Save fertilizer'}</button><button class="btn ghost" value="cancel" formnovalidate>Cancel</button></div></form>`);
    if (r !== 'ok') return;
    const f = dlg.querySelector('form'), v = n => f.elements[n].value;
    const body = { product: v('product'), form: v('form'), n: v('n'), p: v('p'), k: v('k'), note: v('note') };
    try {
      if (editing) await api('PUT', '/api/fertilizer/products/' + x.id, body); else await api('POST', '/api/fertilizer/products', body);
      toast(editing ? 'Fertilizer changed' : `${body.product.trim()} saved`);
      await fertRefresh(); return;
    } catch (e) { toast(e.message, true); x = { ...(x || {}), ...body, n: +body.n, p: +body.p, k: +body.k }; }
  }
}

// ---------- fertilizer panel on a plant page ----------
function fertCfgPlant(p) {
  return {
    legend: html`Shaded green days are in this plant's feeding season. Hatched days are its resting season: do not fertilize. "Fed" marks a feeding you logged and "Due" the next one this page suggests.`,
    cell(ds, c) {
      const es = entriesFor(p.code), fed = es.filter(e => e.applied_on === ds), nd = nextDue(p, es);
      const inS = hasSeason(p) && monthIn(p, +ds.slice(5, 7));
      const badges = [];
      fed.forEach(e => badges.push({ cls: 'b-fed', text: '● Fed ' + e.product }));
      if (nd === ds && !fed.length) badges.push({ cls: 'b-due', text: '▲ Due' });
      if (hasSeason(p) && !inS && !badges.length) badges.push({ cls: 'b-rest', text: 'Rest' });
      return { cls: hasSeason(p) ? (inS ? 'cal-in' : 'cal-rest') : '', badges,
        aria: (fed.length ? 'Fed with ' + fed.map(e => e.product).join(' and ') + '. ' : '') + (nd === ds && !fed.length ? 'Next feeding due. ' : '') + (hasSeason(p) ? (inS ? 'In feeding season.' : 'Resting season, do not fertilize.') : '') };
    },
    pick(ds) { fertDayDetail(p, ds); },
  };
}
function fertDayDetail(p, ds) {
  const el = document.getElementById('fert-day'); if (!el) return;
  const es = entriesFor(p.code), st = fertState(p, es, ds, fertCtx()), fed = es.filter(e => e.applied_on === ds);
  el.innerHTML = rend(html`<section class="day-card" aria-live="polite"><h3>${longDay(ds)}</h3>
    <p class="verdict">${verdictLine(p, st)}</p><p>${fertWords(p, st, ds)}</p>
    ${fed.length ? html`<h4>Fed on this day</h4>${entryRows(fed, {}, false)}` : ''}
    <div class="row noprint"><button class="btn small" type="button" data-act="fertlog" data-code="${p.code}" data-date="${ds}">Log a feeding on this date</button></div></section>`);
}
async function loadFertPlant() {
  const box = document.getElementById('fert-plant'); if (!box || !CUR) return;
  const p = CUR.p;
  try { await Promise.all([loadFertData(false), loadNeeds(p.code)]); } catch (e) { box.innerHTML = rend(html`<p class="notice bad">Could not load feeding data: ${e.message}</p>`); return; }
  const es = entriesFor(p.code), today = todayStr(), st = fertState(p, es, today, fertCtx()), nd = nextDue(p, es);
  const prevSel = CALS.fp && CALS.fp.sel;
  const nb = document.getElementById('fert-need');
  if (nb) nb.innerHTML = rend(FERT.needs[p.code] ? html`<div class="fn-plant"><h3>What to feed it</h3><p>${needLines(FERT.needs[p.code], { block: true })}</p>
      <p class="hint noprint"><a href="#/fertilizer">Your fertilizers</a> are listed on the Fertilizer page. Change this plant's ratio or strength with Edit, under Nutrients.</p></div>` : '');
  box.innerHTML = rend(html`<div class="verdict-box v-${st.state}" role="status"><h3>Today, ${longDay(today)}</h3><p class="verdict">${verdictLine(p, st)}</p><p>${fertWords(p, st, today)}</p>
      ${hasSeason(p) ? html`<p class="hint">Season: ${seasonText(p)}.${nd && st.state !== 'due' && st.state !== 'hold' ? ' Next feeding about ' + longDay(nd) + '.' : ''} Change these in Edit this page.</p>` : ''}</div>
    <div class="row noprint" style="margin:.8rem 0"><button class="btn" type="button" data-act="fertlog" data-code="${p.code}">Log a feeding for this plant</button></div>
    <h3>Feeding calendar</h3><div id="cal-fp"></div><div id="fert-day"></div>
    <h3>Everything logged for this plant</h3>${entryRows(es, {}, false)}`);
  await calMount('fp', fertCfgPlant(p), prevSel ? prevSel.slice(0, 7) : null, prevSel || today);
  fertDayDetail(p, CALS.fp.sel);
}

// ---------- the Fertilizer page ----------
async function viewFertilizer() {
  await loadFertData(true);
  const t = todayStr(), by = Object.fromEntries(FERT.plants.map(p => [p.code, p]));
  const rows = FERT.plants.map(p => ({ p, st: fertState(p, entriesFor(p.code), t, fertCtx()) }));
  const grp = k => rows.filter(r => r.st.state === k || (k === 'wait' && r.st.state === 'fed'));
  const G5 = [['due', 'Time to fertilize', true], ['hold', 'Hold off for now', true], ['wait', 'Fed recently', false], ['rest', 'Resting (out of season)', false], ['unknown', 'No feeding season set', false]];
  const rowHtml = r => html`<li class="${FERT.needs[r.p.code] ? 'fn-li' : ''}">${r.p.photo ? html`<img src="${thumbUrl(r.p.photo)}" alt="" loading="lazy">` : html`<span></span>`}
    <span><a class="nm" href="#/plant/${enc(r.p.code)}">${r.p.common_name}</a><br><span class="muted">${r.p.code}. ${r.st.state === 'rest' ? 'Season opens ' + midDay(r.st.until) + '.' : r.st.state === 'hold' ? r.st.reason : r.st.state === 'unknown' ? '' : r.st.last ? `Last fed ${r.st.since} days ago.${r.st.state === 'wait' || r.st.state === 'fed' ? ' Next about ' + midDay(r.st.next) + '.' : r.st.over > 0 ? ' ' + r.st.over + ' days overdue.' : ''}` : 'Never logged.'}</span></span>${FERT.needs[r.p.code] ? html`<span class="fn-row">${needLines(FERT.needs[r.p.code])}</span>` : ''}
    <button class="btn ghost small noprint" type="button" data-act="fertlog" data-code="${r.p.code}">Log</button></li>`;
  const q = k => grp(k).length;
  return {
    title: 'Fertilizer',
    html: html`<h1>Fertilizer</h1>
    <p class="muted">When to feed each plant, and a record of what you used. Every plant has its own feeding season (the months it grows) and a gap between feedings, and the N-P-K ratio it needs. Change them on a plant's Edit page.</p>
    <div class="verdict-box" role="status"><h2 style="margin:0 0 .4rem">Today, ${longDay(t)}</h2>
      <p>${q('due')} plant${q('due') === 1 ? ' is' : 's are'} due for fertilizer${q('hold') ? `, ${q('hold')} should wait because of cold or health` : ''}. ${q('wait')} ${q('wait') === 1 ? 'was' : 'were'} fed recently and ${q('rest')} ${q('rest') === 1 ? 'is' : 'are'} resting for the season.</p>
      <div class="row noprint"><button class="btn" type="button" data-act="fertlog">Log fertilizer</button>${q('due') ? html`<button class="btn ghost" type="button" data-act="fertlog" data-group="due">Log fertilizer for the ${q('due')} due plants</button>` : ''}</div></div>
    ${G5.map(([k, title, open]) => grp(k).length ? html`<details class="grp" ${open ? raw('open') : ''}><summary><h2>${title} (${grp(k).length})</h2></summary><ul class="todo">${grp(k).map(rowHtml)}</ul></details>` : '')}
    <section class="blk"><h2>Calendar for all plants</h2><div id="cal-fa"></div><div id="fa-day"></div></section>
    <section class="blk" id="fn-products"><h2>Your fertilizers</h2>${productsBlock()}</section>
    <section class="blk"><h2>Feeding seasons</h2><div class="tbl-wrap"><table class="tbl"><thead><tr><th>Plant</th><th>Season</th><th class="num">Every (days)</th><th>Last fed</th><th>Next feeding</th></tr></thead><tbody>
      ${rows.map(r => { const es = entriesFor(r.p.code), nd = nextDue(r.p, es); return html`<tr><th scope="row"><a href="#/plant/${enc(r.p.code)}">${r.p.common_name}</a><div class="hint">${r.p.code}</div></th>
        <td>${hasSeason(r.p) ? MN[r.p.fert_from_month - 1] + ' to ' + MN[r.p.fert_to_month - 1] : 'Not set'}</td><td class="num">${r.p.fert_every_days || ''}</td><td>${es[0] ? midDay(es[0].applied_on) : 'Never logged'}</td><td>${nd ? midDay(nd) : ''}</td></tr>`; })}</tbody></table></div></section>
    <section class="blk"><h2>Everything logged</h2>${entryRows(FERT.entries.slice(0, 60), by, true)}${FERT.entries.length > 60 ? html`<p class="hint">Showing the newest 60 of ${FERT.entries.length}. The change log has the rest.</p>` : ''}</section>`,
    after: async () => {
      const prev = CALS.fa && CALS.fa.sel;
      await calMount('fa', {
        legend: 'The number after "Fed" is how many plants were fed that day. "Due" is how many plants are next due then.',
        cell(ds) {
          const fed = FERT.entries.filter(e => e.applied_on === ds), dueN = FERT.plants.filter(p => nextDue(p, entriesFor(p.code)) === ds).length;
          const badges = []; if (fed.length) badges.push({ cls: 'b-fed', text: '● Fed ' + new Set(fed.map(e => e.plant_code)).size });
          if (dueN) badges.push({ cls: 'b-due', text: '▲ Due ' + dueN });
          return { badges, aria: (fed.length ? `${new Set(fed.map(e => e.plant_code)).size} plants fed. ` : '') + (dueN ? `${dueN} plants due.` : '') };
        },
        pick(ds) {
          const el = document.getElementById('fa-day'); if (!el) return;
          const fed = FERT.entries.filter(e => e.applied_on === ds), due = FERT.plants.filter(p => nextDue(p, entriesFor(p.code)) === ds);
          el.innerHTML = rend(html`<section class="day-card" aria-live="polite"><h3>${longDay(ds)}</h3>
            ${fed.length ? entryRows(fed, by, true) : html`<p class="muted">No feedings logged on this day.</p>`}
            ${due.length ? html`<h4>Due on this day</h4><ul>${due.map(p => html`<li><a href="#/plant/${enc(p.code)}">${p.common_name}</a></li>`)}</ul>` : ''}
            <div class="row noprint"><button class="btn small" type="button" data-act="fertlog" data-date="${ds}">Log fertilizer on this date</button></div></section>`);
        },
      }, prev ? prev.slice(0, 7) : null, prev || t);
      CALS.fa.cfg.pick(CALS.fa.sel);
    },
  };
}

// ---------- log / change a feeding ----------
let FD = null;   // state of the dialog, kept so a failed save does not lose what was typed
function fertState0(opts) {
  const e = opts.entry, last = FERT.products[0];
  const n = !e && opts.codes && opts.codes.length === 1 ? FERT.needs[opts.codes[0]] : null, m = n && n.match && n.match.quality !== 'Not a good match' && n.strength !== 'None needed' ? n.match : null;
  if (m) {                     // logging for one plant: start from the fertilizer and amount the page suggests for it
    const d = m.dose || {}, water = d.kind === 'water';
    return { id: null, codes: opts.codes, applied_on: opts.date || todayStr(), product: m.product, form: m.form, n: m.n, p: m.p, k: m.k,
      amount: water ? d.amount : null, amount_unit: water ? d.unit : 'tsp', water_amount: water ? d.water : null, water_unit: 'gal', method: water ? 'water in' : 'top-dress', note: '' };
  }
  return e ? { id: e.id, codes: [e.plant_code], applied_on: e.applied_on, product: e.product, form: e.form, n: e.n, p: e.p, k: e.k, amount: e.amount, amount_unit: e.amount_unit || 'tsp', water_amount: e.water_amount, water_unit: e.water_unit || 'gal', method: e.method, note: e.note }
    : { id: null, codes: opts.codes || [], applied_on: opts.date || todayStr(), product: '', form: 'liquid', n: null, p: null, k: null, amount: null, amount_unit: 'tsp', water_amount: null, water_unit: 'gal', method: 'water in', note: '' };
}
function readFert() {
  const f = dlg.querySelector('form'), v = n => { const x = f.elements[n]; return x ? x.value : ''; };
  const num = n => v(n) === '' ? null : Number(v(n));
  const codes = [...dlg.querySelectorAll('[name=pl]:checked')].map(x => x.value);
  return { id: FD ? FD.id : null, codes: FD && FD.id ? FD.codes : codes, applied_on: v('applied_on'), product: v('product').trim(), form: v('form'), n: num('n'), p: num('p'), k: num('k'),
    amount: num('amount'), amount_unit: v('amount_unit'), water_amount: num('water_amount'), water_unit: v('water_unit'), method: v('method'), note: v('note').trim() };
}
function fertPreview() {
  const box = document.getElementById('fert-preview'); if (!box) return;
  const s = readFert(), c = fertCalc(s.form, s.n, s.p, s.k, s.amount, s.amount_unit, s.water_amount, s.water_unit), bits = [];
  if (c.ppm_n != null) {
    bits.push(html`<strong>About ${fmt(c.ppm_n, 0)} ppm nitrogen</strong> in the water${c.ppm_p2o5 != null ? html`, ${fmt(c.ppm_p2o5, 0)} ppm phosphate (P₂O₅) and ${fmt(c.ppm_k2o, 0)} ppm potash (K₂O)` : ''}. ${ratioText(s.n, s.p, s.k) ? 'N : P : K ratio ' + ratioText(s.n, s.p, s.k) + '.' : ''}`);
    bits.push(html`<span class="hint">${c.ppm_n > 300 ? 'That is strong for most potted plants, which usually get 50 to 200 ppm nitrogen. Use less product or more water.' : c.ppm_n < 25 ? 'That is very weak. Fine for feeding at every watering, but not enough for a monthly feeding.' : 'Most potted plants do well at 50 to 200 ppm nitrogen.'} Spoon measures are taken as ${s.form === 'liquid' || s.form === 'organic liquid' || s.form === 'foliar spray' ? '4.9 ml per tsp and 14.8 ml per tbsp' : '4 g per tsp and 12 g per tbsp'}, so treat it as an estimate.</span>`);
  } else if (c.n_grams != null) bits.push(html`<strong>About ${fmt(c.n_grams, 2)} g of nitrogen</strong> applied in total (no water amount given, so no ppm).`);
  else bits.push(html`<span class="hint">Enter the N-P-K numbers, the amount, and how much water it goes into to see how strong the mix is.</span>`);
  const t = s.applied_on, rest = (s.codes || []).map(c0 => FERT.plants.find(p => p.code === c0) || (CUR && CUR.p.code === c0 ? CUR.p : null)).filter(p => p && t && hasSeason(p) && !monthIn(p, +t.slice(5, 7)));
  if (rest.length) bits.push(html`<strong class="st-near">▲ ${rest.length} selected plant${rest.length === 1 ? ' is' : 's are'} in a resting season on that date: ${rest.slice(0, 6).map(p => p.common_name).join(', ')}${rest.length > 6 ? ' and more' : ''}.</strong>`);
  box.innerHTML = rend(html`${bits.map(b => html`<p>${b}</p>`)}`);
}
async function fertDialog(opts) {
  if (!(await needName())) return;
  if (!FERT.plants.length) { try { FERT.plants = await api('GET', '/api/plants'); } catch (e) { toast(e.message, true); return; } }
  if (!FERT.products.length && !FERT.entries.length) { try { await loadFertData(false); } catch (e) { /* products only help pre-filling */ } }
  FD = fertState0(opts);
  for (;;) {
    const S = FD, editing = !!S.id, sel = new Set(S.codes), t = todayStr();
    const sec = (v, list, cur) => list.map(x => html`<option value="${x}" ${x === cur ? raw('selected') : ''}>${x}</option>`);
    const num = v => v == null ? '' : v;
    const rest = S.id ? [] : FERT.plants;
    const mp = modal(html`<form method="dialog" data-fert="1"><h2>${editing ? 'Change this feeding' : 'Log fertilizer'}</h2>
      <div class="field-grid"><label class="f">Date<input type="date" name="applied_on" value="${S.applied_on}" max="${addDays(t, 1)}" required></label>
        <label class="f">Fertilizer name<input type="text" name="product" list="fert-products" maxlength="80" value="${S.product}" autocomplete="off" ${editing ? '' : raw('autofocus')}><small>Pick one you used before to fill in the rest.</small></label></div>
      <datalist id="fert-products">${FERT.products.map(x => html`<option value="${x.product}"></option>`)}</datalist>
      <label class="f">Type<select name="form">${sec('', ['liquid', 'powder', 'granular', 'slow-release', 'spikes', 'organic liquid', 'organic solid', 'foliar spray', 'other'], S.form)}</select></label>
      <fieldset class="opt-group"><legend>What is printed on the package (N-P-K, in percent)</legend>
        <div class="field-grid three"><label class="f">Nitrogen (N)<input type="number" step="any" min="0" max="100" name="n" value="${num(S.n)}"></label>
          <label class="f">Phosphate (P)<input type="number" step="any" min="0" max="100" name="p" value="${num(S.p)}"></label>
          <label class="f">Potash (K)<input type="number" step="any" min="0" max="100" name="k" value="${num(S.k)}"></label></div>
        <p class="hint">A bottle labelled 24-8-16 is 24% nitrogen, 8% phosphate and 16% potash. Leave a box empty if the package does not say.</p></fieldset>
      <fieldset class="opt-group"><legend>How much, and into how much water</legend>
        <div class="field-grid"><label class="f">Amount of fertilizer<input type="number" step="any" min="0" name="amount" value="${num(S.amount)}"></label>
          <label class="f">Unit<select name="amount_unit">${sec('', ['tsp', 'tbsp', 'g', 'oz', 'ml', 'fl oz'], S.amount_unit)}</select></label>
          <label class="f">Mixed into this much water<input type="number" step="any" min="0" name="water_amount" value="${num(S.water_amount)}"></label>
          <label class="f">Water unit<select name="water_unit">${sec('', ['gal', 'L', 'qt', 'cup'], S.water_unit)}</select></label></div>
        <p class="hint">For example 1 tsp in 1 gal. Leave the water empty for dry products worked into the soil.</p></fieldset>
      <div class="field-grid"><label class="f">How it was applied<select name="method">${sec('', ['water in', 'foliar spray', 'top-dress', 'mixed into soil', 'spike', 'other'], S.method)}</select></label>
        <label class="f">Note<input type="text" name="note" maxlength="500" value="${S.note}"></label></div>
      <div id="fert-preview" class="notice" aria-live="polite"></div>
      ${editing ? html`<p class="muted">Plant: ${((FERT.plants.find(p => p.code === S.codes[0]) || (CUR && CUR.p)) || {}).common_name || S.codes[0]}</p>` : html`<fieldset class="opt-group"><legend>Plants fed (${sel.size} chosen)</legend>
        <div class="row noprint"><button class="btn ghost small" type="button" data-act="fertpick" data-how="due">All that are due</button><button class="btn ghost small" type="button" data-act="fertpick" data-how="season">All in season</button><button class="btn ghost small" type="button" data-act="fertpick" data-how="none">None</button></div>
        <div class="pickbox">${rest.map(p => html`<label class="chk-row"><input type="checkbox" name="pl" value="${p.code}" ${sel.has(p.code) ? raw('checked') : ''}><span>${p.common_name} <span class="muted">${p.code}</span></span></label>`)}</div></fieldset>`}
      <div class="row"><button class="btn" value="ok">${editing ? 'Save changes' : 'Save feeding'}</button><button class="btn ghost" value="cancel">Cancel</button></div></form>`);
    fertPreview();
    const r = await mp;
    if (r !== 'ok') { FD = null; return; }
    const s = readFert(); FD = s;
    try {
      const body = { ...s, plants: s.codes };
      if (!editing && !s.codes.length) throw new Error('Choose at least one plant.');
      const resting = s.codes.map(c0 => FERT.plants.find(p => p.code === c0)).filter(p => p && hasSeason(p) && !monthIn(p, +s.applied_on.slice(5, 7)));
      if (!editing && resting.length && !(await confirmBox('Some plants are resting', `${resting.length} of the chosen plants are in their resting season on that date (${resting.slice(0, 5).map(p => p.common_name).join(', ')}${resting.length > 5 ? ' and more' : ''}). Log it anyway?`, 'Log anyway', false))) { continue; }
      if (editing) await api('PUT', '/api/fertilizer/' + s.id, body); else await api('POST', '/api/fertilizer', body);
      toast(editing ? 'Feeding changed' : 'Feeding logged for ' + s.codes.length + ' plant' + (s.codes.length === 1 ? '' : 's'));
      FD = null; await fertRefresh(); return;
    } catch (e) { toast(e.message, true); }
  }
}
async function fertRefresh() {
  if (document.getElementById('fert-plant')) return loadFertPlant();
  return route();
}

// ---------- past days for Temperature, Humidity, Light, Water and soil ----------
const HMAP = {
  temp: ['temp_f', 'Temperature', '°F', 1], humidity: ['humidity', 'Humidity', '%', 0], vpd: ['vpd', 'Air dryness (VPD)', ' kPa', 2], light: ['par', 'Light', '', 0],
  soil_moisture: ['soil_moisture', 'Soil moisture', '%', 0], soil_temp: ['soil_temp_f', 'Root-zone temperature', '°F', 1], soil_ph: ['soil_ph', 'Soil pH', '', 1],
};
const HKIND = { temp: ['temp'], hum: ['humidity', 'vpd'], light: ['light'], soil: ['soil_moisture', 'soil_temp', 'soil_ph'] };
const HS = {};
function histBlock(kind) {
  return html`<details class="histbox noprint" data-hist="${kind}"><summary>Past days: pick a date to see what it was</summary><div class="hist-body" id="hb-${kind}"></div></details>`;
}
function histShell(kind) {
  const S = HS[kind], mets = HKIND[kind];
  return html`${mets.length > 1 ? html`<div class="opts tabs" role="group" aria-label="What to look at">${mets.map(m => html`<button type="button" class="btn ${S.metric === m ? '' : 'ghost'} small" data-act="histmetric" data-kind="${kind}" data-m="${m}" aria-pressed="${String(S.metric === m)}">${HMAP[m][1]}</button>`)}</div>` : ''}
    <div class="chart-tools"><label>Readings from<select data-f="histsrc" data-kind="${kind}">${[['auto', 'Best available'], ['sensor', 'My sensor'], ['manual', 'Typed in by me'], ['weather', 'Online weather (outdoors)']].map(([v, l]) => html`<option value="${v}" ${S.source === v ? raw('selected') : ''}>${l}</option>`)}</select></label></div>
    <p class="hint">Each day is marked by how that day's readings compared with this plant's range <em>as recorded on that day</em>. Weather history comes from the online weather for your area (outdoors); sensor and typed-in values appear once you have recorded them.</p>
    <div id="cal-h-${kind}"></div><div id="hd-${kind}"></div>`;
}
async function histOpen(kind) {
  if (!CUR) return;
  HS[kind] = HS[kind] || { metric: HKIND[kind][0], source: 'auto', day: null };
  const S = HS[kind], box = document.getElementById('hb-' + kind); if (!box) return;
  box.innerHTML = rend(histShell(kind));
  await histCal(kind);
}
async function histCal(kind) {
  const S = HS[kind], code = CUR.p.code, m = S.metric, [, , unit, dec] = HMAP[m];
  const doc = document.getElementById('hb-' + kind); if (doc) { const h = doc.querySelector('[data-f=histsrc]'); if (h) h.value = S.source; }
  await calMount('h-' + kind, {
    legend: 'Marks: ✔ in range, ▲ a little out, ■ out of range, ✖ danger. Days with no mark have no readings from the chosen source.',
    async load(month, c) { const d = await api('GET', `/api/plants/${enc(code)}/daily?metric=${m}&month=${month}&source=${S.source}`); c.data = Object.fromEntries(d.days.map(x => [x.date, x])); c.meta = d; },
    cell(ds, c) {
      const d = c.data[ds];
      if (!d || d.status === 'none' || !d.source) return { cls: 's-none', badges: [], aria: 'No readings.' };
      const lv = LEVELBD[d.status] || LEVELBD.info, val = m === 'light' ? (d.dli != null ? `${fmt(d.dli, 1)} mol/m²` : `${fmt(d.daytime_avg, 0)} PAR`) : `${fmt(d.avg, dec)}${unit}`;
      const badges = [{ cls: lv[0], text: lv[1] }, { cls: 'b-val', text: val }];
      if (d.fed && d.fed.length) badges.push({ cls: 'b-fed', text: '● Fed' });
      return { cls: lv[0], badges, aria: `${lv[1].replace(/^\S+ /, '')}, ${val}${d.fed && d.fed.length ? ', fertilizer applied' : ''}.` };
    },
    pick(ds) { histDay(kind, ds); },
  }, null, S.day || todayStr());
  const c = CALS['h-' + kind];
  histDay(kind, c.sel);
}
async function histDay(kind, ds) {
  const S = HS[kind], el = document.getElementById('hd-' + kind), code = CUR.p.code, m = S.metric;
  if (!el) return; S.day = ds;
  const [col, label, unit, dec] = HMAP[m], c = CALS['h-' + kind], d = (c.data || {})[ds];
  el.innerHTML = rend(html`<p class="loading">Loading ${longDay(ds)}</p>`);
  let day; try { day = await api('GET', `/api/plants/${enc(code)}/day?date=${ds}`); } catch (e) { el.innerHTML = rend(html`<p class="notice bad">${e.message}</p>`); return; }
  if (S.day !== ds) return;
  const names = day.source_names, series = [];
  const cls = { sensor: 's1', weather: 's2', manual: 's3' };
  ['sensor', 'manual', 'weather'].forEach(s => { const pts = (day.sources[s] || []).filter(x => x[col] != null).map(x => [Date.parse(x.t), x[col]]); if (pts.length && (S.source === 'auto' || S.source === s)) series.push({ name: names[s], cls: cls[s], pts, key: s }); });
  const main = d && d.source ? series.find(x => x.key === d.source) || series[0] : series[0];
  const vals = main ? main.pts.map(x => x[1]) : [], lo = d ? d.lo : day.ranges[HMAP_RANGE[m][0]], hi = d ? d.hi : day.ranges[HMAP_RANGE[m][1]];
  const f = x => fmt(x, dec) + unit;
  const rangeTxt = has(lo) || has(hi) ? `${has(lo) ? 'from ' + (m === 'light' && d && d.judged_on === 'dli' ? fmt(lo, 1) + ' mol/m²/day' : f(lo)) : ''}${has(lo) && has(hi) ? ' ' : ''}${has(hi) ? 'to ' + (m === 'light' && d && d.judged_on === 'dli' ? fmt(hi, 1) + ' mol/m²/day' : f(hi)) : ''}` : '';
  const now = CUR.p, lvl = d && LEVELBD[d.status];
  const refs = [], bands = [];
  if (has(lo) && has(hi) && !(m === 'light' && d && d.judged_on === 'dli')) bands.push({ lo, hi, label: 'Comfortable range then' });
  else if (has(lo) && !(m === 'light' && d && d.judged_on === 'dli')) refs.push({ v: lo, label: 'Lowest comfortable' });
  else if (has(hi) && !(m === 'light' && d && d.judged_on === 'dli')) refs.push({ v: hi, label: 'Highest comfortable' });
  if (m === 'temp' && has(day.ranges.temp_damage_below)) refs.push({ v: day.ranges.temp_damage_below, label: 'Damage below ' + day.ranges.temp_damage_below + '°F' });
  const cur = HMAP_RANGE[m].map(k => now[k]);
  el.innerHTML = rend(html`<section class="day-card" aria-live="polite"><h3>${longDay(ds)}</h3>
    ${main ? html`<p class="verdict">${lvl ? html`<span class="${lvl[0] === 's-ok' ? 'st-ok' : lvl[0] === 's-near' ? 'st-near' : lvl[0] === 's-bad' ? 'st-bad' : lvl[0] === 's-danger' ? 'st-danger' : 'st-mute'}">${lvl[1]}</span>` : ''}</p>
      <dl class="dl"><dt>${label} (${names[main.key]})</dt><dd>lowest ${f(Math.min(...vals))}, average ${f(vals.reduce((a, b) => a + b, 0) / vals.length)}, highest ${f(Math.max(...vals))}${m === 'light' && d && d.dli != null ? `. Daily light ${fmt(d.dli, 1)} mol/m².` : ''}</dd>
        ${d && d.hours_in != null && m !== 'light' ? html`<dt>Hours in range</dt><dd>${d.hours_in} of ${d.n} hours that had readings</dd>` : ''}
        <dt>Comfortable range then</dt><dd>${rangeTxt || 'No range was recorded for this plant.'}${d && d.range_from_now ? ' (taken from the current page, because the page had none on that day)' : ''}${day.version !== day.current_version ? html` (page version ${day.version}; the current page is version ${day.current_version}${cur.some(x => has(x)) && (cur[0] !== lo || cur[1] !== hi) ? ', and its range is now ' + (has(cur[0]) ? f(cur[0]) : '?') + ' to ' + (has(cur[1]) ? f(cur[1]) : '?') : ''})` : ''}</dd>
        ${day.fertilized.length ? html`<dt>Fertilizer</dt><dd>${day.fertilized.map(e => `${e.product}, ${doseText(e)}`).join('; ')}</dd>` : ''}</dl>
      ${chartCard('hd-' + kind, { title: `${label} on ${midDay(ds)}`, series, fmt: v => String(Math.round(v * 100) / 100), unit, bands, refs, zero: m === 'light', clamp: m === 'humidity' || m === 'soil_moisture' ? [0, 100] : null })}`
      : html`<p>No ${label.toLowerCase()} readings were recorded on this day${S.source === 'auto' ? '' : ' from ' + (names[S.source] || 'that source')}.</p>
        <p class="hint">${m.startsWith('soil') ? 'Soil values come from your sensor or from numbers you type in under Current conditions.' : 'Online weather history is stored from the first time the app ran (it loads about 3 months back); sensor values start when the sensor first reports. You can load older weather on the Weather page.'}</p>
        ${has(lo) || has(hi) ? html`<p>Comfortable range then: ${rangeTxt}.</p>` : ''}`}
    <div class="row noprint"><button class="btn ghost small" type="button" data-act="calnav" data-cal="h-${kind}" data-d="0">Back to today</button></div></section>`);
  if (main) paintChart('hd-' + kind);
}
const HMAP_RANGE = { temp: ['temp_ideal_low', 'temp_ideal_high'], humidity: ['humidity_low', 'humidity_high'], vpd: ['vpd_low', 'vpd_high'], light: ['par_low', 'par_high'], soil_moisture: ['soil_moisture_low', 'soil_moisture_high'], soil_temp: ['soil_temp_low', 'soil_temp_high'], soil_ph: ['soil_ph_low', 'soil_ph_high'] };

// ---------- edit and create ----------
const GROUPS = [
  ['Names and place', ['common_name', 'scientific_name', 'aliases', 'plant_type', 'site', 'location', 'container']],
  ['Identification', ['id_confidence', 'id_basis', 'id_alternatives', 'id_improve']],
  ['About this plant', ['growth_habit', 'kingdom', 'taxon_order', 'family', 'genus', 'height_ground', 'width_ground', 'height_pot', 'width_pot', 'growth_rate', 'lifespan',
    'zone_low', 'zone_high', 'zone_notes', 'native_range', 'conservation_status', 'invasive', 'bloom', 'fruit', 'danger_humans', 'danger_animals', 'pet_safety', 'propagation', 'sources']],
  ['Temperature', ['temp_ideal_low', 'temp_ideal_high', 'temp_damage_below', 'temp_lethal_below', 'temp_damage_above', 'temp_notes']],
  ['Humidity and air dryness', ['humidity_low', 'humidity_high', 'vpd_low', 'vpd_high', 'humidity_notes']],
  ['Sunlight', ['light_summary', 'light_hours', 'par_low', 'par_high', 'dli_low', 'dli_high', 'light_notes']],
  ['Water and soil', ['water_every_days', 'water_notes', 'soil_medium', 'soil_ph_low', 'soil_ph_high', 'soil_moisture_low', 'soil_moisture_high', 'soil_temp_low', 'soil_temp_high']],
  ['Nutrients', ['fertilizer', 'npk_ratio', 'fert_strength', 'nutrients', 'fert_from_month', 'fert_to_month', 'fert_every_days']],
  ['Winter plan', ['winter_plan', 'winter_summary', 'winter_triggers', 'winter_steps', 'indoor_setup']],
  ['Health', ['health_rating', 'health_summary', 'health_observations', 'health_steps']],
  ['Pests and diseases', ['pests_watch', 'pest_steps', 'pests_current', 'pests_found', 'leaf_type', 'pot_size']],
  ['Notes', ['notes']],
];
const HINTS = {
  id_confidence: 'Whole number from 0 to 100.', id_improve: 'One item per line. These show on the page and in the copy-for-Claude request.',
  temp_damage_below: 'Leaves or stems start to be hurt below this.', temp_lethal_below: 'The plant is likely to die below this.',
  temp_ideal_low: 'Lower edge of the comfortable range.', temp_ideal_high: 'Upper edge of the comfortable range.',
  temp_damage_above: 'Leaves start to scorch above this.', vpd_low: 'Vapour pressure deficit in kPa. A sensor can work it out from temperature and humidity.',
  par_low: 'PAR in umol/m2/s at the leaves. Full midday sun is about 1800.', dli_low: 'Mol of light per square metre per day.',
  soil_moisture_low: 'As read by your soil probe, 0 to 100.', soil_temp_low: 'Temperature of the root zone in F.',
  water_every_days: 'Leave empty to let the app work it out from the soil moisture range. Hot weather shortens the gap; cool weather and being indoors lengthen it.',
  winter_steps: 'One step per line, in order.',
  pests_found: 'One per line, from: Spider mites, Mealybugs, Scale, Aphids, Whiteflies, Thrips, Ants, Fungus gnats, Root mealybugs, Slugs or snails, Pill bugs or earwigs, Other. The plant page has tick boxes for these.',
  npk_ratio: 'Three numbers for nitrogen, phosphate and potash, such as 3-1-2. The Fertilizer page finds your closest fertilizer.',
  fert_strength: 'How strong to mix it. The Fertilizer page works out the amount per gallon from this.',
  pet_safety: 'Used by the Pets filter on the Plants page. "Safe for pets" only where the ASPCA lists the plant as non-toxic.',
  zone_low: 'USDA zone, such as 9b or 10. The page compares it with the zone where you are.', zone_high: 'USDA zone, such as 11.',
  height_ground: 'For example 6 to 10 ft.', height_pot: 'For example 3 to 5 ft.', propagation: 'One method per line.',
  sources: 'One per line: a title, a | and the web address, for example "NC State Extension: Aloe vera | https://...".',
  leaf_type: 'Decides which pest treatments suit it before it comes inside.', pot_size: 'Whether the pot can be soaked in a bucket or tub.', health_steps: 'One step per line, in order.', indoor_setup: 'One item per line.',
};
const rangeOf = n => (META.int_ranges && META.int_ranges[n]) || (META.num_ranges && META.num_ranges[n]) || [-60, 150];
function fieldInput(f, val) {
  const hint = HINTS[f.name] || (f.kind === 'list' ? 'One item per line.' : '');
  const wide = (f.kind === 'long' || f.kind === 'list') ? 'wide' : '';
  let v = val == null ? '' : val;          // let: the location defaults to Outdoors below (1.17.1 fixes "Add a plant", which stopped on it)
  let inp;
  if (f.kind === 'long' || f.kind === 'list') inp = html`<textarea name="${f.name}" rows="${f.kind === 'list' ? 5 : 4}">${v}</textarea>`;
  else if (f.kind === 'int') { const mm = rangeOf(f.name); inp = html`<input type="number" inputmode="numeric" step="1" min="${mm[0]}" max="${mm[1]}" name="${f.name}" value="${v}">`; }
  else if (f.kind === 'num') { const mm = rangeOf(f.name); inp = html`<input type="number" inputmode="decimal" step="any" min="${mm[0]}" max="${mm[1]}" name="${f.name}" value="${v}">`; }
  else if (f.kind === 'enum') {
    const opts = (META.enums && META.enums[f.name]) || (f.name === 'winter_plan' ? META.winter_plans : f.name === 'site' ? (META.sites || ['Outdoors', 'Indoors']) : META.health);
    const optional = (META.optional_enums || []).includes(f.name);
    if (f.name === 'site' && !v) v = 'Outdoors';
    inp = html`<select name="${f.name}">${optional ? html`<option value="" ${!v ? raw('selected') : ''}>Not set</option>` : ''}${opts.map(o => html`<option ${o === v ? raw('selected') : ''}>${o}</option>`)}</select>`;
  }
  else inp = html`<input type="text" name="${f.name}" value="${v}" ${f.name === 'common_name' ? raw('required') : ''}>`;
  return html`<label class="f ${wide}">${f.label}${hint ? html`<small>${hint}</small>` : ''}${inp}</label>`;
}
function viewForm(p) {
  const F = Object.fromEntries(META.fields.map(f => [f.name, f]));
  const isNew = !p;
  return {
    title: isNew ? 'Add a plant' : 'Edit ' + p.common_name,
    html: html`<p class="crumb"><a href="${isNew ? '#/' : '#/plant/' + enc(p.code)}">${isNew ? 'All plants' : 'Back to ' + p.common_name}</a></p>
    <h1>${isNew ? 'Add a plant' : 'Edit ' + p.code}</h1>
    <p class="muted">${isNew ? 'Only the common name is required. You can add photos after saving.' : 'Saving makes version ' + (p.version + 1) + '. The old text stays in the page history.'}</p>
    <form data-form="${isNew ? 'new' : 'edit'}" ${p ? raw('data-code="' + esc(p.code) + '" data-ver="' + p.version + '"') : ''} autocomplete="off">
      ${isNew && NEWFILL ? html`<p class="notice ok" role="note">${NEWFILL.__from}: the names are filled in${NEWFILL.__pic ? ', and the picture is added when you save' : ''}. Check them before saving.</p>` : ''}
      ${GROUPS.map(([title, names]) => html`<fieldset><legend>${title}</legend><div class="field-grid">${names.map(n => fieldInput(F[n], p ? p[n] : NEWFILL && NEWFILL[n] ? NEWFILL[n] : (n === 'winter_plan' ? 'Move indoors' : n === 'health_rating' ? 'Fair' : '')))}</div></fieldset>`)}
      ${isNew ? '' : html`<fieldset><legend>Change note</legend><label class="f">What did you change, and why?<small>Optional. It appears in the page history.</small><input type="text" name="__note" maxlength="300"></label></fieldset>`}
      <div id="form-err"></div>
      <div class="sticky-save"><button class="btn" type="submit">${isNew ? 'Add plant' : 'Save changes'}</button>
        <a class="btn ghost" href="${isNew ? '#/' : '#/plant/' + enc(p.code)}">Cancel</a></div>
    </form>`,
  };
}
async function viewEdit(code) { return viewForm(await api('GET', '/api/plants/' + enc(code))); }
async function submitForm(form) {
  if (!(await needName())) return;
  const fd = new FormData(form), fields = {};
  META.fields.forEach(f => { fields[f.name] = fd.get(f.name); });
  const err = document.getElementById('form-err'); err.innerHTML = '';
  const btn = form.querySelector('[type=submit]'); btn.disabled = true;
  try {
    if (form.dataset.form === 'new') {
      const p = await api('POST', '/api/plants', { fields });
      if (NEWFILL && NEWFILL.__pic) {                // 1.18.0: the picture from Identify
        const fd = new FormData(); fd.append('files', NEWFILL.__pic, 'identify-' + ymd(new Date()) + '.jpg'); fd.append('caption', 'Taken with Identify, ' + new Date().toLocaleDateString());
        try { await api('POST', '/api/plants/' + enc(p.code) + '/photos', undefined, fd); } catch (e) { toast('The plant was added, but not the picture: ' + e.message, true); }
      }
      NEWFILL = null;
      toast('Added ' + p.code); go('#/plant/' + enc(p.code));
    } else {
      const r = await api('PUT', '/api/plants/' + enc(form.dataset.code), { base_version: +form.dataset.ver, fields, note: fd.get('__note') || '' });
      toast(r.offline ? (r.changed ? 'Saved' : 'Nothing was changed') : r.changed ? 'Saved as version ' + r.version : 'Nothing was changed'); go('#/plant/' + enc(form.dataset.code));
    }
  } catch (e) {
    btn.disabled = false;
    err.innerHTML = rend(html`<div class="notice bad" role="alert"><strong>Not saved.</strong> ${e.message}</div>`);
    err.scrollIntoView({ block: 'center' });
  }
}

// ---------- charts (plain SVG; width follows the container and the text size) ----------
const CHARTS = {};
const DAYMS = 86400000;
function niceStep(range, n) { const raw = range / n, mag = Math.pow(10, Math.floor(Math.log10(raw))), r = raw / mag; return (r < 1.5 ? 1 : r < 3 ? 2 : r < 7 ? 5 : 10) * mag; }
function xTicks(t0, t1) {
  const span = (t1 - t0) / DAYMS, out = [];
  if (span <= 2.2) {
    const hrs = span <= 1.1 ? 3 : 6, d = new Date(t0); d.setMinutes(0, 0, 0);
    while (d.getHours() % hrs !== 0 || d.getTime() < t0) d.setHours(d.getHours() + 1);
    for (; d.getTime() <= t1; d.setHours(d.getHours() + hrs)) out.push(d.getTime());
  } else if (span > 400) {                       // years: aim for about 6 to 10 ticks
    const yrs = span / 365.25, step = [1, 2, 5, 10, 20, 25, 50].find(n => yrs / n <= 10) || 100;
    const d = new Date(new Date(t0).getFullYear(), 0, 1); while (d.getTime() < t0 || d.getFullYear() % step) d.setFullYear(d.getFullYear() + 1);
    for (; d.getTime() <= t1; d.setFullYear(d.getFullYear() + step)) out.push(d.getTime());
  } else if (span > 100) {                       // months
    const step = span > 250 ? 2 : 1, d = new Date(t0); d.setHours(0, 0, 0, 0); d.setDate(1); if (d.getTime() < t0) d.setMonth(d.getMonth() + 1);
    for (; d.getTime() <= t1; d.setMonth(d.getMonth() + step)) out.push(d.getTime());
  } else {
    const step = span <= 9 ? 1 : span <= 20 ? 2 : span <= 45 ? 7 : 14, d = new Date(t0); d.setHours(0, 0, 0, 0);
    if (d.getTime() < t0) d.setDate(d.getDate() + 1);
    for (; d.getTime() <= t1; d.setDate(d.getDate() + step)) out.push(d.getTime());
  }
  return out;
}
function xLabel(t, span) {
  const d = new Date(t);
  if (span <= 2.2) return d.getHours() === 0 ? d.toLocaleDateString([], { weekday: 'short', day: 'numeric' }) : d.toLocaleTimeString([], { hour: 'numeric' });
  if (span > 400) return String(d.getFullYear());
  if (span > 100) return d.toLocaleDateString([], { month: 'short', year: '2-digit' });
  return span <= 9 ? d.toLocaleDateString([], { weekday: 'short', day: 'numeric' }) : d.toLocaleDateString([], { month: 'short', day: 'numeric' });
}
function chartCard(id, spec) {
  CHARTS[id] = spec;
  const rows = [...new Set(spec.series.flatMap(s => s.pts.map(p => p[0])))].sort((a, b) => b - a).slice(0, 400);
  const look = spec.series.map(s => new Map(s.pts.map(p => [p[0], p[1]])));
  return html`<section class="chart-card" aria-labelledby="h-${id}"><h3 id="h-${id}">${spec.title}</h3>
    <div class="legend">${spec.series.map(s => html`<span><i style="--c:var(--${s.cls})"></i>${s.name}</span>`)}${spec.bands && spec.bands.length ? html`<span><i style="--c:var(--z-ok);border-top-width:.9rem;opacity:.35"></i>${spec.bands[0].label}</span>` : ''}
      ${(spec.refs || []).map(r => html`<span><i class="dash" style="--c:var(--ink)"></i>${r.label}</span>`)}</div>
    <div class="chart-box" id="cb-${id}"></div><div class="chart-tip" id="ct-${id}" role="presentation"></div>
    <details class="tbl-view"><summary>Show these numbers as a table</summary><div class="tbl-wrap"><table class="tbl"><thead><tr><th>Time</th>${spec.series.map(s => html`<th class="num">${s.name}</th>`)}</tr></thead>
      <tbody>${rows.map(t => html`<tr><td>${new Date(t).toLocaleString([], { dateStyle: 'medium', timeStyle: spec.daily ? undefined : 'short' })}</td>${look.map(m => html`<td class="num">${m.has(t) ? spec.fmt(m.get(t)) : ''}</td>`)}</tr>`)}</tbody></table></div>
      ${rows.length >= 400 ? html`<p class="hint">Showing the newest 400 rows.</p>` : ''}</details></section>`;
}
function paintChart(id) {
  const sp = CHARTS[id], box = document.getElementById('cb-' + id), tip = document.getElementById('ct-' + id);
  if (!sp || !box) return;
  const rem = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
  const W = Math.max(300, Math.floor(box.clientWidth)), H = Math.round(clamp(W * .42, 270, 380));
  const m = { l: Math.round(rem * 3.6), r: Math.round(rem * 1.2), t: Math.round(rem * .9), b: Math.round(rem * 2.4) };
  const all = sp.series.flatMap(s => s.pts);
  if (!all.length) { box.innerHTML = rend(html`<div class="empty">No data for this period yet.</div>`); return; }
  const t0 = Math.min(...all.map(p => p[0])), t1 = Math.max(...all.map(p => p[0]));
  let y0 = Math.min(...all.map(p => p[1])), y1 = Math.max(...all.map(p => p[1]));
  (sp.bands || []).forEach(b => { y0 = Math.min(y0, b.lo); y1 = Math.max(y1, b.hi); });
  (sp.refs || []).forEach(r => { y0 = Math.min(y0, r.v); y1 = Math.max(y1, r.v); });
  if (sp.zero) y0 = Math.min(y0, 0);
  if (y1 - y0 < 1) y1 = y0 + 1;
  const step = niceStep(y1 - y0, 5);
  y0 = Math.floor(y0 / step) * step; y1 = Math.ceil(y1 / step) * step;
  if (sp.clamp) { y0 = Math.max(y0, sp.clamp[0]); y1 = Math.min(y1, sp.clamp[1]); }
  const X = t => m.l + (t - t0) / ((t1 - t0) || 1) * (W - m.l - m.r), Y = v => H - m.b - (v - y0) / (y1 - y0) * (H - m.t - m.b);
  const span = (t1 - t0) / DAYMS;
  let g = '';
  for (let v = y0; v <= y1 + 1e-9; v += step) g += `<line class="grid-l" x1="${m.l}" x2="${W - m.r}" y1="${Y(v)}" y2="${Y(v)}"/><text x="${m.l - 8}" y="${Y(v) + 5}" text-anchor="end">${esc(sp.fmt(Math.round(v * 100) / 100))}</text>`;
  g += `<line class="axis-l" x1="${m.l}" x2="${W - m.r}" y1="${H - m.b}" y2="${H - m.b}"/>`;
  xTicks(t0, t1).forEach(t => { g += `<line class="grid-l" x1="${X(t)}" x2="${X(t)}" y1="${H - m.b}" y2="${H - m.b + 6}"/><text x="${X(t)}" y="${H - m.b + rem * 1.5}" text-anchor="middle">${esc(xLabel(t, span))}</text>`; });
  (sp.bands || []).forEach(b => { g += `<rect class="band" x="${m.l}" width="${W - m.l - m.r}" y="${Y(b.hi)}" height="${Math.max(1, Y(b.lo) - Y(b.hi))}"/>`; });
  (sp.refs || []).forEach(r => { g += `<line class="ref-l" x1="${m.l}" x2="${W - m.r}" y1="${Y(r.v)}" y2="${Y(r.v)}"/>`; });
  const gaps = [];
  sp.series.forEach(s => {
    const pts = s.pts.slice().sort((a, b) => a[0] - b[0]);
    const diffs = pts.slice(1).map((p, i) => p[0] - pts[i][0]).sort((a, b) => a - b);
    const lim = (diffs.length ? diffs[Math.floor(diffs.length / 2)] : 3600000) * 3.5;
    gaps.push(lim);
    let d = '', prev = null, runLen = 0;
    pts.forEach(p => {
      if (prev === null || p[0] - prev > lim) { if (runLen === 1) g += `<circle cx="${X(prev)}" cy="${Y(pts.find(q => q[0] === prev)[1])}" r="4" fill="var(--${s.cls})"/>`; d += `M${X(p[0]).toFixed(1)} ${Y(p[1]).toFixed(1)}`; runLen = 1; }
      else { d += `L${X(p[0]).toFixed(1)} ${Y(p[1]).toFixed(1)}`; runLen++; }
      prev = p[0];
    });
    if (runLen === 1 && prev !== null) g += `<circle cx="${X(prev)}" cy="${Y(pts[pts.length - 1][1])}" r="4" fill="var(--${s.cls})"/>`;
    g += `<path class="ln" stroke="var(--${s.cls})" d="${d}"/>`;
  });
  g += `<line class="cross" id="cx-${id}" y1="${m.t}" y2="${H - m.b}" style="display:none"/>` + sp.series.map((s, i) => `<circle id="dot-${id}-${i}" r="5.5" fill="var(--${s.cls})" stroke="var(--sheet)" stroke-width="2" style="display:none"/>`).join('');
  box.innerHTML = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(sp.title)}. The same numbers are in the table below.">${g}</svg>`;
  const svg = box.querySelector('svg');
  const near = (pts, t, lim) => { let best = null; pts.forEach(p => { if (Math.abs(p[0] - t) <= lim && (best === null || Math.abs(p[0] - t) < Math.abs(best[0] - t))) best = p; }); return best; };
  const hide = () => { tip.style.display = 'none'; const c = svg.querySelector('#cx-' + id); if (c) c.style.display = 'none'; sp.series.forEach((s, i) => { const d = svg.querySelector('#dot-' + id + '-' + i); if (d) d.style.display = 'none'; }); };
  box.onpointerleave = hide;
  box.onpointermove = e => {
    const r = svg.getBoundingClientRect(), px = (e.clientX - r.left) * (W / r.width);
    const t = t0 + clamp((px - m.l) / (W - m.l - m.r), 0, 1) * (t1 - t0);
    let anchor = null;
    sp.series.forEach(s => { const p = near(s.pts, t, Infinity); if (p && (anchor === null || Math.abs(p[0] - t) < Math.abs(anchor - t))) anchor = p[0]; });
    if (anchor === null) return;
    const c = svg.querySelector('#cx-' + id); c.setAttribute('x1', X(anchor)); c.setAttribute('x2', X(anchor)); c.style.display = '';
    const lines = [`<strong>${esc(new Date(anchor).toLocaleString([], { dateStyle: 'medium', timeStyle: sp.daily ? undefined : 'short' }))}</strong>`];
    sp.series.forEach((s, i) => {
      const p = near(s.pts, anchor, gaps[i]), d = svg.querySelector('#dot-' + id + '-' + i);
      if (p) { d.setAttribute('cx', X(p[0])); d.setAttribute('cy', Y(p[1])); d.style.display = ''; lines.push(`${esc(s.name)}: ${esc(sp.fmt(p[1]))}${esc(sp.unit || '')}`); } else d.style.display = 'none';
    });
    tip.innerHTML = lines.join('<br>'); tip.style.display = 'block';
    const bx = box.offsetLeft, left = X(anchor) * (r.width / W);
    tip.style.top = (box.offsetTop + 8) + 'px';
    tip.style.left = (left > r.width / 2 ? bx + left - tip.offsetWidth - 14 : bx + left + 14) + 'px';
  };
}
function paintAllCharts() { Object.keys(CHARTS).forEach(paintChart); }

// ---------- forecast and season tables ----------
const MONTHS = ['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar'];
function seasonKeys() { const n = new Date(), y = n.getMonth() >= 6 ? n.getFullYear() : n.getFullYear() - 1; return MONTHS.map((m, i) => [m, (i < 3 ? y : y + 1) + '-' + String([10, 11, 12, 1, 2, 3][i]).padStart(2, '0')]); }
function seasonExpected(ref) {     // the written reference where it applies (Round Rock), otherwise this place's own weather history
  if (ref.applies !== false && (ref.climate || []).length) return { rows: ref.climate, src: 'ref' };
  if (ref.normals) return { rows: ref.normals.months, src: 'history', years: ref.normals.years, since: ref.normals.since };
  return { rows: [], src: 'none' };
}
function seasonTable(ref, monthly) {
  const obs = Object.fromEntries((monthly || []).map(x => [x.month, x]));
  const E = seasonExpected(ref), exp = Object.fromEntries(E.rows.map(c => [c.month, c]));
  const keys = seasonKeys();
  return html`<div class="tbl-wrap"><table class="tbl"><caption class="sr">Expected weather compared with the weather tracked so far this season</caption>
    <thead><tr><th>Month</th><th>Expected low and high</th><th>Tracked low and high</th><th>Expected freezing nights</th><th>Tracked freezing nights</th><th>Expected humidity</th><th>Tracked humidity</th></tr></thead><tbody>
    ${keys.map(([mo, key]) => { const e = exp[mo] || {}, o = obs[key];
      return html`<tr><th scope="row">${mo}</th><td>${e.low != null ? e.low + ' to ' + e.high + '°F' : ''}</td>
        <td>${o ? html`${o.low} to ${o.high}°F<div class="hint">${o.days} days tracked</div>` : html`<span class="muted">Not tracked yet</span>`}</td>
        <td>${e.freeze_nights != null ? e.freeze_nights + ' on average' : ''}</td><td>${o ? o.freeze_nights + (o.days < 28 ? ' so far' : '') : ''}</td>
        <td>${e.rh != null ? (e.rh_pm != null ? e.rh + '% morning, ' + e.rh_pm + '% afternoon' : e.rh + '% average') : ''}</td><td>${o && o.rh != null ? Math.round(o.rh) + '% average' : ''}</td></tr>`; })}</tbody></table></div>
    ${E.src === 'history' ? html`<p class="hint">Expected values for ${placeName()} are averages from its weather history since ${(E.since || '').slice(0, 4)} (${E.years} years or more of every month).</p>`
      : E.src === 'none' ? html`<p class="hint">There is not enough weather history for ${placeName()} yet to fill in the Expected columns. Use Load history on the Weather page (3 years or more).</p>` : ''}`;
}
function forecastBlock(W, plants) {
  const days = (W.forecast && W.forecast.days) || [];
  if (!days.length) return html`<p class="muted">No forecast yet. ${W.status && W.status.error ? 'The last attempt failed: ' + W.status.error : 'The first update runs a few seconds after the app starts, then every hour.'}</p>`;
  const risk = low => plants.filter(p => p.temp_damage_below != null && low < p.temp_damage_below && !isInside(p));
  const coldest = days.reduce((a, b) => (b.low < a.low ? b : a));
  const rs = risk(coldest.low);
  const dName = d => new Date(d + 'T12:00:00').toLocaleDateString([], { weekday: 'long', month: 'short', day: 'numeric' });
  return html`<p class="${coldest.low <= 32 ? 'notice bad' : coldest.low <= 38 ? 'notice' : 'notice ok'}" role="status"><strong>Coldest night in the forecast: ${coldest.low}°F on ${dName(coldest.date)}.</strong>
      ${coldest.low <= 32 ? ' That is a freeze.' : coldest.low <= 38 ? ' Frost is possible in low spots.' : ' No frost expected.'}
      ${rs.length ? ` ${rs.length} of ${plants.filter(p => !isInside(p)).length} plants outside would be damaged by that if they were left outside uncovered.` : ' None of your plants would be damaged by that.'}</p>
    <div class="tbl-wrap"><table class="tbl fc-table"><caption class="sr">Daily forecast</caption><thead><tr><th>Day</th><th class="num">Low</th><th class="num">High</th><th class="num">Humidity</th><th class="num">Daylight</th><th>Plants that would be damaged</th></tr></thead><tbody>
    ${days.map(d => { const r = risk(d.low); return html`<tr><th scope="row">${dName(d.date)}${d.hours < 20 ? html`<div class="hint">rest of the day</div>` : ''}</th>
      <td class="num ${d.low <= 32 ? 'cold' : ''}">${d.low}°F${d.low <= 32 ? ' (freeze)' : ''}</td><td class="num">${d.high}°F</td><td class="num">${d.rh == null ? '' : d.rh + '%'}</td><td class="num">${d.dli} mol/m²</td>
      <td>${r.length ? html`<details><summary>${r.length} plants</summary><ul>${r.map(p => html`<li><a href="#/plant/${enc(p.code)}">${p.common_name}</a>, damage below ${p.temp_damage_below}°F (${p.winter_plan})</li>`)}</ul></details>` : 'None'}</td></tr>`; })}</tbody></table></div>
    <p class="hint">Forecast from Open-Meteo, updated ${W.forecast.fetched_at ? when(W.forecast.fetched_at) : ''}. "Damaged" uses each plant's "damage below" temperature. A night's low can happen at dawn on the next calendar day.</p>`;
}

// ---------- weather page ----------
async function viewWeather() {
  let W;
  try { W = await api('GET', '/api/weather?x=1' + locQS()); }
  catch (e) { if (e.status === 404) { savePlace(null); W = await api('GET', '/api/weather'); } else throw e; }
  const [cond, plants, ing, monthly, ref, st] = await Promise.all([loadCond(), api('GET', '/api/plants'), (ME().role === 'owner' ? api('GET', '/api/ingest').catch(() => null) : null), api('GET', '/api/weather/monthly?x=1' + locQS()), api('GET', '/api/reference'), api('GET', '/api/settings')]);
  WX.places = W.places || []; WX.place = W.location; WX.home = W.home;
  WX.compare = WX.compare.filter(id => WX.places.some(p => String(p.id) === id && String(p.id) !== String(W.location.id)));
  const atHome = W.location.is_home;
  // 1.12.0: sensors send to their own port (8082), which only takes readings; it is closed until opened (README)
  const lanIp = /^\d+\.\d+\.\d+\.\d+$/.test(location.hostname) && !location.hostname.startsWith('127.') ? location.hostname : '';
  const netUrl = `http://${lanIp || '192.168.1.20'}:8082/api/readings`, url = 'http://localhost:8082/api/readings';
  const sample = '{"device":"porch","temp_f":71.2,"humidity":58,"par":240,"soil_moisture":31}';
  const S = W.status || {};
  return {
    title: 'Weather',
    html: html`<h1>Weather and sensors</h1>
    <p class="muted">Tracks the weather for ${WX.places.length > 1 ? `${WX.places.length} places` : W.location.name} from Open-Meteo (free, no account), and takes readings from your own sensors. Everything is stored in your data folder, so the history keeps growing.</p>
    <div class="placebar noprint" role="group" aria-label="Place">
      <label>Location<select data-f="wxplace">${WX.places.map(p => html`<option value="${p.id}" ${String(p.id) === String(W.location.id) ? raw('selected') : ''}>${p.name}${p.is_home ? ' (home)' : ''}</option>`)}</select></label>
      <a class="btn small ghost" href="#sec-places" data-act="gotoplaces">Add or manage places</a>
      <p class="hint" style="flex-basis:100%;margin:0">The same choice as the Location button at the top of every page: plant pages, frost warnings, watering and the Winter plan all use ${W.location.name}${atHome ? '' : html`, not the home place (${W.home.name})`}.</p></div>
    ${condCard(null, cond)}
    <section class="blk"><h2>Next 7 days in ${W.location.name}</h2>${forecastBlock(W, plants)}</section>
    <section class="blk"><h2>Tracked history</h2>
      ${wxControls(plants)}
      <div id="wx-charts"><p class="loading">Loading charts</p></div>
      <p class="hint">${W.weather.count ? `Online weather: ${W.weather.count.toLocaleString()} hourly readings from ${when(W.weather.first)}.` : 'No online weather stored yet.'}
        ${W.sensor.count ? ` Your sensor: ${W.sensor.count.toLocaleString()} readings from ${W.sensor.devices} device${W.sensor.devices === 1 ? '' : 's'}.` : ' No sensor readings yet (see Connect your sensor, below).'}</p></section>
    <section class="blk" id="wx-logged"><h2>All logged weather data${WX.places.length > 1 ? `: ${W.location.name}` : ''}</h2>
      <p class="hint">Every value saved so far, as a table. The first three columns (temperature, humidity, plant light) go back as far as your history does. The other measurements are kept hourly ${W.weather.detail_since ? 'from ' + dayLong(W.weather.detail_since) : 'once collected'} and as daily summaries for all of it.</p>
      ${wtControls()}<div id="wx-table"><p class="loading">Loading table</p></div></section>
    <section class="blk"><h2>Expected and tracked this season in ${W.location.name}</h2>${seasonTable(ref, monthly)}
      <p class="hint">${ref.applies !== false ? `Expected values are 30-year averages for ${W.location.name}. ` : ''}Tracked values come from the readings above: the average of each day's low and high, and how many nights fell to 32°F or below. Days with fewer than 12 readings are skipped.</p></section>
    ${ing ? html`<section class="blk" id="sensor"><h2>Connect your sensor</h2>
      <p>A sensor on your network can send readings to this app. Each reading becomes part of the history above, and "My sensor" can drive the current conditions on every plant page.</p>
      <div class="notice">Sensors on your home network send to this computer's network address on port 8082${lanIp ? '' : ' (for example 192.168.1.20; the README shows how to find yours)'}. That port only takes readings with the token below; the rest of the app stays closed. It is shut until you open it: put the line <span class="code">PLANTDB_SENSOR_BIND=0.0.0.0</span> in a file named .env next to docker-compose.yml, then run docker compose up -d (README, "Connecting your own sensor").</div>
      <dl class="dl"><dt>Address</dt><dd><span class="code">${netUrl}</span></dd><dt>Token</dt><dd><span class="code" id="tok">${ing.token}</span></dd></dl>
      <div class="row noprint" style="margin:.8rem 0"><button class="btn small" type="button" data-act="copytok">Copy token</button><button class="btn danger small" type="button" data-act="tokregen">Make a new token</button></div>
      <p>Send a POST with the header <span class="code">X-Ingest-Token</span> and a JSON body. Every field except one measurement is optional: <span class="code">device</span> (a name, such as porch), <span class="code">ts</span> (UTC time, otherwise now), <span class="code">temp_f</span> or <span class="code">temp_c</span>, <span class="code">humidity</span> (%), <span class="code">par</span> (µmol/m²/s) or <span class="code">lux</span>, <span class="code">soil_moisture</span> (%), <span class="code">soil_temp_f</span> or <span class="code">soil_temp_c</span>, <span class="code">soil_ph</span>. Send up to 500 at once as <span class="code">{"readings":[ ... ]}</span>. Lux is converted to PAR at 54 lux per PAR.</p>
      <h3>Try it from this computer</h3>
      <p>Windows (cmd.exe):</p><pre class="code">curl -X POST ${url} -H "X-Ingest-Token: ${ing.token}" -H "Content-Type: application/json" -d "{\\"device\\":\\"porch\\",\\"temp_f\\":71.2,\\"humidity\\":58,\\"par\\":240}"</pre>
      <p>Windows (PowerShell):</p><pre class="code">Invoke-RestMethod -Method Post -Uri ${url} -Headers @{"X-Ingest-Token"="${ing.token}"} -ContentType "application/json" -Body '${sample}'</pre>
      <p>macOS / Linux (bash):</p><pre class="code">curl -X POST ${url} -H "X-Ingest-Token: ${ing.token}" -H "Content-Type: application/json" -d '${sample}'</pre>
      <p class="hint">Anyone on your network who has the token can add readings, so keep it private. If it leaks, make a new token and update your sensor.</p></section>` : html`<section class="blk" id="sensor"><h2>Connect your sensor</h2><p class="muted">Only ${ME().owner_name} can see the sensor address and token.</p></section>`}
    <section class="blk" id="sec-places"><h2>Places</h2>${placesBlock(W)}</section>
    <section class="blk"><h2>Updates for ${W.location.name}</h2>
      <div id="wx-job" data-running="${W.job && W.job.running ? '1' : '0'}">${jobPanel(W.job)}</div>
      ${runSummary(W)}
      <p class="${S.ok ? 'hint' : S.error ? 'notice bad' : 'hint'}" role="status">${S.at ? html`Latest attempt of any kind ${when(S.at)}: ${S.ok ? 'worked.' : html`<strong>failed.</strong> ${S.error}`}` : 'No update has run yet.'}
        ${W.background ? '' : ' Automatic updates are switched off for this server.'} Weather and history use ${W.db_mb} MB of disk in your data folder.</p>
      <form data-form="wxloc"><div class="field-grid">
        <label class="f">Place name<input type="text" name="name" value="${W.location.name}" maxlength="60"></label>
        <label class="f">Latitude<input type="number" step="any" name="lat" value="${W.location.lat}" min="-90" max="90"></label>
        <label class="f">Longitude<input type="number" step="any" name="lon" value="${W.location.lon}" min="-180" max="180"></label>
        <label class="f">Time zone<input type="text" name="tz" value="${W.location.tz}"></label>
        <label class="f">Years of full hourly detail to keep<small>Every measurement hourly for this many recent years. Older years keep temperature, humidity and light hourly, and everything as daily summaries. Larger numbers use more disk, about 10 MB per year.</small><input type="number" name="detail_years" min="0" max="90" value="${W.weather.detail_years}"></label></div>
        <label class="chk-row" style="border:0"><input type="checkbox" name="enabled" ${W.enabled ? raw('checked') : ''}><span>Update ${W.location.name} every hour</span></label>
        <div class="row"><button class="btn" type="submit">Save this place</button><button class="btn ghost" type="button" data-act="wxrefresh">Update ${W.location.name} now</button>${WX.places.length > 1 ? html`<button class="btn ghost" type="button" data-act="wxrefresh" data-all="1">Update every place now</button>` : ''}</div></form>
      <form data-form="wxback" style="margin-top:1.6rem"><label class="f" style="max-width:24rem">Load older weather history from this date<small>The first update already loads the last 3 months. Pick an earlier date, such as 2025-10-01, to bring in last winter. Open-Meteo's history starts on 1940-01-01. It takes about half a minute per year of history and keeps running if you leave the page. Loading again never duplicates anything.</small><input type="date" name="start" min="1940-01-01" max="${new Date().toISOString().slice(0, 10)}"></label>
        <button class="btn ghost" type="submit">Load history for ${W.location.name}</button></form>
      <details class="runlog" id="wx-runlog" style="margin-top:1.4rem"><summary>Every update that has run (log)</summary><div id="wx-runs"><p class="loading">Loading</p></div></details></section>
    <p class="hint">Weather data by <a href="https://open-meteo.com/" target="_blank" rel="noopener noreferrer">Open-Meteo.com</a>. Light is estimated from solar radiation at about 2.1 PAR per W/m².</p>`,
    after: () => { wxCatalog().then(loadWxCharts); loadWxTable(); loadRunLog(); if (W.job && W.job.running) wxPoll(); },
  };
}
const locQS = () => PLACE ? '&loc=' + enc(PLACE) : '';     // the Weather page shows the place in use (1.11.0)
const WX = { days: 7, period: '7', from: '', to: '', src: 'both', plant: '', show: ['temp', 'hum', 'light'], vars: [], cols: 1, compare: [], places: [] };
try { const v = JSON.parse(localStorage.getItem('plantdb.wxchart') || 'null'); if (v) Object.assign(WX, { period: v.period || '7', from: v.from || '', to: v.to || '', show: Array.isArray(v.show) ? v.show : WX.show, vars: Array.isArray(v.vars) ? v.vars : [], cols: [1, 2, 3].includes(+v.cols) ? +v.cols : 1, compare: Array.isArray(v.compare) ? v.compare.map(String) : [] }); } catch (e) { /* ignore */ }
if (/^\d+$/.test(WX.period)) WX.days = +WX.period;
function wxSave() { try { localStorage.setItem('plantdb.wxchart', JSON.stringify({ period: WX.period, from: WX.from, to: WX.to, show: WX.show, vars: WX.vars, cols: WX.cols, compare: WX.compare })); } catch (e) { /* ignore */ } }
const WX_PERIODS = [['1', 'Last 24 hours'], ['3', 'Last 3 days'], ['7', 'Last 7 days'], ['14', 'Last 14 days'], ['30', 'Last 30 days'], ['90', 'Last 90 days'], ['365', 'Last year'], ['1096', 'Last 3 years'], ['3653', 'Last 10 years'], ['all', 'Everything logged'], ['custom', 'Pick dates']];
const WX_CORE = [['temp', 'Temperature'], ['hum', 'Humidity'], ['light', 'Light (PAR, or daily light)']];
const DAILY_SKIP = ['sunrise', 'sunset'];
let WXCAT = null;
const catOf = k => (WXCAT || []).find(c => c.key === k);
const isDailyKey = k => { const c = (WXCAT || []).filter(x => x.key === k); return c.length && c.every(x => x.kind === 'daily'); };
async function wxCatalog() {
  if (WXCAT) return;
  try { WXCAT = await api('GET', '/api/weather/catalog'); const el = document.getElementById('wx-pick'); if (el) el.innerHTML = rend(wxPickInner()); } catch (e) { /* ignore */ }
}
function wxRangeQS() { return WX.period === 'custom' ? `from=${WX.from || ''}&to=${WX.to || ''}` : WX.period === 'all' ? 'from=1940-01-01' : 'days=' + WX.days; }
function grpBtns(cs) {
  const keys = cs.map(c => c.key).join(',');
  return html`<div class="row grpbtns"><button class="btn small ghost" type="button" data-act="wxgroup" data-keys="${keys}" data-on="1">Tick all</button><button class="btn small ghost" type="button" data-act="wxgroup" data-keys="${keys}" data-on="0">Untick all</button></div>`;
}
function wxPickInner() {
  const box = (key, label, checked, f) => html`<label class="chk-row" style="border:0;padding:.3rem 0"><input type="checkbox" data-f="${f}" data-key="${key}" ${checked ? raw('checked') : ''}><span>${label}</span></label>`;
  const groups = {}, daily = {};
  for (const c of WXCAT || []) {
    if (c.kind === 'hourly' && !['temperature_2m', 'relative_humidity_2m'].includes(c.key)) (groups[c.group] = groups[c.group] || []).push(c);
    if (c.kind === 'daily' && !DAILY_SKIP.includes(c.key) && !(WXCAT || []).some(x => x.kind === 'hourly' && x.key === c.key)) (daily[c.group] = daily[c.group] || []).push(c);
  }
  const lbl = c => c.label + (c.unit ? ' (' + c.unit + ')' : '');
  return html`<fieldset><legend>Main charts</legend>${WX_CORE.map(([k, l]) => box(k, l, WX.show.includes(k), 'wxshow'))}</fieldset>
    ${WXCAT ? html`${Object.entries(groups).map(([g, cs]) => html`<fieldset><legend>${g} (hourly)</legend>${grpBtns(cs)}${cs.map(c => box(c.key, lbl(c), WX.vars.includes(c.key), 'wxvar'))}</fieldset>`)}
      <details class="colpick"><summary>Daily summary values</summary>${Object.entries(daily).map(([g, cs]) => html`<fieldset><legend>${g} (one value per day)</legend>${grpBtns(cs)}${cs.map(c => box(c.key, lbl(c), WX.vars.includes(c.key), 'wxvar'))}</fieldset>`)}</details>` : html`<p class="loading">Loading the list of measurements</p>`}`;
}
let WXBAR = null;               // folded or not for this visit; starts folded on narrow windows and with very large text
function wxBarOpen() { return WXBAR != null ? WXBAR : document.documentElement.dataset.narrow !== '1'; }
function wxControls(plants) {
  const sel = (v, cur) => String(v) === String(cur) ? raw('selected') : '';
  const open = wxBarOpen();
  return html`<div class="wx-bar noprint" id="wx-bar" role="region" aria-label="Chart settings">
    <div class="wx-bar-top"><button class="btn small" type="button" data-act="wxbar" aria-expanded="${open ? 'true' : 'false'}" aria-controls="wx-barbody" id="wx-barbtn">${open ? 'Hide chart settings' : 'Show chart settings'}</button>
      <button class="btn small ghost" type="button" data-act="wxpanel" aria-expanded="false" aria-controls="wx-panel" id="wx-panelbtn">Choose what to chart${WX.places.length > 1 ? ' and compare places' : ''} (<span id="wx-pickcount">${WX.show.length + WX.vars.length}</span>${WX.compare.length ? `, comparing ${WX.compare.length + 1} places` : ''})</button>
      <span class="wx-summary hint" id="wx-sum" role="status"></span></div>
    <div id="wx-barbody" ${open ? '' : raw('hidden')}>
    <div class="wx-bar-row">
      <label>Period<select data-f="wxperiod">${WX_PERIODS.map(([v, l]) => html`<option value="${v}" ${sel(v, WX.period)}>${l}</option>`)}</select></label>
      <span id="wx-dates" class="wx-bar-row" ${WX.period === 'custom' ? '' : raw('hidden')}><label>From<input type="date" data-f="wxfrom" min="1940-01-01" value="${WX.from}"></label><label>To<input type="date" data-f="wxto" min="1940-01-01" value="${WX.to}"></label></span>
      <label>Source<select data-f="wxsrc">${[['both', 'Online weather + my sensor'], ['weather', 'Online weather'], ['sensor', 'My sensor']].map(([v, l]) => html`<option value="${v}" ${sel(v, WX.src)}>${l}</option>`)}</select></label>
      <span class="row-break" aria-hidden="true"></span>
      <label>Plant range<select data-f="wxplant" class="w-fixed" title="Show a plant's comfortable range on the charts"><option value="">None</option>${plants.map(p => html`<option value="${p.code}" ${sel(p.code, WX.plant)} title="${p.code} ${p.common_name}">${p.code} ${p.common_name}</option>`)}</select></label>
      <label>Go to chart<select data-f="wxgoto" id="wx-goto" class="w-fixed"><option value="">Choose a chart</option></select></label>
      <label>Per row<select data-f="wxcols" title="Charts per row">${[1, 2, 3].map(n => html`<option value="${n}" ${sel(n, WX.cols)}>${n}</option>`)}</select></label>
    </div></div>
    <div class="wx-panel" id="wx-panel" hidden>
      <div class="row" style="margin:.2rem 0 .4rem"><button class="btn small" type="button" data-act="wxpanel">Close this list</button><button class="btn small ghost" type="button" data-act="wxmatch">Use the dates and columns from the table below</button><button class="btn small ghost" type="button" data-act="wxclearvars">Remove the extra measurements</button></div>
      <p class="hint">Tick as many as you like; the charts update a moment after you stop. Measurements with the same unit share a chart (three per chart at most). Many measurements over a long period can take several seconds to draw.</p>
      <div class="row" style="margin:.4rem 0"><button class="btn small ghost" type="button" data-act="wxallvars" data-which="hourly">Tick every hourly measurement</button><button class="btn small ghost" type="button" data-act="wxallvars" data-which="daily">Tick every daily summary value</button></div>
      ${WX.places.length > 1 ? html`<fieldset class="cmp-places"><legend>Compare ${WX.place ? WX.place.name : 'this place'} with</legend><p class="hint" style="grid-column:1/-1;margin:0">Each chart gets one line per place (up to 6 places).</p>${WX.places.filter(p => String(p.id) !== String((WX.place || {}).id)).map(p => html`<label class="chk-row" style="border:0;padding:.3rem 0"><input type="checkbox" data-f="wxcmp" data-key="${p.id}" ${WX.compare.includes(String(p.id)) ? raw('checked') : ''}><span>${p.name}${p.is_home ? ' (home)' : ''}</span></label>`)}</fieldset>` : ''}
      <div id="wx-pick">${wxPickInner()}</div></div></div>`;
}
const BUCKET_WORDS = { hour: 'hourly', day: 'daily', week: 'weekly', month: 'monthly' };
async function seriesMulti(base, vars) {
  // web addresses have a length limit, so many measurements are fetched 30 at a time and joined back together
  if (vars.length <= 30) return api('GET', base + (vars.length ? '&vars=' + vars.join(',') : ''));
  const parts = [];
  for (let i = 0; i < vars.length; i += 30) parts.push(vars.slice(i, i + 30));
  const res = await Promise.all(parts.map(p => api('GET', base + '&vars=' + p.join(','))));
  const out = res[0], byT = new Map(out.points.map(p => [p.t, p]));
  for (const r of res.slice(1)) {
    Object.assign(out.vars, r.vars);
    for (const p of r.points) { const q = byT.get(p.t); if (q) q.x = Object.assign(q.x || {}, p.x); else { out.points.push(p); byT.set(p.t, p); } }
  }
  out.points.sort((a, b) => a.t < b.t ? -1 : 1);
  return out;
}
function finishCharts(el, cards, sources, bucket, keepY, done, extraNote) {
  const ts = sources.filter(Boolean).flatMap(r => r.points.map(p => Date.parse(p.t)));
  const span = ts.length ? [Math.min(...ts), Math.max(...ts)] : null;
  const dfmt = t => new Date(t).toLocaleDateString([], { dateStyle: 'medium' });
  const sum = document.getElementById('wx-sum');
  done(); el.className = 'cols-' + WX.cols;
  el.innerHTML = rend(html`<div class="wx-grid">${cards.length ? cards : html`<p class="notice">Nothing chosen. Press "Choose what to chart" and tick at least one measurement.</p>`}</div>`);
  if (sum) sum.textContent = (span ? `Data shown: ${dfmt(span[0])} to ${dfmt(span[1])}. ` : 'No data in this period. ') + (bucket === 'hour' ? 'One point per hour. ' : `One point per ${bucket} (${BUCKET_WORDS[bucket]} values). `) + (extraNote || '') + `${el.querySelectorAll('.chart-card').length} charts.`;
  const go = document.getElementById('wx-goto');
  if (go) go.innerHTML = rend(html`<option value="">Choose a chart</option>${[...el.querySelectorAll('.chart-card h3')].map(h => html`<option value="${h.closest('.chart-card').getAttribute('aria-labelledby')}">${h.textContent}</option>`)}`);
  paintAllCharts(); navLayout();
  requestAnimationFrame(() => { el.style.minHeight = ''; if (Math.abs(window.scrollY - keepY) > 2) window.scrollTo(0, keepY); });
}
function drawCompare(el, o) {
  // one line per place on every chart; your sensor joins in when the home place is one of them
  const placesR = [{ name: o.here.name, r: o.w, d: o.dx }, ...o.others.map((p, i) => ({ name: p.name, r: o.cmp[i], d: o.cmpd[i] }))];
  const bucket = (o.w || o.cmp[0] || {}).bucket || 'hour', day = bucket !== 'hour', per = BUCKET_WORDS[bucket];
  const col = (r, k) => r ? r.points.filter(p => p[k] != null).map(p => [Date.parse(p.t), p[k]]) : [];
  const dli = r => r ? r.points.filter(p => p.par != null && (bucket !== 'day' || p.n >= 12)).map(p => [Date.parse(p.t), Math.round(p.par * 86400 / 1e5) / 10]) : [];
  const withSensor = (list, pts) => (o.s && pts.length ? [...list, { name: 'My sensor', pts }] : list);
  const colour = list => list.map((x, i) => ({ ...x, cls: 's' + (i % 6 + 1) }));
  const band = (lo, hi, label) => has(lo) && has(hi) ? [{ lo, hi, label }] : [];
  const pl = o.pl, nm = pl ? pl.common_name : '';
  const cards = [];
  const avg = day ? `, ${per} average` : '';
  if (WX.show.includes('temp')) {
    const refs = [{ v: 32, label: 'Freezing (32°F)' }];
    if (pl && has(pl.temp_damage_below)) refs.push({ v: pl.temp_damage_below, label: `${nm}: damage below ${pl.temp_damage_below}°F` });
    cards.push(chartCard('wx-temp', { title: `Temperature (°F${avg})`, series: colour(withSensor(placesR.map(p => ({ name: p.name, pts: col(p.r, 'temp_f') })), col(o.s, 'temp_f'))), fmt: v => String(Math.round(v * 10) / 10), unit: '°F', refs, bands: pl ? band(pl.temp_ideal_low, pl.temp_ideal_high, nm + ': comfortable range') : [], daily: day }));
    if (day) {
      cards.push(chartCard('wx-tlow', { title: `Lowest temperature in each ${bucket} (°F)`, series: colour(placesR.map(p => ({ name: p.name, pts: col(p.r, 'temp_min') }))), fmt: v => String(Math.round(v * 10) / 10), unit: '°F', refs, daily: day }));
      cards.push(chartCard('wx-thigh', { title: `Highest temperature in each ${bucket} (°F)`, series: colour(placesR.map(p => ({ name: p.name, pts: col(p.r, 'temp_max') }))), fmt: v => String(Math.round(v * 10) / 10), unit: '°F', daily: day }));
    }
  }
  if (WX.show.includes('hum')) cards.push(chartCard('wx-hum', { title: `Humidity (%${avg})`, series: colour(withSensor(placesR.map(p => ({ name: p.name, pts: col(p.r, 'humidity') })), col(o.s, 'humidity'))), fmt: v => String(Math.round(v)), unit: '%', clamp: [0, 100], bands: pl ? band(pl.humidity_low, pl.humidity_high, nm + ': comfortable range') : [], daily: day }));
  if (WX.show.includes('light')) cards.push(chartCard('wx-light', day ? { title: 'Daily light (mol/m² per day; open sky)', series: colour(withSensor(placesR.map(p => ({ name: p.name, pts: dli(p.r) })), dli(o.s))), fmt: v => String(Math.round(v * 10) / 10), unit: ' mol/m²', zero: true, bands: pl ? band(pl.dli_low, pl.dli_high, nm + ': comfortable range') : [], daily: day }
    : { title: 'Light (PAR, µmol/m²/s)', series: colour(withSensor(placesR.map(p => ({ name: p.name, pts: col(p.r, 'par') })), col(o.s, 'par'))), fmt: v => String(Math.round(v * 10) / 10), unit: ' PAR', zero: true, daily: day }));
  let ci = 0;
  for (const [key, isD] of [...o.hourlyVars.map(k => [k, false]), ...o.dailyVars.map(k => [k, true])]) {
    const src = placesR.map(p => isD ? p.d : p.r), m = (src.find(r => r && r.vars && r.vars[key]) || { vars: {} }).vars[key] || { label: key, unit: '', agg: 'avg' };
    const how = bucket === 'hour' && !isD ? '' : ` (${per} ${m.agg === 'sum' ? 'total' : m.agg === 'max' && !isD ? 'highest' : 'average'})`;
    const series = colour(placesR.map((p, i) => ({ name: p.name, pts: src[i] ? src[i].points.filter(q => q.x && q.x[key] != null).map(q => [Date.parse(q.t), q.x[key]]) : [] })));
    const zero = !/temperature|dew|wet_bulb|apparent|pressure|direction|lifted|height/.test(key);
    cards.push(chartCard('wx-x' + (ci++), { title: m.label + how + (m.unit ? ` (${m.unit})` : ''), series, fmt: v => String(Math.round(v * 100) / 100), unit: m.unit ? ' ' + m.unit : '', zero, daily: day || isD }));
    const empty = series.filter(x => !x.pts.length);
    if (empty.length) cards.push(html`<p class="hint">No ${m.label.toLowerCase()} values for ${empty.map(x => x.name).join(' or ')} in this period. Show that place and use Load history to fetch them.</p>`);
  }
  finishCharts(el, cards, [o.w, o.s, o.dx, ...o.cmp], bucket, o.keepY, o.done, `Comparing ${placesR.map(p => p.name).join(', ')}. `);
}
async function loadWxCharts() {
  const el = document.getElementById('wx-charts'); if (!el) return;
  if (WX.period === 'custom' && (!WX.from || !WX.to)) { el.innerHTML = rend(html`<p class="notice">Pick a From and a To date.</p>`); return; }
  if (WX.period === 'custom' && WX.from > WX.to) { el.innerHTML = rend(html`<p class="notice bad">The From date is after the To date.</p>`); return; }
  const sm = document.getElementById('wx-sum'); if (sm) sm.textContent = 'Loading charts…';
  // Keep the current charts on screen (dimmed) while the new ones load, so the page does not shrink and jump.
  const myReq = WX.req = (WX.req || 0) + 1, keepY = window.scrollY;
  if (el.querySelector('.chart-card')) { el.style.minHeight = el.offsetHeight + 'px'; el.classList.add('busy'); el.setAttribute('aria-busy', 'true'); }
  else el.innerHTML = rend(html`<p class="loading" role="status">Loading charts${WX.period === 'all' || +WX.days > 3000 ? ' (a long period can take a few seconds)' : ''}</p>`);
  const done = () => { el.classList.remove('busy'); el.removeAttribute('aria-busy'); };
  const want = s => WX.src === 'both' || WX.src === s;
  const rq = wxRangeQS();
  const hourlyVars = WX.vars.filter(k => !isDailyKey(k)), dailyVars = WX.vars.filter(isDailyKey);
  let w, s, pl, dx, cmp = [];
  const others = (WX.compare || []).map(id => WX.places.find(p => String(p.id) === id)).filter(Boolean);
  const here = WX.place || { name: 'Online weather', is_home: true };
  try {
    [w, s, pl, ...cmp] = await Promise.all([want('weather') || WX.vars.length || others.length ? seriesMulti(`/api/readings/series?source=weather&${rq}${locQS()}`, hourlyVars) : null,
      want('sensor') && here.is_home ? api('GET', '/api/readings/series?source=sensor&' + rq) : null, WX.plant ? api('GET', '/api/plants/' + enc(WX.plant)) : null,
      ...others.map(o => seriesMulti(`/api/readings/series?source=weather&${rq}&loc=${o.id}`, hourlyVars))]);
    const bk = (w || s || cmp[0]).bucket === 'hour' ? 'day' : (w || s || cmp[0]).bucket;
    if (dailyVars.length) [dx, ...cmp.dx] = await Promise.all([seriesMulti(`/api/readings/series?source=weather&${rq}&bucket=${bk}${locQS()}`, dailyVars), ...others.map(o => seriesMulti(`/api/readings/series?source=weather&${rq}&bucket=${bk}&loc=${o.id}`, dailyVars))]);
  } catch (e) { if (myReq !== WX.req) return; done(); el.style.minHeight = ''; el.innerHTML = rend(html`<p class="notice bad">${e.message}</p>`); return; }
  if (myReq !== WX.req) return;                 // a newer choice was made while this one loaded
  if (others.length) return drawCompare(el, { w, s, pl, dx, cmp, cmpd: cmp.dx || [], others, here, hourlyVars, dailyVars, keepY, done });
  const wCore = want('weather') ? w : null;
  const bucket = ((w || s) || {}).bucket || 'hour', day = bucket !== 'hour';
  const both = !!(wCore && s);
  const col = (r, k, f) => r.points.filter(p => p[k] != null && (!f || f(p))).map(p => [Date.parse(p.t), p[k]]);
  const mk = (key, names) => { const out = []; const sp = s ? col(s, key) : []; if (s && (sp.length || !wCore)) out.push({ name: names.sensor, cls: 's1', pts: sp }); if (wCore) out.push({ name: names.weather, cls: 's2', pts: col(wCore, key) }); return out; };
  const N = { weather: WX.places.length > 1 ? `Online weather, ${here.name}` : 'Online weather', sensor: 'My sensor' };
  const per = { day: 'Daily', week: 'Weekly', month: 'Monthly' }[bucket] || '';
  let tempSeries;
  if (day && !both) { const r = wCore || s; tempSeries = r ? [{ name: bucket === 'day' ? 'Daily low' : `Lowest in the ${bucket}`, cls: 's1', pts: col(r, 'temp_min') }, { name: bucket === 'day' ? 'Daily high' : `Highest in the ${bucket}`, cls: 's2', pts: col(r, 'temp_max') }] : []; }
  else tempSeries = mk('temp_f', N);
  const band = (lo, hi, label) => has(lo) && has(hi) ? [{ lo, hi, label }] : [];
  const nm = pl ? pl.common_name : '';
  const refs = [{ v: 32, label: 'Freezing (32°F)' }];
  if (pl && has(pl.temp_damage_below)) refs.push({ v: pl.temp_damage_below, label: `${nm}: damage below ${pl.temp_damage_below}°F` });
  const cards = [];
  if ((wCore || s) && WX.show.includes('temp')) cards.push(chartCard('wx-temp', { title: 'Temperature (°F)' + (per && both ? `, ${per.toLowerCase()} average` : ''), series: tempSeries, fmt: v => String(Math.round(v * 10) / 10), unit: '°F', refs, bands: pl ? band(pl.temp_ideal_low, pl.temp_ideal_high, nm + ': comfortable range') : [], daily: day }));
  if ((wCore || s) && WX.show.includes('hum')) cards.push(chartCard('wx-hum', { title: 'Humidity (%)' + (per ? `, ${per.toLowerCase()} average` : ''), series: mk('humidity', N), fmt: v => String(Math.round(v)), unit: '%', clamp: [0, 100], bands: pl ? band(pl.humidity_low, pl.humidity_high, nm + ': comfortable range') : [], daily: day }));
  if ((wCore || s) && WX.show.includes('light')) {
    const dli = r => r.points.filter(p => p.par != null && (bucket !== 'day' || p.n >= 12)).map(p => [Date.parse(p.t), Math.round(p.par * 86400 / 1e5) / 10]);
    const lightSeries = day ? [s && (dli(s).length || !wCore) && { name: N.sensor, cls: 's1', pts: dli(s) }, wCore && { name: N.weather, cls: 's2', pts: dli(wCore) }].filter(Boolean) : mk('par', N);
    cards.push(chartCard('wx-light', { title: day ? `Daily light (mol/m² per day${bucket !== 'day' ? `, average over each ${bucket}` : ''}; open sky for online weather)` : 'Light (PAR, µmol/m²/s)', series: lightSeries, fmt: v => String(Math.round(v * 10) / 10), unit: day ? ' mol/m²' : ' PAR', zero: true,
      bands: pl ? (day ? band(pl.dli_low, pl.dli_high, nm + ': comfortable range') : band(pl.par_low, pl.par_high, nm + ': comfortable range')) : [], daily: day }));
  }
  // extra measurements, grouped by unit, three to a chart
  const extras = [];
  for (const [res, keys] of [[w, hourlyVars], [dx, dailyVars]]) {
    if (!res) continue;
    for (const k of keys) {
      const m = (res.vars || {})[k] || { label: k, unit: '', agg: 'avg' };
      const how = res.bucket === 'hour' ? '' : m.agg === 'sum' ? `${BUCKET_WORDS[res.bucket]} total` : m.agg === 'max' ? `${BUCKET_WORDS[res.bucket]} highest` : `${BUCKET_WORDS[res.bucket]} average`;
      extras.push({ key: k, unit: m.unit || '', name: m.label + (how && !isDailyKey(k) ? ` (${how})` : isDailyKey(k) && res.bucket !== 'day' ? ` (${BUCKET_WORDS[res.bucket]} ${m.agg === 'sum' ? 'total' : 'average'})` : ''), daily: res.bucket !== 'hour', fromDaily: m.from_daily,
        pts: res.points.filter(p => p.x && p.x[k] != null).map(p => [Date.parse(p.t), p.x[k]]) });
    }
  }
  const byUnit = {};
  extras.forEach(x => (byUnit[x.unit + '|' + x.daily] = byUnit[x.unit + '|' + x.daily] || []).push(x));
  let ci = 0;
  for (const list of Object.values(byUnit)) {
    for (let i = 0; i < list.length; i += 3) {
      const part = list.slice(i, i + 3), u = part[0].unit;
      const zero = !part.some(x => /temperature|dew|wet_bulb|apparent|pressure|direction|lifted|height/.test(x.key));
      cards.push(chartCard('wx-x' + (ci++), { title: part.map(x => x.name).join(', ') + (u ? ` (${u})` : ''), series: part.map((x, j) => ({ name: x.name, cls: 's' + (j + 1), pts: x.pts })), fmt: v => String(Math.round(v * 100) / 100), unit: u ? ' ' + u : '', zero, daily: part[0].daily }));
      const empty = part.filter(x => !x.pts.length), daily2 = part.filter(x => x.fromDaily);
      if (empty.length) cards.push(html`<p class="hint">No values for ${empty.map(x => x.name).join(', ')} in this period. Use Load history to fetch them; the table below shows what is stored.</p>`);
      if (daily2.length) cards.push(html`<p class="hint">For older years ${daily2.map(x => x.name).join(', ')} come${daily2.length === 1 ? 's' : ''} from the daily summaries, because hourly detail is only kept for recent years.</p>`);
    }
  }
  const ts = [w, s, dx].filter(Boolean).flatMap(r => r.points.map(p => Date.parse(p.t)));
  const span = ts.length ? [Math.min(...ts), Math.max(...ts)] : null;
  const dfmt = t => new Date(t).toLocaleDateString([], { dateStyle: 'medium' });
  const sum = document.getElementById('wx-sum');
  if (sum) sum.textContent = (span ? `Data shown: ${dfmt(span[0])} to ${dfmt(span[1])}. ` : 'No data in this period. ') + (bucket === 'hour' ? 'One point per hour. ' : `One point per ${bucket} (${BUCKET_WORDS[bucket]} values). `);
  done(); el.className = 'cols-' + WX.cols;
  el.innerHTML = rend(html`<div class="wx-grid">${cards.length ? cards : html`<p class="notice">Nothing chosen. Press "Choose what to chart" and tick at least one measurement.</p>`}${s && s.points.length === 0 && want('sensor') ? html`<p class="hint">No sensor readings in this period yet.</p>` : ''}</div>`);
  const go = document.getElementById('wx-goto');
  if (go) go.innerHTML = rend(html`<option value="">Choose a chart</option>${[...el.querySelectorAll('.chart-card h3')].map(h => html`<option value="${h.closest('.chart-card').getAttribute('aria-labelledby')}">${h.textContent}</option>`)}`);
  if (sum) sum.textContent += `${el.querySelectorAll('.chart-card').length} charts.`;
  paintAllCharts(); navLayout();
  requestAnimationFrame(() => { el.style.minHeight = ''; if (Math.abs(window.scrollY - keepY) > 2) window.scrollTo(0, keepY); });   // stay where you were
}

// ---------- places ----------
function placesBlock(W) {
  const P = W.places || [];
  return html`<p>Track the weather for as many places as you like. Each place keeps its own hourly readings, daily summaries, forecast and update log. The <strong>Location</strong> button at the top of every page chooses the place this browser uses for weather, frost warnings, watering and the Winter plan. The home place is the one a browser starts with, and the one hourly updates and backups use.</p>
    <div class="tbl-wrap"><table class="tbl"><caption class="sr">Places with tracked weather</caption><thead><tr><th scope="col">Place</th><th scope="col">Where</th><th scope="col">Stored</th><th scope="col">Last update</th><th scope="col">Hourly updates</th><th scope="col"><span class="sr">Actions</span></th></tr></thead><tbody>
    ${P.map(p => html`<tr><th scope="row">${p.name}${p.is_home ? html`<div><strong class="tag-home">Home</strong></div>` : ''}${String(p.id) === String(W.location.id) ? html`<div class="hint">In use in this browser</div>` : ''}</th>
      <td>${p.lat}, ${p.lon}<div class="hint">${p.tz}</div></td>
      <td>${p.count ? `${num(p.count)} hourly readings from ${dayLong((p.first || '').slice(0, 10))}` : 'Nothing yet'}${p.daily_count ? html`<div class="hint">${num(p.daily_count)} daily summaries</div>` : ''}</td>
      <td>${p.last_update ? html`${when(p.last_update)}${p.last_ok === false ? html`<div class="bad-text"><strong>Failed:</strong> ${p.last_error}</div>` : ''}` : 'Not yet'}</td>
      <td>${p.enabled ? 'On' : 'Off'}</td>
      <td><div class="row" style="gap:.4rem">
        ${String(p.id) === String(W.location.id) ? '' : html`<button class="btn small" type="button" data-act="placeshow" data-id="${p.id}">Use this place</button>`}
        ${p.is_home ? '' : html`<button class="btn small ghost" type="button" data-act="placehome" data-id="${p.id}">Make home</button>`}
        <button class="btn small ghost" type="button" data-act="placeonoff" data-id="${p.id}" data-on="${p.enabled ? '0' : '1'}">${p.enabled ? 'Stop hourly updates' : 'Start hourly updates'}</button>
        ${p.is_home ? '' : html`<button class="btn small danger" type="button" data-act="placedel" data-id="${p.id}">Remove</button>`}</div></td></tr>`)}</tbody></table></div>
    <h3>Add a place</h3>
    <form class="todo-add" data-form="placesearch"><label style="flex:1 1 18rem;font-weight:700">Town or city<input type="text" name="q" placeholder="Baraboo" autocomplete="off"></label><button class="btn" type="submit" style="align-self:end">Search</button></form>
    <div id="place-results" aria-live="polite"></div>
    <details class="colpick"><summary>Or type the place in yourself</summary>
      <form data-form="placeadd"><div class="field-grid">
        <label class="f">Name<input type="text" name="name" maxlength="60" required></label>
        <label class="f">Latitude<input type="number" step="any" name="lat" min="-90" max="90" required></label>
        <label class="f">Longitude<input type="number" step="any" name="lon" min="-180" max="180" required></label>
        <label class="f">Time zone<small>For example America/Chicago</small><input type="text" name="tz" value="${(W.home || {}).tz || ''}" required></label></div>
        <button class="btn" type="submit">Add this place</button></form></details>
    <p class="hint">A new place gets its last 3 months and forecast straight away, then updates every hour. Use Load history (below, with that place shown) for older years.</p>`;
}
async function addPlace(body) {
  if (!(await needName())) return;
  await guard(async () => {
    let r;
    try { r = await api('POST', '/api/places', body); }
    catch (e) { if (e.status === 409 && (await confirmBox('Add it anyway?', e.message + '. Add a second place at the same spot?', 'Add anyway'))) r = await api('POST', '/api/places', { ...body, force: true }); else throw e; }
    placeChanged(String(r.place.id));
    toast(`${r.place.name} added and in use. Fetching its last 3 months and forecast now.`);
    document.body.dataset.job = '1'; await route(); wxPoll();
  });
}
function setPlace(id) {
  placeChanged(id);
  return route();
}

// ---------- weather: update log and the table of everything logged ----------
const WMO = { 0: 'Clear', 1: 'Mostly clear', 2: 'Partly cloudy', 3: 'Overcast', 45: 'Fog', 48: 'Freezing fog', 51: 'Light drizzle', 53: 'Drizzle', 55: 'Heavy drizzle', 56: 'Freezing drizzle', 57: 'Heavy freezing drizzle',
  61: 'Light rain', 63: 'Rain', 65: 'Heavy rain', 66: 'Freezing rain', 67: 'Heavy freezing rain', 71: 'Light snow', 73: 'Snow', 75: 'Heavy snow', 77: 'Snow grains', 80: 'Light showers', 81: 'Showers', 82: 'Heavy showers',
  85: 'Light snow showers', 86: 'Heavy snow showers', 95: 'Thunderstorm', 96: 'Thunderstorm with hail', 99: 'Severe thunderstorm with hail' };
const TRIGGER_WORDS = { auto: 'Automatic (hourly)', 'auto-first': 'Automatic (first run)', 'update-now': 'You pressed Update now', 'load-history': 'You pressed Load history', earlier: 'Before logging began' };
const compass = d => ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'][Math.round(d / 22.5) % 16];
const dayLong = d => d ? new Date(d + 'T12:00:00').toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' }) : '';
const num = n => Number(n).toLocaleString();
function runWhat(r) {
  if (r.kind === 'earlier') return 'Temperature, humidity and sunlight only';
  if (r.kind === 'history' && r.ok && !r.hourly_rows && !r.daily_days) return 'Nothing new was needed';
  const parts = [];
  parts.push(`${num(r.hourly_rows)} hourly reading${r.hourly_rows === 1 ? '' : 's'}` + (r.hourly_rows ? ` (${num(r.hourly_new)} new)` : ''));
  if (r.daily_days) parts.push(`${num(r.daily_days)} daily summar${r.daily_days === 1 ? 'y' : 'ies'} (${num(r.daily_new)} new)`);
  if (r.vars_ok) parts.push(`${r.vars_ok} kinds of measurement`);
  return parts.join(', ');
}
function runRange(r) { return r.range_start ? (r.range_start === r.range_end ? dayLong(r.range_start) : `${dayLong(r.range_start)} to ${dayLong(r.range_end)}`) : ''; }
function runLine(label, r, none) {
  if (!r) return html`<li><strong>${label}:</strong> ${none}</li>`;
  return html`<li><strong>${label}:</strong> ${when(r.ran_at)}. ${r.ok ? '' : html`<strong>Failed:</strong> ${r.error} `}${runRange(r) ? 'Covered ' + runRange(r) + '. ' : ''}${runWhat(r)}.
    ${r.vars_missing && r.vars_missing.length ? html`<details class="inline"><summary>${r.vars_missing.length} measurements Open-Meteo does not offer for this period</summary><p>${r.vars_missing.join(', ')}</p></details>` : ''}${r.note ? html` <span class="hint">${r.note}</span>` : ''}</li>`;
}
function runSummary(W) {
  const R = W.runs || {};
  const idle = R.history && R.history.ok && !R.history.hourly_rows;
  const hist = R.history ? html`${runLine(idle ? 'Last time Load history was pressed' : 'Last Load history', R.history, '')}${idle && R.history_ok ? runLine('Last Load history that fetched new data', R.history_ok, '') : ''}` : runLine('Last Load history', null, R.earlier ? 'none since the update log began. Before then, ' + num(R.earlier.hourly_rows) + ' hourly readings (' + runRange(R.earlier) + ') were collected by the first load and the hourly updates, with temperature, humidity and sunlight only.' : 'none yet.');
  return html`<ul class="runs">${hist}${runLine('Last automatic update', R.auto, 'none yet. The first one runs a few seconds after the app starts.')}</ul>`;
}
function dur(sec) {
  sec = Math.max(0, Math.round(sec));
  if (sec < 60) return sec + ' seconds';
  const m = Math.floor(sec / 60), h = Math.floor(m / 60);
  return h ? `${h} hour${h === 1 ? '' : 's'} ${m % 60} minute${m % 60 === 1 ? '' : 's'}` : `${m} minute${m === 1 ? '' : 's'}`;
}
function jobNumbers(j) {
  const t = j.now_ts || Date.now() / 1000;
  const elapsed = j.started_ts ? t - j.started_ts : 0, quiet = j.beat ? t - j.beat : 0;
  const hist = j.phase === 'history' && j.total;
  const pct = hist ? Math.floor(100 * j.done / j.total) : j.phase === 'recent' && j.total ? 99 : 0;
  const fetched = j.done - (j.skipped || 0);                   // periods actually downloaded so far
  const left = hist && fetched > 0 && j.done < j.total ? elapsed / Math.max(fetched, 1) * (j.total - j.done) : null;
  return { elapsed, quiet, pct, left, hist };
}
function jobPanel(j) {
  if (!j || !j.running) return j && j.finished ? html`<p class="${j.ok ? 'notice ok' : 'notice bad'}" role="status">${j.trigger === 'load-history' ? 'Load history' : 'Update'} ${j.ok ? 'finished' : 'stopped'} ${when(j.finished)}. ${j.error || ''}</p>` : '';
  const n = jobNumbers(j);
  const at = j.place ? ` for ${j.place}` : '';
  const what = (j.trigger === 'load-history' ? 'Loading history' : 'Updating the weather') + at + (j.places_total > 1 ? ` (place ${j.place_no} of ${j.places_total})` : '');
  const waiting = j.waiting_until && j.waiting_until > (j.now_ts || 0);
  return html`<div class="notice jobbox" role="group" aria-label="${what}">
    <p class="jobhead"><strong>${what}: ${n.hist ? n.pct + '% done' : j.phase === 'recent' ? 'last step' : 'starting'}</strong></p>
    <progress max="100" value="${n.pct}" aria-label="${what}, ${n.pct} percent done">${n.pct}%</progress>
    <dl class="jobdl">
      ${n.hist ? html`<dt>Year-long periods</dt><dd>${num(Math.min(j.done + 1, j.total))} of ${num(j.total)}${j.skipped ? `, ${num(j.skipped)} already stored and skipped` : ''}</dd>` : ''}
      <dt>Working on</dt><dd>${j.phase === 'recent' ? 'the last 3 months and the forecast' : j.label ? j.label.replace(/(\d{4})-(\d{2})-(\d{2})/g, (m) => dayLong(m)) : 'starting'}${j.step ? ' (' + j.step + ')' : ''}</dd>
      <dt>Saved so far</dt><dd>${num(j.hourly_saved || 0)} hourly readings, ${num(j.daily_saved || 0)} daily summaries</dd>
      <dt>Running for</dt><dd>${dur(n.elapsed)}</dd>
      ${j.retries ? html`<dt>Dropped connections</dt><dd>${num(j.retries)} so far, each retried automatically</dd>` : ''}
      ${n.left != null ? html`<dt>Time left</dt><dd>about ${dur(n.left)}</dd>` : ''}
      <dt>Last activity</dt><dd>${waiting ? html`<strong>Pausing: ${j.waiting_why || "Open-Meteo's per-minute limit"}</strong>, carrying on in ${dur(j.waiting_until - j.now_ts)}` : n.quiet < 5 ? 'just now' : dur(n.quiet) + ' ago'}${!waiting && n.quiet > 120 ? html`<div class="hint">Nothing for a while. Open-Meteo may be slow; it gives up on a request after 40 seconds and the error is then shown here.</div>` : ''}</dd>
    </dl>
    <p class="hint">It keeps running if you leave this page or close the browser. A small "Loading history" box at the bottom left of every page shows the percentage.</p></div>`;
}
let JOBT = null;
async function wxPoll() {
  clearTimeout(JOBT);
  let j; try { j = await api('GET', '/api/weather/job'); } catch (e) { JOBT = setTimeout(wxPoll, 6000); return; }
  const el = document.getElementById('wx-job');
  const was = document.body.dataset.job === '1';
  document.body.dataset.job = j.running ? '1' : '0';
  if (el) el.innerHTML = rend(jobPanel(j));
  jobBadge(j);
  if (j.running) JOBT = setTimeout(wxPoll, el ? 2000 : 5000);
  else if (was) { toast(j.ok ? (j.trigger === 'load-history' ? 'Load history finished' : 'Weather update finished') : 'Weather update stopped: ' + (j.error || ''), !j.ok); if (location.hash.startsWith('#/weather')) route(); }
}
function jobBadge(j) {
  let b = document.getElementById('job-badge');
  if (!j || !j.running) { if (b) { b.remove(); conLayout(); } return; }
  if (!b) { b = document.createElement('a'); b.id = 'job-badge'; b.href = '#/weather'; b.className = 'noprint'; document.body.appendChild(b); setTimeout(conLayout, 0); }
  const n = jobNumbers(j);
  b.textContent = (j.trigger === 'load-history' ? 'Loading history' : 'Updating weather') + (j.place ? ` for ${j.place}` : '') + (j.places_total > 1 ? ` (${j.place_no} of ${j.places_total})` : '') + ': ' + (n.hist ? n.pct + '%' : '…') + (n.left != null ? ', about ' + dur(n.left) + ' left' : '');
  b.setAttribute('aria-label', b.textContent + '. Open the Weather page for details.');
}
async function loadRunLog() {
  const el = document.getElementById('wx-runs'); if (!el) return;
  const runs = await api('GET', '/api/weather/runs?n=200' + locQS());
  el.innerHTML = rend(html`<div class="tbl-wrap"><table class="tbl"><caption class="sr">Every weather update, newest first</caption><thead><tr><th>When</th><th>Started by</th><th>Dates covered</th><th>Result</th><th>Added</th><th>Not offered</th></tr></thead><tbody>
    ${runs.map(r => html`<tr><th scope="row">${when(r.ran_at)}</th><td>${TRIGGER_WORDS[r.trigger] || r.trigger}${r.kind === 'history' ? html`<div class="hint">older history</div>` : r.kind === 'recent' ? html`<div class="hint">last 3 months + forecast</div>` : ''}</td><td>${runRange(r)}</td>
      <td>${r.ok ? 'Worked' : html`<strong>Failed</strong><div class="hint">${r.error}</div>`}${r.seconds ? html`<div class="hint">${Math.round(r.seconds)} s</div>` : ''}</td>
      <td>${runWhat(r)}${r.note ? html`<div class="hint">${r.note}</div>` : ''}</td>
      <td>${r.vars_missing && r.vars_missing.length ? html`<details><summary>${r.vars_missing.length}</summary><p class="hint">${r.vars_missing.join(', ')}</p></details>` : ''}</td></tr>`)}</tbody></table></div>`);
}

const WT = { kind: 'hourly', from: '', to: '', order: 'desc', per: 50, page: 1, hide: null };
try { const n = +localStorage.getItem('plantdb.wxper'); if (n >= 10 && n <= 1000) WT.per = n; } catch (e) { /* ignore */ }
function wtHidden() {
  if (WT.hide) return WT.hide;
  let v = null; try { v = JSON.parse(localStorage.getItem('plantdb.wxhide') || 'null'); } catch (e) { /* ignore */ }
  WT.hide = new Set(Array.isArray(v) ? v : ['wet_bulb_temperature_2m', 'temperature_80m', 'temperature_120m', 'temperature_180m', 'wind_speed_80m', 'wind_speed_120m', 'wind_speed_180m', 'wind_direction_80m', 'wind_direction_120m', 'wind_direction_180m',
    'soil_temperature_18cm', 'soil_temperature_54cm', 'soil_moisture_1_to_3cm', 'soil_moisture_3_to_9cm', 'soil_moisture_27_to_81cm', 'uv_index_clear_sky', 'terrestrial_radiation', 'lifted_index', 'convective_inhibition', 'boundary_layer_height',
    'total_column_integrated_water_vapour', 'freezing_level_height', 'cape', 'showers', 'evapotranspiration', 'surface_pressure', 'cloud_cover_low', 'cloud_cover_mid', 'cloud_cover_high', 'direct_normal_irradiance', 'snow_depth']);
  return WT.hide;
}
function wtSave() { try { localStorage.setItem('plantdb.wxhide', JSON.stringify([...WT.hide])); } catch (e) { /* ignore */ } }
function wtCell(k, v, tz) {
  if (v == null || v === '') return '';
  if (k === 'sunrise' || k === 'sunset') return new Date(v * 1000).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', timeZone: tz });
  if (k === 'daylight_duration' || k === 'sunshine_duration') return v >= 3600 * 1.5 && !/^sunshine_duration$/.test(k) || WT.kind === 'daily' ? `${Math.floor(v / 3600)} h ${Math.round(v % 3600 / 60)} min` : `${Math.round(v / 60)} min`;
  if (k === 'weather_code') return `${WMO[v] || 'Code'} (${v})`;
  if (k === 'is_day') return v ? 'Day' : 'Night';
  if (/^wind_direction/.test(k)) return `${Math.round(v)}° ${compass(v)}`;
  if (typeof v === 'number') return (Math.round(v * 100) / 100).toLocaleString(undefined, { maximumFractionDigits: 2 });
  return String(v);
}
async function loadWxTable() {
  const el = document.getElementById('wx-table'); if (!el) return;
  const hide = wtHidden();
  const q = new URLSearchParams({ kind: WT.kind === 'daily' ? 'daily' : 'hourly', source: WT.kind === 'sensor' ? 'sensor' : 'weather', order: WT.order, per: WT.per, page: WT.page });
  if (PLACE) q.set('loc', PLACE);
  if (WT.from) q.set('from', WT.from); if (WT.to) q.set('to', WT.to);
  let T; try { T = await api('GET', '/api/weather/table?' + q); } catch (e) { el.innerHTML = rend(html`<p class="notice bad">${e.message}</p>`); return; }
  const cols = T.columns.filter(c => !hide.has(c.key));
  WT.shown = cols.map(c => c.key); WT.kindShown = T.kind;
  const groups = [...new Set(T.columns.map(c => c.group))];
  q.delete('per'); q.delete('page');
  const first = (T.page - 1) * T.per + 1, last = Math.min(T.total, T.page * T.per);
  const lbl = T.kind === 'daily' ? 'Day' : 'Local time';
  el.innerHTML = rend(html`
    <details class="colpick noprint"><summary>Choose columns (${cols.length} of ${T.columns.length} shown)</summary>
      <div class="row"><button class="btn small ghost" type="button" data-act="wtallcols">Show all</button><button class="btn small ghost" type="button" data-act="wtnocols">Show only the basics</button></div>
      ${groups.map(g => html`<fieldset><legend>${g}</legend>${T.columns.filter(c => c.group === g).map(c => html`<label class="chk-row" style="border:0;padding:.3rem 0"><input type="checkbox" data-f="wtcol" data-key="${c.key}" ${hide.has(c.key) ? '' : raw('checked')}><span>${c.label}${c.unit ? ' (' + c.unit + ')' : ''}</span></label>`)}</fieldset>`)}
    </details>
    <p class="hint" role="status">${T.total ? `Showing ${num(first)} to ${num(last)} of ${num(T.total)}. Times are in ${T.tz}.` : 'Nothing logged for these choices.'}
      <a class="noprint" href="/api/weather/table.csv?${q}" download>Download all of it as a spreadsheet (CSV, every column)</a></p>
    ${T.total ? html`${wtPager(T, 'top')}<div class="tbl-wrap wide"><table class="tbl wxt"><caption class="sr">Logged ${T.kind === 'daily' ? 'daily weather' : T.source === 'sensor' ? 'sensor readings' : 'hourly weather'}</caption>
      <thead><tr><th scope="col">${lbl}</th>${T.source === 'sensor' ? html`<th scope="col">Device</th>` : ''}${T.kind === 'daily' ? html`<th scope="col">Status</th>` : ''}${cols.map(c => html`<th scope="col" class="num">${c.label}${c.unit ? html`<div class="hint">${c.unit}</div>` : ''}</th>`)}</tr></thead>
      <tbody>${T.rows.map(r => html`<tr><th scope="row">${T.kind === 'daily' ? dayLong(r.when) : r.when}</th>${T.source === 'sensor' ? html`<td>${r.device}</td>` : ''}${T.kind === 'daily' ? html`<td>${r.kind === 'forecast' ? 'Forecast' : 'Observed'}</td>` : ''}${cols.map(c => html`<td class="num">${wtCell(c.key, r[c.key], T.tz)}</td>`)}</tr>`)}</tbody></table></div>
      ${wtPager(T, 'bottom')}` : ''}`);
}
function wtPager(T, where) {
  const off = c => c ? raw('disabled') : '';
  const newer = WT.order === 'desc' ? 'newer' : 'older', older = WT.order === 'desc' ? 'older' : 'newer';
  return html`<form class="row noprint pager" data-form="wtgo" aria-label="Pages (${where === 'top' ? 'above' : 'below'} the table)">
    <button class="btn ghost small" type="button" data-act="wtpage" data-to="1" ${off(T.page <= 1)} title="Page 1, the ${newer}st rows">First page</button>
    <button class="btn ghost small" type="button" data-act="wtpage" data-d="-1" ${off(T.page <= 1)}>Previous page</button>
    <label class="pg-go">Page <input type="number" name="page" data-max="${T.pages}" value="${T.page}" inputmode="numeric" aria-label="Page number, 1 to ${T.pages}"> of ${num(T.pages)}</label>
    <button class="btn small" type="submit">Go</button>
    <button class="btn ghost small" type="button" data-act="wtpage" data-d="1" ${off(T.page >= T.pages)}>Next page</button>
    <button class="btn ghost small" type="button" data-act="wtpage" data-to="${T.pages}" ${off(T.page >= T.pages)} title="Page ${T.pages}, the ${older}st rows">Last page</button></form>`;
}
function wtControls() {
  return html`<div class="chart-tools noprint">
    <label>Show<select data-f="wtkind">${[['hourly', 'Hourly weather (every hour)'], ['daily', 'Daily weather summaries'], ['sensor', 'My sensor readings']].map(([v, l]) => html`<option value="${v}" ${WT.kind === v ? raw('selected') : ''}>${l}</option>`)}</select></label>
    <label>From<input type="date" data-f="wtfrom" value="${WT.from}"></label><label>To<input type="date" data-f="wtto" value="${WT.to}"></label>
    <label>Order<select data-f="wtorder"><option value="desc" ${WT.order === 'desc' ? raw('selected') : ''}>Newest first</option><option value="asc" ${WT.order === 'asc' ? raw('selected') : ''}>Oldest first</option></select></label>
    <label>Rows per page (10 to 1,000)<input type="number" data-f="wtper" value="${WT.per}" inputmode="numeric" list="wtper-list"></label>
    <datalist id="wtper-list">${[25, 50, 100, 200, 500, 1000].map(n => html`<option value="${n}"></option>`)}</datalist></div>`;
}

// ---------- frost alert and cold-night checklist (added in 1.8.0) ----------
let FROST = null, FROST_AT = 0;
async function loadFrost(force) {
  if (!force && FROST && Date.now() - FROST_AT < 5 * 60000) return FROST;
  try { FROST = await api('GET', '/api/frost'); FROST_AT = Date.now(); } catch (e) { /* no banner if it cannot be worked out */ }
  return FROST;
}
const FZ_WORD = { danger: 'Could die', damage: 'Damaged', watch: 'Close call' };
// a night's low is usually reached just before dawn, so the "night" of a date is the evening before it
function fzDay(d, lower) {
  if (!FROST) return d;
  const name = new Date(d + 'T12:00:00').toLocaleDateString([], { weekday: 'long', month: 'short', day: 'numeric' });
  const w = d === FROST.today ? 'Today' : d === addDays(FROST.today, 1) ? 'Tomorrow' : '';
  return w ? (lower ? w.toLowerCase() : w) + ' (' + name + ')' : name;
}
function fzActBy(d) {
  if (!FROST) return '';
  if (d <= FROST.today) return 'before dark today';
  if (d === addDays(FROST.today, 1)) return 'this evening';
  return new Date(addDays(d, -1) + 'T12:00:00').toLocaleDateString([], { weekday: 'long' }) + ' evening';
}
function fzSig() { const F = FROST; return F && F.first ? [F.first.date, F.first.low, F.worst.date, F.worst.low, F.worst.counts.danger, F.worst.counts.damage, F.worst.counts.watch].join('|') : ''; }
function frostBanner() {
  const F = FROST; if (!F || !F.first) return '';
  try { if (localStorage.getItem('plantdb.frosthide') === fzSig()) return ''; } catch (e) { /* show it */ }
  const W = F.worst, real = W.level !== 'watch', c = W.counts, sameNight = F.first.date === W.date;
  const parts = [c.danger ? `${c.danger} could die` : '', c.damage ? `${c.damage} would be damaged` : '', c.watch ? `${c.watch} ${c.watch === 1 ? 'is a close call' : 'are close calls'}` : ''].filter(Boolean);
  const list = parts.length > 1 ? parts.slice(0, -1).join(', ') + ' and ' + parts[parts.length - 1] : parts[0];
  return html`<section class="fz-banner ${real ? 'bad' : ''} noprint" aria-labelledby="fz-h">
    <p class="fz-title" id="fz-h">${!real ? 'Cold night ahead' : W.low <= 36 ? 'Frost warning' : 'Cold warning'} for ${placeShort()}: down to ${W.low}°F ${fzDay(W.date, true)}</p>
    <p>Of your ${F.outdoor} plants outside, ${list} that night.${sameNight ? '' : ` The first cold night is ${fzDay(F.first.date, true)}, at ${F.first.low}°F.`}
      Bring them in or cover them <strong>${fzActBy(F.first.date)}</strong>.</p>
    <p class="row"><a class="btn" href="#/frost">Open the cold-night checklist</a>
      <button class="btn ghost" type="button" data-act="frosthide">Hide until the forecast changes</button></p></section>`;
}
const FZ_DO = {
  'Move indoors': 'Bring it inside: a heated room, or the garage for a night or two.',
  'Protect outside': 'Cover it down to the ground with frost cloth or an old sheet (not plastic touching the leaves), or move it against the house or onto the porch.',
  'Hardy outside': 'Usually fine outside, but this is below its damage point: cover it, or move the pot against the house.',
  'Seasonal die-back': 'The top growth may die back. Mulch or wrap the pot, or move it to shelter to protect the roots.',
  'Annual': 'An annual: the cold will likely end its season. Bring it in only if you want to keep it going.',
};
const fzNight = z => `${fzDay(z.date)}, ${z.low}°F (${FZ_WORD[z.level].toLowerCase()})`;
function fzRow(p) {
  const d = p.done, many = p.nights.length > 1;
  return html`<li class="fz-row ${d ? 'is-done' : ''}" data-code="${p.code}">
    ${p.photo ? html`<img src="${thumbUrl(p.photo)}" alt="" loading="lazy" width="72" height="72">` : html`<span class="fz-nophoto" aria-hidden="true"></span>`}
    <div class="fz-txt"><a class="nm" href="#/plant/${enc(p.code)}">${p.name}</a> <span class="muted">${p.code}</span>
      <div><span class="fz-lv fz-${p.level}">${FZ_WORD[p.level]}</span> Damaged below ${p.damage}°F${p.lethal != null ? `, dies below ${p.lethal}°F` : ''}.${p.site === 'Covered porch' ? ' On the covered porch, which helps a little but not in a freeze.' : ''}</div>
      <div>Next cold night: ${fzNight(p.next)}.${many && p.worst.date !== p.next.date ? ` Coldest: ${fzNight(p.worst)}.` : ''}${many ? ` Cold on ${p.nights.length} of the next 7 nights.` : ''}</div>
      <div class="hint">${FZ_DO[p.plan] || FZ_DO['Protect outside']}</div>
      ${d ? html`<div class="fz-done">✔ Covered for ${fzDay(p.next.date, true)}, marked by ${d.by} ${when(d.at)}. It comes back on the list for the next cold night.</div>` : ''}</div>
    <div class="fz-acts">${d ? html`<button class="btn small ghost" type="button" data-act="frostundo" data-code="${p.code}" data-date="${p.next.date}">Undo "Covered"</button>`
      : html`<button class="btn small" type="button" data-act="frostin" data-code="${p.code}" data-name="${p.name}">Moved indoors</button>
             <button class="btn small ghost" type="button" data-act="frostcover" data-code="${p.code}" data-date="${p.next.date}">Covered for ${p.next.date === FROST.today ? 'today' : p.next.date === addDays(FROST.today, 1) ? 'tonight' : new Date(addDays(p.next.date, -1) + 'T12:00:00').toLocaleDateString([], { weekday: 'long' }) + ' night'}</button>`}</div></li>`;
}
const FZ_GROUPS = [
  ['in', 'Bring inside', 'Plants whose winter plan is Move indoors.', p => p.plan === 'Move indoors'],
  ['cover', 'Cover or move to shelter', 'Plants that stay outside but would be hurt.', p => p.plan !== 'Move indoors' && p.level !== 'watch'],
  ['watch', 'Close calls', 'Within 3°F of their damage point. Worth covering if the night is clear and still.', p => p.plan !== 'Move indoors' && p.level === 'watch'],
];
async function viewFrost() {
  const F = await loadFrost(true);
  if (!F) throw new Error('The forecast could not be read.');
  const ticked = n => (F.plants || []).filter(p => p.done && p.next.date === n.date).length;
  return {
    title: 'Cold-night checklist',
    html: html`<p class="crumb"><a href="#/winter">Winter plan</a></p><h1>Cold-night checklist</h1>
    <p class="muted">Plants that are outside and would be hurt by a night in the 7-day forecast for ${F.place}. "Could die" and "Damaged" use each plant's own temperatures;
      "Close call" means within ${F.margin}°F of its damage point, because forecasts often miss a clear, still night by a few degrees.
      Plants set to Indoors or Garage or shed are left out, so a plant leaves this list when you press Moved indoors.</p>
    <p>Before a plant comes inside, check it for pests: <a href="#/inside">Getting plants ready to come inside</a>.</p>
    ${!F.nights.length ? html`<p class="notice">No forecast yet. It is fetched a few seconds after the app starts, then every hour.</p>` : ''}
    ${F.nights.length && !F.plants.length ? html`<p class="notice ok">No cold nights in the next 7 days for any plant that is outside.</p>` : ''}
    ${F.nights.length ? html`<section class="blk"><h2>The next 7 nights</h2><div class="tbl-wrap"><table class="tbl fz-tbl"><caption class="sr">Plants at risk each night</caption>
      <thead><tr><th>Day</th><th class="num">Low</th><th class="num">Could die</th><th class="num">Damaged</th><th class="num">Close calls</th><th class="num">Covered</th></tr></thead><tbody>
      ${F.nights.map(n => html`<tr><th scope="row">${fzDay(n.date)}</th><td class="num">${n.low}°F${n.low <= 32 ? ' (freeze)' : ''}</td>
        <td class="num">${n.counts.danger || '–'}</td><td class="num">${n.counts.damage || '–'}</td><td class="num">${n.counts.watch || '–'}</td><td class="num">${n.level ? ticked(n) : '–'}</td></tr>`)}
      </tbody></table></div><p class="hint">Forecast updated ${F.fetched_at ? when(F.fetched_at) : 'not yet'}. The low is usually reached just before dawn, so act the evening before.</p></section>` : ''}
    ${FZ_GROUPS.map(([id, title, sub, test]) => { const g = (F.plants || []).filter(test); if (!g.length) return '';
      const open = g.filter(p => !p.done);
      return html`<section class="blk" id="fz-${id}"><h2>${title} (${g.length})</h2><p class="muted">${sub} Most urgent first.</p>
        ${open.length > 1 ? html`<p>${id === 'in' ? html`<button class="btn small ghost" type="button" data-act="frostallin" data-group="${id}">Moved all ${open.length} indoors</button>`
          : html`<button class="btn small ghost" type="button" data-act="frostallcover" data-group="${id}">Mark all ${open.length} as covered for their next cold night</button>`}</p>` : ''}
        <ul class="fz-list">${g.map(fzRow)}</ul></section>`; })}
    <section class="blk"><h2>Protecting plants on a cold night</h2><ul>
      <li>Move pots against the house wall or onto the porch: they lose less heat there than in the open.</li>
      <li>Water dry pots during the day before: moist soil holds more heat than dry soil.</li>
      <li>Cover plants down to the ground with frost cloth, old sheets or cardboard boxes, so the ground's warmth is trapped. Plastic touching the leaves makes damage worse.</li>
      <li>Take the covers off the next morning once it is above freezing, so the plants get light.</li>
      <li>Group pots together; small pots freeze through faster than big ones.</li></ul></section>`,
  };
}
function frostNote(p) {
  const x = FROST && (FROST.plants || []).find(q => q.code === p.code);
  if (!x || x.level === 'watch') return '';
  const w = x.worst;
  return html`<p class="notice bad noprint fz-note"><strong>Frost risk:</strong> ${fzDay(w.date)} is forecast to drop to ${w.low}°F,
    below this plant's ${w.level === 'danger' ? `lowest survivable temperature (${x.lethal}°F)` : `damage point (${x.damage}°F)`}.
    ${FZ_DO[p.winter_plan] || ''} <a href="#/frost">Open the cold-night checklist</a></p>`;
}

// ---------- winter plan page ----------
async function viewWinter() {
  const [ref, list, W, monthly] = await Promise.all([api('GET', '/api/reference'), api('GET', '/api/plants'), api('GET', '/api/weather'), api('GET', '/api/weather/monthly')]);
  return {
    title: 'Winter plan',
    html: html`<h1>Winter plan</h1><p class="muted">What to expect in ${placeName()} from October to March, when to act, and which plants go where.</p>
    <section class="blk"><h2>The next 7 days</h2>${forecastBlock(W, list)}<p class="row"><a class="btn small" href="#/frost">Open the cold-night checklist</a><a class="btn small ghost" href="#/inside">Get plants ready to come inside</a><a class="btn ghost small" href="#/weather">Open the Weather page for charts and sensors</a></p></section>
    <section class="blk"><h2>Expected and tracked this season</h2>${seasonTable(ref, monthly)}
      ${ref.applies !== false ? (ref.notes || []).map(n => html`<p class="hint">${n}</p>`) : ''}</section>
    <section class="blk"><h2>When to act</h2><dl class="dl">${(ref.triggers || []).map(t => html`<dt>${t.temp}</dt><dd>${t.action}</dd>`)}</dl></section>
    <section class="blk"><h2>Ground rules</h2>${(ref.playbook || []).length ? html`<ul>${ref.playbook.map(x => html`<li>${x}</li>`)}</ul>` : ''}</section>
    <section class="blk"><h2>Plant by plant</h2><div class="cols">${META.winter_plans.map(pl => {
      const g = list.filter(p => p.winter_plan === pl && !isInside(p)).sort((a, b) => (b.temp_damage_below ?? -99) - (a.temp_damage_below ?? -99));
      if (!g.length) return '';
      return html`<div><h3>${pl} (${g.length})</h3><ul class="todo winter-list">${g.map(p => html`<li>${p.photo ? html`<img src="${thumbUrl(p.photo)}" alt="" loading="lazy">` : html`<span></span>`}
        <span><a class="nm" href="#/plant/${enc(p.code)}">${p.common_name}</a><br><span class="muted">${p.code}${p.temp_damage_below != null ? ', damage below ' + p.temp_damage_below + '°F' : ''}${p.site && p.site !== 'Outdoors' ? ', ' + p.site.toLowerCase() : ''}</span>
        <br><button class="btn small noprint" type="button" data-act="movein" data-code="${p.code}" data-name="${p.common_name}">Moved indoors</button></span></li>`)}</ul></div>`;
    })}</div>
    ${(() => { const ins = list.filter(isInside).sort((a, b) => a.code.localeCompare(b.code)); return ins.length ? html`<h3 id="inside-list">Already inside (${ins.length})</h3>
      <p class="hint">These are left out of the lists above and the frost warnings. If one goes back out, press Moved back outside.</p>
      <p><a class="btn small ghost" href="#/outside">Which can go back outside?</a></p>
      <ul class="todo winter-list inside-list">${ins.map(p => html`<li>${p.photo ? html`<img src="${thumbUrl(p.photo)}" alt="" loading="lazy">` : html`<span></span>`}
        <span><a class="nm" href="#/plant/${enc(p.code)}">${p.common_name}</a><br><span class="muted">${p.code}, ${p.site.toLowerCase()}, plan: ${p.winter_plan}</span>
        <br><button class="btn small ghost noprint" type="button" data-act="moveout" data-code="${p.code}" data-name="${p.common_name}">Moved back outside</button></span></li>`)}</ul>` : html`<p class="hint">When you bring a plant in, press its Moved indoors button. It leaves these lists and the frost warnings, and its page shows Location: Indoors.</p>`; })()}
    </section>
    ${ref.applies !== false && (ref.sources || []).length ? html`<section class="blk"><h2>Sources</h2><ul>${ref.sources.map(s => html`<li><a href="${s[1]}" target="_blank" rel="noopener noreferrer">${s[0]}</a></li>`)}</ul></section>` : ''}`,
  };
}

// ---------- back outside in spring (prototype: proto/move-outside) ----------
// #/outside lists the plants that are inside now and whether the forecast nights are warm enough for each to go back out
// (GET /api/outside). In spring the Today page also gets a short note when some are ready (filled by a MutationObserver).
let BO = null, BO_AT = 0;
async function loadOutside(force) {
  if (!force && BO && Date.now() - BO_AT < 5 * 60000) return BO;
  BO = await api('GET', '/api/outside'); BO_AT = Date.now();
  return BO;
}
const BO_WORD = { ready: 'Ready', safe: 'Safe, but cool', early: 'Too early', wait: 'Not yet' };
const BO_GROUPS = [
  ['ready', 'Ready to go back out', 'Every night in the forecast is at or above the low each of these likes.'],
  ['safe', 'Safe to go out, but the nights are cool', 'No night in the forecast comes within 3°F of their damage point, but some nights are cooler than they like. Going out now is fine; they will grow slowly until the nights warm up.'],
  ['early', 'A warm week, but it is early', 'The forecast is fine for these, but in most years colder nights still come after this date. Wait, or put them out and be ready to bring them back in.'],
  ['wait', 'Not yet', 'A night in the forecast is too cold for these.'],
];
const boMd = md => new Date('2001-' + md + 'T12:00:00').toLocaleDateString([], { month: 'long', day: 'numeric' });
function boUsual(p) {
  const u = p.usual;
  if (!u) return '';
  if (p.why === 'autumn' && u.first) return `In most years the first night below ${p.safe_at}°F comes around ${boMd(u.first)}, so it would likely need to come back in soon.`;
  if (!u.safe) return '';
  if (u.safe === '01-01') return `In the last ${u.spring_years} springs, no night went below ${p.safe_at}°F.`;
  return `In most of the last ${u.spring_years} years, the nights stayed above ${p.safe_at}°F from ${boMd(u.safe)} on${u.safe_latest !== u.safe ? ` (in the latest year, from ${boMd(u.safe_latest)})` : ''}.`;
}
function boRow(p) {
  const lv = p.level, c = p.coldest;
  const needs = p.damage != null ? `Damaged below ${p.damage}°F${p.like > p.safe_at ? `; likes nights of ${p.like}°F or more` : ''}.` : p.like != null ? `Likes nights of ${p.like}°F or more.` : 'No temperatures on its page yet, so it cannot be checked.';
  let fc = '';
  if (lv === 'wait') fc = `Too cold ${fzDay(p.first_cold.date, true)}: ${p.first_cold.low}°F. It needs ${p.safe_at}°F or more to be safe${c.date !== p.first_cold.date ? `; the coldest night is ${fzDay(c.date, true)}, ${c.low}°F` : ''}.`;
  else if (c) fc = `Coldest night in the forecast: ${fzDay(c.date, true)}, ${c.low}°F.${p.cool_nights ? ` ${p.cool_nights} of the next ${BO.nights.length} nights are below ${p.like}°F.` : ''}`;
  const usual = boUsual(p);
  const go = lv && lv !== 'wait';
  return html`<li class="fz-row bo-row" data-code="${p.code}">
    ${p.photo ? html`<img src="${thumbUrl(p.photo)}" alt="" loading="lazy" width="72" height="72">` : html`<span class="fz-nophoto" aria-hidden="true"></span>`}
    <div class="fz-txt"><a class="nm" href="#/plant/${enc(p.code)}">${p.name}</a> <span class="muted"><span class="bo-code">${p.code}</span>, ${(p.site || '').toLowerCase()}</span>
      <div>${lv ? html`<span class="bo-lv bo-${lv}">${BO_WORD[lv]}</span> ` : ''}${needs}</div>
      ${fc ? html`<div>${fc}</div>` : ''}${usual ? html`<div class="hint">${usual}</div>` : ''}
      ${go ? html`<div class="hint">Porch first protects leaves that grew indoors from sun scorch. A reminder comes a week later.</div>` : ''}</div>
    ${go ? html`<div class="fz-acts"><button class="btn small" type="button" data-act="boporch" data-code="${p.code}" data-name="${p.name}">Moved to the porch</button>
      <button class="btn small ghost" type="button" data-act="boout" data-code="${p.code}" data-name="${p.name}">Moved outside</button></div>` : ''}</li>`;
}
const boPorchDay = d => new Date(d + 'T12:00:00').toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' });
function boPorchRow(p) {
  return html`<li class="fz-row bo-row bo-porchrow" data-code="${p.code}">
    ${p.photo ? html`<img src="${thumbUrl(p.photo)}" alt="" loading="lazy" width="72" height="72">` : html`<span class="fz-nophoto" aria-hidden="true"></span>`}
    <div class="fz-txt"><a class="nm" href="#/plant/${enc(p.code)}">${p.name}</a> <span class="muted"><span class="bo-code">${p.code}</span>, covered porch</span>
      <div>${p.is_due ? html`<span class="bo-lv bo-ready">Time to move it</span> ` : ''}On the porch since ${boPorchDay(p.on)} (${p.days === 0 ? 'today' : p.days === 1 ? '1 day' : p.days + ' days'}).
        ${p.is_due ? 'It has had its week out of full sun, so it can go to its summer spot.' : html`Move it to its summer spot on or after ${boPorchDay(p.due)}.`}</div></div>
    <div class="fz-acts"><button class="btn small ${p.is_due ? '' : 'ghost'}" type="button" data-act="boout" data-code="${p.code}" data-name="${p.name}">Moved outside</button>
      <button class="btn small ghost" type="button" data-act="boleave" data-code="${p.code}" data-name="${p.name}">Leave it on the porch</button></div></li>`;
}
async function viewOutside() {
  const B = await loadOutside(true);
  const ps = B.plants || [], n = B.counts, anyUsual = ps.some(p => p.usual);
  const go = n.ready + n.safe;
  return {
    title: 'Back outside',
    html: html`<p class="crumb"><a href="#/winter">Winter plan</a></p><h1>Back outside</h1>
    <p class="muted">Plants that are inside now (Indoors, or Garage or shed), and whether the nights in the 7-day forecast for ${B.place} are warm enough for each to go back out.
      Each plant is checked against its own temperatures: safe means no night within ${B.margin}°F of its damage point, and ready means every night is at or above the low it likes.</p>
    ${B.season === 'autumn' ? html`<p class="notice">It is autumn, so most plants that came inside should stay in until spring. This page is most useful from late winter: each plant shows as ready as soon as the nights are warm enough for it.</p>` : ''}
    ${!B.nights.length ? html`<p class="notice">No forecast yet. It is fetched a few seconds after the app starts, then every hour.</p>` : ''}
    ${!ps.length ? html`<p class="notice ok">No plants are inside. When you bring one in, press its Moved indoors button and it shows here.</p>` : ''}
    ${ps.length && B.nights.length ? html`<p class="notice ${go ? 'ok' : ''} bo-sum" role="status"><strong>${go ? `${go} of ${ps.length} plants inside can go back out now.` : `None of the ${ps.length} plants inside can go back out yet.`}</strong>
      ${n.ready ? ` Ready: ${n.ready}.` : ''}${n.safe ? ` Safe, but cool: ${n.safe}.` : ''}${n.early ? ` Too early: ${n.early}.` : ''}${n.wait ? ` Not yet: ${n.wait}.` : ''}</p>` : ''}
    ${B.nights.length && !anyUsual ? html`<p class="hint">To also see when the nights usually warm up each spring, load the weather history: <a href="#/weather">Weather page</a>, Load history. It needs 3 years or more.</p>` : ''}
    ${(B.porch || []).filter(p => p.is_due).length ? html`<section class="blk" id="bo-porchdue"><h2>Time to move from the porch to their summer spot (${B.porch.filter(p => p.is_due).length})</h2>
      <p class="muted">These have had a week on the porch, out of full sun. Press Moved outside once they are in their summer spot, or Leave it on the porch to stop the reminder.</p>
      <ul class="fz-list">${B.porch.filter(p => p.is_due).map(boPorchRow)}</ul></section>` : ''}
    ${ps.some(p => p.level && p.level !== 'wait') || (B.porch || []).length ? html`<p class="notice bo-why"><strong>Why the porch first?</strong> Leaves that grew indoors have never seen full sun, so they get sun scorch within a day or two if they go straight outside. The covered porch is bright but out of the direct sun. After a week, move the plant to its summer spot.</p>` : ''}
    ${BO_GROUPS.map(([id, title, sub]) => { const g = ps.filter(p => p.level === id); if (!g.length) return '';
      return html`<section class="blk" id="bo-${id}"><h2>${title} (${g.length})</h2><p class="muted">${sub}</p><ul class="fz-list">${g.map(boRow)}</ul></section>`; })}
    ${(() => { const g = ps.filter(p => !p.level); return g.length && B.nights.length ? html`<section class="blk" id="bo-unknown"><h2>Cannot be checked (${g.length})</h2>
      <p class="muted">These have no damage point or ideal low on their page.</p><ul class="fz-list">${g.map(boRow)}</ul></section>` : ''; })()}
    ${B.nights.length ? html`<section class="blk"><h2>The next 7 nights</h2><div class="tbl-wrap"><table class="tbl bo-tbl"><caption class="sr">Forecast lows</caption>
      <thead><tr><th>Day</th><th class="num">Low</th></tr></thead><tbody>
      ${B.nights.map(x => html`<tr><th scope="row">${fzDay(x.date)}</th><td class="num">${x.low}°F</td></tr>`)}</tbody></table></div>
      <p class="hint">Forecast updated ${B.fetched_at ? when(B.fetched_at) : 'not yet'}. The low is usually reached just before dawn.</p></section>` : ''}
    ${(B.porch || []).filter(p => !p.is_due).length ? html`<section class="blk" id="bo-porchwait"><h2>On the porch for now (${B.porch.filter(p => !p.is_due).length})</h2>
      <p class="muted">Getting used to the light, and out of full sun so the leaves do not scorch. A reminder comes after a week.</p>
      <ul class="fz-list">${B.porch.filter(p => !p.is_due).map(boPorchRow)}</ul></section>` : ''}
    <section class="blk"><h2>Going back out</h2><ul>
      <li>Ease plants in. Leaves that grew indoors scorch in full sun, so give them a week on the covered porch, then a few hours of morning sun, then their usual spot.</li>
      <li>Moved to the porch sets the plant's Location to Covered porch and sets a reminder for a week later. It shows on the cold-night checklist if a cold night comes.</li>
      <li>Pots dry out much faster outside, especially in wind and sun. Check them every day or two for the first weeks.</li>
      <li>Start feeding again once new growth appears.</li></ul></section>`,
  };
}
async function boMove(el, site) {
  if (!(await needName())) return;
  const code = el.dataset.code, y = window.scrollY;
  await guard(async () => {
    if (site === 'Covered porch') await api('POST', '/api/outside/porch', { code, action: 'start' });
    else await api('POST', '/api/plants/' + enc(code) + '/site', { site });
    toast(el.dataset.name + (site === 'Outdoors' ? ' moved outside' : ' moved to the covered porch, out of full sun. A reminder comes in a week.'));
    BO_AT = 0; FROST_AT = 0;
    await route(); window.scrollTo(0, y);
    const next = document.querySelector('.bo-row [data-act=boporch]') || document.querySelector('.bo-row [data-act=boout]');
    (next || document.querySelector('main h1')).focus({ preventScroll: true });
  });
}
// the Today page: in spring, a short note when plants inside can go back out
new MutationObserver(() => {
  if (!/^#\/today\b/.test(location.hash)) return;
  const h = document.querySelector('#app h1');
  if (!h || document.getElementById('bo-today')) return;
  h.insertAdjacentHTML('afterend', '<div id="bo-today"></div>');
  loadOutside().then(B => {
    const box = document.getElementById('bo-today'), go = B.season === 'spring' ? B.counts.ready + B.counts.safe : 0, due = (B.porch || []).filter(p => p.is_due).length;
    if (!box || (!go && !due)) return;
    box.innerHTML = rend(html`<p class="notice ok noprint">${go ? html`<strong>${go === 1 ? '1 plant inside can' : `${go} plants inside can`} go back outside.</strong>
      The nights in the forecast are warm enough for ${go === 1 ? 'it' : 'them'}. ` : ''}${due ? html`<strong>${due === 1 ? '1 plant on the porch is' : `${due} plants on the porch are`} ready for ${due === 1 ? 'its' : 'their'} summer spot.</strong> ${due === 1 ? 'It has' : 'They have'} had a week out of full sun. ` : ''}<a href="#/outside">Open the Back outside list</a></p>`);
  }).catch(() => { /* no note if it cannot be worked out */ });
}).observe(document.getElementById('app'), { childList: true });

// ---------- display settings and current-conditions dialogs ----------
function displayDialog() {
  const P = window.PlantPrefs.get();
  const group = (key, title, opts, hint) => html`<fieldset class="opt-group"><legend>${title}</legend><div class="opts">${opts.map(([v, l]) => html`<label><input type="radio" name="pref-${key}" data-pref="${key}" value="${v}" ${P[key] === v ? raw('checked') : ''}><span>${l}</span></label>`)}</div>${hint ? html`<p class="hint">${hint}</p>` : ''}</fieldset>`;
  modal(html`<form method="dialog"><h2>Display settings</h2>
    <p class="muted">Changes apply right away and are remembered in this browser. Each computer or phone keeps its own.</p>
    <p><strong>App version:</strong> ${META && META.version ? META.version : 'unknown'}</p>
    ${group('size', 'Text and button size', [['100', 'Standard'], ['115', 'Comfortable'], ['135', 'Large'], ['160', 'Larger'], ['190', 'Largest']], 'Everything scales together, including buttons, bars and charts.')}
    ${group('space', 'Spacing', [['normal', 'Normal'], ['roomy', 'Roomy']], 'Roomy adds space between lines, letters and words.')}
    ${group('contrast', 'Contrast', [['normal', 'Normal'], ['high', 'High']], 'High contrast uses black and white, stronger lines and heavier outlines.')}
    ${group('theme', 'Colours', [['auto', 'Match my device'], ['light', 'Light'], ['dark', 'Dark']])}
    ${group('navside', 'Section menu side', [['left', 'Left'], ['right', 'Right']], 'The "On this page" menu lists the sections of the page you are on.')}
    ${group('navopen', 'Section menu', [['1', 'Open'], ['0', 'Folded away (the Sections button opens it)']], 'On narrow windows and phones it starts folded and covers the page while open.')}
    ${group('width', 'Page width', [['normal', 'Normal'], ['wide', 'Use the full width of the window']], 'Full width gives charts and tables more room on a wide screen.')}
    ${group('layout', 'Plant pages', [['split', 'Photos and details side by side'], ['single', 'One column']], 'Side by side lets each half scroll on its own: scroll with the pointer over the half you want to move. One column stacks the photos above the details.')}
    ${canSpeak() ? html`${group('readbtns', 'Read aloud buttons', [['1', 'Show them on each section'], ['0', 'Hide them']], 'Your browser reads the section aloud with its own voices. The R key reads the whole page either way.')}
    ${group('rate', 'Reading speed', [['0.8', 'Slower'], ['1', 'Normal'], ['1.25', 'Faster'], ['1.5', 'Fastest']])}
    <fieldset class="opt-group"><legend>Voice</legend><label class="f">Voice<select data-pref="voice" id="pref-voice">${voiceOptions(P.voice)}</select></label>
      <p class="row"><button class="btn ghost small" type="button" data-act="voicetest">Try this voice</button></p>
      <p class="hint">"Natural" or "Online" voices in Microsoft Edge sound the most human.</p></fieldset>` : ''}
    ${group('photofit', 'Photos on the Plants page', [['auto', 'Show wide photos whole, fill the card with tall ones'], ['fill', 'Fill the card (wide photos lose their sides)'], ['whole', 'Always show the whole photo']], 'A wide photo cut down to fit a tall card loses its sides. Shown whole, it has a plain band above and below.')}
    ${group('swipe', 'Swipe between plants', [['1', 'On'], ['0', 'Off']], 'On a phone or tablet, swipe left on a plant page for the next plant, or right for the previous one. Start away from the edges of the screen, which your phone uses for Back.')}
    ${group('keys', 'Keyboard shortcuts', [['1', 'On'], ['0', 'Off']], 'R reads the page aloud, [ and ] go to the previous and next plant, ? lists them all.')}
    <div class="row"><button class="btn" value="ok" autofocus>Done</button><button class="btn ghost" type="button" data-act="prefreset">Reset to defaults</button></div></form>`);
}
// ---------- swipe between plants on touch screens (added in 1.14.1) ----------
// A quick sideways swipe on a plant page opens the next plant (swipe left) or the previous one (swipe right), the same as
// the Previous / Next Plant buttons. It stays out of the way of scrolling, zooming, tables and charts that scroll sideways,
// form fields, open windows and menus, and the screen edges (Back on Android, iPhone and iPad).
const SWIPE = { x: 0, y: 0, t: 0, on: false, dir: 0 };
const SWIPE_EDGE = 28, SWIPE_MIN = 70;
function swipeBlocked(el) {
  for (let n = el; n && n !== document.body && n.nodeType === 1; n = n.parentElement) {
    if (n.matches('input,select,textarea,button.main-photo,[contenteditable],dialog,#sidenav,#corner,#console,.pnav,.chart-card,canvas,.thumbs')) return true;
    const cs = getComputedStyle(n);
    if (/(auto|scroll)/.test(cs.overflowX) && n.scrollWidth > n.clientWidth + 2) return true;     // something here scrolls sideways
  }
  return false;
}
function swipeHint() {
  let h = document.getElementById('swipe-hint');
  if (!h) { h = document.createElement('div'); h.id = 'swipe-hint'; h.className = 'swipe-hint'; h.setAttribute('aria-hidden', 'true'); document.body.appendChild(h); }
  return h;
}
function swipeHide() { const h = document.getElementById('swipe-hint'); if (h) { h.classList.remove('show', 'ready'); h.removeAttribute('data-side'); } SWIPE.on = false; SWIPE.dir = 0; }
document.addEventListener('touchstart', e => {
  SWIPE.on = false;
  if (e.touches.length !== 1 || window.PlantPrefs.get().swipe === '0' || !/^#\/plant\/[^/]+$/.test(location.hash) || !document.getElementById('pnav')) return;
  if (document.querySelector('dialog[open]') || (document.documentElement.dataset.narrow === '1' && navOpen())) return;
  const t = e.touches[0];
  if (t.clientX < SWIPE_EDGE || t.clientX > window.innerWidth - SWIPE_EDGE || swipeBlocked(e.target)) return;
  Object.assign(SWIPE, { x: t.clientX, y: t.clientY, t: Date.now(), on: true, dir: 0 });
}, { passive: true });
document.addEventListener('touchmove', e => {
  if (!SWIPE.on) return;
  if (e.touches.length !== 1) { swipeHide(); return; }
  const t = e.touches[0], dx = t.clientX - SWIPE.x, dy = t.clientY - SWIPE.y;
  if (Math.abs(dy) > 40 && Math.abs(dy) > Math.abs(dx)) { swipeHide(); return; }              // they are scrolling
  if (Math.abs(dx) < 24 || Math.abs(dx) < Math.abs(dy) * 1.5) return;
  const dir = dx < 0 ? 1 : -1, link = document.querySelector(dir > 0 ? '#pnav a.pn-next' : '#pnav a.pn-prev'), h = swipeHint();
  if (dir !== SWIPE.dir) {
    SWIPE.dir = dir;
    const name = link ? (link.querySelector('.pn-name') || link).textContent.trim() : '';
    h.textContent = link ? (dir > 0 ? `Next plant: ${name} →` : `← Previous plant: ${name}`) : (dir > 0 ? 'This is the last plant in the list' : 'This is the first plant in the list');
    h.dataset.side = dir > 0 ? 'right' : 'left';
  }
  h.classList.add('show');
  h.classList.toggle('ready', !!link && Math.abs(dx) >= swipeNeed());
}, { passive: true });
const swipeNeed = () => Math.max(SWIPE_MIN, Math.min(140, window.innerWidth * 0.22));
document.addEventListener('touchend', e => {
  if (!SWIPE.on) return;
  const t = e.changedTouches[0], dx = t.clientX - SWIPE.x, dy = t.clientY - SWIPE.y, quick = Date.now() - SWIPE.t < 1200;
  const go = quick && Math.abs(dx) >= swipeNeed() && Math.abs(dx) > Math.abs(dy) * 2 && !(window.getSelection && String(window.getSelection()).trim());
  const link = go ? document.querySelector(dx < 0 ? '#pnav a.pn-next' : '#pnav a.pn-prev') : null;
  swipeHide();
  if (link) link.click();
}, { passive: true });
document.addEventListener('touchcancel', swipeHide, { passive: true });
window.addEventListener('hashchange', swipeHide);

// ---------- read aloud and keyboard shortcuts (added in 1.8.0) ----------
// Uses the browser's own voices (Edge and Chrome on Windows have several English voices); nothing leaves the computer
// except with "online" voices, which the browser itself provides.
const SPEECH = { on: false, el: null, btn: null };
const canSpeak = () => 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window;
const RD_ICON = raw('<svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 10v4h4l5 4V6L8 10z"/><path d="M16.500 8.500a5 5 0 0 1 0 7M19 6a8.500 8.500 0 0 1 0 12"/></svg>');
function addReadButtons() {
  if (!canSpeak()) return;
  const app = document.getElementById('app');
  app.querySelectorAll('section.blk > h2, section.needs > h2, section.cond h2').forEach(h => {
    const sec = h.closest('section'); if (!sec || sec.querySelector(':scope > .rd-btn, :scope > header > .rd-btn')) return;
    const name = h.textContent.trim();
    sec.classList.add('has-rd');
    h.insertAdjacentHTML('afterend', rend(html`<button class="btn ghost small rd-btn noprint" type="button" data-act="readsec" aria-label="Read the ${name} section aloud">${RD_ICON}<span>Read aloud</span></button>`));
  });
  const h1 = app.querySelector('h1');
  if (h1 && !app.querySelector('.rd-page')) h1.insertAdjacentHTML('afterend', rend(html`<p class="rd-page noprint"><button class="btn ghost small" type="button" data-act="readpage">${RD_ICON}<span>Read this page aloud</span></button>
    <span class="hint">Shortcut: R. Press Escape to stop.</span></p>`));
}
// the text a sighted reader would see: no buttons, form controls, icons, hidden parts or closed details
function readableText(root) {
  const out = [];
  const skip = el => el.matches('button,select,option,input,textarea,script,style,svg,canvas,dialog,.rd-btn,.rd-page,.thumbs,.jump,.pnav,.pn-filters,.strip,.ticks,.now-tag,.now-line,[aria-hidden="true"],[hidden]');
  (function walk(n) {
    for (const c of n.childNodes) {
      if (c.nodeType === 3) { const t = c.textContent.replace(/\s+/g, ' '); if (t.trim()) out.push(t); continue; }
      if (c.nodeType !== 1 || skip(c)) continue;
      if (c.tagName === 'DETAILS' && !c.open) { const sm = c.querySelector(':scope > summary'); if (sm) { out.push('. '); walk(sm); out.push('. '); } continue; }
      const cs = getComputedStyle(c);
      if (cs.display === 'none' || (cs.visibility === 'hidden' && !c.classList.contains('sr'))) continue;
      if (c.tagName === 'IMG') { if (c.alt) out.push(' ' + c.alt + '. '); continue; }
      const block = /^(block|flex|grid|list-item|table|table-row|table-caption|flow-root)$/.test(cs.display) || /^H[1-6]$/.test(c.tagName);
      if (block) out.push('. ');
      walk(c);
      if (block) out.push('. '); else if (cs.display === 'table-cell' || cs.display === 'inline-block') out.push(', ');
    }
  })(root);
  return speakable(out.join(''));
}
function speakable(t) {
  return t.replace(/\bP-(\d)(\d)(\d)\b/g, 'P $1 $2 $3')
    .replace(/(-?\d+(?:\.\d+)?)\s?°F/g, '$1 degrees').replace(/°/g, ' degrees').replace(/(\d)\s?F\b/g, '$1 degrees')
    .replace(/(?:u|µ)mol\/m(?:2|²)\/s/g, 'micromoles per square metre per second').replace(/mol\/m(?:2|²)/g, 'moles per square metre')
    .replace(/\/day\b/g, ' a day').replace(/(\d)\s?h\b/g, '$1 hours').replace(/\bRH\b/g, 'relative humidity').replace(/~\s?/g, 'about ')
    .replace(/(\d)\s?-\s?(\d)/g, '$1 to $2').replace(/(\d)\s?in\b/g, '$1 inches').replace(/[✔✖■▲▶◀←→–—]/g, ' ').replace(/\s+/g, ' ')
    .replace(/\s*\.\s*(\.\s*)+/g, '. ').replace(/([:;,])\s*\./g, '$1').replace(/\s+([.,;:])/g, '$1').replace(/^[\s.]+/, '').trim();
}
function rdChunks(t) {          // short pieces: some voices stop after about 15 seconds of one long utterance
  const parts = t.split(/(?<=[.!?:;])\s+/), out = [];
  let cur = '';
  for (const p of parts) { if ((cur + ' ' + p).length > 220 && cur) { out.push(cur); cur = p; } else cur = cur ? cur + ' ' + p : p; }
  if (cur) out.push(cur);
  return out;
}
function rdVoice() {
  const v = window.PlantPrefs.get().voice, all = speechSynthesis.getVoices();
  return (v !== 'auto' && all.find(x => x.name === v)) || all.find(x => /^en(-|_)US/i.test(x.lang) && /natural|online/i.test(x.name)) || all.find(x => /^en/i.test(x.lang)) || null;
}
function stopReading(quiet) {
  if (!canSpeak()) return;
  SPEECH.on = false; speechSynthesis.cancel();
  if (SPEECH.el) SPEECH.el.classList.remove('rd-on');
  if (SPEECH.btn) { SPEECH.btn.querySelector('span').textContent = SPEECH.btn.dataset.act === 'readpage' ? 'Read this page aloud' : 'Read aloud'; SPEECH.btn.setAttribute('aria-pressed', 'false'); }
  SPEECH.el = SPEECH.btn = null;
  const s = document.getElementById('rd-stop'); if (s) s.hidden = true;
  if (!quiet) toast('Stopped reading');
}
function readAloud(el, btn, label) {
  if (!canSpeak()) { toast('This browser cannot read aloud. Edge and Chrome on Windows can.', true); return; }
  const was = SPEECH.btn;
  stopReading(true);
  if (was && was === btn) return;                  // the same button again: stop
  const text = readableText(el); if (!text) { toast('Nothing to read in this section.'); return; }
  const P = window.PlantPrefs.get(), voice = rdVoice(), chunks = rdChunks(text);
  SPEECH.on = true; SPEECH.el = el; SPEECH.btn = btn || null;
  el.classList.add('rd-on');
  if (btn) { btn.querySelector('span').textContent = 'Stop reading'; btn.setAttribute('aria-pressed', 'true'); }
  let st = document.getElementById('rd-stop');
  if (!st) { document.body.insertAdjacentHTML('beforeend', rend(html`<button id="rd-stop" class="btn noprint" type="button" data-act="readstop">Stop reading</button>`)); st = document.getElementById('rd-stop'); }
  st.hidden = false;
  chunks.forEach((c, i) => {
    const u = new SpeechSynthesisUtterance(c);
    u.rate = +P.rate || 1; if (voice) { u.voice = voice; u.lang = voice.lang; } else u.lang = 'en-US';
    if (i === chunks.length - 1) u.onend = () => { if (SPEECH.on && SPEECH.el === el) stopReading(true); };
    speechSynthesis.speak(u);
  });
}
const readTarget = () => document.getElementById('pane-r') || document.getElementById('app');
function voiceOptions(cur) {
  const vs = canSpeak() ? speechSynthesis.getVoices().filter(v => /^en/i.test(v.lang)) : [];
  return html`<option value="auto" ${cur === 'auto' ? raw('selected') : ''}>Best English voice on this computer</option>${vs.map(v => html`<option value="${v.name}" ${cur === v.name ? raw('selected') : ''}>${v.name} (${v.lang})</option>`)}`;
}
if (canSpeak()) speechSynthesis.addEventListener('voiceschanged', () => { const s = document.getElementById('pref-voice'); if (s) s.innerHTML = rend(voiceOptions(window.PlantPrefs.get().voice)); });
function readAloudText(t) {
  if (!canSpeak()) return;
  const P = window.PlantPrefs.get(), v = rdVoice(), u = new SpeechSynthesisUtterance(t);
  u.rate = +P.rate || 1; if (v) { u.voice = v; u.lang = v.lang; }
  speechSynthesis.speak(u);
}
function shortcutsDialog() {
  const k = (key, what) => html`<tr><th scope="row"><kbd>${key}</kbd></th><td>${what}</td></tr>`;
  modal(html`<form method="dialog"><h2>Keyboard shortcuts</h2>
    <p class="muted">They work anywhere except while you are typing in a box. Turn them off in Display settings if they get in the way.</p>
    <table class="tbl"><tbody>
      ${k('R', 'Read this page aloud (press again, or Escape, to stop)')}${k('Escape', 'Stop reading')}
      ${k('[', 'Previous plant (on a plant page)')}${k(']', 'Next plant (on a plant page)')}
      ${k('E', 'Edit this plant (on a plant page)')}${k('/', 'Search plants')}
      ${k('H', 'Go to the Plants page')}${k('M', 'Open or fold the section menu')}${k('L', 'Choose the location for the weather')}${k('U', 'Undo the care you just logged, while its message is showing')}${k('?', 'Show this list')}
    </tbody></table>
    <div class="row"><button class="btn" value="ok" autofocus>Close</button></div></form>`);
}
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && SPEECH.on) { stopReading(); return; }
  if (e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey || window.PlantPrefs.get().keys !== '1') return;
  const t = e.target;
  if (t.closest && t.closest('input,textarea,select,[contenteditable="true"],dialog[open]')) return;
  const click = sel => { const x = document.querySelector(sel); if (x) { e.preventDefault(); x.click(); } };
  switch (e.key) {
    case '[': click('#pnav a.pn-prev'); break;
    case ']': click('#pnav a.pn-next'); break;
    case 'r': case 'R': e.preventDefault(); { const b = document.querySelector('[data-act=readpage]'); readAloud(readTarget(), b, 'this page'); } break;
    case 'e': case 'E': if (CUR && location.hash.startsWith('#/plant/') && !location.hash.endsWith('/edit')) { e.preventDefault(); location.hash = '#/plant/' + enc(CUR.p.code) + '/edit'; } break;
    case 'h': case 'H': e.preventDefault(); go('#/'); break;
    case 'm': case 'M': click('[data-act=navtoggle]:not([aria-hidden])'); break;
    case 'l': case 'L': e.preventDefault(); placeDialog(); break;          // 1.11.0: choose the location
    case '?': e.preventDefault(); shortcutsDialog(); break;
    case '/': {
      e.preventDefault();
      const d = document.getElementById('pn-filters'); if (d) d.open = true;
      const q = document.querySelector('input[data-f=q]'); if (q) { q.focus(); q.select(); } else go('#/');
      break;
    }
  }
});
window.addEventListener('hashchange', () => stopReading(true));
async function condDialog() {
  const c = COND || await loadCond() || { mode: 'manual' };
  const W = await api('GET', '/api/weather').catch(() => null);
  const radio = (v, l, hint) => html`<label class="chk-row" style="border:0"><input type="radio" name="csrc" value="${v}" ${c.mode === v ? raw('checked') : ''}><span><strong>${l}</strong>${hint ? html`<br><span class="hint">${hint}</span>` : ''}</span></label>`;
  const r = await modal(html`<form method="dialog"><h2>Current conditions</h2>
    <p>These feed the "Now" marker on every plant page and the steps for getting a plant back in range.</p>
    <fieldset class="opt-group"><legend>Where do the numbers come from?</legend>
      ${radio('manual', 'I will type them in', 'Use this until you have a sensor. Measure or estimate where the plant is.')}
      ${radio('sensor', 'My sensor', W && W.sensor.count ? 'The newest reading it sent.' : 'No sensor has sent a reading yet. See Weather, Connect your sensor.')}
      ${radio('weather', 'Online weather', 'Open sky for ' + (W ? W.location.name : 'your area') + '. Plants under a roof or in shade get less light than this.')}</fieldset>
    <div id="manual-fields" ${c.mode === 'manual' ? '' : raw('hidden')}><div class="field-grid">
      <label class="f">Temperature (°F)<input type="number" step="any" name="t" value="${has(c.temp_f) && c.mode === 'manual' ? c.temp_f : ''}"></label>
      <label class="f">Humidity (%)<input type="number" step="any" name="h" min="0" max="100" value="${has(c.humidity) && c.mode === 'manual' ? c.humidity : ''}"></label>
      <label class="f">Light<input type="number" step="any" name="l" min="0" value="${has(c.par) && c.mode === 'manual' ? c.par : ''}"></label>
      <label class="f">Light is in<select name="lu"><option value="par">PAR (µmol/m²/s)</option><option value="lux">lux</option></select></label></div>
      <p class="hint">Leave a box empty to keep the last value you typed. Rough light guides when you have no meter: full midday sun about 1,500 to 2,000 PAR (80,000 to 110,000 lux); open shade 200 to 600; under a porch roof 100 to 400; a bright window indoors 100 to 300; a room lit only by a lamp 5 to 30. About 54 lux is 1 PAR in sunlight.</p></div>
    <div class="row"><button class="btn" value="ok">Save</button><button class="btn ghost" value="cancel">Cancel</button></div></form>`);
  if (r !== 'ok') return;
  const f = dlg.querySelector('form'), mode = (dlg.querySelector('[name=csrc]:checked') || {}).value || 'manual';
  const body = { mode };
  if (mode === 'manual') {
    const v = n => dlg.querySelector('[name=' + n + ']').value;
    body.temp_f = v('t'); body.humidity = v('h');
    if (dlg.querySelector('[name=lu]').value === 'lux') body.lux = v('l'); else body.par = v('l');
  }
  await guard(async () => { COND = await api('PUT', '/api/current', body); toast('Current conditions saved'); await route(); });
}

// ---------- photo check before adding photos (added in 1.8.0) ----------
// Each photo is checked in the browser before it is uploaded. The limits were set on Ethan's own photos in
// dev/photos-raw: none of those is flagged, while the same photos blurred, darkened or washed out are.
const PCHK = { dark: 45, black: 0.5, bright: 200, white: 0.2, blur: 35, small: 640 };
async function photoStats(file) {
  let bmp;
  try { bmp = await createImageBitmap(file); } catch (e) { return null; }      // a format this browser cannot read: no check
  const s = Math.min(1, 512 / Math.max(bmp.width, bmp.height)), w = Math.max(3, Math.round(bmp.width * s)), h = Math.max(3, Math.round(bmp.height * s));
  const cv = document.createElement('canvas'); cv.width = w; cv.height = h;
  const cx = cv.getContext('2d', { willReadFrequently: true }); cx.drawImage(bmp, 0, 0, w, h);
  const d = cx.getImageData(0, 0, w, h).data, L = new Float32Array(w * h);
  let sum = 0, black = 0, white = 0;
  for (let i = 0, p = 0; p < L.length; i += 4, p++) {
    const v = 0.2126 * d[i] + 0.7152 * d[i + 1] + 0.0722 * d[i + 2];
    L[p] = v; sum += v; if (v < 16) black++; if (v >= 250) white++;
  }
  // Sharpness: how much the brightness changes between neighbouring pixels, in a 4 x 4 grid of squares. The third
  // sharpest square counts, so a blurred background behind a sharp plant does not make the photo "blurry".
  const tiles = [];
  for (let ty = 0; ty < 4; ty++) for (let tx = 0; tx < 4; tx++) {
    const y0 = Math.max(1, Math.floor(ty * h / 4)), y1 = Math.min(h - 1, Math.floor((ty + 1) * h / 4));
    const x0 = Math.max(1, Math.floor(tx * w / 4)), x1 = Math.min(w - 1, Math.floor((tx + 1) * w / 4));
    let n = 0, m = 0, m2 = 0;
    for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) { const p = y * w + x, v = L[p - w] + L[p + w] + L[p - 1] + L[p + 1] - 4 * L[p]; n++; m += v; m2 += v * v; }
    tiles.push(n ? m2 / n - (m / n) ** 2 : 0);
  }
  tiles.sort((a, b) => b - a);
  return { w: bmp.width, h: bmp.height, mean: sum / L.length, black: black / L.length, white: white / L.length, sharp: tiles[2], bmp };
}
function photoProblems(s) {
  const p = [];
  if (s.mean < PCHK.dark || s.black > PCHK.black) p.push(['Too dark', 'Turn on a light or take the plant into daylight.']);
  else if (s.mean > PCHK.bright || s.white > PCHK.white) p.push(['Too bright (washed out)', 'Keep strong sun off the leaves and out of the background; shade the plant or stand with the sun behind you.']);
  if (s.sharp < PCHK.blur) p.push(['Blurry', 'Hold the phone still, tap the screen on the plant so it focuses, and wait a moment before taking the picture.']);
  if (Math.max(s.w, s.h) < PCHK.small) p.push(['Very small picture', `Only ${s.w} by ${s.h} pixels. Send the photo from the camera at full size, not a screenshot or a thumbnail.`]);
  return p;
}
async function photoCheck(files, input) {
  // Returns the files to upload, or null to add none. Photos that pass are added without asking.
  if (!window.createImageBitmap) return files;
  const n = files.length, checked = [];
  for (const f of files) { let s = null; try { s = await photoStats(f); } catch (e) { s = null; } checked.push({ f, s, probs: s ? photoProblems(s) : [] }); }
  const done = () => checked.forEach(c => c.s && c.s.bmp.close && c.s.bmp.close());
  const bad = checked.filter(c => c.probs.length), good = n - bad.length;
  if (!bad.length) { done(); return files; }
  const pr = modal(html`<form method="dialog" class="pchk"><h2>${n === 1 ? 'Check this photo' : `Check ${bad.length} of these ${n} photos`}</h2>
    <p>${bad.length === 1 ? 'It' : 'They'} may be hard to use for identifying the plant or seeing how it is doing.</p>
    <ul class="pchk-list">${bad.map((c, i) => html`<li><canvas class="pchk-thumb" data-i="${i}" width="120" height="120" role="img" aria-label="${'Preview of ' + c.f.name}"></canvas>
      <div><p class="pchk-name">${c.f.name}</p><ul>${c.probs.map(p => html`<li><strong>${p[0]}.</strong> ${p[1]}</li>`)}</ul></div></li>`)}</ul>
    <div class="row">
      ${input ? html`<button class="btn" value="again" autofocus>Take ${bad.length === 1 ? 'a new one' : 'new ones'}</button>` : ''}
      ${good ? html`<button class="btn ghost" value="good">Add only the ${good} good one${good === 1 ? '' : 's'}</button>` : ''}
      <button class="btn ghost" value="all" ${input ? '' : raw('autofocus')}>Add ${n === 1 ? 'it' : n === 2 ? 'both' : `all ${n}`} anyway</button>
      <button class="btn ghost" value="cancel">Cancel</button></div></form>`);
  document.querySelectorAll('#dlg canvas.pchk-thumb').forEach(cv => {        // previews are drawn, so the page's security rules need no change
    const box = cv.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
    if (box.width) { cv.width = Math.round(box.width * dpr); cv.height = Math.round(box.height * dpr); }
    const b = bad[+cv.dataset.i].s.bmp, k = Math.min(cv.width / b.width, cv.height / b.height), w = b.width * k, h = b.height * k;
    cv.getContext('2d').drawImage(b, (cv.width - w) / 2, (cv.height - h) / 2, w, h);
  });
  const r = await pr; done();
  if (r === 'all') return files;
  if (r === 'good') return checked.filter(c => !c.probs.length).map(c => c.f);
  if (r === 'again' && input) { input.value = ''; input.click(); }
  return null;
}
window.PlantPhotoCheck = { stats: photoStats, problems: photoProblems };     // for dev/test/photocheck_check.py
// ---------- photos page ----------
let TODO = [];
async function viewPhotos() {
  const [un, todo] = await Promise.all([api('GET', '/api/photos/unassigned'), api('GET', '/api/to-photograph')]);
  return {
    title: 'Photos',
    html: html`<h1>Photos</h1><p class="muted">Garden overview shots and anything not yet matched to a plant.</p>
    <section class="blk"><h2>Photos without a plant (${un.length})</h2>
      <label class="f" style="max-width:420px">Upload photos<small>They stay here until you assign them to a plant.</small><input type="file" accept="image/*" multiple data-act="addloose"></label>
      ${un.length ? html`<div class="pgrid">${un.map(x => html`<div class="pcard"><img src="${thumbUrl(x.file)}" alt="${x.caption || 'Unassigned photo'}" data-act="zoomloose" data-file="${x.file}" data-cap="${x.caption}">
        <div class="b"><p style="margin:0 0 8px">${x.caption || 'No caption'}</p><div class="row"><button class="btn small" type="button" data-act="assign" data-id="${x.id}">Assign to a plant</button>
        <button class="btn danger small" type="button" data-act="rmloose" data-id="${x.id}">Remove</button></div></div></div>`)}</div>` : html`<div class="empty">Every photo is assigned to a plant.</div>`}</section>
    <section class="blk"><h2>Still to photograph</h2><p class="muted">Plants and areas where one more picture would help Claude identify or assess them.</p>
      <form class="todo-form" data-form="todo"><div class="field-grid">
        <label class="f">What to photograph<input type="text" name="label" maxlength="200" required placeholder="For example: tag on the maroon pot"></label>
        <label class="f">Note (optional)<input type="text" name="note" maxlength="1000" placeholder="Where it is, what to capture"></label>
        <label class="f">Related plant (optional)<select name="plant" class="w-fixed"><option value="">None</option>${[...PCODES.values()].map(p => html`<option value="${p.code}">${p.code} ${p.common_name}</option>`)}</select></label></div>
        <p class="hint">Plant codes such as P-012 typed anywhere in the text become links; point at one to see a photo of that plant.</p>
        <button class="btn" type="submit">Add to the list</button></form>
      ${todo.length ? todo.map(t => html`<div class="chk-row"><input type="checkbox" data-act="tododone" data-id="${t.id}" ${t.done ? raw('checked') : ''} aria-label="Done: ${t.label}">
        <div class="grow"><div class="${t.done ? 'done' : ''}"><strong>${linkify(t.label)}</strong></div>${t.note ? html`<div class="muted ${t.done ? 'done' : ''}">${linkify(t.note)}</div>` : ''}</div>
        <div class="row" style="gap:.4rem"><button class="btn ghost small" type="button" data-act="todoedit" data-id="${t.id}" aria-label="Edit: ${t.label}">Edit</button>
        <button class="btn danger small" type="button" data-act="tododel" data-id="${t.id}" aria-label="Delete: ${t.label}">Delete</button></div></div>`) : html`<div class="empty">Nothing on the list.</div>`}</section>`,
    after: () => { TODO = todo; },
  };
}

// ---------- backups page ----------
const mb = n => n >= 1073741824 ? (n / 1073741824).toFixed(1) + ' GB' : n >= 1048576 ? (n / 1048576).toFixed(1) + ' MB' : Math.max(1, Math.round(n / 1024)) + ' KB';
const BK_FREQ_WORDS = { '6h': 'Every 6 hours', '12h': 'Every 12 hours', daily: 'Every day', '3d': 'Every 3 days', weekly: 'Every week' };
const BK_KIND = { manual: 'Made by you', auto: 'Automatic', update: 'Before an update' };
let BK = null;
async function viewBackups() {
  if (ME().role !== 'owner') return { title: 'Backups', html: html`<h1>Backups</h1><p class="notice">Backups are looked after by ${ME().owner_name}. They hold a copy of everything, so only the owner can make, download or restore them.</p>` };
  BK = await api('GET', '/api/backups');
  const S = BK.settings, hourOpt = h => new Date(2026, 0, 1, h).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  const where = BK.mounted ? 'the backups folder inside your plant-database folder' : 'data\\backups inside your plant-database folder';
  const last = BK.backups[0];
  return {
    title: 'Backups',
    html: html`<h1>Backups</h1>
    <p class="muted">A backup is a zip with a complete copy of the database (plants, change log, weather history, feeding log, settings) and, if you choose, all the photos. Backups are saved in ${where}, so they survive updates. Copy a few to another drive now and then.</p>
    <p class="${last ? 'notice ok' : 'notice'}" role="status">${last ? html`Latest backup: <strong>${when(last.created_at)}</strong> (${BK_KIND[last.kind]}, ${mb(last.bytes)}).` : 'No backups yet. Make one now.'}
      ${S.enabled ? ` Automatic backups: ${BK_FREQ_WORDS[S.freq].toLowerCase()}${['daily', '3d', 'weekly'].includes(S.freq) ? ' at about ' + hourOpt(S.hour) : ''}.` : ' Automatic backups are off.'}</p>
    <section class="blk"><h2>Back up now</h2>
      <form data-form="bknow"><div class="field-grid">
        <label class="f">Note (optional)<input type="text" name="note" maxlength="300" placeholder="For example: before repotting day"></label></div>
        <label class="chk-row" style="border:0"><input type="checkbox" name="photos"><span>Include the photos (adds about ${mb(BK.photo_bytes)})</span></label>
        <div class="row"><button class="btn" type="submit">Back up now</button></div></form>
      <div id="bk-job" role="status" aria-live="polite">${bkJobHtml(BK.job)}</div></section>
    <section class="blk"><h2>Automatic backups</h2>
      <form data-form="bkset"><label class="chk-row" style="border:0"><input type="checkbox" name="enabled" ${S.enabled ? raw('checked') : ''}><span>Make backups automatically</span></label>
        <div class="field-grid">
          <label class="f">How often<select name="freq">${BK.freqs.map(f => html`<option value="${f}" ${S.freq === f ? raw('selected') : ''}>${BK_FREQ_WORDS[f]}</option>`)}</select></label>
          <label class="f">At about<small>For daily, 3-day and weekly backups</small><select name="hour">${[...Array(24).keys()].map(h => html`<option value="${h}" ${+S.hour === h ? raw('selected') : ''}>${hourOpt(h)}</option>`)}</select></label>
          <label class="f">Keep this many automatic backups<small>Older automatic ones are deleted. Your own backups are never deleted automatically.</small><input type="number" name="keep" min="1" max="365" value="${S.keep}"></label></div>
        <label class="chk-row" style="border:0"><input type="checkbox" name="photos" ${S.photos ? raw('checked') : ''}><span>Include the photos in automatic backups</span></label>
        <p class="hint">The database is ${mb(BK.db_bytes)} (most of it is weather history); a backup zip is usually a third to a half of that. Backups now use ${mb(BK.total_bytes)}; ${mb(BK.free_bytes)} free. The app must be running for automatic backups; a missed one runs when it next starts.</p>
        <button class="btn" type="submit">Save automatic backup settings</button></form></section>
    <section class="blk"><h2>Your backups (${BK.backups.length})</h2>
      ${BK.backups.length ? html`<div class="tbl-wrap"><table class="tbl"><caption class="sr">Backups, newest first</caption><thead><tr><th scope="col">Made</th><th scope="col">Type</th><th scope="col" class="num">Size</th><th scope="col">Contents</th><th scope="col"><span class="sr">Actions</span></th></tr></thead><tbody>
        ${BK.backups.map(b => html`<tr><th scope="row">${when(b.created_at)}${b.note ? html`<div class="hint">${b.note}</div>` : ''}</th><td>${BK_KIND[b.kind]}${b.by && b.kind !== 'auto' ? html`<div class="hint">${b.by}</div>` : ''}</td>
          <td class="num">${mb(b.bytes)}</td><td>${b.broken ? html`<strong>Damaged file</strong>` : html`Database${b.photos ? ' and photos' : ''}${b.plants != null ? `, ${b.plants} plants` : ''}${b.version ? html`<div class="hint">App version ${b.version}</div>` : ''}`}</td>
          <td><div class="row" style="gap:.4rem"><a class="btn small" href="/api/backups/${enc(b.file)}" download>Download</a><button class="btn small danger" type="button" data-act="bkdel" data-file="${b.file}">Delete</button></div></td></tr>`)}</tbody></table></div>` : html`<div class="empty">No backups yet.</div>`}</section>
    <section class="blk"><h2>Restoring a backup</h2>
      <ol><li>Stop the app (in the plant-database folder): <span class="code">docker compose down</span></li>
        <li>Rename the current <span class="code">data\\plants.db</span> to <span class="code">plants-old.db</span> (keep it until you are sure).</li>
        <li>Open the backup zip and copy <span class="code">plants.db</span> into the <span class="code">data</span> folder. If the backup has a <span class="code">photos</span> folder, copy its files into <span class="code">data\\photos</span>.</li>
        <li>Start the app: <span class="code">docker compose up -d</span></li></ol>
      <p class="hint">The README has these steps as cmd.exe, PowerShell and bash commands.</p></section>`,
    after: () => { if (BK.job && BK.job.running) bkPoll(); },
  };
}
function bkJobHtml(j) {
  if (!j || (!j.running && !j.finished)) return '';
  if (j.running) return html`<p class="notice">Making a backup${j.photos ? ' with photos' : ''}… this takes a few seconds (longer with photos).</p>`;
  return j.ok ? html`<p class="notice ok">Backup finished ${when(j.finished)}: ${j.file}</p>` : html`<p class="notice bad">Backup failed: ${j.error}</p>`;
}
async function bkPoll() {
  const el = document.getElementById('bk-job'); if (!el) return;
  let j; try { j = await api('GET', '/api/backups/job'); } catch (e) { return; }
  el.innerHTML = rend(bkJobHtml(j));
  if (j.running) setTimeout(bkPoll, 1500); else if (location.hash.startsWith('#/backups')) { toast(j.ok ? 'Backup finished' : 'Backup failed', !j.ok); route(); }
}

// ---------- labels page ----------
function labelCard(p, base, withLink) {
  return html`<div class="lblwrap"><div class="lbl"><img src="/api/plants/${enc(p.code)}/qr.svg?base=${enc(base)}" alt="QR code for ${p.code}" width="96" height="96" loading="lazy">
    <div><span class="code">${p.code}</span><b>${p.common_name}</b><span class="sci latin">${p.scientific_name || ''}</span></div></div>
    ${withLink ? html`<a class="btn small ghost noprint lbl-open" href="#/plant/${enc(p.code)}" aria-label="Open the page for ${p.code} ${p.common_name}">Open plant page</a>` : ''}</div>`;
}
async function viewLabels() {
  const [list, st] = await Promise.all([api('GET', '/api/plants'), api('GET', '/api/settings')]);
  const base = st.base_url || location.origin;
  const local = /^https?:\/\/(localhost|127\.|\[::1\])/i.test(base);
  return {
    title: 'Labels',
    html: html`<h1>Plant labels</h1><p class="muted">Print these, cut them out and stick one on each pot. Scanning the code with a phone opens that plant's page.</p>
    <div class="noprint">
      <form class="todo-add" data-form="base"><label style="flex:1 1 320px;font-weight:700">Address the codes should open<input type="text" name="base" value="${st.base_url}" placeholder="http://192.168.1.20:8080" inputmode="url"></label>
        <button class="btn" type="submit" style="align-self:end">Save address</button></form>
      ${/\.ts\.net$/i.test(base) ? html`<div class="notice ok">Codes open <strong>${base}</strong>, the app's Tailscale address. Any phone signed in to Tailscale can open them, at home or away, including people you have shared the app with.</div>`
        : local ? html`<div class="notice">The codes currently point to <strong>${base}</strong>, which only works on this computer. A phone cannot open that. Use the app's Tailscale address (README: "Using the app away from home").</div>`
        : html`<div class="notice">Codes open <strong>${base}</strong>. That address only works on your home network, and from version 1.12.0 the app is closed to the home network unless you open it again (README). The Tailscale address works everywhere.</div>`}
      ${/\.ts\.net$/i.test(location.hostname) && base !== location.origin && ME().role === 'owner' ? html`<p><button class="btn ghost" type="button" data-act="usethisbase">Use this address for the codes: ${location.origin}</button></p>` : ''}
      <p class="row"><button class="btn" type="button" data-act="print">Print labels</button>
        <a class="btn ghost" href="/card.html?all=1">Print care cards for all plants</a></p>
      <p class="hint">Care cards: a 4 × 6 inch card (or a full page) for each plant, with its water, light, temperature, humidity, feeding and dangers in big type.</p></div>
    <div class="lsheet">${list.map(p => labelCard(p, base, true))}</div>`,
  };
}

// ---------- audit log page: every change to every record, with filters (1.10.0; was the Change log page) ----------
const AUD = { f: { q: '', plant: '', who: '', kind: '', field: '', from: '', to: '', order: 'desc' }, offset: 0, limit: 100, facets: null, total: 0, t: null };
try { const s = JSON.parse(localStorage.getItem('plantdb.auditf') || '{}'); Object.keys(AUD.f).forEach(k => { if (typeof s[k] === 'string') AUD.f[k] = s[k]; }); } catch (e) { /* defaults */ }
const audSave = () => { try { localStorage.setItem('plantdb.auditf', JSON.stringify(AUD.f)); } catch (e) { /* not remembered */ } };
function audQS(extra) {
  const p = new URLSearchParams();
  Object.entries(AUD.f).forEach(([k, v]) => { if (v && !(k === 'order' && v === 'desc')) p.set(k, v); });
  Object.entries(extra || {}).forEach(([k, v]) => p.set(k, v));
  return p.toString();
}
const audClip = (v, n) => { v = v == null ? '' : String(v).replace(/\s+/g, ' ').trim(); return v.length > n ? v.slice(0, n - 1) + '…' : v; };
const AUD_FIELD_ACTS = ['update', 'edit', 'restore', 'archive', 'unarchive'];
function auditChange(a) {        // "Health rating: from Poor to Fair", for a change to one field of a plant page; '' for anything else
  if (!a.field || !AUD_FIELD_ACTS.includes(a.action)) return '';
  const o = audClip(a.old_value, 60), n = audClip(a.new_value, 60);
  return `${a.label}: ${!o ? 'set to ' + (n || '(empty)') : !n ? 'cleared (it was ' + o + ')' : 'from ' + o + ' to ' + n}`;
}
const shortWho = w => { const m = /^Claude \((batch [^,)]+)/.exec(w || ''); return m ? 'Claude, ' + m[1] : w; };
function audCell(v) {
  if (v == null || v === '') return '';
  const s = String(v);
  return s.length > 160 ? html`<details class="aud-more"><summary>${s.slice(0, 120)}…</summary><div class="aud-full">${s}</div></details>` : s;
}
function audBefore(a) {         // a field that had no value before says so, rather than leaving a blank
  if ((a.old_value == null || a.old_value === '') && auditChange(a)) return html`<td data-label="Before"><span class="muted">Not set</span></td>`;
  return html`<td data-label="Before" class="old">${audCell(a.old_value)}</td>`;
}
function audRecord(a) {
  if (a.plant_code) return html`<a href="#/plant/${enc(a.plant_code)}">${a.plant_code}</a>${a.plant_name ? html` <span class="muted">${a.plant_name}</span>` : ''}`;
  return { setting: 'Setting', backup: 'Backup', request: 'General request', todo: '"Still to photograph" list', photo_add: 'Photos page', photo_remove: 'Photos page', photo_caption: 'Photos page', note: 'Update' }[a.action] || 'Not about one plant';
}
function audRows(list) {
  if (!list.length) return html`<div class="empty">No changes match these filters.<p><button class="btn ghost small" type="button" data-act="audclear">Clear filters</button></p></div>`;
  return html`<div class="tbl-wrap aud-wrap"><table class="tbl aud-tbl"><caption class="sr">Changes</caption>
    <thead><tr><th scope="col">When</th><th scope="col">Record</th><th scope="col">Who</th><th scope="col">What</th><th scope="col">Before</th><th scope="col">After</th></tr></thead>
    <tbody>${list.map(a => html`<tr><td data-label="When">${timeEl(a.changed_at)}</td><td data-label="Record">${audRecord(a)}${a.version != null ? html`<div class="muted">Version ${a.version}</div>` : ''}</td>
      <td data-label="Who">${a.changed_by}</td>
      <td data-label="What"><strong>${a.action_word}</strong>${a.label && a.label !== a.action_word ? html`: ${a.label}` : ''}${a.note && a.note !== a.action_word ? html`<div class="muted">${a.note}</div>` : ''}</td>
      ${audBefore(a)}<td data-label="After" class="new">${audCell(a.new_value)}</td></tr>`)}</tbody></table></div>`;
}
const audInUse = () => Object.entries(AUD.f).filter(([k, v]) => v && k !== 'order').length;
const audInUseWords = () => { const n = audInUse(); return n ? `: ${n} in use` : ''; };
function audWords() {
  const F = AUD.facets || {}, f = AUD.f, w = [];
  if (f.q) w.push(`containing "${f.q}"`);
  if (f.plant === '-') w.push('not about one plant'); else if (f.plant) w.push('for ' + f.plant);
  if (f.who === '~people') w.push('by people'); else if (f.who === '~claude') w.push("from Claude's updates"); else if (f.who) w.push('by ' + f.who);
  if (f.kind) w.push((((F.kinds || []).find(k => k.key === f.kind)) || { label: f.kind }).label.toLowerCase());
  if (f.field) w.push('field: ' + (((F.fields || []).find(x => x.name === f.field)) || { label: f.field }).label);
  if (f.from) w.push('from ' + midDay(f.from)); if (f.to) w.push('to ' + midDay(f.to));
  return w.join(', ');
}
async function audLoad(focusSel) {
  const box = document.getElementById('aud-list'); if (!box) return;
  let r;
  try { r = await api('GET', '/api/audit/search?' + audQS({ limit: AUD.limit, offset: AUD.offset })); }
  catch (e) { box.innerHTML = rend(html`<p class="notice bad">Could not load the audit log: ${e.message}</p>`); return; }
  AUD.total = r.total;
  const end = Math.min(r.offset + r.entries.length, r.total), words = audWords();
  document.getElementById('aud-sum').textContent = r.total ? `Showing ${(r.offset + 1).toLocaleString()} to ${end.toLocaleString()} of ${r.total.toLocaleString()} ${r.total === 1 ? 'change' : 'changes'}${words ? ' ' + words : ''}.` : `No changes${words ? ' ' + words : ''}.`;
  box.innerHTML = rend(audRows(r.entries));
  const pages = Math.max(1, Math.ceil(r.total / AUD.limit)), page = Math.floor(r.offset / AUD.limit) + 1;
  const pager = document.getElementById('aud-pager');
  if (pager) pager.innerHTML = rend(pages > 1 ? html`<button class="btn small ghost" type="button" data-act="audpage" data-d="-1" ${page <= 1 ? raw('disabled') : ''}>Previous page</button>
    <span>Page ${page} of ${pages}</span><button class="btn small ghost" type="button" data-act="audpage" data-d="1" ${page >= pages ? raw('disabled') : ''}>Next page</button>` : '');
  const csv = document.getElementById('aud-csv'); if (csv) csv.href = '/api/audit.csv?' + audQS();
  const iu = document.getElementById('aud-inuse'); if (iu) iu.textContent = audInUseWords();
  if (focusSel) { const el = document.querySelector(focusSel); if (el) el.focus({ preventScroll: true }); }
}
async function viewHistory() {
  AUD.facets = await api('GET', '/api/audit/facets');
  const F = AUD.facets, f = AUD.f, sel = (k, v) => v === f[k] ? raw('selected') : '';
  return {
    title: 'Audit log',
    html: html`<div class="hero"><div><h1>Audit log</h1><p class="muted">Every change to every record: plant pages, photos, feeding and care, requests, settings and backups. ${F.total.toLocaleString()} changes since ${F.first ? midDay(F.first.slice(0, 10)) : 'the start'}. Times are shown in your time zone.</p></div>
      <div class="row noprint"><a class="btn ghost small" href="/api/export.csv">Download plants (CSV)</a><a class="btn ghost small" href="/api/readings.csv">Download weather and sensor readings (CSV)</a><a class="btn ghost small" href="/api/export.json">Download all data (JSON)</a></div></div>
    <details class="aud-fbox noprint" id="aud-fbox" ${document.documentElement.dataset.narrow !== '1' || audInUse() ? raw('open') : ''}><summary>Filters<span id="aud-inuse">${audInUseWords()}</span></summary>
    <form class="aud-filters" role="search" aria-label="Filter the audit log" data-form="audf">
      <label class="f aud-q">Search<input type="search" name="q" data-f="audq" value="${f.q}" placeholder="Words, plant code or name"></label>
      <label class="f">Plant<select name="plant" data-f="aud"><option value="">All plants</option><option value="-" ${sel('plant', '-')}>Not about one plant</option>
        ${F.plants.map(p => html`<option value="${p.code}" ${sel('plant', p.code)}>${p.code} ${p.name}${p.status === 'archived' ? ' (archived)' : ''}</option>`)}</select></label>
      <label class="f">Who<select name="who" data-f="aud"><option value="">Everyone</option><option value="~people" ${sel('who', '~people')}>People (not Claude's updates)</option><option value="~claude" ${sel('who', '~claude')}>Claude's updates (all)</option>
        ${F.who.map(w => html`<option value="${w.name}" ${sel('who', w.name)}>${w.name} (${w.count})</option>`)}</select></label>
      <label class="f">Kind of change<select name="kind" data-f="aud"><option value="">Any kind</option>${F.kinds.map(k => html`<option value="${k.key}" ${sel('kind', k.key)}>${k.label}</option>`)}</select></label>
      <label class="f">Field<select name="field" data-f="aud"><option value="">Any field</option>${F.fields.map(x => html`<option value="${x.name}" ${sel('field', x.name)}>${x.label}</option>`)}</select></label>
      <label class="f">From<input type="date" name="from" data-f="aud" value="${f.from}"></label>
      <label class="f">To<input type="date" name="to" data-f="aud" value="${f.to}"></label>
      <label class="f">Order<select name="order" data-f="aud"><option value="desc">Newest first</option><option value="asc" ${sel('order', 'asc')}>Oldest first</option></select></label>
      <div class="row aud-acts"><button class="btn small ghost" type="button" data-act="audclear">Clear filters</button><a class="btn small ghost" id="aud-csv" href="/api/audit.csv">Download these changes (CSV)</a>
        <button class="btn small ghost" type="button" data-act="audrefresh">Refresh</button></div></form></details>
    <p class="hint noprint">To watch changes as they happen, turn on the audit log console with the Debug button.</p>
    <p id="aud-sum" class="aud-sum" role="status" aria-live="polite">Loading the audit log</p>
    <div id="aud-list"></div>
    <nav class="pager aud-pager row" id="aud-pager" aria-label="Pages of changes"></nav>`,
    after: () => audLoad(),
  };
}

// ---------- the Debug button and the live audit log console (added in 1.10.0) ----------
const DBG = { console: '0', lines: '4', announce: '0' };
try { const s = JSON.parse(localStorage.getItem('plantdb.debug') || '{}'); Object.keys(DBG).forEach(k => { if (typeof s[k] === 'string') DBG[k] = s[k]; }); } catch (e) { /* defaults */ }
const dbgSave = () => { try { localStorage.setItem('plantdb.debug', JSON.stringify(DBG)); } catch (e) { /* not remembered */ } };
const CON = { last: 0, timer: null, paused: false, unseen: 0, busy: false, failed: 0, stick: true };   // stick: the view is at the newest change, so new ones scroll into view
function conEl(id) { return document.getElementById(id); }
function conRow(a) {
  const t = new Date(a.changed_at).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', second: '2-digit' });
  return html`<div class="con-row" data-id="${a.id}"><time datetime="${a.changed_at}" title="${when(a.changed_at)}">${t}</time>
    <span class="con-who" title="${a.changed_by}">${shortWho(a.changed_by)}</span>${a.plant_code ? html` <a href="#/plant/${enc(a.plant_code)}">${a.plant_code}</a>` : ''}
    <span class="con-what">${auditChange(a) || html`<strong>${a.action_word}:</strong> ${a.note || a.label || ''}`}</span></div>`;
}
function conAtBottom() { return CON.stick; }
function conScrolled() { const b = conEl('con-body'); CON.stick = !b || b.scrollTop + b.clientHeight >= b.scrollHeight - 6; if (CON.stick && CON.unseen) { CON.unseen = 0; const n = conEl('con-new'); if (n) n.hidden = true; } }
function conAdd(rows, first) {
  const b = conEl('con-body'); if (!b || !rows.length) return;
  const stick = first || conAtBottom();
  if (first) b.innerHTML = ''; else b.querySelectorAll('p.muted').forEach(x => x.remove());
  b.insertAdjacentHTML('beforeend', rend(html`${rows.map(conRow)}`));
  while (b.children.length > 200) b.firstElementChild.remove();
  conLayout(); fitPanes();
  if (stick) { b.scrollTop = b.scrollHeight; CON.unseen = 0; CON.stick = true; } else CON.unseen += first ? 0 : rows.length;
  const n = conEl('con-new');
  if (n) { n.hidden = !CON.unseen; n.textContent = `${CON.unseen} new ${CON.unseen === 1 ? 'change' : 'changes'} below: show`; }
}
function conState(text) { const s = conEl('con-state'); if (s && s.textContent !== text) s.textContent = text; }
async function conPoll() {
  if (CON.busy || CON.paused || document.hidden || DBG.console !== '1') return;
  CON.busy = true;
  try {
    const first = !CON.started;
    const rows = first ? (await api('GET', '/api/audit?limit=60')).reverse() : await api('GET', '/api/audit?after=' + CON.last + '&limit=100');
    if (CON.paused || DBG.console !== '1') return;        // paused or closed while this check was on its way: Resume picks these up
    if (rows.length) { CON.last = rows[rows.length - 1].id; conAdd(rows, first); }
    else if (first) { const b = conEl('con-body'); if (b) b.innerHTML = rend(html`<p class="muted">Nothing logged yet.</p>`); }
    CON.started = true;
    CON.failed = 0; conState(CON.paused ? 'Paused' : 'Live');
  } catch (e) { CON.failed++; if (!CON.paused) conState('Cannot reach the app, trying again'); }
  finally { CON.busy = false; }
}
function pinLayout() {           // phones: the buttons pinned to the bottom of the screen stack up instead of covering each other
  const r = document.documentElement, tab = conEl('nav-tab'), corner = conEl('corner'), job = conEl('job-badge');
  const shown = e => e && e.getClientRects().length && getComputedStyle(e).display !== 'none';
  if (r.dataset.narrow !== '1' || !corner) { r.dataset.tabup = '0'; if (tab) tab.style.bottom = ''; if (job) job.style.bottom = ''; return; }
  const cr = corner.getBoundingClientRect();
  let top = cr.top;
  if (shown(tab)) {             // Sections sits beside Debug and Display when there is room, above them when not
    const up = tab.getBoundingClientRect().right > cr.left - 8;
    tab.style.bottom = up ? Math.round(innerHeight - cr.top + 8) + 'px' : '';
    r.dataset.tabup = up ? '1' : '0';
    top = Math.min(top, tab.getBoundingClientRect().top);
  } else r.dataset.tabup = '0';
  if (job) job.style.bottom = Math.round(innerHeight - top + 8) + 'px';
}
function conLayout() {
  pinLayout();
  const c = conEl('console'), r = document.documentElement; if (!c) return;
  if (c.hidden) { r.style.setProperty('--console-space', '0px'); return; }
  const narrow = r.dataset.narrow === '1', side = window.PlantPrefs.get().navside, navOpen = r.dataset.navopen === '1';
  const navW = navOpen ? (conEl('sidenav') || { offsetWidth: 0 }).offsetWidth : 0, corner = conEl('corner');
  let left = 12, right = 12;
  if (!narrow) {               // bottom left, clear of the side menu and of the Debug and Display buttons
    left = 16 + (side !== 'right' ? navW : 0);
    right = (corner ? corner.offsetWidth : 0) + 32 + (side === 'right' ? navW : 0);
  }
  c.style.left = left + 'px'; c.style.right = right + 'px';
  const body = conEl('con-body');            // tall enough for the newest 3, 4 or 5 changes; older ones are a scroll away
  if (body) {
    const stick = conAtBottom(), rows = [...body.querySelectorAll('.con-row')].slice(-Number(DBG.lines));
    const h = rows.reduce((t, x) => t + x.offsetHeight, 0);
    body.style.height = h ? h + 'px' : '';
    if (stick) body.scrollTop = body.scrollHeight;
  }
  let bottom = 16;             // sit above any button pinned to the bottom of the screen that it would cover
  ['corner', 'nav-tab', 'job-badge'].forEach(id => {
    const e = conEl(id); if (!e || !e.getClientRects().length || getComputedStyle(e).display === 'none' || getComputedStyle(e).visibility === 'hidden') return;
    const b = e.getBoundingClientRect();
    if (b.top < innerHeight / 2 || b.right <= left || b.left >= innerWidth - right) return;
    bottom = Math.max(bottom, Math.round(innerHeight - b.top + 8));
  });
  c.style.bottom = bottom + 'px';
  r.style.setProperty('--console-space', Math.round(c.offsetHeight + bottom + 8) + 'px');
}
function conApply() {
  const c = conEl('console'), on = DBG.console === '1'; if (!c) return;
  c.hidden = !on; document.documentElement.dataset.console = on ? '1' : '0';
  c.style.setProperty('--con-lines', DBG.lines);
  const b = conEl('con-body'); if (b) b.setAttribute('aria-live', DBG.announce === '1' ? 'polite' : 'off');
  clearInterval(CON.timer); CON.timer = null;
  if (on && !CON.on) {          // just turned on: start again from the newest changes
    Object.assign(CON, { started: false, last: 0, unseen: 0, stick: true, paused: false });
    const p = c.querySelector('[data-act=conpause]'); if (p) { p.textContent = 'Pause'; p.setAttribute('aria-pressed', 'false'); }
    const n = conEl('con-new'); if (n) n.hidden = true;
  }
  CON.on = on;
  if (on) { conPoll(); CON.timer = setInterval(conPoll, 3000); }
  conLayout(); fitPanes();
}
function debugDialog() {
  const r = document.documentElement, P = window.PlantPrefs.get();
  modal(html`<form method="dialog" class="dbg"><h2>Debug</h2>
    <p class="muted">Tools for seeing what the app is doing. These choices are remembered in this browser.</p>
    <fieldset class="opt-group"><legend>Audit log console</legend>
      <label class="chk dbg-chk"><input type="checkbox" data-dbg="console" ${DBG.console === '1' ? raw('checked') : ''}>Show the audit log console</label>
      <p class="hint">A small window at the bottom of the screen with the newest changes to any record, checked every 3 seconds. Scroll it to see older ones; the Audit log page has everything.</p>
      <fieldset class="dbg-lines"><legend>Changes it shows before you scroll</legend><div class="opts">${['3', '4', '5'].map(n => html`<label><input type="radio" name="dbg-lines" data-dbg="lines" value="${n}" ${DBG.lines === n ? raw('checked') : ''}><span>${n}</span></label>`)}</div></fieldset>
      <label class="chk dbg-chk"><input type="checkbox" data-dbg="announce" ${DBG.announce === '1' ? raw('checked') : ''}>Let screen readers announce each new change</label>
      <p id="dbg-msg" class="dbg-msg" role="status" aria-live="polite"></p></fieldset>
    <fieldset class="opt-group"><legend>About this browser and the app</legend><dl class="dl">
      <dt>App version</dt><dd>${META && META.version ? META.version : 'unknown'}</dd>
      ${META && META.runs_as ? html`<dt>Runs as</dt><dd>${META.runs_as.text}</dd>` : ''}
      <dt>Location</dt><dd>${placeName()}${META && META.place && META.place.is_home ? ' (home)' : ''}, time zone ${(META && META.place && META.place.tz) || ''}</dd>
      <dt>Window</dt><dd>${innerWidth} by ${innerHeight} pixels</dd>
      <dt>Text size</dt><dd>${P.size}%</dd>
      <dt>Layout</dt><dd>${r.dataset.narrow === '1' ? 'Narrow: one column, buttons at the bottom' : 'Wide'}${P.layout === 'single' ? ', plant pages in one column' : ''}</dd>
      <dt>Changes logged</dt><dd id="dbg-total">Counting</dd></dl></fieldset>
    <div class="row"><button class="btn" value="ok" autofocus>Done</button></div></form>`);
  api('GET', '/api/audit/facets').then(F => { const d = conEl('dbg-total'); if (d) d.textContent = `${F.total.toLocaleString()} since ${F.first ? midDay(F.first.slice(0, 10)) : 'the start'}`; }).catch(() => {});
}
new MutationObserver(() => conLayout()).observe(document.documentElement, { attributes: true, attributeFilter: ['data-navopen', 'data-narrow', 'data-size', 'data-navside', 'data-space'] });
if (window.ResizeObserver) { const ro = new ResizeObserver(() => conLayout()); ['corner', 'nav-tab'].forEach(id => { const e = conEl(id); if (e) ro.observe(e); }); }
document.addEventListener('visibilitychange', () => { if (!document.hidden) conPoll(); });
document.addEventListener('keydown', e => {      // Enter in the Location window's town box searches, rather than closing the window
  if (e.key === 'Enter' && e.target && e.target.name === 'plcq') { e.preventDefault(); placeSearch(); }
});
{ const b = conEl('con-body'); if (b) b.addEventListener('scroll', conScrolled, { passive: true }); }
if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => { conLayout(); fitPanes(); });   // rows grow a little once the fonts arrive

// ---------- grow lights (1.13.0) ----------
let LT = null;                     // the last answer from /api/lights
const LV_ICON = { too_dim: '▼▼', dim: '▼', good: '✓', bright: '▲', too_bright: '▲▲', unknown: '?' };
function lvTag(v, word) { return html`<span class="lv lv-${v}"><span aria-hidden="true">${LV_ICON[v] || ''}</span> ${word}</span>`; }
function ltSetting(s) {
  return `${s.units > 1 ? s.units + ' side by side, ' : ''}${fmt(s.distance_in, 1)} in from the leaves, ${fmt(s.hours, 1)} hours a day${s.dim_pct < 100 ? `, at ${s.dim_pct}% brightness` : ''}`;
}
function ltLight(id) { return LT && LT.lights.find(L => L.id === +id); }
function ltRooms() {                 // [[room, [places in it]], ...] in the order they were added
  const m = new Map(); (LT ? LT.places : []).forEach(pl => { if (!m.has(pl.room)) m.set(pl.room, []); m.get(pl.room).push(pl); }); return [...m.entries()];
}
function ltRoomsBlock() {
  const rooms = ltRooms();
  if (!rooms.length) return html`<p class="muted">None yet. Add the rooms, shelves and tables where plants will go.</p>`;
  return html`<div class="lt-rooms">${rooms.map(([room, ps]) => html`<section class="lt-room" aria-label="${room}"><h3>${room}</h3><ul>${ps.map(pl => {
    const sp = LT.spots.filter(s => s.place_id === pl.id), n = sp.reduce((a, s) => a + s.plants.length, 0);
    return html`<li><span><strong>${pl.name || 'The room itself'}</strong><br><span class="muted">${sp.length ? `${sp.map(s => s.name).join(', ')}: ${n} plant${n === 1 ? '' : 's'}` : 'No light spot here yet'}</span></span>
      <span class="row noprint"><button class="btn ghost small" type="button" data-act="roomedit" data-id="${pl.id}">Rename</button><button class="btn ghost small" type="button" data-act="roomdel" data-id="${pl.id}">Remove</button></span></li>`; })}</ul></section>`)}</div>`;
}
async function roomDialog(pl) {
  if (!(await needName())) return;
  let x = { room: pl ? pl.room : '', name: pl ? pl.name : '' };
  for (;;) {
    const r = await modal(html`<form method="dialog"><h2>${pl ? 'Rename this room or shelf' : 'Add a room or shelf'}</h2>
      <label class="f">Room<input type="text" name="room" maxlength="60" value="${x.room}" list="lt-roomlist" required autofocus><small>For example "My Bedroom". Pick one already listed to add a shelf to it.</small></label>
      <datalist id="lt-roomlist">${ltRooms().map(([room]) => html`<option value="${room}"></option>`)}</datalist>
      <label class="f">Shelf, table or spot in the room<input type="text" name="name" maxlength="60" value="${x.name}"><small>For example "Top shelf by the window". Leave it empty for the room as a whole.</small></label>
      <div class="row"><button class="btn" value="ok">${pl ? 'Save changes' : 'Add it'}</button><button class="btn ghost" value="cancel" formnovalidate>Cancel</button></div></form>`);
    if (r !== 'ok') return;
    const f = dlg.querySelector('form'); x = { room: f.elements.room.value, name: f.elements.name.value };
    try {
      if (pl) await api('PUT', '/api/lights/places/' + pl.id, x); else await api('POST', '/api/lights/places', x);
      toast(pl ? 'Renamed' : 'Added'); route(); return;
    } catch (e) { toast(e.message, true); }
  }
}
function ltSocketNote(L) {
  return L && L.specs.needs_socket && !L.fixture ? html`<p class="notice"><strong>Needs a socket.</strong> This bulb screws into a lamp or clamp light. Note which one under "Where it is" on the light (Your lights, below).</p>` : '';
}
function ltSteps(steps) {
  if (!steps || !steps.length) return '';
  return html`<details class="lt-steps"><summary>Easing them in from outdoor light</summary>
    <p class="hint">Plants used to the sun drop leaves if the light falls all at once. Start bright and long, then settle on the spot's setting.</p>
    <ol>${steps.map(st => html`<li><strong>${st.when}:</strong> ${st.distance_in != null ? html`${fmt(st.distance_in, 1)} in from the leaves, ${fmt(st.hours, 1)} hours a day${st.dim_pct < 100 ? `, ${st.dim_pct}% brightness` : ''}, about ${st.dli} mol/m² a day. ` : ''}${st.text}</li>`)}</ol></details>`;
}
function ltSpotCard(s, i, plan) {
  const L = ltLight(s.light_id);
  return html`<article class="lt-spot" aria-labelledby="lts-${plan ? 'p' : 's'}${i}"><h3 id="lts-${plan ? 'p' : 's'}${i}">${s.name}</h3>
    ${!plan ? html`<p><strong>Where:</strong> ${s.place || html`<span class="muted">Not chosen yet</span>`}</p>` : ''}
    <p><strong>${s.light}</strong>: ${ltSetting(s)}.</p>
    <p>About <strong>${has(s.dli) ? s.dli : '?'} mol/m² a day</strong> at the leaves${has(s.ppfd) ? html` (${fmt(s.ppfd)} PAR while it is on)` : ''}${s.area_sqft ? html`, lighting about ${fmt(s.area_sqft, 1)} sq ft well` : ''}.
      ${s.crowded ? html`<strong>Crowded:</strong> the pots take about ${fmt(s.room_needed_sqft, 1)} sq ft, so the plants at the edge get less.` : ''}</p>
    ${s.timer_note ? html`<p class="hint">${s.timer_note}</p>` : ''}
    ${ltSocketNote(L)}
    ${s.plants.length ? html`<ul class="lt-plants">${s.plants.map(p => html`<li>${p.photo ? html`<img src="${thumbUrl(p.photo)}" alt="" loading="lazy">` : html`<span></span>`}
      <span><a class="nm" href="#/plant/${enc(p.code)}">${p.name}</a><br><span class="muted">${p.code}. Needs ${has(p.lo) ? `${fmt(p.lo, 1)} to ${fmt(p.hi, 1)}` : '(not set)'} mol/m² a day.</span></span>${lvTag(p.verdict, p.verdict_word)}</li>`)}</ul>` : html`<p class="muted">No plants in this spot yet.</p>`}
    ${ltSteps(s.steps)}
    <div class="row noprint">${plan ? html`<button class="btn" type="button" data-act="spotnew" data-plan="${i}">Set up this spot</button>`
      : html`<button class="btn ghost" type="button" data-act="spotedit" data-id="${s.id}">Change this spot</button><button class="btn ghost" type="button" data-act="spotdel" data-id="${s.id}">Remove this spot</button>`}</div></article>`;
}
function ltLightCard(L) {
  const S = L.specs, bits = [S.watts ? S.watts + ' W' : '', S.lumens ? fmt(S.lumens) + ' lumens' : '', S.kelvin ? S.kelvin + 'K ' + (S.kelvin >= 5000 ? 'cool white' : S.kelvin >= 3500 ? 'neutral white' : 'warm white') : '', S.cri ? 'colour rendering (CRI) ' + S.cri : ''].filter(Boolean);
  const sp = S.spectrum;
  return html`<article class="lt-light" aria-labelledby="ltl-${L.id}">
    ${L.photo ? html`<img class="lt-photo" src="${L.photo}" alt="${S.photo_alt || ''}" loading="lazy">` : ''}
    <div class="lt-body"><h3 id="ltl-${L.id}">${L.name}</h3>
    <p><strong>You have ${L.count}.</strong> ${L.in_use ? `${L.in_use} in use in your spots.` : 'None in a spot yet.'}</p>
    <dl class="dl">
      ${S.kind ? html`<dt>Type</dt><dd>${S.kind}</dd>` : ''}
      <dt>Manufacturer model</dt><dd>${S.model || html`<span class="muted">Not noted yet</span>`}</dd>
      ${bits.length ? html`<dt>Light</dt><dd>${bits.join(', ')}</dd>` : ''}
      ${sp ? html`<dt>Colour mix</dt><dd>Blue ${sp.blue}%, green ${sp.green}%, red ${sp.red}%, far red ${sp.far_red}%</dd>` : ''}
      ${S.power ? html`<dt>Power</dt><dd>${S.power}</dd>` : ''}
      ${S.timer ? html`<dt>Timer</dt><dd>${S.timer}</dd>` : ''}
      <dt>Brightness</dt><dd>${S.dimming && S.dimming.length > 1 ? S.dimming.map(x => x + '%').join(', ') : 'Full only'}</dd>
      ${S.size ? html`<dt>Size</dt><dd>${S.size}</dd>` : ''}
      <dt>Where it is</dt><dd>${L.fixture || html`<span class="muted">Not noted yet</span>`}</dd>
      ${L.notes ? html`<dt>Notes</dt><dd>${L.notes}</dd>` : ''}</dl>
    ${L.points.length ? html`<div class="tbl-wrap"><table class="tbl lt-ppfd"><caption>${S.estimated ? "Claude's estimates" : "Maker's figures"}: light under its centre</caption>
      <thead><tr><th scope="col">Distance</th><th scope="col" class="num">PAR (µmol/m²/s)</th><th scope="col" class="num">12 hours a day gives</th><th scope="col" class="num">Lights about</th></tr></thead>
      <tbody>${L.points.map(p => html`<tr><th scope="row">${fmt(p.distance_in, 1)} in</th><td class="num">${fmt(p.ppfd, 1)}</td><td class="num">${fmt(p.ppfd * 12 * 0.0036, 1)} mol/m²</td><td class="num">${p.area_sqft ? fmt(p.area_sqft, 1) + ' sq ft' + (S.area_estimated && !S.estimated ? ' (estimate)' : '') : ''}</td></tr>`)}</tbody></table></div>` : ''}
    ${S.ppfd_note ? html`<p class="hint">${S.ppfd_note}</p>` : ''}
    ${L.chart ? html`<p class="hint"><a href="${L.chart}" target="_blank" rel="noopener">Open the maker's chart</a> (picture). ${S.chart_alt || ''}</p>` : ''}
    ${S.url ? html`<p class="hint"><a href="${S.url}" target="_blank" rel="noopener noreferrer">Product page</a></p>` : ''}
    <div class="row noprint"><button class="btn ghost small" type="button" data-act="lightedit" data-id="${L.id}">Change this light</button></div></div></article>`;
}
async function viewLights() {
  LT = await api('GET', '/api/lights');
  const n = LT.candidates.length, inSpots = Object.keys(LT.assigned).length, sug = LT.plan.reduce((a, s) => a + s.codes.length, 0);
  return {
    title: 'Grow lights',
    html: html`<h1>Grow lights</h1>
    <p class="muted">Your grow lights, the spots they light, and how much light each plant gets there. A plant's daily light (DLI, in mol/m² a day) is the light at its leaves while the light is on (PAR) times the hours it is on. Each plant page has the range it wants.</p>
    <div class="verdict-box" role="status"><h2 style="margin:0 0 .4rem">This winter</h2>
      <p>${n} plant${n === 1 ? ' lives' : 's live'} inside or ${n === 1 ? 'is' : 'are'} coming in. ${inSpots} ${inSpots === 1 ? 'is' : 'are'} in a light spot you set up.${LT.plan.length ? ` The suggested layout below places ${sug} more under your lights.` : ''}${LT.unplaced.length ? ` ${LT.unplaced.length} ${LT.unplaced.length === 1 ? 'has' : 'have'} no light left in it.` : ''}</p>
      ${has(LT.outdoor_dli) ? html`<p>Outdoors in the open, the last 7 days averaged about <strong>${LT.outdoor_dli} mol/m² a day</strong>. Under the porch roof it is much less.</p>` : ''}
      <div class="row noprint"><button class="btn" type="button" data-act="spotnew">Set up a spot</button><button class="btn ghost" type="button" data-act="lightnew">Add a light</button></div></div>
    <section class="blk" id="lt-spots"><h2>Your light spots</h2>
      ${LT.spots.length ? html`<div class="lt-grid">${LT.spots.map((s, i) => ltSpotCard(s, i, false))}</div>` : html`<p class="muted">None yet. Set one up from the suggested layout below with one press, or with "Set up a spot".</p>`}</section>
    <section class="blk" id="lt-rooms"><h2>Rooms and shelves</h2><p>Where your plants go inside. Choose one for each light spot.</p>${ltRoomsBlock()}
      <div class="row noprint"><button class="btn ghost" type="button" data-act="roomnew">Add a room or shelf</button></div></section>
    <section class="blk" id="lt-plan"><h2>Suggested layout</h2>
      <p>For the plants that are not in a spot yet. Plants that need the most light are placed first. Each goes under the smallest of your lights that can give it enough, sharing a light with plants whose needs overlap, while there is room under it. "Set up this spot" opens it so you can rename it or change anything before saving.</p>
      ${LT.plan.length ? html`<div class="lt-grid">${LT.plan.map((s, i) => ltSpotCard(s, i, true))}</div>` : html`<p class="muted">Every plant that needs a light is in a spot.</p>`}
      ${LT.unplaced.length ? html`<h3>No light left for these</h3><ul class="lt-plants">${LT.unplaced.map(u => html`<li>${u.photo ? html`<img src="${thumbUrl(u.photo)}" alt="" loading="lazy">` : html`<span></span>`}
        <span><a class="nm" href="#/plant/${enc(u.code)}">${u.name}</a><br><span class="muted">${u.code}. Needs ${fmt(u.lo, 1)} to ${fmt(u.hi, 1)} mol/m² a day.</span> ${u.why}</span><span></span></li>`)}</ul>` : ''}</section>
    <section class="blk" id="lt-lights"><h2>Your lights</h2><div class="lt-lights">${LT.lights.map(ltLightCard)}</div></section>
    <section class="blk"><h2>How the numbers work</h2>
      <p>Makers measure light straight under the centre of the light at a few distances. The app draws a smooth line through those figures to get the light at any distance, then multiplies by the hours a day: 100 PAR for 12 hours is about 4.3 mol/m².</p>
      <p>The edges of a light's circle get less, and a window adds some. Plants that stretch or go pale want more; bleached or crisp leaves want less. Several of the same light side by side light a bigger area at about the same strength.</p></section>`,
  };
}
// set up or change a spot
let SP = null;
function spotDims(L, cur) { const d = (L && L.specs.dimming && L.specs.dimming.length ? L.specs.dimming : [100]).slice().sort((a, b) => b - a); return d.map(x => html`<option value="${x}" ${x === +cur ? raw('selected') : ''}>${x === 100 ? 'Full (100%)' : x + '%'}</option>`); }
async function spotDialog(x) {
  if (!(await needName())) return;
  const editing = x && x.id, lights = LT.lights;
  for (;;) {
    const L = ltLight(x.light_id) || lights[0], inSpot = new Set(x.codes || []);
    const others = Object.fromEntries(LT.spots.map(s => [s.id, s.name]));
    const shown = modal(html`<form method="dialog" data-spot class="spot-form"><h2>${editing ? 'Change this spot' : 'Set up a light spot'}</h2>
      <label class="f">Name<input type="text" name="name" maxlength="60" value="${x.name || ''}" required autofocus><small>A short name you will recognise, for example "Hutch, top shelf".</small></label>
      <label class="f">Where<select name="place"><option value="">Not chosen yet</option>${ltRooms().map(([room, ps]) => html`<optgroup label="${room}">${ps.map(pl => html`<option value="${pl.id}" ${pl.id === x.place_id ? raw('selected') : ''}>${pl.label}</option>`)}</optgroup>`)}</select>
        <small>Add rooms and shelves under "Rooms and shelves" on this page.</small></label>
      <label class="f">Light<select name="light">${lights.map(l => html`<option value="${l.id}" ${l.id === L.id ? raw('selected') : ''}>${l.name} (you have ${l.count}${l.in_use ? `, ${l.in_use} in use` : ''})</option>`)}</select></label>
      <div class="field-grid three"><label class="f">How many of this light<input type="number" name="units" min="1" max="50" step="1" value="${x.units || 1}" required><small>Side by side over these plants.</small></label>
        <label class="f">Distance from the leaves (inches)<input type="number" name="distance" min="1" max="120" step="0.5" value="${x.distance_in || 12}" required><small>From the light to the top leaves${L && L.specs.direction === 'side' ? ' (this light shines sideways)' : ''}.</small></label>
        <label class="f">Hours a day<input type="number" name="hours" min="1" max="24" step="0.5" value="${x.hours || 12}" required></label></div>
      <label class="f">Brightness<select name="dim">${spotDims(L, x.dim_pct || 100)}</select></label>
      <div id="sp-prev" class="sp-prev" aria-live="polite"></div>
      <fieldset class="opt-group"><legend>Plants in this spot</legend><p class="hint">Plants that live inside or are coming in. Ticking a plant that is in another spot moves it here.</p>
        <div class="sp-plants">${LT.candidates.map(c => { const sid = LT.assigned[c.code], there = sid && sid !== x.id ? others[sid] : null;
          return html`<label class="chk"><input type="checkbox" name="plant" value="${c.code}" ${inSpot.has(c.code) ? raw('checked') : ''}><span>${c.name} <span class="muted">${c.code}${c.need ? `, needs ${fmt(c.need.lo, 1)} to ${fmt(c.need.hi, 1)}` : ''}${there ? `, now in ${there}` : ''}</span></span></label>`; })}</div></fieldset>
      <label class="f">Note<input type="text" name="notes" maxlength="300" value="${x.notes || ''}"></label>
      <div class="row"><button class="btn" value="ok">${editing ? 'Save changes' : 'Save spot'}</button><button class="btn ghost" value="cancel" formnovalidate>Cancel</button></div></form>`, 'wide');
    SP = { light: String(L.id) };
    spotPreview(true);
    if ((await shown) !== 'ok') return;
    const f = dlg.querySelector('form'), v = k => f.elements[k].value;
    const body = { name: v('name'), place: v('place'), light: v('light'), units: v('units'), distance: v('distance'), hours: v('hours'), dim: v('dim'), notes: v('notes'),
      plants: [...f.querySelectorAll('input[name=plant]:checked')].map(i => i.value) };
    try {
      if (editing) await api('PUT', '/api/lights/spots/' + x.id, body); else await api('POST', '/api/lights/spots', body);
      toast(editing ? 'Spot changed' : `Spot "${body.name.trim()}" set up`);
      route(); return;
    } catch (e) { toast(e.message, true); x = { ...x, name: body.name, place_id: body.place ? +body.place : null, light_id: +body.light, units: +body.units, distance_in: +body.distance, hours: +body.hours, dim_pct: +body.dim, notes: body.notes, codes: body.plants }; }
  }
}
function spotPreview(now) {
  clearTimeout(SP && SP.t);
  const go = async () => {
    const f = dlg.querySelector('form[data-spot]'), out = document.getElementById('sp-prev'); if (!f || !out) return;
    if (f.elements.light.value !== SP.light) {           // a different light: its own brightness steps
      SP.light = f.elements.light.value; const L = ltLight(SP.light);
      f.elements.dim.innerHTML = rend(html`${spotDims(L, 100)}`);
    }
    const q = new URLSearchParams({ light: f.elements.light.value, units: f.elements.units.value, distance: f.elements.distance.value, hours: f.elements.hours.value, dim: f.elements.dim.value,
      plants: [...f.querySelectorAll('input[name=plant]:checked')].map(i => i.value).join(',') });
    try {
      const e = await api('GET', '/api/lights/preview?' + q.toString());
      out.innerHTML = rend(html`<p><strong>About ${has(e.dli) ? e.dli : '?'} mol/m² a day</strong> at the leaves${has(e.ppfd) ? `, ${fmt(e.ppfd)} PAR while it is on` : ''}${e.area_sqft ? `, lighting about ${fmt(e.area_sqft, 1)} sq ft` : ''}.${e.crowded ? ` Crowded: the pots take about ${fmt(e.room_needed_sqft, 1)} sq ft.` : ''}</p>
        ${e.timer_note ? html`<p class="hint">${e.timer_note}</p>` : ''}
        ${e.plants.length ? html`<ul class="sp-verdicts">${e.plants.map(p => html`<li>${lvTag(p.verdict, p.verdict_word)} ${p.name} <span class="muted">(needs ${has(p.lo) ? `${fmt(p.lo, 1)} to ${fmt(p.hi, 1)}` : 'not set'})</span></li>`)}</ul>` : ''}`);
    } catch (err) { out.innerHTML = rend(html`<p class="muted">${err.message}</p>`); }
  };
  if (now) go(); else SP.t = setTimeout(go, 250);
}
async function lightDialog(L) {
  if (!(await needName())) return;
  const S = (L && L.specs) || {}, pts = L ? L.points.map(p => `${fmt(p.distance_in, 2)} in ${fmt(p.ppfd, 2)}${p.area_sqft ? ` (${fmt(p.area_sqft, 2)} sq ft)` : ''}`).join(', ') : '';
  let x = { name: L ? L.name : '', model: S.model || '', count: L ? L.count : 1, fixture: L ? L.fixture : '', notes: L ? L.notes : '', watts: S.watts == null ? '' : S.watts, points: pts,
    timer: S.timer || '', dimming: (S.dimming || [100]).join(', '), kind: S.kind || '' };
  for (;;) {
    const r = await modal(html`<form method="dialog"><h2>${L ? 'Change this light' : 'Add a light you have'}</h2>
      <label class="f">Name<input type="text" name="name" maxlength="80" value="${x.name}" required autofocus></label>
      <label class="f">Manufacturer model<input type="text" name="model" maxlength="80" value="${x.model}"><small>The model number on the box or a label on the light.</small></label>
      <div class="field-grid three"><label class="f">How many you have<input type="number" name="count" min="0" max="100" step="1" value="${x.count}" required></label>
        <label class="f">Watts (each)<input type="number" name="watts" min="0" max="2000" step="any" value="${x.watts}"></label>
        <label class="f">Type<input type="text" name="kind" maxlength="40" value="${x.kind}"><small>For example bulb, strip or clamp light.</small></label></div>
      <label class="f">Where it is<input type="text" name="fixture" maxlength="120" value="${x.fixture}"><small>The room, shelf or lamp it is in, or the socket a bulb screws into.</small></label>
      <label class="f">Light at distances (PPFD)<textarea name="points" rows="2" maxlength="400">${x.points}</textarea><small>From the box or listing: distance in inches and PAR, separated by commas, for example "12 in 719, 24 in 234". Add the area it lights in brackets if the maker gives it.</small></label>
      <div class="field-grid"><label class="f">Timer<input type="text" name="timer" maxlength="120" value="${x.timer}"></label>
        <label class="f">Brightness steps (%)<input type="text" name="dimming" maxlength="40" value="${x.dimming}"><small>For example "25, 50, 75, 100", or "100" if it only has full.</small></label></div>
      <label class="f">Notes<input type="text" name="notes" maxlength="600" value="${x.notes}"></label>
      <div class="row"><button class="btn" value="ok">${L ? 'Save changes' : 'Save light'}</button>${L ? html`<button class="btn ghost" value="remove" formnovalidate>Remove this light</button>` : ''}<button class="btn ghost" value="cancel" formnovalidate>Cancel</button></div></form>`);
    if (r === 'remove') {
      if (!(await confirmBox('Remove this light?', `${L.name} leaves your list. Spots that use it must be changed or removed first.`, 'Remove light', true))) return;
      try { await api('DELETE', '/api/lights/' + L.id); toast('Light removed'); route(); } catch (e) { toast(e.message, true); }
      return;
    }
    if (r !== 'ok') return;
    const f = dlg.querySelector('form'); x = Object.fromEntries(['name', 'model', 'count', 'watts', 'kind', 'fixture', 'points', 'timer', 'dimming', 'notes'].map(k => [k, f.elements[k].value]));
    try {
      if (L) await api('PUT', '/api/lights/' + L.id, x); else await api('POST', '/api/lights', x);
      toast(L ? 'Light changed' : `${x.name.trim()} added`); route(); return;
    } catch (e) { toast(e.message, true); }
  }
}
// a plant's own page: its spot, or what the layout suggests
async function loadGrowPlant(code) {
  const el = document.getElementById('pl-grow'); if (!el) return;
  try {
    const g = await api('GET', '/api/lights?plant=' + enc(code));
    if (!g.lights || (!g.spot && !g.suggestion && !g.unplaced)) { el.innerHTML = ''; return; }
    const me = s => s.plants.find(p => p.code === code) || {};
    el.innerHTML = rend(html`<h3>Grow light this winter</h3>${g.spot ? html`<p>In the spot <strong>${g.spot.name}</strong>${g.spot.place ? ` (${g.spot.place})` : ''}${g.spot.name.includes(g.spot.light) ? '' : `, under the ${g.spot.light}`}: ${ltSetting(g.spot)}. About ${g.spot.dli} mol/m² a day. ${lvTag(me(g.spot).verdict, me(g.spot).verdict_word)}</p>`
      : g.suggestion ? html`<p>Not in a light spot yet. The suggested layout puts it under the <strong>${g.suggestion.light}</strong>, ${ltSetting(g.suggestion)}: about ${g.suggestion.dli} mol/m² a day. ${lvTag(me(g.suggestion).verdict, me(g.suggestion).verdict_word)}</p>`
      : html`<p>Not in a light spot yet. ${g.unplaced.why}</p>`}<p class="noprint"><a href="#/lights">Open Grow lights</a></p>`);
  } catch (e) { el.innerHTML = ''; }
}

// ---------- events ----------
async function copyRequest() {
  const text = requestText(CUR.p);
  try { await navigator.clipboard.writeText(text); toast('Copied. Paste it into your next message to Claude.'); return; } catch (e) { /* fall through */ }
  await modal(html`<form method="dialog"><h2>Copy this request</h2><p>Your browser blocked automatic copying. Select the text and press Ctrl+C (Cmd+C on a Mac).</p>
    <textarea readonly rows="9" autofocus>${text}</textarea><div class="row" style="margin-top:12px"><button class="btn" value="ok">Done</button></div></form>`);
}
async function pickPlant(title, text, withNone) {
  const list = await api('GET', '/api/plants');
  const r = await modal(html`<form method="dialog"><h2>${title}</h2><p>${text}</p>
    <label class="f">Plant<select name="t" autofocus>${withNone ? html`<option value="">Unassigned</option>` : ''}${list.map(p => html`<option value="${p.code}">${p.code}  ${p.common_name}</option>`)}</select></label>
    <div class="row"><button class="btn" value="ok">Move photo</button><button class="btn ghost" value="cancel">Cancel</button></div></form>`);
  return r === 'ok' ? dlg.querySelector('[name=t]').value : null;
}
const acts = {
  gphoto: el => sheetStep(el.dataset.code, +el.dataset.d),
  who() { whoDialog(); },
  spotnew(el) { const p = el.dataset.plan != null ? LT.plan[+el.dataset.plan] : null; spotDialog(p ? { name: p.name, light_id: p.light_id, units: p.units, distance_in: p.distance_in, hours: p.hours, dim_pct: p.dim_pct, codes: p.codes } : { light_id: LT.lights[0] && LT.lights[0].id }); },
  spotedit(el) { const s = LT.spots.find(x => x.id === +el.dataset.id); if (s) spotDialog({ ...s, codes: s.plants.map(p => p.code) }); },
  async spotdel(el) {
    const s = LT.spots.find(x => x.id === +el.dataset.id); if (!s) return;
    if (!(await confirmBox('Remove this spot?', `"${s.name}" is removed and its ${s.plants.length} plant${s.plants.length === 1 ? '' : 's'} go back to the suggested layout. The light itself stays in your list.`, 'Remove spot', true))) return;
    await guard(async () => { await api('DELETE', '/api/lights/spots/' + s.id); toast('Spot removed'); route(); });
  },
  lightedit(el) { lightDialog(ltLight(el.dataset.id)); },
  lightnew() { lightDialog(null); },
  roomnew() { roomDialog(null); },
  roomedit(el) { roomDialog(LT.places.find(p => p.id === +el.dataset.id)); },
  async roomdel(el) {
    const pl = LT.places.find(p => p.id === +el.dataset.id); if (!pl) return;
    if (!(await confirmBox('Remove this room or shelf?', `"${pl.label}" leaves the list.${pl.spots.length ? ` The ${pl.spots.length} light spot${pl.spots.length === 1 ? '' : 's'} there stay, with "Where" set to "Not chosen yet".` : ''}`, 'Remove it', true))) return;
    await guard(async () => { await api('DELETE', '/api/lights/places/' + pl.id); toast('Removed'); route(); });
  },
  async usethisbase() { await guard(async () => { await api('PUT', '/api/settings', { base_url: location.origin }); toast('Codes now open ' + location.origin); route(); }); },
  async whosave() {
    const f = dlg.querySelector('form'), m = document.getElementById('who-msg'), n = cleanName(f.elements.n.value);
    if (!n) { m.textContent = 'Type a name first.'; return; }
    if (viaTS()) {
      try { const r = await api('PUT', '/api/me', { name: n }); META.me = r; paintWho(); m.textContent = `Saved. Your changes now show as ${r.name}.`; }
      catch (e) { m.textContent = e.message; }
    } else { setName(n); m.textContent = `Saved. Your changes now show as ${n}.`; }
  },
  async pdel(el) {
    const m = document.getElementById('who-msg');
    try { const r = await api('DELETE', '/api/people?login=' + enc(el.dataset.login)); peoplePaint(r); m.textContent = `${el.dataset.name} removed. If they open the app again, they come back as "Can view only".`; }
    catch (e) { m.textContent = e.message; }
  },
  fertlog(el) {
    const o = {};
    if (el.dataset.code) o.codes = [el.dataset.code];
    if (el.dataset.date) o.date = el.dataset.date;
    if (el.dataset.group === 'due') { const t = todayStr(); o.codes = FERT.plants.filter(p => fertState(p, entriesFor(p.code), t, fertCtx()).state === 'due').map(p => p.code); }
    return fertDialog(o);
  },
  fzadd() { return productDialog(null); },
  fzedit(el) { const x = FERT.products[+el.dataset.i]; if (x) return productDialog(x); },
  async fzdel(el) {
    const x = FERT.products[+el.dataset.i]; if (!x || !x.saved || !(await needName())) return;
    if (!(await confirmBox('Remove this fertilizer?', `${x.product} comes off your list. Feedings you logged with it stay in the log${x.uses ? ', so it stays in the list as a logged fertilizer' : ''}.`, 'Remove', true))) return;
    await guard(async () => { await api('DELETE', '/api/fertilizer/products/' + x.id); toast(x.product + ' removed'); await fertRefresh(); });
  },
  fertedit(el) { const e = FERT.entries.find(x => x.id === +el.dataset.id); if (e) return fertDialog({ entry: e }); },
  async fertdel(el) {
    const e = FERT.entries.find(x => x.id === +el.dataset.id); if (!e || !(await needName())) return;
    if (!(await confirmBox('Remove this feeding?', `${e.product} on ${longDay(e.applied_on)}. The change log keeps a record that it was removed.`, 'Remove', true))) return;
    await guard(async () => { await api('DELETE', '/api/fertilizer/' + e.id); toast('Feeding removed'); await fertRefresh(); });
  },
  fertpick(el) {
    const t = readFert().applied_on || todayStr(), how = el.dataset.how;
    dlg.querySelectorAll('[name=pl]').forEach(b => {
      const p = FERT.plants.find(x => x.code === b.value);
      b.checked = how === 'none' ? false : how === 'season' ? !!(p && hasSeason(p) && monthIn(p, +t.slice(5, 7))) : !!(p && fertState(p, entriesFor(p.code), t, fertCtx()).state === 'due');
    });
    fertPreview();
  },
  calnav(el) { calNav(el.dataset.cal, +el.dataset.d); },
  calpick(el) { calGo(el.dataset.cal, el.dataset.date, false); },
  calview(el) {
    const id = el.dataset.cal, cur = (CALS[id] && CALS[id].view) || calView(), nv = cur === 'grid' ? 'list' : 'grid';
    try { localStorage.setItem('plantdb.calview', nv); } catch (e) { /* ignore */ }
    Object.values(CALS).forEach(c => { c.view = nv; calRender(c.id); });
  },
  histmetric(el) { const S = HS[el.dataset.kind]; S.metric = el.dataset.m; S.day = S.day; histOpen(el.dataset.kind); },
  display() { displayDialog(); },
  prefreset() { window.PlantPrefs.reset(); displayDialog(); },
  async reqdone(el) { if (!(await needName())) return; await guard(async () => { await api('PUT', '/api/requests/' + el.dataset.id, { done: true }); toast('Marked done'); reloadPlant(); }); },
  async reqreopen(el) { if (!(await needName())) return; await guard(async () => { await api('PUT', '/api/requests/' + el.dataset.id, { done: false }); toast('Reopened'); reloadPlant(); }); },
  async reqanswer(el) {
    if (!(await needName())) return;
    const r = (CUR.p.requests || []).find(x => String(x.id) === el.dataset.id); if (!r) return;
    const res = await modal(html`<form method="dialog"><h2>Answer</h2><p>${r.text}</p>
      <label class="f">Your answer<textarea name="answer" rows="5" maxlength="2000" required></textarea></label>
      <div class="row"><button class="btn" value="ok">Save answer and mark done</button><button class="btn ghost" value="cancel" formnovalidate>Cancel</button></div></form>`);
    if (res !== 'ok') return;
    const a = dlg.querySelector('[name=answer]').value.trim(); if (!a) return;
    await guard(async () => { await api('PUT', '/api/requests/' + r.id, { done: true, answer: a }); toast('Answer saved. Use Copy my answers for Claude to send it.'); reloadPlant(); });
  },
  forclaude() { forClaudeDialog(); },
  debug() { debugDialog(); },
  place() { placeDialog(); },
  plcsearch() { placeSearch(); },
  plcadd(el) { placeAdd(+el.dataset.i); },
  plcweather() { if (dlg.open) dlg.close(); },
  async plchome() {
    const cur = META && META.place; if (!cur || cur.is_home || !(await needName())) return;
    const m = document.getElementById('plc-msg');
    try {
      await api('PUT', '/api/places/' + cur.id, { is_home: true });
      savePlace(null); META = null; COND = null; FROST = null; FROST_AT = 0;
      await route();
      if (m) m.textContent = `${cur.name} is now the home place for everyone.`;
      const h = document.getElementById('plc-home'); if (h) h.innerHTML = rend(plcHomeRow());
    } catch (e) { if (m) m.textContent = e.message; }
  },
  conclose() { DBG.console = '0'; dbgSave(); conApply(); toast('Audit log console off. Turn it back on with the Debug button.'); const d = document.getElementById('debug-btn'); if (d) d.focus(); },
  conpause(el) { CON.paused = !CON.paused; el.setAttribute('aria-pressed', String(CON.paused)); el.textContent = CON.paused ? 'Resume' : 'Pause'; conState(CON.paused ? 'Paused' : 'Live'); if (!CON.paused) conPoll(); },
  connew() { const b = document.getElementById('con-body'); if (b) { b.scrollTop = b.scrollHeight; b.focus(); } CON.unseen = 0; CON.stick = true; const n = document.getElementById('con-new'); if (n) n.hidden = true; },
  audclear() { Object.assign(AUD.f, { q: '', plant: '', who: '', kind: '', field: '', from: '', to: '', order: 'desc' }); AUD.offset = 0; audSave(); route(); },
  audrefresh() { audLoad('[data-act=audrefresh]'); },
  audpage(el) { AUD.offset = Math.max(0, AUD.offset + Number(el.dataset.d) * AUD.limit); audLoad(); const s = document.getElementById('aud-sum'); if (s) { s.scrollIntoView({ block: 'start' }); s.setAttribute('tabindex', '-1'); s.focus({ preventScroll: true }); } },
  async prepdone(el) {
    if (!(await needName())) return;
    const k = el.dataset.k, code = el.dataset.code;
    await guard(async () => { await api('POST', '/api/care', { plant: code, kind: 'prep_' + k }); toast('Saved: ' + PREP_CARE['prep_' + k]); await prepAfterChange(code, `[data-act=prepdone][data-k="${k}"][data-code="${code}"]`); });
  },
  async prepundo(el) {
    const k = el.dataset.k, code = el.dataset.code, D = PREP.data;
    const last = D && D.code === code ? (D.log || []).filter(x => x.kind === 'prep_' + k).pop() : null; if (!last) return;
    if (!(await needName())) return;
    await guard(async () => { await api('DELETE', '/api/care/' + last.id); toast('Removed: ' + PREP_CARE['prep_' + k] + ', ' + relDay(last.done_on)); await prepAfterChange(code, `[data-act=prepdone][data-k="${k}"][data-code="${code}"]`); });
  },
  openprep(el) { try { sessionStorage.setItem('plantdb.toprep', el.dataset.code); } catch (e) { /* the page still opens */ } go('#/plant/' + enc(el.dataset.code)); },
  async fccopy() {
    const t = document.getElementById('fc-text'); if (!t) return;
    let ok = false;
    try { await navigator.clipboard.writeText(t.value); ok = true; }
    catch (e) { t.focus(); t.select(); try { ok = document.execCommand('copy'); } catch (e2) { ok = false; } }
    if (!ok) { t.focus(); t.select(); fcSay('This browser would not copy it. The message is selected: press Ctrl+C to copy it.'); return; }
    await fcMark(); fcSay('Copied. Now paste it into your chat with Claude (Ctrl+V).');
  },
  async fcsave() {
    const a = document.createElement('a');
    a.href = `/api/for-claude.txt?range=${FC.range}&open=${FC.open ? 1 : 0}`; a.download = ''; document.body.appendChild(a); a.click(); a.remove();
    await fcMark(); fcSay('Saved to your Downloads folder. Attach it in your chat with Claude, or open it and copy the text.');
  },
  async todoedit(el) {
    const t = TODO.find(x => String(x.id) === el.dataset.id); if (!t || !(await needName())) return;
    const r = await modal(html`<form method="dialog"><h2>Edit entry</h2>
      <label class="f">What to photograph<input type="text" name="label" maxlength="200" required value="${t.label}"></label>
      <label class="f">Note<textarea name="note" rows="4" maxlength="1000">${t.note || ''}</textarea></label>
      <p class="hint">Type plant codes such as P-012 to link them.</p>
      <div class="row"><button class="btn" value="ok">Save</button><button class="btn ghost" value="cancel" formnovalidate>Cancel</button></div></form>`);
    if (r !== 'ok') return;
    const label = dlg.querySelector('[name=label]').value.trim(), note = dlg.querySelector('[name=note]').value.trim();
    if (!label) return;
    await guard(async () => { await api('PATCH', '/api/to-photograph/' + t.id, { label, note }); toast('Saved'); route(); });
  },
  async bkdel(el) {
    if (!(await needName())) return;
    if (!(await confirmBox('Delete this backup?', el.dataset.file + ' will be removed from the backups folder. This cannot be undone.', 'Delete backup', true))) return;
    await guard(async () => { await api('DELETE', '/api/backups/' + enc(el.dataset.file)); toast('Backup deleted'); route(); });
  },
  needs() { G.needs = !G.needs; gSave(); route(); },
  layout() { const P = window.PlantPrefs.get(); window.PlantPrefs.set('layout', P.layout === 'single' ? 'split' : 'single'); route(); },
  navgo(el, e) {
    if (e) e.preventDefault();
    const it = NAVITEMS[+el.dataset.i]; if (!it) return;
    if (it.top) { window.scrollTo({ top: 0, behavior: 'smooth' }); const p = document.querySelector('.pane'); if (p) document.querySelectorAll('.pane').forEach(x => x.scrollTo({ top: 0 })); }
    else scrollToSection(it.el);
    if (document.documentElement.dataset.narrow === '1') { NAVSESSION = false; navLayout(); }
  },
  navtoggle() {
    const open = !navOpen();
    if (document.documentElement.dataset.narrow === '1') NAVSESSION = open; else { NAVSESSION = null; window.PlantPrefs.set('navopen', open ? '1' : '0'); }
    navLayout(); fitPanes(); paintAllCharts();
    const f = open ? document.querySelector('#sn-list a') : document.getElementById('nav-tab'); if (f) f.focus();
  },
  navside() { window.PlantPrefs.set('navside', window.PlantPrefs.get().navside === 'left' ? 'right' : 'left'); navLayout(); fitPanes(); paintAllCharts(); },
  jump(el) {
    const t = document.getElementById(el.dataset.id); if (!t) return;
    scrollToSection(t);
    if (!t.hasAttribute('tabindex')) t.setAttribute('tabindex', '-1');
    t.focus({ preventScroll: true });
  },
  setcond() { condDialog(); },
  async copytok() {
    const t = document.getElementById('tok').textContent;
    try { await navigator.clipboard.writeText(t); toast('Token copied'); }
    catch (e) { const r = document.createRange(); r.selectNodeContents(document.getElementById('tok')); const s = getSelection(); s.removeAllRanges(); s.addRange(r); toast('Press Ctrl+C to copy the selected token'); }
  },
  async tokregen() {
    if (!(await needName())) return;
    if (!(await confirmBox('Make a new sensor token?', 'The old token stops working right away. Any sensor using it will need the new one.', 'Make new token', true))) return;
    await guard(async () => { await api('POST', '/api/ingest/regenerate'); toast('New token made'); route(); });
  },
  async wxrefresh(el) {
    el.disabled = true;
    try { const r = await api('POST', '/api/weather/refresh', { loc: el.dataset.all ? 'all' : WX.place.id }); toast(r.started ? 'Updating in the background' : 'An update is already running'); document.body.dataset.job = '1'; }
    catch (e) { toast(e.message, true); }
    route();
  },
  printlabel() {
    const src = document.querySelector('#label .lblwrap'); if (!src) return;
    const box = document.createElement('div'); box.id = 'print-label'; box.innerHTML = src.querySelector('.lbl').outerHTML;
    document.body.appendChild(box); document.body.classList.add('print-label');
    const done = () => { box.remove(); document.body.classList.remove('print-label'); window.removeEventListener('afterprint', done); };
    window.addEventListener('afterprint', done); setTimeout(() => window.print(), 50);
  },
  wxmatch() {
    if (!WT.shown) { toast('The table has not loaded yet.', true); return; }
    if (WT.kind === 'sensor') { WX.src = 'sensor'; }
    WX.period = WT.from || WT.to ? 'custom' : 'all'; WX.from = WT.from || '1940-01-01'; WX.to = WT.to || ymd(new Date());
    const core = { temperature_2m: 'temp', relative_humidity_2m: 'hum', par: 'light', temp_f: 'temp', humidity: 'hum' };
    WX.show = [...new Set(WT.shown.map(k => core[k]).filter(Boolean))];
    WX.vars = WT.shown.filter(k => !core[k] && catOf(k) && !DAILY_SKIP.includes(k));
    if (WT.kindShown === 'daily' && WT.shown.some(k => /^temperature_2m_/.test(k))) WX.show = [...new Set([...WX.show, 'temp'])];
    wxSave(); Promise.resolve(route()).then(() => { const c = document.getElementById('wx-charts'); if (c) c.closest('section').scrollIntoView(); });
  },
  wxgroup(el) {
    const keys = el.dataset.keys.split(','), on = el.dataset.on === '1';
    WX.vars = on ? [...new Set([...WX.vars, ...keys])] : WX.vars.filter(k => !keys.includes(k));
    keys.forEach(k => { const b = document.querySelector(`[data-f=wxvar][data-key="${k}"]`); if (b) b.checked = on; });
    const n = document.getElementById('wx-pickcount'); if (n) n.textContent = WX.show.length + WX.vars.length;
    wxSave(); clearTimeout(WX.t); WX.t = setTimeout(loadWxCharts, 600);
  },
  wxallvars(el) {
    const daily = el.dataset.which === 'daily';
    const keys = (WXCAT || []).filter(c => daily ? (c.kind === 'daily' && !DAILY_SKIP.includes(c.key) && !(WXCAT || []).some(x => x.kind === 'hourly' && x.key === c.key)) : (c.kind === 'hourly' && !['temperature_2m', 'relative_humidity_2m'].includes(c.key))).map(c => c.key);
    WX.vars = [...new Set([...WX.vars, ...keys])];
    const d = document.getElementById('wx-pick'); if (d) d.innerHTML = rend(wxPickInner());
    const n = document.getElementById('wx-pickcount'); if (n) n.textContent = WX.show.length + WX.vars.length;
    wxSave(); loadWxCharts();
  },
  wxbar() {
    WXBAR = !wxBarOpen();
    const body = document.getElementById('wx-barbody'), b = document.getElementById('wx-barbtn');
    body.hidden = !WXBAR; b.setAttribute('aria-expanded', WXBAR ? 'true' : 'false'); b.textContent = WXBAR ? 'Hide chart settings' : 'Show chart settings';
    navLayout();
  },
  gotoplaces(el, e) { const t = document.getElementById('sec-places'); if (t) scrollToSection(t); },
  placeshow(el) { setPlace(el.dataset.id).then(() => window.scrollTo(0, 0)); },
  async placehome(el) {
    const p = WX.places.find(x => String(x.id) === el.dataset.id); if (!p || !(await needName())) return;
    if (!(await confirmBox(`Make ${p.name} home?`, `Every computer or phone that has not chosen its own location will use the weather for ${p.name} instead of ${WX.home.name}, and so will the hourly updates and backups.`, 'Make home'))) return;
    await guard(async () => { await api('PUT', '/api/places/' + p.id, { is_home: true }); if (String(PLACE) === String(p.id)) savePlace(null); META = null; COND = null; FROST = null; FROST_AT = 0; toast(`${p.name} is now home`); route(); });
  },
  async placeonoff(el) {
    if (!(await needName())) return;
    await guard(async () => { await api('PUT', '/api/places/' + el.dataset.id, { enabled: el.dataset.on === '1' }); toast(el.dataset.on === '1' ? 'Hourly updates on' : 'Hourly updates stopped; its stored weather is kept'); route(); });
  },
  async placedel(el) {
    const p = WX.places.find(x => String(x.id) === el.dataset.id); if (!p || !(await needName())) return;
    if (!(await confirmBox(`Remove ${p.name}?`, `This deletes its ${num(p.count || 0)} hourly readings, its daily summaries and its update log. To keep them, use "Stop hourly updates" instead. This cannot be undone.`, 'Remove it and its weather', true))) return;
    await guard(async () => { const r = await api('DELETE', '/api/places/' + p.id); toast(`${p.name} removed (${num(r.removed_readings)} readings)`); await setPlace(String(PLACE) === String(p.id) ? null : PLACE); });
  },
  async placepick(el) {
    const r = (PLACE_RESULTS || [])[+el.dataset.i]; if (!r) return;
    await addPlace({ name: r.name, lat: r.lat, lon: r.lon, tz: r.tz });
  },
  wxpanel() {
    const p = document.getElementById('wx-panel'), b = document.getElementById('wx-panelbtn'); if (!p) return;
    p.hidden = !p.hidden; b.setAttribute('aria-expanded', p.hidden ? 'false' : 'true');
    navLayout();
    if (!p.hidden) { const f = p.querySelector('input,button'); if (f) f.focus(); } else b.focus();
  },
  wxclearvars() { WX.vars = []; wxSave(); route(); },
  wtpage(el) { WT.page = el.dataset.to ? +el.dataset.to : Math.max(1, WT.page + (+el.dataset.d)); loadWxTable().then(wtFocusTop); },
  async wtallcols() { wtHidden().clear(); wtSave(); loadWxTable(); },
  async wtnocols() { const T = await api('GET', '/api/weather/table?per=10&kind=' + (WT.kind === 'daily' ? 'daily' : 'hourly') + '&source=' + (WT.kind === 'sensor' ? 'sensor' : 'weather')); WT.hide = new Set(T.columns.map(c => c.key).filter(k => !['temperature_2m', 'relative_humidity_2m', 'par', 'temperature_2m_max', 'temperature_2m_min', 'precipitation_sum', 'relative_humidity_2m_mean'].includes(k) && WT.kind !== 'sensor')); wtSave(); loadWxTable(); },
  // 1.16.0: groups
  grpnew(el) { groupDialog(null, el.dataset.kind); },
  grpedit() { if (CURG) groupDialog(CURG); },
  async grpdel() {
    const d = CURG; if (!d || !(await needName())) return;
    if (!(await confirmBox('Remove the group ' + d.name + '?', 'The group goes away. The plants in it are not changed.', 'Remove the group', true))) return;
    await guard(async () => { await api('DELETE', '/api/groups/' + d.id); toast('Group removed: ' + d.name); if (String(G.group) === String(d.id)) { G.group = ''; gSave(); } await loadGroups(true); go('#/groups'); });
  },
  async grpaddsug(el) {
    const x = PGROUPS && PGROUPS.suggestions[+el.dataset.i]; if (!x || !(await needName())) return;
    await guard(async () => { await api('POST', '/api/groups', { name: x.name, kind: 'smart', rule: x.rule }); toast('Group made: ' + x.name); await loadGroups(true); await route();
      const h = document.querySelector('#grp-suggest h2') || document.querySelector('#grp-yours h2'); if (h) { h.setAttribute('tabindex', '-1'); h.focus(); } });
  },
  async grpaddall() {
    const list = (PGROUPS && PGROUPS.suggestions) || []; if (!list.length || !(await needName())) return;
    await guard(async () => { for (const x of list) await api('POST', '/api/groups', { name: x.name, kind: 'smart', rule: x.rule }); toast(`${list.length} groups made`); await loadGroups(true); route(); });
  },
  async grprm(el) {
    const d = CURG; if (!d || !(await needName())) return;
    await guard(async () => { await api('POST', `/api/groups/${d.id}/members`, { remove: [el.dataset.code] }); toast(`${plantName(el.dataset.code)} taken out of ${d.name}`); await loadGroups(true); route(); });
  },
  grpcare() { groupCare(); },
  grpmove() { groupMove(); },
  grpset() { groupSet(); },
  async grpundo(el) {
    if (!(await needName())) return;
    if (!(await confirmBox('Undo this change?', 'Each plant goes back to what it had before, unless it has been changed again since.', 'Undo the change'))) return;
    await guard(async () => { const r = await api('POST', `/api/bulk/${el.dataset.id}/undo`); toast(`Undone for ${r.undone.length} plant${r.undone.length === 1 ? '' : 's'}` + (r.kept.length ? `. ${r.kept.length} left as they are: changed again since` : '')); await loadCodes(true); route(); });
  },
  grpshow(el, e) { if (e) e.preventDefault(); G.group = String(el.dataset.id); gSave(); go('#/'); },
  plgroups() { plantGroupsDialog(); },
  tickall(el) { const fs = el.closest('fieldset'); fs.querySelectorAll('li:not([hidden]) input[name=code]').forEach(x => { x.checked = el.dataset.on === '1'; }); },
  grprulerow() {
    const box = document.getElementById('rule-rows'); if (!box) return;
    const n = box.querySelectorAll('.rule-row').length; if (n >= 8) { toast('A rule can have up to 8 parts.', true); return; }
    box.insertAdjacentHTML('beforeend', rend(ruleRow({ field: 'genus', op: 'is', value: '' }, n)));
    box.querySelector('.rule-row:last-child select').focus();
  },
  grprulerm(el) { const row = el.closest('.rule-row'); const box = row.parentElement; row.remove();
    box.querySelectorAll('.rule-row').forEach((r, i) => { r.dataset.row = i; r.querySelector('legend').textContent = 'Part ' + (i + 1); }); rulePreview(); box.querySelector('select').focus(); },
  clearfilters() { Object.assign(G, { q: '', plan: '', health: '', low: false, needs: false, group: '', status: 'active', site: '' }, Object.fromEntries(MORE_KEYS.map(k => [k, '']))); MOREOPEN = false; gSave(); route(); },
  plan(el) { G.plan = G.plan === el.dataset.plan ? '' : el.dataset.plan; document.querySelectorAll('.ledger button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.plan === G.plan))); drawGrid(); },
  pick(el) { PIDX = +el.dataset.i; repaintPhotos(); },
  zoom() { const c = curPhoto(); if (c) modal(html`<form method="dialog"><img src="${photoUrl(c.file)}" alt="${c.caption || CUR.p.common_name}"><p class="cap">${c.caption}</p><button class="btn" value="ok" autofocus>Close</button></form>`, 'photo'); },
  zoomloose(el) { modal(html`<form method="dialog"><img src="${photoUrl(el.dataset.file)}" alt="${el.dataset.cap}"><p class="cap">${el.dataset.cap}</p><button class="btn" value="ok" autofocus>Close</button></form>`, 'photo'); },
  copyreq() { return copyRequest(); },
  print() { window.print(); },
  async mainphoto() { if (!(await needName())) return; await guard(async () => { await api('PATCH', '/api/photos/' + curPhoto().id, { is_primary: true }); toast('Main photo changed. It now shows on the Plants page and care cards.'); await loadCodes(true); await reloadPlant(0); }); },
  async capedit() {
    if (!(await needName())) return;
    const c = curPhoto();
    const r = await modal(html`<form method="dialog"><h2>Photo caption</h2><label class="f">Caption<input type="text" name="c" maxlength="200" value="${c.caption}"></label>
      <div class="row"><button class="btn" value="ok">Save caption</button><button class="btn ghost" value="cancel">Cancel</button></div></form>`);
    if (r !== 'ok') return;
    await guard(async () => { await api('PATCH', '/api/photos/' + c.id, { caption: dlg.querySelector('[name=c]').value }); toast('Caption saved'); await reloadPlant(); });
  },
  async movephoto() {
    if (!(await needName())) return;
    const t = await pickPlant('Move photo', 'Choose the plant this photo belongs to. Both plants get a new version in their history.', true);
    if (t === null) return;
    await guard(async () => { await api('PATCH', '/api/photos/' + curPhoto().id, { plant_code: t }); toast('Photo moved'); await reloadPlant(0); });
  },
  async rmphoto() {
    if (!(await needName())) return;
    if (!(await confirmBox('Remove this photo?', 'It leaves this page. The file is kept in the photos_deleted folder inside your data folder, so it can be recovered by hand.', 'Remove photo', true))) return;
    await guard(async () => { await api('DELETE', '/api/photos/' + curPhoto().id); toast('Photo removed'); await reloadPlant(0); });
  },
  readsec(el) { const sec = el.closest('section'); const h = sec && sec.querySelector('h2'); readAloud(sec, el, h ? h.textContent.trim() : 'this section'); },
  readpage(el) { readAloud(readTarget(), el, 'this page'); },
  readstop() { stopReading(); },
  voicetest() { stopReading(true); readAloudText('This is how plant pages will sound. Philodendron Pink Princess, P 0 2 9. Damaged below 55 degrees.'); },
  shortcuts() { shortcutsDialog(); },
  async movein(el) { await moveSite(el, 'Indoors'); },
  frosthide(el) { try { localStorage.setItem('plantdb.frosthide', fzSig()); } catch (e) { /* not remembered */ } const b = el.closest('.fz-banner'); if (b) b.remove(); toast('Frost warning hidden. It comes back if the forecast changes.'); },
  async frostin(el) {
    if (!(await needName())) return;
    const y = window.scrollY, code = el.dataset.code;
    await guard(async () => { await api('POST', '/api/plants/' + enc(code) + '/site', { site: 'Indoors' }); toast(el.dataset.name + ' moved indoors'); await fzReload(y, code); });
  },
  async frostcover(el) { await fzMark(el, 'covered'); },
  async frostundo(el) { await fzMark(el, null); },
  async frostallin(el) {
    const grp = FZ_GROUPS.find(g => g[0] === el.dataset.group); if (!grp || !FROST) return;
    const g = FROST.plants.filter(grp[3]).filter(p => !p.done);
    if (!(await needName())) return;
    if (!(await confirmBox(`Mark ${g.length} plants as moved indoors?`, 'Their Location changes to Indoors, so they leave the cold-night list and the frost warnings. You can change any of them back on its page.', 'Moved them indoors'))) return;
    const y = window.scrollY;
    await guard(async () => { for (const p of g) await api('POST', '/api/plants/' + enc(p.code) + '/site', { site: 'Indoors' }); toast(g.length + ' plants moved indoors'); await fzReload(y); });
  },
  async frostallcover(el) {
    const grp = FZ_GROUPS.find(g => g[0] === el.dataset.group); if (!grp || !FROST) return;
    const g = FROST.plants.filter(grp[3]).filter(p => !p.done);
    if (!(await needName())) return;
    if (!(await confirmBox(`Mark ${g.length} plants as covered?`, 'Each one is ticked off for its next cold night only; it comes back on the list for the night after. This does not change their pages.', 'Mark as covered'))) return;
    const y = window.scrollY;
    await guard(async () => { for (const p of g) await api('POST', '/api/frost/done', { date: p.next.date, code: p.code, what: 'covered' }); toast(g.length + ' plants marked as covered'); await fzReload(y); });
  },
  async moveout(el) { await moveSite(el, 'Outdoors'); },
  async care(el) {
    if (!(await needName())) return;
    const k = el.dataset.kind, code = el.dataset.code;
    await guard(async () => { const r = await api('POST', '/api/care', { plant: code, kind: k }); careUndoToast((k === 'water' ? 'Watered: ' : 'Checked, still moist: ') + el.dataset.name, r && r.ids, code); await careRefresh(code); });
  },
  async careall(el) {
    const codes = el.dataset.codes.split(',').filter(Boolean); if (!codes.length) return;
    if (!(await needName())) return;
    if (!(await confirmBox(`Mark ${codes.length} plants as watered today?`, 'Each one gets a "Watered" entry for today in its care log. You can remove any of them on the plant\'s page.', 'Mark as watered'))) return;
    await guard(async () => { const r = await api('POST', '/api/care', { plants: codes, kind: el.dataset.kind }); careUndoToast(codes.length + ' plants marked as watered', r && r.ids); await careRefresh(); });
  },
  async waterall() {                    // 1.21.0: Plants page, every plant the filters show
    const shown = filteredPlants().filter(p => !isArch(p)); if (!shown.length) return;
    if (!(await needName())) return;
    await guard(async () => {
      const W = await api('GET', '/api/water'), done = new Set(W.plants.filter(w => w.last_water === W.today).map(w => w.code));
      const todo = shown.filter(p => !done.has(p.code)), skip = shown.length - todo.length;
      if (!todo.length) { toast(`All ${shown.length} plants shown were already watered today.`); return; }
      if (!(await confirmBox(`Mark ${todo.length} plant${todo.length === 1 ? '' : 's'} as watered today?`,
        `These are the plants shown with your filters.${skip ? ` ${skip} of them ${skip === 1 ? 'was' : 'were'} already watered today and ${skip === 1 ? 'is' : 'are'} skipped.` : ''} Each gets a "Watered" entry for today in its care log.`, 'Mark as watered'))) return;
      const r = await api('POST', '/api/care', { plants: todo.map(p => p.code), kind: 'water' });
      careUndoToast(`${r.ids.length} plant${r.ids.length === 1 ? '' : 's'} marked as watered${skip ? ` (${skip} already watered today were skipped)` : ''}`, r.ids);
    });
  },
  careother(el) { return careDialog(el.dataset.code, el.dataset.name); },
  async caredel(el) {
    if (!(await needName())) return;
    if (!(await confirmBox('Remove this entry?', el.dataset.what + '. The change log keeps a record that it was removed.', 'Remove', true))) return;
    await guard(async () => { await api('DELETE', '/api/care/' + el.dataset.id); toast('Entry removed'); await loadCarePlant(); });
  },
  todayneeds() { Object.assign(G, { q: '', plan: '', health: '', low: false, needs: true }); gSave(); go('#/'); },
  async archive(el) {
    if (!(await needName())) return;
    const to = el.dataset.to === '1';
    if (to && !(await confirmBox('Archive ' + CUR.p.common_name + '?', 'It disappears from the main list but nothing is deleted. You can move it back at any time.', 'Archive', false))) return;
    await guard(async () => { await api('POST', '/api/plants/' + enc(CUR.p.code) + '/status', { archived: to }); toast(to ? 'Archived' : 'Moved back'); await reloadPlant(); });
  },
  async viewver(el) {
    await guard(async () => {
      const v = await api('GET', '/api/plants/' + enc(CUR.p.code) + '/versions/' + el.dataset.v);
      const f = v.snapshot.fields;
      await modal(html`<form method="dialog"><h2>Version ${v.version}</h2><p class="muted">Saved ${when(v.changed_at)} by ${v.changed_by}. ${v.summary}</p>
        <dl class="dl">${META.fields.filter(x => f[x.name] != null && f[x.name] !== '').map(x => html`<dt>${x.label}</dt><dd>${f[x.name]}</dd>`)}</dl>
        <div class="row" style="margin-top:14px"><button class="btn" value="ok" autofocus>Close</button></div></form>`);
    });
  },
  async restore(el) {
    if (!(await needName())) return;
    const n = el.dataset.v;
    if (!(await confirmBox('Restore the text from version ' + n + '?', 'This saves a new version with the text from version ' + n + '. Nothing is deleted, and photos stay as they are now.', 'Restore', false))) return;
    await guard(async () => { const r = await api('POST', '/api/plants/' + enc(CUR.p.code) + '/restore/' + n); toast(r.changed ? 'Restored as version ' + r.version : 'That version already matches the current text'); await reloadPlant(); });
  },
  tlpick(el) {
    const D = TL.data; if (!D) return;
    TL.b = el.dataset.file; if (!TL.a || TL.a === TL.b) TL.a = D.photos[0].file === TL.b && D.photos[1] ? D.photos[1].file : D.photos[0].file;
    tlRender(); const c = document.querySelector('#tl-box .tl-cmp'); if (c) { c.scrollIntoView({ block: 'center' }); }
    const day = f => tlShort((D.photos.find(x => x.file === f) || {}).added_at);
    toast(`Comparing the photo from ${day(TL.a)} (left) with the one from ${day(TL.b)} (right)`);
  },
  async assign(el) {
    if (!(await needName())) return;
    const t = await pickPlant('Assign photo', 'Choose the plant this photo shows.', false);
    if (!t) return;
    await guard(async () => { await api('PATCH', '/api/photos/' + el.dataset.id, { plant_code: t }); toast('Assigned to ' + t); route(); });
  },
  async rmloose(el) {
    if (!(await needName())) return;
    if (!(await confirmBox('Remove this photo?', 'The file is kept in the photos_deleted folder inside your data folder.', 'Remove photo', true))) return;
    await guard(async () => { await api('DELETE', '/api/photos/' + el.dataset.id); toast('Photo removed'); route(); });
  },
  async tododel(el) { if (!(await needName())) return; await guard(async () => { await api('DELETE', '/api/to-photograph/' + el.dataset.id); route(); }); },
};
const changeActs = {
  grprulefield(el) {      // a different thing to look at: redraw this part with the right comparisons and value suggestions
    const row = el.closest('.rule-row'), i = +row.dataset.row;
    row.outerHTML = rend(ruleRow({ field: el.value, value: '' }, i));
    const again = document.querySelector(`.rule-row[data-row="${i}"] select[name=rf]`); if (again) again.focus();
    rulePreview();
  },
  grprulematch() { rulePreview(); },
  grpsetfield(el) { const F = Object.fromEntries(META.fields.map(x => [x.name, x])), box = document.getElementById('gset-input'); if (box) box.innerHTML = rend(fieldInput(F[el.value], '')); },
  tlsel(el) { TL[el.dataset.side] = el.value; tlRender(); const s = document.querySelector(`select[data-act=tlsel][data-side="${el.dataset.side}"]`); if (s) s.focus(); },
  tlkind(el) { if (el.checked) TL.hide.delete(el.value); else TL.hide.add(el.value); tlRender(); const c = document.querySelector(`input[data-act=tlkind][value="${el.value}"]`); if (c) c.focus(); },
  async site(el) {
    const was = CUR.p.site || 'Outdoors';
    if (!(await needName())) { el.value = was; return; }
    await guard(async () => { await api('POST', '/api/plants/' + enc(CUR.p.code) + '/site', { site: el.value }); toast('Location: ' + el.value); FROST_AT = 0; await reloadPlant(); });
  },
  async addphotos(el) {
    if (!el.files.length) return;
    if (!(await needName())) { el.value = ''; return; }
    const files = await photoCheck([...el.files], el); if (!files) { el.value = ''; return; }
    const fd = new FormData(); files.forEach(f => fd.append('files', f));
    toast('Uploading ' + files.length + ' photo(s)');
    await guard(async () => { await api('POST', '/api/plants/' + enc(CUR.p.code) + '/photos', undefined, fd); toast('Photos added'); await reloadPlant(9999); });
  },
  async addloose(el) {
    if (!el.files.length) return;
    if (!(await needName())) { el.value = ''; return; }
    const files = await photoCheck([...el.files], el); if (!files) { el.value = ''; return; }
    const fd = new FormData(); files.forEach(f => fd.append('files', f));
    await guard(async () => { await api('POST', '/api/photos', undefined, fd); toast('Photos added'); route(); });
  },
  preptrait(el) { prepSaveTraits({ [el.dataset.k]: el.value }, `select[data-act=preptrait][data-k="${el.dataset.k}"]`, (el.dataset.k === 'leaf_type' ? 'Leaf type: ' : 'Pot size: ') + (el.value || 'not set')); },
  preppest(el) {
    const got = [...document.querySelectorAll('input[data-act=preppest]:checked')].map(x => x.value);
    prepSaveTraits({ pests_found: got }, `input[data-act=preppest][value="${el.value}"]`, got.length ? 'Pests found: ' + got.join(', ') : 'No pests found');
  },
  fcrange(el) { FC.range = el.value; fcRefresh('select[data-act=fcrange]'); },
  fcopen(el) { FC.open = el.checked; fcRefresh('input[data-act=fcopen]'); },
  async tododone(el) { if (!(await needName())) { el.checked = !el.checked; return; } await guard(async () => { await api('PATCH', '/api/to-photograph/' + el.dataset.id, { done: el.checked }); route(); }); },
};
// back outside (prototype: proto/move-outside)
Object.assign(acts, {
  async boporch(el) { await boMove(el, 'Covered porch'); },
  async boout(el) { await boMove(el, 'Outdoors'); },
  async boleave(el) {
    if (!(await needName())) return;
    const y = window.scrollY;
    await guard(async () => { await api('POST', '/api/outside/porch', { code: el.dataset.code, action: 'clear' }); toast(el.dataset.name + ' stays on the porch. The reminder is off.'); BO_AT = 0; await route(); window.scrollTo(0, y); (document.querySelector('.bo-porchrow button') || document.querySelector('main h1')).focus({ preventScroll: true }); });
  },
});
function wtFocusTop() { const t = document.querySelector('#wx-table .pager'); if (t) t.scrollIntoView({ block: 'nearest' }); }
let PLACE_RESULTS = [];
const formActs = {
  audf() { clearTimeout(AUD.t); AUD.offset = 0; audLoad(); },       // Enter in the search box searches straight away
  async bknow(form) {
    if (!(await needName())) return;
    const f = form.elements;
    await guard(async () => { const r = await api('POST', '/api/backups', { photos: f.photos.checked, note: f.note.value.trim() }); if (!r.started) toast('A backup is already running', true); bkPoll(); });
  },
  async bkset(form) {
    if (!(await needName())) return;
    const f = form.elements;
    await guard(async () => { await api('PUT', '/api/backups/settings', { enabled: f.enabled.checked, freq: f.freq.value, hour: f.hour.value, keep: f.keep.value, photos: f.photos.checked }); toast('Automatic backup settings saved'); route(); });
  },
  async placesearch(form) {
    const q = form.elements.q.value.trim(), el = document.getElementById('place-results');
    if (q.length < 2) { toast('Type at least 2 letters of the town or city.', true); return; }
    el.innerHTML = rend(html`<p class="loading" role="status">Searching</p>`);
    try { PLACE_RESULTS = await api('GET', '/api/places/search?q=' + enc(q)); }
    catch (e) { el.innerHTML = rend(html`<p class="notice bad">${e.message}</p>`); return; }
    el.innerHTML = rend(PLACE_RESULTS.length ? html`<p>${PLACE_RESULTS.length} found. Choose the right one:</p><ul class="place-res">${PLACE_RESULTS.map((r, i) => html`<li><span><strong>${r.label}</strong><br><span class="hint">${r.lat}, ${r.lon}, ${r.tz}${r.elevation_m != null ? `, ${Math.round(r.elevation_m * 3.281)} ft up` : ''}${r.population ? `, ${num(r.population)} people` : ''}</span></span><button class="btn small" type="button" data-act="placepick" data-i="${i}">Add ${r.name}</button></li>`)}</ul>`
      : html`<p class="notice">Nothing found for "${q}". Check the spelling, try the nearest larger town, or type the place in yourself below.</p>`);
  },
  placeadd(form) { const f = form.elements; return addPlace({ name: f.name.value, lat: f.lat.value, lon: f.lon.value, tz: f.tz.value }); },
  wtgo(form) {
    const max = +form.elements.page.dataset.max, n = Math.round(+form.elements.page.value);
    if (!(n >= 1 && n <= max)) { toast(`Type a page number from 1 to ${max.toLocaleString()}.`, true); form.elements.page.focus(); return; }
    WT.page = n; loadWxTable().then(wtFocusTop);
  },
  new: submitForm, edit: submitForm,
  async wxloc(form) {
    if (!(await needName())) return;
    const f = form.elements;
    await guard(async () => { const r = await api('PUT', '/api/places/' + WX.place.id, { name: f.name.value, lat: f.lat.value, lon: f.lon.value, tz: f.tz.value, enabled: f.enabled.checked, detail_years: f.detail_years.value });
      toast(r.moved ? 'Saved. The place moved: weather already stored stays as it was, and new readings come from the new spot.' : 'Saved'); route(); });
  },
  async wxback(form) {
    const start = form.elements.start.value;
    if (!start) { toast('Pick a start date first.', true); return; }
    await guard(async () => { const r = await api('POST', '/api/weather/refresh', { backfill_start: start, loc: WX.place.id }); toast(r.started ? 'Loading history in the background' : 'An update is already running'); document.body.dataset.job = '1'; route(); });
  },
  async todo(form) {
    const f = form.elements, label = f.label.value.trim();
    let note = f.note.value.trim();
    if (!label) { toast('Type what to photograph first.', true); return; }
    const code = f.plant.value;
    if (code && !(label + ' ' + note).includes(code)) note = (note ? note + ' ' : '') + `Plant: ${code}.`;
    if (!(await needName())) return;
    await guard(async () => { await api('POST', '/api/to-photograph', { label, note }); toast('Added'); route(); });
  },
  async base(form) {
    if (!(await needName())) return;
    await guard(async () => { await api('PUT', '/api/settings', { base_url: form.elements.base.value }); toast('Address saved'); route(); });
  },
};
// ---------- 1.18.0: identify a plant with the camera, and the plant library ----------
// The pictures go to this computer's picture checker (the "plant-vision" container) through the app. Pl@ntNet and Claude are only
// asked when someone presses their buttons. Nothing is saved unless someone presses "Add this picture to its photos" or adds a plant.
const ID_SCOPES = [['common', 'Plants with a common name, and all US plants'], ['texas', 'Texas plants'], ['us', 'US plants'], ['world', 'All plants worldwide'], ['fungi', 'Fungi worldwide: mushrooms, lichens and moulds']];
const ID = { stream: null, timer: null, busy: false, last: null, streak: 0, shot: null, paused: false, said: '', qr: null, mode: 'live', st: null, keys: null };
function idScope() { try { const s = localStorage.getItem('plantdb.idscope'); if (ID_SCOPES.some(x => x[0] === s)) return s; } catch (e) { /* default */ } return 'common'; }
const pct = p => Math.round((p || 0) * 100) + '%';
const sureWord = c => c >= 0.9 ? 'Very likely' : c >= 0.75 ? 'Likely' : c >= 0.5 ? 'Possibly' : 'Unsure';
const canChange = () => ME().role !== 'viewer';
function idStatusText(st) {
  if (!st) return 'Checking the picture checker…';
  if (st.state === 'ready') return `Ready. It compares pictures with ${st.photos} photos of your plants and ${Number(st.species || 0).toLocaleString()} plant species.`;
  if (st.state === 'off') return st.step || 'The picture checker is not running.';
  if (st.state === 'error') return 'The picture checker could not start: ' + (st.error || st.step) + '. Restarting the app usually fixes it; see README, "Identify a plant".';
  return 'The picture checker is setting up: ' + st.step + (st.total ? ` (${st.done} of ${st.total})` : '') + '. The first start downloads about 5 GB and can take 20 to 40 minutes.';
}
async function idLoadStatus() {
  try { ID.st = await api('GET', '/api/identify/status'); } catch (e) { ID.st = { state: 'off', step: e.message }; }
  const b = document.getElementById('id-st');
  if (b) { b.textContent = idStatusText(ID.st); b.className = 'notice ' + (ID.st.state === 'ready' ? 'ok' : ID.st.state === 'off' || ID.st.state === 'error' ? 'bad' : ''); }
  if (ID.st.state !== 'ready' && ID.st.state !== 'error' && document.getElementById('id-st')) { clearTimeout(ID.stt); ID.stt = setTimeout(idLoadStatus, 5000); }
}
async function viewIdentify() {
  idStop();
  let keys = null;
  try { keys = await api('GET', '/api/identify/settings'); } catch (e) { /* shown as not set up */ }
  ID.keys = keys;
  const sc = idScope(), owner = ME().role === 'owner';
  return {
    title: 'Identify a plant',
    after: () => { idLoadStatus(); },
    html: html`<h1>Identify a plant</h1>
    <p>Point your camera at a plant. This computer compares the picture with your plant photos and says which plant it thinks it is, and how sure it is. If it is not one of yours, it suggests what the plant could be. Nothing is saved unless you choose to save it.</p>
    <p id="id-st" class="notice" role="status">Checking the picture checker…</p>
    <section class="id-sec id-cam" aria-labelledby="h-cam"><h2 id="h-cam">Camera</h2>
      <div class="id-view" id="id-view"><video id="id-video" playsinline muted aria-label="Camera picture"></video>
        <p class="id-placeholder" id="id-ph">The camera is off.</p></div>
      <p id="id-live" class="id-live" role="status" aria-live="polite"></p>
      <div class="row id-btns">
        <button class="btn" type="button" data-act="idcam" id="id-cam-btn">Start camera</button>
        <button class="btn ghost" type="button" data-act="idsnap" id="id-snap" disabled>Check this picture</button>
        <label class="btn ghost id-file">Use a photo instead<input type="file" accept="image/*" capture="environment" data-act="idfile"></label>
      </div>
      <p class="hint">While the camera is on it checks about once a second, and also reads plant label QR codes. "Check this picture" holds the picture still and shows everything it found.</p>
      <label class="f id-scope">When it is not one of your plants, suggest names from
        <select data-f="idscope">${ID_SCOPES.map(([k, l]) => html`<option value="${k}" ${k === sc ? raw('selected') : ''}>${l}</option>`)}</select></label>
    </section>
    <section class="id-sec" aria-labelledby="h-idres"><h2 id="h-idres">What it found</h2><div id="id-res"><p class="muted">Start the camera or choose a photo.</p></div></section>
    <section class="id-sec" aria-labelledby="h-second"><h2 id="h-second">Second opinions</h2>
      <p>When this computer is unsure, you can ask Pl@ntNet (free, up to 500 pictures a day) and then Claude (paid per picture, about a cent or two). They only see a picture when you press their button. Pl@ntNet does not keep pictures.</p>
      <ul class="id-keys">
        <li><strong>Pl@ntNet:</strong> ${keys && keys.plantnet ? html`set up (key ending ${keys.plantnet_hint.slice(1)})` : 'not set up'}</li>
        <li><strong>Claude:</strong> ${keys && keys.claude ? html`set up (key ending ${keys.claude_hint.slice(1)}), using ${keys.claude_model}` : 'not set up'}</li>
      </ul>
      ${owner ? html`<details class="id-setkeys"><summary>Set up or change the keys</summary>
        <form data-form="idkeys" autocomplete="off">
          <label class="f">Pl@ntNet API key<small>Free: sign in at my.plantnet.org, open "My account", then "Settings", and copy the API key. Leave empty to keep the saved one.</small>
            <input type="password" name="plantnet_key" autocomplete="off" spellcheck="false"></label>
          <label class="f">Anthropic API key, for Claude<small>From console.anthropic.com, "API keys". It is billed to that account. Leave empty to keep the saved one.</small>
            <input type="password" name="claude_key" autocomplete="off" spellcheck="false"></label>
          <p class="hint">The keys stay on this computer, in the database (and so in its backups). The app never shows them again, only their last 4 characters.</p>
          <div class="row"><button class="btn" type="submit">Save keys</button>
            ${keys && keys.plantnet ? html`<button class="btn ghost" type="button" data-act="idkeydel" data-k="plantnet_key">Remove the Pl@ntNet key</button>` : ''}
            ${keys && keys.claude ? html`<button class="btn ghost" type="button" data-act="idkeydel" data-k="claude_key">Remove the Claude key</button>` : ''}</div>
        </form></details>` : html`<p class="muted">${ME().owner_name || 'The owner'} can set these up.</p>`}
    </section>
    <p><a href="#/library">Search the plant library</a></p>`,
  };
}
function idStop() {
  clearTimeout(ID.timer); ID.timer = null;
  if (ID.stream) ID.stream.getTracks().forEach(t => t.stop());
  ID.stream = null; ID.busy = false; ID.streak = 0; ID.last = null; ID.paused = false; ID.said = '';
}
function idCamUi(on) {
  const b = document.getElementById('id-cam-btn'), s = document.getElementById('id-snap'), ph = document.getElementById('id-ph');
  if (b) b.textContent = on ? 'Stop camera' : 'Start camera';
  if (s) s.disabled = !on;
  if (ph) ph.hidden = on;
}
async function idCamToggle() {
  if (ID.stream) { idStop(); idCamUi(false); idSay('The camera is off.'); return; }
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    toast(window.isSecureContext ? 'This browser cannot use the camera. Use "Use a photo instead".' : 'The browser only allows the camera on a secure address: use http://localhost:8080 on this computer, or the Tailscale address (https://plants...). Or use "Use a photo instead".', true);
    return;
  }
  try {
    ID.stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' }, width: { ideal: 1920 }, height: { ideal: 1080 } }, audio: false });
  } catch (e) {
    toast(e.name === 'NotAllowedError' ? 'The camera was not allowed. Allow it in the browser\'s site settings, then try again.' : 'Could not start the camera: ' + e.message, true);
    return;
  }
  const v = document.getElementById('id-video');
  if (!v) { idStop(); return; }
  v.srcObject = ID.stream; await v.play().catch(() => {});
  if ('BarcodeDetector' in window && !ID.qr) { try { ID.qr = new window.BarcodeDetector({ formats: ['qr_code'] }); } catch (e) { ID.qr = null; } }
  idCamUi(true); idSay('The camera is on. Point it at a plant.');
  idTick();
}
function idSay(t) { if (t === ID.said) return; ID.said = t; const l = document.getElementById('id-live'); if (l) l.textContent = t; }
function idGrab(maxSide) {
  const v = document.getElementById('id-video');
  if (!v || !v.videoWidth) return null;
  const k = Math.min(1, maxSide / Math.max(v.videoWidth, v.videoHeight)), c = document.createElement('canvas');
  c.width = Math.round(v.videoWidth * k); c.height = Math.round(v.videoHeight * k);
  c.getContext('2d').drawImage(v, 0, 0, c.width, c.height);
  return c;
}
const toBlob = c => new Promise(res => c.toBlob(res, 'image/jpeg', 0.86));
async function idAsk(blob, scope) {
  const fd = new FormData(); fd.append('image', blob, 'picture.jpg');
  return api('POST', '/api/identify?scope=' + enc(scope || idScope()), undefined, fd);
}
async function idQr() {
  if (!ID.qr) return false;
  const v = document.getElementById('id-video');
  try {
    const codes = await ID.qr.detect(v);
    for (const q of codes) {
      const m = /#\/plant\/([^/?#\s]+)/.exec(q.rawValue || '');
      if (m) { const code = decodeURIComponent(m[1]); ID.paused = true; await idLabelFound(code); ID.paused = false; return true; }
    }
  } catch (e) { /* no QR this time */ }
  return false;
}
async function idLabelFound(code) {
  await loadCodes(true);
  const p = PCODES.get(code);
  idSay(`Label found: ${code}${p ? ', ' + p.common_name : ''}.`);
  const r = await modal(html`<form method="dialog" class="id-pop"><h2>Label found: ${code}</h2>
    ${p ? html`<p class="id-pop-name">${p.common_name}${p.scientific_name ? html` (<i>${p.scientific_name}</i>)` : ''}</p>${p.photo ? html`<img class="id-pop-img" src="${thumbUrl(p.photo)}" alt="Photo of ${p.common_name}">` : ''}` : html`<p>There is no plant ${code} in the record.</p>`}
    <div class="row">${p ? html`<button class="btn" value="open" autofocus>Open its page</button>` : ''}<button class="btn ghost" value="cancel" ${p ? '' : raw('autofocus')}>Keep looking</button></div></form>`);
  if (r === 'open') { idStop(); go('#/plant/' + enc(code)); }
}
async function idTick() {
  clearTimeout(ID.timer);
  if (!ID.stream || !document.getElementById('id-video')) { idStop(); return; }
  if (!ID.paused && !ID.busy && !document.hidden && !dlg.open) {
    ID.busy = true;
    try {
      if (!(await idQr())) {
        const c = idGrab(800);
        if (c && ID.st && ID.st.state === 'ready') {
          const r = await idAsk(await toBlob(c));
          if (ID.stream) await idLive(r, c);
        } else if (ID.st && ID.st.state !== 'ready') idSay(idStatusText(ID.st));
      }
    } catch (e) { idSay(e.message); if (e.status === 503) idLoadStatus(); }
    ID.busy = false;
  }
  if (ID.stream) ID.timer = setTimeout(idTick, 900);
}
async function idLive(r, canvas) {
  if (ID.paused) return;
  const m = r.matches[0];
  idPaint(r, null, true);
  if (!m) { idSay('Looking. No match yet.'); return; }
  const key = r.likely_new ? '(new)' : m.code;      // a plant that looks unlike all of yours counts as one answer too
  ID.streak = ID.last === key ? ID.streak + 1 : 1; ID.last = key;
  const c = m.confidence || 0;
  // a window: the same plant twice in a row when sure, or four times in a row when less sure or when it is not one of yours
  if ((c >= 0.8 && ID.streak >= 2 && !r.likely_new) || (ID.streak >= 4 && (c >= 0.5 || r.likely_new))) {
    ID.paused = true;
    const big = idGrab(1600) || canvas;
    ID.shot = { blob: await toBlob(big), url: big.toDataURL('image/jpeg', 0.8), result: r };
    await idPopup(r);
    ID.paused = false; ID.streak = 0; ID.last = null;
  } else if (r.likely_new) idSay(`This doesn't look like any of your plants.${r.species[0] ? ' It may be ' + (r.species[0].common_name || r.species[0].scientific_name) + '.' : ''} Hold steady.`);
  else if (c >= 0.5) idSay(`${sureWord(c)} ${m.code}, ${m.common_name} (${pct(c)} sure). Hold steady.`);
  else idSay(`Not sure yet. Closest: ${m.code}, ${m.common_name}. ${r.species[0] ? 'Or it may be ' + (r.species[0].common_name || r.species[0].scientific_name) + '.' : ''}`);
}
async function idSnap() {
  const c = idGrab(1600); if (!c) return;
  ID.paused = true;
  try {
    const blob = await toBlob(c);
    ID.shot = { blob, url: c.toDataURL('image/jpeg', 0.8) };
    idSay('Checking this picture…');
    ID.shot.result = await idAsk(blob);
    idPaint(ID.shot.result, ID.shot.url);
    await idPopup(ID.shot.result);
  } catch (e) { toast(e.message, true); }
  ID.paused = false;
}
async function idFile(input) {
  const f = input.files && input.files[0]; input.value = '';
  if (!f) return;
  const res = document.getElementById('id-res'); if (res) res.innerHTML = rend(html`<p class="muted" role="status">Checking ${f.name}…</p>`);
  try {
    const url = await new Promise((ok, no) => { const fr = new FileReader(); fr.onload = () => ok(fr.result); fr.onerror = no; fr.readAsDataURL(f); });
    ID.shot = { blob: f, url };
    ID.shot.result = await idAsk(f);
    idPaint(ID.shot.result, url);
    await idPopup(ID.shot.result);
  } catch (e) { if (res) res.innerHTML = rend(html`<div class="notice bad" role="alert">${e.message}</div>`); }
}
function idMatchCard(m, first) {
  return html`<li class="id-m"><a href="#/plant/${enc(m.code)}" data-act="idopen" data-code="${m.code}">${m.photo ? html`<img src="${thumbUrl(m.matched_photo || m.photo)}" alt="">` : ''}
    <span><b>${m.code}</b> ${m.common_name}${m.location ? html`<small>${m.location}</small>` : ''}${first && m.confidence != null ? html`<small>${sureWord(m.confidence)}: ${pct(m.confidence)} sure</small>` : ''}</span></a></li>`;
}
function spLinks(s) {
  const q = enc(s.scientific_name);
  return html`<span class="id-links">${s.usda_symbol ? html`<a href="https://plants.usda.gov/plant-profile/${enc(s.usda_symbol)}" target="_blank" rel="noopener noreferrer">USDA PLANTS</a>` : ''}
    <a href="https://powo.science.kew.org/results?q=${q}" target="_blank" rel="noopener noreferrer">Kew (POWO)</a>
    <a href="https://en.wikipedia.org/wiki/${enc(s.scientific_name.replace(/ /g, '_'))}" target="_blank" rel="noopener noreferrer">Wikipedia</a></span>`;
}
function spCard(s, i, src, withAdd) {
  const tags = [];
  if (s.in_texas) tags.push(html`<span class="tag">Grows wild in Texas</span>`);
  else if (s.us_states && s.us_states.length) tags.push(html`<span class="tag">In ${s.us_states.length} US state${s.us_states.length === 1 ? '' : 's'}</span>`);
  if (s.yours && s.yours.length) tags.push(html`<span class="tag tag-yours">You have this: ${s.yours.join(', ')}</span>`);
  else if (s.yours_genus && s.yours_genus.length) tags.push(html`<span class="tag">Same genus as ${s.yours_genus.slice(0, 4).join(', ')}</span>`);
  return html`<li class="id-sp"><div><i class="sci">${s.scientific_name}</i>${s.common_name ? html` <span>${s.common_name}</span>` : ''}
      ${s.probability != null ? html`<b class="id-p">${pct(s.probability)}</b>` : ''}</div>
    <div class="muted">${[s.family, s.order].filter(Boolean).join(', ')}</div>
    ${s.why ? html`<div>${s.why}</div>` : ''}
    ${tags.length ? html`<div class="id-tags">${tags}</div>` : ''}
    <div class="id-acts">${spLinks(s)}${withAdd ? s.kingdom === 'Fungi' ? html`<button class="btn small" type="button" data-act="idfind" data-src="${src}" data-i="${i}">Record a mushroom find</button>`
      : html`<button class="btn small" type="button" data-act="idnew" data-src="${src}" data-i="${i}">Add as a new plant</button>` : ''}</div></li>`;
}
function idPaint(r, picUrl, live) {
  const res = document.getElementById('id-res'); if (!res) return;
  const m = r.matches || [], top = m[0], c = top ? top.confidence || 0 : 0;
  const sc = ID_SCOPES.find(x => x[0] === r.scope);
  res.innerHTML = rend(html`${picUrl ? html`<img class="id-shot" src="${picUrl}" alt="The picture that was checked">` : ''}
    ${top ? html`<h3>${c >= 0.5 && !r.likely_new ? 'Your plant' : 'Closest of your plants'}</h3>
      <p>${c >= 0.5 && !r.likely_new ? html`${sureWord(c)} <b>${top.code}, ${top.common_name}</b>: ${pct(c)} sure.` : html`Probably none of your plants: the closest is ${top.code}, ${top.common_name}, ${pct(c)} sure${r.likely_new ? ', and it looks different from all your photos' : ''}.`}</p>
      <ol class="id-ms ${c >= 0.5 && !r.likely_new ? 'id-sure' : ''}">${m.slice(0, 3).map((x, i) => idMatchCard(x, i === 0))}</ol>` : html`<p>There are no photos of your plants to compare with yet.</p>`}
    <h3>What it could be</h3>
    ${r.scope === 'fungi' ? fungiSafety(true) : ''}
    ${r.genera && r.genera[0] ? html`<p>Most likely genus: <i>${r.genera[0].genus}</i> (${pct(r.genera[0].probability)}). Names below are from: ${sc ? sc[1] : 'the species list'}.</p>` : ''}
    <ol class="id-sps">${(r.species || []).map((s, i) => spCard(s, i, 'local', !live && canChange()))}</ol>
    ${live ? '' : html`<div id="id-more">${idMoreBtns()}</div>`}
    <p class="hint">Checked in ${r.seconds} seconds by ${r.model} on this computer.</p>`);
}
function idMoreBtns() {
  if (!canChange() || !ID.keys) return '';
  return html`<div class="row">${ID.keys.plantnet ? html`<button class="btn ghost" type="button" data-act="idask" data-who="plantnet">Ask Pl@ntNet</button>` : ''}
    ${ID.keys.claude ? html`<button class="btn ghost" type="button" data-act="idask" data-who="claude">Ask Claude</button>` : ''}</div><div id="id-ext"><div id="id-ext-plantnet"></div><div id="id-ext-claude"></div></div>`;
}
async function idPopup(r) {
  const m = r.matches || [], top = m[0], c = top ? top.confidence || 0 : 0, edit = canChange();
  let body;
  if (top && c >= 0.75 && !r.likely_new) {
    idSay(`${sureWord(c)} ${top.code}, ${top.common_name}: ${pct(c)} sure.`);
    body = html`<h2>${sureWord(c)} ${top.code}: ${top.common_name}</h2>
      <p class="id-conf"><b>${pct(c)} sure.</b> ${c >= 0.85 ? 'In tests on your photos, answers this sure were right about 9 times in 10.' : 'It is not certain: compare the photos.'}</p>
      <div class="id-pair">${ID.shot ? html`<figure><img src="${ID.shot.url}" alt="Your picture"><figcaption>Your picture</figcaption></figure>` : ''}
        <figure><img src="${thumbUrl(top.matched_photo || top.photo)}" alt="Photo of ${top.common_name}"><figcaption>Its closest photo</figcaption></figure></div>
      <div class="row"><button class="btn" value="open:${top.code}" autofocus>Open its page</button>
        ${edit && ID.shot ? html`<button class="btn ghost" value="addpic:${top.code}">Add this picture to its photos</button>` : ''}
        <button class="btn ghost" value="cancel">Not this one</button></div>`;
  } else if (top && c >= 0.45 && !r.likely_new) {
    idSay(`Not sure. It could be ${m.slice(0, 3).map(x => x.code).join(', ')}.`);
    body = html`<h2>Which one is it?</h2><p>It is not sure (${pct(c)} for the first). These look closest:</p>
      <div class="id-choose">${m.slice(0, 3).map((x, i) => html`<button class="id-ch" value="open:${x.code}" ${i === 0 ? raw('autofocus') : ''}>
        ${x.photo ? html`<img src="${thumbUrl(x.matched_photo || x.photo)}" alt="">` : ''}<span><b>${x.code}</b> ${x.common_name}</span></button>`)}</div>
      <p class="hint">Choosing one opens its page.${edit ? ' Or add the picture to one:' : ''}</p>
      ${edit && ID.shot ? html`<div class="row">${m.slice(0, 3).map(x => html`<button class="btn small ghost" value="addpic:${x.code}">Add the picture to ${x.code}</button>`)}</div>` : ''}
      <div class="row"><button class="btn ghost" value="cancel">None of these</button></div>`;
  } else {
    const s = (r.species || [])[0];
    idSay(`Probably not one of your plants.${s ? ' It may be ' + (s.common_name || s.scientific_name) + '.' : ''}`);
    body = html`<h2>Probably not one of your plants</h2>
      ${s ? html`<p>It looks most like <i>${s.scientific_name}</i>${s.common_name ? ' (' + s.common_name + ')' : ''}, but names from a picture are often wrong. See all the suggestions on the page${edit && ID.keys && (ID.keys.plantnet || ID.keys.claude) ? ', or ask for a second opinion' : ''}.</p>` : ''}
      ${top ? html`<p>Or is it one of yours after all? The closest are:</p><ul class="id-close">${m.slice(0, 3).map(x => html`<li><button class="linkish" value="open:${x.code}">${x.code} ${x.common_name}</button></li>`)}</ul>` : ''}
      <div class="row"><button class="btn" value="list" autofocus>See the suggestions</button><button class="btn ghost" value="cancel">Keep looking</button></div>`;
  }
  const v = await modal(html`<form method="dialog" class="id-pop">${body}</form>`, 'wide');
  if (v.startsWith('open:')) { idStop(); go('#/plant/' + enc(v.slice(5))); }
  else if (v.startsWith('addpic:')) await idAddPic(v.slice(7));
  else if (v === 'list') {
    if (ID.shot && ID.shot.result) idPaint(ID.shot.result, ID.shot.url);
    if (ID.stream) { idStop(); idCamUi(false); }
    const h = document.getElementById('h-idres'); if (h) { h.setAttribute('tabindex', '-1'); h.focus(); h.scrollIntoView({ block: 'start' }); }
  }
}
async function idAddPic(code) {
  if (!ID.shot || !(await needName())) return;
  const fd = new FormData(); fd.append('files', ID.shot.blob, 'identify-' + ymd(new Date()) + '.jpg'); fd.append('caption', 'Taken with Identify, ' + new Date().toLocaleDateString());
  await guard(async () => { await api('POST', '/api/plants/' + enc(code) + '/photos', undefined, fd); toast('Picture added to ' + code); idSay('Picture added to ' + code + '.'); });
}
async function idAskOutside(who) {
  if (!ID.shot) return;
  const box = document.getElementById('id-ext-' + who); if (!box) return;
  const name = who === 'plantnet' ? 'Pl@ntNet' : 'Claude';
  box.innerHTML = rend(html`<p role="status">Asking ${name}…</p>`);
  try {
    const fd = new FormData(); fd.append('image', ID.shot.blob, 'picture.jpg');
    const r = await api('POST', '/api/identify/' + who, undefined, fd);
    ID.shot[who] = r;
    box.innerHTML = rend(html`<h3>${name} says</h3>${r.note ? html`<p>${r.note}</p>` : ''}
      ${r.species.length ? html`<ol class="id-sps">${r.species.map((s, i) => spCard(s, i, who, canChange()))}</ol>` : ''}
      ${r.tip ? html`<p class="hint">Tip from Claude: ${r.tip}</p>` : ''}
      ${r.remaining != null ? html`<p class="hint">Pl@ntNet pictures left today: ${r.remaining}.</p>` : ''}`);
    const h = box.querySelector('h3'); if (h) { h.setAttribute('tabindex', '-1'); h.focus(); }
  } catch (e) { box.innerHTML = rend(html`<div class="notice bad" role="alert">${e.message}</div>`); }
}

// "Add as a new plant" and "Add to my plants": the Add a plant form opens with the names filled in (and the picture, if any)
let NEWFILL = null;
function idNewPlant(s, withPic) {
  const g = (s.scientific_name || '').split(' ')[0];
  NEWFILL = { common_name: (s.common_name || '').split(',')[0].trim() || s.scientific_name, scientific_name: s.scientific_name, genus: g, family: s.family || '',
              taxon_order: s.order || '', kingdom: 'Plantae', __pic: withPic && ID.shot ? ID.shot.blob : null,
              __from: `Names from ${s.src || 'the plant library'}` };
  idStop(); go('#/new');
}

// ---------- the plant library (1.18.0; 1.21.0: browse every species, filters, records with photos) ----------
// The list comes from the picture checker (offline). Photos come from iNaturalist through the app, which keeps them in
// data/library; the cards ask for the photos of the plants on screen and fill them in as they arrive.
const LIB_DEF = { q: '', scope: 'common', kind: '', family: '', state: '', common: false, mine: '', know: '', sort: 'known', view: 'cards' };
const KNOW_WORD = { native: 'Native to Texas', introduced: 'Introduced to Texas', invasive: 'On the Texas invasive list', near: 'Grows wild near home', bloom: 'Flowering near home this month',
  fruiting: 'Fungi found near home this month', hardy: 'Likely to survive outside here', petsafe: 'Safe for dogs and cats (ASPCA)', pettoxic: 'Toxic to dogs or cats (ASPCA)' };
const LIB = Object.assign({ res: [], total: 0, facets: null, facetsFor: '', photos: {}, t: 0, poll: 0, my: 0 }, LIB_DEF);
try { const s = JSON.parse(localStorage.getItem('plantdb.library') || '{}'); Object.keys(LIB_DEF).forEach(k => { if (s[k] != null && typeof s[k] === typeof LIB_DEF[k]) LIB[k] = s[k]; }); } catch (e) { /* defaults */ }
const libSave = () => { try { localStorage.setItem('plantdb.library', JSON.stringify(Object.fromEntries(Object.keys(LIB_DEF).map(k => [k, LIB[k]])))); } catch (e) { /* not remembered */ } };
const LIB_PAGE = 48;
const LIB_SORTS = [['known', 'Best known first'], ['common', 'Common name A to Z'], ['sci', 'Scientific name A to Z'], ['family', 'Family']];
const LIB_STATE_WORD = s => s.replace(/([a-z])([A-Z])/g, '$1 $2');
const LIB_KIND_SHORT = { dicot: 'Flowering plant', monocot: 'Flowering plant (monocot)', fern: 'Fern', lycophyte: 'Clubmoss', conifer: 'Conifer', cycad: 'Cycad', ginkgo: 'Ginkgo', gnetophyte: 'Gnetophyte', moss: 'Moss', liverwort: 'Liverwort', hornwort: 'Hornwort', alga: 'Alga', other: '',
  mushroom: 'Mushroom', cupfungus: 'Cup fungus', lichen: 'Lichen', rust: 'Rust or smut', mould: 'Mould or mildew', otherfungus: 'Fungus' };
const spHref = s => '#/species/' + enc(s);
function libPreHtml(p) {
  const btn = p.running ? html`<button class="btn ghost" type="button" data-act="libprestop">Stop the download</button>`
    : html`<button class="btn" type="button" data-act="libpre" ${p.online ? '' : raw('disabled')}>Download photos for the Texas list</button>`;
  const msg = p.running ? `Downloading: ${p.done.toLocaleString()} of ${p.total.toLocaleString()} done, about ${Math.max(1, Math.round(p.left * 1.1 / 60))} minutes left. You can leave this page; it carries on.`
    : p.total ? `Finished: ${p.done.toLocaleString()} species fetched${p.all ? ` (the other ${(p.all - p.total).toLocaleString()} were already kept)` : ''}.`
    : p.online ? '' : 'Turn on the iNaturalist photos above first.';
  return html`<p>${msg}</p><p class="row">${btn}</p>`;
}
async function libPrePoll() {
  clearTimeout(LIB.prePoll);
  const box = document.getElementById('lib-pre'); if (!box) return;
  let p; try { p = await api('GET', '/api/library/prefetch'); } catch (e) { return; }
  if (!document.getElementById('lib-pre')) return;
  const had = box.contains(document.activeElement);
  box.innerHTML = rend(libPreHtml(p));
  if (had) { const b = box.querySelector('button'); if (b) b.focus(); }
  if (p.running) LIB.prePoll = setTimeout(libPrePoll, 5000);
}
function libListsHtml(d) {
  const day = t => t ? new Date(t).toLocaleDateString([], { month: 'long', day: 'numeric', year: 'numeric' }) : '';
  return html`<ul class="lib-lists">${d.lists.map(l => html`<li><strong>${l.label}:</strong> ${l.fetched ? `${l.count.toLocaleString()} species, fetched ${day(l.fetched)}.` : d.queued.includes(l.name) || (d.now && d.now[0] === l.name) ? 'Being fetched…' : 'Not fetched yet.'}
      ${l.error ? html` <span class="bad-text">Last try failed: ${l.error}</span>` : ''}</li>`)}</ul>
    ${d.now ? html`<p>Fetching now: ${(d.lists.find(l => l.name === d.now[0]) || { label: d.now[0] }).label}${d.now[2] ? `, ${d.now[1].toLocaleString()} of ${d.now[2].toLocaleString()}` : ''}.</p>` : ''}
    <p class="hint">From iNaturalist (what people have recorded, and whether it is native or introduced in Texas), the ASPCA's lists, and the Texas Department of Agriculture's noxious and invasive plant list (<a href="${d.noxious_law}" target="_blank" rel="noopener noreferrer">about the list</a>). Your hardiness zone, from your own weather history: ${d.zone}.</p>
    ${d.online ? (canChange() ? html`<p class="row"><button class="btn ghost" type="button" data-act="liblists" ${d.now || d.queued.length ? raw('disabled') : ''}>Fetch the lists again now</button></p>` : '') : html`<p class="muted">Library lookups are turned off, so these are not fetched.</p>`}`;
}
async function libListsPoll() {
  clearTimeout(LIB.listPoll);
  const box = document.getElementById('lib-lists'); if (!box) return;
  let d; try { d = await api('GET', '/api/library/local'); } catch (e) { box.innerHTML = rend(html`<p class="muted">${e.message}</p>`); return; }
  if (!document.getElementById('lib-lists')) return;
  const had = box.contains(document.activeElement);
  box.innerHTML = rend(libListsHtml(d));
  if (had) { const b = box.querySelector('button'); if (b) b.focus(); }
  if (d.now || d.queued.length) LIB.listPoll = setTimeout(libListsPoll, 4000);
}
function libFiltersOn() { return ['kind', 'family', 'state', 'mine', 'know'].filter(k => LIB[k]).length + (LIB.common ? 1 : 0); }
async function viewLibrary(qs) {
  for (const k of ['q', 'scope', 'kind', 'family', 'state', 'mine', 'know', 'sort']) if (qs.get(k) != null) LIB[k] = qs.get(k);
  let st = null;
  try { st = await api('GET', '/api/identify/status'); } catch (e) { /* shown below */ }
  const ready = st && st.state === 'ready';
  let fac = null;
  if (ready) { try { fac = await api('GET', '/api/library/facets?scope=' + enc(LIB.scope)); LIB.facets = fac; LIB.facetsFor = LIB.scope; } catch (e) { /* filters without counts */ } }
  let lset = null, pre = null; if (ME().role === 'owner') { try { [lset, pre] = await Promise.all([api('GET', '/api/library/settings'), api('GET', '/api/library/prefetch')]); } catch (e) { /* hidden */ } }
  let mine = { tags: [] }, wl = { wishlist: [] };
  try { [mine, wl] = await Promise.all([api('GET', '/api/library/notes'), api('GET', '/api/wishlist')]); } catch (e) { /* no extras */ }
  const sel = (f, opts) => html`<select data-f="${f}">${opts.map(([v, l]) => html`<option value="${v}" ${String(LIB[f.slice(3)]) === v ? raw('selected') : ''}>${l}</option>`)}</select>`;
  const fungi = LIB.scope === 'fungi';
  return {
    title: 'Library',
    after: () => { if (ready) libLoad(); if (pre && pre.running) libPrePoll(); libListsPoll(); },
    html: html`<h1>Library</h1>
    <p>Every plant species this computer knows, ${st && st.species ? Number(st.species).toLocaleString() : 'about 349,000'} in all${st && st.fungi ? html`, and ${Number(st.fungi).toLocaleString()} fungi (choose "Fungi worldwide" under Look in)` : ''}. Search, filter, and open any of them for its photos, description, classification, where it grows in the US, and the species it is most often mistaken for.</p>
    ${ready ? '' : html`<p class="notice bad" role="status">${idStatusText(st)}</p>`}
    <p class="row"><a class="btn ghost" href="#/around">Around home: what's flowering and fruiting</a><a class="btn ghost" href="#/wishlist">Your wishlist (${wl.wishlist.filter(w => w.status === 'want').length} wanted)</a></p>
    <div class="filters lib-filters" role="search" aria-label="Search and filter the library">
      <label>Search<input type="search" data-f="libq" value="${LIB.q}" placeholder="Common or scientific name" autocomplete="off"></label>
      <label>Look in${sel('libscope', ID_SCOPES.map(([k, l]) => [k, l + (st && st.scopes && st.scopes[k] ? ` (${Number(st.scopes[k].count).toLocaleString()})` : '')]))}</label>
      <label>${fungi ? 'Kind of fungus' : 'Kind of plant'}${sel('libkind', [['', 'Any kind'], ...((fac && fac.kinds) || []).map(k => [k.key, `${k.label} (${k.count.toLocaleString()})`])])}</label>
      <label>Family<input type="text" data-f="libfamily" list="lib-fams" value="${LIB.family}" placeholder="Any family" autocomplete="off">
        <datalist id="lib-fams">${((fac && fac.families) || []).map(f => html`<option value="${f.name}">${f.name} (${f.count})</option>`)}</datalist></label>
      <label>Grows wild in${sel('libstate', [['', 'Anywhere'], ['us', 'The United States'], ['Texas', 'Texas'], ...((fac && fac.states) || []).map(x => [x, LIB_STATE_WORD(x)])])}${fungi ? html`<small>Lichens only: the USDA lists have no other fungi</small>` : ''}</label>
      <label>Show${sel('libmine', [['', 'All of them'], ['species', 'Only ones I have'], ['genus', 'Ones I have, or of the same genus'], ['wish', 'On my wishlist'], ['notes', 'Ones with notes or tags'],
        ...mine.tags.map(t => ['tag:' + t, `Tagged "${t}"`])])}</label>
      <label>Texas and home${sel('libknow', [['', 'Any'], ...Object.entries(KNOW_WORD).filter(([k]) => fungi ? ['near', 'fruiting', 'hardy'].includes(k) : k !== 'fruiting')])}</label>
      <label>Sort by${sel('libsort', LIB_SORTS)}</label>
      <label>Show as${sel('libview', [['cards', 'Cards with photos'], ['table', 'A table']])}</label>
      <label class="chk"><input type="checkbox" data-f="libcommon" ${LIB.common ? raw('checked') : ''}>Only ${fungi ? 'fungi' : 'plants'} with a common name</label>
    </div>
    <p class="row lib-count"><span id="lib-count" class="muted" role="status" aria-live="polite"></span>
      <button class="btn ghost small" type="button" data-act="libclear" id="lib-clear" ${libFiltersOn() || LIB.q ? '' : raw('hidden')}>Clear search and filters</button></p>
    <div id="lib-res"></div>
    <p class="row"><button class="btn" type="button" data-act="libmore" id="lib-more" hidden>Show more</button></p>
    <section class="id-sec" aria-labelledby="h-libsrc"><h2 id="h-libsrc">Where the names and photos come from</h2>
      <ul><li>Names, classification and the lookalikes: the Tree of Life list behind the BioCLIP model (Imageomics Institute, free to use), on this computer.</li>
      <li>Where a plant grows wild in the US: the USDA PLANTS state lists (public domain), on this computer.</li>
      <li>Photos and the short description: iNaturalist, whose members share their photos under Creative Commons licences (each photo names its photographer and licence), and Wikipedia. They are fetched once per species, only the species name is sent, and they are kept on this computer in data\\library.</li></ul>
      ${lset ? html`<label class="chk"><input type="checkbox" data-f="libonline" ${lset.online ? raw('checked') : ''}>Look up photos and descriptions on iNaturalist (turn off to keep the library fully offline)</label>` : ''}
    </section>
    <section class="id-sec" aria-labelledby="h-liblists"><h2 id="h-liblists">Lists about your area</h2>
      <p>The "Texas and home" filter, the tags on the cards and each species' page use these lists. They are fetched in the background and kept on this computer, and fetched again when they get old.</p>
      <div id="lib-lists" aria-live="polite"><p class="muted">Loading…</p></div></section>
    ${pre ? html`<section class="id-sec" aria-labelledby="h-libpre"><h2 id="h-libpre">Photos for offline use</h2>
      <p>Download the photo and short facts for every Texas plant now (about ${st && st.scopes && st.scopes.texas ? Number(st.scopes.texas.count).toLocaleString() : '4,700'} species), so the library shows them even without the internet. It runs in the background at about one species a second (roughly an hour and a half), after anything someone is looking at, and takes about 300 MB in data\\library. Ones already kept are skipped.</p>
      <div id="lib-pre" aria-live="polite">${libPreHtml(pre)}</div></section>` : ''}`,
  };
}
function libQuery(offset) {
  const p = { scope: LIB.scope, q: LIB.q, kind: LIB.kind, family: LIB.family, state: LIB.state, mine: LIB.mine, know: LIB.know, sort: LIB.sort, offset: String(offset), limit: String(LIB_PAGE) };
  if (LIB.common) p.common = '1';
  return new URLSearchParams(Object.fromEntries(Object.entries(p).filter(([, v]) => v !== '')));
}
async function libLoad(more) {
  const box = document.getElementById('lib-res'); if (!box) return;
  const my = ++LIB.my, off = more ? LIB.res.length : 0;
  if (!more) { box.setAttribute('aria-busy', 'true'); }
  try {
    let r = !navigator.onLine ? await offLibBrowse(off) : null;          // 1.24.0: offline, search the list saved on this device
    if (!r) { r = await api('GET', '/api/library/browse?' + libQuery(off)); if (OFF.saved) r = (await offLibBrowse(off)) || r; }
    LIB.offline = !!r.offline;
    if (my !== LIB.my) return;
    LIB.res = more ? LIB.res.concat(r.results) : r.results; LIB.total = r.total;
    libDraw(more ? r.results.length : 0);
  } catch (e) { if (my === LIB.my) box.innerHTML = rend(html`<div class="notice bad" role="alert">${e.message}</div>`); }
  box.removeAttribute('aria-busy');
}
function offKnowOk(k, f) {
  k = k || {};
  return f === 'native' ? k.tx === 'native' : f === 'introduced' ? k.tx === 'introduced' : f === 'invasive' ? !!k.invasive : f === 'near' ? !!k.near : f === 'bloom' ? !!k.bloom
    : f === 'fruiting' ? !!k.fruiting : f === 'hardy' ? ['wild-near', 'zone-yes'].includes(k.hardy) : f === 'petsafe' ? !!k.pets && k.pets.dogs === 'non-toxic' && k.pets.cats === 'non-toxic'
    : f === 'pettoxic' ? !!k.pets && (k.pets.dogs === 'toxic' || k.pets.cats === 'toxic') : true;
}
async function offLibBrowse(off) {             // the library without a connection: the Texas list saved on this device
  const idx = await offSavedJson('/api/library/offline-index'); if (!idx) return null;
  const q = LIB.q.toLowerCase(), fam = LIB.family.toLowerCase(), m = LIB.mine;
  let r = idx.species.filter(x => (!q || (x.n + ' ' + x.c).toLowerCase().includes(q)) && (!LIB.kind || x.k === LIB.kind) && (!fam || x.f.toLowerCase() === fam) && (!LIB.common || x.c)
    && (!m || (m === 'species' && x.y.length) || (m === 'genus' && x.y.length) || (m === 'wish' && x.w) || (m === 'notes' && x.t.length) || (m.startsWith('tag:') && x.t.includes(m.slice(4))))
    && (!LIB.know || offKnowOk(x.kn, LIB.know)));
  if (LIB.sort === 'sci') r = r.slice().sort((a, b) => a.n.localeCompare(b.n)); else if (LIB.sort === 'common') r = r.slice().sort((a, b) => (a.c || '~').localeCompare(b.c || '~'));
  else if (LIB.sort === 'family') r = r.slice().sort((a, b) => a.f.localeCompare(b.f) || a.n.localeCompare(b.n));
  const page = r.slice(off, off + LIB_PAGE).map(x => { LIB.photos[x.n] = x.p ? { url: x.p } : null; return { scientific_name: x.n, common_name: x.c, family: x.f, kind: x.k, genus: x.g,
    in_texas: x.tx, us_states: new Array(x.st).fill(''), yours: x.y, yours_genus: [], wish: x.w, tags: x.t, know: x.kn, own_photo: null }; });
  return { total: r.length, results: page, offline: true };
}
function libTags(s) {
  const t = [];
  if (s.yours && s.yours.length) t.push(html`<span class="tag tag-yours">You have it: ${s.yours.join(', ')}</span>`);
  else if (s.yours_genus && s.yours_genus.length) t.push(html`<span class="tag">Same genus as ${s.yours_genus.slice(0, 3).join(', ')}</span>`);
  const k = s.know || {};
  if (k.invasive) t.push(html`<span class="tag tag-warn">⚠ Texas invasive list</span>`);
  if (k.tx === 'native') t.push(html`<span class="tag">Native to Texas</span>`); else if (k.tx === 'introduced') t.push(html`<span class="tag">Introduced to Texas</span>`);
  if (k.bloom) t.push(html`<span class="tag">Flowering near home now</span>`);
  if (k.fruiting) t.push(html`<span class="tag">Found near home this month</span>`);
  else if (k.near) t.push(html`<span class="tag">Wild near home</span>`);
  if (k.pets) { const tox = ['dogs', 'cats'].filter(a => k.pets[a] === 'toxic'); t.push(tox.length ? html`<span class="tag tag-warn">⚠ Toxic to ${tox.join(' and ')}</span>` : k.pets.dogs === 'non-toxic' && k.pets.cats === 'non-toxic' ? html`<span class="tag">Safe for dogs and cats</span>` : ''); }
  if (s.wish) t.push(html`<span class="tag tag-wish">${s.wish === 'got' ? 'Wishlist: got it' : 'On your wishlist'}</span>`);
  (s.tags || []).forEach(x => t.push(html`<span class="tag tag-own">Tag: ${x}</span>`));
  if (s.in_texas) t.push(html`<span class="tag">Wild in Texas</span>`);
  else if (s.us_states && s.us_states.length) t.push(html`<span class="tag">Wild in ${s.us_states.length} US state${s.us_states.length === 1 ? '' : 's'}</span>`);
  return t;
}
function libPhotoHtml(s, cls) {
  const ph = s.own_photo ? { url: s.own_photo, mine: true } : LIB.photos[s.scientific_name];
  if (ph && ph.url) return html`<img class="${cls}" src="${ph.url}" alt="" loading="lazy" decoding="async">`;
  return html`<div class="nophoto ${cls}" data-ph="${s.scientific_name}">${ph === null ? 'No photo found' : LIB.photos.__off ? 'Photos are off' : 'Finding a photo…'}</div>`;
}
function libCard(s) {
  return html`<article class="sheet lib-card" data-sp="${s.scientific_name}">
    <div class="mat">${libPhotoHtml(s, '')}${s.kind && LIB_KIND_SHORT[s.kind] ? html`<span class="acc">${LIB_KIND_SHORT[s.kind]}</span>` : ''}</div>
    <h3 class="name"><a class="sheet-link" href="${spHref(s.scientific_name)}">${s.common_name || s.scientific_name}</a></h3>
    ${s.common_name ? html`<p class="sci latin">${s.scientific_name}</p>` : ''}
    <p class="lib-fam">${s.family || 'Family not known'}</p>
    ${s.records ? html`<p class="lib-rec">${s.records.toLocaleString()} record${s.records === 1 ? '' : 's'} near home</p>` : ''}
    <div class="tags">${libTags(s)}</div>
  </article>`;
}
function libRow(s) {
  return html`<tr data-sp="${s.scientific_name}"><td class="lib-th">${libPhotoHtml(s, 'lib-thumb')}</td>
    <td><a href="${spHref(s.scientific_name)}">${s.common_name || s.scientific_name}</a></td><td class="latin">${s.scientific_name}</td>
    <td>${s.family}</td><td>${LIB_KIND_SHORT[s.kind] || ''}</td>
    <td>${s.in_texas ? 'Texas' + (s.us_states.length > 1 ? ` and ${s.us_states.length - 1} more states` : '') : s.us_states && s.us_states.length ? `${s.us_states.length} US state${s.us_states.length === 1 ? '' : 's'}` : ''}</td>
    <td>${s.yours && s.yours.length ? s.yours.join(', ') : s.yours_genus && s.yours_genus.length ? 'Same genus: ' + s.yours_genus.slice(0, 3).join(', ') : ''}</td></tr>`;
}
function libDraw(added) {
  const box = document.getElementById('lib-res'); if (!box) return;
  const n = LIB.res.length, cnt = document.getElementById('lib-count'), more = document.getElementById('lib-more'), clr = document.getElementById('lib-clear');
  const sc = ID_SCOPES.find(x => x[0] === LIB.scope);
  if (cnt && LIB.offline) cnt.dataset.off = '1'; else if (cnt) delete cnt.dataset.off;
  if (cnt) cnt.textContent = (LIB.offline ? 'Offline: searching the Texas list saved on this device. ' : '') + (LIB.total ? `Showing ${n.toLocaleString()} of ${LIB.total.toLocaleString()} in ${sc ? sc[1][0].toLowerCase() + sc[1].slice(1) : 'the list'}${LIB.q ? ` matching "${LIB.q}"` : ''}.` : `Nothing found${LIB.q ? ` for "${LIB.q}"` : ''} with these filters.`);
  if (more) { more.hidden = n >= LIB.total; more.textContent = `Show ${Math.min(LIB_PAGE, LIB.total - n)} more`; }
  if (clr) clr.hidden = !(libFiltersOn() || LIB.q);
  if (!LIB.total) {
    box.innerHTML = rend(html`<div class="empty"><p>Try another spelling, fewer filters${LIB.scope !== 'world' ? ', or "All plants worldwide" under Look in' : ''}.</p></div>`);
    return;
  }
  if (LIB.view === 'table') {
    box.innerHTML = rend(html`<div class="tbl-wrap"><table class="tbl lib-tbl"><caption class="sr">Plant species, ${LIB.total} in all</caption><thead><tr><th scope="col">Photo</th><th scope="col">Name</th><th scope="col">Scientific name</th><th scope="col">Family</th><th scope="col">Kind</th><th scope="col">Grows wild in</th><th scope="col">Yours</th></tr></thead>
      <tbody>${LIB.res.map(libRow)}</tbody></table></div>`);
  } else if (added && box.querySelector('.grid')) {
    box.querySelector('.grid').insertAdjacentHTML('beforeend', rend(LIB.res.slice(n - added).map(libCard)));
  } else {
    box.innerHTML = rend(html`<div class="grid lib-grid">${LIB.res.map(libCard)}</div>`);
  }
  if (added) { const first = box.querySelectorAll('[data-sp]')[n - added]; const a = first && first.querySelector('a'); if (a) a.focus(); }
  libPhotos();
}
async function libPhotos() {
  clearTimeout(LIB.poll);
  const want = [...new Set([...document.querySelectorAll('#lib-res [data-ph]')].map(e => e.dataset.ph).filter(n => LIB.photos[n] === undefined || LIB.photos[n] === 'pending'))];
  if (!want.length) return;
  let r;
  try { r = await api('GET', '/api/library/photos?names=' + enc(want.slice(0, 150).join('|'))); } catch (e) { return; }
  LIB.photos.__off = !r.online;
  let pending = 0;
  for (const [name, v] of Object.entries(r.photos)) {
    LIB.photos[name] = v; if (v === 'pending') pending++;
    if (v === 'pending') continue;
    document.querySelectorAll(`#lib-res [data-ph="${CSS.escape(name)}"]`).forEach(el => {
      const s = LIB.res.find(x => x.scientific_name === name); if (!s) return;
      el.outerHTML = rend(libPhotoHtml(s, el.classList.contains('lib-thumb') ? 'lib-thumb' : ''));
    });
  }
  if (!r.online) document.querySelectorAll('#lib-res [data-ph]').forEach(el => { el.textContent = 'Photos are off'; });
  if (pending && document.getElementById('lib-res')) LIB.poll = setTimeout(libPhotos, 3000);     // the background fetch does about one a second
}
function libChanged(reload) {
  libSave();
  history.replaceState(null, '', '#/library' + (LIB.q ? '?' + new URLSearchParams({ q: LIB.q }) : ''));
  lastPath = location.hash.replace(/^#/, '');
  if (reload) route(); else libLoad();
}

// ---------- one species: the library record (1.21.0) ----------
async function viewSpecies(name) {
  let d;
  try { d = await api('GET', '/api/library/taxon?name=' + enc(name)); }
  catch (e) {                                  // 1.24.0: offline, and this species was not opened before: what the saved Texas list knows
    const idx = e.offline || !navigator.onLine ? await offSavedJson('/api/library/offline-index') : null, x = idx && idx.species.find(y => y.n === name);
    if (!x) throw e;
    d = { scientific_name: x.n, common_name: x.c, family: x.f, genus: x.g, kind: LIB_KIND_SHORT[x.k] || '', in_texas: x.tx, us_states: [], classification: [{ rank: 'Family', name: x.f }, { rank: 'Genus', name: x.g }],
      common_names: x.c ? [x.c] : [], similar: [], yours: x.y, yours_genus: [], your_plants: [], your_finds: [], know: x.kn, wish: x.w, tags: x.t, wishlist: null,
      notes: { notes: '', tags: x.t.join(', ') }, care: null, zone: '', home: 'home', near_km: 50, online: false, own_photo: x.p, offline_row: true };
  }
  SPCUR = d;
  const title = d.common_name || d.scientific_name;
  const cls = d.classification || [], states = d.us_states || [];
  const fungus = d.kingdom === 'Fungi';
  const filt = (k, v) => `#/library?${new URLSearchParams({ [k]: v, scope: fungus ? 'fungi' : 'world' })}`;
  return {
    title,
    after: () => spInfo(d),
    html: html`<p class="crumb"><a href="#/library">Back to the library</a></p>
    <article class="species" aria-labelledby="sp-h">
      <header class="sp-head"><h1 id="sp-h">${title}</h1>
        ${d.common_name ? html`<p class="sp-sci latin">${d.scientific_name}</p>` : ''}
        <p class="muted">${[d.kind, d.family ? 'family ' + d.family : ''].filter(Boolean).join(', ')}</p>
        <div class="tags">${libTags(d)}</div></header>
      ${fungus ? fungiSafety(true) : ''}
      <div class="sp-grid">
        <section class="sp-photos" aria-labelledby="sp-ph-h"><h2 id="sp-ph-h">Photos</h2><div id="sp-gallery"><p class="muted" role="status">${d.online ? 'Finding photos…' : 'Photos from iNaturalist are turned off.'}</p></div></section>
        <section aria-labelledby="sp-about-h"><h2 id="sp-about-h">About</h2><div id="sp-about"><p class="muted">${d.online ? 'Looking up the description…' : 'The description comes from iNaturalist and Wikipedia, which are turned off.'}</p></div>
          ${d.your_plants && d.your_plants.length ? html`<h3>Your plants</h3><ul class="sp-yours">${d.your_plants.map(p => html`<li><a href="#/plant/${enc(p.code)}">${p.photo ? html`<img src="${thumbUrl(p.photo)}" alt="" loading="lazy">` : ''}<span><b>${p.code}</b> ${p.common_name}${(d.yours || []).includes(p.code) ? '' : html` <small>(same genus)</small>`}</span></a></li>`)}</ul>` : ''}
          ${d.your_finds && d.your_finds.length ? html`<h3>Your finds</h3><ul class="sp-yours">${d.your_finds.map(f => html`<li><a href="#/fungi/${enc(f.code)}"><span><b>${f.code}</b> ${f.name || 'Unnamed'}, found ${longDay(f.found_on)} <small>(${(MU_ID_TAG[f.id_status] || f.id_status).toLowerCase()})</small></span></a></li>`)}</ul>` : ''}
          ${spWishHtml(d)}
          <div class="row sp-acts">${canChange() ? fungus ? html`<button class="btn" type="button" data-act="munewfrom">Record a find of this</button>` : html`<button class="btn" type="button" data-act="spnew">Add to my plants</button>` : ''}
            <a class="btn ghost" href="#/identify">${fungus ? 'Identify from a photo' : 'Identify a plant'}</a></div>
        </section>
      </div>
      ${spHomeHtml(d, fungus)}
      ${fungus ? '' : spPetsHtml(d)}
      ${fungus ? '' : html`<section aria-labelledby="sp-care-h"><h2 id="sp-care-h">Care sheet</h2><div id="sp-care">${spCareHtml(d)}</div></section>`}
      <section aria-labelledby="sp-notes-h"><h2 id="sp-notes-h">Your notes and tags</h2>
        <p class="hint">Shared with everyone you have given access to the app.</p>
        ${d.notes.notes || d.notes.tags ? html`<div class="sp-mynotes">${d.notes.notes ? html`<p class="pl">${d.notes.notes}</p>` : ''}
          ${d.notes.tags ? html`<div class="tags">${d.notes.tags.split(',').map(t => t.trim()).filter(Boolean).map(t => html`<a class="tag tag-own" href="#/library?${new URLSearchParams({ mine: 'tag:' + t, scope: fungus ? 'fungi' : 'world' })}">Tag: ${t}</a>`)}</div>` : ''}
          <p class="hint">Last changed by ${d.notes.updated_by} on ${when(d.notes.updated_at)}.</p></div>` : html`<p class="muted">No notes yet.</p>`}
        ${canChange() ? html`<details class="sp-notes-edit"><summary>${d.notes.notes || d.notes.tags ? 'Edit the notes and tags' : 'Add notes and tags'}</summary>
          <form data-form="spnotes" autocomplete="off"><label class="f">Notes<textarea name="notes" rows="5">${d.notes.notes}</textarea></label>
            <label class="f">Tags<small>Separate them with commas, for example: shade, gift idea, saw at the nursery</small><input type="text" name="tags" value="${d.notes.tags}"></label>
            <div class="row"><button class="btn" type="submit">Save notes and tags</button></div></form></details>` : ''}</section>
      <section aria-labelledby="sp-names-h"><h2 id="sp-names-h">Names</h2>
        <dl class="dl"><dt>Scientific name</dt><dd class="latin">${d.scientific_name}</dd>
          <dt>Common names</dt><dd id="sp-common">${(d.common_names || []).length ? d.common_names.join('; ') : 'None in the lists on this computer.'}</dd></dl></section>
      <section aria-labelledby="sp-cls-h"><h2 id="sp-cls-h">Classification</h2>
        <ol class="sp-cls">${cls.map(c => html`<li><span class="muted">${c.rank}:</span> ${['Order', 'Family', 'Genus'].includes(c.rank) ? html`<a href="${filt(c.rank.toLowerCase(), c.name)}">${c.name}</a>` : c.name}</li>`)}
          <li><span class="muted">Species:</span> <i>${d.scientific_name}</i></li></ol>
        <p class="hint">The links list every species in that order, family or genus.</p></section>
      <section aria-labelledby="sp-us-h"><h2 id="sp-us-h">${fungus ? 'Where it grows' : 'Where it grows wild in the US'}</h2>
        ${fungus && !states.length ? html`<p>The USDA PLANTS lists cover plants and lichens, not other fungi, so this computer has no US range for it. iNaturalist (below) shows where people have seen it.</p>` : states.length ? html`<p>${states.length === 1 ? 'One state or territory' : states.length + ' states and territories'}, from the USDA PLANTS lists: ${states.map(LIB_STATE_WORD).join(', ')}.</p>`
          : html`<p>It is not on the USDA PLANTS state lists, so it does not grow wild in the US (or is not recorded there). It may still be grown in gardens and homes.</p>`}</section>
      ${d.similar && d.similar.length ? html`<section aria-labelledby="sp-sim-h"><h2 id="sp-sim-h">Looks like</h2>
        <p class="hint">The species the BioCLIP model finds closest to this one. ${fungus ? 'Never use this to tell an edible mushroom from a poisonous one. ' : ''}Species that look alike sit close together, so these are the ones it is easy to mix up with, not always close relatives.</p>
        <div class="grid lib-grid" id="lib-res">${d.similar.map(libCard)}</div></section>` : ''}
      <section aria-labelledby="sp-links-h"><h2 id="sp-links-h">More about it elsewhere</h2>
        <ul class="sp-links" id="sp-links">${d.usda_symbol ? html`<li><a href="https://plants.usda.gov/plant-profile/${enc(d.usda_symbol)}" target="_blank" rel="noopener noreferrer">USDA PLANTS</a>: range map, native status, growth habit</li>` : ''}
          ${fungus ? html`<li><a href="https://www.gbif.org/species/search?q=${enc(d.scientific_name)}" target="_blank" rel="noopener noreferrer">GBIF</a>: records worldwide and accepted name</li>`
            : html`<li><a href="https://powo.science.kew.org/results?q=${enc(d.scientific_name)}" target="_blank" rel="noopener noreferrer">Kew, Plants of the World Online</a>: native range and accepted name</li>`}
          <li><a href="https://www.inaturalist.org/search?q=${enc(d.scientific_name)}" target="_blank" rel="noopener noreferrer">iNaturalist</a>: photos and sightings near you</li>
          <li><a href="https://en.wikipedia.org/wiki/${enc(d.scientific_name.replace(/ /g, '_'))}" target="_blank" rel="noopener noreferrer">Wikipedia</a></li></ul></section>
    </article>`,
  };
}
async function spInfo(d) {
  LIB.res = d.similar || [];
  libPhotos();
  const gal = document.getElementById('sp-gallery'), about = document.getElementById('sp-about');
  if (!gal) return;
  if (!d.online) { if (d.offline_row) spGallery(d, d.own_photo ? [{ url: d.own_photo, credit: 'Photo from iNaturalist (saved on this device)' }] : []); else if (d.own_photo || (d.your_plants || []).some(p => p.photo)) spGallery(d, []); return; }
  let r;
  try { r = await api('GET', '/api/library/info?name=' + enc(d.scientific_name)); } catch (e) { r = { error: e.message }; }
  if (!document.getElementById('sp-gallery')) return;
  if (r.error) { gal.innerHTML = rend(html`<p class="notice">${r.error}</p>`); about.innerHTML = ''; return; }
  spGallery(d, r.photos || []);
  about.innerHTML = rend(html`${r.inat_common ? html`<p><strong>Also called:</strong> ${r.inat_common}</p>` : ''}
    ${r.summary ? html`<p>${r.summary}</p><p class="hint">From Wikipedia${r.wikipedia_url ? html` (<a href="${r.wikipedia_url}" target="_blank" rel="noopener noreferrer">read more</a>)` : ''}, CC BY-SA.</p>` : html`<p class="muted">No description found for this species.</p>`}
    ${r.observations ? html`<p class="hint">iNaturalist members have recorded it ${Number(r.observations).toLocaleString()} times${r.inat_url ? html` (<a href="${r.inat_url}" target="_blank" rel="noopener noreferrer">see them</a>)` : ''}.</p>` : ''}`);
  const cm = document.getElementById('sp-common');
  if (cm && r.inat_common && !(d.common_names || []).some(x => x.toLowerCase() === r.inat_common.toLowerCase())) cm.textContent = [r.inat_common, ...(d.common_names || [])].join('; ');
}
function spGallery(d, photos) {
  const gal = document.getElementById('sp-gallery'); if (!gal) return;
  const mine = (d.your_plants || []).filter(p => p.photo && (d.yours || []).includes(p.code)).map(p => ({ url: thumbUrl(p.photo), credit: `Your plant ${p.code}`, mine: true }));
  const all = mine.concat(photos);
  if (!all.length) { gal.innerHTML = rend(html`<p class="muted">No photos found for this species.</p>`); return; }
  let i = 0;
  const draw = () => {
    const p = all[i];
    gal.innerHTML = rend(html`<figure class="sp-fig"><img src="${p.url}" alt="${p.mine ? 'Your plant' : 'Photo of ' + (d.common_name || d.scientific_name)}">
      <figcaption>${p.mine ? p.credit : html`${p.credit || 'Photo from iNaturalist'}${p.license && !/\bcc\b|rights|public domain/i.test(p.credit || '') ? ` (${p.license})` : ''}${p.page ? html`. <a href="${p.page}" target="_blank" rel="noopener noreferrer">On iNaturalist</a>` : ''}`}</figcaption></figure>
      ${all.length > 1 ? html`<div class="row sp-step"><button class="btn ghost small" type="button" data-act="spph" data-d="-1">‹ Previous photo</button><span class="muted">${i + 1} of ${all.length}</span><button class="btn ghost small" type="button" data-act="spph" data-d="1">Next photo ›</button></div>` : ''}`);
  };
  SPG.step = dd => { i = (i + dd + all.length) % all.length; draw(); const b = gal.querySelector(`[data-act=spph][data-d="${dd}"]`); if (b) b.focus(); };
  draw();
}
// 1.23.0: here at home, pets, care sheet
const MILES = km => Math.round(km * 0.621);
function spHomeHtml(d, fungus) {
  const k = d.know || {}, mi = MILES(d.near_km || 50), care = d.care && d.care.sheet;
  const lines = [];
  if (k.invasive) lines.push(html`<div class="notice bad" role="note"><strong>⚠ On the Texas noxious and invasive plant list</strong> (as ${k.invasive}). Texas law says it may not be sold, distributed or brought into Texas. If it is growing wild on your land, removing it helps. <a href="${d.noxious_law}" target="_blank" rel="noopener noreferrer">About the list</a>.</div>`);
  if (!fungus) lines.push(html`<p><strong>In Texas:</strong> ${k.tx === 'native' ? 'native.' : k.tx === 'introduced' ? 'introduced (not native), growing wild here.' : 'not on the iNaturalist lists of Texas plants (or the lists are not fetched yet).'}</p>`);
  lines.push(html`<p><strong>Near ${d.home}:</strong> ${k.near ? `recorded growing wild ${k.near.toLocaleString()} time${k.near === 1 ? '' : 's'} within ${mi} miles` : `not recorded wild within ${mi} miles`}${k.bloom ? ', and seen flowering there this month' : ''}${k.fruiting ? ', and found there this month' : ''}.</p>`);
  if (!fungus) {
    const zz = care ? `zones ${care.zone_low || '?'} to ${care.zone_high || '?'}` : '';
    const v = k.hardy === 'wild-near' ? html`<strong>Likely.</strong> It grows wild within ${mi} miles of you, so it copes with the weather here.`
      : k.hardy === 'zone-yes' ? html`<strong>Likely.</strong> The care sheet gives ${zz}, and yours is ${d.zone}.`
      : k.hardy === 'zone-no' ? html`<strong>Probably not all year.</strong> The care sheet gives ${zz}, and yours is ${d.zone}. Bring it in, or cover it, on cold nights.`
      : html`Not known yet. ${canChange() ? 'Write a care sheet below to get its hardiness zones.' : ''}`;
    lines.push(html`<p><strong>Will it survive outside here all year?</strong> ${v}</p>`);
  }
  return html`<section aria-labelledby="sp-home-h"><h2 id="sp-home-h">Here at home</h2>${lines}</section>`;
}
function spPetsHtml(d) {
  const p = (d.know || {}).pets, w = v => v === 'toxic' ? '⚠ Toxic' : v === 'non-toxic' ? 'Not toxic' : 'Not listed';
  return html`<section aria-labelledby="sp-pets-h"><h2 id="sp-pets-h">Pets</h2>
    ${p ? html`<table class="tbl sp-pets"><caption class="sr">ASPCA toxicity</caption><thead><tr><th scope="col">Animal</th><th scope="col">ASPCA says</th></tr></thead>
      <tbody>${[['Dogs', p.dogs], ['Cats', p.cats], ['Horses', p.horses]].map(([a, v]) => html`<tr><th scope="row">${a}</th><td>${w(v)}</td></tr>`)}</tbody></table>
      <p class="hint">The ASPCA lists it as ${p.common} (<i>${p.listed_as}</i>)${p.genus ? ', for the whole genus' : ''}.</p>`
      : html`<p>Not on the ASPCA's lists of toxic and non-toxic plants (or the lists are not fetched yet). That does not mean it is safe.</p>`}
    <p class="hint">If a pet may have eaten a plant, call your vet or ASPCA Animal Poison Control at (888) 426-4435.</p></section>`;
}
function spCareHtml(d) {
  const c = d.care;
  const btn = canChange() ? html`<p class="row"><button class="btn ${c ? 'ghost' : ''}" type="button" data-act="spcare">${c ? 'Write it again' : 'Write a care sheet with Claude'}</button></p>` : '';
  if (!c) return html`<p class="muted">No care sheet yet.</p>${canChange() ? html`<p class="hint">Claude writes one in about half a minute with the owner's Anthropic key (a cent or two), for your place and zone. It is kept, and anyone with access can read it.</p>` : ''}${btn}`;
  const sh = c.sheet, F = [['summary', 'In short'], ['light', 'Light'], ['water', 'Water'], ['soil', 'Soil'], ['temperature', 'Temperature'], ['humidity', 'Humidity'], ['feeding', 'Feeding'],
    ['pruning', 'Pruning'], ['propagation', 'Propagation'], ['pests', 'Pests and problems'], ['containers', 'In a pot'], ['outdoors_here', 'Outdoors here']];
  return html`<div class="notice" role="note"><strong>Written by Claude, not checked by a person.</strong> Check anything important before relying on it.</div>
    <dl class="dl">${F.filter(([k]) => sh[k]).map(([k, l]) => html`<dt>${l}</dt><dd>${sh[k]}</dd>`)}
      ${sh.zone_low ? html`<dt>Hardiness</dt><dd>USDA zones ${sh.zone_low} to ${sh.zone_high || '?'}${sh.min_temp_f != null ? `; survives down to about ${sh.min_temp_f}°F` : ''}. Yours is ${d.zone}.</dd>` : ''}</dl>
    <p class="hint">Written ${when(c.written_at)} by ${c.model}, asked by ${c.asked_by}, for ${c.place} (zone ${c.zone}).</p>${btn}`;
}
function spWishHtml(d) {
  const w = d.wishlist;
  if (!w) return canChange() ? html`<div class="sp-wish"><button class="btn ghost" type="button" data-act="spwish">Add to my wishlist</button></div>` : '';
  return html`<div class="sp-wish notice" role="note"><p><strong>${w.status === 'got' ? 'On your wishlist: you got it.' : 'On your wishlist.'}</strong> Added by ${w.added_by} on ${when(w.added_at)}.
    ${w.where_seen ? html`Where to find it: ${w.where_seen}.` : ''}</p>${w.notes ? html`<p class="pl">${w.notes}</p>` : ''}
    <p class="row"><a href="#/wishlist">Open the wishlist</a>${canChange() ? html`<button class="btn ghost small" type="button" data-act="wledit" data-name="${w.name}">Edit</button>` : ''}</p></div>`;
}
// ---------- 1.23.0: around home (#/around) ----------
async function viewAround() {
  const d = await api('GET', '/api/library/around');
  LIB.res = d.sections.flatMap(x => x.species);
  const empty = d.sections.every(x => !x.fetched);
  return {
    title: 'Around home', after: () => { libPhotos(); if (empty && d.online) setTimeout(() => { if (location.hash === '#/around') route(); }, 15000); },
    html: html`<p class="crumb"><a href="#/library">Back to the library</a></p><h1>Around ${d.place}</h1>
    <p>What people have recorded growing wild within ${MILES(d.near_km)} miles of ${d.place}, from iNaturalist: what is flowering this month, the mushrooms and other fungi found this month, and the plants and fungi recorded most often. Open any of them for its page.</p>
    ${d.sections.some(x => x.key === 'fruiting' && x.total) ? fungiSafety(true) : ''}
    ${!d.online ? html`<p class="notice">Library lookups are turned off, so these lists are not fetched. The owner can turn them on at the bottom of the Library page.</p>` : empty ? html`<p class="notice" role="status">The lists are being fetched for the first time. This page fills in by itself in a minute or two.</p>` : ''}
    <div id="lib-res">${d.sections.map(x => html`<section aria-labelledby="ar-${x.key}"><h2 id="ar-${x.key}">${x.title}</h2>
      ${x.total ? html`<p class="muted">${x.total > x.species.length ? `The ${x.species.length} recorded most, of ${x.total.toLocaleString()}.` : `${x.total} species.`} <a href="#/library?${new URLSearchParams({ know: x.key, scope: x.key === 'fruiting' ? 'fungi' : 'world', q: '' })}">See them all in the library</a>.</p>
        <div class="grid lib-grid">${x.species.map(libCard)}</div>` : html`<p class="muted">${x.fetched ? 'Nothing recorded yet.' : 'Not fetched yet.'}</p>`}</section>`)}</div>`,
  };
}

// ---------- 1.22.0: the wishlist (#/wishlist) ----------
let WL = [];
async function viewWishlist() {
  WL = (await api('GET', '/api/wishlist')).wishlist;
  const want = WL.filter(w => w.status === 'want'), got = WL.filter(w => w.status === 'got');
  const item = (w, i) => html`<li class="wl-item"><h3><a href="${spHref(w.name)}">${w.common_name || w.name}</a></h3>
    ${w.common_name ? html`<p class="latin">${w.name}</p>` : ''}
    ${w.yours && w.yours.length ? html`<p><span class="tag tag-yours">You have it: ${w.yours.join(', ')}</span></p>` : ''}
    ${w.where_seen ? html`<p><strong>Where to find it:</strong> ${w.where_seen}</p>` : ''}
    ${w.notes ? html`<p class="pl">${w.notes}</p>` : ''}
    <p class="hint">Added by ${w.added_by} on ${when(w.added_at)}.</p>
    <div class="row wl-acts"><button class="btn small" type="button" data-act="wlgot" data-i="${i}">${w.status === 'got' ? 'Move back to wanted' : 'Got it'}</button>
      <button class="btn ghost small" type="button" data-act="wledit" data-name="${w.name}">Edit</button>
      <button class="btn danger small" type="button" data-act="wlrm" data-i="${i}">Take it off the list</button></div></li>`;
  return {
    title: 'Wishlist',
    html: html`<p class="crumb"><a href="#/library">Back to the library</a></p><h1>Wishlist</h1>
    <p>Plants (or fungi) you would like to have or find. Add one from its page in the <a href="#/library">library</a>. Everyone you have given access to the app sees this list.</p>
    <h2>Wanted (${want.length})</h2>${want.length ? html`<ul class="wl-list">${want.map(w => item(w, WL.indexOf(w)))}</ul>` : html`<p class="muted">Nothing wanted yet. Open a species in the library and press "Add to my wishlist".</p>`}
    ${got.length ? html`<h2>Got them (${got.length})</h2><ul class="wl-list">${got.map(w => item(w, WL.indexOf(w)))}</ul>` : ''}`,
  };
}
Object.assign(acts, {
  async wlgot(el) {
    const w = WL[+el.dataset.i]; if (!w || !(await needName())) return;
    await guard(async () => { await api('PUT', '/api/wishlist', { name: w.name, status: w.status === 'got' ? 'want' : 'got' }); toast(w.status === 'got' ? 'Moved back to wanted' : 'Marked as got it'); await route(); });
  },
  async wlrm(el) {
    const w = WL[+el.dataset.i]; if (!w || !(await needName())) return;
    if (!(await confirmBox('Take it off the wishlist?', `${w.common_name || w.name} and its notes leave the list.`, 'Take it off the list', true))) return;
    await guard(async () => { await api('DELETE', '/api/wishlist', { name: w.name }); toast('Taken off the wishlist'); await route(); });
  },
  async wledit(el) {
    if (!(await needName())) return;
    const all = (await api('GET', '/api/wishlist')).wishlist, w = all.find(x => x.name === el.dataset.name); if (!w) return;
    const r = await modal(html`<form method="dialog"><h2>Edit: ${w.common_name || w.name}</h2>
      <label class="f">Where to find it<small>A nursery, a website, a friend's garden</small><input type="text" name="where" maxlength="300" value="${w.where_seen}"></label>
      <label class="f">Notes<textarea name="notes" rows="4" maxlength="2000">${w.notes}</textarea></label>
      <label class="f">Status<select name="status"><option value="want" ${w.status === 'want' ? raw('selected') : ''}>Wanted</option><option value="got" ${w.status === 'got' ? raw('selected') : ''}>Got it</option></select></label>
      <div class="row"><button class="btn" value="ok">Save changes</button><button class="btn ghost" value="cancel">Cancel</button></div></form>`);
    if (r !== 'ok') return;
    await guard(async () => { await api('PUT', '/api/wishlist', { name: w.name, where_seen: dlg.querySelector('[name=where]').value, notes: dlg.querySelector('[name=notes]').value, status: dlg.querySelector('[name=status]').value }); toast('Saved'); await route(); });
  },
});
const SPG = { step: null };
let SPCUR = null;          // the species page on screen, for "Add to my plants"
Object.assign(acts, {
  libmore: () => libLoad(true),
  libclear: () => { Object.assign(LIB, { q: '', kind: '', family: '', state: '', common: false, mine: '', know: '' }); libChanged(true); },
  spph: el => SPG.step && SPG.step(+el.dataset.d),
  async spcare(el) {
    if (!SPCUR || !(await needName())) return;
    const box = document.getElementById('sp-care'); el.disabled = true;
    box.insertAdjacentHTML('beforeend', rend(html`<p role="status" id="sp-care-wait">Claude is writing the care sheet. This takes about half a minute…</p>`));
    try { const r = await api('POST', '/api/library/care', { name: SPCUR.scientific_name, common_name: SPCUR.common_name || '' }); SPCUR.care = r.care; box.innerHTML = rend(spCareHtml(SPCUR)); toast('Care sheet written'); const h = document.getElementById('sp-care-h'); if (h) { h.setAttribute('tabindex', '-1'); h.focus(); } }
    catch (e) { const w = document.getElementById('sp-care-wait'); if (w) w.remove(); el.disabled = false; box.insertAdjacentHTML('beforeend', rend(html`<div class="notice bad" role="alert">${e.message}</div>`)); }
  },
  async spwish() {
    if (!SPCUR || !(await needName())) return;
    await guard(async () => { await api('PUT', '/api/wishlist', { name: SPCUR.scientific_name, common_name: SPCUR.common_name || '' }); toast('Added to your wishlist'); await route(); });
  },
  async libpre() {
    await guard(async () => { const p = await api('POST', '/api/library/prefetch', { scope: 'texas' }); toast(p.total ? `Downloading ${p.total.toLocaleString()} species in the background` : 'They are all kept already'); await libPrePoll(); });
  },
  async liblists() { await guard(async () => { await api('POST', '/api/library/local'); toast('Fetching the lists again in the background'); await libListsPoll(); }); },
  async libprestop() { await guard(async () => { await api('DELETE', '/api/library/prefetch'); toast('Download stopped'); await libPrePoll(); }); },
  spnew: () => { if (SPCUR) idNewPlant(Object.assign({}, SPCUR, { src: 'the plant library' }), false); },
});
function spFrom(src, i) {
  const list = src === 'library' ? LIB.res : src === 'local' ? ID.shot && ID.shot.result && ID.shot.result.species : ID.shot && ID.shot[src] && ID.shot[src].species;
  const s = list && list[+i];
  return s ? Object.assign({}, s, { src: src === 'library' ? 'the plant library' : src === 'local' ? 'Identify (this computer)' : src === 'plantnet' ? 'Pl@ntNet' : 'Claude' }) : null;
}
Object.assign(acts, {
  idcam: () => idCamToggle(),
  idsnap: () => idSnap(),
  idopen: el => { idStop(); go('#/plant/' + enc(el.dataset.code)); },
  idask: el => idAskOutside(el.dataset.who),
  idnew: el => { const s = spFrom(el.dataset.src, el.dataset.i); if (s) idNewPlant(s, el.dataset.src !== 'library'); },
  idfind: el => { const s = spFrom(el.dataset.src, el.dataset.i); if (!s) return; idStop(); MUFILL = { name: s.common_name || '', scientific_name: s.scientific_name, id_status: 'A guess' }; go('#/fungi/new'); },
  async idkeydel(el) {
    if (!(await confirmBox('Remove the key?', 'The button for this second opinion goes away until a key is saved again.', 'Remove the key', true))) return;
    await guard(async () => { await api('PUT', '/api/identify/settings', { [el.dataset.k]: '' }); toast('Key removed'); route(); });
  },
});
Object.assign(changeActs, { idfile: el => idFile(el) });
Object.assign(formActs, {
  async spnotes(form) {
    if (!SPCUR || !(await needName())) return;
    await guard(async () => { await api('PUT', '/api/library/notes', { name: SPCUR.scientific_name, notes: form.elements.notes.value, tags: form.elements.tags.value }); toast('Notes and tags saved'); await route(); });
  },
  async idkeys(form) {
    const b = {};
    ['plantnet_key', 'claude_key'].forEach(k => { const v = form.elements[k].value.trim(); if (v) b[k] = v; });
    if (!Object.keys(b).length) { toast('Paste a key first.', true); return; }
    await api('PUT', '/api/identify/settings', b); toast('Keys saved'); route();
  },
});
document.addEventListener('visibilitychange', () => { if (document.hidden && ID.stream) { idStop(); idCamUi(false); } });

// ---------- 1.22.0: mushroom finds (#/fungi), a page of their own ----------
// A find is a mushroom (or a cluster) seen anywhere: the yard, a plant pot, a walk. It has photos, where and when, what it grew
// on, what it looks like, and its name with how sure that is. The app never says a mushroom is safe to eat.
const MU = { q: '', id: '', place: '', year: '', status: 'active', list: null, meta: null };
try { const s = JSON.parse(localStorage.getItem('plantdb.fungi') || '{}'); ['q', 'id', 'place', 'year', 'status'].forEach(k => { if (typeof s[k] === 'string') MU[k] = s[k]; }); } catch (e) { /* defaults */ }
const muSave = () => { try { localStorage.setItem('plantdb.fungi', JSON.stringify({ q: MU.q, id: MU.id, place: MU.place, year: MU.year, status: MU.status })); } catch (e) { /* not remembered */ } };
const MU_ID_TAG = { 'Not identified yet': 'Not identified', 'A guess': 'Name is a guess', 'Fairly sure': 'Fairly sure of the name', 'Confirmed by an expert': 'Confirmed name' };
function fungiSafety(short) {
  return html`<aside class="notice bad mu-safe" role="note" aria-label="Safety"><strong>Never eat a wild mushroom because of an app, a photo, or this record.</strong>
    ${short ? html` Deadly mushrooms look like edible ones, and photo IDs are often wrong. <a href="#/fungi/safety">Read more</a>.`
      : html`<ul><li>Deadly species, such as death caps and destroying angels (<i>Amanita</i>), look like common edible ones, and some poisons only show symptoms a day later, when the liver is already damaged.</li>
      <li>Names here come from photos, your notes or Identify. They are leads, not proof. Only an experienced local expert, with the whole mushroom in hand, can confirm one.</li>
      <li><strong>Pets:</strong> dogs often eat mushrooms in yards, and several common lawn species are toxic to them. Pick mushrooms from the yard before letting pets out. If a pet may have eaten one, call your vet or ASPCA Animal Poison Control at (888) 426-4435.</li>
      <li><strong>People:</strong> if someone may have eaten a wild mushroom, call Poison Control at 1-800-222-1222 (or 911 if they are very ill), and keep any leftover pieces.</li>
      <li>Wash your hands after handling wild mushrooms.</li></ul>`}</aside>`;
}
function muYears(list) { return [...new Set(list.map(f => (f.found_on || '').slice(0, 4)).filter(Boolean))].sort().reverse(); }
function muFiltered() {
  const q = MU.q.toLowerCase();
  return (MU.list || []).filter(f => (!MU.id || f.id_status === MU.id) && (!MU.place || f.place_kind === MU.place) && (!MU.year || (f.found_on || '').startsWith(MU.year))
    && (!q || [f.code, f.name, f.scientific_name, f.place, f.near, f.notes, f.cap_colour, f.plant_code].join(' ').toLowerCase().includes(q)));
}
function muCard(f) {
  return html`<article class="sheet mu-card" data-code="${f.code}">
    <div class="mat">${f.photo ? html`<img src="${thumbUrl(f.photo)}" alt="" loading="lazy" decoding="async">` : f.photo_url ? html`<img src="${f.photo_url}" alt="" decoding="async">` : html`<div class="nophoto">No photo yet</div>`}<span class="acc">${f.pending ? 'Not sent yet' : f.code}</span></div>
    <h3 class="name"><a class="sheet-link" href="#/fungi/${enc(f.code)}">${f.name || 'Unnamed mushroom'}</a></h3>
    ${f.scientific_name ? html`<p class="sci latin">${f.scientific_name}</p>` : ''}
    <p class="mu-when">${f.found_on ? longDay(f.found_on) : ''}${f.place_kind ? ' · ' + f.place_kind.replace(/^In (the|a) /, '').replace(/^\w/, c => c.toUpperCase()) : ''}${f.plant_code ? ' ' + f.plant_code : ''}</p>
    <div class="tags"><span class="tag ${f.id_status === 'Confirmed by an expert' ? 'tag-yours' : ''}">${MU_ID_TAG[f.id_status] || f.id_status}</span>${f.status === 'archived' ? html`<span class="tag tag-arch">Archived</span>` : ''}</div>
  </article>`;
}
function muDraw() {
  const box = document.getElementById('mu-grid'); if (!box) return;
  muSave();
  const r = muFiltered();
  document.getElementById('mu-count').textContent = `${r.length} of ${(MU.list || []).length} finds shown`;
  box.innerHTML = rend(r.length ? r.map(muCard) : html`<div class="empty" style="grid-column:1/-1"><p>${(MU.list || []).length ? 'No finds match these filters.' : 'No finds yet. When you spot a mushroom, press "Add a find" and take its photos.'}</p></div>`);
}
async function viewFungi() {
  const d = await api('GET', '/api/fungi?status=' + enc(MU.status));
  MU.list = d.finds; MU.meta = d;
  const sel = (f, opts) => html`<select data-f="${f}">${opts.map(([v, l]) => html`<option value="${v}" ${MU[f.slice(2)] === v ? raw('selected') : ''}>${l}</option>`)}</select>`;
  return {
    title: 'Mushroom finds', after: muDraw,
    html: html`<div class="hero"><div><h1>Mushroom finds</h1>
      <p class="muted">Mushrooms you have spotted in the yard, in your plant pots, or anywhere else, with their photos, where they grew and what they look like.</p></div>
      <a class="btn" href="#/fungi/new">Add a find</a></div>
    ${fungiSafety(true)}
    <div class="filters mu-filters">
      <label>Search<input type="search" data-f="muq" value="${MU.q}" placeholder="Name, place, colour, notes" autocomplete="off"></label>
      <label>Name${sel('muid', [['', 'Any'], ...d.enums.id_status.map(x => [x, x])])}</label>
      <label>Where${sel('muplace', [['', 'Anywhere'], ...d.enums.place_kind.map(x => [x, x])])}</label>
      <label>Year${sel('muyear', [['', 'Any year'], ...muYears(d.finds).map(y => [y, y])])}</label>
      <label>Show${sel('mustatus', [['active', 'Current finds'], ['all', 'Current and archived'], ['archived', 'Archived only']])}</label>
    </div>
    <p id="mu-count" class="muted" aria-live="polite"></p>
    <div class="grid" id="mu-grid"></div>
    <p><a class="btn ghost" href="#/around">Fungi found near home this month</a></p>
    <p class="hint">Look up mushrooms by name in the <a href="#/library?scope=fungi">library</a> (Look in: Fungi worldwide), or take a picture with <a href="#/identify">Identify</a>.</p>`,
  };
}
function viewFungiSafety() {
  return { title: 'Mushroom safety', html: html`<p class="crumb"><a href="#/fungi">Back to the mushroom finds</a></p><h1>Mushroom safety</h1>${fungiSafety(false)}
    <h2>Good habits when you record a find</h2>
    <ul><li>Photograph the cap from above, the underside (gills or pores), the whole stem, and the very base. Dig gently around the base first: a cup or sac there (a volva) is a warning sign of <i>Amanita</i>.</li>
      <li>Note what it grew on, and which trees are near: many mushrooms grow only with certain trees.</li>
      <li>A spore print helps an expert most: put the cap gills-down on half white, half dark paper under a bowl for a few hours, and note the colour.</li>
      <li>Ask for help on iNaturalist or a local mycological society, such as the Texas Mycological Society.</li></ul>` };
}
function muField(meta, f, v, plants) {
  const id = 'mu-' + f.name;
  if (f.name === 'lat' || f.name === 'lon') return '';
  if (f.name === 'plant_code') return html`<label class="f" data-show="pot">${f.label}<select name="plant_code" id="${id}"><option value="">Not in a pot</option>${plants.map(p => html`<option value="${p.code}" ${p.code === v ? raw('selected') : ''}>${p.code} ${p.common_name}</option>`)}</select></label>`;
  if (f.kind === 'enum') return html`<label class="f">${f.label}<select name="${f.name}" id="${id}"><option value="">Not set</option>${meta.enums[f.name].map(o => html`<option ${o === v ? raw('selected') : ''}>${o}</option>`)}</select></label>`;
  if (f.kind === 'long') return html`<label class="f wide">${f.label}<textarea name="${f.name}" id="${id}" rows="4">${v || ''}</textarea></label>`;
  if (f.kind === 'date') return html`<label class="f">${f.label}<input type="date" name="${f.name}" id="${id}" value="${v || todayStr()}" max="${todayStr()}"></label>`;
  const hint = { name: 'A common name, or your own description such as "small brown one by the oak"', cap_size: 'For example 2 inches', spore_print: 'For example white, cream, pink, brown, purple-brown, black' }[f.name];
  return html`<label class="f">${f.label}${hint ? html`<small>${hint}</small>` : ''}<input type="text" name="${f.name}" id="${id}" value="${v || ''}"></label>`;
}
const MU_GROUPS = [['Name', ['name', 'scientific_name', 'id_status']], ['Where and when', ['found_on', 'place_kind', 'plant_code', 'place']],
  ['What it grew on', ['substrate', 'near', 'abundance']], ['What it looks like', ['cap_size', 'cap_colour', 'underside', 'ring', 'volva', 'spore_print', 'bruising', 'smell']], ['Notes', ['notes']]];
let MUFILL = null;            // a new find started from a species page or from Identify
async function viewFindForm(code) {
  const [meta, plants] = await Promise.all([code ? api('GET', '/api/fungi/' + enc(code)) : api('GET', '/api/fungi?status=none'), api('GET', '/api/plants')]);
  MU.meta = meta;
  const F = Object.fromEntries(meta.fields.map(f => [f.name, f])), v = code ? meta : (MUFILL || {});
  return {
    title: code ? 'Edit ' + code : 'Add a mushroom find',
    after: () => muPlaceShow(),
    html: html`<p class="crumb"><a href="${code ? '#/fungi/' + enc(code) : '#/fungi'}">${code ? 'Back to ' + code : 'Back to the mushroom finds'}</a></p>
    <h1>${code ? 'Edit ' + code : 'Add a mushroom find'}</h1>
    ${code ? '' : html`<p class="muted">Only the photos and where you found it really matter now; fill in the rest any time.</p>`}
    <form data-form="musave" ${code ? raw(`data-code="${esc(code)}" data-ver="${meta.version}"`) : ''} autocomplete="off">
      ${code ? '' : html`<fieldset><legend>Photos</legend><label class="f">Photos of the cap, the underside, the stem and the base<small>On a phone this can open the camera. If the photos carry their location, it is offered for the find.</small>
        <input type="file" name="photos" accept="image/*" multiple capture="environment"></label></fieldset>`}
      ${MU_GROUPS.map(([t, names]) => html`<fieldset><legend>${t}</legend><div class="field-grid">${names.map(n => muField(meta, F[n], v[n], plants))}</div>
        ${t === 'Where and when' ? html`<div class="mu-loc"><input type="hidden" name="lat" value="${v.lat == null ? '' : v.lat}"><input type="hidden" name="lon" value="${v.lon == null ? '' : v.lon}">
          <p id="mu-loc-txt" aria-live="polite">${v.lat != null ? html`Location saved: ${(+v.lat).toFixed(5)}, ${(+v.lon).toFixed(5)}.` : 'No map location saved.'}</p>
          <div class="row"><button class="btn ghost small" type="button" data-act="muhere">Use my location now</button><button class="btn ghost small" type="button" data-act="muclearloc">Clear the location</button></div>
          <p class="hint">Saved locations are seen by everyone you have given access to the app.</p></div>` : ''}</fieldset>`)}
      <div id="form-err"></div>
      <div class="sticky-save"><button class="btn" type="submit">${code ? 'Save changes' : 'Add this find'}</button><a class="btn ghost" href="${code ? '#/fungi/' + enc(code) : '#/fungi'}">Cancel</a></div>
    </form>`,
  };
}
function muPlaceShow() {
  const s = document.getElementById('mu-place_kind'), pot = document.querySelector('[data-show=pot]');
  if (s && pot) pot.hidden = s.value !== 'In a plant pot';
}
async function viewFind(code) {
  const f = await api('GET', '/api/fungi/' + enc(code));
  MUCUR = f;
  const ph = f.photos, gps = ph.find(p => p.gps_lat != null);
  const show = n => f[n] != null && f[n] !== '';
  const dl = names => names.filter(show).map(n => html`<dt>${f.fields.find(x => x.name === n).label}</dt><dd>${n === 'plant_code' && f.plant ? html`<a href="#/plant/${enc(f.plant_code)}">${f.plant_code} ${f.plant.common_name}</a>` : n === 'found_on' ? longDay(f[n]) : f[n]}</dd>`);
  return {
    title: (f.name || 'Unnamed mushroom') + ' (' + f.code + ')',
    after: () => muGallery(0),
    html: html`<div class="species mu-find"><p class="crumb"><a href="#/fungi">All mushroom finds</a></p>
    <header class="sp-head"><h1>${f.name || 'Unnamed mushroom'}</h1>
      ${f.scientific_name ? html`<p class="sp-sci latin">${f.scientific_name}${f.id_status !== 'Not identified yet' ? html` <a href="#/species/${enc(f.scientific_name)}">(in the library)</a>` : ''}</p>` : ''}
      <p class="muted"><strong>${f.code}</strong> · found ${longDay(f.found_on)} · page version ${f.version}</p>
      <div class="tags"><span class="tag ${f.id_status === 'Confirmed by an expert' ? 'tag-yours' : ''}">${MU_ID_TAG[f.id_status] || f.id_status}</span>${f.status === 'archived' ? html`<span class="tag tag-arch">Archived</span>` : ''}</div></header>
    ${fungiSafety(true)}
    <div class="sp-grid">
      <section aria-labelledby="mu-ph-h"><h2 id="mu-ph-h">Photos</h2><div id="mu-gallery"></div>
        <label class="f noprint mu-add">Add photos<small>On a phone this can open the camera.</small><input type="file" accept="image/*" multiple capture="environment" data-act="muaddphotos"></label></section>
      <section aria-labelledby="mu-id-h"><h2 id="mu-id-h">What could it be?</h2>
        <p>Identify compares a photo with about 49,000 fungi, on this computer. Treat its answer as a lead to check, never as proof.</p>
        <div class="row"><button class="btn" type="button" data-act="muident" ${ph.length ? '' : raw('disabled')}>Identify the photo shown</button></div>
        <div id="mu-ident" aria-live="polite"></div></section>
    </div>
    <section aria-labelledby="mu-where-h"><h2 id="mu-where-h">Where and when</h2><dl class="dl">${dl(['found_on', 'place_kind', 'plant_code', 'place'])}
      ${f.lat != null ? html`<dt>Map location</dt><dd>${(+f.lat).toFixed(5)}, ${(+f.lon).toFixed(5)} (<a href="https://www.openstreetmap.org/?mlat=${f.lat}&mlon=${f.lon}#map=18/${f.lat}/${f.lon}" target="_blank" rel="noopener noreferrer">open the map</a>)</dd>` : ''}</dl>
      ${f.lat == null && gps ? html`<p><button class="btn ghost" type="button" data-act="mugps" data-lat="${gps.gps_lat}" data-lon="${gps.gps_lon}">Save the location from the photo (${(+gps.gps_lat).toFixed(4)}, ${(+gps.gps_lon).toFixed(4)})</button></p>` : ''}</section>
    <section aria-labelledby="mu-grew-h"><h2 id="mu-grew-h">What it grew on</h2>${['substrate', 'near', 'abundance'].some(show) ? html`<dl class="dl">${dl(['substrate', 'near', 'abundance'])}</dl>` : html`<p class="muted">Not noted yet.</p>`}</section>
    <section aria-labelledby="mu-look-h"><h2 id="mu-look-h">What it looks like</h2>${['cap_size', 'cap_colour', 'underside', 'ring', 'volva', 'spore_print', 'bruising', 'smell'].some(show) ? html`<dl class="dl">${dl(['cap_size', 'cap_colour', 'underside', 'ring', 'volva', 'spore_print', 'bruising', 'smell'])}</dl>` : html`<p class="muted">Not noted yet. Edit the find to add the cap, the underside, the ring, the base and the spore print.</p>`}</section>
    ${show('notes') ? html`<section aria-labelledby="mu-notes-h"><h2 id="mu-notes-h">Notes</h2><p class="pl">${f.notes}</p></section>` : ''}
    <div class="row noprint mu-acts"><a class="btn" href="#/fungi/${enc(f.code)}/edit">Edit this find</a>
      <button class="btn ghost" type="button" data-act="muarch" data-to="${f.status === 'archived' ? '0' : '1'}">${f.status === 'archived' ? 'Bring it back' : 'Archive this find'}</button></div>
    <p class="hint">Added by ${f.created_by} on ${when(f.created_at)}${f.updated_at && f.updated_at !== f.created_at ? `; last changed by ${f.updated_by} on ${when(f.updated_at)}` : ''}. Changes are listed in the Audit log under "Mushroom finds".</p></div>`,
  };
}
let MUCUR = null, MUPIX = 0;
function muGallery(i) {
  const box = document.getElementById('mu-gallery'); if (!box || !MUCUR) return;
  const ph = MUCUR.photos;
  if (!ph.length) { box.innerHTML = rend(html`<p class="muted">No photos yet. Add them below.</p>`); return; }
  MUPIX = ((i % ph.length) + ph.length) % ph.length;
  const p = ph[MUPIX];
  box.innerHTML = rend(html`<figure class="sp-fig"><img src="${p.url || photoUrl(p.file)}" alt="${p.caption || 'Photo ' + (MUPIX + 1) + ' of ' + MUCUR.code}">
    <figcaption>${p.caption || 'No caption'}${p.taken_at ? `. Taken ${when(p.taken_at)}` : ''}${p.gps_lat != null ? '. Has a location.' : ''}${p.is_primary ? html` <strong>★ Main photo</strong>` : ''}</figcaption></figure>
    ${ph.length > 1 ? html`<div class="row sp-step"><button class="btn ghost small" type="button" data-act="mustep" data-d="-1">‹ Previous photo</button><span class="muted">${MUPIX + 1} of ${ph.length}</span><button class="btn ghost small" type="button" data-act="mustep" data-d="1">Next photo ›</button></div>` : ''}
    ${MUCUR.pending ? html`<p class="hint">Captions and the main photo can be changed once the find is sent.</p>` : html`<div class="row noprint">${!p.is_primary ? html`<button class="btn ghost small" type="button" data-act="mumain">Make this the main photo</button>` : ''}
      <button class="btn ghost small" type="button" data-act="mucap">Edit caption</button><button class="btn danger small" type="button" data-act="murmphoto">Remove photo</button></div>`}`);
}
async function muReload(i) { MUCUR = await api('GET', '/api/fungi/' + enc(MUCUR.code)); await route(); muGallery(i == null ? MUPIX : i); }
function muSetLoc(lat, lon, how) {
  const f = document.querySelector('form[data-form=musave]'); if (!f) return;
  f.elements.lat.value = lat == null ? '' : lat; f.elements.lon.value = lon == null ? '' : lon;
  document.getElementById('mu-loc-txt').textContent = lat == null ? 'No map location saved.' : `Location ${how}: ${(+lat).toFixed(5)}, ${(+lon).toFixed(5)}. It is saved with the find.`;
}
Object.assign(acts, {
  muhere: () => {
    if (!navigator.geolocation) { toast('This browser cannot give a location.', true); return; }
    document.getElementById('mu-loc-txt').textContent = 'Finding your location…';
    navigator.geolocation.getCurrentPosition(p => muSetLoc(p.coords.latitude.toFixed(6), p.coords.longitude.toFixed(6), 'from this device'),
      e => { document.getElementById('mu-loc-txt').textContent = e.code === 1 ? 'Location was not allowed. Allow it in the browser\'s site settings, or leave it empty.' : 'Could not get the location: ' + e.message; },
      { enableHighAccuracy: true, timeout: 20000 });
  },
  muclearloc: () => muSetLoc(null, null),
  mustep: el => { muGallery(MUPIX + +el.dataset.d); const b = document.querySelector(`[data-act=mustep][data-d="${el.dataset.d}"]`); if (b) b.focus(); },
  async mumain() { if (!(await needName())) return; await guard(async () => { await api('PATCH', '/api/fungi/photos/' + MUCUR.photos[MUPIX].id, { is_primary: true }); toast('Main photo changed'); await muReload(0); }); },
  async mucap() {
    if (!(await needName())) return;
    const p = MUCUR.photos[MUPIX];
    const r = await modal(html`<form method="dialog"><h2>Edit caption</h2><label class="f">Caption<input type="text" name="c" maxlength="200" value="${p.caption}" placeholder="For example: underside, gills"></label>
      <div class="row"><button class="btn" value="ok">Save caption</button><button class="btn ghost" value="cancel">Cancel</button></div></form>`);
    if (r !== 'ok') return;
    await guard(async () => { await api('PATCH', '/api/fungi/photos/' + p.id, { caption: dlg.querySelector('[name=c]').value }); toast('Caption saved'); await muReload(); });
  },
  async murmphoto() {
    if (!(await needName())) return;
    if (!(await confirmBox('Remove this photo?', 'It leaves the find. The file is kept in the photos_deleted folder.', 'Remove photo', true))) return;
    await guard(async () => { await api('DELETE', '/api/fungi/photos/' + MUCUR.photos[MUPIX].id); toast('Photo removed'); await muReload(0); });
  },
  async mugps(el) {
    if (!(await needName())) return;
    await guard(async () => { await api('PUT', '/api/fungi/' + enc(MUCUR.code), { base_version: MUCUR.version, fields: { lat: el.dataset.lat, lon: el.dataset.lon } }); toast('Location saved'); await muReload(); });
  },
  async muarch(el) {
    if (!(await needName())) return;
    await guard(async () => { await api('POST', '/api/fungi/' + enc(MUCUR.code) + '/status', { archived: el.dataset.to === '1' }); toast(el.dataset.to === '1' ? 'Archived' : 'Brought back'); await muReload(); });
  },
  async muident() {
    const p = MUCUR.photos[MUPIX], box = document.getElementById('mu-ident'); if (!p) return;
    box.innerHTML = rend(html`<p role="status">Checking the photo…</p>`);
    try {
      const blob = await (await fetch(p.url || photoUrl(p.file))).blob(), fd = new FormData(); fd.append('image', blob, 'find.jpg');
      const r = await api('POST', '/api/identify?scope=fungi', undefined, fd);
      MUIDENT = r.species || [];
      box.innerHTML = rend(html`<h3>It looks most like</h3>${r.genera && r.genera[0] ? html`<p>Most likely genus: <i>${r.genera[0].genus}</i> (${pct(r.genera[0].probability)}).</p>` : ''}
        <ol class="id-sps">${MUIDENT.map((s, i) => html`<li class="id-sp"><div><i class="sci">${s.scientific_name}</i>${s.common_name ? html` <span>${s.common_name}</span>` : ''} <b class="id-p">${pct(s.probability)}</b></div>
          <div class="muted">${s.family}</div><div class="id-acts"><a href="#/species/${enc(s.scientific_name)}">Open in the library</a>${canChange() ? html`<button class="btn small ghost" type="button" data-act="muusename" data-i="${i}">Use this name (as a guess)</button>` : ''}</div></li>`)}</ol>
        <p class="hint">Checked in ${r.seconds} seconds on this computer. A second opinion from Pl@ntNet or Claude is on the Identify page.</p>`);
    } catch (e) { box.innerHTML = rend(html`<div class="notice bad" role="alert">${e.message}</div>`); }
  },
  async muusename(el) {
    const s = MUIDENT[+el.dataset.i]; if (!s || !(await needName())) return;
    await guard(async () => { await api('PUT', '/api/fungi/' + enc(MUCUR.code), { base_version: MUCUR.version, fields: { name: MUCUR.name || s.common_name || s.scientific_name, scientific_name: s.scientific_name, id_status: 'A guess' } }); toast('Name saved as a guess'); await muReload(); });
  },
  munewfrom: () => { if (!SPCUR) return; MUFILL = { name: SPCUR.common_name || '', scientific_name: SPCUR.scientific_name, id_status: 'A guess' }; go('#/fungi/new'); },
});
let MUIDENT = [];
Object.assign(changeActs, {
  async muaddphotos(el) {
    const files = [...el.files]; el.value = ''; if (!files.length || !(await needName())) return;
    const fd = new FormData(); files.forEach(f => fd.append('files', f));
    await guard(async () => { const r = await api('POST', '/api/fungi/' + enc(MUCUR.code) + '/photos', undefined, fd); toast(`${files.length} photo${files.length === 1 ? '' : 's'} added`); MUCUR = r; await route(); muGallery(r.photos.length - 1); });
  },
});
Object.assign(formActs, {
  async musave(form) {
    if (!(await needName())) return;
    const fields = {};
    for (const f of (MU.meta ? MU.meta.fields : [])) if (form.elements[f.name]) fields[f.name] = form.elements[f.name].value;
    if (!fields.place_kind || fields.place_kind !== 'In a plant pot') fields.plant_code = '';
    const err = document.getElementById('form-err'); err.innerHTML = '';
    try {
      let code = form.dataset.code;
      if (code) await api('PUT', '/api/fungi/' + enc(code), { base_version: +form.dataset.ver, fields });
      else {
        const r = await api('POST', '/api/fungi', { fields }); code = r.code;
        const files = form.elements.photos ? [...form.elements.photos.files] : [];
        if (files.length) {
          const fd = new FormData(); files.forEach(f => fd.append('files', f));
          const p = await api('POST', '/api/fungi/' + enc(code) + '/photos', undefined, fd);
          if (p.located && fields.lat === '') toast('The location from the photo was saved with the find.');
        }
        MUFILL = null;
      }
      toast(form.dataset.code ? 'Saved' : /^NEW-/.test(code) ? 'Find added' : 'Find ' + code + ' added'); go('#/fungi/' + enc(code));
    } catch (e) { err.innerHTML = rend(html`<div class="notice bad" role="alert"><strong>Not saved.</strong> ${e.message}</div>`); err.scrollIntoView({ block: 'center' }); }
  },
});

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
      <label class="chk"><input type="checkbox" data-f="offkeeplib" ${keeplib ? raw('checked') : ''}>Also keep the library's Texas plant list with its photos (about 300 MB, once the owner has downloaded those photos)</label></div>
      <p>${dl ? `Last saved ${when(dl)}.` : 'Not saved on this device yet.'} ${keep ? 'It is saved again by itself when it is a few hours old and the device is online.' : ''}</p>
      <p id="off-dl" role="status" aria-live="polite"></p>
      ${keep ? html`<p class="row"><button class="btn" type="button" data-act="offdl" ${navigator.onLine ? '' : raw('disabled')}>Save it again now</button></p>` : ''}
      ${est ? html`<p class="hint">This device is using ${mb(est.usage || 0)} for the plant record${est.quota ? `, of the ${mb(est.quota)} the browser allows` : ''}.${persisted === false ? ' The browser may clear it if the device runs short of space.' : persisted ? ' The browser has agreed to keep it.' : ''}</p>` : ''}
      <p class="hint">${ios ? html`On an iPhone or iPad, add the plant record to the Home Screen (Share, then <strong>Add to Home Screen</strong>) and open it from there: Safari clears saved copies of sites that are not on the Home Screen after a few weeks.`
        : html`On Android, choose <strong>Install app</strong> (or <strong>Add to Home screen</strong>) in the browser's menu, and open it from there.`} Open it once while online after each update, so the new version is saved too.</p>
      <label class="f">This device's name<small>Shown in the Audit log and on decisions, so you know where a change came from</small><input type="text" data-f="offdev" value="${offDevice()}" maxlength="40" autocomplete="off"></label>
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
          <button class="btn ghost small" type="button" data-act="offidrm" data-id="${x.id}">Remove</button></li>`)}</ul>` : html`<p class="muted">None. Pictures taken for Identify without a connection wait here and are checked when you're back online.</p>`}
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
  const page = (location.hash.replace(/^#\/?/, '').split('/')[0]) || '';
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

// ---------- prototype proto/care-card: links to the large-print care cards (card.html), added when a plant or group page draws ----------
(function careCardLinks() {
  const main = document.getElementById('app'); if (!main) return;
  const add = () => {
    const h = location.hash;
    let m = h.match(/^#\/plant\/([^/]+)$/), row, href, label;
    if (m) { row = main.querySelector('#details .row.acts') || main.querySelector('.row.acts'); href = '/card.html?plant=' + m[1]; label = 'Large-print care card'; }
    else if ((m = h.match(/^#\/group\/(\d+)$/)) && main.querySelector('#g-plants li.job')) { row = main.querySelector('h1 ~ .row.noprint'); href = '/card.html?group=' + m[1]; label = 'Large-print care cards'; }
    if (!row || row.querySelector('.pc-link')) return;
    const a = document.createElement('a');
    a.className = 'btn ghost pc-link'; a.href = href; a.textContent = label;
    a.title = 'Water, light and temperature needs in big type, to print and keep beside the plants';
    row.insertBefore(a, row.querySelector('[data-act=archive],[data-act=grpdel]'));   // before Archive / Remove this group, or at the end
  };
  new MutationObserver(add).observe(main, { childList: true, subtree: true });
})();

route();
offStart();
wxPoll();                      // shows the progress box on every page while a history load runs
})();
