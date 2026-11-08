/* Plant record front end: watering and the Today page, undo, getting plants ready to come inside, Copy my answers, dates, calendars, fertilizer. One of the files app.js was split into in 1.32.0; they load in order (index.html) and share one scope,
   so a function here may call any other. Plain JavaScript, no inline handlers (the server's content policy forbids them). */
'use strict';

// ---------- watering, care log and the Today page (added in 1.8.0) ----------
const CARE_WORD = { water: 'Watered', check: 'Checked: still moist', repot: 'Repotted', prune: 'Pruned', pests: 'Treated for pests', note: 'Note' };
function relDay(d) {
  if (!d) return '';
  const t = todayStr(), n = daysBetween(d, t);
  if (n === 0) return 'today'; if (n === 1) return 'yesterday'; if (n === -1) return 'tomorrow';
  const name = parseYmd(d).toLocaleDateString([], { weekday: 'long' }), md = parseYmd(d).toLocaleDateString([], { month: 'short', day: 'numeric' });
  if (n > 1 && n < 7) return 'last ' + name + ' (' + md + ')';
  if (n < -1 && n > -7) return name + ' (' + md + ')';
  return md;
}
function waterWords(w) {
  if (!w) return '';
  if (w.state === 'unknown') return 'No watering logged yet. Press Watered when you water it, and reminders start from there.';
  const od = w.overdue, when = od > 0 ? `${od} day${od === 1 ? '' : 's'} overdue (due ${relDay(w.next)})` : od === 0 ? 'due today' : `next check ${relDay(w.next)}`;
  const rain = w.last_rain && (!w.last_water || w.last_rain > w.last_water) ? ` Rain of ${rainF(w.rain_in)} ${relDay(w.last_rain)} was counted as a watering.` : '';
  const chk = w.last_check && w.last_check >= (w.last_water || '') && w.last_check >= (w.last_rain || '') ? ` Checked ${relDay(w.last_check)}: still moist.` : '';
  return `${when[0].toUpperCase() + when.slice(1)}. ${w.last_water ? 'Last watered ' + relDay(w.last_water) + '.' : 'No watering logged yet.'}${rain}${chk} Check about every ${w.every} day${w.every === 1 ? '' : 's'}: it ${w.why === 'set on this page' ? 'is set on this page' : w.why}${w.weather ? '; ' + w.weather : ''}.`;
}
function careQuick(p) {
  return html`<div class="quick noprint" role="group" aria-label="Quick care for this plant">
    <p class="quick-status" id="quick-status">&nbsp;</p>
    <div class="quick-btns">
      <button class="btn" type="button" data-act="care" data-kind="water" data-code="${p.code}" data-name="${p.common_name}">Watered today</button>
      <button class="btn ghost" type="button" data-act="care" data-kind="check" data-code="${p.code}" data-name="${p.common_name}">Checked: still moist</button>
      <button class="btn ghost" type="button" data-act="fertlog" data-code="${p.code}">Log feeding</button>
      <label class="btn ghost quick-photo">Add photos<input type="file" accept="image/*" multiple data-act="addphotos" class="sr"></label>
      <button class="btn ghost" type="button" data-act="careother" data-code="${p.code}" data-name="${p.common_name}">Log other care</button>
    </div>
    <p class="hint" id="water-done-note" hidden>Already watered today, so "Watered today" is off until tomorrow. To take it back, use Undo in the message, or Remove in the care log.</p></div>`;
}
async function loadCarePlant() {
  const box = document.getElementById('care-plant'); if (!box || !CUR) return;
  const code = CUR.p.code;
  let W, log;
  try { [W, log] = await Promise.all([api('GET', '/api/water'), api('GET', '/api/care?n=12&plant=' + enc(code))]); }
  catch (e) { box.innerHTML = rend(html`<p class="notice bad">Could not load the watering record: ${e.message}</p>`); return; }
  if (!CUR || CUR.p.code !== code) return;
  const w = W.plants.find(x => x.code === code);
  const qs = document.getElementById('quick-status'); if (qs) qs.textContent = w ? 'Water: ' + waterWords(w) : '';
  // 1.21.0: once watered today, "Watered today" is switched off until tomorrow (Undo or Remove in the care log switch it back on)
  const wb = document.querySelector('.quick-btns [data-act=care][data-kind=water]'), wn = document.getElementById('water-done-note');
  const done = !!(w && w.last_water === W.today);
  if (wb) { wb.disabled = done; wb.classList.toggle('done-today', done); wb.textContent = done ? '✓ Watered today' : 'Watered today'; }
  if (wn) wn.hidden = !done;
  box.innerHTML = rend(html`<div class="verdict-box v-${w && w.state === 'due' ? 'due' : 'wait'}" role="status"><h3>Watering</h3><p>${w ? waterWords(w) : ''}</p>
      <p class="hint">Change the gap with "Check for water every (days)" in Edit this page. Rain of ${rainF(W.rain_counts_in)} or more counts as a watering for plants whose Location is Outdoors.</p></div>
    <h3>Care log</h3>${log.length ? html`<ul class="care-log">${log.map(e => html`<li><strong>${CARE_WORD[e.kind] || e.kind}</strong> ${relDay(e.done_on)}${e.note ? ': ' + e.note : ''} <span class="muted">(${e.created_by})</span>
      ${e.pending ? html`<span class="muted">(not sent yet)</span>` : html`<button class="btn small ghost noprint" type="button" data-act="caredel" data-id="${e.id}" data-what="${(CARE_WORD[e.kind] || e.kind) + ' ' + relDay(e.done_on)}" aria-label="Remove: ${(CARE_WORD[e.kind] || e.kind)} ${relDay(e.done_on)}">Remove</button>`}</li>`)}</ul>`
      : html`<p class="muted">Nothing logged yet. Use the buttons near the top of the page.</p>`}`);
  await featAdds(['plant', code], true);          // 1.46.0: what feature modules add beside the care part (Turned today, say) draws again with it
}
async function careDialog(code, name) {
  if (!(await needName())) return;
  const r = await modal(html`<form method="dialog"><h2>Log care for ${name}</h2>
    <label class="f">What did you do?<select name="kind"><optgroup label="Care">${Object.entries(CARE_WORD).filter(([k]) => !k.startsWith('prep_')).map(([k, v]) => html`<option value="${k}" ${k === 'repot' ? raw('selected') : ''}>${v}</option>`)}</optgroup>
      <optgroup label="Getting ready to come inside">${Object.entries(CARE_WORD).filter(([k]) => k.startsWith('prep_')).map(([k, v]) => html`<option value="${k}">${v}</option>`)}</optgroup></select></label>
    <label class="f">When<input type="date" name="day" value="${todayStr()}" max="${todayStr()}"></label>
    <label class="f">Note (optional)<input type="text" name="note" maxlength="500" placeholder="For example: moved to a 10 inch pot"></label>
    <div class="row"><button class="btn" value="ok">Save</button><button class="btn ghost" value="cancel">Cancel</button></div></form>`);
  if (r !== 'ok') return;
  const f = dlg.querySelector('form');
  await guard(async () => { const x = await api('POST', '/api/care', { plant: code, kind: f.elements.kind.value, done_on: f.elements.day.value, note: f.elements.note.value }); careUndoToast('Saved: ' + CARE_WORD[f.elements.kind.value] + ' for ' + name, x && x.ids, code); await careRefresh(code); });
}
async function careRefresh(code) {
  if (document.getElementById('care-plant')) return loadCarePlant();
  const y = window.scrollY; await route(); window.scrollTo(0, y);
  const f = (code && document.querySelector(`.job[data-code="${code}"] button`)) || document.querySelector('.job button') || document.querySelector('main h1');
  if (f) f.focus({ preventScroll: true });
}
function jobRow(p, words, btns) {
  return html`<li class="job" data-code="${p.code}">${p.photo ? html`<img src="${thumbUrl(p.photo)}" alt="" loading="lazy" width="64" height="64">` : html`<span class="job-nophoto" aria-hidden="true"></span>`}
    <div class="job-txt"><a class="nm" href="#/plant/${enc(p.code)}">${p.common_name}</a> <span class="muted">${p.code}</span><div>${words}</div></div>
    <div class="job-acts">${btns}</div></li>`;
}
// ---------- undo right after a care button (prototype: proto/undo-care) ----------
// "Watered", "Still moist", "Mark all as watered" and "Log other care" show a message with an Undo button instead of a
// plain toast. Undo removes exactly the entries that press made (by id), so nothing else in the care log is touched.
// The message stays for UNDO_SECS, and the countdown stops while the pointer or keyboard focus is on it. U also undoes.
const UNDO_SECS = 30;
let UNDO = null;      // {el, ids, code, left, timer}
function careUndoClose() {
  if (!UNDO) return;
  clearInterval(UNDO.timer); const el = UNDO.el, hadFocus = el.contains(document.activeElement); UNDO = null; el.remove();
  if (hadFocus) { const m = document.querySelector('main h1'); if (m) { m.setAttribute('tabindex', '-1'); m.focus({ preventScroll: true }); } }
}
function careUndoToast(msg, ids, code) {
  careUndoClose();
  const fn = typeof ids === 'function' ? ids : null;            // 1.29.0: an edit in place: Undo calls fn
  if (!fn && (!Array.isArray(ids) || !ids.length)) { toast(msg); return; }
  const n = fn ? 1 : ids.length, el = document.createElement('div');
  el.className = 'toast undo-toast'; el.setAttribute('role', 'group'); el.setAttribute('aria-label', 'Care saved');
  el.innerHTML = rend(html`<span class="undo-msg" id="undo-msg">${msg}.</span>
    <span class="undo-acts"><button class="btn small" type="button" data-undo="undo" aria-describedby="undo-msg">Undo</button>
    <button class="btn small ghost" type="button" data-undo="close" aria-label="Close this message">Close</button></span>
    <span class="undo-left" aria-hidden="true"></span>`);
  document.getElementById('toasts').appendChild(el);
  UNDO = { el, ids: fn ? [] : ids.slice(), fn, code, left: UNDO_SECS, paused: 0, timer: 0 };
  const left = el.querySelector('.undo-left'), keys = window.PlantPrefs.get().keys === '1' && matchMedia('(any-pointer: fine)').matches;     // no key hint on a phone
  const paint = () => { left.textContent = (n > 1 ? `Undo removes all ${n} entries. ` : '') + `Closes in ${UNDO.left} s${keys ? ' (U undoes it)' : ''}.`; };
  paint();
  const hold = on => { if (UNDO && UNDO.el === el) UNDO.paused = Math.max(0, UNDO.paused + (on ? 1 : -1)); };
  el.addEventListener('pointerenter', () => hold(true)); el.addEventListener('pointerleave', () => hold(false));
  el.addEventListener('focusin', () => hold(true)); el.addEventListener('focusout', () => hold(false));
  UNDO.timer = setInterval(() => {
    if (!UNDO || UNDO.el !== el) return;
    if (UNDO.paused) return;
    UNDO.left -= 1; if (UNDO.left <= 0) careUndoClose(); else paint();
  }, 1000);
}
async function careUndo() {
  if (!UNDO) return;
  if (UNDO.fn) { const f = UNDO.fn; careUndoClose(); await f(); return; }
  const { ids, code } = UNDO, btn = UNDO.el.querySelector('[data-undo=undo]');
  if (btn) btn.disabled = true;
  if (!(await needName())) { if (btn) btn.disabled = false; return; }
  let gone = 0, missing = 0;
  for (const id of ids) {
    try { await api('DELETE', '/api/care/' + id + '?undo=1'); gone++; }
    catch (e) { if (e.status === 404) missing++; else { toast('Could not undo: ' + e.message, true); break; } }
  }
  careUndoClose();
  if (gone) toast(gone === 1 ? 'Undone. The entry was removed from the care log.' : `Undone. ${gone} entries were removed from the care log.`);
  else if (missing) toast('Nothing to undo: someone already removed that entry.');
  await careRefresh(code);
}
document.getElementById('toasts').addEventListener('click', e => {      // its own listener, so this block needs nothing in acts
  const b = e.target.closest && e.target.closest('.undo-toast button'); if (!b) return;
  if (b.dataset.undo === 'undo') careUndo(); else if (b.dataset.undo === 'close') careUndoClose();
});
document.addEventListener('keydown', e => {
  if (!UNDO || (e.key !== 'u' && e.key !== 'U')) return;
  if (e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey || window.PlantPrefs.get().keys !== '1') return;
  if (e.target.closest && e.target.closest('input,textarea,select,[contenteditable="true"],dialog[open]')) return;
  e.preventDefault(); careUndo();
});
// ---------- getting plants ready to come inside (added in 1.9.0) ----------
// Ten ways to keep outdoor pests out of the house. The server rates each one for each plant (from its leaf type, pot
// size, the pests found, its health and the weather); this draws the plant page section, the Coming inside page and
// the Today page jobs, and logs each step to the care log as a "prep_" entry.
const PREP_CARE = { prep_start: 'Started the move-inside checklist', prep_inspect: 'Inspected for pests', prep_potclean: 'Cleaned the pot and saucer', prep_rinse: 'Rinsed with water', prep_wipe: 'Wiped the leaves',
  prep_soap: 'Sprayed insecticidal soap', prep_oil: 'Sprayed horticultural oil', prep_alcohol: 'Dabbed pests with rubbing alcohol', prep_soak: 'Soaked the pot',
  prep_topsoil: 'Refreshed the top of the soil', prep_repot: 'Repotted in fresh soil' };
Object.assign(CARE_WORD, PREP_CARE);          // the care log and "Log other care" know these steps too
const PR_SIGN = { 'Best': '★', 'Good': '✓', 'Use with care': '!', 'Not needed': '–', 'Not for this plant': '✕' };
const prBadge = r => html`<span class="pr-badge pr-${r.toLowerCase().replace(/\s+/g, '-')}"><span aria-hidden="true">${PR_SIGN[r] || ''}</span> ${r}</span>`;
const PREP = { data: null, list: null, open: new Set() };
// 1.40.1: Start the checklist beside a plant's status. 1.41.1: the steps are a checklist of tick boxes instead of one "next step"
// button, on the plant page and inside each plant's fold on the Coming inside page. Every method is listed in order; the ones
// rated Not needed or Not for this plant are marked "Not recommended" but can still be ticked.
function prepActs(D, where) {
  const nm = D.name || D.common_name || D.code, b = [];
  if (!D.started && ['todo', 'apart', 'settled'].includes(D.status))
    b.push(html`<button class="btn small ${D.status === 'todo' ? '' : 'ghost'}" type="button" data-act="prepstart" data-code="${D.code}" aria-label="${nm}: start the checklist">Start the checklist</button>`);
  if (D.started && !D.done_count)
    b.push(html`<button class="btn small ghost" type="button" data-act="prepundo" data-code="${D.code}" data-k="start" data-where="${where}" aria-label="${nm}: undo the start">Undo the start</button>`);
  return b;
}
function prepFocus(el, code) {        // where focus goes after a prep button redraws the page
  if (el.closest('.pr-top')) return '#prep-box .pr-top button';
  const item = el.closest('li.mi-item'); if (item && item.id) return `#${item.id} input[data-act=preptick]`;
  return `details.mi-fold[data-code="${code}"] summary`;
}
const prepRec = m => m.rank >= 2;          // Best, Good and Use with care; Not needed and Not for this plant are not recommended
function prepChecklist(D, where) {
  const nm = D.name || D.common_name || D.code;
  return html`<ol class="mi-list">${D.methods.map((m, i) => {
    const iid = where === 'pg' ? `pm-${m.key}` : `mi-${D.code}-${m.key}`, cid = iid + '-tick', done = m.done.length > 0, rec = prepRec(m);
    return html`<li class="mi-item pm${rec ? '' : ' mi-not'}${done ? ' mi-done' : ''}" id="${iid}">
      <div class="mi-head"><input type="checkbox" id="${cid}" data-act="preptick" data-code="${D.code}" data-k="${m.key}" ${done ? raw('checked') : ''}
          aria-describedby="${iid}-tag">
        <label for="${cid}" class="mi-title"><span class="pm-n">${i + 1}.</span> ${m.title}</label>
        <span id="${iid}-tag">${rec ? prBadge(m.rating) : html`<span class="pr-badge pr-not-rec"><span aria-hidden="true">⊘</span> Not recommended: ${m.rating.toLowerCase()}</span>`}</span></div>
      <div class="mi-body">
        ${done ? html`<p class="pm-done"><strong>Done ${m.done.map(relDay).join(' and ')}.</strong>${m.next_due ? html` Round ${m.done.length + 1} is due ${relDay(m.next_due)}.` : ''}</p>` : ''}
        <p class="pm-why">${m.reason}</p>
        ${done && !m.complete ? html`<p class="row pm-acts"><button class="btn small" type="button" data-act="prepdone" data-code="${D.code}" data-k="${m.key}" aria-label="${nm}: ${m.title.toLowerCase()}, round ${m.done.length + 1} done today">Round ${m.done.length + 1} done today</button></p>` : ''}
        ${m.steps && m.steps.length ? html`<details class="pm-steps"><summary>How to do it</summary><ol>${m.steps.map(x => html`<li>${tText(x)}</li>`)}</ol></details>` : ''}</div></li>`; })}</ol>`;
}
function prepRender() {
  const box = document.getElementById('prep-box'), D = PREP.data; if (!box || !D || box.dataset.code !== D.code) return;
  const o = D.options, nrec = D.methods.filter(prepRec).length;
  box.innerHTML = rend(html`
    ${D.winter_plan !== 'Move indoors' ? html`<p class="hint">Its winter plan is ${D.winter_plan}, so it usually stays outside. If you do bring it in, this is how.</p>` : ''}
    <div class="verdict-box pr-status" role="status"><p><strong>${D.status_word}.</strong> ${D.next}</p>
      ${D.status === 'settled' && !D.started ? html`<p class="hint">Start the checklist if it is new from a store, or came in without a check.</p>` : ''}</div>
    <p class="row pr-top noprint">${prepActs(D, 'top')}<button class="btn small ghost" type="button" data-act="prepjump">Go to the checklist</button></p>
    <fieldset class="pr-traits"><legend>About this plant</legend>
      <p class="hint">These decide which methods suit it. Claude filled in the leaf type from the photos; change anything that is wrong.</p>
      <div class="field-grid">
        <label class="f">Leaf type<select data-act="preptrait" data-k="leaf_type"><option value="">Not set</option>${o.leaf_types.map(x => html`<option ${x === D.leaf_type ? raw('selected') : ''}>${x}</option>`)}</select></label>
        <label class="f">Pot size<select data-act="preptrait" data-k="pot_size"><option value="">Not set</option>${o.pot_sizes.map(x => html`<option ${x === D.pot_size ? raw('selected') : ''}>${x}</option>`)}</select></label>
      </div>
      <fieldset class="pr-pests"><legend>Pests you found</legend>
        <p class="hint">Tick what you see when you inspect it. Leave them all unticked if you found nothing.</p>
        <div class="pr-checks">${o.pests.map(x => html`<label class="chk"><input type="checkbox" data-act="preppest" value="${x}" ${D.pests_found.includes(x) ? raw('checked') : ''}>${x}</label>`)}</div>
      </fieldset>
      ${D.watch.length ? html`<details class="pr-watch"><summary>What this plant often gets (${D.watch.length})</summary><ul>${D.watch.map(x => html`<li>${x}</li>`)}</ul></details>` : ''}
      </fieldset>
    ${D.best.length ? html`<p><strong>Best for this plant:</strong> ${D.best.join(', ')}.</p>` : ''}
    <h3 id="pm-head" tabindex="-1">The checklist, in the order to do it</h3>
    <p class="hint">Tick each step when you have done it; untick it to take back the last time. ${nrec} of the ${D.methods.length} are recommended for this plant. The others are marked Not recommended, and you can still tick them.</p>
    ${prepChecklist(D, 'pg')}
    <p class="hint">After it comes inside, keep it apart from your other houseplants for 3 weeks and check it at every watering. <a href="#/inside">See every plant that is coming inside</a>.</p>`);
}
async function loadPrep(box) {
  try { PREP.data = await api('GET', '/api/plants/' + enc(box.dataset.code) + '/prep'); }
  catch (e) { box.innerHTML = rend(html`<p class="notice bad">Could not load this: ${e.message}</p>`); return; }
  prepRender();
  let jump = null; try { jump = sessionStorage.getItem('plantdb.toprep'); sessionStorage.removeItem('plantdb.toprep'); } catch (e) { /* none */ }
  if (jump === box.dataset.code) {          // from "Open its plan": go to this section, again once the page has settled
    const to = () => { const s = document.getElementById('inside'); if (s) scrollToSection(s); };
    to(); setTimeout(to, 600); setTimeout(to, 1500);
  }
}
new MutationObserver(() => { const b = document.getElementById('prep-box'); if (b && !b.dataset.loaded) { b.dataset.loaded = '1'; loadPrep(b); } })
  .observe(document.getElementById('app'), { childList: true });
async function prepAfterChange(code, focusSel) {      // redraw whatever page is showing, and put focus back where it was
  if (document.getElementById('prep-box')) {
    try { PREP.data = await api('GET', '/api/plants/' + enc(code) + '/prep'); } catch (e) { toast(e.message, true); return; }
    prepRender(); if (document.getElementById('care-plant')) loadCarePlant();
  } else { const y = window.scrollY; await route(); window.scrollTo(0, y); }
  const f = focusSel && document.querySelector(focusSel); if (f) f.focus({ preventScroll: true });
}
async function prepSaveTraits(body, focusSel, said) {
  if (!(await needName())) { prepRender(); return; }
  await guard(async () => {
    const r = await api('POST', '/api/plants/' + enc(PREP.data.code) + '/prep-traits', body);
    PREP.data = r; if (CUR && CUR.p && CUR.p.code === r.code) { CUR.p.version = r.version; Object.assign(CUR.p, { leaf_type: r.leaf_type, pot_size: r.pot_size }); }
    prepRender(); toast(said);
    const f = document.querySelector(focusSel); if (f) f.focus({ preventScroll: true });
  });
}
async function viewInside() {
  const D = await api('GET', '/api/prep'); PREP.list = D;
  const steps = Object.fromEntries(D.methods.map(m => [m.key, m.steps]));      // "How to do it" under each step, as on the plant page
  D.plants.forEach(p => p.methods.forEach(m => { if (!m.steps) m.steps = steps[m.key]; }));
  const c = D.counts, w = D.status_words;
  const groups = ['doing', 'todo', 'ready', 'apart', 'settled'].map(k => [k, D.plants.filter(p => p.status === k)]).filter(g => g[1].length);
  const gHint = { todo: 'Open a plant to see its steps, and tick each one as you do it.',
    settled: 'Already inside. Start the checklist for any that are new from a store, or came in without a check.' };
  const fold = p => {
    const rec = p.methods.filter(prepRec), did = rec.filter(m => m.done.length).length, other = p.methods.filter(m => !prepRec(m) && m.done.length).length;
    return html`<li class="mi-plant"><details class="mi-fold" data-code="${p.code}" ${PREP.open.has(p.code) ? raw('open') : ''}>
      <summary>${p.photo ? html`<img src="${thumbUrl(p.photo)}" alt="" loading="lazy" width="64" height="64">` : html`<span class="job-nophoto" aria-hidden="true"></span>`}
        <span class="mi-sum-txt"><span><strong>${p.name}</strong> <span class="muted">${p.code}</span></span><span>${p.next}</span>
          <span class="pr-sub">${did} of ${rec.length} recommended steps done${other ? `, and ${other} other` : ''}.${p.pests_found.length ? ' Found: ' + p.pests_found.join(', ').toLowerCase() + '.' : ''}</span></span></summary>
      <div class="mi-in">${prepChecklist(p, 'in')}
        <p class="row noprint">${prepActs(p, 'row')}<button class="btn small ghost" type="button" data-act="openprep" data-code="${p.code}" aria-label="${p.name}: open its plan">Open its plan</button></p></div></details></li>`;
  };
  const say = ['todo', 'doing', 'ready', 'apart', 'settled'].filter(k => c[k]).map(k => `${c[k]} ${w[k].toLowerCase()}`).join(', ');
  return {
    title: 'Getting plants ready to come inside',
    html: html`<p class="crumb"><a href="#/winter">Winter plan</a></p><h1>Getting plants ready to come inside</h1>
    <p class="muted">Ten ways to keep ants, mites and other outdoor pests out of the house, and where each plant that is coming inside is up to. Each plant's page rates the methods for that plant, with the steps.</p>
    <div class="verdict-box" role="status"><p><strong>${D.plants.length} ${D.plants.length === 1 ? 'plant' : 'plants'} coming inside:</strong> ${say || 'none yet'}.</p>${D.weather.spray ? html`<p>${D.weather.spray}</p>` : ''}</div>
    <section class="blk" id="in-order"><h2>The order of work</h2><ol class="steps">
      <li>Outdoors, a week or two before the move, open each plant below and tick its steps as you do them. Inspect it first, and tick the pests you find on its page.</li>
      <li>Clean its pot, then do the methods rated Best for it.</li>
      <li>If you found pests, spray again 5 to 7 days later. The Today page reminds you.</li>
      <li>Bring it inside and change its Location to Indoors (or press Moved indoors).</li>
      <li>Keep it apart from your other houseplants for ${D.keep_apart_days} days, with yellow sticky traps nearby, and check it at every watering.</li></ol></section>
    ${D.plants.length ? html`<p class="row noprint"><button class="btn small ghost" type="button" data-act="prepfold" data-open="1">Open every plant</button><button class="btn small ghost" type="button" data-act="prepfold" data-open="0">Close every plant</button></p>` : ''}
    ${groups.map(([k, list]) => html`<section class="blk" id="in-${k}"><h2>${w[k]} (${list.length})</h2>${gHint[k] ? html`<p class="hint">${gHint[k]}</p>` : ''}
      <ul class="mi-plants">${list.map(fold)}</ul></section>`)}
    <section class="blk" id="in-methods"><h2>How to do each method</h2>
      <p class="hint">Not every method suits every plant: open a plant's plan to see which are best for it.</p>
      ${D.methods.map((m, i) => html`<details class="pm-steps pm-ref"><summary>${i + 1}. ${m.title}</summary><ol>${m.steps.map(s => html`<li>${tText(s)}</li>`)}</ol></details>`)}</section>
    <section class="blk" id="in-apart"><h2>Keeping them apart</h2>
      <p>Pests often show up a week or two after the first treatment, when eggs hatch. So keep the plants that came in away from your long-term houseplants for ${D.keep_apart_days} days, and for 2 weeks after the last treatment if you found pests.</p>
      <ul><li>Give any plant where you found pests its own "hospital" spot until two weekly checks come up clean.</li>
        <li>Put yellow sticky traps beside each group. They catch fungus gnats, whiteflies and thrips, and show whether there are more or fewer each week.</li>
        <li>Spider mites thrive in dry indoor air, so a humidifier helps the palms, calathea and alocasias.</li>
        <li>Water less indoors, and let the top of the soil dry between waterings, so fungus gnats have nowhere to breed.</li>
        <li>Predatory mites, sold online, eat spider mites indoors if they come back.</li></ul></section>`,
  };
}
document.addEventListener('toggle', e => { const d = e.target; if (d.classList && d.classList.contains('mi-fold')) { if (d.open) PREP.open.add(d.dataset.code); else PREP.open.delete(d.dataset.code); } }, true);
function todayPrep(PR, t) {
  const again = [], free = [];
  PR.plants.forEach(p => { p.methods.forEach(m => { if (m.next_due && m.next_due <= t) again.push({ p, m }); }); if (p.status === 'apart' && p.keep_until && p.keep_until <= t) free.push(p); });
  const c = PR.counts, w = PR.status_words;
  const say = ['todo', 'doing', 'ready', 'apart'].filter(k => c[k]).map(k => `${c[k]} ${w[k].toLowerCase()}`).join(', ');
  const row = (p, words, btns) => jobRow({ code: p.code, common_name: p.name, photo: p.photo }, words, btns);
  return html`<section class="blk" id="today-inside"><h2>Getting ready to come inside (${again.length + free.length})</h2>
    <p>${PR.plants.length} coming inside${say ? ': ' + say : ''}.</p><p><a class="btn small ghost" href="#/inside">Open the Coming inside page</a></p>
    ${again.length ? html`<ul class="jobs">${again.map(({ p, m }) => row(p, html`${m.title}, round ${m.done.length + 1}. The last round was ${relDay(m.done[m.done.length - 1])}.`,
      html`<button class="btn small" type="button" data-act="prepdone" data-code="${p.code}" data-k="${m.key}" aria-label="${p.name}: ${m.title.toLowerCase()} done today">Done today</button>`))}</ul>` : ''}
    ${free.length ? html`<ul class="jobs">${free.map(p => row(p, 'Its 3 weeks apart end today. If you have seen no pests, it can join your other houseplants.', html`<a class="btn small ghost" href="#/plant/${enc(p.code)}">Open its page</a>`))}</ul>` : ''}
    ${!again.length && !free.length ? html`<p class="notice ok">No sprays due and nobody to move today.</p>` : ''}</section>`;
}
async function viewToday() {
  const [W, reqsAll, , PR, WA, J, SN, EXT] = await Promise.all([api('GET', '/api/water'), api('GET', '/api/requests?open=1'), loadFertData(true), api('GET', '/api/prep').catch(() => null),
    api('GET', '/api/wishlist/alerts').catch(() => ({ alerts: [] })), api('GET', '/api/jobs').catch(() => null), api('GET', '/api/sensors/summary').catch(() => null),   // 1.35.0: sensors
    featTodayLoad()]);                                                                  // 1.46.0: the blocks feature modules registered (features.js)
  const by = Object.fromEntries(FERT.plants.map(p => [p.code, p])), t = todayStr();
  const ws = W.plants.filter(w => by[w.code]);
  const due = ws.filter(w => w.state === 'due').sort((a, b) => b.overdue - a.overdue), soon = ws.filter(w => w.state === 'soon'), unk = ws.filter(w => w.state === 'unknown');
  const here = FERT.plants.filter(atPlace);                                      // 1.48.0: Today is about the home you are looking at
  const feed = here.map(p => ({ p, st: fertState(p, entriesFor(p.code), t, fertCtx()) })).filter(r => r.st.state === 'due');
  const needs = here.filter(needsYou), reqs = reqsAll.filter(q => !q.plant_code || !by[q.plant_code] || atPlace(by[q.plant_code]));
  const wbtn = w => html`<button class="btn small" type="button" data-act="care" data-kind="water" data-code="${w.code}" data-name="${by[w.code].common_name}">Watered</button>
    <button class="btn small ghost" type="button" data-act="care" data-kind="check" data-code="${w.code}" data-name="${by[w.code].common_name}">Still moist</button>`;
  const n = (k, one, many) => k + ' ' + (k === 1 ? one : many);
  // 1.34.0: Today is the page the app opens on. One line says what needs you, with a button to jump to each part
  const winter = coldSeason();                                                  // 1.48.0: a tropical home has no cold night, coming inside or frost blocks
  const F = FROST, cold = winter && F && F.first ? F.worst.counts.danger + F.worst.counts.damage + F.worst.counts.watch : 0;
  const prepN = PR && PR.plants ? PR.plants.reduce((k, p) => k + p.methods.filter(m => m.next_due && m.next_due <= t).length + (p.status === 'apart' && p.keep_until && p.keep_until <= t ? 1 : 0), 0) : 0;
  const snN = SN ? SN.look + SN.quiet : 0;
  const bits = [cold ? `a cold night ${fzDay(F.first.date, true)}` : '', snN ? n(snN, 'sensor to look at', 'sensors to look at') : '', n(due.length, 'plant to water', 'plants to water'), n(feed.length, 'to feed', 'to feed'),
    WA.alerts.length ? n(WA.alerts.length, 'Shopping alert', 'Shopping alerts') : '', n(needs.length, 'thing Claude needs from you', 'things Claude needs from you')].filter(Boolean);
  const line = bits.length > 1 ? bits.slice(0, -1).join(', ') + ', and ' + bits[bits.length - 1] : bits[0];
  const quiet = [];
  if (PR && PR.plants && !prepN) quiet.push('No pest rounds due.');
  if (SN && SN.n && !snN) quiet.push(`${SN.n} sensor${SN.n === 1 ? '' : 's'} sending, all in range.`);
  if (J) {
    const sc = Object.fromEntries((J.schedule || []).map(x => [x.kind, x]));
    if (sc.shops) quiet.push(sc.shops.last ? `Stores last checked ${when(sc.shops.last)}${/^\d{4}-/.test(sc.shops.next) ? '; next ' + when(sc.shops.next) : ''}.` : 'The stores have not been checked yet.');
    if (sc.backup) quiet.push(sc.backup.last ? `Backup made ${when(sc.backup.last)}.` : sc.backup.every === 'turned off' ? 'Automatic backups are turned off.' : 'No automatic backup yet.');
    quiet.push(J.problems ? html`<a href="#/settings">${J.problems} problem${J.problems === 1 ? '' : 's'} to look at</a>.` : 'No problems.');
  }
  // 1.46.0: the page is a list of blocks in a fixed order (the numbers are in features.js), so what a feature module adds lands in
  // the same place every time, whatever order the scripts loaded in
  const blocks = [
    cold ? { order: 10, id: 'today-cold', jump: `Cold night (${cold})`, html: html`<section class="blk" id="today-cold">${frostBanner(true)}</section>` } : null,
    snN ? { order: 20, id: 'today-sensors', jump: `Sensors (${snN})`, html: html`<section class="blk" id="today-sensors"><h2>Sensors (${snN})</h2><ul class="jobs">${SN.cards.map(s => html`<li class="job"><span class="job-nophoto" aria-hidden="true"></span><div class="job-txt"><a class="nm" href="#/sensors">${s.name}</a>${s.plant ? html` <span class="muted">${s.plant.code} ${s.plant.common_name}</span>` : ''}<div>${s.words}</div></div>
      <div class="job-acts">${s.plant ? html`<a class="btn small ghost" href="#/plant/${enc(s.plant.code)}">Open its plant</a>` : ''}</div></li>`)}</ul><p><a class="btn small ghost" href="#/sensors">All your sensors</a></p></section>` } : null,
    { order: 30, id: 'today-water', jump: `Water (${due.length})`, html: html`<section class="blk" id="today-water"><h2>Water (${due.length})</h2>
      ${due.length ? html`${due.length > 1 ? html`<p><button class="btn small ghost" type="button" data-act="careall" data-kind="water" data-codes="${due.map(w => w.code).join(',')}">Watered all ${due.length}</button></p>` : ''}
        <ul class="jobs">${due.map(w => jobRow(by[w.code], waterWords(w), wbtn(w)))}</ul>` : html`<p class="notice ok">Nothing is due for water today.</p>`}
      ${soon.length ? html`<details class="grp"><summary><h3>Check tomorrow (${soon.length})</h3></summary><ul class="jobs">${soon.map(w => jobRow(by[w.code], waterWords(w), wbtn(w)))}</ul></details>` : ''}
      ${unk.length ? html`<details class="grp"><summary><h3>No watering logged yet (${unk.length})</h3></summary>
        <p class="hint">These have no watering in the log and no rain counted, so there is no reminder for them yet. If you water everything on a round, press the button to start the clock for all of them at once.</p>
        <p><button class="btn small ghost" type="button" data-act="careall" data-kind="water" data-codes="${unk.map(w => w.code).join(',')}">I watered all ${unk.length} today</button></p>
        <ul class="jobs">${unk.map(w => jobRow(by[w.code], w.site !== 'Outdoors' ? w.site + '.' : 'Outdoors.', wbtn(w)))}</ul></details>` : ''}</section>` },
    { order: 40, id: 'today-feed', jump: `Feed (${feed.length})`, html: html`<section class="blk" id="today-feed"><h2>Feed (${feed.length})</h2>
      ${feed.length ? html`${feed.length > 1 ? html`<p><button class="btn small ghost" type="button" data-act="fertlog" data-group="due">Log feeding for all ${feed.length}</button></p>` : ''}
        <ul class="jobs">${feed.map(r => jobRow(r.p, fertWords(r.p, r.st, t), html`<button class="btn small" type="button" data-act="fertlog" data-code="${r.p.code}">Log feeding</button>`))}</ul>`
        : html`<p class="notice ok">No plant is due for fertilizer today. The Fertilizer page has the calendar.</p>`}</section>` },
    WA.alerts.length ? { order: 50, id: 'today-wish', jump: `Shopping (${WA.alerts.length})`, html: html`<section class="blk wl-alerts" id="today-wish"><h2>Shopping alerts (${WA.alerts.length})</h2>${wlAlertsHtml(WA.alerts.slice(0, 6), true)}<p><a class="btn small ghost" href="#/shopping/list">Shopping list for a store visit</a></p></section>` } : null,
    winter && PR && PR.plants.length ? { order: 60, id: 'today-inside', html: todayPrep(PR, t) } : null,
    { order: 70, id: 'today-needs', jump: `Needed from you (${needs.length})`, html: html`<section class="blk" id="today-needs"><h2>Needed from you (${needs.length})</h2>
      ${reqs.length ? html`<ul class="jobs">${reqs.slice(0, 8).map(q => { const p = by[q.plant_code] || { code: q.plant_code || '', common_name: q.plant_code || 'General' };
        return jobRow(p, linkify(q.text), p.code ? html`<a class="btn small ghost" href="#/plant/${enc(p.code)}">Answer on its page</a>` : ''); })}</ul>
        ${reqs.length > 8 ? html`<p class="hint">Showing 8 of ${reqs.length} open requests.</p>` : ''}` : ''}
      <p><button class="btn small ghost" type="button" data-act="todayneeds">Show all plants that need something from you</button></p></section>` },
    quiet.length ? { order: 80, id: 'today-quiet', html: html`<section class="blk" id="today-quiet"><h2>Quiet today</h2><p class="muted">${quiet.map((q, i) => html`${i ? ' ' : ''}${q}`)}</p></section>` } : null,
    ...EXT.filter(({ b }) => winter || !b.cold).map(({ b, d }) => ({ order: b.order, id: b.id, jump: b.jump ? b.jump(d) : '', html: b.html(d) })),
  ].filter(Boolean).sort((a, b) => a.order - b.order);
  const jumps = blocks.filter(b => b.jump && b.id);
  return {
    title: 'Today',
    html: html`<h1>Today</h1><p class="muted">${longDay(t)}. Everything that needs you, most urgent first. <a href="#/plants">All plants</a> is one click away.</p>
    <div class="verdict-box" role="status"><p><strong>${line.charAt(0).toUpperCase() + line.slice(1)}.</strong>
      ${W.avg_high != null ? `Highs have been about ${tF(W.avg_high)} lately.` : ''} ${Object.keys(W.rain).length ? `Rain counted as watering for plants out in the open: ${Object.entries(W.rain).slice(-3).map(([d, i]) => relDay(d) + ', ' + rainF(i)).join('; ')}.` : ''}</p>
      <p class="row td-jumps">${jumps.map(b => html`<a class="btn small ghost" href="#${b.id}" data-act="jumpsec" data-sec="${b.id}">${b.jump}</a>`)}</p></div>
    ${blocks.map(b => b.html)}`,
    after: () => document.querySelectorAll('[data-nav]').forEach(a => { if (a.dataset.nav === 'today') a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); }),
  };
}
const KIND_WORD = { check: 'Check', question: 'Question', photo: 'Photo', info: 'Information' };
function needsBox(p) {
  const open = (p.requests || []).filter(r => !r.done), done = (p.requests || []).filter(r => r.done);
  const low = p.id_confidence != null && p.id_confidence < 70;
  if (!open.length && !low && !done.length) return '';
  return html`<section class="needs" id="needs" aria-labelledby="h-needs"><h2 id="h-needs">${open.length || low ? 'Needed from you' : 'Requests (all answered)'}</h2>
    ${open.length ? html`<ul class="needs-list">${open.map(r => html`<li><span class="kind">${KIND_WORD[r.kind] || 'Request'}</span><span class="txt">${linkify(r.text)}</span>
      <span class="row"><button class="btn small" type="button" data-act="reqanswer" data-id="${r.id}">Answer</button><button class="btn small ghost" type="button" data-act="reqdone" data-id="${r.id}">Mark done</button></span></li>`)}</ul>` : ''}
    ${low ? html`<p class="needs-id"><span class="kind">ID info</span> The identification is ${p.id_confidence}% sure. ${lines(p.id_improve).length ? html`To raise it, send: ${lines(p.id_improve).join('; ')}.` : 'A clear photo of the tag or a flower would help.'} <a href="#ident" data-act="jump" data-id="ident">See Plant identification</a></p>` : ''}
    ${done.length ? html`<details class="needs-done"><summary>${done.length} answered</summary><ul>${done.map(r => html`<li>${r.text}<br><span class="hint">${r.answer ? 'Answer: ' + r.answer + '. ' : ''}${r.done_by || ''} ${r.done_at ? when(r.done_at) : ''}</span>
      <button class="btn small ghost" type="button" data-act="reqreopen" data-id="${r.id}">Reopen</button></li>`)}</ul></details>` : ''}
    <p class="hint">Answers are saved on this page and in the change log. To send them to Claude, press Copy my answers for Claude and paste the message into the chat.</p>
    <p class="noprint"><button class="btn small" type="button" data-act="forclaude">Copy my answers for Claude</button></p></section>`;
}
// ---------- copy my answers for Claude (added in 1.8.0) ----------
const FC = { range: 'last', open: false, data: null };
const FC_RANGES = [['last', 'Since I last copied'], ['7', 'The last 7 days'], ['30', 'The last 30 days'], ['all', 'Everything']];
const fcPl = (n, one, many) => `${n} ${n === 1 ? one : many}`;
async function fcLoad() { FC.data = await api('GET', `/api/for-claude?range=${FC.range}&open=${FC.open ? 1 : 0}`); return FC.data; }
function fcWords(n) {
  const w = [];
  if (n.answers) w.push(fcPl(n.answers, 'answer', 'answers'));
  if (n.pages) w.push(fcPl(n.pages, 'change to a plant page', 'changes to plant pages'));
  if (n.photos) w.push('photo changes on ' + fcPl(n.photos, 'page', 'pages'));
  if (n.care) w.push(fcPl(n.care, 'feeding or care entry', 'feeding or care entries'));
  if (n.todo) w.push(fcPl(n.todo, 'change', 'changes') + ' to the "Still to photograph" list');
  return w.length ? w.join(', ') : 'nothing new in that time';
}
function fcBox(D) {
  const last = D.last_copied ? `Since I last copied (${D.last_copied_words})` : 'Since I last copied (never)';
  return html`<div class="fc-pick">
      <label class="f">What to include<select data-act="fcrange">${FC_RANGES.map(([k, w]) => html`<option value="${k}" ${FC.range === k ? raw('selected') : ''}>${k === 'last' ? last : w}</option>`)}</select></label>
      <label class="chk"><input type="checkbox" data-act="fcopen" ${FC.open ? raw('checked') : ''}>Also list what is still open</label></div>
    <p class="fc-sum"><strong>In this message:</strong> ${fcWords(D.counts)}.</p>
    <label class="f">The message<textarea id="fc-text" readonly rows="12" spellcheck="false">${D.text}</textarea></label>`;
}
const fcSay = msg => { const s = document.getElementById('fc-status'); if (s) s.textContent = msg; };
async function forClaudeDialog() {
  if (!(await needName())) return;                          // copying is noted in the change log, under your name
  FC.range = 'last';
  try { await fcLoad(); } catch (e) { toast('Could not gather your answers: ' + e.message, true); return; }
  await modal(html`<form method="dialog" class="fc"><h2>Copy my answers for Claude</h2>
    <p>One message with everything you have done in Plant record: your answers first, then changes to plant pages, photos, feeding and care. Copy it, then paste it into your chat with Claude.</p>
    <div id="fc-box">${fcBox(FC.data)}</div>
    <p id="fc-status" class="fc-status" role="status" aria-live="polite"></p>
    <div class="row"><button class="btn" type="button" data-act="fccopy" autofocus>Copy message</button>
      <button class="btn ghost" type="button" data-act="fcsave">Save as a text file</button>
      <button class="btn ghost" value="close">Close</button></div></form>`);
}
async function fcRefresh(focusSel) {
  const box = document.getElementById('fc-box'); if (!box) return;
  try { await fcLoad(); } catch (e) { fcSay('Could not gather your answers: ' + e.message); return; }
  box.innerHTML = rend(fcBox(FC.data)); fcSay('');
  const f = focusSel && box.querySelector(focusSel); if (f) f.focus();
}
async function fcMark() {
  if (!FC.data) return;
  try {
    const r = await api('POST', '/api/for-claude/copied', { until: FC.data.until });
    FC.data.last_copied = r.last_copied; FC.data.last_copied_words = r.last_copied_words;
    document.querySelectorAll('.fc-n').forEach(x => x.remove());          // the "(2 new)" on the Plants page
  } catch (e) { /* the message is copied either way */ }
}
function fitPanes() {
  const pl = document.querySelector('.plant');
  if (!pl) return;
  const r = document.documentElement;
  if (r.dataset.layout === 'single' || r.dataset.narrow === '1') { pl.style.removeProperty('--pane-h'); return; }
  const topAbs = pl.getBoundingClientRect().top + window.scrollY;
  const con = r.dataset.console === '1' ? (parseFloat(getComputedStyle(r).getPropertyValue('--console-space')) || 0) : 0;   // room for the audit log console
  const h = Math.max(window.innerHeight - topAbs - 12 - con, 360);      // the two halves fill the window exactly, so the page itself never scrolls
  pl.style.setProperty('--pane-h', h + 'px');
}
function repaintPhotos() { const el = document.getElementById('photopanel'); if (el) el.innerHTML = rend(photoPanel(CUR.p)); }
async function reloadPlant(idx) { KEEP = idx == null ? PIDX : idx; await route(); }
const curPhoto = () => CUR.p.photos[clamp(PIDX, 0, CUR.p.photos.length - 1)];

// ---------- plant page: the row of section buttons steps aside while the On this page menu is open (added in 1.8.0) ----------
// The CSS hides the row then; this keeps --jump-h (used by the sticky section titles) right when the menu opens or closes.
new MutationObserver(() => document.querySelectorAll('.pane').forEach(p => { const j = p.querySelector('.jump'); p.style.setProperty('--jump-h', (j ? j.offsetHeight : 0) + 'px'); }))
  .observe(document.documentElement, { attributes: true, attributeFilter: ['data-navopen', 'data-narrow', 'data-layout'] });
// ---------- dates ----------
const pad2 = n => String(n).padStart(2, '0');
const ymd = d => d.getFullYear() + '-' + pad2(d.getMonth() + 1) + '-' + pad2(d.getDate());
const parseYmd = s => { const [y, m, d] = s.split('-').map(Number); return new Date(y, m - 1, d, 12); };   // noon, so daylight-saving shifts never move the date
const addDays = (s, n) => { const d = parseYmd(s); d.setDate(d.getDate() + n); return ymd(d); };
const daysBetween = (a, b) => Math.round((parseYmd(b) - parseYmd(a)) / 86400000);
const longDay = s => parseYmd(s).toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
const midDay = s => parseYmd(s).toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' });
const MONTHN = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const MN = MONTHN.map(m => m.slice(0, 3));
const DOWN = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
function todayStr() {           // today at the place in use, not in the browser's time zone, so care dates match the server's
  try { if (META && META.home_tz) return new Intl.DateTimeFormat('en-CA', { timeZone: META.home_tz, year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date()); } catch (e) { /* unknown zone */ }
  return ymd(new Date());
}

// ---------- calendar (month grid, with a list version for narrow screens and big text) ----------
const CALS = {};
function calView() {
  let v = null; try { v = localStorage.getItem('plantdb.calview'); } catch (e) { /* ignore */ }
  return v === 'grid' || v === 'list' ? v : (document.documentElement.dataset.narrow === '1' ? 'list' : 'grid');
}
function calHtml(id) {
  const c = CALS[id], [Y, M] = c.month.split('-').map(Number), n = new Date(Y, M, 0).getDate(), dow = new Date(Y, M - 1, 1).getDay();
  const today = todayStr();
  const days = Array.from({ length: n }, (_, i) => Y + '-' + pad2(M) + '-' + pad2(i + 1));
  const focus = days.includes(c.sel) ? c.sel : days.includes(today) ? today : days[0];
  const info = Object.fromEntries(days.map(d => [d, c.cfg.cell(d, c)]));
  const label = d => `${longDay(d)}${d === today ? ', today' : ''}. ${info[d].aria || 'Nothing recorded.'}`;
  const cells = [...Array(dow).fill(null), ...days];
  while (cells.length % 7) cells.push(null);
  const weeks = []; for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7));
  const bad = (b, k) => html`<span class="bd ${b.cls || ''}">${b.text}</span>`;
  const view = c.view || calView();
  return html`<div class="cal-wrap" data-view="${view}">
    <div class="cal-nav noprint"><button type="button" class="btn ghost small" data-act="calnav" data-cal="${id}" data-d="-1" aria-label="Previous month">◀ Previous</button>
      <h3 id="calh-${id}" aria-live="polite">${MONTHN[M - 1]} ${Y}</h3>
      <button type="button" class="btn ghost small" data-act="calnav" data-cal="${id}" data-d="1" aria-label="Next month">Next ▶</button>
      <button type="button" class="btn ghost small" data-act="calnav" data-cal="${id}" data-d="0">Today</button>
      <button type="button" class="btn ghost small" data-act="calview" data-cal="${id}">${view === 'grid' ? 'Show as a list' : 'Show as a grid'}</button></div>
    ${c.loading ? html`<p class="loading">Loading</p>` : ''}
    <table class="cal" aria-labelledby="calh-${id}"><thead><tr>${DOWN.map(d => html`<th scope="col"><abbr title="${d}">${d.slice(0, 3)}</abbr></th>`)}</tr></thead>
      <tbody>${weeks.map(w => html`<tr>${w.map(d => d ? html`<td><button type="button" class="day ${info[d].cls || ''} ${d === c.sel ? 'sel' : ''} ${d === today ? 'today' : ''}" data-act="calpick" data-cal="${id}" data-date="${d}"
          tabindex="${d === focus ? 0 : -1}" aria-pressed="${String(d === c.sel)}" aria-label="${label(d)}">
          <span class="dn">${+d.slice(8)}${d === today ? html` <span class="tdy">today</span>` : ''}</span>${(info[d].badges || []).map(bad)}</button></td>` : html`<td></td>`)}</tr>`)}</tbody></table>
    <ul class="cal-list">${days.map(d => html`<li><button type="button" class="day ${info[d].cls || ''} ${d === c.sel ? 'sel' : ''} ${d === today ? 'today' : ''}" data-act="calpick" data-cal="${id}" data-date="${d}" aria-pressed="${String(d === c.sel)}" aria-label="${label(d)}">
        <span class="dn">${midDay(d)}${d === today ? ' (today)' : ''}</span><span class="bds">${(info[d].badges || []).map(bad)}</span></button></li>`)}</ul>
    ${c.cfg.legend ? html`<p class="hint cal-legend">${c.cfg.legend}</p>` : ''}</div>`;
}
function calRender(id, keepFocus) {
  const el = document.getElementById('cal-' + id); if (!el) return;
  el.innerHTML = rend(calHtml(id));
  if (keepFocus) { const b = el.querySelector(`.cal .day[data-date="${keepFocus}"]`); if (b) b.focus(); }
}
async function calMount(id, cfg, month, sel) {
  const c = CALS[id] = { id, cfg, month: month || (sel || todayStr()).slice(0, 7), sel: sel || null, data: {}, loading: false };
  await calLoad(id);
}
async function calLoad(id) {
  const c = CALS[id]; if (!c) return;
  if (c.cfg.load) { c.loading = true; calRender(id); try { await c.cfg.load(c.month, c); } catch (e) { toast(e.message, true); } c.loading = false; }
  calRender(id);
}
async function calGo(id, date, focus) {
  const c = CALS[id]; if (!c) return;
  const m = date.slice(0, 7);
  c.sel = date;
  if (m !== c.month) { c.month = m; await calLoad(id); } else calRender(id, focus ? date : null);
  if (focus) calRender(id, date);
  if (c.cfg.pick) c.cfg.pick(date, c);
}
function calNav(id, d) {
  const c = CALS[id]; if (!c) return;
  if (d === 0) { c.month = todayStr().slice(0, 7); c.sel = todayStr(); calLoad(id).then(() => c.cfg.pick && c.cfg.pick(c.sel, c)); return; }
  const [Y, M] = c.month.split('-').map(Number), n = new Date(Y, M - 1 + d, 1);
  c.month = n.getFullYear() + '-' + pad2(n.getMonth() + 1);
  calLoad(id);
}
const LEVELBD = { ok: ['s-ok', '✔ In range'], near: ['s-near', '▲ A little out'], bad: ['s-bad', '■ Out of range'], danger: ['s-danger', '✖ Danger'], info: ['s-none', 'No range set'] };

// ---------- feeding season and verdict ----------
const hasSeason = p => has(p.fert_from_month) && has(p.fert_to_month) && has(p.fert_every_days);
const monthIn = (p, m) => p.fert_from_month <= p.fert_to_month ? (m >= p.fert_from_month && m <= p.fert_to_month) : (m >= p.fert_from_month || m <= p.fert_to_month);
const seasonText = p => hasSeason(p) ? `${MONTHN[p.fert_from_month - 1]} to ${MONTHN[p.fert_to_month - 1]}, about every ${p.fert_every_days} days` : 'No feeding season set';
function nextSeasonStart(p, ds) {
  let d = ds;
  for (let i = 0; i < 14; i++) {
    if (monthIn(p, +d.slice(5, 7))) return d;
    const [Y, M] = d.split('-').map(Number), n = new Date(Y, M, 1, 12);
    d = ymd(n);
  }
  return ds;
}
const lastFed = (entries, ds) => entries.find(e => e.applied_on <= ds) || null;       // entries are newest first
function nextDue(p, entries) {
  if (!hasSeason(p)) return null;
  const last = entries[0], t = todayStr();
  let base = last ? addDays(last.applied_on, +p.fert_every_days) : t;
  if (base < t) base = t;
  return nextSeasonStart(p, base);
}
function holdReason(p, ds, ctx) {
  const t = todayStr();
  if (ds < t) return null;
  if (ds === t && (p.health_rating === 'Poor' || p.health_rating === 'Critical'))
    return `This plant's health is rated ${p.health_rating}. Fix the problem first (see Health below). Fertilizer on a stressed plant makes it worse.`;
  const lim = has(p.temp_damage_below) ? +p.temp_damage_below : 35;
  const fc = ((ctx && ctx.forecast) || []).filter(d => d.date >= ds && d.date <= addDays(ds, 2));
  const cold = fc.filter(d => d.low <= lim).sort((a, b) => a.low - b.low)[0];
  if (cold) return `A cold night is forecast (${tF(cold.low)} on ${midDay(cold.date)}), at or below the damage point for this plant (${tF(lim)}). Wait until it passes.`;
  return null;
}
function fertState(p, entries, ds, ctx) {
  if (!hasSeason(p)) return { state: 'unknown' };
  const every = +p.fert_every_days, last = lastFed(entries, ds), since = last ? daysBetween(last.applied_on, ds) : null;
  const nxt = last ? nextSeasonStart(p, addDays(last.applied_on, every)) : null;
  if (last && since === 0) return { state: 'fed', last, since, next: nxt };
  if (!monthIn(p, +ds.slice(5, 7))) return { state: 'rest', until: nextSeasonStart(p, ds), last, since };
  if (last && since < every) return { state: 'wait', last, since, next: nxt };
  const hold = holdReason(p, ds, ctx);
  const over = last ? since - every : null;
  return hold ? { state: 'hold', reason: hold, last, since } : { state: 'due', last, since, over };
}
const FS = { due: ['▲', 'Time to fertilize', 'st-near'], hold: ['■', 'Hold off', 'st-bad'], wait: ['✔', 'Fed recently', 'st-ok'], fed: ['✔', 'Fed today', 'st-ok'], rest: ['—', 'Resting, do not fertilize', 'st-mute'], unknown: ['?', 'No feeding season set', 'st-mute'] };
function fertWords(p, st, ds) {
  const day = ds === todayStr() ? 'today' : 'on this date', every = p.fert_every_days;
  const prod = st.last ? ` (${st.last.product})` : '';
  switch (st.state) {
    case 'rest': return `Growth is slow or stopped in these months, so fertilizer would only build up salts in the mix. Do not fertilize ${day}. This plant's feeding season is ${seasonText(p)}; it opens again ${longDay(st.until)}.`;
    case 'fed': return `Fed ${day}${prod}. The next feeding is about ${longDay(st.next)}.`;
    case 'wait': return `Last fed ${st.since} day${st.since === 1 ? '' : 's'} before this date${prod}. Feed about every ${every} days, so wait until ${longDay(st.next)}.`;
    case 'hold': return st.reason;
    case 'due': return `${st.last ? `Last fed ${st.since} days before this date${prod}, and this plant likes feeding about every ${every} days${st.over > 0 ? `, so it is ${st.over} day${st.over === 1 ? '' : 's'} overdue` : ''}.` : 'No feeding is recorded for it yet.'} Water lightly first if the mix is dry, then use the product at the strength on its label (half strength is safer).`;
    default: return 'Open Edit and fill in "Feed from month", "Feed through month" and "Feed every (days)" in the Nutrients group to get a calendar for this plant.';
  }
}
const verdictLine = (p, st) => html`<span class="${FS[st.state][2]}">${FS[st.state][0]} ${FS[st.state][1]}</span>`;

// ---------- fertilizer amount maths (same as the server) ----------
const WATER_L = { L: 1, gal: 3.78541, qt: 0.946353, cup: 0.236588 };
function fertCalc(form, n, p, k, amount, unit, water, wunit) {
  const out = { ppm_n: null, ppm_p2o5: null, ppm_k2o: null, n_grams: null, g: null };
  if (!amount || !unit) return out;
  const liquid = ['liquid', 'organic liquid', 'foliar spray'].includes(form);
  const g = { g: amount, oz: amount * 28.3495, ml: amount, 'fl oz': amount * 29.5735, tsp: amount * (liquid ? 4.92892 : 4), tbsp: amount * (liquid ? 14.7868 : 12) }[unit];
  if (g == null) return out;
  out.g = g;
  if (n != null) out.n_grams = Math.round(g * n / 100 * 1000) / 1000;
  const L = water && WATER_L[wunit] ? water * WATER_L[wunit] : null;
  if (L) for (const [key, pct] of [['ppm_n', n], ['ppm_p2o5', p], ['ppm_k2o', k]]) if (pct != null) out[key] = Math.round(g * pct / 100 * 1000 / L * 10) / 10;
  return out;
}
const npkText = e => ['n', 'p', 'k'].map(x => e[x] == null ? '?' : fmt(e[x], 2)).join('-');
const doseText = e => e.amount == null ? 'amount not noted' : `${fmt(e.amount, 2)} ${e.amount_unit}${e.water_amount ? ' in ' + fmt(e.water_amount, 2) + ' ' + e.water_unit + ' of water' : ''}`;
const ratioText = (n, p, k) => {
  const v = [n, p, k].map(x => +x || 0), m = Math.min(...v.filter(x => x > 0));
  return m && isFinite(m) ? v.map(x => (Math.round(x / m * 10) / 10)).join(' : ') : '';
};

// ---------- fertilizer data shared by the plant page and the Fertilizer page ----------
const FERT = { entries: [], products: [], plants: [], forecast: [], needs: {} };
async function loadFertData(withPlants) {
  const [entries, products, W] = await Promise.all([api('GET', '/api/fertilizer'), api('GET', '/api/fertilizer/products'), api('GET', '/api/weather').catch(() => null)]);
  FERT.entries = entries; FERT.products = products; FERT.forecast = (W && W.forecast && W.forecast.days) || [];
  if (withPlants) { FERT.needs = {}; await Promise.all([api('GET', '/api/plants').then(x => { FERT.plants = x; }), loadNeeds()]); }
}
const entriesFor = code => FERT.entries.filter(e => e.plant_code === code);
function fertShopBlock() {        // 1.30.0: the N-P-K ratios your plants are set to, each with a button to watch the stores for it
  const m = new Map();
  (FERT.plants || []).forEach(p => { const r = String(p.npk_ratio || '').trim(); if (/^\d+(\.\d+)?-\d+(\.\d+)?-\d+(\.\d+)?$/.test(r)) m.set(r, (m.get(r) || 0) + 1); });
  if (!m.size || !canChange()) return '';
  const list = [...m.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8);
  return html`<section class="blk" aria-labelledby="fn-shop-h"><h2 id="fn-shop-h">Shopping for fertilizer</h2>
    <p class="hint">The N-P-K ratios your plants are set to. Watch the stores for one on Shopping; its alerts come here too, on the Today page.</p>
    <ul class="fn-shop">${list.map(([r, n]) => html`<li><strong>${r}</strong>: ${n} plant${n === 1 ? '' : 's'}
      <button class="btn ghost small" type="button" data-act="buywatch" data-kind="fert" data-name="Fertilizer ${r}" data-search="fertilizer ${r}" data-src="fert:${r}">Watch for it on Shopping</button></li>`)}</ul></section>`;
}
const fertCtx = () => ({ forecast: FERT.forecast });

function entryRows(list, plantsByCode, showPlant) {
  if (!list.length) return html`<p class="muted">Nothing logged yet.</p>`;
  return html`<div class="tbl-wrap"><table class="tbl"><caption class="sr">Fertilizer entries</caption><thead><tr><th>Date</th>${showPlant ? html`<th>Plant</th>` : ''}<th>Fertilizer</th><th>N-P-K</th><th>Amount</th><th class="num">About ppm N</th><th>How</th><th class="noprint"><span class="sr">Actions</span></th></tr></thead><tbody>
    ${list.map(e => html`<tr><th scope="row">${midDay(e.applied_on)}</th>${showPlant ? html`<td><a href="#/plant/${enc(e.plant_code)}">${(plantsByCode[e.plant_code] || {}).common_name || e.plant_code}</a></td>` : ''}
      <td>${e.product}${e.note ? html`<div class="hint">${e.note}</div>` : ''}</td><td>${npkText(e)}</td><td>${doseText(e)}</td><td class="num">${e.ppm_n == null ? '' : fmt(e.ppm_n, 0)}</td><td>${e.method}</td>
      <td class="noprint"><button class="btn ghost small" type="button" data-act="fertedit" data-id="${e.id}" aria-label="Change the feeding on ${e.applied_on}">Change</button> <button class="btn danger small" type="button" data-act="fertdel" data-id="${e.id}" aria-label="Remove the feeding on ${e.applied_on}">Remove</button></td></tr>`)}</tbody></table></div>`;
}

// ---------- what each plant needs, and the closest fertilizer you have (1.11.0) ----------
const FZQ = { 'Matches': ['✔', 'q-good'], 'Close': ['✔', 'q-good'], 'Usable': ['▲', 'q-ok'], 'Not a good match': ['■', 'q-bad'] };
const STRENGTH_WORD = { 'Quarter strength': 'quarter strength', 'Quarter to half strength': 'quarter to half strength', 'Half strength': 'half strength', 'Full strength': 'full strength' };
function needLines(n, opts) {
  if (!n) return '';
  const o = opts || {}, m = n.match, none = n.strength === 'None needed';
  const need = n.ratio
    ? (none ? html`<strong>Needs little or no fertilizer.</strong> If you do feed it: N-P-K ratio <strong class="npk">${n.ratio_text}</strong>, lightly.`
            : html`Needs N-P-K ratio <strong class="npk">${n.ratio_text}</strong>${n.strength ? html`, at ${STRENGTH_WORD[n.strength]}` : ''}.`)
    : html`<span class="muted">${n.note}</span>`;
  let match = '';
  if (m) {
    const q = FZQ[m.quality] || ['', ''], d = m.dose;
    const dose = !d ? '' : d.kind === 'water' ? html` ${d.words}${d.ppm_n != null ? ` That is about ${fmt(d.ppm_n, 0)} ppm nitrogen.` : ''}` : html` ${d.words}`;
    const last = m.last ? html` <span class="muted">Last time you used ${fmt(m.last.amount, 2)} ${m.last.amount_unit}${m.last.water_amount ? ` in ${fmt(m.last.water_amount, 2)} ${m.last.water_unit}` : ''}.</span>` : '';
    match = html`<span class="fn-m">${m.quality === 'Not a good match' ? 'Closest you have' : 'Best match you have'}: <strong>${m.product}</strong> <span class="npk">${m.npk_text}</span>
      <span class="fn-q ${q[1]}">${q[0]} ${m.quality}</span>${m.why ? ` ${m.why}` : ''}${m.quality === 'Not a good match' ? ` Look for a fertilizer labelled about ${n.ratio_text}, or add one you have.` : ''}${none ? '' : dose}${m.strength_assumed && d && d.kind === 'water' ? ' (No strength is set for this plant, so this is for half strength.)' : ''}${last}</span>`;
  } else if (n.ratio && !none) match = html`<span class="fn-m muted">${n.note}</span>`;
  return html`<span class="fn-need${o.block ? ' blk-need' : ''}"><span class="fn-n">${need}</span>${match}</span>`;
}
async function loadNeeds(code) {
  try { const r = await api('GET', '/api/fertilizer/needs' + (code ? '?plant=' + enc(code) : '')); r.needs.forEach(n => { FERT.needs[n.code] = n; }); }
  catch (e) { /* the page works without it */ }
}

// ---------- your fertilizers: saved ones and logged ones (1.11.0) ----------
function productsBlock() {
  const P = FERT.products;
  return html`<p>The fertilizers you have. Each plant above is matched to the one whose N-P-K ratio is closest to what it needs. Add the ones in your shed even before you use them; ones you log are added by themselves.</p>
    <p class="row noprint"><button class="btn" type="button" data-act="fzadd">Add a fertilizer you have</button></p>
    ${P.length ? html`<div class="tbl-wrap"><table class="tbl fn-tbl"><caption class="sr">Your fertilizers</caption><thead><tr><th scope="col">Name</th><th scope="col">N-P-K</th><th scope="col">Type</th><th scope="col">Last used</th><th scope="col"><span class="sr">Actions</span></th></tr></thead><tbody>
      ${P.map((x, i) => html`<tr><th scope="row">${x.product}${x.note ? html`<div class="hint">${x.note}</div>` : ''}</th>
        <td>${npkText(x)}${ratioText(x.n, x.p, x.k) ? html`<div class="hint">ratio ${ratioText(x.n, x.p, x.k)}</div>` : ''}</td><td>${x.form}</td>
        <td>${x.last_used ? html`${midDay(x.last_used)}<div class="hint">${doseText(x)}${x.uses > 1 ? `, ${x.uses} times in all` : ''}</div>` : html`<span class="muted">Not used yet</span>`}</td>
        <td class="noprint"><div class="row" style="gap:.4rem"><button class="btn ghost small" type="button" data-act="fzedit" data-i="${i}" aria-label="Change the fertilizer ${x.product}">Change</button>${x.saved ? html`<button class="btn danger small" type="button" data-act="fzdel" data-i="${i}" aria-label="Remove the fertilizer ${x.product}">Remove</button>` : ''}</div></td></tr>`)}</tbody></table></div>
      <p class="hint">Amounts aim for about 150 ppm of the strongest of N, P and K at full strength, 75 at half and 40 at a quarter, which is a usual rate for plants in pots. If the label says to use less, use the label.</p>`
    : html`<p class="muted">None yet.</p>`}`;
}
async function productDialog(x) {
  if (!(await needName())) return;
  const editing = x && x.saved, num = v => v == null ? '' : v;
  for (;;) {
    const r = await modal(html`<form method="dialog"><h2>${editing ? 'Change this fertilizer' : x ? 'Correct this fertilizer' : 'Add a fertilizer you have'}</h2>
      ${x && !x.saved ? html`<p class="muted">This one came from your feeding log. Saving keeps your log as it is and uses these details for matching.</p>` : ''}
      <label class="f">Name<input type="text" name="product" maxlength="80" value="${x ? x.product : ''}" required autofocus></label>
      <label class="f">Type<select name="form">${['liquid', 'powder', 'granular', 'slow-release', 'spikes', 'organic liquid', 'organic solid', 'foliar spray', 'other'].map(v => html`<option ${v === (x ? x.form : 'liquid') ? raw('selected') : ''}>${v}</option>`)}</select>
        <small>Liquid and powder are mixed into water. Granular, slow-release, spikes and organic solid go on or into the mix.</small></label>
      <fieldset class="opt-group"><legend>What is printed on the package (N-P-K, in percent)</legend>
        <div class="field-grid three"><label class="f">Nitrogen (N)<input type="number" step="any" min="0" max="100" name="n" value="${num(x && x.n)}" required></label>
          <label class="f">Phosphate (P)<input type="number" step="any" min="0" max="100" name="p" value="${num(x && x.p)}" required></label>
          <label class="f">Potash (K)<input type="number" step="any" min="0" max="100" name="k" value="${num(x && x.k)}" required></label></div>
        <p class="hint">A bottle labelled 24-8-16 is 24% nitrogen, 8% phosphate and 16% potash.</p></fieldset>
      <label class="f">Note<input type="text" name="note" maxlength="300" value="${x ? x.note || '' : ''}"><small>For example where it is kept, or "with iron".</small></label>
      <div class="row"><button class="btn" value="ok">${editing ? 'Save changes' : 'Save fertilizer'}</button><button class="btn ghost" value="cancel" formnovalidate>Cancel</button></div></form>`);
    if (r !== 'ok') return;
    const f = dlg.querySelector('form'), v = n => f.elements[n].value;
    const body = { product: v('product'), form: v('form'), n: v('n'), p: v('p'), k: v('k'), note: v('note') };
    try {
      if (editing) await api('PUT', '/api/fertilizer/products/' + x.id, body); else await api('POST', '/api/fertilizer/products', body);
      toast(editing ? 'Fertilizer changed' : `${body.product.trim()} saved`);
      await fertRefresh(); return;
    } catch (e) { toast(e.message, true); x = { ...(x || {}), ...body, n: +body.n, p: +body.p, k: +body.k }; }
  }
}

// ---------- fertilizer panel on a plant page ----------
function fertCfgPlant(p) {
  return {
    legend: html`Shaded green days are in this plant's feeding season. Hatched days are its resting season: do not fertilize. "Fed" marks a feeding you logged and "Due" the next one this page suggests.${typeof SNSDAYS !== 'undefined' && SNSDAYS && SNSDAYS.code === p.code && SNSDAYS.sensors.length ? ' "Soil" is the day\'s average soil moisture from the sensor in its pot, and "Watered" a watering (pressed, or seen by the sensor).' : ''}`,
    cell(ds, c) {
      const es = entriesFor(p.code), fed = es.filter(e => e.applied_on === ds), nd = nextDue(p, es);
      const inS = hasSeason(p) && monthIn(p, +ds.slice(5, 7));
      const badges = [];
      fed.forEach(e => badges.push({ cls: 'b-fed', text: '● Fed ' + e.product }));
      if (nd === ds && !fed.length) badges.push({ cls: 'b-due', text: '▲ Due' });
      if (hasSeason(p) && !inS && !badges.length) badges.push({ cls: 'b-rest', text: 'Rest' });
      const soil = typeof SNSDAYS !== 'undefined' && SNSDAYS && SNSDAYS.code === p.code && SNSDAYS.sensors.length ? SNSDAYS.sensors[0].days.find(x => x.d === ds) : null;   // 1.36.0
      if (soil) badges.push({ cls: 'b-soil', text: `Soil ${Math.round(soil.avg)}%` });
      if (SNSDAYS && SNSDAYS.code === p.code && SNSDAYS.waterings.includes(ds)) badges.push({ cls: 'b-water', text: '▲ Watered' });
      return { cls: hasSeason(p) ? (inS ? 'cal-in' : 'cal-rest') : '', badges,
        aria: (soil ? `Soil moisture ${Math.round(soil.avg)}%. ` : '') + (SNSDAYS && SNSDAYS.code === p.code && SNSDAYS.waterings.includes(ds) ? 'Watered. ' : '') + (fed.length ? 'Fed with ' + fed.map(e => e.product).join(' and ') + '. ' : '') + (nd === ds && !fed.length ? 'Next feeding due. ' : '') + (hasSeason(p) ? (inS ? 'In feeding season.' : 'Resting season, do not fertilize.') : '') };
    },
    pick(ds) { fertDayDetail(p, ds); },
  };
}
function fertDayDetail(p, ds) {
  const el = document.getElementById('fert-day'); if (!el) return;
  const es = entriesFor(p.code), st = fertState(p, es, ds, fertCtx()), fed = es.filter(e => e.applied_on === ds);
  el.innerHTML = rend(html`<section class="day-card" aria-live="polite"><h3>${longDay(ds)}</h3>
    <p class="verdict">${verdictLine(p, st)}</p><p>${fertWords(p, st, ds)}</p>
    ${fed.length ? html`<h4>Fed on this day</h4>${entryRows(fed, {}, false)}` : ''}
    <div class="row noprint"><button class="btn small" type="button" data-act="fertlog" data-code="${p.code}" data-date="${ds}">Log a feeding on this date</button></div></section>`);
}
async function loadFertPlant() {
  const box = document.getElementById('fert-plant'); if (!box || !CUR) return;
  const p = CUR.p;
  try { await Promise.all([loadFertData(false), loadNeeds(p.code)]); } catch (e) { box.innerHTML = rend(html`<p class="notice bad">Could not load feeding data: ${e.message}</p>`); return; }
  const es = entriesFor(p.code), today = todayStr(), st = fertState(p, es, today, fertCtx()), nd = nextDue(p, es);
  const prevSel = CALS.fp && CALS.fp.sel;
  const nb = document.getElementById('fert-need');
  if (nb) nb.innerHTML = rend(FERT.needs[p.code] ? html`<div class="fn-plant"><h3>What to feed it</h3><p>${needLines(FERT.needs[p.code], { block: true })}</p>
      <p class="hint noprint"><a href="#/fertilizer">Your fertilizers</a> are listed on the Fertilizer page. Change this plant's ratio or strength with Edit, under Nutrients.</p></div>` : '');
  box.innerHTML = rend(html`<div class="verdict-box v-${st.state}" role="status"><h3>Today, ${longDay(today)}</h3><p class="verdict">${verdictLine(p, st)}</p><p>${fertWords(p, st, today)}</p>
      ${hasSeason(p) ? html`<p class="hint">Season: ${seasonText(p)}.${nd && st.state !== 'due' && st.state !== 'hold' ? ' Next feeding about ' + longDay(nd) + '.' : ''} Change these in Edit this page.</p>` : ''}</div>
    <div class="row noprint" style="margin:.8rem 0"><button class="btn" type="button" data-act="fertlog" data-code="${p.code}">Log a feeding for this plant</button></div>
    <h3>Feeding calendar</h3><div id="cal-fp"></div><div id="fert-day"></div>
    <h3>Everything logged for this plant</h3>${entryRows(es, {}, false)}`);
  await calMount('fp', fertCfgPlant(p), prevSel ? prevSel.slice(0, 7) : null, prevSel || today);
  fertDayDetail(p, CALS.fp.sel);
}

// ---------- the Fertilizer page ----------
async function viewFertilizer() {
  await loadFertData(true);
  const t = todayStr(), by = Object.fromEntries(FERT.plants.map(p => [p.code, p]));
  const rows = FERT.plants.map(p => ({ p, st: fertState(p, entriesFor(p.code), t, fertCtx()) }));
  const grp = k => rows.filter(r => r.st.state === k || (k === 'wait' && r.st.state === 'fed'));
  const G5 = [['due', 'Time to fertilize', true], ['hold', 'Hold off for now', true], ['wait', 'Fed recently', false], ['rest', 'Resting (out of season)', false], ['unknown', 'No feeding season set', false]];
  const rowHtml = r => html`<li class="${FERT.needs[r.p.code] ? 'fn-li' : ''}">${r.p.photo ? html`<img src="${thumbUrl(r.p.photo)}" alt="" loading="lazy">` : html`<span></span>`}
    <span><a class="nm" href="#/plant/${enc(r.p.code)}">${r.p.common_name}</a><br><span class="muted">${r.p.code}. ${r.st.state === 'rest' ? 'Season opens ' + midDay(r.st.until) + '.' : r.st.state === 'hold' ? r.st.reason : r.st.state === 'unknown' ? '' : r.st.last ? `Last fed ${r.st.since} days ago.${r.st.state === 'wait' || r.st.state === 'fed' ? ' Next about ' + midDay(r.st.next) + '.' : r.st.over > 0 ? ' ' + r.st.over + ' days overdue.' : ''}` : 'Never logged.'}</span></span>${FERT.needs[r.p.code] ? html`<span class="fn-row">${needLines(FERT.needs[r.p.code])}</span>` : ''}
    <button class="btn ghost small noprint" type="button" data-act="fertlog" data-code="${r.p.code}">Log</button></li>`;
  const q = k => grp(k).length;
  return {
    title: 'Fertilizer',
    html: html`<h1>Fertilizer</h1>
    <p class="muted">When to feed each plant, and a record of what you used. Every plant has its own feeding season (the months it grows) and a gap between feedings, and the N-P-K ratio it needs. Change them on a plant's Edit page.</p>
    <div class="verdict-box" role="status"><h2 style="margin:0 0 .4rem">Today, ${longDay(t)}</h2>
      <p>${q('due')} plant${q('due') === 1 ? ' is' : 's are'} due for fertilizer${q('hold') ? `, ${q('hold')} should wait because of cold or health` : ''}. ${q('wait')} ${q('wait') === 1 ? 'was' : 'were'} fed recently and ${q('rest')} ${q('rest') === 1 ? 'is' : 'are'} resting for the season.</p>
      <div class="row noprint"><button class="btn" type="button" data-act="fertlog">Log fertilizer</button>${q('due') ? html`<button class="btn ghost" type="button" data-act="fertlog" data-group="due">Log fertilizer for the ${q('due')} due plants</button>` : ''}</div></div>
    ${G5.map(([k, title, open]) => grp(k).length ? html`<details class="grp" ${open ? raw('open') : ''}><summary><h2>${title} (${grp(k).length})</h2></summary><ul class="todo">${grp(k).map(rowHtml)}</ul></details>` : '')}
    <section class="blk"><h2>Calendar for all plants</h2><div id="cal-fa"></div><div id="fa-day"></div></section>
    <section class="blk" id="fn-products"><h2>Your fertilizers</h2>${productsBlock()}</section>
    ${fertShopBlock()}
    <section class="blk"><h2>Feeding seasons</h2><div class="tbl-wrap"><table class="tbl"><thead><tr><th>Plant</th><th>Season</th><th class="num">Every (days)</th><th>Last fed</th><th>Next feeding</th></tr></thead><tbody>
      ${rows.map(r => { const es = entriesFor(r.p.code), nd = nextDue(r.p, es); return html`<tr><th scope="row"><a href="#/plant/${enc(r.p.code)}">${r.p.common_name}</a><div class="hint">${r.p.code}</div></th>
        <td>${hasSeason(r.p) ? MN[r.p.fert_from_month - 1] + ' to ' + MN[r.p.fert_to_month - 1] : 'Not set'}</td><td class="num">${r.p.fert_every_days || ''}</td><td>${es[0] ? midDay(es[0].applied_on) : 'Never logged'}</td><td>${nd ? midDay(nd) : ''}</td></tr>`; })}</tbody></table></div></section>
    <section class="blk"><h2>Everything logged</h2>${entryRows(FERT.entries.slice(0, 60), by, true)}${FERT.entries.length > 60 ? html`<p class="hint">Showing the newest 60 of ${FERT.entries.length}. The change log has the rest.</p>` : ''}</section>`,
    after: async () => {
      const prev = CALS.fa && CALS.fa.sel;
      await calMount('fa', {
        legend: 'The number after "Fed" is how many plants were fed that day. "Due" is how many plants are next due then.',
        cell(ds) {
          const fed = FERT.entries.filter(e => e.applied_on === ds), dueN = FERT.plants.filter(p => nextDue(p, entriesFor(p.code)) === ds).length;
          const badges = []; if (fed.length) badges.push({ cls: 'b-fed', text: '● Fed ' + new Set(fed.map(e => e.plant_code)).size });
          if (dueN) badges.push({ cls: 'b-due', text: '▲ Due ' + dueN });
          return { badges, aria: (fed.length ? `${new Set(fed.map(e => e.plant_code)).size} plants fed. ` : '') + (dueN ? `${dueN} plants due.` : '') };
        },
        pick(ds) {
          const el = document.getElementById('fa-day'); if (!el) return;
          const fed = FERT.entries.filter(e => e.applied_on === ds), due = FERT.plants.filter(p => nextDue(p, entriesFor(p.code)) === ds);
          el.innerHTML = rend(html`<section class="day-card" aria-live="polite"><h3>${longDay(ds)}</h3>
            ${fed.length ? entryRows(fed, by, true) : html`<p class="muted">No feedings logged on this day.</p>`}
            ${due.length ? html`<h4>Due on this day</h4><ul>${due.map(p => html`<li><a href="#/plant/${enc(p.code)}">${p.common_name}</a></li>`)}</ul>` : ''}
            <div class="row noprint"><button class="btn small" type="button" data-act="fertlog" data-date="${ds}">Log fertilizer on this date</button></div></section>`);
        },
      }, prev ? prev.slice(0, 7) : null, prev || t);
      CALS.fa.cfg.pick(CALS.fa.sel);
    },
  };
}

// ---------- log / change a feeding ----------
let FD = null;   // state of the dialog, kept so a failed save does not lose what was typed
function fertState0(opts) {
  const e = opts.entry, last = FERT.products[0];
  const n = !e && opts.codes && opts.codes.length === 1 ? FERT.needs[opts.codes[0]] : null, m = n && n.match && n.match.quality !== 'Not a good match' && n.strength !== 'None needed' ? n.match : null;
  if (m) {                     // logging for one plant: start from the fertilizer and amount the page suggests for it
    const d = m.dose || {}, water = d.kind === 'water';
    return { id: null, codes: opts.codes, applied_on: opts.date || todayStr(), product: m.product, form: m.form, n: m.n, p: m.p, k: m.k,
      amount: water ? d.amount : null, amount_unit: water ? d.unit : 'tsp', water_amount: water ? d.water : null, water_unit: 'gal', method: water ? 'water in' : 'top-dress', note: '' };
  }
  return e ? { id: e.id, codes: [e.plant_code], applied_on: e.applied_on, product: e.product, form: e.form, n: e.n, p: e.p, k: e.k, amount: e.amount, amount_unit: e.amount_unit || 'tsp', water_amount: e.water_amount, water_unit: e.water_unit || 'gal', method: e.method, note: e.note }
    : { id: null, codes: opts.codes || [], applied_on: opts.date || todayStr(), product: '', form: 'liquid', n: null, p: null, k: null, amount: null, amount_unit: 'tsp', water_amount: null, water_unit: 'gal', method: 'water in', note: '' };
}
function readFert() {
  const f = dlg.querySelector('form'), v = n => { const x = f.elements[n]; return x ? x.value : ''; };
  const num = n => v(n) === '' ? null : Number(v(n));
  const codes = [...dlg.querySelectorAll('[name=pl]:checked')].map(x => x.value);
  return { id: FD ? FD.id : null, codes: FD && FD.id ? FD.codes : codes, applied_on: v('applied_on'), product: v('product').trim(), form: v('form'), n: num('n'), p: num('p'), k: num('k'),
    amount: num('amount'), amount_unit: v('amount_unit'), water_amount: num('water_amount'), water_unit: v('water_unit'), method: v('method'), note: v('note').trim() };
}
function fertPreview() {
  const box = document.getElementById('fert-preview'); if (!box) return;
  const s = readFert(), c = fertCalc(s.form, s.n, s.p, s.k, s.amount, s.amount_unit, s.water_amount, s.water_unit), bits = [];
  if (c.ppm_n != null) {
    bits.push(html`<strong>About ${fmt(c.ppm_n, 0)} ppm nitrogen</strong> in the water${c.ppm_p2o5 != null ? html`, ${fmt(c.ppm_p2o5, 0)} ppm phosphate (P₂O₅) and ${fmt(c.ppm_k2o, 0)} ppm potash (K₂O)` : ''}. ${ratioText(s.n, s.p, s.k) ? 'N : P : K ratio ' + ratioText(s.n, s.p, s.k) + '.' : ''}`);
    bits.push(html`<span class="hint">${c.ppm_n > 300 ? 'That is strong for most potted plants, which usually get 50 to 200 ppm nitrogen. Use less product or more water.' : c.ppm_n < 25 ? 'That is very weak. Fine for feeding at every watering, but not enough for a monthly feeding.' : 'Most potted plants do well at 50 to 200 ppm nitrogen.'} Spoon measures are taken as ${s.form === 'liquid' || s.form === 'organic liquid' || s.form === 'foliar spray' ? '4.9 ml per tsp and 14.8 ml per tbsp' : '4 g per tsp and 12 g per tbsp'}, so treat it as an estimate.</span>`);
  } else if (c.n_grams != null) bits.push(html`<strong>About ${fmt(c.n_grams, 2)} g of nitrogen</strong> applied in total (no water amount given, so no ppm).`);
  else bits.push(html`<span class="hint">Enter the N-P-K numbers, the amount, and how much water it goes into to see how strong the mix is.</span>`);
  const t = s.applied_on, rest = (s.codes || []).map(c0 => FERT.plants.find(p => p.code === c0) || (CUR && CUR.p.code === c0 ? CUR.p : null)).filter(p => p && t && hasSeason(p) && !monthIn(p, +t.slice(5, 7)));
  if (rest.length) bits.push(html`<strong class="st-near">▲ ${rest.length} selected plant${rest.length === 1 ? ' is' : 's are'} in a resting season on that date: ${rest.slice(0, 6).map(p => p.common_name).join(', ')}${rest.length > 6 ? ' and more' : ''}.</strong>`);
  box.innerHTML = rend(html`${bits.map(b => html`<p>${b}</p>`)}`);
}
async function fertDialog(opts) {
  if (!(await needName())) return;
  if (!FERT.plants.length) { try { FERT.plants = await api('GET', '/api/plants'); } catch (e) { toast(e.message, true); return; } }
  if (!FERT.products.length && !FERT.entries.length) { try { await loadFertData(false); } catch (e) { /* products only help pre-filling */ } }
  FD = fertState0(opts);
  for (;;) {
    const S = FD, editing = !!S.id, sel = new Set(S.codes), t = todayStr();
    const sec = (v, list, cur) => list.map(x => html`<option value="${x}" ${x === cur ? raw('selected') : ''}>${x}</option>`);
    const num = v => v == null ? '' : v;
    const rest = S.id ? [] : FERT.plants;
    const mp = modal(html`<form method="dialog" data-fert="1"><h2>${editing ? 'Change this feeding' : 'Log fertilizer'}</h2>
      <div class="field-grid"><label class="f">Date<input type="date" name="applied_on" value="${S.applied_on}" max="${addDays(t, 1)}" required></label>
        <label class="f">Fertilizer name<input type="text" name="product" list="fert-products" maxlength="80" value="${S.product}" autocomplete="off" ${editing ? '' : raw('autofocus')}><small>Pick one you used before to fill in the rest.</small></label></div>
      <datalist id="fert-products">${FERT.products.map(x => html`<option value="${x.product}"></option>`)}</datalist>
      <label class="f">Type<select name="form">${sec('', ['liquid', 'powder', 'granular', 'slow-release', 'spikes', 'organic liquid', 'organic solid', 'foliar spray', 'other'], S.form)}</select></label>
      <fieldset class="opt-group"><legend>What is printed on the package (N-P-K, in percent)</legend>
        <div class="field-grid three"><label class="f">Nitrogen (N)<input type="number" step="any" min="0" max="100" name="n" value="${num(S.n)}"></label>
          <label class="f">Phosphate (P)<input type="number" step="any" min="0" max="100" name="p" value="${num(S.p)}"></label>
          <label class="f">Potash (K)<input type="number" step="any" min="0" max="100" name="k" value="${num(S.k)}"></label></div>
        <p class="hint">A bottle labelled 24-8-16 is 24% nitrogen, 8% phosphate and 16% potash. Leave a box empty if the package does not say.</p></fieldset>
      <fieldset class="opt-group"><legend>How much, and into how much water</legend>
        <div class="field-grid"><label class="f">Amount of fertilizer<input type="number" step="any" min="0" name="amount" value="${num(S.amount)}"></label>
          <label class="f">Unit<select name="amount_unit">${sec('', ['tsp', 'tbsp', 'g', 'oz', 'ml', 'fl oz'], S.amount_unit)}</select></label>
          <label class="f">Mixed into this much water<input type="number" step="any" min="0" name="water_amount" value="${num(S.water_amount)}"></label>
          <label class="f">Water unit<select name="water_unit">${sec('', ['gal', 'L', 'qt', 'cup'], S.water_unit)}</select></label></div>
        <p class="hint">For example 1 tsp in 1 gal. Leave the water empty for dry products worked into the soil.</p></fieldset>
      <div class="field-grid"><label class="f">How it was applied<select name="method">${sec('', ['water in', 'foliar spray', 'top-dress', 'mixed into soil', 'spike', 'other'], S.method)}</select></label>
        <label class="f">Note<input type="text" name="note" maxlength="500" value="${S.note}"></label></div>
      <div id="fert-preview" class="notice" aria-live="polite"></div>
      ${editing ? html`<p class="muted">Plant: ${((FERT.plants.find(p => p.code === S.codes[0]) || (CUR && CUR.p)) || {}).common_name || S.codes[0]}</p>` : html`<fieldset class="opt-group"><legend>Plants fed (${sel.size} chosen)</legend>
        <div class="row noprint"><button class="btn ghost small" type="button" data-act="fertpick" data-how="due">All that are due</button><button class="btn ghost small" type="button" data-act="fertpick" data-how="season">All in season</button><button class="btn ghost small" type="button" data-act="fertpick" data-how="none">None</button></div>
        <div class="pickbox">${rest.map(p => html`<label class="chk-row"><input type="checkbox" name="pl" value="${p.code}" ${sel.has(p.code) ? raw('checked') : ''}><span>${p.common_name} <span class="muted">${p.code}</span></span></label>`)}</div></fieldset>`}
      <div class="row"><button class="btn" value="ok">${editing ? 'Save changes' : 'Save feeding'}</button><button class="btn ghost" value="cancel">Cancel</button></div></form>`);
    fertPreview();
    const r = await mp;
    if (r !== 'ok') { FD = null; return; }
    const s = readFert(); FD = s;
    try {
      const body = { ...s, plants: s.codes };
      if (!editing && !s.codes.length) throw new Error('Choose at least one plant.');
      const resting = s.codes.map(c0 => FERT.plants.find(p => p.code === c0)).filter(p => p && hasSeason(p) && !monthIn(p, +s.applied_on.slice(5, 7)));
      if (!editing && resting.length && !(await confirmBox('Some plants are resting', `${resting.length} of the chosen plants are in their resting season on that date (${resting.slice(0, 5).map(p => p.common_name).join(', ')}${resting.length > 5 ? ' and more' : ''}). Log it anyway?`, 'Log anyway', false))) { continue; }
      if (editing) await api('PUT', '/api/fertilizer/' + s.id, body); else await api('POST', '/api/fertilizer', body);
      toast(editing ? 'Feeding changed' : 'Feeding logged for ' + s.codes.length + ' plant' + (s.codes.length === 1 ? '' : 's'));
      FD = null; await fertRefresh(); return;
    } catch (e) { toast(e.message, true); }
  }
}
async function fertRefresh() {
  if (document.getElementById('fert-plant')) return loadFertPlant();
  return route();
}
