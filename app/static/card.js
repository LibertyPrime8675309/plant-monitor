/* Large-print care cards (prototype, proto/care-card): /card.html?plant=P-006, ?plant=P-001,P-006 or ?group=3.
   A page of its own so the printout carries nothing but the cards. Plain JavaScript, no inline handlers (content policy). */
(function () {
'use strict';
const ESC = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ESC[c]);
const enc = encodeURIComponent;
const $ = id => document.getElementById(id);
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const KEY = 'plantdb.card2';                // 1.20.0: new defaults (4 x 6 card, dangers shown), so earlier saved choices start over
const DEF = { size: 'card', notes: 'short', photo: true, qr: true, pets: true };

let OPT = Object.assign({}, DEF);
try { Object.assign(OPT, JSON.parse(localStorage.getItem(KEY) || '{}') || {}); } catch (e) { /* storage blocked: defaults */ }
const saveOpt = () => { try { localStorage.setItem(KEY, JSON.stringify(OPT)); } catch (e) { /* this visit only */ } };

async function get(url) {
  let r;
  try { r = await fetch(url); } catch (e) { throw new Error('Cannot reach the plant server. Check that the container is running.'); }
  let d = null; try { d = await r.json(); } catch (e) { /* not json */ }
  if (!r.ok) throw new Error((d && d.error) || ('Request failed (' + r.status + ')'));
  return d;
}

// the first sentence of a note, or all of it
function note(s) {
  const t = String(s || '').replace(/\s+/g, ' ').trim();
  if (!t || OPT.notes === 'full') return t;
  const m = t.match(/^.+?[.!?](?=\s+[A-Z0-9"(]|$)/);
  return m ? m[0] : t;
}
const range = (lo, hi, unit) => lo != null && hi != null ? `${lo} to ${hi}${unit}` : lo != null ? `at least ${lo}${unit}` : hi != null ? `up to ${hi}${unit}` : '';
function months(a, b) {
  if (!a || !b) return '';
  if ((a === 1 && b === 12) || b === a - 1) return 'all year';
  return `${MONTHS[a - 1]} to ${MONTHS[b - 1]}`;
}

// one box on the card: a heading word, the main fact in large bold type, and any lines under it
// the heading word, the main fact in large bold type, short facts, then the notes
function box(cls, title, main, facts, notes) {
  const f = (facts || []).filter(Boolean), n = (notes || []).filter(Boolean);
  if (!main && !f.length && !n.length) return '';
  return `<section class="pc-box ${cls}"><h3>${esc(title)}</h3>${main ? `<p class="pc-main-fact">${esc(main)}</p>` : ''}${f.map(x => `<p>${esc(x)}</p>`).join('')}${n.map(x => `<p class="pc-note">${esc(x)}</p>`).join('')}</section>`;
}

function card(p, water, base) {
  const photo = (p.photos || []).find(x => x.is_primary) || (p.photos || [])[0];
  const w = water[p.code];
  const waterMain = p.water_every_days ? `Check every ${p.water_every_days} days` : w ? `Check about every ${w.base} days` : '';
  const waterWhy = !p.water_every_days && w && w.why ? `In mild weather. It ${w.why}.` : '';
  const moist = range(p.soil_moisture_low, p.soil_moisture_high, '% soil moisture');
  const light = [p.light_summary, p.light_hours ? p.light_hours.replace(/\bh\b/, 'hours') + ' a day' : ''].filter(Boolean).join(', ');
  const ideal = range(p.temp_ideal_low, p.temp_ideal_high, '°F');
  const feedWhen = [months(p.fert_from_month, p.fert_to_month), p.fert_every_days ? `every ${p.fert_every_days} days` : ''].filter(Boolean).join(', ');
  const feedMain = p.fert_strength || (feedWhen ? 'Feed ' + feedWhen : '');
  const winter = p.winter_plan ? `Winter plan: ${p.winter_plan}` : '';
  const left = [
    box('pc-water', 'Water', waterMain, [waterWhy], [note(p.water_notes), moist && OPT.notes === 'full' ? 'Aim for ' + moist + ' (sensor).' : '']),
    box('pc-light', 'Light', light, [], [note(p.light_notes)])].join(''), right = [
    box('pc-temp', 'Temperature', ideal ? 'Best at ' + ideal : '', [
      p.temp_damage_below != null ? `Harmed below ${p.temp_damage_below}°F.` : '',
      p.temp_lethal_below != null ? `Killed below ${p.temp_lethal_below}°F.` : '',
      p.temp_damage_above != null ? `Harmed above ${p.temp_damage_above}°F.` : ''], [note(p.temp_notes)]),
    box('pc-hum', 'Humidity', range(p.humidity_low, p.humidity_high, '%'), [], [note(p.humidity_notes)]),
    box('pc-feed', 'Feeding', feedMain, [p.fert_strength && feedWhen ? 'Feed ' + feedWhen + '.' : ''],
        [p.fertilizer ? note(p.fertilizer) : '', p.npk_ratio && OPT.notes === 'full' ? `N-P-K about ${p.npk_ratio}.` : '', OPT.notes === 'full' || !feedWhen ? note(p.nutrients) : ''])].join('');
  const petMain = !p.pet_safety ? '' : /pets/i.test(p.pet_safety) ? p.pet_safety : 'Pets: ' + p.pet_safety[0].toLowerCase() + p.pet_safety.slice(1);
  const careful = OPT.pets ? box('pc-care', 'Careful', petMain, [p.danger_animals ? 'Pets: ' + note(p.danger_animals) : '', p.danger_humans ? 'People: ' + note(p.danger_humans) : '']) : '';
  // two fixed columns (water, light and the dangers; temperature, humidity and feeding) so a card breaks across pages
  // predictably. 1.20.0: the dangers go under light, where there is usually room, so most cards stay on one page.
  const boxes = left || right || careful ? `<div class="pc-col">${left}${careful}</div><div class="pc-col">${right}</div>` : '';
  const where = p.location && p.site && p.location.toLowerCase().startsWith(p.site.toLowerCase()) ? p.location : [p.site, p.location].filter(Boolean).join(', ');
  const today = new Date().toLocaleDateString([], { dateStyle: 'long' });
  return `<article class="pc-card" aria-labelledby="pc-h-${esc(p.code)}">
    <header class="pc-head">
      <div class="pc-names">
        <h2 id="pc-h-${esc(p.code)}">${esc(p.common_name)}</h2>
        ${p.scientific_name ? `<p class="pc-sci latin">${esc(p.scientific_name)}</p>` : ''}
        <p class="pc-where"><strong>${esc(p.code)}</strong>${where ? ' · ' + esc(where) : ''}</p>
        ${winter ? `<p class="pc-where">${esc(winter)}</p>` : ''}
        <p class="pc-printed">Printed ${esc(today)} from Plant record, page version ${esc(p.version)}.</p>
      </div>
      ${OPT.qr ? `<figure class="pc-scan"><img class="pc-qr" src="/api/plants/${enc(p.code)}/qr.svg?base=${enc(base)}" alt="Code to scan: opens the page for ${esc(p.code)}" width="96" height="96"><figcaption>Scan for the full page</figcaption></figure>` : ''}
      ${OPT.photo && photo ? `<img class="pc-photo" src="/photos/${enc(photo.file)}" alt="${esc(photo.caption || 'Photo of ' + p.common_name)}">` : ''}
    </header>
    <div class="pc-boxes">${boxes || '<p>This plant has no care details yet.</p>'}</div>
  </article>`;
}

// 1.20.0: a 4 x 6 inch card (landscape): the main facts only, one row each, in large type
function row(cls, title, main, more) {
  const m = (more || []).filter(Boolean);
  if (!main && !m.length) return '';
  // the main fact in bold, and the rest on the same line, so most needs take one line
  return `<div class="pc-row ${cls}"><h3>${esc(title)}</h3><p>${main ? `<b class="pc-main-fact">${esc(main)}</b>` : ''}${m.map((x, i) => `${main || i ? '. ' : ''}${esc(x)}`).join('')}</p></div>`;
}
function card46(p, water, base) {
  const photo = (p.photos || []).find(x => x.is_primary) || (p.photos || [])[0];
  const w = water[p.code];
  const waterMain = p.water_every_days ? `Check every ${p.water_every_days} days` : w ? `Check about every ${w.base} days` : '';
  // shorter wording than the full page, so most plants fit on one card: short month names, and the hours only when brief
  const hrs = p.light_hours && p.light_hours.length <= 12 ? p.light_hours.replace(/\bh\b/, 'hours') + ' a day' : '';
  const light = [String(p.light_summary || '').replace(/\s*\([^)]*\)/g, '').split(/;|\.\s/)[0].replace(/\.$/, '').trim(), hrs].filter(Boolean).join(', ');   // asides in brackets are on the full page
  const ideal = range(p.temp_ideal_low, p.temp_ideal_high, '°F');
  const mo = (a, b) => !a || !b ? '' : (a === 1 && b === 12) || b === a - 1 ? 'all year' : `${MONTHS[a - 1].slice(0, 3)} to ${MONTHS[b - 1].slice(0, 3)}`;
  const feedWhen = [mo(p.fert_from_month, p.fert_to_month), p.fert_every_days ? `every ${p.fert_every_days} days` : ''].filter(Boolean).join(', ');
  const first = p.danger_humans ? String(p.danger_humans).replace(/\s+/g, ' ').trim().match(/^.+?[.!?](?=\s|$)|^.+$/)[0] : '';
  // a long warning would push the card onto a second one: point to the plant's page instead (the scan code opens it)
  const people = !first ? '' : first.length <= 75 ? 'People: ' + first : 'People: see the warning on its page';
  const rows = [
    row('pc-water', 'Water', waterMain),
    row('pc-light', 'Light', light),
    row('pc-temp', 'Temp', ideal ? 'Best at ' + ideal : '', [p.temp_damage_below != null ? `Harmed below ${p.temp_damage_below}°F` : '']),
    row('pc-hum', 'Humidity', range(p.humidity_low, p.humidity_high, '%')),
    row('pc-feed', 'Feeding', p.fert_strength || (feedWhen ? 'Feed ' + feedWhen : ''), [p.fert_strength && feedWhen ? feedWhen[0].toUpperCase() + feedWhen.slice(1) : '']),
    OPT.pets ? row('pc-care', 'Careful', !p.pet_safety ? (p.danger_animals ? 'Pets: see the warning on its page' : '') : /pets/i.test(p.pet_safety) ? p.pet_safety : 'Pets: ' + p.pet_safety[0].toLowerCase() + p.pet_safety.slice(1), [people]) : ''].join('');
  const where = p.location || p.site || '';             // the card sits with the plant, so the spot alone is enough
  return `<article class="pc-card pc-46" aria-labelledby="pc-h-${esc(p.code)}">
    <header class="pc-head">
      <div class="pc-names">
        <h2 id="pc-h-${esc(p.code)}">${esc(p.common_name)}</h2>
        <p class="pc-where"><strong>${esc(p.code)}</strong>${where ? ' · ' + esc(where) : ''}</p>
      </div>
      ${OPT.qr ? `<img class="pc-qr" src="/api/plants/${enc(p.code)}/qr.svg?base=${enc(base)}" alt="Code to scan: opens the page for ${esc(p.code)}" width="80" height="80">` : ''}
      ${OPT.photo && photo ? `<img class="pc-photo" src="/photos/${enc(photo.file)}" alt="${esc(photo.caption || 'Photo of ' + p.common_name)}">` : ''}
    </header>
    <div class="pc-rows">${rows || '<p>This plant has no care details yet.</p>'}</div>
  </article>`;
}

// the paper size goes in its own style element: @page cannot depend on a class
function pageSize() {
  let st = $('pc-page');
  if (!st) { st = document.createElement('style'); st.id = 'pc-page'; document.head.appendChild(st); }
  st.textContent = OPT.size === 'card' ? '@page{size:6in 4in;margin:.15in .18in}' : '@page{size:letter;margin:.45in}';
}

let DATA = null;
function paint() {
  const f = $('pc-opts');
  f.querySelectorAll('input[type=radio]').forEach(i => { i.checked = OPT[i.name] === i.value; });
  f.querySelectorAll('input[type=checkbox]').forEach(i => { i.checked = !!OPT[i.name]; });
  const c46 = OPT.size === 'card';
  $('pc-notes').hidden = c46;
  document.body.classList.toggle('pc-c46', c46);
  pageSize();
  $('pc-cards').innerHTML = DATA.plants.map(p => (c46 ? card46 : card)(p, DATA.water, DATA.base)).join('');
  const n = DATA.plants.length;
  $('pc-count').textContent = c46 ? `${n} ${n === 1 ? 'card' : 'cards'}, one plant on each. In the print window, choose 4 x 6 inch paper.`
    : `${n} ${n === 1 ? 'page' : 'pages'}, one plant on each. Long notes can run onto a second page.`;
}

async function load() {
  const q = new URLSearchParams(location.search);
  let codes = (q.get('plant') || '').split(',').map(s => s.trim()).filter(Boolean), group = null;
  const all = q.get('all') === '1';                     // 1.20.0: every active plant, from the Labels page
  if (all) codes = (await get('/api/plants')).map(p => p.code);
  if (q.get('group')) {
    group = await get('/api/groups/' + enc(q.get('group')));
    codes = group.members.map(m => m.code);
  }
  if (!codes.length && !group) throw new Error('No plant chosen. Open a care card from a plant page or a group page.');
  const [plants, water, st] = await Promise.all([
    Promise.all(codes.map(c => get('/api/plants/' + enc(c)))),
    get('/api/water').catch(() => ({ plants: [] })),
    get('/api/settings').catch(() => ({})),
  ]);
  DATA = { plants, water: Object.fromEntries((water.plants || []).map(w => [w.code, w])), base: st.base_url || location.origin };
  const back = $('pc-back');
  if (all) {
    back.href = '/#/labels'; back.textContent = 'Back to Labels';
    $('pc-title').textContent = 'Large-print care cards for all plants';
    $('pc-intro').textContent = `One card for each of your ${plants.length} plants (archived plants are left out), to print and keep beside them.`;
  } else if (group) {
    back.href = '/#/group/' + enc(group.id); back.textContent = 'Back to the group ' + group.name;
    $('pc-title').textContent = 'Large-print care cards: ' + group.name;
    $('pc-intro').textContent = plants.length ? `One card for each of the ${plants.length} plants in this group, to print and keep beside them.` : 'This group has no plants yet, so there is nothing to print.';
  } else if (plants.length === 1) {
    back.href = '/#/plant/' + enc(plants[0].code); back.textContent = 'Back to ' + plants[0].common_name;
    $('pc-title').textContent = 'Large-print care card: ' + plants[0].common_name;
    $('pc-intro').textContent = 'Its water, light and temperature needs in big type, to print and keep beside the plant.';
  } else {
    $('pc-title').textContent = `Large-print care cards (${plants.length} plants)`;
    $('pc-intro').textContent = 'One card for each plant, to print and keep beside them.';
  }
  document.title = $('pc-title').textContent + ' | Plant record';
  $('pc-opts').hidden = !plants.length;
  paint();
}

$('pc-opts').addEventListener('change', e => {
  const i = e.target; if (!i.name) return;
  OPT[i.name] = i.type === 'checkbox' ? i.checked : i.value;
  saveOpt(); paint();
});
$('pc-print').addEventListener('click', () => window.print());
load().catch(e => {
  $('pc-intro').textContent = '';
  $('pc-cards').innerHTML = `<div class="notice bad" role="alert"><strong>Could not make the card</strong><p>${esc(e.message)}</p><a class="btn ghost" href="/#/">Back to all plants</a></div>`;
});
})();
