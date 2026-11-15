/* Plant record front end: updates from Claude that arrive as a file (1.58.0; plantdb/updates.py). One of the files loaded in order by
   index.html (js/manifest.json); they share one scope. Plain JavaScript, no inline handlers (the server's content policy forbids them).

   Ethan's choices of November 13 and 14, 2026: corrections and new pages come as one small file that Claude saves on his computer,
   and this page shows every change in it before anything is changed. The layout he chose from the previews: every plant on one page,
   each with its picture and its changes, ticked to begin with; a change the page no longer agrees with needs his decision and stays
   as it is unless he chooses Claude's. Today says when a file is waiting.

   #/updates          the files that are waiting, the box to choose one, and what was brought in before
   #/updates/<id>     one file's changes, or what it did if it was brought in already
   Only the owner sees any of it: the server refuses everyone else (OWNER_ONLY_PATHS). */
'use strict';

const UPD = { file: null, items: [] };            // the file being looked at, and its changes with the ticks and choices made on the page
const updDoing = x => x.state === 'ready' ? x.on : x.state === 'conflict' && x.take === 'claude';          // will this change be made?
const updVal = v => v == null || v === '' ? html`<span class="muted">Not set</span>` : html`${String(v)}`;
const updWhat = x => x.kind === 'set' ? x.label : x.kind === 'archive' ? 'Move this plant to the archive' : x.kind === 'ask' ? 'A question for you' : 'A new page for this plant';
const updN = (n, one, many) => `${n} ${n === 1 ? one : many}`;
const updGoWords = n => n === 1 ? 'Make the 1 change' : `Make the ${n} changes`;
function updGroups(items) {           // the changes plant by plant, in the file's order; a new page is a plant of its own
  const m = new Map();
  for (const x of items) { const key = x.kind === 'new' ? 'new' + x.i : x.code || x.name; if (!m.has(key)) m.set(key, { key, items: [] }); m.get(key).items.push(x); }
  return [...m.values()];
}
function updSumWords() {
  const n = UPD.items.length, plants = updGroups(UPD.items).length, need = UPD.items.filter(x => x.state === 'conflict').length, doing = UPD.items.filter(updDoing).length;
  const idle = UPD.items.filter(x => x.state === 'same' || x.state === 'out').length;
  return `${updN(n, 'change', 'changes')} for ${updN(plants, 'plant', 'plants')}. ${doing} ${doing === 1 ? 'is' : 'are'} set to be made`
    + (need ? `; ${need} ${need === 1 ? 'needs' : 'need'} your decision and ${need === 1 ? 'stays' : 'stay'} as ${need === 1 ? 'it is' : 'they are'} unless you choose Claude's` : '')
    + (idle ? `; ${idle} ${idle === 1 ? 'has' : 'have'} nothing to do or cannot be made, and ${idle === 1 ? 'says' : 'say'} why` : '') + '.';
}
function updCount() {                 // after a tick or a choice: the summary and the button say the new number
  const doing = UPD.items.filter(updDoing).length;
  const s = document.getElementById('upd-sum'); if (s) s.textContent = updSumWords();
  const b = document.getElementById('upd-go'); if (b) { b.textContent = updGoWords(doing); b.disabled = !doing; }       // (off: the line after it says why)
}
const updPicUrl = f => `/api/updates/${enc(UPD.file.id)}/photo/${enc(f)}`;
function updDetail(x) {               // what a change is, in full
  return x.kind === 'set' ? html`<p><span class="upd-k">Now:</span> ${updVal(x.now)}</p><p><span class="upd-k">Change to:</span> <strong>${updVal(x.to)}</strong></p>`
    : x.kind === 'ask' ? html`<p>${x.text}</p><p class="hint">It joins what Claude needs from you on this plant's page.</p>`
    : x.kind === 'archive' ? html`<p>It leaves the lists and Today. Nothing is deleted, and <strong>Move back to the main list</strong> on its page undoes it.</p>`
    : html`<p>${x.sci ? html`<i class="latin">${x.sci}</i>. ` : ''}${x.site}. ${x.photos.length ? `${updN(x.photos.length, 'photo comes', 'photos come')} with it:` : 'No photos come with it.'}</p>
      ${x.photos.length ? html`<ul class="upd-pics">${x.photos.map((f, k) => html`<li><img src="${updPicUrl(f)}" alt="Photo ${k + 1} of ${x.photos.length} for the new page${x.captions[k] ? ': ' + x.captions[k] : ''}" loading="lazy" width="120" height="120"></li>`)}</ul>` : ''}
      ${x.fields.length ? html`<p class="hint">${x.fields.map(([l, v]) => `${l}: ${v}`).join('. ')}.</p>` : ''}`;
}
function updChange(x) {               // one change: a tick box, a choice of two when it needs a decision, or a line saying why there is nothing to do
  const id = 'upd-c' + x.i, what = updWhat(x);
  if (x.state === 'same' || x.state === 'out') return html`<li class="upd-ch upd-idle" id="${id}">
    <p class="upd-what"><strong>${what}</strong> <span class="tag upd-tag">${x.state === 'same' ? 'Nothing to do' : 'Left out'}</span></p>
    <p>${x.note}</p>${x.kind === 'set' && x.state === 'out' ? html`<p class="hint">The file wanted: ${updVal(x.to)}</p>` : ''}</li>`;
  if (x.state === 'conflict') {
    const isNew = x.kind === 'new';
    return html`<li class="upd-ch upd-conf" id="${id}" tabindex="-1">
      <p class="upd-what"><strong>${what}</strong> <span class="tag upd-tag">Needs your decision</span></p>
      <p>${isNew ? x.note : 'This no longer says what the file expected, so it may be a change you made yourself.'}</p>
      <fieldset class="upd-pick"><legend class="sr">${what}: which one to keep</legend>
        <label class="chk"><input type="radio" name="upd-take-${x.i}" value="mine" data-act="updtake" data-i="${x.i}" ${x.take === 'mine' ? raw('checked') : ''}><span>${isNew ? html`<span class="upd-k">Do not make this page</span>` : html`<span class="upd-k">Keep what it says now:</span> ${updVal(x.now)}`}</span></label>
        <label class="chk"><input type="radio" name="upd-take-${x.i}" value="claude" data-act="updtake" data-i="${x.i}" ${x.take === 'claude' ? raw('checked') : ''}><span>${isNew ? html`<span class="upd-k">Make the page anyway</span>` : html`<span class="upd-k">Change it to Claude's:</span> <strong>${updVal(x.to)}</strong>`}</span></label></fieldset>
      ${isNew ? html`<div class="upd-vals upd-flat">${updDetail(x)}</div>` : ''}
      ${x.why ? html`<p class="hint">Why Claude suggests it: ${x.why}</p>` : ''}</li>`;
  }
  return html`<li class="upd-ch" id="${id}">
    <label class="chk upd-tick"><input type="checkbox" data-act="updtick" data-i="${x.i}" ${x.on ? raw('checked') : ''} aria-describedby="${id}-v"><span><strong>${what}</strong></span></label>
    <div class="upd-vals" id="${id}-v">${updDetail(x)}</div>
    ${x.note ? html`<p class="hint">${x.note}</p>` : ''}${x.why ? html`<p class="hint">Why: ${x.why}</p>` : ''}</li>`;
}
function updPlant(g) {                // a plant with its picture and its changes
  const x0 = g.items[0], isNew = x0.kind === 'new', known = !isNew && g.items.some(x => x.state !== 'out' || x.photo);
  const ph = isNew ? (x0.photos[0] ? updPicUrl(x0.photos[0]) : '') : x0.photo ? thumbUrl(x0.photo) : '';
  return html`<article class="upd-plant" aria-labelledby="upd-p-${g.key}">
    <div class="upd-ph">${ph ? html`<img src="${ph}" alt="" loading="lazy" width="240" height="180">` : html`<span class="upd-noph">No photo</span>`}</div>
    <div class="upd-body"><h3 id="upd-p-${g.key}">${known ? html`<a href="#/plant/${enc(x0.code)}">${x0.name}</a>` : x0.name} <span class="muted">${isNew ? 'No page yet' : x0.code}</span></h3>
      <ul class="upd-list">${g.items.map(updChange)}</ul></div></article>`;
}
function updReview() {                // every plant on one page, each with its picture and its changes, ticked to begin with
  const F = UPD.file, need = UPD.items.filter(x => x.state === 'conflict'), doing = UPD.items.filter(updDoing).length, can = UPD.items.some(x => x.state === 'ready');
  return html`<h1>Updates from Claude</h1>
    <div class="upd-file"><p class="upd-fhead"><span><strong>${F.name}</strong>${F.made ? `, made ${longDay(F.made)}` : ''}.</span> <a class="btn small ghost" href="#/updates">Choose another file</a></p>
      ${F.about ? html`<p><span class="upd-k">Claude's note:</span> ${F.about}</p>` : ''}</div>
    <p class="upd-sum" id="upd-sum" role="status">${updSumWords()}</p>
    <p class="hint upd-safe">Nothing is changed until you press the button that makes the changes.</p>
    ${need.length ? html`<p class="notice upd-needs" role="note"><strong>${need.length} ${need.length === 1 ? 'change needs' : 'changes need'} your decision.</strong> ${need.map(x => html`<button class="linkish" type="button" data-act="jumpsec" data-sec="upd-c${x.i}">${x.name}: ${updWhat(x)}</button>`)}</p>` : ''}
    ${can ? html`<p class="row upd-all"><button class="btn small ghost" type="button" data-act="updall" data-on="1">Tick every change</button><button class="btn small ghost" type="button" data-act="updall" data-on="0">Untick every change</button></p>` : ''}
    <h2 class="sr">The changes, plant by plant</h2>
    <div class="upd-plants">${updGroups(UPD.items).map(updPlant)}</div>
    <div class="sticky-save upd-bar"><button class="btn" type="button" id="upd-go" data-act="updapply" aria-describedby="upd-go-why" ${doing ? '' : raw('disabled')}>${updGoWords(doing)}</button><span class="why" id="upd-go-why">Nothing is ticked.</span>
      <button class="btn ghost upd-no" type="button" data-act="updaside" data-id="${F.id}">Change nothing</button></div>
    <p class="row upd-no-end"><button class="btn ghost" type="button" data-act="updaside" data-id="${F.id}">Change nothing</button></p>`;      // a phone: the bar holds one button, and this one ends the page
}
// what a file did, once it has been brought in
const UPD_DID = { set: x => x.label, ask: () => 'a question for you', archive: () => 'moved to the archive', new: () => 'page made, with its photos' };
function updDone(B) {
  const made = B.result.filter(x => x.did === 'made'), rest = B.result.filter(x => x.did !== 'made'), gs = updGroups(made);
  const whyNot = x => x.did === 'left' ? 'You left it as it was.' : x.note || 'Nothing to do.';
  return html`<h1>Updates from Claude</h1>
    <div class="notice ok upd-done" role="status"><p><strong>${updN(made.length, 'change', 'changes')} made${rest.length ? `, ${rest.length} left as ${rest.length === 1 ? 'it was' : 'they were'}` : ''}.</strong> From ${B.name}, brought in ${when(B.at)} by ${B.by}.</p>
      ${made.length ? html`<p>Each one is in its plant's page history and in the Audit log, signed "Claude (${B.name})".</p>` : ''}</div>
    ${gs.length ? html`<h2>What changed</h2>
      <ul class="upd-did">${gs.map(g => { const x0 = g.items[0]; return html`<li><a href="#/plant/${enc(x0.code)}">${x0.name}</a> <span class="muted">${x0.code}</span>: ${g.items.map(x => UPD_DID[x.kind](x)).join(', ')}.</li>`; })}</ul>
      <p>To take one back, open the plant's page, then <strong>Page history</strong>, and restore the version before this one. A plant moved to the archive has <strong>Move back to the main list</strong> on its page.</p>` : ''}
    ${rest.length ? html`<h2>What was left as it was</h2>
      <ul class="upd-did upd-rest">${rest.map(x => html`<li>${x.name}${x.code ? html` <span class="muted">${x.code}</span>` : ''}: ${x.kind === 'set' ? x.label : updWhat(x)}. ${whyNot(x)}</li>`)}</ul>` : ''}
    <p class="row"><a class="btn" href="#/">Go to Today</a><a class="btn ghost" href="#/history">Open the Audit log</a><a class="btn ghost" href="#/updates">Bring in another file</a></p>`;
}
// before a file is chosen: the ones that are waiting, the box to choose one, and what was brought in before
function updStart(L) {
  const good = L.waiting.filter(w => !w.bad), bad = L.waiting.filter(w => w.bad);
  return html`<h1>Updates from Claude</h1>
    <p>When Claude has corrections or new pages for your plants, it saves one small file on this computer and tells you its name. You see every change and decide before anything is changed, and nothing about your plants leaves this computer.</p>
    ${good.length ? html`<h2>Waiting for you (${good.length})</h2>
      <ul class="upd-wait">${good.map(w => html`<li class="upd-file"><p><strong>${w.name}</strong>${w.made ? `, made ${longDay(w.made)}` : ''}: ${updN(w.changes, 'change', 'changes')} for ${updN(w.plants, 'plant', 'plants')}.</p>
        ${w.about ? html`<p><span class="upd-k">Claude's note:</span> ${w.about}</p>` : ''}
        <p class="row"><a class="btn small" href="#/updates/${enc(w.id)}" aria-label="Look at the changes: ${w.name}">Look at the changes</a>
          <button class="btn small ghost" type="button" data-act="updaside" data-id="${w.id}" aria-label="Set it aside: ${w.name}">Set it aside</button></p></li>`)}</ul>`
      : L.folder ? html`<p class="notice ok">No update file is waiting.</p>` : ''}
    ${bad.length ? html`<h2>Files that cannot be used (${bad.length})</h2><ul class="upd-old">${bad.map(w => html`<li><strong>${w.name}</strong>: ${w.bad}</li>`)}</ul>` : ''}
    <h2>${good.length ? 'Choose another file' : 'Choose a file'}</h2>
    <form class="upd-choose" data-form="updfile"><label class="f">The update file<small>${L.folder ? 'A file that Claude saved in the plant-updates folder, inside the plant-database folder, shows above by itself. Use this box for a file kept somewhere else.'
        : 'Its name starts with "plant-updates" and ends in .json or .zip.'}</small>
      <input type="file" name="file" accept=".json,.zip,application/json,application/zip" required></label>
      <p class="row"><button class="btn" type="submit">Show its changes</button></p></form>
    <h2>Files you brought in before</h2>
    ${L.before.length ? html`<ul class="upd-old">${L.before.map(b => html`<li><strong>${when(b.at)}</strong>: ${b.name}. ${b.state === 'aside' ? 'Set aside, nothing changed.' : `${updN(b.made_n, 'change', 'changes')} made${b.left_n ? `, ${b.left_n} left as ${b.left_n === 1 ? 'it was' : 'they were'}` : ''}.`}
        ${b.state === 'aside' ? (b.here ? html`<button class="btn small ghost" type="button" data-act="updback" data-id="${b.id}" aria-label="Look at it again: ${b.name}">Look at it again</button>` : '') : html`<a href="#/updates/${enc(b.id)}" aria-label="See what it did: ${b.name}">See what it did</a>`}</li>`)}</ul>`
      : html`<p class="muted">None yet.</p>`}
    <p class="hint">A file can be brought in once. Opening it again shows what it did.</p>`;
}
async function viewUpdates(parts) {
  const title = 'Updates from Claude';
  if (ME().role !== 'owner') return { title, html: html`<h1>${title}</h1><p class="notice">Only ${ME().owner_name || 'the owner'} can bring in updates from Claude.</p>` };
  if (!parts[1]) { UPD.file = null; UPD.items = []; return { title, html: updStart(await api('GET', '/api/updates')) }; }
  const d = await api('GET', '/api/updates/' + enc(parts[1]));
  if (d.before) return { title, html: updDone(d.before) };
  const keep = UPD.file && UPD.file.id === d.id ? Object.fromEntries(UPD.items.map(x => [x.i, x])) : {};     // a redraw keeps the ticks and choices made so far
  UPD.file = d; UPD.items = d.items.map(x => ({ ...x, on: keep[x.i] ? keep[x.i].on : x.state === 'ready', take: keep[x.i] ? keep[x.i].take : 'mine' }));
  return { title, html: updReview() };
}
const updRedraw = async () => { const y = window.scrollY; await route(); window.scrollTo(0, y); };

addFeature({
  name: 'updates',
  pages: { updates: { view: viewUpdates, nav: 'updates', section: 'plants', label: 'Updates from Claude', href: '#/updates', after: 'facts' } },
  today: [{ id: 'upd-today', order: 6,                    // one line for the owner when a file from Claude is waiting in its folder
    load: async () => { if (ME().role !== 'owner') return null; const L = await api('GET', '/api/updates'); const w = L.waiting.filter(x => !x.bad); return w.length ? w : null; },
    html: w => html`<div class="notice upd-today" id="upd-today"><p><span><strong>${w.length === 1 ? 'Plant updates from Claude are waiting' : `${w.length} files of plant updates from Claude are waiting`}:</strong>
      ${w.length === 1 ? html`${w[0].name}, ${updN(w[0].changes, 'change', 'changes')} for ${updN(w[0].plants, 'plant', 'plants')}.` : html`${w.reduce((a, x) => a + x.changes, 0)} changes in all.`}
      Nothing is changed until you have looked.</span> <a class="btn small" href="${w.length === 1 ? '#/updates/' + enc(w[0].id) : '#/updates'}">Look at the changes</a></p></div>` }],
});
Object.assign(acts, {
  updall(el) { UPD.items.forEach(x => { if (x.state === 'ready') x.on = el.dataset.on === '1'; }); updRedraw(); },
  async updapply(el) {
    const accept = UPD.items.filter(x => x.state === 'ready' && x.on).map(x => x.i), take = UPD.items.filter(x => x.state === 'conflict' && x.take === 'claude').map(x => x.i);
    if (!accept.length && !take.length) return;
    if (!(await needName())) return;
    el.disabled = true;
    try { await guard(async () => { await api('POST', `/api/updates/${enc(UPD.file.id)}/apply`, { accept, take }); UPD.file = null; UPD.items = []; ROUTE_FRESH = true; await route(); window.scrollTo(0, 0);
      focusTitle(document.getElementById('app')); }); }
    finally { if (el.isConnected) el.disabled = false; }
  },
  async updaside(el) {                 // "Change nothing" on a file's page, or "Set it aside" in the list: nothing is changed and Today stops naming it
    if (!(await needName())) return;
    await guard(async () => { await api('POST', `/api/updates/${enc(el.dataset.id)}/aside`, { on: true }); toast('Set aside. Nothing was changed.');
      if (location.hash === '#/updates') await route(); else location.hash = '#/updates'; });
  },
  async updback(el) { await guard(async () => { await api('POST', `/api/updates/${enc(el.dataset.id)}/aside`, { on: false }); location.hash = '#/updates/' + enc(el.dataset.id); }); },
});
Object.assign(changeActs, {
  updtick(el) { const x = UPD.items[+el.dataset.i]; if (x) { x.on = el.checked; updCount(); } },
  updtake(el) { const x = UPD.items[+el.dataset.i]; if (x && el.checked) { x.take = el.value; updCount(); } },
});
Object.assign(formActs, {
  async updfile(form) {                // a file chosen on the page: the server checks it and keeps it until it is brought in or set aside
    const f = form.elements.file.files[0]; if (!f) return;
    if (f.size > 30 * 1024 * 1024) { toast('That file is larger than 30 MB, so it is not an update file.', true); return; }
    const fd = new FormData(); fd.append('file', f);
    let d;
    try { d = await api('POST', '/api/updates/upload', null, fd); }
    catch (e) { if (e.status === 409 && e.data && e.data.before) { toast(e.message); location.hash = '#/updates/' + enc(e.data.before.id); return; } throw e; }      // brought in already: show what it did
    location.hash = '#/updates/' + enc(d.id);
  },
});
