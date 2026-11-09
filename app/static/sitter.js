/* Plant-sitter sheet (prototype, proto/sitter-sheet): /sitter.html
   A printable day-by-day plan of which plants to check for water while Ethan is away, from the same reminders as Today.
   A page of its own so the printout carries nothing but the sheet. Plain JavaScript, no inline handlers (content policy). */
(function () {
'use strict';
const { sheet, dayName, esc, iso, addDays } = window.PlantSitterSheet;        // 1.49.0: the sheet itself is in sitter-sheet.js, shared with the sheet by link
const enc = encodeURIComponent;
const $ = id => document.getElementById(id);
const KEY = 'plantdb.sitter';

let OPT = { from: '', to: '', group: '', photos: true, pageday: false, note: '' };     // 1.47.0: photos instead of a list at the end (Ethan, November 8)
try { Object.assign(OPT, JSON.parse(localStorage.getItem(KEY) || '{}') || {}); } catch (e) { /* storage blocked: defaults */ }
const saveOpt = () => { try { localStorage.setItem(KEY, JSON.stringify(OPT)); } catch (e) { /* this visit only */ } };

let PLACE = null;
try { PLACE = localStorage.getItem('plantdb.place') || null; } catch (e) { /* home place */ }
function headers(change, json) {
  const h = {}; if (PLACE) h['X-Place'] = PLACE; if (json) h['Content-Type'] = 'application/json';
  if (change) { let n = ''; try { n = (ME && ME.name) || localStorage.getItem('plantdb.editor') || ''; } catch (e) { /* none */ } h['X-Editor'] = n || 'Unknown'; }   // a change needs the name header (the CSRF guard)
  return h;
}
async function get(url, init) {
  let r;
  try { r = await fetch(url, Object.assign({ headers: headers(init && init.method && init.method !== 'GET', init && init.body) }, init || {})); } catch (e) { throw new Error('Cannot reach the plant server. Check that the container is running.'); }
  let d = null; try { d = await r.json(); } catch (e) { /* not json */ }
  if (!r.ok) throw new Error((d && (d.error || d.message)) || ('Request failed (' + r.status + ')'));
  return d;
}

let busy = 0;
async function load() {
  const my = ++busy, f = $('ps-opts');
  if (!OPT.from || !OPT.to) return;
  const q = `/api/sitter?from=${enc(OPT.from)}&to=${enc(OPT.to)}${OPT.group ? '&group=' + enc(OPT.group) : ''}`;
  let D;
  try { D = await get(q); } catch (e) {
    if (my !== busy) return;
    $('ps-count').textContent = '';
    $('ps-sheet').innerHTML = `<div class="notice bad" role="alert"><strong>Could not make the sheet</strong><p>${esc(e.message)}</p></div>`;
    return;
  }
  if (my !== busy) return;
  if (!D.plants.length) {
    $('ps-count').textContent = '';
    $('ps-sheet').innerHTML = '<p class="notice">There are no plants in this group, so there is nothing to print.</p>';
    return;
  }
  // 1.49.0: boxes the sitter ticked on the shared sheet for these days show on the printout too
  let ticks = new Set();
  try { const T = await get(`/api/sitter/ticks?from=${enc(OPT.from)}&to=${enc(OPT.to)}${OPT.group ? '&group=' + enc(OPT.group) : ''}`); ticks = new Set((T.ticks || []).map(t => `${t.day}|${t.plant_code}|${t.kind}`)); } catch (e) { /* no link yet */ }
  if (my !== busy) return;
  const S = sheet(D, OPT, { ticks });
  const before = D.before.length ? `<div class="notice ps-before noprint" role="note"><h2 class="ps-before-h">Before you go (not printed)</h2>
    <p>${D.before.length === 1 ? 'This plant is' : `These ${D.before.length} plants are`} due for water before ${esc(dayName(D.start))}, or ${D.before.length === 1 ? 'has' : 'have'} no watering logged yet. Check ${D.before.length === 1 ? 'it' : 'them'} before you leave. The days on the sheet assume you do, ${addDays(D.start, -1) === D.today ? 'today' : 'on ' + esc(dayName(addDays(D.start, -1)))}.</p>
    <ul class="ps-before-list">${D.before.map(c => { const p = D.plants.find(x => x.code === c); return `<li><a href="/#/plant/${enc(c)}">${esc(p.name)} <span class="ps-code">${esc(c)}</span></a></li>`; }).join('')}</ul></div>` : '';
  $('ps-sheet').innerHTML = before + S.html;
  const nd = D.days.length;
  $('ps-count').textContent = `${D.plants.length} ${D.plants.length === 1 ? 'plant' : 'plants'}, ${S.jobs} ${S.jobs === 1 ? 'check' : 'checks'} over ${nd} ${nd === 1 ? 'day' : 'days'}.`;
}

function paintOpts() {
  const f = $('ps-opts');
  f.from.value = OPT.from; f.to.value = OPT.to; f.group.value = OPT.group;
  if (f.group.value !== OPT.group) { OPT.group = ''; f.group.value = ''; }      // the group was removed
  f.photos.checked = !!OPT.photos; f.pageday.checked = !!OPT.pageday; f.note.value = OPT.note || '';
}

async function start() {
  const today = iso(new Date());
  if (!OPT.from || OPT.from < today) { OPT.from = addDays(today, 1); OPT.to = addDays(today, 7); }      // old dates: start again from tomorrow
  if (!OPT.to || OPT.to < OPT.from) OPT.to = addDays(OPT.from, 6);
  const f = $('ps-opts');
  f.from.min = today; f.to.min = today;
  const hg = location.hash.match(/group=(\d+)/);                // opened from a group page
  if (hg) { OPT.group = hg[1]; const b = document.querySelector('.crumb a'); b.href = '/#/group/' + hg[1]; b.textContent = 'Back to the group'; }
  try {
    const G = await get('/api/groups');
    for (const g of G.groups || []) {
      const o = document.createElement('option'); o.value = String(g.id); o.textContent = `${g.name} (${g.count} ${g.count === 1 ? 'plant' : 'plants'})`;
      f.group.appendChild(o);
    }
  } catch (e) { /* groups are optional */ }
  paintOpts();
  await load();
}

let noteTimer = null;
$('ps-opts').addEventListener('change', e => {
  const i = e.target; if (!i.name) return;
  if (i.type === 'checkbox') OPT[i.name] = i.checked;
  else if (i.type === 'date') {
    if (!i.value) return;                                       // half-typed date
    OPT[i.name] = i.value;
    if (i.name === 'from' && OPT.to < OPT.from) { OPT.to = addDays(OPT.from, 6); $('ps-to').value = OPT.to; }
  } else OPT[i.name] = i.value;
  saveOpt(); load();
});
$('ps-note').addEventListener('input', () => {
  OPT.note = $('ps-note').value; saveOpt();
  clearTimeout(noteTimer); noteTimer = setTimeout(load, 400);
});
$('ps-opts').addEventListener('submit', e => e.preventDefault());
// 1.49.0: the sheet by link. Editors and the owner make a link for the chosen days (and group); the sitter opens it anywhere.
let ME = null;
async function shareStart() {
  try { ME = await get('/api/me'); } catch (e) { return; }
  if (!ME || ME.role === 'viewer') return;
  $('ps-share').hidden = false;
  await paintLinks();
}
const when = s => s ? new Date(s).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' }) : '';
async function paintLinks() {
  let L; try { L = await get('/api/sitter/shares'); } catch (e) { $('ps-share-msg').textContent = e.message; return; }
  $('ps-share-hint').hidden = !!L.public_base;
  const live = (L.shares || []).filter(x => x.live);
  $('ps-links').innerHTML = live.length ? `<ul class="ps-linklist">${live.map(x => `<li class="ps-linkrow" data-token="${esc(x.token)}">
      <div class="ps-linkwhat"><strong>${esc(dayName(x.from))} to ${esc(dayName(x.to))}</strong>${x.group ? ' (one group)' : ''}
        <span class="hint">${x.ticks ? `${x.ticks} ${x.ticks === 1 ? 'box' : 'boxes'} ticked` : 'Nothing ticked yet'}${x.last_seen ? `. Last opened ${esc(when(x.last_seen))}` : '. Not opened yet'}.</span></div>
      <label class="ps-field ps-wide"><span>${x.url ? 'Link to send' : 'Link (works on your home network only until the public address is saved)'}</span>
        <input type="text" class="ps-url" readonly value="${esc(x.url || x.local_url)}"></label>
      <p class="row"><button class="btn" type="button" data-share="copy">Copy the link</button>
        <a class="btn ghost" href="${esc(x.local_url)}" target="_blank" rel="noopener">Open it</a>
        <button class="btn ghost" type="button" data-share="stop">Take the link down</button></p></li>`).join('')}</ul>` : '';
}
$('ps-mklink').addEventListener('click', async () => {
  const m = $('ps-share-msg'); m.textContent = 'Making the link…';
  try {
    await get('/api/sitter/shares', { method: 'POST', body: JSON.stringify({ from: OPT.from, to: OPT.to, group: OPT.group || null, note: OPT.note || '', photos: !!OPT.photos }) });
    m.textContent = 'Link made. Copy it and send it to the sitter.';
    await paintLinks();
  } catch (e) { m.textContent = 'Could not make the link: ' + e.message; }
});
$('ps-links').addEventListener('click', async e => {
  const b = e.target.closest('[data-share]'); if (!b) return;
  const row = b.closest('.ps-linkrow'), tok = row.dataset.token, m = $('ps-share-msg');
  if (b.dataset.share === 'copy') {
    const i = row.querySelector('.ps-url'); i.select();
    try { await navigator.clipboard.writeText(i.value); m.textContent = 'Copied.'; } catch (err) { m.textContent = 'Could not copy. The link is selected: copy it yourself.'; }
  } else if (b.dataset.share === 'stop') {
    try { await get('/api/sitter/shares/' + enc(tok), { method: 'DELETE' }); m.textContent = 'The link is down. Anyone who opens it now sees that it was taken down.'; await paintLinks(); } catch (err) { m.textContent = err.message; }
  }
});
// 1.47.0: the app saved to an iPhone or iPad home screen (standalone) cannot print; a target=_blank link opens Safari, which can
const standalone = navigator.standalone === true || (window.matchMedia && matchMedia('(display-mode: standalone)').matches);
if (standalone) { $('ps-open').hidden = false; $('ps-print-note').hidden = false; $('ps-print').hidden = true; }
$('ps-open').addEventListener('click', () => { $('ps-open').href = location.pathname + location.hash; });
$('ps-print').addEventListener('click', () => window.print());
shareStart();
start().catch(e => { $('ps-sheet').innerHTML = `<div class="notice bad" role="alert"><strong>Could not make the sheet</strong><p>${esc(e.message)}</p></div>`; });
})();
