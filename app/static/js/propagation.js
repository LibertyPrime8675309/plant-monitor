/* Plant record front end: propagation (prototype, proto/propagation). One of the files loaded in order by index.html; they share one scope.
   Plain JavaScript, no inline handlers (the server's content policy forbids them). Every name here starts with prp. */
'use strict';

// ---------- propagation: cuttings, layers, grafts, divisions, offsets and seeds ----------
// A propagation is one attempt (PR-001...): the way, the plant it came from, when it started, what it sits in, how many pieces, and how
// it is going. It is not a plant until a piece is potted up, which makes a plant with its own P-code linked to its parent (the family
// tree). Seed lots are propagations of the way "seed" with an ordered list of treatment steps. Pages: #/propagating (the list and
// what the attempts show), #/propagating/new, #/propagating/<id>, #/propagating/family.
const prpPl = (n, one, many) => `${n} ${n === 1 ? one : many}`;
const prpDate = d => d ? parseYmd(d).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' }) : '';
const PRP_SITES = ['Indoors', 'Covered porch', 'Outdoors', 'Garage or shed'];
const PRP_STEP_ORDER = ['scarify', 'soak', 'warm', 'cold', 'light', 'dry'];
const prpPieces = p => p.method === 'seed' ? prpPl(p.count, 'seed', 'seeds') : prpPl(p.count, 'piece', 'pieces');
const prpInWater = p => /water/i.test(p.medium || '');

function prpWords(p) {      // one line that says what it is and how it is going
  const bits = [p.method_label + (p.parent_code ? ` from ${p.parent_name || p.parent_code}` : ''), prpPieces(p), `started ${relDay(p.started_on)}`];
  if (p.sprouted) bits.push(`${p.sprouted} sprouted`);
  if (p.lost) bits.push(`${p.lost} lost`);
  if (p.children.length) bits.push(prpPl(p.children.length, 'plant made', 'plants made'));
  return bits.join(', ') + '.';
}
function prpNeedBtns(p, n) {      // the button for one thing that is due
  const id = p.id;
  if (n.kind === 'stage_end') return html`<button class="btn small" type="button" data-act="prpstage" data-do="done" data-sid="${n.stage}" data-id="${id}" aria-label="${'Step finished for ' + p.title}">Step finished</button>`;
  if (n.kind === 'stage_start') return html`<button class="btn small" type="button" data-act="prpstage" data-do="start" data-sid="${n.stage}" data-id="${id}" aria-label="${'Started the next step for ' + p.title}">Started it today</button>`;
  return html`${prpInWater(p) ? html`<button class="btn small" type="button" data-act="prpevent" data-kind="water" data-id="${id}" aria-label="${'Changed the water for ' + p.title}">Changed the water</button>` : ''}
    <button class="btn small ghost" type="button" data-act="prpevent" data-kind="check" data-id="${id}" aria-label="${'Looked at ' + p.title + ', no change'}">Looked, no change</button>`;
}
function prpRow(p, withBtns) {
  const dueNeeds = p.needs.filter(n => n.due);
  return html`<li class="job prp-job" data-prop="${p.id}"><span class="job-nophoto" aria-hidden="true"></span>
    <div class="job-txt"><a class="nm" href="#/propagating/${p.id}">${p.title}</a> <span class="muted">${p.code}</span>
      <div>${prpWords(p)}</div>
      ${withBtns ? dueNeeds.map(n => html`<div class="prp-need">${n.words}.</div>`) : html`<div class="muted">${p.status === 'active' ? p.needs.filter(n => n.kind === 'check').map(n => 'Next look ' + relDay(n.on)) : p.status_word}</div>`}</div>
    <div class="job-acts">${withBtns ? dueNeeds.map(n => prpNeedBtns(p, n)) : ''}</div></li>`;
}
function prpBlock(P) {          // Today and the list page share this: what is due
  const due = P.items.filter(p => P.due.includes(p.id));
  return due.length ? html`<ul class="jobs">${due.map(p => prpRow(p, true))}</ul>` : html`<p class="notice ok">Nothing to look at today.</p>`;
}
async function prpAfter(id) {
  const y = window.scrollY; await route(); window.scrollTo(0, y);
  const f = (id && document.querySelector(`[data-prop="${id}"] button`)) || document.querySelector('.prp-job button, #prp-do button') || document.querySelector('main h1');
  if (f) { if (f.tagName === 'H1') f.setAttribute('tabindex', '-1'); f.focus({ preventScroll: true }); }
}

// ---------- the list ----------
async function prpResults() {
  const R = await api('GET', '/api/propagations/results');
  const rate = w => w.tried ? `${w.made} of ${w.tried} (${w.rate}%)` : 'None finished yet';
  const first = w => w.first_days == null ? 'Not enough yet' : `${prpPl(w.first_days, 'day', 'days')} (from ${prpPl(w.first_n, 'attempt', 'attempts')})`;
  const ways = Object.values(R.ways);
  return html`<section class="blk" id="prp-results"><h2>What your attempts show</h2>
    <p class="hint">Counted from finished attempts only: pieces tried, and how many became plants. A first sign is roots, sprouts or a holding graft, and the figure is the middle one of your attempts. Ones still going never change a rate.</p>
    ${ways.length ? html`<div class="tbl-wrap"><table class="tbl prp-tbl"><caption class="sr">Results for each way</caption><thead><tr><th scope="col">Way</th><th scope="col">Became plants</th><th scope="col">Days to a first sign</th><th scope="col">Going now</th></tr></thead>
      <tbody>${ways.map(w => html`<tr><th scope="row">${w.label}</th><td>${rate(w)}</td><td>${first(w)}</td><td>${w.going}</td></tr>`)}</tbody></table></div>` : html`<p class="muted">Nothing yet. Start one and the results build up as you finish them.</p>`}
    ${R.species.length ? html`<h3>By plant</h3><div class="tbl-wrap"><table class="tbl prp-tbl"><caption class="sr">Results for each species</caption><thead><tr><th scope="col">Plant</th><th scope="col">Ways tried</th><th scope="col">Became plants</th><th scope="col">Days to a first sign</th></tr></thead>
      <tbody>${R.species.map(s => html`<tr><th scope="row">${s.species}</th><td>${s.ways.join(', ')}</td><td>${rate(s)}</td><td>${first(s)}</td></tr>`)}</tbody></table></div>` : ''}</section>`;
}
async function viewPropagating(parts, qs) {
  if (parts[1] === 'new') return prpViewNew(qs);
  if (parts[1] === 'family') return prpViewFamily();
  if (parts[1] && /^\d+$/.test(parts[1])) return prpViewOne(+parts[1]);
  const P = await api('GET', '/api/propagations'), can = canChange();
  const going = P.items.filter(p => p.status === 'active' || p.status === 'ready'), done = P.items.filter(p => !(p.status === 'active' || p.status === 'ready'));
  return {
    title: 'Propagation',
    html: html`<h1>Propagation</h1>
    <p class="muted">Cuttings, layers, grafts, divisions, offsets and seeds, from the first cut to a new plant. <a href="#/guide">How each way is done</a> is in the guide.</p>
    <p class="row noprint">${can ? html`<a class="btn" href="#/propagating/new">Start one</a>` : ''}<a class="btn ghost" href="#/propagating/family">Family tree</a></p>
    <div class="verdict-box" role="status"><p><strong>${prpPl(P.counts.active, 'attempt is', 'attempts are')} going.</strong> ${P.counts.due ? `${P.counts.due} need${P.counts.due === 1 ? 's' : ''} a look today.` : 'None needs a look today.'}${P.counts.finished ? ` ${P.counts.finished} finished.` : ''}</p></div>
    <section class="blk" id="prp-do"><h2>To do today (${P.counts.due})</h2>${prpBlock(P)}</section>
    <section class="blk" id="prp-going"><h2>Going (${going.length})</h2>
      ${going.length ? html`<ul class="jobs">${going.map(p => prpRow(p, false))}</ul>` : html`<p class="muted">Nothing going. ${can ? 'Press Start one, or start a cutting from a plant\'s own page.' : ''}</p>`}</section>
    <details class="grp" id="prp-finished" ${done.length && !going.length ? raw('open') : ''}><summary><h2>Finished (${done.length})</h2></summary>
      ${done.length ? html`<ul class="jobs">${done.map(p => prpRow(p, false))}</ul>` : html`<p class="muted">Nothing finished yet.</p>`}</details>
    ${await prpResults()}`,
  };
}

// ---------- start one ----------
async function prpViewNew(qs) {
  const [P, plants] = await Promise.all([api('GET', '/api/propagations'), api('GET', '/api/plants')]);
  const parent = qs.get('parent') || '', method = qs.get('method') || 'stem', today = todayStr();
  const opt = (v, t, sel) => html`<option value="${v}" ${sel ? raw('selected') : ''}>${t}</option>`;
  return {
    title: 'Start a propagation',
    html: html`<h1>Start a propagation</h1>
    <p class="muted">Write down what you did while you remember it. Only the way and how many are needed; the rest helps you learn what works.</p>
    <form data-form="prpnew" class="prp-form" novalidate>
      <div class="field-grid">
        <label class="f">Way<select name="method">${Object.entries(P.methods).map(([k, m]) => opt(k, m.label, k === method))}</select></label>
        <label class="f">Taken from<select name="parent_code">${opt('', 'No plant of mine (seed from outside, or a gift)', !parent)}${plants.map(p => opt(p.code, `${p.code} ${p.common_name}`, p.code === parent))}</select></label>
        <label class="f">Name it (or leave to be named for you)<input type="text" name="title" maxlength="120" autocomplete="off"></label>
        <label class="f">Species, if not from a plant above<input type="text" name="species" maxlength="120" autocomplete="off"></label>
        <label class="f">How many pieces or seeds<input type="number" name="count" min="1" max="5000" step="1" value="1" inputmode="numeric"></label>
        <label class="f">Started on<input type="date" name="started_on" value="${today}" max="${today}"></label>
        <label class="f">What it sits in<input type="text" name="medium" maxlength="120" placeholder="Water, perlite, sphagnum, bark mix" autocomplete="off"></label>
        <label class="f">Setup<input type="text" name="setup" maxlength="300" placeholder="Dome, heat mat, jar, bag" autocomplete="off"></label>
        <label class="f">Rooting hormone<input type="text" name="hormone" maxlength="120" autocomplete="off"></label>
        <label class="f">Where it is<input type="text" name="place" maxlength="120" placeholder="Shelf, window, fridge" autocomplete="off"></label>
        <label class="f">Look at it every (days, or leave empty for the usual)<input type="number" name="check_every" min="1" max="120" step="1" inputmode="numeric"></label>
        <label class="f">Seeds: collected on<input type="date" name="collected_on" max="${today}"></label>
        <label class="f">Seeds: collected where<input type="text" name="collected_at" maxlength="300" autocomplete="off"></label>
      </div>
      <label class="f">Notes<textarea name="notes" rows="3" maxlength="2000"></textarea></label>
      <fieldset class="prp-steps"><legend>Treatment steps, for seeds that need them</legend>
        <p class="hint">Tick the steps in the order they are done. The days and temperatures are only starting points: change them to suit the plant. Each step starts when you press Start on its page, and Today tells you when it ends.</p>
        ${PRP_STEP_ORDER.map(k => html`<div class="prp-step-row"><label class="chk"><input type="checkbox" name="s_${k}"> ${P.stage_kinds[k]}</label>
          <label class="f">Days<input type="number" name="d_${k}" min="0" max="730" value="${P.stage_preset[k].days}" inputmode="numeric"></label>
          <label class="f">Lowest °F<input type="number" name="l_${k}" min="-20" max="140" value="${P.stage_preset[k].low ?? ''}" inputmode="numeric"></label>
          <label class="f">Highest °F<input type="number" name="h_${k}" min="-20" max="140" value="${P.stage_preset[k].high ?? ''}" inputmode="numeric"></label></div>`)}
      </fieldset>
      <p class="row"><button class="btn" type="submit">Start it</button> <a class="btn ghost" href="#/propagating">Cancel</a></p>
    </form>`,
  };
}

// ---------- one attempt ----------
function prpStageRow(s, can, id) {
  const temp = s.temp_low != null || s.temp_high != null ? `, ${s.temp_low ?? '?'} to ${s.temp_high ?? '?'}°F` : '';
  const state = s.state === 'done' ? `Finished ${prpDate(s.ended_on)}` : s.state === 'running' ? `Started ${prpDate(s.started_on)}; ends ${prpDate(s.ends_on)}` + (s.days_left < 0 ? ` (${prpPl(-s.days_left, 'day', 'days')} over)` : s.days_left === 0 ? ' (today)' : ` (${prpPl(s.days_left, 'day', 'days left')})`) : 'Not started';
  const b = (act, label, extra) => html`<button class="btn small ${extra || 'ghost'}" type="button" data-act="prpstage" data-do="${act}" data-sid="${s.id}" data-id="${id}" aria-label="${label + ': ' + s.label}">${label}</button>`;
  return html`<li class="prp-stage" data-sid="${s.id}"><strong>${s.label}</strong>, ${prpPl(s.days, 'day', 'days')}${temp}. <span class="${s.state === 'running' ? 'prp-run' : 'muted'}">${state}.</span>
    ${can ? html`<span class="noprint">${s.state === 'waiting' ? b('start', 'Start', '') : s.state === 'running' ? html`${b('done', 'Finish')} ${b('undo', 'Take back the start')}` : b('undo', 'Take back the finish')}
      ${s.state !== 'done' ? b('remove', 'Remove') : ''}</span>` : ''}</li>`;
}
async function prpViewOne(id) {
  const c = await api('GET', '/api/propagations/' + id), can = canChange(), P = await api('GET', '/api/propagations');
  const open = c.status === 'active' || c.status === 'ready';
  const todayD = todayStr();
  const parentName = c.parent_code ? html`<a href="#/plant/${enc(c.parent_code)}">${c.parent_name || c.parent_code}</a> <span class="muted">${c.parent_code}</span>` : 'no plant of mine';
  const lostForm = html`<form data-form="prpcount" class="prp-count noprint" data-id="${id}"><label class="f">How many were lost<input type="number" name="n" min="1" max="${c.count}" step="1" inputmode="numeric" required></label>
    <input type="hidden" name="kind" value="lost"><button class="btn small ghost" type="submit">Record the loss</button></form>`;
  return {
    title: c.title,
    html: html`<p class="noprint"><a href="#/propagating">All propagation</a></p>
    <h1>${c.title}</h1>
    <div class="verdict-box" role="status"><p><strong>${c.status_word}.</strong> ${c.method_label} from ${parentName}. ${prpPieces(c)}, started ${prpDate(c.started_on)} (${prpPl(c.days, 'day', 'days')} ago).
      ${c.method === 'seed' && c.sprouted ? ` ${c.sprouted} sprouted.` : ''}${c.lost ? ` ${c.lost} lost.` : ''}${c.medium ? ` In ${c.medium}.` : ''}${c.place ? ` At ${c.place}.` : ''}
      <a class="noprint" href="#/guide?sec=${c.guide}">How to do it</a></p></div>
    ${open && c.due.length ? html`<section class="blk" id="prp-now" data-prop="${id}"><h2>To do now</h2><ul class="jobs">${prpRow(c, true)}</ul></section>` : ''}
    <section class="blk" id="prp-steps"><h2>Treatment steps (${c.stages.length})</h2>
      ${c.stages.length ? html`<ol class="prp-stages">${c.stages.map(s => prpStageRow(s, can, id))}</ol>` : html`<p class="muted">No steps. Seeds that need a soak, warm or cold period get one here.</p>`}
      ${can ? html`<form data-form="prpstageadd" class="prp-stageadd noprint" data-id="${id}"><div class="field-grid">
        <label class="f">Add a step<select name="kind">${Object.entries(P.stage_kinds).map(([k, v]) => html`<option value="${k}">${v}</option>`)}</select></label>
        <label class="f">Days<input type="number" name="days" min="0" max="730" step="1" inputmode="numeric" placeholder="Usual"></label>
        <label class="f">Lowest °F<input type="number" name="temp_low" min="-20" max="140" inputmode="numeric"></label>
        <label class="f">Highest °F<input type="number" name="temp_high" min="-20" max="140" inputmode="numeric"></label></div>
        <button class="btn small" type="submit">Add the step</button></form>` : ''}</section>
    ${can && open ? html`<section class="blk noprint" id="prp-record"><h2>Record what happened</h2>
      <p class="row">${c.marks.map(m => m.kind === 'sprouted' ? '' : html`<button class="btn small" type="button" data-act="prpevent" data-kind="${m.kind}" data-id="${id}">${m.word}</button>`)}
        ${prpInWater(c) ? html`<button class="btn small" type="button" data-act="prpevent" data-kind="water" data-id="${id}">Changed the water</button>` : ''}
        <button class="btn small ghost" type="button" data-act="prpevent" data-kind="check" data-id="${id}">Looked, no change</button></p>
      ${c.method === 'seed' ? html`<form data-form="prpcount" class="prp-count" data-id="${id}"><label class="f">How many sprouted<input type="number" name="n" min="1" max="${c.count}" step="1" inputmode="numeric" required></label>
        <input type="hidden" name="kind" value="sprouted"><button class="btn small" type="submit">Record sprouts</button></form>` : ''}
      ${lostForm}
      <form data-form="prpnote" class="prp-note" data-id="${id}"><label class="f">Add a note<input type="text" name="text" maxlength="500" autocomplete="off" required></label><button class="btn small ghost" type="submit">Save the note</button></form>
      <p class="row">${c.status === 'active' ? html`<button class="btn small" type="button" data-act="prpstatus" data-st="ready" data-id="${id}">Ready to pot up (${c.ready_words.toLowerCase()})</button>` : html`<button class="btn small ghost" type="button" data-act="prpstatus" data-st="active" data-id="${id}">Not ready yet: going again</button>`}
        <button class="btn small ghost" type="button" data-act="prpstatus" data-st="failed" data-id="${id}">It did not work</button>
        <button class="btn small ghost" type="button" data-act="prpstatus" data-st="gave_away" data-id="${id}">Given away</button>
        ${c.method === 'seed' ? html`<button class="btn small ghost" type="button" data-act="prpstatus" data-st="done" data-id="${id}">Finished: no more will come</button>` : ''}</p></section>` : ''}
    ${can && !open && c.status !== 'done' ? html`<p class="noprint"><button class="btn small" type="button" data-act="prpstatus" data-st="active" data-id="${id}">Mark it going again</button></p>` : ''}
    ${can && open && c.left > 0 ? html`<section class="blk noprint" id="prp-pot"><h2>Pot it up as a new plant</h2>
      <p class="hint">${prpPl(c.left, 'piece is', 'pieces are')} not a plant yet. Each one potted up gets its own page and P-code, linked to ${c.parent_code ? c.parent_name || c.parent_code : 'this attempt'} in the family tree. What suits the species (light, water, temperatures) is copied from the parent plant.</p>
      <form data-form="prppromote" data-id="${id}"><div class="field-grid">
        <label class="f">Its name<input type="text" name="common_name" maxlength="120" value="${c.parent_name || c.species || ''}" autocomplete="off" required></label>
        <label class="f">Scientific name (optional)<input type="text" name="scientific_name" maxlength="160" value="${c.parent_code ? '' : c.species || ''}" autocomplete="off"></label>
        <label class="f">Where it will live<select name="site">${PRP_SITES.map(s => html`<option>${s}</option>`)}</select></label>
        <label class="f">Potted on<input type="date" name="made_on" value="${todayD}" max="${todayD}"></label></div>
        <button class="btn" type="submit">Pot it up</button></form></section>` : ''}
    <section class="blk" id="prp-made"><h2>Plants made (${c.children.length})</h2>
      ${c.children.length ? html`<ul>${c.children.map(k => html`<li><a href="#/plant/${enc(k.code)}">${k.name}</a> <span class="muted">${k.code}, potted ${prpDate(k.made_on)}</span></li>`)}</ul>` : html`<p class="muted">None yet.</p>`}
      <p class="noprint"><a href="#/propagating/family">Family tree</a></p></section>
    <section class="blk" id="prp-history"><h2>What happened (${c.events.length})</h2>
      ${c.events.length ? html`<ul class="prp-events">${c.events.map(e => html`<li><strong>${e.word}${e.n ? ' ' + e.n : ''}</strong>, ${prpDate(e.on_date)}${e.text ? ': ' + e.text : ''}
        ${can ? html`<button class="btn small ghost noprint" type="button" data-act="prpundo" data-eid="${e.id}" data-id="${id}" aria-label="${'Take back ' + e.word + ' of ' + prpDate(e.on_date)}">Take back</button>` : ''}</li>`)}</ul>` : html`<p class="muted">Nothing recorded yet.</p>`}</section>
    ${can ? html`<details class="grp noprint" id="prp-edit"><summary><h2>Change the details</h2></summary>
      <form data-form="prpedit" data-id="${id}"><div class="field-grid">
        <label class="f">Name<input type="text" name="title" maxlength="120" value="${c.title}"></label>
        <label class="f">Species<input type="text" name="species" maxlength="120" value="${c.species}"></label>
        <label class="f">How many<input type="number" name="count" min="${Math.max(1, c.children.length)}" max="5000" value="${c.count}"></label>
        <label class="f">Started on<input type="date" name="started_on" value="${c.started_on}" max="${todayD}"></label>
        <label class="f">What it sits in<input type="text" name="medium" maxlength="120" value="${c.medium}"></label>
        <label class="f">Setup<input type="text" name="setup" maxlength="300" value="${c.setup}"></label>
        <label class="f">Rooting hormone<input type="text" name="hormone" maxlength="120" value="${c.hormone}"></label>
        <label class="f">Where it is<input type="text" name="place" maxlength="120" value="${c.place}"></label>
        <label class="f">Look every (days)<input type="number" name="check_every" min="1" max="120" value="${c.check_every}"></label>
        <label class="f">Collected where<input type="text" name="collected_at" maxlength="300" value="${c.collected_at}"></label></div>
        <label class="f">Notes<textarea name="notes" rows="3" maxlength="2000">${c.notes}</textarea></label>
        <label class="f">How it ended<textarea name="outcome_note" rows="2" maxlength="2000">${c.outcome_note}</textarea></label>
        <p class="row"><button class="btn" type="submit">Save changes</button></p></form>
      ${c.children.length ? '' : html`<p><button class="btn danger small" type="button" data-act="prpremove" data-id="${id}">Remove this record</button></p>`}</details>` : ''}`,
  };
}

// ---------- the family tree ----------
function prpMakes(m) {
  return html`<li class="prp-make"><span class="prp-via">${m.method_label}</span> <a href="#/propagating/${m.id}">${m.code}</a>, started ${prpDate(m.started_on)}: ${m.status_word.toLowerCase()}.
    ${m.children.length ? html`<ul>${m.children.map(prpNode)}</ul>` : m.status === 'active' || m.status === 'ready' ? html`<span class="muted"> No plant made yet${m.sprouted ? ` (${m.sprouted} sprouted)` : ''}.</span>` : ''}</li>`;
}
function prpNode(n) {
  return html`<li class="prp-plant"><a class="nm" href="#/plant/${enc(n.code)}">${n.name}</a> <span class="muted">${n.code}${n.scientific ? ', ' + n.scientific : ''}. ${n.generation === 1 ? 'The original plant' : 'Generation ' + n.generation}${n.archived ? '. No longer kept' : ''}.</span>
    ${n.makes.length ? html`<ul>${n.makes.map(prpMakes)}</ul>` : ''}</li>`;
}
async function prpViewFamily() {
  const T = await api('GET', '/api/propagations/tree');
  return {
    title: 'Family tree',
    html: html`<p class="noprint"><a href="#/propagating">All propagation</a></p><h1>Family tree</h1>
    <p class="muted">Each plant, what has been made from it, and what those made. Only plants with a propagation record appear. Generation 1 is the plant the line started from.</p>
    <section class="blk" id="prp-tree"><h2>From your plants (${T.roots.length})</h2>
      ${T.roots.length ? html`<ul class="prp-tree">${T.roots.map(prpNode)}</ul>` : html`<p class="muted">Nothing yet. Start a cutting from a plant's own page, then pot it up when it has roots.</p>`}</section>
    <section class="blk" id="prp-outside"><h2>From seed or plants that came from elsewhere (${T.outside.length})</h2>
      ${T.outside.length ? html`<ul class="prp-tree">${T.outside.map(m => prpMakes(m))}</ul>` : html`<p class="muted">None.</p>`}</section>`,
  };
}

// ---------- actions ----------
const prpBody = f => {      // a form's text boxes as an object; empty ones are left out so the server uses its usual
  const o = {}; for (const el of f.elements) { if (!el.name || el.type === 'checkbox' || el.type === 'submit' || el.type === 'button') continue; if (el.value !== '') o[el.name] = el.value; } return o;
};
Object.assign(acts, {
  async prpevent(el) {
    if (!(await needName())) return;
    const id = el.dataset.id;
    await guard(async () => { await api('POST', `/api/propagations/${id}/events`, { kind: el.dataset.kind }); toast(el.textContent.trim() + ': saved'); await prpAfter(id); });
  },
  async prpundo(el) {
    if (!(await needName())) return;
    await guard(async () => { await api('DELETE', '/api/propagations/events/' + el.dataset.eid); toast('Taken back'); await prpAfter(); });
  },
  async prpstage(el) {
    if (!(await needName())) return;
    const sid = el.dataset.sid, id = el.dataset.id, what = el.dataset.do;
    if (what === 'remove' && !(await confirmBox('Remove this step?', 'It is taken off the list. Steps already finished stay.', 'Remove it', true))) return;
    await guard(async () => {
      if (what === 'remove') await api('DELETE', '/api/propagations/stages/' + sid);
      else await api('PUT', '/api/propagations/stages/' + sid, { action: what });
      toast(what === 'start' ? 'Step started' : what === 'done' ? 'Step finished' : what === 'remove' ? 'Step removed' : 'Taken back'); await prpAfter(id);
    });
  },
  async prpstatus(el) {
    if (!(await needName())) return;
    const st = el.dataset.st, id = el.dataset.id;
    if ((st === 'failed' || st === 'gave_away') && !(await confirmBox(st === 'failed' ? 'Mark it as not working?' : 'Mark it as given away?', 'It moves to Finished and counts in "What your attempts show". You can mark it going again.', 'Yes', false))) return;
    await guard(async () => { await api('POST', `/api/propagations/${id}/status`, { status: st }); toast('Saved'); await prpAfter(id); });
  },
  async prpremove(el) {
    if (!(await needName())) return;
    if (!(await confirmBox('Remove this record?', 'Its history is deleted. It is kept in the change log.', 'Remove it', true))) return;
    await guard(async () => { await api('DELETE', '/api/propagations/' + el.dataset.id); toast('Removed'); location.hash = '#/propagating'; });
  },
});
Object.assign(formActs, {
  async prpnew(f) {
    if (!(await needName())) return;
    const b = prpBody(f);
    b.stages = PRP_STEP_ORDER.filter(k => f.elements['s_' + k].checked).map(k => { const s = { kind: k, days: f.elements['d_' + k].value };
      if (f.elements['l_' + k].value !== '') s.temp_low = f.elements['l_' + k].value; if (f.elements['h_' + k].value !== '') s.temp_high = f.elements['h_' + k].value; return s; });
    for (const k of Object.keys(b)) if (/^[sdlh]_/.test(k)) delete b[k];
    await guard(async () => { const r = await api('POST', '/api/propagations', b); toast('Started ' + r.code); location.hash = '#/propagating/' + r.id; });
  },
  async prpedit(f) {
    if (!(await needName())) return;
    const b = {}; for (const el of f.elements) if (el.name) b[el.name] = el.value;
    const id = f.dataset.id;
    await guard(async () => { await api('PUT', '/api/propagations/' + id, b); toast('Saved'); await prpAfter(); });
  },
  async prpnote(f) {
    if (!(await needName())) return;
    const id = f.dataset.id;
    await guard(async () => { await api('POST', `/api/propagations/${id}/events`, { kind: 'note', text: f.elements.text.value }); toast('Note saved'); await prpAfter(id); });
  },
  async prpcount(f) {
    if (!(await needName())) return;
    const id = f.dataset.id, kind = f.elements.kind.value;
    await guard(async () => { await api('POST', `/api/propagations/${id}/events`, { kind, n: f.elements.n.value }); toast(kind === 'lost' ? 'Saved: lost' : 'Saved: sprouted'); await prpAfter(id); });
  },
  async prpstageadd(f) {
    if (!(await needName())) return;
    const id = f.dataset.id, b = prpBody(f);
    await guard(async () => { await api('POST', `/api/propagations/${id}/stages`, b); toast('Step added'); await prpAfter(id); });
  },
  async prppromote(f) {
    if (!(await needName())) return;
    const id = f.dataset.id, b = prpBody(f);
    await guard(async () => { const r = await api('POST', `/api/propagations/${id}/promote`, b); toast(`Potted up as ${r.code}`); await prpAfter(id); });
  },
});

// What this module adds, said once (features.js):
//  - the page #/propagating (no top-bar link, as the guide: a ninth link wraps the bar; the plant page, Today and the guide link to it, and Search finds it);
//  - a block on Today (order 66, after Turn the pots) with what is due: a look, a changed jar of water, the end of a seed's cold step;
//  - on a plant's page, "Family and propagation": where it came from, what has been made from it, and a button to start a cutting or seeds;
//  - on the guide page, a link here.
addFeature({
  name: 'propagation',
  pages: { propagating: { view: viewPropagating, nav: 'plants', label: 'Propagation', href: '#/propagating' } },
  today: {
    id: 'today-prop', order: 66,
    load: async () => { const P = await api('GET', '/api/propagations'); return P.counts.due ? P : null; },
    jump: P => `Propagation (${P.counts.due})`,
    html: P => html`<section class="blk" id="today-prop"><h2>Propagation (${P.counts.due})</h2>${prpBlock(P)}
      <p><a class="btn small ghost" href="#/propagating">All propagation</a></p></section>`,
  },
  adds: [
    { id: 'prp-plant', match: parts => parts[0] === 'plant' && parts[1] && parts[2] !== 'edit', anchor: '#uses', where: 'afterend',
      load: async parts => api('GET', '/api/propagations/plant/' + enc(decodeURIComponent(parts[1]))),
      html: (D, parts) => {
        const code = decodeURIComponent(parts[1]), can = canChange();
        return html`<section class="blk" id="prp-plant"><h2>Family and propagation</h2>
          ${D.origin ? html`<p>${D.ancestors.length ? html`Made from <a href="#/plant/${enc(D.ancestors[0].code)}">${D.ancestors[0].name || D.ancestors[0].code}</a> <span class="muted">${D.ancestors[0].code}</span> by ${D.ancestors[0].via.toLowerCase()}` : 'Grown from seed or a plant from elsewhere'}
              (<a href="#/propagating/${D.origin.id}">${D.origin.code}</a>, started ${prpDate(D.origin.started_on)}). Generation ${D.generation}.</p>` : html`<p class="muted">Not made from another plant in this app.</p>`}
          ${D.made.length ? html`<h3>Made from this plant (${D.made.length})</h3><ul>${D.made.map(m => html`<li><a href="#/propagating/${m.id}">${m.title}</a> <span class="muted">${m.code}</span>: ${m.status_word.toLowerCase()}${m.children.length ? ', made ' + m.children.map(k => k.code).join(', ') : ''}</li>`)}</ul>` : ''}
          <p class="row noprint">${can ? html`<a class="btn small" href="#/propagating/new?parent=${enc(code)}">Start a cutting, layer or seeds from this plant</a>` : ''}
            <a class="btn small ghost" href="#/propagating/family">Family tree</a> <a class="btn small ghost" href="#/propagating">All propagation</a></p></section>`;
      } },
    { id: 'prp-guidelink', match: parts => parts[0] === 'guide', anchor: 'main h1, #app h1', where: 'afterend', load: async () => true,
      html: () => html`<p class="hint noprint" id="prp-guidelink">Keep track of what you try: <a href="#/propagating">Propagation</a>, with a <a href="#/propagating/family">family tree</a>.</p>` },
  ],
});
