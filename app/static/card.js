/* Large-print care cards (prototype, proto/care-card): /card.html?plant=P-006, ?plant=P-001,P-006 or ?group=3.
   A page of its own so the printout carries nothing but the cards. Plain JavaScript, no inline handlers (content policy). */
(function () {
'use strict';
const ESC = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ESC[c]);
const enc = encodeURIComponent;
const $ = id => document.getElementById(id);
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const KEY = 'plantdb.card';
const DEF = { notes: 'short', photo: true, qr: true, pets: false };

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
  const careful = OPT.pets ? box('pc-care', 'Careful', '', [p.danger_animals ? 'Pets: ' + note(p.danger_animals) : '', p.danger_humans ? 'People: ' + note(p.danger_humans) : '']) : '';
  // two fixed columns (water and light; temperature, humidity and feeding) so a card breaks across pages predictably
  const boxes = left || right ? `<div class="pc-col">${left}</div><div class="pc-col">${right}</div>${careful}` : careful;
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

let DATA = null;
function paint() {
  const f = $('pc-opts');
  f.querySelectorAll('input[type=radio]').forEach(i => { i.checked = OPT[i.name] === i.value; });
  f.querySelectorAll('input[type=checkbox]').forEach(i => { i.checked = !!OPT[i.name]; });
  $('pc-cards').innerHTML = DATA.plants.map(p => card(p, DATA.water, DATA.base)).join('');
  const n = DATA.plants.length;
  $('pc-count').textContent = `${n} ${n === 1 ? 'card' : 'cards'}. Each starts on a new page; long notes can run onto a second page.`;
}

async function load() {
  const q = new URLSearchParams(location.search);
  let codes = (q.get('plant') || '').split(',').map(s => s.trim()).filter(Boolean), group = null;
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
  if (group) {
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
