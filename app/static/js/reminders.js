/* Plant record front end: your own reminders (prototype proto/reminders). One of the files loaded in order by index.html
   (js/manifest.json); they share one scope. Plain JavaScript, no inline handlers (the server's content policy forbids them).

   A reminder is a note to yourself with a date, for one plant or for none: "Check the cutting for roots", "Spray again for
   mealybugs", "Buy potting mix". It shows on Today from its day until it is done; a plant's page lists its own and has "Add a
   reminder". The page #/reminders (in the Today row) lists them all. One can repeat: done, and the next one is set that many days
   after today. Server: plantdb/reminders.py. */
'use strict';

const RM_WHEN = [['1', 'Tomorrow'], ['3', 'In 3 days'], ['7', 'In a week'], ['14', 'In 2 weeks'], ['30', 'In a month'], ['90', 'In 3 months'], ['day', 'On this date']];
const rmPl = (n, one, many) => `${n} ${n === 1 ? one : many}`;
const rmDay = s => parseYmd(s).toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' });   // "Saturday, November 7"
function rmDue(r) {                     // "Due today", "2 days late: it was due Saturday, November 7", "Due Tuesday, November 10"
  const n = daysBetween(r.due_on, todayStr());
  if (n === 0) return 'Due today';
  if (n === 1) return 'Due yesterday';
  if (n > 0) return `${rmPl(n, 'day', 'days')} late: it was due ${rmDay(r.due_on)}`;
  return 'Due ' + (n === -1 ? 'tomorrow' : rmDay(r.due_on));
}
const rmRepeat = r => r.repeat_days ? ` ${r.repeat_word}.` : '';
const rmWho = r => r.created_by && r.created_by !== 'Unknown' ? ` Set by ${r.created_by}.` : '';
function rmBtns(r, small) {
  const what = r.text + (r.plant_name ? ', ' + r.plant_name : '');
  return html`<button class="btn small" type="button" data-act="rmdone" data-id="${r.id}" aria-label="${'Done: ' + what}">Done</button>
    ${small ? '' : html`<button class="btn small ghost" type="button" data-act="rmlater" data-id="${r.id}" data-due="${r.due_on}" aria-label="${'Remind me in a week instead: ' + what}">A week later</button>`}
    <button class="btn small ghost" type="button" data-act="rmedit" data-id="${r.id}" aria-label="${'Change or remove: ' + what}">Change</button>`;
}
// One reminder as a row: the plant's photo and name when it is for a plant, else a plain box
function rmRow(r, small) {
  const words = html`<strong class="rm-text">${r.text}</strong><div class="rm-when rm-${r.state}">${r.state === 'late' ? html`<span class="rm-flag">Late:</span> ` : ''}${rmDue(r)}.${rmRepeat(r)}${rmWho(r)}</div>`;
  if (r.plant_code) return html`<li class="job rm-job" data-rm="${r.id}" data-code="${r.plant_code}">${r.photo ? html`<img src="${thumbUrl(r.photo)}" alt="" loading="lazy" width="64" height="64">` : html`<span class="job-nophoto" aria-hidden="true"></span>`}
    <div class="job-txt"><a class="nm" href="#/plant/${enc(r.plant_code)}">${r.plant_name || r.plant_code}</a> <span class="muted">${r.plant_code}</span><div>${words}</div></div>
    <div class="job-acts">${rmBtns(r, small)}</div></li>`;
  return html`<li class="job rm-job" data-rm="${r.id}"><span class="job-nophoto rm-none" aria-hidden="true"></span>
    <div class="job-txt"><span class="nm">Not for a particular plant</span><div>${words}</div></div><div class="job-acts">${rmBtns(r, small)}</div></li>`;
}
function rmDoneRow(r) {
  return html`<li class="rm-donerow" data-rm="${r.id}"><span><strong>${r.text}</strong>${r.plant_code ? html` (<a href="#/plant/${enc(r.plant_code)}">${r.plant_name || r.plant_code}</a>)` : ''}:
    done ${relDay(r.done_on)}${r.done_by && r.done_by !== 'Unknown' ? ' by ' + r.done_by : ''}.</span>
    ${r.can_undo ? html`<button class="btn small ghost" type="button" data-act="rmundo" data-id="${r.id}" aria-label="${'Not done yet: ' + r.text}">Not done yet</button>` : ''}</li>`;
}
async function viewReminders() {
  const R = await api('GET', '/api/reminders');
  const due = R.open.filter(r => r.state !== 'later'), later = R.open.filter(r => r.state === 'later');
  const line = R.counts.due ? `${rmPl(R.counts.due, 'reminder is', 'reminders are')} due${R.counts.late ? `, ${R.counts.late} of them late` : ''}.`
    : 'Nothing is due today.';
  return {
    title: 'Reminders',
    after: () => navMark('reminders'),
    html: html`<h1>Reminders</h1>
    <p class="muted">Notes to yourself with a date: something to check on a plant, a second spray, something to buy. Each one shows on Today from its day until you press Done.</p>
    <div class="verdict-box rm-sum" role="status"><p><strong>${line}</strong> ${later.length ? `${rmPl(later.length, 'more is', 'more are')} coming up.` : ''}</p>
      <p><button class="btn" type="button" data-act="rmnew">Add a reminder</button></p></div>
    <section class="blk" id="rm-due"><h2>Due now (${due.length})</h2>
      ${due.length ? html`<ul class="jobs">${due.map(r => rmRow(r))}</ul>` : html`<p class="muted">Nothing is due today.</p>`}</section>
    <section class="blk" id="rm-later"><h2>Coming up (${later.length})</h2>
      ${later.length ? html`<ul class="jobs">${later.map(r => rmRow(r, true))}</ul>` : html`<p class="muted">No reminders set for later.</p>`}</section>
    <section class="blk" id="rm-done"><h2>Done lately (${R.done.length})</h2>
      ${R.done.length ? html`<p class="hint">The last 30 days. "Not done yet" puts one back, as long as its next time round has not been changed.</p><ul class="rm-done">${R.done.map(rmDoneRow)}</ul>`
        : html`<p class="muted">Nothing done in the last 30 days.</p>`}</section>`,
  };
}
// after a change: draw the page again where you were, and put the focus somewhere sensible
async function rmAfter(focusSel) {
  if (document.getElementById('care-plant') && CUR) await featAdds(['plant', CUR.p.code], true);
  else { const y = window.scrollY; ROUTE_FRESH = true; await route(); window.scrollTo(0, y); }
  const f = (focusSel && document.querySelector(focusSel)) || document.querySelector('#rm-plant button, #rm-due .job button, #today-remind .job button, [data-act=rmnew]') || document.querySelector('main h1');
  if (f) f.focus({ preventScroll: true });
}
// One window for a new reminder or a change to one. code: the plant it is for (from a plant's page), or none (choose in the window)
async function rmDialog(r, code) {
  if (!(await needName())) return;
  let plants = [];
  if (!r && !code) { try { plants = (await api('GET', '/api/plants')).filter(atPlace).sort((a, b) => a.common_name.localeCompare(b.common_name)); } catch (e) { plants = []; } }
  const R = await api('GET', '/api/reminders?done=0' + (code ? '&plant=' + enc(code) : ''));
  const name = code ? (CUR && CUR.p.code === code ? CUR.p.common_name : code) : r && r.plant_name;
  const res = await modal(html`<form method="dialog" class="rm-dlg"><h2>${r ? 'Change the reminder' : 'Add a reminder'}${name ? ': ' + name : ''}</h2>
    <label class="f">What to do<input type="text" name="text" maxlength="200" required autocomplete="off" value="${r ? r.text : ''}" aria-describedby="rm-eg"></label>
    <p class="hint" id="rm-eg">For example: Check the cutting for roots. Spray again for mealybugs. Buy potting mix.</p>
    ${!r && !code ? html`<label class="f">For which plant<select name="plant"><option value="">Not for a particular plant</option>${plants.map(p => html`<option value="${p.code}">${p.common_name} (${p.code})</option>`)}</select></label>` : ''}
    <fieldset><legend>${r ? `${rmDue(r)}. Move it to` : 'When'}</legend>
      ${r ? html`<label class="chk"><input type="radio" name="when" value="" checked> Leave the date as it is</label>` : ''}
      ${RM_WHEN.map(([v, l], i) => html`<label class="chk"><input type="radio" name="when" value="${v}" ${!r && v === '7' ? raw('checked') : ''}> ${l}${v === 'day' ? ':' : ` (${midDay(addDays(todayStr(), +v))})`}</label>`)}
      <label class="f">The date, for "On this date"<input type="date" name="day" min="${todayStr()}"></label></fieldset>
    <label class="f">Repeat<select name="repeat">${R.repeats.map(([n, l]) => html`<option value="${n}" ${(r ? r.repeat_days : 0) === n ? raw('selected') : ''}>${l}</option>`)}</select></label>
    <p class="hint">A repeating reminder comes back that long after the day you press Done.</p>
    <div class="row"><button class="btn" value="ok">${r ? 'Save changes' : 'Add the reminder'}</button>
      ${r ? html`<button class="btn ghost danger" value="del">Remove it</button>` : ''}<button class="btn ghost" value="cancel">Cancel</button></div></form>`);
  if (res !== 'ok' && res !== 'del') return;
  const f = dlg.querySelector('form');
  if (res === 'del') {
    if (!(await confirmBox('Remove this reminder?', `"${r.text}" goes from the list. The audit log keeps a note of it.`, 'Remove it', true))) return;
    await guard(async () => { await api('DELETE', '/api/reminders/' + r.id); toast('Reminder removed: ' + r.text); await rmAfter(); });
    return;
  }
  let w = f.elements.when.value;
  if (!w && f.elements.day.value) w = 'day';          // a date typed in without choosing "On this date" first
  let due = null;
  if (w === 'day') { if (!f.elements.day.value) { toast('Choose the date, or pick one of the other choices.', true); return; } due = f.elements.day.value; }
  else if (w) due = addDays(todayStr(), +w);
  const text = f.elements.text.value.trim();
  if (!text) { toast('Say what the reminder is for.', true); return; }
  const body = { text, repeat_days: +f.elements.repeat.value };
  if (due) body.due_on = due;
  await guard(async () => {
    if (r) { await api('PUT', '/api/reminders/' + r.id, body); toast('Reminder saved' + (due ? ': due ' + relDay(due) : '') + '.'); }
    else {
      body.plant = code || (f.elements.plant ? f.elements.plant.value : '');
      const x = await api('POST', '/api/reminders', body);
      toast(`Reminder added for ${relDay(body.due_on)}: ${text}` + offWhen(x));
    }
    await rmAfter(r ? `[data-rm="${r.id}"] button` : null);
  });
}
async function rmFind(id) {
  const R = await api('GET', '/api/reminders' + (CUR && document.getElementById('care-plant') ? '?plant=' + enc(CUR.p.code) : ''));
  return R.open.find(x => String(x.id) === String(id)) || R.done.find(x => String(x.id) === String(id));
}
Object.assign(acts, {
  async rmnew(el) { await rmDialog(null, el.dataset.code || null); },
  async rmedit(el) { const r = await guard(() => rmFind(el.dataset.id)); if (r) await rmDialog(r); },
  async rmdone(el) {
    if (!(await needName())) return;
    await guard(async () => {
      const x = await api('POST', `/api/reminders/${el.dataset.id}/done`);
      toast('Done.' + (x && x.next ? ` It comes back ${relDay(x.next)}.` : '') + ' "Not done yet" on the Reminders page puts it back.');
      await rmAfter();
    });
  },
  async rmlater(el) {
    if (!(await needName())) return;
    const d = addDays(el.dataset.due > todayStr() ? el.dataset.due : todayStr(), 7);
    await guard(async () => { await api('PUT', '/api/reminders/' + el.dataset.id, { due_on: d }); toast('Moved to ' + relDay(d) + '.'); await rmAfter(); });
  },
  async rmundo(el) {
    if (!(await needName())) return;
    await guard(async () => { await api('DELETE', `/api/reminders/${el.dataset.id}/done`); toast('Put back on the list.'); await rmAfter(`[data-rm="${el.dataset.id}"] button`); });
  },
});

// What this module adds (features.js): the page, a block on Today when something is due, and a line on a plant's page
addFeature({
  name: 'reminders',
  pages: { reminders: { view: viewReminders, nav: 'reminders', section: 'today', label: 'Reminders', href: '#/reminders', after: 'repotting' } },
  today: {
    id: 'today-remind', order: 69,                                   // after repotting (68), before needed from you (70)
    load: async () => { const R = await api('GET', '/api/reminders?done=0'); return R.counts.due ? R : null; },
    jump: R => `Reminders (${R.counts.due})`,
    html: R => html`<section class="blk" id="today-remind"><h2>Reminders (${R.counts.due})</h2>
      <ul class="jobs">${R.open.filter(r => r.state !== 'later').map(r => rmRow(r))}</ul>
      <p><a class="btn small ghost" href="#/reminders">All reminders</a> <button class="btn small ghost" type="button" data-act="rmnew">Add a reminder</button></p></section>`,
  },
  adds: {
    id: 'rm-plant', care: true,
    match: parts => parts[0] === 'plant' && parts[1] && parts[2] !== 'edit',
    anchor: main => { const b = main.querySelector('.quick-btns'); return b && b.parentElement; }, where: 'beforeend',
    load: async parts => {
      if (!CUR || CUR.p.code !== parts[1]) return null;
      const R = await api('GET', '/api/reminders?done=0&plant=' + enc(parts[1]));     // offline with nothing saved: leave it out
      return { R, code: parts[1], name: CUR.p.common_name };
    },
    html: ({ R, code, name }) => html`<div class="rm-plant" id="rm-plant"><p class="hint">Reminders: ${R.open.length ? rmPl(R.open.length, 'set', 'set') + '.' : 'none set.'}
        <button class="btn small ghost" type="button" data-act="rmnew" data-code="${code}" aria-label="${'Add a reminder for ' + name}">Add a reminder</button> <a href="#/reminders">All reminders</a></p>
      ${R.open.length ? html`<ul class="jobs rm-plist">${R.open.map(r => html`<li class="job rm-job" data-rm="${r.id}"><div class="job-txt"><strong class="rm-text">${r.text}</strong>
        <div class="rm-when rm-${r.state}">${r.state === 'late' ? html`<span class="rm-flag">Late:</span> ` : ''}${rmDue(r)}.${rmRepeat(r)}</div></div>
        <div class="job-acts">${rmBtns(r, r.state === 'later')}</div></li>`)}</ul>` : ''}</div>`,
  },
});
