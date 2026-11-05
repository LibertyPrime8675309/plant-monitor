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
      <span><a class="nm" href="#/plant/${enc(p.code)}">${p.name}</a><br><span class="muted">${p.code}. Needs ${has(p.lo) ? `${fmt(p.lo, 1)} to ${fmt(p.hi, 1)}` : '(not set)'} mol/m² a day.</span>${p.better ? html`<br><span class="lt-better">It would suit <strong>${p.better.name}</strong> (about ${p.better.dli} mol/m² a day).</span>` : ''}</span>${lvTag(p.verdict, p.verdict_word)}</li>`)}</ul>` : html`<p class="muted">No plants in this spot yet.</p>`}
    ${ltSteps(s.steps)}
    <div class="row noprint">${plan ? html`<button class="btn" type="button" data-act="spotnew" data-plan="${i}">Set up this spot</button>`
      : html`<button class="btn ghost" type="button" data-act="spotadd" data-id="${s.id}" aria-label="Add plants to ${s.name}">Add plants</button><button class="btn ghost" type="button" data-act="spotedit" data-id="${s.id}" aria-label="Change ${s.name}">Change this spot</button><button class="btn ghost" type="button" data-act="spotdel" data-id="${s.id}" aria-label="Remove ${s.name}">Remove this spot</button>`}</div></article>`;
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
      ${LT.plan.length > 1 ? html`<p class="row noprint"><button class="btn" type="button" data-act="spotplanall">Set up all ${LT.plan.length} suggested spots</button></p>` : ''}
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
// 1.41.0: the Light menu A to Z, grow lights before room lights, each saying what tells it apart; a card on the chosen light;
// the plant list with search, Show and Sort, a photo, a link to each plant, and a tag saying how this setting suits it
const ltSorted = () => (LT ? LT.lights : []).slice().sort((a, b) => (a.room_light - b.room_light) || a.name.localeCompare(b.name, undefined, { sensitivity: 'base', numeric: true }));
const ltKind = S => ((S.kind || '').split(/ \(|:| with /)[0] || 'Light').toLowerCase();
const ltColour = k => k ? `${k}K ${k >= 5000 ? 'cool white' : k >= 3500 ? 'neutral white' : 'warm white'}` : '';
function ltFree(l, x) { return l.count - l.in_use + (x && x.id && x.light_id === l.id ? (x.units0 || 0) : 0); }
function ltOption(l, x, sel) {
  const S = l.specs, R = l.reach, free = ltFree(l, x);
  const bits = [ltKind(S), S.watts ? fmt(S.watts, 1) + ' W' : '', R ? `up to ${fmt(R.ppfd_max)} PAR at ${fmt(R.near_in, 1)} in` : 'no light figures yet', free > 0 ? `${free} of ${l.count} free` : `none free (you have ${l.count})`].filter(Boolean);
  return html`<option value="${l.id}" ${sel ? raw('selected') : ''}>${l.name}: ${bits.join(', ')}</option>`;
}
function ltOptions(x, cur) {
  const all = ltSorted(), grow = all.filter(l => !l.room_light), room = all.filter(l => l.room_light);
  return html`<optgroup label="Grow lights">${grow.map(l => ltOption(l, x, l.id === cur))}</optgroup>${room.length ? html`<optgroup label="Room lights">${room.map(l => ltOption(l, x, l.id === cur))}</optgroup>` : ''}`;
}
function spotLightCard(L, x) {
  if (!L) return '';
  const S = L.specs, R = L.reach, free = ltFree(L, x), need = LT.candidates.filter(c => c.need).length;
  const power = [S.watts ? fmt(S.watts, 1) + ' W' : '', S.lumens ? fmt(S.lumens) + ' lumens' : '', ltColour(S.kelvin)].filter(Boolean).join(', ');
  return html`<h3 class="sp-light-h">${L.name}${S.model ? html` <span class="muted">(${S.model})</span>` : ''}</h3>
    <dl class="dl sp-light-facts"><dt>Type</dt><dd>${S.kind || 'Not given'}${S.direction === 'side' ? '. It shines sideways.' : ''}</dd>
      ${power ? html`<dt>Power and colour</dt><dd>${power}</dd>` : ''}
      <dt>Brightness</dt><dd>${S.dimming && S.dimming.length > 1 ? S.dimming.slice().sort((a, b) => a - b).map(v => v + '%').join(', ') : 'Full only'}</dd>
      <dt>Free</dt><dd>${free > 0 ? `${free} of the ${L.count} you have` : `None: all ${L.count} are in your spots`}</dd>
      ${R ? html`<dt>Light at the leaves (PAR)</dt><dd>${R.one_point ? html`${fmt(R.ppfd_max)} at ${fmt(R.near_in, 1)} in${R.dim_min < 100 ? `, down to ${fmt(R.ppfd_min, 1)} on ${R.dim_min}%` : ''}` : html`From ${fmt(R.ppfd_max)} at ${fmt(R.near_in, 1)} in, down to ${fmt(R.ppfd_min, 1)} at ${fmt(R.far_in, 1)} in${R.dim_min < 100 ? ` on ${R.dim_min}%` : ''}`}</dd>
        <dt>Daily light (mol/m² a day)</dt><dd>${fmt(R.dli12[0], 1)} to ${fmt(R.dli12[1], 1)} on 12 hours; ${fmt(R.dli_any[0], 1)} to ${fmt(R.dli_any[1], 1)} from 8 to 16 hours</dd>`
      : html`<dt>Light figures</dt><dd>None yet. Add them with "Change the light figures" under Your lights.</dd>`}</dl>
    <p class="hint">${R ? (R.one_point ? `Measured at one distance only, so the figures are for ${fmt(R.near_in, 1)} in. ` : 'For one of this light, within the distances that were measured; not stretched past them. ') : ''}${R ? `At some setting it can give the daily light ${L.suits} of the ${need} plants here want.` : ''}${L.room_light ? ' This is a room light, not a grow light: it only suits plants that need little light.' : ''}</p>${ltSocketNote(L)}`;
}
function ltVerdict(dli, lo, hi) {          // the same rule as light_verdict() on the server
  if (!has(dli) || (!has(lo) && !has(hi))) return 'unknown';
  if (has(lo) && dli < lo) return dli < lo * 0.8 ? 'too_dim' : 'dim';
  if (has(hi) && dli > hi) return dli > hi * 1.3 ? 'too_bright' : 'bright';
  return 'good';
}
function spotRow(c, x, others, inSpot) {
  const sid = LT.assigned[c.code], there = sid && sid !== x.id ? others[sid] : null, id = 'spp-' + c.code;
  return html`<li class="sp-row" data-code="${c.code}" data-name="${c.name.toLowerCase()}" data-lo="${c.need ? c.need.lo : ''}" data-hi="${c.need ? c.need.hi : ''}" data-target="${c.need ? c.need.target : ''}"
      data-free="${sid ? '0' : '1'}" data-inside="${c.inside ? '1' : '0'}">
    <input type="checkbox" id="${id}" name="plant" value="${c.code}" ${inSpot.has(c.code) ? raw('checked') : ''}>
    ${c.photo ? html`<img src="${thumbUrl(c.photo)}" alt="" loading="lazy" width="56" height="56">` : html`<span class="sp-nophoto" aria-hidden="true"></span>`}
    <span class="sp-txt"><label for="${id}" class="nm">${c.name}</label>
      <span class="muted">${c.need ? `Needs ${fmt(c.need.lo, 1)} to ${fmt(c.need.hi, 1)} mol/m² a day.` : 'Light needs not set.'} ${c.inside ? 'Lives inside.' : 'Coming inside.'}${there ? ` Now in ${there}.` : ''}</span>
      <a href="#/plant/${enc(c.code)}" target="_blank" rel="noopener" aria-label="Open ${c.name}, ${c.code}, in a new tab">Open ${c.code}</a></span>
    <span class="sp-fit"></span></li>`;
}
async function spotDialog(x, opt) {
  if (!(await needName())) return;
  if (!LT) LT = await api('GET', '/api/lights');
  const editing = x && x.id;
  if (editing && x.units0 == null) x = { ...x, units0: x.units };
  for (;;) {
    const L = ltLight(x.light_id) || ltSorted()[0], inSpot = new Set(x.codes || []);
    const others = Object.fromEntries(LT.spots.map(s => [s.id, s.name])), n = LT.candidates.length;
    const shown = modal(html`<form method="dialog" data-spot data-id="${editing ? x.id : ''}" class="spot-form"><h2>${editing ? 'Change this spot' : 'Set up a light spot'}</h2>
      <label class="f">Name<input type="text" name="name" maxlength="60" value="${x.name || ''}" required autofocus><small>A short name you will recognise, for example "Hutch, top shelf".</small></label>
      <label class="f">Where<select name="place"><option value="">Not chosen yet</option>${ltRooms().map(([room, ps]) => html`<optgroup label="${room}">${ps.map(pl => html`<option value="${pl.id}" ${pl.id === x.place_id ? raw('selected') : ''}>${pl.label}</option>`)}</optgroup>`)}</select>
        <small>Add rooms and shelves under "Rooms and shelves" on this page.</small></label>
      <label class="f">Light<select name="light">${ltOptions(x, L && L.id)}</select><small>A to Z. Each says its type, power, its most light (PAR) and how many are free.</small></label>
      <section class="sp-light" id="sp-light" aria-label="About this light">${spotLightCard(L, x)}</section>
      <div class="field-grid three"><label class="f">How many of this light<input type="number" name="units" min="1" max="50" step="1" value="${x.units || 1}" required><small>Side by side over these plants.</small></label>
        <label class="f">Distance from the leaves (inches)<input type="number" name="distance" min="1" max="120" step="0.5" value="${x.distance_in || 12}" required><small>From the light to the top leaves${L && L.specs.direction === 'side' ? ' (this light shines sideways)' : ''}.</small></label>
        <label class="f">Hours a day<input type="number" name="hours" min="1" max="24" step="0.5" value="${x.hours || 12}" required></label></div>
      <label class="f">Brightness<select name="dim">${spotDims(L, x.dim_pct || 100)}</select></label>
      <p class="row"><button class="btn ghost" type="button" data-act="spotbest">Best setting for the ticked plants</button></p>
      <p id="sp-best" class="sp-best" aria-live="polite"></p>
      <div id="sp-prev" class="sp-prev" aria-live="polite"></div>
      <fieldset class="opt-group sp-pick"><legend>Plants in this spot</legend>
        <p class="hint">Plants that live inside or are coming in. Ticking a plant that is in another spot moves it here. The tag on each says how this light, at this setting, suits it.</p>
        <div class="sp-tools">
          <label class="f">Search plants<input type="search" data-sp="q" autocomplete="off"></label>
          <label class="f">Show<select data-sp="show"><option value="">All plants (${n})</option><option value="fit">Fits this setting</option><option value="near">Fits or nearly fits</option>
            <option value="free">Not in a spot yet</option><option value="ticked">Ticked for this spot</option><option value="inside">Lives inside</option><option value="coming">Coming inside</option></select></label>
          <label class="f">Sort<select data-sp="sort"><option value="name">Name, A to Z</option><option value="code">Code</option><option value="need">Most light needed first</option><option value="fit">Best fit first</option></select></label>
        </div>
        <p id="sp-count" class="sp-count" role="status"></p>
        <ul class="sp-plants">${LT.candidates.map(c => spotRow(c, x, others, inSpot))}</ul></fieldset>
      <label class="f">Note<input type="text" name="notes" maxlength="300" value="${x.notes || ''}"></label>
      <div class="row"><button class="btn" value="ok">${editing ? 'Save changes' : 'Save spot'}</button><button class="btn ghost" value="cancel" formnovalidate>Cancel</button></div></form>`, 'wide');
    SP = { light: String(L.id), dli: null, x };
    if (opt && opt.show) { const f = dlg.querySelector('form[data-spot]'); f.querySelector('[data-sp=show]').value = opt.show; f.querySelector('[data-sp=q]').focus(); }
    spotFilter(); spotPreview(true);
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
function spotFilter() {
  const f = dlg.querySelector('form[data-spot]'); if (!f) return;
  const q = f.querySelector('[data-sp=q]').value.trim().toLowerCase(), show = f.querySelector('[data-sp=show]').value, sort = f.querySelector('[data-sp=sort]').value;
  const ul = f.querySelector('ul.sp-plants'), rows = [...ul.children], dli = SP && SP.dli;
  const num = (r, k) => r.dataset[k] === '' ? null : +r.dataset[k];
  const verdict = r => ltVerdict(dli, num(r, 'lo'), num(r, 'hi'));
  let shown = 0;
  rows.forEach(r => {
    const v = verdict(r), tick = r.querySelector('input').checked;
    const ok = (!q || r.dataset.name.includes(q) || r.dataset.code.toLowerCase().includes(q)) &&
      (!show || (show === 'fit' && v === 'good') || (show === 'near' && ['good', 'dim', 'bright'].includes(v)) || (show === 'free' && (r.dataset.free === '1' || tick)) ||
       (show === 'ticked' && tick) || (show === 'inside' && r.dataset.inside === '1') || (show === 'coming' && r.dataset.inside === '0'));
    r.hidden = !ok; if (ok) shown++;
    r.querySelector('.sp-fit').innerHTML = has(dli) && v !== 'unknown' ? rend(lvTag(v, LIGHT_WORD[v])) : '';
  });
  const fitKey = r => { const t = num(r, 'target'); return t == null || !has(dli) ? 99 : Math.abs(Math.log(Math.max(dli, 0.01) / Math.max(t, 0.01))); };
  const cmp = { name: (a, b) => a.dataset.name.localeCompare(b.dataset.name), code: (a, b) => a.dataset.code.localeCompare(b.dataset.code, undefined, { numeric: true }),
    need: (a, b) => (num(b, 'target') ?? -1) - (num(a, 'target') ?? -1) || a.dataset.name.localeCompare(b.dataset.name), fit: (a, b) => fitKey(a) - fitKey(b) || a.dataset.name.localeCompare(b.dataset.name) }[sort];
  const order = rows.slice().sort(cmp);
  if (order.some((r, i) => r !== rows[i])) order.forEach(r => ul.appendChild(r));      // appendChild moves; focus stays on a moved box
  const ticked = rows.filter(r => r.querySelector('input').checked).length;
  f.querySelector('#sp-count').textContent = `Showing ${shown} of ${rows.length}. ${ticked} ticked for this spot.`;
}
const LIGHT_WORD = { too_dim: 'Too dim', dim: 'A bit dim', good: 'Good', bright: 'A bit bright', too_bright: 'Too bright', unknown: 'Needs not set' };
function spotPreview(now) {
  clearTimeout(SP && SP.t);
  const go = async () => {
    const f = dlg.querySelector('form[data-spot]'), out = document.getElementById('sp-prev'); if (!f || !out) return;
    if (f.elements.light.value !== SP.light) {           // a different light: its own brightness steps and its card
      SP.light = f.elements.light.value; const L = ltLight(SP.light);
      f.elements.dim.innerHTML = rend(html`${spotDims(L, 100)}`);
      const card = document.getElementById('sp-light'); if (card) card.innerHTML = rend(spotLightCard(L, SP.x));
    }
    const q = new URLSearchParams({ light: f.elements.light.value, units: f.elements.units.value, distance: f.elements.distance.value, hours: f.elements.hours.value, dim: f.elements.dim.value,
      plants: [...f.querySelectorAll('input[name=plant]:checked')].map(i => i.value).join(','), spot: f.dataset.id || '' });
    try {
      const e = await api('GET', '/api/lights/preview?' + q.toString());
      SP.dli = e.dli; spotFilter();
      const ticked = e.plants.length, cover = e.area_sqft;
      out.innerHTML = rend(html`<p><strong>About ${has(e.dli) ? e.dli : '?'} mol/m² a day</strong> at the leaves${has(e.ppfd) ? `, ${fmt(e.ppfd)} PAR while it is on` : ''}${cover ? `, lighting about ${fmt(cover, 1)} sq ft` : ''}.</p>
        ${ticked ? html`<p>${ticked} plant${ticked === 1 ? '' : 's'} ticked; their pots take about ${fmt(e.room_needed_sqft, 1)} sq ft${cover ? ` of the ${fmt(cover, 1)} the light covers well` : ''}.${e.crowded ? ' Crowded: the plants at the edge get less.' : ''}</p>` : ''}
        ${e.timer_note ? html`<p class="hint">${e.timer_note}</p>` : ''}
        ${e.plants.length ? html`<ul class="sp-verdicts">${e.plants.map(p => html`<li>${lvTag(p.verdict, p.verdict_word)} ${p.name} <span class="muted">(needs ${has(p.lo) ? `${fmt(p.lo, 1)} to ${fmt(p.hi, 1)}` : 'not set'})</span>${p.better ? html`. It would suit <strong>${p.better.name}</strong> (about ${p.better.dli}).` : ''}</li>`)}</ul>` : ''}`);
    } catch (err) { out.innerHTML = rend(html`<p class="muted">${err.message}</p>`); }
  };
  if (now) go(); else SP.t = setTimeout(go, 250);
}
async function spotBest() {
  const f = dlg.querySelector('form[data-spot]'), say = document.getElementById('sp-best'); if (!f) return;
  const codes = [...f.querySelectorAll('input[name=plant]:checked')].map(i => i.value);
  if (!codes.length) { say.textContent = 'Tick the plants for this spot first.'; return; }
  try {
    const b = await api('GET', '/api/lights/best?' + new URLSearchParams({ light: f.elements.light.value, units: f.elements.units.value, plants: codes.join(',') }).toString());
    f.elements.distance.value = b.distance_in; f.elements.hours.value = b.hours;
    if ([...f.elements.dim.options].some(o => +o.value === b.dim_pct)) f.elements.dim.value = String(b.dim_pct);
    say.textContent = `Set to ${b.distance_in} in from the leaves, ${b.hours} hours a day${b.dim_pct < 100 ? `, ${b.dim_pct}% brightness` : ''}: about ${b.dli} mol/m² a day. ${b.good} of the ${b.of} ticked plants with light needs are in their range${b.good < b.of ? '. The list under it shows which are not, and a spot of yours that would suit them, if there is one' : ''}.`;
    spotPreview(true);
  } catch (e) { say.textContent = e.message; }
}
document.addEventListener('keydown', e => { if (e.key === 'Enter' && e.target.dataset && e.target.dataset.sp === 'q') e.preventDefault(); });   // Enter in the search box must not save the spot
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
// a plant's own page: its spot, or what the layout suggests; 1.41.0: put it in a spot from here
let GROW = null;
async function loadGrowPlant(code) {
  const el = document.getElementById('pl-grow'); if (!el) return;
  try {
    const g = await api('GET', '/api/lights?plant=' + enc(code)); GROW = { code, ...g };
    if (!g.lights || (!g.spot && !g.suggestion && !g.unplaced && !g.candidate)) { el.innerHTML = ''; return; }
    const me = s => s.plants.find(p => p.code === code) || {};
    const acts = !g.spot && g.candidate ? html`<p class="row noprint">${g.suggestion ? html`<button class="btn small" type="button" data-act="growsug" data-code="${code}">Set up the suggested spot</button>` : ''}
      ${g.spots.length ? html`<button class="btn small ${g.suggestion ? 'ghost' : ''}" type="button" data-act="growadd" data-code="${code}">Add it to one of your spots</button>` : ''}
      <button class="btn small ghost" type="button" data-act="grownew" data-code="${code}">Set up a new spot for it</button></p>` : '';
    el.innerHTML = rend(html`<h3>Grow light this winter</h3>${g.spot ? html`<p>In the spot <strong>${g.spot.name}</strong>${g.spot.place ? ` (${g.spot.place})` : ''}${g.spot.name.includes(g.spot.light) ? '' : `, under the ${g.spot.light}`}: ${ltSetting(g.spot)}. About ${g.spot.dli} mol/m² a day. ${lvTag(me(g.spot).verdict, me(g.spot).verdict_word)}</p>
        ${me(g.spot).better ? html`<p>It would suit <strong>${me(g.spot).better.name}</strong> better (about ${me(g.spot).better.dli} mol/m² a day).</p>` : ''}`
      : g.suggestion ? html`<p>Not in a light spot yet. The suggested layout puts it under the <strong>${g.suggestion.light}</strong>, ${ltSetting(g.suggestion)}: about ${g.suggestion.dli} mol/m² a day. ${lvTag(me(g.suggestion).verdict, me(g.suggestion).verdict_word)}</p>`
      : g.unplaced ? html`<p>Not in a light spot yet. ${g.unplaced.why}</p>` : html`<p>Not in a light spot yet.</p>`}${acts}<p class="noprint"><a href="#/lights">Open Grow lights</a></p>`);
  } catch (e) { el.innerHTML = ''; }
}
async function growAddDialog(code) {
  if (!(await needName())) return;
  const g = GROW && GROW.code === code ? GROW : await api('GET', '/api/lights?plant=' + enc(code));
  const r = await modal(html`<form method="dialog"><h2>Add it to one of your spots</h2>
    <p class="hint">${g.need ? `It needs ${fmt(g.need.lo, 1)} to ${fmt(g.need.hi, 1)} mol/m² a day.` : 'Its light needs are not set.'} The tag on each spot says how that spot's light suits it.</p>
    <fieldset class="opt-group"><legend>Spots</legend>${g.spots.map((s, i) => html`<label class="chk sp-choice"><input type="radio" name="spot" value="${s.id}" ${i === 0 ? raw('required') : ''}>
      <span><strong>${s.name}</strong>${s.place ? ` (${s.place})` : ''}<br><span class="muted">${s.light}, about ${has(s.dli) ? s.dli : '?'} mol/m² a day, ${s.n} plant${s.n === 1 ? '' : 's'} there now.</span></span>${lvTag(s.verdict, s.verdict_word)}</label>`)}</fieldset>
    <div class="row"><button class="btn" value="ok">Add it</button><button class="btn ghost" value="cancel" formnovalidate>Cancel</button></div></form>`);
  if (r !== 'ok') return;
  const sid = dlg.querySelector('input[name=spot]:checked').value;
  await guard(async () => { const x = await api('POST', `/api/lights/spots/${sid}/plants`, { add: [code] }); toast(`Added to ${x.name}`); LT = null; loadGrowPlant(code); });
}
