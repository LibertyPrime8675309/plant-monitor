/* Plant record front end: the plant library, one species' page, around home. Split out of discover.js in 1.57.0 (review item 25); the scripts load in the order js/manifest.json
   gives and share one scope, so a function here may call any other. Plain JavaScript, no inline handlers (the content policy forbids them). */
'use strict';

// ---------- the plant library (1.18.0; 1.21.0: browse every species, filters, records with photos) ----------
// The list comes from the picture checker (offline). Photos come from iNaturalist through the app, which keeps them in
// data/library; the cards ask for the photos of the plants on screen and fill them in as they arrive.
const LIB_DEF = { q: '', scope: 'common', kind: '', family: '', state: '', common: false, mine: '', know: '', sort: 'known', view: 'cards' };
function knowWord() {         // 1.28.0: named for the place in use; the invasive list is only built in for Texas
  const w = { native: `Native to ${regionName()}`, introduced: `Introduced to ${regionName()}`, invasive: 'On the Texas invasive list', near: 'Grows wild near here', bloom: 'Flowering near here this month',
    fruiting: 'Fungi found near here this month', hardy: 'Likely to survive outside here', petsafe: 'Safe for dogs and cats (ASPCA)', pettoxic: 'Toxic to dogs or cats (ASPCA)' };
  if (!(REGION() && REGION().id === 18)) delete w.invasive;
  return w;
}
const LIB = Object.assign({ res: [], total: 0, facets: null, facetsFor: '', photos: {}, t: 0, poll: 0, my: 0 }, LIB_DEF);
try { const s = JSON.parse(localStorage.getItem('plantdb.library') || '{}'); Object.keys(LIB_DEF).forEach(k => { if (s[k] != null && typeof s[k] === typeof LIB_DEF[k]) LIB[k] = s[k]; }); } catch (e) { /* defaults */ }
const libSave = () => { try { localStorage.setItem('plantdb.library', JSON.stringify(Object.fromEntries(Object.keys(LIB_DEF).map(k => [k, LIB[k]])))); } catch (e) { /* not remembered */ } };
const LIB_PAGE = 48;
const LIB_SORTS = [['known', 'Best known first'], ['common', 'Common name A to Z'], ['sci', 'Scientific name A to Z'], ['family', 'Family']];
const LIB_STATE_WORD = s => s.replace(/([a-z])([A-Z])/g, '$1 $2');
const LIB_KIND_SHORT = { dicot: 'Flowering plant', monocot: 'Flowering plant (monocot)', fern: 'Fern', lycophyte: 'Clubmoss', conifer: 'Conifer', cycad: 'Cycad', ginkgo: 'Ginkgo', gnetophyte: 'Gnetophyte', moss: 'Moss', liverwort: 'Liverwort', hornwort: 'Hornwort', alga: 'Alga', other: '',
  mushroom: 'Mushroom', cupfungus: 'Cup fungus', lichen: 'Lichen', rust: 'Rust or smut', mould: 'Mould or mildew', otherfungus: 'Fungus' };
const spHref = s => '#/species/' + enc(s);
// 1.28.0: library photos for offline use, by area (any place iNaturalist knows), in a table
function libAreasHtml(d) {
  const owner = ME().role === 'owner', A = d.areas || [];
  const day = t => t ? new Date(t).toLocaleDateString([], { month: 'long', day: 'numeric', year: 'numeric' }) : 'Not yet';
  const stateWords = a => a.error ? html`<div class="bad-text"><strong>Last try failed:</strong> ${a.error}</div>`
    : a.state === 'list' ? html`<div class="hint">Getting the list of plants recorded there…</div>`
    : a.state === 'photos' ? html`<div class="hint">Downloading: ${num(a.left)} left, about ${Math.max(1, Math.round(a.left * 1.1 / 60))} minutes</div>` : '';
  return html`${A.length ? html`<div class="tbl-wrap"><table class="tbl lib-areas"><caption class="sr">Download areas</caption><thead><tr><th scope="col">Area</th><th scope="col">Photos downloaded</th><th scope="col">Percent</th><th scope="col">Last updated</th>${owner ? html`<th scope="col"><span class="sr">Actions</span></th>` : ''}</tr></thead><tbody>
    ${A.map(a => html`<tr><th scope="row">${a.name}${stateWords(a)}</th>
      <td>${a.total ? `${num(a.kept)} of ${num(a.total)}` : a.state === 'list' ? 'Counting…' : 'Not counted yet'}${a.no_photo ? html`<div class="hint">${num(a.no_photo)} ${a.no_photo === 1 ? 'has' : 'have'} no photo on iNaturalist</div>` : ''}</td>
      <td><span class="pct-num">${a.total ? `${a.percent}%` : '—'}</span>${a.total ? html`<span class="pct-bar" aria-hidden="true"><i style="width:${Math.min(100, a.percent)}%"></i></span>` : ''}</td>
      <td>${day(a.checked_at)}</td>
      ${owner ? html`<td><div class="row" style="gap:.4rem"><button class="btn small" type="button" data-act="libareaupd" data-id="${a.id}" ${a.state !== 'idle' || !d.online ? raw('disabled') : ''}>Check for updates</button>
        <button class="btn small ghost" type="button" data-act="libareadel" data-id="${a.id}" data-name="${a.name}" aria-label="Remove the area ${a.name}">Remove</button></div></td>` : ''}</tr>`)}</tbody></table></div>`
    : html`<p class="muted">No areas yet.${owner ? ' Add one below.' : ' The owner can add them.'}</p>`}
  ${owner && d.running ? html`<p class="row"><button class="btn ghost" type="button" data-act="libareastop">Stop all downloads</button></p>` : ''}
  ${owner ? html`<h3>Add an area</h3>${d.online ? html`<form class="todo-add" data-form="libareafind"><label style="flex:1 1 18rem;font-weight:700">Country, state, county, city or park<input type="text" name="q" placeholder="California" autocomplete="off"></label><button class="btn" type="submit" style="align-self:end">Search</button></form>
    <div id="libarea-res" aria-live="polite"></div>` : html`<p class="muted">Turn on the iNaturalist photos above first.</p>`}` : ''}`;
}
async function libAreasPoll() {
  clearTimeout(LIB.prePoll);
  const box = document.getElementById('lib-pre'); if (!box) return;
  let d; try { d = await api('GET', '/api/library/areas'); } catch (e) { return; }
  if (!document.getElementById('lib-pre')) return;
  const tbl = box.querySelector('.lib-areas-wrap'), had = tbl && tbl.contains(document.activeElement) ? document.activeElement.dataset : null;
  const keepRes = document.getElementById('libarea-res'), resHtml = keepRes ? keepRes.innerHTML : '', q = box.querySelector('[name=q]'), qv = q ? q.value : '';
  const focusedQ = q && document.activeElement === q;
  box.innerHTML = rend(html`<div class="lib-areas-wrap">${libAreasHtml(d)}</div>`);
  const nr = document.getElementById('libarea-res'); if (nr) nr.innerHTML = resHtml;
  const nq = box.querySelector('[name=q]'); if (nq) { nq.value = qv; if (focusedQ) nq.focus(); }
  if (had && had.act) { const b = box.querySelector(`[data-act="${had.act}"][data-id="${had.id}"]`); if (b && !b.disabled) b.focus(); }
  if (d.running) LIB.prePoll = setTimeout(libAreasPoll, 5000);
}
function libListsHtml(d) {
  const day = t => t ? new Date(t).toLocaleDateString([], { month: 'long', day: 'numeric', year: 'numeric' }) : '';
  return html`<ul class="lib-lists">${d.lists.map(l => html`<li><strong>${l.label}:</strong> ${l.fetched ? `${l.count.toLocaleString()} species, fetched ${day(l.fetched)}.` : d.queued.includes(l.name) || (d.now && d.now[0] === l.name) ? 'Being fetched…' : 'Not fetched yet.'}
      ${l.error ? html` <span class="bad-text">Last try failed: ${l.error}</span>` : ''}</li>`)}</ul>
    ${d.now ? html`<p>Fetching now: ${(d.lists.find(l => l.name === d.now[0]) || { label: d.now[0] }).label}${d.now[2] ? `, ${d.now[1].toLocaleString()} of ${d.now[2].toLocaleString()}` : ''}.</p>` : ''}
    <p class="hint">These are for ${d.place}, the place chosen with the Location button. From iNaturalist (what people have recorded, and whether it is native or introduced in ${d.region ? d.region.name : 'its state or country'}) and the ASPCA's lists${d.noxious ? html`, and the Texas Department of Agriculture's noxious and invasive plant list (<a href="${d.noxious_law}" target="_blank" rel="noopener noreferrer">about the list</a>)` : ''}. Hardiness zone, from the place's own weather history: ${d.zone}.</p>
    ${d.noxious ? '' : html`<p class="hint">The app has no built-in list of plants that are illegal to grow or sell here. Ask your state or country's agriculture department, or look for the place on EDDMapS.</p>`}
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
  ID_SCOPES = idScopes(); if (LIB.scope === 'texas') LIB.scope = 'state';
  if (!ID_SCOPES.some(x => x[0] === LIB.scope)) LIB.scope = 'common';
  if (LIB.know && !knowWord()[LIB.know]) LIB.know = '';
  let st = null;
  try { st = await api('GET', '/api/identify/status'); } catch (e) { /* shown below */ }
  const ready = st && st.state === 'ready';
  let fac = null;
  if (ready) { try { fac = await api('GET', '/api/library/facets?scope=' + enc(LIB.scope)); LIB.facets = fac; LIB.facetsFor = LIB.scope; } catch (e) { /* filters without counts */ } }
  let lset = null; if (ME().role === 'owner') { try { lset = await api('GET', '/api/library/settings'); } catch (e) { /* hidden */ } }
  let mine = { tags: [] }, wl = { wishlist: [] };
  try { [mine, wl] = await Promise.all([api('GET', '/api/library/notes'), api('GET', '/api/wishlist')]); } catch (e) { /* no extras */ }
  const sel = (f, opts) => html`<select data-f="${f}">${opts.map(([v, l]) => html`<option value="${v}" ${String(LIB[f.slice(3)]) === v ? raw('selected') : ''}>${l}</option>`)}</select>`;
  const fungi = LIB.scope === 'fungi';
  return {
    title: 'Library',
    after: () => { if (ready) libLoad(); libAreasPoll(); libListsPoll(); },
    html: html`<h1>Library</h1>
    <p>Every plant species this computer knows, ${st && st.species ? Number(st.species).toLocaleString() : 'about 349,000'} in all${st && st.fungi ? html`, and ${Number(st.fungi).toLocaleString()} fungi (choose "Fungi worldwide" under Look in)` : ''}. Open any of them for its photos, description, where it grows, and look-alikes.</p>
    ${ready ? '' : html`<p class="notice bad" role="status">${idStatusText(st)}</p>`}
    <p class="row"><a class="btn ghost" href="#/around">Around home: what's flowering and fruiting</a><a class="btn ghost" href="#/wishlist">Your wishlist (${wl.wishlist.filter(w => w.status === 'want' && (w.kind || 'plant') === 'plant').length} wanted)</a></p>
    <div class="filters filters-main lib-filters" role="search" aria-label="Search and filter the library">
      <label>Search<input type="search" data-f="libq" value="${LIB.q}" placeholder="Common or scientific name" autocomplete="off"></label>
      <label>Look in${sel('libscope', ID_SCOPES.map(([k, l]) => [k, l + (st && st.scopes && st.scopes[k] ? ` (${Number(st.scopes[k].count).toLocaleString()})` : '')]))}</label>
      <label>Sort by${sel('libsort', LIB_SORTS)}</label>
    </div>
    ${filterFold(html`<label>${fungi ? 'Kind of fungus' : 'Kind of plant'}${sel('libkind', [['', 'Any kind'], ...((fac && fac.kinds) || []).map(k => [k.key, `${k.label} (${k.count.toLocaleString()})`])])}</label>
      <label>Family<input type="text" data-f="libfamily" list="lib-fams" value="${LIB.family}" placeholder="Any family" autocomplete="off">
        <datalist id="lib-fams">${((fac && fac.families) || []).map(f => html`<option value="${f.name}">${f.name} (${f.count})</option>`)}</datalist></label>
      <label>Grows wild in${sel('libstate', [['', 'Anywhere'], ['us', 'The United States'], ...(regionState() ? [[regionState(), LIB_STATE_WORD(regionState())]] : []), ...((fac && fac.states) || []).filter(x => x !== regionState()).map(x => [x, LIB_STATE_WORD(x)])])}${fungi ? html`<small>Lichens only: the USDA lists have no other fungi</small>` : ''}</label>
      <label>Show${sel('libmine', [['', 'All of them'], ['species', 'Only ones I have'], ['genus', 'Ones I have, or of the same genus'], ['wish', 'On my wishlist'], ['notes', 'Ones with notes or tags'],
        ...mine.tags.map(t => ['tag:' + t, `Tagged "${t}"`])])}</label>
      <label>Your area${sel('libknow', [['', 'Any'], ...Object.entries(knowWord()).filter(([k]) => fungi ? ['near', 'fruiting', 'hardy'].includes(k) : k !== 'fruiting')])}</label>
      <label>Show as${sel('libview', [['cards', 'Cards with photos'], ['table', 'A table']])}</label>
      <label class="chk"><input type="checkbox" data-f="libcommon" ${LIB.common ? raw('checked') : ''}>Only ${fungi ? 'fungi' : 'plants'} with a common name</label>`, libFiltersOn() + (LIB.view === 'table' ? 1 : 0))}
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
      <p>The "Your area" filter, the tags on the cards and each species' page use these lists. They are fetched in the background and kept on this computer, and fetched again when they get old.</p>
      <div id="lib-lists" aria-live="polite"><p class="muted">Loading…</p></div></section>
    <section class="id-sec" aria-labelledby="h-libpre"><h2 id="h-libpre">Photos for offline use</h2>
      <p>Download the photo and short facts of every plant species recorded in an area, so the library shows them even without the internet. An area can be any country, state, county, city or park that iNaturalist knows. Downloads run in the background at about one species a second, after anything someone is looking at, and the photos are kept in data\\library (about 70 KB each). <strong>Check for updates</strong> gets the area's list again and downloads only what is new. Removing an area keeps its photos.</p>
      <div id="lib-pre" aria-live="polite"><p class="muted">Loading…</p></div></section>`,
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
async function offLibBrowse(off) {             // the library without a connection: the download areas' list saved on this device
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
  if (k.tx === 'native') t.push(html`<span class="tag">Native to ${regionName()}</span>`); else if (k.tx === 'introduced') t.push(html`<span class="tag">Introduced to ${regionName()}</span>`);
  if (k.bloom) t.push(html`<span class="tag">Flowering near home now</span>`);
  if (k.fruiting) t.push(html`<span class="tag">Found near home this month</span>`);
  else if (k.near) t.push(html`<span class="tag">Wild near home</span>`);
  if (k.pets) { const tox = ['dogs', 'cats'].filter(a => k.pets[a] === 'toxic'); t.push(tox.length ? html`<span class="tag tag-warn">⚠ Toxic to ${tox.join(' and ')}</span>` : k.pets.dogs === 'non-toxic' && k.pets.cats === 'non-toxic' ? html`<span class="tag">Safe for dogs and cats</span>` : ''); }
  if (s.wish) t.push(html`<span class="tag tag-wish">${s.wish === 'got' ? 'Wishlist: got it' : 'On your wishlist'}</span>`);
  (s.tags || []).forEach(x => t.push(html`<span class="tag tag-own">Tag: ${x}</span>`));
  if (inRegion(s)) t.push(html`<span class="tag">Wild in ${LIB_STATE_WORD(regionState())}</span>`);
  else if (s.us_states && s.us_states.length) t.push(html`<span class="tag">Wild in ${s.us_states.length} US state${s.us_states.length === 1 ? '' : 's'}</span>`);
  return t;
}
function libPhotoHtml(s, cls) {
  const ph = s.own_photo ? { url: s.own_photo, mine: true } : LIB.photos[s.scientific_name];
  if (ph && ph.url) return html`<img class="${cls}" src="${ph.url}" alt="" loading="lazy" decoding="async">`;
  const none = ph === null || LIB.photos.__off;        // 1.57.0: no photo to wait for: a short line, not a big empty box
  return html`<div class="nophoto ${cls}${none ? ' nophoto-none' : ''}" data-ph="${s.scientific_name}">${ph === null ? 'No photo found' : LIB.photos.__off ? 'Photos are off' : 'Finding a photo…'}</div>`;
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
    <td>${inRegion(s) ? LIB_STATE_WORD(regionState()) + (s.us_states.length > 1 ? ` and ${s.us_states.length - 1} more states` : '') : s.us_states && s.us_states.length ? `${s.us_states.length} US state${s.us_states.length === 1 ? '' : 's'}` : ''}</td>
    <td>${s.yours && s.yours.length ? s.yours.join(', ') : s.yours_genus && s.yours_genus.length ? 'Same genus: ' + s.yours_genus.slice(0, 3).join(', ') : ''}</td></tr>`;
}
function libDraw(added) {
  const box = document.getElementById('lib-res'); if (!box) return;
  const n = LIB.res.length, cnt = document.getElementById('lib-count'), more = document.getElementById('lib-more'), clr = document.getElementById('lib-clear');
  const sc = ID_SCOPES.find(x => x[0] === LIB.scope);
  if (cnt && LIB.offline) cnt.dataset.off = '1'; else if (cnt) delete cnt.dataset.off;
  if (cnt) cnt.textContent = (LIB.offline ? 'Offline: searching the plants of your download areas saved on this device. ' : '') + (LIB.total ? `Showing ${n.toLocaleString()} of ${LIB.total.toLocaleString()} in ${sc ? sc[1][0].toLowerCase() + sc[1].slice(1) : 'the list'}${LIB.q ? ` matching "${LIB.q}"` : ''}.` : `Nothing found${LIB.q ? ` for "${LIB.q}"` : ''} with these filters.`);
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
    box.innerHTML = rend(html`<h2 class="sr">The plants found</h2><div class="grid lib-grid">${LIB.res.map(libCard)}</div>`);
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
  if (!r.online) document.querySelectorAll('#lib-res [data-ph]').forEach(el => { el.textContent = 'Photos are off'; el.classList.add('nophoto-none'); });
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
      <div class="sp-more">${spHomeHtml(d, fungus)}
      ${fungus ? '' : spPetsHtml(d)}
      ${fungus ? '' : html`<section aria-labelledby="sp-care-h"><h2 id="sp-care-h">Care sheet</h2><div id="sp-care">${spCareHtml(d)}</div></section>`}
      <section aria-labelledby="sp-facts-h"><h2 id="sp-facts-h">${fungus ? 'What it does, and growing it' : 'Uses, partners and propagation'}</h2><div class="facts-box" data-facts-name="${d.scientific_name}" data-facts-common="${d.common_name || ''}" data-facts-kind="${fungus ? 'fungus' : 'plant'}"><p class="loading">Loading</p></div></section>
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
          : html`<p>It is not on the USDA PLANTS state lists, so it does not grow wild in the US (or is not recorded there). It may still be grown in gardens and homes.</p>`}</section></div>
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
  if (!fungus) lines.push(html`<p><strong>In ${regionName()}:</strong> ${k.tx === 'native' ? 'native.' : k.tx === 'introduced' ? 'introduced (not native), growing wild here.' : `not on the iNaturalist lists of ${regionName()} plants (or the lists are not fetched yet).`}</p>`);
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
      ${sh.zone_low ? html`<dt>Hardiness</dt><dd>USDA zones ${sh.zone_low} to ${sh.zone_high || '?'}${sh.min_temp_f != null ? `; survives down to about ${tF(sh.min_temp_f)}` : ''}. Yours is ${d.zone}.</dd>` : ''}</dl>
    <p class="hint">Written ${when(c.written_at)} by ${c.model}, asked by ${c.asked_by}, for ${c.place} (zone ${c.zone}).</p>${btn}`;
}
function spWishHtml(d) {
  const w = d.wishlist;
  if (!w) return canChange() ? html`<div class="sp-wish"><button class="btn ghost" type="button" data-act="spwish">Add to my wishlist</button></div>` : '';
  return html`<div class="sp-wish notice" role="note"><p><strong>${w.status === 'got' ? 'On your wishlist: you got it.' : 'On your wishlist.'}</strong> Added by ${w.added_by} on ${when(w.added_at)}.
    ${w.where_seen ? html`Where to find it: ${w.where_seen}.` : ''}</p>${w.notes ? html`<p class="pl">${w.notes}</p>` : ''}
    <p class="row"><a href="#/wishlist">Open the wishlist</a>${canChange() ? html`<button class="btn ghost small" type="button" data-act="wledit" data-name="${w.name}" aria-label="Edit the wishlist entry for ${w.common_name || w.name}">Edit</button>` : ''}</p></div>`;
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


Object.assign(acts, {
  async factswrite(el) {
    const box = el.closest('.facts-box'); if (!box || !(await needName())) return;
    el.disabled = true;
    box.insertAdjacentHTML('beforeend', rend(html`<p role="status" class="facts-wait">Claude is writing them. This takes about half a minute…</p>`));
    try {
      const r = await api('POST', '/api/facts', { name: box.dataset.factsName, common_name: box.dataset.factsCommon || '', kind: box.dataset.factsKind || 'plant' });
      box.innerHTML = rend(factsHtml(r.facts, box)); toast('Written and kept');
      const h = box.closest('section') && box.closest('section').querySelector('h2'); if (h) { h.setAttribute('tabindex', '-1'); h.focus(); }
    } catch (e) { const w = box.querySelector('.facts-wait'); if (w) w.remove(); el.disabled = false; box.insertAdjacentHTML('beforeend', rend(html`<div class="notice bad" role="alert">${e.message}</div>`)); }
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
  async libareaadd(el) {
    if (!(await needName())) return;
    await guard(async () => { await api('POST', '/api/library/areas', { place_id: +el.dataset.pid, name: el.dataset.name }); toast(`${el.dataset.name} added. Its download has started.`);
      const r = document.getElementById('libarea-res'); if (r) r.innerHTML = ''; await libAreasPoll(); });
  },
  async libareaupd(el) { if (!(await needName())) return; await guard(async () => { await api('POST', '/api/library/areas/' + el.dataset.id); toast('Checking for updates in the background'); await libAreasPoll(); }); },
  async libareadel(el) {
    if (!(await confirmBox(`Remove ${el.dataset.name}?`, 'It leaves the table and any download for it stops. Its photos stay on this computer.', 'Remove area', true))) return;
    await guard(async () => { await api('DELETE', '/api/library/areas/' + el.dataset.id); toast('Area removed'); await libAreasPoll(); });
  },
  async libareastop() { await guard(async () => { await api('POST', '/api/library/areas/stop'); toast('Downloads stopped'); await libAreasPoll(); }); },
  spnew: () => { if (SPCUR) idNewPlant(Object.assign({}, SPCUR, { src: 'the plant library' }), false); },
});
