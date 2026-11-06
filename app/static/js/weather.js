/* Plant record front end: charts, the Weather page, places, the weather log, frost, winter and back outside. One of the files app.js was split into in 1.32.0; they load in order (index.html) and share one scope,
   so a function here may call any other. Plain JavaScript, no inline handlers (the server's content policy forbids them). */
'use strict';

// ---------- charts (plain SVG; width follows the container and the text size) ----------
const CHARTS = {};
const DAYMS = 86400000;
function niceStep(range, n) { const raw = range / n, mag = Math.pow(10, Math.floor(Math.log10(raw))), r = raw / mag; return (r < 1.5 ? 1 : r < 3 ? 2 : r < 7 ? 5 : 10) * mag; }
function xTicks(t0, t1) {
  const span = (t1 - t0) / DAYMS, out = [];
  if (span <= 2.2) {
    const hrs = span <= 1.1 ? 3 : 6, d = new Date(t0); d.setMinutes(0, 0, 0);
    while (d.getHours() % hrs !== 0 || d.getTime() < t0) d.setHours(d.getHours() + 1);
    for (; d.getTime() <= t1; d.setHours(d.getHours() + hrs)) out.push(d.getTime());
  } else if (span > 400) {                       // years: aim for about 6 to 10 ticks
    const yrs = span / 365.25, step = [1, 2, 5, 10, 20, 25, 50].find(n => yrs / n <= 10) || 100;
    const d = new Date(new Date(t0).getFullYear(), 0, 1); while (d.getTime() < t0 || d.getFullYear() % step) d.setFullYear(d.getFullYear() + 1);
    for (; d.getTime() <= t1; d.setFullYear(d.getFullYear() + step)) out.push(d.getTime());
  } else if (span > 100) {                       // months
    const step = span > 250 ? 2 : 1, d = new Date(t0); d.setHours(0, 0, 0, 0); d.setDate(1); if (d.getTime() < t0) d.setMonth(d.getMonth() + 1);
    for (; d.getTime() <= t1; d.setMonth(d.getMonth() + step)) out.push(d.getTime());
  } else {
    const step = span <= 9 ? 1 : span <= 20 ? 2 : span <= 45 ? 7 : 14, d = new Date(t0); d.setHours(0, 0, 0, 0);
    if (d.getTime() < t0) d.setDate(d.getDate() + 1);
    for (; d.getTime() <= t1; d.setDate(d.getDate() + step)) out.push(d.getTime());
  }
  return out;
}
function xLabel(t, span) {
  const d = new Date(t);
  if (span <= 2.2) return d.getHours() === 0 ? d.toLocaleDateString([], { weekday: 'short', day: 'numeric' }) : d.toLocaleTimeString([], { hour: 'numeric' });
  if (span > 400) return String(d.getFullYear());
  if (span > 100) return d.toLocaleDateString([], { month: 'short', year: '2-digit' });
  return span <= 9 ? d.toLocaleDateString([], { weekday: 'short', day: 'numeric' }) : d.toLocaleDateString([], { month: 'short', day: 'numeric' });
}
function chartCard(id, spec) {
  CHARTS[id] = spec;
  const rows = [...new Set(spec.series.flatMap(s => s.pts.map(p => p[0])))].sort((a, b) => b - a).slice(0, 400);
  const look = spec.series.map(s => new Map(s.pts.map(p => [p[0], p[1]])));
  return html`<section class="chart-card" aria-labelledby="h-${id}"><h3 id="h-${id}">${spec.title}</h3>
    <div class="legend">${spec.series.map(s => html`<span><i style="--c:var(--${s.cls})"></i>${s.name}</span>`)}${spec.bands && spec.bands.length ? html`<span><i style="--c:var(--z-ok);border-top-width:.9rem;opacity:.35"></i>${spec.bands[0].label}</span>` : ''}
      ${(spec.refs || []).map(r => html`<span><i class="dash" style="--c:var(--ink)"></i>${r.label}</span>`)}</div>
    <div class="chart-box" id="cb-${id}"></div><div class="chart-tip" id="ct-${id}" role="presentation"></div>
    <details class="tbl-view"><summary>Show these numbers as a table</summary><div class="tbl-wrap"><table class="tbl"><thead><tr><th>Time</th>${spec.series.map(s => html`<th class="num">${s.name}</th>`)}</tr></thead>
      <tbody>${rows.map(t => html`<tr><td>${new Date(t).toLocaleString([], { dateStyle: 'medium', timeStyle: spec.daily ? undefined : 'short' })}</td>${look.map(m => html`<td class="num">${m.has(t) ? spec.fmt(m.get(t)) : ''}</td>`)}</tr>`)}</tbody></table></div>
      ${rows.length >= 400 ? html`<p class="hint">Showing the newest 400 rows.</p>` : ''}</details></section>`;
}
function paintChart(id) {
  const sp = CHARTS[id], box = document.getElementById('cb-' + id), tip = document.getElementById('ct-' + id);
  if (!sp || !box) return;
  const rem = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
  const W = Math.max(300, Math.floor(box.clientWidth)), H = Math.round(clamp(W * .42, 270, 380));
  const m = { l: Math.round(rem * 3.6), r: Math.round(rem * 1.2), t: Math.round(rem * .9), b: Math.round(rem * 2.4) };
  const all = sp.series.flatMap(s => s.pts);
  if (!all.length) { box.innerHTML = rend(html`<div class="empty">No data for this period yet.</div>`); return; }
  const t0 = Math.min(...all.map(p => p[0])), t1 = Math.max(...all.map(p => p[0]));
  let y0 = Math.min(...all.map(p => p[1])), y1 = Math.max(...all.map(p => p[1]));
  (sp.bands || []).forEach(b => { y0 = Math.min(y0, b.lo); y1 = Math.max(y1, b.hi); });
  (sp.refs || []).forEach(r => { y0 = Math.min(y0, r.v); y1 = Math.max(y1, r.v); });
  if (sp.zero) y0 = Math.min(y0, 0);
  if (y1 - y0 < 1) y1 = y0 + 1;
  const step = niceStep(y1 - y0, 5);
  y0 = Math.floor(y0 / step) * step; y1 = Math.ceil(y1 / step) * step;
  if (sp.clamp) { y0 = Math.max(y0, sp.clamp[0]); y1 = Math.min(y1, sp.clamp[1]); }
  const X = t => m.l + (t - t0) / ((t1 - t0) || 1) * (W - m.l - m.r), Y = v => H - m.b - (v - y0) / (y1 - y0) * (H - m.t - m.b);
  const span = (t1 - t0) / DAYMS;
  let g = '';
  for (let v = y0; v <= y1 + 1e-9; v += step) g += `<line class="grid-l" x1="${m.l}" x2="${W - m.r}" y1="${Y(v)}" y2="${Y(v)}"/><text x="${m.l - 8}" y="${Y(v) + 5}" text-anchor="end">${esc(sp.fmt(Math.round(v * 100) / 100))}</text>`;
  g += `<line class="axis-l" x1="${m.l}" x2="${W - m.r}" y1="${H - m.b}" y2="${H - m.b}"/>`;
  xTicks(t0, t1).forEach(t => { g += `<line class="grid-l" x1="${X(t)}" x2="${X(t)}" y1="${H - m.b}" y2="${H - m.b + 6}"/><text x="${X(t)}" y="${H - m.b + rem * 1.5}" text-anchor="middle">${esc(xLabel(t, span))}</text>`; });
  (sp.bands || []).forEach(b => { g += `<rect class="band" x="${m.l}" width="${W - m.l - m.r}" y="${Y(b.hi)}" height="${Math.max(1, Y(b.lo) - Y(b.hi))}"/>`; });
  (sp.refs || []).forEach(r => { g += `<line class="ref-l" x1="${m.l}" x2="${W - m.r}" y1="${Y(r.v)}" y2="${Y(r.v)}"/>`; });
  const gaps = [];
  sp.series.forEach(s => {
    const pts = s.pts.slice().sort((a, b) => a[0] - b[0]);
    const diffs = pts.slice(1).map((p, i) => p[0] - pts[i][0]).sort((a, b) => a - b);
    const lim = (diffs.length ? diffs[Math.floor(diffs.length / 2)] : 3600000) * 3.5;
    gaps.push(lim);
    let d = '', prev = null, runLen = 0;
    pts.forEach(p => {
      if (prev === null || p[0] - prev > lim) { if (runLen === 1) g += `<circle cx="${X(prev)}" cy="${Y(pts.find(q => q[0] === prev)[1])}" r="4" fill="var(--${s.cls})"/>`; d += `M${X(p[0]).toFixed(1)} ${Y(p[1]).toFixed(1)}`; runLen = 1; }
      else { d += `L${X(p[0]).toFixed(1)} ${Y(p[1]).toFixed(1)}`; runLen++; }
      prev = p[0];
    });
    if (runLen === 1 && prev !== null) g += `<circle cx="${X(prev)}" cy="${Y(pts[pts.length - 1][1])}" r="4" fill="var(--${s.cls})"/>`;
    g += `<path class="ln" stroke="var(--${s.cls})" d="${d}"/>`;
  });
  g += `<line class="cross" id="cx-${id}" y1="${m.t}" y2="${H - m.b}" style="display:none"/>` + sp.series.map((s, i) => `<circle id="dot-${id}-${i}" r="5.5" fill="var(--${s.cls})" stroke="var(--sheet)" stroke-width="2" style="display:none"/>`).join('');
  box.innerHTML = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(sp.title)}. The same numbers are in the table below.">${g}</svg>`;
  const svg = box.querySelector('svg');
  const near = (pts, t, lim) => { let best = null; pts.forEach(p => { if (Math.abs(p[0] - t) <= lim && (best === null || Math.abs(p[0] - t) < Math.abs(best[0] - t))) best = p; }); return best; };
  const hide = () => { tip.style.display = 'none'; const c = svg.querySelector('#cx-' + id); if (c) c.style.display = 'none'; sp.series.forEach((s, i) => { const d = svg.querySelector('#dot-' + id + '-' + i); if (d) d.style.display = 'none'; }); };
  box.onpointerleave = hide;
  box.onpointermove = e => {
    const r = svg.getBoundingClientRect(), px = (e.clientX - r.left) * (W / r.width);
    const t = t0 + clamp((px - m.l) / (W - m.l - m.r), 0, 1) * (t1 - t0);
    let anchor = null;
    sp.series.forEach(s => { const p = near(s.pts, t, Infinity); if (p && (anchor === null || Math.abs(p[0] - t) < Math.abs(anchor - t))) anchor = p[0]; });
    if (anchor === null) return;
    const c = svg.querySelector('#cx-' + id); c.setAttribute('x1', X(anchor)); c.setAttribute('x2', X(anchor)); c.style.display = '';
    const lines = [`<strong>${esc(new Date(anchor).toLocaleString([], { dateStyle: 'medium', timeStyle: sp.daily ? undefined : 'short' }))}</strong>`];
    sp.series.forEach((s, i) => {
      const p = near(s.pts, anchor, gaps[i]), d = svg.querySelector('#dot-' + id + '-' + i);
      if (p) { d.setAttribute('cx', X(p[0])); d.setAttribute('cy', Y(p[1])); d.style.display = ''; lines.push(`${esc(s.name)}: ${esc(sp.fmt(p[1]))}${esc(sp.unit || '')}`); } else d.style.display = 'none';
    });
    tip.innerHTML = lines.join('<br>'); tip.style.display = 'block';
    const bx = box.offsetLeft, left = X(anchor) * (r.width / W);
    tip.style.top = (box.offsetTop + 8) + 'px';
    tip.style.left = (left > r.width / 2 ? bx + left - tip.offsetWidth - 14 : bx + left + 14) + 'px';
  };
}
function paintAllCharts() { Object.keys(CHARTS).forEach(paintChart); }

// ---------- forecast and season tables ----------
const MONTHS = ['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar'];
function seasonKeys() { const n = new Date(), y = n.getMonth() >= 6 ? n.getFullYear() : n.getFullYear() - 1; return MONTHS.map((m, i) => [m, (i < 3 ? y : y + 1) + '-' + String([10, 11, 12, 1, 2, 3][i]).padStart(2, '0')]); }
function seasonExpected(ref) {     // the written reference where it applies (Round Rock), otherwise this place's own weather history
  if (ref.applies !== false && (ref.climate || []).length) return { rows: ref.climate, src: 'ref' };
  if (ref.normals) return { rows: ref.normals.months, src: 'history', years: ref.normals.years, since: ref.normals.since };
  return { rows: [], src: 'none' };
}
// 1.34.0: the USDA hardiness zone (winter) and the AHS heat zone (summer) side by side, both from the place's own weather history
function climateBlock(W, H, P) {
  const Z = META && String(META.place.id) === String(W.location.id) ? META.zone : null;
  const winter = Z && Z.zone ? html`<p>The last ${Z.years} winters averaged a coldest night of <strong>${Z.winter_low}°F</strong>, which is <strong>USDA hardiness zone ${Z.zone}</strong> (how cold a usual winter gets, the zone on plant tags).${Z.map_note ? ' ' + Z.map_note : ''} <a href="${Z.map_url}" target="_blank" rel="noopener noreferrer">Look up a ZIP code on the USDA map</a>.</p>`
    : Z && Z.map_zone ? html`<p>Zone ${Z.map_zone} on the 2023 USDA map. The winter zone from your own weather history appears after 3 whole years of it.</p>`
    : html`<p class="muted">The winter zone from this place's weather history appears after 3 whole years of it.</p>`;
  if (!H) return html`${winter}<p class="muted">Summer heat could not be worked out.</p>`;
  const summer = H.zone ? html`<p>A usual year here has <strong>${H.over86} days above ${H.line}°F</strong>, which is <strong>AHS heat zone ${H.zone}</strong> of 12 (1 = cool summers, 12 = very hot), and its hottest day reaches about <strong>${H.hottest}°F</strong>. ${H.months.length ? `Hot days come ${H.months.length === 1 ? 'in ' + H.months[0].month : 'from ' + H.months[0].month + ' to ' + H.months[H.months.length - 1].month} (about ${H.months.map(m => `${m.days} in ${m.month}`).join(', ')}).` : ''}
      From ${H.years} whole years of weather (${H.since} on). Many plant tags give a heat zone range next to the hardiness zones; this is the number to compare it with.</p>`
    : html`<p class="muted">The summer heat zone appears after 3 whole years of weather history here${H.years ? ` (${H.years} so far)` : ''}.</p>`;
  const rows = (H.per_year || []).filter(y => !y.partial || y.over86);
  // 1.36.0: how the plants fare in a usual summer here, each count a link to the Plants page with the Summer here filter set
  const n = { hard: 0, few: 0, fine: 0, hotter: 0 };
  for (const x of Object.values((P && P.plants) || {})) { if (x.level) n[x.level]++; if (x.fit === 'hotter') n.hotter++; }
  const link = (k, count, words) => count ? html`<li><a href="#/plants" data-act="heatf" data-heatf="${k}">${count} plant${count === 1 ? '' : 's'}</a>: ${words}</li>` : '';
  const plantsPart = H.zone && (n.hard + n.few + n.fine + n.hotter) ? html`<h3>Your plants in a usual summer here</h3><ul class="heat-counts">${link('hard', n.hard, 'summer heat is hard on them (10 days or more reach the temperature where their leaves scorch)')}
      ${link('few', n.few, 'a few days a summer are too hot for them')}${link('fine', n.fine, 'summer heat is fine for them')}${link('hotter', n.hotter, `${H.place} is hotter than the AHS heat zones they are listed for`)}</ul>
      <p class="hint">Each link opens the Plants page with the "Summer here" filter set. Each plant's page has the details under About this plant.</p>` : '';
  return html`${winter}${summer}${plantsPart}
    ${rows.length ? html`<div class="tbl-wrap"><table class="tbl heat-tbl"><caption class="sr">Hot days each year in ${H.place}</caption>
      <thead><tr><th scope="col">Year</th><th scope="col">Days above ${H.line}°F</th><th scope="col">Hottest day</th></tr></thead>
      <tbody>${rows.map(y => html`<tr><th scope="row">${y.year}${y.partial ? ' (so far)' : ''}</th><td>${y.over86}</td><td>${y.hottest}°F</td></tr>`)}</tbody></table></div>` : ''}`;
}
function seasonTable(ref, monthly) {
  const obs = Object.fromEntries((monthly || []).map(x => [x.month, x]));
  const E = seasonExpected(ref), exp = Object.fromEntries(E.rows.map(c => [c.month, c]));
  const keys = seasonKeys();
  return html`<div class="tbl-wrap"><table class="tbl"><caption class="sr">Expected weather compared with the weather tracked so far this season</caption>
    <thead><tr><th>Month</th><th>Expected low and high</th><th>Tracked low and high</th><th>Expected freezing nights</th><th>Tracked freezing nights</th><th>Expected humidity</th><th>Tracked humidity</th></tr></thead><tbody>
    ${keys.map(([mo, key]) => { const e = exp[mo] || {}, o = obs[key];
      return html`<tr><th scope="row">${mo}</th><td>${e.low != null ? e.low + ' to ' + e.high + '°F' : ''}</td>
        <td>${o ? html`${o.low} to ${o.high}°F<div class="hint">${o.days} days tracked</div>` : html`<span class="muted">Not tracked yet</span>`}</td>
        <td>${e.freeze_nights != null ? e.freeze_nights + ' on average' : ''}</td><td>${o ? o.freeze_nights + (o.days < 28 ? ' so far' : '') : ''}</td>
        <td>${e.rh != null ? (e.rh_pm != null ? e.rh + '% morning, ' + e.rh_pm + '% afternoon' : e.rh + '% average') : ''}</td><td>${o && o.rh != null ? Math.round(o.rh) + '% average' : ''}</td></tr>`; })}</tbody></table></div>
    ${E.src === 'history' ? html`<p class="hint">Expected values for ${placeName()} are averages from its weather history since ${(E.since || '').slice(0, 4)} (${E.years} years or more of every month).</p>`
      : E.src === 'none' ? html`<p class="hint">There is not enough weather history for ${placeName()} yet to fill in the Expected columns. Use Load history on the Weather page (3 years or more).</p>` : ''}`;
}
function forecastBlock(W, plants) {
  const days = (W.forecast && W.forecast.days) || [];
  if (!days.length) return html`<p class="muted">No forecast yet. ${W.status && W.status.error ? 'The last attempt failed: ' + W.status.error : 'The first update runs a few seconds after the app starts, then every hour.'}</p>`;
  const risk = low => plants.filter(p => p.temp_damage_below != null && low < p.temp_damage_below && !isInside(p));
  const coldest = days.reduce((a, b) => (b.low < a.low ? b : a));
  const rs = risk(coldest.low);
  const dName = d => new Date(d + 'T12:00:00').toLocaleDateString([], { weekday: 'long', month: 'short', day: 'numeric' });
  return html`<p class="${coldest.low <= 32 ? 'notice bad' : coldest.low <= 38 ? 'notice' : 'notice ok'}" role="status"><strong>Coldest night in the forecast: ${coldest.low}°F on ${dName(coldest.date)}.</strong>
      ${coldest.low <= 32 ? ' That is a freeze.' : coldest.low <= 38 ? ' Frost is possible in low spots.' : ' No frost expected.'}
      ${rs.length ? ` ${rs.length} of ${plants.filter(p => !isInside(p)).length} plants outside would be damaged by that if they were left outside uncovered.` : ' None of your plants would be damaged by that.'}</p>
    <div class="tbl-wrap"><table class="tbl fc-table"><caption class="sr">Daily forecast</caption><thead><tr><th>Day</th><th class="num">Low</th><th class="num">High</th><th class="num">Humidity</th><th class="num">Daylight</th><th>Plants that would be damaged</th></tr></thead><tbody>
    ${days.map(d => { const r = risk(d.low); return html`<tr><th scope="row">${dName(d.date)}${d.hours < 20 ? html`<div class="hint">rest of the day</div>` : ''}</th>
      <td class="num ${d.low <= 32 ? 'cold' : ''}">${d.low}°F${d.low <= 32 ? ' (freeze)' : ''}</td><td class="num">${d.high}°F</td><td class="num">${d.rh == null ? '' : d.rh + '%'}</td><td class="num">${d.dli} mol/m²</td>
      <td>${r.length ? html`<details><summary>${r.length} plants</summary><ul>${r.map(p => html`<li><a href="#/plant/${enc(p.code)}">${p.common_name}</a>, damage below ${p.temp_damage_below}°F (${p.winter_plan})</li>`)}</ul></details>` : 'None'}</td></tr>`; })}</tbody></table></div>
    <p class="hint">Forecast from Open-Meteo, updated ${W.forecast.fetched_at ? when(W.forecast.fetched_at) : ''}. "Damaged" uses each plant's "damage below" temperature. A night's low can happen at dawn on the next calendar day.</p>`;
}

// ---------- weather page ----------
async function viewWeather(sec) {
  let W;
  try { W = await api('GET', '/api/weather?x=1' + locQS()); }
  catch (e) { if (e.status === 404) { savePlace(null); W = await api('GET', '/api/weather'); } else throw e; }
  const [cond, plants, ing, monthly, ref, st, heat, heatP] = await Promise.all([loadCond(), api('GET', '/api/plants'), (ME().role === 'owner' ? api('GET', '/api/ingest').catch(() => null) : null), api('GET', '/api/weather/monthly?x=1' + locQS()), api('GET', '/api/reference'), api('GET', '/api/settings'), api('GET', '/api/heat?x=1' + locQS()).catch(() => null), api('GET', '/api/heat/plants?x=1' + locQS()).catch(() => null)]);
  WX.places = W.places || []; WX.place = W.location; WX.home = W.home;
  WX.compare = WX.compare.filter(id => WX.places.some(p => String(p.id) === id && String(p.id) !== String(W.location.id)));
  const atHome = W.location.is_home;
  // 1.12.0: sensors send to their own port (8082), which only takes readings; it is closed until opened (README)
  const lanIp = /^\d+\.\d+\.\d+\.\d+$/.test(location.hostname) && !location.hostname.startsWith('127.') ? location.hostname : '';
  const netUrl = `http://${lanIp || '192.168.1.20'}:8082/api/readings`, url = 'http://localhost:8082/api/readings';
  const sample = '{"device":"porch","temp_f":71.2,"humidity":58,"par":240,"soil_moisture":31}';
  const S = W.status || {};
  return {
    title: 'Weather',
    html: html`<h1>Weather and sensors</h1>
    <div class="placebar noprint" role="group" aria-label="Place">
      <label>Location<select data-f="wxplace">${WX.places.map(p => html`<option value="${p.id}" ${String(p.id) === String(W.location.id) ? raw('selected') : ''}>${p.name}${p.is_home ? ' (home)' : ''}</option>`)}</select></label>
      <a class="btn small ghost" href="#sec-places" data-act="gotoplaces">Add or manage places</a>
      <span class="hint">Open-Meteo weather and your own sensors, kept in your data folder.${atHome ? '' : html` This is not the home place (${W.home.name}); the Location button at the top chooses it.`}</span></div>
    ${condCard(null, cond)}
    <section class="blk"><h2>Next 7 days in ${W.location.name}</h2>${forecastBlock(W, plants)}</section>
    <section class="blk"><h2>Tracked history</h2>
      ${wxControls(plants)}
      <div id="wx-charts"><p class="loading">Loading charts</p></div>
      <p class="hint">${W.weather.count ? `Online weather: ${W.weather.count.toLocaleString()} hourly readings from ${when(W.weather.first)}.` : 'No online weather stored yet.'}
        ${W.sensor.count ? ` Your sensor: ${W.sensor.count.toLocaleString()} readings from ${W.sensor.devices} device${W.sensor.devices === 1 ? '' : 's'}.` : ' No sensor readings yet (see Connect your sensor, below).'}</p></section>
    <section class="blk" id="wx-logged"><h2>All logged weather data${WX.places.length > 1 ? `: ${W.location.name}` : ''}</h2>
      <p class="hint">Every value saved so far, as a table. The first three columns (temperature, humidity, plant light) go back as far as your history does. The other measurements are kept hourly ${W.weather.detail_since ? 'from ' + dayLong(W.weather.detail_since) : 'once collected'} and as daily summaries for all of it.</p>
      ${wtControls()}<div id="wx-table"><p class="loading">Loading table</p></div></section>
    <section class="blk"><h2>Expected and tracked this season in ${W.location.name}</h2>${seasonTable(ref, monthly)}
      <p class="hint">${ref.applies !== false ? `Expected values are 30-year averages for ${W.location.name}. ` : ''}Tracked values come from the readings above: the average of each day's low and high, and how many nights fell to 32°F or below. Days with fewer than 12 readings are skipped.</p></section>
    <section class="blk" id="wx-climate"><h2>Your climate: winter cold and summer heat in ${W.location.name}</h2>${climateBlock(W, heat, heatP)}</section>
    ${ing ? html`<section class="blk" id="sensor"><h2>Connect your sensor</h2><p><a class="btn small ghost" href="#/sensors">Your sensors: newest values and alerts</a></p>
      <p>A sensor on your network can send readings to this app. Each reading becomes part of the history above, and "My sensor" can drive the current conditions on every plant page.</p>
      <div class="notice">Sensors on your home network send to this computer's network address on port 8082${lanIp ? '' : ' (for example 192.168.1.20; the README shows how to find yours)'}. That port only takes readings with the token below; the rest of the app stays closed. It is shut until you open it: put the line <span class="code">PLANTDB_SENSOR_BIND=0.0.0.0</span> in a file named .env next to docker-compose.yml, then run docker compose up -d (README, "Connecting your own sensor").</div>
      <dl class="dl"><dt>Address</dt><dd><span class="code">${netUrl}</span></dd><dt>Token</dt><dd><span class="code" id="tok">${ing.token}</span></dd></dl>
      <div class="row noprint" style="margin:.8rem 0"><button class="btn small" type="button" data-act="copytok">Copy token</button><button class="btn danger small" type="button" data-act="tokregen">Make a new token</button></div>
      <p>Send a POST with the header <span class="code">X-Ingest-Token</span> and a JSON body. Every field except one measurement is optional: <span class="code">device</span> (a name, such as porch), <span class="code">ts</span> (UTC time, otherwise now), <span class="code">temp_f</span> or <span class="code">temp_c</span>, <span class="code">humidity</span> (%), <span class="code">par</span> (µmol/m²/s) or <span class="code">lux</span>, <span class="code">soil_moisture</span> (%), <span class="code">soil_temp_f</span> or <span class="code">soil_temp_c</span>, <span class="code">soil_ph</span>. Send up to 500 at once as <span class="code">{"readings":[ ... ]}</span>. Lux is converted to PAR at 54 lux per PAR.</p>
      <h3>Try it from this computer</h3>
      <p>Windows (cmd.exe):</p><pre class="code">curl -X POST ${url} -H "X-Ingest-Token: ${ing.token}" -H "Content-Type: application/json" -d "{\\"device\\":\\"porch\\",\\"temp_f\\":71.2,\\"humidity\\":58,\\"par\\":240}"</pre>
      <p>Windows (PowerShell):</p><pre class="code">Invoke-RestMethod -Method Post -Uri ${url} -Headers @{"X-Ingest-Token"="${ing.token}"} -ContentType "application/json" -Body '${sample}'</pre>
      <p>macOS / Linux (bash):</p><pre class="code">curl -X POST ${url} -H "X-Ingest-Token: ${ing.token}" -H "Content-Type: application/json" -d '${sample}'</pre>
      <p class="hint">Anyone on your network who has the token can add readings, so keep it private. If it leaks, make a new token and update your sensor.</p></section>` : html`<section class="blk" id="sensor"><h2>Connect your sensor</h2><p class="muted">Only ${ME().owner_name} can see the sensor address and token.</p></section>`}
    <section class="blk" id="sec-places"><h2>Places</h2>${placesBlock(W)}</section>
    <section class="blk"><h2>Updates for ${W.location.name}</h2>
      <div id="wx-job" data-running="${W.job && W.job.running ? '1' : '0'}">${jobPanel(W.job)}</div>
      ${runSummary(W)}
      <p class="${S.ok ? 'hint' : S.error ? 'notice bad' : 'hint'}" role="status">${S.at ? html`Latest attempt of any kind ${when(S.at)}: ${S.ok ? 'worked.' : html`<strong>failed.</strong> ${S.error}`}` : 'No update has run yet.'}
        ${W.background ? '' : ' Automatic updates are switched off for this server.'} Weather and history use ${W.db_mb} MB of disk in your data folder.</p>
      <form data-form="wxloc"><div class="field-grid">
        <label class="f">Place name<input type="text" name="name" value="${W.location.name}" maxlength="60"></label>
        <label class="f">Latitude<input type="number" step="any" name="lat" value="${W.location.lat}" min="-90" max="90"></label>
        <label class="f">Longitude<input type="number" step="any" name="lon" value="${W.location.lon}" min="-180" max="180"></label>
        <label class="f">Time zone<input type="text" name="tz" value="${W.location.tz}"></label>
        <label class="f">Years of full hourly detail to keep<small>Every measurement hourly for this many recent years. Older years keep temperature, humidity and light hourly, and everything as daily summaries. Larger numbers use more disk, about 10 MB per year.</small><input type="number" name="detail_years" min="0" max="90" value="${W.weather.detail_years}"></label></div>
        <label class="chk-row" style="border:0"><input type="checkbox" name="enabled" ${W.enabled ? raw('checked') : ''}><span>Update ${W.location.name} every hour</span></label>
        <div class="row"><button class="btn" type="submit">Save this place</button><button class="btn ghost" type="button" data-act="wxrefresh">Update ${W.location.name} now</button>${WX.places.length > 1 ? html`<button class="btn ghost" type="button" data-act="wxrefresh" data-all="1">Update every place now</button>` : ''}</div></form>
      <form data-form="wxback" style="margin-top:1.6rem"><label class="f" style="max-width:24rem">Load older weather history from this date<small>The first update already loads the last 3 months. Pick an earlier date, such as 2025-10-01, to bring in last winter. Open-Meteo's history starts on 1940-01-01. It takes about half a minute per year of history and keeps running if you leave the page. Loading again never duplicates anything.</small><input type="date" name="start" min="1940-01-01" max="${new Date().toISOString().slice(0, 10)}"></label>
        <button class="btn ghost" type="submit">Load history for ${W.location.name}</button></form>
      <details class="runlog" id="wx-runlog" style="margin-top:1.4rem"><summary>Every update that has run (log)</summary><div id="wx-runs"><p class="loading">Loading</p></div></details></section>
    <p class="hint">Weather data by <a href="https://open-meteo.com/" target="_blank" rel="noopener noreferrer">Open-Meteo.com</a>. Light is estimated from solar radiation at about 2.1 PAR per W/m².</p>`,
    after: () => { wxCatalog().then(loadWxCharts); loadWxTable(); loadRunLog(); if (W.job && W.job.running) wxPoll(); },
  };
}
const locQS = () => PLACE ? '&loc=' + enc(PLACE) : '';     // the Weather page shows the place in use (1.11.0)
const WX = { days: 7, period: '7', from: '', to: '', src: 'both', plant: '', show: ['temp', 'hum', 'light'], vars: [], cols: 1, compare: [], places: [] };
try { const v = JSON.parse(localStorage.getItem('plantdb.wxchart') || 'null'); if (v) Object.assign(WX, { period: v.period || '7', from: v.from || '', to: v.to || '', show: Array.isArray(v.show) ? v.show : WX.show, vars: Array.isArray(v.vars) ? v.vars : [], cols: [1, 2, 3].includes(+v.cols) ? +v.cols : 1, compare: Array.isArray(v.compare) ? v.compare.map(String) : [] }); } catch (e) { /* ignore */ }
if (/^\d+$/.test(WX.period)) WX.days = +WX.period;
function wxSave() { try { localStorage.setItem('plantdb.wxchart', JSON.stringify({ period: WX.period, from: WX.from, to: WX.to, show: WX.show, vars: WX.vars, cols: WX.cols, compare: WX.compare })); } catch (e) { /* ignore */ } }
const WX_PERIODS = [['1', 'Last 24 hours'], ['3', 'Last 3 days'], ['7', 'Last 7 days'], ['14', 'Last 14 days'], ['30', 'Last 30 days'], ['90', 'Last 90 days'], ['365', 'Last year'], ['1096', 'Last 3 years'], ['3653', 'Last 10 years'], ['all', 'Everything logged'], ['custom', 'Pick dates']];
const WX_CORE = [['temp', 'Temperature'], ['hum', 'Humidity'], ['light', 'Light (PAR, or daily light)']];
const DAILY_SKIP = ['sunrise', 'sunset'];
let WXCAT = null;
const catOf = k => (WXCAT || []).find(c => c.key === k);
const isDailyKey = k => { const c = (WXCAT || []).filter(x => x.key === k); return c.length && c.every(x => x.kind === 'daily'); };
async function wxCatalog() {
  if (WXCAT) return;
  try { WXCAT = await api('GET', '/api/weather/catalog'); const el = document.getElementById('wx-pick'); if (el) el.innerHTML = rend(wxPickInner()); } catch (e) { /* ignore */ }
}
function wxRangeQS() { return WX.period === 'custom' ? `from=${WX.from || ''}&to=${WX.to || ''}` : WX.period === 'all' ? 'from=1940-01-01' : 'days=' + WX.days; }
function grpBtns(cs) {
  const keys = cs.map(c => c.key).join(',');
  return html`<div class="row grpbtns"><button class="btn small ghost" type="button" data-act="wxgroup" data-keys="${keys}" data-on="1">Tick all</button><button class="btn small ghost" type="button" data-act="wxgroup" data-keys="${keys}" data-on="0">Untick all</button></div>`;
}
function wxPickInner() {
  const box = (key, label, checked, f) => html`<label class="chk-row" style="border:0;padding:.3rem 0"><input type="checkbox" data-f="${f}" data-key="${key}" ${checked ? raw('checked') : ''}><span>${label}</span></label>`;
  const groups = {}, daily = {};
  for (const c of WXCAT || []) {
    if (c.kind === 'hourly' && !['temperature_2m', 'relative_humidity_2m'].includes(c.key)) (groups[c.group] = groups[c.group] || []).push(c);
    if (c.kind === 'daily' && !DAILY_SKIP.includes(c.key) && !(WXCAT || []).some(x => x.kind === 'hourly' && x.key === c.key)) (daily[c.group] = daily[c.group] || []).push(c);
  }
  const lbl = c => c.label + (c.unit ? ' (' + c.unit + ')' : '');
  return html`<fieldset><legend>Main charts</legend>${WX_CORE.map(([k, l]) => box(k, l, WX.show.includes(k), 'wxshow'))}</fieldset>
    ${WXCAT ? html`${Object.entries(groups).map(([g, cs]) => html`<fieldset><legend>${g} (hourly)</legend>${grpBtns(cs)}${cs.map(c => box(c.key, lbl(c), WX.vars.includes(c.key), 'wxvar'))}</fieldset>`)}
      <details class="colpick"><summary>Daily summary values</summary>${Object.entries(daily).map(([g, cs]) => html`<fieldset><legend>${g} (one value per day)</legend>${grpBtns(cs)}${cs.map(c => box(c.key, lbl(c), WX.vars.includes(c.key), 'wxvar'))}</fieldset>`)}</details>` : html`<p class="loading">Loading the list of measurements</p>`}`;
}
let WXBAR = null;               // folded or not for this visit; starts folded on narrow windows and with very large text
function wxBarOpen() { return WXBAR != null ? WXBAR : document.documentElement.dataset.narrow !== '1'; }
function wxControls(plants) {
  const sel = (v, cur) => String(v) === String(cur) ? raw('selected') : '';
  const open = wxBarOpen();
  return html`<div class="wx-bar noprint" id="wx-bar" role="region" aria-label="Chart settings">
    <div class="wx-bar-top"><button class="btn small" type="button" data-act="wxbar" aria-expanded="${open ? 'true' : 'false'}" aria-controls="wx-barbody" id="wx-barbtn">${open ? 'Hide chart settings' : 'Show chart settings'}</button>
      <button class="btn small ghost" type="button" data-act="wxpanel" aria-expanded="false" aria-controls="wx-panel" id="wx-panelbtn">Choose what to chart${WX.places.length > 1 ? ' and compare places' : ''} (<span id="wx-pickcount">${WX.show.length + WX.vars.length}</span>${WX.compare.length ? `, comparing ${WX.compare.length + 1} places` : ''})</button>
      <span class="wx-summary hint" id="wx-sum" role="status"></span></div>
    <div id="wx-barbody" ${open ? '' : raw('hidden')}>
    <div class="wx-bar-row">
      <label>Period<select data-f="wxperiod">${WX_PERIODS.map(([v, l]) => html`<option value="${v}" ${sel(v, WX.period)}>${l}</option>`)}</select></label>
      <span id="wx-dates" class="wx-bar-row" ${WX.period === 'custom' ? '' : raw('hidden')}><label>From<input type="date" data-f="wxfrom" min="1940-01-01" value="${WX.from}"></label><label>To<input type="date" data-f="wxto" min="1940-01-01" value="${WX.to}"></label></span>
      <label>Source<select data-f="wxsrc">${[['both', 'Online weather + my sensor'], ['weather', 'Online weather'], ['sensor', 'My sensor']].map(([v, l]) => html`<option value="${v}" ${sel(v, WX.src)}>${l}</option>`)}</select></label>
      <span class="row-break" aria-hidden="true"></span>
      <label>Plant range<select data-f="wxplant" class="w-fixed" title="Show a plant's comfortable range on the charts"><option value="">None</option>${plants.map(p => html`<option value="${p.code}" ${sel(p.code, WX.plant)} title="${p.code} ${p.common_name}">${p.code} ${p.common_name}</option>`)}</select></label>
      <label>Go to chart<select data-f="wxgoto" id="wx-goto" class="w-fixed"><option value="">Choose a chart</option></select></label>
      <label>Per row<select data-f="wxcols" title="Charts per row">${[1, 2, 3].map(n => html`<option value="${n}" ${sel(n, WX.cols)}>${n}</option>`)}</select></label>
    </div></div>
    <div class="wx-panel" id="wx-panel" hidden>
      <div class="row" style="margin:.2rem 0 .4rem"><button class="btn small" type="button" data-act="wxpanel">Close this list</button><button class="btn small ghost" type="button" data-act="wxmatch">Use the dates and columns from the table below</button><button class="btn small ghost" type="button" data-act="wxclearvars">Remove the extra measurements</button></div>
      <p class="hint">Tick as many as you like; the charts update a moment after you stop. Measurements with the same unit share a chart (three per chart at most). Many measurements over a long period can take several seconds to draw.</p>
      <div class="row" style="margin:.4rem 0"><button class="btn small ghost" type="button" data-act="wxallvars" data-which="hourly">Tick every hourly measurement</button><button class="btn small ghost" type="button" data-act="wxallvars" data-which="daily">Tick every daily summary value</button></div>
      ${WX.places.length > 1 ? html`<fieldset class="cmp-places"><legend>Compare ${WX.place ? WX.place.name : 'this place'} with</legend><p class="hint" style="grid-column:1/-1;margin:0">Each chart gets one line per place (up to 6 places).</p>${WX.places.filter(p => String(p.id) !== String((WX.place || {}).id)).map(p => html`<label class="chk-row" style="border:0;padding:.3rem 0"><input type="checkbox" data-f="wxcmp" data-key="${p.id}" ${WX.compare.includes(String(p.id)) ? raw('checked') : ''}><span>${p.name}${p.is_home ? ' (home)' : ''}</span></label>`)}</fieldset>` : ''}
      <div id="wx-pick">${wxPickInner()}</div></div></div>`;
}
const BUCKET_WORDS = { hour: 'hourly', day: 'daily', week: 'weekly', month: 'monthly' };
async function seriesMulti(base, vars) {
  // web addresses have a length limit, so many measurements are fetched 30 at a time and joined back together
  if (vars.length <= 30) return api('GET', base + (vars.length ? '&vars=' + vars.join(',') : ''));
  const parts = [];
  for (let i = 0; i < vars.length; i += 30) parts.push(vars.slice(i, i + 30));
  const res = await Promise.all(parts.map(p => api('GET', base + '&vars=' + p.join(','))));
  const out = res[0], byT = new Map(out.points.map(p => [p.t, p]));
  for (const r of res.slice(1)) {
    Object.assign(out.vars, r.vars);
    for (const p of r.points) { const q = byT.get(p.t); if (q) q.x = Object.assign(q.x || {}, p.x); else { out.points.push(p); byT.set(p.t, p); } }
  }
  out.points.sort((a, b) => a.t < b.t ? -1 : 1);
  return out;
}
function finishCharts(el, cards, sources, bucket, keepY, done, extraNote) {
  const ts = sources.filter(Boolean).flatMap(r => r.points.map(p => Date.parse(p.t)));
  const span = ts.length ? [Math.min(...ts), Math.max(...ts)] : null;
  const dfmt = t => new Date(t).toLocaleDateString([], { dateStyle: 'medium' });
  const sum = document.getElementById('wx-sum');
  done(); el.className = 'cols-' + WX.cols;
  el.innerHTML = rend(html`<div class="wx-grid">${cards.length ? cards : html`<p class="notice">Nothing chosen. Press "Choose what to chart" and tick at least one measurement.</p>`}</div>`);
  if (sum) sum.textContent = (span ? `Data shown: ${dfmt(span[0])} to ${dfmt(span[1])}. ` : 'No data in this period. ') + (bucket === 'hour' ? 'One point per hour. ' : `One point per ${bucket} (${BUCKET_WORDS[bucket]} values). `) + (extraNote || '') + `${el.querySelectorAll('.chart-card').length} charts.`;
  const go = document.getElementById('wx-goto');
  if (go) go.innerHTML = rend(html`<option value="">Choose a chart</option>${[...el.querySelectorAll('.chart-card h3')].map(h => html`<option value="${h.closest('.chart-card').getAttribute('aria-labelledby')}">${h.textContent}</option>`)}`);
  paintAllCharts(); navLayout();
  requestAnimationFrame(() => { el.style.minHeight = ''; if (Math.abs(window.scrollY - keepY) > 2) window.scrollTo(0, keepY); });
}
function drawCompare(el, o) {
  // one line per place on every chart; your sensor joins in when the home place is one of them
  const placesR = [{ name: o.here.name, r: o.w, d: o.dx }, ...o.others.map((p, i) => ({ name: p.name, r: o.cmp[i], d: o.cmpd[i] }))];
  const bucket = (o.w || o.cmp[0] || {}).bucket || 'hour', day = bucket !== 'hour', per = BUCKET_WORDS[bucket];
  const col = (r, k) => r ? r.points.filter(p => p[k] != null).map(p => [Date.parse(p.t), p[k]]) : [];
  const dli = r => r ? r.points.filter(p => p.par != null && (bucket !== 'day' || p.n >= 12)).map(p => [Date.parse(p.t), Math.round(p.par * 86400 / 1e5) / 10]) : [];
  const withSensor = (list, pts) => (o.s && pts.length ? [...list, { name: 'My sensor', pts }] : list);
  const colour = list => list.map((x, i) => ({ ...x, cls: 's' + (i % 6 + 1) }));
  const band = (lo, hi, label) => has(lo) && has(hi) ? [{ lo, hi, label }] : [];
  const pl = o.pl, nm = pl ? pl.common_name : '';
  const cards = [];
  const avg = day ? `, ${per} average` : '';
  if (WX.show.includes('temp')) {
    const refs = [{ v: 32, label: 'Freezing (32°F)' }];
    if (pl && has(pl.temp_damage_below)) refs.push({ v: pl.temp_damage_below, label: `${nm}: damage below ${pl.temp_damage_below}°F` });
    cards.push(chartCard('wx-temp', { title: `Temperature (°F${avg})`, series: colour(withSensor(placesR.map(p => ({ name: p.name, pts: col(p.r, 'temp_f') })), col(o.s, 'temp_f'))), fmt: v => String(Math.round(v * 10) / 10), unit: '°F', refs, bands: pl ? band(pl.temp_ideal_low, pl.temp_ideal_high, nm + ': comfortable range') : [], daily: day }));
    if (day) {
      cards.push(chartCard('wx-tlow', { title: `Lowest temperature in each ${bucket} (°F)`, series: colour(placesR.map(p => ({ name: p.name, pts: col(p.r, 'temp_min') }))), fmt: v => String(Math.round(v * 10) / 10), unit: '°F', refs, daily: day }));
      cards.push(chartCard('wx-thigh', { title: `Highest temperature in each ${bucket} (°F)`, series: colour(placesR.map(p => ({ name: p.name, pts: col(p.r, 'temp_max') }))), fmt: v => String(Math.round(v * 10) / 10), unit: '°F', daily: day }));
    }
  }
  if (WX.show.includes('hum')) cards.push(chartCard('wx-hum', { title: `Humidity (%${avg})`, series: colour(withSensor(placesR.map(p => ({ name: p.name, pts: col(p.r, 'humidity') })), col(o.s, 'humidity'))), fmt: v => String(Math.round(v)), unit: '%', clamp: [0, 100], bands: pl ? band(pl.humidity_low, pl.humidity_high, nm + ': comfortable range') : [], daily: day }));
  if (WX.show.includes('light')) cards.push(chartCard('wx-light', day ? { title: 'Daily light (mol/m² per day; open sky)', series: colour(withSensor(placesR.map(p => ({ name: p.name, pts: dli(p.r) })), dli(o.s))), fmt: v => String(Math.round(v * 10) / 10), unit: ' mol/m²', zero: true, bands: pl ? band(pl.dli_low, pl.dli_high, nm + ': comfortable range') : [], daily: day }
    : { title: 'Light (PAR, µmol/m²/s)', series: colour(withSensor(placesR.map(p => ({ name: p.name, pts: col(p.r, 'par') })), col(o.s, 'par'))), fmt: v => String(Math.round(v * 10) / 10), unit: ' PAR', zero: true, daily: day }));
  let ci = 0;
  for (const [key, isD] of [...o.hourlyVars.map(k => [k, false]), ...o.dailyVars.map(k => [k, true])]) {
    const src = placesR.map(p => isD ? p.d : p.r), m = (src.find(r => r && r.vars && r.vars[key]) || { vars: {} }).vars[key] || { label: key, unit: '', agg: 'avg' };
    const how = bucket === 'hour' && !isD ? '' : ` (${per} ${m.agg === 'sum' ? 'total' : m.agg === 'max' && !isD ? 'highest' : 'average'})`;
    const series = colour(placesR.map((p, i) => ({ name: p.name, pts: src[i] ? src[i].points.filter(q => q.x && q.x[key] != null).map(q => [Date.parse(q.t), q.x[key]]) : [] })));
    const zero = !/temperature|dew|wet_bulb|apparent|pressure|direction|lifted|height/.test(key);
    cards.push(chartCard('wx-x' + (ci++), { title: m.label + how + (m.unit ? ` (${m.unit})` : ''), series, fmt: v => String(Math.round(v * 100) / 100), unit: m.unit ? ' ' + m.unit : '', zero, daily: day || isD }));
    const empty = series.filter(x => !x.pts.length);
    if (empty.length) cards.push(html`<p class="hint">No ${m.label.toLowerCase()} values for ${empty.map(x => x.name).join(' or ')} in this period. Show that place and use Load history to fetch them.</p>`);
  }
  finishCharts(el, cards, [o.w, o.s, o.dx, ...o.cmp], bucket, o.keepY, o.done, `Comparing ${placesR.map(p => p.name).join(', ')}. `);
}
async function loadWxCharts() {
  const el = document.getElementById('wx-charts'); if (!el) return;
  if (WX.period === 'custom' && (!WX.from || !WX.to)) { el.innerHTML = rend(html`<p class="notice">Pick a From and a To date.</p>`); return; }
  if (WX.period === 'custom' && WX.from > WX.to) { el.innerHTML = rend(html`<p class="notice bad">The From date is after the To date.</p>`); return; }
  const sm = document.getElementById('wx-sum'); if (sm) sm.textContent = 'Loading charts…';
  // Keep the current charts on screen (dimmed) while the new ones load, so the page does not shrink and jump.
  const myReq = WX.req = (WX.req || 0) + 1, keepY = window.scrollY;
  if (el.querySelector('.chart-card')) { el.style.minHeight = el.offsetHeight + 'px'; el.classList.add('busy'); el.setAttribute('aria-busy', 'true'); }
  else el.innerHTML = rend(html`<p class="loading" role="status">Loading charts${WX.period === 'all' || +WX.days > 3000 ? ' (a long period can take a few seconds)' : ''}</p>`);
  const done = () => { el.classList.remove('busy'); el.removeAttribute('aria-busy'); };
  const want = s => WX.src === 'both' || WX.src === s;
  const rq = wxRangeQS();
  const hourlyVars = WX.vars.filter(k => !isDailyKey(k)), dailyVars = WX.vars.filter(isDailyKey);
  let w, s, pl, dx, cmp = [];
  const others = (WX.compare || []).map(id => WX.places.find(p => String(p.id) === id)).filter(Boolean);
  const here = WX.place || { name: 'Online weather', is_home: true };
  try {
    [w, s, pl, ...cmp] = await Promise.all([want('weather') || WX.vars.length || others.length ? seriesMulti(`/api/readings/series?source=weather&${rq}${locQS()}`, hourlyVars) : null,
      want('sensor') && here.is_home ? api('GET', '/api/readings/series?source=sensor&' + rq) : null, WX.plant ? api('GET', '/api/plants/' + enc(WX.plant)) : null,
      ...others.map(o => seriesMulti(`/api/readings/series?source=weather&${rq}&loc=${o.id}`, hourlyVars))]);
    const bk = (w || s || cmp[0]).bucket === 'hour' ? 'day' : (w || s || cmp[0]).bucket;
    if (dailyVars.length) [dx, ...cmp.dx] = await Promise.all([seriesMulti(`/api/readings/series?source=weather&${rq}&bucket=${bk}${locQS()}`, dailyVars), ...others.map(o => seriesMulti(`/api/readings/series?source=weather&${rq}&bucket=${bk}&loc=${o.id}`, dailyVars))]);
  } catch (e) { if (myReq !== WX.req) return; done(); el.style.minHeight = ''; el.innerHTML = rend(html`<p class="notice bad">${e.message}</p>`); return; }
  if (myReq !== WX.req) return;                 // a newer choice was made while this one loaded
  if (others.length) return drawCompare(el, { w, s, pl, dx, cmp, cmpd: cmp.dx || [], others, here, hourlyVars, dailyVars, keepY, done });
  const wCore = want('weather') ? w : null;
  const bucket = ((w || s) || {}).bucket || 'hour', day = bucket !== 'hour';
  const both = !!(wCore && s);
  const col = (r, k, f) => r.points.filter(p => p[k] != null && (!f || f(p))).map(p => [Date.parse(p.t), p[k]]);
  const mk = (key, names) => { const out = []; const sp = s ? col(s, key) : []; if (s && (sp.length || !wCore)) out.push({ name: names.sensor, cls: 's1', pts: sp }); if (wCore) out.push({ name: names.weather, cls: 's2', pts: col(wCore, key) }); return out; };
  const N = { weather: WX.places.length > 1 ? `Online weather, ${here.name}` : 'Online weather', sensor: 'My sensor' };
  const per = { day: 'Daily', week: 'Weekly', month: 'Monthly' }[bucket] || '';
  let tempSeries;
  if (day && !both) { const r = wCore || s; tempSeries = r ? [{ name: bucket === 'day' ? 'Daily low' : `Lowest in the ${bucket}`, cls: 's1', pts: col(r, 'temp_min') }, { name: bucket === 'day' ? 'Daily high' : `Highest in the ${bucket}`, cls: 's2', pts: col(r, 'temp_max') }] : []; }
  else tempSeries = mk('temp_f', N);
  const band = (lo, hi, label) => has(lo) && has(hi) ? [{ lo, hi, label }] : [];
  const nm = pl ? pl.common_name : '';
  const refs = [{ v: 32, label: 'Freezing (32°F)' }];
  if (pl && has(pl.temp_damage_below)) refs.push({ v: pl.temp_damage_below, label: `${nm}: damage below ${pl.temp_damage_below}°F` });
  const cards = [];
  if ((wCore || s) && WX.show.includes('temp')) cards.push(chartCard('wx-temp', { title: 'Temperature (°F)' + (per && both ? `, ${per.toLowerCase()} average` : ''), series: tempSeries, fmt: v => String(Math.round(v * 10) / 10), unit: '°F', refs, bands: pl ? band(pl.temp_ideal_low, pl.temp_ideal_high, nm + ': comfortable range') : [], daily: day }));
  if ((wCore || s) && WX.show.includes('hum')) cards.push(chartCard('wx-hum', { title: 'Humidity (%)' + (per ? `, ${per.toLowerCase()} average` : ''), series: mk('humidity', N), fmt: v => String(Math.round(v)), unit: '%', clamp: [0, 100], bands: pl ? band(pl.humidity_low, pl.humidity_high, nm + ': comfortable range') : [], daily: day }));
  if ((wCore || s) && WX.show.includes('light')) {
    const dli = r => r.points.filter(p => p.par != null && (bucket !== 'day' || p.n >= 12)).map(p => [Date.parse(p.t), Math.round(p.par * 86400 / 1e5) / 10]);
    const lightSeries = day ? [s && (dli(s).length || !wCore) && { name: N.sensor, cls: 's1', pts: dli(s) }, wCore && { name: N.weather, cls: 's2', pts: dli(wCore) }].filter(Boolean) : mk('par', N);
    cards.push(chartCard('wx-light', { title: day ? `Daily light (mol/m² per day${bucket !== 'day' ? `, average over each ${bucket}` : ''}; open sky for online weather)` : 'Light (PAR, µmol/m²/s)', series: lightSeries, fmt: v => String(Math.round(v * 10) / 10), unit: day ? ' mol/m²' : ' PAR', zero: true,
      bands: pl ? (day ? band(pl.dli_low, pl.dli_high, nm + ': comfortable range') : band(pl.par_low, pl.par_high, nm + ': comfortable range')) : [], daily: day }));
  }
  // extra measurements, grouped by unit, three to a chart
  const extras = [];
  for (const [res, keys] of [[w, hourlyVars], [dx, dailyVars]]) {
    if (!res) continue;
    for (const k of keys) {
      const m = (res.vars || {})[k] || { label: k, unit: '', agg: 'avg' };
      const how = res.bucket === 'hour' ? '' : m.agg === 'sum' ? `${BUCKET_WORDS[res.bucket]} total` : m.agg === 'max' ? `${BUCKET_WORDS[res.bucket]} highest` : `${BUCKET_WORDS[res.bucket]} average`;
      extras.push({ key: k, unit: m.unit || '', name: m.label + (how && !isDailyKey(k) ? ` (${how})` : isDailyKey(k) && res.bucket !== 'day' ? ` (${BUCKET_WORDS[res.bucket]} ${m.agg === 'sum' ? 'total' : 'average'})` : ''), daily: res.bucket !== 'hour', fromDaily: m.from_daily,
        pts: res.points.filter(p => p.x && p.x[k] != null).map(p => [Date.parse(p.t), p.x[k]]) });
    }
  }
  const byUnit = {};
  extras.forEach(x => (byUnit[x.unit + '|' + x.daily] = byUnit[x.unit + '|' + x.daily] || []).push(x));
  let ci = 0;
  for (const list of Object.values(byUnit)) {
    for (let i = 0; i < list.length; i += 3) {
      const part = list.slice(i, i + 3), u = part[0].unit;
      const zero = !part.some(x => /temperature|dew|wet_bulb|apparent|pressure|direction|lifted|height/.test(x.key));
      cards.push(chartCard('wx-x' + (ci++), { title: part.map(x => x.name).join(', ') + (u ? ` (${u})` : ''), series: part.map((x, j) => ({ name: x.name, cls: 's' + (j + 1), pts: x.pts })), fmt: v => String(Math.round(v * 100) / 100), unit: u ? ' ' + u : '', zero, daily: part[0].daily }));
      const empty = part.filter(x => !x.pts.length), daily2 = part.filter(x => x.fromDaily);
      if (empty.length) cards.push(html`<p class="hint">No values for ${empty.map(x => x.name).join(', ')} in this period. Use Load history to fetch them; the table below shows what is stored.</p>`);
      if (daily2.length) cards.push(html`<p class="hint">For older years ${daily2.map(x => x.name).join(', ')} come${daily2.length === 1 ? 's' : ''} from the daily summaries, because hourly detail is only kept for recent years.</p>`);
    }
  }
  const ts = [w, s, dx].filter(Boolean).flatMap(r => r.points.map(p => Date.parse(p.t)));
  const span = ts.length ? [Math.min(...ts), Math.max(...ts)] : null;
  const dfmt = t => new Date(t).toLocaleDateString([], { dateStyle: 'medium' });
  const sum = document.getElementById('wx-sum');
  if (sum) sum.textContent = (span ? `Data shown: ${dfmt(span[0])} to ${dfmt(span[1])}. ` : 'No data in this period. ') + (bucket === 'hour' ? 'One point per hour. ' : `One point per ${bucket} (${BUCKET_WORDS[bucket]} values). `);
  done(); el.className = 'cols-' + WX.cols;
  el.innerHTML = rend(html`<div class="wx-grid">${cards.length ? cards : html`<p class="notice">Nothing chosen. Press "Choose what to chart" and tick at least one measurement.</p>`}${s && s.points.length === 0 && want('sensor') ? html`<p class="hint">No sensor readings in this period yet.</p>` : ''}</div>`);
  const go = document.getElementById('wx-goto');
  if (go) go.innerHTML = rend(html`<option value="">Choose a chart</option>${[...el.querySelectorAll('.chart-card h3')].map(h => html`<option value="${h.closest('.chart-card').getAttribute('aria-labelledby')}">${h.textContent}</option>`)}`);
  if (sum) sum.textContent += `${el.querySelectorAll('.chart-card').length} charts.`;
  paintAllCharts(); navLayout();
  requestAnimationFrame(() => { el.style.minHeight = ''; if (Math.abs(window.scrollY - keepY) > 2) window.scrollTo(0, keepY); });   // stay where you were
}

// ---------- places ----------
function placesBlock(W) {
  const P = W.places || [];
  return html`<p>Track the weather for as many places as you like. Each place keeps its own hourly readings, daily summaries, forecast and update log. The <strong>Location</strong> button at the top of every page chooses the place this browser uses for weather, frost warnings, watering and the Winter plan. The home place is the one a browser starts with, and the one hourly updates and backups use.</p>
    <div class="tbl-wrap"><table class="tbl"><caption class="sr">Places with tracked weather</caption><thead><tr><th scope="col">Place</th><th scope="col">Where</th><th scope="col">Stored</th><th scope="col">Last update</th><th scope="col">Hourly updates</th><th scope="col">Plants</th><th scope="col"><span class="sr">Actions</span></th></tr></thead><tbody>
    ${P.map(p => html`<tr><th scope="row">${p.name}${p.is_home ? html`<div><strong class="tag-home">Main home</strong></div>` : p.plants_here ? html`<div><strong class="tag-home">Home</strong></div>` : ''}${String(p.id) === String(W.location.id) ? html`<div class="hint">In use in this browser</div>` : ''}</th>
      <td>${p.lat}, ${p.lon}<div class="hint">${p.tz}</div></td>
      <td>${p.count ? `${num(p.count)} hourly readings from ${dayLong((p.first || '').slice(0, 10))}` : 'Nothing yet'}${p.daily_count ? html`<div class="hint">${num(p.daily_count)} daily summaries</div>` : ''}</td>
      <td>${p.last_update ? html`${when(p.last_update)}${p.last_ok === false ? html`<div class="bad-text"><strong>Failed:</strong> ${p.last_error}</div>` : ''}` : 'Not yet'}</td>
      <td>${p.enabled ? 'On' : 'Off'}</td>
      <td>${p.plants_here ? `Plants live here: ${num(p.plant_count || 0)}` : 'No plants (weather only)'}</td>
      <td><div class="row" style="gap:.4rem">
        ${String(p.id) === String(W.location.id) ? '' : html`<button class="btn small" type="button" data-act="placeshow" data-id="${p.id}">Use this place</button>`}
        ${p.is_home ? '' : html`<button class="btn small ghost" type="button" data-act="placehome" data-id="${p.id}">Make main home</button>`}
        ${p.is_home ? '' : html`<button class="btn small ghost" type="button" data-act="placeplants" data-id="${p.id}" data-on="${p.plants_here ? '0' : '1'}">${p.plants_here ? 'No plants live here' : 'Plants live here'}</button>`}
        <button class="btn small ghost" type="button" data-act="placeonoff" data-id="${p.id}" data-on="${p.enabled ? '0' : '1'}">${p.enabled ? 'Stop hourly updates' : 'Start hourly updates'}</button>
        ${p.is_home ? '' : html`<button class="btn small danger" type="button" data-act="placedel" data-id="${p.id}" aria-label="Remove the place ${p.name}">Remove</button>`}</div></td></tr>`)}</tbody></table></div>
    <h3>Add a place</h3>
    <form class="todo-add" data-form="placesearch"><label style="flex:1 1 18rem;font-weight:700">Town or city<input type="text" name="q" placeholder="Baraboo" autocomplete="off"></label><button class="btn" type="submit" style="align-self:end">Search</button></form>
    <div id="place-results" aria-live="polite"></div>
    <details class="colpick"><summary>Or type the place in yourself</summary>
      <form data-form="placeadd"><div class="field-grid">
        <label class="f">Name<input type="text" name="name" maxlength="60" required></label>
        <label class="f">Latitude<input type="number" step="any" name="lat" min="-90" max="90" required></label>
        <label class="f">Longitude<input type="number" step="any" name="lon" min="-180" max="180" required></label>
        <label class="f">Time zone<small>For example America/Chicago</small><input type="text" name="tz" value="${(W.home || {}).tz || ''}" required></label></div>
        <button class="btn" type="submit">Add this place</button></form></details>
    <p class="hint">A new place gets its last 3 months and forecast straight away, then updates every hour. Use Load history (below, with that place shown) for older years.</p>`;
}
async function addPlace(body) {
  if (!(await needName())) return;
  await guard(async () => {
    let r;
    try { r = await api('POST', '/api/places', body); }
    catch (e) { if (e.status === 409 && (await confirmBox('Add it anyway?', e.message + '. Add a second place at the same spot?', 'Add anyway'))) r = await api('POST', '/api/places', { ...body, force: true }); else throw e; }
    placeChanged(String(r.place.id));
    toast(`${r.place.name} added and in use. Fetching its last 3 months and forecast now.`);
    document.body.dataset.job = '1'; await route(); wxPoll();
  });
}
function setPlace(id) {
  placeChanged(id);
  return route();
}

// ---------- weather: update log and the table of everything logged ----------
const WMO = { 0: 'Clear', 1: 'Mostly clear', 2: 'Partly cloudy', 3: 'Overcast', 45: 'Fog', 48: 'Freezing fog', 51: 'Light drizzle', 53: 'Drizzle', 55: 'Heavy drizzle', 56: 'Freezing drizzle', 57: 'Heavy freezing drizzle',
  61: 'Light rain', 63: 'Rain', 65: 'Heavy rain', 66: 'Freezing rain', 67: 'Heavy freezing rain', 71: 'Light snow', 73: 'Snow', 75: 'Heavy snow', 77: 'Snow grains', 80: 'Light showers', 81: 'Showers', 82: 'Heavy showers',
  85: 'Light snow showers', 86: 'Heavy snow showers', 95: 'Thunderstorm', 96: 'Thunderstorm with hail', 99: 'Severe thunderstorm with hail' };
const TRIGGER_WORDS = { auto: 'Automatic (hourly)', 'auto-first': 'Automatic (first run)', 'update-now': 'You pressed Update now', 'load-history': 'You pressed Load history', earlier: 'Before logging began' };
const compass = d => ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'][Math.round(d / 22.5) % 16];
const dayLong = d => d ? new Date(d + 'T12:00:00').toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' }) : '';
const num = n => Number(n).toLocaleString();
function runWhat(r) {
  if (r.kind === 'earlier') return 'Temperature, humidity and sunlight only';
  if (r.kind === 'history' && r.ok && !r.hourly_rows && !r.daily_days) return 'Nothing new was needed';
  const parts = [];
  parts.push(`${num(r.hourly_rows)} hourly reading${r.hourly_rows === 1 ? '' : 's'}` + (r.hourly_rows ? ` (${num(r.hourly_new)} new)` : ''));
  if (r.daily_days) parts.push(`${num(r.daily_days)} daily summar${r.daily_days === 1 ? 'y' : 'ies'} (${num(r.daily_new)} new)`);
  if (r.vars_ok) parts.push(`${r.vars_ok} kinds of measurement`);
  return parts.join(', ');
}
function runRange(r) { return r.range_start ? (r.range_start === r.range_end ? dayLong(r.range_start) : `${dayLong(r.range_start)} to ${dayLong(r.range_end)}`) : ''; }
function runLine(label, r, none) {
  if (!r) return html`<li><strong>${label}:</strong> ${none}</li>`;
  return html`<li><strong>${label}:</strong> ${when(r.ran_at)}. ${r.ok ? '' : html`<strong>Failed:</strong> ${r.error} `}${runRange(r) ? 'Covered ' + runRange(r) + '. ' : ''}${runWhat(r)}.
    ${r.vars_missing && r.vars_missing.length ? html`<details class="inline"><summary>${r.vars_missing.length} measurements Open-Meteo does not offer for this period</summary><p>${r.vars_missing.join(', ')}</p></details>` : ''}${r.note ? html` <span class="hint">${r.note}</span>` : ''}</li>`;
}
function runSummary(W) {
  const R = W.runs || {};
  const idle = R.history && R.history.ok && !R.history.hourly_rows;
  const hist = R.history ? html`${runLine(idle ? 'Last time Load history was pressed' : 'Last Load history', R.history, '')}${idle && R.history_ok ? runLine('Last Load history that fetched new data', R.history_ok, '') : ''}` : runLine('Last Load history', null, R.earlier ? 'none since the update log began. Before then, ' + num(R.earlier.hourly_rows) + ' hourly readings (' + runRange(R.earlier) + ') were collected by the first load and the hourly updates, with temperature, humidity and sunlight only.' : 'none yet.');
  return html`<ul class="runs">${hist}${runLine('Last automatic update', R.auto, 'none yet. The first one runs a few seconds after the app starts.')}</ul>`;
}
function dur(sec) {
  sec = Math.max(0, Math.round(sec));
  if (sec < 60) return sec + ' seconds';
  const m = Math.floor(sec / 60), h = Math.floor(m / 60);
  return h ? `${h} hour${h === 1 ? '' : 's'} ${m % 60} minute${m % 60 === 1 ? '' : 's'}` : `${m} minute${m === 1 ? '' : 's'}`;
}
function jobNumbers(j) {
  const t = j.now_ts || Date.now() / 1000;
  const elapsed = j.started_ts ? t - j.started_ts : 0, quiet = j.beat ? t - j.beat : 0;
  const hist = j.phase === 'history' && j.total;
  const pct = hist ? Math.floor(100 * j.done / j.total) : j.phase === 'recent' && j.total ? 99 : 0;
  const fetched = j.done - (j.skipped || 0);                   // periods actually downloaded so far
  const left = hist && fetched > 0 && j.done < j.total ? elapsed / Math.max(fetched, 1) * (j.total - j.done) : null;
  return { elapsed, quiet, pct, left, hist };
}
function jobPanel(j) {
  if (!j || !j.running) return j && j.finished ? html`<p class="${j.ok ? 'notice ok' : 'notice bad'}" role="status">${j.trigger === 'load-history' ? 'Load history' : 'Update'} ${j.ok ? 'finished' : 'stopped'} ${when(j.finished)}. ${j.error || ''}</p>` : '';
  const n = jobNumbers(j);
  const at = j.place ? ` for ${j.place}` : '';
  const what = (j.trigger === 'load-history' ? 'Loading history' : 'Updating the weather') + at + (j.places_total > 1 ? ` (place ${j.place_no} of ${j.places_total})` : '');
  const waiting = j.waiting_until && j.waiting_until > (j.now_ts || 0);
  return html`<div class="notice jobbox" role="group" aria-label="${what}">
    <p class="jobhead"><strong>${what}: ${n.hist ? n.pct + '% done' : j.phase === 'recent' ? 'last step' : 'starting'}</strong></p>
    <progress max="100" value="${n.pct}" aria-label="${what}, ${n.pct} percent done">${n.pct}%</progress>
    <dl class="jobdl">
      ${n.hist ? html`<dt>Year-long periods</dt><dd>${num(Math.min(j.done + 1, j.total))} of ${num(j.total)}${j.skipped ? `, ${num(j.skipped)} already stored and skipped` : ''}</dd>` : ''}
      <dt>Working on</dt><dd>${j.phase === 'recent' ? 'the last 3 months and the forecast' : j.label ? j.label.replace(/(\d{4})-(\d{2})-(\d{2})/g, (m) => dayLong(m)) : 'starting'}${j.step ? ' (' + j.step + ')' : ''}</dd>
      <dt>Saved so far</dt><dd>${num(j.hourly_saved || 0)} hourly readings, ${num(j.daily_saved || 0)} daily summaries</dd>
      <dt>Running for</dt><dd>${dur(n.elapsed)}</dd>
      ${j.retries ? html`<dt>Dropped connections</dt><dd>${num(j.retries)} so far, each retried automatically</dd>` : ''}
      ${n.left != null ? html`<dt>Time left</dt><dd>about ${dur(n.left)}</dd>` : ''}
      <dt>Last activity</dt><dd>${waiting ? html`<strong>Pausing: ${j.waiting_why || "Open-Meteo's per-minute limit"}</strong>, carrying on in ${dur(j.waiting_until - j.now_ts)}` : n.quiet < 5 ? 'just now' : dur(n.quiet) + ' ago'}${!waiting && n.quiet > 120 ? html`<div class="hint">Nothing for a while. Open-Meteo may be slow; it gives up on a request after 40 seconds and the error is then shown here.</div>` : ''}</dd>
    </dl>
    <p class="hint">It keeps running if you leave this page or close the browser. A small "Loading history" box at the bottom left of every page shows the percentage.</p></div>`;
}
let JOBT = null;
async function wxPoll() {
  clearTimeout(JOBT);
  let j; try { j = await api('GET', '/api/weather/job'); } catch (e) { JOBT = setTimeout(wxPoll, 6000); return; }
  const el = document.getElementById('wx-job');
  const was = document.body.dataset.job === '1';
  document.body.dataset.job = j.running ? '1' : '0';
  if (el) el.innerHTML = rend(jobPanel(j));
  jobBadge(j);
  if (j.running) JOBT = setTimeout(wxPoll, el ? 2000 : 5000);
  else if (was) { toast(j.ok ? (j.trigger === 'load-history' ? 'Load history finished' : 'Weather update finished') : 'Weather update stopped: ' + (j.error || ''), !j.ok); if (location.hash.startsWith('#/weather')) route(); }
}
function jobBadge(j) {
  let b = document.getElementById('job-badge');
  if (!j || !j.running) { if (b) { b.remove(); conLayout(); } return; }
  if (!b) { b = document.createElement('a'); b.id = 'job-badge'; b.href = '#/weather'; b.className = 'noprint'; document.body.appendChild(b); setTimeout(conLayout, 0); }
  const n = jobNumbers(j);
  b.textContent = (j.trigger === 'load-history' ? 'Loading history' : 'Updating weather') + (j.place ? ` for ${j.place}` : '') + (j.places_total > 1 ? ` (${j.place_no} of ${j.places_total})` : '') + ': ' + (n.hist ? n.pct + '%' : '…') + (n.left != null ? ', about ' + dur(n.left) + ' left' : '');
  b.setAttribute('aria-label', b.textContent + '. Open the Weather page for details.');
}
async function loadRunLog() {
  const el = document.getElementById('wx-runs'); if (!el) return;
  const runs = await api('GET', '/api/weather/runs?n=200' + locQS());
  el.innerHTML = rend(html`<div class="tbl-wrap"><table class="tbl"><caption class="sr">Every weather update, newest first</caption><thead><tr><th>When</th><th>Started by</th><th>Dates covered</th><th>Result</th><th>Added</th><th>Not offered</th></tr></thead><tbody>
    ${runs.map(r => html`<tr><th scope="row">${when(r.ran_at)}</th><td>${TRIGGER_WORDS[r.trigger] || r.trigger}${r.kind === 'history' ? html`<div class="hint">older history</div>` : r.kind === 'recent' ? html`<div class="hint">last 3 months + forecast</div>` : ''}</td><td>${runRange(r)}</td>
      <td>${r.ok ? 'Worked' : html`<strong>Failed</strong><div class="hint">${r.error}</div>`}${r.seconds ? html`<div class="hint">${Math.round(r.seconds)} s</div>` : ''}</td>
      <td>${runWhat(r)}${r.note ? html`<div class="hint">${r.note}</div>` : ''}</td>
      <td>${r.vars_missing && r.vars_missing.length ? html`<details><summary>${r.vars_missing.length}</summary><p class="hint">${r.vars_missing.join(', ')}</p></details>` : ''}</td></tr>`)}</tbody></table></div>`);
}

const WT = { kind: 'hourly', from: '', to: '', order: 'desc', per: 50, page: 1, hide: null };
try { const n = +localStorage.getItem('plantdb.wxper'); if (n >= 10 && n <= 1000) WT.per = n; } catch (e) { /* ignore */ }
function wtHidden() {
  if (WT.hide) return WT.hide;
  let v = null; try { v = JSON.parse(localStorage.getItem('plantdb.wxhide') || 'null'); } catch (e) { /* ignore */ }
  WT.hide = new Set(Array.isArray(v) ? v : ['wet_bulb_temperature_2m', 'temperature_80m', 'temperature_120m', 'temperature_180m', 'wind_speed_80m', 'wind_speed_120m', 'wind_speed_180m', 'wind_direction_80m', 'wind_direction_120m', 'wind_direction_180m',
    'soil_temperature_18cm', 'soil_temperature_54cm', 'soil_moisture_1_to_3cm', 'soil_moisture_3_to_9cm', 'soil_moisture_27_to_81cm', 'uv_index_clear_sky', 'terrestrial_radiation', 'lifted_index', 'convective_inhibition', 'boundary_layer_height',
    'total_column_integrated_water_vapour', 'freezing_level_height', 'cape', 'showers', 'evapotranspiration', 'surface_pressure', 'cloud_cover_low', 'cloud_cover_mid', 'cloud_cover_high', 'direct_normal_irradiance', 'snow_depth']);
  return WT.hide;
}
function wtSave() { try { localStorage.setItem('plantdb.wxhide', JSON.stringify([...WT.hide])); } catch (e) { /* ignore */ } }
function wtCell(k, v, tz) {
  if (v == null || v === '') return '';
  if (k === 'sunrise' || k === 'sunset') return new Date(v * 1000).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', timeZone: tz });
  if (k === 'daylight_duration' || k === 'sunshine_duration') return v >= 3600 * 1.5 && !/^sunshine_duration$/.test(k) || WT.kind === 'daily' ? `${Math.floor(v / 3600)} h ${Math.round(v % 3600 / 60)} min` : `${Math.round(v / 60)} min`;
  if (k === 'weather_code') return `${WMO[v] || 'Code'} (${v})`;
  if (k === 'is_day') return v ? 'Day' : 'Night';
  if (/^wind_direction/.test(k)) return `${Math.round(v)}° ${compass(v)}`;
  if (typeof v === 'number') return (Math.round(v * 100) / 100).toLocaleString(undefined, { maximumFractionDigits: 2 });
  return String(v);
}
async function loadWxTable() {
  const el = document.getElementById('wx-table'); if (!el) return;
  const hide = wtHidden();
  const q = new URLSearchParams({ kind: WT.kind === 'daily' ? 'daily' : 'hourly', source: WT.kind === 'sensor' ? 'sensor' : 'weather', order: WT.order, per: WT.per, page: WT.page });
  if (PLACE) q.set('loc', PLACE);
  if (WT.from) q.set('from', WT.from); if (WT.to) q.set('to', WT.to);
  let T; try { T = await api('GET', '/api/weather/table?' + q); } catch (e) { el.innerHTML = rend(html`<p class="notice bad">${e.message}</p>`); return; }
  const cols = T.columns.filter(c => !hide.has(c.key));
  WT.shown = cols.map(c => c.key); WT.kindShown = T.kind;
  const groups = [...new Set(T.columns.map(c => c.group))];
  q.delete('per'); q.delete('page');
  const first = (T.page - 1) * T.per + 1, last = Math.min(T.total, T.page * T.per);
  const lbl = T.kind === 'daily' ? 'Day' : 'Local time';
  el.innerHTML = rend(html`
    <details class="colpick noprint"><summary>Choose columns (${cols.length} of ${T.columns.length} shown)</summary>
      <div class="row"><button class="btn small ghost" type="button" data-act="wtallcols">Show all</button><button class="btn small ghost" type="button" data-act="wtnocols">Show only the basics</button></div>
      ${groups.map(g => html`<fieldset><legend>${g}</legend>${T.columns.filter(c => c.group === g).map(c => html`<label class="chk-row" style="border:0;padding:.3rem 0"><input type="checkbox" data-f="wtcol" data-key="${c.key}" ${hide.has(c.key) ? '' : raw('checked')}><span>${c.label}${c.unit ? ' (' + c.unit + ')' : ''}</span></label>`)}</fieldset>`)}
    </details>
    <p class="hint" role="status">${T.total ? `Showing ${num(first)} to ${num(last)} of ${num(T.total)}. Times are in ${T.tz}.` : 'Nothing logged for these choices.'}
      <a class="noprint" href="/api/weather/table.csv?${q}" download>Download all of it as a spreadsheet (CSV, every column)</a></p>
    ${T.total ? html`${wtPager(T, 'top')}<div class="tbl-wrap wide"><table class="tbl wxt"><caption class="sr">Logged ${T.kind === 'daily' ? 'daily weather' : T.source === 'sensor' ? 'sensor readings' : 'hourly weather'}</caption>
      <thead><tr><th scope="col">${lbl}</th>${T.source === 'sensor' ? html`<th scope="col">Device</th>` : ''}${T.kind === 'daily' ? html`<th scope="col">Status</th>` : ''}${cols.map(c => html`<th scope="col" class="num">${c.label}${c.unit ? html`<div class="hint">${c.unit}</div>` : ''}</th>`)}</tr></thead>
      <tbody>${T.rows.map(r => html`<tr><th scope="row">${T.kind === 'daily' ? dayLong(r.when) : r.when}</th>${T.source === 'sensor' ? html`<td>${r.device}</td>` : ''}${T.kind === 'daily' ? html`<td>${r.kind === 'forecast' ? 'Forecast' : 'Observed'}</td>` : ''}${cols.map(c => html`<td class="num">${wtCell(c.key, r[c.key], T.tz)}</td>`)}</tr>`)}</tbody></table></div>
      ${wtPager(T, 'bottom')}` : ''}`);
}
function wtPager(T, where) {
  const off = c => c ? raw('disabled') : '';
  const newer = WT.order === 'desc' ? 'newer' : 'older', older = WT.order === 'desc' ? 'older' : 'newer';
  return html`<form class="row noprint pager" data-form="wtgo" aria-label="Pages (${where === 'top' ? 'above' : 'below'} the table)">
    <button class="btn ghost small" type="button" data-act="wtpage" data-to="1" ${off(T.page <= 1)} title="Page 1, the ${newer}st rows">First page</button>
    <button class="btn ghost small" type="button" data-act="wtpage" data-d="-1" ${off(T.page <= 1)}>Previous page</button>
    <label class="pg-go">Page <input type="number" name="page" data-max="${T.pages}" value="${T.page}" inputmode="numeric" aria-label="Page number, 1 to ${T.pages}"> of ${num(T.pages)}</label>
    <button class="btn small" type="submit">Go to that page</button>
    <button class="btn ghost small" type="button" data-act="wtpage" data-d="1" ${off(T.page >= T.pages)}>Next page</button>
    <button class="btn ghost small" type="button" data-act="wtpage" data-to="${T.pages}" ${off(T.page >= T.pages)} title="Page ${T.pages}, the ${older}st rows">Last page</button></form>`;
}
function wtControls() {
  return html`<div class="chart-tools noprint">
    <label>Show<select data-f="wtkind">${[['hourly', 'Hourly weather (every hour)'], ['daily', 'Daily weather summaries'], ['sensor', 'My sensor readings']].map(([v, l]) => html`<option value="${v}" ${WT.kind === v ? raw('selected') : ''}>${l}</option>`)}</select></label>
    <label>From<input type="date" data-f="wtfrom" value="${WT.from}"></label><label>To<input type="date" data-f="wtto" value="${WT.to}"></label>
    <label>Order<select data-f="wtorder"><option value="desc" ${WT.order === 'desc' ? raw('selected') : ''}>Newest first</option><option value="asc" ${WT.order === 'asc' ? raw('selected') : ''}>Oldest first</option></select></label>
    <label>Rows per page (10 to 1,000)<input type="number" data-f="wtper" value="${WT.per}" inputmode="numeric" list="wtper-list"></label>
    <datalist id="wtper-list">${[25, 50, 100, 200, 500, 1000].map(n => html`<option value="${n}"></option>`)}</datalist></div>`;
}

// ---------- frost alert and cold-night checklist (added in 1.8.0) ----------
let FROST = null, FROST_AT = 0;
async function loadFrost(force) {
  if (!force && FROST && Date.now() - FROST_AT < 5 * 60000) return FROST;
  try { FROST = await api('GET', '/api/frost'); FROST_AT = Date.now(); } catch (e) { /* no banner if it cannot be worked out */ }
  return FROST;
}
const FZ_WORD = { danger: 'Could die', damage: 'Damaged', watch: 'Close call' };
// a night's low is usually reached just before dawn, so the "night" of a date is the evening before it
function fzDay(d, lower) {
  if (!FROST) return d;
  const name = new Date(d + 'T12:00:00').toLocaleDateString([], { weekday: 'long', month: 'short', day: 'numeric' });
  const w = d === FROST.today ? 'Today' : d === addDays(FROST.today, 1) ? 'Tomorrow' : '';
  return w ? (lower ? w.toLowerCase() : w) + ' (' + name + ')' : name;
}
function fzActBy(d) {
  if (!FROST) return '';
  if (d <= FROST.today) return 'before dark today';
  if (d === addDays(FROST.today, 1)) return 'this evening';
  return new Date(addDays(d, -1) + 'T12:00:00').toLocaleDateString([], { weekday: 'long' }) + ' evening';
}
function fzSig() { const F = FROST; return F && F.first ? [F.first.date, F.first.low, F.worst.date, F.worst.low, F.worst.counts.danger, F.worst.counts.damage, F.worst.counts.watch].join('|') : ''; }
function frostBanner(inPage) {
  const F = FROST; if (!F || !F.first) return '';
  try { if (!inPage && localStorage.getItem('plantdb.frosthide') === fzSig()) return ''; } catch (e) { /* show it */ }
  const W = F.worst, real = W.level !== 'watch', c = W.counts, sameNight = F.first.date === W.date;
  const parts = [c.danger ? `${c.danger} could die` : '', c.damage ? `${c.damage} would be damaged` : '', c.watch ? `${c.watch} ${c.watch === 1 ? 'is a close call' : 'are close calls'}` : ''].filter(Boolean);
  const list = parts.length > 1 ? parts.slice(0, -1).join(', ') + ' and ' + parts[parts.length - 1] : parts[0];
  const title = `${!real ? 'Cold night ahead' : W.low <= 36 ? 'Frost warning' : 'Cold warning'} for ${placeShort()}: down to ${W.low}°F ${fzDay(W.date, true)}`;
  // 1.34.0: on Today the warning is part of the page (a section with a heading, never hidden); elsewhere it is the banner above the page
  return html`<${inPage ? 'div' : 'section'} class="fz-banner ${real ? 'bad' : ''} noprint" ${inPage ? '' : raw('aria-labelledby="fz-h"')}>
    ${inPage ? html`<h2 class="fz-title">${title}</h2>` : html`<p class="fz-title" id="fz-h">${title}</p>`}
    <p>Of your ${F.outdoor} plants outside, ${list} that night.${sameNight ? '' : ` The first cold night is ${fzDay(F.first.date, true)}, at ${F.first.low}°F.`}
      Bring them in or cover them <strong>${fzActBy(F.first.date)}</strong>.</p>
    <p class="row"><a class="btn" href="#/frost">Open the cold-night checklist</a>
      ${inPage ? '' : html`<button class="btn ghost" type="button" data-act="frosthide">Hide until the forecast changes</button>`}</p></${inPage ? 'div' : 'section'}>`;
}
const FZ_DO = {
  'Move indoors': 'Bring it inside: a heated room, or the garage for a night or two.',
  'Protect outside': 'Cover it down to the ground with frost cloth or an old sheet (not plastic touching the leaves), or move it against the house or onto the porch.',
  'Hardy outside': 'Usually fine outside, but this is below its damage point: cover it, or move the pot against the house.',
  'Seasonal die-back': 'The top growth may die back. Mulch or wrap the pot, or move it to shelter to protect the roots.',
  'Annual': 'An annual: the cold will likely end its season. Bring it in only if you want to keep it going.',
};
const fzNight = z => `${fzDay(z.date)}, ${z.low}°F (${FZ_WORD[z.level].toLowerCase()})`;
function fzRow(p) {
  const d = p.done, many = p.nights.length > 1;
  return html`<li class="fz-row ${d ? 'is-done' : ''}" data-code="${p.code}">
    ${p.photo ? html`<img src="${thumbUrl(p.photo)}" alt="" loading="lazy" width="72" height="72">` : html`<span class="fz-nophoto" aria-hidden="true"></span>`}
    <div class="fz-txt"><a class="nm" href="#/plant/${enc(p.code)}">${p.name}</a> <span class="muted">${p.code}</span>
      <div><span class="fz-lv fz-${p.level}">${FZ_WORD[p.level]}</span> Damaged below ${p.damage}°F${p.lethal != null ? `, dies below ${p.lethal}°F` : ''}.${p.site === 'Covered porch' ? ' On the covered porch, which helps a little but not in a freeze.' : ''}</div>
      <div>Next cold night: ${fzNight(p.next)}.${many && p.worst.date !== p.next.date ? ` Coldest: ${fzNight(p.worst)}.` : ''}${many ? ` Cold on ${p.nights.length} of the next 7 nights.` : ''}</div>
      <div class="hint">${FZ_DO[p.plan] || FZ_DO['Protect outside']}</div>
      ${d ? html`<div class="fz-done">✔ Covered for ${fzDay(p.next.date, true)}, marked by ${d.by} ${when(d.at)}. It comes back on the list for the next cold night.</div>` : ''}</div>
    <div class="fz-acts">${d ? html`<button class="btn small ghost" type="button" data-act="frostundo" data-code="${p.code}" data-date="${p.next.date}">Undo "Covered"</button>`
      : html`<button class="btn small" type="button" data-act="frostin" data-code="${p.code}" data-name="${p.name}">Moved indoors</button>
             <button class="btn small ghost" type="button" data-act="frostcover" data-code="${p.code}" data-date="${p.next.date}">Covered for ${p.next.date === FROST.today ? 'today' : p.next.date === addDays(FROST.today, 1) ? 'tonight' : new Date(addDays(p.next.date, -1) + 'T12:00:00').toLocaleDateString([], { weekday: 'long' }) + ' night'}</button>`}</div></li>`;
}
const FZ_GROUPS = [
  ['in', 'Bring inside', 'Plants whose winter plan is Move indoors.', p => p.plan === 'Move indoors'],
  ['cover', 'Cover or move to shelter', 'Plants that stay outside but would be hurt.', p => p.plan !== 'Move indoors' && p.level !== 'watch'],
  ['watch', 'Close calls', 'Within 3°F of their damage point. Worth covering if the night is clear and still.', p => p.plan !== 'Move indoors' && p.level === 'watch'],
];
async function viewFrost() {
  const F = await loadFrost(true);
  if (!F) throw new Error('The forecast could not be read.');
  const ticked = n => (F.plants || []).filter(p => p.done && p.next.date === n.date).length;
  return {
    title: 'Cold-night checklist',
    html: html`<p class="crumb"><a href="#/winter">Winter plan</a></p><h1>Cold-night checklist</h1>
    <p class="muted">Plants that are outside and would be hurt by a night in the 7-day forecast for ${F.place}. "Could die" and "Damaged" use each plant's own temperatures;
      "Close call" means within ${F.margin}°F of its damage point, because forecasts often miss a clear, still night by a few degrees.
      Plants set to Indoors or Garage or shed are left out, so a plant leaves this list when you press Moved indoors.</p>
    <p>Before a plant comes inside, check it for pests: <a href="#/inside">Getting plants ready to come inside</a>.</p>
    ${canChange() ? html`<p class="row noprint"><button class="btn ghost small" type="button" data-act="buywatch" data-kind="frost" data-name="Frost cloth" data-search="frost cloth; frost blanket; plant cover" data-src="frost">Watch the stores for frost cloth</button></p>` : ''}
    ${!F.nights.length ? html`<p class="notice">No forecast yet. It is fetched a few seconds after the app starts, then every hour.</p>` : ''}
    ${F.nights.length && !F.plants.length ? html`<p class="notice ok">No cold nights in the next 7 days for any plant that is outside.</p>` : ''}
    ${F.nights.length ? html`<section class="blk"><h2>The next 7 nights</h2><div class="tbl-wrap"><table class="tbl fz-tbl"><caption class="sr">Plants at risk each night</caption>
      <thead><tr><th>Day</th><th class="num">Low</th><th class="num">Could die</th><th class="num">Damaged</th><th class="num">Close calls</th><th class="num">Covered</th></tr></thead><tbody>
      ${F.nights.map(n => html`<tr><th scope="row">${fzDay(n.date)}</th><td class="num">${n.low}°F${n.low <= 32 ? ' (freeze)' : ''}</td>
        <td class="num">${n.counts.danger || '–'}</td><td class="num">${n.counts.damage || '–'}</td><td class="num">${n.counts.watch || '–'}</td><td class="num">${n.level ? ticked(n) : '–'}</td></tr>`)}
      </tbody></table></div><p class="hint">Forecast updated ${F.fetched_at ? when(F.fetched_at) : 'not yet'}. The low is usually reached just before dawn, so act the evening before.</p></section>` : ''}
    ${FZ_GROUPS.map(([id, title, sub, test]) => { const g = (F.plants || []).filter(test); if (!g.length) return '';
      const open = g.filter(p => !p.done);
      return html`<section class="blk" id="fz-${id}"><h2>${title} (${g.length})</h2><p class="muted">${sub} Most urgent first.</p>
        ${open.length > 1 ? html`<p>${id === 'in' ? html`<button class="btn small ghost" type="button" data-act="frostallin" data-group="${id}">Moved all ${open.length} indoors</button>`
          : html`<button class="btn small ghost" type="button" data-act="frostallcover" data-group="${id}">Mark all ${open.length} as covered for their next cold night</button>`}</p>` : ''}
        <ul class="fz-list">${g.map(fzRow)}</ul></section>`; })}
    <section class="blk"><h2>Protecting plants on a cold night</h2><ul>
      <li>Move pots against the house wall or onto the porch: they lose less heat there than in the open.</li>
      <li>Water dry pots during the day before: moist soil holds more heat than dry soil.</li>
      <li>Cover plants down to the ground with frost cloth, old sheets or cardboard boxes, so the ground's warmth is trapped. Plastic touching the leaves makes damage worse.</li>
      <li>Take the covers off the next morning once it is above freezing, so the plants get light.</li>
      <li>Group pots together; small pots freeze through faster than big ones.</li></ul></section>`,
  };
}
function frostNote(p) {
  const x = FROST && (FROST.plants || []).find(q => q.code === p.code);
  if (!x || x.level === 'watch') return '';
  const w = x.worst;
  return html`<p class="notice bad noprint fz-note"><strong>Frost risk:</strong> ${fzDay(w.date)} is forecast to drop to ${w.low}°F,
    below this plant's ${w.level === 'danger' ? `lowest survivable temperature (${x.lethal}°F)` : `damage point (${x.damage}°F)`}.
    ${FZ_DO[p.winter_plan] || ''} <a href="#/frost">Open the cold-night checklist</a></p>`;
}

// ---------- winter plan page ----------
async function viewWinter() {
  const [ref, list, W, monthly] = await Promise.all([api('GET', '/api/reference'), api('GET', '/api/plants'), api('GET', '/api/weather'), api('GET', '/api/weather/monthly')]);
  return {
    title: 'Winter plan',
    html: html`<h1>Winter plan</h1><p class="muted">What to expect in ${placeName()} from October to March, when to act, and which plants go where.</p>
    <section class="blk"><h2>The next 7 days</h2>${forecastBlock(W, list)}<p class="row"><a class="btn small" href="#/frost">Open the cold-night checklist</a><a class="btn small ghost" href="#/inside">Get plants ready to come inside</a><a class="btn ghost small" href="#/weather">Open the Weather page for charts and sensors</a></p></section>
    <section class="blk"><h2>Expected and tracked this season</h2>${seasonTable(ref, monthly)}
      ${ref.applies !== false ? (ref.notes || []).map(n => html`<p class="hint">${n}</p>`) : ''}</section>
    <section class="blk"><h2>When to act</h2><dl class="dl">${(ref.triggers || []).map(t => html`<dt>${t.temp}</dt><dd>${t.action}</dd>`)}</dl></section>
    <section class="blk"><h2>Ground rules</h2>${(ref.playbook || []).length ? html`<ul>${ref.playbook.map(x => html`<li>${x}</li>`)}</ul>` : ''}</section>
    <section class="blk"><h2>Plant by plant</h2><div class="cols">${META.winter_plans.map(pl => {
      const g = list.filter(p => p.winter_plan === pl && !isInside(p)).sort((a, b) => (b.temp_damage_below ?? -99) - (a.temp_damage_below ?? -99));
      if (!g.length) return '';
      return html`<div><h3>${pl} (${g.length})</h3><ul class="todo winter-list">${g.map(p => html`<li>${p.photo ? html`<img src="${thumbUrl(p.photo)}" alt="" loading="lazy">` : html`<span></span>`}
        <span><a class="nm" href="#/plant/${enc(p.code)}">${p.common_name}</a><br><span class="muted">${p.code}${p.temp_damage_below != null ? ', damage below ' + p.temp_damage_below + '°F' : ''}${p.site && p.site !== 'Outdoors' ? ', ' + p.site.toLowerCase() : ''}</span>
        <br><button class="btn small noprint" type="button" data-act="movein" data-code="${p.code}" data-name="${p.common_name}">Moved indoors</button></span></li>`)}</ul></div>`;
    })}</div>
    ${(() => { const ins = list.filter(isInside).sort((a, b) => a.code.localeCompare(b.code)); return ins.length ? html`<h3 id="inside-list">Already inside (${ins.length})</h3>
      <p class="hint">These are left out of the lists above and the frost warnings. If one goes back out, press Moved back outside.</p>
      <p><a class="btn small ghost" href="#/outside">Which can go back outside?</a></p>
      <ul class="todo winter-list inside-list">${ins.map(p => html`<li>${p.photo ? html`<img src="${thumbUrl(p.photo)}" alt="" loading="lazy">` : html`<span></span>`}
        <span><a class="nm" href="#/plant/${enc(p.code)}">${p.common_name}</a><br><span class="muted">${p.code}, ${p.site.toLowerCase()}, plan: ${p.winter_plan}</span>
        <br><button class="btn small ghost noprint" type="button" data-act="moveout" data-code="${p.code}" data-name="${p.common_name}">Moved back outside</button></span></li>`)}</ul>` : html`<p class="hint">When you bring a plant in, press its Moved indoors button. It leaves these lists and the frost warnings, and its page shows Location: Indoors.</p>`; })()}
    </section>
    ${ref.applies !== false && (ref.sources || []).length ? html`<section class="blk"><h2>Sources</h2><ul>${ref.sources.map(s => html`<li><a href="${s[1]}" target="_blank" rel="noopener noreferrer">${s[0]}</a></li>`)}</ul></section>` : ''}`,
  };
}

// ---------- back outside in spring (prototype: proto/move-outside) ----------
// #/outside lists the plants that are inside now and whether the forecast nights are warm enough for each to go back out
// (GET /api/outside). In spring the Today page also gets a short note when some are ready (filled by a MutationObserver).
let BO = null, BO_AT = 0;
async function loadOutside(force) {
  if (!force && BO && Date.now() - BO_AT < 5 * 60000) return BO;
  BO = await api('GET', '/api/outside'); BO_AT = Date.now();
  return BO;
}
const BO_WORD = { ready: 'Ready', safe: 'Safe, but cool', early: 'Too early', wait: 'Not yet' };
const BO_GROUPS = [
  ['ready', 'Ready to go back out', 'Every night in the forecast is at or above the low each of these likes.'],
  ['safe', 'Safe to go out, but the nights are cool', 'No night in the forecast comes within 3°F of their damage point, but some nights are cooler than they like. Going out now is fine; they will grow slowly until the nights warm up.'],
  ['early', 'A warm week, but it is early', 'The forecast is fine for these, but in most years colder nights still come after this date. Wait, or put them out and be ready to bring them back in.'],
  ['wait', 'Not yet', 'A night in the forecast is too cold for these.'],
];
const boMd = md => new Date('2001-' + md + 'T12:00:00').toLocaleDateString([], { month: 'long', day: 'numeric' });
function boUsual(p) {
  const u = p.usual;
  if (!u) return '';
  if (p.why === 'autumn' && u.first) return `In most years the first night below ${p.safe_at}°F comes around ${boMd(u.first)}, so it would likely need to come back in soon.`;
  if (!u.safe) return '';
  if (u.safe === '01-01') return `In the last ${u.spring_years} springs, no night went below ${p.safe_at}°F.`;
  return `In most of the last ${u.spring_years} years, the nights stayed above ${p.safe_at}°F from ${boMd(u.safe)} on${u.safe_latest !== u.safe ? ` (in the latest year, from ${boMd(u.safe_latest)})` : ''}.`;
}
function boRow(p) {
  const lv = p.level, c = p.coldest;
  const needs = p.damage != null ? `Damaged below ${p.damage}°F${p.like > p.safe_at ? `; likes nights of ${p.like}°F or more` : ''}.` : p.like != null ? `Likes nights of ${p.like}°F or more.` : 'No temperatures on its page yet, so it cannot be checked.';
  let fc = '';
  if (lv === 'wait') fc = `Too cold ${fzDay(p.first_cold.date, true)}: ${p.first_cold.low}°F. It needs ${p.safe_at}°F or more to be safe${c.date !== p.first_cold.date ? `; the coldest night is ${fzDay(c.date, true)}, ${c.low}°F` : ''}.`;
  else if (c) fc = `Coldest night in the forecast: ${fzDay(c.date, true)}, ${c.low}°F.${p.cool_nights ? ` ${p.cool_nights} of the next ${BO.nights.length} nights are below ${p.like}°F.` : ''}`;
  const usual = boUsual(p);
  const go = lv && lv !== 'wait';
  return html`<li class="fz-row bo-row" data-code="${p.code}">
    ${p.photo ? html`<img src="${thumbUrl(p.photo)}" alt="" loading="lazy" width="72" height="72">` : html`<span class="fz-nophoto" aria-hidden="true"></span>`}
    <div class="fz-txt"><a class="nm" href="#/plant/${enc(p.code)}">${p.name}</a> <span class="muted"><span class="bo-code">${p.code}</span>, ${(p.site || '').toLowerCase()}</span>
      <div>${lv ? html`<span class="bo-lv bo-${lv}">${BO_WORD[lv]}</span> ` : ''}${needs}</div>
      ${fc ? html`<div>${fc}</div>` : ''}${usual ? html`<div class="hint">${usual}</div>` : ''}
      ${go ? html`<div class="hint">Porch first protects leaves that grew indoors from sun scorch. A reminder comes a week later.</div>` : ''}</div>
    ${go ? html`<div class="fz-acts"><button class="btn small" type="button" data-act="boporch" data-code="${p.code}" data-name="${p.name}">Moved to the porch</button>
      <button class="btn small ghost" type="button" data-act="boout" data-code="${p.code}" data-name="${p.name}">Moved outside</button></div>` : ''}</li>`;
}
const boPorchDay = d => new Date(d + 'T12:00:00').toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' });
function boPorchRow(p) {
  return html`<li class="fz-row bo-row bo-porchrow" data-code="${p.code}">
    ${p.photo ? html`<img src="${thumbUrl(p.photo)}" alt="" loading="lazy" width="72" height="72">` : html`<span class="fz-nophoto" aria-hidden="true"></span>`}
    <div class="fz-txt"><a class="nm" href="#/plant/${enc(p.code)}">${p.name}</a> <span class="muted"><span class="bo-code">${p.code}</span>, covered porch</span>
      <div>${p.is_due ? html`<span class="bo-lv bo-ready">Time to move it</span> ` : ''}On the porch since ${boPorchDay(p.on)} (${p.days === 0 ? 'today' : p.days === 1 ? '1 day' : p.days + ' days'}).
        ${p.is_due ? 'It has had its week out of full sun, so it can go to its summer spot.' : html`Move it to its summer spot on or after ${boPorchDay(p.due)}.`}</div></div>
    <div class="fz-acts"><button class="btn small ${p.is_due ? '' : 'ghost'}" type="button" data-act="boout" data-code="${p.code}" data-name="${p.name}">Moved outside</button>
      <button class="btn small ghost" type="button" data-act="boleave" data-code="${p.code}" data-name="${p.name}">Leave it on the porch</button></div></li>`;
}
async function viewOutside() {
  const B = await loadOutside(true);
  const ps = B.plants || [], n = B.counts, anyUsual = ps.some(p => p.usual);
  const go = n.ready + n.safe;
  return {
    title: 'Back outside',
    html: html`<p class="crumb"><a href="#/winter">Winter plan</a></p><h1>Back outside</h1>
    <p class="muted">Plants that are inside now (Indoors, or Garage or shed), and whether the nights in the 7-day forecast for ${B.place} are warm enough for each to go back out.
      Each plant is checked against its own temperatures: safe means no night within ${B.margin}°F of its damage point, and ready means every night is at or above the low it likes.</p>
    ${B.season === 'autumn' ? html`<p class="notice">It is autumn, so most plants that came inside should stay in until spring. This page is most useful from late winter: each plant shows as ready as soon as the nights are warm enough for it.</p>` : ''}
    ${!B.nights.length ? html`<p class="notice">No forecast yet. It is fetched a few seconds after the app starts, then every hour.</p>` : ''}
    ${!ps.length ? html`<p class="notice ok">No plants are inside. When you bring one in, press its Moved indoors button and it shows here.</p>` : ''}
    ${ps.length && B.nights.length ? html`<p class="notice ${go ? 'ok' : ''} bo-sum" role="status"><strong>${go ? `${go} of ${ps.length} plants inside can go back out now.` : `None of the ${ps.length} plants inside can go back out yet.`}</strong>
      ${n.ready ? ` Ready: ${n.ready}.` : ''}${n.safe ? ` Safe, but cool: ${n.safe}.` : ''}${n.early ? ` Too early: ${n.early}.` : ''}${n.wait ? ` Not yet: ${n.wait}.` : ''}</p>` : ''}
    ${B.nights.length && !anyUsual ? html`<p class="hint">To also see when the nights usually warm up each spring, load the weather history: <a href="#/weather">Weather page</a>, Load history. It needs 3 years or more.</p>` : ''}
    ${(B.porch || []).filter(p => p.is_due).length ? html`<section class="blk" id="bo-porchdue"><h2>Time to move from the porch to their summer spot (${B.porch.filter(p => p.is_due).length})</h2>
      <p class="muted">These have had a week on the porch, out of full sun. Press Moved outside once they are in their summer spot, or Leave it on the porch to stop the reminder.</p>
      <ul class="fz-list">${B.porch.filter(p => p.is_due).map(boPorchRow)}</ul></section>` : ''}
    ${ps.some(p => p.level && p.level !== 'wait') || (B.porch || []).length ? html`<p class="notice bo-why"><strong>Why the porch first?</strong> Leaves that grew indoors have never seen full sun, so they get sun scorch within a day or two if they go straight outside. The covered porch is bright but out of the direct sun. After a week, move the plant to its summer spot.</p>` : ''}
    ${BO_GROUPS.map(([id, title, sub]) => { const g = ps.filter(p => p.level === id); if (!g.length) return '';
      return html`<section class="blk" id="bo-${id}"><h2>${title} (${g.length})</h2><p class="muted">${sub}</p><ul class="fz-list">${g.map(boRow)}</ul></section>`; })}
    ${(() => { const g = ps.filter(p => !p.level); return g.length && B.nights.length ? html`<section class="blk" id="bo-unknown"><h2>Cannot be checked (${g.length})</h2>
      <p class="muted">These have no damage point or ideal low on their page.</p><ul class="fz-list">${g.map(boRow)}</ul></section>` : ''; })()}
    ${B.nights.length ? html`<section class="blk"><h2>The next 7 nights</h2><div class="tbl-wrap"><table class="tbl bo-tbl"><caption class="sr">Forecast lows</caption>
      <thead><tr><th>Day</th><th class="num">Low</th></tr></thead><tbody>
      ${B.nights.map(x => html`<tr><th scope="row">${fzDay(x.date)}</th><td class="num">${x.low}°F</td></tr>`)}</tbody></table></div>
      <p class="hint">Forecast updated ${B.fetched_at ? when(B.fetched_at) : 'not yet'}. The low is usually reached just before dawn.</p></section>` : ''}
    ${(B.porch || []).filter(p => !p.is_due).length ? html`<section class="blk" id="bo-porchwait"><h2>On the porch for now (${B.porch.filter(p => !p.is_due).length})</h2>
      <p class="muted">Getting used to the light, and out of full sun so the leaves do not scorch. A reminder comes after a week.</p>
      <ul class="fz-list">${B.porch.filter(p => !p.is_due).map(boPorchRow)}</ul></section>` : ''}
    <section class="blk"><h2>Going back out</h2><ul>
      <li>Ease plants in. Leaves that grew indoors scorch in full sun, so give them a week on the covered porch, then a few hours of morning sun, then their usual spot.</li>
      <li>Moved to the porch sets the plant's Location to Covered porch and sets a reminder for a week later. It shows on the cold-night checklist if a cold night comes.</li>
      <li>Pots dry out much faster outside, especially in wind and sun. Check them every day or two for the first weeks.</li>
      <li>Start feeding again once new growth appears.</li></ul></section>`,
  };
}
async function boMove(el, site) {
  if (!(await needName())) return;
  const code = el.dataset.code, y = window.scrollY;
  await guard(async () => {
    if (site === 'Covered porch') await api('POST', '/api/outside/porch', { code, action: 'start' });
    else await api('POST', '/api/plants/' + enc(code) + '/site', { site });
    toast(el.dataset.name + (site === 'Outdoors' ? ' moved outside' : ' moved to the covered porch, out of full sun. A reminder comes in a week.'));
    BO_AT = 0; FROST_AT = 0;
    await route(); window.scrollTo(0, y);
    const next = document.querySelector('.bo-row [data-act=boporch]') || document.querySelector('.bo-row [data-act=boout]');
    (next || document.querySelector('main h1')).focus({ preventScroll: true });
  });
}
// the Today page: in spring, a short note when plants inside can go back out
new MutationObserver(() => {
  if (!/^#\/today\b/.test(location.hash)) return;
  const h = document.querySelector('#app h1');
  if (!h || document.getElementById('bo-today')) return;
  h.insertAdjacentHTML('afterend', '<div id="bo-today"></div>');
  loadOutside().then(B => {
    const box = document.getElementById('bo-today'), go = B.season === 'spring' ? B.counts.ready + B.counts.safe : 0, due = (B.porch || []).filter(p => p.is_due).length;
    if (!box || (!go && !due)) return;
    box.innerHTML = rend(html`<p class="notice ok noprint">${go ? html`<strong>${go === 1 ? '1 plant inside can' : `${go} plants inside can`} go back outside.</strong>
      The nights in the forecast are warm enough for ${go === 1 ? 'it' : 'them'}. ` : ''}${due ? html`<strong>${due === 1 ? '1 plant on the porch is' : `${due} plants on the porch are`} ready for ${due === 1 ? 'its' : 'their'} summer spot.</strong> ${due === 1 ? 'It has' : 'They have'} had a week out of full sun. ` : ''}<a href="#/outside">Open the Back outside list</a></p>`);
  }).catch(() => { /* no note if it cannot be worked out */ });
}).observe(document.getElementById('app'), { childList: true });
