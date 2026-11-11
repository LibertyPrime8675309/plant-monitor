/* Plant record front end: Display settings, swiping, read aloud, the photo check, the Photos, Backups, Labels and Audit log pages, Debug. One of the files app.js was split into in 1.32.0; they load in order (index.html) and share one scope,
   so a function here may call any other. Plain JavaScript, no inline handlers (the server's content policy forbids them). */
'use strict';

// ---------- display settings and current-conditions dialogs ----------
function displayDialog() {
  const P = window.PlantPrefs.get();
  const group = (key, title, opts, hint) => html`<fieldset class="opt-group"><legend>${title}</legend><div class="opts">${opts.map(([v, l]) => html`<label><input type="radio" name="pref-${key}" data-pref="${key}" value="${v}" ${P[key] === v ? raw('checked') : ''}><span>${l}</span></label>`)}</div>${hint ? html`<p class="hint">${hint}</p>` : ''}</fieldset>`;
  const G = {};
  G.size = group('size', 'Text and button size', [['100', 'Standard'], ['115', 'Comfortable'], ['135', 'Large'], ['160', 'Larger'], ['190', 'Largest']], 'Everything scales together, including buttons, bars and charts.');
  G.space = group('space', 'Spacing', [['normal', 'Normal'], ['roomy', 'Roomy']], 'Roomy adds space between lines, letters and words.');
  G.contrast = group('contrast', 'Contrast', [['normal', 'Normal'], ['high', 'High']], 'High contrast uses black and white, stronger lines and heavier outlines.');
  G.theme = group('theme', 'Colours', [['auto', 'Match my device'], ['light', 'Light'], ['dark', 'Dark']]);
  G.navside = group('navside', 'Navigation menu side', [['left', 'Left'], ['right', 'Right']], 'The Navigation menu lists the sections of the page you are on. Display is at its bottom.');
  G.navopen = group('navopen', 'Navigation menu', [['1', 'Open'], ['0', 'Folded away (the Navigation button opens it)']], 'On narrow windows and phones it starts folded and covers the page while open.');
  G.width = group('width', 'Page width', [['normal', 'Normal'], ['wide', 'Use the full width of the window']], 'Full width gives charts and tables more room on a wide screen.');
  G.lines = group('lines', 'Line length', [['full', 'Use the full width'], ['short', 'Shorter lines (about 70 letters)']], 'Full width fits more on the screen. Shorter lines can be easier to follow from one line to the next.');
  G.notes = group('notes', 'Notes under buttons and boxes', [['show', 'Always show them'], ['ask', 'Show them when I ask']], 'The small notes that say what a button does or what to type. "When I ask" folds each into a Note button: press it, hold a finger on the button or box it belongs to, or point at it with the mouse. Screen readers still read every note.');
  G.layout = group('layout', 'Plant pages', [['split', 'Photos and details side by side'], ['single', 'One column']], 'Side by side lets each half scroll on its own: scroll with the pointer over the half you want to move. One column stacks the photos above the details.');
  const speak = canSpeak() ? html`${group('readbtns', 'Read aloud buttons', [['1', 'Show them on each section'], ['0', 'Hide them']], 'Your browser reads the section aloud with its own voices. The R key reads the whole page either way.')}
    ${group('rate', 'Reading speed', [['0.8', 'Slower'], ['1', 'Normal'], ['1.25', 'Faster'], ['1.5', 'Fastest']])}
    <fieldset class="opt-group"><legend>Voice</legend><label class="f">Voice<select data-pref="voice" id="pref-voice">${voiceOptions(P.voice)}</select></label>
      <p class="row"><button class="btn ghost small" type="button" data-act="voicetest">Try this voice</button></p>
      <p class="hint">"Natural" or "Online" voices in Microsoft Edge sound the most human.</p></fieldset>` : html`<p class="muted">This browser cannot read aloud.</p>`;
  G.photofit = group('photofit', 'Photos on the Plants page', [['auto', 'Show wide photos whole, fill the card with tall ones'], ['fill', 'Fill the card (wide photos lose their sides)'], ['whole', 'Always show the whole photo']], 'A wide photo cut down to fit a tall card loses its sides. Shown whole, it has a plain band above and below.');
  G.swipe = group('swipe', 'Swipe between plants', [['1', 'On'], ['0', 'Off']], 'On a phone or tablet, swipe left on a plant page for the next plant, or right for the previous one. Start away from the edges of the screen, which your phone uses for Back.');
  G.keys = group('keys', 'Keyboard shortcuts', [['1', 'On'], ['0', 'Off']], 'R reads the page aloud, [ and ] go to the previous and next plant, ? lists them all.');
  G.vsearch = typeof vsCan === 'function' && vsCan() ? html`${group('vsearch', 'Search by voice', [['1', 'Show the buttons, and say what was heard aloud'], ['quiet', 'Show the buttons, but do not speak'], ['0', 'Hide the buttons (the V key is off too)']],
    'A Search by voice button sits beside each search box. What you say is turned into words on this computer, and is not saved. If you use a screen reader, choose "do not speak": it reads the line under the button out already.')}<p class="hint" id="vs-dv-st" role="status"></p>` : html`<p class="muted">This browser cannot record from a microphone here. Open Plant record through its https Tailscale address, or in a newer browser.</p>`;
  // 1.47.0 (PLAN.md step 4a): units. A region sets all three; each can then be changed by hand. These follow you to every device.
  const U = unitsGet(), usel = (k, title, hint) => html`<label class="f">${title}<select data-act="unitset" data-u="${k}" id="pref-u-${k}">${Object.entries(UNIT_WORDS[k]).map(([v, l]) => html`<option value="${v}" ${U[k] === v ? raw('selected') : ''}>${l}</option>`)}</select>${hint ? html`<small>${hint}</small>` : ''}</label>`;
  G.units = html`<fieldset class="opt-group"><legend>Units</legend>${usel('region', 'Where you are', U.own ? 'Sets the three below at once.' : `Following the home you are looking at (${placeName()}) until you choose. Sets the three below at once.`)}${usel('temp', 'Temperature')}${usel('len', 'Lengths (pots, distances)')}${usel('rain', 'Rain and water')}
    <p class="hint">The record keeps everything in °F and inches underneath; this changes what you see and type, on every page and in push messages. Unlike the other parts of Display, units apply on every device you sign in on.</p></fieldset>`;
  // 5b (PLAN.md step 5): what Identify asks on each page, or the answer to use without asking. Follows you to every device.
  const IM = idModePref(), imsel = (page, title) => html`<label class="f">${title}<select data-act="idmodeset" data-page="${page}" id="pref-im-${page}">
    ${[['ask', 'Ask each time'], ['mine', 'One of my plants'], ['new', 'A new find']].map(([v, l]) => html`<option value="${v}" ${(IM[page] === 'mine' || IM[page] === 'new' ? IM[page] : 'ask') === v ? raw('selected') : ''}>${l}</option>`)}</select></label>`;
  G.idmode = html`<fieldset class="opt-group"><legend>What you are looking at</legend>${imsel('identify', ID_MODE_PAGES.identify)}${imsel('add', ID_MODE_PAGES.add)}${imsel('plant', ID_MODE_PAGES.plant)}
    <p class="hint">"One of my plants" puts the names you already have first (a cutting, a new pot of the same plant). "A new find" ignores what you have and puts the plants recorded in this home's country first. "Ask each time" offers your last answer first. These follow you to every device you sign in on.</p></fieldset>`;
  const SH = window.PlantSync ? window.PlantSync.shared() : {};
  const share = part => html`<fieldset class="opt-group dv-share"><legend>Where these apply</legend><label class="chk"><input type="checkbox" data-dvshare="${part}" ${SH[part] ? raw('checked') : ''}>Use these on every device I sign in on</label>
    <p class="hint">Off (the usual): only this device. On: any phone, tablet or computer where you sign in and tick this too gets them.</p></fieldset>`;
  const SECS = [['Text and colours', html`${G.size}${G.space}${G.contrast}${G.theme}${share('text')}`], ['Page layout', html`${G.width}${G.lines}${G.notes}${G.layout}${G.navside}${G.navopen}${share('layout')}`],
    ['Units', G.units], ['Identify', G.idmode], ['Reading aloud', html`${speak}${share('read')}`], ['Photos and touch', html`${G.photofit}${G.swipe}${share('photos')}`], ['Keyboard and voice', html`${G.keys}${G.vsearch}${share('keys')}`]];
  const keep = DVSCROLL; DVSCROLL = 0;
  modal(html`<form method="dialog" class="dv-form">
    <div class="dv-head"><div class="dv-title"><h2 id="dv-title">Display settings</h2>
        <p class="muted dv-intro">Changes apply right away. Each part is kept on this device unless you tick "Use these on every device I sign in on" in it.</p>
        <p class="dv-ver"><strong>App version:</strong> ${META && META.version ? META.version : 'unknown'}</p></div>
      <div class="row dv-acts"><button class="btn" value="ok" autofocus>Done</button><button class="btn ghost" type="button" data-act="prefreset">Reset to defaults</button></div></div>
    <div class="dv-main"><nav class="dv-tabs" aria-label="Parts of the display settings">${SECS.map(([n], i) => html`<button type="button" class="dv-tab" data-act="dvjump" data-to="dv-s${i}" ${i ? '' : raw('aria-current="true"')}>${n}</button>`)}</nav>
      <div class="dv-body" id="dv-body" tabindex="-1">${SECS.map(([n, body], i) => html`<section id="dv-s${i}" aria-labelledby="dv-h${i}"><h3 id="dv-h${i}">${n}</h3><div class="dv-cols">${body}</div></section>`)}</div></div></form>`, 'dv');
  dlg.setAttribute('aria-labelledby', 'dv-title');
  const body = document.getElementById('dv-body');
  if (keep) body.scrollTop = keep;
  const mark = () => {                         // the part being read is marked in the menu, in words for screen readers too
    const top = body.getBoundingClientRect().top + 8;
    let cur = 'dv-s0';
    body.querySelectorAll('section').forEach(sc => { if (sc.getBoundingClientRect().top <= top + 40) cur = sc.id; });
    if (body.scrollTop + body.clientHeight >= body.scrollHeight - 4) cur = body.querySelector('section:last-child').id;
    dlg.querySelectorAll('.dv-tab').forEach(b => { if (b.dataset.to === cur) b.setAttribute('aria-current', 'true'); else b.removeAttribute('aria-current'); });
  };
  body.addEventListener('scroll', () => { DVSCROLL = body.scrollTop; mark(); }, { passive: true });
  mark();
}
let DVSCROLL = 0;              // Reset to defaults redraws the window; it stays where it was
// ---------- swipe between plants on touch screens (added in 1.14.1) ----------
// A quick sideways swipe on a plant page opens the next plant (swipe left) or the previous one (swipe right), the same as
// the Previous / Next Plant buttons. It stays out of the way of scrolling, zooming, tables and charts that scroll sideways,
// form fields, open windows and menus, and the screen edges (Back on Android, iPhone and iPad).
const SWIPE = { x: 0, y: 0, t: 0, on: false, dir: 0 };
const SWIPE_EDGE = 28, SWIPE_MIN = 70;
function swipeBlocked(el) {
  for (let n = el; n && n !== document.body && n.nodeType === 1; n = n.parentElement) {
    if (n.matches('input,select,textarea,button.main-photo,[contenteditable],dialog,#sidenav,#corner,#console,.pnav,.chart-card,canvas,.thumbs')) return true;
    const cs = getComputedStyle(n);
    if (/(auto|scroll)/.test(cs.overflowX) && n.scrollWidth > n.clientWidth + 2) return true;     // something here scrolls sideways
  }
  return false;
}
function swipeHint() {
  let h = document.getElementById('swipe-hint');
  if (!h) { h = document.createElement('div'); h.id = 'swipe-hint'; h.className = 'swipe-hint'; h.setAttribute('aria-hidden', 'true'); document.body.appendChild(h); }
  return h;
}
function swipeHide() { const h = document.getElementById('swipe-hint'); if (h) { h.classList.remove('show', 'ready'); h.removeAttribute('data-side'); } SWIPE.on = false; SWIPE.dir = 0; }
document.addEventListener('touchstart', e => {
  SWIPE.on = false;
  if (e.touches.length !== 1 || window.PlantPrefs.get().swipe === '0' || !/^#\/plant\/[^/]+$/.test(location.hash) || !document.getElementById('pnav')) return;
  if (document.querySelector('dialog[open]') || (document.documentElement.dataset.narrow === '1' && navOpen())) return;
  const t = e.touches[0];
  if (t.clientX < SWIPE_EDGE || t.clientX > window.innerWidth - SWIPE_EDGE || swipeBlocked(e.target)) return;
  Object.assign(SWIPE, { x: t.clientX, y: t.clientY, t: Date.now(), on: true, dir: 0 });
}, { passive: true });
document.addEventListener('touchmove', e => {
  if (!SWIPE.on) return;
  if (e.touches.length !== 1) { swipeHide(); return; }
  const t = e.touches[0], dx = t.clientX - SWIPE.x, dy = t.clientY - SWIPE.y;
  if (Math.abs(dy) > 40 && Math.abs(dy) > Math.abs(dx)) { swipeHide(); return; }              // they are scrolling
  if (Math.abs(dx) < 24 || Math.abs(dx) < Math.abs(dy) * 1.5) return;
  const dir = dx < 0 ? 1 : -1, link = document.querySelector(dir > 0 ? '#pnav a.pn-next' : '#pnav a.pn-prev'), h = swipeHint();
  if (dir !== SWIPE.dir) {
    SWIPE.dir = dir;
    const name = link ? (link.querySelector('.pn-name') || link).textContent.trim() : '';
    h.textContent = link ? (dir > 0 ? `Next plant: ${name} →` : `← Previous plant: ${name}`) : (dir > 0 ? 'This is the last plant in the list' : 'This is the first plant in the list');
    h.dataset.side = dir > 0 ? 'right' : 'left';
  }
  h.classList.add('show');
  h.classList.toggle('ready', !!link && Math.abs(dx) >= swipeNeed());
}, { passive: true });
const swipeNeed = () => Math.max(SWIPE_MIN, Math.min(140, window.innerWidth * 0.22));
document.addEventListener('touchend', e => {
  if (!SWIPE.on) return;
  const t = e.changedTouches[0], dx = t.clientX - SWIPE.x, dy = t.clientY - SWIPE.y, quick = Date.now() - SWIPE.t < 1200;
  const go = quick && Math.abs(dx) >= swipeNeed() && Math.abs(dx) > Math.abs(dy) * 2 && !(window.getSelection && String(window.getSelection()).trim());
  const link = go ? document.querySelector(dx < 0 ? '#pnav a.pn-next' : '#pnav a.pn-prev') : null;
  swipeHide();
  if (link) link.click();
}, { passive: true });
document.addEventListener('touchcancel', swipeHide, { passive: true });
window.addEventListener('hashchange', swipeHide);

// ---------- read aloud and keyboard shortcuts (added in 1.8.0) ----------
// Uses the browser's own voices (Edge and Chrome on Windows have several English voices); nothing leaves the computer
// except with "online" voices, which the browser itself provides.
const SPEECH = { on: false, el: null, btn: null };
const canSpeak = () => 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window;
const RD_ICON = raw('<svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 10v4h4l5 4V6L8 10z"/><path d="M16.500 8.500a5 5 0 0 1 0 7M19 6a8.500 8.500 0 0 1 0 12"/></svg>');
function addReadButtons() {
  if (!canSpeak()) { foldMeasure(); return; }
  const app = document.getElementById('app');
  // 1.56.5: not on the small Settings cards, a sentence and a button each, where Read aloud squeezed the title onto three lines
  app.querySelectorAll('section.blk > h2, section.blk > header.sec-head > h2, section.needs > h2, section.cond h2').forEach(h => {
    const sec = h.closest('section'); if (!sec || sec.matches('.set-card:not(.set-health)') || sec.querySelector(':scope > .rd-btn, :scope > header > .rd-btn, :scope > .sec-tools > .rd-btn, :scope > header > .sec-tools > .rd-btn')) return;
    const name = h.textContent.trim();
    sec.classList.add('has-rd');
    const b = rend(html`<button class="btn ghost small rd-btn noprint" type="button" data-act="readsec" aria-label="Read the ${name} section aloud">${RD_ICON}<span>Read aloud</span></button>`);
    const tools = sec.querySelector(':scope > .sec-tools, :scope > header > .sec-tools');      // 1.42.0: beside Show or hide
    if (tools) tools.insertAdjacentHTML('afterbegin', b); else h.insertAdjacentHTML('afterend', b);
  });
  foldMeasure();
  const h1 = app.querySelector('h1');
  if (h1 && !app.querySelector('.rd-page')) h1.insertAdjacentHTML('afterend', rend(html`<p class="rd-page noprint"><button class="btn ghost small" type="button" data-act="readpage" aria-keyshortcuts="R">${RD_ICON}<span>Read this page aloud</span></button></p>`));   // 1.56.5: the R and Escape keys are under Display and the keyboard list, not beside every page title
}
// ---------- 1.42.0: every section on every page can be folded shut, and stays so ----------
// Each section in the Navigation menu gets a "Hide" / "Show" button beside its title (a section that already folds by its own
// title, a <details>, is left as it is). What is folded is remembered on this device for that page, by the section's name
// without its numbers ("Water (37)" and "Water (12)" are the same section); plant pages share one memory.
const FOLDS = (() => { try { return JSON.parse(localStorage.getItem('plantdb.folds') || '{}'); } catch (e) { return {}; } })();
const foldPage = () => { const h = (location.hash || '#/').split('?')[0]; return /^#\/plant\//.test(h) ? '#/plant' : h; };
const foldKey = t => t.replace(/\(\s*[\d,]+\s*\)/g, '').replace(/[\d][\d,.]*/g, '#').replace(/\s+/g, ' ').trim().toLowerCase();
function foldSave() { try { localStorage.setItem('plantdb.folds', JSON.stringify(FOLDS)); } catch (e) { /* this visit only */ } }
// 1.57.0: a plant page is long (about 20 sections). The reference sections start folded on a device that has never folded anything on
// a plant page, so the details, care and requests come first; Show opens each, and what you fold or open is remembered as before.
// (Not in the automated checks, which read every section: navigator.webdriver; plant_folds_check turns it on.)
const PLANT_REF_FOLDED = ['plant identification', 'about this plant', 'uses, partners and propagation', 'temperature', 'humidity', 'sunlight',
  'water and soil', 'nutrients', 'pests and diseases', 'timeline', 'page history'];
(() => { try {
  if (localStorage.getItem('plantdb.foldseed') || FOLDS['#/plant'] || (navigator.webdriver && !localStorage.getItem('plantdb.foldseedtest'))) return;
  FOLDS['#/plant'] = PLANT_REF_FOLDED.slice(); localStorage.setItem('plantdb.foldseed', '1'); foldSave();
} catch (e) { /* storage blocked: every section open */ } })();
function foldIsSet(text) { return (FOLDS[foldPage()] || []).includes(foldKey(text)); }
function foldRemember(text, on) {
  const pg = foldPage(), k = foldKey(text), list = (FOLDS[pg] || []).filter(x => x !== k);
  if (on) list.push(k);
  if (list.length) FOLDS[pg] = list; else delete FOLDS[pg];
  foldSave();
}
function foldTarget(it) {          // the element that folds, and its title (kept in view, with the path down to it)
  const h = it.head || it.el;
  if (h.closest('summary') || it.el.closest('summary')) return null;
  if (it.el === h && h.matches('h1,h2,h3')) return { bare: h };
  const sec = it.el, title = h === sec ? sec.querySelector('h1,h2,h3') : h;
  let keep = title; while (keep && keep.parentElement !== sec) keep = keep.parentElement;
  return { sec, keep, title };
}
function foldBtn(it, open) {
  return rend(html`<button class="btn ghost small sec-fold noprint" type="button" data-act="secfold" data-for="${it.id}" aria-expanded="${open ? 'true' : 'false'}"
    aria-label="${open ? 'Hide' : 'Show'} the ${it.text} section"><span aria-hidden="true">${open ? '▾' : '▸'}</span> <span>${open ? 'Hide' : 'Show'}</span></button>`);
}
// ---------- 1.57.0: notes on request (Display: "Notes under buttons and boxes: Show them when I ask") ----------
// Each small note (.hint) becomes a Note button that opens it in place. It also opens while the mouse is over the control it belongs
// to (or the note), and when a finger rests on that control for half a second. The words stay in the page, so screen readers read them.
const NOTE_SEL = '.hint, label.f > small';      // the small notes: hints, and the note under a field's name
function notesPass(root) {
  if (document.documentElement.dataset.notes !== 'ask') return;
  (root || document).querySelectorAll('.hint:not([data-note]), label.f > small:not([data-note])').forEach(n => {
    n.dataset.note = '1'; n.setAttribute('role', 'button'); n.setAttribute('tabindex', '0'); n.setAttribute('aria-expanded', 'false');
  });
}
function noteToggle(n, open) {
  const on = open == null ? !n.classList.contains('note-open') : open;
  n.classList.toggle('note-open', on); n.setAttribute('aria-expanded', on ? 'true' : 'false');
}
const noteFor = el => { const box = el.closest('label, .f, .row, li, fieldset, .chk, p'); return box && (box.querySelector(':scope > .hint') || (box.matches('label.f') && box.querySelector(':scope > small')) || (box.nextElementSibling && box.nextElementSibling.matches('.hint') ? box.nextElementSibling : null)); };
document.addEventListener('click', e => {
  if (document.documentElement.dataset.notes !== 'ask') return;
  if (NOTEHOLD.swallow) { NOTEHOLD.swallow = false; e.preventDefault(); e.stopPropagation(); return; }
  const n = e.target.closest(NOTE_SEL); if (!n || e.target.closest('a,button,input,select,textarea')) return;
  if (!n.dataset.note) notesPass(n.parentElement);   // drawn after the page: becomes a Note button now
  noteToggle(n); e.stopPropagation(); e.preventDefault();   // in a field's label, opening the note does not also jump to the field
}, true);
document.addEventListener('keydown', e => {
  if (document.documentElement.dataset.notes !== 'ask') return;
  const n = e.target.closest && e.target.closest('[data-note]');
  if (n && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); noteToggle(n); }
  else if (e.key === 'Escape' && n) noteToggle(n, false);
});
const NOTEHOLD = { t: 0, swallow: false };
document.addEventListener('pointerdown', e => {
  if (document.documentElement.dataset.notes !== 'ask' || e.pointerType !== 'touch') return;
  const n = noteFor(e.target); if (!n) return;
  clearTimeout(NOTEHOLD.t);
  NOTEHOLD.t = setTimeout(() => { noteToggle(n, true); NOTEHOLD.swallow = true; setTimeout(() => { NOTEHOLD.swallow = false; }, 800); }, 550);
}, { passive: true });
['pointerup', 'pointercancel', 'pointermove'].forEach(k => document.addEventListener(k, e => { if (k !== 'pointermove' || Math.abs(e.movementX) + Math.abs(e.movementY) > 6) clearTimeout(NOTEHOLD.t); }, { passive: true }));
document.addEventListener('prefs', () => { if (document.documentElement.dataset.notes === 'ask') notesPass(); });

function addFoldButtons() {
  NAVITEMS.forEach(it => {
    if (it.top || !it.id) return;
    const t = foldTarget(it); if (!t) return;
    if (t.bare) {                      // a title with no section of its own: it folds what follows, up to the next title
      const h = t.bare;
      if (!(h.nextElementSibling && h.nextElementSibling.classList.contains('sec-tools'))) h.insertAdjacentHTML('afterend', rend(html`<div class="sec-tools sec-bare noprint">${raw(foldBtn(it, true))}</div>`));
      foldSet(it, foldIsSet(it.text), false);
      return;
    }
    const { sec, keep, title } = t;
    if (sec.querySelector('.sec-fold')) return;
    sec.classList.add('has-fold');
    const tools = `<div class="sec-tools noprint">${foldBtn(it, true)}</div>`;
    if (!keep) sec.insertAdjacentHTML('afterbegin', tools);                                   // no title: the buttons go first
    else if (keep === title) { keep.classList.add('sec-keep'); keep.insertAdjacentHTML('afterend', tools); }  // beside the title, top right
    else if (keep.matches('header')) { keep.classList.add('sec-keep', 'sec-head-row'); keep.insertAdjacentHTML('beforeend', tools); }
    else { keep.classList.add('sec-keep'); title.insertAdjacentHTML('afterend', tools.replace('sec-tools', 'sec-tools sec-inline')); }   // a title further in
    const rd = sec.querySelector(':scope > .rd-btn'); const tl = sec.querySelector('.sec-tools');
    if (rd && tl) tl.insertAdjacentElement('afterbegin', rd);
    if (title) title.classList.add('fold-click');           // 1.56.3: the title folds it too
    if (foldIsSet(it.text)) foldSet(it, true, false);
  });
  // 1.56.3 (Ethan, November 10): a section that folds by its title bar (Today's and Fertilizer's groups, Turn the pots) shows Hide/Show
  // at the right of the bar like every other section's. 1.56.4: it only looks like a button: the whole title bar is the one control
  // (a button inside it was a control inside a control, which screen readers report as a fault), and it says open or closed itself.
  document.querySelectorAll('main details.grp').forEach(d => {
    const s = d.querySelector(':scope > summary'); if (!s || s.querySelector('.det-fold')) return;
    s.insertAdjacentHTML('beforeend', rend(html`<span class="sec-tools det-tools noprint" aria-hidden="true"><span class="btn ghost small sec-fold det-fold"></span></span>`));
    const b = s.querySelector('.det-fold');
    const label = () => { b.innerHTML = rend(html`<span>${d.open ? '▾' : '▸'}</span> <span>${d.open ? 'Hide' : 'Show'}</span>`); };
    d.addEventListener('toggle', label);
    label();
  });
  foldMeasure();
}
// 1.56.3: pressing a section's title (or its title bar) does what its Show/Hide button does; buttons and links in the bar keep their own
document.addEventListener('click', e => {
  const t = e.target; if (!(t instanceof Element)) return;
  if (t.closest('a,button,input,select,textarea,label,summary,[data-act],[data-ed],[contenteditable]')) return;
  if (String(window.getSelection && window.getSelection()) !== '') return;              // selecting the words is not a press
  const head = t.closest('.fold-click, header.sec-head, h1, h2, h3'); if (!head) return;
  if (head.matches('h1,h2,h3') && head.nextElementSibling && head.nextElementSibling.classList.contains('sec-bare')) { head.nextElementSibling.querySelector('.sec-fold').click(); return; }
  const sec = head.closest('.has-fold'); if (!sec) return;
  if (!(head.classList.contains('fold-click') || (head.matches('header.sec-head') && head.querySelector('.fold-click')))) return;
  const b = sec.querySelector('.sec-fold'); if (b) b.click();
});
function foldParts(it) {           // what hides: everything in the section beside the path down to its title, or what follows a bare title
  const t = foldTarget(it); if (!t) return [];
  if (t.bare) { const out = []; let n = t.bare.nextElementSibling; while (n && !n.matches('h1,h2') && !n.querySelector('h2') && !n.matches('section,details.blk')) { if (!n.classList.contains('sec-tools')) out.push(n); n = n.nextElementSibling; } return out; }
  const out = [], tl = t.sec.querySelector('.sec-tools');
  if (!t.title) return [...t.sec.children].filter(c => c !== tl);
  for (let n = t.title; n && n !== t.sec; n = n.parentElement)
    for (const c of n.parentElement.children) if (c !== n && !c.classList.contains('sec-tools') && !c.contains(tl) && !c.classList.contains('rd-page')) out.push(c);
  return out;
}
function foldSet(it, folded, remember) {
  foldParts(it).forEach(c => c.classList.toggle('fold-hid', folded));
  const t = foldTarget(it); if (t && t.sec) t.sec.dataset.folded = folded ? '1' : '0';
  document.querySelectorAll(`[data-act=secfold][data-for="${it.id}"]`).forEach(b => {
    b.setAttribute('aria-expanded', folded ? 'false' : 'true'); b.setAttribute('aria-label', `${folded ? 'Show' : 'Hide'} the ${it.text} section`);
    b.innerHTML = rend(html`<span aria-hidden="true">${folded ? '▸' : '▾'}</span> <span>${folded ? 'Show' : 'Hide'}</span>`);
  });
  if (remember) foldRemember(it.text, folded);
}
function foldOpenFor(el) {         // the menu or a section button goes to a folded section: open it first
  const it = NAVITEMS.find(x => x.el === el || (x.head && x.head === el) || x.el.contains(el));
  if (it && !it.top && foldParts(it).some(c => c.classList.contains('fold-hid'))) foldSet(it, false, true);
}
function titleWidth(t) {           // the width a title takes on one line
  const css = t.style.cssText; t.style.whiteSpace = 'nowrap'; t.style.width = 'max-content'; t.style.paddingRight = '0';
  const w = t.getBoundingClientRect().width; t.style.cssText = css; return w;
}
function foldMeasure() {           // room on the title's right for its buttons
  const level = (t, tl) => { const lh = parseFloat(getComputedStyle(t).lineHeight) || t.offsetHeight; return (Math.min(lh, t.offsetHeight) - tl.offsetHeight) / 2; };
  document.querySelectorAll('#app .has-fold').forEach(sec => {
    const tl = sec.querySelector(':scope > .sec-tools'); if (!tl) return;
    // 1.56.4: the buttons sit beside the title, level with its first line, whenever the title keeps at least 16 rem and over half the
    // width; otherwise they go on the line under it, at the right. Either way they stay put when the section is folded or opened.
    let t = tl.previousElementSibling; while (t && t.matches('.rd-page')) t = t.previousElementSibling;    // the plant's name has Read this page aloud under it
    const w = Math.ceil([...tl.children].reduce((a, c) => a + c.getBoundingClientRect().width, 0) + 8 * (tl.children.length - 1) + 14);
    const room = sec.clientWidth - w, rem = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
    const isT = !!(t && t.matches('h1,h2,h3'));
    const beside = isT && (room >= Math.max(16 * rem, sec.clientWidth * 0.5) || titleWidth(t) <= room);
    sec.classList.toggle('tools-beside', beside);
    sec.style.setProperty('--tools-w', w + 'px');
    tl.style.top = beside ? Math.max(0, t.offsetTop + level(t, tl)) + 'px' : '';
  });
  // 1.56.4: a title with no section of its own (Fertilizer's "Today" box) has its Hide/Show at the right of the title, not on a line under it
  // 1.57.0: and so does a title further into its section (the label card's "Name and details")
  document.querySelectorAll('#app .sec-bare, #app .sec-inline').forEach(tl => {
    const t = tl.previousElementSibling; tl.style.marginTop = ''; tl.style.marginBottom = ''; if (!t || !t.matches('h1,h2,h3')) return;
    t.style.paddingRight = '';
    const w = Math.ceil([...tl.children].reduce((a, c) => a + c.getBoundingClientRect().width, 0) + 8 * (tl.children.length - 1) + 14), host = t.parentElement.clientWidth;
    if (host - w < Math.max(16 * (parseFloat(getComputedStyle(document.documentElement).fontSize) || 16), host * 0.5) && titleWidth(t) > host - w) return;
    t.style.paddingRight = w + 'px';
    const mb = parseFloat(getComputedStyle(t).marginBottom) || 0;
    const lv = level(t, tl), th = tl.offsetHeight;
    tl.style.marginTop = (lv - t.offsetHeight - mb) + 'px'; tl.style.marginBottom = (t.offsetHeight + mb - lv - th) + 'px';
  });
}
window.addEventListener('resize', () => { clearTimeout(foldMeasure.t); foldMeasure.t = setTimeout(foldMeasure, 200); });
if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => foldMeasure());   // 1.56.4: titles change height once their font has loaded
// the text a sighted reader would see: no buttons, form controls, icons, hidden parts or closed details
function readableText(root) {
  const out = [];
  const skip = el => el.matches('button,select,option,input,textarea,script,style,svg,canvas,dialog,.rd-btn,.rd-page,.fold-hid,.sec-tools,.thumbs,.jump,.pnav,.pn-filters,.strip,.ticks,.now-tag,.now-line,[aria-hidden="true"],[hidden]');
  (function walk(n) {
    for (const c of n.childNodes) {
      if (c.nodeType === 3) { const t = c.textContent.replace(/\s+/g, ' '); if (t.trim()) out.push(t); continue; }
      if (c.nodeType !== 1 || skip(c)) continue;
      if (c.tagName === 'DETAILS' && !c.open) { const sm = c.querySelector(':scope > summary'); if (sm) { out.push('. '); walk(sm); out.push('. '); } continue; }
      const cs = getComputedStyle(c);
      if (cs.display === 'none' || (cs.visibility === 'hidden' && !c.classList.contains('sr'))) continue;
      if (c.tagName === 'IMG') { if (c.alt) out.push(' ' + c.alt + '. '); continue; }
      const block = /^(block|flex|grid|list-item|table|table-row|table-caption|flow-root)$/.test(cs.display) || /^H[1-6]$/.test(c.tagName);
      if (block) out.push('. ');
      walk(c);
      if (block) out.push('. '); else if (cs.display === 'table-cell' || cs.display === 'inline-block') out.push(', ');
    }
  })(root);
  return speakable(out.join(''));
}
function speakable(t) {
  return t.replace(/\bP-(\d)(\d)(\d)\b/g, 'P $1 $2 $3')
    .replace(/(-?\d+(?:\.\d+)?)\s?°[FC]/g, '$1 degrees').replace(/°/g, ' degrees').replace(/(\d)\s?F\b/g, '$1 degrees')
    .replace(/(?:u|µ)mol\/m(?:2|²)\/s/g, 'micromoles per square metre per second').replace(/mol\/m(?:2|²)/g, 'moles per square metre')
    .replace(/\/day\b/g, ' a day').replace(/(\d)\s?h\b/g, '$1 hours').replace(/\bRH\b/g, 'relative humidity').replace(/~\s?/g, 'about ')
    .replace(/(\d)\s?-\s?(\d)/g, '$1 to $2').replace(/(\d)\s?in\b/g, '$1 inches').replace(/[✔✖■▲▶◀←→–—]/g, ' ').replace(/\s+/g, ' ')
    .replace(/\s*\.\s*(\.\s*)+/g, '. ').replace(/([:;,])\s*\./g, '$1').replace(/\s+([.,;:])/g, '$1').replace(/^[\s.]+/, '').trim();
}
function rdChunks(t) {          // short pieces: some voices stop after about 15 seconds of one long utterance
  const parts = t.split(/(?<=[.!?:;])\s+/), out = [];
  let cur = '';
  for (const p of parts) { if ((cur + ' ' + p).length > 220 && cur) { out.push(cur); cur = p; } else cur = cur ? cur + ' ' + p : p; }
  if (cur) out.push(cur);
  return out;
}
function rdVoice() {
  const v = window.PlantPrefs.get().voice, all = speechSynthesis.getVoices();
  return (v !== 'auto' && all.find(x => x.name === v)) || all.find(x => /^en(-|_)US/i.test(x.lang) && /natural|online/i.test(x.name)) || all.find(x => /^en/i.test(x.lang)) || null;
}
function stopReading(quiet) {
  if (!canSpeak()) return;
  SPEECH.on = false; speechSynthesis.cancel();
  if (SPEECH.el) SPEECH.el.classList.remove('rd-on');
  if (SPEECH.btn) { SPEECH.btn.querySelector('span').textContent = SPEECH.btn.dataset.act === 'readpage' ? 'Read this page aloud' : 'Read aloud'; SPEECH.btn.setAttribute('aria-pressed', 'false'); }
  SPEECH.el = SPEECH.btn = null;
  const s = document.getElementById('rd-stop'); if (s) s.hidden = true;
  if (!quiet) toast('Stopped reading');
}
function readAloud(el, btn, label) {
  if (!canSpeak()) { toast('This browser cannot read aloud. Edge and Chrome on Windows can.', true); return; }
  const was = SPEECH.btn;
  stopReading(true);
  if (was && was === btn) return;                  // the same button again: stop
  const text = readableText(el); if (!text) { toast('Nothing to read in this section.'); return; }
  const P = window.PlantPrefs.get(), voice = rdVoice(), chunks = rdChunks(text);
  SPEECH.on = true; SPEECH.el = el; SPEECH.btn = btn || null;
  el.classList.add('rd-on');
  if (btn) { btn.querySelector('span').textContent = 'Stop reading'; btn.setAttribute('aria-pressed', 'true'); }
  let st = document.getElementById('rd-stop');
  if (!st) { document.body.insertAdjacentHTML('beforeend', rend(html`<button id="rd-stop" class="btn noprint" type="button" data-act="readstop">Stop reading</button>`)); st = document.getElementById('rd-stop'); }
  st.hidden = false;
  chunks.forEach((c, i) => {
    const u = new SpeechSynthesisUtterance(c);
    u.rate = +P.rate || 1; if (voice) { u.voice = voice; u.lang = voice.lang; } else u.lang = 'en-US';
    if (i === chunks.length - 1) u.onend = () => { if (SPEECH.on && SPEECH.el === el) stopReading(true); };
    speechSynthesis.speak(u);
  });
}
const readTarget = () => document.getElementById('pane-r') || document.getElementById('app');
function voiceOptions(cur) {
  const vs = canSpeak() ? speechSynthesis.getVoices().filter(v => /^en/i.test(v.lang)) : [];
  return html`<option value="auto" ${cur === 'auto' ? raw('selected') : ''}>Best English voice on this computer</option>${vs.map(v => html`<option value="${v.name}" ${cur === v.name ? raw('selected') : ''}>${v.name} (${v.lang})</option>`)}`;
}
if (canSpeak()) speechSynthesis.addEventListener('voiceschanged', () => { const s = document.getElementById('pref-voice'); if (s) s.innerHTML = rend(voiceOptions(window.PlantPrefs.get().voice)); });
function readAloudText(t) {
  if (!canSpeak()) return;
  const P = window.PlantPrefs.get(), v = rdVoice(), u = new SpeechSynthesisUtterance(t);
  u.rate = +P.rate || 1; if (v) { u.voice = v; u.lang = v.lang; }
  speechSynthesis.speak(u);
}
function shortcutsDialog() {
  const k = (key, what) => html`<tr><th scope="row"><kbd>${key}</kbd></th><td>${what}</td></tr>`;
  modal(html`<form method="dialog"><h2>Keyboard shortcuts</h2>
    <p class="muted">They work anywhere except while you are typing in a box. Turn them off in Display settings if they get in the way.</p>
    <table class="tbl"><tbody>
      ${k('R', 'Read this page aloud (press again, or Escape, to stop)')}${k('Escape', 'Stop reading')}
      ${k('[', 'Previous plant (on a plant page)')}${k(']', 'Next plant (on a plant page)')}
      ${k('E', 'Edit this plant (on a plant page)')}${k('/', 'Search: the plant filter on the Plants page, everything else elsewhere')}${typeof vsOn === 'function' && vsOn() ? k('V', 'Search by voice (speak into the microphone; say "open" and a page or plant to go there)') : ''}
      ${k('H', 'Go to the Plants page')}${k('M', 'Open or fold the section menu')}${k('L', 'Choose the location for the weather')}${k('U', 'Undo the care you just logged, while its message is showing')}${k('?', 'Show this list')}
    </tbody></table>
    <div class="row"><button class="btn" value="ok" autofocus>Close</button></div></form>`);
}
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && SPEECH.on) { stopReading(); return; }
  if (e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey || window.PlantPrefs.get().keys !== '1') return;
  const t = e.target;
  if (t.closest && t.closest('input,textarea,select,[contenteditable="true"],dialog[open]')) return;
  const click = sel => { const x = document.querySelector(sel); if (x) { e.preventDefault(); x.click(); } };
  switch (e.key) {
    case '[': click('#pnav a.pn-prev'); break;
    case ']': click('#pnav a.pn-next'); break;
    case 'r': case 'R': e.preventDefault(); { const b = document.querySelector('[data-act=readpage]'); readAloud(readTarget(), b, 'this page'); } break;
    case 'e': case 'E': if (CUR && location.hash.startsWith('#/plant/') && !location.hash.endsWith('/edit')) { e.preventDefault(); location.hash = '#/plant/' + enc(CUR.p.code) + '/edit'; } break;
    case 'h': case 'H': e.preventDefault(); go('#/plants'); break;
    case 'm': case 'M': click('[data-act=navtoggle]:not([aria-hidden])'); break;
    case 'l': case 'L': e.preventDefault(); placeDialog(); break;          // 1.11.0: choose the location
    case '?': e.preventDefault(); shortcutsDialog(); break;
    case '/': {                               // the Plants page's own search box when it is on screen; Search everywhere elsewhere (1.33.0)
      e.preventDefault();
      const d = document.getElementById('pn-filters'); if (d) d.open = true;
      const q = document.querySelector('input[data-f=q]'); if (q) { q.focus(); q.select(); } else searchDialog();
      break;
    }
  }
});
window.addEventListener('hashchange', () => stopReading(true));
async function condDialog() {
  const c = COND || await loadCond() || { mode: 'manual' };
  const W = await api('GET', '/api/weather').catch(() => null);
  const radio = (v, l, hint) => html`<label class="chk-row" style="border:0"><input type="radio" name="csrc" value="${v}" ${c.mode === v ? raw('checked') : ''}><span><strong>${l}</strong>${hint ? html`<br><span class="hint">${hint}</span>` : ''}</span></label>`;
  const r = await modal(html`<form method="dialog"><h2>Current conditions</h2>
    <p>These feed the "Now" marker on every plant page and the steps for getting a plant back in range.</p>
    <fieldset class="opt-group"><legend>Where do the numbers come from?</legend>
      ${radio('manual', 'I will type them in', 'Use this until you have a sensor. Measure or estimate where the plant is.')}
      ${radio('sensor', 'My sensor', W && W.sensor.count ? 'The newest reading it sent.' : 'No sensor has sent a reading yet. See Weather, Connect your sensor.')}
      ${radio('weather', 'Online weather', 'Open sky for ' + (W ? W.location.name : 'your area') + '. Plants under a roof or in shade get less light than this.')}</fieldset>
    <div id="manual-fields" ${c.mode === 'manual' ? '' : raw('hidden')}><div class="field-grid">
      <label class="f">Temperature (${tU()})<input type="number" step="any" name="t" value="${has(c.temp_f) && c.mode === 'manual' ? tNum(c.temp_f, 1) : ''}"></label>
      <label class="f">Humidity (%)<input type="number" step="any" name="h" min="0" max="100" value="${has(c.humidity) && c.mode === 'manual' ? c.humidity : ''}"></label>
      <label class="f">Light<input type="number" step="any" name="l" min="0" value="${has(c.par) && c.mode === 'manual' ? c.par : ''}"></label>
      <label class="f">Light is in<select name="lu"><option value="par">PAR (µmol/m²/s)</option><option value="lux">lux</option></select></label></div>
      <p class="hint">Leave a box empty to keep the last value you typed. Rough light guides when you have no meter: full midday sun about 1,500 to 2,000 PAR (80,000 to 110,000 lux); open shade 200 to 600; under a porch roof 100 to 400; a bright window indoors 100 to 300; a room lit only by a lamp 5 to 30. About 54 lux is 1 PAR in sunlight.</p></div>
    <div class="row"><button class="btn" value="ok">Save</button><button class="btn ghost" value="cancel">Cancel</button></div></form>`);
  if (r !== 'ok') return;
  const f = dlg.querySelector('form'), mode = (dlg.querySelector('[name=csrc]:checked') || {}).value || 'manual';
  const body = { mode };
  if (mode === 'manual') {
    const v = n => dlg.querySelector('[name=' + n + ']').value;
    body.temp_f = v('t') === '' ? '' : tIn(v('t')); body.humidity = v('h');       // 1.47.0: typed in the person's unit, kept in °F
    if (dlg.querySelector('[name=lu]').value === 'lux') body.lux = v('l'); else body.par = v('l');
  }
  await guard(async () => { COND = await api('PUT', '/api/current', body); toast('Current conditions saved'); await route(); });
}

// ---------- photo check before adding photos (added in 1.8.0) ----------
// Each photo is checked in the browser before it is uploaded. The limits were set on Ethan's own photos in
// dev/photos-raw: none of those is flagged, while the same photos blurred, darkened or washed out are.
const PCHK = { dark: 45, black: 0.5, bright: 200, white: 0.2, blur: 35, small: 640 };
async function photoStats(file) {
  let bmp;
  try { bmp = await createImageBitmap(file); } catch (e) { return null; }      // a format this browser cannot read: no check
  const s = Math.min(1, 512 / Math.max(bmp.width, bmp.height)), w = Math.max(3, Math.round(bmp.width * s)), h = Math.max(3, Math.round(bmp.height * s));
  const cv = document.createElement('canvas'); cv.width = w; cv.height = h;
  const cx = cv.getContext('2d', { willReadFrequently: true }); cx.drawImage(bmp, 0, 0, w, h);
  const d = cx.getImageData(0, 0, w, h).data, L = new Float32Array(w * h);
  let sum = 0, black = 0, white = 0;
  for (let i = 0, p = 0; p < L.length; i += 4, p++) {
    const v = 0.2126 * d[i] + 0.7152 * d[i + 1] + 0.0722 * d[i + 2];
    L[p] = v; sum += v; if (v < 16) black++; if (v >= 250) white++;
  }
  // Sharpness: how much the brightness changes between neighbouring pixels, in a 4 x 4 grid of squares. The third
  // sharpest square counts, so a blurred background behind a sharp plant does not make the photo "blurry".
  const tiles = [];
  for (let ty = 0; ty < 4; ty++) for (let tx = 0; tx < 4; tx++) {
    const y0 = Math.max(1, Math.floor(ty * h / 4)), y1 = Math.min(h - 1, Math.floor((ty + 1) * h / 4));
    const x0 = Math.max(1, Math.floor(tx * w / 4)), x1 = Math.min(w - 1, Math.floor((tx + 1) * w / 4));
    let n = 0, m = 0, m2 = 0;
    for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) { const p = y * w + x, v = L[p - w] + L[p + w] + L[p - 1] + L[p + 1] - 4 * L[p]; n++; m += v; m2 += v * v; }
    tiles.push(n ? m2 / n - (m / n) ** 2 : 0);
  }
  tiles.sort((a, b) => b - a);
  return { w: bmp.width, h: bmp.height, mean: sum / L.length, black: black / L.length, white: white / L.length, sharp: tiles[2], bmp };
}
function photoProblems(s) {
  const p = [];
  if (s.mean < PCHK.dark || s.black > PCHK.black) p.push(['Too dark', 'Turn on a light or take the plant into daylight.']);
  else if (s.mean > PCHK.bright || s.white > PCHK.white) p.push(['Too bright (washed out)', 'Keep strong sun off the leaves and out of the background; shade the plant or stand with the sun behind you.']);
  if (s.sharp < PCHK.blur) p.push(['Blurry', 'Hold the phone still, tap the screen on the plant so it focuses, and wait a moment before taking the picture.']);
  if (Math.max(s.w, s.h) < PCHK.small) p.push(['Very small picture', `Only ${s.w} by ${s.h} pixels. Send the photo from the camera at full size, not a screenshot or a thumbnail.`]);
  return p;
}
async function photoCheck(files, input) {
  // Returns the files to upload, or null to add none. Photos that pass are added without asking.
  if (!window.createImageBitmap) return files;
  const n = files.length, checked = [];
  for (const f of files) { let s = null; try { s = await photoStats(f); } catch (e) { s = null; } checked.push({ f, s, probs: s ? photoProblems(s) : [] }); }
  const done = () => checked.forEach(c => c.s && c.s.bmp.close && c.s.bmp.close());
  const bad = checked.filter(c => c.probs.length), good = n - bad.length;
  if (!bad.length) { done(); return files; }
  const pr = modal(html`<form method="dialog" class="pchk"><h2>${n === 1 ? 'Check this photo' : `Check ${bad.length} of these ${n} photos`}</h2>
    <p>${bad.length === 1 ? 'It' : 'They'} may be hard to use for identifying the plant or seeing how it is doing.</p>
    <ul class="pchk-list">${bad.map((c, i) => html`<li><canvas class="pchk-thumb" data-i="${i}" width="120" height="120" role="img" aria-label="${'Preview of ' + c.f.name}"></canvas>
      <div><p class="pchk-name">${c.f.name}</p><ul>${c.probs.map(p => html`<li><strong>${p[0]}.</strong> ${p[1]}</li>`)}</ul></div></li>`)}</ul>
    <div class="row">
      ${input ? html`<button class="btn" value="again" autofocus>Take ${bad.length === 1 ? 'a new one' : 'new ones'}</button>` : ''}
      ${good ? html`<button class="btn ghost" value="good">Add only the ${good} good one${good === 1 ? '' : 's'}</button>` : ''}
      <button class="btn ghost" value="all" ${input ? '' : raw('autofocus')}>Add ${n === 1 ? 'it' : n === 2 ? 'both' : `all ${n}`} anyway</button>
      <button class="btn ghost" value="cancel">Cancel</button></div></form>`);
  document.querySelectorAll('#dlg canvas.pchk-thumb').forEach(cv => {        // previews are drawn, so the page's security rules need no change
    const box = cv.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
    if (box.width) { cv.width = Math.round(box.width * dpr); cv.height = Math.round(box.height * dpr); }
    const b = bad[+cv.dataset.i].s.bmp, k = Math.min(cv.width / b.width, cv.height / b.height), w = b.width * k, h = b.height * k;
    cv.getContext('2d').drawImage(b, (cv.width - w) / 2, (cv.height - h) / 2, w, h);
  });
  const r = await pr; done();
  if (r === 'all') return files;
  if (r === 'good') return checked.filter(c => !c.probs.length).map(c => c.f);
  if (r === 'again' && input) { input.value = ''; input.click(); }
  return null;
}
window.PlantPhotoCheck = { stats: photoStats, problems: photoProblems };     // for dev/test/photocheck_check.py
// ---------- photos page ----------
let TODO = [];
async function viewPhotos() {
  const [un, todo] = await Promise.all([api('GET', '/api/photos/unassigned'), api('GET', '/api/to-photograph')]);
  return {
    title: 'Photos',
    html: html`<h1>Photos</h1><p class="muted">Garden overview shots and anything not yet matched to a plant.</p><p class="noprint"><a href="#/share">Photos shared from your phone</a> (Share → Plants on an Android phone with the app on its Home Screen).</p>
    <section class="blk"><h2>Photos without a plant (${un.length})</h2>
      <label class="f" style="max-width:420px">Upload photos<small>They stay here until you assign them to a plant.</small><input type="file" accept="image/*" multiple data-act="addloose"></label>
      ${un.length ? html`<div class="pgrid">${un.map(x => html`<div class="pcard"><img src="${thumbUrl(x.file)}" alt="${x.caption || 'Unassigned photo'}" data-act="zoomloose" data-file="${x.file}" data-cap="${x.caption}">
        <div class="b"><p style="margin:0 0 8px">${x.caption || 'No caption'}</p><div class="row"><button class="btn small" type="button" data-act="assign" data-id="${x.id}">Assign to a plant</button>
        <button class="btn danger small" type="button" data-act="rmloose" data-id="${x.id}" aria-label="Remove this unassigned photo">Remove</button></div></div></div>`)}</div>` : html`<div class="empty">Every photo is assigned to a plant.</div>`}</section>
    <section class="blk"><h2>Still to photograph</h2><p class="muted">Plants and areas where one more picture would help Claude identify or assess them.</p>
      <form class="todo-form" data-form="todo"><div class="field-grid">
        <label class="f">What to photograph<input type="text" name="label" maxlength="200" required placeholder="For example: tag on the maroon pot"></label>
        <label class="f">Note (optional)<input type="text" name="note" maxlength="1000" placeholder="Where it is, what to capture"></label>
        <label class="f">Related plant (optional)<select name="plant" class="w-fixed"><option value="">None</option>${[...PCODES.values()].map(p => html`<option value="${p.code}">${p.code} ${p.common_name}</option>`)}</select></label></div>
        <p class="hint">Plant codes such as P-012 typed anywhere in the text become links; point at one to see a photo of that plant.</p>
        <button class="btn" type="submit">Add to the list</button></form>
      ${todo.length ? todo.map(t => html`<div class="chk-row"><input type="checkbox" data-act="tododone" data-id="${t.id}" ${t.done ? raw('checked') : ''} aria-label="Done: ${t.label}">
        <div class="grow"><div class="${t.done ? 'done' : ''}"><strong>${linkify(t.label)}</strong></div>${t.note ? html`<div class="muted ${t.done ? 'done' : ''}">${linkify(t.note)}</div>` : ''}</div>
        <div class="row" style="gap:.4rem"><button class="btn ghost small" type="button" data-act="todoedit" data-id="${t.id}" aria-label="Edit: ${t.label}">Edit</button>
        <button class="btn danger small" type="button" data-act="tododel" data-id="${t.id}" aria-label="Delete: ${t.label}">Delete</button></div></div>`) : html`<div class="empty">Nothing on the list.</div>`}</section>`,
    after: () => { TODO = todo; },
  };
}

// ---------- backups page ----------
const mb = n => n >= 1073741824 ? (n / 1073741824).toFixed(1) + ' GB' : n >= 1048576 ? (n / 1048576).toFixed(1) + ' MB' : Math.max(1, Math.round(n / 1024)) + ' KB';
const BK_FREQ_WORDS = { '6h': 'Every 6 hours', '12h': 'Every 12 hours', daily: 'Every day', '3d': 'Every 3 days', weekly: 'Every week' };
const BK_KIND = { manual: 'Made by you', auto: 'Automatic', update: 'Before an update' };
let BK = null;
let CP = null;
function copiesHtml(C) {          // 1.33.0: the second copy of each backup
  const st = C.status || {};
  return html`<section class="blk" id="bk-copies"><h2>Second copy</h2>
    <p>Backups are on this PC's drive. A second copy of each new backup can also go to another drive, and to another computer over Tailscale (your girlfriend's PC, say), as soon as the backup is made. The newest ${C.keep} are kept in the folder, the newest 20 on the other computer.</p>
    <h3>Another drive</h3>
    ${C.dir_ok ? html`<p><span aria-hidden="true">✓</span> Copies go to <code>${C.dir_env || 'backups-copy, next to the data folder'}</code>${C.dir_files.length ? ` (${C.dir_files.length} there now).` : ' (none there yet).'}${!C.dir_env ? ' That is the same drive: to use another one, put <code>PLANTDB_COPY_DIR=D:\\PlantBackups</code> (your folder) in the <code>.env</code> file next to docker-compose.yml, then run the updater or <code>docker compose up -d</code>.' : ''}</p>`
      : html`<p class="muted">No folder is mapped. Put <code>PLANTDB_COPY_DIR=D:\\PlantBackups</code> (a folder on another drive) in the <code>.env</code> file next to docker-compose.yml, then run <code>docker compose up -d</code>.</p>`}
    <h3>Another computer</h3>
    <form data-form="bkcopies" class="f-grid" autocomplete="off">
      <label class="f">Receiver address<small>The other computer's Tailscale address and port, from its receiver (see the receiver folder in the release)</small><input type="url" name="url" maxlength="300" placeholder="http://100.101.102.103:8089" value="${C.url || ''}"></label>
      <label class="f">Token<small>${C.have_token ? 'Saved. Type a new one to change it.' : 'The BACKUP_TOKEN from the receiver\'s .env file.'}</small><input type="password" name="token" maxlength="200" autocomplete="off"></label>
      <div class="row"><button class="btn" type="submit">Save</button>${C.url || C.dir_ok ? html`<button class="btn ghost" type="button" data-act="bkcopynow">Copy the newest backup now</button>` : ''}</div></form>
    ${st.file ? html`<p class="hint">Last copy: ${st.file}, ${when(st.at)}. Folder: ${st.dir || 'not set up'}. Other computer: ${st.receiver || 'not set up'}.</p>` : ''}
    <p id="bk-copy-msg" role="status" aria-live="polite"></p></section>`;
}
async function viewBackups() {
  if (ME().role !== 'owner') return { title: 'Backups', html: html`<h1>Backups</h1><p class="notice">Backups are looked after by ${ME().owner_name}. They hold a copy of everything, so only the owner can make, download or restore them.</p>` };
  [BK, CP] = await Promise.all([api('GET', '/api/backups'), api('GET', '/api/backups/copies').catch(() => null)]);
  const S = BK.settings, hourOpt = h => new Date(2026, 0, 1, h).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  const where = BK.mounted ? 'the backups folder inside your plant-database folder' : 'data\\backups inside your plant-database folder';
  const last = BK.backups[0];
  return {
    title: 'Backups',
    html: html`<h1>Backups</h1>
    <p class="muted">A backup is a zip with a complete copy of the database (plants, change log, weather history, feeding log, settings) and, if you choose, all the photos. Backups are saved in ${where}, so they survive updates. Copy a few to another drive now and then.</p>
    <p class="${last ? 'notice ok' : 'notice'}" role="status">${last ? html`Latest backup: <strong>${when(last.created_at)}</strong> (${BK_KIND[last.kind]}, ${mb(last.bytes)}).` : 'No backups yet. Make one now.'}
      ${S.enabled ? ` Automatic backups: ${BK_FREQ_WORDS[S.freq].toLowerCase()}${['daily', '3d', 'weekly'].includes(S.freq) ? ' at about ' + hourOpt(S.hour) : ''}.` : ' Automatic backups are off.'}</p>
    <section class="blk"><h2>Back up now</h2>
      <form data-form="bknow"><div class="field-grid">
        <label class="f">Note (optional)<input type="text" name="note" maxlength="300" placeholder="For example: before repotting day"></label></div>
        <label class="chk-row" style="border:0"><input type="checkbox" name="photos"><span>Include the photos (adds about ${mb(BK.photo_bytes)})</span></label>
        <div class="row"><button class="btn" type="submit">Back up now</button></div></form>
      <div id="bk-job" role="status" aria-live="polite">${bkJobHtml(BK.job)}</div></section>
    <section class="blk"><h2>Automatic backups</h2>
      <form data-form="bkset"><label class="chk-row" style="border:0"><input type="checkbox" name="enabled" ${S.enabled ? raw('checked') : ''}><span>Make backups automatically</span></label>
        <div class="field-grid">
          <label class="f">How often<select name="freq">${BK.freqs.map(f => html`<option value="${f}" ${S.freq === f ? raw('selected') : ''}>${BK_FREQ_WORDS[f]}</option>`)}</select></label>
          <label class="f">At about<small>For daily, 3-day and weekly backups</small><select name="hour">${[...Array(24).keys()].map(h => html`<option value="${h}" ${+S.hour === h ? raw('selected') : ''}>${hourOpt(h)}</option>`)}</select></label>
          <label class="f">Keep this many automatic backups<small>Older automatic ones are deleted. Your own backups are never deleted automatically.</small><input type="number" name="keep" min="1" max="365" value="${S.keep}"></label></div>
        <label class="chk-row" style="border:0"><input type="checkbox" name="photos" ${S.photos ? raw('checked') : ''}><span>Include the photos in automatic backups</span></label>
        <p class="hint">The database is ${mb(BK.db_bytes)} (most of it is weather history); a backup zip is usually a third to a half of that. Backups now use ${mb(BK.total_bytes)}; ${mb(BK.free_bytes)} free. The app must be running for automatic backups; a missed one runs when it next starts.</p>
        <button class="btn" type="submit">Save automatic backup settings</button></form></section>
    ${CP ? copiesHtml(CP) : ''}
    <section class="blk"><h2>Your backups (${BK.backups.length})</h2>
      ${BK.backups.length ? html`<div class="tbl-wrap"><table class="tbl"><caption class="sr">Backups, newest first</caption><thead><tr><th scope="col">Made</th><th scope="col">Type</th><th scope="col" class="num">Size</th><th scope="col">Contents</th><th scope="col"><span class="sr">Actions</span></th></tr></thead><tbody>
        ${BK.backups.map(b => html`<tr><th scope="row">${when(b.created_at)}${b.note ? html`<div class="hint">${b.note}</div>` : ''}</th><td>${BK_KIND[b.kind]}${b.by && b.kind !== 'auto' ? html`<div class="hint">${b.by}</div>` : ''}</td>
          <td class="num">${mb(b.bytes)}</td><td>${b.broken ? html`<strong>Damaged file</strong>` : html`Database${b.photos ? ' and photos' : ''}${b.plants != null ? `, ${b.plants} plants` : ''}${b.version ? html`<div class="hint">App version ${b.version}</div>` : ''}`}</td>
          <td><div class="row" style="gap:.4rem"><a class="btn small" href="/api/backups/${enc(b.file)}" download aria-label="Download the backup ${b.file}">Download</a>${!b.broken && ME().role === 'owner' ? html`<button class="btn small ghost" type="button" data-act="bkrestore" data-file="${b.file}" data-made="${when(b.created_at)}" data-plants="${b.plants == null ? '' : b.plants}" data-photos="${b.photos ? '1' : ''}">Restore</button>` : ''}<button class="btn small danger" type="button" data-act="bkdel" data-file="${b.file}" aria-label="Delete the backup ${b.file}">Delete</button></div></td></tr>`)}</tbody></table></div>` : html`<div class="empty">No backups yet.</div>`}</section>
    <section class="blk"><h2>Restoring a backup</h2>
      <ol><li>Stop the app (in the plant-database folder): <span class="code">docker compose down</span></li>
        <li>Rename the current <span class="code">data\\plants.db</span> to <span class="code">plants-old.db</span> (keep it until you are sure).</li>
        <li>Open the backup zip and copy <span class="code">plants.db</span> into the <span class="code">data</span> folder. If the backup has a <span class="code">photos</span> folder, copy its files into <span class="code">data\\photos</span>.</li>
        <li>Start the app: <span class="code">docker compose up -d</span></li></ol>
      <p class="hint">The README has these steps as cmd.exe, PowerShell and bash commands.</p></section>`,
    after: () => { if (BK.job && BK.job.running) bkPoll(); },
  };
}
function bkJobHtml(j) {
  if (!j || (!j.running && !j.finished)) return '';
  if (j.running) return html`<p class="notice">Making a backup${j.photos ? ' with photos' : ''}… this takes a few seconds (longer with photos).</p>`;
  return j.ok ? html`<p class="notice ok">Backup finished ${when(j.finished)}: ${j.file}</p>` : html`<p class="notice bad">Backup failed: ${j.error}</p>`;
}
async function bkPoll() {
  const el = document.getElementById('bk-job'); if (!el) return;
  let j; try { j = await api('GET', '/api/backups/job'); } catch (e) { return; }
  el.innerHTML = rend(bkJobHtml(j));
  if (j.running) setTimeout(bkPoll, 1500); else if (location.hash.startsWith('#/backups')) { toast(j.ok ? 'Backup finished' : 'Backup failed', !j.ok); route(); }
}

// ---------- labels page ----------
function labelCard(p, base, withLink) {
  return html`<div class="lblwrap"><div class="lbl"><img src="/api/plants/${enc(p.code)}/qr.svg?base=${enc(base)}" alt="QR code for ${p.code}" width="96" height="96" loading="lazy">
    <div><span class="code">${p.code}</span><b>${p.common_name}</b><span class="sci latin">${p.scientific_name || ''}</span></div></div>
    ${withLink ? html`<a class="btn small ghost noprint lbl-open" href="#/plant/${enc(p.code)}" aria-label="Open the page for ${p.code} ${p.common_name}">Open plant page</a>` : ''}</div>`;
}
async function viewLabels() {
  const [list, st] = await Promise.all([api('GET', '/api/plants'), api('GET', '/api/settings')]);
  const base = st.base_url || location.origin;
  const local = /^https?:\/\/(localhost|127\.|\[::1\])/i.test(base);
  return {
    title: 'Labels',
    html: html`<h1>Plant labels</h1><p class="muted">Print these, cut them out and stick one on each pot. Scanning the code with a phone opens that plant's page.</p>
    <div class="noprint">
      <form class="todo-add" data-form="base"><label style="flex:1 1 320px;font-weight:700">Address the codes should open<input type="text" name="base" value="${st.base_url}" placeholder="http://192.168.1.20:8080" inputmode="url"></label>
        <button class="btn" type="submit" style="align-self:end">Save address</button></form>
      ${/\.ts\.net$/i.test(base) ? html`<div class="notice ok">Codes open <strong>${base}</strong>, the app's Tailscale address. Any phone signed in to Tailscale can open them, at home or away, including people you have shared the app with.</div>`
        : local ? html`<div class="notice">The codes currently point to <strong>${base}</strong>, which only works on this computer. A phone cannot open that. Use the app's Tailscale address (README: "Using the app away from home").</div>`
        : html`<div class="notice">Codes open <strong>${base}</strong>. That address only works on your home network, and from version 1.12.0 the app is closed to the home network unless you open it again (README). The Tailscale address works everywhere.</div>`}
      ${/\.ts\.net$/i.test(location.hostname) && base !== location.origin && ME().role === 'owner' ? html`<p><button class="btn ghost" type="button" data-act="usethisbase">Use this address for the codes: ${location.origin}</button></p>` : ''}
      <p class="row"><button class="btn" type="button" data-act="print">Print labels</button>
        <a class="btn ghost" href="/card.html?all=1">Print care cards for all plants</a></p>
      <p class="hint">Care cards: a 4 × 6 inch card (or a full page) for each plant, with its water, light, temperature, humidity, feeding and dangers in big type.</p></div>
    <div class="lsheet">${list.map(p => labelCard(p, base, true))}</div>
    <section class="blk" id="place-labels"><h2>Room, area and shelf labels</h2>
      <p class="muted">One for each room or area and each spot under Rooms and spots. Stick it on the shelf or by the door: scanning it opens the Plants page showing just what lives there.</p>
      ${placeLabels(base)}</section>`,
  };
}
// 1.34.0: labels for rooms, areas and spots
function placeLabels(base) {
  const homes = (META && META.where) || [], multi = homes.length > 1;
  const card = (q, name, sub, href, aria) => html`<div class="lblwrap"><div class="lbl"><img src="/api/where/qr.svg?${q}&base=${enc(base)}" alt="QR code for ${name}" width="96" height="96" loading="lazy">
      <div><b>${name}</b><span class="sci">${sub}</span></div></div>
    <a class="btn small ghost noprint lbl-open" href="${href}" aria-label="${aria}">Show its plants</a></div>`;
  const cards = homes.flatMap(h => h.areas.flatMap(a => [card('area=' + a.id, a.name, `${a.site}${multi ? ', ' + h.home.name : ''} · ${a.plants} plant${a.plants === 1 ? '' : 's'}`, `#/plants?area=${a.id}`, `Show the plants in ${a.name}`),
    ...(a.spots || []).map(sp => card('spot=' + sp.id, sp.name, `${a.name}${multi ? ', ' + h.home.name : ''} · ${sp.plants} plant${sp.plants === 1 ? '' : 's'}`, `#/plants?spot=${sp.id}`, `Show the plants at ${sp.name}, ${a.name}`))]));
  return cards.length ? html`<div class="lsheet">${cards}</div>` : html`<p class="muted">No rooms or spots yet. Add them under <a href="#/where">Rooms and spots</a>.</p>`;
}

// ---------- audit log page: every change to every record, with filters (1.10.0; was the Change log page) ----------
let AUDOPEN = false;             // 1.39.1: the audit filters box stays open for the visit once you open it
document.addEventListener('toggle', e => { if (e.target && e.target.id === 'aud-fbox') AUDOPEN = e.target.open; }, true);
const AUD = { f: { q: '', plant: '', who: '', kind: '', field: '', from: '', to: '', order: 'desc' }, offset: 0, limit: 100, facets: null, total: 0, t: null };
try { const s = JSON.parse(localStorage.getItem('plantdb.auditf') || '{}'); Object.keys(AUD.f).forEach(k => { if (typeof s[k] === 'string') AUD.f[k] = s[k]; }); } catch (e) { /* defaults */ }
const audSave = () => { try { localStorage.setItem('plantdb.auditf', JSON.stringify(AUD.f)); } catch (e) { /* not remembered */ } };
function audQS(extra) {
  const p = new URLSearchParams();
  Object.entries(AUD.f).forEach(([k, v]) => { if (v && !(k === 'order' && v === 'desc')) p.set(k, v); });
  Object.entries(extra || {}).forEach(([k, v]) => p.set(k, v));
  return p.toString();
}
const audClip = (v, n) => { v = v == null ? '' : String(v).replace(/\s+/g, ' ').trim(); return v.length > n ? v.slice(0, n - 1) + '…' : v; };
const AUD_FIELD_ACTS = ['update', 'edit', 'restore', 'archive', 'unarchive'];
function auditChange(a) {        // "Health rating: from Poor to Fair", for a change to one field of a plant page; '' for anything else
  if (!a.field || !AUD_FIELD_ACTS.includes(a.action)) return '';
  const o = audClip(a.old_value, 60), n = audClip(a.new_value, 60);
  return `${a.label}: ${!o ? 'set to ' + (n || '(empty)') : !n ? 'cleared (it was ' + o + ')' : 'from ' + o + ' to ' + n}`;
}
const shortWho = w => { const m = /^Claude \((batch [^,)]+)/.exec(w || ''); return m ? 'Claude, ' + m[1] : w; };
function audCell(v) {
  if (v == null || v === '') return '';
  const s = String(v);
  return s.length > 160 ? html`<details class="aud-more"><summary>${s.slice(0, 120)}…</summary><div class="aud-full">${s}</div></details>` : s;
}
function audBefore(a) {         // a field that had no value before says so, rather than leaving a blank
  if ((a.old_value == null || a.old_value === '') && auditChange(a)) return html`<td data-label="Before"><span class="muted">Not set</span></td>`;
  return html`<td data-label="Before" class="old">${audCell(a.old_value)}</td>`;
}
function audRecord(a) {
  if (a.plant_code) return html`<a href="#/plant/${enc(a.plant_code)}">${a.plant_code}</a>${a.plant_name ? html` <span class="muted">${a.plant_name}</span>` : ''}`;
  return { setting: 'Setting', backup: 'Backup', request: 'General request', todo: '"Still to photograph" list', photo_add: 'Photos page', photo_remove: 'Photos page', photo_caption: 'Photos page', note: 'Update' }[a.action] || 'Not about one plant';
}
function audRows(list) {
  if (!list.length) return html`<div class="empty">No changes match these filters.<p><button class="btn ghost small" type="button" data-act="audclear">Clear filters</button></p></div>`;
  return html`<div class="tbl-wrap aud-wrap"><table class="tbl aud-tbl"><caption class="sr">Changes</caption>
    <thead><tr><th scope="col">When</th><th scope="col">Record</th><th scope="col">Who</th><th scope="col">What</th><th scope="col">Before</th><th scope="col">After</th></tr></thead>
    <tbody>${list.map(a => html`<tr><td data-label="When">${timeEl(a.changed_at)}</td><td data-label="Record">${audRecord(a)}${a.version != null ? html`<div class="muted">Version ${a.version}</div>` : ''}</td>
      <td data-label="Who">${a.changed_by}</td>
      <td data-label="What"><strong>${a.action_word}</strong>${a.label && a.label !== a.action_word ? html`: ${a.label}` : ''}${a.note && a.note !== a.action_word ? html`<div class="muted">${a.note}</div>` : ''}</td>
      ${audBefore(a)}<td data-label="After" class="new">${audCell(a.new_value)}</td></tr>`)}</tbody></table></div>`;
}
const audInUse = () => Object.entries(AUD.f).filter(([k, v]) => v && k !== 'order').length;
const audInUseWords = () => { const n = audInUse(); return n ? `: ${n} in use` : ''; };
function audWords() {
  const F = AUD.facets || {}, f = AUD.f, w = [];
  if (f.q) w.push(`containing "${f.q}"`);
  if (f.plant === '-') w.push('not about one plant'); else if (f.plant) w.push('for ' + f.plant);
  if (f.who === '~people') w.push('by people'); else if (f.who === '~claude') w.push("from Claude's updates"); else if (f.who) w.push('by ' + f.who);
  if (f.kind) w.push((((F.kinds || []).find(k => k.key === f.kind)) || { label: f.kind }).label.toLowerCase());
  if (f.field) w.push('field: ' + (((F.fields || []).find(x => x.name === f.field)) || { label: f.field }).label);
  if (f.from) w.push('from ' + midDay(f.from)); if (f.to) w.push('to ' + midDay(f.to));
  return w.join(', ');
}
async function audLoad(focusSel) {
  const box = document.getElementById('aud-list'); if (!box) return;
  let r;
  try { r = await api('GET', '/api/audit/search?' + audQS({ limit: AUD.limit, offset: AUD.offset })); }
  catch (e) { box.innerHTML = rend(html`<p class="notice bad">Could not load the audit log: ${e.message}</p>`); return; }
  AUD.total = r.total;
  const end = Math.min(r.offset + r.entries.length, r.total), words = audWords();
  document.getElementById('aud-sum').textContent = r.total ? `Showing ${(r.offset + 1).toLocaleString()} to ${end.toLocaleString()} of ${r.total.toLocaleString()} ${r.total === 1 ? 'change' : 'changes'}${words ? ' ' + words : ''}.` : `No changes${words ? ' ' + words : ''}.`;
  box.innerHTML = rend(audRows(r.entries));
  const pages = Math.max(1, Math.ceil(r.total / AUD.limit)), page = Math.floor(r.offset / AUD.limit) + 1;
  const pager = document.getElementById('aud-pager');
  if (pager) pager.innerHTML = rend(pages > 1 ? html`<button class="btn small ghost" type="button" data-act="audpage" data-d="-1" ${page <= 1 ? raw('disabled') : ''}>Previous page</button>
    <span>Page ${page} of ${pages}</span><button class="btn small ghost" type="button" data-act="audpage" data-d="1" ${page >= pages ? raw('disabled') : ''}>Next page</button>` : '');
  const csv = document.getElementById('aud-csv'); if (csv) csv.href = '/api/audit.csv?' + audQS();
  const iu = document.getElementById('aud-inuse'); if (iu) iu.textContent = audInUseWords();
  if (focusSel) { const el = document.querySelector(focusSel); if (el) el.focus({ preventScroll: true }); }
}
async function viewHistory() {
  AUD.facets = await api('GET', '/api/audit/facets');
  const F = AUD.facets, f = AUD.f, sel = (k, v) => v === f[k] ? raw('selected') : '';
  return {
    title: 'Audit log',
    html: html`<div class="hero"><div><h1>Audit log</h1><p class="muted">Every change to every record. ${F.total.toLocaleString()} changes since ${F.first ? midDay(F.first.slice(0, 10)) : 'the start'}. Times are shown in your time zone.</p></div>
      <div class="row noprint"><a class="btn ghost small" href="/api/export.csv">Download plants (CSV)</a><a class="btn ghost small" href="/api/readings.csv">Download weather and sensor readings (CSV)</a><a class="btn ghost small" href="/api/export.json">Download all data (JSON)</a></div></div>
    <details class="aud-fbox noprint" id="aud-fbox" ${audInUse() || AUDOPEN ? raw('open') : ''}><summary>Search and filters<span id="aud-inuse">${audInUseWords()}</span></summary>
    <form class="aud-filters" role="search" aria-label="Filter the audit log" data-form="audf">
      <label class="f aud-q">Search<input type="search" name="q" data-f="audq" value="${f.q}" placeholder="Words, plant code or name"></label>
      <label class="f">Plant<select name="plant" data-f="aud"><option value="">All plants</option><option value="-" ${sel('plant', '-')}>Not about one plant</option>
        ${F.plants.map(p => html`<option value="${p.code}" ${sel('plant', p.code)}>${p.code} ${p.name}${p.status === 'archived' ? ' (archived)' : ''}</option>`)}</select></label>
      <label class="f">Who<select name="who" data-f="aud"><option value="">Everyone</option><option value="~people" ${sel('who', '~people')}>People (not Claude's updates)</option><option value="~claude" ${sel('who', '~claude')}>Claude's updates (all)</option>
        ${F.who.map(w => html`<option value="${w.name}" ${sel('who', w.name)}>${w.name} (${w.count})</option>`)}</select></label>
      <label class="f">Kind of change<select name="kind" data-f="aud"><option value="">Any kind</option>${F.kinds.map(k => html`<option value="${k.key}" ${sel('kind', k.key)}>${k.label}</option>`)}</select></label>
      <label class="f">Field<select name="field" data-f="aud"><option value="">Any field</option>${F.fields.map(x => html`<option value="${x.name}" ${sel('field', x.name)}>${x.label}</option>`)}</select></label>
      <label class="f">From<input type="date" name="from" data-f="aud" value="${f.from}"></label>
      <label class="f">To<input type="date" name="to" data-f="aud" value="${f.to}"></label>
      <label class="f">Order<select name="order" data-f="aud"><option value="desc">Newest first</option><option value="asc" ${sel('order', 'asc')}>Oldest first</option></select></label>
      <div class="row aud-acts"><button class="btn small ghost" type="button" data-act="audclear">Clear filters</button><a class="btn small ghost" id="aud-csv" href="/api/audit.csv">Download these changes (CSV)</a>
        <button class="btn small ghost" type="button" data-act="audrefresh">Refresh</button></div></form></details>
    <p class="hint noprint">To watch changes as they happen, turn on the audit log console with the Debug button.</p>
    <p id="aud-sum" class="aud-sum" role="status" aria-live="polite">Loading the audit log</p>
    <div id="aud-list"></div>
    <nav class="pager aud-pager row" id="aud-pager" aria-label="Pages of changes"></nav>`,
    after: () => audLoad(),
  };
}

// ---------- the Debug button and the live audit log console (added in 1.10.0) ----------
const DBG = { console: '0', lines: '4', announce: '0' };
try { const s = JSON.parse(localStorage.getItem('plantdb.debug') || '{}'); Object.keys(DBG).forEach(k => { if (typeof s[k] === 'string') DBG[k] = s[k]; }); } catch (e) { /* defaults */ }
const dbgSave = () => { try { localStorage.setItem('plantdb.debug', JSON.stringify(DBG)); } catch (e) { /* not remembered */ } };
const CON = { last: 0, timer: null, paused: false, unseen: 0, busy: false, failed: 0, stick: true };   // stick: the view is at the newest change, so new ones scroll into view
function conEl(id) { return document.getElementById(id); }
function conRow(a) {
  const t = new Date(a.changed_at).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', second: '2-digit' });
  return html`<div class="con-row" data-id="${a.id}"><time datetime="${a.changed_at}" title="${when(a.changed_at)}">${t}</time>
    <span class="con-who" title="${a.changed_by}">${shortWho(a.changed_by)}</span>${a.plant_code ? html` <a href="#/plant/${enc(a.plant_code)}">${a.plant_code}</a>` : ''}
    <span class="con-what">${auditChange(a) || html`<strong>${a.action_word}:</strong> ${a.note || a.label || ''}`}</span></div>`;
}
function conAtBottom() { return CON.stick; }
function conScrolled() { const b = conEl('con-body'); CON.stick = !b || b.scrollTop + b.clientHeight >= b.scrollHeight - 6; if (CON.stick && CON.unseen) { CON.unseen = 0; const n = conEl('con-new'); if (n) n.hidden = true; } }
function conAdd(rows, first) {
  const b = conEl('con-body'); if (!b || !rows.length) return;
  const stick = first || conAtBottom();
  if (first) b.innerHTML = ''; else b.querySelectorAll('p.muted').forEach(x => x.remove());
  b.insertAdjacentHTML('beforeend', rend(html`${rows.map(conRow)}`));
  while (b.children.length > 200) b.firstElementChild.remove();
  conLayout(); fitPanes();
  if (stick) { b.scrollTop = b.scrollHeight; CON.unseen = 0; CON.stick = true; } else CON.unseen += first ? 0 : rows.length;
  const n = conEl('con-new');
  if (n) { n.hidden = !CON.unseen; n.textContent = `${CON.unseen} new ${CON.unseen === 1 ? 'change' : 'changes'} below: show`; }
}
function conState(text) { const s = conEl('con-state'); if (s && s.textContent !== text) s.textContent = text; }
async function conPoll() {
  if (CON.busy || CON.paused || document.hidden || DBG.console !== '1') return;
  CON.busy = true;
  try {
    const first = !CON.started;
    const rows = first ? (await api('GET', '/api/audit?limit=60')).reverse() : await api('GET', '/api/audit?after=' + CON.last + '&limit=100');
    if (CON.paused || DBG.console !== '1') return;        // paused or closed while this check was on its way: Resume picks these up
    if (rows.length) { CON.last = rows[rows.length - 1].id; conAdd(rows, first); }
    else if (first) { const b = conEl('con-body'); if (b) b.innerHTML = rend(html`<p class="muted">Nothing logged yet.</p>`); }
    CON.started = true;
    CON.failed = 0; conState(CON.paused ? 'Paused' : 'Live');
  } catch (e) { CON.failed++; if (!CON.paused) conState('Cannot reach the app, trying again'); }
  finally { CON.busy = false; }
}
// 1.26.0: on phones (narrow windows) the list of pages folds behind one "Pages" button, which names the page you are on
function topMoreFold() { const top = document.querySelector('header.top'), m = document.getElementById('more-btn'); if (top) top.classList.remove('more-open'); if (m) m.setAttribute('aria-expanded', 'false'); }
function pagesMenu(open) {
  const b = document.getElementById('pages-btn'), top = document.querySelector('header.top'); if (!b || !top) return;
  const cur = document.querySelector('#main-nav a[aria-current=page]'), c = document.getElementById('pages-cur');
  const sub = document.querySelector('#sub-nav:not([hidden]) a[aria-current=page]'), word = a => a.childNodes[0].textContent.trim();
  const narrow = document.documentElement.dataset.narrow === '1';     // 1.56.5: on a narrow screen just the page, so it fits beside Search and More
  if (c) c.textContent = narrow && sub ? word(sub) : (cur ? word(cur) : 'Plants') + (sub && cur && word(sub) !== word(cur) ? ', ' + word(sub) : '');   // 1.29.0: the section and its page, without the wishlist alert count
  b.setAttribute('aria-expanded', open ? 'true' : 'false'); top.classList.toggle('pages-open', !!open);
}
document.addEventListener('keydown', e => {      // Escape folds the list of pages again and goes back to its button
  const top = document.querySelector('header.top');
  if (e.key === 'Escape' && top && top.classList.contains('pages-open') && top.contains(document.activeElement)) { pagesMenu(false); const b = document.getElementById('pages-btn'); if (b) b.focus(); }
  if (e.key === 'Escape' && top && top.classList.contains('more-open') && top.contains(document.activeElement)) { topMoreFold(); const b = document.getElementById('more-btn'); if (b) b.focus(); }
});
function pinLayout() {           // phones: the buttons pinned to the bottom of the screen stack up instead of covering each other
  const r = document.documentElement, tab = conEl('nav-tab'), corner = conEl('corner'), job = conEl('job-badge');
  // 1.26.0: on phones Navigation (was Sections) and Debug share one bar along the bottom of the screen
  if (tab && corner) {
    const home = document.getElementById('sidenav');
    if (r.dataset.narrow === '1' && tab.parentNode !== corner) corner.prepend(tab);
    else if (r.dataset.narrow !== '1' && tab.parentNode === corner && home) home.after(tab);
  }
  // 1.42.0: Display sits at the bottom of the Navigation menu; on a page with no sections (no menu) it stays in the corner
  const disp = conEl('display-btn'), foot = conEl('sn-foot'), inCorner = r.dataset.navempty === '1' && r.dataset.narrow !== '1';
  // 1.57.0: on such a page it goes in the top bar, beside Search, where it covers nothing (in the corner it hid the end of tables)
  const acts = document.querySelector('header.top .top-acts');
  if (disp && foot && acts) { if (inCorner && disp.parentNode !== acts) acts.prepend(disp); else if (!inCorner && disp.parentNode !== foot) foot.append(disp); }
  r.dataset.tabup = '0'; if (tab) tab.style.bottom = '';
  if (r.dataset.narrow !== '1' || !corner) { r.style.removeProperty('--pin-h'); if (job) job.style.bottom = ''; return; }
  const cr = corner.getBoundingClientRect();
  r.style.setProperty('--pin-h', Math.round(cr.height) + 'px');
  if (job) job.style.bottom = Math.round(innerHeight - cr.top + 8) + 'px';
}
// 1.57.0: on a phone, the Navigation and Display bar at the bottom slips away while you scroll down the page and comes back as soon
// as you scroll up (or reach the end), so it does not take that space the whole time. Never while it has the focus.
let BARY = 0;
window.addEventListener('scroll', () => {
  const r = document.documentElement, y = window.scrollY, corner = document.getElementById('corner');
  if (r.dataset.narrow !== '1' || !corner) { if (r.dataset.barhide) delete r.dataset.barhide; BARY = y; return; }
  const end = y + innerHeight >= document.documentElement.scrollHeight - 40;
  if (corner.contains(document.activeElement) || end || y < 80) delete r.dataset.barhide;
  else if (y > BARY + 30) r.dataset.barhide = '1';
  else if (y < BARY - 10) delete r.dataset.barhide;
  if (Math.abs(y - BARY) > 10) BARY = y;
}, { passive: true });
function conLayout() {
  pinLayout();
  const c = conEl('console'), r = document.documentElement; if (!c) return;
  if (c.hidden) { r.style.setProperty('--console-space', '0px'); return; }
  const narrow = r.dataset.narrow === '1', side = window.PlantPrefs.get().navside, navOpen = r.dataset.navopen === '1';
  const navW = navOpen ? (conEl('sidenav') || { offsetWidth: 0 }).offsetWidth : 0, corner = conEl('corner');
  let left = 12, right = 12;
  if (!narrow) {               // bottom left, clear of the side menu and of the Debug and Display buttons
    left = 16 + (side !== 'right' ? navW : 0);
    right = (corner ? corner.offsetWidth : 0) + 32 + (side === 'right' ? navW : 0);
  }
  c.style.left = left + 'px'; c.style.right = right + 'px';
  const body = conEl('con-body');            // tall enough for the newest 3, 4 or 5 changes; older ones are a scroll away
  if (body) {
    const stick = conAtBottom(), rows = [...body.querySelectorAll('.con-row')].slice(-Number(DBG.lines));
    const h = rows.reduce((t, x) => t + x.offsetHeight, 0);
    body.style.height = h ? h + 'px' : '';
    if (stick) body.scrollTop = body.scrollHeight;
  }
  let bottom = 16;             // sit above any button pinned to the bottom of the screen that it would cover
  ['corner', 'nav-tab', 'job-badge'].forEach(id => {
    const e = conEl(id); if (!e || !e.getClientRects().length || getComputedStyle(e).display === 'none' || getComputedStyle(e).visibility === 'hidden') return;
    const b = e.getBoundingClientRect();
    if (b.top < innerHeight / 2 || b.right <= left || b.left >= innerWidth - right) return;
    bottom = Math.max(bottom, Math.round(innerHeight - b.top + 8));
  });
  c.style.bottom = bottom + 'px';
  r.style.setProperty('--console-space', Math.round(c.offsetHeight + bottom + 8) + 'px');
}
function conApply() {
  const c = conEl('console'), on = DBG.console === '1'; if (!c) return;
  c.hidden = !on; document.documentElement.dataset.console = on ? '1' : '0';
  c.style.setProperty('--con-lines', DBG.lines);
  const b = conEl('con-body'); if (b) b.setAttribute('aria-live', DBG.announce === '1' ? 'polite' : 'off');
  clearInterval(CON.timer); CON.timer = null;
  if (on && !CON.on) {          // just turned on: start again from the newest changes
    Object.assign(CON, { started: false, last: 0, unseen: 0, stick: true, paused: false });
    const p = c.querySelector('[data-act=conpause]'); if (p) { p.textContent = 'Pause'; p.setAttribute('aria-pressed', 'false'); }
    const n = conEl('con-new'); if (n) n.hidden = true;
  }
  CON.on = on;
  if (on) { conPoll(); CON.timer = setInterval(conPoll, 3000); }
  conLayout(); fitPanes();
}
function debugDialog() {
  const r = document.documentElement, P = window.PlantPrefs.get();
  modal(html`<form method="dialog" class="dbg"><h2>Debug</h2>
    <p class="muted">Tools for seeing what the app is doing. These choices are remembered in this browser.</p>
    <fieldset class="opt-group"><legend>Audit log console</legend>
      <label class="chk dbg-chk"><input type="checkbox" data-dbg="console" ${DBG.console === '1' ? raw('checked') : ''}>Show the audit log console</label>
      <p class="hint">A small window at the bottom of the screen with the newest changes to any record, checked every 3 seconds. Scroll it to see older ones; the Audit log page has everything.</p>
      <fieldset class="dbg-lines"><legend>Changes it shows before you scroll</legend><div class="opts">${['3', '4', '5'].map(n => html`<label><input type="radio" name="dbg-lines" data-dbg="lines" value="${n}" ${DBG.lines === n ? raw('checked') : ''}><span>${n}</span></label>`)}</div></fieldset>
      <label class="chk dbg-chk"><input type="checkbox" data-dbg="announce" ${DBG.announce === '1' ? raw('checked') : ''}>Let screen readers announce each new change</label>
      <p id="dbg-msg" class="dbg-msg" role="status" aria-live="polite"></p></fieldset>
    <fieldset class="opt-group"><legend>About this browser and the app</legend><dl class="dl">
      <dt>App version</dt><dd>${META && META.version ? META.version : 'unknown'}</dd>
      ${META && META.runs_as ? html`<dt>Runs as</dt><dd>${META.runs_as.text}</dd>` : ''}
      <dt>Location</dt><dd>${placeName()}${META && META.place && META.place.is_home ? ' (home)' : ''}, time zone ${(META && META.place && META.place.tz) || ''}</dd>
      <dt>Window</dt><dd>${innerWidth} by ${innerHeight} pixels</dd>
      <dt>Text size</dt><dd>${P.size}%</dd>
      <dt>Layout</dt><dd>${r.dataset.narrow === '1' ? 'Narrow: one column, buttons at the bottom' : 'Wide'}${P.layout === 'single' ? ', plant pages in one column' : ''}</dd>
      <dt>Changes logged</dt><dd id="dbg-total">Counting</dd></dl></fieldset>
    <fieldset class="opt-group"><legend>Page timings</legend>
      <p class="hint">How long the last pages took to change on this device, in seconds. "Waiting" is the time spent waiting for the plant server; "Drawing" is the time this device took to show the page; "Saved copy" means it showed what it had from before, and checked again just after.</p>
      ${TIMINGS.length ? html`<div class="tbl-wrap"><table class="tbl dbg-times"><caption class="sr">Page timings</caption><thead><tr><th scope="col">Page</th><th scope="col">Total</th><th scope="col">Waiting</th><th scope="col">Drawing</th><th scope="col">Slowest answers (server's own time)</th></tr></thead><tbody>
        ${TIMINGS.slice(0, 20).map(t => html`<tr><th scope="row">${t.page}<br><small class="muted">${when(t.at)}</small></th><td>${(t.total / 1000).toFixed(2)}</td><td>${(t.wait / 1000).toFixed(2)}</td><td>${(t.draw / 1000).toFixed(2)}</td>
          <td>${t.calls.length ? t.calls.slice(0, 3).map((c, i) => html`${i ? raw('<br>') : ''}${c.url.split('?')[0]}: ${(c.ms / 1000).toFixed(2)}${c.server != null ? ` (${(c.server / 1000).toFixed(2)})` : ''}`) : ''}${t.saved ? html`${t.calls.length ? raw('<br>') : ''}<span class="tag">Saved copy: ${t.saved}</span>` : ''}</td></tr>`)}
      </tbody></table></div>
      <div class="row"><button class="btn ghost small" type="button" data-act="dbgtimeclear">Clear the timings</button></div>` : html`<p class="muted">None yet. Open a few pages, then look again.</p>`}</fieldset>
    <div class="row"><button class="btn" value="ok" autofocus>Done</button></div></form>`);
  api('GET', '/api/audit/facets').then(F => { const d = conEl('dbg-total'); if (d) d.textContent = `${F.total.toLocaleString()} since ${F.first ? midDay(F.first.slice(0, 10)) : 'the start'}`; }).catch(() => {});
}
new MutationObserver(() => conLayout()).observe(document.documentElement, { attributes: true, attributeFilter: ['data-navopen', 'data-narrow', 'data-size', 'data-navside', 'data-space'] });
if (window.ResizeObserver) { const ro = new ResizeObserver(() => conLayout()); ['corner', 'nav-tab'].forEach(id => { const e = conEl(id); if (e) ro.observe(e); }); }
document.addEventListener('visibilitychange', () => { if (!document.hidden) conPoll(); });
document.addEventListener('keydown', e => {      // Enter in the Location window's town box searches, rather than closing the window
  if (e.key === 'Enter' && e.target && e.target.name === 'plcq') { e.preventDefault(); placeSearch(); }
});
{ const b = conEl('con-body'); if (b) b.addEventListener('scroll', conScrolled, { passive: true }); }
if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => { navLayout(); conLayout(); fitPanes(); });   // rows grow a little once the fonts arrive
