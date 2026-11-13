// ---------- previews (proto/import-and-cards; November 13, 2026) ----------
// Two sets of options Ethan chooses between from pictures on his screens:
//   item 12 of the November 12 review: plant updates that arrive as a file he brings in (the "Updates from Claude" page), and
//   the watering cards on Today using less of the screen, with their pictures kept.
// Nothing here is on unless localStorage "plantdb.preview" says so:
//   {"water": "flow" | "boxes" | "tick" | "spots", "ticked": 2,
//    "updates": "plant" | "walk" | "kind", "updstate": "start" | "done", "updstep": 2}
// so the app is unchanged without it, and the Updates page is in the menu only while "updates" is set. Each choice also sets
// data-pv-<name> on <html> for css/preview.css. The option he picks is then built as a real change and this file goes away.
'use strict';
const PVS = (() => { try { return JSON.parse(localStorage.getItem('plantdb.preview') || '{}') || {}; } catch (e) { return {}; } })();
const PV = k => PVS[k] || '';
for (const [k, v] of Object.entries(PVS)) if (v) document.documentElement.setAttribute('data-pv-' + k, v);

// ===== the watering cards =====
// As built in 1.58.0 a card is 9rem wide and about 23rem tall: a picture, the name, the code, how late, two buttons one above the other
// and "Why"; and every spot has a band of the page to itself however few plants it holds. Four ways to give that room back. In all of
// them the code sits beside the name, how late a plant is opens the reason (the "Why" line is gone), and a phone has one list to go
// to a spot in place of a button for each.
//   flow:  the same cards and buttons in one run, with a tile where each spot starts (its name and "Watered all N here").
//   boxes: the same cards and buttons, each spot still in a box of its own; spots with few plants share a row.
//   tick:  one run with tiles, and a card is a larger picture, the name and how late: press the picture to tick it, and one bar
//          at the bottom of the screen holds Watered and Still moist for everything ticked.
//   spots: a spot is a row: its name, its one button and a strip of pictures. Its plants open into cards on request.
const pvWhy = (p, w) => w.state === 'unknown' ? html`<p class="wpl-st"><strong>${waterShort(w)}.</strong></p>`
  : html`<details class="wpl-why wpl-st"><summary aria-label="${waterShort(w)}. Why: ${p.common_name}">${waterShort(w)}.</summary><p>${waterWords(w)}</p></details>`;      // how late it is opens the reason
const pvPic = p => p.photo ? html`<img src="${thumbUrl(p.photo)}" alt="" loading="lazy" width="160" height="120">` : html`<span class="job-nophoto" aria-hidden="true"></span>`;
function pvCardTight(p, w, btns) {
  return html`<li class="wpl-card" data-code="${p.code}"><a class="wpl-open" href="#/plant/${enc(p.code)}">${pvPic(p)}<span class="nm">${p.common_name}</span> <span class="muted wpl-code">${p.code}</span></a>
    ${pvWhy(p, w)}
    <div class="wpl-acts">${btns}</div></li>`;
}
function pvCardTick(p, w, on) {
  const kind = w.action && w.action !== 'water' ? w.action : 'water';
  return html`<li class="wpl-card wpl-pick" data-code="${p.code}">
    <label class="wpl-tk"><input type="checkbox" data-f="pvtick" data-code="${p.code}" data-kind="${kind}" aria-label="Tick ${p.common_name}" ${on ? raw('checked') : ''}>${pvPic(p)}<span class="wpl-tkmark" aria-hidden="true">✓ Ticked</span></label>
    <p class="wpl-nml"><a class="nm" href="#/plant/${enc(p.code)}">${p.common_name}</a> <span class="muted wpl-code">${p.code}</span></p>
    ${pvWhy(p, w)}</li>`;
}
const pvLate = ws => {                 // "Up to 6 days overdue", "2 overdue (up to 3 days), 1 due today": a spot's plants in a few words
  const od = ws.filter(w => w.overdue > 0), td = ws.filter(w => w.overdue === 0 && w.state === 'due').length, most = Math.max(0, ...od.map(w => w.overdue));
  const days = `${most} day${most === 1 ? '' : 's'}`;
  if (od.length && od.length === ws.length) return od.length === 1 ? `${days} overdue` : `Up to ${days} overdue`;
  return [od.length ? `${od.length} overdue (up to ${days})` : '', td ? `${td} due today` : ''].filter(Boolean).join(', ') || (ws[0] ? waterShort(ws[0]) : '');
};
function pvWaterByPlace(list, by, wbtn, canAll, key) {
  const mode = PV('water'), gs = wplGroups(list, by), nm = g => g.a ? g.a.name + ': ' + (g.s ? g.s.name : 'no spot set') : 'No room set';
  const narrow = document.documentElement.dataset.narrow === '1', nTick = key === 'due' ? +PV('ticked') || 0 : 0;
  const run = mode === 'flow' || mode === 'tick';          // one run of cards, with a tile where each spot starts
  let seen = 0;
  // going to a spot: a phone gets one list in place of a button for each spot; a run of cards on a wide screen is short enough to need neither
  const jump = gs.length < 3 || mode === 'spots' || (run && !narrow) ? ''
    : narrow ? html`<label class="wpl-go">Go to a spot<select data-f="pvgo"><option value="">Choose one of ${gs.length}</option>${gs.map((g, i) => html`<option value="wpl-${key}-${i}">${nm(g)} (${g.ws.length})</option>`)}</select></label>`
    : html`<nav class="wpl-jump row" aria-label="Go to a spot">${gs.map((g, i) => html`<button class="btn small ghost" type="button" data-act="jumpsec" data-sec="wpl-${key}-${i}">${nm(g)} (${g.ws.length})</button>`)}</nav>`;
  const all = (g, name, n) => n > 1 && canAll ? html`<button class="btn small" type="button" data-act="careall" data-kind="water" data-codes="${g.ws.map(w => w.code).join(',')}" aria-label="Watered all ${n} here: ${name}">Watered all ${n} here</button>` : '';
  // the ticked plants' buttons: a bar held at the bottom of the screen, there only while something is ticked
  const bar = mode === 'tick' ? html`<div class="wpl-bar" role="group" aria-label="The plants you ticked" ${nTick ? '' : raw('hidden')}><span class="wpl-bar-n" role="status">${pvBarWords(nTick)}</span>
      <button class="btn small" type="button" data-act="pvtickdo" data-kind="water">Watered</button>
      <button class="btn small ghost" type="button" data-act="pvtickdo" data-kind="check">Still moist</button>
      <button class="btn small ghost" type="button" data-act="pvtickclear">Untick</button></div>` : '';
  const hint = mode === 'tick' ? html`<p class="hint wpl-tickhint">Press a picture to tick a plant. <strong>Watered</strong> and <strong>Still moist</strong> for the ticked plants then stay at the bottom of the screen.</p>` : '';
  const card = w => mode === 'tick' ? pvCardTick(by[w.code], w, seen++ < nTick) : pvCardTight(by[w.code], w, wbtn(w));
  const head = (g, i, tile) => { const name = nm(g), n = g.ws.length;
    return html`<div class="wpl-head${tile ? ' wpl-tile' : ''}">${tile ? html`<p class="wpl-kick" aria-hidden="true">Spot</p>` : ''}<h3 id="wpl-${key}-${i}" tabindex="-1">${name} <span class="wpl-n">(${n})</span></h3>${mode === 'spots' ? html`<span class="wpl-late">${pvLate(g.ws)}</span>` : ''}${all(g, name, n)}</div>`; };
  if (mode === 'spots') return html`<div class="wpl wpl-spots">${gs.map((g, i) => { const n = g.ws.length;
    return html`<section class="wpl-grp wpl-spot" aria-labelledby="wpl-${key}-${i}">${head(g, i)}
      <div class="wpl-strips"><ul class="wpl-strip">${g.ws.map(w => { const p = by[w.code]; return html`<li><a href="#/plant/${enc(p.code)}">${p.photo ? html`<img src="${thumbUrl(p.photo)}" alt="${p.common_name}, ${waterShort(w).toLowerCase()}" loading="lazy" width="120" height="120">` : html`<span class="job-nophoto wpl-noph">${p.common_name}</span>`}</a></li>`; })}</ul>
        <details class="wpl-more"><summary>${n === 1 ? 'Its name and its buttons' : `The ${n} plants one by one, with their names and buttons`}</summary>
          <ul class="wpl-cards">${g.ws.map(w => pvCardTight(by[w.code], w, wbtn(w)))}</ul></details></div></section>`; })}</div>`;
  if (run) return html`<div class="wpl wpl-${mode} wpl-run">${jump}${hint}
    <div class="wpl-grid">${gs.map((g, i) => html`<section class="wpl-in" aria-labelledby="wpl-${key}-${i}">${head(g, i, true)}<ul class="wpl-cards" role="list">${g.ws.map(card)}</ul></section>`)}</div>
    ${bar}</div>`;
  return html`<div class="wpl wpl-${mode} wpl-flow">${jump}
    ${gs.map((g, i) => html`<section class="wpl-grp" aria-labelledby="wpl-${key}-${i}" style="--n:${g.ws.length}">${head(g, i)}<ul class="wpl-cards">${g.ws.map(card)}</ul></section>`)}</div>`;
}
const pvBarWords = n => n ? `${n} ticked` : '';
function pvTickState(wpl) {             // the bar is there while something is ticked, and says how many
  const n = wpl.querySelectorAll('input[data-f=pvtick]:checked').length, bar = wpl.querySelector('.wpl-bar'); if (!bar) return;
  bar.hidden = !n; bar.querySelector('.wpl-bar-n').textContent = pvBarWords(n);
}
document.addEventListener('change', e => {
  const el = e.target; if (!el.dataset) return;
  if (el.dataset.f === 'pvtick') pvTickState(el.closest('.wpl'));
  else if (el.dataset.f === 'pvgo' && el.value) { const t = document.getElementById(el.value); if (t) { scrollToSection(t); navFlash(t); } el.value = ''; }
  else if (el.dataset.f === 'updtick') { const x = UPD.items[+el.dataset.i]; if (x) { x.on = el.checked; updCount(); } }
  else if (el.dataset.f === 'updtake') { const x = UPD.items[+el.dataset.i]; if (x) { x.take = el.value; updCount(); } }
});

// ===== item 12: updates that arrive as a file =====
// Today a correction to a plant's page travels in an upgrade batch inside a release (39 of them so far, with his plants' details in
// the public code). His choice (November 13): Claude saves a small file on his computer and a page shows each change to accept or skip.
// This is that page, three ways. UPD_FILE stands for the file; the changes are made up to show every kind (a correction, one that
// needs a decision because the page no longer says what the file expected, a new page, a plant to archive, a question). "Now" is read
// from the record when the page draws, as the real page will. Nothing is changed here: the last button only shows what follows.
const UPD_FILE = {
  name: 'plant-updates-20261114-0312.json', made: '2026-11-14',
  about: 'From the photos you added on November 12 and your answers of November 13: two plants look better than their pages say, one name is surer, one vine is finished for good, and one plant in your photos has no page yet.',
  changes: [
    { kind: 'set', code: 'P-009', field: 'health_rating', from: 'Fair', to: 'Good', why: 'Five new leaves since October, and none of them droop in the November 12 photos.' },
    { kind: 'set', code: 'P-009', field: 'health_summary', from: 'Recovering. Several leaves droop or curl and some old ones are dead, but new leaves with red sheaths are coming.',
      to: 'Recovered. Five new leaves have opened since October, and the dead leaves at the base are gone.', why: 'So the page says what the plant looks like now.' },
    { kind: 'set', code: 'P-012', field: 'scientific_name', from: 'Aeonium haworthii type (probable)', to: "Aeonium haworthii 'Kiwi' (likely)", why: 'The close-up shows yellow centres with red edges, which is the cultivar Kiwi.' },
    { kind: 'set', code: 'P-012', field: 'id_confidence', from: 70, to: 85, why: 'The same close-up.' },
    { kind: 'set', code: 'P-052', field: 'winter_plan', from: 'Protect outside', to: 'Move indoors', why: 'You said it will spend the winter by the living room window.' },
    { kind: 'set', code: 'P-010', field: 'water_every_days', from: null, to: 7, why: 'You said you water it every week. Until now the reminder was worked out from the weather.' },
    { kind: 'set', code: 'P-072', field: 'location', from: 'On the concrete by the steps', to: 'On the ground by the steps, beside the hose', why: 'It moved between the October and November photos.' },
    { kind: 'set', code: 'P-055', field: 'health_rating', from: 'Poor', to: 'Fair', why: 'The yellow leaves are gone, and two new ones are dark and firm.' },
    { kind: 'set', code: 'P-016', field: 'container', from: 'Terracotta bowl with perlite and bark', to: 'Small terracotta pot of its own, with gritty mix', why: 'It has a pot of its own in the November 12 photos.' },
    { kind: 'archive', code: 'P-005', why: 'It has died back and this kind does not return. Its page and photos stay in the archive.' },
    { kind: 'new', name: 'Hardy aloe, second pot', sci: 'Aloiampelos striatula', site: 'Outdoors', like: 'P-015', photos: 3, why: 'Your November 12 photos show a second pot of it by the steps, with no page of its own.' },
    { kind: 'ask', code: 'P-014', text: 'Is the largest aloe still in the black pot with white gravel, or has it been repotted?', why: 'The newest photo shows a terracotta pot beside it.' },
    { kind: 'ask', code: 'P-003', text: 'Has the fig dropped its leaves yet? The date helps time next year\'s frost warnings.', why: '' },
  ],
};
const UPD = { items: [], step: 0, seen: {}, state: '' };
const updSame = (a, b) => String(a == null ? '' : a).trim() === String(b == null ? '' : b).trim();
async function updLoad() {
  const codes = [...new Set(UPD_FILE.changes.map(c => c.code || c.like).filter(Boolean))];
  const got = await Promise.all(codes.map(c => api('GET', '/api/plants/' + enc(c)).catch(() => null)));
  const P = Object.fromEntries(got.filter(Boolean).map(p => [p.code, p])), L = Object.fromEntries((META.fields || []).map(f => [f.name, f.label]));
  UPD.items = UPD_FILE.changes.map((c, i) => {
    const p = P[c.code] || null, now = c.kind === 'set' && p ? p[c.field] : null;
    const conflict = c.kind === 'set' && !!p && !updSame(now, c.from) && !updSame(now, c.to);        // the page no longer says what the file expected
    const like = c.like && P[c.like], pics = like ? like.photos.slice(1, 1 + c.photos).map(x => x.file) : [];
    return { ...c, i, p, now, pics, conflict, on: !conflict, take: 'mine', label: c.kind === 'set' ? L[c.field] || c.field : '' };
  });
  UPD.step = Math.max(0, (+PV('updstep') || 1) - 1); UPD.seen = {}; UPD.state = PV('updstate');
  if (PV('updates') === 'walk') updGroups().slice(0, UPD.step).forEach((g, k) => { UPD.seen[g.key] = k === 1 ? 'skip' : 'ok'; if (k === 1) g.items.forEach(x => { x.on = false; }); });
}
function updGroups() {                 // the changes plant by plant, in the file's order; a new page is a plant of its own
  const m = new Map();
  for (const x of UPD.items) { const key = x.code || 'new' + x.i; if (!m.has(key)) m.set(key, { key, p: x.p, items: [] }); m.get(key).items.push(x); }
  return [...m.values()];
}
const updDoing = x => x.conflict ? x.take === 'claude' : x.on;          // will this change be made?
const updVal = v => v == null || v === '' ? html`<span class="muted">Not set</span>` : html`${String(v)}`;
const updWhat = x => x.kind === 'set' ? x.label : x.kind === 'archive' ? 'Move this plant to the archive' : x.kind === 'ask' ? 'A question for you' : 'A new page for this plant';
const updName = g => g.p ? g.p.common_name : g.items[0].name;
const updPhoto = g => g.p ? ((g.p.photos.find(x => x.is_primary) || g.p.photos[0] || {}).file || '') : (g.items[0].pics[0] || '');
function updSumWords() {
  const n = UPD.items.length, plants = updGroups().length, need = UPD.items.filter(x => x.conflict).length, doing = UPD.items.filter(updDoing).length;
  return `${n} changes for ${plants} plants. ${doing} ${doing === 1 ? 'is' : 'are'} set to be made${need ? `; ${need} ${need === 1 ? 'needs' : 'need'} your decision and ${need === 1 ? 'stays' : 'stay'} as ${need === 1 ? 'it is' : 'they are'} unless you choose Claude's` : ''}.`;
}
function updCount() {                  // after a tick: the summary and the button say the new number
  const doing = UPD.items.filter(updDoing).length;
  const s = document.getElementById('upd-sum'); if (s) s.textContent = updSumWords();
  const b = document.getElementById('upd-go'); if (b) { b.textContent = updGoWords(doing); b.disabled = !doing; }
  const w = document.getElementById('upd-go-why'); if (w) w.hidden = !!doing;
}
const updGoWords = n => n === 1 ? 'Make the 1 change' : `Make the ${n} changes`;
function updChange(x) {                // one change: what it is, what the page says now and what it would say, why; a tick box, or a choice of two
  const id = 'upd-c' + x.i;
  if (x.conflict) return html`<li class="upd-ch upd-conf" id="${id}" tabindex="-1">
    <p class="upd-what"><strong>${x.label}</strong> <span class="tag upd-tag">Needs your decision</span></p>
    <p>This no longer says what the file expected, so it may be a change you made yourself.</p>
    <fieldset class="upd-pick"><legend class="sr">${x.label}: which one to keep</legend>
      <label class="chk"><input type="radio" name="upd-take-${x.i}" value="mine" data-f="updtake" data-i="${x.i}" ${x.take === 'mine' ? raw('checked') : ''}><span><span class="upd-k">Keep what it says now:</span> ${updVal(x.now)}</span></label>
      <label class="chk"><input type="radio" name="upd-take-${x.i}" value="claude" data-f="updtake" data-i="${x.i}" ${x.take === 'claude' ? raw('checked') : ''}><span><span class="upd-k">Change it to Claude's:</span> <strong>${updVal(x.to)}</strong></span></label></fieldset>
    ${x.why ? html`<p class="hint">Why Claude suggests it: ${x.why}</p>` : ''}</li>`;
  return html`<li class="upd-ch" id="${id}">
    <label class="chk upd-tick"><input type="checkbox" data-f="updtick" data-i="${x.i}" ${x.on ? raw('checked') : ''} aria-describedby="${id}-v"><span><strong>${updWhat(x)}</strong></span></label>
    <div class="upd-vals" id="${id}-v">${x.kind === 'set' ? html`<p><span class="upd-k">Now:</span> ${updVal(x.now)}</p><p><span class="upd-k">Change to:</span> <strong>${updVal(x.to)}</strong></p>`
      : x.kind === 'ask' ? html`<p>${x.text}</p><p class="hint">It joins what Claude needs from you on this plant's page.</p>`
      : x.kind === 'archive' ? html`<p>It leaves the lists and Today. Nothing is deleted, and <strong>Move back to the main list</strong> on its page undoes it.</p>`
      : html`<p><i class="latin">${x.sci}</i>. ${x.site}. ${x.photos} photos come with it${x.pics.length ? ':' : '.'}</p>${x.pics.length ? html`<ul class="upd-pics">${x.pics.map((f, k) => html`<li><img src="${thumbUrl(f)}" alt="Photo ${k + 1} of ${x.pics.length} for the new page" loading="lazy" width="120" height="120"></li>`)}</ul>` : ''}`}</div>
    ${x.why ? html`<p class="hint">Why: ${x.why}</p>` : ''}</li>`;
}
function updPlant(g, big) {            // a plant with its picture and its changes
  const ph = updPhoto(g), name = updName(g), isNew = !g.p;
  return html`<article class="upd-plant${big ? ' upd-big' : ''}" aria-labelledby="upd-p-${g.key}">
    <div class="upd-ph">${ph ? html`<img src="${thumbUrl(ph)}" alt="" loading="lazy" width="${big ? 520 : 240}" height="${big ? 390 : 180}">` : html`<span class="job-nophoto" aria-hidden="true"></span>`}</div>
    <div class="upd-body"><h3 id="upd-p-${g.key}">${isNew ? name : html`<a href="#/plant/${enc(g.p.code)}">${name}</a>`} <span class="muted">${isNew ? 'No page yet' : g.p.code}</span></h3>
      <ul class="upd-list">${g.items.map(updChange)}</ul></div></article>`;
}
function updHead(short) {         // short: the walk-through after its first plant, where the plant should be the first thing on the screen
  if (short) return html`<h1>Updates from Claude</h1>
    <details class="upd-file upd-fold"><summary>${UPD_FILE.name}, and Claude's note</summary><p>Made ${longDay(UPD_FILE.made)}. ${UPD_FILE.about}</p>
      <p class="upd-sum" id="upd-sum" role="status">${updSumWords()}</p>
      <p><button class="btn small ghost" type="button" data-act="updstart">Choose another file</button></p></details>`;
  return html`<h1>Updates from Claude</h1>
    <div class="upd-file"><p><strong>${UPD_FILE.name}</strong>, made ${longDay(UPD_FILE.made)}. <button class="btn small ghost" type="button" data-act="updstart">Choose another file</button></p>
      <p><span class="upd-k">Claude's note:</span> ${UPD_FILE.about}</p></div>
    <p class="upd-sum" id="upd-sum" role="status">${updSumWords()}</p>
    <p class="hint upd-safe">Nothing is changed until you press the button that makes the changes.</p>`;
}
function updBar() {
  const doing = UPD.items.filter(updDoing).length;
  return html`<div class="sticky-save upd-bar"><button class="btn" type="button" id="upd-go" data-act="updapply" aria-describedby="upd-go-why" ${doing ? '' : raw('disabled')}>${updGoWords(doing)}</button>
    <button class="btn ghost upd-no" type="button" data-act="updstart">Change nothing</button>
    <span class="why" id="upd-go-why" ${doing ? raw('hidden') : ''}>Nothing is ticked.</span></div>
    <p class="row upd-no-end"><button class="btn ghost" type="button" data-act="updstart">Change nothing</button></p>`;      // a phone: the bar holds one button, and this one ends the page
}
const updTicks = () => html`<p class="row upd-all"><button class="btn small ghost" type="button" data-act="updall" data-on="1">Tick every change</button><button class="btn small ghost" type="button" data-act="updall" data-on="0">Untick every change</button></p>`;
// A: every plant on one page, each with its picture and its changes, ticked to begin with
function updByPlant() {
  const need = UPD.items.filter(x => x.conflict);
  return html`${updHead()}
    ${need.length ? html`<p class="notice upd-needs" role="note"><strong>${need.length} ${need.length === 1 ? 'change needs' : 'changes need'} your decision.</strong> ${need.map(x => html`<a href="#upd-c${x.i}" data-act="jumpsec" data-sec="upd-c${x.i}">${x.p.common_name}: ${x.label}</a>`)}</p>` : ''}
    ${updTicks()}
    <h2 class="sr">The changes, plant by plant</h2>
    <div class="upd-plants">${updGroups().map(g => updPlant(g))}</div>
    ${updBar()}`;
}
// B: one plant at a time, like the health walk-through
function updWalk() {
  const gs = updGroups(), n = gs.length, i = Math.min(UPD.step, n), okN = Object.values(UPD.seen).filter(v => v === 'ok').length, skN = Object.values(UPD.seen).filter(v => v === 'skip').length;
  const list = html`<details class="grp upd-idx"><summary><h3>All ${n} plants in this file</h3></summary><ol class="upd-steps">${gs.map((g, k) => html`<li><button class="btn small ghost" type="button" data-act="updstep" data-to="${k}" ${k === i ? raw('aria-current="step"') : ''}>${updName(g)}</button>
      <span class="${UPD.seen[g.key] ? '' : 'muted'}">${UPD.seen[g.key] === 'ok' ? '✓ Accepted' : UPD.seen[g.key] === 'skip' ? 'Skipped' : 'Not looked at yet'}</span></li>`)}</ol></details>`;
  if (i >= n) return html`${updHead()}
    <h2>You have looked at all ${n} plants</h2>
    <p>${okN} accepted, ${skN} skipped. Open any plant in the list to look again.</p>${list}${updBar()}`;
  const g = gs[i];
  return html`${updHead(i > 0)}
    <p class="upd-prog" role="status"><strong>Plant ${i + 1} of ${n}</strong>${okN || skN ? `: ${okN} accepted and ${skN} skipped so far` : ''}</p>
    <div class="upd-meter" role="presentation"><span style="width:${Math.round(100 * i / n)}%"></span></div>
    ${updPlant(g, true)}
    <p class="row upd-nav"><button class="btn" type="button" data-act="updnext" data-how="ok">${g.items.some(x => x.conflict) ? 'Go on with my choice' : g.items.length === 1 ? 'Accept and go on' : `Accept the ${g.items.filter(x => x.on).length} ticked and go on`}</button>
      <button class="btn ghost" type="button" data-act="updnext" data-how="skip">Skip this plant</button>
      <button class="btn ghost" type="button" data-act="updstep" data-to="${i - 1}" ${i ? '' : raw('disabled')}>Back</button></p>
    ${list}`;
}
// C: a short list, one line a change, by the kind of change
function updRow(x) {
  const name = x.p ? x.p.common_name : x.name, ph = x.p ? ((x.p.photos.find(q => q.is_primary) || x.p.photos[0] || {}).file || '') : (x.pics[0] || ''), id = 'upd-c' + x.i;
  const line = x.kind === 'set' ? html`${x.label}: now ${updVal(x.now)}; change to <strong>${updVal(x.to)}</strong>`
    : x.kind === 'ask' ? html`${x.text}` : x.kind === 'archive' ? html`Move to the archive. Nothing is deleted.` : html`<i class="latin">${x.sci}</i>. ${x.site}. ${x.photos} photos come with it.`;
  return html`<li class="upd-row" id="${id}"><label class="upd-tick"><input type="checkbox" data-f="updtick" data-i="${x.i}" ${x.on ? raw('checked') : ''}>
      ${ph ? html`<img src="${thumbUrl(ph)}" alt="" loading="lazy" width="64" height="64">` : html`<span class="job-nophoto" aria-hidden="true"></span>`}
      <span class="upd-row-t"><span class="nm">${name}</span> <span class="muted">${x.p ? x.p.code : 'No page yet'}</span><span class="upd-line">${line}</span></span></label>
    ${x.why ? html`<details class="wpl-why"><summary aria-label="Why: ${name}, ${updWhat(x)}">Why</summary><p>${x.why}</p></details>` : ''}</li>`;
}
function updByKind() {
  const need = UPD.items.filter(x => x.conflict), by = k => UPD.items.filter(x => x.kind === k && !x.conflict);
  const part = (title, xs) => xs.length ? html`<section class="upd-kind"><h2>${title} (${xs.length})</h2><ul class="upd-rows">${xs.map(updRow)}</ul></section>` : '';
  return html`${updHead()}${updTicks()}
    ${need.length ? html`<section class="upd-kind"><h2>${need.length === 1 ? 'Needs' : 'Need'} your decision (${need.length})</h2>
      <ul class="upd-list upd-needlist">${need.map(x => html`<li class="upd-needp"><p class="upd-needn"><a href="#/plant/${enc(x.p.code)}">${x.p.common_name}</a> <span class="muted">${x.p.code}</span></p><ul class="upd-list">${updChange(x)}</ul></li>`)}</ul></section>` : ''}
    ${part('Corrections', by('set'))}${part('New pages', by('new'))}${part('Plants to archive', by('archive'))}${part('Questions for you', by('ask'))}
    ${updBar()}`;
}
// before a file is chosen, and after the changes are made
function updStart() {
  return html`<h1>Updates from Claude</h1>
    <p>When Claude has corrections or new pages for your plants, it saves one small file on this computer and tells you its name. Choose that file here. You see every change and decide before anything is changed, and nothing about your plants leaves this computer.</p>
    <form class="upd-choose" data-form="updfile"><label class="f">The update file<small>Claude saves it in Documents, Claude, Plants, updates. Its name starts with "plant-updates".</small>
      <input type="file" name="file" accept=".json,.zip" data-f="updfile"></label>
      <p class="row"><button class="btn" type="button" data-act="updopen">Show its changes</button></p></form>
    <h2>Files you brought in before</h2>
    <ul class="upd-old">
      <li><strong>${longDay('2026-11-09')}</strong>: plant-updates-20261109-1841.json. 9 changes made, 1 skipped. <a href="#/audit">See them in the Audit log</a></li>
      <li><strong>${longDay('2026-11-04')}</strong>: plant-updates-20261104-0207.json. 22 changes made. <a href="#/audit">See them in the Audit log</a></li></ul>
    <p class="hint">A file can be brought in once. Opening it again shows what it did.</p>`;
}
function updDone() {
  const done = UPD.items.filter(updDoing), left = UPD.items.length - done.length, gs = updGroups().filter(g => g.items.some(updDoing));
  return html`<h1>Updates from Claude</h1>
    <div class="notice ok upd-done" role="status"><p><strong>${done.length} ${done.length === 1 ? 'change' : 'changes'} made${left ? `, ${left} left as ${left === 1 ? 'it was' : 'they were'}` : ''}.</strong> From ${UPD_FILE.name}.</p>
      <p>Each one is in its plant's page history and in the Audit log, signed "Claude (${UPD_FILE.name})".</p></div>
    <p class="hint upd-proto">This is a preview: nothing in the record was changed.</p>
    <h2>What changed</h2>
    <ul class="upd-did">${gs.map(g => html`<li>${g.p ? html`<a href="#/plant/${enc(g.p.code)}">${updName(g)}</a> <span class="muted">${g.p.code}</span>` : html`<strong>${updName(g)}</strong> <span class="muted">a new page</span>`}:
      ${g.items.filter(updDoing).map(x => x.kind === 'set' ? x.label : x.kind === 'ask' ? 'a question for you' : x.kind === 'archive' ? 'archived' : 'page made, with its photos').join(', ')}.</li>`)}</ul>
    <p>To take one back, open the plant's page, then <strong>Page history</strong>, and restore the version before today's.</p>
    <p class="row"><a class="btn" href="#/">Go to Today</a><a class="btn ghost" href="#/audit">Open the Audit log</a><button class="btn ghost" type="button" data-act="updstart">Bring in another file</button></p>`;
}
async function viewUpdates() {
  if (!UPD.items.length || UPD.fresh) { await updLoad(); UPD.fresh = false; }
  const kind = PV('updates') || 'plant';
  return { title: 'Updates from Claude', html: UPD.state === 'start' ? updStart() : UPD.state === 'done' ? updDone() : kind === 'walk' ? updWalk() : kind === 'kind' ? updByKind() : updByPlant() };
}
const updRedraw = async () => { const y = scrollY; await route(); scrollTo(0, y); };
Object.assign(acts, {
  updall(el) { UPD.items.forEach(x => { if (!x.conflict) x.on = el.dataset.on === '1'; }); updRedraw(); },
  updstep(el) { UPD.step = Math.max(0, +el.dataset.to); route(); },
  updnext(el) { const g = updGroups()[UPD.step]; if (!g) return; UPD.seen[g.key] = el.dataset.how;
    if (el.dataset.how === 'skip') g.items.forEach(x => { x.on = false; x.take = 'mine'; });
    UPD.step++; route(); },
  updapply() { UPD.state = 'done'; route(); },
  updstart() { UPD.state = 'start'; route(); },
  updopen() { UPD.state = ''; UPD.fresh = true; route(); },
  async pvtickdo(el) {                 // Watered or Still moist for every ticked plant of this list (a pot kept in water gets its own kind)
    const wpl = el.closest('.wpl'), ticks = [...wpl.querySelectorAll('input[data-f=pvtick]:checked')]; if (!ticks.length) return;
    if (!(await needName())) return;
    const kinds = {}; ticks.forEach(t => { const k = el.dataset.kind === 'check' ? 'check' : t.dataset.kind; (kinds[k] = kinds[k] || []).push(t.dataset.code); });
    await guard(async () => { let ids = [];
      for (const [kind, codes] of Object.entries(kinds)) { const r = await api('POST', '/api/care', { plants: codes, kind }); ids = ids.concat((r && r.ids) || []); }
      careUndoToast(`${ticks.length} ${ticks.length === 1 ? 'plant' : 'plants'} marked as ${el.dataset.kind === 'check' ? 'still moist' : 'watered'}`, ids); await careRefresh(); });
  },
  pvtickclear(el) { const wpl = el.closest('.wpl'); wpl.querySelectorAll('input[data-f=pvtick]:checked').forEach(t => { t.checked = false; }); pvTickState(wpl); },
});
if (PV('updates')) addFeature({ name: 'updates', pages: { updates: { view: viewUpdates, nav: 'updates', section: 'plants', label: 'Updates from Claude', href: '#/updates', after: 'facts' } } });
