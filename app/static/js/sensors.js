/* Plant record front end: your sensors (1.35.0). One of the files loaded in order by index.html; they share one scope.
   Plain JavaScript, no inline handlers (the server's content policy forbids them). Grown from the proto/sensor-dashboard prototype.
   Every state is a word with its own mark (✓ ↓ ↑ !), never colour alone. */
'use strict';

const SNS = { list: [] };
const snsNum = (m, v) => v == null ? '' : (m === 'temp_f' || m === 'soil_temp_f' || m === 'soil_ph' ? String(r1(v)) : String(Math.round(v)));
const snsVal = (m, unit, v) => snsNum(m, v) + (unit || '');
function snsHeard(s) {
  if (!s.last) return html`<p class="notice sns-quiet" role="status"><strong>No readings yet.</strong> This sensor is set up, but nothing has arrived from it.</p>`;
  const a = ago(s.minutes_ago);
  if (s.quiet) return html`<p class="notice bad sns-quiet" role="status"><strong>Quiet: last heard ${a}.</strong> It usually sends more often than every ${s.quiet_hours} hour${s.quiet_hours === 1 ? '' : 's'}. Check its battery, power or Wi-Fi.</p>`;
  return html`<p class="sns-heard">Last reading ${a} (${timeEl(s.last)}).</p>`;
}
function snsJudge(j) {
  if (!j) return '';
  const mark = { ok: '✓', low: '↓', high: '↑', bad: '!' }[j.level] || '';
  return html`<p class="sns-judge"><span class="tag sns-${j.level}"><span aria-hidden="true">${mark} </span>${j.word}</span> ${j.text}</p>`;
}
// a little line of the last 24 hours, drawn as an SVG with a text alternative; the plant's range is a lighter band behind it
function snsSpark(m) {
  const v = (m.spark || []).filter(x => x != null); if (v.length < 3) return '';
  const pts = m.spark, W = 160, H = 44, pad = 3;
  let lo = Math.min(...v), hi = Math.max(...v);
  if (m.range) { if (m.range[0] != null) lo = Math.min(lo, m.range[0]); if (m.range[1] != null) hi = Math.max(hi, m.range[1]); }
  if (hi - lo < 1) { hi += 0.5; lo -= 0.5; }
  const y = x => H - pad - (x - lo) / (hi - lo) * (H - 2 * pad), xs = i => pad + i / (pts.length - 1) * (W - 2 * pad);
  let d = '';
  pts.forEach((p, i) => { if (p == null) return; d += (d ? ' L' : 'M') + xs(i).toFixed(1) + ' ' + y(p).toFixed(1); });   // gaps are bridged
  const band = m.range && m.range[0] != null && m.range[1] != null ? html`<rect x="0" y="${y(m.range[1]).toFixed(1)}" width="${W}" height="${(y(m.range[0]) - y(m.range[1])).toFixed(1)}" class="sns-band"/>` : '';
  const first = v[0], last = v[v.length - 1];
  return html`<svg class="sns-spark" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="Last 24 hours: from ${snsVal(m.key, m.unit, first)} to ${snsVal(m.key, m.unit, last)}, lowest ${snsVal(m.key, m.unit, Math.min(...v))}, highest ${snsVal(m.key, m.unit, Math.max(...v))}">${band}<path d="${d.trim()}" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/></svg>`;
}
function snsMetric(m) {
  const day = m.day_n > 1 && m.day_min !== m.day_max ? html`<span class="hint">Last 24 hours: ${snsVal(m.key, m.unit, m.day_min)} to ${snsVal(m.key, m.unit, m.day_max)}.</span>` : '';
  const unitWord = m.key === 'weight_g' ? ' g' : ' points';
  const ch = m.change && Math.abs(m.change.by) >= 1 ? html`<span class="hint">${m.change.by < 0 ? 'Down' : 'Up'} ${Math.abs(Math.round(m.change.by))}${unitWord} since ${m.change.hours} hours before.</span>` : m.change ? html`<span class="hint">About the same as ${m.change.hours} hours before.</span>` : '';
  return html`<div class="sns-m"><dt>${m.label}</dt><dd><div class="sns-top"><span class="sns-big">${snsVal(m.key, m.unit, m.value)}</span>${snsSpark(m)}</div>${snsJudge(m.judge)}${ch}${day}</dd></div>`;
}
function snsCard(s, onPlant) {
  const dli = s.dli ? html`<div class="sns-m"><dt>Daily light (last 24 hours)</dt><dd><span class="sns-big">${String(s.dli.value)} mol/m²</span>${snsJudge(s.dli.judge)}<span class="hint">Worked out from ${s.dli.hours} hours of light readings.</span></dd></div>` : '';
  const where = html`<p>${s.plant ? html`In <a href="#/plant/${enc(s.plant.code)}">${s.plant.code} ${s.plant.common_name}</a>${s.plant.site ? ` (${s.plant.site.toLowerCase()})` : ''}. ` : html`<span class="muted">Not in a plant's pot, so its values are not compared with any plant's needs. </span>`}
    ${s.place ? html`At <a href="#/plants?${s.place.spot_id ? 'spot=' + s.place.spot_id : 'area=' + s.place.area_id}">${s.place.text}</a>.` : html`<span class="muted">No spot set.</span>`}</p>`;
  const look = s.needs_look ? html`<p class="sns-look"><strong>Needs a look.</strong></p>` : '';
  return html`<article class="sns-card${s.needs_look ? ' sns-alert' : ''}${s.quiet ? ' sns-off' : ''}" aria-labelledby="sns-h-${enc(s.device)}" id="sns-${enc(s.device)}">
    <h3 id="sns-h-${enc(s.device)}">${onPlant ? 'Sensor: ' : ''}${s.name}${s.named ? html` <span class="hint">(${s.device})</span>` : ''}</h3>
    ${look}${onPlant ? '' : where}${snsHeard(s)}
    ${s.metrics.length || dli ? html`<dl class="sns-dl">${s.metrics.map(snsMetric)}${dli}</dl>` : ''}
    ${s.plant && s.metrics.some(m => m.key === 'soil_moisture') ? html`<p class="hint">${s.auto_water ? 'A jump in soil moisture logs a watering for this plant.' : 'A jump in soil moisture is not logged as a watering.'}</p>` : ''}
    <div class="row noprint"><button class="btn small ghost" type="button" data-act="snsedit" data-dev="${s.device}">Change name, spot or plant</button>
      ${s.raw ? html`<button class="btn small ghost" type="button" data-act="snscal" data-dev="${s.device}">${s.calibrated ? 'Calibrate the soil probe again' : 'Calibrate the soil probe'}</button>` : ''}
      ${ME().role === 'owner' ? html`<button class="btn small danger" type="button" data-act="snsrm" data-dev="${s.device}">Forget this sensor</button>` : ''}</div></article>`;
}
async function viewSensors() {
  const d = await api('GET', '/api/sensors'); SNS.list = d.sensors;
  const L = SNS.list, look = L.filter(s => s.needs_look).length, quiet = L.filter(s => s.quiet).length;
  const ing = ME().role === 'owner' ? await api('GET', '/api/ingest').catch(() => null) : null;
  return {
    title: 'Sensors',
    html: html`<h1>Your sensors${L.length ? ` (${L.length})` : ''}</h1>
    <p class="muted">Every sensor that sends readings: its newest values, the last 24 hours, and whether they suit the plant it is in. The ones that need a look come first.</p>
    ${L.length ? html`<div class="verdict-box" role="status"><p><strong>${L.length} sensor${L.length === 1 ? '' : 's'}. ${look ? `${look} need${look === 1 ? 's' : ''} a look.` : 'Every linked plant is within its range.'}${quiet ? ` ${quiet} ${quiet === 1 ? 'has' : 'have'} gone quiet.` : ''}</strong></p></div>
      <div class="sns-grid">${L.map(s => snsCard(s, false))}</div>
      <p class="hint">Link a sensor to the plant whose pot it is in, and its values are compared with that plant's ranges; its newest values also show under Water and soil on that plant's page. Say where it sits (a spot or room) and the room's label leads to it too. Notifications can tell you when a pot is dry, a sensor sees dangerous cold, or one goes quiet (Settings → Notifications).</p>`
      : html`<p class="notice">No sensor has sent a reading yet. When one does, it appears here with its newest values and whether they suit its plant.</p>`}
    <section class="blk" id="sns-setup"><h2>Setting up a sensor</h2>
      <p>Any device that can make a web request can send readings: an ESP32 or ESP8266 running <strong>ESPHome</strong> (the easiest: no code, a short text file), a Raspberry Pi, or a phone app. The app's <code>sensors/</code> folder has a ready ESPHome file for a soil moisture probe, an air temperature and humidity sensor, a light sensor and a weighing cell under the pot, and the README section "Your sensors" says how to flash it.</p>
      ${ing ? html`<p>Readings go to <code>${ing.url.replace(/:\d+\//, ':8082/')}</code> on port 8082 with the header <code>X-Ingest-Token: ${ing.token}</code> (the same token as under Weather → Connect your sensor). Each reading names its <strong>device</strong>; a new device name appears here on its first reading.</p>` : html`<p class="muted">Only ${ME().owner_name} can see the sensor address and token (Weather → Connect your sensor).</p>`}
      <p class="hint">Fields a reading can carry: <code>temp_f</code> or <code>temp_c</code>, <code>humidity</code>, <code>par</code> or <code>lux</code>, <code>soil_moisture</code> (0 to 100), <code>soil_temp_f</code> or <code>soil_temp_c</code>, <code>soil_ph</code>, <code>weight_g</code>, and a <code>note</code>.</p></section>`,
  };
}
async function snsDialog(dev) {
  const s = SNS.list.find(x => x.device === dev); if (!s) return;
  let plants = [];
  try { plants = await api('GET', '/api/plants'); } catch (e) { toast(e.message, true); return; }
  const cur = s.plant ? s.plant.code : '', curPlace = s.place ? (s.place.spot_id ? 'spot:' + s.place.spot_id : 'area:' + s.place.area_id) : '';
  const places = ((META && META.where) || []).flatMap(h => h.areas.flatMap(a => [['area:' + a.id, `${a.name}${(META.where.length > 1) ? ' (' + h.home.name + ')' : ''}`], ...(a.spots || []).map(sp => ['spot:' + sp.id, `    ${sp.name}, ${a.name}`])]));
  const r = await modal(html`<form method="dialog"><h2>Sensor "${s.device}"</h2>
    <p>Give it a name you will recognise, say where it sits, and which plant's pot it is in. Its readings are then compared with that plant's needs.</p>
    <label class="f">Name<small>For example "Monstera pot" or "Porch shelf". Leave it empty to use "${s.device}".</small><input type="text" name="name" maxlength="60" value="${s.named ? s.name : ''}" autofocus></label>
    <label class="f">Where it sits<select name="place"><option value="">No particular spot</option>${places.map(([v, t]) => html`<option value="${v}" ${v === curPlace ? raw('selected') : ''}>${t}</option>`)}</select></label>
    <label class="f">Plant it is in<select name="plant"><option value="">Not in a plant</option>${plants.map(p => html`<option value="${p.code}" ${p.code === cur ? raw('selected') : ''}>${p.code}  ${p.common_name}</option>`)}</select></label>
    <label class="f">Say it has gone quiet after this many hours without a reading<input type="number" name="quiet_hours" min="1" max="168" step="1" value="${s.quiet_hours}"></label>
    <label class="chk"><input type="checkbox" name="auto_water" ${s.auto_water ? raw('checked') : ''}> When the soil moisture jumps up, log a watering for the plant</label>
    <div class="row"><button class="btn" value="ok">Save sensor</button><button class="btn ghost" value="cancel">Cancel</button></div></form>`);
  if (r !== 'ok' || !(await needName())) return;
  const f = dlg.querySelector('form').elements, pl = f.place.value;
  await guard(async () => {
    await api('PUT', '/api/sensors/' + enc(s.device), { name: f.name.value.trim(), plant: f.plant.value, quiet_hours: +f.quiet_hours.value || 3, auto_water: f.auto_water.checked,
      spot: pl.startsWith('spot:') ? pl.slice(5) : '', area: pl.startsWith('area:') ? pl.slice(5) : '' });
    toast('Sensor saved'); route();
  });
}
// 1.36.0: calibrating a soil probe in the app: the probe in dry air is 0 %, in a glass of water 100 %
let CALPOLL = 0;
function calBody(d, name) {
  const fresh = d.raw != null && d.raw_minutes != null && d.raw_minutes <= 20;
  return html`<p class="cal-now" role="status"><strong>Probe now:</strong> ${d.raw == null ? 'no raw reading yet' : `${d.raw} V, ${d.raw_minutes === 0 ? 'just now' : d.raw_minutes + ' minute' + (d.raw_minutes === 1 ? '' : 's') + ' ago'}`}${fresh ? '' : d.raw == null ? '' : ' (wait for a fresh one)'}</p>
    <ol class="cal-steps"><li>Take the probe out of the pot, wipe it, and hold it in the air. When a fresh reading shows, press <strong>This is dry air</strong>.</li>
      <li>Put the probe in a glass of water up to its line. When a fresh reading shows, press <strong>This is water</strong>.</li></ol>
    <p><strong>Saved:</strong> dry air ${d.cal_dry == null ? 'not yet' : d.cal_dry + ' V'}; water ${d.cal_wet == null ? 'not yet' : d.cal_wet + ' V'}.${d.done ? ' The app now works out the soil moisture from the probe\'s volts, so the numbers in the ESPHome file no longer matter.' : ''}</p>
    <div class="row"><button class="btn" type="button" data-act="calstep" data-step="dry" data-dev="${d.device}" ${fresh ? '' : raw('disabled')}>This is dry air</button>
      <button class="btn" type="button" data-act="calstep" data-step="wet" data-dev="${d.device}" ${fresh ? '' : raw('disabled')}>This is water</button>
      ${d.cal_dry != null || d.cal_wet != null ? html`<button class="btn ghost" type="button" data-act="calstep" data-step="clear" data-dev="${d.device}">Start over</button>` : ''}</div>`;
}
async function calDialog(dev) {
  const s = SNS.list.find(x => x.device === dev), name = s ? s.name : dev;
  let d; try { d = await api('GET', '/api/sensors/' + enc(dev) + '/calibrate'); } catch (e) { toast(e.message, true); return; }
  clearInterval(CALPOLL);
  CALPOLL = setInterval(async () => { if (!dlg.open || !document.getElementById('cal-box')) { clearInterval(CALPOLL); return; } try { const x = await api('GET', '/api/sensors/' + enc(dev) + '/calibrate'); const b = document.getElementById('cal-box'); if (b) b.innerHTML = rend(calBody(x, name)); } catch (e) { /* next time */ } }, 5000);
  await modal(html`<form method="dialog"><h2>Calibrate the soil probe: ${name}</h2>
    <p>Each probe reads a little differently. Two readings, one in dry air and one in water, tell the app what 0 % and 100 % look like for this one. The reading refreshes every few seconds.</p>
    <div id="cal-box">${calBody(d, name)}</div>
    <div class="row"><button class="btn ghost" value="cancel">Close</button></div></form>`);
  clearInterval(CALPOLL); route();
}
Object.assign(acts, {
  snscal(el) { calDialog(el.dataset.dev); },
  async calstep(el) {
    if (!(await needName())) return;
    try { const d = await api('POST', '/api/sensors/' + enc(el.dataset.dev) + '/calibrate', { step: el.dataset.step }); const b = document.getElementById('cal-box'); if (b) b.innerHTML = rend(calBody(d, '')); toast(el.dataset.step === 'clear' ? 'Calibration cleared' : el.dataset.step === 'dry' ? 'Dry air saved' : 'Water saved'); }
    catch (e) { toast(e.message, true); }
  },
  snsedit(el) { snsDialog(el.dataset.dev); },
  async snsrm(el) {
    const s = SNS.list.find(x => x.device === el.dataset.dev);
    if (!(await confirmBox('Forget this sensor?', `${s ? s.name : el.dataset.dev} and all its readings are removed. If it sends again, it comes back as a new sensor.`, 'Forget the sensor', true))) return;
    await guard(async () => { await api('DELETE', '/api/sensors/' + enc(el.dataset.dev)); toast('Sensor forgotten'); route(); });
  },
});
// 1.46.0: what this module adds, said once (features.js) instead of watching the page for changes:
//  - the page #/sensors (already in the top bar's Weather section);
//  - on a plant's page, the sensor in its pot, under the "Water and soil" title.
addFeature({
  name: 'sensors',
  pages: { sensors: { view: viewSensors, nav: 'sensors' } },
  adds: {
    id: 'sns-plant',
    match: parts => parts[0] === 'plant' && !!parts[1] && parts[2] !== 'edit',
    anchor: 'section#soil > h2', where: 'afterend',
    load: async parts => { const L = (await api('GET', '/api/sensors?plant=' + enc(parts[1]))).sensors; return L.length ? L : null; },
    html: L => html`<div id="sns-plant" class="sns-plant">${L.map(s => snsCard(s, true))}</div>`,
    then: (el, L) => L.forEach(s => { if (!SNS.list.some(x => x.device === s.device)) SNS.list.push(s); }),
  },
});
