/* Plant record front end: cuttings and new plants (prototype, proto/cuttings). One of the files loaded in order by index.html
   (js/manifest.json); they share one scope. Plain JavaScript, no inline handlers (the server's content policy forbids them). */
'use strict';

// ---------- cuttings ----------
// Cuttings, divisions, pups and seeds taken from your plants, from the day you take them until they are potted up (or given away,
// or did not take). The page #/cuttings (in the Today row, after Repotting) lists them; Today gets "Cuttings to look at" when a
// batch is due its weekly look; a plant's own page gets a line under its care buttons with "Take cuttings".
const cutPl = (n, one, many) => `${n} ${n === 1 ? one : many}`;
const CUT_ONE = { 'Stem cuttings': 'stem cutting', 'Leaf cuttings': 'leaf cutting', Division: 'division', 'Offsets or pups': 'offset or pup', 'Air layering': 'air layer', Seed: 'seed' };
const CUT_MANY = { Division: 'divisions', 'Air layering': 'air layers', Seed: 'seeds' };
function cutWhat(x) {                    // "3 stem cuttings in water"
  const n = x.how_many, m = n === 1 ? (CUT_ONE[x.method] || x.method.toLowerCase()) : (CUT_MANY[x.method] || x.method.toLowerCase());
  return `${n} ${m}${x.medium && x.medium !== 'Still on the plant' ? ' in ' + x.medium.toLowerCase() : x.medium ? ', still on the plant' : ''}`;
}
const cutCap = s => s.charAt(0).toUpperCase() + s.slice(1);
function cutAgo(d) { const n = daysBetween(d, todayStr()); return n === 0 ? 'today' : n === 1 ? 'yesterday' : `${relDay(d)}, ${n} days ago`; }
function cutWords(x) {
  const bits = [`${cutCap(cutWhat(x))}, taken ${cutAgo(x.started_on)}.`];
  const seed = x.method === 'Seed';           // seeds come up rather than root
  if (x.stage === 'rooting') bits.push(x.look_due ? (seed ? 'Look for seedlings today.' : 'Look for roots today.') : `${seed ? 'Not up yet' : 'Still rooting'}. Next look ${relDay(x.next_look)}.`);
  else if (x.stage === 'rooted') bits.push(`${seed ? 'Seedlings up' : 'Has roots'} since ${relDay(x.stage_on)}${x.rooted_after != null ? ` (after ${cutPl(x.rooted_after, 'day', 'days')})` : ''}.`
    + (x.look_due ? ' Ready to pot up once the roots are 1 to 2 inches long?' : ` Next look ${relDay(x.next_look)}.`));
  else bits.push(`${x.stage_word}${x.stage === 'given' && x.given_to ? ' to ' + x.given_to : ''}, ${relDay(x.stage_on)}.`);
  if (x.stage === 'rooting' && x.usual) bits.push(x.usual);
  if (x.notes) bits.push('Note: ' + x.notes);
  if (x.archived) bits.push('(The plant it came from is archived.)');
  return bits.join(' ');
}
const cutRow = x => ({ code: x.plant, common_name: 'From ' + x.name, photo: x.photo });
function cutBtns(x) {
  const lab = ` for the ${cutWhat(x)} from ${x.name}`;
  const b = (act, label, extra, cls) => html`<button class="btn small${cls ? ' ' + cls : ''}" type="button" data-act="${act}" data-id="${x.id}" ${extra ? raw(extra) : ''} aria-label="${label + lab}">${label}</button>`;
  if (x.stage === 'rooting' && x.method === 'Seed') return html`${b('cutstage', 'Seedlings are up', 'data-stage="rooted"')}${b('cutlook', 'Nothing up yet', '', 'ghost')}${b('cutedit', 'Change', '', 'ghost')}`;
  if (x.stage === 'rooting') return html`${b('cutstage', 'Has roots', 'data-stage="rooted"')}${b('cutlook', 'No roots yet', '', 'ghost')}${b('cutedit', 'Change', '', 'ghost')}`;
  if (x.stage === 'rooted') return html`${b('cutstage', 'Potted up', 'data-stage="potted"')}${b('cutlook', 'Not ready yet', '', 'ghost')}${b('cutedit', 'Change', '', 'ghost')}`;
  return b('cutedit', 'Change', '', 'ghost');
}
const cutList = (L, empty) => L.length ? html`<ul class="jobs cut-list">${L.map(x => html`${jobRow(cutRow(x), cutWords(x), cutBtns(x))}`)}</ul>` : html`<p class="muted">${empty}</p>`;
async function viewCuttings() {
  const R = cutKeep(await api('GET', '/api/cuttings'));
  const L = R.cuttings, due = L.filter(x => x.look_due);
  const rooting = L.filter(x => x.stage === 'rooting' && !x.look_due), rooted = L.filter(x => x.stage === 'rooted' && !x.look_due), done = L.filter(x => !x.active);
  const C = R.counts, active = C.rooting + C.rooted;
  const line = active ? `${cutPl(active, 'batch', 'batches')} in progress (${cutPl(C.pieces, 'piece', 'pieces')}): ${C.rooting} rooting, ${C.rooted} with roots.` : 'No cuttings in progress.';
  return {
    title: 'Cuttings',
    after: () => navMark('cuttings'),
    html: html`<h1>Cuttings</h1>
    <p class="muted">Keep track of cuttings, divisions, pups and seeds from your plants, from the day you take them until they are potted up. Each batch comes up on Today once a week, so you remember to look for roots.</p>
    <div class="verdict-box" role="status"><p><strong>${line}</strong>${due.length ? ` ${cutPl(due.length, 'batch is', 'batches are')} due a look today.` : ''}</p></div>
    <p class="noprint"><button class="btn" type="button" data-act="cutadd">Take cuttings</button></p>
    <section class="blk" id="cut-due"><h2>Look at these today (${due.length})</h2>${cutList(due, 'Nothing is due a look today.')}</section>
    <section class="blk" id="cut-rooting"><h2>Still rooting (${rooting.length})</h2>${cutList(rooting, 'No other cuttings are rooting.')}</section>
    <section class="blk" id="cut-rooted"><h2>Has roots, waiting for a pot (${rooted.length})</h2>${cutList(rooted, 'No other cuttings are waiting for a pot.')}</section>
    <section class="blk" id="cut-done"><h2>Finished in the last ${R.done_days} days (${done.length})</h2>
      <p class="hint">Potted up, given away, or did not take. Change one to set its stage back, or to remove it from the record.</p>${cutList(done, 'Nothing finished lately.')}</section>
    <section class="blk" id="cut-tips"><h2>Tips for rooting cuttings</h2>
      <ul class="rp-list"><li>Take a piece 4 to 6 inches long with at least one node (the bump where a leaf joins the stem). Roots grow from the node.</li>
        <li>Take off the lowest leaves so no leaf sits in the water or mix.</li>
        <li>Keep them warm and in bright light, out of direct sun.</li>
        <li>In water: change the water once a week. Pot them up when the roots are 1 to 2 inches long.</li>
        <li>In mix or moss: keep it damp, not wet. A gentle tug that meets resistance means roots.</li></ul></section>`,
  };
}
async function cutAfterChange(id) {
  if (document.getElementById('care-plant')) {
    await loadCarePlant();
    const b = document.querySelector('#cut-plant button') || document.getElementById('cut-plant');
    if (b) { if (b.id === 'cut-plant') b.setAttribute('tabindex', '-1'); b.focus({ preventScroll: true }); }
    return;
  }
  const y = window.scrollY; ROUTE_FRESH = true; await route(); window.scrollTo(0, y);
  const f = (id && document.querySelector(`button[data-act][data-id="${id}"]`)) || document.querySelector('#cut-due .job button, #today-cut .job button') || document.querySelector('main h1');
  if (f) f.focus({ preventScroll: true });
}
// One window to take cuttings (code: from that plant; none: choose the plant) or to change a batch (x)
async function cutDialog(code, name, x) {
  if (!(await needName())) return;
  const R = await api('GET', '/api/cuttings' + (code ? '?plant=' + enc(code) : ''));
  let plants = [];
  if (!code && !x) plants = (await api('GET', '/api/plants')).filter(p => p.status === 'active').sort((a, b) => a.common_name.localeCompare(b.common_name));
  const v = x || { method: 'Stem cuttings', medium: '', how_many: 1, started_on: todayStr(), notes: '', stage: 'rooting', given_to: '' };
  const sel = (a, b) => a === b ? raw('selected') : '';
  const r = await modal(html`<form method="dialog" class="cut-dlg"><h2>${x ? `Change cuttings from ${x.name}` : code ? `Take cuttings from ${name}` : 'Take cuttings'}</h2>
    ${plants.length ? html`<label class="f">From which plant<select name="plant" required><option value="">Choose a plant</option>
      ${plants.map(p => html`<option value="${p.code}">${p.common_name} (${p.code})</option>`)}</select></label>` : ''}
    <label class="f">How<select name="method">${R.methods.map(m => html`<option ${sel(m, v.method)}>${m}</option>`)}</select></label>
    <label class="f">Rooting in<select name="medium"><option value="" ${sel('', v.medium)}>Not said</option>${R.media.map(m => html`<option ${sel(m, v.medium)}>${m}</option>`)}</select></label>
    <label class="f">How many pieces<input type="number" name="how_many" min="1" max="500" inputmode="numeric" value="${v.how_many}"></label>
    <label class="f">Taken on<input type="date" name="started_on" max="${todayStr()}" value="${v.started_on}"></label>
    ${x ? html`<label class="f">Where it is up to<select name="stage">${Object.entries(R.stages).map(([k, l]) => html`<option value="${k}" ${sel(k, v.stage)}>${l}</option>`)}</select></label>
      <label class="f">Given to (only for "Given away")<input type="text" name="given_to" maxlength="80" value="${v.given_to}"></label>` : ''}
    <label class="f">Note (optional)<textarea name="notes" rows="2" maxlength="300">${v.notes}</textarea></label>
    <div class="row"><button class="btn" value="ok">${x ? 'Save changes' : 'Save cuttings'}</button><button class="btn ghost" value="cancel">Cancel</button>
      ${x ? html`<button class="btn ghost danger" value="remove">Remove from the record</button>` : ''}</div></form>`);
  if (r !== 'ok' && r !== 'remove') return;
  const f = dlg.querySelector('form').elements;
  if (r === 'remove') {
    if (!(await confirmBox('Remove these cuttings from the record?', `The ${cutWhat(x)} from ${x.name}, taken ${relDay(x.started_on)}, are taken off the list. The audit log keeps a note of them.`, 'Remove', true))) return;
    await guard(async () => { await api('DELETE', '/api/cuttings/' + x.id); toast('Cuttings removed from the record'); await cutAfterChange(); });
    return;
  }
  const body = { method: f.method.value, medium: f.medium.value, how_many: +f.how_many.value || 1, started_on: f.started_on.value || todayStr(), notes: f.notes.value.trim() };
  if (x) Object.assign(body, { stage: f.stage.value, given_to: f.given_to.value.trim() });
  else body.plant = code || (f.plant && f.plant.value);
  if (!body.plant && !x) { toast('Choose the plant the cuttings came from.', true); return; }
  await guard(async () => {
    const res = x ? await api('PUT', '/api/cuttings/' + x.id, body) : await api('POST', '/api/cuttings', body);
    toast(x ? 'Cuttings changed' : `Saved: ${cutWhat(body)}. They come up on Today in a week for a look.`);
    await cutAfterChange(x ? x.id : res.id);
  });
}
async function cutFind(id) { const R = await api('GET', '/api/cuttings'); return R.cuttings.find(x => x.id === +id) || null; }
Object.assign(acts, {
  async cutadd(el) { await cutDialog(el.dataset.code, el.dataset.name); },
  async cutedit(el) {
    let x = (CUT_LAST || []).find(c => c.id === +el.dataset.id);
    if (!x) x = await guard(() => cutFind(el.dataset.id));
    if (x) await cutDialog(null, null, x);
  },
  async cutstage(el) {
    if (!(await needName())) return;
    const st = el.dataset.stage, id = el.dataset.id;
    await guard(async () => { await api('PUT', '/api/cuttings/' + id, { stage: st }); toast(st === 'rooted' ? 'Has roots: good news. Next look in a week.' : 'Potted up'); await cutAfterChange(id); });
  },
  async cutlook(el) {
    if (!(await needName())) return;
    const id = el.dataset.id;
    await guard(async () => { await api('PUT', '/api/cuttings/' + id, { checked: true }); toast('Noted. Next look in a week.'); await cutAfterChange(id); });
  },
});
let CUT_LAST = null;                       // the batches last drawn, so Change opens without asking the server again
const cutKeep = R => { CUT_LAST = R.cuttings; return R; };

// What this module adds (features.js): the page in the Today row after Repotting (one more page in the Care row makes it wrap to a
// second line on a laptop), a block on Today when a batch is due its weekly look, and a line under a plant's care buttons.
addFeature({
  name: 'cuttings',
  pages: { cuttings: { view: viewCuttings, nav: 'cuttings', section: 'today', label: 'Cuttings', href: '#/cuttings', after: 'repotting' } },
  today: {
    id: 'today-cut', order: 67,                                    // after turn the pots (65), before repotting (68)
    load: async () => { const R = cutKeep(await api('GET', '/api/cuttings')); return R.counts.due ? R : null; },
    jump: R => `Cuttings (${R.counts.due})`,
    html: R => html`<section class="blk" id="today-cut"><h2>Cuttings to look at (${R.counts.due})</h2>
      ${cutList(R.cuttings.filter(x => x.look_due), '')}<p><a class="btn small ghost" href="#/cuttings">All cuttings</a></p></section>`,
  },
  adds: {
    id: 'cut-plant', care: true,
    match: parts => parts[0] === 'plant' && parts[1] && parts[2] !== 'edit',
    anchor: main => { const b = main.querySelector('.quick-btns'); return b && b.parentElement; }, where: 'beforeend',
    load: async parts => {
      if (!CUR || CUR.p.code !== parts[1] || CUR.p.status !== 'active') return null;
      const R = cutKeep(await api('GET', '/api/cuttings?plant=' + enc(parts[1])));     // offline with nothing saved: leave it out
      return { R, code: parts[1], name: CUR.p.common_name };
    },
    html: ({ R, code, name }) => {
      const on = R.cuttings.filter(x => x.active);
      const words = on.length ? on.map(x => `${cutWhat(x)}, ${x.stage === 'rooting' ? (x.method === 'Seed' ? 'not up yet' : 'rooting') : x.method === 'Seed' ? 'seedlings up' : 'with roots'} (taken ${relDay(x.started_on)})`).join('; ') + '.'
        : R.cuttings.length ? 'none in progress.' : 'none recorded.';
      return html`<p class="hint cut-plant" id="cut-plant">Cuttings: ${words}
        <button class="btn small ghost" type="button" data-act="cutadd" data-code="${code}" data-name="${name}" aria-label="${'Take cuttings from ' + name}">Take cuttings</button>
        ${R.cuttings.length ? html`<a href="#/cuttings">All cuttings</a>` : ''}</p>`;
    },
  },
});
