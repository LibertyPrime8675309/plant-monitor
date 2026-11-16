'use strict';
/* Grow lights reads your layouts (prototype, proto/lights-read-layouts, on top of Layouts; Ethan, November 15, 2026: "Yes" to
   "Should Grow lights read a shelf's layout where there is one?", then "Proceed with grow lights reading a layout").

   A light spot on Grow lights is one setting for every plant in it: one distance from the leaves, one number. A layout knows more:
   where each plant stands under the light, how tall it is and how far to the side. So where a plant is drawn on a layout that has
   a grow light with its maker's figures, Grow lights shows that plant's own daily light from the drawing, with a link to the
   layout. A plant that is not drawn keeps what its spot gives, as before. Nothing is saved and nothing in the record changes: this
   module only reads (GET /api/layouts) and adds to two pages, Grow lights and a plant's own page.

   The sums are layouts.js's own (lyLight), so the two pages cannot disagree about a plant's number.

   Ethan chose, November 16, 2026: the plant's mark in its spot is the layout's (option 1); a light's hours and brightness are set on
   the layout (lights.py follows it: spot_layout, and layouts.py's layout_light_to_spots); a plant under a light on a layout but in no
   spot counts as having a light (lights.py: layout_lit, the summary and the suggested layout). The server works the same sums out
   (layouts.py: layout_light), and lightsread_check.py checks that the two agree. */
let LG = null;                                         // what the layouts say: { by: Map(plant code -> [reading]), lit: [layouts with a light that has figures], V: the verdicts' words }
const lgMol = n => `${fmt(n, 1)} mol/m² a day`;

// Every layout with a grow light that has figures, and for each plant drawn on one, its light there.
// A reading: { lid, lname, pid (the layout's place), name (the plant's), here (the record has the plant at that place), item, dli, verdict ('none' when
// no light reaches it), reached, need, on: [{ light_id, name, up, side, dli, hours, dim_pct }], shut: [names of lights shut out] }
async function lgRead() {
  const d = await api('GET', '/api/layouts'), by = new Map(), lit = [];
  for (const L of d.layouts) {
    const m = lyLight(L); if (!m.any) continue;
    lit.push(L);
    for (const it of L.items) {
      const x = it.kind === 'plant' && it.plant && !it.gone ? m.get(it.id) : null; if (!x) continue;
      const r = { lid: L.id, lname: L.name, pid: L.pid, name: it.name, here: it.rec != null && it.rec === L.pid, item: it.id, dli: x.dli, verdict: x.verdict, reached: x.reached, need: x.need,
        on: x.on.map(o => ({ light_id: o.li.light_id, name: o.li.name, up: o.up, side: o.side, dli: o.dli, hours: o.li.hours, dim_pct: o.li.dim_pct })), shut: x.shut.map(o => o.li.name) };
      if (!by.has(it.plant)) by.set(it.plant, []);
      by.get(it.plant).push(r);
    }
  }
  return (LG = { by, lit, V: d.verdicts || {} });
}
// The reading to use for a plant: on the layout of the spot's own place; else on the layout of the place the record has it; else
// one where a light reaches it; else any.
function lgFor(code, pid) {
  const a = (LG && LG.by.get(code)) || [];
  return a.find(r => pid != null && r.pid === pid) || a.find(r => r.here) || a.find(r => r.reached) || a[0] || null;
}
const lgTag = r => (r.reached ? lvTag(r.verdict, LG.V[r.verdict] || '') : html`<span class="lv lv-unknown lg-none"><span aria-hidden="true">– </span>No light reaches it</span>`);
const lgWhere = r => { const o = r.on[0]; return o ? `${lenF(r1(o.up))} under the ${o.name}${o.side >= 0.5 ? `, ${lenF(r1(o.side))} to the side` : ''}` : ''; };
const lgLink = r => html`<a href="#/layouts/${r.lid}?sel=${r.item}">${r.lname}</a>`;
// The line under a plant in its spot. was: the plant as its spot has it (its mark and word there).
function lgLine(r, was, s) {
  const differs = was && was.verdict && (was.verdict !== r.verdict);
  return html`<span class="lg-line">On the layout ${lgLink(r)}: ${r.reached ? html`about <strong>${lgMol(r.dli)}</strong>${lgWhere(r) ? `, ${lgWhere(r)}` : ''}.` : html`<strong>no light drawn there reaches it</strong>${r.shut.length ? ` (the ${r.shut[0]} is shut out)` : ''}.`}
    ${differs ? html` <span class="muted">The spot's one setting gives ${has(s.dli) ? s.dli : '?'} (${was.verdict_word}).</span>` : ''}</span>`;
}
// What a spot and the layout of its place say about the same light, in words for the spot's box.
function lgSpotLine(s, rs) {
  const count = new Map(); rs.forEach(r => count.set(r.lid, (count.get(r.lid) || 0) + 1));
  const lid = [...count].sort((a, b) => b[1] - a[1])[0][0], L = LG.lit.find(x => x.id === lid), mine = rs.filter(r => r.lid === lid);
  const li = L.items.find(i => i.kind === 'light' && i.light_id === s.light_id && !i.gone);
  const ups = mine.filter(r => r.reached).flatMap(r => r.on.filter(o => o.light_id === s.light_id).map(o => o.up)), lo = Math.min(...ups), hi = Math.max(...ups);
  const n = s.plants.length, k = mine.length, set = s.layout && s.layout.id === lid;
  return html`<div class="lg-spot" data-lid="${lid}"><p><strong>On the layout <a href="#/layouts/${lid}">${L.name}</a>:</strong> ${k === n ? (n === 1 ? 'its plant is' : `all ${n} of its plants are`) : `${k} of its ${n} plants ${k === 1 ? 'is' : 'are'}`} drawn.
      ${ups.length ? `${ups.length === 1 || Math.abs(hi - lo) < 0.5 ? `The top of ${ups.length === 1 ? 'the plant' : 'each'} is ${lenF(r1(lo))}` : `Their tops are ${lenF(r1(lo))} to ${lenF(r1(hi))}`} under this light; this spot says ${lenF(s.distance_in)} from the leaves.` : li ? 'This light reaches none of them there.' : 'This light is not drawn there.'}</p>
    ${set && li ? html`<p class="lg-set">Its hours (${fmt(li.hours, 1)} a day) and brightness (${li.dim_pct}%) are set on the layout, for this spot too.</p>` : ''}</div>`;
}
// Grow lights is on screen: each plant in a spot that is drawn on a layout gets its own number, and each such spot a line.
function lgSpots() {
  if (!LG || typeof LT === 'undefined' || !LT) return;
  document.querySelectorAll('#lt-spots details.lt-spot-fold[data-id]').forEach(box => {
    const s = LT.spots.find(x => String(x.id) === box.dataset.id); if (!s) return;
    const rs = [], final = [];
    box.querySelectorAll('ul.lt-plants > li').forEach(li => {
      const a = li.querySelector('a.nm'), code = a ? decodeURIComponent(a.getAttribute('href').replace('#/plant/', '')) : '', was = s.plants.find(p => p.code === code), r = was ? lgFor(code, s.place_id) : null;
      if (!r) { if (was) final.push(was.verdict); return; }
      rs.push(r); final.push(r.verdict);
      li.classList.add('lg-read'); li.dataset.lg = r.verdict;
      if (!li.querySelector('.lg-line')) li.insertAdjacentHTML('beforeend', rend(lgLine(r, was, s)));      // a row of its own under the plant, the whole width of its box
      const tag = li.querySelector(':scope > .lv');
      if (tag) tag.outerHTML = rend(lgTag(r));
    });
    if (!rs.length) return;
    const list = box.querySelector('ul.lt-plants');
    if (list && !box.querySelector('.lg-spot')) list.insertAdjacentHTML('beforebegin', rend(lgSpotLine(s, rs)));
    const sum = box.querySelector('summary .lt-sum');
    if (sum && !sum.querySelector('.lg-sum')) {
      const off = final.filter(v => v && !['good', 'unknown'].includes(v)).length, n = s.plants.length;
      const plants = [...sum.children].find(x => x.firstElementChild && x.firstElementChild.textContent === 'Plants:');
      if (plants) plants.innerHTML = rend(html`<strong>Plants:</strong> ${n}${off ? ` (${off} not in their range)` : ''}`);
      sum.insertAdjacentHTML('beforeend', rend(html`<span class="lg-sum">${rs.length === n ? (n === 1 ? 'Read from its layout' : `All ${n} read from a layout`) : `${rs.length} of ${n} read from a layout`}</span>`));
    }
  });
}

addFeature({
  name: 'layoutlights',
  adds: [{
    id: 'lg-note',
    match: parts => parts[0] === 'lights',
    anchor: main => main.querySelector('#lt-spots .sec-head'), where: 'afterend',
    load: async () => { const d = await lgRead(); return d.lit.length ? d : null; },
    html: d => {
      if (typeof LT === 'undefined' || !LT) return '';
      const inSpots = LT.spots.flatMap(s => s.plants.map(p => ({ p, r: lgFor(p.code, s.place_id) }))).filter(x => x.r).length;
      const loose = Object.keys(LT.drawn || {}).map(code => ({ code, r: lgFor(code, null) })).filter(x => x.r && x.r.reached);
      return html`<div class="lg-note" id="lg-note"><p><strong>Read from your layouts.</strong> ${d.lit.length === 1 ? html`Your layout <a href="#/layouts/${d.lit[0].id}">${d.lit[0].name}</a> has a grow light drawn on it.` : html`${d.lit.length} of your <a href="#/layouts">layouts</a> have a grow light drawn on them.`}
          ${inSpots ? `${inSpots === 1 ? 'One plant in the spots below is' : `${inSpots} of the plants in the spots below are`} drawn there, so ${inSpots === 1 ? 'its' : 'their'} light is read from where ${inSpots === 1 ? 'it stands' : 'each stands'} on the drawing: its own distance under the light, and how far to the side.` : 'No plant in the spots below is drawn there yet.'}
          A plant that is not drawn keeps what its spot gives.</p>
        ${loose.length ? html`<details class="lg-fold"><summary class="btn small ghost"><span>Under a light on a layout, but in no light spot (${loose.length})</span></summary>
          <p class="hint">These count as having a light: the summary above and the suggested layout below leave them out.</p>
          <ul class="lt-plants lt-two">${loose.map(({ code, r }) => html`<li><span></span><span class="lt-pt"><a class="nm" href="#/plant/${enc(code)}">${r.name}</a><span class="lg-code">${code}</span></span>${lgTag(r)}
            <span class="lg-line">On the layout ${lgLink(r)}: about <strong>${lgMol(r.dli)}</strong>${lgWhere(r) ? `, ${lgWhere(r)}` : ''}.</span></li>`)}</ul></details>` : ''}</div>`;
    },
    then: () => lgSpots(),
  }, {
    id: 'lg-plant',
    match: parts => parts[0] === 'plant' && parts[1] && parts[2] !== 'edit',
    anchor: '#pl-grow', where: 'afterend',
    load: async parts => { await lgRead(); const r = lgFor(decodeURIComponent(parts[1]), null); return r ? { r } : null; },
    html: ({ r }) => html`<p class="lg-plant" id="lg-plant"><strong>Its light on the layout ${lgLink(r)}:</strong> ${r.reached ? html`about ${lgMol(r.dli)}${lgWhere(r) ? `, ${lgWhere(r)}` : ''}.` : 'no light drawn there reaches it.'} ${lgTag(r)}
      <span class="hint lg-hint">Read from where it is drawn. A light spot gives one number for every plant in it.</span></p>`,
  }],
});
