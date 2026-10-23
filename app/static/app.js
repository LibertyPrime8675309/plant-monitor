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
  try { const list = await api('GET', '/api/plants'); PCODES = new Map(list.map(p => [p.code, p])); PCODES_AT = Date.now(); } catch (e) { /* links just stay plain text */ }
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
function paintWho() { const n = getName(); document.getElementById('who-name').textContent = n ? 'Editing as ' + n : 'Set your name'; }

// ---------- api ----------
async function api(method, url, body, form) {
  const opts = { method, headers: {} };
  if (method !== 'GET') opts.headers['X-Editor'] = cleanName(getName()) || 'Unknown';
  if (form) opts.body = form;
  else if (body !== undefined) { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
  let r;
  try { r = await fetch(url, opts); } catch (e) { throw new Error('Cannot reach the plant server. Check that the container is running.'); }
  let data = null;
  try { data = await r.json(); } catch (e) { /* not json */ }
  if (!r.ok) { const e = new Error((data && data.error) || ('Request failed (' + r.status + ')')); e.status = r.status; e.data = data; throw e; }
  return data;
}

// ---------- toast, dialog ----------
function toast(msg, isErr) {
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
  const h = location.hash.replace(/^#/, '') || '/';
  const parts = h.split('/').filter(Boolean);
  const nav = parts[0] === 'winter' || parts[0] === 'frost' ? 'winter' : parts[0] === 'weather' ? 'weather' : parts[0] === 'fertilizer' ? 'fertilizer' : parts[0] === 'photos' ? 'photos' : parts[0] === 'labels' ? 'labels' : parts[0] === 'history' ? 'history' : parts[0] === 'backups' ? 'backups' : 'plants';
  document.querySelectorAll('[data-nav]').forEach(a => { if (a.dataset.nav === nav) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); });
  try {
    let view;
    await Promise.all([loadCodes(), loadFrost()]);
    if (!META) { META = await api('GET', '/api/meta'); const v = document.getElementById('app-ver'); if (v && META.version) v.textContent = 'v' + META.version; }
    if (parts[0] === 'plant' && parts[1] && parts[2] === 'edit') view = await viewEdit(decodeURIComponent(parts[1]));
    else if (parts[0] === 'plant' && parts[1]) view = await viewPlant(decodeURIComponent(parts[1]));
    else if (parts[0] === 'new') view = viewForm(null);
    else if (parts[0] === 'winter') view = await viewWinter();
    else if (parts[0] === 'weather') view = await viewWeather();
    else if (parts[0] === 'today') view = await viewToday();
    else if (parts[0] === 'fertilizer') view = await viewFertilizer();
    else if (parts[0] === 'photos') view = await viewPhotos();
    else if (parts[0] === 'labels') view = await viewLabels();
    else if (parts[0] === 'history') view = await viewHistory();
    else if (parts[0] === 'backups') view = await viewBackups();
    else if (parts[0] === 'frost') view = await viewFrost();
    else view = await viewGallery();
    if (my !== token) return;
    app.innerHTML = rend(view.html);
    if (parts[0] !== 'frost' && parts[0] !== 'plant') app.insertAdjacentHTML('afterbegin', rend(frostBanner()));   // plant pages have their own note
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
document.addEventListener('toggle', e => { if (e.target && e.target.id === 'pn-filters') PNOPEN = e.target.open; }, true);
let NAVITEMS = [];
function buildSideNav() {
  const list = document.getElementById('sn-list'); if (!list) return;
  const app = document.getElementById('app'), used = new Set();
  const slug = t => { let b = 'sec-' + t.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40) || 'sec', k = b, i = 2; while (used.has(k) || (document.getElementById(k) && document.getElementById(k).dataset.navid !== '1')) k = b + '-' + i++; used.add(k); return k; };
  NAVITEMS = [];
  const h1 = app.querySelector('h1');
  if (h1) NAVITEMS.push({ el: h1, text: 'Top of the page', id: null, top: true });
  app.querySelectorAll('h2').forEach(h => {
    if (h.closest('dialog,.chart-card,#sidenav') || !h.offsetParent) return;
    const sec = h.closest('section') || h;
    if (!sec.id) { sec.id = slug(h.textContent); sec.dataset.navid = '1'; }
    NAVITEMS.push({ el: sec, head: h, text: h.textContent.trim(), id: sec.id });
  });
  list.innerHTML = rend(html`${NAVITEMS.map((it, i) => html`<li><a href="#${it.id || 'app'}" data-act="navgo" data-i="${i}">${it.text}</a></li>`)}`);
  if (!NAVITEMS.length) list.innerHTML = rend(html`<li class="muted">This page has no sections.</li>`);
  navActive();
}
function scrollToSection(t) {
  const beh = matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', pane = t.closest('.pane');
  const split = document.documentElement.dataset.layout !== 'single' && document.documentElement.dataset.narrow !== '1';
  if (pane && split) {   // scroll only this half, not the whole page
    const jb = pane.querySelector('.jump'), off = jb ? jb.offsetHeight + 8 : 8;
    pane.scrollTo({ top: pane.scrollTop + t.getBoundingClientRect().top - pane.getBoundingClientRect().top - off, behavior: beh });
  } else t.scrollIntoView({ behavior: beh, block: 'start' });
  const h = t.matches('h1,h2') ? t : t.querySelector('h2,h1');
  if (h) { h.setAttribute('tabindex', '-1'); h.focus({ preventScroll: true }); }
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
const G = { q: '', plan: '', health: '', low: false, needs: false, sort: 'code', archived: false };
// the Plants page filters are remembered in this browser and also decide where Previous / Next plant go on plant pages
try { const s = JSON.parse(localStorage.getItem('plantdb.filters') || '{}'); for (const k of ['q', 'plan', 'health', 'low', 'needs', 'sort']) if (k in s && typeof s[k] === typeof G[k]) G[k] = s[k]; } catch (e) { /* defaults */ }
function gSave() { try { localStorage.setItem('plantdb.filters', JSON.stringify({ q: G.q, plan: G.plan, health: G.health, low: G.low, needs: G.needs, sort: G.sort })); } catch (e) { /* not saved */ } }
const gActive = () => !!(G.q.trim() || G.plan || G.health || G.low || G.needs);
const needsYou = p => (p.requests_open || 0) > 0 || (p.id_confidence != null && p.id_confidence < 70);
let ALL = [];
const SORTS = { code: 'Code', health: 'Health, worst first', conf: 'ID confidence, lowest first', updated: 'Recently updated', name: 'Name A to Z' };

function filteredPlants(list) {
  const q = G.q.trim().toLowerCase();
  let r = (list || ALL).filter(p =>
    (!G.plan || p.winter_plan === G.plan) && (!G.health || p.health_rating === G.health) &&
    (!G.low || (p.id_confidence != null && p.id_confidence < 70)) && (!G.needs || needsYou(p)) &&
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
  }[G.sort] || ((a, b) => a.code.localeCompare(b.code));
}
function sheet(p) {
  return html`<a class="sheet" href="#/plant/${enc(p.code)}">
    <div class="mat">${p.photo ? html`<img src="${thumbUrl(p.photo)}" alt="" loading="lazy" decoding="async" width="520" height="650">` : html`<div class="nophoto">No photo yet</div>`}
      <span class="acc">${p.code}</span><div class="bar" style="--hb:${HEALTH_COLOR[p.health_rating] || 'var(--line)'}"></div></div>
    <h3 class="name">${p.common_name}</h3>
    <p class="sci latin">${p.scientific_name || 'Scientific name not set'}</p>
    <div class="tags">${planTag(p.winter_plan)}${healthTag(p.health_rating)}</div>
    ${needsYou(p) ? html`<p class="needs-badge">Needs from you: ${[p.requests_open ? `${p.requests_open} request${p.requests_open === 1 ? '' : 's'}` : '', p.id_confidence != null && p.id_confidence < 70 ? 'ID info' : ''].filter(Boolean).join(', ')}</p>` : ''}
    <div class="meter"><span>ID ${p.id_confidence == null ? 'not rated' : p.id_confidence + '%'}</span><i style="--v:${p.id_confidence || 0}%;--mc:${confColor(p.id_confidence)}"></i></div>
  </a>`;
}
function drawGrid() {
  gSave();
  if (!document.getElementById('grid')) { drawPnav(); return; }
  const r = filteredPlants();
  document.getElementById('count').textContent = r.length + ' of ' + ALL.length + ' plants shown';
  document.getElementById('grid').innerHTML = r.length
    ? rend(r.map(sheet))
    : rend(html`<div class="empty" style="grid-column:1/-1"><p>No plants match these filters.</p><button class="btn ghost" type="button" data-act="clearfilters">Clear filters</button></div>`);
}
function ledger() {
  const n = pl => ALL.filter(p => p.winter_plan === pl).length;
  return html`${META.winter_plans.map(pl => html`<button type="button" data-act="plan" data-plan="${pl}" style="--bar:${PLAN_COLOR[pl]}" aria-pressed="${String(G.plan === pl)}"><b>${n(pl)}</b>${pl}</button>`)}`;
}
async function viewGallery() {
  ALL = await api('GET', '/api/plants' + (G.archived ? '?status=archived' : ''));
  const lowN = ALL.filter(p => p.id_confidence != null && p.id_confidence < 70).length;
  const needN = ALL.filter(needsYou).length;
  let todoN = 0, fcN = 0;
  await Promise.all([api('GET', '/api/to-photograph').then(t => { todoN = t.filter(x => !x.done).length; }).catch(() => {}),
    api('GET', '/api/for-claude?range=last').then(d => { fcN = d.counts.answers; }).catch(() => {})]);
  return {
    title: '',
    html: html`<div class="hero"><div><h1>${G.archived ? 'Archived plants' : 'Outdoor plants'}</h1>
      <p class="muted">${META.counts.plants} plants and ${META.counts.photos} photos in Round Rock, Texas. Each plant has its own page, version number and change log.</p></div>
      <a class="btn" href="#/new">Add a plant</a></div>
    <div class="needs-bar" role="group" aria-label="What Claude needs from you">
      <button type="button" class="btn ${G.needs ? '' : 'ghost'}" data-act="needs" aria-pressed="${String(G.needs)}">${G.needs ? 'Showing plants that need something from you' : 'Show plants that need something from you'} (${needN})</button>
      <span class="hint">Questions, checks, photos and ID details I am waiting for. ${todoN ? html`Plus <a href="#/photos">${todoN} things to photograph</a> that are not in the database yet.` : ''}</span>
      <button type="button" class="btn ghost" data-act="forclaude"><span>Copy my answers for Claude${fcN ? html`<span class="fc-n"> (${fcN} new)</span>` : ''}</span></button></div>
    <div class="ledger" role="group" aria-label="Filter by winter plan">${ledger()}</div>
    <div class="filters">
      <label>Search<input type="search" data-f="q" value="${G.q}" placeholder="Name, code, location"></label>
      <label>Health<select data-f="health"><option value="">Any</option>${META.health.map(h => html`<option ${G.health === h ? raw('selected') : ''}>${h}</option>`)}</select></label>
      <label>Sort by<select data-f="sort">${Object.entries(SORTS).map(([k, v]) => html`<option value="${k}" ${G.sort === k ? raw('selected') : ''}>${v}</option>`)}</select></label>
      <label class="chk"><input type="checkbox" data-f="low" ${G.low ? raw('checked') : ''}>ID confidence under 70% (${lowN})</label>
    </div>
    <p id="count" class="muted" aria-live="polite"></p>
    <div class="grid" id="grid"></div>
    <p style="margin-top:36px"><label class="chk" style="display:inline-flex;gap:8px;align-items:center"><input type="checkbox" data-f="archived" ${G.archived ? raw('checked') : ''} style="width:20px;height:20px;margin:0">Show archived plants instead</label></p>`,
    after: drawGrid,
  };
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
const keyOf = items => html`<div class="key" aria-hidden="true">${items.map(i => html`<span class="${i[0]}">${i[1]}</span>`)}</div>`;

const TEMP_MARKS = [['A', 20, 'Round Rock design low'], ['B', 32, 'Freezing'], ['C', 38, 'Typical January night']];
const HUM_MARKS = [['D', 71, 'Outdoors, November to February (average)'], ['E', 30, 'Indoors with the heater running']];
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
    ${strip(zones, TEMP_MARKS.map(m => [m[1], m[0]]), [0, 20, 40, 60, 80, 100].map(x => [x, x + '°']), now)}
    ${keyOf([['z-fatal', 'Likely fatal'], ['z-damage', 'Damage'], ['z-cool', 'Cool but safe'], ['z-ok', 'Comfortable'], ['z-hot', 'Too hot'], ...(ha != null ? [['z-heat', 'Heat damage']] : []), ...(now ? [['z-now', 'Now']] : [])])}
    <ul class="verdicts">${TEMP_MARKS.map(m => { const [k, txt] = tempVerdict(p, m[1]); return html`<li class="v-${k}"><span class="k">${m[0]}</span><span><strong>${m[2]}, ${m[1]}°F.</strong> ${txt}</span></li>`; })}</ul>`;
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
    ${strip([['z-dry', a], ['z-ok', b - a], ['z-wet', 100 - b]], HUM_MARKS.map(m => [m[1], m[0]]), [0, 25, 50, 75, 100].map(x => [x, x + '%']), h == null ? null : { pos: posLin(h, 0, 100), label: h + '%' })}
    ${keyOf([['z-dry', 'Too dry'], ['z-ok', 'Comfortable'], ['z-wet', 'Too humid'], ...(h != null ? [['z-now', 'Now']] : [])])}
    <ul class="verdicts">${HUM_MARKS.map(m => { const [k, txt] = verdict(m[1]); return html`<li class="v-${kk(k)}"><span class="k">${m[0]}</span><span><strong>${m[2]}, about ${m[1]}%.</strong> ${txt}</span></li>`; })}</ul>
    ${paras(p.humidity_notes)}`;
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
    else if (PH > p.soil_ph_high) { level = 'near'; state = 'Soil too alkaline'; detail = `pH ${PH} is above ${p.soil_ph_high}.`; steps = ['Water with rain water, because Round Rock tap water is alkaline.', 'Feed with an acid-type fertilizer, and add chelated iron if new leaves are pale with green veins.', 'Or repot into fresh mix, with pine bark or peat added.']; }
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
      <p class="cap">${cur.caption || 'No caption'}${cur.is_primary ? ' (main photo)' : ''}. Added ${when(cur.added_at)} by ${cur.added_by}.</p>`
      : html`<div class="empty">No photos yet. Add one below.</div>`}
    ${ph.length > 1 ? html`<div class="thumbs">${ph.map((x, j) => html`<button type="button" data-act="pick" data-i="${j}" aria-label="Photo ${j + 1} of ${ph.length}" aria-current="${String(j === i)}"><img src="${thumbUrl(x.file)}" alt=""></button>`)}</div>` : ''}
    <div class="row noprint">
      ${cur && !cur.is_primary ? html`<button class="btn ghost small" type="button" data-act="mainphoto">Make main photo</button>` : ''}
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
const JUMPS = [['needs', 'Needed'], ['sec-now', 'Now'], ['ident', 'Identification'], ['temp', 'Temperature'], ['hum', 'Humidity'], ['light', 'Light'], ['soil', 'Water and soil'], ['nutrients', 'Nutrients'], ['winter', 'Winter'], ['health', 'Health'], ['pests', 'Pests'], ['label', 'Label'], ['history', 'History']];
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
      <div class="pane" id="pane-l" tabindex="0" role="region" aria-label="Photos"><div id="photopanel">${photoPanel(p)}</div></div>
      <div class="pane" id="pane-r" tabindex="0" role="region" aria-label="Details">
        <nav class="jump noprint" aria-label="Jump to a section">${JUMPS.filter(j => j[0] !== 'needs' || (p.requests || []).length || (p.id_confidence != null && p.id_confidence < 70)).map(j => html`<button class="btn ghost small" type="button" data-act="jump" data-id="${j[0]}">${j[1]}</button>`)}</nav>
        <div class="label">
          <div class="l-top"><b>${p.code}</b><span>Page version ${p.version}</span><span>Updated ${timeEl(p.updated_at)} by ${p.updated_by}</span></div>
          <div class="l-body"><h1>${p.common_name}</h1><p class="sci latin">${p.scientific_name || 'Scientific name not set'}</p>
            <dl><dt id="site-lbl">Location</dt><dd>${sitePicker(p)}</dd>
              ${dl.map(x => html`<dt>${x[0]}</dt><dd>${x[1]}</dd>`)}
              <dt>ID confidence</dt><dd>${p.id_confidence == null ? 'Not rated' : p.id_confidence + '%'}</dd>
              <dt>Winter plan</dt><dd>${planTag(p.winter_plan)}</dd><dt>Health</dt><dd>${healthTag(p.health_rating)}</dd></dl>
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

        <section class="blk" id="temp"><h2>Temperature</h2>${tempBlock(p, cur)}${paras(p.temp_notes)}${histBlock('temp')}</section>
        <section class="blk" id="hum"><h2>Humidity</h2>${humBlock(p, cur)}${histBlock('hum')}</section>
        <section class="blk" id="light"><h2>Sunlight</h2>${lightBlock(p, cur)}${histBlock('light')}</section>
        <section class="blk" id="soil"><h2>Water and soil</h2><div id="care-plant"><p class="loading">Loading the watering record</p></div>${soilBlock(p, cur)}${histBlock('soil')}</section>
        <section class="blk" id="nutrients"><h2>Nutrients</h2>
          ${p.fertilizer ? html`<p><strong>Fertilizer:</strong> ${p.fertilizer}</p>` : ''}${paras(p.nutrients)}
          ${!p.fertilizer && !p.nutrients ? html`<p class="muted">Not filled in yet. Use Edit to add it.</p>` : ''}
          <h3>Feeding schedule and log</h3><div id="fert-plant"><p class="loading">Loading</p></div></section>

        <section class="blk" id="winter"><h2>Winter in Round Rock</h2>
          <p>${planTag(p.winter_plan)}</p>${paras(p.winter_summary)}
          ${p.winter_triggers ? html`<h3>When to act</h3>${paras(p.winter_triggers)}` : ''}
          ${lines(p.winter_steps).length ? html`<h3>Steps</h3>${ol(p.winter_steps)}` : ''}
          ${lines(p.indoor_setup).length ? html`<h3>Keeping it comfortable when the weather cannot</h3>${ul(p.indoor_setup)}` : ''}</section>

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
    after: () => { fitPanes(); loadFertPlant(); loadCarePlant(); pnavLayout(); setTimeout(pnavLayout, 300); },
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
    </div></div>`;
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
  box.innerHTML = rend(html`<div class="verdict-box v-${w && w.state === 'due' ? 'due' : 'wait'}" role="status"><h3>Watering</h3><p>${w ? waterWords(w) : ''}</p>
      <p class="hint">Change the gap with "Check for water every (days)" in Edit this page. Rain of ${W.rain_counts_in} in or more counts as a watering for plants whose Location is Outdoors.</p></div>
    <h3>Care log</h3>${log.length ? html`<ul class="care-log">${log.map(e => html`<li><strong>${CARE_WORD[e.kind] || e.kind}</strong> ${relDay(e.done_on)}${e.note ? ': ' + e.note : ''} <span class="muted">(${e.created_by})</span>
      <button class="btn small ghost noprint" type="button" data-act="caredel" data-id="${e.id}" data-what="${(CARE_WORD[e.kind] || e.kind) + ' ' + relDay(e.done_on)}">Remove</button></li>`)}</ul>`
      : html`<p class="muted">Nothing logged yet. Use the buttons near the top of the page.</p>`}`);
}
async function careDialog(code, name) {
  if (!(await needName())) return;
  const r = await modal(html`<form method="dialog"><h2>Log care for ${name}</h2>
    <label class="f">What did you do?<select name="kind">${Object.entries(CARE_WORD).map(([k, v]) => html`<option value="${k}" ${k === 'repot' ? raw('selected') : ''}>${v}</option>`)}</select></label>
    <label class="f">When<input type="date" name="day" value="${todayStr()}" max="${todayStr()}"></label>
    <label class="f">Note (optional)<input type="text" name="note" maxlength="500" placeholder="For example: moved to a 10 inch pot"></label>
    <div class="row"><button class="btn" value="ok">Save</button><button class="btn ghost" value="cancel">Cancel</button></div></form>`);
  if (r !== 'ok') return;
  const f = dlg.querySelector('form');
  await guard(async () => { await api('POST', '/api/care', { plant: code, kind: f.elements.kind.value, done_on: f.elements.day.value, note: f.elements.note.value }); toast('Saved: ' + CARE_WORD[f.elements.kind.value]); await careRefresh(code); });
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
async function viewToday() {
  const [W, reqs] = await Promise.all([api('GET', '/api/water'), api('GET', '/api/requests?open=1'), loadFertData(true)]);
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
  const h = Math.max(window.innerHeight - topAbs - 12, 360);            // the two halves fill the window exactly, so the page itself never scrolls
  pl.style.setProperty('--pane-h', h + 'px');
}
function repaintPhotos() { const el = document.getElementById('photopanel'); if (el) el.innerHTML = rend(photoPanel(CUR.p)); }
async function reloadPlant(idx) { KEEP = idx == null ? PIDX : idx; await route(); }
const curPhoto = () => CUR.p.photos[clamp(PIDX, 0, CUR.p.photos.length - 1)];

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
const todayStr = () => ymd(new Date());

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
const FERT = { entries: [], products: [], plants: [], forecast: [] };
async function loadFertData(withPlants) {
  const [entries, products, W] = await Promise.all([api('GET', '/api/fertilizer'), api('GET', '/api/fertilizer/products'), api('GET', '/api/weather').catch(() => null)]);
  FERT.entries = entries; FERT.products = products; FERT.forecast = (W && W.forecast && W.forecast.days) || [];
  if (withPlants) FERT.plants = await api('GET', '/api/plants');
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
  try { await loadFertData(false); } catch (e) { box.innerHTML = rend(html`<p class="notice bad">Could not load feeding data: ${e.message}</p>`); return; }
  const es = entriesFor(p.code), today = todayStr(), st = fertState(p, es, today, fertCtx()), nd = nextDue(p, es);
  const prevSel = CALS.fp && CALS.fp.sel;
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
  const rowHtml = r => html`<li>${r.p.photo ? html`<img src="${thumbUrl(r.p.photo)}" alt="" loading="lazy">` : html`<span></span>`}
    <span><a class="nm" href="#/plant/${enc(r.p.code)}">${r.p.common_name}</a><br><span class="muted">${r.p.code}. ${r.st.state === 'rest' ? 'Season opens ' + midDay(r.st.until) + '.' : r.st.state === 'hold' ? r.st.reason : r.st.state === 'unknown' ? '' : r.st.last ? `Last fed ${r.st.since} days ago.${r.st.state === 'wait' || r.st.state === 'fed' ? ' Next about ' + midDay(r.st.next) + '.' : r.st.over > 0 ? ' ' + r.st.over + ' days overdue.' : ''}` : 'Never logged.'}</span></span>
    <button class="btn ghost small noprint" type="button" data-act="fertlog" data-code="${r.p.code}">Log</button></li>`;
  const q = k => grp(k).length;
  return {
    title: 'Fertilizer',
    html: html`<h1>Fertilizer</h1>
    <p class="muted">When to feed each plant, and a record of what you used. Every plant has its own feeding season for Round Rock (months it is growing) and a gap between feedings. Change them on a plant's Edit page.</p>
    <div class="verdict-box" role="status"><h2 style="margin:0 0 .4rem">Today, ${longDay(t)}</h2>
      <p>${q('due')} plant${q('due') === 1 ? ' is' : 's are'} due for fertilizer${q('hold') ? `, ${q('hold')} should wait because of cold or health` : ''}. ${q('wait')} ${q('wait') === 1 ? 'was' : 'were'} fed recently and ${q('rest')} ${q('rest') === 1 ? 'is' : 'are'} resting for the season.</p>
      <div class="row noprint"><button class="btn" type="button" data-act="fertlog">Log fertilizer</button>${q('due') ? html`<button class="btn ghost" type="button" data-act="fertlog" data-group="due">Log fertilizer for the ${q('due')} due plants</button>` : ''}</div></div>
    ${G5.map(([k, title, open]) => grp(k).length ? html`<details class="grp" ${open ? raw('open') : ''}><summary><h2>${title} (${grp(k).length})</h2></summary><ul class="todo">${grp(k).map(rowHtml)}</ul></details>` : '')}
    <section class="blk"><h2>Calendar for all plants</h2><div id="cal-fa"></div><div id="fa-day"></div></section>
    <section class="blk"><h2>Fertilizers you have used</h2>${FERT.products.length ? html`<div class="tbl-wrap"><table class="tbl"><thead><tr><th>Name</th><th>N-P-K</th><th>Type</th><th>Last dose</th></tr></thead><tbody>
      ${FERT.products.map(x => html`<tr><th scope="row">${x.product}</th><td>${npkText(x)}${ratioText(x.n, x.p, x.k) ? html`<div class="hint">ratio ${ratioText(x.n, x.p, x.k)}</div>` : ''}</td><td>${x.form}</td><td>${doseText(x)}</td></tr>`)}</tbody></table></div>` : html`<p class="muted">None yet. The first one you log is remembered here and fills in the form next time.</p>`}</section>
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
  ['Temperature', ['temp_ideal_low', 'temp_ideal_high', 'temp_damage_below', 'temp_lethal_below', 'temp_damage_above', 'temp_notes']],
  ['Humidity and air dryness', ['humidity_low', 'humidity_high', 'vpd_low', 'vpd_high', 'humidity_notes']],
  ['Sunlight', ['light_summary', 'light_hours', 'par_low', 'par_high', 'dli_low', 'dli_high', 'light_notes']],
  ['Water and soil', ['water_every_days', 'water_notes', 'soil_medium', 'soil_ph_low', 'soil_ph_high', 'soil_moisture_low', 'soil_moisture_high', 'soil_temp_low', 'soil_temp_high']],
  ['Nutrients', ['fertilizer', 'nutrients', 'fert_from_month', 'fert_to_month', 'fert_every_days']],
  ['Winter plan', ['winter_plan', 'winter_summary', 'winter_triggers', 'winter_steps', 'indoor_setup']],
  ['Health', ['health_rating', 'health_summary', 'health_observations', 'health_steps']],
  ['Pests and diseases', ['pests_watch', 'pest_steps', 'pests_current']],
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
  winter_steps: 'One step per line, in order.', health_steps: 'One step per line, in order.', indoor_setup: 'One item per line.',
};
const rangeOf = n => (META.int_ranges && META.int_ranges[n]) || (META.num_ranges && META.num_ranges[n]) || [-60, 150];
function fieldInput(f, val) {
  const hint = HINTS[f.name] || (f.kind === 'list' ? 'One item per line.' : '');
  const wide = (f.kind === 'long' || f.kind === 'list') ? 'wide' : '';
  const v = val == null ? '' : val;
  let inp;
  if (f.kind === 'long' || f.kind === 'list') inp = html`<textarea name="${f.name}" rows="${f.kind === 'list' ? 5 : 4}">${v}</textarea>`;
  else if (f.kind === 'int') { const mm = rangeOf(f.name); inp = html`<input type="number" inputmode="numeric" step="1" min="${mm[0]}" max="${mm[1]}" name="${f.name}" value="${v}">`; }
  else if (f.kind === 'num') { const mm = rangeOf(f.name); inp = html`<input type="number" inputmode="decimal" step="any" min="${mm[0]}" max="${mm[1]}" name="${f.name}" value="${v}">`; }
  else if (f.kind === 'enum') { const opts = f.name === 'winter_plan' ? META.winter_plans : f.name === 'site' ? (META.sites || ['Outdoors', 'Indoors']) : META.health; if (f.name === 'site' && !v) v = 'Outdoors'; inp = html`<select name="${f.name}">${opts.map(o => html`<option ${o === v ? raw('selected') : ''}>${o}</option>`)}</select>`; }
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
      ${GROUPS.map(([title, names]) => html`<fieldset><legend>${title}</legend><div class="field-grid">${names.map(n => fieldInput(F[n], p ? p[n] : (n === 'winter_plan' ? 'Move indoors' : n === 'health_rating' ? 'Fair' : '')))}</div></fieldset>`)}
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
      toast('Added ' + p.code); go('#/plant/' + enc(p.code));
    } else {
      const r = await api('PUT', '/api/plants/' + enc(form.dataset.code), { base_version: +form.dataset.ver, fields, note: fd.get('__note') || '' });
      toast(r.changed ? 'Saved as version ' + r.version : 'Nothing was changed'); go('#/plant/' + enc(form.dataset.code));
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
function seasonTable(ref, monthly) {
  const obs = Object.fromEntries((monthly || []).map(x => [x.month, x]));
  const exp = Object.fromEntries((ref.climate || []).map(c => [c.month, c]));
  const keys = seasonKeys();
  return html`<div class="tbl-wrap"><table class="tbl"><caption class="sr">Expected weather compared with the weather tracked so far this season</caption>
    <thead><tr><th>Month</th><th>Expected low and high</th><th>Tracked low and high</th><th>Expected freezing nights</th><th>Tracked freezing nights</th><th>Expected humidity</th><th>Tracked humidity</th></tr></thead><tbody>
    ${keys.map(([mo, key]) => { const e = exp[mo] || {}, o = obs[key];
      return html`<tr><th scope="row">${mo}</th><td>${e.low != null ? e.low + ' to ' + e.high + '°F' : ''}</td>
        <td>${o ? html`${o.low} to ${o.high}°F<div class="hint">${o.days} days tracked</div>` : html`<span class="muted">Not tracked yet</span>`}</td>
        <td>${e.freeze_nights != null ? e.freeze_nights + ' on average' : ''}</td><td>${o ? o.freeze_nights + (o.days < 28 ? ' so far' : '') : ''}</td>
        <td>${e.rh != null ? e.rh + '% morning, ' + e.rh_pm + '% afternoon' : ''}</td><td>${o && o.rh != null ? Math.round(o.rh) + '% average' : ''}</td></tr>`; })}</tbody></table></div>`;
}
function forecastBlock(W, plants) {
  const days = (W.forecast && W.forecast.days) || [];
  if (!days.length) return html`<p class="muted">No forecast yet. ${W.status && W.status.error ? 'The last attempt failed: ' + W.status.error : 'The first update runs a few seconds after the app starts, then every hour.'}</p>`;
  const risk = low => plants.filter(p => p.temp_damage_below != null && low < p.temp_damage_below && !isInside(p));
  const away = W.location && W.home && !W.location.is_home;
  const coldest = days.reduce((a, b) => (b.low < a.low ? b : a));
  const rs = risk(coldest.low);
  const dName = d => new Date(d + 'T12:00:00').toLocaleDateString([], { weekday: 'long', month: 'short', day: 'numeric' });
  return html`<p class="${coldest.low <= 32 ? 'notice bad' : coldest.low <= 38 ? 'notice' : 'notice ok'}" role="status"><strong>Coldest night in the forecast: ${coldest.low}°F on ${dName(coldest.date)}.</strong>
      ${coldest.low <= 32 ? ' That is a freeze.' : coldest.low <= 38 ? ' Frost is possible in low spots.' : ' No frost expected.'}
      ${rs.length ? ` ${rs.length} of ${plants.filter(p => !isInside(p)).length} plants outside would be damaged by that if they were left outside uncovered${away ? ' there' : ''}.` : ' None of your plants would be damaged by that.'}${away ? ` (Your plants are at ${W.home.name}; this shows what this weather would do to them.)` : ''}</p>
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
  catch (e) { if (e.status === 404) { WXP = null; try { localStorage.removeItem('plantdb.wxplace'); } catch (x) { /* ignore */ } W = await api('GET', '/api/weather'); } else throw e; }
  const [cond, plants, ing, monthly, ref, st] = await Promise.all([loadCond(), api('GET', '/api/plants'), api('GET', '/api/ingest'), api('GET', '/api/weather/monthly?x=1' + locQS()), api('GET', '/api/reference'), api('GET', '/api/settings')]);
  WX.places = W.places || []; WX.place = W.location; WX.home = W.home;
  WX.compare = WX.compare.filter(id => WX.places.some(p => String(p.id) === id && String(p.id) !== String(W.location.id)));
  const atHome = W.location.is_home;
  const base = st.base_url || location.origin, isLocal = /^https?:\/\/(localhost|127\.|\[::1\])/i.test(base);
  const url = base.replace(/\/$/, '') + '/api/readings';
  const sample = '{"device":"porch","temp_f":71.2,"humidity":58,"par":240,"soil_moisture":31}';
  const S = W.status || {};
  return {
    title: 'Weather',
    html: html`<h1>Weather and sensors</h1>
    <p class="muted">Tracks the weather for ${WX.places.length > 1 ? `${WX.places.length} places` : W.location.name} from Open-Meteo (free, no account), and takes readings from your own sensors. Everything is stored in your data folder, so the history keeps growing.</p>
    <div class="placebar noprint" role="group" aria-label="Place">
      <label>Showing the weather for<select data-f="wxplace">${WX.places.map(p => html`<option value="${p.id}" ${String(p.id) === String(W.location.id) ? raw('selected') : ''}>${p.name}${p.is_home ? ' (home, where your plants are)' : ''}</option>`)}</select></label>
      <a class="btn small ghost" href="#sec-places" data-act="gotoplaces">Add or manage places</a>
      ${atHome ? '' : html`<p class="hint" style="flex-basis:100%;margin:0">Your plants are at ${W.home.name}, so plant pages, current conditions and the Winter plan keep using ${W.home.name}.</p>`}</div>
    ${condCard(null, cond)}
    <section class="blk"><h2>Next 7 days${atHome ? '' : ` in ${W.location.name}`}</h2>${forecastBlock(W, plants)}</section>
    <section class="blk"><h2>Tracked history</h2>
      ${wxControls(plants)}
      <div id="wx-charts"><p class="loading">Loading charts</p></div>
      <p class="hint">${W.weather.count ? `Online weather: ${W.weather.count.toLocaleString()} hourly readings from ${when(W.weather.first)}.` : 'No online weather stored yet.'}
        ${W.sensor.count ? ` Your sensor: ${W.sensor.count.toLocaleString()} readings from ${W.sensor.devices} device${W.sensor.devices === 1 ? '' : 's'}.` : ' No sensor readings yet (see Connect your sensor, below).'}</p></section>
    <section class="blk" id="wx-logged"><h2>All logged weather data${WX.places.length > 1 ? `: ${W.location.name}` : ''}</h2>
      <p class="hint">Every value saved so far, as a table. The first three columns (temperature, humidity, plant light) go back as far as your history does. The other measurements are kept hourly ${W.weather.detail_since ? 'from ' + dayLong(W.weather.detail_since) : 'once collected'} and as daily summaries for all of it.</p>
      ${wtControls()}<div id="wx-table"><p class="loading">Loading table</p></div></section>
    <section class="blk"><h2>Expected and tracked this season${atHome ? '' : ` (tracked: ${W.location.name})`}</h2>${seasonTable(ref, monthly)}
      <p class="hint">Expected values are 30-year averages for ${W.home.name}${atHome ? '' : `; the tracked columns are ${W.location.name}`}. Tracked values come from the readings above: the average of each day's low and high, and how many nights fell to 32°F or below. Days with fewer than 12 readings are skipped.</p></section>
    <section class="blk" id="sensor"><h2>Connect your sensor</h2>
      <p>A sensor on your network can send readings to this app. Each reading becomes part of the history above, and "My sensor" can drive the current conditions on every plant page.</p>
      ${isLocal ? html`<div class="notice">The address below uses <strong>${base}</strong>, which only works on this computer. A sensor on another device needs this computer's network address instead (for example http://192.168.1.20:8080). Set it on the Labels page; the README shows how to find it.</div>` : ''}
      <dl class="dl"><dt>Address</dt><dd><span class="code">${url}</span></dd><dt>Token</dt><dd><span class="code" id="tok">${ing.token}</span></dd></dl>
      <div class="row noprint" style="margin:.8rem 0"><button class="btn small" type="button" data-act="copytok">Copy token</button><button class="btn danger small" type="button" data-act="tokregen">Make a new token</button></div>
      <p>Send a POST with the header <span class="code">X-Ingest-Token</span> and a JSON body. Every field except one measurement is optional: <span class="code">device</span> (a name, such as porch), <span class="code">ts</span> (UTC time, otherwise now), <span class="code">temp_f</span> or <span class="code">temp_c</span>, <span class="code">humidity</span> (%), <span class="code">par</span> (µmol/m²/s) or <span class="code">lux</span>, <span class="code">soil_moisture</span> (%), <span class="code">soil_temp_f</span> or <span class="code">soil_temp_c</span>, <span class="code">soil_ph</span>. Send up to 500 at once as <span class="code">{"readings":[ ... ]}</span>. Lux is converted to PAR at 54 lux per PAR.</p>
      <h3>Try it from this computer</h3>
      <p>Windows (cmd.exe):</p><pre class="code">curl -X POST ${url} -H "X-Ingest-Token: ${ing.token}" -H "Content-Type: application/json" -d "{\\"device\\":\\"porch\\",\\"temp_f\\":71.2,\\"humidity\\":58,\\"par\\":240}"</pre>
      <p>Windows (PowerShell):</p><pre class="code">Invoke-RestMethod -Method Post -Uri ${url} -Headers @{"X-Ingest-Token"="${ing.token}"} -ContentType "application/json" -Body '${sample}'</pre>
      <p>macOS / Linux (bash):</p><pre class="code">curl -X POST ${url} -H "X-Ingest-Token: ${ing.token}" -H "Content-Type: application/json" -d '${sample}'</pre>
      <p class="hint">Anyone on your network who has the token can add readings, so keep it private. If it leaks, make a new token and update your sensor.</p></section>
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
let WXP = null;                     // the place the Weather page shows (null = home); remembered on this computer
try { WXP = localStorage.getItem('plantdb.wxplace') || null; } catch (e) { /* ignore */ }
const locQS = () => WXP ? '&loc=' + enc(WXP) : '';
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
  return html`<p>Track the weather for as many places as you like. Each place keeps its own hourly readings, daily summaries, forecast and update log. The home place is where your plants are: plant pages, current conditions and the Winter plan use it.</p>
    <div class="tbl-wrap"><table class="tbl"><caption class="sr">Places with tracked weather</caption><thead><tr><th scope="col">Place</th><th scope="col">Where</th><th scope="col">Stored</th><th scope="col">Last update</th><th scope="col">Hourly updates</th><th scope="col"><span class="sr">Actions</span></th></tr></thead><tbody>
    ${P.map(p => html`<tr><th scope="row">${p.name}${p.is_home ? html`<div><strong class="tag-home">Home (your plants)</strong></div>` : ''}${String(p.id) === String(W.location.id) ? html`<div class="hint">Shown on this page</div>` : ''}</th>
      <td>${p.lat}, ${p.lon}<div class="hint">${p.tz}</div></td>
      <td>${p.count ? `${num(p.count)} hourly readings from ${dayLong((p.first || '').slice(0, 10))}` : 'Nothing yet'}${p.daily_count ? html`<div class="hint">${num(p.daily_count)} daily summaries</div>` : ''}</td>
      <td>${p.last_update ? html`${when(p.last_update)}${p.last_ok === false ? html`<div class="bad-text"><strong>Failed:</strong> ${p.last_error}</div>` : ''}` : 'Not yet'}</td>
      <td>${p.enabled ? 'On' : 'Off'}</td>
      <td><div class="row" style="gap:.4rem">
        ${String(p.id) === String(W.location.id) ? '' : html`<button class="btn small" type="button" data-act="placeshow" data-id="${p.id}">Show</button>`}
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
    WXP = String(r.place.id); try { localStorage.setItem('plantdb.wxplace', WXP); } catch (e) { /* ignore */ }
    toast(`${r.place.name} added. Fetching its last 3 months and forecast now.`);
    document.body.dataset.job = '1'; await route(); wxPoll();
  });
}
function setPlace(id) {
  WXP = id ? String(id) : null;
  try { if (WXP) localStorage.setItem('plantdb.wxplace', WXP); else localStorage.removeItem('plantdb.wxplace'); } catch (e) { /* ignore */ }
  WT.page = 1; WX.compare = WX.compare.filter(x => x !== WXP);
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
  if (!j || !j.running) { if (b) b.remove(); return; }
  if (!b) { b = document.createElement('a'); b.id = 'job-badge'; b.href = '#/weather'; b.className = 'noprint'; document.body.appendChild(b); }
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
  if (WXP) q.set('loc', WXP);
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
    <p class="fz-title" id="fz-h">${!real ? 'Cold night ahead' : W.low <= 36 ? 'Frost warning' : 'Cold warning'}: down to ${W.low}°F ${fzDay(W.date, true)}</p>
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
    html: html`<h1>Winter plan</h1><p class="muted">What to expect in Round Rock from October to March, when to act, and which plants go where.</p>
    <section class="blk"><h2>The next 7 days</h2>${forecastBlock(W, list)}<p class="row"><a class="btn small" href="#/frost">Open the cold-night checklist</a><a class="btn ghost small" href="#/weather">Open the Weather page for charts and sensors</a></p></section>
    <section class="blk"><h2>Expected and tracked this season</h2>${seasonTable(ref, monthly)}
      ${(ref.notes || []).map(n => html`<p class="hint">${n}</p>`)}</section>
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
      <ul class="todo winter-list inside-list">${ins.map(p => html`<li>${p.photo ? html`<img src="${thumbUrl(p.photo)}" alt="" loading="lazy">` : html`<span></span>`}
        <span><a class="nm" href="#/plant/${enc(p.code)}">${p.common_name}</a><br><span class="muted">${p.code}, ${p.site.toLowerCase()}, plan: ${p.winter_plan}</span>
        <br><button class="btn small ghost noprint" type="button" data-act="moveout" data-code="${p.code}" data-name="${p.common_name}">Moved back outside</button></span></li>`)}</ul>` : html`<p class="hint">When you bring a plant in, press its Moved indoors button. It leaves these lists and the frost warnings, and its page shows Location: Indoors.</p>`; })()}
    </section>
    ${(ref.sources || []).length ? html`<section class="blk"><h2>Sources</h2><ul>${ref.sources.map(s => html`<li><a href="${s[1]}" target="_blank" rel="noopener noreferrer">${s[0]}</a></li>`)}</ul></section>` : ''}`,
  };
}

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
    ${group('keys', 'Keyboard shortcuts', [['1', 'On'], ['0', 'Off']], 'R reads the page aloud, [ and ] go to the previous and next plant, ? lists them all.')}
    <div class="row"><button class="btn" value="ok" autofocus>Done</button><button class="btn ghost" type="button" data-act="prefreset">Reset to defaults</button></div></form>`);
}
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
      ${k('H', 'Go to the Plants page')}${k('M', 'Open or fold the section menu')}${k('?', 'Show this list')}
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
      ${local ? html`<div class="notice">The codes currently point to <strong>${base}</strong>, which only works on this computer. A phone cannot open that. Type your computer's network address here, for example http://192.168.1.20:8080 (the README shows how to find it).</div>` : html`<div class="notice ok">Codes open ${base}. The phone must be on the same Wi-Fi as this computer.</div>`}
      <p><button class="btn" type="button" data-act="print">Print labels</button></p></div>
    <div class="lsheet">${list.map(p => labelCard(p, base, true))}</div>`,
  };
}

// ---------- change log page ----------
let LOG = [];
function logRows(q) {
  q = (q || '').trim().toLowerCase();
  const rows = LOG.filter(a => !q || [a.plant_code, a.changed_by, a.label, a.field, a.action, a.note, a.old_value, a.new_value].join(' ').toLowerCase().includes(q));
  return rows.length ? html`<div class="tbl-wrap"><table class="tbl"><thead><tr><th>When</th><th>Plant</th><th>Version</th><th>By</th><th>What</th><th>Before</th><th>After</th></tr></thead><tbody>
    ${rows.map(a => html`<tr><td>${timeEl(a.changed_at)}</td><td>${a.plant_code ? html`<a href="#/plant/${enc(a.plant_code)}">${a.plant_code}</a>` : 'Setting'}</td><td>${a.version == null ? '' : a.version}</td><td>${a.changed_by}</td>
      <td>${a.label || a.action}${a.note && !a.field ? html`<div class="muted">${a.note}</div>` : ''}</td><td class="old">${a.old_value || ''}</td><td class="new">${a.new_value || ''}</td></tr>`)}</tbody></table></div>`
    : html`<div class="empty">No matching changes.</div>`;
}
async function viewHistory() {
  LOG = await api('GET', '/api/audit?limit=500');
  return {
    title: 'Change log',
    html: html`<div class="hero"><div><h1>Change log</h1><p class="muted">Every edit to every plant: what changed, what it was before, who did it and when. Newest first. Times are shown in your time zone.</p></div>
      <div class="row noprint"><a class="btn ghost small" href="/api/audit.csv">Download change log (CSV)</a><a class="btn ghost small" href="/api/export.csv">Download plants (CSV)</a><a class="btn ghost small" href="/api/readings.csv">Download weather and sensor readings (CSV)</a><a class="btn ghost small" href="/api/export.json">Download everything (JSON)</a></div></div>
    <label class="f noprint" style="max-width:420px">Filter<input type="search" data-f="logq" placeholder="Plant code, name of editor, field"></label>
    <div id="logbody">${logRows('')}</div>`,
  };
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
  async who() { await askName(true); },
  fertlog(el) {
    const o = {};
    if (el.dataset.code) o.codes = [el.dataset.code];
    if (el.dataset.date) o.date = el.dataset.date;
    if (el.dataset.group === 'due') { const t = todayStr(); o.codes = FERT.plants.filter(p => fertState(p, entriesFor(p.code), t, fertCtx()).state === 'due').map(p => p.code); }
    return fertDialog(o);
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
    if (!(await confirmBox(`Make ${p.name} home?`, `Plant pages, current conditions ("Online weather"), frost warnings and the Winter plan will use the weather for ${p.name} instead of ${WX.home.name}.`, 'Make home'))) return;
    await guard(async () => { await api('PUT', '/api/places/' + p.id, { is_home: true }); COND = null; toast(`${p.name} is now home`); route(); });
  },
  async placeonoff(el) {
    if (!(await needName())) return;
    await guard(async () => { await api('PUT', '/api/places/' + el.dataset.id, { enabled: el.dataset.on === '1' }); toast(el.dataset.on === '1' ? 'Hourly updates on' : 'Hourly updates stopped; its stored weather is kept'); route(); });
  },
  async placedel(el) {
    const p = WX.places.find(x => String(x.id) === el.dataset.id); if (!p || !(await needName())) return;
    if (!(await confirmBox(`Remove ${p.name}?`, `This deletes its ${num(p.count || 0)} hourly readings, its daily summaries and its update log. To keep them, use "Stop hourly updates" instead. This cannot be undone.`, 'Remove it and its weather', true))) return;
    await guard(async () => { const r = await api('DELETE', '/api/places/' + p.id); toast(`${p.name} removed (${num(r.removed_readings)} readings)`); if (String(WXP) === String(p.id)) WXP = null; await setPlace(WXP); });
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
  clearfilters() { Object.assign(G, { q: '', plan: '', health: '', low: false, needs: false }); gSave(); route(); },
  plan(el) { G.plan = G.plan === el.dataset.plan ? '' : el.dataset.plan; document.querySelectorAll('.ledger button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.plan === G.plan))); drawGrid(); },
  pick(el) { PIDX = +el.dataset.i; repaintPhotos(); },
  zoom() { const c = curPhoto(); if (c) modal(html`<form method="dialog"><img src="${photoUrl(c.file)}" alt="${c.caption || CUR.p.common_name}"><p class="cap">${c.caption}</p><button class="btn" value="ok" autofocus>Close</button></form>`, 'photo'); },
  zoomloose(el) { modal(html`<form method="dialog"><img src="${photoUrl(el.dataset.file)}" alt="${el.dataset.cap}"><p class="cap">${el.dataset.cap}</p><button class="btn" value="ok" autofocus>Close</button></form>`, 'photo'); },
  copyreq() { return copyRequest(); },
  print() { window.print(); },
  async mainphoto() { if (!(await needName())) return; await guard(async () => { await api('PATCH', '/api/photos/' + curPhoto().id, { is_primary: true }); toast('Main photo changed'); await reloadPlant(); }); },
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
    await guard(async () => { await api('POST', '/api/care', { plant: code, kind: k }); toast((k === 'water' ? 'Watered: ' : 'Checked, still moist: ') + el.dataset.name); await careRefresh(code); });
  },
  async careall(el) {
    const codes = el.dataset.codes.split(',').filter(Boolean); if (!codes.length) return;
    if (!(await needName())) return;
    if (!(await confirmBox(`Mark ${codes.length} plants as watered today?`, 'Each one gets a "Watered" entry for today in its care log. You can remove any of them on the plant\'s page.', 'Mark as watered'))) return;
    await guard(async () => { await api('POST', '/api/care', { plants: codes, kind: el.dataset.kind }); toast(codes.length + ' plants marked as watered'); await careRefresh(); });
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
  fcrange(el) { FC.range = el.value; fcRefresh('select[data-act=fcrange]'); },
  fcopen(el) { FC.open = el.checked; fcRefresh('input[data-act=fcopen]'); },
  async tododone(el) { if (!(await needName())) { el.checked = !el.checked; return; } await guard(async () => { await api('PATCH', '/api/to-photograph/' + el.dataset.id, { done: el.checked }); route(); }); },
};
function wtFocusTop() { const t = document.querySelector('#wx-table .pager'); if (t) t.scrollIntoView({ block: 'nearest' }); }
let PLACE_RESULTS = [];
const formActs = {
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
document.addEventListener('click', e => {
  const el = e.target.closest('[data-act]');
  if (!el || el.tagName === 'INPUT') return;
  const fn = acts[el.dataset.act];
  if (fn) { e.preventDefault(); fn(el); }
});
document.addEventListener('change', e => {
  const el = e.target;
  if (el.dataset && el.dataset.act && changeActs[el.dataset.act]) { changeActs[el.dataset.act](el); return; }
  if (el.dataset && el.dataset.pref) { window.PlantPrefs.set(el.dataset.pref, el.value); if (el.dataset.pref === 'layout' && document.querySelector('.plant')) route(); return; }
  if (el.name === 'csrc') { const mf = document.getElementById('manual-fields'); if (mf) mf.hidden = el.value !== 'manual'; return; }
  const f = el.dataset && el.dataset.f;
  if (!f) return;
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
  else if (f === 'pnplan') { G.plan = el.value; drawGrid(); }
  else if (f === 'pnneeds') { G.needs = el.checked; drawGrid(); }
  else if (f === 'sort') { G.sort = el.value; drawGrid(); }
  else if (f === 'low') { G.low = el.checked; drawGrid(); }
  else if (f === 'archived') { G.archived = el.checked; G.plan = ''; route(); }
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
  if (e.target.closest && e.target.closest('form[data-fert]')) {
    if (e.target.name === 'product') { const x = FERT.products.find(q => q.product.toLowerCase() === e.target.value.trim().toLowerCase()); const f = e.target.form; if (x && !f.elements.n.value && !f.elements.amount.value) { ['form', 'n', 'p', 'k', 'amount', 'amount_unit', 'water_amount', 'water_unit', 'method'].forEach(k => { if (x[k] != null && f.elements[k]) f.elements[k].value = x[k]; }); } }
    fertPreview();
  }
  const f = e.target.dataset && e.target.dataset.f;
  if (f === 'q') { G.q = e.target.value; drawGrid(); }
  else if (f === 'logq') document.getElementById('logbody').innerHTML = rend(logRows(e.target.value));
});
document.addEventListener('submit', e => {
  const form = e.target.closest('form[data-form]');
  if (!form) return;
  e.preventDefault();
  const fn = formActs[form.dataset.form];
  if (fn) guard(() => fn(form));
});

document.addEventListener('prefs', () => { if (document.documentElement.dataset.narrow !== '1') NAVSESSION = null; navLayout(); fitPanes(); paintAllCharts(); Object.keys(CALS).forEach(id => calRender(id)); });
let rzT = null;
window.addEventListener('resize', () => { clearTimeout(rzT); rzT = setTimeout(() => { navLayout(); fitPanes(); paintAllCharts(); Object.keys(CALS).forEach(id => calRender(id)); }, 120); });
paintWho();
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
route();
wxPoll();                      // shows the progress box on every page while a history load runs
})();
