/* Plant record front end: helpers, state, the api() call with its saved answers and fetching ahead, the Home button, people, toasts and dialogs, the router, the section menu. One of the files app.js was split into in 1.32.0; they load in order (index.html) and share one scope,
   so a function here may call any other. Plain JavaScript, no inline handlers (the server's content policy forbids them). */
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
// 1.47.0: notes written in °F ("keep warm (70 to 80°F)") read in the person's unit; the stored text is untouched
const tText = s => unitsGet().temp === 'c' ? String(s).replace(/(-?\d+(?:\.\d+)?) (and|to|or) (-?\d+(?:\.\d+)?)\s?°F/g, (m, a, w, b) => `${tF(+a, false)} ${w} ${tF(+b)}`).replace(/(-?\d+(?:\.\d+)?)\s?°F/g, (m, n) => tF(+n)) : s;
function linkify(text) {
  const t = tText(String(text == null ? '' : text));        // 1.47.0: free text written in °F reads in the person's unit
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
// ---------- units (1.47.0, PLAN.md step 4a) ----------
// Everything is stored and sent in °F and inches (the weather, every plant's temperatures, pot sizes, rain). What a person sees is
// in their own units: a region sets all of them at once, and each can then be changed by hand. Kept in localStorage 'plantdb.units'
// and sent to the server with the other settings that follow you (prefs.js KEYS), so it holds on every device and in push messages.
const UNIT_REGIONS = { us: { temp: 'f', len: 'in', rain: 'in' }, ca: { temp: 'c', len: 'in', rain: 'mm' }, metric: { temp: 'c', len: 'cm', rain: 'mm' } };
const UNIT_WORDS = { region: { us: 'United States (°F, inches)', ca: 'Canada (°C, inches, mm of rain)', metric: 'Everywhere else (°C, cm, mm)' },
  temp: { f: 'Fahrenheit (°F)', c: 'Celsius (°C)' }, len: { in: 'Inches', cm: 'Centimetres' }, rain: { in: 'Inches', mm: 'Millimetres' } };
function unitsRaw() { try { return JSON.parse(localStorage.getItem('plantdb.units') || '{}') || {}; } catch (e) { return {}; } }
function unitsGet() {
  const u = unitsRaw();
  const site = (typeof META !== 'undefined' && META && META.place && META.place.units) || 'us';      // 1.48.0: no choice of your own: the site's default
  const region = UNIT_REGIONS[u.region] ? u.region : (UNIT_REGIONS[site] ? site : 'us'), base = UNIT_REGIONS[region];
  return { region, own: !!UNIT_REGIONS[u.region], temp: u.temp || base.temp, len: u.len || base.len, rain: u.rain || base.rain };
}
function unitsSet(changes) {              // {region} resets the three; {temp|len|rain} overrides one
  const u = unitsRaw();
  if ('region' in changes) { for (const k of ['region', 'temp', 'len', 'rain']) delete u[k]; if (UNIT_REGIONS[changes.region]) u.region = changes.region; }   // 1.48.0: 'us' is kept too, since the site's default may be metric
  const base = UNIT_REGIONS[u.region] || UNIT_REGIONS[unitsGet().region] || UNIT_REGIONS.us;
  for (const k of ['temp', 'len', 'rain']) if (k in changes && changes[k]) { if (changes[k] === base[k]) delete u[k]; else u[k] = changes[k]; }
  try { if (Object.keys(u).length) localStorage.setItem('plantdb.units', JSON.stringify(u)); else localStorage.removeItem('plantdb.units'); } catch (e) { /* this visit only */ }
  document.dispatchEvent(new Event('units'));
  return u;
}
const tU = () => unitsGet().temp === 'c' ? '°C' : '°F';                                    // the temperature unit's sign
const tNum = (f, dp) => {                                                                 // a °F value as a number in the person's unit
  if (f == null || f === '' || isNaN(+f)) return f;
  if (unitsGet().temp !== 'c') return +f;
  const c = (+f - 32) * 5 / 9; return dp != null ? +c.toFixed(dp) : Number.isInteger(+f) ? Math.round(c) : +c.toFixed(1);
};
const tF = (f, unit = true) => (f == null || f === '' || isNaN(+f)) ? (f == null || f === '' ? '' : String(f)) : String(tNum(f)) + (unit ? tU() : '');
const tD = (df, unit = true) => {                                                         // a difference in °F (3°F warmer): no offset
  if (df == null || df === '' || isNaN(+df)) return '';
  const v = unitsGet().temp === 'c' ? +(+df * 5 / 9).toFixed(Number.isInteger(+df) && +df % 9 === 0 ? 0 : 1) : +(+df).toFixed(1);
  return String(v) + (unit ? tU() : '');
};
const tIn = v => (v == null || v === '' || isNaN(+v)) ? v : unitsGet().temp === 'c' ? r1(+v * 9 / 5 + 32) : +v;   // a value typed in the person's unit, back to °F
const lenU = () => unitsGet().len === 'cm' ? 'cm' : 'in';
const lenF = (inches, unit = true) => {                                                    // inches to the person's length unit ("6 in" / "15 cm")
  if (inches == null || inches === '' || isNaN(+inches)) return inches == null ? '' : String(inches);
  const v = unitsGet().len === 'cm' ? (+inches * 2.54 < 3 ? r1(+inches * 2.54) : Math.round(+inches * 2.54)) : +inches;
  return String(v) + (unit ? ' ' + lenU() : '');
};
const lenIn = v => (v == null || v === '' || isNaN(+v)) ? v : unitsGet().len === 'cm' ? r1(+v / 2.54) : +v;        // a length typed in the person's unit, back to inches
const areaF = (sqft, unit = true) => {                                                     // square feet to the person's unit ("12 sq ft" / "1.1 m²")
  if (sqft == null || sqft === '' || isNaN(+sqft)) return sqft == null ? '' : String(sqft);
  const m = unitsGet().len === 'cm'; const v = m ? r1(+sqft * 0.0929) : r1(+sqft);
  return String(v) + (unit ? (m ? ' m²' : ' sq ft') : '');
};
const rainU = () => unitsGet().rain === 'mm' ? 'mm' : 'in';
const rainF = (inches, unit = true) => {                                                   // inches of rain or water to the person's unit
  if (inches == null || inches === '' || isNaN(+inches)) return inches == null ? '' : String(inches);
  const v = unitsGet().rain === 'mm' ? (+inches * 25.4 < 1 ? r1(+inches * 25.4) : Math.round(+inches * 25.4)) : +(+inches).toFixed(2);
  return String(v) + (unit ? ' ' + rainU() : '');
};
const deg = n => (n == null || n === '') ? 'not set' : tF(n);
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
  if (el) {
    el.textContent = viaTS() ? 'Signed in as ' + n : n ? 'Editing as ' + n : 'Set your name';
    el.parentNode.setAttribute('aria-label', el.textContent + (viaTS() ? '. People and your name' : '. Change who is editing'));      // 1.58.0: the spoken name starts with the words shown
  }
  document.documentElement.dataset.role = ME().role;
  topSoon();
}
let TOPRAF = 0;                  // 1.26.1: the name and the place change the width of their buttons, so the top bar is fitted again
function topSoon() { cancelAnimationFrame(TOPRAF); TOPRAF = requestAnimationFrame(() => navLayout()); }

// ---------- api ----------
// the place this browser uses for weather, frost, watering and "today" (1.11.0); null = the home place
let PLACE = null;
try { PLACE = localStorage.getItem('plantdb.place') || null; } catch (e) { /* ignore */ }
// ---------- 1.30.0: quicker page changes ----------
// QC keeps the last answer to each GET in memory. While a page is being drawn (QUICK set by route), an answer seen in the last
// 15 minutes is used at once, and route() then asks again quietly and redraws if anything changed. Any change made (a POST, PUT
// or DELETE) empties it. PF remembers which answers each page needs, so hovering a link, or a quiet moment, can fetch them ahead.
const QC = new Map(), QC_MAX = 120, QC_AGE = 15 * 60000;
let QUICK = null, TIMING = null, QGEN = 0;     // QGEN goes up with every change made, so an answer asked for before it is not kept
const qcKey = url => url + '|' + (PLACE || '');
const qcCopy = d => (typeof structuredClone === 'function' ? structuredClone(d) : JSON.parse(JSON.stringify(d)));
const QC_SKIP = /^\/api\/(wishlist\/check|shops\/check|weather\/job|lib\/.*job|audit\/recent|me\b|conflicts|backups\/job)|[?&]_=/;
function qcPut(url, data) {
  if (QC_SKIP.test(url)) return;
  const k = qcKey(url); QC.delete(k); QC.set(k, { data: qcCopy(data), at: Date.now() });
  while (QC.size > QC_MAX) QC.delete(QC.keys().next().value);
}
const PFLY = new Map();              // answers being fetched ahead right now, so a page waits for those rather than asking twice
async function api(method, url, body, form) {
  if (method === 'GET' && !QC_SKIP.test(url)) {
    const k = qcKey(url), hit = QC.get(k);
    if (QUICK) QUICK.used.push(url);
    if (QUICK && hit && Date.now() - hit.at < QC_AGE) {
      QUICK.stale.push(url); if (TIMING) TIMING.calls.push({ url, ms: 0, saved: true });
      return qcCopy(hit.data);
    }
    if (PFLY.has(k)) { const gen = QGEN; try { const d = await PFLY.get(k); if (d !== undefined && gen === QGEN) return qcCopy(d); } catch (e) { /* ask again below */ } }
  }
  if (method !== 'GET') { QGEN++; QC.clear(); PFLY.clear(); }
  const t0 = performance.now(), m = {}, gen = QGEN, d = await apiNet(method, url, body, form, m);
  if (method === 'GET') { if (gen === QGEN) qcPut(url, d); if (TIMING) TIMING.calls.push({ url, ms: Math.round(performance.now() - t0), server: m.took }); }
  else { QGEN++; QC.clear(); PFLY.clear(); }
  return d;
}
// 1.56.5: after an update the server answers with its new version. The page reloads once by itself, so the new version is all there
// (it took two or three reloads by hand). With a box being typed in or a window open it asks instead, so nothing typed is lost.
const PAGE_VERSION = (document.querySelector('meta[name=app-version]') || {}).content || '';
function newerApp(v) {
  if (!v || !PAGE_VERSION || v === PAGE_VERSION || newerApp.seen === v) return;
  newerApp.seen = v;
  let again = false; try { again = sessionStorage.getItem('plantdb.reloadedFor') === v; } catch (e) { /* no storage: ask */ }
  const a = document.activeElement, busy = !!document.querySelector('dialog[open]') || !!(a && a.matches && a.matches('input:not([type=checkbox]):not([type=radio]),textarea,select,[contenteditable]'));
  if (!again && !busy) {
    try { sessionStorage.setItem('plantdb.reloadedFor', v); } catch (e) { /* reload anyway */ }
    toast(`Version ${v} is installed. Opening it now.`);
    setTimeout(() => location.reload(), 1200);
    return;
  }
  document.querySelectorAll('.nv-bar').forEach(x => x.remove());
  document.body.insertAdjacentHTML('afterbegin', rend(html`<div class="notice nv-bar noprint" role="status"><span>Version ${v} is installed. Reload to use it${busy ? ' (finish what you are typing first)' : ''}.</span>
    <button class="btn small" type="button" data-act="reloadnow">Reload now</button></div>`));
}

// 1.56.5: what a viewer may still send, from the server's own lists (the page kept its own copy, which missed "Got it" on What's new)
function viewerMay(url) {
  const path = url.split('?')[0], ok = ME().viewer_ok || { posts: ['/api/identify', '/api/me/prefs', '/api/voice', '/api/whatsnew/seen'], prefixes: ['/api/push/'] };
  return path === '/api/me' || ok.posts.includes(path) || ok.prefixes.some(p => path.startsWith(p));
}
async function apiNet(method, url, body, form, m) {     // m.took: how long the server said it took to make the answer (ms)
  if (method === 'GET' && /^\/api\/fungi\/NEW-/i.test(url)) {        // 1.24.0: a find made offline that is not sent yet
    const f = await idbGet('finds', decodeURIComponent(url.split('/')[3].split('?')[0]));
    if (!f) { const e = new Error('That find was sent to the plant record. Open the Mushrooms page to see it with its new code.'); e.status = 404; throw e; }
    return offFindDict(f);
  }
  const opts = { method, headers: {} };
  if (PLACE) opts.headers['X-Place'] = PLACE;
  if (method !== 'GET') opts.headers['X-Editor'] = cleanName(viaTS() ? ME().name : getName()) || 'Unknown';
  if (method !== 'GET' && ME().role === 'viewer' && !viewerMay(url)) {      // the server refuses these too; this just says so sooner
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
  if (!r.headers.get('X-Offline-Saved')) newerApp(r.headers.get('X-App-Version'));
  if (m) m.took = +r.headers.get('X-Took-Ms') || null;
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

// 1.57.0: a new page puts the focus on its title, so a screen reader says which page opened (it went to the whole page area)
function focusTitle(app) {
  const h = app.querySelector('h1');
  if (!h) { app.focus({ preventScroll: true }); return; }
  if (!h.hasAttribute('tabindex')) h.setAttribute('tabindex', '-1');
  h.focus({ preventScroll: true });
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
  const home = META.place.is_home || META.place.plants_here;                 // 1.29.0: "Home: Round Rock, TX"
  const l = document.querySelector('#place-btn .pl-l'); if (l) l.textContent = home ? 'Home:' : 'Place:';
  const b = document.getElementById('place-btn');
  if (b) b.setAttribute('aria-label', `${home ? 'Home' : 'Place'}: ${META.place.name}${META.place.is_home ? ' (main home)' : ''}. Choose another home or place`);
  topSoon();
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
// 1.29.0: Rooms and spots: each home's areas outside and rooms inside, and the spots in them, all editable on the page
async function viewWhere() {
  const d = await api('GET', '/api/where'); let S = { items: [] }; try { S = await api('GET', '/api/where/sort'); } catch (e) { /* none */ }
  if (META) META.where = d.homes;
  WHAREAS = d.homes.flatMap(h => h.areas);                     // 1.56.3: the spots each area offers in Plants without a spot
  const can = canChange(), multi = d.homes.length > 1;
  const areaHtml = a => html`<li class="wh-area" data-aid="${a.id}">
    <div class="wh-row"><label class="f wh-name">${a.side === 'out' ? 'Area' : 'Room'}<input type="text" maxlength="60" value="${a.name}" data-ed="area" data-id="${a.id}" data-k="name" ${can ? '' : raw('readonly')}></label>
      <label class="chk"><input type="checkbox" data-ed="area" data-id="${a.id}" data-k="sheltered" ${a.sheltered ? raw('checked') : ''} ${can ? '' : raw('disabled')}>${a.side === 'out' ? 'Roof overhead (like a covered porch)' : 'Heated (not a garage or shed)'}</label>
      <span class="muted">${a.plants} plant${a.plants === 1 ? '' : 's'}${a.lights ? `, ${a.lights} light spot${a.lights === 1 ? '' : 's'}` : ''}. Counts as: ${a.site}.</span>
      ${can ? html`<button class="btn small ghost wh-del" type="button" data-act="whareadel" data-id="${a.id}" data-name="${a.name}">Remove ${a.name}</button>` : ''}</div>
    <ul class="wh-spots">${a.spots.map(sp => html`<li><label class="f">Spot<input type="text" maxlength="60" value="${sp.name}" data-ed="spot" data-id="${sp.id}" data-k="name" ${can ? '' : raw('readonly')}></label>
      <span class="muted">${sp.plants} plant${sp.plants === 1 ? '' : 's'}${sp.sheet ? `. ${sp.sheet[0].toUpperCase() + sp.sheet.slice(1)}.` : ''}</span>
      <button class="btn small ghost" type="button" data-act="ltplace" data-id="${sp.id}" aria-label="Measurements and photos of ${sp.name}">Measurements and photos</button>${can ? html`<button class="btn small ghost" type="button" data-act="whspotdel" data-id="${sp.id}" data-name="${sp.name}" aria-label="Remove the spot ${sp.name}">Remove</button>` : ''}</li>`)}
      ${can ? html`<li><form class="row wh-add" data-form="whspotadd" data-aid="${a.id}"><label class="f">New spot in ${a.name}<input type="text" name="name" maxlength="60" placeholder="${a.side === 'out' ? 'Pallet shelf' : 'Brown hutch'}"></label><button class="btn small" type="submit">Add spot</button></form></li>` : ''}</ul></li>`;
  const sideHtml = (h, side) => html`<section class="blk wh-side"><h3>${side === 'out' ? 'Outside' : 'Inside'}</h3><ul class="wh-areas">${h.areas.filter(a => a.side === side).map(areaHtml)}</ul>
    ${can ? html`<form class="row wh-add" data-form="whareaadd" data-home="${h.home.is_home ? '' : h.home.id}" data-side="${side}"><label class="f">New ${side === 'out' ? 'area outside' : 'room inside'}<input type="text" name="name" maxlength="60" placeholder="${side === 'out' ? 'Patio' : 'Dining room'}"></label>
      <label class="chk"><input type="checkbox" name="sheltered" ${side === 'in' ? raw('checked') : ''}>${side === 'out' ? 'Roof overhead' : 'Heated'}</label><button class="btn small" type="submit">Add ${side === 'out' ? 'area' : 'room'}</button></form>` : ''}</section>`;
  return { title: 'Rooms and spots', html: html`<h1>Rooms and spots</h1>
    <p>Where plants go at each home: outside or inside, then the area or room, then the spot in it. Choose them on each plant's page. Rename anything here by typing over it; it saves when you leave the box. A room or shelf for grow lights is chosen from the same list.</p>
    <p class="hint">"Roof overhead" and "Heated" decide how frost warnings and watering treat the plants there: outside with a roof counts as a covered porch, and inside without heat counts as a garage or shed.</p>
    ${S.items.length && can ? html`<section class="blk" id="wh-sort"><h2 tabindex="-1">Plants without a spot (${S.items.reduce((n, it) => n + it.plants.length, 0)})</h2>
      <p>These plants are not on a spot from your list yet. For each group, choose the area and one of its spots, or <strong>A new spot</strong> and its name, then press <strong>Put in this spot</strong>. Untick a plant to leave it for later. <strong>Put them all in their spots</strong> at the bottom does every group at once. What is written on a plant ("Spot (where exactly)") stays as it is.</p>
      <ul class="whs-list">${S.items.map((it, i) => whsCard(it, i, d.homes))}</ul>
      <p class="row"><button class="btn" type="button" data-act="whsort">Put them all in their spots</button></p></section>` : ''}
    ${d.homes.map(h => html`<section class="blk wh-home"><h2>${multi ? h.home.name : 'Your home'}${h.home.is_home && multi ? ' (main home)' : ''}</h2><div class="wh-sides">${sideHtml(h, 'out')}${sideHtml(h, 'in')}</div></section>`)}`,
    after: () => { WHSORT = S.items; } };
}
let WHSORT = [], WHAREAS = [];
// 1.56.3 (Ethan, November 10): "Plants without a spot". Each group of plants with the same words written on them (or none):
// its plants, ticked; the area; one of that area's spots or a new one; and Put in this spot.
function whsSpotOpts(aid, spotId, name) {
  const a = WHAREAS.find(x => x.id === +aid), sps = a ? a.spots : [];
  const pick = spotId || (sps.find(sp => name && sp.name.toLowerCase() === name.toLowerCase()) || {}).id || 'new';
  return html`${sps.map(sp => html`<option value="${sp.id}" ${String(sp.id) === String(pick) ? raw('selected') : ''}>${sp.name}</option>`)}<option value="new" ${pick === 'new' ? raw('selected') : ''}>A new spot…</option>`;
}
function whsCard(it, i, homes) {
  const isNew = !it.spot_id && !(WHAREAS.find(x => x.id === it.area_id) || { spots: [] }).spots.some(sp => it.name && sp.name.toLowerCase() === it.name.toLowerCase());
  return html`<li class="whs-card" id="whs-${i}"><h3>${it.text ? html`Written on ${it.plants.length === 1 ? 'it' : 'them'}: "${it.text}"` : 'Nothing written on them'}</h3>
    <fieldset class="whs-plants"><legend>Plants (${it.plants.length})</legend>${it.plants.map(x => html`<div class="whs-plant"><label><input type="checkbox" checked data-whs="${i}" data-k="code" value="${x.code}">
      ${x.photo ? html`<img src="${thumbUrl(x.photo)}" alt="" loading="lazy" width="48" height="48">` : html`<span class="job-nophoto" aria-hidden="true"></span>`}<span>${x.name} <span class="muted">${x.code}</span></span></label>
      <a href="#/plant/${enc(x.code)}" class="whs-open">Open ${x.code}</a></div>`)}</fieldset>
    <div class="whs-pick">
      <label class="f">Area or room<select data-whs="${i}" data-k="area">${homes.map(h => html`<optgroup label="${h.home.name}">${h.areas.map(a => html`<option value="${a.id}" ${a.id === it.area_id ? raw('selected') : ''}>${a.side === 'out' ? 'Outside' : 'Inside'}: ${a.name}</option>`)}</optgroup>`)}</select></label>
      <label class="f">Spot<select data-whs="${i}" data-k="spot">${whsSpotOpts(it.area_id, it.spot_id, it.name)}</select></label>
      <label class="f" ${isNew ? '' : raw('hidden')} data-whsnew="${i}">Name of the new spot<input type="text" maxlength="60" value="${it.name}" data-whs="${i}" data-k="name"></label>
    </div>
    <p class="row"><button class="btn" type="button" data-act="whsone" data-i="${i}">Put in this spot</button></p></li>`;
}
function whsItem(i) {
  const it = WHSORT[i], q = k => document.querySelector(`[data-whs="${i}"][data-k=${k}]`); if (!it || !q('area')) return null;
  const codes = [...document.querySelectorAll(`[data-whs="${i}"][data-k=code]:checked`)].map(x => x.value);
  const spot = q('spot').value;
  return { text: it.text, from_area_id: it.area_id, area_id: +q('area').value, codes, ...(spot === 'new' ? { name: q('name').value } : { spot_id: +spot }) };
}
// 1.58.0 (Ethan, November 12): Put in this spot redraws the page, which used to undo the area, spot, name and ticks chosen in every
// other group. They are noted first and put back afterwards, matched by group (its area and what is written on it), since the
// groups' places in the list change when one is done.
const whsKey = it => `${it.area_id}|${it.text || ''}`;
function whsKeep(skip) {
  const out = {};
  WHSORT.forEach((it, i) => {
    const q = k => document.querySelector(`[data-whs="${i}"][data-k=${k}]`); if (i === skip || !q('area')) return;
    out[whsKey(it)] = { area: q('area').value, spot: q('spot').value, name: q('name') ? q('name').value : null,
      off: [...document.querySelectorAll(`[data-whs="${i}"][data-k=code]:not(:checked)`)].map(x => x.value) };
  });
  return out;
}
function whsRestore(kept) {
  WHSORT.forEach((it, i) => {
    const k = kept[whsKey(it)], q = n => document.querySelector(`[data-whs="${i}"][data-k=${n}]`), area = q('area'), sel = q('spot');
    if (!k || !area || !sel) return;
    if ([...area.options].some(o => o.value === k.area)) area.value = k.area;
    if (q('name') && k.name !== null) q('name').value = k.name;
    sel.innerHTML = rend(whsSpotOpts(area.value, null, k.name));
    if ([...sel.options].some(o => o.value === k.spot)) sel.value = k.spot;
    const nf = document.querySelector(`[data-whsnew="${i}"]`); if (nf) nf.hidden = sel.value !== 'new';
    document.querySelectorAll(`[data-whs="${i}"][data-k=code]`).forEach(b => { if (k.off.includes(b.value)) b.checked = false; });
  });
}
document.addEventListener('change', e => {
  const t = e.target; if (!t.dataset || t.dataset.whs === undefined) return;
  const i = t.dataset.whs, sel = document.querySelector(`[data-whs="${i}"][data-k=spot]`), nf = document.querySelector(`[data-whsnew="${i}"]`);
  if (t.dataset.k === 'area' && sel) sel.innerHTML = rend(whsSpotOpts(t.value, null, (document.querySelector(`[data-whs="${i}"][data-k=name]`) || {}).value));
  if ((t.dataset.k === 'area' || t.dataset.k === 'spot') && sel && nf) nf.hidden = sel.value !== 'new';
});

// 1.29.0: Pots and trays: each kind you have, how many, and which plants use them
const CT_MAT = ['Terracotta', 'Thin plastic', 'Thick plastic'];
async function viewPots() {
  const d = await api('GET', '/api/containers'); CT = d;
  const pots = d.items.filter(x => x.kind === 'pot'), trays = d.items.filter(x => x.kind === 'tray');
  return { title: 'Pots and trays', html: html`<h1>Pots and trays</h1>
    <p>Your pots and catch trays, how many of each you have, and which plants use them. Type over any value to change it; it saves when you leave the box. Sizes are in ${lenU() === 'cm' ? 'centimetres' : 'inches'}. The floor area is worked out for you (a round one counts as the square around it), and the Grow lights page uses them: a plant takes up the floor of its catch tray, or of its pot when it has no tray.</p>
    <section class="blk" id="ct-pots"><h2>Pots (${pots.length})</h2><div class="ct-list">${pots.map(ctCard)}</div>
      ${canChange() ? html`<p class="row"><button class="btn" type="button" data-act="ctadd" data-kind="pot">Add a pot</button></p>` : ''}</section>
    <section class="blk" id="ct-trays"><h2>Catch trays (${trays.length})</h2><div class="ct-list">${trays.map(ctCard)}</div>
      ${canChange() ? html`<p class="row"><button class="btn" type="button" data-act="ctadd" data-kind="tray">Add a catch tray</button></p>` : ''}</section>` };
}
let CT = null;
function ctCard(x) {
  const can = canChange(), ro = can ? '' : raw('readonly'), dis = can ? '' : raw('disabled'), ed = k => raw(`data-ed="cont" data-id="${x.id}" data-k="${k}"`);
  const num = (k, label) => html`<label class="f ct-num">${label.replace('(in)', '(' + lenU() + ')')}<input type="number" inputmode="decimal" min="0" max="${lenU() === 'cm' ? 600 : 240}" step="any" value="${x[k] == null ? '' : lenF(x[k], false)}" ${ed(k)} ${ro}></label>`;   // 1.47.0: sizes show and take the person's unit; kept in inches
  const other = x.material && !CT_MAT.includes(x.material);
  const over = x.in_use > x.qty;
  return html`<article class="ct-card" id="ct-${x.id}" data-cid="${x.id}">
    <div class="ct-photos">${x.photos.length ? x.photos.map((ph, i) => html`<figure><img src="${thumbUrl(ph.file)}" alt="${x.name}, photo ${i + 1}" loading="lazy">${can ? html`<button class="btn small ghost" type="button" data-act="ctphotodel" data-id="${ph.id}" aria-label="Remove photo ${i + 1} of ${x.name}">Remove</button>` : ''}</figure>`) : html`<p class="muted">No photo yet.</p>`}
      ${can ? html`<label class="btn ghost small ct-file">Add a photo<input type="file" accept="image/*" multiple data-act="ctphoto" data-id="${x.id}"></label>` : ''}</div>
    <div class="ct-body">
      <label class="f ct-name">Name<input type="text" maxlength="80" value="${x.name}" ${ed('name')} ${ro}></label>
      <div class="ct-qty"><label class="f ct-num">How many you have<input type="number" inputmode="numeric" min="0" max="9999" step="1" value="${x.qty}" ${ed('qty')} ${ro}></label>
        <p class="ct-use ${over ? 'bad-text' : ''}" aria-live="polite"><strong>${x.in_use} / ${x.qty} in use</strong>, ${Math.max(0, x.free)} free${over ? ` (${x.in_use - x.qty} more in use than you have)` : ''}</p></div>
      <div class="field-grid ct-grid">
        <label class="f">Shape<select ${ed('shape')} ${dis}>${[['circle', 'Circle'], ['square', 'Square'], ['rectangle', 'Rectangle']].map(([k, l]) => html`<option value="${k}" ${x.shape === k ? raw('selected') : ''}>${l}</option>`)}</select></label>
        ${x.shape === 'circle' ? num('dia_in', 'Across (in)') : x.shape === 'square' ? num('len_in', 'Side (in)') : html`${num('len_in', 'Length (in)')}${num('wid_in', 'Width (in)')}`}
        ${x.kind === 'pot' ? num('height_in', 'Height (in)') : num('height_in', 'Depth (in)')}
        <p class="f ct-sq"><span class="ct-l">Floor it covers</span> <strong>${x.sqft == null ? 'Add the sizes' : areaF(x.sqft)}</strong></p>
        ${x.kind === 'pot' ? html`<label class="f">Drainage holes<select ${ed('drainage')} ${dis}><option value="" ${x.drainage == null ? raw('selected') : ''}>Not noted</option><option value="1" ${x.drainage === true ? raw('selected') : ''}>Yes</option><option value="0" ${x.drainage === false ? raw('selected') : ''}>No</option></select></label>` : ''}
        <label class="f">Material<select data-f="ctmat" data-id="${x.id}" ${dis}>${CT_MAT.map(m => html`<option ${m === x.material ? raw('selected') : ''}>${m}</option>`)}<option value="" ${!x.material ? raw('selected') : ''}>Not noted</option><option value="__other" ${other ? raw('selected') : ''}>Other (type it)</option></select></label>
        <label class="f" ${other ? '' : raw('hidden')} data-other="${x.id}">Other material<input type="text" maxlength="60" value="${other ? x.material : ''}" ${ed('material')} ${ro}></label>
      </div>
      ${x.kind === 'pot' && x.drainage === false ? html`<p class="notice" role="note">No drainage holes: water collects at the bottom. Water less, or drill holes.</p>` : ''}
      <p><strong>Used by:</strong> ${x.plants.length ? x.plants.map((pl, i) => html`${i ? ', ' : ''}<a href="#/plant/${enc(pl.code)}">${pl.code} ${pl.name}</a>`) : html`<span class="muted">no plants yet. Choose it on a plant's page (Names and place, ${x.kind === 'pot' ? 'Pot' : 'Catch tray'}).</span>`}</p>
      ${edLong('cont', x.id, 'notes', 'Notes', x.notes, can)}
      ${can ? html`<p class="row"><button class="btn small ghost" type="button" data-act="buywatch" data-kind="pots" data-name="${x.name}" data-src="pots:${x.id}"
          data-search="${[x.material && x.material !== 'Other' ? x.material : '', x.kind === 'tray' ? 'plant saucer' : 'pot'].join(' ').trim()}">Watch for more on Shopping</button>
        <button class="btn small danger" type="button" data-act="ctdel" data-id="${x.id}" data-name="${x.name}">Remove ${x.name}</button></p>` : ''}
    </div></article>`;
}
function ctRedraw(x) {
  const old = document.getElementById('ct-' + x.id); if (!old) return;
  const f = document.activeElement && old.contains(document.activeElement) ? document.activeElement.dataset.k : null;
  const i = CT.items.findIndex(y => y.id === x.id); if (i >= 0) CT.items[i] = x;
  const tmp = document.createElement('div'); tmp.innerHTML = rend(ctCard(x)); old.replaceWith(tmp.firstElementChild);
  if (f) { const n = document.querySelector(`#ct-${x.id} [data-k="${f}"]`); if (n) n.focus(); }
}

// 1.29.0: edit in place. Fields marked data-ed save when you leave them (or press Enter); Escape puts back what was there; the
// message that follows has Undo. Long text shows as text with an Edit button (edLong), so reading never changes anything.
function edLong(kind, id, k, label, v, can) {
  return html`<div class="ed-long" data-ed-long="${kind}:${id}:${k}"><p><strong>${label}:</strong> <span class="ed-text">${v || html`<span class="muted">none</span>`}</span>
    ${can ? html` <button class="btn small ghost" type="button" data-act="edlong" aria-label="Edit ${label.toLowerCase()}">Edit</button>` : ''}</p>
    <label class="f wide" hidden>${label}<textarea rows="3" maxlength="2000" data-ed="${kind}" data-id="${id}" data-k="${k}">${v || ''}</textarea><small>Saves when you leave the box. Escape puts back what was there.</small></label></div>`;
}
const edVal = el => el.type === 'checkbox' ? (el.checked ? '1' : '0') : el.value;
const edLabel = el => { const l = el.closest('label'); return ((l && l.childNodes[0] && l.childNodes[0].textContent) || el.getAttribute('aria-label') || el.dataset.k).trim().replace(/\s*\((in|cm)\)$/, ''); };
function edPut(el, v) { if (el.type === 'checkbox') el.checked = v === '1'; else el.value = v; }
async function edSend(el, v) {
  const kind = el.dataset.ed, id = el.dataset.id, k = el.dataset.k;
  const val = el.type === 'checkbox' ? v === '1' : (el.type === 'number' && v !== '' ? +v : v);
  if (kind === 'light') { await api('PUT', '/api/lights/' + id, { [k]: val }); return null; }
  if (kind === 'cont') { const x = await api('PUT', '/api/containers/' + id, { [k]: /_in$/.test(k) && val !== '' ? lenIn(val) : val }); META = await api('GET', '/api/meta'); return () => ctRedraw(x); }   // 1.47.0: a size typed in cm goes back to inches
  if (kind === 'area') { const r = await api('PUT', '/api/where/areas/' + id, { [k]: val }); if (META) META.where = r.homes; return null; }
  if (kind === 'spot') { const r = await api('PUT', '/api/where/spots/' + id, { [k]: val }); if (META) META.where = r.homes; return null; }
  if (kind === 'plant') {
    const box = el.closest('[data-pver]'), conv = x => k === 'height_in' && x !== '' && x != null ? String(lenIn(x)) : x, was = conv(el.dataset.was);    // 1.56.0: a height typed in cm is kept in inches
    const r = await api('PUT', '/api/plants/' + enc(id), { base_version: +box.dataset.pver, base_values: { [k]: was }, fields: { [k]: conv(v) } });
    box.dataset.pver = r.version; if (CUR && CUR.p && CUR.p.code === id) CUR.p = r;
    if (r.conflicts) toast('Someone else changed this plant too. Their other changes are kept.');
    if (['home_id', 'area_id', 'spot_id', 'pot_id', 'tray_id', 'winter_plan', 'health_rating', 'common_name', 'scientific_name', 'id_confidence'].includes(k)) {
      META = await api('GET', '/api/meta');
      return async () => { KEEP = PIDX; await route(); const n = document.querySelector(`[data-ed=plant][data-k="${k}"]`); if (n) n.focus({ preventScroll: true }); };
    }
    return null;
  }
  return null;
}
const edOrig = el => el.type === 'checkbox' ? (el.defaultChecked ? '1' : '0') : el.tagName === 'SELECT' ? ((([...el.options].find(o => o.defaultSelected) || el.options[0]) || {}).value || '') : el.defaultValue;
async function edSave(el) {
  if (el.dataset.busy) return;
  if (el.dataset.was === undefined) el.dataset.was = edOrig(el);     // changed without being focused first (a pointer on a list)
  const v = edVal(el), was = el.dataset.was;
  if (was === undefined || v === was) return;
  if (!(await needName())) { edPut(el, was); return; }
  el.dataset.busy = '1';
  try {
    const after = await edSend(el, v);
    el.dataset.was = v;
    const label = edLabel(el), kind = el.dataset.ed, id = el.dataset.id, k = el.dataset.k;
    careUndoToast(`Saved: ${label}`, async () => {
      const cur = document.querySelector(`[data-ed="${kind}"][data-id="${CSS.escape(id)}"][data-k="${k}"]`) || el;
      edPut(cur, was); cur.dataset.was = v; await edSave(cur);
    });
    const lg = el.closest('.ed-long'); if (lg) { lg.querySelector('.ed-text').textContent = v || 'none'; lg.querySelector('label').hidden = true; const b = lg.querySelector('[data-act=edlong]'); if (b) b.focus(); }
    if (after) after();
  } catch (e) { toast(e.message, true); edPut(el, was); }
  finally { delete el.dataset.busy; }
}
document.addEventListener('focusin', e => { const el = e.target; if (el.dataset && el.dataset.ed && el.dataset.was === undefined) el.dataset.was = edVal(el); }, true);
document.addEventListener('keydown', e => {
  const el = e.target; if (!el.dataset || !el.dataset.ed) return;
  if (e.key === 'Escape' && el.dataset.was !== undefined) { e.preventDefault(); e.stopPropagation(); edPut(el, el.dataset.was); toast('Put back as it was'); }
  else if (e.key === 'Enter' && el.tagName !== 'TEXTAREA' && el.type !== 'checkbox') { e.preventDefault(); edSave(el); }
}, true);
document.addEventListener('change', e => { const el = e.target; if (el.dataset && el.dataset.ed) edSave(el); }, true);

// 1.29.0: Settings: one page for the things that are not about plants
let JOBST = 0;
async function jobsDialog() {               // 1.32.0: the background jobs, in one window, kept up to date while it is open
  const d = await api('GET', '/api/jobs?_=' + Date.now());
  const owner = ME().role === 'owner', ago = t => (t ? when(t) : 'never');
  const box = html`<h2>Jobs</h2>
    <h3>Running now (${d.running.length})</h3>
    ${d.running.length ? html`<ul class="job-list">${d.running.map(j => html`<li><strong>${j.word}</strong>${j.label ? `: ${j.label}` : ''}
      ${j.total ? html` <span class="muted">(${j.done} of ${j.total})</span>` : ''}<br><small class="muted">Started ${when(j.started)}</small></li>`)}</ul>` : html`<p class="muted">Nothing is running.</p>`}
    <h3>On a schedule</h3>
    <ul class="job-list">${d.schedule.map(s => html`<li><strong>${s.word}</strong>: ${s.every}.${s.next ? ` Next ${/^\d{4}-/.test(s.next) ? when(s.next) : s.next}.` : ''} Last ${ago(s.last)}.
      ${owner && ['weather', 'shops', 'backup'].includes(s.kind) ? html` <button class="btn ghost small" type="button" data-act="jobrun" data-kind="${s.kind}">Run now</button>` : ''}</li>`)}</ul>
    <h3>Finished (${d.done.length})</h3>
    ${d.done.length ? html`<ul class="job-list">${d.done.map(j => html`<li><span aria-hidden="true">${j.ok ? '✓' : '✗'}</span> <strong>${j.word}</strong>${j.label ? `: ${j.label}` : ''}, ${j.ok ? 'done' : 'failed'}${j.text ? `: ${j.text}` : ''}
      <br><small class="muted">${when(j.finished)}, ${j.seconds != null ? `${j.seconds} s` : ''}</small></li>`)}</ul>` : html`<p class="muted">Nothing has finished since the app started.</p>`}
    ${d.problems ? html`<p><a href="#" data-act="problems">${d.problems} problem${d.problems === 1 ? '' : 's'} on the Problems list</a></p>` : ''}
    <div class="row"><button class="btn" value="ok" autofocus>Done</button></div><p id="job-msg" role="status" aria-live="polite"></p>`;
  const open = document.querySelector('dialog[open] form.jobs-dlg');
  if (open) { const f = document.activeElement; open.innerHTML = rend(box); if (f && f.dataset && f.dataset.kind) { const n = open.querySelector(`[data-kind="${f.dataset.kind}"]`); if (n) n.focus(); } return; }
  clearTimeout(JOBST);
  const tick = () => { JOBST = setTimeout(async () => { if (document.querySelector('dialog[open] form.jobs-dlg')) { try { await jobsDialog(); } catch (e) { /* next time */ } tick(); } }, 3000); };
  tick();
  await modal(html`<form method="dialog" class="jobs-dlg">${box}</form>`);
  clearTimeout(JOBST);
}
async function problemsDialog() {           // 1.31.0
  const d = await api('GET', '/api/problems?' + (PROBALL ? 'all=1' : ''));
  const owner = ME().role === 'owner';
  const text = () => d.problems.map(p => `${when(p.at)} | ${p.area_word} | ${p.text}${p.times > 1 ? ` (${p.times} times)` : ''}${p.detail ? '\n    ' + p.detail.trim().split('\n').slice(-3).join('\n    ') : ''}`).join('\n');
  modal(html`<form method="dialog" class="prob-dlg"><h2>Problems</h2>
    <p class="muted">${d.problems.length ? `${d.problems.length} ${PROBALL ? 'kept' : 'not yet cleared'}, newest first. Clearing one just takes it off this list.` : (PROBALL ? 'Nothing has been recorded.' : 'Nothing is waiting. Problems that were cleared can still be shown.')}</p>
    ${d.problems.length ? html`<ul class="prob-list">${d.problems.map(p => html`<li ${p.cleared_at ? raw('class="muted"') : ''}><strong>${p.area_word}</strong>: ${p.text}${p.times > 1 ? html` <span class="tag">${p.times} times</span>` : ''}<br><small>${when(p.at)}${p.cleared_at ? ', cleared' : ''}</small>
      ${p.detail ? html`<details><summary>Details</summary><pre class="prob-detail">${p.detail}</pre></details>` : ''}
      ${owner && !p.cleared_at ? html`<button class="btn ghost small" type="button" data-act="probclear" data-id="${p.id}">Clear</button>` : ''}</li>`)}</ul>` : ''}
    <div class="row">${d.problems.length ? html`<button class="btn ghost" type="button" data-act="probcopy">Copy the list for Claude</button>` : ''}${owner && d.open ? html`<button class="btn ghost" type="button" data-act="probclear" data-id="all">Clear them all</button>` : ''}
      <button class="btn ghost" type="button" data-act="proball">${PROBALL ? 'Only the ones not cleared' : 'Show cleared ones too'}</button><button class="btn" value="ok" autofocus>Done</button></div>
    <p id="prob-msg" role="status" aria-live="polite"></p></form>`);
  PROBTEXT = text();
}
let PROBALL = false, PROBTEXT = '';
// 1.36.0: the health of the app in one card: version, backups and their copies, the last weather update and store check, problems, disk space
const gb = n => n == null ? '' : n >= 1e9 ? (n / 1e9).toFixed(1) + ' GB' : (n / 1e6).toFixed(0) + ' MB';
async function loadHealth() {
  const box = document.getElementById('health-box'); if (!box) return;
  let H; try { H = await api('GET', '/api/health'); } catch (e) { box.innerHTML = rend(html`<p class="notice bad">Could not check: ${e.message}</p>`); return; }
  const ok = (good, text) => html`<li class="${good ? 'hl-ok' : 'hl-bad'}"><span aria-hidden="true">${good ? '✓' : '!'}</span> ${text}</li>`;
  const oldAge = ts => ts && (Date.now() - new Date(ts)) > 2 * 86400e3;
  const lowDisk = H.free_bytes != null && H.free_bytes < 2e9;
  const copyGood = H.copy.at && !/failed/.test(H.copy.dir + H.copy.receiver) && (H.copy.dir || H.copy.receiver) && H.copy.away !== false;   // 1.58.0: a copy beside the data is not a second copy
  const notes = (H.backup_notes || []).filter(n => n.key !== 'one-drive');
  box.innerHTML = rend(html`<ul class="hl">
    <li><span aria-hidden="true">●</span> Version ${H.version}${H.db_version && H.db_version !== H.version ? ` (the database was last opened by ${H.db_version})` : ''}, running as ${H.runs_as || 'the app'}. ${H.plants} plants, ${H.photos} photos, ${H.readings.toLocaleString()} readings${H.sensors ? ` from ${H.sensors} sensor${H.sensors === 1 ? '' : 's'}` : ''}.</li>
    ${H.journal && H.journal.note ? html`<li><span aria-hidden="true">●</span> Saving mode: ${(H.journal.mode || '').toUpperCase()}. ${H.journal.note}</li>` : ''}
    ${ok(H.backup.last && !oldAge(H.backup.last), H.backup.last ? `Last backup ${when(H.backup.last)}${/^\d{4}-/.test(H.backup.next) ? ', next ' + when(H.backup.next) : ''}.` : H.backup.every === 'turned off' ? 'Automatic backups are turned off.' : 'No automatic backup yet.')}
    ${notes.map(n => ok(false, html`${bkNote(n)} <a href="#/backups">Backups</a>`))}
    ${H.copy.away === false ? ok(false, html`${bkNote('one-drive')} <a href="#/backups?sec=bk-copies">How to keep a copy on another drive</a>`)
      : ok(copyGood, H.copy.at ? `Second copy ${when(H.copy.at)}: ${[H.copy.dir ? 'folder ' + H.copy.dir : '', H.copy.receiver ? 'other computer ' + H.copy.receiver : ''].filter(Boolean).join('; ') || 'nowhere set up'}.` : 'No second copy of a backup yet (Backups page).')}
    ${ok(H.weather.last && !oldAge(H.weather.last), H.weather.last ? `Weather updated ${when(H.weather.last)}.` : 'No weather update yet.')}
    ${ok(true, H.shops.last ? `Stores checked ${when(H.shops.last)} (${H.shops.every}).` : `Stores not checked yet (${H.shops.every}).`)}
    ${ok(!H.problems, H.problems ? `${H.problems} problem${H.problems === 1 ? '' : 's'} to look at.` : 'No problems.')}
    ${ok(!lowDisk, `Data folder ${gb(H.data_bytes)} (database ${gb(H.db_bytes)})${H.free_bytes != null ? `; ${gb(H.free_bytes)} free of ${gb(H.disk_bytes)} on its disk` : ''}.`)}</ul>`);
}
function viewSettings() {
  const me = ME(), owner = me.role === 'owner';
  const card = (title, text, btn) => html`<section class="blk set-card"><h2>${title}</h2><p>${text}</p><div class="row">${btn}</div></section>`;
  return { title: 'Settings', after: () => { api('GET', '/api/problems').then(d => { const n = document.getElementById('prob-n'); if (n && d.open) n.textContent = ` (${d.open})`; }).catch(() => {}); loadHealth(); }, html: html`<h1>Settings</h1>
    <p class="muted">Plant record version <strong>${META.version}</strong>${META.runs_as ? `, running as ${META.runs_as}` : ''}. The version number is also always beside the name at the top of the page.</p>
    <p>Offline use, Backups and the Audit log are in the row of pages above: <a href="#/offline">Offline use</a>, <a href="#/backups">Backups</a>, <a href="#/history">Audit log</a>.</p>
    <div class="set-grid">
    ${card('People and your name', owner ? 'Your name in the audit log, and who can view, edit or own the app.' : 'Your name in the audit log, and what you are allowed to do.', html`<button class="btn" type="button" data-act="who">${owner ? 'Open people and names' : 'Open your name'}</button>`)}
    ${card('Display', 'Text size, colours, page layout, reading aloud, photos, touch and keyboard. Also on the Display button at the bottom of every page.', html`<button class="btn" type="button" data-act="display">Open Display settings</button>`)}
    ${card('Homes and places', 'Where plants live, and the places whose weather is tracked.', html`<a class="btn" href="#/weather?sec=places">Open Homes and places</a>`)}
    ${card('Stores and keys', 'The stores Shopping checks, the eBay and Etsy keys, and the Pl@ntNet and Claude keys for Identify.', html`<a class="btn" href="#/shopping/stores">Stores</a><a class="btn ghost" href="#/identify">Keys (Identify page)</a>`)}
    ${card('Notifications', 'Messages on your phone or computer, even when the app is closed: cold nights, Shopping alerts, what is due today, and requests from Claude. Chosen for your own sign-in.', html`<button class="btn" type="button" data-act="notify" aria-haspopup="dialog">Open Notifications</button>`)}
    <section class="blk set-card set-health" id="health"><h2>Health of the app</h2><div id="health-box" aria-live="polite"><p class="loading">Checking</p></div>
      <div class="row"><button class="btn" type="button" data-act="jobs" aria-haspopup="dialog">Open the Jobs list</button><button class="btn ghost" type="button" data-act="problems" aria-haspopup="dialog">Open the Problems list<span id="prob-n"></span></button></div></section>
    ${card('Debug', 'A live view of the audit log at the bottom of the screen, and other tools for checking the app.', html`<button class="btn" type="button" id="debug-btn" data-act="debug" aria-haspopup="dialog">Open Debug</button>`)}
    </div>` };
}
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
    ${P.homes && P.homes.length > 1 ? html`<label class="f">Starts on<select data-f="phome" data-login="${p.login}">${P.homes.map(h => html`<option value="${h.id}" ${(p.home_id || P.main_home) === h.id ? raw('selected') : ''}>${h.name}</option>`)}</select></label>
      ${p.role === 'editor' ? html`<fieldset class="f p-homes"><legend>Can change plants at</legend>${P.homes.map(h => html`<label class="chk"><input type="checkbox" data-f="pedithome" data-login="${p.login}" value="${h.id}" ${!(p.edit_homes || []).length || p.edit_homes.includes(h.id) ? raw('checked') : ''}>${h.name}</label>`)}<small>All ticked: every home. Untick a home to keep its plants as they are.</small></fieldset>` : ''}` : ''}
    ${p.login === self ? '' : html`<button class="btn small danger" type="button" data-act="pdel" data-login="${p.login}" data-name="${p.name}" aria-label="Remove ${p.name} from the people list">Remove</button>`}</li>`)}</ul>`;
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
// 1.25.0: a press that starts and ends outside the window closes it, as Cancel would (a drag that ends outside does not)
let DLGDOWN = false;
const outsideDlg = e => { const r = dlg.getBoundingClientRect(); return e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom; };
dlg.addEventListener('pointerdown', e => { DLGDOWN = e.target === dlg && outsideDlg(e); });
dlg.addEventListener('click', e => { if (DLGDOWN && e.target === dlg && outsideDlg(e)) { dlg.close(''); } DLGDOWN = false; });
function modal(content, cls) {
  dlg.className = cls || '';
  dlg.innerHTML = rend(content);
  notesPass(dlg);                                   // 1.57.0: notes on request, in windows too
  setTimeout(() => scrollBoxes(dlg), 0);            // 1.58.0: a table that scrolls in a window can be scrolled by keyboard (measured once the window is open)
  const h2 = dlg.querySelector('h2');               // the window is named by its heading, for screen readers
  if (h2) { h2.id = h2.id || 'dlg-title'; dlg.setAttribute('aria-labelledby', h2.id); } else dlg.removeAttribute('aria-labelledby');
  return new Promise(res => {
    const done = () => { dlg.removeEventListener('close', done); res(dlg.returnValue); };
    dlg.addEventListener('close', done);
    dlg.returnValue = '';
    if (!dlg.open) dlg.showModal();
    const f = dlg.querySelector('[autofocus]') || dlg.querySelector('input,select,textarea');
    if (f) f.focus();
  });
}
async function confirmBox(title, text, okLabel, danger) {
  const r = await modal(html`<form method="dialog"><h2>${title}</h2><p>${text}</p>
    <div class="row"><button class="btn ${danger ? 'danger' : ''}" value="ok">${okLabel}</button>
    <button class="btn ghost" value="cancel" autofocus>Cancel</button></div></form>`, 'small');
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
function go(h) { if (h && !h.startsWith('#')) { location.href = h; return; } NAVCLICK = Date.now(); if (location.hash === h) route(); else location.hash = h; }   // 1.52.1: a page of its own (sitter.html) too
window.addEventListener('hashchange', route);
// 1.38.0: where you were on each page. Going back (the browser's Back button, or a "Back to" link pressed after a page you came from)
// returns to the same place on the page; a link to a new page starts at the top. The position is noted when you leave the page.
const SCROLLS = {};
let NAVCLICK = 0;
document.addEventListener('click', e => { const a = e.target.closest('a[href^="#/"]'); if (a) NAVCLICK = Date.now(); }, true);
function scrollBack(h) {
  const y = SCROLLS[h]; if (!y) return false;
  const put = () => { if (location.hash.replace(/^#/, '') === h && !document.querySelector('#dlg[open]')) window.scrollTo(0, y); };
  put(); setTimeout(put, 250); setTimeout(put, 900);
  return true;
}
let ROUTE_FRESH = false;             // set to draw the page again from fresh answers, keeping the scroll position
async function quickRecheck(my, urls) {
  // the page was drawn from saved answers: ask again, and redraw if any changed, unless you have started typing or choosing on it
  const before = urls.map(u => { const x = QC.get(qcKey(u)); return x ? JSON.stringify(x.data) : ''; });
  let changed = false;
  for (let i = 0; i < urls.length; i++) {
    const gen = QGEN;
    try { const d = await apiNet('GET', urls[i]); if (gen !== QGEN) return; if (JSON.stringify(d) !== before[i]) changed = true; qcPut(urls[i], d); } catch (e) { /* keep what is shown */ }
    if (my !== token) return;
  }
  if (!changed || my !== token) return;
  const a = document.activeElement;
  if (a && app.contains(a) && /^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName)) return;
  if (document.querySelector('dialog[open]')) return;
  ROUTE_FRESH = true; route();
}
// which answers each page needs, learned as you go and kept on this device; plant, species, group and find pages share one pattern
let PF = {};
try { PF = JSON.parse(localStorage.getItem('plantdb.prefetch') || '{}') || {}; } catch (e) { PF = {}; }
function pfPattern(h) {
  const m = h.split('?')[0].match(/^\/(plant|species|group|fungi)\/([^/]+)$/);
  return m ? ['/' + m[1] + '/*', m[2]] : [h, null];
}
function pfLearn(h, used) {
  const [k, id] = pfPattern(h), list = [...new Set(used)].filter(u => !QC_SKIP.test(u)).slice(0, 12);
  if (!list.length) return;
  PF[k] = id ? list.map(u => u.split(id).join('{id}')) : list;
  const keys = Object.keys(PF); if (keys.length > 80) delete PF[keys[0]];
  try { localStorage.setItem('plantdb.prefetch', JSON.stringify(PF)); } catch (e) { /* this visit only */ }
}
function pfUrls(href) {
  const h = href.replace(/^#/, '') || '/', [k, id] = pfPattern(h), list = PF[k];
  return list ? list.map(u => (id ? u.split('{id}').join(id) : u)) : [];
}
function prefetch(href) {
  for (const u of pfUrls(href)) {
    const k = qcKey(u), hit = QC.get(k);
    if ((hit && Date.now() - hit.at < 60000) || PFLY.has(k)) continue;
    const gen = QGEN, p = apiNet('GET', u).then(d => { if (gen !== QGEN) return undefined; qcPut(u, d); return d; }).catch(() => undefined).finally(() => { if (PFLY.get(k) === p) PFLY.delete(k); });
    PFLY.set(k, p);
  }
}
function pfIdle(my) {                // when the page is quiet, fetch the other pages of its section ahead
  const go = () => {
    if (my !== token || document.hidden || (navigator.connection && navigator.connection.saveData)) return;
    [...document.querySelectorAll('#sub-nav a[href^="#/"]:not([aria-current])')].forEach((a, i) => setTimeout(() => { if (my === token) prefetch(a.getAttribute('href')); }, i * 400));
  };
  if (window.requestIdleCallback) requestIdleCallback(go, { timeout: 4000 }); else setTimeout(go, 2000);
}
['pointerover', 'focusin', 'touchstart'].forEach(ev => document.addEventListener(ev, e => {
  const a = e.target && e.target.closest && e.target.closest('a[href^="#/"]');
  if (a) prefetch(a.getAttribute('href'));
}, { passive: true }));
// page timings, shown on Debug: how long each page took to change, how much of that was waiting for answers, and which ones
let TIMINGS = [];
try { TIMINGS = JSON.parse(localStorage.getItem('plantdb.timings') || '[]') || []; } catch (e) { TIMINGS = []; }
function timingKeep(T, t0, tData, tEnd) {
  TIMINGS.unshift({ at: new Date().toISOString(), page: T.page, total: Math.round(tEnd - t0), wait: Math.round(tData - t0), draw: Math.round(tEnd - tData),
    saved: T.calls.filter(c => c.saved).length, calls: T.calls.filter(c => !c.saved).sort((a, b) => b.ms - a.ms).slice(0, 6) });
  TIMINGS = TIMINGS.slice(0, 40);
  try { localStorage.setItem('plantdb.timings', JSON.stringify(TIMINGS)); } catch (e) { /* this visit only */ }
}
async function route() {
  const my = ++token;
  OFF.saved = null;
  const h = location.hash.replace(/^#/, '') || '/';
  if (lastPath && lastPath !== h) SCROLLS[lastPath] = window.scrollY;
  const wentBack = Date.now() - NAVCLICK > 1000;      // not from a link just pressed: Back, Forward, or typed
  const [hp, hq] = h.split('?');                     // 1.18.0: #/library?q=... keeps the search in the address
  const parts = hp.split('/').filter(Boolean), qs = new URLSearchParams(hq || '');
  if (parts[0] !== 'identify') idStop();
  if (parts[0] !== 'new') NEWFILL = null;
  if (parts[0] !== 'fungi' || parts[1] !== 'new') MUFILL = null;
  const nav = parts[0] === 'winter' || parts[0] === 'frost' || parts[0] === 'inside' || parts[0] === 'outside' ? 'winter' : parts[0] === 'weather' || parts[0] === 'sensors' ? 'weather' : parts[0] === 'fertilizer' ? 'fertilizer' : parts[0] === 'lights' ? 'lights' : parts[0] === 'photos' ? 'photos' : parts[0] === 'labels' ? 'labels' : parts[0] === 'history' || parts[0] === 'audit' ? 'history' : parts[0] === 'backups' ? 'backups' : parts[0] === 'groups' || parts[0] === 'group' ? 'groups' : parts[0] === 'identify' ? 'identify' : parts[0] === 'library' || parts[0] === 'species' || parts[0] === 'wishlist' || parts[0] === 'around' ? 'library' : parts[0] === 'fungi' ? 'fungi' : parts[0] === 'offline' || parts[0] === 'decisions' ? 'offline' : parts[0] === 'today' || !parts.length ? 'today' : 'plants';
  navMark(parts[0] === 'weather' && qs.get('sec') === 'places' ? 'places' : FEAT.pages[parts[0]] ? (FEAT.pages[parts[0]].nav || parts[0]) : ['pots', 'where', 'settings', 'new', 'wishlist', 'frost', 'inside', 'outside', 'around', 'decisions', 'review'].includes(parts[0]) ? parts[0] : parts[0] === 'share' ? 'photos' : parts[0] === 'shopping' || parts[0] === 'store' ? 'shopping' : nav);   // 1.46.0: registered pages (features.js) say which link is theirs
  pagesMenu(false); topMoreFold();
  wlBadge();
  // 1.30.0: the screen changes at once. If the page is not ready in a moment, its name shows with "Loading"; a page opened before
  // shows what was saved from last time, and is checked again just after (see QC above)
  const t0 = performance.now(), fresh = ROUTE_FRESH || h === lastPath; ROUTE_FRESH = false;   // 1.42.0: the same page drawn again after a change keeps its place (no Loading flash that sent it to the top)
  const quick = !fresh && !(parts[2] === 'edit' || parts[0] === 'new' || (parts[0] === 'fungi' && parts[1] === 'new') || parts[0] === 'decisions' || parts[0] === 'offline');
  QUICK = quick ? { used: [], stale: [] } : { used: [], stale: [], off: true };
  TIMING = { page: '#' + h, calls: [], quick };
  const myQuick = QUICK, myTiming = TIMING;
  if (!fresh) setTimeout(() => {
    if (my !== token || myTiming.drawn) return;
    const cur = document.querySelector('#sub-nav a[aria-current=page]') || document.querySelector('#main-nav a[aria-current=page]');
    app.setAttribute('aria-busy', 'true');
    app.innerHTML = rend(html`<h1>${cur ? cur.childNodes[0].textContent.trim() : 'Plant record'}</h1><p class="loading" role="status">Loading</p>`);
  }, 150);
  try {
    let view;
    // shared lists (plant names for links, frost, groups) only hold the page up the first time; after that they refresh alongside it
    const need = (have, p) => (have ? (p.catch(() => {}), null) : p);
    const groupsNow = parts[0] === 'groups' || parts[0] === 'group';
    await Promise.all([need(PCODES_AT > 0, loadCodes()), need(!!FROST, loadFrost()), need(!!PGROUPS && !groupsNow, loadGroups(groupsNow || parts[0] === 'plants')),
      G.care && !CAREDUE ? loadCareDue() : null,
      META ? null : api('GET', '/api/meta').then(M => { META = M; const v = document.getElementById('app-ver'); if (v && META.version) v.textContent = 'v' + META.version; paintPlace(); paintWho(); })]);
    if (myQuick.off) QUICK = null;
    if (parts[0] === 'plant' && parts[1] && parts[2] === 'edit') view = await viewEdit(decodeURIComponent(parts[1]));
    else if (parts[0] === 'plant' && parts[1]) view = await viewPlant(decodeURIComponent(parts[1]));
    else if (parts[0] === 'new' && parts[1] === 'several') view = await viewSeveral();
    else if (parts[0] === 'new') { if (!ID.keys) { try { ID.keys = await api('GET', '/api/identify/settings'); } catch (e) { /* no Pl@ntNet then */ } } view = viewForm(null); }
    else if (parts[0] === 'winter') view = await viewWinter();
    else if (parts[0] === 'weather') view = await viewWeather(qs.get('sec'));
    else if (parts[0] === 'review') view = await viewReview(qs);     // 1.37.0
    else if (parts[0] === 'share') view = await viewShare();           // 1.37.0
    else if (parts[0] === 'settings') view = viewSettings();
    else if (parts[0] === 'where') view = await viewWhere();
    else if (parts[0] === 'pots') view = await viewPots();
    else if (parts[0] === 'today' || !parts.length) view = await viewToday();     // 1.34.0: Today is the page the app opens on
    else if (parts[0] === 'plants') view = await viewGallery(qs);
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
    else if (parts[0] === 'shopping' && parts[1] === 'stores') view = await viewStores();
    else if (parts[0] === 'shopping' && parts[1] === 'list') view = await viewShopList();
    else if (parts[0] === 'shopping') view = await viewShopping();
    else if (parts[0] === 'store' && parts[1]) view = await viewStore(decodeURIComponent(parts[1]));
    else if (parts[0] === 'offline') view = await viewOffline();
    else if (parts[0] === 'decisions') view = await viewDecisions();
    else if (parts[0] === 'around') view = await viewAround();
    else if (parts[0] === 'fungi' && !parts[1]) view = await viewFungi();
    else if (parts[0] === 'fungi' && parts[1] === 'safety') view = viewFungiSafety();
    else if (parts[0] === 'fungi' && parts[1] === 'new') view = await viewFindForm(null);
    else if (parts[0] === 'fungi' && parts[2] === 'edit') view = await viewFindForm(decodeURIComponent(parts[1]));
    else if (parts[0] === 'fungi') view = await viewFind(decodeURIComponent(parts[1]));
    else if (FEAT.pages[parts[0]]) view = await FEAT.pages[parts[0]].view(parts, qs);   // 1.46.0: pages a feature module registered (features.js)
    else view = await viewGallery();
    if (QUICK === myQuick) QUICK = null;
    if (my !== token) return;
    const tData = performance.now(), keepY = fresh ? window.scrollY : 0;
    myTiming.drawn = true; app.removeAttribute('aria-busy');
    app.innerHTML = rend(view.html);
    if (parts[0] !== 'frost' && parts[0] !== 'plant' && parts[0] !== 'today' && parts.length && coldSeason()) app.insertAdjacentHTML('afterbegin', rend(frostBanner()));   // 1.48.0: no frost banner at a tropical home   // plant pages have their own note; Today has its own section
    if (((OFF.saved && OFF.saved !== 'none') || !navigator.onLine || OFF.reach === 'no') && parts[0] !== 'offline') app.insertAdjacentHTML('afterbegin', rend(html`<p class="notice off-note noprint" role="note"><strong>Offline.</strong> This is what this device saved${OFF.saved && OFF.saved !== 'none' ? ' on ' + when(OFF.saved) : ''}. Changes you make are kept here and sent when the plant server can be reached. <button class="btn small ghost" type="button" data-act="offtry">Try to connect now</button> <a href="#/offline">Offline page</a></p>`));
    await offNotice(parts);
    if (my !== token) return;
    if (META && META.mirror && META.mirror.on) app.insertAdjacentHTML('afterbegin', rend(html`<p class="notice vw-note mirror-note noprint" role="note"><strong>This is the mirror:</strong> a read-only copy${META.mirror.made ? ` of the backup made ${when(META.mirror.made)}` : META.mirror.at ? ` taken ${when(META.mirror.at)}` : ', waiting for its first backup'}${META.mirror.error ? ` (${META.mirror.error})` : ''}. Changes are turned off here; ${META.mirror.main ? html`make them in <a href="${META.mirror.main}">the main app</a>` : 'make them in the main app'}.</p>`));   // 1.37.0
    else if (ME().role === 'viewer') app.insertAdjacentHTML('afterbegin', rend(html`<p class="notice vw-note noprint" role="note"><strong>View only.</strong> You can look at everything here, but changes are turned off. Ask ${ME().owner_name} if you would like to edit.</p>`));
    if (view.title) document.title = view.title + ' | Plant record'; else document.title = 'Plant record';
    if (view.after) view.after();
    featAdds(parts);                              // 1.46.0: what feature modules add to this page once it is on screen (features.js); they rebuild Navigation when done
    if (parts[0] === 'weather' && qs.get('sec') === 'places') setTimeout(() => { const t = document.getElementById('sec-places'); if (t) { scrollToSection(t); navFlash(t); } }, 300);   // 1.29.0: Homes and places
    else if (qs.get('sec')) { const go2 = () => { const t = document.getElementById(qs.get('sec')); if (t) { scrollToSection(t); navFlash(t); } }; setTimeout(go2, 300); setTimeout(go2, 1500); }   // 1.36.0: #/plant/P-001?sec=inside opens the page at that section
    buildSideNav(); addFoldButtons(); navLayout(); addReadButtons(); notesPass(); scrollBoxes(); setTimeout(() => { buildSideNav(); addFoldButtons(); navLayout(); addReadButtons(); notesPass(); scrollBoxes(); }, 1200);
    if (h !== lastPath) { if (!(wentBack && !qs.get('sec') && scrollBack(h))) window.scrollTo(0, 0); focusTitle(app); NAVPIN = -1; navActive(); }
    else if (fresh && keepY) window.scrollTo(0, keepY);
    lastPath = h;
    timingKeep(myTiming, t0, tData, performance.now());
    pfLearn(h, myQuick.used);
    if (myQuick.stale.length) quickRecheck(my, myQuick.stale);
    pfIdle(my);
  } catch (e) {
    if (QUICK === myQuick) QUICK = null;
    app.removeAttribute('aria-busy');
    if (my !== token) return;
    myTiming.drawn = true;                       // 1.38.0: so the "Loading" stand-in does not replace the message when the page failed within 150 ms
    app.innerHTML = rend(html`<div class="notice bad" role="alert"><strong>${e.status === 404 ? 'Not found' : 'Something went wrong'}</strong><p>${e.message}</p>
      <a class="btn ghost" href="#/plants">Back to all plants</a></div>`);
  }
}


// ---------- section menu (left or right, can be folded away) ----------
let NAVSESSION = null;                // on narrow screens the menu starts folded; opening it there lasts until a link is chosen
function navOpen() { const P = window.PlantPrefs.get(), r = document.documentElement, narrow = r.dataset.narrow === '1'; if (r.dataset.navempty === '1' && !narrow) return false; return NAVSESSION != null ? NAVSESSION : (P.navopen === '1' && !narrow); }
// 1.26.0: with large text on a computer, the page links fold behind the Pages button once they would take more than two rows (or
// the top bar more than a fifth of the window), and a top bar still taller than a fifth of the window scrolls away with the page, as on phones, instead of staying pinned
// 1.29.0: the top bar has six sections; the pages of the section you are in are on a second row (Ethan's choice, November 2026)
const SECTIONS = [
  ['today', 'Today', [['today', 'Today', '#/']]],
  ['plants', 'Plants', [['plants', 'All plants', '#/plants'], ['groups', 'Groups', '#/groups'], ['new', 'Add plants', '#/new'], ['fungi', 'Mushrooms', '#/fungi'], ['where', 'Rooms and spots', '#/where'], ['photos', 'Photos', '#/photos'], ['labels', 'Labels', '#/labels'], ['review', 'Year in review', '#/review']]],   // 1.37.0: the year in review
  ['care', 'Care', [['winter', 'Winter plan', '#/winter'], ['frost', 'Cold-night checklist', '#/frost'], ['inside', 'Coming inside', '#/inside'], ['outside', 'Back outside', '#/outside'], ['fertilizer', 'Fertilizer', '#/fertilizer'], ['lights', 'Grow lights', '#/lights'], ['pots', 'Pots and trays', '#/pots']]],   // 1.36.0: every page in its section's row
  ['weather', 'Weather', [['weather', 'Weather', '#/weather'], ['sensors', 'Sensors', '#/sensors'], ['places', 'Homes and places', '#/weather?sec=places']]],
  ['discover', 'Discover', [['identify', 'Identify', '#/identify'], ['library', 'Library', '#/library'], ['around', 'Around home', '#/around'], ['wishlist', 'Wishlist', '#/wishlist'], ['shopping', 'Shopping', '#/shopping']]],
  ['settings', 'Settings', [['settings', 'Settings', '#/settings'], ['offline', 'Offline use', '#/offline'], ['decisions', 'Offline decisions', '#/decisions'], ['backups', 'Backups', '#/backups'], ['history', 'Audit log', '#/history']]],
];
// 1.48.0 (PLAN.md step 4b): the cold-season pages belong to a home with a winter. At a tropical home (Homes and places, Seasons) they
// are left out of the top bar, and Today leaves out its cold blocks (care.js). The pages still open by address, so nothing breaks.
const COLD_PAGES = ['winter', 'frost', 'inside', 'outside'];
const coldSeason = () => !(typeof META !== 'undefined' && META && META.place && META.place.season === 'tropical');
const secPages = sec => coldSeason() ? sec[2] : sec[2].filter(p => !COLD_PAGES.includes(p[0]));
const secOf = nav => (SECTIONS.find(x => x[2].some(p => p[0] === nav)) || SECTIONS[1]);
function navMark(nav) {
  const sec = secOf(nav);
  document.querySelectorAll('#main-nav a[data-sec]').forEach(a => {
    if (a.dataset.sec === sec[0]) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current');
    const S2 = SECTIONS.find(x => x[0] === a.dataset.sec), first = S2 && secPages(S2)[0];       // 1.48.0: a section opens on its first page that applies here
    if (first) a.setAttribute('href', first[2]);
  });
  const sub = document.getElementById('sub-nav');
  if (sub) {
    const pages = secPages(sec);
    sub.hidden = pages.length < 2;
    sub.setAttribute('aria-label', `${sec[1]} pages`);
    sub.innerHTML = rend(html`${pages.map(([k, label, href]) => html`<a href="${href}" data-nav="${k}" ${k === nav ? raw('aria-current="page"') : ''}>${label}</a>`)}`);
  }
  WLBADGE = 0;                                     // the wishlist count goes on the new links
}
function topFit() {
  const r = document.documentElement, nav = document.getElementById('main-nav'), top = document.querySelector('.top');
  if (!nav || !top) return;
  if (r.dataset.narrow === '1') { r.dataset.pagesfold = '0'; r.dataset.toptall = '0'; r.dataset.topmode = ''; r.dataset.navrow = '0'; return; }
  const was = top.classList.contains('pages-open'); top.classList.remove('pages-open');
  // 1.26.1: the bar spans the window. Everything on one line if it fits; otherwise the name and the buttons on the first line and
  // the page links on a line of their own, spread across the whole width
  const rows = () => new Set([...nav.querySelectorAll('a')].map(x => Math.round(x.getBoundingClientRect().top))).size;
  const fit = () => {
    r.dataset.pagesfold = '0'; r.dataset.topmode = 'one'; r.dataset.navrow = '0';
    if (rows() > 1) r.dataset.topmode = 'tier';
    r.dataset.navrow = rows() === 1 ? '1' : '0';
    const a = nav.querySelector('a');
    if (a && (nav.offsetHeight > a.offsetHeight * 2.5 || top.offsetHeight > innerHeight * 0.2)) { r.dataset.pagesfold = '1'; r.dataset.topmode = ''; r.dataset.navrow = '0'; }
  };
  r.dataset.topcompact = '0'; r.dataset.toptall = '0'; fit();
  // 1.33.0: when Online, Location and Editing no longer fit beside the name, the Search button keeps only its icon and the Location
  // button only its pin and place (their full names stay for screen readers) before the bar grows another row
  const brand = top.querySelector('.brand'), acts = top.querySelector('.top-acts');
  if (brand && acts && Math.abs(brand.getBoundingClientRect().top - acts.getBoundingClientRect().top) > 8) { r.dataset.topcompact = '1'; fit(); }
  if (was) top.classList.add('pages-open');
  r.dataset.toptall = top.offsetHeight > innerHeight * 0.2 ? '1' : '0';
}
// 1.57.0: when the top bar is too tall to stay put, the Navigation menu starts under it and moves up as it scrolls away (it ran from
// the top of the window, beside a top bar pushed over to make room)
function navTop() {
  const r = document.documentElement, top = document.querySelector('.top');
  if (r.dataset.toptall === '1' && r.dataset.narrow !== '1' && top) r.style.setProperty('--nav-top', Math.max(0, Math.round(top.getBoundingClientRect().bottom)) + 'px');
  else r.style.removeProperty('--nav-top');
}
window.addEventListener('scroll', () => { if (document.documentElement.dataset.toptall === '1' && !navTop.f) navTop.f = requestAnimationFrame(() => { navTop.f = 0; navTop(); }); }, { passive: true });
function navLayout() {
  const r = document.documentElement, top = document.querySelector('.top');
  topFit();
  r.style.setProperty('--top-h', (r.dataset.narrow === '1' || r.dataset.toptall === '1' ? 0 : (top ? top.getBoundingClientRect().height : 64)) + 'px');   // on phones the top bar scrolls away
  navTop();
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
document.addEventListener('toggle', e => { if (e.target && e.target.id === 'pn-filters') PNOPEN = e.target.open; if (e.target && e.target.id === 'more-f') { MOREOPEN = e.target.open; try { localStorage.setItem('plantdb.morefilters', MOREOPEN ? '1' : '0'); } catch (x) { /* this visit only */ } } }, true);
let NAVITEMS = [];
function buildSideNav() {
  const list = document.getElementById('sn-list'); if (!list) return;
  const app = document.getElementById('app'), used = new Set();
  const slug = t => { let b = 'sec-' + t.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40) || 'sec', k = b, i = 2; while (used.has(k) || (document.getElementById(k) && document.getElementById(k).dataset.navid !== '1')) k = b + '-' + i++; used.add(k); return k; };
  const pinned = NAVPIN >= 0 && NAVITEMS[NAVPIN] ? (NAVITEMS[NAVPIN].id || 'top') : null;   // a rebuild of the same page keeps your choice
  NAVITEMS = []; NAVPIN = -1;
  const h1 = app.querySelector('h1');
  if (h1) NAVITEMS.push({ el: h1, text: 'Top of the page', id: null, top: true });
  // 1.14.1: every section title (h2) plus any part marked data-section="Its name", in page order, so new sections join by themselves
  const seen = new Set();
  app.querySelectorAll('h2, [data-section]').forEach(h => {
    if (h.closest('dialog,.chart-card,#sidenav') || !h.offsetParent || h.classList.contains('sr')) return;   // 1.57.0: a heading only for screen readers is not a section
    const marked = h.matches("[data-section]"), sec = marked ? h : (h.closest('section') || h);
    if (seen.has(sec) || (!marked && sec.closest("[data-section]") && sec.closest("[data-section]") !== sec)) return;
    seen.add(sec);
    const text = marked ? h.dataset.section : h.textContent.trim();
    if (!sec.id) { sec.id = slug(text); sec.dataset.navid = '1'; }
    NAVITEMS.push({ el: sec, head: marked ? sec : h, text, id: sec.id });
  });
  buildJumpRow();
  document.documentElement.dataset.navempty = NAVITEMS.length <= 1 ? '1' : '0';     // 1.39.1: only "Top of the page": no menu for this page
  if (typeof pinLayout === 'function') pinLayout();                                 // 1.42.0: Display follows the menu
  list.innerHTML = rend(html`${NAVITEMS.map((it, i) => html`<li><a href="#${it.id || 'app'}" data-act="navgo" data-i="${i}">${it.text}</a></li>`)}`);
  if (!NAVITEMS.length) list.innerHTML = rend(html`<li class="muted">This page has no sections.</li>`);
  if (pinned) NAVPIN = NAVITEMS.findIndex(it => (it.id || 'top') === pinned);
  navActive();
}
// the row of section buttons on plant pages: the same sections as the menu, with shorter names where the title is long
const JUMP_SHORT = { 'Name and details': 'Details', 'Current conditions': 'Now', 'Needed from you': 'Needed', 'Requests (all answered)': 'Requests',
  'Getting this plant back in range': 'Back in range', 'In range': 'In range', 'Plant identification': 'Identification', 'About this plant': 'About', 'Uses, partners and propagation': 'Uses',
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
  foldOpenFor(t);            // 1.42.0
  const beh = matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', pane = t.closest('.pane');
  const split = document.documentElement.dataset.layout !== 'single' && document.documentElement.dataset.narrow !== '1';
  if (pane && split) {   // scroll only this half, not the whole page
    const jb = pane.querySelector('.jump'), off = jb ? jb.offsetHeight + 8 : 8;
    pane.scrollTo({ top: pane.scrollTop + t.getBoundingClientRect().top - pane.getBoundingClientRect().top - off, behavior: beh });
  } else t.scrollIntoView({ behavior: beh, block: 'start' });
  const h = t.matches('h1,h2') ? t : (t.querySelector('h2,h1') || t);
  if (h) { if (!h.hasAttribute('tabindex')) h.setAttribute('tabindex', '-1'); h.focus({ preventScroll: true }); }
}
let navRaf = 0, NAVPIN = -1;   // 1.27.3: the section just chosen in the menu stays marked until you scroll yourself
function navPin(i) { NAVPIN = i; navActive(); }
function navFlash(t) {             // a short outline round the section you jumped to, so you can see where it is (also on short pages that cannot scroll)
  const h = t.matches('h1,h2') ? t : (t.querySelector('h2,h1') || t);
  document.querySelectorAll('.sn-flash').forEach(x => x.classList.remove('sn-flash'));
  h.classList.add('sn-flash'); clearTimeout(navFlash.t); navFlash.t = setTimeout(() => h.classList.remove('sn-flash'), 2500);
}
function navActive() {
  cancelAnimationFrame(navRaf);
  navRaf = requestAnimationFrame(() => {
    let cur = 0;
    if (NAVPIN >= 0 && NAVPIN < NAVITEMS.length) cur = NAVPIN;
    else {
      const th = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--top-h')) || 64, line = th + (window.innerHeight - th) * 0.35;
      const se = document.scrollingElement || document.documentElement, panes = [...document.querySelectorAll('.pane')].filter(p => p.scrollHeight > p.clientHeight + 2);
      const atTop = se.scrollTop < 4 && panes.every(p => p.scrollTop < 4);
      const atEnd = se.scrollHeight > se.clientHeight + 2 && se.scrollTop + se.clientHeight >= se.scrollHeight - 4;
      NAVITEMS.forEach((it, i) => { const r = it.el.getBoundingClientRect(); if (r.top <= line && r.bottom > 0) cur = i; });
      if (atEnd) NAVITEMS.forEach((it, i) => { const r = it.el.getBoundingClientRect(); if (r.top < window.innerHeight - 40 && r.bottom > 0 && i > cur) cur = i; });   // the last sections cannot reach the line
      else if (atTop && NAVITEMS[0] && NAVITEMS[0].top) cur = 0;
    }
    document.querySelectorAll('#sn-list a').forEach((a, i) => { if (i === cur) a.setAttribute('aria-current', 'true'); else a.removeAttribute('aria-current'); });
  });
}
const navUnpin = () => { if (NAVPIN >= 0) { NAVPIN = -1; navActive(); } };
window.addEventListener('wheel', navUnpin, { capture: true, passive: true });
window.addEventListener('touchmove', navUnpin, { capture: true, passive: true });
window.addEventListener('pointerdown', e => { if (!e.target.closest('#sidenav,#jumprow,.jump')) navUnpin(); }, { capture: true, passive: true });   // dragging a scroll bar
window.addEventListener('keydown', e => { if (['PageUp', 'PageDown', 'Home', 'End', 'ArrowUp', 'ArrowDown', ' '].includes(e.key) && !e.target.closest('input,textarea,select,#sidenav')) navUnpin(); }, true);
window.addEventListener('scroll', navActive, { capture: true, passive: true });
