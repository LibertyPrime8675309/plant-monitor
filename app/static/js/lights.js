/* Plant record front end: grow lights. One of the files app.js was split into in 1.32.0; they load in order (index.html) and share one scope,
   so a function here may call any other. Plain JavaScript, no inline handlers (the server's content policy forbids them). */
'use strict';

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
      <span class="row noprint"><button class="btn ghost small" type="button" data-act="roomedit" data-id="${pl.id}" aria-label="Rename the room ${pl.name}">Rename</button><button class="btn ghost small" type="button" data-act="roomdel" data-id="${pl.id}" aria-label="Remove the room ${pl.name}">Remove</button></span></li>`; })}</ul></section>`)}</div>`;
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
  return L && L.specs.needs_socket && !L.fixture ? html`<p class="notice"><strong>Needs a socket.</strong> This bulb screws into a lamp or clamp light. Note which one under "Where it is" on the light (Your lights, at the top of the page).</p>` : '';
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
    <dl class="dl lt-facts"><dt>You have</dt><dd>${L.count}${L.in_use ? ` (${L.in_use} in use in your spots)` : ''}</dd>${S.model ? html`<dt>Model</dt><dd>${S.model}</dd>` : ''}${L.fixture ? html`<dt>Where it is</dt><dd>${L.fixture}</dd>` : ''}</dl>
    ${canChange() ? html`<p class="row noprint"><button class="btn ghost small" type="button" data-act="ltedit" data-id="${L.id}" aria-expanded="false" aria-controls="lt-ed-${L.id}">Edit the name, count, model and where it is</button></p>` : ''}
    ${(() => { const can = canChange(), ed = k => raw(`data-ed="light" data-id="${L.id}" data-k="${k}" ${can ? '' : 'readonly'}`); return html`<div class="field-grid lt-ed" id="lt-ed-${L.id}" hidden>
      <label class="f">Name<input type="text" maxlength="80" value="${L.name}" ${ed('name')}></label>
      <label class="f lt-n">How many you have<input type="number" inputmode="numeric" min="0" max="100" step="1" value="${L.count}" ${ed('count')}><small>${L.in_use ? `${L.in_use} in use in your spots.` : 'None in a spot yet.'}</small></label>
      <label class="f">Manufacturer model<input type="text" maxlength="80" value="${S.model || ''}" ${ed('model')}></label>
      <label class="f">Where it is<input type="text" maxlength="600" value="${L.fixture || ''}" ${ed('fixture')}><small>For a bulb, the lamp or socket it screws into.</small></label></div>`; })()}
    <dl class="dl">
      ${S.kind ? html`<dt>Type</dt><dd>${S.kind}</dd>` : ''}
      ${bits.length ? html`<dt>Light</dt><dd>${bits.join(', ')}</dd>` : ''}
      ${sp ? html`<dt>Colour mix</dt><dd>Blue ${sp.blue}%, green ${sp.green}%, red ${sp.red}%, far red ${sp.far_red}%</dd>` : ''}
      ${S.power ? html`<dt>Power</dt><dd>${S.power}</dd>` : ''}
      ${S.timer ? html`<dt>Timer</dt><dd>${S.timer}</dd>` : ''}
      <dt>Brightness</dt><dd>${S.dimming && S.dimming.length > 1 ? S.dimming.map(x => x + '%').join(', ') : 'Full only'}</dd>
      ${S.size ? html`<dt>Size</dt><dd>${S.size}</dd>` : ''}
    </dl>${edLong('light', L.id, 'notes', 'Notes', L.notes, canChange())}
    ${L.points.length ? html`<div class="tbl-wrap"><table class="tbl lt-ppfd"><caption>${S.estimated ? "Claude's estimates" : "Maker's figures"}: light under its centre</caption>
      <thead><tr><th scope="col">Distance</th><th scope="col" class="num">PAR (µmol/m²/s)</th><th scope="col" class="num">12 hours a day gives</th><th scope="col" class="num">Lights about</th></tr></thead>
      <tbody>${L.points.map(p => html`<tr><th scope="row">${fmt(p.distance_in, 1)} in</th><td class="num">${fmt(p.ppfd, 1)}</td><td class="num">${fmt(p.ppfd * 12 * 0.0036, 1)} mol/m²</td><td class="num">${p.area_sqft ? fmt(p.area_sqft, 1) + ' sq ft' + (S.area_estimated && !S.estimated ? ' (estimate)' : '') : ''}</td></tr>`)}</tbody></table></div>` : ''}
    ${S.ppfd_note ? html`<p class="hint">${S.ppfd_note}</p>` : ''}
    ${L.chart ? html`<p class="hint"><a href="${L.chart}" target="_blank" rel="noopener">Open the maker's chart</a> (picture). ${S.chart_alt || ''}</p>` : ''}
    ${S.url ? html`<p class="hint"><a href="${S.url}" target="_blank" rel="noopener noreferrer">Product page</a></p>` : ''}
    <div class="row noprint"><button class="btn ghost small" type="button" data-act="lightedit" data-id="${L.id}">Change the light figures, timer and brightness</button></div></div></article>`;
}
// 1.28.1: Your lights is at the top and folds; this browser remembers whether you left it open (open the first time)
function ltLightsOpen() { try { return localStorage.getItem('plantdb.ltlights') !== '0'; } catch (e) { return true; } }
document.addEventListener('toggle', e => { const d = e.target; if (d && d.dataset && d.dataset.remember === 'ltlights') { try { localStorage.setItem('plantdb.ltlights', d.open ? '1' : '0'); } catch (x) { /* this visit only */ } } }, true);
async function viewLights() {
  LT = await api('GET', '/api/lights');
  const n = LT.candidates.length, inSpots = Object.keys(LT.assigned).length, sug = LT.plan.reduce((a, s) => a + s.codes.length, 0);
  return {
    title: 'Grow lights',
    html: html`<h1>Grow lights</h1>
    <p class="muted">Your grow lights, the spots they light, and how much light each plant gets there. A plant's daily light (DLI, in mol/m² a day) is the light at its leaves while the light is on (PAR) times the hours it is on. Each plant page has the range it wants.</p>
    <details class="blk lt-lights-box" id="lt-lights" data-remember="ltlights" ${ltLightsOpen() ? raw('open') : ''}><summary><h2>Your lights (${LT.lights.length})</h2><span class="hint">Show or hide</span></summary>
      <div class="lt-lights">${LT.lights.map(ltLightCard)}</div></details>
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
      <label class="f">Where it is<input type="text" name="fixture" maxlength="600" value="${x.fixture}"><small>The room, shelf or lamp it is in, or the socket a bulb screws into.</small></label>
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
