/* Plant record front end: lights that fit the room (1.56.0, PLAN.md step 8; plantdb/fit.py). One of the files loaded in order by
   index.html (js/manifest.json); they share one scope. Plain JavaScript, no inline handlers (the server's content policy forbids them).

   - How a light holds (its mount): shown on each light's card on Grow lights, set with "How it holds".
   - A room's or shelf's measurements and photos: "Measurements and photos" under Rooms and shelves.
   - Each light spot says whether its light fits there before its light is counted (fitBlock), and has a setup card to print
     (#/lightcard/ID) with a "Set up and checked" tick that clears itself when the spot changes.
   - Today lists the spots with plants that are not set up and checked yet.
   lights.js draws the Grow lights page and calls fitBlock(), checkedLine(), mountLine() and placeBits() from here. */
'use strict';

const FIT_ICON = { fits: '✓', nofit: '✗', tall: '▲', shaded: '◐', point: '↘', unchecked: '?', note: 'i' };
const FIT_STATUS_ICON = { fits: '✓', nofit: '✗', unchecked: '?' };
// the fit of a spot: a tag with the word, then one line per thing found (each with its own word, never colour alone)
function fitBlock(f, opts) {
  if (!f) return '';
  const o = opts || {};
  return html`<div class="fit fit-${f.status}" ${o.id ? raw(`id="${o.id}"`) : ''}>
    <p class="fit-head"><span class="fit-tag fit-${f.status}"><span aria-hidden="true">${FIT_STATUS_ICON[f.status] || ''}</span> ${f.word}</span>
      <span class="muted">${f.status === 'fits' ? 'The light can be put here.' : f.status === 'nofit' ? 'The light, or a plant, will not go here as it is.' : 'Something the app needs to check it is not filled in yet.'}</span></p>
    ${f.lines.length ? html`<ul class="fit-lines">${f.lines.map(x => html`<li class="fit-l fit-${x.kind}"><strong><span aria-hidden="true">${FIT_ICON[x.kind] || ''} </span>${x.word}:</strong> ${x.text}</li>`)}</ul>` : ''}</div>`;
}
function checkedLine(s, onCard) {
  const ch = s.checked, can = canChange();
  const card = onCard ? '' : html`<a class="btn ghost small" href="#/lightcard/${s.id}">Setup card</a>`;
  if (ch && !ch.stale) return html`<p class="fit-checked"><span><strong><span aria-hidden="true">✓ </span>Set up and checked</strong> ${timeEl(ch.at)} by ${ch.by}${ch.note ? html`: ${ch.note}` : ''}</span>
    <span class="row noprint">${card}${can ? html`<button class="btn ghost small" type="button" data-act="spotuncheck" data-id="${s.id}" aria-label="Take the tick off ${s.name}">Take the tick off</button>` : ''}</span></p>`;
  return html`<p class="fit-checked"><span><strong>${ch && ch.stale ? html`<span aria-hidden="true">↻ </span>Changed since it was checked` : 'Not set up and checked yet'}</strong>${ch && ch.stale ? html` (${timeEl(ch.at)} by ${ch.by})` : ''}</span>
    <span class="row noprint">${card}${can ? html`<button class="btn small" type="button" data-act="spotcheck" data-id="${s.id}" aria-label="${s.name}: set up and checked">Set up and checked</button>` : ''}</span></p>`;
}
function mountLine(L) {
  return html`<dt>How it holds</dt><dd>${L.mount_words || html`<span class="muted">Not said yet.</span>`}${canChange() ? html` <button class="btn ghost small noprint" type="button" data-act="ltmount" data-id="${L.id}" aria-label="How the ${L.name} holds">How it holds</button>` : ''}</dd>`;
}
function placeBits(pl) {      // a room's or shelf's main photo and measurements, and its button, under Rooms and shelves
  return html`${pl.photo ? html`<img class="fit-pthumb" src="${thumbUrl(pl.photo)}" alt="${pl.label}" loading="lazy">` : ''}
    <button class="btn ghost small noprint" type="button" data-act="ltplace" data-id="${pl.id}" aria-label="Measurements and photos of ${pl.label}">Measurements and photos</button>`;
}
// ---- how a light holds
const MOUNT_FIELDS = [['footprint_in', 'Base across', 'floor surface'], ['height_lo', 'Lowest height', 'floor'], ['height_hi', 'Height (or highest)', 'floor surface'],
  ['grip_in', 'Thickest edge it grips', 'clamp'], ['reach_in', 'Arm reach from the clamp', 'clamp'], ['length_in', 'Length it needs above the plants', 'under']];
async function mountDialog(L) {
  if (!(await needName())) return;
  const m = L.mount || {}, K = (LT && LT.mount_kinds) || {}, P = (LT && LT.points) || {};
  const num = ([k, label, kinds]) => html`<label class="f" data-mk="${kinds}">${label} (${lenU()})<input type="number" inputmode="decimal" min="0" step="any" name="${k}" value="${m[k] == null ? '' : lenF(m[k], false)}"></label>`;
  const shown = modal(html`<form method="dialog" class="fit-form" data-mount><h2>How the ${L.name} holds</h2>
    <p class="hint">So the app can tell whether it can be put where the plants are. Leave a number empty when you do not know it; the spot then says what is missing.</p>
    <label class="f">How it holds<select name="kind" data-act="mountkind"><option value="">Not said</option>${Object.entries(K).map(([k, l]) => html`<option value="${k}" ${m.kind === k ? raw('selected') : ''}>${l}</option>`)}</select></label>
    <label class="f" data-mk="socket floor surface clamp under hang">Which way it points<select name="points">${Object.entries(P).map(([k, l]) => html`<option value="${k}" ${(m.points || 'down') === k ? raw('selected') : ''}>${l[0].toUpperCase() + l.slice(1)}</option>`)}</select></label>
    <div class="field-grid three">${MOUNT_FIELDS.map(num)}</div>
    <label class="chk" data-mk="clamp"><input type="checkbox" name="pot_rim" ${m.pot_rim ? raw('checked') : ''}> It can also clip onto the rim of a pot</label>
    <div class="row"><button class="btn" value="ok">Save changes</button><button class="btn ghost" value="cancel" formnovalidate>Cancel</button></div></form>`);
  mountKindShow();
  if ((await shown) !== 'ok') return;
  const f = dlg.querySelector('form[data-mount]'), kind = f.elements.kind.value;
  const mount = kind ? { kind, points: f.elements.points.value, pot_rim: f.elements.pot_rim.checked } : {};
  if (kind) MOUNT_FIELDS.forEach(([k, , kinds]) => { const v = f.elements[k].value; if (v !== '' && kinds.split(' ').includes(kind)) mount[k] = lenIn(v); });
  await guard(async () => { await api('PUT', '/api/lights/' + L.id, { mount }); toast(kind ? 'Saved: how it holds' : 'Cleared: how it holds'); LT = null; route(); });
}
function mountKindShow() {
  const f = dlg.querySelector('form[data-mount]'); if (!f) return;
  const k = f.elements.kind.value;
  f.querySelectorAll('[data-mk]').forEach(el => { el.hidden = !k || !el.dataset.mk.split(' ').includes(k); });
}
// ---- a room's or shelf's measurements and photos
const SHEET_SHELF = [['levels', 'Levels', '', 'How many levels hold plants. 1 for a table or a single shelf.'], ['gap_in', 'Clear height between levels', 'len', 'From the top of one level to the underside of the next.'],
  ['width_in', 'Width of a level', 'len', ''], ['depth_in', 'Depth of a level', 'len', ''], ['free_in', 'Free surface beside the plants', 'len', 'Room on the level for the base of a light that stands.'],
  ['floor_in', 'Free floor beside it', 'len', 'Room for a floor stand.']];
const SHEET_ROOM = [['ceiling_in', 'Ceiling height', 'len', ''], ['floor_in', 'Free floor for a stand', 'len', '']];
function placePhotos(P) {
  const can = canChange();
  return html`<div class="fit-photos" id="pd-photos">${P.photos.length ? P.photos.map((ph, i) => html`<figure><img src="${thumbUrl(ph.file)}" alt="${P.label}, photo ${i + 1}${ph.is_primary ? ' (main photo)' : ''}" loading="lazy">
      <figcaption>${ph.is_primary ? 'Main photo' : html`Photo ${i + 1}`}</figcaption>
      ${can ? html`<span class="row">${ph.is_primary ? '' : html`<button class="btn ghost small" type="button" data-act="placephotomain" data-id="${ph.id}" aria-label="Make photo ${i + 1} the main photo">Make it the main photo</button>`}
        <button class="btn ghost small" type="button" data-act="placephotodel" data-id="${ph.id}" aria-label="Remove photo ${i + 1}">Remove</button></span>` : ''}</figure>`)
    : html`<p class="muted">No photo yet. A photo of each shelf helps when you fill in its measurements and set up a light.</p>`}
    ${can ? html`<label class="btn ghost small">Add photos<input type="file" accept="image/*" multiple class="sr" data-act="placephoto" data-id="${P.id}"></label>` : ''}</div>`;
}
async function roomSheetDialog(pid) {
  if (!(await needName())) return;
  let P = await guard(() => api('GET', '/api/rooms/' + pid)); if (!P) return;
  const s = P.sheet || {}, can = canChange(), ro = can ? '' : raw('disabled');
  const fld = ([k, label, unit, hint]) => html`<label class="f">${label}${unit ? ` (${lenU()})` : ''}<input type="number" inputmode="decimal" min="0" step="any" name="${k}" value="${s[k] == null ? '' : unit ? lenF(s[k], false) : s[k]}" ${ro}>${hint ? html`<small>${hint}</small>` : ''}</label>`;
  const pick = (k, label, opts) => html`<label class="f">${label}<select name="${k}" ${ro}><option value="">Not known</option>${opts.map(([v, l]) => html`<option value="${v}" ${s[k] === v ? raw('selected') : ''}>${l}</option>`)}</select></label>`;
  const r = await modal(html`<form method="dialog" class="fit-form" data-place="${pid}"><h2>${P.label}</h2>
    <h3>Photos</h3>${placePhotos(P)}
    <h3>Measurements</h3><p class="hint">In ${lenU() === 'cm' ? 'centimetres' : 'inches'}. Fill in what you know; leave the rest empty. They let a light spot here say whether a light fits.</p>
    ${P.is_room ? html`<div class="field-grid three">${SHEET_ROOM.map(fld)}</div>${pick('socket', 'An outlet within reach', [['yes', 'Yes'], ['no', 'No']])}`
      : html`<div class="field-grid three">${SHEET_SHELF.map(fld)}</div>
      <div class="field-grid three">${pick('top', 'Above the top level', [['nothing', 'Nothing: open space'], ['ceiling', 'The ceiling'], ['other', 'Something else (a cabinet, another shelf)']])}
        ${fld(['top_in', 'Clear height above the top level', 'len', 'To the ceiling or whatever is above it.'])}</div>
      <div class="field-grid three">${pick('edge', 'An edge to clamp to', [['yes', 'Yes'], ['no', 'No']])}${fld(['edge_in', 'How thick the edge is', 'len', ''])}
        ${pick('socket', 'An outlet within reach', [['yes', 'Yes'], ['no', 'No']])}</div>`}
    <label class="f">Notes<textarea name="notes" rows="2" maxlength="400" ${ro}>${s.notes || ''}</textarea></label>
    <div class="row">${can ? html`<button class="btn" value="ok">Save changes</button>` : ''}<button class="btn ghost" value="cancel" formnovalidate>${can ? 'Cancel' : 'Close'}</button></div></form>`, 'wide');
  if (r !== 'ok') { LT = null; route(); return; }
  const f = dlg.querySelector('form[data-place]'), sheet = {};
  [...f.elements].forEach(el => {
    if (!el.name || el.value === '') return;
    const lenField = /_in$/.test(el.name);
    sheet[el.name] = lenField ? lenIn(el.value) : el.value;
  });
  await guard(async () => { await api('PUT', '/api/rooms/' + pid, { sheet }); toast('Measurements saved'); LT = null; route(); });
}
async function placePhotoRedraw(P) { const box = document.getElementById('pd-photos'); if (box) box.outerHTML = rend(placePhotos(P)); }
// ---- set up and checked
async function spotCheckDialog(id) {
  if (!(await needName())) return;
  const r = await modal(html`<form method="dialog"><h2>Set up and checked</h2>
    <p>Tick this once the light is up, the plants are under it, and it all fits as the setup card says.</p>
    <label class="f">What you found (optional)<input type="text" name="note" maxlength="400" autofocus><small>For example "the gooseneck does not reach the back row". It stays with the spot.</small></label>
    <div class="row"><button class="btn" value="ok">Set up and checked</button><button class="btn ghost" value="cancel" formnovalidate>Cancel</button></div></form>`);
  if (r !== 'ok') return;
  const note = dlg.querySelector('form').elements.note.value;
  await guard(async () => { await api('POST', `/api/lights/spots/${id}/checked`, { note }); toast('Set up and checked'); LT = null; route(); });
}
// ---- the setup card (#/lightcard/ID)
async function viewLightCard(parts) {
  LT = await api('GET', '/api/lights');
  const s = LT.spots.find(x => String(x.id) === String(parts[1]));
  if (!s) return { title: 'Setup card', html: html`<h1>Setup card</h1><p>That light spot is not set up any more. <a href="#/lights">Open Grow lights</a></p>` };
  const L = ltLight(s.light_id), M = (L && L.mount) || {}, side = M.points === 'side' || (L && L.specs.direction === 'side');
  const pl = (LT.places || []).find(p => p.id === s.place_id);
  const ps = s.plants.slice().sort((a, b) => side ? ((a.height_in ?? 999) - (b.height_in ?? 999)) : a.name.localeCompare(b.name));
  const holder = s.holder && LT.holders ? LT.holders[s.holder] : '';
  return { title: 'Setup card: ' + s.name, html: html`<p class="crumb noprint"><a href="#/lights">Grow lights</a></p>
    <article class="fit-card"><h1>Setup card: ${s.name}</h1>
      <div class="fit-card-top">${s.place_photo ? html`<img class="fit-card-photo" src="${thumbUrl(s.place_photo)}" alt="${s.place || ''}">` : ''}
        <dl class="dl"><dt>Where</dt><dd>${s.place || 'Not chosen yet'}${s.level ? (s.level === 'top' ? ', top level' : ', a lower level') : ''}</dd>
          ${pl && pl.words ? html`<dt>Its measurements</dt><dd>${pl.words}</dd>` : ''}
          <dt>Light</dt><dd>${s.units > 1 ? `${s.units} × ` : ''}${s.light}</dd>
          ${L && L.mount_words ? html`<dt>How it holds</dt><dd>${L.mount_words}${holder ? ` Here it screws into ${holder}.` : ''}</dd>` : ''}
          <dt>${side ? 'Beside the plants' : 'Above the leaves'}</dt><dd>${lenF(s.distance_in)} from the ${side ? 'nearest leaves, shining sideways' : 'top leaves'}${M.points === 'angled' ? ', angled in from the side' : ''}</dd>
          <dt>Hours a day</dt><dd>${fmt(s.hours, 1)}${s.dim_pct < 100 ? `, at ${s.dim_pct}% brightness` : ''}. ${s.timer_note || ''}</dd>
          <dt>Light at the leaves</dt><dd>About ${has(s.dli) ? s.dli : '?'} mol/m² a day</dd></dl></div>
      ${fitBlock(s.fit)}
      <h2>Plants${side ? ', nearest the light first' : ''} (${ps.length})</h2>
      ${ps.length ? html`<ol class="fit-card-plants">${ps.map(p => html`<li>${p.photo ? html`<img src="${thumbUrl(p.photo)}" alt="" loading="lazy">` : html`<span></span>`}
        <span><strong>${p.name}</strong> <span class="muted">${p.code}</span><br>${has(p.height_in) ? `${lenF(p.height_in)} tall with its pot` : html`<span class="muted">Height not known</span>`}. ${lvTag(p.verdict, p.verdict_word)}</span></li>`)}</ol>`
        : html`<p class="muted">No plants in this spot yet.</p>`}
      ${s.notes ? html`<p><strong>Note:</strong> ${s.notes}</p>` : ''}
      ${checkedLine(s, true)}
      <p class="row noprint"><button class="btn ghost" type="button" data-act="print">Print this card</button><a class="btn ghost" href="#/lights">Back to Grow lights</a></p></article>` };
}
addFeature({
  name: 'fit',
  pages: { lightcard: { view: viewLightCard, nav: 'lights' } },
  today: [{
    id: 'fit-unchecked', order: 74,
    load: async () => { const d = await api('GET', '/api/lights/unchecked'); return d.spots.length ? d : null; },
    jump: d => `Light spots (${d.spots.length})`,
    html: d => html`<section class="blk" id="fit-unchecked"><h2>Light spots to set up and check (${d.spots.length})</h2>
      <p>Each has plants in it but has not been ticked "Set up and checked"${d.spots.some(x => x.changed) ? ', or was changed since' : ''}. Its setup card says what goes where.</p>
      <ul class="fit-today">${d.spots.map(x => html`<li><a href="#/lightcard/${x.id}">${x.name}</a>${x.changed ? html` <span class="muted">(changed since it was checked)</span>` : ''}</li>`)}</ul></section>`,
  }],
});
Object.assign(acts, {
  ltmount: async el => {
    const L = ltLight(el.dataset.id); if (!L) return;
    await mountDialog(L);
  },
  ltplace: el => roomSheetDialog(+el.dataset.id),
  spotcheck: el => spotCheckDialog(el.dataset.id),
  spotuncheck: async el => { if (!(await needName())) return; await guard(async () => { await api('DELETE', `/api/lights/spots/${el.dataset.id}/checked`); toast('Tick taken off'); LT = null; route(); }); },
  placephotodel: async el => { if (!(await needName())) return; const P = await guard(() => api('DELETE', '/api/rooms/photos/' + el.dataset.id)); if (P) { toast('Photo removed'); placePhotoRedraw(P); } },
  placephotomain: async el => { if (!(await needName())) return; const P = await guard(() => api('PUT', '/api/rooms/photos/' + el.dataset.id, { primary: true })); if (P) { toast('Main photo changed'); placePhotoRedraw(P); } },
});
Object.assign(changeActs, {
  mountkind: () => mountKindShow(),
  async placephoto(el) {
    if (!el.files.length || !(await needName())) return;
    const fd = new FormData(); [...el.files].forEach(f => fd.append('files', f));
    const P = await guard(() => api('POST', '/api/rooms/' + el.dataset.id + '/photos', null, fd));
    if (P) { toast(el.files.length === 1 ? 'Photo added' : `${el.files.length} photos added`); placePhotoRedraw(P); }
  },
});
