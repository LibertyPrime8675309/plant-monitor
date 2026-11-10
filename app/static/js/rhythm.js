/* Plant record front end: how often you water (prototype, proto/water-rhythm). One of the files loaded in order by index.html; they
   share one scope. Plain JavaScript, no inline handlers (the server's content policy forbids them).

   The watering reminder guesses a gap from the plant's soil moisture range and the weather. The care log knows what really happens.
   This compares the two: the page #/rhythm (Care) lists the plants watered well before or well after their reminder, and a plant's
   own page says how often it has been watered, both with a button that makes the reminder match. Nothing new is stored: the button
   changes the plant's "Check for water every (days)" (PUT /api/rhythm), with Undo. */
'use strict';

const rhPl = (n, one, many) => `${n} ${n === 1 ? one : many}`;
const rhDays = n => rhPl(n, 'day', 'days');
const rhGap = g => { const n = Math.round(g); return rhDays(n); };
function rhSince(p) {        // "since Aug 3"
  return p.first ? 'since ' + parseYmd(p.first).toLocaleDateString([], { month: 'short', day: 'numeric' }) : '';
}
function rhWords(p, long) {
  if (p.state === 'few') {
    const need = Math.max(1, (RH.min_gaps || 3) + 1 - (p.waterings + p.rain_days));
    return p.waterings ? `Not enough waterings logged yet to see a pattern: ${rhPl(need, 'more is', 'more are')} needed.` : 'No watering logged in the last four months.';
  }
  const rain = p.rain_days ? ` (${rhPl(p.rain_days, 'day', 'days')} of rain counted as waterings)` : '';
  const gaps = long && p.gaps.length ? ` Recent gaps: ${p.gaps.join(', ')} days.` : '';
  const skip = long && p.left_out ? ` ${rhPl(p.left_out, 'gap', 'gaps')} over ${RH.max_gap} days left out, as times nothing was logged.` : '';
  const vs = p.state === 'often' ? `That is sooner than the reminder, which says every ${rhDays(p.every)}.`
    : p.state === 'seldom' ? `That is later than the reminder, which says every ${rhDays(p.every)}.`
    : `That matches the reminder, which says every ${rhDays(p.every)}.`;
  const moist = p.checks ? ` Found still moist ${rhPl(p.checks, 'time', 'times')}.` : '';
  return `Watered about every ${rhGap(p.gap)} ${rhSince(p)}${rain}. ${vs}${moist}${gaps}${skip}`;
}
function rhBtn(p) {
  if (!p.suggest || p.state === 'matches') return '';
  return html`<button class="btn small" type="button" data-act="rhset" data-code="${p.code}" data-name="${p.name}" data-every="${p.suggest.every}"
    data-old="${p.own_setting == null ? '' : p.own_setting}" aria-label="${'Remind me every ' + p.suggest.every + ' days to check ' + p.name}">Remind me every ${rhDays(p.suggest.every)}</button>`;
}
const rhRow = p => jobRow({ code: p.code, common_name: p.name, photo: p.photo }, rhWords(p, false), rhBtn(p));
let RH = { min_gaps: 3, max_gap: 45 };
async function viewRhythm() {
  RH = await api('GET', '/api/rhythm');
  const C = RH.counts, by = s => RH.plants.filter(p => p.state === s);
  const judged = C.often + C.seldom + C.matches;
  return {
    title: 'How often you water',
    html: html`<h1>How often you water</h1>
    <p class="muted">The watering reminder guesses how often to check each plant from its soil moisture range and the weather. Your care log shows how often you really water. Where the two are far apart, the reminder can be changed to match what works for you.</p>
    <div class="verdict-box" role="status"><p><strong>${judged ? `${rhPl(C.often, 'plant is', 'plants are')} watered sooner than the reminder says, ${C.seldom} later, and ${C.matches} about right.`
      : 'Not enough waterings logged yet to compare.'}</strong>
      ${C.few ? ` ${rhPl(C.few, 'plant has', 'plants have')} too few waterings logged to tell.` : ''}</p>
      <p class="hint">From the last ${RH.window} days of the care log. "About every" is the middle gap between waterings, so one long or short gap does not move it. Rain of ${rainF(RH.rain_counts_in)} or more counts as a watering for plants whose Location is Outdoors.</p></div>
    <section class="blk" id="rh-often"><h2>Watered sooner than the reminder (${C.often})</h2>
      <p class="hint">The pot may dry faster than the app thinks (a small pot, a sunny window, a heater nearby), so a shorter reminder would suit it. Or it is watered before it needs it: push a finger into the mix first, and if it is still damp, press "Checked: still moist" instead.</p>
      ${C.often ? html`<ul class="jobs">${by('often').map(rhRow)}</ul>` : html`<p class="muted">None.</p>`}</section>
    <section class="blk" id="rh-seldom"><h2>Watered later than the reminder (${C.seldom})</h2>
      <p class="hint">If the mix was still moist when the reminder came ("Found still moist"), a longer reminder suits it. If it was dry and the watering was simply late, keep the reminder as it is.</p>
      ${C.seldom ? html`<ul class="jobs">${by('seldom').map(rhRow)}</ul>` : html`<p class="muted">None.</p>`}</section>
    <details class="grp" id="rh-match"><summary><h2>About right (${C.matches})</h2></summary>
      ${C.matches ? html`<ul class="jobs">${by('matches').map(rhRow)}</ul>` : html`<p class="muted">None yet.</p>`}</details>
    <details class="grp" id="rh-few"><summary><h2>Not enough logged yet (${C.few})</h2></summary>
      <p class="hint">A pattern needs at least ${RH.min_gaps + 1} waterings in the last ${RH.window} days. Press "Watered today" on Today or on the plant's page each time.</p>
      ${C.few ? html`<ul class="jobs">${by('few').map(rhRow)}</ul>` : html`<p class="muted">None.</p>`}</details>
    <p class="hint">"Remind me every" changes the plant's "Check for water every (days)" so the reminder comes round at about that gap in weather like today's, and the change is in the plant's history. To go back to the app's own guess, empty that box in Edit this page.</p>`,
  };
}
async function rhAfter(code) {
  if (document.getElementById('care-plant')) {
    await loadCarePlant();
    const f = document.getElementById('rh-plant'); if (f) { f.setAttribute('tabindex', '-1'); f.focus({ preventScroll: true }); }
    return;
  }
  const y = window.scrollY; await route(); window.scrollTo(0, y);
  const f = (code && document.querySelector(`.job[data-code="${code}"] a`)) || document.querySelector('main h1');
  if (f) f.focus({ preventScroll: true });
}
Object.assign(acts, {
  async rhset(el) {
    if (!(await needName())) return;
    const code = el.dataset.code, name = el.dataset.name, n = +el.dataset.every, old = el.dataset.old === '' ? null : +el.dataset.old;
    await guard(async () => {
      const r = await api('PUT', '/api/rhythm', { plant: code, every: n });
      const p = r.plants[0];
      careUndoToast(`${name}: watering reminder now every ${rhDays(p ? p.every : n)}`, async () => {
        await guard(async () => { await api('PUT', '/api/rhythm', { plant: code, setting: old }); toast('Undone. The watering reminder is back as it was.'); await rhAfter(code); });
      }, code);
      await rhAfter(code);
    });
  },
  async rhclear(el) {
    if (!(await needName())) return;
    const code = el.dataset.code, old = +el.dataset.old;
    await guard(async () => {
      await api('PUT', '/api/rhythm', { plant: code, every: null });
      careUndoToast('The app works out the watering gap again', async () => {
        await guard(async () => { await api('PUT', '/api/rhythm', { plant: code, setting: old }); toast('Undone.'); await rhAfter(code); });
      }, code);
      await rhAfter(code);
    });
  },
});
// What this module adds (features.js):
//  - the page #/rhythm under Care, after Turn the pots;
//  - on a plant's own page, a line inside the Watering box saying how often it has really been watered, with the button.
//    It draws again whenever the care part does (care: true), so pressing "Watered today" updates it.
addFeature({
  name: 'rhythm',
  pages: { rhythm: { view: viewRhythm, nav: 'rhythm', section: 'care', label: 'How often you water', href: '#/rhythm', after: 'turning' } },
  adds: {
    id: 'rh-plant', care: true,
    match: parts => parts[0] === 'plant' && parts[1] && parts[2] !== 'edit',
    anchor: '#care-plant .verdict-box', where: 'beforeend',
    load: async parts => {
      if (!CUR || CUR.p.code !== parts[1]) return null;
      const R = await api('GET', '/api/rhythm?plant=' + enc(parts[1]));
      RH = Object.assign(RH, { min_gaps: R.min_gaps, max_gap: R.max_gap });
      const p = R.plants[0];
      return p && (p.waterings || p.rain_days) ? p : null;
    },
    html: p => html`<div id="rh-plant" class="rh-plant"><h4>How often you water</h4><p>${rhWords(p, true)}</p>
      ${rhBtn(p) || p.own_setting != null ? html`<p class="rh-acts">${rhBtn(p)}
        ${p.own_setting != null ? html`<button class="btn small ghost" type="button" data-act="rhclear" data-code="${p.code}" data-old="${p.own_setting}">Let the app work out the gap</button>` : ''}
        <a class="btn small ghost" href="#/rhythm">All plants</a></p>` : html`<p><a href="#/rhythm">All plants</a></p>`}</div>`,
  },
});
