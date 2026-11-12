/* Plant record front end: the actions (data-act, data-f, data-form) and the event delegation that runs them. One of the files app.js was split into in 1.32.0; they load in order (index.html) and share one scope,
   so a function here may call any other. Plain JavaScript, no inline handlers (the server's content policy forbids them). */
'use strict';

// ---------- events ----------
async function copyRequest() {
  const text = requestText(CUR.p);
  try { await navigator.clipboard.writeText(text); toast('Copied. Paste it into your next message to Claude.'); return; } catch (e) { /* fall through */ }
  await modal(html`<form method="dialog"><h2>Copy this request</h2><p>Your browser blocked automatic copying. Select the text and press Ctrl+C (Cmd+C on a Mac).</p>
    <textarea readonly rows="9" autofocus>${text}</textarea><div class="row" style="margin-top:12px"><button class="btn" value="ok">Done</button></div></form>`);
}
async function pickPlant(title, text, withNone) {
  const list = await api('GET', '/api/plants');
  const r = await modal(html`<form method="dialog"><h2>${title}</h2><p>${text}</p>
    <label class="f">Plant<select name="t" autofocus>${withNone ? html`<option value="">Unassigned</option>` : ''}${list.map(p => html`<option value="${p.code}">${p.code}  ${p.common_name}</option>`)}</select></label>
    <div class="row"><button class="btn" value="ok">Move photo</button><button class="btn ghost" value="cancel">Cancel</button></div></form>`);
  return r === 'ok' ? dlg.querySelector('[name=t]').value : null;
}
const acts = {
  gphoto: el => sheetStep(el.dataset.code, +el.dataset.d),
  who() { whoDialog(); },
  spotnew(el) { const p = el.dataset.plan != null ? LT.plan[+el.dataset.plan] : null; spotDialog(p ? { name: p.name, light_id: p.light_id, units: p.units, distance_in: p.distance_in, hours: p.hours, dim_pct: p.dim_pct, codes: p.codes } : { light_id: ltSorted()[0] && ltSorted()[0].id }); },
  spotadd(el) { const s = LT.spots.find(x => x.id === +el.dataset.id); if (s) spotDialog({ ...s, codes: s.plants.map(p => p.code) }, { show: 'free' }); },     // 1.41.0
  spotbest() { spotBest(); },
  async spotplanall() {
    if (!(await needName())) return;
    const n = LT.plan.length, k = LT.plan.reduce((a, s) => a + s.codes.length, 0);
    if (!(await confirmBox(`Set up all ${n} suggested spots?`, `${k} plants go into ${n} new spots, named "Bright light 1" and so on, with the settings shown. You can rename, move or change each one afterwards.`, 'Set up all of them'))) return;
    await guard(async () => { const r = await api('POST', '/api/lights/spots/plan', {}); toast(`${r.made} spots set up, with ${r.plants} plants`); route(); });
  },
  async growsug(el) {
    LT = await api('GET', '/api/lights'); const code = el.dataset.code, p = LT.plan.find(s => s.codes.includes(code)); if (!p) { toast('The suggested layout has changed. Open Grow lights to see it.', true); return; }
    spotDialog({ name: p.name, light_id: p.light_id, units: p.units, distance_in: p.distance_in, hours: p.hours, dim_pct: p.dim_pct, codes: p.codes });
  },
  growadd(el) { growAddDialog(el.dataset.code); },
  async grownew(el) { LT = await api('GET', '/api/lights'); spotDialog({ light_id: ltSorted()[0] && ltSorted()[0].id, codes: [el.dataset.code] }, { show: 'fit' }); },
  spotedit(el) { const s = LT.spots.find(x => x.id === +el.dataset.id); if (s) spotDialog({ ...s, codes: s.plants.map(p => p.code) }); },
  async spotdel(el) {
    const s = LT.spots.find(x => x.id === +el.dataset.id); if (!s) return;
    if (!(await confirmBox('Remove this spot?', `"${s.name}" is removed and its ${s.plants.length} plant${s.plants.length === 1 ? '' : 's'} go back to the suggested layout. The light itself stays in your list.`, 'Remove spot', true))) return;
    await guard(async () => { await api('DELETE', '/api/lights/spots/' + s.id); toast('Spot removed'); route(); });
  },
  lightedit(el) { lightDialog(ltLight(el.dataset.id)); },
  lightnew() { lightDialog(null); },
  roomnew() { roomDialog(null); },
  roomedit(el) { roomDialog(LT.places.find(p => p.id === +el.dataset.id)); },
  shelfnew(el) { roomDialog(null, { room: el.dataset.room }); },       // 1.42.0
  async roomdel(el) {
    const pl = LT.places.find(p => p.id === +el.dataset.id); if (!pl) return;
    const room = !pl.name, shelves = room ? LT.places.filter(p => p.room === pl.room && p.name) : [];
    const spots = room ? LT.spots.filter(s => s.place_id === pl.id || shelves.some(x => x.id === s.place_id)) : LT.spots.filter(s => s.place_id === pl.id);
    const what = room ? `The room "${pl.room}"${shelves.length ? ` and its ${shelves.length} shel${shelves.length === 1 ? 'f' : 'ves'} (${shelves.map(x => x.name).join(', ')})` : ''} leave${shelves.length ? '' : 's'} the list.` : `The shelf "${pl.name}" leaves the list. The room ${pl.room} stays.`;
    if (!(await confirmBox(room ? 'Remove this room?' : 'Remove this shelf?', `${what}${spots.length ? ` The ${spots.length} light spot${spots.length === 1 ? '' : 's'} there stay, with "Where" set to ${room ? '"Not chosen yet"' : `the room as a whole`}.` : ''}`, room ? 'Remove the room' : 'Remove the shelf', true))) return;
    await guard(async () => { await api('DELETE', '/api/lights/places/' + pl.id); toast('Removed'); route(); });
  },
  async usethisbase() { await guard(async () => { await api('PUT', '/api/settings', { base_url: location.origin }); toast('Codes now open ' + location.origin); route(); }); },
  async whosave() {
    const f = dlg.querySelector('form'), m = document.getElementById('who-msg'), n = cleanName(f.elements.n.value);
    if (!n) { m.textContent = 'Type a name first.'; return; }
    if (viaTS()) {
      try { const r = await api('PUT', '/api/me', { name: n }); META.me = r; paintWho(); m.textContent = `Saved. Your changes now show as ${r.name}.`; }
      catch (e) { m.textContent = e.message; }
    } else { setName(n); m.textContent = `Saved. Your changes now show as ${n}.`; }
  },
  async pdel(el) {
    const m = document.getElementById('who-msg');
    try { const r = await api('DELETE', '/api/people?login=' + enc(el.dataset.login)); peoplePaint(r); m.textContent = `${el.dataset.name} removed. If they open the app again, they come back as "Can view only".`; }
    catch (e) { m.textContent = e.message; }
  },
  fertlog(el) {
    const o = {};
    if (el.dataset.code) o.codes = [el.dataset.code];
    if (el.dataset.date) o.date = el.dataset.date;
    if (el.dataset.group === 'due') { const t = todayStr(); o.codes = FERT.plants.filter(p => fertState(p, entriesFor(p.code), t, fertCtx()).state === 'due').map(p => p.code); }
    return fertDialog(o);
  },
  fzadd() { return productDialog(null); },
  fzedit(el) { const x = FERT.products[+el.dataset.i]; if (x) return productDialog(x); },
  async fzdel(el) {
    const x = FERT.products[+el.dataset.i]; if (!x || !x.saved || !(await needName())) return;
    if (!(await confirmBox('Remove this fertilizer?', `${x.product} comes off your list. Feedings you logged with it stay in the log${x.uses ? ', so it stays in the list as a logged fertilizer' : ''}.`, 'Remove', true))) return;
    await guard(async () => { await api('DELETE', '/api/fertilizer/products/' + x.id); toast(x.product + ' removed'); await fertRefresh(); });
  },
  fertedit(el) { const e = FERT.entries.find(x => x.id === +el.dataset.id); if (e) return fertDialog({ entry: e }); },
  async fertdel(el) {
    const e = FERT.entries.find(x => x.id === +el.dataset.id); if (!e || !(await needName())) return;
    if (!(await confirmBox('Remove this feeding?', `${e.product} on ${longDay(e.applied_on)}. The change log keeps a record that it was removed.`, 'Remove', true))) return;
    await guard(async () => { await api('DELETE', '/api/fertilizer/' + e.id); toast('Feeding removed'); await fertRefresh(); });
  },
  fertpick(el) {
    const t = readFert().applied_on || todayStr(), how = el.dataset.how;
    dlg.querySelectorAll('[name=pl]').forEach(b => {
      const p = FERT.plants.find(x => x.code === b.value);
      b.checked = how === 'none' ? false : how === 'season' ? !!(p && hasSeason(p) && monthIn(p, +t.slice(5, 7))) : !!(p && fertState(p, entriesFor(p.code), t, fertCtx()).state === 'due');
    });
    fertPreview();
  },
  calnav(el) { calNav(el.dataset.cal, +el.dataset.d); },
  calpick(el) { calGo(el.dataset.cal, el.dataset.date, false); },
  calview(el) {
    const id = el.dataset.cal, cur = (CALS[id] && CALS[id].view) || calView(), nv = cur === 'grid' ? 'list' : 'grid';
    try { localStorage.setItem('plantdb.calview', nv); } catch (e) { /* ignore */ }
    Object.values(CALS).forEach(c => { c.view = nv; calRender(c.id); });
  },
  histmetric(el) { const S = HS[el.dataset.kind]; S.metric = el.dataset.m; S.day = S.day; histOpen(el.dataset.kind); },
  display() { displayDialog(); },
  prefreset() { DVSCROLL = (document.getElementById('dv-body') || {}).scrollTop || 0; window.PlantPrefs.reset(); displayDialog(); },
  dvjump(el) {
    const t = document.getElementById(el.dataset.to); if (!t) return;
    t.scrollIntoView({ block: 'start', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
    const h = t.querySelector('h3'); if (h) { h.setAttribute('tabindex', '-1'); h.focus({ preventScroll: true }); }
  },
  async reqdone(el) { if (!(await needName())) return; await guard(async () => { await api('PUT', '/api/requests/' + el.dataset.id, { done: true }); toast('Marked done'); reloadPlant(); }); },
  async reqreopen(el) { if (!(await needName())) return; await guard(async () => { await api('PUT', '/api/requests/' + el.dataset.id, { done: false }); toast('Reopened'); reloadPlant(); }); },
  async reqanswer(el) {
    if (!(await needName())) return;
    const r = (CUR.p.requests || []).find(x => String(x.id) === el.dataset.id); if (!r) return;
    const res = await modal(html`<form method="dialog"><h2>Answer</h2><p>${r.text}</p>
      <label class="f">Your answer<textarea name="answer" rows="5" maxlength="2000" required></textarea></label>
      <div class="row"><button class="btn" value="ok">Save answer and mark done</button><button class="btn ghost" value="cancel" formnovalidate>Cancel</button></div></form>`);
    if (res !== 'ok') return;
    const a = dlg.querySelector('[name=answer]').value.trim(); if (!a) return;
    await guard(async () => { await api('PUT', '/api/requests/' + r.id, { done: true, answer: a }); toast('Answer saved. Use Copy my answers for Claude to send it.'); reloadPlant(); });
  },
  forclaude() { forClaudeDialog(); },
  debug() { debugDialog(); },
  dbgtimeclear() { TIMINGS = []; try { localStorage.removeItem('plantdb.timings'); } catch (e) { /* nothing kept */ } const d = document.querySelector('dialog[open]'); if (d) d.close(); debugDialog(); },
  place() { placeDialog(); },
  plcsearch() { placeSearch(); },
  plcadd(el) { placeAdd(+el.dataset.i); },
  plcweather() { if (dlg.open) dlg.close(); },
  async plchome() {
    const cur = META && META.place; if (!cur || cur.is_home || !(await needName())) return;
    const m = document.getElementById('plc-msg');
    try {
      await api('PUT', '/api/places/' + cur.id, { is_home: true });
      savePlace(null); META = null; COND = null; FROST = null; FROST_AT = 0;
      await route();
      if (m) m.textContent = `${cur.name} is now the home place for everyone.`;
      const h = document.getElementById('plc-home'); if (h) h.innerHTML = rend(plcHomeRow());
    } catch (e) { if (m) m.textContent = e.message; }
  },
  conclose() { DBG.console = '0'; dbgSave(); conApply(); toast('Audit log console off. Turn it back on with the Debug button.'); const d = document.getElementById('debug-btn') || document.querySelector('#app h1'); if (d) { if (d.tagName === 'H1') d.setAttribute('tabindex', '-1'); d.focus(); } },
  conpause(el) { CON.paused = !CON.paused; el.setAttribute('aria-pressed', String(CON.paused)); el.textContent = CON.paused ? 'Resume' : 'Pause'; conState(CON.paused ? 'Paused' : 'Live'); if (!CON.paused) conPoll(); },
  connew() { const b = document.getElementById('con-body'); if (b) { b.scrollTop = b.scrollHeight; b.focus(); } CON.unseen = 0; CON.stick = true; const n = document.getElementById('con-new'); if (n) n.hidden = true; },
  audclear() { Object.assign(AUD.f, { q: '', plant: '', who: '', kind: '', field: '', from: '', to: '', order: 'desc' }); AUD.offset = 0; audSave(); route(); },
  audrefresh() { audLoad('[data-act=audrefresh]'); },
  audpage(el) { AUD.offset = Math.max(0, AUD.offset + Number(el.dataset.d) * AUD.limit); audLoad(); const s = document.getElementById('aud-sum'); if (s) { s.scrollIntoView({ block: 'start' }); s.setAttribute('tabindex', '-1'); s.focus({ preventScroll: true }); } },
  async prepdone(el) {
    if (!(await needName())) return;
    const k = el.dataset.k, code = el.dataset.code, f = prepFocus(el, code);
    await guard(async () => { await api('POST', '/api/care', { plant: code, kind: 'prep_' + k }); toast('Saved: ' + PREP_CARE['prep_' + k]); await prepAfterChange(code, f); });
  },
  async prepstart(el) {         // 1.40.1
    if (!(await needName())) return;
    const code = el.dataset.code, f = el.closest('#prep-box') ? '#pm-inspect-tick' : `#mi-${code}-inspect-tick`;      // 1.41.1: on to the first tick box
    await guard(async () => { await api('POST', '/api/care', { plant: code, kind: 'prep_start' }); toast('Started the checklist. Inspect it for pests first.'); await prepAfterChange(code, f); });
  },
  lttop(el) {                 // 1.42.0: the Grow lights summary at the top folds as one
    const t = document.getElementById('lt-top'), b = document.getElementById('lt-top-body'), open = b.hidden;
    b.hidden = !open; t.dataset.open = open ? '1' : '0'; el.setAttribute('aria-expanded', open ? 'true' : 'false'); el.textContent = open ? 'Hide the summary' : 'Show the summary';
    try { localStorage.setItem('plantdb.lttop', open ? '1' : '0'); } catch (e) { /* this visit only */ }
    ltTopMeasure();
  },
  ltspotsall(el) { const on = el.dataset.open === '1'; document.querySelectorAll('details.lt-spot-fold').forEach(d => { d.open = on; }); },
  secfold(el) {               // 1.42.0: Show or hide a section
    const it = NAVITEMS.find(x => x.id === el.dataset.for); if (!it) return;
    const folded = el.getAttribute('aria-expanded') === 'true';
    foldSet(it, folded, true); navActive();
    if (!folded) window.dispatchEvent(new Event('resize'));     // charts and the like measure themselves again
  },
  prepfold(el) { const on = el.dataset.open === '1'; document.querySelectorAll('details.mi-fold').forEach(d => { d.open = on; }); },
  prepjump() { const h = document.getElementById('pm-head'); if (h) { scrollToSection(h); h.focus({ preventScroll: true }); } },
  async prepundo(el) {
    const k = el.dataset.k, code = el.dataset.code, f = prepFocus(el, code);
    const D = document.getElementById('prep-box') ? (PREP.data && PREP.data.code === code ? PREP.data : null) : (PREP.list ? PREP.list.plants.find(p => p.code === code) : null);
    const last = D ? (D.log || []).filter(x => x.kind === 'prep_' + k).pop() : null; if (!last) return;
    if (!(await needName())) return;
    await guard(async () => { await api('DELETE', '/api/care/' + last.id); toast('Removed: ' + PREP_CARE['prep_' + k] + ', ' + relDay(last.done_on)); await prepAfterChange(code, f); });
  },
  openprep(el) { try { sessionStorage.setItem('plantdb.toprep', el.dataset.code); } catch (e) { /* the page still opens */ } go('#/plant/' + enc(el.dataset.code)); },
  async fccopy() {
    const t = document.getElementById('fc-text'); if (!t) return;
    let ok = false;
    try { await navigator.clipboard.writeText(t.value); ok = true; }
    catch (e) { t.focus(); t.select(); try { ok = document.execCommand('copy'); } catch (e2) { ok = false; } }
    if (!ok) { t.focus(); t.select(); fcSay('This browser would not copy it. The message is selected: press Ctrl+C to copy it.'); return; }
    await fcMark(); fcSay('Copied. Now paste it into your chat with Claude (Ctrl+V).');
  },
  async fcsave() {
    const a = document.createElement('a');
    a.href = `/api/for-claude.txt?range=${FC.range}&open=${FC.open ? 1 : 0}`; a.download = ''; document.body.appendChild(a); a.click(); a.remove();
    await fcMark(); fcSay('Saved to your Downloads folder. Attach it in your chat with Claude, or open it and copy the text.');
  },
  async todoedit(el) {
    const t = TODO.find(x => String(x.id) === el.dataset.id); if (!t || !(await needName())) return;
    const r = await modal(html`<form method="dialog"><h2>Edit entry</h2>
      <label class="f">What to photograph<input type="text" name="label" maxlength="200" required value="${t.label}"></label>
      <label class="f">Note<textarea name="note" rows="4" maxlength="1000">${t.note || ''}</textarea></label>
      <p class="hint">Type plant codes such as P-012 to link them.</p>
      <div class="row"><button class="btn" value="ok">Save</button><button class="btn ghost" value="cancel" formnovalidate>Cancel</button></div></form>`);
    if (r !== 'ok') return;
    const label = dlg.querySelector('[name=label]').value.trim(), note = dlg.querySelector('[name=note]').value.trim();
    if (!label) return;
    await guard(async () => { await api('PATCH', '/api/to-photograph/' + t.id, { label, note }); toast('Saved'); route(); });
  },
  jobs() { jobsDialog(); },
  async jobrun(el) {
    const m = document.getElementById('job-msg'); el.disabled = true;
    try { await api('POST', '/api/jobs/run', { kind: el.dataset.kind }); if (m) m.textContent = 'Started.'; await jobsDialog(); }
    catch (e) { if (m) m.textContent = e.message; el.disabled = false; }
  },
  problems() { const d = document.querySelector('dialog[open]'); if (d) d.close(); problemsDialog(); },
  proball() { PROBALL = !PROBALL; const d = document.querySelector('dialog[open]'); if (d) d.close(); problemsDialog(); },
  async probclear(el) { await guard(async () => { await api('POST', '/api/problems', el.dataset.id === 'all' ? { all: true } : { id: +el.dataset.id }); const d = document.querySelector('dialog[open]'); if (d) d.close(); problemsDialog(); }); },
  async probcopy() {
    const m = document.getElementById('prob-msg');
    try { await navigator.clipboard.writeText('Problems from Plant record ' + (META && META.version) + ':\n' + PROBTEXT); if (m) m.textContent = 'Copied. Paste it into the chat with Claude.'; }
    catch (e) { if (m) m.textContent = 'Could not copy. Select the list and copy it yourself.'; }
  },
  async bkcopynow(el) {              // 1.33.0
    const m = document.getElementById('bk-copy-msg'); el.disabled = true; if (m) m.textContent = 'Copying…';
    try { const r = await api('POST', '/api/backups/copies', {}); const st = r.status || {}; if (m) m.textContent = `Done. Folder: ${st.dir || 'not set up'}. Other computer: ${st.receiver || 'not set up'}.`; }
    catch (e) { if (m) m.textContent = e.message; }
    el.disabled = false;
  },
  async bkrestore(el) {              // 1.31.0: put a backup's database back in place
    if (!(await needName())) return;
    const r = await modal(html`<form method="dialog"><h2>Restore this backup?</h2>
      <p>The plant record goes back to how it was on <strong>${el.dataset.made}</strong>${el.dataset.plants ? ` (${el.dataset.plants} plants)` : ''}. Every plant, note, setting and log entry made since then is replaced by what the backup holds.</p>
      <ul><li>A backup of how things are now is made first, so this can be undone by restoring that one.</li>
        <li>Photos are never removed. ${el.dataset.photos ? 'Photos in the backup that are missing from your folder are put back.' : 'This backup has no photos; your photos stay as they are.'}</li>
        <li>An older backup is brought up to this version on the way in.</li></ul>
      <div class="row"><button class="btn danger" value="ok">Restore it</button><button class="btn ghost" value="cancel" autofocus>Cancel</button></div></form>`);
    if (r !== 'ok') return;
    el.disabled = true; toast('Restoring. This takes a few seconds.');
    await guard(async () => {
      const x = await api('POST', '/api/backups/restore', { file: el.dataset.file });
      QC.clear(); PCODES_AT = 0; FROST = null; PGROUPS = null; META = null;
      await modal(html`<form method="dialog"><h2>Restored</h2><p>${x.plants} plants are back as they were. ${x.photos_added ? `${x.photos_added} photos were put back. ` : ''}The database from before is kept as <code>${x.before}</code>.</p>
        <div class="row"><button class="btn" value="ok" autofocus>Done</button></div></form>`);
      location.reload();
    });
    el.disabled = false;
  },
  async bkdel(el) {
    if (!(await needName())) return;
    if (!(await confirmBox('Delete this backup?', el.dataset.file + ' will be removed from the backups folder. This cannot be undone.', 'Delete backup', true))) return;
    await guard(async () => { await api('DELETE', '/api/backups/' + enc(el.dataset.file)); toast('Backup deleted'); route(); });
  },
  needs() { G.needs = !G.needs; gSave(); route(); },
  edlong(el) { const w = el.closest('.ed-long'), l = w.querySelector('label'); l.hidden = false; const t = l.querySelector('textarea'); t.dataset.was = t.value; t.focus(); },
  async whareadel(el) { if (!(await needName())) return; if (!(await confirmBox(`Remove ${el.dataset.name}?`, 'Its spots are removed too. Plants must be moved out of it first.', 'Remove', true))) return;
    await guard(async () => { await api('DELETE', '/api/where/areas/' + el.dataset.id); META = await api('GET', '/api/meta'); toast('Removed'); route(); }); },
  async whspotdel(el) { if (!(await needName())) return; if (!(await confirmBox(`Remove the spot ${el.dataset.name}?`, 'Plants there keep their area or room; they just have no spot.', 'Remove', true))) return;
    await guard(async () => { await api('DELETE', '/api/where/spots/' + el.dataset.id); META = await api('GET', '/api/meta'); toast('Spot removed'); route(); }); },
  async whsort() {                                   // 1.56.3: every group at once
    if (!(await needName())) return;
    const items = WHSORT.map((_, i) => whsItem(i)).filter(x => x && x.codes.length), kept = whsKeep(-1);   // 1.58.0: kept for any group left
    await guard(async () => { const r = await api('POST', '/api/where/sort', { items }); META = await api('GET', '/api/meta');
      toast(`${r.moved} plant${r.moved === 1 ? '' : 's'} put in their spots${r.made.length ? `. New spot${r.made.length === 1 ? '' : 's'}: ${r.made.join('; ')}` : ''}.`); await route(); whsRestore(kept);
      const h = document.querySelector('#wh-sort h2'); if (h) h.focus(); });
  },
  async whsone(el) {                                 // 1.56.3: one group; the focus goes on to the next
    if (!(await needName())) return;
    const i = +el.dataset.i, item = whsItem(i); if (!item) return;
    if (!item.codes.length) { toast('Tick at least one plant to put in this spot.', true); return; }
    if (!item.spot_id && !String(item.name || '').trim()) { toast('Type the name of the new spot, or choose one of the spots.', true); return; }
    const where = item.spot_id ? document.querySelector(`[data-whs="${i}"][data-k=spot] option:checked`).textContent : item.name.trim();
    const kept = whsKeep(i);                         // 1.58.0: what was chosen in the other groups survives the redraw
    await guard(async () => { const r = await api('POST', '/api/where/sort', { items: [item] }); META = await api('GET', '/api/meta');
      toast(`${r.moved} plant${r.moved === 1 ? '' : 's'} put in ${where}${r.made.length ? ' (a new spot)' : ''}.`); await route(); whsRestore(kept);
      const next = document.querySelector(`#whs-${i} [data-k=area]`) || document.querySelector('#wh-sort h2') || document.querySelector('main h1'); if (next) next.focus(); });
  },
  async ctadd(el) { if (!(await needName())) return;
    await guard(async () => { const x = await api('POST', '/api/containers', { kind: el.dataset.kind, name: el.dataset.kind === 'pot' ? 'New pot' : 'New catch tray', shape: 'circle', qty: 1 });
      META = await api('GET', '/api/meta'); await route(); const n = document.querySelector(`#ct-${x.id} [data-k=name]`); if (n) { n.focus(); n.select(); } toast('Added. Type its name and sizes.'); }); },
  async ctdel(el) { if (!(await needName())) return; if (!(await confirmBox(`Remove ${el.dataset.name}?`, 'Its photos are removed too.', 'Remove', true))) return;
    await guard(async () => { await api('DELETE', '/api/containers/' + el.dataset.id); META = await api('GET', '/api/meta'); toast('Removed'); route(); }); },
  async ctphotodel(el) { if (!(await needName())) return; await guard(async () => { await api('DELETE', '/api/containers/photos/' + el.dataset.id); toast('Photo removed'); route(); }); },
  sevreset() { SEV.photos.forEach(p => { try { URL.revokeObjectURL(p.url); } catch (e) { /* gone */ } }); Object.assign(SEV, { step: 'pick', photos: [], order: [], plants: [], done: null, busy: false }); SEV.home = sevDefaultHome(); sevDraw('input[type=file]'); },
  ltedit(el) {                          // 1.39.1: a light's name, count, model and place are text until you ask to edit them
    const box = document.getElementById('lt-ed-' + el.dataset.id); if (!box) return;
    box.hidden = !box.hidden; el.setAttribute('aria-expanded', String(!box.hidden)); el.textContent = box.hidden ? 'Edit the name, count, model and where it is' : 'Done editing';
    if (!box.hidden) { const i = box.querySelector('input'); if (i) i.focus(); }
  },
  async newfill(el) {                   // 1.38.0: Add a plant: the names from the photos on the form; 1.40.0: all of them together, with Pl@ntNet, and "Not this"
    const form = el.closest('form') || document.querySelector('form[data-form=new]'), inp = form && form.elements.__photos, st = document.getElementById('newfill-st');
    const files = inp ? [...inp.files] : []; if (!files.length) return;
    el.disabled = true; if (st) st.innerHTML = rend(html`<p class="muted" role="status">Checking ${files.length === 1 ? 'the photo' : `the ${files.length} photos together`}…</p>`);
    try {
      if (!navigator.onLine || !(await offProbe())) { if (st) st.textContent = 'This needs a connection to the plant server. Save the plant now and the photo is checked when it can be reached; the names are then offered on the Offline page.'; return; }
      if (!NEWID.mode) { NEWID.mode = await idPickMode('add'); if (!NEWID.mode) { if (st) st.textContent = ''; return; } }   // 5b: asked once per form
      ID.mode = NEWID.mode;
      const r = await idAsk(files[0], null, files.slice(1, 6), NEWID.ex); NEWID.r = r;
      const sp = (r.species || []).filter(x => x.scientific_name), m = (r.matches || [])[0];
      if (!sp.length) { if (st) st.innerHTML = rend(html`<p>No name was found for this photo. Type the names yourself.</p>`); return; }
      acts.newuse({ dataset: { i: '0' } }, true);
      if (st) st.innerHTML = rend(html`${m && m.confidence >= .6 ? html`<p class="notice" role="note"><strong>This may be a plant you already have:</strong> <a href="#/plant/${enc(m.code)}" target="_blank" rel="noopener">${m.code} ${m.common_name || ''}</a> (${pct(m.confidence)} sure).</p>` : ''}
        <p>The first name is filled in (empty fields only; what you typed stays). Choose another with <strong>Use this name</strong>, or say <strong>Not this</strong> to check again without it.</p>
        ${idNamesPanel(r, { src: 'new', id: 'new-splist', use: 'newuse', reject: 'new' })}`);
    } catch (e) { if (st) st.innerHTML = rend(html`<p class="notice bad">${e.message}</p>`); }
    finally { el.disabled = false; }
  },
  newuse(el, quiet) {                   // 1.40.0: put one of the names found on the form
    const s0 = NEWID.r && (NEWID.r.species || [])[+el.dataset.i]; const form = document.querySelector('form[data-form=new]'); if (!s0 || !form) return;
    const put = (k, v, force) => { const i = form.elements[k]; if (i && (force || !i.value.trim())) i.value = v == null ? '' : v; };
    const force = !quiet;
    put('common_name', (s0.common_name || '').split(',')[0].trim() || s0.scientific_name, force); put('scientific_name', s0.scientific_name, force); put('genus', (s0.scientific_name || '').split(' ')[0], force); put('family', s0.family || '', force);
    put('id_confidence', Math.round((s0.probability || 0) * 100), force);
    put('id_basis', `Suggested by ${(s0.sources || ['the picture checker on this computer']).map(w => w === 'this computer' ? 'the picture checker on this computer' : w).join(' and ')} from the photo${NEWID.r.pictures > 1 ? 's' : ''} on the form. Check it.`, force);
    if (!quiet) { toast('Names filled in: ' + ((s0.common_name || '').split(',')[0].trim() || s0.scientific_name)); const cn = form.elements.common_name; if (cn) cn.focus(); }
  },
  sevrecheck(el) { return sevIdentify(+el.dataset.g, true); },
  sevask(el) { return sevIdentify(+el.dataset.g, true, 'yes'); },
  async sevsave() {
    if (!(await needName())) return;
    const err = document.getElementById('sev-err');
    const list = SEV.plants.map((P, gi) => [P, gi]).filter(([P]) => P.add);
    const bad = list.find(([P]) => !String(P.fields.common_name || '').trim());
    if (bad) { if (err) err.textContent = `Plant ${bad[1] + 1} needs a common name.`; const i = document.querySelector(`[data-f=sevfield][data-g="${bad[1]}"][data-k=common_name]`); if (i) i.focus(); return; }
    const plants = list.map(([P, gi]) => { const n = SEV.photos.filter(p => p.group === gi).length;
      const fields = { ...P.fields, site: SEV.site, home_id: SEV.home || '',
        id_basis: P.pick >= 0 ? `Suggested by ${((P.species[P.pick] || {}).sources || ['the picture checker on this computer']).map(w => w === 'this computer' ? 'the picture checker on this computer' : w).join(' and ')} from ${n} photo${n === 1 ? '' : 's'} (${P.fields.id_confidence || 0}% likely). Check it.` : '' };
      return { fields, photos: SEV.photos.filter(p => p.group === gi).map(p => p.file) }; });
    const shared = SEV.photos.filter(p => p.rel === 'all').map(p => p.file);      // 1.38.0: wide shots go on every plant
    SEV.busy = true; const b = document.querySelector('[data-act=sevsave]'); if (b) b.disabled = true;
    try { const r = await api('POST', '/api/plants/several', { plants, shared }); ALL = await api('GET', '/api/plants?status=all'); META = await api('GET', '/api/meta'); SEV.done = r.codes; SEV.busy = false; sevDraw('.notice.ok'); toast(`${r.codes.length} plants added`); }
    catch (e) { SEV.busy = false; if (b) b.disabled = false; if (err) err.textContent = e.message; }
  },
  idphmore() { IDPH.shown += IDPH_PAGE; drawIdPhotos(); const rows = document.querySelectorAll('#idph-tbl tbody tr'); const a = rows[IDPH.shown - IDPH_PAGE] && rows[IDPH.shown - IDPH_PAGE].querySelector('a'); if (a) a.focus(); },
  layout() { const P = window.PlantPrefs.get(); window.PlantPrefs.set('layout', P.layout === 'single' ? 'split' : 'single'); route(); },
  navgo(el, e) {
    if (e) e.preventDefault();
    const it = NAVITEMS[+el.dataset.i]; if (!it) return;
    if (it.top) { window.scrollTo({ top: 0, behavior: 'smooth' }); const p = document.querySelector('.pane'); if (p) document.querySelectorAll('.pane').forEach(x => x.scrollTo({ top: 0 })); }
    else { scrollToSection(it.el); navFlash(it.el); }
    navPin(+el.dataset.i);
    if (document.documentElement.dataset.narrow === '1') { NAVSESSION = false; navLayout(); }
  },
  navtoggle() {
    const open = !navOpen();
    if (document.documentElement.dataset.narrow === '1') NAVSESSION = open; else { NAVSESSION = null; window.PlantPrefs.set('navopen', open ? '1' : '0'); }
    navLayout(); fitPanes(); paintAllCharts();
    const f = open ? document.querySelector('#sn-list a') : document.getElementById('nav-tab'); if (f) f.focus();
  },
  reloadnow() { location.reload(); },          // 1.56.5: a new version is installed
  async pledit(el) {                     // 1.56.5: a plant's main details as text, or in boxes to change
    const open = el.getAttribute('aria-expanded') !== 'true'; PLEDIT = open && CUR && CUR.p ? CUR.p.code : null;
    if (!open) { await route(); const b = document.querySelector('[data-act=pledit]'); if (b) b.focus(); return; }   // drawn again with what was changed
    const ed = document.getElementById('pl-ed'), box = document.getElementById('details');
    if (ed) ed.hidden = false; if (box) box.classList.add('pl-editing');
    el.setAttribute('aria-expanded', 'true'); el.textContent = 'Done changing';
    const f = ed && ed.querySelector('input,select'); if (f) f.focus();
  },
  topmore(el) { const top = document.querySelector('header.top'), open = el.getAttribute('aria-expanded') !== 'true';    // 1.56.5: Online, Home and Editing behind More on a narrow screen
    el.setAttribute('aria-expanded', open ? 'true' : 'false'); top.classList.toggle('more-open', open); if (open) { pagesMenu(false); const f = document.getElementById('net'); if (f) f.focus(); } },
  pages() { const b = document.getElementById('pages-btn'); const open = b && b.getAttribute('aria-expanded') !== 'true'; pagesMenu(open); if (open) topMoreFold();
    if (open) { const a = document.querySelector('#main-nav a[aria-current=page]') || document.querySelector('#main-nav a'); if (a) a.focus(); } },
  navside() { window.PlantPrefs.set('navside', window.PlantPrefs.get().navside === 'left' ? 'right' : 'left'); navLayout(); fitPanes(); paintAllCharts(); },
  jump(el) {
    const t = document.getElementById(el.dataset.id); if (!t) return;
    scrollToSection(t); navFlash(t);
    const ni = NAVITEMS.findIndex(it => it.id === el.dataset.id); if (ni >= 0) navPin(ni);
    if (!t.hasAttribute('tabindex')) t.setAttribute('tabindex', '-1');
    t.focus({ preventScroll: true });
  },
  setcond() { condDialog(); },
  async copytok() {
    const t = document.getElementById('tok').textContent;
    try { await navigator.clipboard.writeText(t); toast('Token copied'); }
    catch (e) { const r = document.createRange(); r.selectNodeContents(document.getElementById('tok')); const s = getSelection(); s.removeAllRanges(); s.addRange(r); toast('Press Ctrl+C to copy the selected token'); }
  },
  async tokregen() {
    if (!(await needName())) return;
    if (!(await confirmBox('Make a new sensor token?', 'The old token stops working right away. Any sensor using it will need the new one.', 'Make new token', true))) return;
    await guard(async () => { await api('POST', '/api/ingest/regenerate'); toast('New token made'); route(); });
  },
  async wxrefresh(el) {
    el.disabled = true;
    try { const r = await api('POST', '/api/weather/refresh', { loc: el.dataset.all ? 'all' : WX.place.id }); toast(r.started ? 'Updating in the background' : 'An update is already running'); document.body.dataset.job = '1'; }
    catch (e) { toast(e.message, true); }
    route();
  },
  printlabel() {
    const src = document.querySelector('#label .lblwrap'); if (!src) return;
    const box = document.createElement('div'); box.id = 'print-label'; box.innerHTML = src.querySelector('.lbl').outerHTML;
    document.body.appendChild(box); document.body.classList.add('print-label');
    const done = () => { box.remove(); document.body.classList.remove('print-label'); window.removeEventListener('afterprint', done); };
    window.addEventListener('afterprint', done); setTimeout(() => window.print(), 50);
  },
  wxmatch() {
    if (!WT.shown) { toast('The table has not loaded yet.', true); return; }
    if (WT.kind === 'sensor') { WX.src = 'sensor'; }
    WX.period = WT.from || WT.to ? 'custom' : 'all'; WX.from = WT.from || '1940-01-01'; WX.to = WT.to || ymd(new Date());
    const core = { temperature_2m: 'temp', relative_humidity_2m: 'hum', par: 'light', temp_f: 'temp', humidity: 'hum' };
    WX.show = [...new Set(WT.shown.map(k => core[k]).filter(Boolean))];
    WX.vars = WT.shown.filter(k => !core[k] && catOf(k) && !DAILY_SKIP.includes(k));
    if (WT.kindShown === 'daily' && WT.shown.some(k => /^temperature_2m_/.test(k))) WX.show = [...new Set([...WX.show, 'temp'])];
    wxSave(); Promise.resolve(route()).then(() => { const c = document.getElementById('wx-charts'); if (c) c.closest('section').scrollIntoView(); });
  },
  wxgroup(el) {
    const keys = el.dataset.keys.split(','), on = el.dataset.on === '1';
    WX.vars = on ? [...new Set([...WX.vars, ...keys])] : WX.vars.filter(k => !keys.includes(k));
    keys.forEach(k => { const b = document.querySelector(`[data-f=wxvar][data-key="${k}"]`); if (b) b.checked = on; });
    const n = document.getElementById('wx-pickcount'); if (n) n.textContent = WX.show.length + WX.vars.length;
    wxSave(); clearTimeout(WX.t); WX.t = setTimeout(loadWxCharts, 600);
  },
  wxallvars(el) {
    const daily = el.dataset.which === 'daily';
    const keys = (WXCAT || []).filter(c => daily ? (c.kind === 'daily' && !DAILY_SKIP.includes(c.key) && !(WXCAT || []).some(x => x.kind === 'hourly' && x.key === c.key)) : (c.kind === 'hourly' && !['temperature_2m', 'relative_humidity_2m'].includes(c.key))).map(c => c.key);
    WX.vars = [...new Set([...WX.vars, ...keys])];
    const d = document.getElementById('wx-pick'); if (d) d.innerHTML = rend(wxPickInner());
    const n = document.getElementById('wx-pickcount'); if (n) n.textContent = WX.show.length + WX.vars.length;
    wxSave(); loadWxCharts();
  },
  wxbar() {
    WXBAR = !wxBarOpen();
    const body = document.getElementById('wx-barbody'), b = document.getElementById('wx-barbtn');
    body.hidden = !WXBAR; b.setAttribute('aria-expanded', WXBAR ? 'true' : 'false'); b.textContent = WXBAR ? 'Hide chart settings' : 'Show chart settings';
    navLayout();
  },
  gotoplaces(el, e) { const t = document.getElementById('sec-places'); if (t) scrollToSection(t); },
  jumpsec(el) { const t = document.getElementById(el.dataset.sec); if (t) { scrollToSection(t); navFlash(t); } },   // 1.34.0: Today's jump buttons (scrollToSection puts the focus on the heading)
  placeshow(el) { setPlace(el.dataset.id).then(() => window.scrollTo(0, 0)); },
  async placehome(el) {
    const p = WX.places.find(x => String(x.id) === el.dataset.id); if (!p || !(await needName())) return;
    if (!(await confirmBox(`Make ${p.name} home?`, `Every computer or phone that has not chosen its own location will use the weather for ${p.name} instead of ${WX.home.name}, and so will the hourly updates and backups.`, 'Make home'))) return;
    await guard(async () => { await api('PUT', '/api/places/' + p.id, { is_home: true }); if (String(PLACE) === String(p.id)) savePlace(null); META = null; COND = null; FROST = null; FROST_AT = 0; toast(`${p.name} is now home`); route(); });
  },
  async placeplants(el) {             // 1.28.0: a home of its own
    if (!(await needName())) return;
    const on = el.dataset.on === '1';
    await guard(async () => { await api('PUT', '/api/places/' + el.dataset.id, { plants_here: on }); META = null; COND = null; FROST = null; FROST_AT = 0;
      toast(on ? 'Plants can now be given this home' : 'No plants live there now'); route(); });
  },
  async placeonoff(el) {
    if (!(await needName())) return;
    await guard(async () => { await api('PUT', '/api/places/' + el.dataset.id, { enabled: el.dataset.on === '1' }); toast(el.dataset.on === '1' ? 'Hourly updates on' : 'Hourly updates stopped; its stored weather is kept'); route(); });
  },
  async placedel(el) {
    const p = WX.places.find(x => String(x.id) === el.dataset.id); if (!p || !(await needName())) return;
    if (!(await confirmBox(`Remove ${p.name}?`, `This deletes its ${num(p.count || 0)} hourly readings, its daily summaries and its update log. To keep them, use "Stop hourly updates" instead. This cannot be undone.`, 'Remove it and its weather', true))) return;
    await guard(async () => { const r = await api('DELETE', '/api/places/' + p.id); toast(`${p.name} removed (${num(r.removed_readings)} readings)`); await setPlace(String(PLACE) === String(p.id) ? null : PLACE); });
  },
  async placepick(el) {
    const r = (PLACE_RESULTS || [])[+el.dataset.i]; if (!r) return;
    await addPlace({ name: r.name, lat: r.lat, lon: r.lon, tz: r.tz, country: r.country || '' });     // 1.48.0: the country comes with the search result
  },
  wxpanel() {
    const p = document.getElementById('wx-panel'), b = document.getElementById('wx-panelbtn'); if (!p) return;
    p.hidden = !p.hidden; b.setAttribute('aria-expanded', p.hidden ? 'false' : 'true');
    navLayout();
    if (!p.hidden) { const f = p.querySelector('input,button'); if (f) f.focus(); } else b.focus();
  },
  wxclearvars() { WX.vars = []; wxSave(); route(); },
  wtpage(el) { WT.page = el.dataset.to ? +el.dataset.to : Math.max(1, WT.page + (+el.dataset.d)); loadWxTable().then(wtFocusTop); },
  async wtallcols() { wtHidden().clear(); wtSave(); loadWxTable(); },
  async wtnocols() { const T = await api('GET', '/api/weather/table?per=10&kind=' + (WT.kind === 'daily' ? 'daily' : 'hourly') + '&source=' + (WT.kind === 'sensor' ? 'sensor' : 'weather')); WT.hide = new Set(T.columns.map(c => c.key).filter(k => !['temperature_2m', 'relative_humidity_2m', 'par', 'temperature_2m_max', 'temperature_2m_min', 'precipitation_sum', 'relative_humidity_2m_mean'].includes(k) && WT.kind !== 'sensor')); wtSave(); loadWxTable(); },
  // 1.16.0: groups
  grpnew(el) { groupDialog(null, el.dataset.kind); },
  grpedit() { if (CURG) groupDialog(CURG); },
  async grpdel() {
    const d = CURG; if (!d || !(await needName())) return;
    if (!(await confirmBox('Remove the group ' + d.name + '?', 'The group goes away. The plants in it are not changed.', 'Remove the group', true))) return;
    await guard(async () => { await api('DELETE', '/api/groups/' + d.id); toast('Group removed: ' + d.name); if (String(G.group) === String(d.id)) { G.group = ''; gSave(); } await loadGroups(true); go('#/groups'); });
  },
  async grpaddsug(el) {
    const x = PGROUPS && PGROUPS.suggestions[+el.dataset.i]; if (!x || !(await needName())) return;
    await guard(async () => { await api('POST', '/api/groups', { name: x.name, kind: 'smart', rule: x.rule }); toast('Group made: ' + x.name); await loadGroups(true); await route();
      const h = document.querySelector('#grp-suggest h2') || document.querySelector('#grp-yours h2'); if (h) { h.setAttribute('tabindex', '-1'); h.focus(); } });
  },
  async grpaddall() {
    const list = (PGROUPS && PGROUPS.suggestions) || []; if (!list.length || !(await needName())) return;
    await guard(async () => { for (const x of list) await api('POST', '/api/groups', { name: x.name, kind: 'smart', rule: x.rule }); toast(`${list.length} groups made`); await loadGroups(true); route(); });
  },
  async grprm(el) {
    const d = CURG; if (!d || !(await needName())) return;
    await guard(async () => { await api('POST', `/api/groups/${d.id}/members`, { remove: [el.dataset.code] }); toast(`${plantName(el.dataset.code)} taken out of ${d.name}`); await loadGroups(true); route(); });
  },
  grpcare() { groupCare(); },
  grpmove() { groupMove(); },
  grpset() { groupSet(); },
  async grpundo(el) {
    if (!(await needName())) return;
    if (!(await confirmBox('Undo this change?', 'Each plant goes back to what it had before, unless it has been changed again since.', 'Undo the change'))) return;
    await guard(async () => { const r = await api('POST', `/api/bulk/${el.dataset.id}/undo`); toast(`Undone for ${r.undone.length} plant${r.undone.length === 1 ? '' : 's'}` + (r.kept.length ? `. ${r.kept.length} left as they are: changed again since` : '')); await loadCodes(true); route(); });
  },
  grpshow(el, e) { if (e) e.preventDefault(); G.group = String(el.dataset.id); gSave(); go('#/plants'); },
  plgroups() { plantGroupsDialog(); },
  tickall(el) { const fs = el.closest('fieldset'); fs.querySelectorAll('li:not([hidden]) input[name=code]').forEach(x => { x.checked = el.dataset.on === '1'; }); },
  grprulerow() {
    const box = document.getElementById('rule-rows'); if (!box) return;
    const n = box.querySelectorAll('.rule-row').length; if (n >= 8) { toast('A rule can have up to 8 parts.', true); return; }
    box.insertAdjacentHTML('beforeend', rend(ruleRow({ field: 'genus', op: 'is', value: '' }, n)));
    box.querySelector('.rule-row:last-child select').focus();
  },
  grprulerm(el) { const row = el.closest('.rule-row'); const box = row.parentElement; row.remove();
    box.querySelectorAll('.rule-row').forEach((r, i) => { r.dataset.row = i; r.querySelector('legend').textContent = 'Part ' + (i + 1); }); rulePreview(); box.querySelector('select').focus(); },
  clearfilters() { Object.assign(G, { q: '', plan: '', health: '', low: false, needs: false, group: '', status: 'active', site: '', home: '', area: '', spot: '' }, Object.fromEntries(MORE_KEYS.map(k => [k, '']))); MOREOPEN = false; gSave(); route(); },
  clearplace() { G.area = ''; G.spot = ''; gSave(); route(); },
  heatf(el) { Object.assign(G, { q: '', needs: false, status: 'active', heat: el.dataset.heatf }); gSave(); go('#/plants'); },   // 1.36.0: from the Weather page's summer counts
  plan(el) { G.plan = G.plan === el.dataset.plan ? '' : el.dataset.plan; document.querySelectorAll('.ledger button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.plan === G.plan))); drawGrid(); },
  pick(el) { PIDX = +el.dataset.i; repaintPhotos(); },
  zoom() { const c = curPhoto(); if (c) modal(html`<form method="dialog"><img src="${photoUrl(c.file)}" alt="${c.caption || CUR.p.common_name}"><p class="cap">${c.caption}</p><button class="btn" value="ok" autofocus>Close</button></form>`, 'photo'); },
  zoomloose(el) { modal(html`<form method="dialog"><img src="${photoUrl(el.dataset.file)}" alt="${el.dataset.cap}"><p class="cap">${el.dataset.cap}</p><button class="btn" value="ok" autofocus>Close</button></form>`, 'photo'); },
  copyreq() { return copyRequest(); },
  print() { window.print(); },
  async mainphoto() { if (!(await needName())) return; await guard(async () => { await api('PATCH', '/api/photos/' + curPhoto().id, { is_primary: true }); toast('Main photo changed. It now shows on the Plants page and care cards.'); await loadCodes(true); await reloadPlant(0); }); },
  async capedit() {
    if (!(await needName())) return;
    const c = curPhoto();
    const r = await modal(html`<form method="dialog"><h2>Photo caption</h2><label class="f">Caption<input type="text" name="c" maxlength="200" value="${c.caption}"></label>
      <div class="row"><button class="btn" value="ok">Save caption</button><button class="btn ghost" value="cancel">Cancel</button></div></form>`);
    if (r !== 'ok') return;
    await guard(async () => { await api('PATCH', '/api/photos/' + c.id, { caption: dlg.querySelector('[name=c]').value }); toast('Caption saved'); await reloadPlant(); });
  },
  async movephoto() {
    if (!(await needName())) return;
    const t = await pickPlant('Move photo', 'Choose the plant this photo belongs to. Both plants get a new version in their history.', true);
    if (t === null) return;
    await guard(async () => { await api('PATCH', '/api/photos/' + curPhoto().id, { plant_code: t }); toast('Photo moved'); await reloadPlant(0); });
  },
  async rmphoto() {
    if (!(await needName())) return;
    if (!(await confirmBox('Remove this photo?', 'It leaves this page. The file is kept in the photos_deleted folder inside your data folder, so it can be recovered by hand.', 'Remove photo', true))) return;
    await guard(async () => { await api('DELETE', '/api/photos/' + curPhoto().id); toast('Photo removed'); await reloadPlant(0); });
  },
  readsec(el) { const sec = el.closest('section'); const h = sec && sec.querySelector('h2'); readAloud(sec, el, h ? h.textContent.trim() : 'this section'); },
  readpage(el) { readAloud(readTarget(), el, 'this page'); },
  readstop() { stopReading(); },
  voicetest() { stopReading(true); readAloudText('This is how plant pages will sound. Philodendron Pink Princess, P 0 2 9. Damaged below 55 degrees.'); },
  shortcuts() { shortcutsDialog(); },
  async movein(el) { await moveSite(el, 'Indoors'); },
  frosthide(el) { try { localStorage.setItem('plantdb.frosthide', fzSig()); } catch (e) { /* not remembered */ } const b = el.closest('.fz-banner'); if (b) b.remove(); toast('Frost warning hidden. It comes back if the forecast changes.'); },
  async frostin(el) {
    if (!(await needName())) return;
    const y = window.scrollY, code = el.dataset.code;
    await guard(async () => { await api('POST', '/api/plants/' + enc(code) + '/site', { site: 'Indoors' }); toast(el.dataset.name + ' moved indoors'); await fzReload(y, code); });
  },
  async frostcover(el) { await fzMark(el, 'covered'); },
  async frostundo(el) { await fzMark(el, null); },
  async frostallin(el) {
    const grp = FZ_GROUPS.find(g => g[0] === el.dataset.group); if (!grp || !FROST) return;
    const g = FROST.plants.filter(grp[3]).filter(p => !p.done);
    if (!(await needName())) return;
    if (!(await confirmBox(`Mark ${g.length} plants as moved indoors?`, 'Their Location changes to Indoors, so they leave the cold-night list and the frost warnings. You can change any of them back on its page.', 'Moved them indoors'))) return;
    const y = window.scrollY;
    await guard(async () => { for (const p of g) await api('POST', '/api/plants/' + enc(p.code) + '/site', { site: 'Indoors' }); toast(g.length + ' plants moved indoors'); await fzReload(y); });
  },
  async frostallcover(el) {
    const grp = FZ_GROUPS.find(g => g[0] === el.dataset.group); if (!grp || !FROST) return;
    const g = FROST.plants.filter(grp[3]).filter(p => !p.done);
    if (!(await needName())) return;
    if (!(await confirmBox(`Mark ${g.length} plants as covered?`, 'Each one is ticked off for its next cold night only; it comes back on the list for the night after. This does not change their pages.', 'Mark as covered'))) return;
    const y = window.scrollY;
    await guard(async () => { for (const p of g) await api('POST', '/api/frost/done', { date: p.next.date, code: p.code, what: 'covered' }); toast(g.length + ' plants marked as covered'); await fzReload(y); });
  },
  async moveout(el) { await moveSite(el, 'Outdoors'); },
  async care(el) {
    if (!(await needName())) return;
    const k = el.dataset.kind, code = el.dataset.code;
    await guard(async () => { const r = await api('POST', '/api/care', { plant: code, kind: k }); careUndoToast((k === 'water' ? 'Watered: ' : k === 'check' ? 'Checked, still moist: ' : (CARE_WORD[k] || k) + ': ') + el.dataset.name + offWhen(r), r && r.ids, code); await careRefresh(code); });
  },
  async careall(el) {
    const codes = el.dataset.codes.split(',').filter(Boolean); if (!codes.length) return;
    if (!(await needName())) return;
    if (!(await confirmBox(`Mark ${codes.length} plants as watered today?`, 'Each one gets a "Watered" entry for today in its care log. You can remove any of them on the plant\'s page.', 'Mark as watered'))) return;
    await guard(async () => { const r = await api('POST', '/api/care', { plants: codes, kind: el.dataset.kind }); careUndoToast(codes.length + ' plants marked as watered' + offWhen(r), r && r.ids); await careRefresh(); });
  },
  async waterall() {                    // 1.21.0: Plants page, every plant the filters show; 1.58.0: at one home (waterAllList)
    const WAL = waterAllList(), shown = WAL.list;
    if (WAL.untended) { toast(`Plants at ${WAL.home.name} are cared for outside the app, so Water all leaves them out. You can still log one on its own page.`); return; }
    if (!shown.length) return;
    if (!(await needName())) return;
    await guard(async () => {
      const W = await api('GET', '/api/water'), done = new Set(W.plants.filter(w => w.last_water === W.today).map(w => w.code));
      const todo = shown.filter(p => !done.has(p.code)), skip = shown.length - todo.length;
      if (!todo.length) { toast(`All ${shown.length} plants shown were already watered today.`); return; }
      if (!(await confirmBox(`Mark ${todo.length} plant${todo.length === 1 ? '' : 's'} as watered today?`,
        `These are the plants shown with your filters${WAL.home ? ` at ${WAL.home.name}` : ''}.${WAL.away ? ` The ${WAL.away} shown at other homes ${WAL.away === 1 ? 'is' : 'are'} left out.` : ''}${skip ? ` ${skip} of them ${skip === 1 ? 'was' : 'were'} already watered today and ${skip === 1 ? 'is' : 'are'} skipped.` : ''} Each gets a "Watered" entry for today in its care log.`, 'Mark as watered'))) return;
      const r = await api('POST', '/api/care', { plants: todo.map(p => p.code), kind: 'water' });
      const nn = r.offline ? todo.length : r.ids.length, sk = skip + (r.offline ? 0 : (r.skipped || []).length);   // the server also skips any it finds already watered
      careUndoToast(`${nn} plant${nn === 1 ? '' : 's'} marked as watered${sk ? ` (${sk} already watered today ${sk === 1 ? 'was' : 'were'} skipped)` : ''}${offWhen(r)}`, r.ids);
    });
  },
  careother(el) { return careDialog(el.dataset.code, el.dataset.name); },
  async caredel(el) {
    if (!(await needName())) return;
    if (!(await confirmBox('Remove this entry?', el.dataset.what + '. The change log keeps a record that it was removed.', 'Remove', true))) return;
    await guard(async () => { await api('DELETE', '/api/care/' + el.dataset.id); toast('Entry removed'); await loadCarePlant(); });
  },
  todayneeds() { Object.assign(G, { q: '', plan: '', health: '', low: false, needs: true }); gSave(); go('#/plants'); },
  async archive(el) {
    if (!(await needName())) return;
    const to = el.dataset.to === '1';
    if (to && !(await confirmBox('Archive ' + CUR.p.common_name + '?', 'It disappears from the main list but nothing is deleted. You can move it back at any time.', 'Archive', false))) return;
    await guard(async () => { await api('POST', '/api/plants/' + enc(CUR.p.code) + '/status', { archived: to }); toast(to ? 'Archived' : 'Moved back'); await reloadPlant(); });
  },
  async viewver(el) {
    await guard(async () => {
      const v = await api('GET', '/api/plants/' + enc(CUR.p.code) + '/versions/' + el.dataset.v);
      const f = v.snapshot.fields;
      await modal(html`<form method="dialog"><h2>Version ${v.version}</h2><p class="muted">Saved ${when(v.changed_at)} by ${v.changed_by}. ${v.summary}</p>
        <dl class="dl">${META.fields.filter(x => f[x.name] != null && f[x.name] !== '').map(x => html`<dt>${x.label}</dt><dd>${f[x.name]}</dd>`)}</dl>
        <div class="row" style="margin-top:14px"><button class="btn" value="ok" autofocus>Close</button></div></form>`);
    });
  },
  async restore(el) {
    if (!(await needName())) return;
    const n = el.dataset.v;
    if (!(await confirmBox('Restore the text from version ' + n + '?', 'This saves a new version with the text from version ' + n + '. Nothing is deleted, and photos stay as they are now.', 'Restore', false))) return;
    await guard(async () => { const r = await api('POST', '/api/plants/' + enc(CUR.p.code) + '/restore/' + n); toast(r.changed ? 'Restored as version ' + r.version : 'That version already matches the current text'); await reloadPlant(); });
  },
  tlpick(el) {
    const D = TL.data; if (!D) return;
    TL.b = el.dataset.file; if (!TL.a || TL.a === TL.b) TL.a = D.photos[0].file === TL.b && D.photos[1] ? D.photos[1].file : D.photos[0].file;
    tlRender(); const c = document.querySelector('#tl-box .tl-cmp'); if (c) { c.scrollIntoView({ block: 'center' }); }
    const day = f => tlShort((D.photos.find(x => x.file === f) || {}).added_at);
    toast(`Comparing the photo from ${day(TL.a)} (left) with the one from ${day(TL.b)} (right)`);
  },
  async assign(el) {
    if (!(await needName())) return;
    const t = await pickPlant('Assign photo', 'Choose the plant this photo shows.', false);
    if (!t) return;
    await guard(async () => { await api('PATCH', '/api/photos/' + el.dataset.id, { plant_code: t }); toast('Assigned to ' + t); route(); });
  },
  async rmloose(el) {
    if (!(await needName())) return;
    if (!(await confirmBox('Remove this photo?', 'The file is kept in the photos_deleted folder inside your data folder.', 'Remove photo', true))) return;
    await guard(async () => { await api('DELETE', '/api/photos/' + el.dataset.id); toast('Photo removed'); route(); });
  },
  async tododel(el) { if (!(await needName())) return; await guard(async () => { await api('DELETE', '/api/to-photograph/' + el.dataset.id); route(); }); },
};
document.addEventListener('change', e => { const el = e.target; if (el.dataset && el.dataset.dvshare && window.PlantSync) { window.PlantSync.share(el.dataset.dvshare, el.checked);
  toast(el.checked ? 'These settings now follow you to other devices' : 'These settings now stay on this device'); } }, true);
const changeActs = {
  // 1.48.0: a home's country, units default or seasons (Homes and places)
  async placesite(el) {
    const k = el.dataset.k, v = el.value.trim();
    await guard(async () => {
      await api('PUT', '/api/places/' + el.dataset.id, { [k]: v });
      META = await api('GET', '/api/meta');
      toast(k === 'country' ? 'Country saved' : k === 'units' ? 'Units for this home saved' : k === 'tended' ? (v === '0' ? 'Care there is done outside the app' : 'Care there is logged in this app') : 'Seasons saved');
      if (k !== 'country') { ROUTE_FRESH = true; await route(); }        // (and 1.58.0: care, which changes Water all)        // units and seasons change what pages show
      const n = document.querySelector(`[data-act=placesite][data-id="${el.dataset.id}"][data-k="${k}"]`); if (n) n.focus({ preventScroll: true });
    });
  },
  // 1.47.0: units in Display. A new region resets the three; one unit changed by hand stands until the region changes.
  async unitset(el) {
    const raw = unitsSet({ [el.dataset.u]: el.value });
    const U = unitsGet(); for (const k of ['temp', 'len', 'rain']) { const o = document.getElementById('pref-u-' + k); if (o) o.value = U[k]; }
    try { await api('PUT', '/api/me/prefs', { units: Object.keys(raw).length ? JSON.stringify(raw) : null }); } catch (e) { /* offline: prefs.js sends it later */ }   // at once, so the server's sentences change too
    ROUTE_FRESH = true; route();                  // the page behind the window redraws in the new units, from fresh answers
  },
  idmodeset(el) {                     // 5b: Identify's question, per page, in Display
    const v = idModePref(); if (el.value === 'ask') delete v[el.dataset.page]; else v[el.dataset.page] = el.value;
    idModeSave(v);
    const sel = document.querySelector('[data-act=idmode]'); if (sel && el.dataset.page === 'identify' && el.value !== 'ask') { sel.value = el.value; ID.mode = el.value; }
  },
  async ctphoto(el) {                 // 1.29.0: photos of a pot or tray
    if (!el.files.length || !(await needName())) return;
    const fd = new FormData(); [...el.files].forEach(f => fd.append('files', f));
    await guard(async () => { const x = await api('POST', '/api/containers/' + el.dataset.id + '/photos', null, fd); toast('Photo added'); ctRedraw(x); });
  },
  grprulefield(el) {      // a different thing to look at: redraw this part with the right comparisons and value suggestions
    const row = el.closest('.rule-row'), i = +row.dataset.row;
    row.outerHTML = rend(ruleRow({ field: el.value, value: '' }, i));
    const again = document.querySelector(`.rule-row[data-row="${i}"] select[name=rf]`); if (again) again.focus();
    rulePreview();
  },
  grprulematch() { rulePreview(); },
  grpsetfield(el) { const F = Object.fromEntries(META.fields.map(x => [x.name, x])), box = document.getElementById('gset-input'); if (box) box.innerHTML = rend(fieldInput(F[el.value], '')); },
  tlsel(el) { TL[el.dataset.side] = el.value; tlRender(); const s = document.querySelector(`select[data-act=tlsel][data-side="${el.dataset.side}"]`); if (s) s.focus(); },
  tlkind(el) { if (el.checked) TL.hide.delete(el.value); else TL.hide.add(el.value); tlRender(); const c = document.querySelector(`input[data-act=tlkind][value="${el.value}"]`); if (c) c.focus(); },
  async site(el) {
    const was = CUR.p.site || 'Outdoors';
    if (!(await needName())) { el.value = was; return; }
    await guard(async () => { await api('POST', '/api/plants/' + enc(CUR.p.code) + '/site', { site: el.value }); toast('Location: ' + el.value); FROST_AT = 0; await reloadPlant(); });
  },
  async addphotos(el) {
    if (!el.files.length) return;
    if (!(await needName())) { el.value = ''; return; }
    const files = await photoCheck([...el.files], el); if (!files) { el.value = ''; return; }
    const fd = new FormData(); files.forEach(f => fd.append('files', f));
    toast('Uploading ' + files.length + ' photo(s)');
    await guard(async () => { await api('POST', '/api/plants/' + enc(CUR.p.code) + '/photos', undefined, fd); toast('Photos added'); await reloadPlant(9999); });
  },
  async addloose(el) {
    if (!el.files.length) return;
    if (!(await needName())) { el.value = ''; return; }
    const files = await photoCheck([...el.files], el); if (!files) { el.value = ''; return; }
    const fd = new FormData(); files.forEach(f => fd.append('files', f));
    await guard(async () => { await api('POST', '/api/photos', undefined, fd); toast('Photos added'); route(); });
  },
  preptrait(el) { prepSaveTraits({ [el.dataset.k]: el.value }, `select[data-act=preptrait][data-k="${el.dataset.k}"]`, (el.dataset.k === 'leaf_type' ? 'Leaf type: ' : 'Pot size: ') + (el.value || 'not set')); },
  async preptick(el) {        // 1.41.1: a step's tick box: ticking logs it today, unticking takes back the last time
    const k = el.dataset.k, code = el.dataset.code, f = prepFocus(el, code), on = el.checked;
    if (!(await needName())) { el.checked = !on; return; }
    if (on) { await guard(async () => { await api('POST', '/api/care', { plant: code, kind: 'prep_' + k }); toast('Saved: ' + PREP_CARE['prep_' + k]); }); }
    else {
      const D = document.getElementById('prep-box') ? (PREP.data && PREP.data.code === code ? PREP.data : null) : (PREP.list ? PREP.list.plants.find(p => p.code === code) : null);
      const last = D ? (D.log || []).filter(x => x.kind === 'prep_' + k).pop() : null;
      if (last) await guard(async () => { await api('DELETE', '/api/care/' + last.id); toast('Removed: ' + PREP_CARE['prep_' + k] + ', ' + relDay(last.done_on)); });
    }
    await prepAfterChange(code, f);
  },
  preppest(el) {
    const got = [...document.querySelectorAll('input[data-act=preppest]:checked')].map(x => x.value);
    prepSaveTraits({ pests_found: got }, `input[data-act=preppest][value="${el.value}"]`, got.length ? 'Pests found: ' + got.join(', ') : 'No pests found');
  },
  fcrange(el) { FC.range = el.value; fcRefresh('select[data-act=fcrange]'); },
  fcopen(el) { FC.open = el.checked; fcRefresh('input[data-act=fcopen]'); },
  async tododone(el) { if (!(await needName())) { el.checked = !el.checked; return; } await guard(async () => { await api('PATCH', '/api/to-photograph/' + el.dataset.id, { done: el.checked }); route(); }); },
};
// back outside (prototype: proto/move-outside)
Object.assign(acts, {
  async boporch(el) { await boMove(el, 'Covered porch'); },
  async boout(el) { await boMove(el, 'Outdoors'); },
  async boleave(el) {
    if (!(await needName())) return;
    const y = window.scrollY;
    await guard(async () => { await api('POST', '/api/outside/porch', { code: el.dataset.code, action: 'clear' }); toast(el.dataset.name + ' stays on the porch. The reminder is off.'); BO_AT = 0; await route(); window.scrollTo(0, y); (document.querySelector('.bo-porchrow button') || document.querySelector('main h1')).focus({ preventScroll: true }); });
  },
});
function wtFocusTop() { const t = document.querySelector('#wx-table .pager'); if (t) t.scrollIntoView({ block: 'nearest' }); }
let PLACE_RESULTS = [];
const formActs = {
  async bkcopies(form) {             // 1.33.0
    const b = { url: form.elements.url.value.trim() }; if (form.elements.token.value) b.token = form.elements.token.value;
    await api('PUT', '/api/backups/copies', b); toast('Saved'); route();
  },
  audf() { clearTimeout(AUD.t); AUD.offset = 0; audLoad(); },       // Enter in the search box searches straight away
  async bknow(form) {
    if (!(await needName())) return;
    const f = form.elements;
    await guard(async () => { const r = await api('POST', '/api/backups', { photos: f.photos.checked, note: f.note.value.trim() }); if (!r.started) toast('A backup is already running', true); bkPoll(); });
  },
  async bkset(form) {
    if (!(await needName())) return;
    const f = form.elements;
    await guard(async () => { await api('PUT', '/api/backups/settings', { enabled: f.enabled.checked, freq: f.freq.value, hour: f.hour.value, keep: f.keep.value, photos: f.photos.checked }); toast('Automatic backup settings saved'); route(); });
  },
  async placesearch(form) {
    const q = form.elements.q.value.trim(), el = document.getElementById('place-results');
    if (q.length < 2) { toast('Type at least 2 letters of the town or city.', true); return; }
    el.innerHTML = rend(html`<p class="loading" role="status">Searching</p>`);
    try { PLACE_RESULTS = await api('GET', '/api/places/search?q=' + enc(q)); }
    catch (e) { el.innerHTML = rend(html`<p class="notice bad">${e.message}</p>`); return; }
    el.innerHTML = rend(PLACE_RESULTS.length ? html`<p>${PLACE_RESULTS.length} found. Choose the right one:</p><ul class="place-res">${PLACE_RESULTS.map((r, i) => html`<li><span><strong>${r.label}</strong><br><span class="hint">${r.lat}, ${r.lon}, ${r.tz}${r.elevation_m != null ? `, ${Math.round(r.elevation_m * 3.281)} ft up` : ''}${r.population ? `, ${num(r.population)} people` : ''}</span></span><button class="btn small" type="button" data-act="placepick" data-i="${i}">Add ${r.name}</button></li>`)}</ul>`
      : html`<p class="notice">Nothing found for "${q}". Check the spelling, try the nearest larger town, or type the place in yourself below.</p>`);
  },
  async libareafind(form) {
    const q = form.elements.q.value.trim(), el = document.getElementById('libarea-res');
    if (q.length < 2) { toast('Type at least 2 letters of the place.', true); return; }
    el.innerHTML = rend(html`<p class="loading" role="status">Searching</p>`);
    let R; try { R = await api('GET', '/api/library/areas/search?q=' + enc(q)); } catch (e) { el.innerHTML = rend(html`<p class="notice bad">${e.message}</p>`); return; }
    el.innerHTML = rend(R.length ? html`<p>${R.length} found. Choose the right one:</p><ul class="place-res">${R.map(r => html`<li><span><strong>${r.name}</strong><br><span class="hint">${r.kind}</span></span>
      <button class="btn small" type="button" data-act="libareaadd" data-pid="${r.place_id}" data-name="${r.name}">Add and download</button></li>`)}</ul>`
      : html`<p class="notice">Nothing found for "${q}". Check the spelling or try a larger area.</p>`);
  },
  sevgo(form) { return sevGo(form); },
  async whareaadd(form) { if (!(await needName())) return;
    await guard(async () => { await api('POST', '/api/where/areas', { home_id: form.dataset.home || null, side: form.dataset.side, name: form.elements.name.value, sheltered: form.elements.sheltered.checked });
      META = await api('GET', '/api/meta'); toast('Added'); route(); }); },
  async whspotadd(form) { if (!(await needName())) return;
    await guard(async () => { await api('POST', '/api/where/spots', { area_id: +form.dataset.aid, name: form.elements.name.value }); META = await api('GET', '/api/meta'); toast('Spot added'); route(); }); },
  placeadd(form) { const f = form.elements; return addPlace({ name: f.name.value, lat: f.lat.value, lon: f.lon.value, tz: f.tz.value }); },
  wtgo(form) {
    const max = +form.elements.page.dataset.max, n = Math.round(+form.elements.page.value);
    if (!(n >= 1 && n <= max)) { toast(`Type a page number from 1 to ${max.toLocaleString()}.`, true); form.elements.page.focus(); return; }
    WT.page = n; loadWxTable().then(wtFocusTop);
  },
  new: submitForm, edit: submitForm,
  async wxloc(form) {
    if (!(await needName())) return;
    const f = form.elements;
    await guard(async () => { const r = await api('PUT', '/api/places/' + WX.place.id, { name: f.name.value, lat: f.lat.value, lon: f.lon.value, tz: f.tz.value, enabled: f.enabled.checked, detail_years: f.detail_years.value });
      toast(r.moved ? 'Saved. The place moved: weather already stored stays as it was, and new readings come from the new spot.' : 'Saved'); route(); });
  },
  async wxback(form) {
    const start = form.elements.start.value;
    if (!start) { toast('Pick a start date first.', true); return; }
    await guard(async () => { const r = await api('POST', '/api/weather/refresh', { backfill_start: start, loc: WX.place.id }); toast(r.started ? 'Loading history in the background' : 'An update is already running'); document.body.dataset.job = '1'; route(); });
  },
  async todo(form) {
    const f = form.elements, label = f.label.value.trim();
    let note = f.note.value.trim();
    if (!label) { toast('Type what to photograph first.', true); return; }
    const code = f.plant.value;
    if (code && !(label + ' ' + note).includes(code)) note = (note ? note + ' ' : '') + `Plant: ${code}.`;
    if (!(await needName())) return;
    await guard(async () => { await api('POST', '/api/to-photograph', { label, note }); toast('Added'); route(); });
  },
  async base(form) {
    if (!(await needName())) return;
    await guard(async () => { await api('PUT', '/api/settings', { base_url: form.elements.base.value }); toast('Address saved'); route(); });
  },
};
