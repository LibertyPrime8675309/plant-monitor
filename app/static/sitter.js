/* Plant-sitter sheet (prototype, proto/sitter-sheet): /sitter.html
   A printable day-by-day plan of which plants to check for water while Ethan is away, from the same reminders as Today.
   A page of its own so the printout carries nothing but the sheet. Plain JavaScript, no inline handlers (content policy). */
(function () {
'use strict';
const ESC = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ESC[c]);
const enc = encodeURIComponent;
const $ = id => document.getElementById(id);
const KEY = 'plantdb.sitter';

let OPT = { from: '', to: '', group: '', photos: true, list: true, note: '' };
try { Object.assign(OPT, JSON.parse(localStorage.getItem(KEY) || '{}') || {}); } catch (e) { /* storage blocked: defaults */ }
const saveOpt = () => { try { localStorage.setItem(KEY, JSON.stringify(OPT)); } catch (e) { /* this visit only */ } };

let PLACE = null;
try { PLACE = localStorage.getItem('plantdb.place') || null; } catch (e) { /* home place */ }
async function get(url) {
  let r;
  try { r = await fetch(url, { headers: PLACE ? { 'X-Place': PLACE } : {} }); } catch (e) { throw new Error('Cannot reach the plant server. Check that the container is running.'); }
  let d = null; try { d = await r.json(); } catch (e) { /* not json */ }
  if (!r.ok) throw new Error((d && (d.error || d.message)) || ('Request failed (' + r.status + ')'));
  return d;
}

// dates as local days: '2026-11-07' -> 'Saturday, November 7'
const asDate = s => { const [y, m, d] = s.split('-').map(Number); return new Date(y, m - 1, d); };
const iso = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
const addDays = (s, n) => { const d = asDate(s); d.setDate(d.getDate() + n); return iso(d); };
const dayName = s => asDate(s).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
const dayShort = s => asDate(s).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });

// the first two sentences of a note
function short(s) {
  const t = String(s || '').replace(/\s+/g, ' ').trim();
  const m = t.match(/^(.+?[.!?])(\s+.+?[.!?])?(?=\s+[A-Z0-9"(]|$)/);
  return m ? m[0] : t;
}
const where = p => p.spot && p.spot.toLowerCase().startsWith(p.site.toLowerCase()) ? p.spot : [p.site, p.spot].filter(Boolean).join(', ');
const tick = '<span class="ps-box" aria-hidden="true"></span>';

function sheet(D) {
  const by = Object.fromEntries(D.plants.map(p => [p.code, p]));
  const outside = D.plants.some(p => p.open_sky);
  const span = D.start === D.end ? dayName(D.start) : `${dayName(D.start)} to ${dayName(D.end)}`;
  const jobs = D.days.reduce((n, d) => n + d.plants.length, 0);
  const item = (code, extra) => { const p = by[code];
    return `<li>${tick}<span class="ps-what"><strong>${esc(p.name)}</strong> <span class="ps-code">${esc(p.code)}</span><span class="ps-where">${esc(where(p))}${extra ? '. ' + esc(extra) : ''}</span></span></li>`; };
  const intro = `<ul class="ps-how">
      <li>On each day below, check the plants listed. The plant list at the end says where each one is and how to tell if it needs water.</li>
      <li>Water only if it needs it. A plant that is still moist can wait.</li>
      ${outside ? `<li>If at least ${D.rain_counts_in} inch of rain fell, the plants that are <strong>Outdoors</strong> (not on the porch) do not need watering that day.</li>` : ''}
      <li>Tick the box when it is done.</li></ul>`;
  const beyond = D.forecast_to && D.end > D.forecast_to;
  // one line per plant (not per night), so a cold spell does not fill pages: the nights it is at risk and its limit
  const coldBy = {};
  for (const n of D.nights) for (const x of n.plants) (coldBy[x.code] = coldBy[x.code] || { x, nights: [] }).nights.push(n);
  const coldCodes = D.plants.map(p => p.code).filter(c => coldBy[c]);
  const cold = coldCodes.length ? `<section class="ps-sec ps-cold" aria-labelledby="ps-cold-h"><h3 id="ps-cold-h">Cold nights in the forecast</h3>
      <p>Before dark on the nights listed, move these plants inside or cover them.</p>
      <ul class="ps-list">${coldCodes.map(c => { const { x, nights } = coldBy[c];
        return item(c, `${nights.map(n => `${dayShort(n.date)} (${n.low}°F)`).join(', ')}. ${x.lethal != null && Math.min(...nights.map(n => n.low)) < x.lethal ? `Killed below ${x.lethal}°F` : `Harmed below ${x.damage}°F`}`); }).join('')}</ul>
      ${beyond ? `<p class="ps-note">The forecast only goes as far as ${esc(dayName(D.forecast_to))}. Check the weather for later nights.</p>` : ''}</section>`
    : beyond || !D.forecast_to ? `<section class="ps-sec ps-cold" aria-labelledby="ps-cold-h"><h3 id="ps-cold-h">Cold nights</h3>
      <p>${D.forecast_to && D.start <= D.forecast_to ? `No cold nights for these plants in the forecast up to ${esc(dayName(D.forecast_to))}.` : 'There is no forecast for these days yet.'}
      Check the weather. If a night near freezing is forecast, ask me what to bring in.</p></section>` : '';
  const days = `<section class="ps-sec" aria-labelledby="ps-days-h"><h3 id="ps-days-h">Day by day</h3>
    ${D.days.map(d => `<div class="ps-day"><h4>${esc(dayName(d.date))}${d.high != null ? `<span class="ps-wx">Forecast: high ${esc(d.high)}°F, low ${esc(d.low)}°F</span>` : ''}</h4>
      ${d.plants.length ? `<ul class="ps-list">${d.plants.map(c => item(c)).join('')}</ul>` : '<p class="ps-none">Nothing to check today.</p>'}</div>`).join('')}</section>`;
  const list = OPT.list ? `<section class="ps-sec ps-plants" aria-labelledby="ps-pl-h"><h3 id="ps-pl-h">The plants</h3>
    <ul class="ps-cards">${D.plants.map(p => `<li class="ps-card">
      ${OPT.photos && p.photo ? `<img class="ps-photo" src="/photos/${enc(p.photo)}" alt="Photo of ${esc(p.name)}">` : ''}
      <div class="ps-card-txt"><p class="ps-card-h"><strong>${esc(p.name)}</strong> <span class="ps-code">${esc(p.code)}</span></p>
        <p><strong>Where:</strong> ${esc(where(p))}</p>
        <p><strong>Check:</strong> about every ${esc(p.every)} ${p.every === 1 ? 'day' : 'days'}${p.visits.length ? ` (${p.visits.map(dayShort).map(esc).join('; ')})` : ' (not needed during these dates)'}</p>
        ${p.water_notes ? `<p><strong>How to water:</strong> ${esc(short(p.water_notes))}</p>` : ''}
        ${p.damage_below != null && p.site !== 'Indoors' ? `<p><strong>Cold:</strong> harmed below ${esc(p.damage_below)}°F</p>` : ''}
      </div></li>`).join('')}</ul></section>` : '';
  return { jobs, html: `<article class="ps-doc" aria-labelledby="ps-title">
    <header class="ps-head"><h2 id="ps-title">Looking after the plants</h2><p class="ps-span">${esc(span)}</p>
      ${OPT.note.trim() ? `<p class="ps-msg">${esc(OPT.note.trim())}</p>` : ''}${intro}</header>
    ${cold}${days}${list}
    <p class="ps-printed">Made ${esc(new Date().toLocaleDateString('en-US', { dateStyle: 'long' }))} from Plant record${D.group ? `, group "${esc(D.group.name)}"` : ''}.</p></article>` };
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
  f.querySelector('[name=photos]').disabled = !OPT.list;
  if (!D.plants.length) {
    $('ps-count').textContent = '';
    $('ps-sheet').innerHTML = '<p class="notice">There are no plants in this group, so there is nothing to print.</p>';
    return;
  }
  const S = sheet(D);
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
  f.photos.checked = !!OPT.photos; f.list.checked = !!OPT.list; f.note.value = OPT.note || '';
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
$('ps-print').addEventListener('click', () => window.print());
start().catch(e => { $('ps-sheet').innerHTML = `<div class="notice bad" role="alert"><strong>Could not make the sheet</strong><p>${esc(e.message)}</p></div>`; });
})();
