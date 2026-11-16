/* Plant record: short forms in plain words (1.58.0, the dyslexia audit). PAR, PPFD, DLI, ASPCA and the like are strings of letters a
   reader has to decode. The first time each one appears on a page, its plain words follow it in brackets, and the page Words used in the
   app explains them all. Display → Reading → "Short forms" turns the brackets off. Plain JavaScript, no inline handlers. */
'use strict';

const WORDS = [
  // [short form, in brackets on the page, the longer explanation on the Words page]
  ['PAR', 'light plants can use', 'Photosynthetically active radiation: the part of light, from blue to red, that plants use to grow. Grow lights give it as PPFD at a distance.'],
  ['PPFD', 'light reaching the leaves', 'Photosynthetic photon flux density: how much plant-usable light lands on the leaves each second, in µmol/m²/s. Higher is brighter.'],
  ['DLI', 'daily light', 'Daily light integral: all the plant-usable light a plant gets in a day, in mol/m²/day. Each plant has a range it needs.'],
  ['VPD', 'how dry the air feels to a leaf', 'Vapour pressure deficit: how strongly the air pulls water out of leaves. Low is damp and still; high is dry and thirsty.'],
  ['CRI', 'how true colours look', 'Colour rendering index: how natural colours look under a light, out of 100. Above 90 looks like daylight.'],
  ['ASPCA', 'a pet-safety list', 'The American Society for the Prevention of Cruelty to Animals. Its lists say which plants are poisonous to dogs, cats and horses.'],
  ['USDA', 'US farming department', 'The United States Department of Agriculture. Its hardiness zones say how cold the winters get where you live.'],
  ['AHS', 'heat zone list', 'The American Horticultural Society. Its heat zones count the days a year above 86°F where you live.'],
  ['IUCN', 'world list of threatened species', 'The International Union for Conservation of Nature. Its Red List says how threatened a species is in the wild.'],
  ['CITES', 'trade rules for rare species', 'The Convention on International Trade in Endangered Species: the treaty that controls trade in rare plants and animals.'],
  ['LECA', 'clay pebbles', 'Lightweight expanded clay aggregate: baked clay balls used instead of soil in semi-hydro pots.'],
  ['NPK', 'nitrogen, phosphorus, potassium', 'The three main plant foods, always in that order on a fertilizer label, as N-P-K, such as 10-10-10.'],
  ['N-P-K', 'nitrogen, phosphorus, potassium', null],
  ['EC', 'how much fertilizer is in the water', 'Electrical conductivity: a meter reading of how much dissolved fertilizer is in water. Higher means stronger.'],
  ['CSV', 'a spreadsheet file', 'Comma-separated values: a plain file that any spreadsheet app opens.'],
  ['UTC', 'world time', 'Coordinated Universal Time: the clock that every time zone counts from.'],
  ['NNE', 'north-north-east', 'Wind directions are short forms: N is north, NNE north-north-east, NE north-east, and so on round the compass.'],
  ['SSW', 'south-south-west', null], ['WNW', 'west-north-west', null], ['ESE', 'east-south-east', null], ['ENE', 'east-north-east', null],
  ['NNW', 'north-north-west', null], ['SSE', 'south-south-east', null], ['WSW', 'west-south-west', null],
];
const WORD_RE = new RegExp('(^|[^A-Za-z0-9-])(' + WORDS.map(w => w[0].replace(/-/g, '\\-')).sort((a, b) => b.length - a.length).join('|') + ')(?![A-Za-z0-9-])');
const WORD_MAP = Object.fromEntries(WORDS.map(w => [w[0], w[1]]));
const WORD_SKIP = 'button,a,h1,h2,h3,h4,legend,label,select,option,input,textarea,th,code,pre,.tag,.code,svg,script,style,.abx,[data-noabbr],.sr,summary,.lt-top';      // .lt-top: a bar held at the top stays short

// The first time each short form appears on the page, its plain words follow it. Runs after each page is drawn, and again with the late parts.
function abbrPass() {
  const app = document.getElementById('app');
  if (!app || document.documentElement.dataset.abbr === '0') return;
  const seen = new Set([...app.querySelectorAll('.abx')].map(x => x.dataset.for));
  const walker = document.createTreeWalker(app, NodeFilter.SHOW_TEXT, { acceptNode: n => n.parentElement && !n.parentElement.closest(WORD_SKIP) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT });
  const todo = [];
  while (walker.nextNode()) todo.push(walker.currentNode);
  for (let node of todo) {
    for (let guard = 0; guard < 6 && node; guard++) {
      const t = node.nodeValue, m = WORD_RE.exec(t);
      if (!m) break;
      const word = m[2], at = m.index + m[1].length, end = at + word.length;
      const rest = t.slice(end);
      const before = t.slice(0, at), around = (node.parentElement && node.parentElement.textContent || '').toLowerCase();
      // said already on this page; already explained in brackets; itself in brackets after its long name ("Clay pebbles (LECA)"); or its words are there already
      if (seen.has(WORD_MAP[word]) || /^\s*\(/.test(rest) || /\(\s*$/.test(before) || around.includes(WORD_MAP[word])) {
        if (/^\s*\(/.test(rest)) seen.add(WORD_MAP[word]);
        const after = node.splitText(end); node = after; continue;
      }
      seen.add(WORD_MAP[word]);
      const after = node.splitText(end);
      const x = document.createElement('span'); x.className = 'abx'; x.dataset.for = WORD_MAP[word]; x.textContent = ` (${WORD_MAP[word]})`;
      after.parentNode.insertBefore(x, after);
      node = after;
    }
  }
}
document.addEventListener('prefs', () => {
  const app = document.getElementById('app'); if (!app) return;
  if (document.documentElement.dataset.abbr === '0') app.querySelectorAll('.abx').forEach(x => x.remove()); else abbrPass();
});

function viewWords() {
  return { title: 'Words used in the app', html: html`<h1>Words used in the app</h1>
    <p class="lede">The short forms the app uses, in plain words. The first time one appears on a page, its plain words follow it in brackets. To turn that off, open Display, then Reading, then Short forms.</p>
    <dl class="words-list">${WORDS.filter(w => w[2]).map(w => html`<div class="words-row" id="word-${w[0]}"><dt>${w[0]}</dt><dd><strong>${w[1][0].toUpperCase() + w[1].slice(1)}.</strong> ${w[2]}</dd></div>`)}</dl>` };
}

addFeature({
  name: 'words',
  pages: { words: { view: viewWords, nav: 'settings', label: 'Words used in the app', href: '#/words' } },
});

// ---------- the reading guide (1.58.0, the dyslexia audit) ----------
// A soft band across the page that follows the line being read: the mouse pointer, a finger on the screen, or the keyboard's place.
// Display → Reading → Reading guide. It never takes a click or a tap (pointer-events: none).
const RGUIDE = { el: null, y: -1, raf: 0 };
function rguideOn() { return document.documentElement.dataset.rguide === '1'; }
function rguideMove(y) {
  if (!rguideOn()) { if (RGUIDE.el) RGUIDE.el.hidden = true; return; }
  if (!RGUIDE.el) { RGUIDE.el = document.createElement('div'); RGUIDE.el.className = 'rguide'; RGUIDE.el.setAttribute('aria-hidden', 'true'); document.body.appendChild(RGUIDE.el); }
  RGUIDE.y = y;
  if (RGUIDE.raf) return;
  RGUIDE.raf = requestAnimationFrame(() => { RGUIDE.raf = 0; RGUIDE.el.hidden = false; RGUIDE.el.style.transform = `translateY(${Math.round(RGUIDE.y)}px)`; });
}
document.addEventListener('pointermove', e => { if (rguideOn()) rguideMove(e.clientY); }, { passive: true });
document.addEventListener('touchstart', e => { if (rguideOn() && e.touches[0]) rguideMove(e.touches[0].clientY); }, { passive: true });
document.addEventListener('touchmove', e => { if (rguideOn() && e.touches[0]) rguideMove(e.touches[0].clientY); }, { passive: true });
document.addEventListener('focusin', e => { if (rguideOn() && e.target && e.target.getBoundingClientRect) { const r = e.target.getBoundingClientRect(); rguideMove(r.top + r.height / 2); } });
document.addEventListener('prefs', () => { if (!rguideOn() && RGUIDE.el) RGUIDE.el.hidden = true; });
