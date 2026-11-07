/* Plant record front end: the repotting plan (prototype, proto/repotting). One of the files loaded in order by index.html; they
   share one scope. Plain JavaScript, no inline handlers (the server's content policy forbids them). */
'use strict';

// ---------- repotting plan ----------
// Which plants are due for a bigger pot or fresh soil this spring, from the "Repotted" entries in the care log and how fast each
// plant grows. The page #/repotting (in the Today row) lists them; a plant's own page gets a line under its care buttons; Today gets a section
// in repotting season (March to May) and the four weeks before it. A repot is a care log entry of kind 'repot'.
// It goes in the Today row of the top bar, beside the Health walk-through: one more page in the Care row makes that row wrap to a
// second line on a laptop, and the taller bar stops the Grow lights summary staying at the top (lights check)
if (!SECTIONS[0][2].some(x => x[0] === 'repotting')) SECTIONS[0][2].push(['repotting', 'Repotting', '#/repotting']);
const RP_MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const rpPl = (n, one, many) => `${n} ${n === 1 ? one : many}`;
const rpRow = p => ({ code: p.code, common_name: p.name, photo: p.photo });
const rpDate = s => { const d = parseYmd(s); return `${RP_MONTHS[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`; };
function rpAgo(s) {                       // "20 months ago", "2 years ago"
  const a = parseYmd(s), b = parseYmd(todayStr());
  const m = (b.getFullYear() - a.getFullYear()) * 12 + b.getMonth() - a.getMonth() - (b.getDate() < a.getDate() ? 1 : 0);
  if (m < 1) return daysBetween(s, todayStr()) < 1 ? 'today' : rpPl(daysBetween(s, todayStr()), 'day ago', 'days ago');
  if (m < 24) return rpPl(m, 'month ago', 'months ago');
  return rpPl(Math.floor(m / 12), 'year ago', 'years ago');
}
function rpWhen(p, R) {
  if (p.state === 'never') return 'No repotting recorded yet.';
  const when = p.state === 'due' ? (R.season.now ? 'Due now, this spring.' : `Due in spring ${R.season.year}.`) : `Next due in spring ${p.spring}.`;
  return `${when} Last repotted ${rpDate(p.last)} (${rpAgo(p.last)}).`;
}
const rpWords = (p, R) => `${p.where ? p.where + '. ' : ''}${rpWhen(p, R)} ${p.why}.`;
function rpBtns(p) {
  return html`${p.state === 'never' ? '' : html`<button class="btn small" type="button" data-act="repotted" data-code="${p.code}" data-name="${p.name}" aria-label="${'Repotted ' + p.name + ' today'}">Repotted today</button>`}
    <button class="btn small ghost" type="button" data-act="repotset" data-code="${p.code}" aria-label="${(p.state === 'never' ? 'When was it repotted: ' : 'Change repotting for ') + p.name}">${p.state === 'never' ? 'When was it repotted?' : 'Change'}</button>`;
}
// The year choices for "When was it last repotted?". A year is saved as April 15 of that year (or today, if that is still to come),
// with a note saying the date is a guess, so the plan can count from it.
function rpYears() {
  const y = +todayStr().slice(0, 4);
  return [[y, `This year (${y})`], [y - 1, `Last year (${y - 1})`], [y - 2, `${y - 2}`], [y - 3, `${y - 3} or earlier`]];
}
function rpGuess(y) {
  const t = todayStr(), d = `${y}-04-15`;
  return { done_on: d > t ? t : d, note: `Date estimated: some time in ${y}${y === +t.slice(0, 4) - 3 ? ' or earlier' : ''}` };
}
function rpDueBlock(R, withNever) {     // the part Today and the page share
  const due = R.plants.filter(p => p.state === 'due'), never = R.plants.filter(p => p.state === 'never');
  return html`${due.length ? html`<ul class="jobs">${due.map(p => jobRow(rpRow(p), rpWords(p, R), rpBtns(p)))}</ul>`
      : html`<p class="notice ok">No plant with a recorded repotting is due ${R.season.now ? 'this spring' : `by spring ${R.season.year}`}.</p>`}
    ${withNever && never.length ? html`<p class="hint">${rpPl(never.length, 'plant has', 'plants have')} no repotting recorded yet. <a href="#/repotting?sec=rp-never">Say when</a></p>` : ''}`;
}
async function viewRepotting() {
  const R = await api('GET', '/api/repotting');
  const C = R.counts, never = R.plants.filter(p => p.state === 'never'), later = R.plants.filter(p => p.state === 'later');
  const line = [rpPl(C.due, 'plant is', 'plants are') + (R.season.now ? ' due for repotting this spring' : ` due for repotting in spring ${R.season.year}`),
    C.never ? rpPl(C.never, 'has', 'have') + ' no repotting recorded yet' : ''].filter(Boolean).join('; ');
  return {
    title: 'Repotting',
    after: () => navMark('repotting'),
    html: html`<h1>Repotting</h1>
    <p class="muted">A plant in a pot slowly fills it with roots and wears out its soil. Most want a pot one size bigger, or fresh soil, every one to three years: fast growers more often, slow growers less. This plan counts from the last time each plant was repotted.</p>
    <div class="verdict-box rp-sum" role="status"><p><strong>${line.charAt(0).toUpperCase() + line.slice(1)}.</strong></p><p>${R.season.words}</p></div>
    <section class="blk" id="rp-due"><h2>${R.season.now ? 'Due this spring' : `Due in spring ${R.season.year}`} (${C.due})</h2>${rpDueBlock(R, false)}</section>
    <section class="blk" id="rp-never"><h2>Not recorded yet (${never.length})</h2>
      ${never.length ? html`<p class="hint">Say roughly when each of these was last repotted, and the plan works out when it is next due. A guess of the year is enough. If you do not know, leave it: it stays here.</p>
      ${never.length > 1 ? html`<form class="rp-bulk noprint" data-form="repotall" data-codes="${never.map(p => p.code).join(',')}">
        <label class="f">Last repotted, for all ${never.length}<select name="year"><option value="">Choose a year</option>${rpYears().map(([y, l]) => html`<option value="${y}">${l}</option>`)}</select></label>
        <button class="btn small ghost" type="submit">Save for all ${never.length}</button>
        <p class="hint">Saves the same year for every plant in this list. You can change any of them afterwards with its own button.</p></form>` : ''}
      <ul class="jobs">${never.map(p => jobRow(rpRow(p), rpWords(p, R), rpBtns(p)))}</ul>` : html`<p class="muted">Every plant on the plan has a repotting recorded.</p>`}</section>
    <section class="blk" id="rp-later"><h2>Later (${later.length})</h2>
      ${later.length ? html`<ul class="jobs">${later.map(p => jobRow(rpRow(p), rpWords(p, R), rpBtns(p)))}</ul>` : html`<p class="muted">Nothing else on the plan yet.</p>`}</section>
    <section class="blk" id="rp-signs"><h2>Signs a plant cannot wait for spring</h2>
      <ul class="rp-list"><li>Roots come out of the drainage holes, or circle round on top of the soil.</li>
        <li>Water runs straight through, or the soil is dry again a day or two after watering.</li>
        <li>The plant lifts out of its pot in one solid block of roots, or the pot has cracked or bulged.</li>
        <li>It is so top-heavy that it tips over.</li>
        <li>The soil has sunk, turned hard, or smells sour.</li></ul>
      <h3>When you repot</h3>
      <ul class="rp-list"><li>Go up only one size: a pot 1 to 2 inches wider, with a drainage hole.</li>
        <li>Use fresh potting mix that suits the plant (see its Water and soil section), and water it in.</li>
        <li>Keep it out of strong sun for about a week, and do not feed it for 4 to 6 weeks.</li>
        <li>A plant in Poor or Critical health is better left until it recovers, unless the pot or soil is the problem.</li></ul></section>
    <section class="blk" id="rp-out"><h2>Left out (${R.left_out.length})</h2>
      ${R.left_out.length ? html`<ul class="jobs">${R.left_out.map(p => jobRow(rpRow(p), p.why + '.', html`<button class="btn small ghost" type="button" data-act="repotset" data-code="${p.code}" aria-label="${'Change repotting for ' + p.name}">Change</button>`))}</ul>`
        : html`<p class="muted">No plant is left out.</p>`}</section>
    <p class="hint">Each repotting is saved in the plant's care log as "Repotted", so you can see it on the plant's page and remove it there.</p>`,
  };
}
async function rpAfterChange(code) {
  if (document.getElementById('care-plant')) {
    await loadCarePlant();
    const b = document.querySelector('#rp-plant button') || document.getElementById('rp-plant');
    if (b) { if (b.id === 'rp-plant') b.setAttribute('tabindex', '-1'); b.focus({ preventScroll: true }); }
    return;
  }
  const y = window.scrollY; ROUTE_FRESH = true; await route(); window.scrollTo(0, y);
  const f = (code && document.querySelector(`.job[data-code="${code}"] button`)) || document.querySelector('#rp-due .job button, #today-repot .job button') || document.querySelector('main h1');
  if (f) f.focus({ preventScroll: true });
}
// One window for a plant: when it was last repotted (a year, or an exact date) and how often it is due
async function rpDialog(code) {
  if (!(await needName())) return;
  const R = await api('GET', '/api/repotting?plant=' + enc(code));
  const p = R.plants[0] || R.left_out[0]; if (!p) return;
  const usual = p.auto ? `Usual for this plant: every ${p.auto} months` : 'Usual for this plant: no reminders';
  const cur = p.choice == null ? 'auto' : String(p.choice);
  const r = await modal(html`<form method="dialog" class="rp-dlg"><h2>Repotting: ${p.name}</h2>
    <fieldset><legend>${p.last ? `Last repotted ${rpDate(p.last)}. Add a repotting?` : 'When was it last repotted?'}</legend>
      <label class="chk"><input type="radio" name="when" value="" checked> ${p.last ? 'No, leave it' : 'Not sure: leave it for now'}</label>
      <label class="chk"><input type="radio" name="when" value="today"> Today</label>
      ${rpYears().map(([y, l]) => html`<label class="chk"><input type="radio" name="when" value="${y}"> ${l}</label>`)}
      <label class="chk"><input type="radio" name="when" value="day"> On this date:</label>
      <label class="f">The date, for "On this date"<input type="date" name="day" max="${todayStr()}"></label></fieldset>
    <label class="f">Repot it every<select name="every">
      <option value="auto" ${cur === 'auto' ? raw('selected') : ''}>${usual}</option>
      ${R.choices.map(n => html`<option value="${n}" ${cur === String(n) ? raw('selected') : ''}>${n} months${n === 12 ? ' (every year)' : n === 24 ? ' (every 2 years)' : n === 36 ? ' (every 3 years)' : ''}</option>`)}
      <option value="off" ${cur === 'off' ? raw('selected') : ''}>No reminders for this plant</option></select></label>
    <p class="hint">${p.auto ? `The usual comes from its growth rate: ${p.growth || 'not filled in'}.` : p.why + '.'}</p>
    <div class="row"><button class="btn" value="ok">Save</button><button class="btn ghost" value="cancel">Cancel</button></div></form>`);
  if (r !== 'ok') return;
  const f = dlg.querySelector('form'), every = f.elements.every.value;
  let w = f.elements.when.value;
  if (!w && f.elements.day.value) w = 'day';          // a date typed in without choosing "On this date" first
  let body = null;
  if (w === 'today') body = {};
  else if (w === 'day') { if (!f.elements.day.value) { toast('Choose the date, or pick a year instead.', true); return; } body = { done_on: f.elements.day.value }; }
  else if (w) body = rpGuess(+w);
  await guard(async () => {
    const said = [];
    let x = null;
    if (body) { x = await api('POST', '/api/care', Object.assign({ plant: code, kind: 'repot' }, body)); said.push('repotting saved'); }
    if (every !== cur) { await api('PUT', '/api/repotting', { plant: code, every: every === 'auto' || every === 'off' ? every : +every }); said.push(every === 'off' ? 'no reminders' : every === 'auto' ? 'usual timing' : `every ${every} months`); }
    if (!said.length) return;
    const msg = p.name + ': ' + said.join(', ') + offWhen(x);
    if (x && x.ids) careUndoToast(msg, x.ids, code); else toast(msg);
    await rpAfterChange(code);
  });
}
Object.assign(acts, {
  async repotted(el) {
    if (!(await needName())) return;
    const code = el.dataset.code;
    await guard(async () => { const r = await api('POST', '/api/care', { plant: code, kind: 'repot' }); careUndoToast('Repotted: ' + el.dataset.name + offWhen(r), r && r.ids, code); await rpAfterChange(code); });
  },
  async repotset(el) { await rpDialog(el.dataset.code); },
});
// "Save for all" is a form (formActs, events.js), so Enter works and moving through the list with the arrow keys saves nothing
Object.assign(formActs, {
  async repotall(f) {
    const y = f.elements.year.value, codes = f.dataset.codes.split(',').filter(Boolean);
    if (!y) { toast('Choose a year first.', true); f.elements.year.focus(); return; }
    if (!(await needName())) return;
    const g = rpGuess(+y), label = rpYears().find(([n]) => String(n) === y)[1];
    if (!(await confirmBox(`Save "${label}" for ${codes.length} plants?`, `Each one gets a "Repotted" entry dated ${rpDate(g.done_on)} in its care log, marked as an estimate. You can remove any of them on the plant's page.`, 'Save for all'))) return;
    await guard(async () => { const r = await api('POST', '/api/care', Object.assign({ plants: codes, kind: 'repot' }, g)); careUndoToast(`Last repotted ${label}: saved for ${codes.length} plants` + offWhen(r), r && r.ids); await rpAfterChange(); });
  },
});

// Today: a "Repot this spring" section in repotting season and the four weeks before it. viewToday (care.js) is wrapped, not edited.
{
  const todayBase = viewToday;
  viewToday = async function () {
    const [V, R] = await Promise.all([todayBase(), api('GET', '/api/repotting').catch(() => null)]);
    if (!R || !R.counts.due) return V;
    const soon = !R.season.now && daysBetween(todayStr(), R.season.from) <= 28;
    if (!R.season.now && !soon) return V;
    const after = V.after, n = R.counts.due;
    V.after = () => {
      if (after) after();
      const needs = document.getElementById('today-needs'); if (!needs || document.getElementById('today-repot')) return;
      needs.insertAdjacentHTML('beforebegin', rend(html`<section class="blk" id="today-repot"><h2>${R.season.now ? 'Repot this spring' : 'Repotting season soon'} (${n})</h2>
        ${soon ? html`<p>Repotting season starts ${rpDate(R.season.from)}. Get pots one size bigger and fresh potting mix ready for these.</p>` : ''}
        ${rpDueBlock(R, true)}<p><a class="btn small ghost" href="#/repotting">The whole repotting plan</a></p></section>`));
      const jumps = document.querySelector('.td-jumps'), last = jumps && jumps.lastElementChild;
      if (last) last.insertAdjacentHTML('beforebegin', rend(html`<a class="btn small ghost" href="#today-repot" data-act="jumpsec" data-sec="today-repot">Repot (${n})</a>`));
    };
    return V;
  };
}

// On a plant's own page: one line under the care buttons saying when it was last repotted and when it is next due, with Change.
// loadCarePlant (care.js) is wrapped rather than edited, so this prototype stays in its own file.
{
  const careBase = loadCarePlant;
  loadCarePlant = async function () {
    // asked for alongside the care part, not after it, so redrawing a plant's care (a tick on the checklist) takes no longer
    const code0 = CUR && CUR.p.code;
    const ask = code0 ? api('GET', '/api/repotting?plant=' + enc(code0)).catch(() => null) : null;
    await careBase();
    if (!CUR || !ask) return;
    const code = CUR.p.code, name = CUR.p.common_name;
    const R = await ask; if (!R) return;
    if (!CUR || CUR.p.code !== code || code !== code0) return;
    const btns = document.querySelector('.quick-btns'); if (!btns) return;
    const old = document.getElementById('rp-plant'); if (old) old.remove();
    const p = R.plants[0], out = R.left_out[0];
    let words = p ? (p.state === 'never' ? 'none recorded yet.' : rpWhen(p, R)) : out ? `no reminders. ${out.why}.` : '';
    words = words.charAt(0).toLowerCase() + words.slice(1);
    if (!words) return;
    btns.parentElement.insertAdjacentHTML('beforeend', rend(html`<p class="hint rp-plant" id="rp-plant">Repotting: ${words}
      <button class="btn small ghost" type="button" data-act="repotset" data-code="${code}" aria-label="${(p && p.state === 'never' ? 'When was it repotted: ' : 'Change repotting for ') + name}">${p && p.state === 'never' ? 'When was it repotted?' : 'Change'}</button> <a href="#/repotting">All plants</a></p>`));
  };
}
