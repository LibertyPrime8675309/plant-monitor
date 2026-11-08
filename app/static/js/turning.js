/* Plant record front end: turn the pots (prototype, proto/turn-pots). One of the files loaded in order by index.html; they share one scope.
   Plain JavaScript, no inline handlers (the server's content policy forbids them). */
'use strict';

// ---------- turn the pots ----------
// A plant by a window grows toward the light and leans. A quarter turn every week or two keeps it straight. The page #/turning
// (Care) lists the pots due for a turn; Today gets a "Turn the pots" section. A turn is a care log entry of kind 'turn'.
CARE_WORD.turn = 'Turned the pot';                      // also offered in Log other care, and shown in the care log
const tnPl = (n, one, many) => `${n} ${n === 1 ? one : many}`;
const tnRow = p => ({ code: p.code, common_name: p.name, photo: p.photo });
function tnWords(p) {
  const where = p.where ? p.where + '. ' : p.site !== 'Indoors' ? p.site + '. ' : '';
  if (p.state === 'never') return where + 'No turn logged yet. Reminders start from the first time you mark it turned.';
  const over = daysBetween(p.due_on, todayStr());
  const when = p.state === 'due' ? (over > 0 ? `${tnPl(over, 'day', 'days')} overdue` : 'Due today') : p.state === 'soon' ? 'Due tomorrow' : 'Next turn ' + relDay(p.due_on);
  return `${where}${when}. Last turned ${relDay(p.last)}${p.days > 1 ? ` (${p.days} days ago)` : ''}.`;
}
function tnBtns(p, withOff) {
  return html`<button class="btn small" type="button" data-act="turned" data-code="${p.code}" data-name="${p.name}" aria-label="${'Turned ' + p.name}">Turned</button>
    ${withOff ? html`<button class="btn small ghost" type="button" data-act="turnset" data-code="${p.code}" data-on="0" aria-label="${'No turn reminders for ' + p.name}">No reminders</button>` : ''}`;
}
function tnAllBtn(list, label) {
  return list.length > 1 ? html`<p><button class="btn small ghost" type="button" data-act="turnedall" data-codes="${list.map(p => p.code).join(',')}">${label}</button></p>` : '';
}
function tnDueBlock(T, withOff) {      // the part Today and the page share: what is due, and what has never been turned
  const due = T.plants.filter(p => p.state === 'due'), never = T.plants.filter(p => p.state === 'never');
  return html`${due.length ? html`${tnAllBtn(due, `Turned all ${due.length}`)}<ul class="jobs">${due.map(p => jobRow(tnRow(p), tnWords(p), tnBtns(p, withOff)))}</ul>`
      : html`<p class="notice ok">No pot is due for a turn today.</p>`}
    ${never.length ? html`<details class="grp tn-never"><summary><h3>Not turned yet (${never.length})</h3></summary>
      <p class="hint">These have no turn in the log yet. If you turn them all on one round, press the button to start the clock for all of them at once.</p>
      ${tnAllBtn(never, `I turned all ${never.length} today`)}
      <ul class="jobs">${never.map(p => jobRow(tnRow(p), tnWords(p), tnBtns(p, withOff)))}</ul></details>` : ''}`;
}
async function viewTurning() {
  const T = await api('GET', '/api/turning');
  const C = T.counts, later = T.plants.filter(p => p.state === 'soon' || p.state === 'ok');
  const line = [tnPl(C.due, 'pot to turn today', 'pots to turn today'), C.never ? tnPl(C.never, 'not turned yet', 'not turned yet') : '', C.soon ? `${C.soon} due tomorrow` : ''].filter(Boolean).join(', ');
  return {
    title: 'Turn the pots',
    html: html`<h1>Turn the pots</h1>
    <p class="muted">A plant by a window grows toward the light and starts to lean. Give each pot a quarter turn every week or two, always the same way round (clockwise, say), and it grows straight and even on every side.</p>
    <div class="verdict-box" role="status"><p><strong>${line.charAt(0).toUpperCase() + line.slice(1)}.</strong> ${tnPl(T.plants.length, 'pot is', 'pots are')} on the list, a turn every ${T.every} days.</p></div>
    <div class="tn-every noprint"><label class="f">Remind me to turn each pot every
      <select name="every" data-act="turnevery">${T.choices.map(n => html`<option value="${n}" ${n === T.every ? raw('selected') : ''}>${n} days${n === 14 ? ' (usual)' : ''}</option>`)}</select></label></div>
    <section class="blk" id="turn-due"><h2>Due today (${C.due})</h2>${tnDueBlock(T, true)}</section>
    <section class="blk" id="turn-later"><h2>Coming up (${later.length})</h2>
      ${later.length ? html`<ul class="jobs">${later.map(p => jobRow(tnRow(p), tnWords(p), tnBtns(p, true)))}</ul>` : html`<p class="muted">Nothing else on the list yet.</p>`}</section>
    <section class="blk" id="turn-out"><h2>Left out (${T.left_out.length})</h2>
      <p class="hint">Plants out in the open get light from all round as the sun moves, so they are left out and not listed here. So are plants under a grow light that shines down from above. Switch any plant on or off with its button.</p>
      ${T.left_out.length ? html`<ul class="jobs">${T.left_out.map(p => jobRow(tnRow(p), p.why + '.',
        html`<button class="btn small ghost" type="button" data-act="turnset" data-code="${p.code}" data-on="1" aria-label="${'Remind me to turn ' + p.name}">Remind me</button>`))}</ul>` : ''}</section>
    <p class="hint">Each turn is saved in the plant's care log as "Turned the pot", so you can see it on the plant's page and undo it there.</p>`,
  };
}
async function tnAfterChange(code) {
  if (document.getElementById('care-plant')) {          // on a plant's page: just its care part, focus back on the button
    await loadCarePlant();
    // the pressed button is now "✓ Turned today" and disabled, so focus goes to the line that says it was turned and when next
    const b = document.querySelector('#tn-plant-btn:not([disabled])') || document.querySelector('#tn-plant button:not([disabled])') || document.getElementById('tn-plant');
    if (b) { if (b.id === 'tn-plant') b.setAttribute('tabindex', '-1'); b.focus({ preventScroll: true }); }
    return;
  }
  const y = window.scrollY; await route(); window.scrollTo(0, y);
  const f = (code && document.querySelector(`.job[data-code="${code}"] button`)) || document.querySelector('#turn-due .job button, #today-turn .job button') || document.querySelector('main h1');
  if (f) f.focus({ preventScroll: true });
}
Object.assign(acts, {
  async turned(el) {
    if (!(await needName())) return;
    const code = el.dataset.code;
    await guard(async () => { const r = await api('POST', '/api/care', { plant: code, kind: 'turn' }); careUndoToast('Turned: ' + el.dataset.name + offWhen(r), r && r.ids, code); await tnAfterChange(); });
  },
  async turnedall(el) {
    const codes = el.dataset.codes.split(',').filter(Boolean); if (!codes.length) return;
    if (!(await needName())) return;
    if (!(await confirmBox(`Mark ${codes.length} pots as turned today?`, 'Each one gets a "Turned the pot" entry for today in its care log. You can remove any of them on the plant\'s page.', 'Mark as turned'))) return;
    await guard(async () => { const r = await api('POST', '/api/care', { plants: codes, kind: 'turn' }); careUndoToast(codes.length + ' pots marked as turned' + offWhen(r), r && r.ids); await tnAfterChange(); });
  },
  async turnset(el) {
    if (!(await needName())) return;
    const on = el.dataset.on === '1';
    await guard(async () => { await api('PUT', '/api/turning', { plant: el.dataset.code, on }); toast(on ? 'Turn reminders switched on' : 'Turn reminders switched off'); await tnAfterChange(); });
  },
});
Object.assign(changeActs, {
  async turnevery(el) {
    if (!(await needName())) { route(); return; }
    await guard(async () => { await api('PUT', '/api/turning', { every: +el.value }); toast(`A turn every ${el.value} days`); await tnAfterChange(); });
    const s = document.querySelector('select[data-act=turnevery]'); if (s) s.focus();
  },
});
// 1.46.0: what this module adds, said once (features.js) instead of wrapping viewToday and loadCarePlant:
//  - the page #/turning under Care, after Back outside;
//  - a "Turn the pots" block on Today (order 65: after Coming inside, before Needed from you) with a jump button;
//  - on a plant's own page (Ethan, November 6), a "Turned today" button beside "Watered today" for a pot on the list, with a line
//    saying when it is due. A plant left out (switched off, or under a light from above) says why, with Remind me. Plants out in
//    the open get nothing. It draws again whenever the care part of the page does (care: true).
addFeature({
  name: 'turning',
  care: { turn: 'Turned the pot' },
  pages: { turning: { view: viewTurning, nav: 'turning', section: 'care', label: 'Turn the pots', href: '#/turning', after: 'outside' } },
  today: {
    id: 'today-turn', order: 65,
    load: async () => { const T = await api('GET', '/api/turning'); return T.plants.length ? T : null; },
    jump: T => `Turn (${T.counts.due})`,
    html: T => html`<section class="blk" id="today-turn"><h2>Turn the pots (${T.counts.due})</h2>${tnDueBlock(T, false)}
      <p><a class="btn small ghost" href="#/turning">All pots and how often</a></p></section>`,
  },
  adds: {
    id: 'tn-plant', care: true,
    match: parts => parts[0] === 'plant' && parts[1] && parts[2] !== 'edit',
    anchor: main => { const b = main.querySelector('.quick-btns'); return b && b.parentElement; }, where: 'beforeend',
    load: async parts => {
      if (!CUR || CUR.p.code !== parts[1]) return null;
      const T = await api('GET', '/api/turning');                // offline with nothing saved: leave it out
      const code = parts[1], p = T.plants.find(x => x.code === code), out = T.left_out.find(x => x.code === code);
      return p || out ? { T, p, out, code, name: CUR.p.common_name } : null;
    },
    html: ({ T, p, out, code, name }) => {
      if (p) {
        const done = p.last === T.today;
        return html`<p class="hint" id="tn-plant">Turn the pot: ${done ? 'turned today; next turn ' + relDay(p.due_on) + '. To take it back, use Undo in the message, or Remove in the care log.' : tnWords(p)} <a href="#/turning">All pots</a></p>`;
      }
      return html`<p class="hint" id="tn-plant">Turn the pot: no reminders for this plant. ${out.why}.
        <button class="btn small ghost" type="button" data-act="turnset" data-code="${code}" data-on="1" aria-label="${'Remind me to turn ' + name}">Remind me</button></p>`;
    },
    then: (el, { T, p, code, name }) => {                        // the button goes beside Watered today, not under the line
      const oldB = document.getElementById('tn-plant-btn'); if (oldB) oldB.remove();
      if (!p) return;
      const btns = document.querySelector('.quick-btns'); if (!btns) return;
      const done = p.last === T.today, wb = btns.querySelector('[data-act=care][data-kind=water]');
      (wb || btns.firstElementChild).insertAdjacentHTML('afterend', rend(html`<button class="btn ghost${done ? ' done-today' : ''}" type="button" id="tn-plant-btn" data-act="turned" data-code="${code}" data-name="${name}"
        aria-describedby="tn-plant" ${done ? raw('disabled') : ''}>${done ? '✓ Turned today' : 'Turned today'}</button>`));
    },
  },
});
