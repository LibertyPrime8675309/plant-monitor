/* Plant record front end: search by voice (prototype proto/voice-search, rebuilt on 1.42.0). Loads after notify.js (index.html) and
   shares the one scope with the other files. Plain JavaScript, no inline handlers (the server's content policy forbids them).

   A "Search by voice" button beside every search box, added by a MutationObserver, so no page needs changing. Pressing it records
   a few seconds from the microphone (MediaRecorder: Chrome, Edge, Brave, Firefox and Safari) and stops by itself after about
   1.5 seconds of quiet, after 15 seconds, or when pressed again. The recording goes to the app (POST /api/voice), which passes it
   to the speech service on this computer (Whisper, container plant-speech). Nothing goes to Google, Microsoft or anyone else, and
   the recording is not saved. Spoken codes are tidied ("p 36", "pea zero three six" become P-036; "f 2" becomes F-002) and extra
   words dropped ("show me the monstera plants" searches for monstera).

   "Open ..." (or "go to ...", "take me to ...") opens something, in this order:
     1. a plant code opens that plant (a mushroom code opens Mushrooms, searched for that find);
     2. otherwise the name of a page opens the page ("open weather", "open Today", "open grow lights", "open coming inside");
     3. otherwise the one plant whose name matches; if several match, the line says so and asks for one of their codes.
   The line under the button says what was heard. Display settings: show the buttons and say that line aloud in the Read aloud
   voice (the usual), show them without speaking (for screen reader users, whose reader already reads the line), or hide them
   (which also turns the V key off). */
'use strict';
const VS = { rec: null, stream: null, ctx: null, tick: 0, btn: null, box: null, st: null, stAt: 0, busy: false, cancel: false };
const vsCan = () => !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.MediaRecorder);
const vsPref = () => window.PlantPrefs.get().vsearch || '1';
const vsOn = () => vsCan() && vsPref() !== '0';
const VS_QUIET_MS = 1500, VS_MAX_MS = 15000, VS_NOTHING_MS = 7000;
const VS_DIGITS = { zero: '0', oh: '0', o: '0', one: '1', won: '1', two: '2', to: '2', too: '2', three: '3', four: '4', for: '4', five: '5', six: '6', seven: '7', eight: '8', ate: '8', nine: '9' };
function vsClean(said) {
  let t = String(said || '').toLowerCase().replace(/[.,!?;:"“”]+/g, ' ').replace(/\s+/g, ' ').trim();
  let open = false;
  const m = t.match(/^(?:please )?(?:open|go to|take me to|show me|show|find|search for|look for|look up)(?: the| my)? (.+)$/);
  if (m) { open = /^(?:please )?(?:open|go to|take me to)\b/.test(t); t = m[1]; }
  const phrase = t.replace(/ please$/, '').trim();                         // what follows "open", for a page name
  t = t.replace(/^(?:the|my|a) /, '').replace(/ (?:plants?|please)$/, '').trim();
  // a plant or mushroom code: a letter (P or F, as heard) then up to three digits, spoken one by one or as a number
  const w = t.split(' ');
  const head = { p: 'P', pee: 'P', pea: 'P', plant: 'P', f: 'F', ef: 'F', eff: 'F', find: 'F' }[w[0]];
  if (head && w.length > 1) {
    const rest = w.slice(1).filter(x => x !== 'dash' && x !== '-' && x !== 'number').map(x => VS_DIGITS[x] != null ? VS_DIGITS[x] : x).join('').replace(/^-/, '');
    if (/^\d{1,3}$/.test(rest)) t = head + '-' + rest.padStart(3, '0');
  }
  const one = t.match(/^([pf])-?\s?(\d{1,3})$/);
  if (one) t = one[1].toUpperCase() + '-' + one[2].padStart(3, '0');
  return { q: t, open, phrase };
}
// pages by name: every page in the top bar's lists (PAGES_LIST, from SECTIONS), plus the short names people say
const VS_PAGE_NAMES = { home: '#/', 'today': '#/', 'plants': '#/plants', 'plant list': '#/plants', 'my plants': '#/plants', 'add a plant': '#/new',
  'add plant': '#/new', 'new plant': '#/new', 'add several plants': '#/new?several=1', 'rooms': '#/where', 'spots': '#/where', 'winter': '#/winter',
  'cold nights': '#/frost', 'cold night': '#/frost', 'frost': '#/frost', 'frost checklist': '#/frost', 'lights': '#/lights', 'grow light': '#/lights',
  'pots': '#/pots', 'trays': '#/pots', 'places': '#/weather?sec=places', 'homes': '#/weather?sec=places', 'audit': '#/history', 'history': '#/history',
  'backup': '#/backups', 'fertiliser': '#/fertilizer', 'feeding': '#/fertilizer', 'identification': '#/identify', 'review': '#/review',
  'year review': '#/review', 'wish list': '#/wishlist', 'stores': '#/shopping/stores', 'shopping list': '#/shopping/list', 'mushroom': '#/fungi',
  'display': 'display', 'display settings': 'display', 'settings page': '#/settings', 'search': 'search' };
const vsNorm = s => String(s || '').toLowerCase().replace(/[-–—]/g, ' ').replace(/[^a-z0-9 ]/g, '').replace(/\s+/g, ' ').trim()
  .replace(/^(?:the|my) /, '').replace(/ (?:page|screen|tab)$/, '').trim();
function vsPage(words) {
  const n = vsNorm(words); if (!n) return null;
  const list = (typeof PAGES_LIST !== 'undefined' ? PAGES_LIST : []).map(([label, href]) => [vsNorm(label), href]);
  const hit = list.find(([l]) => l === n) || list.find(([l]) => l === n + 's' || l + 's' === n);
  if (hit) return hit[1];
  return VS_PAGE_NAMES[n] || null;
}
function vsGo(href) {
  const d = document.querySelector('dialog[open]'); if (d) d.close();
  if (href === 'display') { displayDialog(); return; }
  if (href === 'search') { searchDialog(); return; }
  go(href);
}
// ---- the speech service's state, for the buttons, the Identify page and Display
async function vsStatus(force) {
  if (!force && VS.st && VS.st.state === 'ready' && Date.now() - VS.stAt < 120000) return VS.st;
  try { const r = await fetch('/api/voice/status', { credentials: 'same-origin' }); VS.st = await r.json(); }
  catch (e) { VS.st = { state: 'off', step: navigator.onLine ? 'Cannot reach the plant server.' : 'You are offline. Search by voice needs the plant server.' }; }
  VS.stAt = Date.now();
  return VS.st;
}
function vsStatusText(st) {
  if (!st) return 'Checking the speech service…';
  if (st.state === 'ready') return `Search by voice is ready: Whisper (${st.model || 'small.en'}) turns what you say into words on this computer.`;
  if (st.state === 'setting up' || st.state === 'starting') return 'The speech service for Search by voice is getting ready: ' + (st.step || 'starting') + (st.total ? ` (${st.done} of ${st.total} MB)` : '') + '. The first start downloads about 465 MB.';
  if (st.state === 'error') return 'The speech service could not start: ' + (st.error || st.step) + '. Restarting the app usually fixes it; see README, "Search by voice".';
  return st.step || 'The speech service is not running. Start it with the updater, or see README, "Search by voice".';
}
async function vsShowStatus(el) {
  if (!el || el.dataset.vsBusy) return;
  el.dataset.vsBusy = '1';
  const st = await vsStatus(true);
  delete el.dataset.vsBusy;
  if (!el.isConnected) return;
  el.textContent = vsStatusText(st);
  if (el.classList.contains('notice')) el.className = 'notice ' + (st.state === 'ready' ? 'ok' : st.state === 'off' || st.state === 'error' ? 'bad' : '');
  if (st.state === 'setting up' || st.state === 'starting') setTimeout(() => vsShowStatus(el), 5000);
}
// ---- the buttons
function vsAdd() {
  if (!vsCan()) return;
  document.querySelectorAll('input[type=search]:not([data-vs])').forEach(inp => {
    inp.dataset.vs = '1';
    const lab = inp.closest('label') || inp;
    const name = (lab.firstChild && lab.firstChild.nodeType === 3 ? lab.firstChild.textContent : 'Search').trim().toLowerCase() || 'search';
    const w = document.createElement('div');
    w.className = 'vs-wrap noprint';
    w.innerHTML = rend(html`<button class="btn ghost vs-btn" type="button" data-act="vsearch" aria-pressed="false"><svg class="vs-mic" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3z"/><path d="M6 11a6 6 0 0 0 12 0M12 17v4M8.5 21h7"/></svg><span class="vs-word">Search by voice</span></button><p class="vs-msg" role="status" aria-live="polite"></p>`);
    w.querySelector('button').setAttribute('aria-label', 'Search by voice: say what to put in the ' + name + ' box');
    lab.after(w);
  });
  const id = document.getElementById('id-st');                 // the Identify page: the speech service's state under the picture checker's
  if (id && !document.getElementById('vs-st')) { id.insertAdjacentHTML('afterend', '<p id="vs-st" class="notice" role="status">Checking the speech service…</p>'); vsShowStatus(document.getElementById('vs-st')); }
  const dv = document.getElementById('vs-dv-st');               // Display settings
  if (dv && !dv.dataset.vsDone) { dv.dataset.vsDone = '1'; vsShowStatus(dv); }
}
function vsSay(msg, bad, speak) {
  const p = VS.btn && VS.btn.parentNode.querySelector('.vs-msg');
  if (p) { p.textContent = msg; p.classList.toggle('bad-text', !!bad); }
  if (speak && vsPref() === '1' && canSpeak()) { try { speechSynthesis.cancel(); readAloudText(msg); } catch (e) { /* the line is on screen either way */ } }     // in the Read aloud voice
}
function vsLook(word) {
  if (!VS.btn) return;
  const on = word !== 'Search by voice';
  VS.btn.setAttribute('aria-pressed', on ? 'true' : 'false'); VS.btn.classList.toggle('vs-on', on);
  VS.btn.querySelector('.vs-word').textContent = word;
}
function vsRelease() {                            // the microphone and the sound meter, off
  clearInterval(VS.tick); VS.tick = 0;
  if (VS.stream) VS.stream.getTracks().forEach(t => t.stop());
  if (VS.ctx) { try { VS.ctx.close(); } catch (e) { /* closed already */ } }
  VS.stream = VS.ctx = null;
}
function vsStop(cancel) {
  VS.cancel = !!cancel;
  if (VS.rec && VS.rec.state !== 'inactive') { try { VS.rec.stop(); } catch (e) { /* stopped already */ } }
  else { vsRelease(); VS.rec = null; vsLook('Search by voice'); }
}
function vsMime() {
  const all = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg;codecs=opus', 'audio/aac'];
  return all.find(t => MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(t)) || '';
}
async function vsStart(btn) {
  if (VS.busy) return;
  if (VS.rec) { const same = VS.btn === btn; vsStop(!same); if (same) return; }
  if (!vsCan()) return;
  stopReading(true);
  VS.btn = btn;
  // the sound meter's audio context is made now, while the press still counts as one (Safari keeps it paused otherwise)
  let ctx = null; try { const AC = window.AudioContext || window.webkitAudioContext; ctx = new AC(); if (ctx.state === 'suspended') ctx.resume(); } catch (e) { ctx = null; }
  const drop = () => { if (ctx) { try { ctx.close(); } catch (e) { /* closed */ } } };
  const wrap = btn.closest('.vs-wrap'), lab = wrap.previousElementSibling;
  VS.box = (lab && (lab.matches('input') ? lab : lab.querySelector('input[type=search]'))) || null;
  const st = await vsStatus(true);                 // asked each time: a moment on this computer, and never out of date
  if (st.state !== 'ready') { drop(); vsSay(vsStatusText(st), true, true); return; }
  let stream;
  try { stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true } }); }
  catch (e) {
    drop();
    const n = e && e.name;
    vsSay(n === 'NotAllowedError' || n === 'SecurityError' ? (window.isSecureContext ? 'The browser is not allowed to use the microphone. Allow it in the site settings (the icon at the left of the address bar), then try again.'
      : 'The browser only lets a page use the microphone over a secure connection. Open Plant record through its https Tailscale address (or http://localhost on this computer).')
      : n === 'NotFoundError' || n === 'OverconstrainedError' ? 'No microphone was found. Check that one is plugged in and turned on.'
      : 'The microphone could not be started: ' + (e && e.message || n) + '.', true, true);
    return;
  }
  const mime = vsMime(), rec = mime ? new MediaRecorder(stream, { mimeType: mime, audioBitsPerSecond: 32000 }) : new MediaRecorder(stream);
  const chunks = [], t0 = Date.now();
  let heard = 0, quietSince = 0, floor = 0, n = 0;
  VS.rec = rec; VS.stream = stream; VS.cancel = false;
  rec.ondataavailable = e => { if (e.data && e.data.size) chunks.push(e.data); };
  rec.onstop = () => {
    vsRelease(); VS.rec = null; vsLook('Search by voice');
    if (VS.cancel) { VS.cancel = false; return; }
    if (heard < 2) { vsSay('I did not hear anything. Press the button and try again.', true, true); return; }
    vsSend(new Blob(chunks, { type: rec.mimeType || mime || 'audio/webm' }));
  };
  // the sound meter: speech is anything well above the room's own noise; about 1.5 seconds of quiet after it ends the recording
  try {
    if (!ctx) throw new Error('no audio context');
    const src = ctx.createMediaStreamSource(stream), an = ctx.createAnalyser();
    an.fftSize = 1024; src.connect(an); VS.ctx = ctx;
    const buf = new Float32Array(an.fftSize);
    VS.tick = setInterval(() => {
      if (ctx.state !== 'running') {               // the meter never started: record 6 seconds and send them
        if (Date.now() - t0 > 1000 && heard < 2) heard = 2;
        if (Date.now() - t0 >= 6000) vsStop(false);
        return;
      }
      an.getFloatTimeDomainData(buf);
      let s = 0; for (let i = 0; i < buf.length; i++) s += buf[i] * buf[i];
      const rms = Math.sqrt(s / buf.length), ms = Date.now() - t0;
      if (++n <= 3) { floor = Math.max(floor, rms); return; }                 // the first 0.3 seconds: how loud the room is
      const loud = rms > Math.max(0.015, floor * 3);
      if (loud) { heard++; quietSince = 0; } else if (heard >= 2 && !quietSince) quietSince = Date.now();
      if ((heard >= 2 && quietSince && Date.now() - quietSince >= VS_QUIET_MS) || ms >= VS_MAX_MS || (heard < 2 && ms >= VS_NOTHING_MS)) vsStop(false);
    }, 100);
  } catch (e) { drop(); VS.tick = setTimeout(() => vsStop(false), 6000); heard = 2; }   // no sound meter: stop after 6 seconds and send
  rec.start(250);
  vsLook('Listening. Press to stop');
  vsSay('Listening. Say a plant, a code, or "open" and a page. It stops by itself when you pause.');
}
async function vsSend(blob) {
  VS.busy = true; vsLook('Working…');
  vsSay('Working out what you said…');
  const fd = new FormData(), ext = /mp4|aac/.test(blob.type) ? 'm4a' : /ogg/.test(blob.type) ? 'ogg' : 'webm';
  fd.append('audio', blob, 'voice.' + ext);
  let r, j;
  try {
    let who = 'Unknown'; try { who = cleanName(viaTS() ? ME().name : getName()) || 'Unknown'; } catch (e) { /* no name yet */ }
    r = await fetch('/api/voice', { method: 'POST', body: fd, headers: { 'X-Editor': who }, credentials: 'same-origin' });
    j = await r.json().catch(() => ({}));
  } catch (e) {
    VS.busy = false; vsLook('Search by voice');
    vsSay(navigator.onLine ? 'Cannot reach the plant server. Check that the container is running.' : 'You are offline. Search by voice needs the plant server.', true, true);
    return;
  }
  VS.busy = false; vsLook('Search by voice');
  if (!r.ok) { if (r.status === 503) VS.st = null; vsSay(j.error || `Search by voice did not work (${r.status}).`, true, true); return; }
  vsFinish(j.text || '');
}
function vsFungiFind(code) {                     // a mushroom code: Mushrooms, searched for that find
  let n = 0; const t = setInterval(() => { const b = document.querySelector('input[data-f=muq]'); if (b || ++n > 30) { clearInterval(t); if (b) { b.value = code; b.dispatchEvent(new Event('input', { bubbles: true })); } } }, 100);
}
function vsOpen(q, phrase) {                     // the rule in the note at the top: a code, then a page, then one plant by name
  if (/^P-\d{3}$/.test(q)) {
    if (ALL.length && !ALL.some(p => p.code === q)) return 'No plant has the code ' + q + '.';
    vsGo('#/plant/' + enc(q)); return true;
  }
  if (/^F-\d{3}$/.test(q)) { vsGo('#/fungi'); vsFungiFind(q); return true; }
  const pg = vsPage(phrase) || vsPage(q); if (pg) { vsGo(pg); return true; }
  if (!ALL.length) return null;
  const s = q.toLowerCase();
  const hits = ALL.filter(p => !isArch(p) && [p.code, p.common_name, p.scientific_name, p.aliases].join(' ').toLowerCase().includes(s));
  if (hits.length === 1) { vsGo('#/plant/' + enc(hits[0].code)); return true; }
  if (hits.length > 1) return hits.length + ' plants match "' + q + '". Say "open" and one of their codes, for example ' + hits.slice(0, 2).map(p => p.code).join(' or ') + '.';
  return 'No page or plant is called "' + q + '".';
}
function vsFinish(said) {
  const { q, open, phrase } = vsClean(said), box = VS.box;
  if (!q) { vsSay('I did not catch any words. Press the button and try again.', true, true); return; }
  const heard = 'Heard "' + said.trim() + '". ';
  if (open) {
    const r = vsOpen(q, phrase);
    if (r === true) return;                     // the page or plant opens; nothing left to say
    if (typeof r === 'string') {                // could not open one thing: still search, and say why
      if (box) { box.value = q; box.dispatchEvent(new Event('input', { bubbles: true })); }
      vsSay(heard + r, false, true); return;
    }
  }
  if (!box) { vsSay(heard + 'There is no search box here.', true, true); return; }
  box.value = q;
  box.dispatchEvent(new Event('input', { bubbles: true }));
  let msg = heard + 'Searching for ' + q + '.';
  if (box.dataset.f === 'q' && /^#\/(plants|plant\/)/.test(location.hash) && ALL.length) {
    const n = filteredPlants().length;
    msg = heard + (n === 0 ? 'No plants match ' + q + '.' : n === 1 ? 'One plant matches.' : n + ' plants match.');
  }
  vsSay(msg, false, true);
}
Object.assign(acts, { vsearch(el) { vsStart(el); } });
window.PlantVoice = { clean: vsClean, page: vsPage, finish: t => vsFinish(t) };          // for dev/test/voice_check.py
new MutationObserver(vsAdd).observe(document.getElementById('app'), { childList: true, subtree: true });
new MutationObserver(vsAdd).observe(dlg, { childList: true, subtree: true });
vsAdd();
window.addEventListener('hashchange', () => { if (VS.rec) vsStop(true); });
document.addEventListener('keydown', e => {          // V: search by voice (the same rules as the other shortcuts; off with the buttons)
  if (e.key !== 'v' && e.key !== 'V') return;
  if (e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey || window.PlantPrefs.get().keys !== '1' || !vsOn()) return;
  const t = e.target; if (t.closest && t.closest('input,textarea,select,[contenteditable="true"],dialog[open]')) return;
  const d = document.getElementById('pn-filters'); if (d) d.open = true;
  const b = [...document.querySelectorAll('#app .vs-btn')].find(x => x.offsetParent);
  e.preventDefault();
  if (b) { b.focus(); vsStart(b); return; }
  searchDialog();                                    // no search box on this page: the Search window, listening
  setTimeout(() => { const s = dlg.querySelector('.vs-btn'); if (s) { s.focus(); vsStart(s); } }, 0);
});
