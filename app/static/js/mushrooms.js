/* Plant record front end: mushroom finds (#/fungi). Nothing here may say or suggest that a wild mushroom is edible or safe. Split out of discover.js in 1.57.0 (review item 25); the scripts load in the order js/manifest.json
   gives and share one scope, so a function here may call any other. Plain JavaScript, no inline handlers (the content policy forbids them). */
'use strict';

// ---------- 1.22.0: mushroom finds (#/fungi), a page of their own ----------
// A find is a mushroom (or a cluster) seen anywhere: the yard, a plant pot, a walk. It has photos, where and when, what it grew
// on, what it looks like, and its name with how sure that is. The app never says a mushroom is safe to eat.
const MU = { q: '', id: '', place: '', year: '', status: 'active', list: null, meta: null };
try { const s = JSON.parse(localStorage.getItem('plantdb.fungi') || '{}'); ['q', 'id', 'place', 'year', 'status'].forEach(k => { if (typeof s[k] === 'string') MU[k] = s[k]; }); } catch (e) { /* defaults */ }
const muSave = () => { try { localStorage.setItem('plantdb.fungi', JSON.stringify({ q: MU.q, id: MU.id, place: MU.place, year: MU.year, status: MU.status })); } catch (e) { /* not remembered */ } };
const MU_ID_TAG = { 'Not identified yet': 'Not identified', 'A guess': 'Name is a guess', 'Fairly sure': 'Fairly sure of the name', 'Confirmed by an expert': 'Confirmed name' };
function fungiSafety(short) {
  return html`<aside class="notice bad mu-safe" role="note" aria-label="Safety"><strong>Never eat a wild mushroom because of an app, a photo, or this record.</strong>
    ${short ? html` Deadly mushrooms look like edible ones, and photo IDs are often wrong. <a href="#/fungi/safety">Read more</a>.`
      : html`<ul><li>Deadly species, such as death caps and destroying angels (<i>Amanita</i>), look like common edible ones, and some poisons only show symptoms a day later, when the liver is already damaged.</li>
      <li>Names here come from photos, your notes or Identify. They are leads, not proof. Only an experienced local expert, with the whole mushroom in hand, can confirm one.</li>
      <li><strong>Pets:</strong> dogs often eat mushrooms in yards, and several common lawn species are toxic to them. Pick mushrooms from the yard before letting pets out. If a pet may have eaten one, call your vet or ASPCA Animal Poison Control at (888) 426-4435.</li>
      <li><strong>People:</strong> if someone may have eaten a wild mushroom, call Poison Control at 1-800-222-1222 (or 911 if they are very ill), and keep any leftover pieces.</li>
      <li>Wash your hands after handling wild mushrooms.</li></ul>`}</aside>`;
}
function muYears(list) { return [...new Set(list.map(f => (f.found_on || '').slice(0, 4)).filter(Boolean))].sort().reverse(); }
function muFiltered() {
  const q = MU.q.toLowerCase();
  return (MU.list || []).filter(f => (!MU.id || f.id_status === MU.id) && (!MU.place || f.place_kind === MU.place) && (!MU.year || (f.found_on || '').startsWith(MU.year))
    && (!q || [f.code, f.name, f.scientific_name, f.place, f.near, f.notes, f.cap_colour, f.plant_code].join(' ').toLowerCase().includes(q)));
}
function muCard(f) {
  return html`<article class="sheet mu-card" data-code="${f.code}">
    <div class="mat">${f.photo ? html`<img src="${thumbUrl(f.photo)}" alt="" loading="lazy" decoding="async">` : f.photo_url ? html`<img src="${f.photo_url}" alt="" decoding="async">` : html`<div class="nophoto">No photo yet</div>`}<span class="acc">${f.pending ? 'Not sent yet' : f.code}</span></div>
    <h3 class="name"><a class="sheet-link" href="#/fungi/${enc(f.code)}">${f.name || 'Unnamed mushroom'}</a></h3>
    ${f.scientific_name ? html`<p class="sci latin">${f.scientific_name}</p>` : ''}
    <p class="mu-when">${f.found_on ? longDay(f.found_on) : ''}${f.place_kind ? ' · ' + f.place_kind.replace(/^In (the|a) /, '').replace(/^\w/, c => c.toUpperCase()) : ''}${f.plant_code ? ' ' + f.plant_code : ''}</p>
    <div class="tags"><span class="tag ${f.id_status === 'Confirmed by an expert' ? 'tag-yours' : ''}">${MU_ID_TAG[f.id_status] || f.id_status}</span>${f.status === 'archived' ? html`<span class="tag tag-arch">Archived</span>` : ''}</div>
  </article>`;
}
function muDraw() {
  const box = document.getElementById('mu-grid'); if (!box) return;
  muSave();
  const r = muFiltered();
  document.getElementById('mu-count').textContent = `${r.length} of ${(MU.list || []).length} finds shown`;
  box.innerHTML = rend(r.length ? r.map(muCard) : html`<div class="empty" style="grid-column:1/-1"><p>${(MU.list || []).length ? 'No finds match these filters.' : 'No finds yet. When you spot a mushroom, press "Add a find" and take its photos.'}</p></div>`);
}
async function viewFungi() {
  const d = await api('GET', '/api/fungi?status=' + enc(MU.status));
  MU.list = d.finds; MU.meta = d;
  const sel = (f, opts) => html`<select data-f="${f}">${opts.map(([v, l]) => html`<option value="${v}" ${MU[f.slice(2)] === v ? raw('selected') : ''}>${l}</option>`)}</select>`;
  return {
    title: 'Mushroom finds', after: muDraw,
    html: html`<div class="hero"><div><h1>Mushroom finds</h1>
      <p class="muted">Mushrooms you have spotted in the yard, in your plant pots, or anywhere else, with their photos, where they grew and what they look like.</p></div>
      <a class="btn" href="#/fungi/new">Add a find</a></div>
    ${fungiSafety(true)}
    <div class="filters mu-filters">
      <label>Search<input type="search" data-f="muq" value="${MU.q}" placeholder="Name, place, colour, notes" autocomplete="off"></label>
      <label>Name${sel('muid', [['', 'Any'], ...d.enums.id_status.map(x => [x, x])])}</label>
      <label>Where${sel('muplace', [['', 'Anywhere'], ...d.enums.place_kind.map(x => [x, x])])}</label>
      <label>Year${sel('muyear', [['', 'Any year'], ...muYears(d.finds).map(y => [y, y])])}</label>
      <label>Show${sel('mustatus', [['active', 'Current finds'], ['all', 'Current and archived'], ['archived', 'Archived only']])}</label>
    </div>
    <p id="mu-count" class="muted" aria-live="polite"></p>
    <div class="grid" id="mu-grid"></div>
    <p class="row"><a class="btn ghost" href="#/around">Fungi found near home this month</a><a class="btn ghost small noprint" href="/api/fungi.csv">Download the finds (CSV)</a></p>
    <p class="hint">Look up mushrooms by name in the <a href="#/library?scope=fungi">library</a> (Look in: Fungi worldwide), or take a picture with <a href="#/identify">Identify</a>.</p>`,
  };
}
function viewFungiSafety() {
  return { title: 'Mushroom safety', html: html`<p class="crumb"><a href="#/fungi">Back to the mushroom finds</a></p><h1>Mushroom safety</h1>${fungiSafety(false)}
    <h2>Good habits when you record a find</h2>
    <ul><li>Photograph the cap from above, the underside (gills or pores), the whole stem, and the very base. Dig gently around the base first: a cup or sac there (a volva) is a warning sign of <i>Amanita</i>.</li>
      <li>Note what it grew on, and which trees are near: many mushrooms grow only with certain trees.</li>
      <li>A spore print helps an expert most: put the cap gills-down on half white, half dark paper under a bowl for a few hours, and note the colour.</li>
      <li>Ask for help on iNaturalist or a local mycological society (most states and many cities have one; the North American Mycological Association lists them).</li></ul>` };
}
function muField(meta, f, v, plants) {
  const id = 'mu-' + f.name;
  if (f.name === 'lat' || f.name === 'lon') return '';
  if (f.name === 'plant_code') return html`<label class="f" data-show="pot">${f.label}<select name="plant_code" id="${id}"><option value="">Not in a pot</option>${plants.map(p => html`<option value="${p.code}" ${p.code === v ? raw('selected') : ''}>${p.code} ${p.common_name}</option>`)}</select></label>`;
  if (f.kind === 'enum') return html`<label class="f">${f.label}<select name="${f.name}" id="${id}"><option value="">Not set</option>${meta.enums[f.name].map(o => html`<option ${o === v ? raw('selected') : ''}>${o}</option>`)}</select></label>`;
  if (f.kind === 'long') return html`<label class="f wide">${f.label}<textarea name="${f.name}" id="${id}" rows="4">${v || ''}</textarea></label>`;
  if (f.kind === 'date') return html`<label class="f">${f.label}<input type="date" name="${f.name}" id="${id}" value="${v || todayStr()}" max="${todayStr()}"></label>`;
  const hint = { name: 'A common name, or your own description such as "small brown one by the oak"', cap_size: 'For example 2 inches',
    stem: 'Length and thickness, colour, hollow or solid, and how it meets the cap', spore_print: 'Pick the nearest, or type your own',
    bruising: 'Cut the stem or press the cap, wait a minute', smell: 'Crush a bit of the cap' }[f.name];
  // 5d: a 'pick' field offers the usual answers (what a field guide asks for) and takes anything else too
  const picks = f.kind === 'pick' && meta.picks && meta.picks[f.name];
  return html`<label class="f">${f.label}${hint ? html`<small>${hint}</small>` : ''}<input type="text" name="${f.name}" id="${id}" value="${v || ''}" ${picks ? raw(`list="${id}-list"`) : ''}></label>
    ${picks ? html`<datalist id="${id}-list">${picks.map(o => html`<option value="${o}"></option>`)}</datalist>` : ''}`;
}
const MU_GROUPS = [['Name', ['name', 'scientific_name', 'id_status']], ['Where and when', ['found_on', 'place_kind', 'plant_code', 'place']],
  ['What it grew on', ['substrate', 'habitat', 'near', 'abundance']], ['What it looks like', ['cap_size', 'cap_colour', 'underside', 'stem', 'ring', 'volva', 'spore_print', 'bruising', 'smell']], ['Notes', ['notes']]];   // 5d: habitat and stem
let MUFILL = null;            // a new find started from a species page or from Identify
async function viewFindForm(code) {
  const [meta, plants] = await Promise.all([code ? api('GET', '/api/fungi/' + enc(code)) : api('GET', '/api/fungi?status=none'), api('GET', '/api/plants')]);
  MU.meta = meta;
  const F = Object.fromEntries(meta.fields.map(f => [f.name, f])), v = code ? meta : (MUFILL || {});
  return {
    title: code ? 'Edit ' + code : 'Add a mushroom find',
    after: () => muPlaceShow(),
    html: html`<p class="crumb"><a href="${code ? '#/fungi/' + enc(code) : '#/fungi'}">${code ? 'Back to ' + code : 'Back to the mushroom finds'}</a></p>
    <h1>${code ? 'Edit ' + code : 'Add a mushroom find'}</h1>
    ${code ? '' : html`<p class="muted">Only the photos and where you found it really matter now; fill in the rest any time.</p>`}
    <form data-form="musave" ${code ? raw(`data-code="${esc(code)}" data-ver="${meta.version}"`) : ''} autocomplete="off">
      ${code ? '' : html`<fieldset><legend>Photos</legend><label class="f">Photos of the cap, the underside, the stem and the base<small>On a phone you can take them or choose them from your photos. If the photos carry their location, it is offered for the find.</small>
        <input type="file" name="photos" accept="image/*" multiple></label></fieldset>`}
      ${MU_GROUPS.map(([t, names]) => html`<fieldset><legend>${t}</legend>${t === 'What it looks like' ? html`<p class="hint">These are what a field guide or an expert asks for to check a lead. Nothing recorded here, and nothing the app says, means a mushroom is safe to eat.</p>` : ''}<div class="field-grid">${names.map(n => muField(meta, F[n], v[n], plants))}</div>
        ${t === 'Where and when' ? html`<div class="mu-loc"><input type="hidden" name="lat" value="${v.lat == null ? '' : v.lat}"><input type="hidden" name="lon" value="${v.lon == null ? '' : v.lon}">
          <p id="mu-loc-txt" aria-live="polite">${v.lat != null ? html`Location saved: ${(+v.lat).toFixed(5)}, ${(+v.lon).toFixed(5)}.` : 'No map location saved.'}</p>
          <div class="row"><button class="btn ghost small" type="button" data-act="muhere">Use my location now</button><button class="btn ghost small" type="button" data-act="muclearloc">Clear the location</button></div>
          <p class="hint">Saved locations are seen by everyone you have given access to the app.</p></div>` : ''}</fieldset>`)}
      <div id="form-err"></div>
      <div class="sticky-save"><button class="btn" type="submit">${code ? 'Save changes' : 'Add this find'}</button><a class="btn ghost" href="${code ? '#/fungi/' + enc(code) : '#/fungi'}">Cancel</a></div>
    </form>`,
  };
}
function muPlaceShow() {
  const s = document.getElementById('mu-place_kind'), pot = document.querySelector('[data-show=pot]');
  if (s && pot) pot.hidden = s.value !== 'In a plant pot';
}
async function viewFind(code) {
  const f = await api('GET', '/api/fungi/' + enc(code));
  MUCUR = f;
  const ph = f.photos, gps = ph.find(p => p.gps_lat != null);
  const show = n => f[n] != null && f[n] !== '';
  const dl = names => names.filter(show).map(n => html`<dt>${f.fields.find(x => x.name === n).label}</dt><dd>${n === 'plant_code' && f.plant ? html`<a href="#/plant/${enc(f.plant_code)}">${f.plant_code} ${f.plant.common_name}</a>` : n === 'found_on' ? longDay(f[n]) : f[n]}</dd>`);
  return {
    title: (f.name || 'Unnamed mushroom') + ' (' + f.code + ')',
    after: () => muGallery(0),
    html: html`<div class="species mu-find"><p class="crumb"><a href="#/fungi">All mushroom finds</a></p>
    <header class="sp-head"><h1>${f.name || 'Unnamed mushroom'}</h1>
      ${f.scientific_name ? html`<p class="sp-sci latin">${f.scientific_name}${f.id_status !== 'Not identified yet' ? html` <a href="#/species/${enc(f.scientific_name)}">(in the library)</a>` : ''}</p>` : ''}
      <p class="muted"><strong>${f.code}</strong> · found ${longDay(f.found_on)} · page version ${f.version}</p>
      <div class="tags"><span class="tag ${f.id_status === 'Confirmed by an expert' ? 'tag-yours' : ''}">${MU_ID_TAG[f.id_status] || f.id_status}</span>${f.status === 'archived' ? html`<span class="tag tag-arch">Archived</span>` : ''}</div></header>
    ${fungiSafety(true)}
    <div class="sp-grid">
      <section aria-labelledby="mu-ph-h"><h2 id="mu-ph-h">Photos</h2><div id="mu-gallery"></div>
        <label class="f noprint mu-add">Add photos<small>On a phone you can take them or choose them from your photos.</small><input type="file" accept="image/*" multiple data-act="muaddphotos"></label></section>
      <section aria-labelledby="mu-id-h"><h2 id="mu-id-h">What could it be?</h2>
        <p>Identify compares a photo with about 49,000 fungi, on this computer. Treat its answer as a lead to check, never as proof.</p>
        <div class="row"><button class="btn" type="button" data-act="muident" ${ph.length ? '' : raw('disabled')} aria-describedby="mu-ident-why">Identify the photo shown</button><span class="why" id="mu-ident-why">Add a photo of the find first.</span></div>
        <div id="mu-ident" aria-live="polite"></div></section>
    </div>
    <div class="mu-info"><section aria-labelledby="mu-where-h"><h2 id="mu-where-h">Where and when</h2><dl class="dl">${dl(['found_on', 'place_kind', 'plant_code', 'place'])}
      ${f.lat != null ? html`<dt>Map location</dt><dd>${(+f.lat).toFixed(5)}, ${(+f.lon).toFixed(5)} (<a href="https://www.openstreetmap.org/?mlat=${f.lat}&mlon=${f.lon}#map=18/${f.lat}/${f.lon}" target="_blank" rel="noopener noreferrer">open the map</a>)</dd>` : ''}</dl>
      ${f.lat == null && gps ? html`<p><button class="btn ghost" type="button" data-act="mugps" data-lat="${gps.gps_lat}" data-lon="${gps.gps_lon}">Save the location from the photo (${(+gps.gps_lat).toFixed(4)}, ${(+gps.gps_lon).toFixed(4)})</button></p>` : ''}</section>
    <section aria-labelledby="mu-grew-h"><h2 id="mu-grew-h">What it grew on</h2>${['substrate', 'habitat', 'near', 'abundance'].some(show) ? html`<dl class="dl">${dl(['substrate', 'habitat', 'near', 'abundance'])}</dl>` : html`<p class="muted">Not noted yet.</p>`}</section>
    <section aria-labelledby="mu-look-h"><h2 id="mu-look-h">What it looks like</h2>${['cap_size', 'cap_colour', 'underside', 'stem', 'ring', 'volva', 'spore_print', 'bruising', 'smell'].some(show) ? html`<dl class="dl">${dl(['cap_size', 'cap_colour', 'underside', 'stem', 'ring', 'volva', 'spore_print', 'bruising', 'smell'])}</dl>` : html`<p class="muted">Not noted yet. Edit the find to add the cap, the underside, the ring, the base and the spore print.</p>`}</section>
    ${show('notes') ? html`<section aria-labelledby="mu-notes-h"><h2 id="mu-notes-h">Notes</h2><p class="pl">${f.notes}</p></section>` : ''}
    ${f.scientific_name && f.id_status !== 'Not identified yet' ? html`<section aria-labelledby="mu-facts-h"><h2 id="mu-facts-h">What it does, and growing it</h2><div class="facts-box" data-facts-name="${f.scientific_name}" data-facts-common="${f.name || ''}" data-facts-kind="fungus"><p class="loading">Loading</p></div></section>` : ''}</div>
    <div class="row noprint mu-acts"><a class="btn" href="#/fungi/${enc(f.code)}/edit">Edit this find</a>
      <button class="btn ghost" type="button" data-act="muarch" data-to="${f.status === 'archived' ? '0' : '1'}">${f.status === 'archived' ? 'Bring it back' : 'Archive this find'}</button></div>
    <p class="hint">Added by ${f.created_by} on ${when(f.created_at)}${f.updated_at && f.updated_at !== f.created_at ? `; last changed by ${f.updated_by} on ${when(f.updated_at)}` : ''}. Changes are listed in the Audit log under "Mushroom finds".</p></div>`,
  };
}
let MUCUR = null, MUPIX = 0;
function muGallery(i) {
  const box = document.getElementById('mu-gallery'); if (!box || !MUCUR) return;
  const ph = MUCUR.photos;
  if (!ph.length) { box.innerHTML = rend(html`<p class="muted">No photos yet. Add them below.</p>`); return; }
  MUPIX = ((i % ph.length) + ph.length) % ph.length;
  const p = ph[MUPIX];
  box.innerHTML = rend(html`<figure class="sp-fig"><img src="${p.url || photoUrl(p.file)}" alt="${p.caption || 'Photo ' + (MUPIX + 1) + ' of ' + MUCUR.code}">
    <figcaption>${p.caption || 'No caption'}${p.taken_at ? `. Taken ${when(p.taken_at)}` : ''}${p.gps_lat != null ? '. Has a location.' : ''}${p.is_primary ? html` <strong>★ Main photo</strong>` : ''}</figcaption></figure>
    ${ph.length > 1 ? html`<div class="row sp-step"><button class="btn ghost small" type="button" data-act="mustep" data-d="-1">‹ Previous photo</button><span class="muted">${MUPIX + 1} of ${ph.length}</span><button class="btn ghost small" type="button" data-act="mustep" data-d="1">Next photo ›</button></div>` : ''}
    ${MUCUR.pending ? html`<p class="hint">Captions and the main photo can be changed once the find is sent.</p>` : html`<div class="row noprint">${!p.is_primary ? html`<button class="btn ghost small" type="button" data-act="mumain">Make this the main photo</button>` : ''}
      <button class="btn ghost small" type="button" data-act="mucap">Edit caption</button><button class="btn danger small" type="button" data-act="murmphoto">Remove photo</button></div>`}`);
}
async function muReload(i) { MUCUR = await api('GET', '/api/fungi/' + enc(MUCUR.code)); await route(); muGallery(i == null ? MUPIX : i); }
function muSetLoc(lat, lon, how) {
  const f = document.querySelector('form[data-form=musave]'); if (!f) return;
  f.elements.lat.value = lat == null ? '' : lat; f.elements.lon.value = lon == null ? '' : lon;
  document.getElementById('mu-loc-txt').textContent = lat == null ? 'No map location saved.' : `Location ${how}: ${(+lat).toFixed(5)}, ${(+lon).toFixed(5)}. It is saved with the find.`;
}
Object.assign(acts, {
  muhere: () => {
    if (!navigator.geolocation) { toast('This browser cannot give a location.', true); return; }
    document.getElementById('mu-loc-txt').textContent = 'Finding your location…';
    navigator.geolocation.getCurrentPosition(p => muSetLoc(p.coords.latitude.toFixed(6), p.coords.longitude.toFixed(6), 'from this device'),
      e => { document.getElementById('mu-loc-txt').textContent = e.code === 1 ? 'Location was not allowed. Allow it in the browser\'s site settings, or leave it empty.' : 'Could not get the location: ' + e.message; },
      { enableHighAccuracy: true, timeout: 20000 });
  },
  muclearloc: () => muSetLoc(null, null),
  mustep: el => { muGallery(MUPIX + +el.dataset.d); const b = document.querySelector(`[data-act=mustep][data-d="${el.dataset.d}"]`); if (b) b.focus(); },
  async mumain() { if (!(await needName())) return; await guard(async () => { await api('PATCH', '/api/fungi/photos/' + MUCUR.photos[MUPIX].id, { is_primary: true }); toast('Main photo changed'); await muReload(0); }); },
  async mucap() {
    if (!(await needName())) return;
    const p = MUCUR.photos[MUPIX];
    const r = await modal(html`<form method="dialog"><h2>Edit caption</h2><label class="f">Caption<input type="text" name="c" maxlength="200" value="${p.caption}" placeholder="For example: underside, gills"></label>
      <div class="row"><button class="btn" value="ok">Save caption</button><button class="btn ghost" value="cancel">Cancel</button></div></form>`);
    if (r !== 'ok') return;
    await guard(async () => { await api('PATCH', '/api/fungi/photos/' + p.id, { caption: dlg.querySelector('[name=c]').value }); toast('Caption saved'); await muReload(); });
  },
  async murmphoto() {
    if (!(await needName())) return;
    if (!(await confirmBox('Remove this photo?', 'It leaves the find. The file is kept in the photos_deleted folder.', 'Remove photo', true))) return;
    await guard(async () => { await api('DELETE', '/api/fungi/photos/' + MUCUR.photos[MUPIX].id); toast('Photo removed'); await muReload(0); });
  },
  async mugps(el) {
    if (!(await needName())) return;
    await guard(async () => { await api('PUT', '/api/fungi/' + enc(MUCUR.code), { base_version: MUCUR.version, fields: { lat: el.dataset.lat, lon: el.dataset.lon } }); toast('Location saved'); await muReload(); });
  },
  async muarch(el) {
    if (!(await needName())) return;
    await guard(async () => { await api('POST', '/api/fungi/' + enc(MUCUR.code) + '/status', { archived: el.dataset.to === '1' }); toast(el.dataset.to === '1' ? 'Archived' : 'Brought back'); await muReload(); });
  },
  async muident() {
    const p = MUCUR.photos[MUPIX], box = document.getElementById('mu-ident'); if (!p) return;
    box.innerHTML = rend(html`<p role="status">Checking the photo…</p>`);
    try {
      const blob = await (await fetch(p.url || photoUrl(p.file))).blob(), fd = new FormData(); fd.append('image', blob, 'find.jpg');
      const r = await api('POST', '/api/identify?scope=fungi', undefined, fd);
      MUIDENT = r.species || [];
      box.innerHTML = rend(html`<h3>It looks most like</h3>${r.genera && r.genera[0] ? html`<p>Most likely genus: <i>${r.genera[0].genus}</i> (${pct(r.genera[0].probability)}).</p>` : ''}
        <ol class="id-sps">${MUIDENT.map((s, i) => html`<li class="id-sp"><div><i class="sci">${s.scientific_name}</i>${s.common_name ? html` <span>${s.common_name}</span>` : ''} <b class="id-p">${pct(s.probability)}</b></div>
          <div class="muted">${s.family}</div><div class="id-acts"><a href="#/species/${enc(s.scientific_name)}">Open in the library</a>${canChange() ? html`<button class="btn small ghost" type="button" data-act="muusename" data-i="${i}">Use this name (as a guess)</button>` : ''}</div></li>`)}</ol>
        <p class="hint">Checked in ${r.seconds} seconds on this computer. A second opinion from Pl@ntNet or Claude is on the Identify page.</p>`);
    } catch (e) { box.innerHTML = rend(html`<div class="notice bad" role="alert">${e.message}</div>`); }
  },
  async muusename(el) {
    const s = MUIDENT[+el.dataset.i]; if (!s || !(await needName())) return;
    await guard(async () => { await api('PUT', '/api/fungi/' + enc(MUCUR.code), { base_version: MUCUR.version, fields: { name: MUCUR.name || s.common_name || s.scientific_name, scientific_name: s.scientific_name, id_status: 'A guess' } }); toast('Name saved as a guess'); await muReload(); });
  },
  munewfrom: () => { if (!SPCUR) return; MUFILL = { name: SPCUR.common_name || '', scientific_name: SPCUR.scientific_name, id_status: 'A guess' }; go('#/fungi/new'); },
});
let MUIDENT = [];
Object.assign(changeActs, {
  async muaddphotos(el) {
    const files = [...el.files]; el.value = ''; if (!files.length || !(await needName())) return;
    const fd = new FormData(); files.forEach(f => fd.append('files', f));
    await guard(async () => { const r = await api('POST', '/api/fungi/' + enc(MUCUR.code) + '/photos', undefined, fd); toast(`${files.length} photo${files.length === 1 ? '' : 's'} added`); MUCUR = r; await route(); muGallery(r.photos.length - 1); });
  },
});
Object.assign(formActs, {
  async musave(form) {
    if (!(await needName())) return;
    const fields = {};
    for (const f of (MU.meta ? MU.meta.fields : [])) if (form.elements[f.name]) fields[f.name] = form.elements[f.name].value;
    if (!fields.place_kind || fields.place_kind !== 'In a plant pot') fields.plant_code = '';
    const err = document.getElementById('form-err'); err.innerHTML = '';
    try {
      let code = form.dataset.code;
      if (code) await api('PUT', '/api/fungi/' + enc(code), { base_version: +form.dataset.ver, fields });
      else {
        const r = await api('POST', '/api/fungi', { fields }); code = r.code;
        const files = form.elements.photos ? [...form.elements.photos.files] : [];
        if (files.length) {
          const fd = new FormData(); files.forEach(f => fd.append('files', f));
          const p = await api('POST', '/api/fungi/' + enc(code) + '/photos', undefined, fd);
          if (p.located && fields.lat === '') toast('The location from the photo was saved with the find.');
        }
        MUFILL = null;
      }
      toast(form.dataset.code ? 'Saved' : /^NEW-/.test(code) ? 'Find added' : 'Find ' + code + ' added'); go('#/fungi/' + enc(code));
    } catch (e) { err.innerHTML = rend(html`<div class="notice bad" role="alert"><strong>Not saved.</strong> ${e.message}</div>`); err.scrollIntoView({ block: 'center' }); }
  },
});
