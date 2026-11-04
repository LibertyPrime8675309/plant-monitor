/* Plant record front end: the Plants page: the gallery and its filters. One of the files app.js was split into in 1.32.0; they load in order (index.html) and share one scope,
   so a function here may call any other. Plain JavaScript, no inline handlers (the server's content policy forbids them). */
'use strict';

// ---------- gallery ----------
const G = { q: '', plan: '', health: '', low: false, needs: false, sort: 'code', group: '', status: 'active', site: '', home: '',   // 1.28.0: home   // 1.16.2: status and site
  light: '', pets: '', hardy: '', care: '', grow: '', leaf: '', pot: '', photo: '' };                                      // 1.17.0: more filters
const MORE_KEYS = ['light', 'pets', 'hardy', 'care', 'grow', 'leaf', 'pot', 'photo'];     // the More filters (defined further down)
// the Plants page filters are remembered in this browser and also decide where Previous / Next plant go on plant pages
try { const s = JSON.parse(localStorage.getItem('plantdb.filters') || '{}'); for (const k of ['q', 'plan', 'health', 'low', 'needs', 'sort', 'group', 'status', 'site', 'home', ...MORE_KEYS]) if (k in s && typeof s[k] === typeof G[k]) G[k] = s[k]; } catch (e) { /* defaults */ }
function gSave() { try { localStorage.setItem('plantdb.filters', JSON.stringify({ q: G.q, plan: G.plan, health: G.health, low: G.low, needs: G.needs, sort: G.sort, group: G.group, status: G.status, site: G.site, home: G.home, ...Object.fromEntries(MORE_KEYS.map(k => [k, G[k]])) })); } catch (e) { /* not saved */ } }
const gActive = () => !!(G.q.trim() || G.plan || G.health || G.low || G.needs || (G.group && groupById(G.group)) || G.status !== 'active' || G.site || (G.home && homeById(G.home)) || moreOn());
const STATUS_WORD = { active: 'Active only', all: 'Active and archived', archived: 'Archived only' };
const isArch = p => p.status === 'archived';
const statusOk = p => G.status === 'all' || (G.status === 'archived' ? isArch(p) : !isArch(p));
const needsYou = p => (p.requests_open || 0) > 0 || (p.id_confidence != null && p.id_confidence < 70);
let ALL = [];
const SORTS = { code: 'Code', health: 'Health, worst first', conf: 'ID confidence, lowest first', updated: 'Recently updated', name: 'Name A to Z', group: 'Group A to Z' };

function filteredPlants(list) {
  const q = G.q.trim().toLowerCase();
  let r = (list || ALL).filter(p =>
    statusOk(p) && (!G.site || (p.site || 'Outdoors') === G.site) && homeOk(p) && moreOk(p) &&
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
    <div class="tags">${isArch(p) ? html`<span class="tag tag-arch">Archived</span>` : ''}${HOMES().length > 1 ? html`<span class="tag tag-homeat">⌂ ${plantHome(p).name}</span>` : ''}${planTag(p.winter_plan)}${healthTag(p.health_rating)}</div>
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
  if (document.getElementById('idph-tbl')) { drawIdPhotos(); return; }      // 1.28.0: the photo table on the Identify page
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
      ${homeFilter()}${siteFilter()}${groupFilter()}${statusFilter()}
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
// 1.28.0: homes. A plant's home_id is empty for the main home; other homes are places marked "Plants live here".
const HOMES = () => (META && META.homes) || [];
const homeById = id => HOMES().find(h => String(h.id) === String(id)) || null;
const mainHome = () => HOMES().find(h => h.is_home) || HOMES()[0] || { id: '', name: 'Home' };
const plantHome = p => (p && p.home_id && homeById(p.home_id)) || mainHome();
const homeOk = p => !G.home || !homeById(G.home) || String(plantHome(p).id) === String(G.home);
function homeFilter() {
  if (HOMES().length < 2) return '';
  return html`<label>Home<select data-f="home"><option value="">All homes</option>${HOMES().map(h => html`<option value="${h.id}" ${String(G.home) === String(h.id) ? raw('selected') : ''}>${h.name}</option>`)}</select></label>`;
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
