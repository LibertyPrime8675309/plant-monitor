/* Plant record front end: past days, and the edit and add forms. One of the files app.js was split into in 1.32.0; they load in order (index.html) and share one scope,
   so a function here may call any other. Plain JavaScript, no inline handlers (the server's content policy forbids them). */
'use strict';

// ---------- past days for Temperature, Humidity, Light, Water and soil ----------
const HMAP = {
  temp: ['temp_f', 'Temperature', '°F', 1], humidity: ['humidity', 'Humidity', '%', 0], vpd: ['vpd', 'Air dryness (VPD)', ' kPa', 2], light: ['par', 'Light', '', 0],
  soil_moisture: ['soil_moisture', 'Soil moisture', '%', 0], soil_temp: ['soil_temp_f', 'Root-zone temperature', '°F', 1], soil_ph: ['soil_ph', 'Soil pH', '', 1],
};
const HKIND = { temp: ['temp'], hum: ['humidity', 'vpd'], light: ['light'], soil: ['soil_moisture', 'soil_temp', 'soil_ph'] };
const HS = {};
function histBlock(kind) {
  return html`<details class="histbox noprint" data-hist="${kind}"><summary>Past days: pick a date to see what it was</summary><div class="hist-body" id="hb-${kind}"></div></details>`;
}
function histShell(kind) {
  const S = HS[kind], mets = HKIND[kind];
  return html`${mets.length > 1 ? html`<div class="opts tabs" role="group" aria-label="What to look at">${mets.map(m => html`<button type="button" class="btn ${S.metric === m ? '' : 'ghost'} small" data-act="histmetric" data-kind="${kind}" data-m="${m}" aria-pressed="${String(S.metric === m)}">${HMAP[m][1]}</button>`)}</div>` : ''}
    <div class="chart-tools"><label>Readings from<select data-f="histsrc" data-kind="${kind}">${[['auto', 'Best available'], ['sensor', 'My sensor'], ['manual', 'Typed in by me'], ['weather', 'Online weather (outdoors)']].map(([v, l]) => html`<option value="${v}" ${S.source === v ? raw('selected') : ''}>${l}</option>`)}</select></label></div>
    <p class="hint">Each day is marked by how that day's readings compared with this plant's range <em>as recorded on that day</em>. Weather history comes from the online weather for your area (outdoors); sensor and typed-in values appear once you have recorded them.</p>
    <div id="cal-h-${kind}"></div><div id="hd-${kind}"></div>`;
}
async function histOpen(kind) {
  if (!CUR) return;
  HS[kind] = HS[kind] || { metric: HKIND[kind][0], source: 'auto', day: null };
  const S = HS[kind], box = document.getElementById('hb-' + kind); if (!box) return;
  box.innerHTML = rend(histShell(kind));
  await histCal(kind);
}
async function histCal(kind) {
  const S = HS[kind], code = CUR.p.code, m = S.metric, [, , unit, dec] = HMAP[m];
  const doc = document.getElementById('hb-' + kind); if (doc) { const h = doc.querySelector('[data-f=histsrc]'); if (h) h.value = S.source; }
  await calMount('h-' + kind, {
    legend: 'Marks: ✔ in range, ▲ a little out, ■ out of range, ✖ danger. Days with no mark have no readings from the chosen source.',
    async load(month, c) { const d = await api('GET', `/api/plants/${enc(code)}/daily?metric=${m}&month=${month}&source=${S.source}`); c.data = Object.fromEntries(d.days.map(x => [x.date, x])); c.meta = d; },
    cell(ds, c) {
      const d = c.data[ds];
      if (!d || d.status === 'none' || !d.source) return { cls: 's-none', badges: [], aria: 'No readings.' };
      const lv = LEVELBD[d.status] || LEVELBD.info, val = m === 'light' ? (d.dli != null ? `${fmt(d.dli, 1)} mol/m²` : `${fmt(d.daytime_avg, 0)} PAR`) : unit === '°F' ? tF(fmt(d.avg, dec)) : `${fmt(d.avg, dec)}${unit}`;   // 1.47.0: temperatures in the person's unit
      const badges = [{ cls: lv[0], text: lv[1] }, { cls: 'b-val', text: val }];
      if (d.fed && d.fed.length) badges.push({ cls: 'b-fed', text: '● Fed' });
      return { cls: lv[0], badges, aria: `${lv[1].replace(/^\S+ /, '')}, ${val}${d.fed && d.fed.length ? ', fertilizer applied' : ''}.` };
    },
    pick(ds) { histDay(kind, ds); },
  }, null, S.day || todayStr());
  const c = CALS['h-' + kind];
  histDay(kind, c.sel);
}
async function histDay(kind, ds) {
  const S = HS[kind], el = document.getElementById('hd-' + kind), code = CUR.p.code, m = S.metric;
  if (!el) return; S.day = ds;
  const [col, label, unit, dec] = HMAP[m], c = CALS['h-' + kind], d = (c.data || {})[ds];
  el.innerHTML = rend(html`<p class="loading">Loading ${longDay(ds)}</p>`);
  let day; try { day = await api('GET', `/api/plants/${enc(code)}/day?date=${ds}`); } catch (e) { el.innerHTML = rend(html`<p class="notice bad">${e.message}</p>`); return; }
  if (S.day !== ds) return;
  const names = day.source_names, series = [];
  const cls = { sensor: 's1', weather: 's2', manual: 's3' };
  ['sensor', 'manual', 'weather'].forEach(s => { const pts = (day.sources[s] || []).filter(x => x[col] != null).map(x => [Date.parse(x.t), x[col]]); if (pts.length && (S.source === 'auto' || S.source === s)) series.push({ name: names[s], cls: cls[s], pts, key: s }); });
  const main = d && d.source ? series.find(x => x.key === d.source) || series[0] : series[0];
  const vals = main ? main.pts.map(x => x[1]) : [], lo = d ? d.lo : day.ranges[HMAP_RANGE[m][0]], hi = d ? d.hi : day.ranges[HMAP_RANGE[m][1]];
  const f = x => unit === '°F' ? tF(fmt(x, dec)) : fmt(x, dec) + unit;        // 1.47.0: temperatures in the person's unit (the chart converts itself)
  const rangeTxt = has(lo) || has(hi) ? `${has(lo) ? 'from ' + (m === 'light' && d && d.judged_on === 'dli' ? fmt(lo, 1) + ' mol/m²/day' : f(lo)) : ''}${has(lo) && has(hi) ? ' ' : ''}${has(hi) ? 'to ' + (m === 'light' && d && d.judged_on === 'dli' ? fmt(hi, 1) + ' mol/m²/day' : f(hi)) : ''}` : '';
  const now = CUR.p, lvl = d && LEVELBD[d.status];
  const refs = [], bands = [];
  if (has(lo) && has(hi) && !(m === 'light' && d && d.judged_on === 'dli')) bands.push({ lo, hi, label: 'Comfortable range then' });
  else if (has(lo) && !(m === 'light' && d && d.judged_on === 'dli')) refs.push({ v: lo, label: 'Lowest comfortable' });
  else if (has(hi) && !(m === 'light' && d && d.judged_on === 'dli')) refs.push({ v: hi, label: 'Highest comfortable' });
  if (m === 'temp' && has(day.ranges.temp_damage_below)) refs.push({ v: day.ranges.temp_damage_below, label: 'Damage below ' + day.ranges.temp_damage_below + '°F' });   // tempChart() converts this label with the chart
  const cur = HMAP_RANGE[m].map(k => now[k]);
  el.innerHTML = rend(html`<section class="day-card" aria-live="polite"><h3>${longDay(ds)}</h3>
    ${main ? html`<p class="verdict">${lvl ? html`<span class="${lvl[0] === 's-ok' ? 'st-ok' : lvl[0] === 's-near' ? 'st-near' : lvl[0] === 's-bad' ? 'st-bad' : lvl[0] === 's-danger' ? 'st-danger' : 'st-mute'}">${lvl[1]}</span>` : ''}</p>
      <dl class="dl"><dt>${label} (${names[main.key]})</dt><dd>lowest ${f(Math.min(...vals))}, average ${f(vals.reduce((a, b) => a + b, 0) / vals.length)}, highest ${f(Math.max(...vals))}${m === 'light' && d && d.dli != null ? `. Daily light ${fmt(d.dli, 1)} mol/m².` : ''}</dd>
        ${d && d.hours_in != null && m !== 'light' ? html`<dt>Hours in range</dt><dd>${d.hours_in} of ${d.n} hours that had readings</dd>` : ''}
        <dt>Comfortable range then</dt><dd>${rangeTxt || 'No range was recorded for this plant.'}${d && d.range_from_now ? ' (taken from the current page, because the page had none on that day)' : ''}${day.version !== day.current_version ? html` (page version ${day.version}; the current page is version ${day.current_version}${cur.some(x => has(x)) && (cur[0] !== lo || cur[1] !== hi) ? ', and its range is now ' + (has(cur[0]) ? f(cur[0]) : '?') + ' to ' + (has(cur[1]) ? f(cur[1]) : '?') : ''})` : ''}</dd>
        ${day.fertilized.length ? html`<dt>Fertilizer</dt><dd>${day.fertilized.map(e => `${e.product}, ${doseText(e)}`).join('; ')}</dd>` : ''}</dl>
      ${chartCard('hd-' + kind, { title: `${label} on ${midDay(ds)}`, series, fmt: v => String(Math.round(v * 100) / 100), unit, bands, refs, zero: m === 'light', clamp: m === 'humidity' || m === 'soil_moisture' ? [0, 100] : null })}`
      : html`<p>No ${label.toLowerCase()} readings were recorded on this day${S.source === 'auto' ? '' : ' from ' + (names[S.source] || 'that source')}.</p>
        <p class="hint">${m.startsWith('soil') ? 'Soil values come from your sensor or from numbers you type in under Current conditions.' : 'Online weather history is stored from the first time the app ran (it loads about 3 months back); sensor values start when the sensor first reports. You can load older weather on the Weather page.'}</p>
        ${has(lo) || has(hi) ? html`<p>Comfortable range then: ${rangeTxt}.</p>` : ''}`}
    <div class="row noprint"><button class="btn ghost small" type="button" data-act="calnav" data-cal="h-${kind}" data-d="0">Back to today</button></div></section>`);
  if (main) paintChart('hd-' + kind);
}
const HMAP_RANGE = { temp: ['temp_ideal_low', 'temp_ideal_high'], humidity: ['humidity_low', 'humidity_high'], vpd: ['vpd_low', 'vpd_high'], light: ['par_low', 'par_high'], soil_moisture: ['soil_moisture_low', 'soil_moisture_high'], soil_temp: ['soil_temp_low', 'soil_temp_high'], soil_ph: ['soil_ph_low', 'soil_ph_high'] };

// ---------- edit and create ----------
const GROUPS = [
  ['Names and place', ['common_name', 'scientific_name', 'aliases', 'plant_type', 'home_id', 'area_id', 'spot_id', 'location', 'container', 'pot_id', 'tray_id', 'height_in']],
  ['Identification', ['id_confidence', 'id_basis', 'id_alternatives', 'id_improve']],
  ['About this plant', ['growth_habit', 'kingdom', 'taxon_order', 'family', 'genus', 'height_ground', 'width_ground', 'height_pot', 'width_pot', 'growth_rate', 'lifespan',
    'zone_low', 'zone_high', 'zone_notes', 'heat_zone_high', 'heat_zone_low', 'heat_zone_source', 'native_range', 'conservation_status', 'invasive', 'bloom', 'fruit', 'danger_humans', 'danger_animals', 'pet_safety', 'propagation', 'sources']],
  ['Temperature', ['temp_ideal_low', 'temp_ideal_high', 'temp_damage_below', 'temp_lethal_below', 'temp_damage_above', 'temp_notes']],
  ['Humidity and air dryness', ['humidity_low', 'humidity_high', 'vpd_low', 'vpd_high', 'humidity_notes']],
  ['Sunlight', ['light_summary', 'light_hours', 'par_low', 'par_high', 'dli_low', 'dli_high', 'light_notes']],
  ['Water and soil', ['water_every_days', 'water_notes', 'soil_medium', 'soil_ph_low', 'soil_ph_high', 'soil_moisture_low', 'soil_moisture_high', 'soil_temp_low', 'soil_temp_high']],
  ['Nutrients', ['fertilizer', 'npk_ratio', 'fert_strength', 'nutrients', 'fert_from_month', 'fert_to_month', 'fert_every_days']],
  ['Winter plan', ['winter_plan', 'winter_summary', 'winter_triggers', 'winter_steps', 'indoor_setup']],
  ['Health', ['health_rating', 'health_summary', 'health_observations', 'health_steps']],
  ['Pests and diseases', ['pests_watch', 'pest_steps', 'pests_current', 'pests_found', 'leaf_type', 'pot_size']],
  ['Notes', ['notes']],
];
const HINTS = {
  id_confidence: 'Whole number from 0 to 100.', id_improve: 'One item per line. These show on the page and in the copy-for-Claude request.',
  temp_damage_below: 'Leaves or stems start to be hurt below this.', temp_lethal_below: 'The plant is likely to die below this.',
  temp_ideal_low: 'Lower edge of the comfortable range.', temp_ideal_high: 'Upper edge of the comfortable range.',
  temp_damage_above: 'Leaves start to scorch above this.', vpd_low: 'Vapour pressure deficit in kPa. A sensor can work it out from temperature and humidity.',
  par_low: 'PAR in umol/m2/s at the leaves. Full midday sun is about 1800.', dli_low: 'Mol of light per square metre per day.',
  soil_moisture_low: 'As read by your soil probe, 0 to 100.', soil_temp_low: 'Temperature of the root zone in F.',
  water_every_days: 'Leave empty to let the app work it out from the soil moisture range. Hot weather shortens the gap; cool weather and being indoors lengthen it.',
  winter_steps: 'One step per line, in order.',
  pests_found: 'One per line, from: Spider mites, Mealybugs, Scale, Aphids, Whiteflies, Thrips, Ants, Fungus gnats, Root mealybugs, Slugs or snails, Pill bugs or earwigs, Other. The plant page has tick boxes for these.',
  npk_ratio: 'Three numbers for nitrogen, phosphate and potash, such as 3-1-2. The Fertilizer page finds your closest fertilizer.',
  fert_strength: 'How strong to mix it. The Fertilizer page works out the amount per gallon from this.',
  pet_safety: 'Used by the Pets filter on the Plants page. "Safe for pets" only where the ASPCA lists the plant as non-toxic.',
  home_id: 'Where the plant lives. Weather, frost warnings and watering for a home only list its own plants.',
  heat_zone_high: 'AHS heat zone, 1 to 12: the hottest it is listed for, such as 12.', heat_zone_low: 'AHS heat zone, 1 to 12: the coolest it is listed for, such as 1.', heat_zone_source: 'Where the range came from: a title, a | and the web address.',
  zone_low: 'USDA zone, such as 9b or 10. The page compares it with the zone where you are.', zone_high: 'USDA zone, such as 11.',
  height_ground: 'For example 6 to 10 ft.', height_pot: 'For example 3 to 5 ft.', propagation: 'One method per line.',
  sources: 'One per line: a title, a | and the web address, for example "NC State Extension: Aloe vera | https://...".',
  height_in: 'Today, from the surface the pot stands on to the top of the plant. The Grow lights page uses it to check the plant fits under a shelf or a light.',
  leaf_type: 'Decides which pest treatments suit it before it comes inside.', pot_size: 'Whether the pot can be soaked in a bucket or tub.', health_steps: 'One step per line, in order.', indoor_setup: 'One item per line.',
};
const rangeOf = n => (META.int_ranges && META.int_ranges[n]) || (META.num_ranges && META.num_ranges[n]) || [-60, 150];
// 1.47.0: a plant's temperatures are kept in °F and shown and typed in the person's unit (Display, Units); submitForm() converts back
const TEMP_FIELDS = ['temp_ideal_low', 'temp_ideal_high', 'temp_damage_below', 'temp_lethal_below', 'temp_damage_above', 'soil_temp_low', 'soil_temp_high'];
const tempLabel = s => String(s).replace(/\((°?F)\)/, '(' + tU() + ')');
const LEN_FIELDS = ['height_in'];                  // 1.56.0: kept in inches, shown and typed in the person's length unit
function fieldInput(f, val) {
  const hint = HINTS[f.name] || (f.kind === 'list' ? 'One item per line.' : '');
  const wide = (f.kind === 'long' || f.kind === 'list') ? 'wide' : '';
  let v = val == null ? '' : val;          // let: the location defaults to Outdoors below (1.17.1 fixes "Add a plant", which stopped on it)
  let inp;
  const isTemp = TEMP_FIELDS.includes(f.name);
  if (isTemp) { f = { ...f, label: tempLabel(f.label) }; if (v !== '') v = tNum(v); }
  if (LEN_FIELDS.includes(f.name)) { f = { ...f, label: String(f.label).replace('(in)', '(' + lenU() + ')') }; if (v !== '') v = lenF(v, false); }
  if (f.kind === 'long' || f.kind === 'list') inp = html`<textarea name="${f.name}" rows="${f.kind === 'list' ? 5 : 4}">${v}</textarea>`;
  else if (f.kind === 'int' && isTemp) { const mm = rangeOf(f.name); inp = html`<input type="number" inputmode="decimal" step="${unitsGet().temp === 'c' ? '0.5' : '1'}" min="${tNum(mm[0])}" max="${tNum(mm[1])}" name="${f.name}" value="${v}">`; }
  else if (f.kind === 'int') { const mm = rangeOf(f.name); inp = html`<input type="number" inputmode="numeric" step="1" min="${mm[0]}" max="${mm[1]}" name="${f.name}" value="${v}">`; }
  else if (f.kind === 'num') { const mm = rangeOf(f.name); inp = html`<input type="number" inputmode="decimal" step="any" min="${mm[0]}" max="${mm[1]}" name="${f.name}" value="${v}">`; }
  else if (f.kind === 'area') return whereInputs(v, FORMP);          // 1.29.0: inside or outside, area or room, spot (all three)
  else if (f.kind === 'spot') return '';
  else if (f.kind === 'pot' || f.kind === 'tray') {                   // 1.29.0: one of your pots or trays
    const items = ((META && META.containers) || []).filter(x => x.kind === f.kind);
    inp = html`<select name="${f.name}"><option value="">None chosen</option>${items.map(x => html`<option value="${x.id}" ${String(v) === String(x.id) ? raw('selected') : ''}>${x.name} (${x.size}; ${x.free} of ${x.qty} free)</option>`)}</select>`;
    return html`<label class="f">${f.label}<small>${items.length ? 'From Pots and trays (Care).' : html`Add yours on <a href="#/pots">Pots and trays</a> first.`}</small>${inp}</label>`;
  }
  else if (f.kind === 'home') {       // 1.28.0
    const hs = HOMES(); if (hs.length < 2 && !v) return '';
    inp = html`<select name="${f.name}" data-f="wherehome">${hs.map(h => html`<option value="${h.is_home ? '' : h.id}" ${(h.is_home ? !v : String(v) === String(h.id)) ? raw('selected') : ''}>${h.name}${h.is_home ? ' (main home)' : ''}</option>`)}</select>`;
  }
  else if (f.kind === 'enum') {
    const opts = (META.enums && META.enums[f.name]) || (f.name === 'winter_plan' ? META.winter_plans : f.name === 'site' ? (META.sites || ['Outdoors', 'Indoors']) : META.health);
    const optional = (META.optional_enums || []).includes(f.name);
    if (f.name === 'site' && !v) v = 'Outdoors';
    inp = html`<select name="${f.name}">${optional ? html`<option value="" ${!v ? raw('selected') : ''}>Not set</option>` : ''}${opts.map(o => html`<option ${o === v ? raw('selected') : ''}>${o}</option>`)}</select>`;
  }
  else inp = html`<input type="text" name="${f.name}" value="${v}" ${f.name === 'common_name' ? raw('required') : ''}>`;
  return html`<label class="f ${wide}">${f.label}${hint ? html`<small>${hint}</small>` : ''}${inp}</label>`;
}
let FORMP = null;                    // the plant the form is for (null: a new one), for whereInputs()
const WHERE = () => (META && META.where) || [];
const whereHome = hid => WHERE().find(h => hid ? String(h.home.id) === String(hid) && !h.home.is_home : h.home.is_home) || WHERE()[0] || { areas: [] };
function whereAreaOpts(hid, side, cur) {
  const A = whereHome(hid).areas.filter(a => a.side === side);
  return html`${A.map(a => html`<option value="${a.id}" ${String(a.id) === String(cur) ? raw('selected') : ''}>${a.name}${a.sheltered ? (side === 'out' ? ' (roof overhead)' : '') : (side === 'in' ? ' (not heated)' : '')}</option>`)}`;
}
function whereSpotOpts(aid, cur) {
  const a = WHERE().flatMap(h => h.areas).find(x => String(x.id) === String(aid));
  return html`<option value="">No particular spot</option>${(a ? a.spots : []).map(sp => html`<option value="${sp.id}" ${String(sp.id) === String(cur) ? raw('selected') : ''}>${sp.name}</option>`)}`;
}
function whereInputs(aid, p) {
  const all = WHERE().flatMap(h => h.areas), a = all.find(x => String(x.id) === String(aid)) || null;
  const hid = p ? p.home_id : (NEWFILL && NEWFILL.home_id) || '', side = a ? a.side : ((p && ['Indoors', 'Garage or shed'].includes(p.site)) ? 'in' : 'out');
  return html`<fieldset class="f wide where-f"><legend>Where it is</legend>
    <div class="opts" role="radiogroup" aria-label="Inside or outside">${[['out', 'Outside'], ['in', 'Inside']].map(([k, l]) => html`<label><input type="radio" name="__side" value="${k}" data-f="whereside" ${k === side ? raw('checked') : ''}><span>${l}</span></label>`)}</div>
    <label class="f">Area or room<small>Change the list on <a href="#/where">Rooms and spots</a>.</small><select name="area_id" data-f="wherearea">${whereAreaOpts(hid, side, aid)}</select></label>
    <label class="f">Spot<select name="spot_id">${whereSpotOpts(a ? a.id : (whereHome(hid).areas.find(x => x.side === side) || {}).id, p ? p.spot_id : '')}</select></label></fieldset>`;
}
function whereRefresh(form, what) {
  const hid = form.elements.home_id ? form.elements.home_id.value : '', side = (form.querySelector('[name=__side]:checked') || {}).value || 'out';
  const as = form.elements.area_id, ss = form.elements.spot_id; if (!as) return;
  if (what !== 'area') as.innerHTML = rend(whereAreaOpts(hid, side, as.value));
  if (ss) ss.innerHTML = rend(whereSpotOpts(as.value, ss.value));
}
function whereWords(p) {               // "Outside, Yard, Black bench"
  const a = WHERE().flatMap(h => h.areas).find(x => String(x.id) === String(p.area_id)); if (!a) return '';
  const sp = a.spots.find(x => String(x.id) === String(p.spot_id));
  return `${a.side === 'out' ? 'Outside' : 'Inside'}, ${a.name}${sp ? ', ' + sp.name : ''}`;
}
const contById = id => ((META && META.containers) || []).find(x => String(x.id) === String(id));
function viewForm(p) {
  FORMP = p;
  const F = Object.fromEntries(META.fields.map(f => [f.name, f]));
  const isNew = !p;
  return {
    title: isNew ? 'Add a plant' : 'Edit ' + p.common_name,
    html: html`<p class="crumb"><a href="${isNew ? '#/plants' : '#/plant/' + enc(p.code)}">${isNew ? 'All plants' : 'Back to ' + p.common_name}</a></p>
    <h1>${isNew ? 'Add a plant' : 'Edit ' + p.code}</h1>
    ${isNew ? addModeRow('one') : ''}
    <p class="muted">${isNew ? 'Only the common name is required. Without a connection the plant is kept on this device and sent later; its first photo is then checked by the picture checker, and the names are offered on the Offline page.' : 'Saving makes version ' + (p.version + 1) + '. The old text stays in the page history.'}</p>
    <form data-form="${isNew ? 'new' : 'edit'}" ${p ? raw('data-code="' + esc(p.code) + '" data-ver="' + p.version + '"') : ''} autocomplete="off">
      ${isNew && NEWFILL ? html`<p class="notice ok" role="note">${NEWFILL.__from}: the names are filled in${NEWFILL.__pic ? ', and the picture is added when you save' : ''}. Check them before saving.</p>` : ''}
      ${isNew ? html`<fieldset><legend>Photos</legend><div class="field-grid">
        <label class="f wide">Photos<small>Optional. Take them now or choose them from your photos; the first one becomes the main photo. With a photo, the common name can wait: a stand-in name is used until the photo is checked.</small><input type="file" name="__photos" accept="image/*" multiple data-f="newphotos"></label>
        <p class="row wide"><button class="btn ghost" type="button" data-act="newfill" id="newfill-btn" disabled>Fill in the names from the first photo</button></p>
        <div id="newfill-st" class="hint wide" role="status" aria-live="polite">Choose a photo, then the names can be filled in from it${ID.keys && ID.keys.plantnet ? ' (this computer and Pl@ntNet)' : ''}.</div></div></fieldset>` : ''}
      ${GROUPS.map(([title, names]) => html`<fieldset><legend>${title}</legend><div class="field-grid fg-form">${names.map(n => fieldInput(F[n], p ? p[n] : NEWFILL && NEWFILL[n] ? NEWFILL[n] : (n === 'winter_plan' ? 'Move indoors' : n === 'health_rating' ? 'Fair' : '')))}</div></fieldset>`)}
      ${isNew ? '' : html`<fieldset><legend>Change note</legend><label class="f">What did you change, and why?<small>Optional. It appears in the page history.</small><input type="text" name="__note" maxlength="300"></label></fieldset>`}
      <div id="form-err"></div>
      <div class="sticky-save"><button class="btn" type="submit">${isNew ? 'Add plant' : 'Save changes'}</button>
        <a class="btn ghost" href="${isNew ? '#/plants' : '#/plant/' + enc(p.code)}">Cancel</a></div>
    </form>`,
  };
}
// 1.28.0: add several plants at once from photos: each photo is checked, photos of one plant are grouped, the fields are filled
// in from the likeliest species, and nothing is added until you have checked them on the review screen.
function addModeRow(cur) {
  return html`<nav class="row add-mode" aria-label="How many plants">
    <a class="btn ${cur === 'one' ? '' : 'ghost'}" href="#/new" ${cur === 'one' ? raw('aria-current="page"') : ''}>One plant</a>
    <a class="btn ${cur === 'several' ? '' : 'ghost'}" href="#/new/several" ${cur === 'several' ? raw('aria-current="page"') : ''}>Several plants from photos</a></nav>`;
}
let NEWID = { r: null, ex: null };              // 1.40.0: the names found for the Add a plant form's photos, and the ones said "Not this" to
const SEV = { step: 'pick', photos: [], order: [], plants: [], home: '', site: 'Outdoors', busy: false, done: null };
const SEV_FIELDS = [['common_name', 'Common name', 'text'], ['scientific_name', 'Scientific name', 'text'], ['plant_type', 'Plant type', 'text'],
  ['family', 'Family', 'text'], ['genus', 'Genus', 'text'], ['pet_safety', 'Safety for pets', 'pets'], ['id_confidence', 'ID confidence (%)', 'int'],
  ['location', 'Spot (where exactly)', 'text'], ['notes', 'Notes', 'long']];
const SEV_REL = [['same', 'Same plant as the photo above'], ['new', 'A different plant'], ['all', 'Shows all of them (a wide shot: it goes on every plant)'], ['out', 'Leave this photo out']];
function sevDefaultHome() { const cur = META.place, h = HOMES().find(x => String(x.id) === String(cur && cur.id)); return h && !h.is_home ? String(h.id) : ''; }
async function viewSeveral() {
  if (SEV.step === 'pick' && !SEV.photos.length) { SEV.home = sevDefaultHome(); }
  if (!ID.keys) { try { ID.keys = await api('GET', '/api/identify/settings'); } catch (e) { /* no Pl@ntNet button then */ } }
  return { title: 'Add several plants', html: html`<p class="crumb"><a href="#/plants">All plants</a></p><h1>Add a plant</h1>${addModeRow('several')}
    <div id="sev">${sevHtml()}</div>` };
}
function sevHtml() {
  if (SEV.done) return html`<div class="notice ok" role="status"><strong>${SEV.done.length} plant${SEV.done.length === 1 ? '' : 's'} added:</strong>
    <ul>${SEV.done.map(c => html`<li><a href="#/plant/${enc(c)}">${c} ${(ALL.find(p => p.code === c) || {}).common_name || ''}</a></li>`)}</ul>
    <p>Each one has a page of its own now. The care details (temperature, water, light and so on) are still empty: fill them in on each page, or ask Claude with "Copy my answers for Claude".</p></div>
    <p class="row"><button class="btn" type="button" data-act="sevreset">Add more plants</button><a class="btn ghost" href="#/plants">Go to the Plants page</a></p>`;
  const homes = HOMES();
  const homeSel = homes.length > 1 ? html`<label class="f">Home<small>Where these plants live.</small><select data-f="sevset" data-k="home">${homes.map(h => html`<option value="${h.is_home ? '' : h.id}" ${(h.is_home ? !SEV.home : String(SEV.home) === String(h.id)) ? raw('selected') : ''}>${h.name}</option>`)}</select></label>` : '';
  const siteSel = html`<label class="f">Location<select data-f="sevset" data-k="site">${(META.sites || ['Outdoors', 'Indoors']).map(x => html`<option ${x === SEV.site ? raw('selected') : ''}>${x}</option>`)}</select></label>`;
  if (SEV.step !== 'review') return html`<p>Choose photos of several plants at once, from this device or your phone. Each photo is checked by the picture checker on this computer, and each plant's names and details are filled in from what it looks like. On the next screen you say, photo by photo, whether it shows the same plant as the one above or a different plant, and a wide shot of several plants together can go on every one of them. Nothing is added until you have checked everything.</p>
    <form data-form="sevgo" class="sev-pick">
      <div class="field-grid">${homeSel}${siteSel}
        <label class="f wide">Photos<small>Choose as many as you like (JPG or PNG), from your photos or the camera. They are put in the order they were taken. A photo of the plant's label or tag helps.</small><input type="file" name="files" accept="image/*" multiple required></label></div>
      <div class="row"><button class="btn" type="submit" ${SEV.busy ? raw('disabled') : ''}>Check these photos</button></div>
      <p id="sev-prog" role="status" aria-live="polite" class="muted"></p></form>`;
  const N = SEV.plants.length, keep = SEV.plants.filter(p => p.add).length;
  const shared = SEV.photos.filter(p => p.rel === 'all'), out = SEV.photos.filter(p => p.rel === 'out');
  return html`<p>${SEV.photos.length} photo${SEV.photos.length === 1 ? '' : 's'}, put together as ${N} plant${N === 1 ? '' : 's'}. Under each photo, say whether it shows the same plant as the photo above or a different one; the plants below follow your answers. Then check each plant: pick the right name and fix anything that is wrong. Plants are only added when you press <strong>Add ${keep} plant${keep === 1 ? '' : 's'}</strong> at the bottom.</p>
    <div class="field-grid sev-all">${homeSel}${siteSel}</div>
    ${SEV.plants.map((P, gi) => sevPlantHtml(P, gi, N))}
    ${shared.length ? html`<fieldset class="sev-plant sev-shared" id="sev-shared" data-section="Photos of all of them"><legend>Shows all of them (${shared.length})</legend>
      <p class="hint">These wide shots go on every plant added, with the caption "Several plants together".</p><ul class="sev-pics">${shared.map(ph => sevPicHtml(ph))}</ul></fieldset>` : ''}
    ${out.length ? html`<fieldset class="sev-plant sev-off" id="sev-out" data-section="Photos left out"><legend>Left out (${out.length})</legend><ul class="sev-pics">${out.map(ph => sevPicHtml(ph))}</ul></fieldset>` : ''}
    <div class="sticky-save"><button class="btn" type="button" data-act="sevsave" ${keep && !SEV.busy ? '' : raw('disabled')}>Add ${keep} plant${keep === 1 ? '' : 's'}</button>
      <button class="btn ghost" type="button" data-act="sevreset">Start again</button><span id="sev-err" role="alert"></span></div>`;
}
function sevPicHtml(ph) {                 // one photo with the question under it (the first photo in the order only asks about wide shots and leaving out)
  const i = SEV.photos.indexOf(ph), first = SEV.order[0] === i;
  const opts = first ? SEV_REL.filter(([k]) => k !== 'same').map(([k, l]) => [k, k === 'new' ? 'The first plant' : l]) : SEV_REL;
  return html`<li><img src="${ph.url}" alt="Photo ${i + 1}${ph.name ? ', ' + ph.name : ''}" width="${ph.w || 400}" height="${ph.h || 400}" loading="lazy" decoding="async">
    <span class="hint">${ph.taken ? new Date(ph.taken).toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }) : 'No date in the photo'}${ph.error ? html`<br><span class="bad-text">${ph.error}</span>` : ''}${ph.why ? html`<br>${ph.why}` : ''}</span>
    <fieldset class="sev-rel"><legend class="sr">Photo ${i + 1} shows</legend>${opts.map(([k, l]) => html`<label class="chk"><input type="radio" name="sevrel${i}" data-f="sevrel" data-p="${i}" value="${k}" ${ph.rel === k ? raw('checked') : ''}>${l}</label>`)}</fieldset></li>`;
}
function sevPlantHtml(P, gi, N) {
  const pics = SEV.photos.filter(ph => ph.group === gi);
  const f = P.fields, sp = P.species || [], shared = SEV.photos.filter(p => p.rel === 'all').length;
  return html`<fieldset class="sev-plant ${P.add ? '' : 'sev-off'}" id="sev-p${gi}" data-section="Plant ${gi + 1}${f.common_name ? ': ' + f.common_name : ''}"><legend>Plant ${gi + 1} of ${N}${f.common_name ? `: ${f.common_name}` : ''}</legend>
    <label class="chk"><input type="checkbox" data-f="sevadd" data-g="${gi}" ${P.add ? raw('checked') : ''}>Add this plant</label>
    ${(P.matches || []).length ? html`<p class="notice" role="note"><strong>This may be a plant you already have:</strong> ${P.matches.map((m, k) => html`${k ? ', ' : ''}<a href="#/plant/${enc(m.code)}" target="_blank" rel="noopener">${m.code} ${m.common_name}</a> (${Math.round(m.confidence * 100)}% sure)`)}. If it is, untick "Add this plant" and add the photos on its page instead.</p>` : ''}
    <ul class="sev-pics">${pics.map(ph => sevPicHtml(ph))}</ul>
    ${shared ? html`<p class="hint">Plus ${shared === 1 ? 'the wide shot' : `the ${shared} wide shots`} marked "Shows all of them".</p>` : ''}
    <fieldset class="sev-names"><legend>What it could be</legend>
      ${P.busy ? html`<p class="muted" role="status">Checking ${pics.length === 1 ? 'its photo' : `its ${pics.length} photos together`}…</p>` : P.iderr ? html`<p class="notice bad">${P.iderr}</p>` : ''}
      ${P.id ? idNamesPanel(P.id, { src: 'sev', id: `sev-names-${gi}`, pick: gi, picked: P.pick, reject: 'sev' }) : sp.length ? html`<p class="hint">First guess from each photo on its own; the photos are being checked together.</p>` : ''}
      <label class="chk"><input type="radio" name="sevsp${gi}" data-f="sevpick" data-g="${gi}" value="-1" ${P.pick === -1 ? raw('checked') : ''}><span>None of these: I will type the names</span></label>
      <p class="row noprint"><button class="btn small ghost" type="button" data-act="sevrecheck" data-g="${gi}" ${P.busy ? raw('disabled') : ''}>Check the photos again</button>
        ${ID.keys && ID.keys.plantnet && !(P.id && P.id.plantnet) ? html`<button class="btn small ghost" type="button" data-act="sevask" data-g="${gi}" ${P.busy ? raw('disabled') : ''}>Ask Pl@ntNet about this plant</button>` : ''}</p></fieldset>
    <div class="field-grid">${SEV_FIELDS.map(([k, label, kind]) => {
      const v = f[k] == null ? '' : f[k], at = raw(`data-f="sevfield" data-g="${gi}" data-k="${k}"`);
      if (kind === 'pets') return html`<label class="f">${label}<select ${at}><option value="">Not set</option>${(META.enums.pet_safety || []).map(o => html`<option ${o === v ? raw('selected') : ''}>${o}</option>`)}</select></label>`;
      if (kind === 'long') return html`<label class="f wide">${label}<textarea rows="2" ${at}>${v}</textarea></label>`;
      return html`<label class="f">${label}${k === 'common_name' ? html`<small>Required.</small>` : ''}<input type="${kind === 'int' ? 'number' : 'text'}" ${kind === 'int' ? raw('min="0" max="100" inputmode="numeric"') : ''} value="${v}" ${at}></label>`; })}</div>
  </fieldset>`;
}
function sevFill(P) {          // the fields from the chosen species; anything you typed yourself stays
  const x = P.pick >= 0 ? (P.species || [])[P.pick] : null, f = P.fields, mine = P.typed;
  const want = x ? { common_name: x.common_name || x.scientific_name, scientific_name: x.scientific_name, family: x.family || '', genus: x.genus || '',
    plant_type: LIB_KIND_SHORT[x.kind] || '', pet_safety: x.pets || '', id_confidence: Math.round((x.probability || 0) * 100) } : { id_confidence: '' };
  for (const [k, v] of Object.entries(want)) if (!mine.has(k)) f[k] = v;
}
// 1.38.0: you say what each photo shows. Photos are in the order they were taken; the first guess is "same plant as the one above"
// when the picture checker sees the same species in both, "a different plant" otherwise. (Grouping by the minutes between photos,
// from 1.28.0, is gone: it put photos of different plants together whenever they were taken in one round.)
function sevFirstGuess() {
  SEV.order = SEV.photos.map((p, i) => i).sort((a, b) => (SEV.photos[a].taken || '').localeCompare(SEV.photos[b].taken || '') || a - b);
  let prev = null;
  for (const i of SEV.order) {
    const p = SEV.photos[i], top = (p.species || [])[0], ptop = prev && (prev.species || [])[0];
    const same = top && ptop && top.probability >= .3 && ptop.probability >= .3 && top.scientific_name === ptop.scientific_name;
    p.rel = !prev ? 'new' : same ? 'same' : 'new';
    p.why = !prev ? '' : same ? `Looks like the same species as the photo above (${top.common_name || top.scientific_name}).` : top && ptop ? 'Looks like a different species from the photo above.' : '';
    prev = p;
  }
  sevGroup();
}
function sevGroup() {          // the chain of answers makes the plants: "same" joins the plant above, "new" starts one
  let g = -1;
  for (const i of SEV.order) {
    const p = SEV.photos[i];
    if (p.rel === 'all' || p.rel === 'out') { p.group = p.rel; continue; }
    if (p.rel === 'new' || g < 0) g++;
    p.group = g;
  }
  sevPlants(g + 1);
}
function sevPlants(n) {        // one entry per plant, with the species of its photos added together; what you typed for a plant stays with its first photo
  const old = SEV.plants; SEV.plants = [];
  for (let gi = 0; gi < n; gi++) {
    const pics = SEV.photos.filter(p => p.group === gi), tot = {};
    pics.forEach(p => (p.species || []).forEach(x => { const t = tot[x.scientific_name] || (tot[x.scientific_name] = { ...x, probability: 0 }); t.probability += (x.probability || 0) / pics.length; }));
    const species = Object.values(tot).sort((a, b) => b.probability - a.probability).slice(0, 3);
    const matches = []; pics.forEach(p => (p.matches || []).forEach(m => { if (!matches.some(x => x.code === m.code)) matches.push(m); }));
    const key = pics.length ? pics[0].file : '';
    const was = old.find(P => P.key === key) || null;
    const P = was || { add: true, pick: species.length ? 0 : -1, fields: {}, typed: new Set() };
    P.key = key; P.species = species; P.matches = matches;
    if (!was) { if (matches.length && matches[0].confidence >= .8) P.add = false; sevFill(P); }
    else if (!P.typed.size) { P.pick = species.length ? 0 : -1; sevFill(P); }
    SEV.plants.push(P);
  }
}
// 1.40.0: each plant's photos are checked together with the one identifier (this computer, Pl@ntNet when set up, "Not this" left out)
async function sevIdentify(gi, force, plantnet) {
  const P = SEV.plants[gi]; if (!P) return;
  const files = SEV.photos.filter(p => p.group === gi).map(p => p.file);
  const key = files.join('|') + '#' + JSON.stringify(P.ex || null) + (plantnet || '');
  if (!files.length || (!force && P.idkey === key)) return;
  P.idkey = key; P.busy = true; P.iderr = null; sevDrawPlant(gi);
  try {
    const r = await api('POST', '/api/plants/several/identify?scope=' + enc(idScope()) + '&mode=' + (SEV.mode || ID.mode || 'mine'), { photos: files, exclude: P.ex ? P.ex.species : [], exclude_genera: P.ex ? P.ex.genera : [], plantnet: plantnet || 'auto' });
    if (P.idkey !== key) return;
    P.id = r; P.species = r.species || []; P.matches = r.matches || [];
    if (!P.typed.has('common_name')) { P.pick = P.species.length ? 0 : -1; sevFill(P); }
  } catch (e) { P.iderr = e.message; }
  P.busy = false; sevDrawPlant(gi);
}
async function sevIdentifyAll() { for (let gi = 0; gi < SEV.plants.length; gi++) await sevIdentify(gi); }
function sevDrawPlant(gi) {
  const old = document.getElementById('sev-p' + gi); if (!old) return;
  const had = document.activeElement && old.contains(document.activeElement) ? document.activeElement.getAttribute('data-k') : null;
  old.outerHTML = rend(sevPlantHtml(SEV.plants[gi], gi, SEV.plants.length));
  if (had) { const el = document.querySelector(`#sev-p${gi} [data-k="${had}"]`); if (el) el.focus(); }
}
function sevDraw(focusSel) {
  const box = document.getElementById('sev'); if (!box) return;
  box.innerHTML = rend(sevHtml()); buildSideNav(); addFoldButtons();
  if (focusSel) { const el = box.querySelector(focusSel); if (el) el.focus(); }
}
// 1.38.0: the preview of each photo is made small on this device (about 800 px) before it is shown, so a phone does not hold ten
// full-size pictures at once; that is what left white patches while scrolling the review screen.
async function sevPreview(file) {
  try {
    const bm = await createImageBitmap(file, { imageOrientation: 'from-image' });
    const k = Math.min(1, 800 / Math.max(bm.width, bm.height)), w = Math.max(1, Math.round(bm.width * k)), h = Math.max(1, Math.round(bm.height * k));
    const cv = document.createElement('canvas'); cv.width = w; cv.height = h; cv.getContext('2d').drawImage(bm, 0, 0, w, h); bm.close();
    const blob = await new Promise(ok => cv.toBlob(ok, 'image/jpeg', .82));
    if (blob) return { url: URL.createObjectURL(blob), w, h };
  } catch (e) { /* the full picture, then */ }
  return { url: URL.createObjectURL(file), w: 400, h: 400 };
}
async function sevGo(form) {
  if (!(await needName())) return;
  const files = [...form.elements.files.files]; if (!files.length) { toast('Choose some photos first.', true); return; }
  SEV.mode = await idPickMode('add'); if (!SEV.mode) return;          // 5b: one of my plants (a cutting, a new pot) or new finds
  SEV.busy = true; SEV.photos = [];
  form.querySelector('button[type=submit]').disabled = true;
  const prog = document.getElementById('sev-prog');
  for (let i = 0; i < files.length; i++) {
    if (prog) prog.textContent = `Checking photo ${i + 1} of ${files.length}…`;
    const fd = new FormData(); fd.append('image', files[i], files[i].name);
    try { const r = await api('POST', '/api/plants/several/photo?scope=' + enc(idScope()) + '&mode=' + SEV.mode, null, fd); SEV.photos.push({ ...r, ...(await sevPreview(files[i])) }); }
    catch (e) { toast(`${files[i].name}: ${e.message}`, true); }
  }
  SEV.busy = false;
  if (!SEV.photos.length) { sevDraw(); return; }
  sevFirstGuess(); SEV.step = 'review'; sevDraw('#sev-p0 legend');
  const lg = document.querySelector('#sev-p0'); if (lg) lg.scrollIntoView({ block: 'start' });
  toast(`${SEV.photos.length} photos checked: ${SEV.plants.length} plant${SEV.plants.length === 1 ? '' : 's'}. Each plant's photos are now checked together.`);
  sevIdentifyAll();
}
async function viewEdit(code) { return viewForm(await api('GET', '/api/plants/' + enc(code))); }
async function submitForm(form) {
  if (!(await needName())) return;
  const fd = new FormData(form), fields = {};
  META.fields.forEach(f => { let v = fd.get(f.name); if (v === null) return; if (TEMP_FIELDS.includes(f.name) && v !== '') v = String(Math.round(tIn(v))); if (LEN_FIELDS.includes(f.name) && v !== '') v = String(lenIn(v)); fields[f.name] = v; });   // 1.29.0: a field not on the form (Location now follows the area) is left out; 1.47.0: temperatures typed in the person's unit go back to whole °F
  const err = document.getElementById('form-err'); err.innerHTML = '';
  const btn = form.querySelector('[type=submit]'); btn.disabled = true;
  try {
    if (form.dataset.form === 'new') {
      const files = [...(form.elements.__photos ? form.elements.__photos.files : [])];        // 1.38.0: photos on the form itself
      if (!String(fields.common_name || '').trim() && files.length) fields.common_name = 'New plant, ' + new Date().toLocaleDateString();   // a stand-in name until the photo is checked
      const p = await api('POST', '/api/plants', { fields });   // without a connection: kept on this device with a NEW- code, sent later
      if (NEWFILL && NEWFILL.__pic) {                // 1.18.0: the picture from Identify
        const fd = new FormData(); fd.append('files', NEWFILL.__pic, 'identify-' + ymd(new Date()) + '.jpg'); fd.append('caption', 'Taken with Identify, ' + new Date().toLocaleDateString());
        try { await api('POST', '/api/plants/' + enc(p.code) + '/photos', undefined, fd); } catch (e) { toast('The plant was added, but not the picture: ' + e.message, true); }
      }
      if (files.length) {
        const fd = new FormData(); files.forEach(f => fd.append('files', f, f.name || 'photo.jpg'));
        try { await api('POST', '/api/plants/' + enc(p.code) + '/photos', undefined, fd); } catch (e) { toast('The plant was added, but not the photos: ' + e.message, true); }
        if (p.offline) { const fd2 = new FormData(); fd2.append('image', files[0], 'picture.jpg'); await offIdQueue('/api/identify?scope=' + enc(idScope()), fd2, { ref: p.code, kind: 'plant', quiet: true }).catch(() => null); }
      }
      NEWFILL = null;
      if (p.offline) { toast('Kept on this device as ' + p.code + '; it is sent when the plant server can be reached.'); go('#/offline'); }
      else { toast('Added ' + p.code); go('#/plant/' + enc(p.code)); }
    } else {
      const r = await api('PUT', '/api/plants/' + enc(form.dataset.code), { base_version: +form.dataset.ver, fields, note: fd.get('__note') || '' });
      toast(r.offline ? (r.changed ? 'Saved' : 'Nothing was changed') : r.changed ? 'Saved as version ' + r.version : 'Nothing was changed'); go('#/plant/' + enc(form.dataset.code));
    }
  } catch (e) {
    btn.disabled = false;
    err.innerHTML = rend(html`<div class="notice bad" role="alert"><strong>Not saved.</strong> ${e.message}</div>`);
    err.scrollIntoView({ block: 'center' });
  }
}
