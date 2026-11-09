/* Plant record: the plant-sitter sheet opened by link (1.49.0, PLAN.md step 4c): /share/<token>, served by plantdb/sitter.py.
   The person has no sign-in and may be outside the Tailnet (through Tailscale Funnel), so this page reaches only
   /share/<token>/data, /tick and the photos on the sheet. Ticks are saved as soon as a box is ticked. Plain JavaScript, no inline
   handlers (content policy). Display choices (text size, dark, high contrast) are kept in this browser only. */
(function () {
'use strict';
const { sheet, esc } = window.PlantSitterSheet;
const $ = id => document.getElementById(id);
const TOKEN = document.body.dataset.token, BASE = '/share/' + encodeURIComponent(TOKEN);
const SIZES = ['100', '115', '135', '160', '190'];
const r = document.documentElement;

// ---- display, the same attributes the app uses so the stylesheet applies
let P = { size: '135', theme: 'auto', contrast: 'normal' };          // a sheet read on a phone in a hurry: larger text than the app's default
try { Object.assign(P, JSON.parse(localStorage.getItem('plantdb.share') || '{}') || {}); } catch (e) { /* storage blocked */ }
function apply() {
  r.setAttribute('data-size', P.size); r.setAttribute('data-contrast', P.contrast);
  if (P.theme === 'auto') r.removeAttribute('data-theme'); else r.setAttribute('data-theme', P.theme);
  const rem = parseFloat(getComputedStyle(r).fontSize) || 16;
  r.setAttribute('data-narrow', (window.innerWidth / rem) < 58 ? '1' : '0');
  r.setAttribute('data-touch', window.matchMedia && matchMedia('(hover: none) and (pointer: coarse)').matches ? '1' : '0');
  const dark = P.theme === 'dark' || (P.theme === 'auto' && window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches);
  $('sh-theme').setAttribute('aria-pressed', dark ? 'true' : 'false'); $('sh-theme').textContent = dark ? 'Light' : 'Dark';
  $('sh-contrast').setAttribute('aria-pressed', P.contrast === 'high' ? 'true' : 'false');
  $('sh-smaller').disabled = P.size === SIZES[0]; $('sh-larger').disabled = P.size === SIZES[SIZES.length - 1];
  try { localStorage.setItem('plantdb.share', JSON.stringify(P)); } catch (e) { /* this visit only */ }
}
$('sh-smaller').addEventListener('click', () => { P.size = SIZES[Math.max(0, SIZES.indexOf(P.size) - 1)]; apply(); });
$('sh-larger').addEventListener('click', () => { P.size = SIZES[Math.min(SIZES.length - 1, SIZES.indexOf(P.size) + 1)]; apply(); });
$('sh-theme').addEventListener('click', () => { P.theme = $('sh-theme').getAttribute('aria-pressed') === 'true' ? 'light' : 'dark'; apply(); });
$('sh-contrast').addEventListener('click', () => { P.contrast = P.contrast === 'high' ? 'normal' : 'high'; apply(); });
$('sh-print').addEventListener('click', () => window.print());
window.addEventListener('resize', apply);
apply();

// ---- the sheet
async function get(url, init) {
  let res;
  try { res = await fetch(url, init); } catch (e) { throw new Error('No connection. Check the phone has a signal, then pull down to try again.'); }
  let d = null; try { d = await res.json(); } catch (e) { /* not json */ }
  if (!res.ok) { const err = new Error((d && (d.error || d.message)) || ('Request failed (' + res.status + ')')); err.status = res.status; throw err; }
  return d;
}
const fail = (title, msg) => { $('ps-sheet').innerHTML = `<div class="notice bad" role="alert"><strong>${esc(title)}</strong><p>${esc(msg)}</p></div>`; };

let D = null;
async function load() {
  try { D = await get(BASE + '/data'); } catch (e) {
    if (e.status === 410) fail('This sheet is no longer available', e.message);
    else if (e.status === 404) fail('This link does not work', e.message);
    else fail('Could not load the sheet', e.message);
    return;
  }
  document.title = `Looking after ${esc(D.owner)}'s plants | Plant record`;
  const ticks = new Set((D.ticks || []).map(t => `${t.day}|${t.plant_code}|${t.kind}`));
  const S = sheet(D, { photos: D.photos, pageday: false, note: D.note || '' }, { ticks, tickable: true, units: D.units, photo: f => f });
  $('ps-sheet').innerHTML = S.html;
  $('sh-foot').hidden = false;
  const n = D.days.length;
  $('sh-saved').textContent = `${D.plants.length} ${D.plants.length === 1 ? 'plant' : 'plants'}, ${S.jobs} ${S.jobs === 1 ? 'check' : 'checks'} over ${n} ${n === 1 ? 'day' : 'days'}.`;
}

// a tick is saved at once; if it cannot be, the box goes back and says so
$('ps-sheet').addEventListener('change', async e => {
  const b = e.target; if (!b.classList.contains('ps-tick')) return;
  const li = b.closest('li'), on = b.checked, msg = $('sh-saved');
  b.disabled = true; msg.textContent = 'Saving…';
  try {
    await get(BASE + '/tick', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ day: b.dataset.day, plant: b.dataset.plant, kind: b.dataset.kind, on }) });
    li.classList.toggle('ps-done', on);
    msg.textContent = on ? 'Saved.' : 'Tick removed.';
  } catch (err) {
    b.checked = !on;
    msg.textContent = (err.status === 410 ? 'This sheet is no longer available. ' : 'Not saved. ') + err.message;
  }
  b.disabled = false;
});
load();
})();
