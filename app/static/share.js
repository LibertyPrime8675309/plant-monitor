/* Plant record: the plant-sitter sheet opened by link (1.49.0, PLAN.md step 4c): /share/<token>, served by plantdb/sitter.py.
   The person has no sign-in and may be outside the Tailnet (through Tailscale Funnel), so this page reaches only
   /share/<token>/data, /tick and the photos on the sheet. Ticks are saved as soon as a box is ticked. Plain JavaScript, no inline
   handlers (content policy). Display choices (text size, colours, contrast, colour vision, letter shapes, spacing, a page tint; 1.58.0) are kept in this browser only. */
(function () {
'use strict';
const { sheet, esc } = window.PlantSitterSheet;
const $ = id => document.getElementById(id);
const TOKEN = document.body.dataset.token, BASE = '/share/' + encodeURIComponent(TOKEN);
const SIZES = ['100', '115', '135', '160', '190'];
const r = document.documentElement;

// ---- display, the same attributes the app uses so the stylesheet applies
// 1.58.0: the same colours and reading choices as the app's Display settings (prefs.js), for a sitter who reads better with them
let P = { size: '135', theme: 'auto', contrast: 'auto', cvd: 'usual', font: 'atkinson', plain: '0', space: 'normal', tint: 'none' };   // a sheet read on a phone in a hurry: larger text than the app's default
try { Object.assign(P, JSON.parse(localStorage.getItem('plantdb.share') || '{}') || {}); } catch (e) { /* storage blocked */ }
const TONE = { cream: ['light', 'cream'], softdark: ['dark', 'soft'] }, OPTS = ['theme', 'contrast', 'cvd', 'font', 'space', 'tint'];
const mq = q => !!(window.matchMedia && matchMedia(q).matches);
const easyOn = () => P.font !== 'atkinson' && P.plain === '1' && P.space !== 'normal' && (P.theme === 'cream' || P.theme === 'softdark');
function apply() {
  r.setAttribute('data-size', P.size);
  r.setAttribute('data-contrast', P.contrast === 'auto' ? (mq('(prefers-contrast: more)') ? 'high' : 'normal') : P.contrast);
  const tone = TONE[P.theme], th = tone ? tone[0] : P.theme;
  if (th === 'auto') r.removeAttribute('data-theme'); else r.setAttribute('data-theme', th);
  if (tone) r.setAttribute('data-tone', tone[1]); else r.removeAttribute('data-tone');
  r.setAttribute('data-mode', th === 'auto' ? (mq('(prefers-color-scheme: dark)') ? 'dark' : 'light') : th);
  if (P.tint === 'none' || r.getAttribute('data-mode') === 'dark' || tone) r.removeAttribute('data-tint'); else r.setAttribute('data-tint', P.tint);
  if (P.cvd === 'usual') r.removeAttribute('data-cvd'); else r.setAttribute('data-cvd', P.cvd);
  r.setAttribute('data-font', P.font); r.setAttribute('data-plain', P.plain); r.setAttribute('data-space', P.space); r.setAttribute('data-lines', 'short');
  const rem = parseFloat(getComputedStyle(r).fontSize) || 16;
  r.setAttribute('data-narrow', (window.innerWidth / rem) < 58 ? '1' : '0');
  r.setAttribute('data-touch', mq('(hover: none) and (pointer: coarse)') ? '1' : '0');
  OPTS.forEach(k => { $('sh-o-' + k).value = P[k]; });
  $('sh-o-plain').checked = P.plain === '1';
  $('sh-easy').setAttribute('aria-pressed', easyOn() ? 'true' : 'false');
  $('sh-smaller').disabled = P.size === SIZES[0]; $('sh-larger').disabled = P.size === SIZES[SIZES.length - 1];
  try { localStorage.setItem('plantdb.share', JSON.stringify(P)); } catch (e) { /* this visit only */ }
}
$('sh-smaller').addEventListener('click', () => { P.size = SIZES[Math.max(0, SIZES.indexOf(P.size) - 1)]; apply(); });
$('sh-larger').addEventListener('click', () => { P.size = SIZES[Math.min(SIZES.length - 1, SIZES.indexOf(P.size) + 1)]; apply(); });
OPTS.forEach(k => $('sh-o-' + k).addEventListener('change', e => { P[k] = e.target.value; apply(); }));
$('sh-o-plain').addEventListener('change', e => { P.plain = e.target.checked ? '1' : '0'; apply(); });
// Easier reading, as in the app: Lexend, one plain font, roomy spacing and Cream paper (Soft dark on a dark page); pressed again, back as it was
$('sh-easy').addEventListener('click', () => {
  if (easyOn() && P.easyprev) { Object.assign(P, P.easyprev); delete P.easyprev; }
  else { P.easyprev = { font: P.font, plain: P.plain, space: P.space, theme: P.theme };
    Object.assign(P, { font: 'lexend', plain: '1', space: P.space === 'widest' ? 'widest' : 'roomy', theme: r.getAttribute('data-mode') === 'dark' ? 'softdark' : 'cream' }); }
  apply();
});
$('sh-print').addEventListener('click', () => window.print());
if (window.matchMedia) ['(prefers-color-scheme: dark)', '(prefers-contrast: more)'].forEach(q => { const m = matchMedia(q); if (m.addEventListener) m.addEventListener('change', apply); });
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
