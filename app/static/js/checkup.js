// ---------- prototype proto/health-walk: a walk round the plants, one at a time, to say how each one looks now ----------
// Rebuilt on the 1.32.0 layout for 1.42.0: this file loads after events.js (it adds to acts, changeActs and formActs) and before main.js.
// #/checkup chooses which plants (due ones, where, which group, in what order) and holds the settings for how often plants
// are due; #/checkup/walk shows one plant at a time with big health choices and Take a photo. "Looks the same" is logged as
// care kind 'looked'; a new rating and the note (added to the Health summary) are saved on the plant page (version checked)
// and logged too. Group pages get a "Health walk-through" section with the group's own number of days. The walk is kept in CK
// while the app is open; the choices are remembered in localStorage plantdb.checkup.
Object.assign(CARE_WORD, { looked: 'Looked over' });
if (!SECTIONS[0][2].some(x => x[0] === 'checkup')) SECTIONS[0][2].push(['checkup', 'Health walk-through', '#/checkup']);   // a second page in the Today section of the top bar
const CK = { data: null, list: null, i: 0, done: {}, focus: false };
const CK_KEY = 'plantdb.checkup', CK_ORDER = { oldest: 'Longest since looked over first', worst: 'Worst health first', code: 'By plant code' };
function ckOpts() {
  let o = {};
  try { o = JSON.parse(localStorage.getItem(CK_KEY) || '{}') || {}; } catch (e) { o = {}; }
  return { which: o.which === 'all' ? 'all' : 'due', site: typeof o.site === 'string' ? o.site : '', group: /^\d+$/.test(String(o.group || '')) ? String(o.group) : '',
    order: CK_ORDER[o.order] ? o.order : 'oldest' };
}
function ckKeep(o) { try { localStorage.setItem(CK_KEY, JSON.stringify(o)); } catch (e) { /* storage blocked: fine for this visit */ } }
const ckAgo = p => p.last_looked == null ? 'Not looked over yet' : p.days <= 0 ? 'Looked over today' : p.days === 1 ? 'Looked over yesterday'
  : `Looked over ${p.days} days ago (${relDay(p.last_looked)})`;
const ckEvery = p => `Due every ${ckN(p.every, 'day', 'days')}` + (p.every_why === 'the usual' ? '' : `, because ${p.every_why.startsWith('the group') ? 'of ' : ''}${p.every_why}`);
function ckPick(D, o) {
  const l = D.plants.filter(p => (o.which === 'all' || p.due) && (!o.site || p.site === o.site) && (!o.group || p.groups.includes(+o.group)));
  const age = p => p.days == null ? 1e6 : p.days - p.every;           // most overdue first
  const hw = p => HEALTH_ORDER[p.health] == null ? 9 : HEALTH_ORDER[p.health];
  if (o.order === 'oldest') l.sort((a, b) => age(b) - age(a) || a.code.localeCompare(b.code));
  else if (o.order === 'worst') l.sort((a, b) => hw(a) - hw(b) || age(b) - age(a) || a.code.localeCompare(b.code));
  else l.sort((a, b) => a.code.localeCompare(b.code));
  return l;
}
const ckN = (n, one, many) => n + ' ' + (n === 1 ? one : many);
const ckFormOpts = f => ({ which: f.elements.which.value, site: f.elements.site.value, group: f.elements.group ? f.elements.group.value : '', order: f.elements.order.value });
function ckCountText() {
  const f = document.querySelector('form[data-form=ckstart]'); if (!f || !CK.data) return '';
  const n = ckPick(CK.data, ckFormOpts(f)).length;
  const b = f.querySelector('button[type=submit]'); if (b) b.disabled = !n;
  return n ? `This walk-through has ${ckN(n, 'plant', 'plants')}.` : 'No plants match these choices.';
}
function ckSetupHtml(D) {
  const o = ckOpts(), due = D.plants.filter(p => p.due);
  const sites = D.sites.filter(s => D.plants.some(p => p.site === s));
  if (o.site && !sites.includes(o.site)) o.site = '';
  if (o.group && !D.groups.some(g => String(g.id) === o.group)) o.group = '';
  const radio = (name, v, label) => html`<label><input type="radio" name="${name}" value="${v}" data-act="ckopt" ${o[name] === v ? raw('checked') : ''}><span>${label}</span></label>`;
  const left = CK.list && CK.i < CK.list.length;
  const own = D.groups.filter(g => g.days);
  return html`<h1>Health walk-through</h1>
    <p>Go round your plants one at a time and say how each one looks today. If nothing has changed, one press saves it and moves on.
      A plant is due again after ${ckN(D.due_days, 'day', 'days')}, or ${ckN(D.poor_days, 'day', 'days')} when its health is Poor or Critical. A group can have its own number, which then decides for its plants.</p>
    <div class="verdict-box" role="status"><p><strong>${due.length ? `${ckN(due.length, 'plant is', 'plants are')} due to be looked over.` : 'Every plant has been looked over recently.'}</strong>
      ${due.length && D.plants.length - due.length ? ` ${ckN(D.plants.length - due.length, 'plant was', 'plants were')} looked over recently.` : ''}</p></div>
    ${left ? html`<p class="ck-resume"><a class="btn" href="#/checkup/walk" data-act="ckresume">Carry on where you stopped: plant ${CK.i + 1} of ${CK.list.length}</a></p>` : ''}
    <form data-form="ckstart" class="ck-setup noprint">
      <fieldset class="opt-group"><legend>Which plants</legend><div class="opts">${radio('which', 'due', `Due ones (${due.length})`)}${radio('which', 'all', `All of them (${D.plants.length})`)}</div></fieldset>
      <fieldset class="opt-group"><legend>Where</legend><div class="opts">${radio('site', '', 'Everywhere')}${sites.map(s => radio('site', s, s))}</div></fieldset>
      ${D.groups.length ? html`<label class="f ck-group">Group<select name="group" data-act="ckopt"><option value="">Any group, or none</option>
        ${D.groups.map(g => html`<option value="${g.id}" ${o.group === String(g.id) ? raw('selected') : ''}>${g.name} (${ckN(g.count, 'plant', 'plants')})</option>`)}</select></label>` : ''}
      <fieldset class="opt-group"><legend>In what order</legend><div class="opts">${Object.entries(CK_ORDER).map(([k, v]) => radio('order', k, v))}</div></fieldset>
      <p id="ck-count" class="ck-count" role="status" aria-live="polite"></p>
      <p><button class="btn ck-big" type="submit">${left ? 'Start a new walk-through' : 'Start the walk-through'}</button></p>
    </form>
    <section class="blk" id="ck-due"><h2>Due to be looked over (${due.length})</h2>
      ${due.length ? html`<details class="ck-notes"><summary>Show the ${ckN(due.length, 'plant', 'plants')}, most overdue first</summary><ul class="ck-due">${ckPick(D, { which: 'due', site: '', group: '', order: 'oldest' }).map(p => html`<li><a href="#/plant/${enc(p.code)}">${p.code}</a> ${p.name}
        <span class="ck-meta">${p.site}${p.health ? ', health ' + p.health : ''}. ${ckAgo(p)}. ${ckEvery(p)}.</span></li>`)}</ul></details>` : html`<p class="notice ok">Nothing is due.</p>`}</section>
    <section class="blk" id="ck-how-often"><h2>How often plants are due</h2>
      ${canChange() ? html`<form data-form="ckset" class="ck-set">
        <label class="f">Days between looks, usually<input type="number" name="days" min="1" max="365" step="1" inputmode="numeric" required value="${D.due_days}"></label>
        <label class="f">Days between looks for plants in Poor or Critical health<input type="number" name="poor_days" min="1" max="365" step="1" inputmode="numeric" required value="${D.poor_days}"></label>
        <p><button class="btn" type="submit">Save how often</button></p></form>`
        : html`<p>Usually every ${ckN(D.due_days, 'day', 'days')}; plants in Poor or Critical health every ${ckN(D.poor_days, 'day', 'days')}.</p>`}
      <h3>Groups with their own number</h3>
      ${own.length ? html`<ul class="ck-list">${own.map(g => html`<li><a href="#/group/${g.id}">${g.name}</a>: every ${ckN(g.days, 'day', 'days')} (${ckN(g.count, 'plant', 'plants')})</li>`)}</ul>` : html`<p>None yet.</p>`}
      <p class="hint">To give a group its own number, open the group from the <a href="#/groups">Groups</a> page and use its Health walk-through section.
        A plant in a group with its own number goes by that number, even when its health is Poor or Critical, so a group can be looked at less often (cacti once a month, say).
        A plant in several such groups goes by the shortest of them. Plants in no group with its own number go by the Poor or Critical number when their health is Poor or Critical.</p></section>`;
}
function ckPhotoHtml(p) {
  return p.photo ? html`<a href="${photoUrl(p.photo)}" target="_blank" rel="noopener"><img src="${thumbUrl(p.photo)}" alt="${(p.newphoto ? 'New photo of ' : 'Photo of ') + p.name}"></a>${p.newphoto ? html`<p class="ck-meta">The photo you just took.</p>` : ''}`
    : html`<div class="ck-nophoto">No photo yet</div>`;
}
function ckCardHtml() {
  const p = CK.list[CK.i], n = CK.list.length, prev = CK.done[p.code];
  const opts = (CK.data.health || ['Good', 'Fair', 'Poor', 'Critical']);
  const cur = prev && prev.now ? prev.now : p.health;
  return html`<h1>Health walk-through</h1>
    <div class="ck-prog"><p><strong>Plant ${CK.i + 1} of ${n}</strong>${Object.keys(CK.done).length ? `. Saved so far: ${Object.values(CK.done).filter(d => d.kind !== 'skip').length}` : ''}</p>
      <progress max="${n}" value="${CK.i}" aria-label="${`Plant ${CK.i + 1} of ${n}`}"></progress></div>
    <article class="ck-card" aria-labelledby="ck-name">
      <div class="ck-photo"><div id="ck-pic">${ckPhotoHtml(p)}</div>
        ${canChange() ? html`<label class="btn ghost ck-photo-btn">Take a photo<input type="file" accept="image/*" capture="environment" data-act="ckphoto" class="sr"></label>` : ''}</div>
      <div class="ck-body">
        <div class="ck-title" id="ck-name" role="heading" aria-level="2" tabindex="-1"><a href="#/plant/${enc(p.code)}">${p.code}</a> ${p.name}</div>
        <p>${p.site}${p.location ? ': ' + p.location : ''}</p>
        <p>${p.health ? healthTag(p.health) : html`<span class="tag">Health: not set</span>`} <span class="ck-meta">${ckAgo(p)}. ${ckEvery(p)}.</span></p>
        ${prev ? html`<p class="notice ok">Already saved on this walk: ${prev.text}. Saving again adds another entry.</p>` : ''}
        ${p.summary ? html`<details class="ck-notes"><summary>Health notes on its page</summary><p class="pl">${p.summary}</p></details>` : ''}
        ${canChange() ? html`<form data-form="cksave" class="ck-form">
          <fieldset class="opt-group"><legend>How does it look now?</legend><div class="opts ck-health">${opts.map(h => html`<label><input type="radio" name="health" value="${h}" data-act="ckpick" ${cur === h ? raw('checked') : ''}><span>${h}${h === p.health ? ' (as before)' : ''}</span></label>`)}</div></fieldset>
          <label class="f">Anything you noticed? (optional)<small>It goes in the care log and at the end of its health notes, with today's date.</small><textarea name="note" rows="2" maxlength="400"></textarea></label>
          <div class="ck-acts"><button class="btn ck-big" type="submit" id="ck-save">${ckSaveWord(p, cur)}</button>
            <button class="btn ghost" type="button" data-act="ckskip">Skip this plant</button></div>
        </form>` : html`<p class="notice">Changes are turned off for you, so you can look through the plants but not save.</p>
          <div class="ck-acts"><button class="btn" type="button" data-act="ckskip">Next plant</button></div>`}
        <div class="ck-nav"><button class="btn ghost small" type="button" data-act="ckback" ${CK.i ? '' : raw('disabled')}>Back to the previous plant</button>
          <button class="btn ghost small" type="button" data-act="ckstop">Stop and see what you've done</button></div>
      </div>
    </article>`;
}
const ckSaveWord = (p, h) => !h || h === p.health ? 'Looks the same: save and go on' : `Save "${h}" and go on`;
function ckDoneHtml() {
  const all = Object.values(CK.done), changed = all.filter(d => d.kind === 'changed'), same = all.filter(d => d.kind === 'same'), skipped = all.filter(d => d.kind === 'skip');
  const pics = (CK.list || []).filter(p => p.pics).reduce((s, p) => s + p.pics, 0);
  const left = CK.list ? CK.list.length - CK.i : 0;
  const li = d => html`<li><a href="#/plant/${enc(d.code)}">${d.code}</a> ${d.name}: ${d.text}</li>`;
  return html`<h1>${left > 0 ? 'Walk-through paused' : 'Walk-through finished'}</h1>
    <div class="verdict-box" role="status"><p><strong>You looked over ${ckN(changed.length + same.length, 'plant', 'plants')}${changed.length ? `, and ${ckN(changed.length, 'has', 'have')} a new health rating` : ''}.</strong>
      ${pics ? ` You took ${ckN(pics, 'new photo', 'new photos')}.` : ''}${skipped.length ? ` ${ckN(skipped.length, 'plant was', 'plants were')} skipped.` : ''}${left > 0 ? ` ${ckN(left, 'plant is', 'plants are')} left on this walk.` : ''}</p></div>
    <p class="ck-acts">${left > 0 ? html`<a class="btn" href="#/checkup/walk" data-act="ckresume">Carry on: plant ${CK.i + 1} of ${CK.list.length}</a>` : ''}
      <a class="btn ghost" href="#/checkup">Start another walk-through</a> <a class="btn ghost" href="#/today">Back to Today</a></p>
    ${changed.length ? html`<section class="blk"><h2>New health ratings (${changed.length})</h2><ul class="ck-list">${changed.map(li)}</ul></section>` : ''}
    ${skipped.length ? html`<section class="blk"><h2>Skipped (${skipped.length})</h2><ul class="ck-list">${skipped.map(li)}</ul></section>` : ''}
    ${same.length ? html`<section class="blk"><h2>Look the same (${same.length})</h2><ul class="ck-list">${same.map(li)}</ul></section>` : ''}`;
}
async function viewCheckup(sub) {
  const navToday = () => { navMark('checkup'); pagesMenu(false); };          // a page of the Today section
  if (sub === 'walk' && CK.list) {
    const end = CK.stopped || CK.i >= CK.list.length;
    return { title: 'Health walk-through', html: end ? ckDoneHtml() : ckCardHtml(), after: () => {
      navToday();
      if (CK.focus) { CK.focus = false; setTimeout(() => { const h = document.getElementById(end ? 'app' : 'ck-name'); window.scrollTo(0, 0); if (h) h.focus({ preventScroll: true }); }, 0); }     // after route() focuses #app
    } };
  }
  CK.data = await api('GET', '/api/checkup');
  return { title: 'Health walk-through', html: ckSetupHtml(CK.data), after: () => {
    navToday(); const c = document.getElementById('ck-count'); if (c) c.textContent = ckCountText();
  } };
}
function ckNext(rec) {
  const p = CK.list[CK.i];
  if (rec) CK.done[p.code] = Object.assign({ code: p.code, name: p.name }, rec);
  CK.i++; CK.focus = true; go('#/checkup/walk');
}
// the line added to the end of the Health summary: "Nov 4, 2026 (health walk-through): Good to Poor. Yellow lower leaves."
function ckSummaryLine(was, now, note) {
  const d = parseYmd(todayStr()).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });
  const t = (was !== now ? `${was || 'Not set'} to ${now}. ` : '') + note;
  return `${d} (health walk-through): ${/[.!?]$/.test(t) ? t : t + '.'}`;
}
Object.assign(acts, {
  ckskip() { if (!CK.list) return; const p = CK.list[CK.i]; ckNext(CK.done[p.code] && CK.done[p.code].kind !== 'skip' ? null : { kind: 'skip', text: 'skipped' }); },
  ckback() { if (!CK.list || !CK.i) return; CK.i = Math.min(CK.i, CK.list.length) - 1; CK.stopped = false; CK.focus = true; go('#/checkup/walk'); },
  ckstop() { CK.stopped = true; CK.focus = true; go('#/checkup/walk'); },
  ckresume() { CK.stopped = false; CK.focus = true; go('#/checkup/walk'); },
  ckgroupwalk(el) { ckKeep(Object.assign(ckOpts(), { which: 'due', site: '', group: el.dataset.id })); go('#/checkup'); },
});
Object.assign(changeActs, {
  ckopt() {
    const f = document.querySelector('form[data-form=ckstart]'); if (!f) return;
    ckKeep(ckFormOpts(f));
    const c = document.getElementById('ck-count'); if (c) c.textContent = ckCountText();
  },
  ckpick(el) { const b = document.getElementById('ck-save'); if (b && CK.list) b.textContent = ckSaveWord(CK.list[CK.i], el.value); },
  async ckphoto(el) {                       // Take a photo during the walk: added to the plant's photos; the note and choice on the page stay as they are
    if (!el.files.length || !CK.list) return;
    const p = CK.list[CK.i];
    if (!(await needName())) { el.value = ''; return; }
    const files = await photoCheck([...el.files], el); if (!files) { el.value = ''; return; }
    const fd = new FormData(); files.forEach(f => fd.append('files', f)); fd.append('caption', 'Health walk-through, ' + todayStr());
    toast('Uploading the photo');
    await guard(async () => {
      const r = await api('POST', '/api/plants/' + enc(p.code) + '/photos', undefined, fd);
      if (r && r.version) p.version = r.version;                        // adding a photo raises the page version
      const ph = r && r.photos ? r.photos.slice().sort((a, b) => b.id - a.id)[0] : null;
      if (ph) { p.photo = ph.file; p.newphoto = true; }
      p.pics = (p.pics || 0) + files.length;
      const box = document.getElementById('ck-pic'); if (box) box.innerHTML = rend(ckPhotoHtml(p));
      toast(r && r.offline ? `Photo kept on this device for ${p.code}. It is sent when the connection is back.` : `Photo added to ${p.code}`);
    });
    el.value = '';
  },
});
Object.assign(formActs, {
  ckstart(form) {
    const o = ckFormOpts(form);
    ckKeep(o);
    CK.list = ckPick(CK.data, o).map(p => Object.assign({}, p)); CK.i = 0; CK.done = {}; CK.stopped = false; CK.focus = true;
    if (!CK.list.length) { toast('No plants match these choices.', true); return; }
    go('#/checkup/walk');
  },
  async ckset(form) {
    if (!(await needName())) return;
    CK.data = await api('PUT', '/api/checkup/settings', { days: form.elements.days.value, poor_days: form.elements.poor_days.value });
    toast(`Saved: every ${form.elements.days.value} days, or ${form.elements.poor_days.value} for plants in Poor or Critical health`);
    route();
  },
  async ckgroupset(form) {
    if (!(await needName())) return;
    const v = form.elements.days.value.trim();
    await api('PUT', '/api/checkup/groups/' + enc(form.dataset.id), { days: v === '' ? null : v });
    toast(v === '' ? 'Saved: this group uses the usual number of days' : `Saved: this group is due every ${v} days`);
    const s = document.getElementById('g-walk'); if (s) s.remove();          // drawn again with the new number
    ckGroupBox();
  },
  async cksave(form) {
    if (!(await needName())) return;
    const p = CK.list[CK.i], nh = form.elements.health.value || p.health, note = form.elements.note.value.trim().slice(0, 400);
    const changed = !!nh && nh !== p.health;
    const btn = form.querySelector('button[type=submit]'); if (btn) btn.disabled = true;
    try {
      if (changed || note) {
        const fields = {};
        if (changed) fields.health_rating = nh;
        if (note) fields.health_summary = (p.summary ? p.summary + '\n' : '') + ckSummaryLine(p.health, nh, note);
        const r = await api('PUT', '/api/plants/' + enc(p.code), { base_version: p.version, fields, note: 'Health walk-through' + (note ? ': ' + note : '') });
        if (r && r.version) p.version = r.version;
        if (r && r.health_summary != null) p.summary = r.health_summary;
      }
      const text = changed ? `health ${p.health || 'not set'} to ${nh}` : 'looks the same';
      const cr = await api('POST', '/api/care', { plant: p.code, kind: 'looked', note: (changed ? `Health ${p.health || 'not set'} to ${nh}` : 'Looks the same') + (note ? '. ' + note : '') });
      toast(cr && cr.offline ? `Kept on this device: ${p.code} ${text}. It is sent when the connection is back.` : `Saved: ${p.code} ${text}`);   // 1.38.0 offline: the saves wait like other care
      ckNext({ kind: changed ? 'changed' : 'same', now: nh, was: p.health, text: text + (note ? ` ("${note}")` : '') });
    } catch (e) {
      if (btn) btn.disabled = false;
      if (e.status === 409 && e.data && e.data.current) {          // changed elsewhere since the walk started: show what it is now, and choose again
        const cur = e.data.current;
        p.version = cur.version; p.health = cur.health_rating || ''; p.summary = (cur.health_summary || '').trim();
        toast(`${p.code} was changed by someone else since you started. Its health is now ${p.health || 'not set'}. Choose again and save.`, true);
        route(); return;
      }
      throw e;
    }
  },
});
// the Today page gets a line about the walk-through, added when the page draws (no changes to viewToday)
(function ckTodayLink() {
  const main = document.getElementById('app'); if (!main) return;
  let busy = false;
  new MutationObserver(() => {
    if (location.hash !== '#/today' || busy || main.querySelector('.ck-today')) return;
    const at = main.querySelector('#today-water'); if (!at) return;
    busy = true;
    api('GET', '/api/checkup').then(D => {
      busy = false;
      if (location.hash !== '#/today' || main.querySelector('.ck-today')) return;
      const at2 = main.querySelector('#today-water'); if (!at2) return;
      const due = D.plants.filter(p => p.due).length;
      const p = document.createElement('p'); p.className = 'ck-today noprint';
      p.innerHTML = rend(html`<span>${due ? `${ckN(due, 'plant is', 'plants are')} due to be looked over.` : 'Every plant has been looked over recently.'}</span>
        <a class="btn ghost" href="#/checkup">Health walk-through</a>`);
      at2.before(p);
    }).catch(() => { busy = false; });
  }).observe(main, { childList: true, subtree: true });
})();
// group pages get a "Health walk-through" section after "What suits all of them": the group's own number of days, and a start button
let CK_GBUSY = false;
function ckGroupBox() {
  const main = document.getElementById('app'), m = location.hash.match(/^#\/group\/(\d+)$/);
  if (!main || !m || CK_GBUSY || main.querySelector('#g-walk')) return;
  const at = main.querySelector('#g-fit'); if (!at) return;
  CK_GBUSY = true;
  api('GET', '/api/checkup').then(D => {
    CK_GBUSY = false;
    if (location.hash !== '#/group/' + m[1] || main.querySelector('#g-walk')) return;
    const g = D.groups.find(x => String(x.id) === m[1]), at2 = main.querySelector('#g-fit'); if (!g || !at2) return;
    const mine = D.plants.filter(p => p.groups.includes(g.id)), due = mine.filter(p => p.due).length;
    const s = document.createElement('section'); s.className = 'blk'; s.id = 'g-walk';
    s.innerHTML = rend(html`<h2>Health walk-through</h2>
      <p>${g.days ? `Plants in this group are due to be looked over every ${ckN(g.days, 'day', 'days')}, even when their health is Poor or Critical.`
          : `This group uses the usual number of days (${D.due_days}), and ${ckN(D.poor_days, 'day', 'days')} for plants in Poor or Critical health.`}
        ${mine.length ? (due ? `${due} of its ${ckN(mine.length, 'plant', 'plants')} ${due === 1 ? 'is' : 'are'} due now.` : 'None of its plants are due now.') : ''}</p>
      ${canChange() ? html`<form data-form="ckgroupset" data-id="${g.id}" class="ck-set">
        <label class="f">Days between looks for this group<small>Leave it empty to use the usual ${D.due_days}. The number you give decides for every plant in the group, even ones in Poor or Critical health, so it can be longer than ${D.poor_days} (cacti every 30 days, say). A plant in several groups goes by the shortest.</small>
          <input type="number" name="days" min="1" max="365" step="1" inputmode="numeric" value="${g.days || ''}"></label>
        <p><button class="btn" type="submit">Save for this group</button></p></form>` : ''}
      ${due ? html`<p><button class="btn ghost" type="button" data-act="ckgroupwalk" data-id="${g.id}">Walk through the ${ckN(due, 'due plant', 'due plants')} in this group</button></p>` : ''}`);
    at2.after(s);
    buildSideNav(); addFoldButtons(); navLayout(); addReadButtons();      // 1.42.0: in Navigation, with Show or hide
  }).catch(() => { CK_GBUSY = false; });
}
(function ckGroupWatch() {
  const main = document.getElementById('app'); if (!main) return;
  new MutationObserver(() => { if (/^#\/group\/\d+$/.test(location.hash)) ckGroupBox(); }).observe(main, { childList: true, subtree: true });
})();

