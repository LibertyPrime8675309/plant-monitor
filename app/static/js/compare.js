/* Plant record front end: compare lights (1.58.0, PLAN.md step 10; plantdb/compare.py). One of the files loaded in order by
   index.html (js/manifest.json); they share one scope. Plain JavaScript, no inline handlers (the server's content policy forbids them).

   - The Compare lights page (#/compare, linked from Grow lights and found by Search): every light, owned and considered, worked
     out at one distance the person picks, with search, sort (any column; the headers are buttons with aria-sort, and the sort is
     said in words above the table), filters shown as chips that remove themselves, a Columns choice that follows the person
     (the synced pref plantdb.compare), and "Pick to compare" for two to four lights side by side. When the table would not fit
     the width (a phone, or large text), each light is a card of label and value instead, so the page never scrolls sideways.
   - Each light opens a window with everything about it and, for an editor: "Try it in a spot", "Bought it" (for a light being
     considered), "Change the listing details" (brand, link, price and its date, and the rest), "No longer used" and "Remove".
   - "Add a light you are considering" takes what a listing gives. */
'use strict';

let CMP = null;                                    // { d: /api/lights/compare, q, sort, f, picked, cards }
const CMP_PREF = 'plantdb.compare';
const CMP_DEF_COLS = ['owned', 'ppfd', 'area', 'dli', 'perwatt', 'points', 'source'];
const cmpPref = () => { try { return JSON.parse(localStorage.getItem(CMP_PREF) || '{}') || {}; } catch (e) { return {}; } };
const cmpSave = p => { try { localStorage.setItem(CMP_PREF, JSON.stringify({ ...cmpPref(), ...p })); } catch (e) { /* this visit only */ } };
const cmpYes = v => v === true ? 'Yes' : v === false ? 'No' : 'Not known';
const cmpColour = k => k ? `${k}K ${k >= 5000 ? 'cool white' : k >= 3500 ? 'neutral white' : 'warm white'}` : '';
const cmpTimer = r => !r.timer || /^none/i.test(r.timer) ? 'None' : [r.timer_repeats ? 'Repeats every day' : 'Does not repeat',
  r.timer_keeps === false ? 'lost in a power cut' : r.timer_keeps === true ? 'keeps its setting after a power cut' : ''].filter(Boolean).join(', ');
const cmpOwned = r => r.status === 'owned' ? `${r.count}${r.in_use ? ` (${r.in_use} in use)` : ''}` : r.status_word;

// Each column: label (for the header and the card), its value in words, a value to sort by (null sorts last), and whether a
// higher number is the usual first ("highest first").
function cmpCols() {
  const at = lenF(CMP.d.at), h = CMP.d.hours;
  return {
    owned:    { label: 'Owned', v: cmpOwned, s: r => (r.status === 'owned' ? 1000 : r.status === 'considering' ? 0 : -1) + r.count, hi: true },
    brand:    { label: 'Brand', v: r => r.brand, s: r => r.brand || null },
    ppfd:     { label: `PAR at ${at}`, tl: `PAR at ${at} (µmol/m²/s)`, v: r => has(r.ppfd) ? `${fmt(r.ppfd)} µmol/m²/s` : r.beyond, tv: r => has(r.ppfd) ? fmt(r.ppfd) : 'Beyond its chart', s: r => r.ppfd, hi: true },
    area:     { label: `Area lit at ${at}`, tl: `Area lit (${unitsGet().len === 'cm' ? 'm²' : 'sq ft'})`, v: r => has(r.area_sqft) ? areaF(r.area_sqft) : (has(r.ppfd) ? 'Not given' : ''), tv: r => has(r.area_sqft) ? areaF(r.area_sqft, false) : (has(r.ppfd) ? 'Not given' : ''), s: r => r.area_sqft, hi: true },
    dli:      { label: `Daily light, ${h} hours`, tl: `Daily light, ${h} h (mol/m²)`, v: r => has(r.dli) ? `${fmt(r.dli, 1)} mol/m²` : '', tv: r => has(r.dli) ? fmt(r.dli, 1) : '', s: r => r.dli, hi: true },
    perwatt:  { label: 'Light per watt (rough)', tl: 'Light per watt (rough, µmol/J)', v: r => has(r.per_watt) ? `${fmt(r.per_watt, 2)} µmol/J` : '', tv: r => has(r.per_watt) ? fmt(r.per_watt, 2) : '', s: r => r.per_watt, hi: true },
    watts:    { label: 'Watts', v: r => has(r.watts) ? `${fmt(r.watts, 1)} W` : '', tv: r => has(r.watts) ? fmt(r.watts, 1) : '', s: r => r.watts, hi: true },
    colour:   { label: 'Colour', v: r => cmpColour(r.kelvin), s: r => r.kelvin, hi: true },
    cri:      { label: 'Colour rendering (CRI)', v: r => r.cri, s: r => r.cri_num, hi: true },
    redblue:  { label: 'Red and blue', v: r => has(r.red) ? `Red ${fmt(r.red)}%, blue ${fmt(r.blue)}%` : 'Not given', s: r => r.red, hi: true },
    points:   { label: 'Points', v: r => CMP.d.directions[r.direction] || '', s: r => CMP.d.directions[r.direction] || null },
    dimming:  { label: 'Brightness steps', v: r => r.dimmable ? r.dimming.map(x => x + '%').join(', ') : 'Full only', s: r => r.dimming.length, hi: true },
    timer:    { label: 'Timer', v: cmpTimer, s: r => (r.timer_repeats ? 2 : 0) + (r.timer_keeps ? 1 : 0), hi: true },
    socket:   { label: 'Needs a socket', v: r => r.needs_socket ? 'Yes' : 'No', s: r => r.needs_socket ? 1 : 0 },
    mount:    { label: 'How it holds', v: r => CMP.d.mount_kinds[r.mount_kind] || '', s: r => CMP.d.mount_kinds[r.mount_kind] || null },
    size:     { label: 'Size', v: r => r.size, s: r => r.size || null },
    price:    { label: 'Price', v: r => has(r.price) ? `$${fmt(r.price, 2)}${r.price_on ? ` (${dateF(r.price_on)})` : ''}` : '', tv: r => has(r.price) ? `$${fmt(r.price, 2)}` : '', s: r => r.price },
    perlight: { label: 'Price per light (rough)', v: r => has(r.per_light) ? `$${fmt(r.per_light, 2)}` : '', s: r => r.per_light },
    source:   { label: 'Numbers from', v: r => r.source_words, tv: r => ({ maker: 'Maker', estimate: 'Estimate', doubtful: 'Doubtful' })[r.source], s: r => ({ maker: 0, estimate: 1, doubtful: 2 })[r.source] },
  };
}
const CMP_HELP = {
  perwatt: 'The PAR times the area it lights, for each watt it draws: higher gives more light for the electricity. Rough, because the edges of the area get less than the centre.',
  perlight: 'Dollars for each 100 µmol/s of light landing in the area it lights at this distance. Lower is better value. Rough, for the same reason.',
  source: "Maker's figures, Claude's estimate (the maker gives none), or Doubtful (the listing contradicts itself).",
};
function cmpShown() {
  const p = cmpPref(), all = cmpCols();
  return (Array.isArray(p.cols) && p.cols.length ? p.cols : CMP_DEF_COLS).filter(k => all[k]);
}

// ---- filters: [key, words for its chip, test]
function cmpFilters() {
  const f = CMP.f, out = [];
  if (f.status !== 'active') out.push(['status', f.status === 'all' ? 'Showing every light' : `Only: ${CMP.d.statuses[f.status].toLowerCase()}`, r => f.status === 'all' || r.status === f.status]);
  else out.push(['', '', r => r.status !== 'retired']);
  if (f.points) out.push(['points', `Points ${CMP.d.directions[f.points].toLowerCase()}`, r => r.direction === f.points]);
  if (f.dimmable) out.push(['dimmable', 'Can be dimmed', r => r.dimmable]);
  if (f.repeats) out.push(['repeats', 'Timer repeats every day', r => r.timer_repeats]);
  if (f.socket) out.push(['socket', f.socket === 'yes' ? 'Needs a socket' : 'Does not need a socket', r => r.needs_socket === (f.socket === 'yes')]);
  if (has(f.kmin)) out.push(['kmin', `Colour at least ${f.kmin}K`, r => has(r.kelvin) && r.kelvin >= +f.kmin]);
  if (has(f.kmax)) out.push(['kmax', `Colour at most ${f.kmax}K`, r => has(r.kelvin) && r.kelvin <= +f.kmax]);
  if (has(f.ppfd)) out.push(['ppfd', `At least ${f.ppfd} PAR at ${lenF(CMP.d.at)}`, r => has(r.ppfd) && r.ppfd >= +f.ppfd]);
  if (f.mount) out.push(['mount', `Holds: ${CMP.d.mount_kinds[f.mount].toLowerCase()}`, r => r.mount_kind === f.mount]);
  return out;
}
function cmpRows() {
  const q = CMP.q.trim().toLowerCase(), fs = cmpFilters(), col = cmpCols()[CMP.sort.k] || cmpCols().ppfd, dir = CMP.sort.dir;
  let rows = CMP.d.rows.filter(r => fs.every(([, , t]) => t(r)) && (!q || [r.name, r.brand, r.kind, r.model].join(' ').toLowerCase().includes(q)));
  const key = r => col.s(r);
  rows = rows.slice().sort((a, b) => {
    const x = key(a), y = key(b);
    if (!has(x) && !has(y)) return a.name.localeCompare(b.name);
    if (!has(x)) return 1;                                      // not known always last, whichever way
    if (!has(y)) return -1;
    const c = typeof x === 'string' ? x.localeCompare(y, undefined, { numeric: true, sensitivity: 'base' }) : x - y;
    return (dir === 'desc' ? -c : c) || a.name.localeCompare(b.name);
  });
  return rows;
}
const cmpDirWord = (k, dir) => { const c = cmpCols()[k]; const text = c && typeof c.s(CMP.d.rows[0] || {}) === 'string'; return text ? (dir === 'desc' ? 'Z to A' : 'A to Z') : (dir === 'desc' ? 'highest first' : 'lowest first'); };

// ---- the page
async function viewCompare() {
  const p = cmpPref();
  const at = p.at || 12, hours = p.hours || 12;
  const d = await api('GET', `/api/lights/compare?at=${at}&hours=${hours}`);
  CMP = { d, q: CMP ? CMP.q : '', sort: p.sort || { k: 'ppfd', dir: 'desc' }, picked: CMP ? CMP.picked : [], cards: false,
    f: CMP ? CMP.f : { status: 'active', points: '', dimmable: false, repeats: false, socket: '', kmin: '', kmax: '', ppfd: '', mount: '' } };
  CMP.picked = CMP.picked.filter(id => d.rows.some(r => r.id === id));
  const can = canChange(), cols = cmpCols();
  const sel = (act, label, opts, cur, id, k) => html`<label class="f">${label}<select data-act="${act}" ${id ? raw(`id="${id}"`) : ''} ${k ? raw(`data-k="${k}"`) : ''}>${opts.map(([v, w]) => html`<option value="${v}" ${String(v) === String(cur) ? raw('selected') : ''}>${w}</option>`)}</select></label>`;
  setTimeout(cmpFit, 0);
  return { title: 'Compare lights', html: html`<h1>Compare lights</h1>
    <p class="lede">Your grow lights and the ones you are considering, worked out at one distance from the leaves, because makers measure at different distances. Outside a maker's figures a light says "beyond the maker's chart" rather than a stretched guess. <a href="#/lights">Grow lights</a> is where you set up spots.</p>
    ${can ? html`<p class="row noprint"><button class="btn" type="button" data-act="cmpnew">Add a light you are considering</button></p>` : ''}
    <div class="cmp-controls" role="group" aria-label="What to compare">
      ${sel('cmpat', 'Compare at', d.choices.map(x => [x, lenF(x)]), d.at)}
      ${sel('cmphours', 'Hours a day', d.hours_choices.map(x => [x, `${x} hours`]), d.hours)}
      <label class="f cmp-q">Search<input type="search" id="cmp-q" value="${CMP.q}" autocomplete="off" placeholder="Name, brand or kind"></label>
      ${sel('cmpsort', 'Sort by', Object.entries(cols).map(([k, c]) => [k, c.label]).concat([['name', 'Name']]), CMP.sort.k, 'cmp-sortk')}
      <label class="f">Order<select data-act="cmpdir" id="cmp-dir"><option value="desc" ${CMP.sort.dir === 'desc' ? raw('selected') : ''}>Highest or Z first</option><option value="asc" ${CMP.sort.dir === 'asc' ? raw('selected') : ''}>Lowest or A first</option></select></label>
      <p class="cmp-colbtn"><button class="btn ghost" type="button" data-act="cmpcols">Columns</button></p>
    </div>
    <details class="cmp-filters" id="cmp-filters" ${cmpFilters().length > 1 ? raw('open') : ''}><summary>Filters</summary>
      <div class="cmp-controls" role="group" aria-label="Filters">
        ${sel('cmpf', 'Show', [['active', 'Owned and considering'], ['owned', 'Owned'], ['considering', 'Considering'], ['retired', 'No longer used'], ['all', 'Every light']], CMP.f.status, '', 'status')}
        ${sel('cmpf', 'Points', [['', 'Any way']].concat(Object.entries(d.directions)), CMP.f.points, '', 'points')}
        ${sel('cmpf', 'Socket', [['', 'Either'], ['yes', 'Needs a socket'], ['no', 'Plugs in or wired']], CMP.f.socket, '', 'socket')}
        ${sel('cmpf', 'How it holds', [['', 'Any']].concat(Object.entries(d.mount_kinds)), CMP.f.mount, '', 'mount')}
        <label class="f cmp-n">Colour from (K)<input type="number" min="1000" max="10000" step="100" data-act="cmpf" data-k="kmin" value="${CMP.f.kmin}"></label>
        <label class="f cmp-n">Colour to (K)<input type="number" min="1000" max="10000" step="100" data-act="cmpf" data-k="kmax" value="${CMP.f.kmax}"></label>
        <label class="f cmp-n">At least this PAR<input type="number" min="0" max="3000" step="10" data-act="cmpf" data-k="ppfd" value="${CMP.f.ppfd}"></label>
        <label class="chk"><input type="checkbox" data-act="cmpf" data-k="dimmable" ${CMP.f.dimmable ? raw('checked') : ''}> Can be dimmed</label>
        <label class="chk"><input type="checkbox" data-act="cmpf" data-k="repeats" ${CMP.f.repeats ? raw('checked') : ''}> Timer repeats every day</label>
      </div></details>
    <div id="cmp-chips" class="cmp-chips" aria-live="polite"></div>
    <p id="cmp-say" class="cmp-say" aria-live="polite" tabindex="-1"></p>
    <section id="cmp-picked" class="blk" hidden></section>
    <div id="cmp-list"></div>
    <section class="blk"><h2>How the numbers work</h2>
      <p>Each light's PAR and area at the distance you pick come from a smooth line through its maker's figures (or Claude's estimates, where the maker gives none). Daily light is the PAR times the hours. Light per watt and price per light are rough: they treat the whole area as getting the centre's light.</p>
      <p>${CMP_HELP.perlight}</p></section>` };
}
// Draw the parts that change with search, sort and filters, keeping the focus where it was
function cmpDraw() {
  if (!CMP || !document.getElementById('cmp-list')) return;
  const a = document.activeElement, keep = a && a.closest && a.closest('#cmp-list, #cmp-chips, #cmp-picked') && a.dataset.act ? [a.dataset.act, a.dataset.k || a.dataset.id || ''] : null;
  cmpDraw1();
  if (keep) {                                       // the same control after a redraw keeps the focus (a sort, a pick, a resize)
    const b = [...document.querySelectorAll(`[data-act="${keep[0]}"]`)].find(x => (x.dataset.k || x.dataset.id || '') === keep[1]);
    if (b) b.focus();
  }
}
function cmpDraw1() {
  const rows = cmpRows(), cols = cmpCols(), shown = cmpShown(), fs = cmpFilters().filter(x => x[0]);
  const chips = document.getElementById('cmp-chips');
  chips.innerHTML = rend(fs.length ? html`<span class="muted">Filters on:</span> ${fs.map(([k, w]) => html`<button class="chip" type="button" data-act="cmpchip" data-k="${k}" aria-label="Remove the filter: ${w}">${w} <span aria-hidden="true">✕</span></button>`)}
    <button class="btn ghost small" type="button" data-act="cmpchip" data-k="*">Clear all filters</button>` : '');
  const c = cols[CMP.sort.k];
  document.getElementById('cmp-say').textContent = `${rows.length} of ${CMP.d.rows.length} lights${CMP.q.trim() ? ` matching "${CMP.q.trim()}"` : ''}, sorted by ${c ? (/^[A-Z]{2}/.test(c.label) ? c.label : c.label.charAt(0).toLowerCase() + c.label.slice(1)) : 'name'}, ${CMP.sort.k === 'name' ? (CMP.sort.dir === 'desc' ? 'Z to A' : 'A to Z') : cmpDirWord(CMP.sort.k, CMP.sort.dir)}. Not known goes last.`;
  const list = document.getElementById('cmp-list');
  const pick = r => { const on = CMP.picked.includes(r.id), full = !on && CMP.picked.length >= 4;
    return html`<label class="chk cmp-pick"><input type="checkbox" data-act="cmppick" data-id="${r.id}" ${on ? raw('checked') : ''} ${full ? raw('disabled') : ''}> Pick<span class="sr"> ${r.name} to compare</span>${CMP.cards ? ' to compare' : ''}</label>`; };
  const nameBtn = r => html`<button class="linkish cmp-name" type="button" data-act="cmpopen" data-id="${r.id}">${r.name}</button>${r.status !== 'owned' ? html` <span class="tag">${r.status_word}</span>` : ''}`;
  if (!rows.length) { list.innerHTML = rend(html`<p class="muted">No light matches. Remove a filter or change the search.</p>`); cmpPickedDraw(); return; }
  if (CMP.cards) {
    list.innerHTML = rend(html`<ul class="cmp-cards">${rows.map(r => html`<li class="cmp-card"><h3>${nameBtn(r)}</h3>
      <dl class="dl">${shown.map(k => html`<dt>${cols[k].label}</dt><dd>${cols[k].v(r) || '—'}</dd>`)}</dl>${pick(r)}</li>`)}</ul>`);
  } else {
    const th = k => { const cur = CMP.sort.k === k, lab = k === 'name' ? 'Name' : (cols[k].tl || cols[k].label);
      return html`<th scope="col" ${raw(`aria-sort="${cur ? (CMP.sort.dir === 'desc' ? 'descending' : 'ascending') : 'none'}"`)}><button type="button" class="cmp-th" data-act="cmpth" data-k="${k}">${lab}<span aria-hidden="true">${cur ? (CMP.sort.dir === 'desc' ? ' ▼' : ' ▲') : ''}</span></button>${CMP_HELP[k] ? html`<span class="sr"> (${CMP_HELP[k]})</span>` : ''}</th>`; };
    list.innerHTML = rend(html`<div class="tbl-wrap wide cmp-wrap" id="cmp-wrap"><table class="tbl cmp-tbl"><caption class="sr">Lights compared at ${lenF(CMP.d.at)}, ${CMP.d.hours} hours a day</caption>
      <thead><tr>${th('name')}${shown.map(th)}<th scope="col"><span class="sr">Pick to compare</span></th></tr></thead>
      <tbody>${rows.map(r => html`<tr><th scope="row">${nameBtn(r)}</th>${shown.map(k => html`<td data-h="${cols[k].label}" ${k === 'source' ? raw(`title="${r.source_words.replace(/"/g, '&quot;')}"`) : ''}>${(cols[k].tv || cols[k].v)(r) || '—'}${k === 'source' && r.source === 'doubtful' ? html`<span class="sr">: ${r.source_words}</span>` : ''}</td>`)}<td>${pick(r)}</td></tr>`)}</tbody></table></div>`);
  }
  cmpPickedDraw();
}
// a table that does not fit the width becomes cards (phones, large text, many columns): the page never scrolls sideways
function cmpFit() {
  if (!CMP || !document.getElementById('cmp-list')) return;
  const narrow = innerWidth < 900; CMP.w = innerWidth;
  CMP.cards = narrow; cmpDraw();
  if (!narrow) { const w = document.getElementById('cmp-wrap'); if (w && w.scrollWidth > w.clientWidth + 1) { CMP.cards = true; cmpDraw(); } }
}
window.addEventListener('resize', () => { if (!CMP || CMP.w === innerWidth) return; CMP.w = innerWidth; clearTimeout(CMP.rt); CMP.rt = setTimeout(cmpFit, 200); });   // only when the width changes
document.addEventListener('input', e => {
  if (e.target.id !== 'cmp-q' || !CMP) return;
  clearTimeout(CMP.qt); CMP.qt = setTimeout(() => { CMP.q = e.target.value; cmpDraw(); }, 200);
});
document.addEventListener('keydown', e => { if (e.key === 'Enter' && e.target.id === 'cmp-q') e.preventDefault(); });
// two to four lights side by side: one row per column, one column per light; stacked under each other when that does not fit
function cmpPickedDraw() {
  const box = document.getElementById('cmp-picked'); if (!box) return;
  const ls = CMP.picked.map(id => CMP.d.rows.find(r => r.id === id)).filter(Boolean), cols = cmpCols();
  if (ls.length < 2) {
    box.hidden = ls.length === 0;
    box.innerHTML = rend(ls.length ? html`<p class="muted">Picked: ${ls[0].name}. Pick one to three more to see them side by side.</p>
      <p><button class="btn ghost small" type="button" data-act="cmpunpick">Clear the picks</button></p>` : '');
    return;
  }
  box.hidden = false;
  const keys = Object.keys(cols);
  const table = html`<div class="tbl-wrap wide" id="cmp-side-wrap"><table class="tbl cmp-side"><caption class="sr">The picked lights side by side</caption>
    <thead><tr><th scope="col">What</th>${ls.map(r => html`<th scope="col">${r.name}</th>`)}</tr></thead>
    <tbody>${keys.map(k => html`<tr><th scope="row">${cols[k].label}</th>${ls.map(r => html`<td>${cols[k].v(r) || '—'}</td>`)}</tr>`)}</tbody></table></div>`;
  box.innerHTML = rend(html`<h2>The ${ls.length} picked, side by side</h2>${table}
    <p class="row"><button class="btn ghost small" type="button" data-act="cmpunpick">Clear the picks</button></p>`);
  const w = document.getElementById('cmp-side-wrap');
  if (w && w.scrollWidth > w.clientWidth + 1) {                   // stacked: each thing, then each light's value under it
    w.outerHTML = rend(html`<dl class="cmp-stack">${keys.map(k => html`<dt>${cols[k].label}</dt><dd><ul>${ls.map(r => html`<li><strong>${r.name}:</strong> ${cols[k].v(r) || '—'}</li>`)}</ul></dd>`)}</dl>`);
  }
}

// ---- one light: everything about it, and what can be done with it
async function cmpOpen(id) {
  const r = CMP.d.rows.find(x => x.id === +id); if (!r) return;
  const cols = cmpCols(), can = canChange();
  const res = await modal(html`<form method="dialog" class="cmp-dlg"><h2>${r.name}</h2>
    ${r.photo ? html`<img class="cmp-photo" src="${r.photo}" alt="" loading="lazy">` : ''}
    <dl class="dl">${[['Status', r.status === 'owned' ? `Owned: ${cmpOwned(r)}` : r.status_word], ['Kind', r.kind], ['Model', r.model]].filter(x => x[1]).map(([a, b]) => html`<dt>${a}</dt><dd>${b}</dd>`)}
      ${Object.keys(cols).filter(k => k !== 'owned').map(k => html`<dt>${cols[k].label}</dt><dd>${cols[k].v(r) || '—'}</dd>`)}
      ${r.mount_words ? html`<dt>Mounting</dt><dd>${r.mount_words}</dd>` : ''}</dl>
    ${r.chart.length ? html`<p><strong>${r.source === 'estimate' ? "Claude's estimates" : "Maker's figures"}:</strong> ${r.chart.map(([x, y], i) => `${i ? ', ' : ''}${lenF(x)} ${fmt(y)} PAR`).join('')}.</p>` : ''}
    ${r.notes ? html`<p class="muted">${r.notes}</p>` : ''}
    ${r.url ? html`<p><a href="${r.url}" target="_blank" rel="noopener noreferrer">Open the listing</a></p>` : ''}
    <div class="row">${CMP.d.spots.length ? html`<button class="btn" value="try">Try it in a spot</button>` : ''}
      ${can && r.status !== 'owned' ? html`<button class="btn" value="bought">Bought it</button>` : ''}
      ${can ? html`<button class="btn ghost" value="edit">Change the listing details</button>` : ''}
      ${can && r.status === 'owned' && !r.in_use ? html`<button class="btn ghost" value="retire">No longer used</button>` : ''}
      ${can && r.status === 'retired' ? html`<button class="btn ghost" value="considering">Considering again</button>` : ''}
      ${can && r.status !== 'owned' && !r.in_use ? html`<button class="btn ghost" value="remove">Remove</button>` : ''}
      <button class="btn ghost" value="cancel">Close</button></div>
    ${!CMP.d.spots.length ? html`<p class="hint">Set up a light spot on Grow lights to try a light in it.</p>` : ''}</form>`);
  if (res === 'try') return cmpTry(r);
  if (res === 'bought') return cmpBought(r);
  if (res === 'edit') return cmpDialog(r);
  if (res === 'retire' || res === 'considering') {
    if (res === 'retire' && !(await confirmBox('No longer used?', `${r.name} leaves Your lights on Grow lights and stays here, under "No longer used".`, 'No longer used'))) return;
    await guard(async () => { await api('POST', `/api/lights/${r.id}/status`, { status: res === 'retire' ? 'retired' : 'considering' }); toast(res === 'retire' ? `No longer used: ${r.name}` : `Considering: ${r.name}`); route(); });
  }
  if (res === 'remove') {
    if (!(await confirmBox('Remove this light?', `${r.name} leaves the list.`, 'Remove light', true))) return;
    await guard(async () => { await api('DELETE', '/api/lights/' + r.id); toast(`Removed: ${r.name}`); route(); });
  }
}
async function cmpBought(r) {
  if (!(await needName())) return;
  const res = await modal(html`<form method="dialog"><h2>Bought: ${r.name}</h2>
    <p>It moves to Your lights on Grow lights, with what you entered here, so there is nothing to type again.</p>
    <div class="field-grid"><label class="f">How many<input type="number" name="count" min="1" max="100" step="1" value="1" required autofocus></label>
      <label class="f">Bought on<input type="date" name="on" value="${todayStr()}" max="${todayStr()}"></label></div>
    <div class="row"><button class="btn" value="ok">Bought it</button><button class="btn ghost" value="cancel" formnovalidate>Cancel</button></div></form>`, 'small');
  if (res !== 'ok') return;
  const f = dlg.querySelector('form');
  await guard(async () => { await api('POST', `/api/lights/${r.id}/status`, { status: 'owned', count: f.elements.count.value, on: f.elements.on.value });
    toast(`Bought: ${r.name}. It is in Your lights on Grow lights.`); route(); });
}
// a candidate's listing, or the listing details of any light (prices go on owned lights too)
async function cmpDialog(r) {
  if (!(await needName())) return;
  const L = r || {}, S = r ? (CMP.d.rows.find(x => x.id === r.id) || r) : {};
  const pts = S.chart ? S.chart.map(([x, y]) => `${fmt(x, 2)} in ${fmt(y, 2)}`).join(', ') : '';
  const yn = (name, label, v) => html`<label class="f">${label}<select name="${name}"><option value="" ${v == null ? raw('selected') : ''}>Not known</option><option value="1" ${v === true ? raw('selected') : ''}>Yes</option><option value="0" ${v === false ? raw('selected') : ''}>No</option></select></label>`;
  let x = null;
  for (;;) {
    const v = k => x ? x[k] : null;
    const res = await modal(html`<form method="dialog" class="cmp-form"><h2>${r ? `Listing details: ${L.name}` : 'Add a light you are considering'}</h2>
      ${r ? '' : html`<p class="hint">Copy what the listing gives; leave out what it does not say. "Bought it" later moves it to your lights without typing it again.</p>`}
      <label class="f">Name<input type="text" name="name" maxlength="80" required autofocus value="${v('name') ?? (L.name || '')}"></label>
      <div class="field-grid"><label class="f">Brand<input type="text" name="brand" maxlength="60" value="${v('brand') ?? (S.brand || '')}"></label>
        <label class="f">Kind<input type="text" name="kind" maxlength="40" value="${v('kind') ?? (S.kind || '')}"><small>For example bulb, strip or clamp light.</small></label></div>
      <label class="f">Link to the listing<input type="url" name="url" maxlength="400" value="${v('url') ?? (S.url || '')}"></label>
      <div class="field-grid"><label class="f">Price ($)<input type="number" name="price" min="0" max="100000" step="0.01" value="${v('price') ?? (has(S.price) ? S.price : '')}"></label>
        <label class="f">Price on<input type="date" name="price_on" value="${v('price_on') ?? (S.price_on || todayStr())}"><small>Prices move, so the date goes with it.</small></label>
        <label class="f">Watts<input type="number" name="watts" min="0" max="2000" step="any" value="${v('watts') ?? (has(S.watts) ? S.watts : '')}"></label></div>
      <label class="f">Light at distances (PPFD)<textarea name="points" rows="2" maxlength="400">${v('points') ?? pts}</textarea><small>Two or more, from the listing's chart: distance in inches and PAR, for example "12 in 719, 24 in 234". Add the area lit in brackets if it gives one, like "12 in 719 (3 sq ft)".</small></label>
      <div class="field-grid"><label class="f">Points<select name="direction"><option value="">Not known</option>${Object.entries(CMP.d.directions).map(([k, w]) => html`<option value="${k}" ${(v('direction') ?? S.direction) === k ? raw('selected') : ''}>${w}</option>`)}</select></label>
        <label class="f">Colour temperature (K)<input type="number" name="kelvin" min="1000" max="10000" step="100" value="${v('kelvin') ?? (S.kelvin || '')}"></label>
        <label class="f">Colour rendering (CRI)<input type="text" name="cri" maxlength="20" value="${v('cri') ?? (S.cri || '')}"></label></div>
      <div class="field-grid"><label class="f">Brightness steps (%)<input type="text" name="dimming" maxlength="40" value="${v('dimming') ?? (S.dimming ? S.dimming.join(', ') : '100')}"><small>"25, 50, 75, 100", or "100" for full only.</small></label>
        <label class="f">Timer<input type="text" name="timer" maxlength="120" value="${v('timer') ?? (S.timer || '')}"><small>What the listing says, for example "4, 8 or 12 hours".</small></label></div>
      <div class="field-grid">${yn('timer_repeats', 'Timer repeats every day', x ? (x.timer_repeats === '' ? null : x.timer_repeats === '1') : (S.timer ? !!S.timer_repeats : null))}
        ${yn('timer_keeps', 'Keeps its timer after a power cut', x ? (x.timer_keeps === '' ? null : x.timer_keeps === '1') : (S.timer_keeps ?? null))}
        ${yn('needs_socket', 'Needs a bulb socket', x ? (x.needs_socket === '' ? null : x.needs_socket === '1') : (r ? !!S.needs_socket : null))}</div>
      <label class="f">Notes<input type="text" name="notes" maxlength="600" value="${v('notes') ?? (S.notes || '')}"></label>
      <div class="row"><button class="btn" value="ok">${r ? 'Save changes' : 'Add the light'}</button><button class="btn ghost" value="cancel" formnovalidate>Cancel</button></div></form>`);
    if (res !== 'ok') return;
    const f = dlg.querySelector('form');
    x = Object.fromEntries(['name', 'brand', 'kind', 'url', 'price', 'price_on', 'watts', 'points', 'direction', 'kelvin', 'cri', 'dimming', 'timer', 'timer_repeats', 'timer_keeps', 'needs_socket', 'notes'].map(k => [k, f.elements[k].value]));
    try {
      if (r) await api('PUT', '/api/lights/' + r.id, x);
      else await api('POST', '/api/lights', { ...x, status: 'considering' });
      toast(r ? 'Saved: listing details' : `Added: ${x.name.trim()}, as a light you are considering`); route(); return;
    } catch (e) { toast(e.message, true); }
  }
}
// what each plant in one of your spots would get from this light
async function cmpTry(r) {
  const sp = CMP.d.spots;
  CMP.tryId = r.id;
  const shown = modal(html`<form method="dialog" class="cmp-try"><h2>Try ${r.name} in a spot</h2>
    <label class="f">Spot<select name="spot" id="cmp-try-spot" autofocus>${sp.map(s => html`<option value="${s.id}">${s.name}</option>`)}</select></label>
    <div id="cmp-try-out" aria-live="polite"><p class="muted">Working it out…</p></div>
    <div class="row"><button class="btn ghost" value="cancel">Close</button></div></form>`);
  cmpTryShow(r.id, sp[0].id);
  return shown;
}
async function cmpTryShow(id, spot) {
  const out = document.getElementById('cmp-try-out'); if (!out) return;
  try {
    const t = await api('GET', `/api/lights/${id}/try?spot=${spot}`), s = t.spot;
    const n = s.units > 1 ? `${s.units} of them` : 'one';
    out.innerHTML = rend(html`<p>The spot <strong>${s.name}</strong>${s.place ? ` (${s.place})` : ''}: ${lenF(s.distance_in)} from the leaves, ${fmt(s.hours, 1)} hours a day${s.dim_pct < 100 ? `, ${s.dim_pct}% brightness` : ''}.</p>
      <ul class="cmp-try-sum"><li><strong>Now</strong>, with ${s.light || 'its light'}: ${has(t.now.dli) ? `about ${fmt(t.now.dli, 1)} mol/m² a day` : 'not known'}${t.now.area_sqft ? `, lighting about ${areaF(t.now.area_sqft)}` : ''}.</li>
        <li><strong>With ${t.light.name}</strong> (${n}${t.new.dim_pct < 100 ? `, at ${t.new.dim_pct}%` : ''}): ${has(t.new.dli) ? `about ${fmt(t.new.dli, 1)} mol/m² a day` : 'not known'}${t.new.area_sqft ? `, lighting about ${areaF(t.new.area_sqft)}` : ''}${t.new.crowded ? '; crowded, so the plants at the edge get less' : ''}.</li></ul>
      ${t.notes.map(x => html`<p class="hint">${x}</p>`)}
      ${t.plants.length ? html`<div class="tbl-wrap"><table class="tbl cmp-try-tbl"><caption>Each plant there</caption>
        <thead><tr><th scope="col">Plant</th><th scope="col">Needs</th><th scope="col">Now</th><th scope="col">With this light</th></tr></thead>
        <tbody>${t.plants.map(p => html`<tr><th scope="row">${p.name} <span class="muted">${p.code}</span></th><td data-h="Needs">${has(p.lo) ? `${fmt(p.lo, 1)} to ${fmt(p.hi, 1)}` : 'Not set'}</td>
          <td data-h="Now">${lvTag(p.now_verdict, p.now_word)}</td><td data-h="With this light">${lvTag(p.new_verdict, p.new_word)}</td></tr>`)}</tbody></table></div>`
        : html`<p class="muted">No plants are in this spot yet.</p>`}
      <h3>Does it fit there?</h3>${fitBlock(t.fit)}`);
  } catch (e) { out.innerHTML = rend(html`<p class="muted">${e.message}</p>`); }
}
async function cmpColsDialog() {
  const cols = cmpCols(), shown = cmpShown();
  const res = await modal(html`<form method="dialog"><h2>Columns</h2><p>Choose what the table shows. The name always shows. Your choice follows you to any device you sign in on.</p>
    <fieldset class="cmp-colset"><legend class="sr">Columns</legend>${Object.entries(cols).map(([k, c]) => html`<label class="chk"><input type="checkbox" name="col" value="${k}" ${shown.includes(k) ? raw('checked') : ''}> ${c.label}</label>`)}</fieldset>
    <div class="row"><button class="btn" value="ok">Show these columns</button><button class="btn ghost" value="reset">Back to the usual columns</button><button class="btn ghost" value="cancel">Cancel</button></div></form>`);
  if (res === 'reset') cmpSave({ cols: null });
  else if (res === 'ok') cmpSave({ cols: [...dlg.querySelectorAll('input[name=col]:checked')].map(i => i.value) });
  else return;
  cmpFit();
}

addFeature({
  name: 'compare',
  // Not a link of its own in the top bar (the Care row would wrap); Grow lights links to it, and Search finds it.
  pages: { compare: { view: viewCompare, nav: 'lights', label: 'Compare lights', href: '#/compare' } },
  adds: [{
    id: 'cmp-ltlink',
    match: parts => parts[0] === 'lights',
    anchor: main => main.querySelector('#lt-lights > header'), where: 'beforeend',
    load: async () => true,
    html: () => html`<a class="btn ghost small noprint" id="cmp-ltlink" href="#/compare">Compare lights</a>`,
  }],
});
Object.assign(acts, {
  cmpnew: () => cmpDialog(null),
  cmpopen: el => cmpOpen(el.dataset.id),
  cmpcols: () => cmpColsDialog(),
  cmpth: el => { const k = el.dataset.k, c = cmpCols()[k];
    CMP.sort = CMP.sort.k === k ? { k, dir: CMP.sort.dir === 'desc' ? 'asc' : 'desc' } : { k, dir: k === 'name' || !c || !c.hi ? 'asc' : 'desc' };
    cmpSave({ sort: CMP.sort }); cmpDraw();
    const sk = document.getElementById('cmp-sortk'), sd = document.getElementById('cmp-dir'); if (sk) sk.value = k; if (sd) sd.value = CMP.sort.dir;
    const b = document.querySelector(`.cmp-th[data-k="${k}"]`); if (b) b.focus(); },
  cmpchip: el => { const k = el.dataset.k, F = CMP.f;                 // a chip removes its own filter; the focus goes to the next chip
    const clear = key => { if (key === 'status') F.status = 'active'; else F[key] = typeof F[key] === 'boolean' ? false : ''; };
    if (k === '*') Object.keys(F).forEach(clear); else clear(k);
    document.querySelectorAll('[data-act=cmpf]').forEach(c => { if (c.type === 'checkbox') c.checked = !!F[c.dataset.k]; else c.value = F[c.dataset.k]; });
    cmpDraw();
    const b = document.querySelector('#cmp-chips button.chip') || document.getElementById('cmp-say'); if (b) b.focus(); },
  cmpunpick: () => { CMP.picked = []; cmpDraw(); },
});
Object.assign(changeActs, {
  cmpat: el => { cmpSave({ at: +el.value }); route().then(() => { const s = document.querySelector('[data-act=cmpat]'); if (s) s.focus(); }); },
  cmphours: el => { cmpSave({ hours: +el.value }); route().then(() => { const s = document.querySelector('[data-act=cmphours]'); if (s) s.focus(); }); },
  cmpsort: el => { const c = cmpCols()[el.value]; CMP.sort = { k: el.value, dir: el.value === 'name' || !c || !c.hi ? 'asc' : 'desc' }; cmpSave({ sort: CMP.sort });
    const sd = document.getElementById('cmp-dir'); if (sd) sd.value = CMP.sort.dir; cmpDraw(); },
  cmpdir: el => { CMP.sort = { ...CMP.sort, dir: el.value }; cmpSave({ sort: CMP.sort }); cmpDraw(); },
  cmpf: el => { const v = el.type === 'checkbox' ? el.checked : el.value;   // unchanged: leave the chips alone, so a press on one that blurred this box still lands
    if (CMP.f[el.dataset.k] === v) return; CMP.f[el.dataset.k] = v; cmpDraw(); },
  cmppick: el => { const id = +el.dataset.id; CMP.picked = el.checked ? CMP.picked.concat(id).slice(0, 4) : CMP.picked.filter(x => x !== id); cmpDraw();
    const again = document.querySelector(`[data-act=cmppick][data-id="${id}"]`); if (again) again.focus(); },
});
// the spot chosen in "Try it in a spot"
document.addEventListener('change', e => { if (e.target.id === 'cmp-try-spot' && CMP && CMP.tryId) cmpTryShow(CMP.tryId, e.target.value); });
