/* Plant record: the plant-sitter sheet itself (1.49.0, PLAN.md step 4c), shared by sitter.html (the page in the app) and
   share.html (the sheet someone outside the Tailnet opens by link, through /share/<token>). Plain JavaScript, no inline handlers.
   Sets window.PlantSitterSheet = { sheet, dayName, dayShort, esc, iso, addDays }.
   sheet(D, OPT, X): D is the API's sheet data; OPT = { photos, pageday, note }; X = { ticks: Set of "day|code|kind", tickable: true
   to draw real check boxes that the page saves (the shared sheet), units: {temp, rain} to use instead of this browser's choice,
   photo: f => url for the plant photos (the shared sheet reaches them through its own path) }. */
(function () {
'use strict';
const ESC = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ESC[c]);
// dates as local days: '2026-11-07' -> 'Saturday, November 7'
const asDate = s => { const [y, m, d] = s.split('-').map(Number); return new Date(y, m - 1, d); };
const iso = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
const addDays = (s, n) => { const d = asDate(s); d.setDate(d.getDate() + n); return iso(d); };
const dayName = s => asDate(s).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
const dayShort = s => asDate(s).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });

// the first sentence of a note
function short(s) {
  const t = String(s || '').replace(/\s+/g, ' ').trim();
  const m = t.match(/^.+?[.!?](?=\s+[A-Z0-9"(]|$)/);
  return m ? m[0] : t;
}
const where = p => p.spot && p.spot.toLowerCase().startsWith(p.site.toLowerCase()) ? p.spot : [p.site, p.spot].filter(Boolean).join(', ');

// 1.47.0: temperatures and rain in the units the person chose in Display (localStorage plantdb.units; core.js has the full version)
const UREG = { us: { temp: 'f', rain: 'in' }, ca: { temp: 'c', rain: 'mm' }, metric: { temp: 'c', rain: 'mm' } };
function unitsHere() {
  try { const u = JSON.parse(localStorage.getItem('plantdb.units') || '{}') || {}, b = UREG[u.region] || UREG.us; return { temp: u.temp || b.temp, rain: u.rain || b.rain }; } catch (e) { return { temp: 'f', rain: 'in' }; }
}

function sheet(D, OPT, X) {
  X = X || {}; OPT = OPT || { photos: true, pageday: false, note: '' };
  const U = X.units || unitsHere();
  const tF = f => f == null ? '' : U.temp === 'c' ? `${Number.isInteger(+f) ? Math.round((f - 32) * 5 / 9) : Math.round((f - 32) * 50 / 9) / 10}°C` : `${f}°F`;
  const rainF = x => U.rain === 'mm' ? `${Math.round(x * 25.4)} mm` : `${x} inch`;
  const thumb = X.photo || (f => f ? `/thumbs/${encodeURIComponent(f)}` : '');
  const ticks = X.ticks || new Set();
  // the box: on the shared sheet a real check box that saves; in the app a printed box, filled in where the sitter ticked it
  const tick = (day, code, kind) => { const on = ticks.has(`${day}|${code}|${kind}`);
    return X.tickable ? `<input type="checkbox" class="ps-tick" data-day="${esc(day)}" data-plant="${esc(code)}" data-kind="${kind}" ${on ? 'checked' : ''} aria-label="${kind === 'cold' ? 'Moved or covered' : 'Checked'}: ${esc(by[code].name)} ${esc(code)}">`
      : `<span class="ps-box ${on ? 'ps-ticked' : ''}" aria-hidden="true">${on ? '✓' : ''}</span>${on ? '<span class="sr">Ticked by the sitter.</span>' : ''}`; };
  const by = Object.fromEntries(D.plants.map(p => [p.code, p]));
  const outside = D.plants.some(p => p.open_sky);
  const span = D.start === D.end ? dayName(D.start) : `${dayName(D.start)} to ${dayName(D.end)}`;
  const jobs = D.days.reduce((n, d) => n + d.plants.length, 0);
  // one entry per plant per day: its photo (so the sitter knows which pot), where it is, and how to tell if it needs water
  const item = (code, extra, day, kind) => { const p = by[code], how = p.action_words || (p.water_notes ? short(p.water_notes) : '');      // 1.56.0: semi-hydro and water-only pots say what to do
    return `<li${ticks.has(`${day || ''}|${code}|${kind || 'water'}`) ? ' class="ps-done"' : ''}>${tick(day || '', code, kind || 'water')}${OPT.photos && p.photo ? `<img class="ps-pic" src="${thumb(p.photo)}" alt="" loading="lazy">` : OPT.photos ? '<span class="ps-pic ps-nopic" aria-hidden="true"></span>' : ''}<span class="ps-what"><strong>${esc(p.name)}</strong> <span class="ps-code">${esc(p.code)}</span><span class="ps-where">${esc(where(p))}${extra ? '. ' + esc(extra) : ''}</span>${how && !extra ? `<span class="ps-how1">${esc(how)}</span>` : ''}</span></li>`; };
  const intro = `<ul class="ps-how">
      <li>On each day below, check the plants listed. Each line says where the plant is and how to tell if it needs water${OPT.photos ? ', with its photo' : ''}.</li>
      <li>Water only if it needs it. A plant that is still moist can wait.</li>
      ${outside ? `<li>If at least ${rainF(D.rain_counts_in)} of rain fell, the plants that are <strong>Outdoors</strong> (not on the porch) do not need watering that day.</li>` : ''}
      <li>Tick the box when it is done.</li></ul>`;
  const beyond = D.forecast_to && D.end > D.forecast_to;
  // one line per plant (not per night), so a cold spell does not fill pages: the nights it is at risk and its limit
  const coldBy = {};
  for (const n of D.nights) for (const x of n.plants) (coldBy[x.code] = coldBy[x.code] || { x, nights: [] }).nights.push(n);
  const coldCodes = D.plants.map(p => p.code).filter(c => coldBy[c]);
  const cold = coldCodes.length ? `<section class="ps-sec ps-cold" aria-labelledby="ps-cold-h"><h3 id="ps-cold-h">Cold nights in the forecast</h3>
      <p>Before dark on the nights listed, move these plants inside or cover them.</p>
      <ul class="ps-list">${coldCodes.map(c => { const { x, nights } = coldBy[c];
        return item(c, `${nights.map(n => `${dayShort(n.date)} (${tF(n.low)})`).join(', ')}. ${x.lethal != null && Math.min(...nights.map(n => n.low)) < x.lethal ? `Killed below ${tF(x.lethal)}` : `Harmed below ${tF(x.damage)}`}`, nights[0].date, 'cold'); }).join('')}</ul>
      ${beyond ? `<p class="ps-note">The forecast only goes as far as ${esc(dayName(D.forecast_to))}. Check the weather for later nights.</p>` : ''}</section>`
    : beyond || !D.forecast_to ? `<section class="ps-sec ps-cold" aria-labelledby="ps-cold-h"><h3 id="ps-cold-h">Cold nights</h3>
      <p>${D.forecast_to && D.start <= D.forecast_to ? `No cold nights for these plants in the forecast up to ${esc(dayName(D.forecast_to))}.` : 'There is no forecast for these days yet.'}
      Check the weather. If a night near freezing is forecast, ask me what to bring in.</p></section>` : '';
  const days = `<section class="ps-sec ps-days" aria-labelledby="ps-days-h"><h3 id="ps-days-h">Day by day</h3>
    ${D.days.map(d => `<div class="ps-day"><h4>${esc(dayName(d.date))}${d.high != null ? `<span class="ps-wx">Forecast: high ${tF(d.high)}, low ${tF(d.low)}</span>` : ''}</h4>
      ${d.plants.length ? `<ul class="ps-list">${d.plants.map(c => item(c, '', d.date, 'water')).join('')}</ul>` : '<p class="ps-none">Nothing to check today.</p>'}</div>`).join('')}</section>`;
  // 1.56.0: a photo of each room or shelf the plants are on, so the sitter knows where to look
  const places = OPT.photos && (D.places || []).length ? `<section class="ps-sec ps-places" aria-labelledby="ps-places-h"><h3 id="ps-places-h">Where the plants are</h3>
    <ul class="ps-placelist">${D.places.map(pl => `<li><img src="${thumb(pl.photo)}" alt="${esc(pl.label)}" loading="lazy"><span>${esc(pl.label)}</span></li>`).join('')}</ul></section>` : '';
  const list = '';          // 1.47.0: the list at the end is gone; each day's lines carry the place and the watering words (Ethan, November 8)
  return { jobs, html: `<article class="ps-doc${OPT.pageday ? ' ps-pageday' : ''}" aria-labelledby="ps-title">
    <header class="ps-head"><h2 id="ps-title">Looking after the plants</h2><p class="ps-span">${esc(span)}</p>
      ${OPT.note.trim() ? `<p class="ps-msg">${esc(OPT.note.trim())}</p>` : ''}${intro}</header>
    ${places}${cold}${days}${list}
    <p class="ps-printed">Made ${esc(new Date().toLocaleDateString('en-US', { dateStyle: 'long' }))} from Plant record${D.group ? `, group "${esc(D.group.name)}"` : ''}.</p></article>` };
}
window.PlantSitterSheet = { sheet, dayName, dayShort, esc, iso, addDays };
})();
