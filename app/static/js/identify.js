/* Plant record front end: Identify (the camera, the picture checker, the two ways to identify, the names list used on every page that
   identifies), and the shared region helpers. It was discover.js until 1.57.0, when the library, Shopping and mushroom finds moved to
   library.js, shopping.js and mushrooms.js (review item 25). The scripts load in the order js/manifest.json gives and share one scope,
   so a function here may call any other. Plain JavaScript, no inline handlers (the server's content policy forbids them). */
'use strict';

// ---------- 1.18.0: identify a plant with the camera, and the plant library ----------
// The pictures go to this computer's picture checker (the "plant-vision" container) through the app. Pl@ntNet and Claude are only
// asked when someone presses their buttons. Nothing is saved unless someone presses "Add this picture to its photos" or adds a plant.
// 1.28.0: the place in use's state or country (META.region), instead of Texas everywhere
const REGION = () => (META && META.region) || null;
const regionName = () => (REGION() && REGION().name) || 'your state or country';
const regionState = () => (REGION() && REGION().usda) || '';
const inRegion = s => !!(regionState() && ((s.us_states || []).some(Boolean) ? s.us_states.includes(regionState()) : s.in_texas));   // offline rows carry only a yes or no
const ID_SCOPES_ALL = [['common', 'Plants with a common name, and all US plants'], ['state', 'Plants of your state'], ['us', 'US plants'], ['world', 'All plants worldwide'], ['fungi', 'Fungi worldwide: mushrooms, lichens and moulds']];
const ID = { stream: null, timer: null, busy: false, last: null, streak: 0, shot: null, paused: false, said: '', qr: null, mode: null, modeByHand: false, st: null, keys: null };   // mode (5b): 'mine' or 'new', the way the next check runs
function idScopes() { return ID_SCOPES_ALL.filter(x => x[0] !== 'state' || regionState()).map(x => x[0] === 'state' ? ['state', `${LIB_STATE_WORD(regionState())} plants`] : x); }
let ID_SCOPES = ID_SCOPES_ALL;            // filled in by idScopes() once the place is known
function idScope() { ID_SCOPES = idScopes(); try { let s = localStorage.getItem('plantdb.idscope'); if (s === 'texas') s = 'state'; if (ID_SCOPES.some(x => x[0] === s)) return s; } catch (e) { /* default */ } return 'common'; }
// ---------- PLAN.md step 5b: two ways to identify ----------
// 'mine': which of my plants is this? (the record's own species and genera, houseplants and look-alike photos are lifted).
// 'new': a plant met somewhere: no lift for the record's own plants; species recorded in the home's country are lifted instead.
// Every page that identifies asks first, offering the last answer first, unless Display says what to use on that page
// (localStorage plantdb.idmode = { identify, add, plant: 'ask' | 'mine' | 'new', last }; synced to the server by prefs.js).
const ID_MODE_WORDS = { mine: 'One of my plants', new: 'A new find' };
const ID_MODE_HELP = { mine: 'A plant in the record, or a cutting or new pot of one: names you already have come first.',
                       new: 'A plant met in a garden, a shop or the wild: plants recorded in this country come first, and what you have does not count.' };
const ID_MODE_PAGES = { identify: 'On Identify', add: 'When adding plants', plant: 'On a plant\'s own page' };
function idModePref() { try { const v = JSON.parse(localStorage.getItem('plantdb.idmode') || '{}') || {}; return typeof v === 'object' ? v : {}; } catch (e) { return {}; } }
function idModeSave(v) { try { localStorage.setItem('plantdb.idmode', JSON.stringify(v)); } catch (e) { /* this visit only */ } }
function idModeFor(page) { const v = idModePref()[page]; return v === 'mine' || v === 'new' ? v : 'ask'; }
function idModeLast() { const v = idModePref().last; return v === 'new' ? 'new' : 'mine'; }
// the question: a window with two big buttons (the last answer first) and a box to stop asking on this page. null = cancelled
async function idPickMode(page) {
  if (page === 'identify' && ID.modeByHand && ID.mode) return ID.mode;      // the choice on the page, made by hand this visit, wins
  const set = idModeFor(page); if (set !== 'ask') { ID.mode = set; return set; }
  const first = idModeLast(), order = first === 'new' ? ['new', 'mine'] : ['mine', 'new'];
  const r = await modal(html`<form method="dialog" class="idm-form"><h2>What are you looking at?</h2>
    <div class="idm-choices">${order.map((m, i) => html`<button class="btn idm-btn" value="${m}" ${i ? '' : raw('autofocus')}><strong>${ID_MODE_WORDS[m]}</strong><span>${ID_MODE_HELP[m]}</span></button>`)}</div>
    <label class="chk"><input type="checkbox" name="keep">Do not ask again ${ID_MODE_PAGES[page].charAt(0).toLowerCase() + ID_MODE_PAGES[page].slice(1)}: always use the answer I choose now (change it in Display settings)</label>
    <div class="row"><button class="btn ghost" value="cancel">Cancel</button></div></form>`, 'idm');
  if (r !== 'mine' && r !== 'new') return null;
  const v = idModePref(); v.last = r;
  const keep = dlg.querySelector('[name=keep]'); if (keep && keep.checked) v[page] = r;
  idModeSave(v); ID.mode = r;
  const sel = document.querySelector('[data-act=idmode]'); if (sel) sel.value = r;
  return r;
}
// the line under a result saying which way it was checked, and whether the country's list is there yet
function idModeNote(r) {
  if (!r || !r.mode) return '';
  const C = r.country, cc = ID.st && ID.st.site_country;
  let where = '';
  if (r.mode === 'new') {
    if (C && C.state === 'ready') where = ` Plants recorded in ${C.code} (${Number(C.species).toLocaleString()} species) come first.`;
    else if (C && C.state === 'fetching') where = ` The list of plants recorded in ${C.code} is downloading (the first time only); until it is there, no country is favoured.`;
    else if (C && C.state === 'error') where = ` The list of plants recorded in ${C.code} could not be downloaded; no country is favoured.`;
    else if (!cc) where = ' This home has no country set (Weather → Homes and places), so no country is favoured.';
  }
  return html`<p class="hint id-mode-note">Checked as <strong>${ID_MODE_WORDS[r.mode].toLowerCase()}</strong>.${where}</p>`;
}
const pct = p => Math.round((p || 0) * 100) + '%';
const sureWord = c => c >= 0.9 ? 'Very likely' : c >= 0.75 ? 'Likely' : c >= 0.5 ? 'Possibly' : 'Unsure';
const canChange = () => ME().role !== 'viewer';
function idStatusText(st) {
  if (!st) return 'Checking the picture checker…';
  if (st.state === 'ready') return `Ready. It compares pictures with ${st.photos} photos of your plants and ${Number(st.species || 0).toLocaleString()} plant species.`
    + (st.examples && (st.examples.yes || st.examples.no) ? ` It has also learned from ${st.examples.yes} confirmed ${st.examples.yes === 1 ? 'picture' : 'pictures'} and ${st.examples.no} said "Not this" to.` : '');   // 5c
  if (st.state === 'off') return st.step || 'The picture checker is not running.';
  if (st.state === 'error') return 'The picture checker could not start: ' + (st.error || st.step) + '. Restarting the app usually fixes it; see README, "Identify a plant".';
  return 'The picture checker is setting up: ' + st.step + (st.total ? ` (${st.done} of ${st.total})` : '') + '. The first start downloads about 5 GB and can take 20 to 40 minutes.';
}
async function idLoadStatus() {
  try { ID.st = await api('GET', '/api/identify/status'); } catch (e) { ID.st = { state: 'off', step: e.message }; }
  const b = document.getElementById('id-st');
  if (b) { b.textContent = idStatusText(ID.st); b.className = 'notice ' + (ID.st.state === 'ready' ? 'ok' : ID.st.state === 'off' || ID.st.state === 'error' ? 'bad' : ''); }
  if (ID.st.state !== 'ready' && ID.st.state !== 'error' && document.getElementById('id-st')) { clearTimeout(ID.stt); ID.stt = setTimeout(idLoadStatus, 5000); }
}
async function viewIdentify() {
  idStop();
  let keys = null;
  try { keys = await api('GET', '/api/identify/settings'); } catch (e) { /* shown as not set up */ }
  ID.keys = keys;
  const sc = idScope(), owner = ME().role === 'owner';
  try { ALL = await api('GET', '/api/plants?status=all'); } catch (e) { /* the table says so */ }
  await loadGroups();
  IDPH.shown = IDPH_PAGE;
  return {
    title: 'Identify a plant',
    after: () => { idLoadStatus(); drawIdPhotos(); },
    html: html`<h1>Identify a plant</h1>
    <p>Point your camera at a plant. This computer compares the picture with your plant photos and says which plant it thinks it is, and how sure it is. If it is not one of yours, it suggests what the plant could be. Nothing is saved unless you choose to save it.</p>
    <p id="id-st" class="notice" role="status">Checking the picture checker…</p>
    <div class="id-two"><section class="id-sec id-cam" aria-labelledby="h-cam"><h2 id="h-cam">Camera</h2>
      <div class="id-view" id="id-view"><video id="id-video" playsinline muted aria-label="Camera picture"></video>
        <p class="id-placeholder" id="id-ph">The camera is off.</p></div>
      <p id="id-live" class="id-live" role="status" aria-live="polite"></p>
      <div class="row id-btns">
        <button class="btn" type="button" data-act="idcam" id="id-cam-btn">Start camera</button>
        <button class="btn ghost" type="button" data-act="idsnap" id="id-snap" disabled aria-describedby="id-snap-why">Check this picture</button><span class="why" id="id-snap-why">Start the camera first.</span>
        <label class="btn ghost id-file">Choose a photo<input type="file" accept="image/*" data-act="idfile"></label>
      </div>
      <p class="hint">While the camera is on it checks about once a second, and also reads plant label QR codes. "Check this picture" holds the picture still and shows everything it found.</p>
      <label class="f id-scope">What you are looking at
        <select data-act="idmode">${['mine', 'new'].map(m => html`<option value="${m}" ${(idModeFor('identify') !== 'ask' ? idModeFor('identify') : ID.mode || idModeLast()) === m ? raw('selected') : ''}>${ID_MODE_WORDS[m]}</option>`)}</select>
        <small>${idModeFor('identify') === 'ask' ? 'Asked when the camera starts or a photo is chosen; change it here any time.' : `Set in Display settings to "${ID_MODE_WORDS[idModeFor('identify')]}" for this page; a change here holds while you are on the page.`}</small></label>
      <label class="f id-scope">When it is not one of your plants, suggest names from
        <select data-act="idscope">${ID_SCOPES.map(([k, l]) => html`<option value="${k}" ${k === sc ? raw('selected') : ''}>${l}</option>`)}</select></label>
    </section>
    <section class="id-sec" aria-labelledby="h-idres"><h2 id="h-idres">What it found</h2><div id="id-res"><p class="muted">Start the camera or choose a photo.</p></div></section></div>
    <section class="id-sec" aria-labelledby="h-second"><h2 id="h-second">Second opinions</h2>
      <p>When this computer is unsure, you can ask Pl@ntNet (free, up to 500 pictures a day) and then Claude (paid per picture, about a cent or two). They only see a picture when you press their button. Pl@ntNet does not keep pictures.</p>
      <ul class="id-keys">
        <li><strong>Pl@ntNet:</strong> ${keys && keys.plantnet ? html`set up (key ending ${keys.plantnet_hint.slice(1)})` : 'not set up'}</li>
        <li><strong>Claude:</strong> ${keys && keys.claude ? html`set up (key ending ${keys.claude_hint.slice(1)}), using ${keys.claude_model}` : 'not set up'}</li>
      </ul>
      ${owner ? html`<details class="id-setkeys"><summary>Set up or change the keys</summary>
        <form data-form="idkeys" autocomplete="off">
          <label class="f">Pl@ntNet API key<small>Free: sign in at my.plantnet.org, open "My account", then "Settings", and copy the API key. Leave empty to keep the saved one.</small>
            <input type="password" name="plantnet_key" autocomplete="off" spellcheck="false"></label>
          <label class="f">Anthropic API key, for Claude<small>From console.anthropic.com, "API keys". It is billed to that account. Leave empty to keep the saved one.</small>
            <input type="password" name="claude_key" autocomplete="off" spellcheck="false"></label>
          <label class="chk"><input type="checkbox" name="plantnet_auto" ${keys && keys.plantnet_auto ? raw('checked') : ''}>Ask Pl@ntNet on its own whenever this computer is unsure (needs the Pl@ntNet key; one of its 500 free pictures a day each time)</label>
          <p class="hint">The keys stay on this computer, in the database (and so in its backups). The app never shows them again, only their last 4 characters.</p>
          <div class="row"><button class="btn" type="submit">Save keys</button>
            ${keys && keys.plantnet ? html`<button class="btn ghost" type="button" data-act="idkeydel" data-k="plantnet_key">Remove the Pl@ntNet key</button>` : ''}
            ${keys && keys.claude ? html`<button class="btn ghost" type="button" data-act="idkeydel" data-k="claude_key">Remove the Claude key</button>` : ''}</div>
        </form></details>` : html`<p class="muted">${ME().owner_name || 'The owner'} can set these up.</p>`}
    </section>
    <section class="id-sec" aria-labelledby="h-idph"><h2 id="h-idph">Your plant photos</h2>
      <p>These are the photos Identify compares your pictures with, one row per plant. Choose a plant or a photo to open its page. The search and filters are the same as on the Plants page; changing them here changes them there too.</p>
      <div class="filters filters-main">
        <label>Search<input type="search" data-f="q" value="${G.q}" placeholder="Name, code, location"></label>
        <label>Sort by<select data-f="sort">${Object.entries(SORTS).map(([k, v]) => html`<option value="${k}" ${G.sort === k ? raw('selected') : ''}>${v}</option>`)}</select></label>
        <label class="chk"><input type="checkbox" data-f="idphnone" ${IDPH.none ? raw('checked') : ''}>Only plants with no photos</label>
        <button class="btn ghost small" type="button" data-act="clearfilters">Clear filters</button>
      </div>
      ${moreFilters(html`<label>Health<select data-f="health"><option value="">Any</option>${META.health.map(h => html`<option ${G.health === h ? raw('selected') : ''}>${h}</option>`)}</select></label>
        ${homeFilter()}${siteFilter()}${groupFilter()}${statusFilter()}`, (G.health ? 1 : 0) + (G.home ? 1 : 0) + (G.site ? 1 : 0) + (G.group ? 1 : 0) + (G.status !== 'active' ? 1 : 0))}
      <p id="idph-count" class="muted" role="status" aria-live="polite"></p>
      <div id="idph-tbl"></div>
      <p class="row"><button class="btn" type="button" data-act="idphmore" id="idph-more" hidden>Show more</button></p>
    </section>
    <p><a href="#/library">Search the plant library</a></p>`,
  };
}
// 1.28.0: the photo table (one row per plant, its photos in a strip), using the Plants page filters
const IDPH_PAGE = 30, IDPH = { shown: 30, none: false };
function drawIdPhotos() {
  const box = document.getElementById('idph-tbl'); if (!box) return;
  gSave();
  const r = filteredPlants().filter(p => !IDPH.none || !(p.photos || []).length);
  const nPh = r.reduce((n, p) => n + (p.photos || []).length, 0), show = r.slice(0, IDPH.shown);
  const mf = document.querySelector('#more-f > summary'); if (mf) { const n = moreOn(); mf.textContent = 'More filters' + (n ? ` (${n} on)` : ''); }
  document.getElementById('idph-count').textContent = `Showing ${show.length} of ${r.length} plants, with ${num(nPh)} photo${nPh === 1 ? '' : 's'} between them.`;
  const day = t => t ? new Date(t).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' }) : '';
  const multi = HOMES().length > 1;
  box.innerHTML = rend(r.length ? html`<div class="tbl-wrap"><table class="tbl idph"><caption class="sr">Your plants and their photos</caption><thead><tr>
    <th scope="col">Plant</th><th scope="col">Photos</th><th scope="col">${multi ? 'Home and spot' : 'Where'}</th><th scope="col">Newest photo</th></tr></thead><tbody>
    ${show.map(p => { const ph = p.photos || [];
      return html`<tr><th scope="row"><a href="#/plant/${enc(p.code)}"><strong>${p.code}</strong> ${p.common_name}</a><div class="latin muted">${p.scientific_name || ''}</div><div>${ph.length} photo${ph.length === 1 ? '' : 's'}</div></th>
      <td>${ph.length ? html`<div class="idph-strip">${ph.slice(0, 8).map((f, i) => html`<a href="#/plant/${enc(p.code)}"><img src="${thumbUrl(f)}" alt="${p.common_name}, photo ${i + 1} of ${ph.length}${i === 0 ? ' (main photo)' : ''}" loading="lazy"></a>`)}
        ${ph.length > 8 ? html`<a class="btn ghost small" href="#/plant/${enc(p.code)}">${ph.length - 8} more</a>` : ''}</div>` : html`<span class="muted">No photos yet. Identify cannot recognise it until it has one.</span>`}</td>
      <td>${multi ? html`<div>${plantHome(p).name}</div>` : ''}<div class="${multi ? 'muted' : ''}">${p.location || p.site || ''}</div></td>
      <td>${day(p.photo_at)}</td></tr>`; })}</tbody></table></div>`
    : html`<p class="notice">No plants match these filters. <button class="btn ghost small" type="button" data-act="clearfilters">Clear filters</button></p>`);
  const more = document.getElementById('idph-more'); if (more) { more.hidden = r.length <= IDPH.shown; more.textContent = `Show ${Math.min(IDPH_PAGE, r.length - IDPH.shown)} more`; }
  if (typeof fitTables === 'function') fitTables();
}
function idStop() {
  clearTimeout(ID.timer); ID.timer = null;
  if (ID.stream) ID.stream.getTracks().forEach(t => t.stop());
  ID.stream = null; ID.busy = false; ID.streak = 0; ID.last = null; ID.paused = false; ID.said = '';
}
function idCamUi(on) {
  const b = document.getElementById('id-cam-btn'), s = document.getElementById('id-snap'), ph = document.getElementById('id-ph');
  if (b) b.textContent = on ? 'Stop camera' : 'Start camera';
  if (s) s.disabled = !on;
  if (ph) ph.hidden = on;
}
async function idCamToggle() {
  if (ID.stream) { idStop(); idCamUi(false); idSay('The camera is off.'); return; }
  if (!(await idPickMode('identify'))) return;                         // 5b: one of my plants, or a new find
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    toast(window.isSecureContext ? 'This browser cannot use the camera. Use "Use a photo instead".' : 'The browser only allows the camera on a secure address: use http://localhost:8080 on this computer, or the Tailscale address (https://plants...). Or use "Use a photo instead".', true);
    return;
  }
  try {
    ID.stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' }, width: { ideal: 1920 }, height: { ideal: 1080 } }, audio: false });
  } catch (e) {
    toast(e.name === 'NotAllowedError' ? 'The camera was not allowed. Allow it in the browser\'s site settings, then try again.' : 'Could not start the camera: ' + e.message, true);
    return;
  }
  const v = document.getElementById('id-video');
  if (!v) { idStop(); return; }
  v.srcObject = ID.stream; await v.play().catch(() => {});
  if ('BarcodeDetector' in window && !ID.qr) { try { ID.qr = new window.BarcodeDetector({ formats: ['qr_code'] }); } catch (e) { ID.qr = null; } }
  idCamUi(true); idSay('The camera is on. Point it at a plant.');
  idTick();
}
function idSay(t) { if (t === ID.said) return; ID.said = t; const l = document.getElementById('id-live'); if (l) l.textContent = t; }
function idGrab(maxSide) {
  const v = document.getElementById('id-video');
  if (!v || !v.videoWidth) return null;
  const k = Math.min(1, maxSide / Math.max(v.videoWidth, v.videoHeight)), c = document.createElement('canvas');
  c.width = Math.round(v.videoWidth * k); c.height = Math.round(v.videoHeight * k);
  c.getContext('2d').drawImage(v, 0, 0, c.width, c.height);
  return c;
}
const toBlob = c => new Promise(res => c.toBlob(res, 'image/jpeg', 0.86));
async function idAsk(blob, scope, more, ex) {  // 1.39.0: more = other pictures of the same plant, checked together; 1.40.0: ex = {species: [], genera: []} said "Not this"
  const fd = new FormData(); fd.append('image', blob, 'picture.jpg');
  (more || []).forEach((b, i) => fd.append('images', b, `picture${i + 2}.jpg`));
  const q = { scope: scope || idScope(), mode: ID.mode || 'mine' };     // 5b
  if (ex && ex.species.length) q.exclude = ex.species.join('|');
  if (ex && ex.genera.length) q.exclude_genera = ex.genera.join('|');
  return api('POST', '/api/identify?' + new URLSearchParams(q).toString(), undefined, fd);
}
// 5c (1.52.0): "Not this" and "This is right" send the picture too, as a form: the checker keeps it as an example of what the
// name does not (or does) look like. Without a picture (Add several, the plant form) the rejection is words only, as before.
function idReject(name, genus, blob, plant) {
  if (!blob) return api('POST', '/api/identify/reject', { name, genus, plant: plant || null });
  const fd = new FormData(); fd.append('name', name); fd.append('genus', genus ? '1' : '0'); if (plant) fd.append('plant', plant); fd.append('image', blob, 'picture.jpg');
  return api('POST', '/api/identify/reject', undefined, fd);
}
async function idConfirm(el) {
  const name = el.dataset.name, src = el.dataset.ctx;
  if (!(await needName())) return;
  const fd = new FormData(); fd.append('name', name); fd.append('source', src);
  if (src === 'id' && ID.shot && ID.shot.blob) fd.append('image', ID.shot.blob, 'picture.jpg');
  else if (src === 'plant' && el.dataset.code) fd.append('plant', el.dataset.code);
  else return;
  await guard(async () => {
    const r = await api('POST', '/api/identify/confirm', undefined, fd);
    toast(`Saved: this picture is ${name}. The checker now has ${r.examples} ${r.examples === 1 ? 'example' : 'examples'} of it.`);
    el.disabled = true; el.textContent = 'Confirmed';
  });
}
// 1.40.0: "Not this": the name (or its genus) leaves the list, the pictures are checked again without it, and the choice is logged
async function idNot(el) {
  const ctx = el.dataset.ctx, name = el.dataset.name, genus = el.dataset.genus === '1';
  if (ctx === 'id') {
    if (!ID.shot) return;
    ID.shot.ex = ID.shot.ex || { species: [], genera: [] }; (genus ? ID.shot.ex.genera : ID.shot.ex.species).push(name);
    if (canChange()) idReject(name, genus, ID.shot.blob).catch(() => null);          // 5c: with the picture, so the checker learns
    const res = document.getElementById('id-res'); if (res) res.insertAdjacentHTML('afterbegin', rend(html`<p class="muted" role="status">Checking again without ${genus ? 'the genus ' : ''}${name}…</p>`));
    try { ID.shot.result = await idAsk(ID.shot.blob, null, ID.shot.more, ID.shot.ex); ID.shot.plantnet = ID.shot.result.plantnet || null; idPaint(ID.shot.result, ID.shot.url); idSay(`Not ${name}. Checked again.`); }
    catch (e) { toast(e.message, true); }
    const f = document.querySelector('#id-splist li'); if (f) { f.setAttribute('tabindex', '-1'); f.focus(); }
  } else if (ctx === 'sev') {
    const P = SEV.plants[+el.dataset.g]; if (!P) return;
    P.ex = P.ex || { species: [], genera: [] }; (genus ? P.ex.genera : P.ex.species).push(name);
    if (canChange()) api('POST', '/api/identify/reject', { name, genus }).catch(() => null);
    await sevIdentify(+el.dataset.g, true);
  } else if (ctx === 'plant') {                // the plant's page: the rejection sticks to the plant
    const code = el.dataset.g; if (!code) return;
    await guard(async () => { await api('POST', '/api/identify/reject', { name, genus, plant: code }); await plantIdentify(code); });
  } else if (ctx === 'new') {
    NEWID.ex = NEWID.ex || { species: [], genera: [] }; (genus ? NEWID.ex.genera : NEWID.ex.species).push(name);
    if (canChange()) api('POST', '/api/identify/reject', { name, genus }).catch(() => null);
    const b = document.getElementById('newfill-btn'); if (b) acts.newfill(b);
  }
}
// 1.39.0: another picture of the same plant, from a file or the camera: all of them are checked together
async function idAddShot(blob, url) {
  if (!ID.shot) return;
  ID.shot.more = (ID.shot.more || []).concat([blob]); ID.shot.moreUrls = (ID.shot.moreUrls || []).concat([url]);
  const res = document.getElementById('id-res'); if (res) res.insertAdjacentHTML('afterbegin', rend(html`<p class="muted" role="status">Checking ${ID.shot.more.length + 1} pictures together…</p>`));
  try {
    ID.shot.result = await idAsk(ID.shot.blob, null, ID.shot.more); ID.shot.plantnet = ID.shot.result.plantnet || null;
    idPaint(ID.shot.result, ID.shot.url);
    await idPopup(ID.shot.result);
  } catch (e) { toast(e.message, true); }
}
// 1.40.0: a plant's page: its own photos through the one identifier, with its own "Not this" list; "Use this name" renames the plant
let PLANTID = null;
async function plantIdentify(code, plantnet) {
  const box = document.getElementById('plant-id'); if (!box) return;
  if (!PLANTID || PLANTID.code !== code || !PLANTID.mode) { const m = await idPickMode('plant'); if (!m) return; PLANTID = { code, mode: m }; }   // 5b: asked once per plant
  const mode = PLANTID.mode;
  box.innerHTML = rend(html`<p class="muted" role="status">Checking its photos${ID.keys && ID.keys.plantnet ? ' with this computer and Pl@ntNet' : ''}…</p>`);
  try {
    if (!ID.keys) { try { ID.keys = await api('GET', '/api/identify/settings'); } catch (e) { /* fine */ } }
    const r = await api('POST', '/api/plants/' + enc(code) + '/identify?mode=' + mode, { plantnet: plantnet || 'auto' }); PLANTID = { code, r, mode };
    box.innerHTML = rend(html`<h3>What its photos say it could be</h3>${idModeNote(r)}${idNamesPanel(r, { src: 'plant', id: 'plant-splist', use: 'plantuse', reject: 'plant', code })}
      ${ID.keys && ID.keys.plantnet && !r.plantnet ? html`<p class="row"><button class="btn small ghost" type="button" data-act="plantask" data-code="${code}">Ask Pl@ntNet as well</button></p>` : ''}`);
    const h = box.querySelector('h3'); if (h) { h.setAttribute('tabindex', '-1'); h.focus(); }
  } catch (e) { box.innerHTML = rend(html`<div class="notice bad" role="alert">${e.message}</div>`); }
}
async function idMoreFile(input) {
  const f = input.files && input.files[0]; input.value = '';
  if (!f) return;
  const url = await new Promise((ok, no) => { const fr = new FileReader(); fr.onload = () => ok(fr.result); fr.onerror = no; fr.readAsDataURL(f); });
  await idAddShot(f, url);
}
async function idSnapMore() {
  const c = idGrab(1600); if (!c || !ID.shot) return;
  ID.paused = true;
  try { await idAddShot(await toBlob(c), c.toDataURL('image/jpeg', 0.8)); } catch (e) { toast(e.message, true); }
  ID.paused = false;
}
async function idQr() {
  if (!ID.qr) return false;
  const v = document.getElementById('id-video');
  try {
    const codes = await ID.qr.detect(v);
    for (const q of codes) {
      const m = /#\/plant\/([^/?#\s]+)/.exec(q.rawValue || '');
      if (m) { const code = decodeURIComponent(m[1]); ID.paused = true; await idLabelFound(code); ID.paused = false; return true; }
    }
  } catch (e) { /* no QR this time */ }
  return false;
}
async function idLabelFound(code) {
  await loadCodes(true);
  const p = PCODES.get(code);
  idSay(`Label found: ${code}${p ? ', ' + p.common_name : ''}.`);
  const r = await modal(html`<form method="dialog" class="id-pop"><h2>Label found: ${code}</h2>
    ${p ? html`<p class="id-pop-name">${p.common_name}${p.scientific_name ? html` (<i>${p.scientific_name}</i>)` : ''}</p>${p.photo ? html`<img class="id-pop-img" src="${thumbUrl(p.photo)}" alt="Photo of ${p.common_name}">` : ''}` : html`<p>There is no plant ${code} in the record.</p>`}
    <div class="row">${p ? html`<button class="btn" value="open" autofocus>Open its page</button>` : ''}<button class="btn ghost" value="cancel" ${p ? '' : raw('autofocus')}>Keep looking</button></div></form>`);
  if (r === 'open') { idStop(); go('#/plant/' + enc(code)); }
}
async function idTick() {
  clearTimeout(ID.timer);
  if (!ID.stream || !document.getElementById('id-video')) { idStop(); return; }
  if (!ID.paused && !ID.busy && !document.hidden && !dlg.open) {
    ID.busy = true;
    try {
      if (!(await idQr())) {
        const c = idGrab(800);
        if (c && ID.st && ID.st.state === 'ready') {
          const r = await idAsk(await toBlob(c));
          if (ID.stream) await idLive(r, c);
        } else if (ID.st && ID.st.state !== 'ready') idSay(idStatusText(ID.st));
      }
    } catch (e) { idSay(e.message); if (e.status === 503) idLoadStatus(); }
    ID.busy = false;
  }
  if (ID.stream) ID.timer = setTimeout(idTick, 900);
}
async function idLive(r, canvas) {
  if (ID.paused) return;
  const m = r.matches[0];
  idPaint(r, null, true);
  if (!m) { idSay('Looking. No match yet.'); return; }
  const key = r.likely_new ? '(new)' : m.code;      // a plant that looks unlike all of yours counts as one answer too
  ID.streak = ID.last === key ? ID.streak + 1 : 1; ID.last = key;
  const c = m.confidence || 0;
  // a window: the same plant twice in a row when sure, or four times in a row when less sure or when it is not one of yours
  if ((c >= 0.8 && ID.streak >= 2 && !r.likely_new) || (ID.streak >= 4 && (c >= 0.5 || r.likely_new))) {
    ID.paused = true;
    const big = idGrab(1600) || canvas;
    ID.shot = { blob: await toBlob(big), url: big.toDataURL('image/jpeg', 0.8), result: r };
    await idPopup(r);
    ID.paused = false; ID.streak = 0; ID.last = null;
  } else if (r.likely_new) idSay(`This doesn't look like any of your plants.${r.species[0] ? ' It may be ' + (r.species[0].common_name || r.species[0].scientific_name) + '.' : ''} Hold steady.`);
  else if (c >= 0.5) idSay(`${sureWord(c)} ${m.code}, ${m.common_name} (${pct(c)} sure). Hold steady.`);
  else idSay(`Not sure yet. Closest: ${m.code}, ${m.common_name}. ${r.species[0] ? 'Or it may be ' + (r.species[0].common_name || r.species[0].scientific_name) + '.' : ''}`);
}
async function idSnap() {
  const c = idGrab(1600); if (!c) return;
  ID.paused = true;
  try {
    const blob = await toBlob(c);
    ID.shot = { blob, url: c.toDataURL('image/jpeg', 0.8) };
    idSay('Checking this picture…');
    ID.shot.result = await idAsk(blob); ID.shot.plantnet = ID.shot.result.plantnet || null;
    idPaint(ID.shot.result, ID.shot.url);
    await idPopup(ID.shot.result);
  } catch (e) { toast(e.message, true); }
  ID.paused = false;
}
async function idFile(input) {
  const f = input.files && input.files[0]; input.value = '';
  if (!f) return;
  if (!(await idPickMode('identify'))) return;                         // 5b
  const res = document.getElementById('id-res'); if (res) res.innerHTML = rend(html`<p class="muted" role="status">Checking ${f.name}…</p>`);
  try {
    const url = await new Promise((ok, no) => { const fr = new FileReader(); fr.onload = () => ok(fr.result); fr.onerror = no; fr.readAsDataURL(f); });
    ID.shot = { blob: f, url };
    ID.shot.result = await idAsk(f); ID.shot.plantnet = ID.shot.result.plantnet || null;
    idPaint(ID.shot.result, url);
    await idPopup(ID.shot.result);
  } catch (e) { if (res) res.innerHTML = rend(html`<div class="notice bad" role="alert">${e.message}</div>`); }
}
function idMatchCard(m, first) {
  return html`<li class="id-m"><a href="#/plant/${enc(m.code)}" data-act="idopen" data-code="${m.code}">${m.photo ? html`<img src="${thumbUrl(m.matched_photo || m.photo)}" alt="">` : ''}
    <span><b>${m.code}</b> ${m.common_name}${m.location ? html`<small>${m.location}</small>` : ''}${first && m.confidence != null ? html`<small>${sureWord(m.confidence)}: ${pct(m.confidence)} sure</small>` : ''}</span></a></li>`;
}
function spLinks(s) {
  const q = enc(s.scientific_name);
  return html`<span class="id-links">${s.usda_symbol ? html`<a href="https://plants.usda.gov/plant-profile/${enc(s.usda_symbol)}" target="_blank" rel="noopener noreferrer">USDA PLANTS</a>` : ''}
    <a href="https://powo.science.kew.org/results?q=${q}" target="_blank" rel="noopener noreferrer">Kew (POWO)</a>
    <a href="https://en.wikipedia.org/wiki/${enc(s.scientific_name.replace(/ /g, '_'))}" target="_blank" rel="noopener noreferrer">Wikipedia</a></span>`;
}
// 1.40.0: one result panel for Identify, Add a plant and Add several: the merged names (this computer and Pl@ntNet), the likeliest
// genus and family, "Not this" on every name (ctx says which page re-asks), and either "Add as a new plant" or a "Use this name" choice.
function idNamesPanel(r, o) {
  const sp = r.species || [], fold = sp.length > 5, id = o.id || 'id-splist';
  const src = r.sources || ['this computer'];
  return html`${r.plantnet && r.plantnet.error ? html`<p class="notice bad">Pl@ntNet: ${r.plantnet.error}</p>` : ''}${r.plantnet && r.plantnet.note && !(r.plantnet.species || []).length ? html`<p class="hint">${r.plantnet.note}</p>` : ''}
    ${r.genera && r.genera[0] ? html`<p class="id-sum">Most likely genus: ${r.genera.slice(0, 3).map((g, i) => html`${i ? ', then ' : ''}<i>${g.genus}</i> (${pct(g.probability)})`)}${r.families && r.families[0] ? html`; family ${r.families.slice(0, 2).map((f, i) => html`${i ? ' or ' : ''}${f.family} (${pct(f.probability)})`)}` : ''}. ${sp.length ? 'When none of the names fits, the genus is the safer answer. ' : ''}From ${src.join(' and ')}${r.pictures > 1 ? ` (from ${r.pictures} pictures together)` : ''}.</p>` : ''}
    ${sp.length ? html`<ol class="id-sps ${fold ? 'id-fold' : ''}" id="${id}">${sp.map((x, i) => spCard(x, i, o.src, o.add, o))}</ol>
    ${fold ? html`<p><button class="btn small ghost" type="button" data-act="idmoresp" data-list="${id}" aria-controls="${id}" aria-expanded="false">Show ${sp.length - 5} more names</button></p>` : ''}` : html`<p class="muted">No name was found${(r.excluded && (r.excluded.species.length || r.excluded.genera.length)) ? ' that you have not said "Not this" to' : ''}.</p>`}
    ${(r.excluded && (r.excluded.species.length || r.excluded.genera.length)) ? html`<p class="hint">Not this: ${[...r.excluded.genera.map(g => g + ' (the genus)'), ...r.excluded.species].join(', ')}.</p>` : ''}`;
}
function spCard(s, i, src, withAdd, o) {
  o = o || {};
  const tags = [];
  (s.sources || []).forEach(w => tags.push(html`<span class="tag tag-src">${w === 'Pl@ntNet' ? `Pl@ntNet${s.plantnet_probability != null ? ' ' + pct(s.plantnet_probability) : ''}` : 'This computer'}</span>`));
  if (inRegion(s)) tags.push(html`<span class="tag">Grows wild in ${LIB_STATE_WORD(regionState())}</span>`);
  else if (s.us_states && s.us_states.length) tags.push(html`<span class="tag">In ${s.us_states.length} US state${s.us_states.length === 1 ? '' : 's'}</span>`);
  if (s.yours && s.yours.length) tags.push(html`<span class="tag tag-yours">You have this: ${s.yours.join(', ')}</span>`);
  else if (s.yours_genus && s.yours_genus.length) tags.push(html`<span class="tag">Same genus as ${s.yours_genus.slice(0, 4).join(', ')}</span>`);
  (s.basis_words || []).filter(w => !/you have/.test(w) || !(s.yours && s.yours.length)).forEach(w => tags.push(html`<span class="tag tag-why">${/^lowered/.test(w) ? w.charAt(0).toUpperCase() + w.slice(1) : 'Lifted: ' + w}</span>`));   // 1.39.0; 5c: lowered too
  return html`<li class="id-sp"><div><i class="sci">${s.scientific_name}</i>${s.common_name ? html` <span>${s.common_name}</span>` : ''}
      ${s.probability != null ? html`<b class="id-p">${pct(s.probability)}</b>` : ''}</div>
    <div class="muted">${[s.family, s.order].filter(Boolean).join(', ')}</div>
    ${s.why ? html`<div>${s.why}</div>` : ''}
    ${tags.length ? html`<div class="id-tags">${tags}</div>` : ''}
    ${o.pick != null ? html`<label class="chk"><input type="radio" name="sevsp${o.pick}" data-f="sevpick" data-g="${o.pick}" value="${i}" ${o.picked === i ? raw('checked') : ''}>Use this name</label>` : ''}
    <div class="id-acts">${spLinks(s)}${withAdd ? s.kingdom === 'Fungi' ? html`<button class="btn small" type="button" data-act="idfind" data-src="${src}" data-i="${i}">Record a mushroom find</button>`
      : html`<button class="btn small" type="button" data-act="idnew" data-src="${src}" data-i="${i}">Add as a new plant</button>` : ''}
      ${o.use ? html`<button class="btn small" type="button" data-act="${o.use}" data-i="${i}">Use this name</button>` : ''}
      ${(o.reject === 'id' || o.reject === 'plant') && canChange() && s.kingdom !== 'Fungi' && /^[A-Z][a-z]+ [a-z]/.test(s.scientific_name || '') ? html`<button class="btn small ghost" type="button" data-act="idright" data-ctx="${o.reject}" data-code="${o.code || ''}" data-name="${s.scientific_name}" aria-label="This is right: ${s.scientific_name}">This is right</button>` : ''}
      ${o.reject ? html`<button class="btn small ghost" type="button" data-act="idnot" data-ctx="${o.reject}" data-g="${o.pick == null ? (o.code || '') : o.pick}" data-name="${s.scientific_name}" aria-label="Not this: ${s.scientific_name}">Not this</button>
      <button class="btn small ghost" type="button" data-act="idnot" data-ctx="${o.reject}" data-g="${o.pick == null ? (o.code || '') : o.pick}" data-name="${s.genus || (s.scientific_name || '').split(' ')[0]}" data-genus="1" aria-label="Not this genus: ${s.genus || (s.scientific_name || '').split(' ')[0]}">Not this genus</button>` : ''}</div></li>`;
}
function idPaint(r, picUrl, live) {
  const res = document.getElementById('id-res'); if (!res) return;
  const m = r.matches || [], top = m[0], c = top ? top.confidence || 0 : 0;
  const sc = ID_SCOPES.find(x => x[0] === r.scope);
  res.innerHTML = rend(html`${picUrl ? html`<img class="id-shot" src="${picUrl}" alt="The picture that was checked">` : ''}
    ${top ? html`<h3>${c >= 0.5 && !r.likely_new ? 'Your plant' : 'Closest of your plants'}</h3>
      <p>${c >= 0.5 && !r.likely_new ? html`${sureWord(c)} <b>${top.code}, ${top.common_name}</b>: ${pct(c)} sure.` : html`Probably none of your plants: the closest is ${top.code}, ${top.common_name}, ${pct(c)} sure${r.likely_new ? ', and it looks different from all your photos' : ''}.`}</p>
      <ol class="id-ms ${c >= 0.5 && !r.likely_new ? 'id-sure' : ''}">${m.slice(0, 3).map((x, i) => idMatchCard(x, i === 0))}</ol>` : html`<p>There are no photos of your plants to compare with yet.</p>`}
    <h3>What it could be</h3>
    ${r.scope === 'fungi' ? fungiSafety(true) : ''}
    ${idNamesPanel(r, { src: 'local', add: !live && canChange(), reject: live ? null : 'id' })}
    ${live ? '' : html`<div class="row id-again"><label class="btn ghost small">Add another photo of the same plant<input type="file" accept="image/*" data-act="idmorefile" class="sr"></label>
      ${ID.stream ? html`<button class="btn ghost small" type="button" data-act="idsnapmore">Add a camera shot of it</button>` : ''}
      ${(ID.shot && ID.shot.moreUrls || []).map((u, i) => html`<img class="id-more-pic" src="${u}" alt="Extra picture ${i + 1}">`)}</div>`}
    ${live ? '' : html`<div id="id-more">${idMoreBtns()}</div>`}
    ${idModeNote(r)}
    <p class="hint">Checked in ${r.seconds} seconds by ${r.model} on this computer${r.prior ? (r.mode === 'new' ? ', weighted toward the plants of this country' : ', weighted toward the plants you have, houseplants and the plants of your state') : ''}.</p>`);
}
function idMoreBtns() {
  if (!canChange() || !ID.keys) return '';
  return html`<div class="row">${ID.keys.plantnet ? html`<button class="btn ghost" type="button" data-act="idask" data-who="plantnet">Ask Pl@ntNet</button>` : ''}
    ${ID.keys.claude ? html`<button class="btn ghost" type="button" data-act="idask" data-who="claude">Ask Claude</button>` : ''}</div><div id="id-ext"><div id="id-ext-plantnet"></div><div id="id-ext-claude"></div></div>`;
}
async function idPopup(r) {
  const m = r.matches || [], top = m[0], c = top ? top.confidence || 0 : 0, edit = canChange();
  let body;
  if (top && c >= 0.75 && !r.likely_new) {
    idSay(`${sureWord(c)} ${top.code}, ${top.common_name}: ${pct(c)} sure.`);
    body = html`<h2>${sureWord(c)} ${top.code}: ${top.common_name}</h2>
      <p class="id-conf"><b>${pct(c)} sure.</b> ${c >= 0.85 ? 'In tests on your photos, answers this sure were right about 9 times in 10.' : 'It is not certain: compare the photos.'}</p>
      <div class="id-pair">${ID.shot ? html`<figure><img src="${ID.shot.url}" alt="Your picture"><figcaption>Your picture</figcaption></figure>` : ''}
        <figure><img src="${thumbUrl(top.matched_photo || top.photo)}" alt="Photo of ${top.common_name}"><figcaption>Its closest photo</figcaption></figure></div>
      <div class="row"><button class="btn" value="open:${top.code}" autofocus>Open its page</button>
        ${edit && ID.shot ? html`<button class="btn ghost" value="addpic:${top.code}">Add this picture to its photos</button>` : ''}
        <button class="btn ghost" value="cancel">Not this one</button></div>`;
  } else if (top && c >= 0.45 && !r.likely_new) {
    idSay(`Not sure. It could be ${m.slice(0, 3).map(x => x.code).join(', ')}.`);
    body = html`<h2>Which one is it?</h2><p>It is not sure (${pct(c)} for the first). These look closest:</p>
      <div class="id-choose">${m.slice(0, 3).map((x, i) => html`<button class="id-ch" value="open:${x.code}" ${i === 0 ? raw('autofocus') : ''}>
        ${x.photo ? html`<img src="${thumbUrl(x.matched_photo || x.photo)}" alt="">` : ''}<span><b>${x.code}</b> ${x.common_name}</span></button>`)}</div>
      <p class="hint">Choosing one opens its page.${edit ? ' Or add the picture to one:' : ''}</p>
      ${edit && ID.shot ? html`<div class="row">${m.slice(0, 3).map(x => html`<button class="btn small ghost" value="addpic:${x.code}">Add the picture to ${x.code}</button>`)}</div>` : ''}
      <div class="row"><button class="btn ghost" value="cancel">None of these</button></div>`;
  } else {
    const s = (r.species || [])[0];
    idSay(`Probably not one of your plants.${s ? ' It may be ' + (s.common_name || s.scientific_name) + '.' : ''}`);
    body = html`<h2>Probably not one of your plants</h2>
      ${s ? html`<p>It looks most like <i>${s.scientific_name}</i>${s.common_name ? ' (' + s.common_name + ')' : ''}, but names from a picture are often wrong. See all the suggestions on the page${edit && ID.keys && (ID.keys.plantnet || ID.keys.claude) ? ', or ask for a second opinion' : ''}.</p>` : ''}
      ${top ? html`<p>Or is it one of yours after all? The closest are:</p><ul class="id-close">${m.slice(0, 3).map(x => html`<li><button class="linkish" value="open:${x.code}">${x.code} ${x.common_name}</button></li>`)}</ul>` : ''}
      <div class="row"><button class="btn" value="list" autofocus>See the suggestions</button><button class="btn ghost" value="cancel">Keep looking</button></div>`;
  }
  const v = await modal(html`<form method="dialog" class="id-pop">${body}</form>`, 'wide');
  if (v.startsWith('open:')) { idStop(); go('#/plant/' + enc(v.slice(5))); }
  else if (v.startsWith('addpic:')) await idAddPic(v.slice(7));
  else if (v === 'list') {
    if (ID.shot && ID.shot.result) idPaint(ID.shot.result, ID.shot.url);
    if (ID.stream) { idStop(); idCamUi(false); }
    const h = document.getElementById('h-idres'); if (h) { h.setAttribute('tabindex', '-1'); h.focus(); h.scrollIntoView({ block: 'start' }); }
  }
}
async function idAddPic(code) {
  if (!ID.shot || !(await needName())) return;
  const fd = new FormData(); fd.append('files', ID.shot.blob, 'identify-' + ymd(new Date()) + '.jpg'); fd.append('caption', 'Taken with Identify, ' + new Date().toLocaleDateString());
  await guard(async () => { await api('POST', '/api/plants/' + enc(code) + '/photos', undefined, fd); toast('Picture added to ' + code); idSay('Picture added to ' + code + '.'); });
}
async function idAskOutside(who) {
  if (!ID.shot) return;
  const box = document.getElementById('id-ext-' + who); if (!box) return;
  const name = who === 'plantnet' ? 'Pl@ntNet' : 'Claude';
  box.innerHTML = rend(html`<p role="status">Asking ${name}…</p>`);
  try {
    const fd = new FormData(); fd.append('image', ID.shot.blob, 'picture.jpg');
    const r = await api('POST', '/api/identify/' + who, undefined, fd);
    ID.shot[who] = r;
    box.innerHTML = rend(html`<h3>${name} says</h3>${r.note ? html`<p>${r.note}</p>` : ''}
      ${r.species.length ? html`<ol class="id-sps">${r.species.map((s, i) => spCard(s, i, who, canChange()))}</ol>` : ''}
      ${r.tip ? html`<p class="hint">Tip from Claude: ${r.tip}</p>` : ''}
      ${r.remaining != null ? html`<p class="hint">Pl@ntNet pictures left today: ${r.remaining}.</p>` : ''}`);
    const h = box.querySelector('h3'); if (h) { h.setAttribute('tabindex', '-1'); h.focus(); }
  } catch (e) { box.innerHTML = rend(html`<div class="notice bad" role="alert">${e.message}</div>`); }
}

// "Add as a new plant" and "Add to my plants": the Add a plant form opens with the names filled in (and the picture, if any)
let NEWFILL = null;
function idNewPlant(s, withPic) {
  const g = (s.scientific_name || '').split(' ')[0];
  NEWFILL = { common_name: (s.common_name || '').split(',')[0].trim() || s.scientific_name, scientific_name: s.scientific_name, genus: g, family: s.family || '',
              taxon_order: s.order || '', kingdom: 'Plantae', __pic: withPic && ID.shot ? ID.shot.blob : null,
              __from: `Names from ${s.src || 'the plant library'}` };
  idStop(); go('#/new');
}


function spFrom(src, i) {
  const list = src === 'library' ? LIB.res : src === 'local' ? ID.shot && ID.shot.result && ID.shot.result.species : ID.shot && ID.shot[src] && ID.shot[src].species;
  const s = list && list[+i];
  return s ? Object.assign({}, s, { src: src === 'library' ? 'the plant library' : src === 'local' ? (s.sources && s.sources.length ? 'Identify (' + s.sources.join(' and ') + ')' : 'Identify (this computer)') : src === 'plantnet' ? 'Pl@ntNet' : 'Claude' }) : null;
}
Object.assign(acts, {
  idcam: () => idCamToggle(),
  idsnap: () => idSnap(),
  idsnapmore: () => idSnapMore(),
  idnot: el => idNot(el),
  idright: el => idConfirm(el),          // 5c
  plantid: el => plantIdentify(el.dataset.code),
  plantask: el => plantIdentify(el.dataset.code, 'yes'),
  async plantuse(el) {                  // rename the plant to the chosen name (the page's own fields; the old name stays in the history)
    const s0 = PLANTID && (PLANTID.r.species || [])[+el.dataset.i]; if (!s0) return;
    if (!(await needName())) return;
    const name = (s0.common_name || '').split(',')[0].trim() || s0.scientific_name;
    if (!(await confirmBox(`Name it ${name}?`, `${s0.scientific_name}${s0.family ? ', ' + s0.family : ''}. The common and scientific names, genus, family and ID confidence change; the old ones stay in the page history.`, 'Use this name'))) return;
    await guard(async () => {
      const p = await api('GET', '/api/plants/' + enc(PLANTID.code));
      const fields = { common_name: name, scientific_name: s0.scientific_name, genus: (s0.scientific_name || '').split(' ')[0], family: s0.family || p.family, id_confidence: Math.round((s0.probability || 0) * 100),
        id_basis: `Suggested by ${(s0.sources || ['the picture checker on this computer']).map(w => w === 'this computer' ? 'the picture checker on this computer' : w).join(' and ')} from the plant's photos. Check it.` };
      await api('PUT', '/api/plants/' + enc(PLANTID.code), { base_version: p.version, fields, note: 'Named from its photos' });
      toast(`${PLANTID.code} is now ${name}`); await reloadPlant();
    });
  },
  idmoresp(el) { const l = document.getElementById(el.dataset.list || 'id-splist'); if (!l) return; const open = l.classList.toggle('id-fold'); el.setAttribute('aria-expanded', String(!open)); el.textContent = open ? `Show ${l.children.length - 5} more names` : 'Show fewer names'; if (!open) { const sixth = l.children[5]; if (sixth) { sixth.setAttribute('tabindex', '-1'); sixth.focus(); } } },
  idopen: el => { idStop(); go('#/plant/' + enc(el.dataset.code)); },
  idask: el => idAskOutside(el.dataset.who),
  idnew: el => { const s = spFrom(el.dataset.src, el.dataset.i); if (s) idNewPlant(s, el.dataset.src !== 'library'); },
  idfind: el => { const s = spFrom(el.dataset.src, el.dataset.i); if (!s) return; idStop(); MUFILL = { name: s.common_name || '', scientific_name: s.scientific_name, id_status: 'A guess' }; go('#/fungi/new'); },
  async idkeydel(el) {
    if (!(await confirmBox('Remove the key?', 'The button for this second opinion goes away until a key is saved again.', 'Remove the key', true))) return;
    await guard(async () => { await api('PUT', '/api/identify/settings', { [el.dataset.k]: '' }); toast('Key removed'); route(); });
  },
});
Object.assign(changeActs, { idfile: el => idFile(el), idmorefile: el => idMoreFile(el),
  idmode: el => { ID.mode = el.value; ID.modeByHand = true; const v = idModePref(); v.last = el.value; idModeSave(v); idSay(`Checking as ${ID_MODE_WORDS[el.value].toLowerCase()}.`); },   // 5b
  idscope: el => { try { localStorage.setItem('plantdb.idscope', el.value); } catch (e) { /* this visit only */ } } });   // 1.51.0: the list choice was never saved before (a select with no handler since 1.18.0)
Object.assign(formActs, {
  async spnotes(form) {
    if (!SPCUR || !(await needName())) return;
    await guard(async () => { await api('PUT', '/api/library/notes', { name: SPCUR.scientific_name, notes: form.elements.notes.value, tags: form.elements.tags.value }); toast('Notes and tags saved'); await route(); });
  },
  async idkeys(form) {
    const b = {};
    ['plantnet_key', 'claude_key'].forEach(k => { const v = form.elements[k].value.trim(); if (v) b[k] = v; });
    const auto = !!form.elements.plantnet_auto.checked;
    if (!Object.keys(b).length && auto === !!(ID.keys && ID.keys.plantnet_auto)) { toast('Paste a key first.', true); return; }
    b.plantnet_auto = auto;
    await api('PUT', '/api/identify/settings', b); toast(Object.keys(b).length > 1 ? 'Keys saved' : 'Saved'); route();
  },
});
document.addEventListener('visibilitychange', () => { if (document.hidden && ID.stream) { idStop(); idCamUi(false); } });
