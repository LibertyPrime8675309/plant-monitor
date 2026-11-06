/* Plant record front end: Identify, the library, species pages, around home, the wishlist, Shopping, mushroom finds. One of the files app.js was split into in 1.32.0; they load in order (index.html) and share one scope,
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
const ID = { stream: null, timer: null, busy: false, last: null, streak: 0, shot: null, paused: false, said: '', qr: null, mode: 'live', st: null, keys: null };
function idScopes() { return ID_SCOPES_ALL.filter(x => x[0] !== 'state' || regionState()).map(x => x[0] === 'state' ? ['state', `${LIB_STATE_WORD(regionState())} plants`] : x); }
let ID_SCOPES = ID_SCOPES_ALL;            // filled in by idScopes() once the place is known
function idScope() { ID_SCOPES = idScopes(); try { let s = localStorage.getItem('plantdb.idscope'); if (s === 'texas') s = 'state'; if (ID_SCOPES.some(x => x[0] === s)) return s; } catch (e) { /* default */ } return 'common'; }
const pct = p => Math.round((p || 0) * 100) + '%';
const sureWord = c => c >= 0.9 ? 'Very likely' : c >= 0.75 ? 'Likely' : c >= 0.5 ? 'Possibly' : 'Unsure';
const canChange = () => ME().role !== 'viewer';
function idStatusText(st) {
  if (!st) return 'Checking the picture checker…';
  if (st.state === 'ready') return `Ready. It compares pictures with ${st.photos} photos of your plants and ${Number(st.species || 0).toLocaleString()} plant species.`;
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
        <button class="btn ghost" type="button" data-act="idsnap" id="id-snap" disabled>Check this picture</button>
        <label class="btn ghost id-file">Choose a photo<input type="file" accept="image/*" data-act="idfile"></label>
      </div>
      <p class="hint">While the camera is on it checks about once a second, and also reads plant label QR codes. "Check this picture" holds the picture still and shows everything it found.</p>
      <label class="f id-scope">When it is not one of your plants, suggest names from
        <select data-f="idscope">${ID_SCOPES.map(([k, l]) => html`<option value="${k}" ${k === sc ? raw('selected') : ''}>${l}</option>`)}</select></label>
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
  const q = { scope: scope || idScope() };
  if (ex && ex.species.length) q.exclude = ex.species.join('|');
  if (ex && ex.genera.length) q.exclude_genera = ex.genera.join('|');
  return api('POST', '/api/identify?' + new URLSearchParams(q).toString(), undefined, fd);
}
// 1.40.0: "Not this": the name (or its genus) leaves the list, the pictures are checked again without it, and the choice is logged
async function idNot(el) {
  const ctx = el.dataset.ctx, name = el.dataset.name, genus = el.dataset.genus === '1';
  if (ctx === 'id') {
    if (!ID.shot) return;
    ID.shot.ex = ID.shot.ex || { species: [], genera: [] }; (genus ? ID.shot.ex.genera : ID.shot.ex.species).push(name);
    if (canChange()) api('POST', '/api/identify/reject', { name, genus }).catch(() => null);
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
  box.innerHTML = rend(html`<p class="muted" role="status">Checking its photos${ID.keys && ID.keys.plantnet ? ' with this computer and Pl@ntNet' : ''}…</p>`);
  try {
    if (!ID.keys) { try { ID.keys = await api('GET', '/api/identify/settings'); } catch (e) { /* fine */ } }
    const r = await api('POST', '/api/plants/' + enc(code) + '/identify', { plantnet: plantnet || 'auto' }); PLANTID = { code, r };
    box.innerHTML = rend(html`<h3>What its photos say it could be</h3>${idNamesPanel(r, { src: 'plant', id: 'plant-splist', use: 'plantuse', reject: 'plant', code })}
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
  (s.basis_words || []).filter(w => !/you have/.test(w) || !(s.yours && s.yours.length)).forEach(w => tags.push(html`<span class="tag tag-why">Lifted: ${w}</span>`));   // 1.39.0
  return html`<li class="id-sp"><div><i class="sci">${s.scientific_name}</i>${s.common_name ? html` <span>${s.common_name}</span>` : ''}
      ${s.probability != null ? html`<b class="id-p">${pct(s.probability)}</b>` : ''}</div>
    <div class="muted">${[s.family, s.order].filter(Boolean).join(', ')}</div>
    ${s.why ? html`<div>${s.why}</div>` : ''}
    ${tags.length ? html`<div class="id-tags">${tags}</div>` : ''}
    ${o.pick != null ? html`<label class="chk"><input type="radio" name="sevsp${o.pick}" data-f="sevpick" data-g="${o.pick}" value="${i}" ${o.picked === i ? raw('checked') : ''}>Use this name</label>` : ''}
    <div class="id-acts">${spLinks(s)}${withAdd ? s.kingdom === 'Fungi' ? html`<button class="btn small" type="button" data-act="idfind" data-src="${src}" data-i="${i}">Record a mushroom find</button>`
      : html`<button class="btn small" type="button" data-act="idnew" data-src="${src}" data-i="${i}">Add as a new plant</button>` : ''}
      ${o.use ? html`<button class="btn small" type="button" data-act="${o.use}" data-i="${i}">Use this name</button>` : ''}
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
    <p class="hint">Checked in ${r.seconds} seconds by ${r.model} on this computer${r.prior ? ', weighted toward the plants you have, houseplants and the plants of your state' : ''}.</p>`);
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
  return html`<div class="nophoto ${cls}" data-ph="${s.scientific_name}">${ph === null ? 'No photo found' : LIB.photos.__off ? 'Photos are off' : 'Finding a photo…'}</div>`;
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
    box.innerHTML = rend(html`<div class="grid lib-grid">${LIB.res.map(libCard)}</div>`);
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
  if (!r.online) document.querySelectorAll('#lib-res [data-ph]').forEach(el => { el.textContent = 'Photos are off'; });
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
      ${sh.zone_low ? html`<dt>Hardiness</dt><dd>USDA zones ${sh.zone_low} to ${sh.zone_high || '?'}${sh.min_temp_f != null ? `; survives down to about ${sh.min_temp_f}°F` : ''}. Yours is ${d.zone}.</dd>` : ''}</dl>
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

// ---------- 1.22.0: the wishlist (#/wishlist) ----------
let WL = [];
async function viewWishlist() {
  const wl = await api('GET', '/api/wishlist');
  WL = wl.wishlist.filter(w => (w.kind || 'plant') === 'plant');        // 1.30.0: supplies are on Shopping only
  const want = WL.filter(w => w.status === 'want'), got = WL.filter(w => w.status === 'got');
  const money = n => n == null ? '' : '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const item = (w, i) => html`<li class="wl-item"><h3><a href="${spHref(w.name)}">${w.common_name || w.name}</a></h3>
    ${w.common_name ? html`<p class="latin">${w.name}</p>` : ''}
    ${w.yours && w.yours.length ? html`<p><span class="tag tag-yours">You have it: ${w.yours.join(', ')}</span></p>` : ''}
    ${w.status === 'want' ? html`<div class="wl-price">
      ${w.offers && w.offers.best ? html`<p><strong>Cheapest now:</strong> ${money(w.offers.best.price)} at ${w.offers.best.shop_name}: <a href="${w.offers.best.url}" target="_blank" rel="noopener noreferrer">${w.offers.best.title}</a></p>` : ''}
      <p>${w.offers && w.offers.count ? `In stock at ${w.offers.shops} shop${w.offers.shops === 1 ? '' : 's'} (${w.offers.count} listing${w.offers.count === 1 ? '' : 's'}).` : wl.checked ? 'Not found at the shops checked.' : 'The shops have not been checked yet.'}
        <strong>Alerts:</strong> ${[w.max_price != null ? `${money(w.max_price)} or less` : '', w.alert_stock ? 'when it is in stock' : ''].filter(Boolean).join('; ') || 'none set (Edit to add one)'}.</p>
      <p class="hint">Searching for: ${(w.terms || []).join('; ') || 'nothing (Edit to add search words)'}.</p>
      <details class="wl-offers" data-wish="${w.name}"><summary>Every listing found, with past prices</summary><div class="wl-offers-box"><p class="loading">Loading</p></div></details></div>` : ''}
    ${w.where_seen ? html`<p><strong>Where to find it:</strong> ${w.where_seen}</p>` : ''}
    ${w.notes ? html`<p class="pl">${w.notes}</p>` : ''}
    <p class="hint">Added by ${w.added_by} on ${when(w.added_at)}.</p>
    <div class="row wl-acts"><button class="btn small" type="button" data-act="wlgot" data-i="${i}">${w.status === 'got' ? 'Move back to wanted' : 'Got it'}</button>
      <button class="btn ghost small" type="button" data-act="wledit" data-name="${w.name}">Edit, and set alerts</button>
      <button class="btn danger small" type="button" data-act="wlrm" data-i="${i}">Take it off the list</button></div></li>`;
  const al = (wl.alerts || []).filter(a => WL.some(w => w.name === a.wish));
  return {
    title: 'Wishlist',
    html: html`<p class="crumb"><a href="#/library">Back to the library</a></p><h1>Wishlist</h1>
    <p>Plants (or fungi) you would like to have or find. Add one from its page in the <a href="#/library">library</a>. Everyone you have given access to the app sees this list.</p>
    <p class="notice" role="note">The stores, prices and alerts are on <a href="#/shopping">Shopping</a>${al.length ? html`, with <strong>${al.length} alert${al.length === 1 ? '' : 's'}</strong> waiting` : ''}. ${wl.checked ? `The stores were last checked ${when(wl.checked)}.` : ''}</p>
    <h2>Wanted (${want.length})</h2>${want.length ? html`<ul class="wl-list">${want.map(w => item(w, WL.indexOf(w)))}</ul>` : html`<p class="muted">Nothing wanted yet. Open a species in the library and press "Add to my wishlist".</p>`}
    ${got.length ? html`<h2>Got them (${got.length})</h2><ul class="wl-list">${got.map(w => item(w, WL.indexOf(w)))}</ul>` : ''}`,
  };
}
let WLSHOPS = null, WLBADGE = 0;
async function wlBadge() {           // 1.27.0: the number of wishlist alerts beside Library in the top bar (checked at most once a minute)
  if (Date.now() - WLBADGE < 60000) return;
  WLBADGE = Date.now();
  let n = 0; try { n = (await api('GET', '/api/wishlist/alerts')).alerts.length; } catch (e) { return; }
  const a = document.querySelector('#main-nav a[data-sec=discover]'), w = document.querySelector('#sub-nav a[data-nav=shopping]');
  if (w) { let bw = w.querySelector('.nav-badge'); if (!n) { if (bw) bw.remove(); } else { if (!bw) { bw = document.createElement('span'); bw.className = 'nav-badge'; w.append(bw); } bw.innerHTML = rend(html` <span aria-hidden="true">(${n})</span><span class="sr">, ${n} shopping alert${n === 1 ? '' : 's'}</span>`); } }
  if (!a) return;
  let b = a.querySelector('.nav-badge');
  if (!n) { if (b) b.remove(); return; }
  if (!b) { b = document.createElement('span'); b.className = 'nav-badge'; a.append(b); }
  b.innerHTML = rend(html` <span aria-hidden="true">(${n})</span><span class="sr">, ${n} shopping alert${n === 1 ? '' : 's'}</span>`);
}
function wlAlertsHtml(al, today) {
  return html`<ul class="wl-alert-list">${al.map(a => html`<li><span class="tag ${a.kind === 'price' ? 'tag-yours' : ''}">${a.kind === 'price' ? 'Price' : 'In stock'}</span>
      ${a.url ? html`<a href="${a.url}" target="_blank" rel="noopener noreferrer">${a.text}</a>` : a.text} <small class="muted">${when(a.created_at)}</small>
      <button class="btn ghost small" type="button" data-act="wldismiss" data-id="${a.id}">Dismiss</button></li>`)}</ul>
    <div class="row">${al.length > 1 ? html`<button class="btn ghost small" type="button" data-act="wldismiss" data-id="all">Dismiss them all</button>` : ''}${today ? html`<a class="btn ghost small" href="#/shopping">Open Shopping</a>` : ''}</div>`;
}
async function wlPoll() {
  const msg = () => document.getElementById('wl-check-msg');
  for (let n = 0; n < 900 && msg(); n++) {
    let r; try { r = await api('GET', '/api/wishlist/check'); } catch (e) { return; }
    if (!r.busy) { if (msg()) { toast('Shops checked'); WLBADGE = 0; await route(); } return; }
    if (msg()) msg().textContent = `Checking ${r.now || 'the shops'} (${r.done + 1} of ${r.total})…`;
    await new Promise(res => setTimeout(res, 2000));
  }
}
document.addEventListener('toggle', async e => {         // the listings for one entry, loaded when opened
  const d = e.target; if (!d.matches || !d.matches('details.wl-offers') || !d.open || d.dataset.loaded) return;
  d.dataset.loaded = '1';
  const box = d.querySelector('.wl-offers-box');
  try {
    const r = await api('GET', '/api/wishlist/offers?name=' + enc(d.dataset.wish));
    const money = n => n == null ? 'no price shown' : '$' + Number(n).toFixed(2);
    box.innerHTML = rend(r.offers.length ? html`<ul class="wl-offer-list">${r.offers.map(o => html`<li class="${o.gone ? 'muted' : ''}">
        <strong>${money(o.price)}</strong>${o.unit ? html` (${'$' + Number(o.unit.per).toFixed(2)} a ${o.unit.unit})` : ''} at <a href="#/store/${enc(o.shop)}">${o.shop_name}</a>: <a href="${o.url}" target="_blank" rel="noopener noreferrer">${o.title}</a>
        ${o.gone ? html` <span class="tag">No longer listed</span>` : o.available ? '' : html` <span class="tag">Out of stock</span>`}
        ${o.detail ? html`<br><small>${o.detail}</small>` : ''}
        ${o.history.length > 1 ? html`<br><small>Past: ${o.history.slice(-6).map(h => `${when(h.at)} ${h.available ? money(h.price) : 'gone or out of stock'}`).join('; ')}</small>` : ''}
        <br><small class="muted">First seen ${when(o.first_seen)}, last seen ${when(o.last_seen)}</small></li>`)}</ul>` : html`<p class="muted">Nothing found yet.</p>`);
  } catch (err) { box.innerHTML = rend(html`<p class="muted">${err.message}</p>`); }
}, true);
Object.assign(acts, {
  async wlcheck(el) {
    if (!(await needName())) return;
    el.disabled = true;
    await guard(async () => { await api('POST', '/api/wishlist/check'); wlPoll(); });
  },
  async wldismiss(el) {
    if (!(await needName())) return;
    await guard(async () => { await api('POST', '/api/wishlist/alerts', el.dataset.id === 'all' ? { all: true } : { id: +el.dataset.id }); toast('Dismissed'); WLBADGE = 0; await route(); });
  },
  async shopedit(el) {
    const s = WLSHOPS && WLSHOPS.shops.find(x => x.key === el.dataset.key); if (!s) return;
    const r = await modal(html`<form method="dialog"><h2>${s.name}</h2>
      <label class="f">Web address<input type="url" name="url" maxlength="300" value="${s.url}"></label>
      <label class="f">More pages to read<small>For a shop without an online store: the pages that list its plants, one per line</small><textarea name="pages" rows="5">${s.pages.join('\n')}</textarea></label>
      <div class="row"><button class="btn" value="ok">Save changes</button><button class="btn ghost" value="cancel">Cancel</button></div></form>`);
    if (r !== 'ok') return;
    await guard(async () => { await api('PUT', '/api/shops', { key: s.key, url: dlg.querySelector('[name=url]').value, pages: dlg.querySelector('[name=pages]').value }); toast('Saved'); await route(); });
  },
  async shoprm(el) {
    const s = WLSHOPS && WLSHOPS.shops.find(x => x.key === el.dataset.key); if (!s) return;
    if (!(await confirmBox('Remove this shop?', `${s.name} is no longer checked, and what it had is forgotten.`, 'Remove the shop', true))) return;
    await guard(async () => { await api('DELETE', '/api/shops?key=' + enc(s.key)); toast('Removed'); await route(); });
  },
  async shopkeyrm(el) {
    if (!(await confirmBox('Remove the key?', `${el.dataset.shop === 'ebay' ? 'eBay' : 'Etsy'} is not searched again until a key is saved.`, 'Remove it', true))) return;
    await guard(async () => { await api('DELETE', '/api/shops/keys', { shop: el.dataset.shop }); toast('Removed'); await route(); });
  },
});
Object.assign(changeActs, {
  async shopon(el) { await guard(async () => { await api('PUT', '/api/shops', { key: el.dataset.key, enabled: el.checked }); toast(el.checked ? 'Turned on' : 'Turned off'); }); },
  async shophours(el) { await guard(async () => { await api('PUT', '/api/shops', { hours: el.value }); toast('Saved'); }); },
});
Object.assign(formActs, {
  async shopadd(form) {
    const e = form.elements;
    await api('POST', '/api/shops', { name: e.name.value, url: e.url.value, local: e.local.checked, online: e.online ? e.online.checked : false,
      home_id: e.home_id ? e.home_id.value : '', phone: e.phone ? e.phone.value : '', address: e.address ? e.address.value : '' });
    toast('Store added. It is read on the next check.'); route();
  },
  async shopkeys(form) {
    const b = { shop: form.dataset.shop }; [...form.elements].forEach(x => { if (x.name) b[x.name] = x.value.trim(); });
    await api('PUT', '/api/shops/keys', b); toast('Saved'); route();
  },
});
Object.assign(acts, {
  async wlgot(el) {
    const w = WL[+el.dataset.i]; if (!w || !(await needName())) return;
    await guard(async () => { await api('PUT', '/api/wishlist', { name: w.name, status: w.status === 'got' ? 'want' : 'got' }); toast(w.status === 'got' ? 'Moved back to wanted' : 'Marked as got it'); await route(); });
  },
  async wlrm(el) {
    const w = WL[+el.dataset.i]; if (!w || !(await needName())) return;
    if (!(await confirmBox('Take it off the wishlist?', `${w.common_name || w.name} and its notes leave the list.`, 'Take it off the list', true))) return;
    await guard(async () => { await api('DELETE', '/api/wishlist', { name: w.name }); toast('Taken off the wishlist'); await route(); });
  },
  async wledit(el) {
    if (!(await needName())) return;
    const all = (await api('GET', '/api/wishlist')).wishlist, w = all.find(x => x.name === el.dataset.name); if (!w) return;
    const r = await modal(html`<form method="dialog"><h2>Edit: ${w.common_name || w.name}</h2>
      <label class="f">Where to find it<small>A nursery, a website, a friend's garden</small><input type="text" name="where" maxlength="300" value="${w.where_seen}"></label>
      <label class="f">Notes<textarea name="notes" rows="4" maxlength="2000">${w.notes}</textarea></label>
      <label class="f">Status<select name="status"><option value="want" ${w.status === 'want' ? raw('selected') : ''}>Wanted</option><option value="got" ${w.status === 'got' ? raw('selected') : ''}>Got it</option></select></label>
      <fieldset class="opt-group"><legend>Shops and alerts</legend>
        <label class="f">Search the shops for<small>One search per line, such as a variety: Monstera Thai Constellation. Left empty, its common and scientific names are used.</small><textarea name="search" rows="2" maxlength="300">${w.search_words || ''}</textarea></label>
        <label class="f">Alert me when the price is at or under<small>In dollars, such as 25. Shipping is not included. Leave empty for no price alert.</small><input type="number" name="max_price" min="0.01" step="0.01" inputmode="decimal" value="${w.max_price == null ? '' : w.max_price}"></label>
        <label class="chk"><input type="checkbox" name="alert_stock" ${w.alert_stock ? raw('checked') : ''}> Alert me when a shop has it in stock</label></fieldset>
      <div class="row"><button class="btn" value="ok">Save changes</button><button class="btn ghost" value="cancel">Cancel</button></div></form>`);
    if (r !== 'ok') return;
    const q = n => dlg.querySelector(`[name=${n}]`);
    await guard(async () => { await api('PUT', '/api/wishlist', { name: w.name, where_seen: q('where').value, notes: q('notes').value, status: q('status').value,
      search_words: q('search').value, max_price: q('max_price').value, alert_stock: q('alert_stock').checked }); toast('Saved'); await route(); });
  },
});
// ---------- 1.30.0: Shopping: wishlist plants and garden supplies, the stores, and each store's details ----------
let SHOPF = { near: 'all', kind: 'all' };
try { const s = JSON.parse(localStorage.getItem('plantdb.shopping') || '{}'); if (s && typeof s.near === 'string') SHOPF.near = s.near; if (s && typeof s.kind === 'string') SHOPF.kind = s.kind; } catch (e) { /* defaults */ }
const shopSave = () => { try { localStorage.setItem('plantdb.shopping', JSON.stringify(SHOPF)); } catch (e) { /* this visit only */ } };
let SHOPD = null;                    // the last answer from /api/shopping
const money2 = n => (n == null ? '' : '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
const unitMoney = u => (u ? `${money2(u.per)} a ${u.unit}` : '');
const telHref = p => 'tel:' + String(p).replace(/[^\d+]/g, '');
function phoneLinks(text) {           // "(530) 272-4769; toll-free (888) 784-1722": each number is a link you can tap to call
  const t = String(text || ''), re = /\+?1?[\s.-]?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}/g, out = []; let last = 0, m;
  while ((m = re.exec(t))) { const lead = m[0].match(/^\s*/)[0]; out.push(t.slice(last, m.index) + lead); out.push(html`<a href="${telHref(m[0])}">${m[0].trim()}</a>`); last = m.index + m[0].length; }
  if (last < t.length) out.push(t.slice(last));
  return out;
}
const kindWord = k => ((SHOPD && SHOPD.kinds.find(x => x.key === k)) || {}).label || k;
const kindUnit = k => ((SHOPD && SHOPD.kinds.find(x => x.key === k)) || {}).unit || '';
function buySource(w) {
  const s = w.source || '';
  if (s.startsWith('pots:')) return html`<p class="hint">From <a href="#/pots">Pots and trays</a>.</p>`;
  if (s.startsWith('fert:')) return html`<p class="hint">From the <a href="#/fertilizer">Fertilizer</a> page: the N-P-K ratio ${s.slice(5)}.</p>`;
  if (s === 'frost') return html`<p class="hint">From the <a href="#/frost">cold-night checklist</a>.</p>`;
  return '';
}
function buyCard(w) {
  const o = w.offers || {}, b = o.best, can = canChange(), plant = w.kind === 'plant';
  const visit = (SHOPD.visit || []).filter(s => (s.carries || []).includes(w.kind));
  return html`<li class="wl-item buy-item" id="buy-${enc(w.name)}"><p><span class="tag">${kindWord(w.kind)}</span>${w.status === 'got' ? html` <span class="tag tag-yours">Got it</span>` : ''}</p>
    <h3>${plant ? html`<a href="${spHref(w.name)}">${w.common_name || w.name}</a>` : w.name}</h3>${plant && w.common_name ? html`<p class="latin">${w.name}</p>` : ''}
    ${buySource(w)}
    ${w.status === 'want' ? html`<div class="wl-price">
      ${b ? html`<p><strong>Cheapest now:</strong> ${money2(b.price)}${b.unit && b.unit.unit !== 'each' ? html` for ${b.unit.size} (<strong>${unitMoney(b.unit)}</strong>)` : b.unit ? html` (${unitMoney(b.unit)})` : ''} at <a href="#/store/${enc(b.shop)}">${b.shop_name}</a>: <a href="${b.url}" target="_blank" rel="noopener noreferrer">${b.title}</a></p>` : ''}
      <p>${o.count ? `In stock at ${o.shops} store${o.shops === 1 ? '' : 's'} (${o.count} listing${o.count === 1 ? '' : 's'}).` : SHOPD.checked ? 'Not found at the stores checked.' : 'The stores have not been checked yet.'}
        <strong>Alerts:</strong> ${[w.max_price != null ? `${money2(w.max_price)}${w.price_per === 'unit' ? ' a ' + kindUnit(w.kind) : ''} or less` : '', w.alert_stock ? 'when it is in stock' : ''].filter(Boolean).join('; ') || 'none set (Edit to add one)'}.</p>
      <p class="hint">Searching for: ${(w.terms || []).join('; ') || 'nothing (Edit to add search words)'}.</p>
      <details class="wl-offers" data-wish="${w.name}"><summary>Every listing found, with past prices</summary><div class="wl-offers-box"><p class="loading">Loading</p></div></details></div>` : ''}
    ${w.status === 'want' && visit.length ? html`<details class="buy-visit"><summary>Stores near you that carry ${kindWord(w.kind).toLowerCase()} (${visit.length})</summary><ul>${visit.map(s => html`<li><a href="#/store/${enc(s.key)}">${s.name}</a>${s.phone ? html`: ${phoneLinks(s.phone)}` : ''}${s.miles != null ? html` <small class="muted">about ${fmt(s.miles, 0)} miles</small>` : ''}</li>`)}</ul></details>` : ''}
    ${w.where_seen ? html`<p><strong>Where to find it:</strong> ${w.where_seen}</p>` : ''}
    ${w.notes ? html`<p class="pl">${w.notes}</p>` : ''}
    ${can ? html`<div class="row wl-acts"><button class="btn small" type="button" data-act="buygot" data-name="${w.name}">${w.status === 'got' ? 'Move back to watching' : 'Got it'}</button>
      <button class="btn ghost small" type="button" data-act="buyedit" data-name="${w.name}">Edit, and set alerts</button>
      <button class="btn danger small" type="button" data-act="buyrm" data-name="${w.name}">Stop watching</button></div>` : ''}</li>`;
}
async function viewShopping() {
  const d = SHOPD = await api('GET', '/api/shopping?near=' + enc(SHOPF.near));
  if (SHOPF.near !== 'all' && !d.homes.some(h => String(h.id) === SHOPF.near)) SHOPF.near = 'all';
  const want = d.items.filter(w => w.status === 'want'), got = d.items.filter(w => w.status === 'got');
  const count = k => want.filter(w => k === 'all' || w.kind === k).length;
  const show = want.filter(w => SHOPF.kind === 'all' || w.kind === SHOPF.kind), shownGot = got.filter(w => SHOPF.kind === 'all' || w.kind === SHOPF.kind);
  const opts = [['all', 'All']].concat(d.kinds.map(k => [k.key, k.label]));
  const al = d.alerts || [];
  return {
    title: 'Shopping',
    after: () => { if (d.busy) wlPoll(); },
    html: html`<h1>Shopping</h1>
    <p>Plants from your <a href="#/wishlist">wishlist</a> and garden supplies you are watching for. The stores are checked ${d.hours !== '0' ? `every ${d.hours} hours` : 'only when you ask'}, with alerts here and on the Today page.</p>
    ${al.length ? html`<section class="blk wl-alerts" aria-labelledby="wl-al-h"><h2 id="wl-al-h">Alerts (${al.length})</h2>${wlAlertsHtml(al)}</section>` : ''}
    <div class="filters buy-top"><label class="f">Stores near<select data-act="shopnear"><option value="all" ${SHOPF.near === 'all' ? raw('selected') : ''}>Both homes${d.homes.length > 2 ? ' (all)' : ''}</option>
        ${d.homes.map(h => html`<option value="${h.id}" ${String(h.id) === SHOPF.near ? raw('selected') : ''}>${h.name}</option>`)}</select></label>
      <div class="row wl-check">${canChange() ? html`<button class="btn" type="button" data-act="wlcheck" ${want.length ? '' : raw('disabled')}>Check the stores now</button>` : ''}
        <span id="wl-check-msg" role="status" aria-live="polite">${d.checked ? `Last checked ${when(d.checked)}.` : 'Not checked yet.'}</span></div></div>
    <fieldset class="buy-kinds-r"><legend>Show</legend><div class="opts">${opts.map(([k, l]) => html`<label><input type="radio" name="buykind" data-act="shopkind" value="${k}" ${SHOPF.kind === k ? raw('checked') : ''}><span>${l} (${count(k)})</span></label>`)}</div></fieldset>
    <label class="f buy-kinds-s">Show<select data-act="shopkind">${opts.map(([k, l]) => html`<option value="${k}" ${SHOPF.kind === k ? raw('selected') : ''}>${l} (${count(k)})</option>`)}</select></label>
    <div class="row">${canChange() ? html`<button class="btn" type="button" data-act="buynew">Add something to watch</button>` : ''}<a class="btn ghost" href="#/shopping/list">Shopping list for a store visit</a><a class="btn ghost" href="#/shopping/stores">Stores (${d.stores})</a></div>
    <h2>Watching (${show.length})</h2>
    ${show.length ? html`<ul class="wl-list">${show.map(buyCard)}</ul>` : html`<p class="muted">${want.length ? 'Nothing of this kind yet.' : 'Nothing yet.'} ${canChange() ? 'Press "Add something to watch", or add a plant from its page in the library.' : ''}</p>`}
    ${shownGot.length ? html`<details class="blk"><summary><h2 class="sum-h">Got them (${shownGot.length})</h2></summary><ul class="wl-list">${shownGot.map(buyCard)}</ul></details>` : ''}`,
  };
}
// ---------- 1.34.0: the shopping list for a store visit ----------
// What to look for on a visit, from everything on Shopping. Ticks are kept on this device until "Done shopping"; the extra
// items (things not on Shopping) follow your sign-in like the other settings (plantdb.shoplist in prefs.js).
const SL = { store: null, big: false, ticks: {}, extra: [] };     // store null: not chosen yet, so the first store you can visit
function slLoad() {
  try { const x = JSON.parse(localStorage.getItem('plantdb.shoplist') || '{}'); if (Array.isArray(x.extra)) SL.extra = x.extra.filter(t => typeof t === 'string').slice(0, 60); if (typeof x.store === 'string') SL.store = x.store; } catch (e) { /* defaults */ }
  try { const t = JSON.parse(sessionStorage.getItem('plantdb.shopticks') || '{}'); if (t && typeof t === 'object') SL.ticks = t; } catch (e) { /* none */ }
}
function slSave() {
  try { localStorage.setItem('plantdb.shoplist', JSON.stringify({ extra: SL.extra, store: SL.store })); } catch (e) { /* this visit only */ }
  try { sessionStorage.setItem('plantdb.shopticks', JSON.stringify(SL.ticks)); } catch (e) { /* not kept */ }
}
slLoad();
function slCarries(store, w) {           // the store carries this kind, or a listing of it was found there
  const o = w.offers || {};
  return (store.carries || []).includes(w.kind) || (o.best && o.best.shop === store.key);
}
function slWhy(w) {
  const o = w.offers || {}, b = o.best, bits = [];
  if (w.max_price != null) bits.push(`Watching for ${money2(w.max_price)}${w.price_per === 'unit' ? ' a ' + kindUnit(w.kind) : ''} or less.`);
  if (b) bits.push(`Online it is ${money2(b.price)}${b.unit && b.unit.unit !== 'each' ? ` for ${b.unit.size} (${unitMoney(b.unit)})` : ''} at ${b.shop_name}.`);
  if (w.source) bits.push(w.source);
  if (w.where_seen) bits.push(`Where to find it: ${w.where_seen}.`);
  if (w.notes) bits.push(w.notes);
  return bits.join(' ');
}
async function viewShopList() {
  const d = SHOPD = await api('GET', '/api/shopping?near=all');
  const want = d.items.filter(w => w.status === 'want');
  const stores = (d.visit || []).map(s => ({ ...s, n: want.filter(w => slCarries(s, w)).length }));
  const homes = d.homes || [];
  const opts = [...stores.map(s => [s.key, `${s.name} (carries ${s.n} of these)`]), ...homes.map(h => ['home:' + h.id, `Any store near ${h.name}`]), ['', 'Everything you are watching']];
  if (SL.store == null || !opts.some(o => o[0] === SL.store)) SL.store = stores.length ? stores[0].key : '';
  const store = stores.find(s => s.key === SL.store) || null, homeId = SL.store.startsWith('home:') ? SL.store.slice(5) : '';
  const carried = store ? want.filter(w => slCarries(store, w)) : want, missing = store ? want.filter(w => !slCarries(store, w)) : [];
  const nearStores = homeId ? stores.filter(s => String(s.home_id_eff) === homeId) : [];
  const ticked = k => !!SL.ticks[k];
  const item = w => html`<li><label class="chk"><input type="checkbox" data-act="sltick" data-k="${w.name}" ${ticked(w.name) ? raw('checked') : ''}> <span class="sl-txt"><strong>${w.common_name || w.name}</strong> <span class="tag">${kindWord(w.kind)}</span>${w.kind === 'plant' && w.common_name ? html` <span class="latin">${w.name}</span>` : ''}
    ${slWhy(w) ? html`<br><span class="muted">${slWhy(w)}</span>` : ''}</span></label></li>`;
  const nTick = Object.keys(SL.ticks).filter(ticked).length;
  return {
    title: 'Shopping list',
    html: html`<p class="crumb noprint"><a href="#/shopping">Back to Shopping</a></p><h1>Shopping list${store ? html`: ${store.name}` : homeId ? html`: near ${(homes.find(h => String(h.id) === homeId) || {}).name || ''}` : ''}</h1>
    <p class="noprint">What to look for on a visit, from everything you are watching on Shopping. Tick what you bought; "Done shopping" then marks the ticked ones as <strong>got it</strong>. Print it, or show it large for the store.</p>
    <div class="filters noprint"><label class="f">Store<select data-act="slstore">${opts.map(([v, t]) => html`<option value="${v}" ${v === SL.store ? raw('selected') : ''}>${t}</option>`)}</select></label>
      <div class="row" style="align-items:end"><button class="btn ghost" type="button" data-act="slbig" aria-pressed="${SL.big ? 'true' : 'false'}">${SL.big ? 'Normal print' : 'Large print'}</button><button class="btn ghost" type="button" data-act="print">Print</button></div></div>
    <section class="blk sl-list ${SL.big ? 'sl-big' : ''}" id="sl-main">
      ${store ? html`<h2>${store.name}</h2><p>${store.address || ''}${store.address && store.phone ? ' · ' : ''}${store.phone ? phoneLinks(store.phone) : ''}${store.hours ? html` · ${store.hours}` : ''}${store.maps ? html` <a class="noprint" href="${store.maps}" target="_blank" rel="noopener noreferrer">Open in a map</a>` : ''}</p>`
        : homeId ? html`<h2>Stores near ${(homes.find(h => String(h.id) === homeId) || {}).name || ''}</h2>${nearStores.length ? html`<ul class="sl-stores">${nearStores.map(s => html`<li><strong>${s.name}</strong>${s.n ? ` carries ${s.n} of these` : ''}${s.address ? html`<br>${s.address}` : ''}${s.phone ? html` · ${phoneLinks(s.phone)}` : ''}${s.hours ? html` · ${s.hours}` : ''}</li>`)}</ul>` : html`<p class="muted">No stores you can visit are set near here yet (Shopping → Stores).</p>`}`
        : html`<h2>Everything you are watching</h2>`}
      ${carried.length ? html`<ul class="tick-list">${carried.map(item)}</ul>` : html`<p class="muted">Nothing on Shopping ${store ? 'that this store carries, as far as the app knows' : 'yet'}.</p>`}
      ${missing.length ? html`<h3>Not carried here, as far as the app knows (${missing.length})</h3><p class="hint noprint">Ask at the store, or set what it carries on its page under Shopping → Stores.</p><ul class="tick-list">${missing.map(item)}</ul>` : ''}
      <h3>Anything else</h3>
      <form class="row noprint" data-form="sladd"><label class="f" style="flex:1 1 16rem">Add to the list<small>Things not on Shopping: twine, a new trowel</small><input type="text" name="text" maxlength="80" autocomplete="off"></label><button class="btn ghost" type="submit" style="align-self:end">Add</button></form>
      ${SL.extra.length ? html`<ul class="tick-list">${SL.extra.map(t => html`<li><label class="chk"><input type="checkbox" data-act="sltick" data-k="${'extra:' + t}" ${ticked('extra:' + t) ? raw('checked') : ''}> <span class="sl-txt"><strong>${t}</strong></span></label> <button class="btn small ghost noprint" type="button" data-act="slrm" data-t="${t}" aria-label="Remove ${t} from the list">Remove</button></li>`)}</ul>` : html`<p class="muted noprint">Nothing extra yet.</p>`}
      <div class="row noprint"><button class="btn" type="button" data-act="sldone" ${nTick ? '' : raw('disabled')}>Done shopping: mark the ${nTick} ticked as got</button>${nTick ? html`<button class="btn ghost" type="button" data-act="slclear">Clear the ticks</button>` : ''}</div></section>`,
  };
}
function storeRows(list, cols) {
  const how = s => s.kind === 'api' ? 'Searches its listings' : s.platform === 'shopify' || s.platform === 'woo' ? 'Reads its online store' : s.platform === 'page' || s.kind === 'page' ? 'Call or visit: its pages are read for the names you watch' : 'Finds out on the first check';
  const owner = ME().role === 'owner';
  return html`<div class="tbl-wrap"><table class="tbl wl-shops"><thead><tr><th scope="col">Store</th><th scope="col">Carries</th><th scope="col">How it is checked</th>${cols.phone ? html`<th scope="col">Phone</th>` : ''}<th scope="col">Last check</th>${owner ? html`<th scope="col">Check it</th>` : ''}</tr></thead><tbody>
    ${list.map(s => html`<tr><th scope="row"><a href="#/store/${enc(s.key)}">${s.name}</a>${s.miles != null ? html`<br><small class="muted">about ${fmt(s.miles, 0)} miles</small>` : ''}</th>
      <td>${s.carries.length ? s.carries.map(k => kindWord(k)).join(', ') : html`<span class="muted">Not set</span>`}</td><td>${how(s)}</td>
      ${cols.phone ? html`<td>${s.phone ? phoneLinks(s.phone) : html`<span class="muted">Not known</span>`}</td>` : ''}
      <td>${s.error ? html`<span class="bad-text">⚠ ${s.status}</span>` : s.status || (s.enabled ? 'Not checked yet' : 'Off')}${s.checked_at ? html`<br><small class="muted">${when(s.checked_at)}</small>` : ''}</td>
      ${owner ? html`<td><label class="chk"><input type="checkbox" data-act="shopon" data-key="${s.key}" ${s.enabled ? raw('checked') : ''}> On</label>
        ${s.kind !== 'api' ? html`<button class="btn ghost small" type="button" data-act="shopedit" data-key="${s.key}">Change address</button>` : ''}
        ${s.custom ? html`<button class="btn danger small" type="button" data-act="shoprm" data-key="${s.key}" aria-label="Remove the store ${s.name}">Remove</button>` : ''}</td>` : ''}</tr>`)}
  </tbody></table></div>`;
}
let STF = { show: 'all', carries: '' };
async function viewStores() {
  const sh = WLSHOPS = await api('GET', '/api/shops');
  if (!SHOPD) SHOPD = { kinds: sh.kinds, visit: [] };
  const owner = ME().role === 'owner';
  const keep = s => !STF.carries || s.carries.includes(STF.carries);
  const groups = sh.homes.map(h => [h, sh.shops.filter(s => s.local && s.home_id_eff === h.id && keep(s))]);
  const online = sh.shops.filter(s => !s.local && keep(s)), alsoOnline = sh.shops.filter(s => s.local && s.online && keep(s));
  const showHome = h => STF.show === 'all' || STF.show === String(h.id), showOnline = STF.show === 'all' || STF.show === 'online';
  return {
    title: 'Stores',
    html: html`<p class="crumb"><a href="#/shopping">Back to Shopping</a></p><h1>Stores</h1>
    <p>Every store Shopping checks or lists. Choose one for its address, phone number, hours and listings. Stores you can visit are read for the names you watch; call them to be sure.</p>
    <div class="filters"><label class="f">Show<select data-act="storeshow"><option value="all">${sh.homes.length > 1 ? 'Every home, and online' : 'Near home, and online'}</option>
        ${sh.homes.map(h => html`<option value="${h.id}" ${STF.show === String(h.id) ? raw('selected') : ''}>Near ${h.name}</option>`)}<option value="online" ${STF.show === 'online' ? raw('selected') : ''}>Online only</option></select></label>
      <label class="f">Carries<select data-act="storecarries"><option value="">Anything</option>${sh.kinds.map(k => html`<option value="${k.key}" ${STF.carries === k.key ? raw('selected') : ''}>${k.label}</option>`)}</select></label></div>
    ${groups.filter(([h]) => showHome(h)).map(([h, list]) => html`<section class="blk" aria-labelledby="st-h-${h.id}"><h2 id="st-h-${h.id}">Near ${h.name} (${list.length})</h2>
      ${list.length ? storeRows(list, { phone: true }) : html`<p class="muted">None yet.${owner ? ' Add one below.' : ''}</p>`}</section>`)}
    ${showOnline ? html`<section class="blk" aria-labelledby="st-h-on"><h2 id="st-h-on">Online (${online.length})</h2>${storeRows(online, { phone: false })}
      ${alsoOnline.length ? html`<p class="hint">Also selling online, and counted for every home: ${alsoOnline.map((s, i) => html`${i ? ', ' : ''}<a href="#/store/${enc(s.key)}">${s.name}</a>`)}.</p>` : ''}</section>` : ''}
    ${owner ? html`<section class="blk" aria-labelledby="st-own-h"><h2 id="st-own-h">Store settings</h2>
      <label class="f">Check the stores<select data-act="shophours">${[['6', 'Every 6 hours'], ['12', 'Every 12 hours (twice a day)'], ['24', 'Once a day'], ['48', 'Every 2 days'], ['0', 'Only when I press "Check the stores now"']].map(([v, t]) => html`<option value="${v}" ${sh.hours === v ? raw('selected') : ''}>${t}</option>`)}</select></label>
      <h3>Add a store</h3>
      <form data-form="shopadd" class="f-grid" autocomplete="off"><label class="f">Store name<input type="text" name="name" maxlength="80" required></label>
        <label class="f">Web address<small>Its home page, or the page that lists what it sells</small><input type="url" name="url" maxlength="300" placeholder="https://" required></label>
        <label class="chk"><input type="checkbox" name="local"> A store you can visit</label>
        <label class="f">Near<select name="home_id">${sh.homes.map(h => html`<option value="${h.id}">${h.name}</option>`)}</select></label>
        <label class="chk"><input type="checkbox" name="online"> It also sells online (counts for every home)</label>
        <label class="f">Phone<input type="tel" name="phone" maxlength="120"></label><label class="f">Address<input type="text" name="address" maxlength="200"></label>
        <div class="row"><button class="btn" type="submit">Add the store</button></div></form>
      <h3>eBay and Etsy keys</h3>
      <p class="hint">eBay and Etsy are searched through their official services, which need free keys. They are kept on this computer and never shown again.</p>
      <form data-form="shopkeys" data-shop="ebay" class="f-grid" autocomplete="off"><p><strong>eBay</strong>: ${sh.have_ebay ? 'saved.' : 'not set.'} Create a free account at <a href="https://developer.ebay.com/" target="_blank" rel="noopener noreferrer">developer.ebay.com</a>, make a "Production" keyset, and paste its App ID (Client ID) and Cert ID (Client Secret).</p>
        <label class="f">App ID<input type="password" name="ebay_app_id" autocomplete="off"></label><label class="f">Cert ID<input type="password" name="ebay_cert_id" autocomplete="off"></label>
        <div class="row"><button class="btn" type="submit">Save the eBay keys</button>${sh.have_ebay ? html`<button class="btn ghost" type="button" data-act="shopkeyrm" data-shop="ebay">Remove them</button>` : ''}</div></form>
      <form data-form="shopkeys" data-shop="etsy" autocomplete="off"><p><strong>Etsy</strong>: ${sh.have_etsy ? 'saved.' : 'not set.'} Register an app at <a href="https://www.etsy.com/developers/register" target="_blank" rel="noopener noreferrer">etsy.com/developers</a> and paste its key (keystring).</p>
        <label class="f">Etsy key<input type="password" name="etsy_key" autocomplete="off"></label>
        <div class="row"><button class="btn" type="submit">Save the Etsy key</button>${sh.have_etsy ? html`<button class="btn ghost" type="button" data-act="shopkeyrm" data-shop="etsy">Remove it</button>` : ''}</div></form></section>` : ''}`,
  };
}
let STORE = null;
async function viewStore(key) {
  const [s, sh] = await Promise.all([api('GET', '/api/shops/' + enc(key)), SHOPD ? Promise.resolve(null) : api('GET', '/api/shops')]);
  if (sh) SHOPD = { kinds: sh.kinds, visit: [] };
  STORE = s;
  const can = canChange(), owner = ME().role === 'owner', me = cleanName(viaTS() ? ME().name : getName());
  const how = s.kind === 'api' ? 'its listings are searched for what you watch' : s.platform === 'shopify' || s.platform === 'woo' ? 'its online store is read for names, prices and stock' : s.platform === 'page' || s.kind === 'page' ? 'its pages are read for the names you watch, with a price if the page shows one. Call to be sure' : 'found out on the first check';
  return {
    title: s.name,
    html: html`<p class="crumb"><a href="#/shopping/stores">Back to the stores</a></p><h1>${s.name}</h1>
    <p>${s.local ? html`<span class="tag">Near ${s.home_name}</span> <span class="tag">Store you can visit</span> ` : ''}${s.online || !s.local ? html`<span class="tag">Online store</span>` : ''}${s.enabled ? '' : html` <span class="tag">Not checked (turned off)</span>`}</p>
    <div class="set-grid">
    <section class="set-card blk" aria-labelledby="st-find"><h2 id="st-find">${s.local ? 'Find it' : 'Its details'}</h2>
      ${s.local ? html`<p><strong>Address:</strong> ${s.address || html`<span class="muted">not known yet</span>`}${s.maps ? html`<br><a href="${s.maps}" target="_blank" rel="noopener noreferrer">Open in a map</a>` : ''}${s.miles != null ? html` · about ${fmt(s.miles, 0)} miles from ${s.home_name}` : ''}</p>` : ''}
      <p><strong>Phone:</strong> ${s.phone ? phoneLinks(s.phone) : html`<span class="muted">not known yet</span>`}</p>
      ${s.local ? html`<p><strong>Hours:</strong> ${s.hours || html`<span class="muted">not known yet</span>`}</p>` : ''}
      ${s.email ? html`<p><strong>Email:</strong> <a href="mailto:${s.email}">${s.email}</a></p>` : ''}
      <p><strong>Website:</strong> <a href="${s.website || s.url}" target="_blank" rel="noopener noreferrer">${(s.website || s.url).replace(/^https?:\/\/(www\.)?/, '').replace(/\/$/, '')}</a></p>
      ${s.details_src ? html`<p class="hint">${s.details_src}${s.details_at && !/\d{4}/.test(s.details_src) ? `, ${when(s.details_at)}` : ''}.${s.local ? ' Hours and phone numbers change: call before a long drive.' : ''}</p>` : ''}
      ${can ? html`<div class="row"><button class="btn ghost small" type="button" data-act="storeedit">Edit details</button>${s.local ? html`<button class="btn ghost small" type="button" data-act="storelookup">Look them up on OpenStreetMap</button>` : ''}</div>
        <p id="st-look" role="status" aria-live="polite"></p>` : ''}</section>
    <section class="set-card blk" aria-labelledby="st-car"><h2 id="st-car">What it carries</h2>
      <p>${s.carries.length ? s.carries.map(k => html`<span class="tag">${kindWord(k)}</span> `) : html`<span class="muted">Not set yet.${can ? ' Choose Edit details to set it.' : ''}</span>`}</p>
      <p><strong>How it is checked:</strong> ${how}.</p>
      <p><strong>Last check:</strong> ${s.checked_at ? html`${when(s.checked_at)}. ${s.error ? html`<span class="bad-text">⚠ ${s.status}</span>` : s.status || ''}` : 'not checked yet.'}</p>
      ${owner ? html`<label class="chk"><input type="checkbox" data-act="shopon" data-key="${s.key}" ${s.enabled ? raw('checked') : ''}> Check this store</label>` : ''}</section>
    </div>
    <section class="blk" aria-labelledby="st-has"><h2 id="st-has">What you are watching that it has (${s.listings.length})</h2>
      ${s.listings.length ? html`<div class="tbl-wrap"><table class="tbl"><thead><tr><th scope="col">Watching</th><th scope="col">Listing</th><th scope="col">Price</th><th scope="col">Per unit</th><th scope="col">In stock</th></tr></thead><tbody>
        ${s.listings.map(o => html`<tr><th scope="row"><a href="#/shopping">${o.common_name || o.wish}</a></th><td><a href="${o.url}" target="_blank" rel="noopener noreferrer">${o.title}</a>${o.size ? html`<br><small class="muted">${o.size}</small>` : ''}</td>
          <td>${o.price == null ? html`<span class="muted">Not shown</span>` : money2(o.price)}${o.before ? html`<br><small class="muted">was ${money2(o.before.price)} on ${when(o.before.at)}</small>` : ''}</td>
          <td>${o.unit ? unitMoney(o.unit) : ''}</td><td>${o.available ? html`<span aria-hidden="true">✓</span> Yes` : html`<span aria-hidden="true">✗</span> Sold out`}</td></tr>`)}
      </tbody></table></div>` : html`<p class="muted">Nothing you are watching was found here at the last check.</p>`}</section>
    <section class="blk" aria-labelledby="st-notes"><h2 id="st-notes">What they had</h2>
      <p class="hint">For notes after you call or visit. Everyone who can open the plant record sees them.</p>
      ${s.notes.length ? html`<ul class="wl-alert-list">${s.notes.map(n => html`<li><strong>${midDay(n.created_at.slice(0, 10))}</strong>, ${n.created_by}: ${n.text}
        ${can && (owner || n.created_by === me) ? html` <button class="btn ghost small" type="button" data-act="storenoterm" data-id="${n.id}" aria-label="Remove this note">Remove</button>` : ''}</li>`)}</ul>` : html`<p class="muted">No notes yet.</p>`}
      ${can ? html`<form data-form="storenote" class="store-note"><label class="f">Add a note<textarea name="text" rows="2" maxlength="1000" required></textarea></label><div class="row"><button class="btn" type="submit">Save the note</button></div></form>` : ''}</section>`,
  };
}
function buyDialog(w) {                  // add or edit something on Shopping
  const kinds = SHOPD.kinds, isNew = !w, plant = w && w.kind === 'plant';
  w = w || { name: '', kind: SHOPF.kind !== 'all' && SHOPF.kind !== 'plant' ? SHOPF.kind : 'mix', search_words: '', max_price: null, price_per: '', alert_stock: 0, notes: '', where_seen: '', status: 'want' };
  const unitOf = k => (kinds.find(x => x.key === k) || {}).unit || '';
  return modal(html`<form method="dialog" class="buy-dlg"><h2>${isNew ? 'Add something to watch' : 'Edit: ' + (w.common_name || w.name)}</h2>
    ${plant ? html`<p>${w.common_name ? html`${w.common_name} (<i>${w.name}</i>)` : html`<i>${w.name}</i>`}, from your wishlist.</p>`
      : html`<label class="f">What it is<small>As you would say it, for example "Pumice, 1/4 in" or "8 in terracotta pot"</small><input type="text" name="name" maxlength="120" value="${w.name}" required></label>
        <label class="f">Kind<select name="kind">${kinds.filter(k => k.key !== 'plant').map(k => html`<option value="${k.key}" ${k.key === w.kind ? raw('selected') : ''}>${k.label}</option>`)}</select></label>`}
    <label class="f">Search the stores for<small>One search per line, for example "pumice" and "horticultural pumice". Left empty, its name is used.</small><textarea name="search" rows="2" maxlength="300">${w.search_words || ''}</textarea></label>
    <fieldset class="opt-group"><legend>Alerts</legend>
      <label class="f">Alert me when the price is at or under<small>In dollars, such as 25. Shipping is not included. Leave empty for no price alert.</small><input type="number" name="max_price" min="0.01" step="0.01" inputmode="decimal" value="${w.max_price == null ? '' : w.max_price}"></label>
      <div class="opts buy-per" data-unit-for="kind">${[['', 'For the whole listing'], ['unit', 'Per unit (a quart, a pound or a square foot)']].map(([v, l]) => html`<label><input type="radio" name="price_per" value="${v}" ${(w.price_per || '') === v ? raw('checked') : ''}><span>${l}</span></label>`)}</div>
      <p class="hint">Per unit works for potting mixes and amendments (a quart), fertilizers (a pound) and frost cloth (a square foot), when a listing says its size.</p>
      <label class="chk"><input type="checkbox" name="alert_stock" ${w.alert_stock ? raw('checked') : ''}> Alert me when a store has it in stock</label></fieldset>
    <label class="f">Where to find it<small>A store, a website, a friend</small><input type="text" name="where" maxlength="300" value="${w.where_seen || ''}"></label>
    <label class="f">Notes<textarea name="notes" rows="3" maxlength="2000">${w.notes || ''}</textarea></label>
    <div class="row"><button class="btn" value="ok">${isNew ? 'Start watching' : 'Save changes'}</button><button class="btn ghost" value="cancel">Cancel</button></div></form>`);
}
function buyBody(w) {
  const q = n => dlg.querySelector(`[name=${n}]`), per = dlg.querySelector('[name=price_per]:checked');
  const b = { search_words: q('search').value, max_price: q('max_price').value, alert_stock: q('alert_stock').checked, where_seen: q('where').value, notes: q('notes').value,
    price_per: per ? per.value : '' };
  if (!w || w.kind !== 'plant') { b.kind = q('kind').value; if (w && q('name').value.trim() !== w.name) b.rename = q('name').value.trim(); if (!w) b.name = q('name').value.trim(); }
  return b;
}
const buyItem = name => SHOPD && SHOPD.items.find(x => x.name === name);
Object.assign(acts, {
  async buynew() {
    if (!(await needName())) return;
    if ((await buyDialog(null)) !== 'ok') return;
    const b = buyBody(null);
    if (!b.name) { toast('Give it a name first', true); return; }
    if (buyItem(b.name)) { toast(`"${b.name}" is already on Shopping`, true); return; }
    await guard(async () => { await api('PUT', '/api/wishlist', b); toast('Watching ' + b.name); SHOPF.kind = 'all'; shopSave(); await route(); });
  },
  async buyedit(el) {
    const w = buyItem(el.dataset.name); if (!w || !(await needName())) return;
    if ((await buyDialog(w)) !== 'ok') return;
    await guard(async () => { await api('PUT', '/api/wishlist', { name: w.name, ...buyBody(w) }); toast('Saved'); await route(); });
  },
  slbig(el) { SL.big = !SL.big; const b = document.getElementById('sl-main'); if (b) b.classList.toggle('sl-big', SL.big); el.textContent = SL.big ? 'Normal print' : 'Large print'; el.setAttribute('aria-pressed', SL.big ? 'true' : 'false'); },
  slclear() { SL.ticks = {}; slSave(); route(); },
  slrm(el) { SL.extra = SL.extra.filter(t => t !== el.dataset.t); delete SL.ticks['extra:' + el.dataset.t]; slSave(); route(); },
  async sldone() {
    const names = Object.keys(SL.ticks).filter(k => SL.ticks[k] && !k.startsWith('extra:')), extras = Object.keys(SL.ticks).filter(k => SL.ticks[k] && k.startsWith('extra:')).map(k => k.slice(6));
    if (names.length && !(await needName())) return;
    await guard(async () => {
      for (const n of names) await api('PUT', '/api/wishlist', { name: n, status: 'got' });
      SL.extra = SL.extra.filter(t => !extras.includes(t)); SL.ticks = {}; slSave();
      toast(names.length ? `Marked ${names.length} as got it` + (extras.length ? ` and crossed off ${extras.length} extra` : '') : `Crossed off ${extras.length}`); await route();
    });
  },
  async buygot(el) {
    const w = buyItem(el.dataset.name); if (!w || !(await needName())) return;
    await guard(async () => { await api('PUT', '/api/wishlist', { name: w.name, status: w.status === 'got' ? 'want' : 'got' }); toast(w.status === 'got' ? 'Moved back to watching' : 'Marked as got it'); await route(); });
  },
  async buyrm(el) {
    const w = buyItem(el.dataset.name); if (!w || !(await needName())) return;
    if (!(await confirmBox('Stop watching it?', `${w.common_name || w.name} leaves Shopping${w.kind === 'plant' ? ' and the wishlist' : ''}, with its listings and notes.`, 'Stop watching', true))) return;
    await guard(async () => { await api('DELETE', '/api/wishlist', { name: w.name }); toast('Stopped watching ' + (w.common_name || w.name)); await route(); });
  },
  async buywatch(el) {                   // from Pots and trays, Fertilizer and the cold-night checklist: watch for it on Shopping
    if (!(await needName())) return;
    await guard(async () => {
      const have = (await api('GET', '/api/wishlist')).wishlist.find(x => x.name === el.dataset.name);
      if (!have) await api('PUT', '/api/wishlist', { name: el.dataset.name, kind: el.dataset.kind, search_words: el.dataset.search || '', source: el.dataset.src || '' });
      toast(have ? 'Already on Shopping' : 'Watching ' + el.dataset.name + ' on Shopping'); SHOPF.kind = el.dataset.kind; shopSave(); go('#/shopping');
    });
  },
  async storeedit() {
    const s = STORE; if (!s || !(await needName())) return;
    const homes = (META && META.homes) || [];
    const r = await modal(html`<form method="dialog"><h2>Edit: ${s.name}</h2>
      <label class="f">Address<input type="text" name="address" maxlength="200" value="${s.address}"></label>
      <label class="f">Phone<small>More than one? Separate them with a semicolon.</small><input type="tel" name="phone" maxlength="120" value="${s.phone}"></label>
      <label class="f">Hours<input type="text" name="hours" maxlength="300" value="${s.hours}"></label>
      <label class="f">Email<input type="email" name="email" maxlength="120" value="${s.email}"></label>
      <label class="f">Website<input type="url" name="website" maxlength="300" value="${s.website}"></label>
      ${s.local && homes.length > 1 ? html`<label class="f">Near<select name="home_id">${homes.map(h => html`<option value="${h.id}" ${h.id === s.home_id_eff ? raw('selected') : ''}>${h.name}</option>`)}</select></label>` : ''}
      <fieldset class="opt-group"><legend>What it carries</legend>${SHOPD.kinds.map(k => html`<label class="chk"><input type="checkbox" name="carries" value="${k.key}" ${s.carries.includes(k.key) ? raw('checked') : ''}> ${k.label}</label>`)}</fieldset>
      <div class="row"><button class="btn" value="ok">Save changes</button><button class="btn ghost" value="cancel">Cancel</button></div></form>`);
    if (r !== 'ok') return;
    const q = n => dlg.querySelector(`[name=${n}]`), b = { carries: [...dlg.querySelectorAll('[name=carries]:checked')].map(x => x.value) };
    ['address', 'phone', 'hours', 'email', 'website'].forEach(k => { b[k] = q(k).value; });
    if (q('home_id')) b.home_id = q('home_id').value;
    await guard(async () => { await api('PUT', '/api/stores/' + enc(s.key) + '/details', b); toast('Saved'); await route(); });
  },
  async storelookup(el) {
    const s = STORE; if (!s || !(await needName())) return;
    el.disabled = true; const m = document.getElementById('st-look'); if (m) m.textContent = 'Looking it up…';
    try {
      const r = await api('POST', '/api/stores/' + enc(s.key) + '/lookup');
      toast(r.filled.length ? 'Filled in: ' + r.filled.join(', ') : 'Nothing new was found on OpenStreetMap');
      await route();
    } catch (e) { if (m) m.textContent = e.message; el.disabled = false; }
  },
  async storenoterm(el) {
    if (!(await confirmBox('Remove this note?', 'It is taken off the store\'s page for everyone.', 'Remove the note', true))) return;
    await guard(async () => { await api('DELETE', '/api/stores/notes/' + enc(el.dataset.id)); toast('Removed'); await route(); });
  },
});
Object.assign(changeActs, {
  shopnear(el) { SHOPF.near = el.value; shopSave(); route(); },
  shopkind(el) { SHOPF.kind = el.value; shopSave(); route(); },
  storeshow(el) { STF.show = el.value; route(); },
  storecarries(el) { STF.carries = el.value; route(); },
  slstore(el) { SL.store = el.value; slSave(); route(); },
  sltick(el) { SL.ticks[el.dataset.k] = el.checked; slSave(); const n = Object.values(SL.ticks).filter(Boolean).length, b = document.querySelector('[data-act=sldone]'); if (b) { b.disabled = !n; b.textContent = `Done shopping: mark the ${n} ticked as got`; } const c = document.querySelector('[data-act=slclear]'); if (c && !n) c.remove(); },
});
Object.assign(formActs, {
  sladd(form) {                          // 1.34.0: an extra line on the shopping list
    const t = form.elements.text.value.trim().slice(0, 80); if (!t) return;
    if (!SL.extra.includes(t)) SL.extra.push(t);
    slSave(); route();
  },
  async storenote(form) {
    if (!(await needName())) return;
    await api('POST', '/api/stores/' + enc(STORE.key) + '/notes', { text: form.elements.text.value }); toast('Note saved'); await route();
  },
});
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
});const SPG = { step: null };
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
Object.assign(changeActs, { idfile: el => idFile(el), idmorefile: el => idMoreFile(el) });
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
    <p><a class="btn ghost" href="#/around">Fungi found near home this month</a></p>
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
  const hint = { name: 'A common name, or your own description such as "small brown one by the oak"', cap_size: 'For example 2 inches', spore_print: 'For example white, cream, pink, brown, purple-brown, black' }[f.name];
  return html`<label class="f">${f.label}${hint ? html`<small>${hint}</small>` : ''}<input type="text" name="${f.name}" id="${id}" value="${v || ''}"></label>`;
}
const MU_GROUPS = [['Name', ['name', 'scientific_name', 'id_status']], ['Where and when', ['found_on', 'place_kind', 'plant_code', 'place']],
  ['What it grew on', ['substrate', 'near', 'abundance']], ['What it looks like', ['cap_size', 'cap_colour', 'underside', 'ring', 'volva', 'spore_print', 'bruising', 'smell']], ['Notes', ['notes']]];
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
      ${MU_GROUPS.map(([t, names]) => html`<fieldset><legend>${t}</legend><div class="field-grid">${names.map(n => muField(meta, F[n], v[n], plants))}</div>
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
        <div class="row"><button class="btn" type="button" data-act="muident" ${ph.length ? '' : raw('disabled')}>Identify the photo shown</button></div>
        <div id="mu-ident" aria-live="polite"></div></section>
    </div>
    <div class="mu-info"><section aria-labelledby="mu-where-h"><h2 id="mu-where-h">Where and when</h2><dl class="dl">${dl(['found_on', 'place_kind', 'plant_code', 'place'])}
      ${f.lat != null ? html`<dt>Map location</dt><dd>${(+f.lat).toFixed(5)}, ${(+f.lon).toFixed(5)} (<a href="https://www.openstreetmap.org/?mlat=${f.lat}&mlon=${f.lon}#map=18/${f.lat}/${f.lon}" target="_blank" rel="noopener noreferrer">open the map</a>)</dd>` : ''}</dl>
      ${f.lat == null && gps ? html`<p><button class="btn ghost" type="button" data-act="mugps" data-lat="${gps.gps_lat}" data-lon="${gps.gps_lon}">Save the location from the photo (${(+gps.gps_lat).toFixed(4)}, ${(+gps.gps_lon).toFixed(4)})</button></p>` : ''}</section>
    <section aria-labelledby="mu-grew-h"><h2 id="mu-grew-h">What it grew on</h2>${['substrate', 'near', 'abundance'].some(show) ? html`<dl class="dl">${dl(['substrate', 'near', 'abundance'])}</dl>` : html`<p class="muted">Not noted yet.</p>`}</section>
    <section aria-labelledby="mu-look-h"><h2 id="mu-look-h">What it looks like</h2>${['cap_size', 'cap_colour', 'underside', 'ring', 'volva', 'spore_print', 'bruising', 'smell'].some(show) ? html`<dl class="dl">${dl(['cap_size', 'cap_colour', 'underside', 'ring', 'volva', 'spore_print', 'bruising', 'smell'])}</dl>` : html`<p class="muted">Not noted yet. Edit the find to add the cap, the underside, the ring, the base and the spore print.</p>`}</section>
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
