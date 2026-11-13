/* Plant record front end: what is in each pot (1.56.0, PLAN.md step 9; plantdb/mixes.py). One of the files loaded in order by
   index.html (js/manifest.json); they share one scope. Plain JavaScript, no inline handlers (the server's content policy forbids them).

   - The Potting mixes page (#/mixes): recipes in parts by volume with an estimated summary and, once there are enough waterings,
     how often plants in each go between waterings; the amendments with their grades and properties; how often semi-hydro and
     water-only plants are topped up, flushed, given fresh water and have their roots checked.
   - On a plant's page, "What it is in": how it grows (soil mix, semi-hydro, water only), what holds its water, the mix its
     species wants, what it is in now (with "What is it in now?", "Repotted: record the new mix" and "Save as a recipe"), and
     for semi-hydro and water-only plants their own care.
   - On Today, the semi-hydro and water-only plants due a flush or a root check (top-ups and water changes are in the Water list). */
'use strict';

let MXD = null;                                    // /api/mixes, reloaded after each change
const mxLoad = async () => (MXD = await api('GET', '/api/mixes'));
const mxAm = id => (MXD && MXD.amendments.find(a => String(a.id) === String(id))) || null;
const mxLow = n => /^[A-Z]{2}/.test(n) ? n : n.charAt(0).toLowerCase() + n.slice(1);   // a name inside a sentence; LECA stays LECA
const MX_DOING = { topup: 'Topping up', flush: 'Flushing', waterchange: 'Fresh water', rootcheck: 'Checking the roots' };
const MX_ROLE_H = { part: 'Parts of a mix', medium: 'Semi-hydro media', additive: 'Additives (a pinch, not a part)' };

function mxSummary(s) {
  if (!s || !s.known) return html`<p class="muted">Not enough is known about its parts to estimate how it behaves.</p>`;
  return html`<p class="mx-shares">${s.shares.map(x => html`<span>${x.share}% ${mxLow(x.name)}${x.grade ? ` (${x.grade})` : ''}</span>`)}</p><p>${s.words}</p>`;
}
function mxInterval(r) {
  const iv = r.interval || {};
  if (iv.days) return html`<p><strong>Plants in it go about ${iv.days} days between waterings</strong> (${iv.plants} plants, since ${dateF(iv.since)}).</p>`;
  return html`<p class="muted">Watering gaps: not enough yet (${iv.plants || 0} of 3 plants, ${iv.gaps || 0} of 6 gaps logged). Keep pressing Watered and it will show here.</p>`;
}
const dateF = d => d ? parseYmd(d).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' }) : '';
// ---- the Potting mixes page
async function viewMixes() {
  await mxLoad();
  const can = canChange(), E = MXD.every;
  const byRole = r => MXD.amendments.filter(a => a.role === r);
  return { title: 'Potting mixes', html: html`<h1>Potting mixes</h1>
    <p class="lede">What goes into your pots: recipes in parts by volume, the amendments they are made of, and how often semi-hydro and water-only plants are looked after. A plant's own page says what it is in now; <a href="#/pots">Pots and trays</a> has the pots themselves.</p>
    <section class="blk" id="mx-recipes"><h2>Recipes (${MXD.recipes.length})</h2>
      ${can ? html`<p><button class="btn" type="button" data-act="mxrecipe">New recipe</button></p>` : ''}
      ${MXD.recipes.length ? html`<div class="mx-cards">${MXD.recipes.map(r => html`<article class="mx-card" data-id="${r.id}"><h3>${r.name}</h3>
          <p><strong>Parts:</strong> ${r.words}</p>${mxSummary(r.summary)}${mxInterval(r)}
          ${r.plants.length ? html`<p>In it now: ${r.plants.map((c, i) => html`${i ? ', ' : ''}<a href="#/plant/${enc(c)}">${c}</a>`)}</p>` : html`<p class="muted">No plant is in it yet.</p>`}
          ${r.notes ? html`<p class="muted">${r.notes}</p>` : ''}
          ${can ? html`<p class="row"><button class="btn ghost small" type="button" data-act="mxrecipe" data-id="${r.id}" aria-label="Change the recipe ${r.name}">Change</button>
            <button class="btn ghost small" type="button" data-act="mxrecipedel" data-id="${r.id}" aria-label="Remove the recipe ${r.name}">Remove</button></p>` : ''}</article>`)}</div>`
        : html`<p class="muted">No recipes yet. Make one here, or record what a plant is in on its page and press "Save as a recipe".</p>`}</section>
    <section class="blk" id="mx-amendments"><h2>Amendments (${MXD.amendments.length})</h2>
      <p class="hint">How much each holds water and lets in air is a rough guide for comparing them, from 1 (low) to 5 (very high), not a measurement. Change any that your own pots disagree with.</p>
      ${can ? html`<p><button class="btn" type="button" data-act="mxam">Add an amendment</button></p>` : ''}
      ${['part', 'medium', 'additive'].map(role => byRole(role).length ? html`<h3>${MX_ROLE_H[role]} (${byRole(role).length})</h3>
        <ul class="mx-ams">${byRole(role).map(a => html`<li><span><strong>${a.name}</strong>${a.grades.length ? html` <span class="muted">(${a.grades.join(', ')})</span>` : ''}<br>
          ${a.words ? html`${a.words[0].toUpperCase() + a.words.slice(1)}.` : html`<span class="muted">No properties set.</span>`}${a.notes ? html`<br><span class="muted">${a.notes}</span>` : ''}</span>
          ${can ? html`<span class="row"><button class="btn ghost small" type="button" data-act="mxam" data-id="${a.id}" aria-label="Change ${a.name}">Change</button>
            <button class="btn ghost small" type="button" data-act="mxamdel" data-id="${a.id}" aria-label="Remove ${a.name}">Remove</button></span>` : ''}</li>`)}</ul>` : '')}</section>
    <section class="blk" id="mx-every"><h2>Semi-hydro and water-only care</h2>
      <p>How often the app reminds you, in days. A plant's own "Water every" setting, if it has one, comes first for top-ups and water changes.</p>
      <form data-form="mxevery" class="field-grid">
        ${[['topup', 'Top up the reservoir'], ['flush', 'Flush (semi-hydro)'], ['waterchange', 'Change the water (water only)'], ['rootcheck', 'Check the roots (water only)']].map(([k, l]) =>
          html`<label class="f">${l}<input type="number" name="${k}" min="1" max="90" step="1" value="${E[k]}" ${can ? '' : raw('disabled')}></label>`)}
        ${can ? html`<p><button class="btn" type="submit">Save changes</button></p>` : ''}</form></section>` };
}
// ---- parts rows, shared by a recipe and a pot
function mxPartRow(p) {
  p = p || {};
  const a = mxAm(p.amendment_id), additive = a && a.role === 'additive';
  return html`<li class="mx-part">
    <label class="f">Amendment<select name="am" data-act="mxampick">${raw('<option value="">Choose…</option>')}${['part', 'medium', 'additive'].map(role => html`<optgroup label="${MX_ROLE_H[role]}">${MXD.amendments.filter(x => x.role === role).map(x => html`<option value="${x.id}" ${String(x.id) === String(p.amendment_id) ? raw('selected') : ''}>${x.name}</option>`)}</optgroup>`)}</select></label>
    <label class="f">Grade<input type="text" name="grade" maxlength="40" value="${p.grade || ''}" list="${a ? 'mx-gr-' + a.id : ''}" placeholder="${a && a.grades.length ? a.grades.join(', ') : 'Optional'}"></label>
    <label class="f mx-q" ${additive ? raw('hidden') : ''}>Parts<input type="number" name="parts" min="0" max="100" step="any" inputmode="decimal" value="${p.parts == null ? '' : p.parts}"></label>
    <label class="f mx-amt" ${additive ? '' : raw('hidden')}>How much<input type="text" name="amount" maxlength="60" value="${p.amount || ''}" placeholder="1 tablespoon a gallon"></label>
    <button class="btn ghost small" type="button" data-act="mxpartdel" aria-label="Remove this part">Remove</button></li>`;
}
const mxDatalists = () => html`${MXD.amendments.filter(a => a.grades.length).map(a => html`<datalist id="mx-gr-${a.id}">${a.grades.map(g => html`<option value="${g}"></option>`)}</datalist>`)}`;
function mxReadParts(f) {
  return [...f.querySelectorAll('.mx-part')].map(li => ({ amendment_id: li.querySelector('[name=am]').value, grade: li.querySelector('[name=grade]').value,
    parts: li.querySelector('[name=parts]').value, amount: li.querySelector('[name=amount]').value })).filter(p => p.amendment_id);
}
async function mxRecipeDialog(id) {
  if (!(await needName())) return;
  if (!MXD) await mxLoad();
  const r = id ? MXD.recipes.find(x => String(x.id) === String(id)) : null;
  const res = await modal(html`<form method="dialog" data-mxrecipe><h2>${r ? 'Change the recipe' : 'New recipe'}</h2>
    <label class="f">Name<input type="text" name="name" maxlength="80" required value="${r ? r.name : ''}" placeholder="Aroid chunky"></label>
    <p class="hint">Parts by volume, the way you scoop them: 3 parts bark, 2 parts perlite, 1 part coir. Halves are fine (0.5).</p>
    <ol class="mx-parts" id="mx-parts">${(r ? r.parts : [{}, {}]).map(mxPartRow)}</ol>
    <p><button class="btn ghost small" type="button" data-act="mxpartadd">Add a part</button></p>${mxDatalists()}
    <label class="f">Notes<textarea name="notes" rows="2" maxlength="600">${r ? r.notes : ''}</textarea></label>
    <div class="row"><button class="btn" value="ok">${r ? 'Save changes' : 'Save the recipe'}</button><button class="btn ghost" value="cancel" formnovalidate>Cancel</button></div></form>`, 'wide');
  if (res !== 'ok') return;
  const f = dlg.querySelector('form[data-mxrecipe]');
  const body = { name: f.elements.name.value, notes: f.elements.notes.value, parts: mxReadParts(f) };
  await guard(async () => { await api(r ? 'PUT' : 'POST', '/api/mixes/recipes' + (r ? '/' + r.id : ''), body); toast(r ? 'Recipe saved' : 'Recipe added: ' + body.name); MXD = null; route(); });
}
async function mxAmDialog(id) {
  if (!(await needName())) return;
  if (!MXD) await mxLoad();
  const a = id ? mxAm(id) : null, S = MXD.scale;
  const sel = (k, label, opts) => html`<label class="f">${label}<select name="${k}"><option value="">Not known</option>${opts.map(([v, l]) => html`<option value="${v}" ${a && a[k] != null && String(a[k]) === String(v) ? raw('selected') : ''}>${l}</option>`)}</select></label>`;
  const res = await modal(html`<form method="dialog" data-mxam><h2>${a ? 'Change ' + a.name : 'Add an amendment'}</h2>
    <div class="field-grid"><label class="f">Name<input type="text" name="name" maxlength="80" required value="${a ? a.name : ''}"></label>
      ${sel('role', 'What it is', Object.entries(MXD.roles))}</div>
    <label class="f">Grades or sizes<input type="text" name="grades" maxlength="300" value="${a ? a.grades.join(', ') : ''}" placeholder="small, medium, large"><small>Separate them with commas.</small></label>
    <div class="field-grid three">${sel('holds_water', 'Holds water', S.map((w, i) => [i + 1, `${i + 1}: ${w}`]))}${sel('airy', 'Lets in air', S.map((w, i) => [i + 1, `${i + 1}: ${w}`]))}
      ${sel('lasts_months', 'Breaks down in', [[0, 'Does not break down'], [6, 'About 6 months'], [12, 'About a year'], [18, 'About 18 months'], [24, 'About 2 years'], [36, 'About 3 years'], [60, 'About 5 years']])}
      ${sel('feeds', 'Feeds the plant', MXD.feeds.map((w, i) => [i, w[0].toUpperCase() + w.slice(1)]))}${sel('ph', 'pH', Object.entries(MXD.ph).map(([v, w]) => [v, w[0].toUpperCase() + w.slice(1)]))}
      ${sel('weight', 'Weight', MXD.weight.map((w, i) => [i + 1, w[0].toUpperCase() + w.slice(1)]))}</div>
    <label class="f">Notes<textarea name="notes" rows="2" maxlength="600">${a ? a.notes : ''}</textarea></label>
    <label class="f">Where this comes from<input type="text" name="source" maxlength="300" value="${a ? a.source : 'My own experience'}"></label>
    <div class="row"><button class="btn" value="ok">${a ? 'Save changes' : 'Add the amendment'}</button><button class="btn ghost" value="cancel" formnovalidate>Cancel</button></div></form>`, 'wide');
  if (res !== 'ok') return;
  const f = dlg.querySelector('form[data-mxam]'), body = {};
  ['name', 'role', 'grades', 'holds_water', 'airy', 'lasts_months', 'feeds', 'ph', 'weight', 'notes', 'source'].forEach(k => { body[k] = f.elements[k].value; });
  if (!body.role) body.role = 'part';
  await guard(async () => { await api(a ? 'PUT' : 'POST', '/api/mixes/amendments' + (a ? '/' + a.id : ''), body); toast(a ? 'Saved: ' + body.name : 'Added: ' + body.name); MXD = null; route(); });
}
// ---- on a plant's page
function mxLayerLine(L, what) { return L ? html`<p><strong>${what}:</strong> ${mxLow(L.name)}${L.grade ? ` (${L.grade})` : ''}${L.depth_in ? `, about ${lenF(L.depth_in)} deep` : ''}.</p>` : ''; }
function mxPlantHtml(S, p) {
  const can = canChange(), m = S.mix, ver = S.version;
  const opt = (k, label, list, val, none) => html`<label class="f">${label}<select data-act="mxfield" data-k="${k}" data-code="${S.code}" data-ver="${ver}" ${can ? '' : raw('disabled')}>
    <option value="">${none}</option>${list.map(x => html`<option ${x === val ? raw('selected') : ''}>${x}</option>`)}</select></label>`;
  const hy = (S.hydro || []).map(h => html`<li><strong>${MX_DOING[h.kind] || h.word}:</strong> ${h.last ? html`last ${relDay(h.last)}, ${h.state === 'due' ? html`<strong>due ${h.overdue > 0 ? `${h.overdue} day${h.overdue === 1 ? '' : 's'} ago` : 'today'}</strong>` : `next ${relDay(h.next)}`}` : 'nothing logged yet'} (about every ${h.every} days).
    ${can ? html`<button class="btn small ghost" type="button" data-act="care" data-kind="${h.kind}" data-code="${S.code}" data-name="${p.common_name}">${h.word}</button>` : ''}</li>`);
  return html`<section class="blk" id="mx-plant"><h2>What it is in</h2>
    <div class="field-grid mx-fields">${opt('grow_kind', 'How it grows', MX_GROW, S.grow_kind_set, 'Soil mix (not set)')}${opt('reservoir', 'What holds its water', MX_RES, S.reservoir, 'Not said')}
      ${opt('mix_wants', 'Mix its species wants', MX_WANTS, S.mix_wants_source === 'set on this plant' ? S.mix_wants : '', S.mix_wants && S.mix_wants_source !== 'set on this plant' ? 'Same as its species' : 'Not known')}</div>
    ${S.mix_wants && S.mix_wants_source && S.mix_wants_source !== 'set on this plant' ? html`<p class="hint">Its species wants a ${S.mix_wants.toLowerCase()} mix. Choose one above to set it for this plant alone.</p>` : ''}
    ${hy.length ? html`<h3>${S.grow_kind} care</h3><ul class="mx-hydro">${hy}</ul>` : ''}
    <h3>In it now</h3>
    ${m ? html`<p><strong>${m.recipe ? html`${m.recipe}: ` : ''}${m.words || 'a layer only'}</strong> <span class="muted">(since ${dateF(m.mixed_on)}${m.care_id ? ', when it was repotted' : ''})</span></p>
        ${mxLayerLine(m.top, 'Top layer')}${mxLayerLine(m.bottom, 'Bottom layer')}${m.notes ? html`<p class="muted">${m.notes}</p>` : ''}
        ${S.grow_kind === 'Soil mix' ? mxSummary(m.summary) : ''}
        ${S.warning ? html`<p class="notice"><strong>Does not suit its species:</strong> ${S.warning}</p>` : ''}`
      : html`<p class="muted">Not recorded yet.</p>`}
    ${can ? html`<p class="row noprint"><button class="btn small" type="button" data-act="mxpot" data-code="${S.code}">What is it in now?</button>
      <button class="btn small ghost" type="button" data-act="mxpot" data-code="${S.code}" data-repot="1">Repotted: record the new mix</button>
      ${m && !m.recipe && m.parts.length ? html`<button class="btn small ghost" type="button" data-act="mxsaverecipe" data-code="${S.code}">Save as a recipe</button>` : ''}
</p>` : ''}
    <p class="noprint"><a href="#/mixes">Potting mixes</a>: recipes and amendments.</p>
    ${S.history.length ? html`<details><summary>Earlier (${S.history.length})</summary><ul>${S.history.map(h => html`<li>${dateF(h.mixed_on)}: ${h.recipe ? `${h.recipe}: ` : ''}${h.words || 'a layer only'}${h.top ? `; top layer ${mxLow(h.top.name)}` : ''}
      ${can ? html` <button class="btn ghost small" type="button" data-act="mxpotdel" data-id="${h.id}" data-code="${S.code}" aria-label="Remove the entry of ${dateF(h.mixed_on)}">Remove</button>` : ''}</li>`)}</ul></details>` : ''}
  </section>`;
}
let MX_GROW = ['Soil mix', 'Semi-hydro', 'Water only'], MX_RES = [], MX_WANTS = [];
async function mxPotDialog(code, repot) {
  if (!(await needName())) return;
  await mxLoad(); MX_RES = MXD.reservoirs; MX_WANTS = MXD.mix_wants;
  const S = await guard(() => api('GET', '/api/mixes/plant/' + enc(code))); if (!S) return;
  const m = S.mix;
  const layer = (k, L) => html`<fieldset class="mx-layer"><legend>${k === 'top' ? 'Top layer (optional)' : 'Bottom layer (optional)'}</legend><div class="field-grid three">
    <label class="f">What<select name="${k}_am"><option value="">None</option>${MXD.amendments.filter(a => a.role !== 'additive').map(a => html`<option value="${a.id}" ${L && String(L.amendment_id) === String(a.id) ? raw('selected') : ''}>${a.name}</option>`)}</select></label>
    <label class="f">Grade<input type="text" name="${k}_grade" maxlength="40" value="${L ? L.grade : ''}"></label>
    <label class="f">How deep (${lenU()})<input type="number" name="${k}_depth" min="0" step="any" inputmode="decimal" value="${L && L.depth_in ? lenF(L.depth_in, false) : ''}"></label></div></fieldset>`;
  const res = await modal(html`<form method="dialog" data-mxpot><h2>${repot ? 'Repotted: the new mix' : 'What is it in now?'}</h2>
    <div class="field-grid"><label class="f">On<input type="date" name="mixed_on" value="${todayStr()}" max="${todayStr()}" required></label>
      <label class="chk"><input type="checkbox" name="repot" ${repot ? raw('checked') : ''}> This was a repot (logs "Repotted" on that day)</label></div>
    <label class="f">From a recipe<select name="recipe" data-act="mxrecipepick"><option value="">No recipe: list the parts</option>${MXD.recipes.map(r => html`<option value="${r.id}" ${m && String(m.recipe_id) === String(r.id) ? raw('selected') : ''}>${r.name}</option>`)}</select>
      <small>Choosing one fills in its parts. Change them if this pot differs.</small></label>
    <ol class="mx-parts" id="mx-parts">${(m && m.parts.length ? m.parts : [{}]).map(mxPartRow)}</ol>
    <p><button class="btn ghost small" type="button" data-act="mxpartadd">Add a part</button></p>${mxDatalists()}
    ${layer('top', m && m.top)}${layer('bottom', m && m.bottom)}
    <label class="f">Notes<input type="text" name="notes" maxlength="400" value=""></label>
    <label class="f">Also save these parts as a new recipe called (optional)<input type="text" name="save_as" maxlength="80"></label>
    <div class="row"><button class="btn" value="ok">Save</button><button class="btn ghost" value="cancel" formnovalidate>Cancel</button></div></form>`, 'wide');
  if (res !== 'ok') return;
  const f = dlg.querySelector('form[data-mxpot]');
  const L = k => f.elements[k + '_am'].value ? { amendment_id: f.elements[k + '_am'].value, grade: f.elements[k + '_grade'].value, depth_in: f.elements[k + '_depth'].value ? lenIn(f.elements[k + '_depth'].value) : '' } : null;
  const body = { mixed_on: f.elements.mixed_on.value, repot: f.elements.repot.checked, recipe_id: f.elements.recipe.value || null, parts: mxReadParts(f),
    top: L('top'), bottom: L('bottom'), notes: f.elements.notes.value, save_as: f.elements.save_as.value.trim() };
  await guard(async () => { await api('POST', '/api/mixes/plant/' + enc(code), body); toast(body.repot ? 'Repotted, with its mix' : 'Saved: what it is in'); MXD = null; route(); });
}
let MX_CARE = null;
function mxCare() {                       // Today's two parts ask in the same moment: one request serves both
  if (!MX_CARE) MX_CARE = api('GET', '/api/mixes/care').then(d => ({ due: d.items.filter(x => x.last), fresh: d.items.filter(x => !x.last), every: d.every }))
    .finally(() => { MX_CARE = null; });
  return MX_CARE;
}
const mxCareRow = x => html`<li class="job" data-code="${x.code}">${x.photo ? html`<img src="${thumbUrl(x.photo)}" alt="" loading="lazy" width="64" height="64">` : html`<span class="job-nophoto" aria-hidden="true"></span>`}
  <div class="job-txt"><a class="nm" href="#/plant/${enc(x.code)}">${x.name}</a> <span class="muted">${x.code}, ${x.grow_kind.toLowerCase()}</span>
    <div>${MX_DOING[x.kind] || x.word}: ${x.last ? `last ${relDay(x.last)}, ${x.overdue > 0 ? `${x.overdue} day${x.overdue === 1 ? '' : 's'} overdue` : 'due today'}` : 'nothing logged yet'} (about every ${x.every} days).</div></div>
  <div class="job-acts"><button class="btn small" type="button" data-act="care" data-kind="${x.kind}" data-code="${x.code}" data-name="${x.name}">${x.word}</button></div></li>`;
addFeature({
  name: 'mixes',
  care: { topup: 'Topped up the reservoir', flush: 'Flushed', waterchange: 'Changed the water', rootcheck: 'Checked the roots' },
  // not a link of its own in the top bar: one more would wrap the Care row and stop Grow lights' title staying at the top.
  // It belongs with Pots and trays (marked while it is open), which links to it, as does each plant's "What it is in".
  pages: { mixes: { view: viewMixes, nav: 'pots', label: 'Potting mixes', href: '#/mixes' } },      // a label with no section: Search finds it
  adds: [{
    id: 'mx-potslink',
    match: parts => parts[0] === 'pots',
    anchor: main => main.querySelector('h1 + p'), where: 'afterend',
    load: async () => true,
    html: () => html`<p class="mx-potslink" id="mx-potslink">What goes into the pots (recipes, amendments, and care for semi-hydro and water-only plants) is on <a href="#/mixes">Potting mixes</a>.</p>`,
  }, {
    id: 'mx-plant', care: true,
    match: parts => parts[0] === 'plant' && parts[1] && parts[2] !== 'edit',
    anchor: main => { const b = main.querySelector('#care-plant'); return b && b.closest('section'); }, where: 'afterend',
    load: async parts => {
      if (!CUR || CUR.p.code !== parts[1]) return null;
      const [S, M] = await Promise.all([api('GET', '/api/mixes/plant/' + enc(parts[1])), MXD ? Promise.resolve(MXD) : mxLoad()]);
      MX_RES = M.reservoirs; MX_WANTS = M.mix_wants; MX_GROW = M.grow_kinds;
      return { S, p: CUR.p };
    },
    html: ({ S, p }) => mxPlantHtml(S, p),
  }],
  // 1.58.0 (November 12 review, item 8): a flush or root check that has never been logged has no rhythm to be late on, so it is not counted as due
  // (it stayed on Today for ever: "Flush and roots (6)" with nothing logged). Those wait in a folded part until the first one is logged, like watering.
  today: [{
    id: 'mx-hydro', order: 33,                                       // just after Water (30)
    load: async () => { const d = await mxCare(); return d.due.length ? d : null; },
    jump: d => `Flush and roots (${d.due.length})`,
    html: d => html`<section class="blk" id="mx-hydro"><h2>Semi-hydro and water-only care (${d.due.length})</h2><ul class="jobs">${d.due.map(mxCareRow)}</ul></section>`,
  }, {
    id: 'mx-hydro-new', order: 34,
    load: async () => { const d = await mxCare(); return d.fresh.length ? d : null; },
    html: d => html`<section class="blk" id="mx-hydro-new"><details class="grp"><summary><h2>No flush or root check logged yet (${d.fresh.length})</h2></summary>
      <p class="hint">Semi-hydro pots are flushed and water-only plants have their roots checked now and then. None is logged for these yet, so there is no reminder: log the first one and the next is counted from that day.</p>
      <ul class="jobs">${d.fresh.map(mxCareRow)}</ul></details></section>`,
  }],
});
Object.assign(acts, {
  mxrecipe: el => mxRecipeDialog(el.dataset.id),
  mxam: el => mxAmDialog(el.dataset.id),
  async mxrecipedel(el) {
    const r = MXD && MXD.recipes.find(x => String(x.id) === el.dataset.id); if (!r || !(await needName())) return;
    if (!(await confirmBox(`Remove the recipe ${r.name}?`, 'Pots made with it keep their parts; only the recipe goes.', 'Remove the recipe'))) return;
    await guard(async () => { await api('DELETE', '/api/mixes/recipes/' + r.id); toast('Recipe removed: ' + r.name); MXD = null; route(); });
  },
  async mxamdel(el) {
    const a = mxAm(el.dataset.id); if (!a || !(await needName())) return;
    if (!(await confirmBox(`Remove ${a.name}?`, 'It goes from the list. Pots that had it keep it in their record.', 'Remove it'))) return;
    await guard(async () => { await api('DELETE', '/api/mixes/amendments/' + a.id); toast('Removed: ' + a.name); MXD = null; route(); });
  },
  mxpartadd(el) {
    const ol = el.closest('form').querySelector('.mx-parts'); ol.insertAdjacentHTML('beforeend', rend(mxPartRow({})));
    const s = ol.lastElementChild.querySelector('select'); if (s) s.focus();
  },
  mxpartdel(el) {
    const li = el.closest('.mx-part'), ol = li.parentElement; li.remove();
    if (!ol.children.length) ol.insertAdjacentHTML('beforeend', rend(mxPartRow({})));
    const s = ol.querySelector('select'); if (s) s.focus();
  },
  mxpot: el => mxPotDialog(el.dataset.code, !!el.dataset.repot),
  async mxpotdel(el) {
    if (!(await needName())) return;
    if (!(await confirmBox('Remove this entry?', 'It goes from the plant\'s list of what it was in. A "Repotted" entry in its care log stays.', 'Remove it'))) return;
    await guard(async () => { await api('DELETE', '/api/mixes/pot/' + el.dataset.id); toast('Entry removed'); route(); });
  },
  async mxsaverecipe(el) {
    if (!(await needName())) return;
    const S = await guard(() => api('GET', '/api/mixes/plant/' + enc(el.dataset.code))); if (!S || !S.mix) return;
    const res = await modal(html`<form method="dialog"><h2>Save as a recipe</h2><p>${S.mix.words}</p>
      <label class="f">Name of the recipe<input type="text" name="name" maxlength="80" required autofocus></label>
      <div class="row"><button class="btn" value="ok">Save the recipe</button><button class="btn ghost" value="cancel" formnovalidate>Cancel</button></div></form>`);
    if (res !== 'ok') return;
    const name = dlg.querySelector('form').elements.name.value;
    await guard(async () => { await api('POST', '/api/mixes/recipes', { name, parts: S.mix.parts.filter(p => p.amendment_id), notes: `Saved from ${el.dataset.code}` }); toast('Recipe saved: ' + name); MXD = null; route(); });
  },
});
Object.assign(changeActs, {
  mxampick(el) {                                      // an amendment chosen in a row: its grades, and parts or an amount
    const li = el.closest('.mx-part'), a = mxAm(el.value);
    const g = li.querySelector('[name=grade]'); g.setAttribute('list', a ? 'mx-gr-' + a.id : ''); g.placeholder = a && a.grades.length ? a.grades.join(', ') : 'Optional';
    const add = a && a.role === 'additive'; li.querySelector('.mx-q').hidden = add; li.querySelector('.mx-amt').hidden = !add;
  },
  mxrecipepick(el) {                                  // a recipe chosen for a pot: its parts fill the rows
    const r = MXD && MXD.recipes.find(x => String(x.id) === el.value); if (!r) return;
    const ol = el.closest('form').querySelector('.mx-parts'); ol.innerHTML = rend(html`${r.parts.map(mxPartRow)}`);
  },
  async mxfield(el) {                                 // how it grows, what holds its water, the mix it wants: saved as plant fields
    if (!(await needName())) { route(); return; }
    await guard(async () => {
      await api('PUT', '/api/plants/' + enc(el.dataset.code), { base_version: +el.dataset.ver, fields: { [el.dataset.k]: el.value } });
      toast('Saved'); CUR = null; route();
    });
  },
});
Object.assign(formActs, {
  async mxevery(f) {
    if (!(await needName())) return;
    const body = {}; ['topup', 'flush', 'waterchange', 'rootcheck'].forEach(k => { body[k] = f.elements[k].value; });
    await guard(async () => { await api('PUT', '/api/mixes/every', body); toast('Saved: how often'); MXD = null; route(); });
  },
});
