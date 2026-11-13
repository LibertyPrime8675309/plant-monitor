// ---------- layout previews (proto/first-screen; November 12 review, items 9 and 10) ----------
// Options Ethan chooses between from pictures on his screens. Nothing here is on unless localStorage "plantdb.preview" says so:
//   {"water": "rows" | "cards", "plants": "tools" | "chips", "plant": "top", "bar": "one"}
// so the app is unchanged without it. Each choice also sets data-pv-<name> on <html> for css/preview.css.
// The option he picks is then built as a real change and this file goes away.
'use strict';
const PVS = (() => { try { return JSON.parse(localStorage.getItem('plantdb.preview') || '{}') || {}; } catch (e) { return {}; } })();
const PV = k => PVS[k] || '';
for (const [k, v] of Object.entries(PVS)) if (v) document.documentElement.setAttribute('data-pv-' + k, v);

// Where a feature adds its line about a plant's care (repotting, turning, pests): the box with the care buttons, or, when those are
// under the plant's name (the "plant" option), a box of its own where the buttons used to be.
const quickMore = main => main.querySelector('#quick-more') || (b => b && b.parentElement)(main.querySelector('.quick-btns'));
// ----- item 9: the watering list in walking order -----
let WPL_ORDER = '';                // 'place' or 'late', for this visit
// The plants of a watering list grouped by room and spot, in the order of Rooms and spots (a room's plants with no spot come last in it).
function wplGroups(list, by) {
  const order = new Map(); let i = 0;
  for (const h of WHERE()) for (const a of h.areas) { for (const s of a.spots) order.set(a.id + '|' + s.id, { i: i++, a, s }); order.set(a.id + '|', { i: i++, a, s: null }); }
  const g = new Map();
  for (const w of list) { const p = by[w.code], k = (p.area_id || '') + '|' + (p.spot_id || ''); if (!g.has(k)) g.set(k, []); g.get(k).push(w); }
  return [...g.entries()].map(([k, ws]) => ({ k, o: order.get(k) || { i: 1e6, a: null, s: null }, ws })).sort((x, y) => x.o.i - y.o.i);
}
function waterShort(w) {          // "4 days overdue", "Due today": the part of waterWords() that changes from plant to plant
  if (w.state === 'unknown') return 'No watering logged yet';
  const od = w.overdue, hy = w.action && w.action !== 'water' ? HYDRO_DO[w.action][0] + ': ' : '';
  const s = od > 0 ? `${od} day${od === 1 ? '' : 's'} overdue` : od === 0 ? 'due today' : `next ${hy ? '' : 'check '}${relDay(w.next)}`;
  return hy ? hy + s : s[0].toUpperCase() + s.slice(1);
}
const wplLast = w => w.last_rain && (!w.last_water || w.last_rain > w.last_water) ? `Rain counted ${relDay(w.last_rain)}.` : w.last_water ? `Watered ${relDay(w.last_water)}.` : 'No watering logged yet.';
function wplWhy(w) { return html`<details class="wpl-why"><summary>Why</summary><p>${waterWords(w)}</p></details>`; }
function wplRow(p, w, btns) {
  return html`<li class="job wpl-row" data-code="${p.code}">${p.photo ? html`<img src="${thumbUrl(p.photo)}" alt="" loading="lazy" width="48" height="48">` : html`<span class="job-nophoto" aria-hidden="true"></span>`}
    <div class="job-txt"><a class="nm" href="#/plant/${enc(p.code)}">${p.common_name}</a> <span class="muted">${p.code}</span>
      <div class="wpl-line"><span class="wpl-st"><strong>${waterShort(w)}.</strong> <span class="wpl-last">${wplLast(w)}</span></span>${wplWhy(w)}</div></div>
    <div class="job-acts">${btns}</div></li>`;
}
function wplCard(p, w, btns) {
  return html`<li class="wpl-card" data-code="${p.code}"><a class="wpl-ph" href="#/plant/${enc(p.code)}" tabindex="-1" aria-hidden="true">${p.photo ? html`<img src="${thumbUrl(p.photo)}" alt="" loading="lazy" width="160" height="120">` : html`<span class="job-nophoto"></span>`}</a>
    <a class="nm" href="#/plant/${enc(p.code)}">${p.common_name}</a> <span class="muted">${p.code}</span>
    <p class="wpl-st"><strong>${waterShort(w)}.</strong></p>
    <div class="wpl-acts">${btns}</div>${wplWhy(w)}</li>`;
}
function waterByPlace(due, by, wbtn, kind, canAll) {
  const gs = wplGroups(due, by);
  return html`<div class="wpl wpl-as-${kind}">${gs.map((g, i) => {
    const name = g.o.a ? g.o.a.name + ': ' + (g.o.s ? g.o.s.name : 'no spot set') : 'No room set', n = g.ws.length;
    return html`<section class="wpl-grp" aria-labelledby="wpl-h-${i}"><div class="wpl-head"><h3 id="wpl-h-${i}">${name} <span class="wpl-n">(${n})</span></h3>
      ${n > 1 && canAll ? html`<button class="btn small" type="button" data-act="careall" data-kind="water" data-codes="${g.ws.map(w => w.code).join(',')}" aria-label="Watered all ${n} here: ${name}">Watered all ${n} here</button>` : ''}</div>
      <ul class="${kind === 'cards' ? 'wpl-cards' : 'jobs wpl-rows'}">${g.ws.map(w => kind === 'cards' ? wplCard(by[w.code], w, wbtn(w)) : wplRow(by[w.code], w, wbtn(w)))}</ul></section>`; })}</div>`;
}

// ----- item 10: All plants with its cards on the first screen -----
// One row of tools (search, where, winter plan, sort), one row of small buttons (more filters, what Claude needs, water all), then the cards.
// "chips" keeps the five winter-plan counts as a row of small buttons; "tools" makes them a list in the tool row.
// On a phone only the search box stays out: the lists go in the fold and the actions in a fold of their own.
function pvPlantsHead({ needN, fcN, todoN, lowN }) {
  const narrow = document.documentElement.dataset.narrow === '1', chips = PV('plants') === 'chips' && !narrow;
  const planN = pl => ALL.filter(p => statusOk(p) && p.winter_plan === pl).length;
  const lists = html`${homeFilter()}${siteFilter()}${chips ? '' : html`<label>Winter plan<select data-f="pnplan"><option value="">Any</option>${META.winter_plans.map(pl => html`<option value="${pl}" ${G.plan === pl ? raw('selected') : ''}>${pl} (${planN(pl)})</option>`)}</select></label>`}
    <label>Sort by<select data-f="sort">${Object.entries(SORTS).map(([k, v]) => html`<option value="${k}" ${G.sort === k ? raw('selected') : ''}>${v}</option>`)}</select></label>`;
  const needs = html`<button type="button" class="btn small ${G.needs ? '' : 'ghost'}" data-act="needs" aria-pressed="${String(G.needs)}">${G.needs ? 'Showing plants that need something from you' : 'Plants that need something from you'} (${needN})</button>`;
  const acts = html`<button type="button" class="btn small ghost" data-act="forclaude"><span>Copy my answers for Claude${fcN ? html`<span class="fc-n"> (${fcN} new)</span>` : ''}</span></button>
    ${todoN ? html`<a class="btn small ghost" href="#/photos">${todoN} to photograph</a>` : ''}
    <span class="water-all pv-wa noprint"><button class="btn small ghost" type="button" data-act="waterall" id="wa-btn" aria-describedby="wa-why wa-hint">Water all</button><span class="why" id="wa-why"></span>
      <details class="pv-what"><summary>What Water all does</summary><span class="hint" id="wa-hint"></span></details></span>`;
  const more = html`<label>Health<select data-f="health"><option value="">Any</option>${META.health.map(h => html`<option ${G.health === h ? raw('selected') : ''}>${h}</option>`)}</select></label>
      ${groupFilter()}${statusFilter()}
      <label class="chk"><input type="checkbox" data-f="low" ${G.low ? raw('checked') : ''}>ID confidence under 70% (${lowN})</label>`;
  const on = (G.health ? 1 : 0) + (G.group ? 1 : 0) + (G.status !== 'active' ? 1 : 0) + (G.low ? 1 : 0) + (narrow ? (G.plan ? 1 : 0) + (G.site ? 1 : 0) + (G.home ? 1 : 0) : 0);
  return html`<div class="hero pv-hero"><div class="pv-title"><h1 id="g-title">${G.status === 'archived' ? 'Archived plants' : 'All plants'}</h1><p id="count" class="muted" aria-live="polite"></p></div>
      <a class="btn" href="#/new">Add a plant</a></div>
    ${chips ? html`<div class="ledger pv-ledger" role="group" aria-label="Filter by winter plan">${ledger()}</div>` : ''}
    <div class="filters filters-main pv-tools"><label>Search<input type="search" data-f="q" value="${G.q}" placeholder="Name, code, location"></label>${narrow ? '' : lists}</div>
    ${placeChip()}
    <div class="pv-row">${moreFilters(html`${narrow ? lists : ''}${more}`, on)}
      ${narrow ? html`<details class="more-f pv-acts"><summary>More to do here</summary><div class="row">${needs}${acts}</div></details>` : html`${needs}${acts}`}</div>`;
}
