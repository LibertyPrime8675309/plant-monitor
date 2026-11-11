/* Plant record front end: a plant's page: conditions, gauges, About this plant, the timeline, facts, previous and next. One of the files app.js was split into in 1.32.0; they load in order (index.html) and share one scope,
   so a function here may call any other. Plain JavaScript, no inline handlers (the server's content policy forbids them). */
'use strict';

// ---------- current conditions ----------
let COND = null;
const has = v => v != null && v !== '';
async function loadCond() { try { COND = await api('GET', '/api/current'); } catch (e) { COND = null; } return COND; }
const fmt = (n, d = 0) => has(n) ? Number(n).toLocaleString(undefined, { maximumFractionDigits: d }) : '';
function ago(min) { if (min == null) return ''; if (min < 2) return 'just now'; if (min < 90) return min + ' minutes ago'; if (min < 48 * 60) return Math.round(min / 60) + ' hours ago'; return Math.round(min / 1440) + ' days ago'; }

// ---------- gauges ----------
const posLin = (v, mn, mx) => (clamp(v, mn, mx) - mn) / (mx - mn) * 100;
const posSqrt = (v, mn, mx) => Math.sqrt(clamp(v, mn, mx) / mx) * 100;
function nowMarker(pos, label) {
  const edge = pos < 16 ? 'left:0' : pos > 84 ? 'right:0' : `left:${pos}%;transform:translateX(-50%)`;
  return { line: html`<div class="now-line" style="left:${pos}%;bottom:2.1rem"></div>`, tag: html`<div class="now-tag" style="${edge}">Now ${label}</div>` };
}
function strip(zones, marks, ticks, now) {
  const n = now ? nowMarker(now.pos, now.label) : null;
  return html`<div class="strip-wrap"><div class="strip">${zones.map(z => html`<div class="z ${z[0]}" style="width:${z[1]}%"></div>`)}
    ${marks.map(m => html`<div class="mk" style="left:${m[0]}%"><span>${m[1]}</span></div>`)}</div>
    <div class="ticks" aria-hidden="true">${ticks.map(t => html`<span style="left:${t[0]}%">${t[1]}</span>`)}</div>
    ${n ? html`<div class="now-space"></div>${n.line}${n.tag}` : ''}</div>`;
}
function fitNowTags() {         // 1.11.0: keep each "Now" label inside its strip; with large text a label near either end ran off the screen
  document.querySelectorAll('.strip-wrap > .now-tag').forEach(t => {
    t.classList.remove('nt-l', 'nt-r');
    const w = t.parentElement.getBoundingClientRect(), r = t.getBoundingClientRect();
    if (r.right > w.right + 1) t.classList.add('nt-r'); else if (r.left < w.left - 1) t.classList.add('nt-l');
  });
}
new MutationObserver(() => requestAnimationFrame(fitNowTags)).observe(document.getElementById('app'), { childList: true, subtree: true });
// 1.26.0: a table too wide for the screen becomes a list, one box per row, each value with its column's name beside it, instead of
// scrolling sideways. The long weather log (.tbl-wrap.wide) keeps its scrolling table.
function fitTables() {
  document.querySelectorAll('#app .tbl-wrap:not(.wide) > table.tbl').forEach(t => {
    if (!t.dataset.labelled) {
      const names = [...t.querySelectorAll('thead tr:last-child > th')].map(th => th.textContent.trim());
      t.querySelectorAll('tbody tr, tfoot tr').forEach(tr => { let i = 0;
        [...tr.children].forEach(c => { const n = names[i] || ''; if (n && !c.dataset.label && c.colSpan === 1) c.dataset.label = n; i += c.colSpan || 1; }); });
      t.dataset.labelled = '1';
    }
    t.classList.remove('stacked');
    if (t.scrollWidth > t.parentElement.clientWidth + 2 && t.querySelector('thead')) t.classList.add('stacked');
  });
}
let FITT = 0;
function fitTablesSoon() { cancelAnimationFrame(FITT); FITT = requestAnimationFrame(fitTables); }
new MutationObserver(fitTablesSoon).observe(document.getElementById('app'), { childList: true, subtree: true });
window.addEventListener('resize', fitTablesSoon); document.addEventListener('prefs', fitTablesSoon);
new MutationObserver(() => {                      // 1.12.0: for people who can only view, menus and tick boxes that save straight away are switched off
  if (ME().role !== 'viewer') return;
  document.querySelectorAll('#app select[data-act=site], #app select[data-act=plan], #app [data-act=preptrait], #app [data-act=preppest], #app input[type=file]').forEach(el => { if (!el.disabled) el.disabled = true; });
}).observe(document.getElementById('app'), { childList: true, subtree: true });
window.addEventListener('resize', () => requestAnimationFrame(fitNowTags));
const keyOf = items => html`<div class="key" aria-hidden="true">${items.map(i => html`<span class="${i[0]}">${i[1]}</span>`)}</div>`;

// marks on the temperature and humidity strips: from the weather history of the place in use, when it has 3 years or more
function tempMarks() {
  const C = META && META.climate, here = placeShort();
  if (!C) return [['A', 20, 'Hard freeze'], ['B', 32, 'Freezing']];
  return [['A', C.winter_low, `Coldest night of a usual winter in ${here}`], ['B', 32, 'Freezing'], ['C', C.cold_month_low, `Usual ${MONTHN[C.cold_month - 1]} night in ${here}`]]
    .sort((a, b) => a[1] - b[1]).map((m, i) => ['ABC'[i], m[1], m[2]]);
}
function humMarks() {
  const C = META && META.climate, out = [];
  if (C && C.winter_rh != null) { const cm = C.cold_month; out.push(['D', C.winter_rh, `Outdoors in ${placeShort()}, ${MONTHN[(cm + 10) % 12]} to ${MONTHN[cm % 12]} (average)`]); }   // the coldest month and the ones either side
  out.push([out.length ? 'E' : 'D', 30, 'Indoors with the heater running']);
  return out;
}
const LIGHT_MARKS = [['F', 1800, 'Full sun at midday'], ['G', 400, 'Open shade or a roofed porch'], ['H', 200, 'Indoors by a bright window']];

function tempVerdict(p, t) {
  const L = p.temp_lethal_below, D = p.temp_damage_below, IL = p.temp_ideal_low, IH = p.temp_ideal_high, HA = p.temp_damage_above;
  if (t < L) return ['fatal', `Likely fatal. This plant dies below ${tF(L)}, so it must be inside or well covered.`];
  if (t < D) return ['damage', `Damage likely. Leaves and stems are hurt below ${tF(D)}, so protect it or bring it in.`];
  if (t < IL) return ['cool', `Cooler than ideal, but no damage expected. Comfortable starts at ${tF(IL)}.`];
  if (t <= IH) return ['ok', 'Comfortable.'];
  if (has(HA) && t >= HA) return ['damage', `Too hot. Leaves are likely to scorch at ${tF(HA)} and above.`];
  return ['hot', `Warmer than ideal (above ${tF(IH)}).`];
}
function tempBlock(p, cur) {
  const v = [p.temp_lethal_below, p.temp_damage_below, p.temp_ideal_low, p.temp_ideal_high];
  if (v.some(x => x == null)) return html`<p class="muted">Temperature limits are not filled in yet. Use Edit to add them.</p>`;
  const l = clamp(v[0], 0, 100), d = clamp(Math.max(v[1], v[0]), 0, 100), il = clamp(Math.max(v[2], v[1], v[0]), 0, 100), ih = clamp(Math.max(v[3], v[2], v[1], v[0]), 0, 100);
  const ha = has(p.temp_damage_above) && p.temp_damage_above > v[3] ? clamp(p.temp_damage_above, 0, 100) : null;
  const zones = [['z-fatal', l], ['z-damage', d - l], ['z-cool', il - d], ['z-ok', ih - il]];
  if (ha != null) { zones.push(['z-hot', ha - ih]); zones.push(['z-heat', 100 - ha]); } else zones.push(['z-hot', 100 - ih]);
  const t = cur && has(cur.temp_f) ? cur.temp_f : null;
  const now = t == null ? null : { pos: posLin(t, 0, 100), label: tF(t) };
  const st = t == null ? '' : (() => { const [k, txt] = tempVerdict(p, t); return html`<p class="nowstate v-${k}"><strong>Now ${tF(t)}.</strong> ${txt}</p>`; })();
  return html`<p>Comfortable between <strong>${deg(p.temp_ideal_low)}</strong> and <strong>${deg(p.temp_ideal_high)}</strong>. Damage below ${deg(p.temp_damage_below)}. Dies below ${deg(p.temp_lethal_below)}.${has(p.temp_damage_above) ? html` Heat damage from ${deg(p.temp_damage_above)}.` : ''}</p>
    ${st}
    ${strip(zones, tempMarks().map(m => [m[1], m[0]]), [0, 20, 40, 60, 80, 100].map(x => [x, tF(x, false) + '°']), now)}
    ${keyOf([['z-fatal', 'Likely fatal'], ['z-damage', 'Damage'], ['z-cool', 'Cool but safe'], ['z-ok', 'Comfortable'], ['z-hot', 'Too hot'], ...(ha != null ? [['z-heat', 'Heat damage']] : []), ...(now ? [['z-now', 'Now']] : [])])}
    <ul class="verdicts">${tempMarks().map(m => { const [k, txt] = tempVerdict(p, m[1]); return html`<li class="v-${k}"><span class="k">${m[0]}</span><span><strong>${m[2]}, ${tF(m[1])}.</strong> ${txt}</span></li>`; })}</ul>`;
}
function humBlock(p, cur) {
  const lo = p.humidity_low, hi = p.humidity_high;
  if (lo == null || hi == null) return html`<p class="muted">Humidity range is not filled in yet.</p>`;
  const a = clamp(lo, 0, 100), b = clamp(Math.max(hi, lo), 0, 100);
  const verdict = t => t < lo ? ['dry', 'Drier than this plant likes. Raise humidity or move it.'] : t > hi ? ['wet', 'More humid than ideal. Give it airflow and avoid watering late in the day.'] : ['ok', 'Comfortable.'];
  const h = cur && has(cur.humidity) ? cur.humidity : null;
  const kk = k => k === 'dry' ? 'hot' : k === 'wet' ? 'cool' : 'ok';
  return html`<p>Comfortable between <strong>${lo}%</strong> and <strong>${hi}%</strong> relative humidity.${has(p.vpd_low) && has(p.vpd_high) ? html` Ideal air dryness (VPD) is <strong>${p.vpd_low} to ${p.vpd_high} kPa</strong>. VPD is how hard the air pulls water out of leaves; it rises when the air is warm and dry.` : ''}</p>
    ${h == null ? '' : (() => { const [k, txt] = verdict(h); return html`<p class="nowstate v-${kk(k)}"><strong>Now ${h}%.</strong> ${txt}${cur.vpd != null && has(p.vpd_low) ? html` Air dryness now: ${cur.vpd} kPa.` : ''}</p>`; })()}
    ${strip([['z-dry', a], ['z-ok', b - a], ['z-wet', 100 - b]], humMarks().map(m => [m[1], m[0]]), [0, 25, 50, 75, 100].map(x => [x, x + '%']), h == null ? null : { pos: posLin(h, 0, 100), label: h + '%' })}
    ${keyOf([['z-dry', 'Too dry'], ['z-ok', 'Comfortable'], ['z-wet', 'Too humid'], ...(h != null ? [['z-now', 'Now']] : [])])}
    <ul class="verdicts">${humMarks().map(m => { const [k, txt] = verdict(m[1]); return html`<li class="v-${kk(k)}"><span class="k">${m[0]}</span><span><strong>${m[2]}, about ${m[1]}%.</strong> ${txt}</span></li>`; })}</ul>
    ${paras(p.humidity_notes)}`;
}
// ---------- 1.14.0: about this plant ----------
const ABOUT_FIELDS = ['growth_habit', 'kingdom', 'taxon_order', 'family', 'genus', 'height_ground', 'width_ground', 'height_pot', 'width_pot', 'growth_rate', 'lifespan',
  'zone_low', 'zone_high', 'zone_notes', 'heat_zone_high', 'heat_zone_low', 'heat_zone_source', 'native_range', 'conservation_status', 'invasive', 'bloom', 'fruit', 'danger_humans', 'danger_animals', 'pet_safety', 'propagation', 'sources'];
function zoneNum(z) { const m = /^\s*(\d{1,2})\s*([ab])?\s*$/i.exec(String(z || '')); return m ? +m[1] + ((m[2] || '').toLowerCase() === 'b' ? 0.5 : 0) : null; }
// ---------- 1.36.0: summer heat (AHS heat zones) under About this plant, grown from prototype #33 ----------
let HEATV = null;
const HEAT_CACHE = new Map();         // `${place}|${above}` -> {at, data}
const MONTH_FULL = { Jan: 'January', Feb: 'February', Mar: 'March', Apr: 'April', May: 'May', Jun: 'June', Jul: 'July', Aug: 'August', Sep: 'September', Oct: 'October', Nov: 'November', Dec: 'December' };
function andList(a) { return a.length < 2 ? (a[0] || '') : a.slice(0, -1).join(', ') + ' and ' + a[a.length - 1]; }
function heatMonths(ms) {               // ['Jun','Jul','Aug','Sep'] -> 'June to September'; gaps -> 'May, July and August'
  const all = Object.keys(MONTH_FULL), idx = ms.map(m => all.indexOf(m.month));
  const run = idx.every((v, i) => !i || v === idx[i - 1] + 1);
  return run && ms.length > 2 ? `${MONTH_FULL[ms[0].month]} to ${MONTH_FULL[ms[ms.length - 1].month]}` : andList(ms.map(m => MONTH_FULL[m.month]));
}
async function loadHeat(p) {
  const above = has(p.temp_damage_above) ? +p.temp_damage_above : '', key = `${PLACE || ''}|${above}`, hit = HEAT_CACHE.get(key);
  if (hit && Date.now() - hit.at < 10 * 60e3) return hit.data;
  try { const H = await api('GET', '/api/heat' + (above !== '' ? '?above=' + above : '')); HEAT_CACHE.set(key, { at: Date.now(), data: H }); return H; }
  catch (e) { return null; }
}
function heatVerdict(p, H) {
  const T = H.above, n = H.reach, where = p.site === 'Indoors' || p.site === 'Garage or shed' ? ` It is ${p.site === 'Indoors' ? 'indoors' : 'in the garage or shed'} now, so this matters when it goes outside.` : '';
  if (T == null || n == null) return '';
  const when = (H.hot_months || []).length ? `, mostly in ${heatMonths(H.hot_months)}` : '';
  const days = x => x < 1 ? 'Less than 1 day' : `About ${Math.round(x)} day${Math.round(x) === 1 ? '' : 's'}`;
  if (H.level === 'fine') return html`<p class="nowstate v-ok"><strong>✓ Summer heat is fine for it here.</strong> A usual summer's hottest day, about ${tF(H.hottest)}, stays below the ${tF(T)} where its leaves start to scorch.${where}</p>`;
  if (H.level === 'few') return html`<p class="nowstate v-hot"><strong>▲ A few days a summer are too hot for it.</strong> ${days(n)} a year reach ${tF(T)} or more, where its leaves can scorch${when}. Move it into afternoon shade when the forecast is that hot.${where}</p>`;
  return html`<p class="nowstate v-damage"><strong>■ Summer heat is hard on it here.</strong> ${days(n)} a year reach ${tF(T)} or more, where its leaves can scorch${when}. Keep it in afternoon shade, or bring it inside, through those months.${where}</p>`;
}
function heatRange(p, H) {             // the AHS heat zones the plant is listed for, against the zone here
  const hi = has(p.heat_zone_high) ? +p.heat_zone_high : null, lo = has(p.heat_zone_low) ? +p.heat_zone_low : null;
  if (hi == null || lo == null) return html`<p class="muted">No published AHS heat zone range for this plant yet. You can add one with Edit, under About this plant.</p>`;
  const top = Math.max(hi, lo), bot = Math.min(hi, lo), src = String(p.heat_zone_source || ''), i = src.lastIndexOf('|');
  const t = i > 0 ? src.slice(0, i).trim() : src.trim(), u = i > 0 ? src.slice(i + 1).trim() : '';
  const from = !src.trim() ? '' : /^https?:\/\//.test(u) ? html` (from <a href="${u}" target="_blank" rel="noopener noreferrer">${t}</a>)` : html` (from ${t})`;
  const listed = html`It is listed for <strong>AHS heat zones ${top} to ${bot}</strong>${from}.`;
  if (H.zone == null) return html`<p>${listed}</p>`;
  if (H.zone > top) return html`<p class="nowstate v-damage"><strong>■ ${H.place} is hotter than its heat zones.</strong> ${listed} Here is zone ${H.zone}, so expect it to struggle through the summer unless it gets shade, extra water or a cooler spot.</p>`;
  if (H.zone < bot) return html`<p class="nowstate v-cool"><strong>▼ Summers here are cooler than its heat zones.</strong> ${listed} Here is zone ${H.zone}, so it may grow or flower less than it would somewhere hotter.</p>`;
  return html`<p class="nowstate v-ok"><strong>✓ ${H.place} is within its heat zones.</strong> ${listed} Here is zone ${H.zone}.</p>`;
}
function heatBlock(p, H) {
  const head = html`<h3>Summer heat (AHS heat zones)</h3>`;
  if (!H) return '';
  if (H.zone == null) return html`${head}<p class="muted">Not enough weather history yet. Once ${H.place} has 3 whole years of weather, this says how many hot days a usual year has and what that means for this plant. <a href="#/weather">Load the weather history on the Weather page</a>.</p>${heatRange(p, H)}`;
  return html`${head}<p>Where you are: over the last ${H.years} years at ${H.place}, an average of ${H.over86} days a year went above ${tF(H.line)}, which is <strong>heat zone ${H.zone}</strong>
      on the American Horticultural Society's scale of 1 (cool summers) to 12 (very hot). A usual year's hottest day is about ${tF(H.hottest)}. <a href="#/weather">The Weather page</a> has each year's count.</p>
    ${heatVerdict(p, H)}${heatRange(p, H)}
    <p class="hint">${tF(H.line)} is where many plants start to suffer from heat. The highs are air temperatures in the shade from the weather history; in full sun, leaves and dark pots get hotter.${has(p.temp_damage_above) ? '' : ' This plant has no "Heat damage above" temperature yet (Edit, under Temperature), so there is no verdict for it.'}</p>`;
}
function zoneHere(p) {
  const Z = META && META.zone, lo = zoneNum(p.zone_low), here = !Z ? null : Z.zone ? zoneNum(Z.zone) : zoneNum(String(Z.map_zone || '').split(' ')[0]);   // no weather history yet: the colder end of the map zone
  const where = html`${Z && Z.zone ? html`<p>Where you are: the last ${Z.years} winters of weather at ${placeName()} averaged a coldest night of ${tF(Z.winter_low)}, which is <strong>zone ${Z.zone}</strong>.${Z.map_note ? ' ' + Z.map_note : ''} <a href="${Z.map_url}" target="_blank" rel="noopener noreferrer">Look up a ZIP code on the USDA map</a>.</p>`
    : Z && Z.map_zone ? html`<p>Where you are: zone ${Z.map_zone} on the 2023 USDA map. <a href="${Z.map_url}" target="_blank" rel="noopener noreferrer">Look up a ZIP code on the USDA map</a>.</p>` : ''}`;
  // 1.34.0: summer heat next to winter cold, from the same weather history; 1.36.0: the whole verdict for this plant (heatBlock)
  const summer = heatBlock(p, HEATV);
  if (lo == null || here == null) return html`${where}${summer}`;
  const ok = here >= lo, gap = Math.round((lo - here) * 2);
  return html`${where}<p class="nowstate ${ok ? 'v-ok' : 'v-cool'}"><strong>${ok ? '✓ Hardy here.' : '▼ Not hardy here.'}</strong> ${ok ? 'It can stay outside through a usual winter, though a rare hard freeze can still hurt it.'
    : `A usual winter is about ${tD(gap * 5)} colder than it can take (${gap} half-zone${gap === 1 ? '' : 's'}), so it needs to come inside or be protected.`}</p>${summer}`;
}
function srcList(v) {
  return lines(v).map(x => { const i = x.lastIndexOf('|'), t = i > 0 ? x.slice(0, i).trim() : x.trim(), u = i > 0 ? x.slice(i + 1).trim() : '';
    return /^https?:\/\//.test(u) ? html`<li><a href="${u}" target="_blank" rel="noopener noreferrer">${t}</a></li>` : html`<li>${x}</li>`; });
}
function aboutBlock(p) {
  if (!ABOUT_FIELDS.some(f => has(p[f]) && p[f] !== '')) return html`<p class="muted">Not filled in yet. Use Edit to add it, under "About this plant".</p>`;
  const row = (k, v) => has(v) && v !== '' ? html`<dt>${k}</dt><dd>${v}</dd>` : '';
  const size = [['In the ground', p.height_ground, p.width_ground], ['In a pot', p.height_pot, p.width_pot]].filter(r => r[1] || r[2]);
  const zones = p.zone_low || p.zone_high ? (p.zone_low && p.zone_high && p.zone_low !== p.zone_high ? `Zones ${p.zone_low} to ${p.zone_high}` : `Zone ${p.zone_low || p.zone_high}`) : '';
  const unsure = p.id_confidence != null && p.id_confidence < 85 ? html`<p class="hint">The identification is ${p.id_confidence}% sure, so these details are for the closest match. Some may change if the ID does.</p>` : '';
  return html`${unsure}<dl class="dl about-dl">${row('Type of plant', p.growth_habit)}${row('Kingdom', p.kingdom)}${row('Order', p.taxon_order)}${row('Family', p.family)}${row('Genus', p.genus)}
      ${row('Species', p.scientific_name)}${row('Growth rate', p.growth_rate)}${row('Lifespan', p.lifespan)}</dl>
    ${size.length ? html`<h3>Mature size</h3><div class="tbl-wrap"><table class="tbl"><thead><tr><th scope="col">Where</th><th scope="col">Height</th><th scope="col">Width</th></tr></thead>
      <tbody>${size.map(r => html`<tr><th scope="row">${r[0]}</th><td>${r[1] || ''}</td><td>${r[2] || ''}</td></tr>`)}</tbody></table></div>` : ''}
    ${zones || p.zone_notes ? html`<h3>Hardiness zones (USDA)</h3>${zones ? html`<p><strong>${zones}.</strong></p>` : ''}${paras(p.zone_notes)}${zoneHere(p)}` : heatBlock(p, HEATV)}
    ${p.native_range ? html`<h3>Native range</h3>${paras(p.native_range)}` : ''}
    ${p.conservation_status ? html`<h3>Conservation status</h3>${paras(p.conservation_status)}` : ''}
    ${p.invasive ? html`<h3>Invasive risk</h3>${paras(p.invasive)}` : ''}
    ${p.bloom ? html`<h3>Flowers</h3>${paras(p.bloom)}` : ''}
    ${p.fruit ? html`<h3>Fruit</h3>${paras(p.fruit)}` : ''}
    ${p.danger_humans || p.danger_animals || p.pet_safety ? html`<div class="danger-box"><h3><span aria-hidden="true">⚠ </span>Dangers</h3>${p.danger_humans ? html`<h4>To people</h4>${paras(p.danger_humans)}` : ''}${p.danger_animals ? html`<h4>To pets and other animals</h4>${paras(p.danger_animals)}${p.pet_safety ? html`<p><strong>In short: ${p.pet_safety}.</strong></p>` : ''}` : ''}
      <p class="hint">If someone may have been poisoned, call Poison Control at 1-800-222-1222. For a pet, call your vet or the ASPCA Animal Poison Control Center at 888-426-4435.</p></div>` : ''}
    ${lines(p.propagation).length ? html`<h3>Propagation</h3>${ol(p.propagation)}` : ''}
    ${lines(p.sources).length ? html`<h3>Sources and further reading</h3><ul class="srcs">${srcList(p.sources)}</ul>` : ''}`;
}
function lightBlock(p, cur) {
  const lo = p.par_low, hi = p.par_high;
  const old = html`${p.light_summary ? html`<p><strong>${p.light_summary}</strong>${p.light_hours ? html`, about ${p.light_hours}` : ''}.</p>` : ''}${paras(p.light_notes)}`;
  if (!has(lo) || !has(hi)) return old;
  const MX = 2000, TICKS = [0, 100, 250, 500, 1000, 2000];
  const v = cur && has(cur.par) ? cur.par : null;
  const verdict = x => x < lo ? ['cool', 'Dimmer than this plant likes.'] : x > hi ? ['hot', 'Brighter than this plant likes.'] : ['ok', 'Comfortable.'];
  const lux = n => Math.round(n * 54 / 100) * 100;
  return html`<p>Comfortable light at the leaves is <strong>${fmt(lo)} to ${fmt(hi)} PAR</strong> (µmol/m²/s), roughly ${fmt(lux(lo))} to ${fmt(lux(hi))} lux.
      ${has(p.dli_low) && has(p.dli_high) ? html`Over a whole day that adds up to <strong>${p.dli_low} to ${p.dli_high} mol/m²/day</strong> (DLI).` : ''}</p>
    ${cur && has(cur.dli_today) ? html`<p>Light so far today: <strong>${cur.dli_today} mol/m²</strong>${has(p.dli_low) ? html` of the ${p.dli_low} to ${p.dli_high} this plant wants.` : '.'} ${cur.mode === 'weather' ? 'This is for open sky, so a plant under a roof or shade cloth gets less.' : ''}</p>` : ''}
    ${v == null ? '' : (() => { const [k, txt] = verdict(v); return html`<p class="nowstate v-${k}"><strong>Now ${fmt(v)} PAR.</strong> ${txt}${cur.mode === 'weather' ? ' This is open sky; under a roof it is much lower.' : ''}</p>`; })()}
    ${strip([['z-dim', posSqrt(lo, 0, MX)], ['z-ok', posSqrt(hi, 0, MX) - posSqrt(lo, 0, MX)], ['z-bright', 100 - posSqrt(hi, 0, MX)]], LIGHT_MARKS.map(m => [posSqrt(m[1], 0, MX), m[0]]), TICKS.map(x => [posSqrt(x, 0, MX), fmt(x)]), v == null ? null : { pos: posSqrt(v, 0, MX), label: fmt(v) + ' PAR' })}
    ${keyOf([['z-dim', 'Too dim'], ['z-ok', 'Comfortable'], ['z-bright', 'Too bright'], ...(v != null ? [['z-now', 'Now']] : [])])}
    <p class="hint">The scale stretches the dim end so low light is easy to read. Numbers are PAR in µmol/m²/s. 1 PAR is about 54 lux in sunlight.</p>
    <ul class="verdicts">${LIGHT_MARKS.map(m => { const [k, txt] = verdict(m[1]); return html`<li class="v-${k}"><span class="k">${m[0]}</span><span><strong>${m[2]}, about ${fmt(m[1])} PAR.</strong> ${txt}</span></li>`; })}</ul>
    ${old}`;
}
function rangeGauge(title, lo, hi, mn, mx, unit, now, names, ticks) {
  if (!has(lo) || !has(hi)) return '';
  const a = posLin(lo, mn, mx), b = posLin(hi, mn, mx);
  const cv = unit === '°F' ? (v, u) => tF(v, u) : (v, u) => v + (u ? unit : '');     // 1.47.0: a temperature gauge reads in the person's unit
  return html`<h3 class="gauge-title">${title}: ${cv(lo, false)} to ${cv(hi, true)}</h3>
    ${strip([[names[0][0], a], ['z-ok', b - a], [names[1][0], 100 - b]], [], ticks.map(x => [posLin(x, mn, mx), cv(x, true)]), now == null ? null : { pos: posLin(now, mn, mx), label: cv(now, true) })}
    ${keyOf([[names[0][0], names[0][1]], ['z-ok', 'Comfortable'], [names[1][0], names[1][1]], ...(now != null ? [['z-now', 'Now']] : [])])}`;
}
function soilBlock(p, cur) {
  const sm = cur && has(cur.soil_moisture) ? cur.soil_moisture : null, st = cur && has(cur.soil_temp_f) ? cur.soil_temp_f : null, ph = cur && has(cur.soil_ph) ? cur.soil_ph : null;
  return html`${paras(p.water_notes)}
    ${p.soil_medium ? html`<h3>Soil or potting mix</h3>${paras(p.soil_medium)}` : ''}
    ${rangeGauge('Soil moisture (a probe reading)', p.soil_moisture_low, p.soil_moisture_high, 0, 100, '%', sm, [['z-dry', 'Too dry'], ['z-wet', 'Too wet']], [0, 25, 50, 75, 100])}
    ${has(p.soil_moisture_low) ? html`<p class="hint">Probe readings depend on the sensor and the mix. Calibrate it: the reading in dry mix is 0% and in soaked mix is 100%.</p>` : ''}
    ${rangeGauge('Root-zone temperature', p.soil_temp_low, p.soil_temp_high, 30, 110, '°F', st, [['z-cool', 'Too cool'], ['z-hot', 'Too warm']], [30, 50, 70, 90, 110])}
    ${rangeGauge('Soil pH', p.soil_ph_low, p.soil_ph_high, 3, 9, '', ph, [['z-hot', 'Too acidic'], ['z-wet', 'Too alkaline']], [3, 4, 5, 6, 7, 8, 9])}`;
}

// ---------- is the plant in range, and what to do ----------
const LV = { ok: ['✔', 'In range'], near: ['▲', ''], bad: ['■', ''], danger: ['✖', ''] };
function winterTail(p, n) { const s = lines(p.winter_steps).slice(0, n); return s.length ? { title: 'From this plant\'s own winter steps', items: s } : null; }
function judge(p, cur) {
  const out = [];
  if (!cur) return out;
  const T = cur.temp_f, H = cur.humidity, L = cur.par, V = cur.vpd, SM = cur.soil_moisture, ST = cur.soil_temp_f, PH = cur.soil_ph;
  const openSky = cur.mode === 'weather' ? 'This reading is for open sky. Under a roof or shade cloth the plant gets less.' : '';
  const IL = p.temp_ideal_low, IH = p.temp_ideal_high;
  if (has(T) && has(IL) && has(IH)) {
    let level = 'ok', state = 'In range', detail = `${tF(T)} is inside the comfortable ${tF(IL, false)} to ${tF(IH)}.`, steps = [], tail = null;
    if (has(p.temp_lethal_below) && T < p.temp_lethal_below) {
      level = 'danger'; state = 'Far too cold: likely fatal'; detail = `${tF(T)} is ${tD(r1(IL - T))} below the comfortable minimum of ${tF(IL)}, and below the ${tF(p.temp_lethal_below)} this plant dies at.`;
      steps = ['Bring it inside or into a heated room right now.', `Aim for at least ${tF(IL)}. Warm it up gradually, not next to a heater.`, 'Do not water it until it is back above ' + tF(IL) + ', then water lightly.', 'Do not prune, repot or fertilize while it is stressed.', 'Check it in the morning for black or mushy leaves and stems. Trim them only after it has warmed up.'];
      tail = winterTail(p, 4);
    } else if (has(p.temp_damage_below) && T < p.temp_damage_below) {
      level = 'bad'; state = 'Too cold: damage likely'; detail = `${tF(T)} is ${tD(r1(IL - T))} below the comfortable minimum of ${tF(IL)}. Leaves and stems are hurt below ${tF(p.temp_damage_below)}.`;
      steps = ['Move it indoors, into the garage or under the porch roof now.', `If it cannot move: cover it to the ground with frost cloth or a sheet over a frame. Plastic must not touch the leaves. Remove the cover once it is above ${tF(35)}.`, 'Group pots against a south or east wall and pile mulch around the pots.', 'Water the day before a freeze, but not when the plant is already cold or the soil is frozen.', 'Hold off fertilizer until spring.'];
      tail = winterTail(p, 4);
    } else if (T < IL) {
      level = 'near'; state = 'A little cool'; detail = `${tF(T)} is ${tD(r1(IL - T))} below the comfortable minimum of ${tF(IL)}. No damage is expected yet.`;
      steps = ['Move it close to the house wall or under the porch roof for the night.', 'Keep the mix on the dry side. Cold, wet roots are the main risk at this temperature.', 'No fertilizer while it is cool.', `It is comfortable again from ${tF(IL)}.`];
      if (p.winter_triggers) tail = { title: 'When to act, from this page', items: lines(p.winter_triggers) };
    } else if (has(p.temp_damage_above) && T >= p.temp_damage_above) {
      level = 'bad'; state = 'Too hot: heat damage likely'; detail = `${tF(T)} is ${tD(r1(T - IH))} above the comfortable maximum of ${tF(IH)}. Leaves can scorch from ${tF(p.temp_damage_above)}.`;
      steps = ['Move it into shade now.', 'If the mix is dry, water slowly until it drains. If it is already wet, do not add water.', 'Use 50% shade cloth over the afternoon until temperatures fall.', 'Look for scorched, bleached or crispy leaves, and trim them only after it cools.', 'Move pots off hot concrete or metal.'];
    } else if (T > IH) {
      level = 'near'; state = 'A little warm'; detail = `${tF(T)} is ${tD(r1(T - IH))} above the comfortable maximum of ${tF(IH)}.`;
      steps = ['Give it shade in the afternoon: 30 to 50% shade cloth, or move it under the porch roof or a tree.', 'Water in the morning. Check the mix daily and water when the top inch is dry.', 'Do not fertilize, repot or prune in the heat.', 'Move pots off hot concrete or metal and out of reflected heat.'];
    }
    out.push({ key: 'temp', label: 'Temperature', value: tF(T), level, state, detail, steps, tail });
  }
  if (has(H) && has(p.humidity_low) && has(p.humidity_high)) {
    const lo = p.humidity_low, hi = p.humidity_high;
    let level = 'ok', state = 'In range', detail = `${H}% is inside the comfortable ${lo} to ${hi}%.`, steps = [];
    if (H < lo) {
      level = lo - H > 15 ? 'bad' : 'near'; state = 'Too dry'; detail = `${H}% is ${r1(lo - H)} points below the comfortable minimum of ${lo}%.`;
      steps = ['Group the plant with other plants; they raise the humidity around each other.', 'Set the pot on a tray of pebbles with water below the pebbles. The pot must not stand in the water.', `Run a humidifier nearby, aiming for ${lo} to ${hi}%.`, 'Keep it away from heater vents, fireplaces and drafts.', 'Water on schedule. Misting only helps for a few minutes and can spot the leaves.'];
    } else if (H > hi) {
      level = H - hi > 15 ? 'bad' : 'near'; state = 'Too humid'; detail = `${H}% is ${r1(H - hi)} points above the comfortable maximum of ${hi}%.`;
      steps = ['Increase airflow: a small fan on low, or more space between plants.', 'Water in the morning so leaves dry before night, and keep water off the leaves.', 'Remove dead leaves and flowers.', 'Watch for mildew, grey mould and rot. Let the top of the mix dry before watering again.', 'Indoors, run a dehumidifier. Outdoors, move it under cover from drizzle.'];
    }
    out.push({ key: 'hum', label: 'Humidity', value: H + '%', level, state, detail, steps });
  }
  if (has(L) && has(p.par_low) && has(p.par_high)) {
    const lo = p.par_low, hi = p.par_high;
    let level = 'ok', state = 'In range', detail = `${fmt(L)} PAR is inside the comfortable ${fmt(lo)} to ${fmt(hi)}.`, steps = [];
    if (L < lo) {
      level = L < lo * .6 ? 'bad' : 'near'; state = 'Too dim'; detail = `${fmt(L)} PAR is below the comfortable minimum of ${fmt(lo)}.`;
      steps = ['Move it to a brighter spot: a south or east window indoors, or the sunniest part of the porch outdoors.', 'Clean the window glass and keep the plant within about 3 ft (1 m) of it.', `Or add a full-spectrum LED grow light about 12 in (30 cm) above the plant for 12 to 14 hours a day on a timer. Aim for ${fmt(lo)} to ${fmt(hi)} PAR at the leaves.`, 'Turn the pot a quarter turn each week so it grows evenly.', 'Water less often. A plant in low light uses water slowly.'];
    } else if (L > hi) {
      level = L > hi * 1.5 ? 'bad' : 'near'; state = 'Too bright'; detail = `${fmt(L)} PAR is above the comfortable maximum of ${fmt(hi)}.`;
      steps = ['Move it into filtered light, or use 30 to 50% shade cloth, especially from noon to 4 pm.', 'Do not move a shaded plant straight into full sun. Step it up over 7 to 10 days.', 'Look for bleached, tan or crispy patches (sunburn). Trim them off later.', 'Water a little more often. Bright light dries the mix faster.'];
    }
    out.push({ key: 'light', label: 'Light', value: fmt(L) + ' PAR', level, state, detail, steps, note: openSky });
  }
  if (has(V) && has(p.vpd_low) && has(p.vpd_high)) {
    let level = 'ok', state = 'In range', detail = `${V} kPa is inside the comfortable ${p.vpd_low} to ${p.vpd_high}.`, steps = [];
    if (V > p.vpd_high) { level = V > p.vpd_high * 1.4 ? 'bad' : 'near'; state = 'Air too dry and warm'; detail = `${V} kPa is above ${p.vpd_high}. The air is pulling water out of the leaves faster than the roots can supply it.`;
      steps = ['Raise the humidity (see the humidity steps) or lower the temperature.', 'Shade the plant and shelter it from wind.', 'Check the mix and water if it is dry.']; }
    else if (V < p.vpd_low) { level = 'near'; state = 'Air too damp'; detail = `${V} kPa is below ${p.vpd_low}. The air is so damp that the plant barely transpires.`;
      steps = ['Add airflow with a small fan, or more space around the plant.', 'Keep the mix drier and water in the morning.', 'Watch for mildew and rot.']; }
    out.push({ key: 'vpd', label: 'Air dryness (VPD)', value: V + ' kPa', level, state, detail, steps });
  }
  if (has(SM) && has(p.soil_moisture_low) && has(p.soil_moisture_high)) {
    let level = 'ok', state = 'In range', detail = `${SM}% is inside the comfortable ${p.soil_moisture_low} to ${p.soil_moisture_high}%.`, steps = [];
    if (SM < p.soil_moisture_low) { level = SM < p.soil_moisture_low * .5 ? 'bad' : 'near'; state = 'Soil too dry'; detail = `${SM}% is below ${p.soil_moisture_low}%.`;
      steps = ['Water thoroughly until it drains from the bottom, then empty the saucer.', 'If water runs straight through, soak the pot in a bucket for 15 minutes, because the mix has dried and shrunk.', 'Check again in a few hours with the probe.']; }
    else if (SM > p.soil_moisture_high) { level = SM > p.soil_moisture_high * 1.3 ? 'bad' : 'near'; state = 'Soil too wet'; detail = `${SM}% is above ${p.soil_moisture_high}%.`;
      steps = ['Do not water until the reading falls back into range.', 'Empty the saucer and make sure the drainage holes are clear.', 'Move it somewhere airy and warm so the mix dries.', 'If leaves yellow or the base is soft, slide the plant out. Mushy, dark roots mean root rot: trim them and repot into fresh, dry mix.']; }
    out.push({ key: 'soil', label: 'Soil moisture', value: SM + '%', level, state, detail, steps });
  }
  if (has(ST) && has(p.soil_temp_low) && has(p.soil_temp_high)) {
    let level = 'ok', state = 'In range', detail = `${tF(ST)} is inside the comfortable ${tF(p.soil_temp_low, false)} to ${tF(p.soil_temp_high)}.`, steps = [];
    if (ST < p.soil_temp_low) { level = ST < p.soil_temp_low - 10 ? 'bad' : 'near'; state = 'Roots too cool'; detail = `${tF(ST)} is ${tD(p.soil_temp_low - ST)} below ${tF(p.soil_temp_low)}.`;
      steps = ['Lift the pot off cold ground or concrete onto feet or a board.', 'Wrap the pot in burlap or bubble wrap, or sink it into a larger pot of mulch.', 'Water only when the mix is dry; cold, wet roots rot.']; }
    else if (ST > p.soil_temp_high) { level = ST > p.soil_temp_high + 10 ? 'bad' : 'near'; state = 'Roots too warm'; detail = `${tF(ST)} is ${tD(ST - p.soil_temp_high)} above ${tF(p.soil_temp_high)}.`;
      steps = ['Shade the sides of the pot from the afternoon sun.', 'Stand the pot off hot concrete or metal, or double-pot it.', 'Water in the morning, and mulch the surface.']; }
    out.push({ key: 'soiltemp', label: 'Root-zone temperature', value: tF(ST), level, state, detail, steps });
  }
  if (has(PH) && has(p.soil_ph_low) && has(p.soil_ph_high)) {
    let level = 'ok', state = 'In range', detail = `pH ${PH} is inside the comfortable ${p.soil_ph_low} to ${p.soil_ph_high}.`, steps = [];
    if (PH < p.soil_ph_low) { level = 'near'; state = 'Soil too acidic'; detail = `pH ${PH} is below ${p.soil_ph_low}.`; steps = ['Water with plain rain water or let tap water stand, and stop acid-type fertilizers.', 'Mix in a small amount of dolomitic lime (about 1 teaspoon per gallon of mix) and test again in 2 weeks.', 'Or repot into fresh mix.']; }
    else if (PH > p.soil_ph_high) { level = 'near'; state = 'Soil too alkaline'; detail = `pH ${PH} is above ${p.soil_ph_high}.`; steps = ['Water with rain water: tap water is often alkaline.', 'Feed with an acid-type fertilizer, and add chelated iron if new leaves are pale with green veins.', 'Or repot into fresh mix, with pine bark or peat added.']; }
    out.push({ key: 'ph', label: 'Soil pH', value: 'pH ' + PH, level, state, detail, steps });
  }
  return out;
}
function condCard(p, cur) {
  const res = p ? judge(p, cur) : [];
  const by = Object.fromEntries(res.map(r => [r.key, r]));
  const cell = (key, label, val, unit) => {
    if (!has(val)) return '';
    const r = by[key];
    return html`<div class="val"><span class="lab">${label}</span><span class="n">${fmt(val, 1)}${unit}</span>
      ${r ? html`<span class="st st-${r.level}">${LV[r.level][0]} ${r.state}</span>` : ''}</div>`;
  };
  const any = cur && ['temp_f', 'humidity', 'par', 'soil_moisture', 'soil_temp_f', 'soil_ph'].some(k => has(cur[k]));
  return html`<section class="cond" id="sec-now" aria-labelledby="cond-h"><header><h2 id="cond-h">Current conditions</h2>
      <button class="btn small noprint" type="button" data-act="setcond">${any ? 'Change' : 'Set current conditions'}</button></header>
    ${any ? html`<div class="vals">${cell('temp', 'Temperature', tNum(cur.temp_f), tU())}${cell('hum', 'Humidity', cur.humidity, '%')}${cell('light', 'Light (PAR)', cur.par, '')}${cell('vpd', 'Air dryness (VPD)', cur.vpd, ' kPa')}
        ${cell('soil', 'Soil moisture', cur.soil_moisture, '%')}${cell('soiltemp', 'Root-zone temp', tNum(cur.soil_temp_f), tU())}${cell('ph', 'Soil pH', cur.soil_ph, '')}</div>
      <p class="src">${cur.label}${cur.as_of ? html`, updated ${ago(cur.age_minutes)}` : ''}.${cur.stale ? html` <strong>This reading is old.</strong>` : ''}${cur.dli_today != null ? html` Light so far today: ${cur.dli_today} mol/m².` : ''}
        ${cur.mode === 'weather' ? ' Light is for open sky; plants under a roof get less.' : ''}</p>
      ${p && isInside(p) && cur.mode === 'weather' ? html`<p class="src"><strong>This plant is ${p.site.toLowerCase()}</strong>, so these outdoor readings do not apply to it. Use Change to type in the indoor temperature and humidity, or a sensor near it.</p>` : ''}`
      : html`<p class="src">Type in the temperature, humidity and light where this plant sits (or pick your sensor or the online weather). The bars below then show a "Now" marker, and this page says what to do if the plant is outside its comfortable range.</p>`}
  </section>`;
}
function adviceBlock(p, cur) {
  const res = judge(p, cur);
  if (!res.length) return '';
  const bad = res.filter(r => r.level !== 'ok');
  return html`<section class="advice" id="sec-advice" aria-labelledby="adv-h"><h2 id="adv-h">${bad.length ? 'Getting this plant back in range' : 'In range'}</h2>
    ${bad.length ? bad.map(r => html`<div class="issue"><h3 class="st-${r.level}">${LV[r.level][0]} ${r.label}: ${r.state} (${r.value})</h3><p>${r.detail}</p>
        <p><strong>What to do</strong></p><ol>${r.steps.map(x => html`<li>${x}</li>`)}</ol>
        ${r.tail ? html`<p><strong>${r.tail.title}</strong></p><ul>${r.tail.items.map(x => html`<li>${x}</li>`)}</ul>` : ''}
        ${r.note ? html`<p class="hint">${r.note}</p>` : ''}</div>`)
      : html`<p class="good">✔ Everything you have entered is inside this plant's comfortable range.</p>`}
    ${bad.length && res.length > bad.length ? html`<p class="src" style="padding:.6rem 1.1rem;color:var(--ink-2)">In range: ${res.filter(r => r.level === 'ok').map(r => r.label).join(', ')}.</p>` : ''}
  </section>`;
}

// ---------- plant page ----------
let CUR = null, PIDX = 0, KEEP = null;
function requestText(p) {
  const items = lines(p.id_improve);
  return `Plant ${p.code} (${p.common_name}${p.scientific_name ? ', ' + p.scientific_name : ''}). Claude's current ID confidence is ${p.id_confidence == null ? 'not rated' : p.id_confidence + '%'}.\n\n` +
    (items.length ? 'To raise it, I am sending:\n' + items.map(x => '- ' + x).join('\n') : 'Please tell me what else you need to identify this plant.') +
    `\n\n(Attach photos in the same message, then I will update the record.)`;
}
function photoPanel(p) {
  const ph = p.photos, i = clamp(PIDX, 0, Math.max(0, ph.length - 1)), cur = ph[i];
  return html`${cur ? html`<button type="button" class="main-photo" data-act="zoom" aria-label="Enlarge photo"><img src="${photoUrl(cur.file)}" alt="${cur.caption || p.common_name}"></button>
      <p class="cap">${cur.caption || 'No caption'}. Added ${when(cur.added_at)} by ${cur.added_by}.</p>
      ${ph.length > 1 ? html`<p class="main-note noprint">${cur.is_primary
        ? html`<strong>★ This is the main photo.</strong> It is the one shown on the Plants page, on care cards and in plant link previews.`
        : html`<button class="btn small" type="button" data-act="mainphoto">Make this the main photo</button> <span class="hint">The main photo is the one shown on the Plants page, on care cards and in plant link previews.</span>`}</p>` : ''}`
      : html`<div class="empty">No photos yet. Add one below.</div>`}
    ${ph.length > 1 ? html`<div class="thumbs">${ph.map((x, j) => html`<button type="button" data-act="pick" data-i="${j}" aria-label="Photo ${j + 1} of ${ph.length}${x.is_primary ? ', the main photo' : ''}" aria-current="${String(j === i)}"><img src="${thumbUrl(x.file)}" alt="">${x.is_primary ? html`<span class="th-main" aria-hidden="true">★ Main</span>` : ''}</button>`)}</div>` : ''}
    <div class="row noprint">
      ${cur ? html`<button class="btn ghost small" type="button" data-act="capedit">Edit caption</button>
        <button class="btn ghost small" type="button" data-act="movephoto">Move to another plant</button>
        <button class="btn danger small" type="button" data-act="rmphoto">Remove photo</button>` : ''}
    </div>
    <label class="f noprint" style="margin-top:1.2rem">Add photos<small>JPG or PNG. Location data is removed when the photo is saved.</small>
      <input type="file" accept="image/*" multiple data-act="addphotos"></label>`;
}
// ---------- plant timeline and photo comparison (added in 1.8.0) ----------
const TL = { code: null, data: null, a: null, b: null, hide: new Set() };
const TL_KINDS = [['photo', 'Photos'], ['change', 'Changes to the page'], ['care', 'Feeding and care'], ['request', 'Answers'], ['created', 'Page created']];
const TL_WORD = { photo: 'Photo', change: 'Changed', care: 'Care', request: 'Answer', created: 'Created' };
const tlDay = ts => new Date(ts).toLocaleDateString([], { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
const tlShort = ts => new Date(ts).toLocaleDateString([], { month: 'short', day: 'numeric' });
function tlChange(ch) {
  const set = x => x != null && x !== '', v = x => ch.field === 'id_confidence' ? x + '%' : x;
  const what = !set(ch.old) ? html`set to ${v(ch.new)}` : !set(ch.new) ? html`cleared (it was ${v(ch.old)})` : html`from ${v(ch.old)} to ${v(ch.new)}`;
  return html`<li><strong>${ch.label.replace(' (%)', '')}:</strong> ${what}</li>`;
}
function tlTrend(list, cur, word, order) {
  // "Critical until Oct 22, Poor now (getting better)": the first value the log knows, the day it first changed, and now.
  const set = x => x != null && x !== '';
  if (!list.length || !set(cur)) return '';
  const startsEmpty = !set(list[0].old), first = startsEmpty ? list[0].new : list[0].old, until = startsEmpty ? list[1] : list[0];
  if (!until || String(first) === String(cur)) return '';
  const a = order(first), b = order(cur), better = a < 0 || b < 0 || isNaN(a) || isNaN(b) || a === b ? null : b > a;
  const pc = x => word === 'ID confidence' ? x + '%' : x;
  const how = better == null ? '' : word === 'Health' ? (better ? ' (getting better)' : ' (getting worse)') : (better ? ' (more certain)' : ' (less certain)');
  return html`<li><strong>${word}:</strong> ${pc(first)} until ${tlShort(until.at)}, ${pc(cur)} now${how}</li>`;
}
function tlCompare(D) {
  const ps = D.photos; if (ps.length < 2) return '';
  const a = ps.find(x => x.file === TL.a) || ps[0], b = ps.find(x => x.file === TL.b) || ps[ps.length - 1];
  const opt = (sel, side) => html`<label class="f">${side === 'a' ? 'Left photo' : 'Right photo'}<select data-act="tlsel" data-side="${side}">${ps.map((x, i) => html`<option value="${x.file}" ${x.file === sel.file ? raw('selected') : ''}>${i + 1}. ${tlShort(x.added_at)}: ${x.caption || 'no caption'}</option>`)}</select></label>`;
  const fig = x => html`<figure class="tl-fig"><img src="${photoUrl(x.file)}" alt="${x.caption || 'Plant photo'}" loading="lazy"><figcaption><strong>${tlShort(x.added_at)}</strong>. ${x.caption || ''}</figcaption></figure>`;
  return html`<h3>Compare two photos</h3><p class="muted">The oldest and the newest photo, side by side. Pick others to compare.</p>
    <div class="tl-pick">${opt(a, 'a')}${opt(b, 'b')}</div><div class="tl-cmp">${fig(a)}${fig(b)}</div>`;
}
// ---------- 1.36.0: the soil moisture over the last 60 days, from the sensor in the pot, with the waterings marked ----------
let SNSDAYS = null;
function moistureChart(D) {
  if (!D || !D.sensors.length) return '';
  const S = D.sensors[0], days = [], d0 = new Date(D.start + 'T00:00:00'), d1 = new Date(D.end + 'T00:00:00');
  for (let d = new Date(d0); d <= d1; d.setDate(d.getDate() + 1)) days.push(d.toISOString().slice(0, 10));
  const by = Object.fromEntries(S.days.map(x => [x.d, x])), W = 640, H = 150, L = 34, R = 8, T = 10, B = 26;
  const x = i => L + i / Math.max(1, days.length - 1) * (W - L - R), y = v => T + (100 - v) / 100 * (H - T - B);
  let path = '';
  days.forEach((d, i) => { const v = by[d]; if (!v) return; path += (path ? ' L' : 'M') + x(i).toFixed(1) + ' ' + y(v.avg).toFixed(1); });
  const [lo, hi] = D.range || [], band = lo != null && hi != null ? html`<rect x="${L}" y="${y(hi).toFixed(1)}" width="${W - L - R}" height="${(y(lo) - y(hi)).toFixed(1)}" class="sns-band"/>` : '';
  const wset = new Set(D.waterings), marks = days.map((d, i) => wset.has(d) ? html`<g><line x1="${x(i).toFixed(1)}" x2="${x(i).toFixed(1)}" y1="${T}" y2="${H - B}" class="mc-water"/><text x="${x(i).toFixed(1)}" y="${H - B + 14}" text-anchor="middle" class="mc-lbl">▲</text></g>` : '');
  const ticks = [0, 25, 50, 75, 100].map(v => html`<g><line x1="${L}" x2="${W - R}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}" class="mc-grid"/><text x="${L - 4}" y="${(y(v) + 4).toFixed(1)}" text-anchor="end" class="mc-lbl">${v}</text></g>`);
  const first = days.findIndex(d => by[d]), lastD = S.days[S.days.length - 1];
  const words = `Soil moisture from ${S.name} over the last ${days.length} days: ${S.days.length} days with readings, lowest ${Math.min(...S.days.map(z => z.min))}%, highest ${Math.max(...S.days.map(z => z.max))}%, now ${lastD.avg}%. ${D.waterings.length} watering${D.waterings.length === 1 ? '' : 's'} marked.`;
  return html`<h3>Soil moisture, last ${days.length} days</h3>
    <svg class="mchart" viewBox="0 0 ${W} ${H}" role="img" aria-label="${words}">${band}${ticks}${marks}<path d="${path}" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linejoin="round"/>
      <text x="${L}" y="${H - 2}" class="mc-lbl">${tlShort(D.start)}</text><text x="${W - R}" y="${H - 2}" text-anchor="end" class="mc-lbl">${tlShort(D.end)}</text></svg>
    <p class="hint">${words} ▲ marks a watering (pressed, or seen by the sensor)${lo != null && hi != null ? `; the shaded band is this plant's range, ${lo} to ${hi}%` : ''}. <a href="#/sensors">Your sensors</a>.</p>`;
}
function tlRender() {
  const box = document.getElementById('tl-box'), D = TL.data; if (!box || !D) return;
  const ev = D.events.filter(e => !TL.hide.has(e.kind));
  const days = []; ev.forEach(e => { const d = tlDay(e.at); if (!days.length || days[days.length - 1].d !== d) days.push({ d, items: [] }); days[days.length - 1].items.push(e); });
  const trend = [tlTrend(D.health, D.current.health, 'Health', h => HEALTH_ORDER[h] ?? -1), tlTrend(D.confidence, D.current.id_confidence, 'ID confidence', n => +n)].filter(Boolean);
  box.innerHTML = rend(html`${trend.length ? html`<ul class="tl-trend">${trend}</ul>` : ''}
    ${moistureChart(SNSDAYS)}
    ${tlCompare(D)}
    <h3>Everything that has happened</h3>
    <fieldset class="tl-filter"><legend>Show</legend>${TL_KINDS.map(([k, w]) => html`<label class="chk"><input type="checkbox" data-act="tlkind" value="${k}" ${TL.hide.has(k) ? '' : raw('checked')}>${w}</label>`)}</fieldset>
    ${days.length ? days.map(g => html`<h4 class="tl-day">${g.d}</h4><ul class="tl">${g.items.map(e => html`<li class="tl-item tl-${e.kind}">
      <span class="tl-kind">${e.kind === 'request' && !e.answer ? 'Done' : TL_WORD[e.kind]}</span><div class="tl-body">${e.kind === 'request'
        ? html`<div><strong>Asked:</strong> ${linkify(e.question || '')}</div><div class="tl-ans">${e.answer ? html`<strong>Answer:</strong> ${linkify(e.answer)}` : 'Marked done'}</div>`
        : html`<div>${linkify(e.title)}</div>`}
        ${e.changes.length || e.other ? html`<ul class="tl-ch">${e.changes.map(tlChange)}${e.other ? html`<li class="muted">and ${e.other} other detail${e.other === 1 ? '' : 's'}</li>` : ''}</ul>` : ''}
        ${e.photos.length ? html`<div class="tl-photos">${e.photos.map(x => html`<button type="button" class="tl-thumb" data-act="tlpick" data-file="${x.file}" title="Compare this photo"><img src="${thumbUrl(x.file)}" alt="${x.caption || 'Plant photo'}" loading="lazy"><span>Compare</span></button>`)}</div>` : ''}
        ${e.by ? html`<div class="tl-by muted">By ${e.by}</div>` : ''}</div></li>`)}</ul>`)
      : html`<p class="muted">Nothing to show with these choices.</p>`}`);
}
async function loadTimeline(box) {
  const code = box.dataset.code;
  try { TL.data = await api('GET', '/api/plants/' + enc(code) + '/timeline'); } catch (e) { box.innerHTML = rend(html`<p class="notice bad">Could not load the timeline: ${e.message}</p>`); return; }
  if (TL.code !== code) { TL.code = code; TL.a = TL.b = null; }
  tlRender();
}
// ---------- 1.27.0: uses, partners, deterrents, propagation and breeding (one species' facts, on plant, species and find pages) ----------
const FACT_EVIDENCE = { Tested: 'shown in trials', Traditional: "gardeners' lore, not proven", 'Same needs': 'same light, water and soil', 'Different needs': 'needs different light, water or soil' };
function factYours(list, lead) {
  return list && list.length ? html`<span class="fact-yours">${lead} ${list.map((x, i) => html`${i ? ', ' : ''}<a href="#/plant/${enc(x.code)}">${x.code} ${x.name}</a>`)}</span>` : '';
}
function factsHtml(f, box) {
  const fungus = box.dataset.factsKind === 'fungus', name = box.dataset.factsCommon || box.dataset.factsName;
  if (!f) {
    const can = canChange() && box.dataset.canWrite === '1';
    return html`<p class="muted">Nothing kept for ${name} yet.</p>
      ${can && box.dataset.factsName ? html`<p><button class="btn" type="button" data-act="factswrite">Write them with Claude</button></p>
        <p class="hint">Claude writes the uses, ${fungus ? 'partner trees and plants, and how it is grown' : 'good and bad partner plants, deterrents, propagation and breeding'} for this species, for ${fungus ? 'your area' : 'Round Rock'}. It takes about half a minute, uses the owner's Anthropic key, and is kept.</p>`
        : html`<p class="hint">${box.dataset.factsName ? 'The owner can let Claude write them by saving an Anthropic API key on the Identify page.' : 'Set the scientific name (Edit this page) so they can be looked up.'}</p>`}`;
  }
  const ev = e => html`<span class="fact-ev">(${FACT_EVIDENCE[e] || e})</span>`;
  const partner = p => html`<li><strong>${p.name}</strong>${p.sci && p.sci.toLowerCase() !== (p.name || '').toLowerCase() ? html` <i class="latin">${p.sci}</i>` : ''}: ${p.why} ${ev(p.evidence)}${p.yours && p.yours.length ? html`<br>${factYours(p.yours, 'You have it:')}` : ''}</li>`;
  const genus = f.key.split(' ')[0], same = f.cross_same || [], other = f.cross_other || [];
  const src = f.origin === 'researched' ? `Written for your plants by ${f.written_by || 'Claude'}, from general horticultural knowledge` : `Written by Claude when ${f.written_by || 'someone'} asked`;
  const sp = (box.dataset.factsName || '').replace(/^[x\u00d7]\s*/, '');
  return html`${!f.key.includes(' ') && /^[A-Z][a-z]+\s+[a-z]{3,}/.test(sp) && !/^[A-Z][a-z]+\s+(sp|spp|cultivar|type|hybrid|or|cf)\b/.test(sp) ? html`<p class="hint">For the genus <i class="latin">${f.name}</i> as a whole.</p>` : ''}
    ${f.summary ? html`<p>${f.summary}</p>` : ''}
    <div class="facts">
      <div><h3>Uses</h3>${f.uses.length ? html`<ul class="fact-list">${f.uses.map(u => html`<li><strong>${u.kind}:</strong> ${u.text}${u.caution ? html`<br><span class="fact-warn">⚠ ${u.caution}</span>` : ''}</li>`)}</ul>` : html`<p class="muted">None known beyond being grown for its looks.</p>`}
        ${fungus ? html`<p class="hint">Uses never include eating it. Never eat a wild mushroom because of an app, a photo, or this record.</p>` : html`<p class="hint">Traditional uses are not medical advice.</p>`}
        ${f.compost.verdict ? html`<h3>In the compost</h3><p><strong>${f.compost.verdict}.</strong> ${f.compost.why}</p>` : ''}</div>
      ${f.deters.length || f.attracts.length ? html`<div>${f.deters.length ? html`<h3>Keeps away</h3><ul class="fact-list">${f.deters.map(x => html`<li><strong>${x.what}:</strong> ${x.how} ${ev(x.evidence)}</li>`)}</ul>` : ''}
        ${f.attracts.length ? html`<h3>Brings in</h3><ul class="fact-list">${f.attracts.map(x => html`<li><strong>${x.what}:</strong> ${x.why}</li>`)}</ul>` : ''}</div>` : ''}
      <div><h3>Good partners</h3>${f.partners_good.length ? html`<ul class="fact-list">${f.partners_good.map(partner)}</ul>` : html`<p class="muted">None noted.</p>`}
        <h3>Keep apart from</h3>${f.partners_bad.length ? html`<ul class="fact-list">${f.partners_bad.map(partner)}</ul>` : html`<p class="muted">None noted.</p>`}</div>
      <div><h3>${fungus ? 'Growing it' : 'Propagation'}</h3>${f.propagation.length ? html`<ul class="fact-list">${f.propagation.map(x => html`<li><strong>${x.method}</strong>${x.when ? html` (${x.when})` : ''}: ${x.how}</li>`)}</ul>` : html`<p class="muted">Not noted.</p>`}
        ${fungus ? '' : html`<h3>Breeding</h3>${f.breeding.text ? html`<p>${f.breeding.text}</p>` : ''}
          ${same.length ? html`<p>${factYours(same, 'Your plants of the same species:')}</p>` : ''}
          ${other.length ? html`<p>${factYours(other, `Your plants it may cross with (${[genus].concat(f.breeding.cross_genera || []).map(g => g.charAt(0).toUpperCase() + g.slice(1)).join(' or ')}):`)}</p>` : ''}
          ${!same.length && !other.length ? html`<p class="muted">None of your plants are close enough relatives to cross with it.</p>` : ''}
          ${f.breeding.patent ? html`<p class="fact-warn">⚠ ${f.breeding.patent}</p>` : ''}`}</div>
    </div>
    <p class="hint">${src}${f.written_at ? `, ${when(f.written_at)}` : ''}. Not checked by a person. Evidence: "shown in trials" has been tested; "gardeners' lore" is widely repeated but not proven.
      ${f.sources.length ? html`Read more: ${f.sources.map((x, i) => html`${i ? '; ' : ''}<a href="${x.url}" target="_blank" rel="noopener noreferrer">${x.title}</a>`)}.` : ''}</p>
    ${f.origin === 'claude' && canChange() && box.dataset.canWrite === '1' ? html`<p><button class="btn ghost small" type="button" data-act="factswrite">Write them again with Claude</button></p>` : ''}`;
}
async function loadFacts(box) {
  const q = box.dataset.factsCode ? 'code=' + enc(box.dataset.factsCode) : 'name=' + enc(box.dataset.factsName || '');   // by code alone, so it is saved for offline use
  try {
    const r = await api('GET', '/api/facts?' + q);
    box.dataset.canWrite = r.can_write ? '1' : '0';
    box.innerHTML = rend(factsHtml(r.facts, box));
  } catch (e) { box.innerHTML = rend(html`<p class="muted">${e.offline || !navigator.onLine ? 'Not saved on this device. They load once you are back online.' : e.message}</p>`); }
}
new MutationObserver(() => document.querySelectorAll('.facts-box:not([data-loaded])').forEach(b => { b.dataset.loaded = '1'; loadFacts(b); }))
  .observe(document.getElementById('app'), { childList: true, subtree: true });

new MutationObserver(() => { const b = document.getElementById('tl-box'); if (b && !b.dataset.loaded) { b.dataset.loaded = '1'; loadTimeline(b); } })
  .observe(document.getElementById('app'), { childList: true });
function slips(h) {
  const byV = {};
  h.audit.forEach(a => { (byV[a.version] = byV[a.version] || []).push(a); });
  return h.versions.map(v => {
    const rows = (byV[v.version] || []).filter(a => a.field);
    const cur = v.version === h.current;
    return html`<article class="slip ${cur ? 'cur' : ''}">
      <header><h3>Version ${v.version}${cur ? ' (current)' : ''}</h3><span class="when">${timeEl(v.changed_at)} by ${v.changed_by}</span></header>
      <p style="margin:.4rem 0">${v.summary || ''}</p>
      ${rows.length ? html`<table class="chg"><thead class="sr"><tr><th>Field</th><th>Before and after</th></tr></thead><tbody>${rows.map(a => html`<tr><th scope="row">${a.label || a.field}</th>
        <td>${a.old_value == null || a.old_value === '' ? html`<span class="muted">Before: empty</span>` : html`<div class="old">${a.old_value}</div>`}
        ${a.new_value == null || a.new_value === '' ? html`<div class="muted">After: empty</div>` : html`<div class="new">${a.new_value}</div>`}</td></tr>`)}</tbody></table>` : ''}
      <div class="row noprint"><button class="btn ghost small" type="button" data-act="viewver" data-v="${v.version}">View this version</button>
        ${cur ? '' : html`<button class="btn ghost small" type="button" data-act="restore" data-v="${v.version}">Restore its text</button>`}</div>
    </article>`;
  });
}
// 1.29.0: the plant's main details, edited right on its page (the rest is under "Edit this page"). 1.56.5: they read as text, and
// "Change these details" opens the boxes (the page read like a form before)
let PLEDIT = null;                     // the code of the plant whose details are open to change
function plantEdHtml(p) {
  const ed = k => raw(`data-ed="plant" data-id="${esc(p.code)}" data-k="${k}"`);
  const txt = (k, label, max) => html`<label class="f">${label}<input type="text" maxlength="${max || 200}" value="${p[k] || ''}" ${ed(k)}></label>`;
  const all = WHERE().flatMap(h => h.areas), a = all.find(x => String(x.id) === String(p.area_id));
  const hs = HOMES(), conts = k => ((META && META.containers) || []).filter(x => x.kind === k);
  const sel = (k, label, opts, cur) => html`<label class="f">${label}<select ${ed(k)}>${opts.map(([v, l]) => html`<option value="${v}" ${String(v) === String(cur == null ? '' : cur) ? raw('selected') : ''}>${l}</option>`)}</select></label>`;
  const areas = WHERE().map(h => [h, h.areas]).filter(([h]) => HOMES().length < 2 || String(plantHome(p).id) === String(h.home.id)).flatMap(([h, as]) => as.map(x => [x.id, `${x.side === 'out' ? 'Outside' : 'Inside'}: ${x.name}`]));
  return html`<div class="field-grid pl-ed noprint" id="pl-ed" data-pver="${p.version}" data-section-skip ${PLEDIT === p.code ? '' : raw('hidden')}>
    ${txt('common_name', 'Common name', 120)}${txt('scientific_name', 'Scientific name', 200)}${txt('aliases', 'Other names / cultivar')}${txt('plant_type', 'Plant type', 120)}
    ${hs.length > 1 ? sel('home_id', 'Home', hs.map(h => [h.is_home ? '' : h.id, h.name]), p.home_id || '') : ''}
    ${sel('area_id', 'Area or room', areas, p.area_id)}
    ${sel('spot_id', 'Spot', [['', 'No particular spot']].concat((a ? a.spots : []).map(x => [x.id, x.name])), p.spot_id || '')}
    ${txt('location', 'More about where', 200)}${txt('container', 'Container', 200)}
    ${sel('pot_id', 'Pot', [['', 'None chosen']].concat(conts('pot').map(x => [x.id, `${x.name} (${x.free} of ${x.qty} free)`])), p.pot_id || '')}
    ${sel('tray_id', 'Catch tray', [['', 'None chosen']].concat(conts('tray').map(x => [x.id, `${x.name} (${x.free} of ${x.qty} free)`])), p.tray_id || '')}
    <label class="f">Height now, with its pot (${lenU()})<input type="number" inputmode="decimal" min="0" step="any" value="${p.height_in == null ? '' : lenF(p.height_in, false)}" ${ed('height_in')}></label>
    <label class="f">ID confidence (%)<input type="number" inputmode="numeric" min="0" max="100" step="1" value="${p.id_confidence == null ? '' : p.id_confidence}" ${ed('id_confidence')}></label>
    ${sel('winter_plan', 'Winter plan', (META.winter_plans || []).map(x => [x, x]), p.winter_plan)}
    ${sel('health_rating', 'Health', (META.health || []).map(x => [x, x]), p.health_rating)}
    <p class="hint wide">Change any of these by typing or choosing; each saves when you leave it. Everything else is under "Edit this page".</p></div>`;
}
async function viewPlant(code) {
  const [p, h, cur, st] = await Promise.all([api('GET', '/api/plants/' + enc(code) + '?fill=1'), api('GET', '/api/plants/' + enc(code) + '/history'), loadCond(), api('GET', '/api/settings').catch(() => ({}))]);   // 1.53.0: fill=1 reads the species' facts for empty fields
  CUR = { p, h, base: st.base_url || location.origin };
  HEATV = await loadHeat(p);                     // 1.36.0: the summer heat for this plant (cached for 10 minutes per place and temperature)
  SNSDAYS = await api('GET', '/api/sensors/days?days=60&plant=' + enc(code)).catch(() => null);   // 1.36.0: the soil moisture day by day, for the timeline and the calendar
  PIDX = KEEP != null ? KEEP : Math.max(0, p.photos.findIndex(x => x.is_primary));
  KEEP = null;
  const archived = p.status === 'archived';
  const pot = contById(p.pot_id), tray = contById(p.tray_id);
  const dl = [['Also known as', p.aliases], ['Plant type', p.plant_type], ['Home', HOMES().length > 1 ? plantHome(p).name : ''], ['Where', whereWords(p)], ['More about where', p.location], ['Container', p.container],
    ['Pot', pot ? html`<a href="#/pots">${pot.name}</a> (${pot.size})` : ''], ['Catch tray', tray ? html`<a href="#/pots">${tray.name}</a> (${tray.size})` : ''], ['Height now, with its pot', p.height_in == null ? '' : lenF(p.height_in)]].filter(x => x[1]);
  const single = document.documentElement.dataset.layout === 'single';
  return {
    title: p.common_name,
    // 1.56.5: the plant's name comes first, then Previous / Next (they came first, and on a phone the name was a screen further down)
    html: html`<header class="pl-head"><h1>${p.common_name}</h1><p class="sci latin">${p.scientific_name || 'Scientific name not set'}</p></header>
    ${pnavBlock(p.code)}<p class="crumb"><a href="#/plants">All plants</a>
      <button class="btn ghost small noprint pl-layout" type="button" data-act="layout">${single ? 'Show photos and details side by side' : 'Switch to one column'}</button></p>
    ${archived ? html`<div class="notice">This record is archived. It is hidden from the main list.</div>` : ''}
    <div class="plant">
      <div class="pane" id="pane-l" tabindex="0" role="region" aria-label="Photos"><section class="ph-sec" data-section="Photos"><h2 class="ph-title">Photos</h2><div id="photopanel">${photoPanel(p)}</div></section></div>
      <div class="pane" id="pane-r" tabindex="0" role="region" aria-label="Details">
        <nav class="jump noprint" id="jumprow" aria-label="Jump to a section"></nav>
        <div class="label${PLEDIT === p.code ? ' pl-editing' : ''}" id="details" data-section="Name and details">
          <div class="l-top"><b>${p.code}</b><a href="#history" data-act="jumpsec" data-sec="history">Page history</a></div>
          <div class="l-body"><h2 class="l-title">Name and details</h2>
            ${canChange() ? html`<p class="row noprint pl-edrow"><button class="btn small" type="button" data-act="pledit" aria-controls="pl-ed" aria-expanded="${PLEDIT === p.code ? 'true' : 'false'}">${PLEDIT === p.code ? 'Done changing' : 'Change these details'}</button></p>${plantEdHtml(p)}` : ''}
            <dl><dt id="site-lbl">Location</dt><dd>${sitePicker(p)}</dd>
              ${dl.map(x => html`<dt class="ro">${x[0]}</dt><dd class="ro">${x[1]}</dd>`)}
              <dt class="ro">ID confidence</dt><dd class="ro">${p.id_confidence == null ? 'Not rated' : p.id_confidence + '%'}</dd>
              <dt class="ro">Winter plan</dt><dd class="ro">${planTag(p.winter_plan)}</dd><dt class="ro">Health</dt><dd class="ro">${healthTag(p.health_rating)}</dd>
              <dt>Groups</dt><dd id="pl-groups">${groupsOf(p.code).length ? groupsOf(p.code).map((g, i) => html`${i ? ', ' : ''}<a href="#/group/${g.id}">${g.name}</a>`) : 'None yet'}
                <button class="btn small ghost noprint" type="button" data-act="plgroups">Change groups</button></dd></dl>
            <div class="row acts noprint"><a class="btn" href="#/plant/${enc(p.code)}/edit">Edit this page</a>
              <button class="btn ghost" type="button" data-act="archive" data-to="${archived ? '0' : '1'}">${archived ? 'Move back to the main list' : 'Archive'}</button></div></div>
        </div>
        ${careQuick(p)}

        ${frostNote(p)}${needsBox(p)}
        ${condCard(p, cur)}${adviceBlock(p, cur)}

        <section class="blk" id="ident"><h2>Plant identification</h2>
          <div class="big-meter"><span class="n">${p.id_confidence == null ? '?' : p.id_confidence + '%'}</span><i style="--v:${p.id_confidence || 0}%;--mc:${confColor(p.id_confidence)}" role="img" aria-label="ID confidence ${p.id_confidence || 0} percent"></i></div>
          ${paras(p.id_basis)}
          ${lines(p.id_alternatives).length ? html`<h3>Other possibilities</h3>${ul(p.id_alternatives)}` : ''}
          ${lines(p.id_improve).length ? html`<div class="ask"><h3 style="margin-top:0">To reach 100%, send</h3>${ul(p.id_improve)}
            <button class="btn small noprint" type="button" data-act="copyreq">Copy this as a request for Claude</button></div>` : ''}
          ${(p.photos || []).length && canChange() ? html`<p class="row noprint"><button class="btn small ghost" type="button" data-act="plantid" data-code="${p.code}">Check the name from its ${p.photos.length === 1 ? 'photo' : p.photos.length + ' photos'}</button></p>
            <div id="plant-id" aria-live="polite"></div>` : ''}
        </section>

        <section class="blk" id="about"><h2>About this plant</h2>${aboutBlock(p)}</section>
        <section class="blk" id="uses"><h2>Uses, partners and propagation</h2><div class="facts-box" data-facts-code="${p.code}" data-facts-name="${p.scientific_name || ''}" data-facts-common="${p.common_name}"><p class="loading">Loading</p></div></section>

        <section class="blk" id="temp"><h2>Temperature</h2>${tempBlock(p, cur)}${paras(p.temp_notes)}${histBlock('temp')}</section>
        <section class="blk" id="hum"><h2>Humidity</h2>${humBlock(p, cur)}${histBlock('hum')}</section>
        <section class="blk" id="light"><h2>Sunlight</h2>${lightBlock(p, cur)}<div id="pl-grow" class="pl-grow"></div>${histBlock('light')}</section>
        <section class="blk" id="soil"><h2>Water and soil</h2><div id="care-plant"><p class="loading">Loading the watering record</p></div>${soilBlock(p, cur)}${histBlock('soil')}</section>
        <section class="blk" id="nutrients"><h2>Nutrients</h2>
          ${p.fertilizer ? html`<p><strong>Fertilizer:</strong> ${p.fertilizer}</p>` : ''}${paras(p.nutrients)}
          ${!p.fertilizer && !p.nutrients ? html`<p class="muted">Not filled in yet. Use Edit to add it.</p>` : ''}
          <div id="fert-need"></div>
          <h3>Feeding schedule and log</h3><div id="fert-plant"><p class="loading">Loading</p></div></section>

        <section class="blk" id="winter"><h2>Winter in ${placeShort()}</h2>
          <p>${planTag(p.winter_plan)}</p>${paras(p.winter_summary)}
          ${p.winter_triggers ? html`<h3>When to act</h3>${paras(p.winter_triggers)}` : ''}
          ${lines(p.winter_steps).length ? html`<h3>Steps</h3>${ol(p.winter_steps)}` : ''}
          ${lines(p.indoor_setup).length ? html`<h3>Keeping it comfortable when the weather cannot</h3>${ul(p.indoor_setup)}` : ''}</section>

        <section class="blk" id="inside"><h2>Getting ready to come inside</h2><p class="row noprint"><a class="btn small ghost" href="#/inside">Every plant coming inside, with its status</a></p><div id="prep-box" data-code="${p.code}"><p class="loading">Loading the pest check plan</p></div></section>

        <section class="blk" id="health"><h2>Health</h2>
          <p>${healthTag(p.health_rating)}</p>${paras(p.health_summary)}
          ${lines(p.health_observations).length ? html`<h3>What I can see</h3>${ul(p.health_observations)}` : ''}
          ${lines(p.health_steps).length ? html`<h3>Steps to improve</h3>${ol(p.health_steps)}` : ''}</section>

        <section class="blk" id="pests"><h2>Pests and diseases</h2>
          ${p.pests_current ? html`<h3 style="margin-top:0">Seen now</h3>${paras(p.pests_current)}` : ''}
          ${lines(p.pests_watch).length ? html`<h3>What to watch for</h3>${ul(p.pests_watch)}` : ''}
          ${lines(p.pest_steps).length ? html`<h3>Prevention and treatment</h3>${ol(p.pest_steps)}` : ''}
          ${!p.pests_current && !p.pests_watch ? html`<p class="muted">Not filled in yet. Use Edit to add it.</p>` : ''}</section>

        ${p.notes ? html`<section class="blk" id="notes"><h2>Notes</h2>${paras(p.notes)}</section>` : ''}

        <section class="blk" id="label"><h2>Label</h2>
          <p class="muted">The same label as on the Labels page. Scanning the code with a phone opens this page.</p>
          ${labelCard(p, CUR.base, false)}
          <p class="noprint"><button class="btn" type="button" data-act="printlabel">Print this label</button></p></section>

        <section class="blk" id="timeline"><h2>Timeline</h2><div id="tl-box" data-code="${p.code}"><p class="loading">Loading the timeline</p></div></section>

        <section class="blk" id="history"><h2>Page history</h2>
          <p class="muted">Version ${p.version}, updated ${timeEl(p.updated_at)} by ${p.updated_by}. Created ${timeEl(p.created_at)} by ${p.created_by}. Every save makes a new version and keeps the old one.</p>
          ${slips(h)}</section>
      </div>
    </div>`,
    after: () => { fitPanes(); loadFertPlant(); loadCarePlant(); loadGrowPlant(p.code); pnavLayout(); setTimeout(pnavLayout, 300); },
  };
}
// where the plant is now: a plain-looking menu in the plant's label; choosing saves straight away
const isInside = p => (META.inside_sites || ['Indoors']).includes(p.site);
async function moveSite(el, site) {
  if (!(await needName())) return;
  const code = el.dataset.code, y = window.scrollY;
  await guard(async () => {
    await api('POST', '/api/plants/' + enc(code) + '/site', { site });
    toast(el.dataset.name + (site === 'Indoors' ? ' moved indoors' : ' moved back outside')); FROST_AT = 0;
    await route(); window.scrollTo(0, y);
    const back = document.querySelector(`[data-act="${site === 'Indoors' ? 'moveout' : 'movein'}"][data-code="${code}"]`);
    const next = document.querySelector('.winter-list [data-act="movein"]');
    (next || back || document.querySelector('main h1')).focus({ preventScroll: true });
  });
}
async function fzMark(el, what) {
  if (!(await needName())) return;
  const y = window.scrollY, code = el.dataset.code;
  await guard(async () => { await api('POST', '/api/frost/done', { date: el.dataset.date, code, what }); toast(what ? 'Marked as covered' : 'Tick removed'); await fzReload(y, code); });
}
async function fzReload(y, code) {
  await loadFrost(true); await loadCodes(true); await route(); window.scrollTo(0, y);
  const f = (code && document.querySelector(`.fz-row[data-code="${code}"] button`)) || document.querySelector('.fz-row:not(.is-done) button') || document.querySelector('main h1');
  if (f) f.focus({ preventScroll: true });
}
function sitePicker(p) {
  const v = p.site || 'Outdoors';
  return html`<select class="site-pick noprint" data-act="site" aria-labelledby="site-lbl" title="Change where this plant is">${(META.sites || ['Outdoors', 'Indoors']).map(o => html`<option ${o === v ? raw('selected') : ''}>${o}</option>`)}</select><span class="printonly">${v}</span>`;
}
// ---------- previous / next plant (follows the Plants page filters and sort) ----------
function pnavNeighbours(code) {
  const all = [...PCODES.values()], list = filteredPlants(all);
  let i = list.findIndex(p => p.code === code), inList = i >= 0;
  if (!inList) {                                   // this plant is filtered out: go to the plants either side of where it would sort
    const cur = PCODES.get(code) || { code, common_name: '', health_rating: '', id_confidence: null, updated_at: '' };
    const cmp = plantCmp(); i = list.findIndex(p => cmp(cur, p) < 0); if (i < 0) i = list.length;
    return { prev: list[i - 1] || null, next: list[i] || null, pos: null, n: list.length, total: all.length };
  }
  return { prev: list[i - 1] || null, next: list[i + 1] || null, pos: i + 1, n: list.length, total: all.length };
}
function pnavLink(p, dir) {
  const word = dir === 'prev' ? 'Previous Plant' : 'Next Plant', arrow = dir === 'prev' ? '←' : '→';
  if (!p) return html`<span class="pn pn-${dir} pn-none" aria-disabled="true"><span class="pn-dir">${dir === 'prev' ? arrow + ' ' + word : word + ' ' + arrow}</span><span class="pn-name">${dir === 'prev' ? 'This is the first plant in the list' : 'This is the last plant in the list'}</span></span>`;
  return html`<a class="pn pn-${dir}" href="#/plant/${enc(p.code)}" rel="${dir}" data-pncode="${p.code}">
    <span class="pn-dir">${dir === 'prev' ? arrow + ' ' + word : word + ' ' + arrow}</span><span class="pn-name">${p.common_name}</span><span class="pn-code">${p.code}</span></a>`;
}
function filterWords() {
  const w = [];
  if (G.needs) w.push('needs something from you'); if (G.plan) w.push(G.plan); if (G.health) w.push('health ' + G.health);
  if (G.low) w.push('ID under 70%'); if (G.q.trim()) w.push('"' + G.q.trim() + '"');
  if (G.group && groupById(G.group)) w.push('group ' + groupById(G.group).name);
  if (G.site) w.push(G.site.toLowerCase());
  if (G.home && homeById(G.home)) w.push('at ' + homeById(G.home).name);
  if (G.status !== 'active') w.push(G.status === 'all' ? 'archived included' : 'archived only');
  for (const d of MORE) if (G[d.key]) { const o = moreOpts(d).find(x => x[0] === G[d.key]); if (o) w.push(o[1].toLowerCase()); }
  return (w.length ? w.join(', ') : 'all plants') + '; sorted by ' + (SORTS[G.sort] || 'code').toLowerCase();
}
function pnavBlock(code) {
  const N = pnavNeighbours(code);
  return html`<nav class="pnav noprint" id="pnav" aria-label="Previous and next plant" data-code="${code}">${pnavLink(N.prev, 'prev')}${pnavLink(N.next, 'next')}</nav>
    <details class="pn-filters noprint" id="pn-filters"${PNOPEN ? raw(' open') : ''}><summary>Filters for Previous / Next: <span id="pn-sum">${filterWords()}</span>
      <span class="pn-pos" id="pn-pos">${N.pos ? `plant ${N.pos} of ${N.n}` : `this plant is not in the filtered list (${N.n} of ${N.total})`}</span></summary>
      <div class="filters">
        <label>Search<input type="search" data-f="q" value="${G.q}" placeholder="Name, code, location"></label>
        <label>Winter plan<select data-f="pnplan"><option value="">Any</option>${META.winter_plans.map(pl => html`<option ${G.plan === pl ? raw('selected') : ''}>${pl}</option>`)}</select></label>
        <label>Health<select data-f="health"><option value="">Any</option>${META.health.map(h => html`<option ${G.health === h ? raw('selected') : ''}>${h}</option>`)}</select></label>
        ${homeFilter()}${siteFilter()}${groupFilter()}${statusFilter()}${moreSelects()}
        <label>Sort by<select data-f="sort">${Object.entries(SORTS).map(([k, v]) => html`<option value="${k}" ${G.sort === k ? raw('selected') : ''}>${v}</option>`)}</select></label>
        <label class="chk"><input type="checkbox" data-f="pnneeds" ${G.needs ? raw('checked') : ''}>Needs something from you</label>
        <label class="chk"><input type="checkbox" data-f="low" ${G.low ? raw('checked') : ''}>ID confidence under 70%</label>
        <button class="btn ghost small" type="button" data-act="clearfilters">Clear filters</button>
      </div><p class="hint">These are the same filters as on the Plants page; changing them here changes them there too.</p></details>`;
}
let PNOPEN = false;
function drawPnav() {
  const nav = document.getElementById('pnav'); if (!nav) return;
  const N = pnavNeighbours(nav.dataset.code);
  nav.innerHTML = rend(html`${pnavLink(N.prev, 'prev')}${pnavLink(N.next, 'next')}`);
  const sum = document.getElementById('pn-sum'); if (sum) sum.textContent = filterWords();
  const pos = document.getElementById('pn-pos'); if (pos) pos.textContent = N.pos ? `plant ${N.pos} of ${N.n}` : `this plant is not in the filtered list (${N.n} of ${N.total})`;
  pnavLayout();
}
// on wide screens the two buttons sit in the empty margins either side of the page, halfway down; otherwise in a row at the top
function pnavLayout() {
  const nav = document.getElementById('pnav'); if (!nav) return;
  const r = document.documentElement, main = document.getElementById('app'), cs = getComputedStyle(main), mb = main.getBoundingClientRect();
  const pl = document.querySelector('.plant'), pb = pl && pl.getBoundingClientRect();     // the page content can be narrower than <main>
  const m = pb && pb.width ? { left: pb.left, right: pb.right } : { left: mb.left + parseFloat(cs.paddingLeft), right: mb.right - parseFloat(cs.paddingRight) };
  let lo = 0, hi = window.innerWidth;
  for (const id of ['sidenav', 'nav-tab']) {
    const el = document.getElementById(id); if (!el || !el.offsetWidth) continue;
    const b = el.getBoundingClientRect(); if (b.width >= window.innerWidth * 0.6) continue;
    if (b.right <= m.left + 4) lo = Math.max(lo, b.right); else if (b.left >= m.right - 4) hi = Math.min(hi, b.left);
  }
  const left = m.left - lo, right = hi - m.right, need = 150;
  const side = left >= need && right >= need && r.dataset.narrow !== '1';
  nav.classList.toggle('pn-side', side);
  if (side) {
    const w = Math.min(260, left - 24, right - 24);
    nav.style.setProperty('--pn-w', w + 'px');
    nav.style.setProperty('--pn-l', (lo + (left - w) / 2) + 'px');
    nav.style.setProperty('--pn-r', (window.innerWidth - hi + (right - w) / 2) + 'px');
  }
}
window.addEventListener('resize', () => pnavLayout());
