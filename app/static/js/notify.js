/* Plant record front end: push notifications (1.33.0), the search window (1.33.0) and dictation (1.34.0). One of the files loaded in order by
   index.html; they share one scope. Plain JavaScript, no inline handlers (the server's content policy forbids them). */
'use strict';

// ---------- 1.33.0: push notifications ----------
function pushSupported() { return 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window; }
function pushDeviceName() {
  const ua = navigator.userAgent, os = /iPhone|iPad/.test(ua) ? (/iPad/.test(ua) || (navigator.maxTouchPoints > 1 && /Mac/.test(ua)) ? 'iPad' : 'iPhone') : /Android/.test(ua) ? 'Android phone' : /Windows/.test(ua) ? 'Windows PC' : /Mac/.test(ua) ? 'Mac' : 'device';
  const br = /Edg\//.test(ua) ? 'Edge' : /Brave/.test(ua) ? 'Brave' : /Chrome\//.test(ua) ? 'Chrome' : /Firefox\//.test(ua) ? 'Firefox' : /Safari\//.test(ua) ? 'Safari' : 'browser';
  return `${os}, ${br}`;
}
function b64ToBytes(s) { const b = atob(s.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - s.length % 4) % 4)); return Uint8Array.from(b, c => c.charCodeAt(0)); }
async function swReady(ms) {         // the service worker, or null if none is registered here within a moment (ready would wait for ever)
  const reg = await navigator.serviceWorker.getRegistration();
  if (!reg) return null;
  return Promise.race([navigator.serviceWorker.ready, new Promise(r => setTimeout(() => r(null), ms))]);
}
async function pushCurrent() {
  if (!pushSupported()) return null;
  try { const reg = await swReady(2000); return reg ? await reg.pushManager.getSubscription() : null; } catch (e) { return null; }
}
async function pushTurnOn(key) {
  if (!pushSupported()) throw new Error('This browser cannot show notifications from a web page. On an iPhone or iPad, add the app to the Home Screen first (Share, then Add to Home Screen), then open it from there.');
  const perm = await Notification.requestPermission();
  if (perm !== 'granted') throw new Error(perm === 'denied' ? 'Notifications are blocked for this site in the browser\'s settings. Allow them there, then try again.' : 'Notifications were not allowed.');
  const reg = await swReady(5000);
  if (!reg) throw new Error('The app\'s service worker is not running in this browser (it is what receives the messages). Reload the page and try again.');
  const sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64ToBytes(key) });
  const j = sub.toJSON();
  await api('POST', '/api/push/subscribe', { endpoint: j.endpoint, keys: j.keys, device: pushDeviceName() });
  return sub;
}
async function pushTurnOff() {
  const sub = await pushCurrent(); if (!sub) return;
  try { await api('DELETE', '/api/push/subscribe', { endpoint: sub.endpoint }); } catch (e) { /* the server may already have dropped it */ }
  await sub.unsubscribe();
}
async function notifyDialog() {
  const d = await api('GET', '/api/push?_=' + Date.now()), cur = await pushCurrent(), ok = pushSupported();
  const here = cur && d.devices.length ? true : !!cur;
  const box = html`<form method="dialog" class="ntf-dlg"><h2>Notifications</h2>
    <p class="muted">Messages on this device's lock screen or desktop, even when the app is closed: cold nights, Shopping alerts, what is due, and requests from Claude. They go through the browser's own push service; nothing else sees them.</p>
    <fieldset class="opt-group"><legend>This device</legend>
      ${!ok ? html`<p class="notice">This browser cannot receive notifications from a web page.${/iPhone|iPad/.test(navigator.userAgent) ? ' On an iPhone or iPad: Share, then Add to Home Screen, and open the app from there.' : ''}</p>`
        : here ? html`<p><span aria-hidden="true">✓</span> Turned on here (${pushDeviceName()}).</p><div class="row"><button class="btn ghost" type="button" data-act="pushtest">Send a test</button><button class="btn ghost" type="button" data-act="pushoff">Turn off on this device</button></div>`
        : html`<div class="row"><button class="btn" type="button" data-act="pushon">Turn on for this device</button></div>${Notification.permission === 'denied' ? html`<p class="hint">The browser is blocking notifications for this site. Allow them in its site settings first.</p>` : ''}`}
      ${!d.https ? html`<p class="hint">Notifications need the app's Tailscale address (https), or this computer itself (localhost).</p>` : ''}
      <p id="ntf-msg" role="status" aria-live="polite"></p></fieldset>
    <fieldset class="opt-group"><legend>What reaches you (on every device you turned on)</legend>
      ${d.kinds.map(k => html`<label class="chk"><input type="checkbox" data-f="pushkind" data-kind="${k.key}" ${k.on ? raw('checked') : ''}> ${k.label}<br><small class="hint">${k.help}</small></label>`)}
      <p class="hint">These are your own choices, saved for your sign-in. Cold nights and what is due are for the home you start on.</p></fieldset>
    <fieldset class="opt-group"><legend>Your devices (${d.devices.length})</legend>
      ${d.devices.length ? html`<ul class="ntf-list">${d.devices.map(x => html`<li>${x.device || 'A device'} <small class="muted">since ${when(x.created_at)}${x.last_ok ? `, last message ${when(x.last_ok)}` : ''}${x.fails ? `, ${x.fails} failed` : ''}</small>
        <button class="btn ghost small" type="button" data-act="pushrm" data-id="${x.id}" aria-label="Remove the device ${x.device}">Remove</button></li>`)}</ul>` : html`<p class="muted">None yet.</p>`}</fieldset>
    <div class="row"><button class="btn" value="ok" autofocus>Done</button></div></form>`;
  const open = document.querySelector('dialog[open] form.ntf-dlg');
  if (open) { open.outerHTML = rend(box); return; }
  await modal(box);
}
Object.assign(acts, {
  notify() { notifyDialog(); },
  async pushon(el) {
    const m = document.getElementById('ntf-msg'); el.disabled = true;
    try { const d = await api('GET', '/api/push'); await pushTurnOn(d.key); toast('Notifications are on for this device'); await notifyDialog(); }
    catch (e) { if (m) m.textContent = e.message; el.disabled = false; }
  },
  async pushoff() { await guard(async () => { await pushTurnOff(); toast('Turned off on this device'); await notifyDialog(); }); },
  async pushtest(el) {
    const m = document.getElementById('ntf-msg'); el.disabled = true;
    try { const r = await api('POST', '/api/push/test'); if (m) m.textContent = r.sent ? 'Sent. It should appear in a moment.' : 'Nothing was sent: this device is not on the list. Turn it on again.'; }
    catch (e) { if (m) m.textContent = e.message; }
    el.disabled = false;
  },
  async pushrm(el) { await guard(async () => { await api('DELETE', '/api/push/devices/' + enc(el.dataset.id)); toast('Removed'); await notifyDialog(); }); },
});
document.addEventListener('change', e => {
  const el = e.target; if (!el.dataset || el.dataset.f !== 'pushkind') return;
  api('PUT', '/api/me/prefs', { ['push.' + el.dataset.kind]: el.checked ? '1' : '0' }).then(() => toast('Saved')).catch(err => toast(err.message, true));
});

// ---------- 1.33.0: search everywhere (the magnifier in the top bar, or the / key away from the Plants page: see the shortcuts in ui.js) ----------
// 1.36.0: the pages are the sections' own lists (core.js SECTIONS), so a page added there is found here too, plus the pages inside Shopping
// 1.47.0: worked out when searching, not when this file loads, so pages that feature modules register later (Turn the pots, the
// health walk-through) are found too
const pagesList = () => {
  const L = SECTIONS.flatMap(sec => sec[2].map(([k, label, href]) => [label, href])).concat([['Shopping list for a store visit', '#/shopping/list'], ['Stores', '#/shopping/stores']]);
  for (const [key, p] of Object.entries(FEAT.pages)) { const href = p.href || '#/' + key; if (p.label && !L.some(x => x[1] === href)) L.push([p.label, href]); }
  L.push(['Plant-sitter sheet', '/sitter.html'], ['Large-print care cards', '/card.html']);     // 1.52.1: the pages of their own, reached from Today and a plant's page
  return L;
};
let SRCH = { t: 0, q: '', seq: 0 };
function searchDialog() {
  modal(html`<form method="dialog" class="srch-dlg" role="search"><h2>Search</h2>
    <label class="f">Plants, pages, groups, stores, finds and the library<input type="search" id="srch-q" autocomplete="off" placeholder="A name, a code, a room, a page" aria-controls="srch-res" aria-describedby="srch-help"></label>
    <p class="hint" id="srch-help">Type at least two letters. Use the arrow keys to move through the results, and Enter to open one.</p>
    <div id="srch-res" aria-live="polite"></div>
    <div class="row"><button class="btn ghost" value="cancel">Close</button></div></form>`);
  const q = document.getElementById('srch-q'); if (q) { q.focus(); q.addEventListener('input', () => { clearTimeout(SRCH.t); SRCH.t = setTimeout(() => searchRun(q.value), 250); }); }
}
async function searchRun(q) {
  const box = document.getElementById('srch-res'); if (!box) return;
  q = q.trim(); SRCH.q = q; const seq = ++SRCH.seq;
  const pages = q.length >= 2 ? pagesList().filter(([n]) => n.toLowerCase().includes(q.toLowerCase())).map(([n, h]) => ({ title: n, sub: 'page', href: h })) : [];
  let groups = [];
  if (q.length >= 2) { try { groups = (await api('GET', '/api/search?q=' + enc(q))).groups; } catch (e) { groups = [{ kind: 'err', word: 'Could not search', items: [{ title: e.message, sub: '', href: '' }] }]; } }
  if (seq !== SRCH.seq || !document.getElementById('srch-res')) return;
  const all = (pages.length ? [{ kind: 'pages', word: 'Pages', items: pages }] : []).concat(groups);
  if (!all.length) { box.innerHTML = rend(q.length >= 2 ? html`<p class="muted">Nothing matches "${q}".</p>` : ''); return; }
  box.innerHTML = rend(html`${all.map(g => html`<h3 class="srch-h">${g.word}</h3><ul class="srch-list">${g.items.map(it => html`<li>${it.href ? html`<a href="${it.href}" data-act="srchgo">${it.title}</a>` : it.title}${it.sub ? html` <small class="muted">${it.sub}</small>` : ''}</li>`)}</ul>`)}`);
}
Object.assign(acts, {
  search() { searchDialog(); },
  srchgo(el, e) { if (e) e.preventDefault(); const d = document.querySelector('dialog[open]'); if (d) d.close(); go(el.getAttribute('href')); },
});
document.addEventListener('keydown', e => {
  const t = e.target, typing = t && (/^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName) || t.isContentEditable);
  const d = document.querySelector('dialog[open] form.srch-dlg'); if (!d) return;
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
    const links = [...d.querySelectorAll('.srch-list a')]; if (!links.length) return;
    e.preventDefault();
    const i = links.indexOf(document.activeElement);
    const n = e.key === 'ArrowDown' ? (i < 0 ? 0 : Math.min(links.length - 1, i + 1)) : (i <= 0 ? -1 : i - 1);
    if (n < 0) document.getElementById('srch-q').focus(); else links[n].focus();
  }
});

// ---------- 1.34.0: speak a note. A Speak button after every text box that takes several lines; what you say is written into it ----------
// 1.44.0: what you say goes to the speech service on this computer (Whisper, as Search by voice does; voice.js), not to Google or
// Microsoft. It records until you press the button again, pause for about 3 seconds, or reach a minute, then adds the words to the box.
// Every browser with a microphone recorder has it (Chrome, Edge, Brave, Firefox, Safari).
const DICT_QUIET_MS = 3000, DICT_MAX_MS = 60000, DICT_NOTHING_MS = 10000;
let DICT = null;                                  // the recording now: { rec, stream, ctx, tick, ta, btn, base, cancel }
function addSpeakButtons(root) {
  if (!vsCan()) return;
  (root || document).querySelectorAll('textarea:not([data-speak])').forEach(ta => {
    ta.dataset.speak = '1';
    if (ta.readOnly || ta.disabled || ta.closest('[hidden]')) return;
    const lab = ta.closest('label'), name = (lab ? lab.childNodes[0].textContent : ta.getAttribute('aria-label') || 'this box').trim();
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'btn small ghost spk-btn noprint'; b.dataset.act = 'dictate'; b.setAttribute('aria-pressed', 'false');
    b.setAttribute('aria-label', `Speak into ${name}`); b.title = 'Dictate: what you say is added to the box (turned into words on this computer)'; b.textContent = 'Speak';
    (lab || ta).insertAdjacentElement('afterend', b);
    b.spkTarget = ta;
  });
}
function dictLook(btn, word, on) { btn.textContent = word; btn.setAttribute('aria-pressed', on ? 'true' : 'false'); btn.classList.toggle('spk-on', !!on); }
function dictRelease(d) {
  clearInterval(d.tick); clearTimeout(d.tick);
  if (d.stream) d.stream.getTracks().forEach(t => t.stop());
  if (d.ctx) { try { d.ctx.close(); } catch (e) { /* closed */ } }
  d.stream = d.ctx = null;
}
function dictateStop(cancel) {
  if (!DICT) return;
  const d = DICT; d.cancel = !!cancel;
  if (d.rec && d.rec.state !== 'inactive') { try { d.rec.stop(); } catch (e) { /* stopped already */ } }
  else { dictRelease(d); DICT = null; dictLook(d.btn, 'Speak', false); }
}
const dictCap = t => t.charAt(0).toUpperCase() + t.slice(1);            // a new sentence starts with a capital letter
const dictJoin = (a, b) => { a = (a || '').replace(/\s+$/, ''); b = (b || '').trim(); if (!b) return a; if (!a) return dictCap(b); return a + (/[.!?]$/.test(a) ? ' ' + dictCap(b) : /[,;:]$/.test(a) ? ' ' + b : '. ' + dictCap(b)); };
async function dictateStart(btn) {
  const ta = btn.spkTarget; if (!ta || !vsCan()) return;
  if (DICT && DICT.busy) return;
  if (DICT) dictateStop(true);
  if (typeof VS !== 'undefined' && VS.rec) vsStop(true);            // one microphone at a time
  stopReading(true);
  let ctx = null; try { const AC = window.AudioContext || window.webkitAudioContext; ctx = new AC(); if (ctx.state === 'suspended') ctx.resume(); } catch (e) { ctx = null; }
  const drop = () => { if (ctx) { try { ctx.close(); } catch (e) { /* closed */ } } };
  const st = await vsStatus(true);
  if (st.state !== 'ready') { drop(); toast(vsStatusText(st), true); return; }
  let stream;
  try { stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true } }); }
  catch (e) { drop(); toast(micErrText(e), true); return; }
  const mime = vsMime(), rec = mime ? new MediaRecorder(stream, { mimeType: mime, audioBitsPerSecond: 32000 }) : new MediaRecorder(stream);
  const chunks = [], t0 = Date.now(), d = { rec, stream, ctx: null, tick: 0, ta, btn, base: ta.value, cancel: false, busy: false };
  let heard = 0, quietSince = 0, floor = 0, n = 0;
  DICT = d;
  rec.ondataavailable = e => { if (e.data && e.data.size) chunks.push(e.data); };
  rec.onstop = () => {
    dictRelease(d);
    if (d.cancel) { if (DICT === d) DICT = null; dictLook(btn, 'Speak', false); return; }
    if (heard < 2) { if (DICT === d) DICT = null; dictLook(btn, 'Speak', false); toast('I did not hear anything. Press Speak and try again.', true); return; }
    dictSend(d, new Blob(chunks, { type: rec.mimeType || mime || 'audio/webm' }));
  };
  try {                                           // the sound meter: speech is anything well above the room's own noise
    if (!ctx) throw new Error('no audio context');
    const src = ctx.createMediaStreamSource(stream), an = ctx.createAnalyser();
    an.fftSize = 1024; src.connect(an); d.ctx = ctx;
    const buf = new Float32Array(an.fftSize);
    d.tick = setInterval(() => {
      const ms = Date.now() - t0;
      if (ctx.state !== 'running') { if (ms > 1000) heard = Math.max(heard, 2); if (ms >= DICT_MAX_MS) dictateStop(false); return; }    // no meter: until pressed, or a minute
      an.getFloatTimeDomainData(buf);
      let s = 0; for (let i = 0; i < buf.length; i++) s += buf[i] * buf[i];
      const rms = Math.sqrt(s / buf.length);
      if (++n <= 3) { floor = Math.max(floor, rms); return; }
      const loud = rms > Math.max(0.015, floor * 3);
      if (loud) { heard++; quietSince = 0; } else if (heard >= 2 && !quietSince) quietSince = Date.now();
      if ((heard >= 2 && quietSince && Date.now() - quietSince >= DICT_QUIET_MS) || ms >= DICT_MAX_MS || (heard < 2 && ms >= DICT_NOTHING_MS)) dictateStop(false);
    }, 100);
  } catch (e) { drop(); heard = 2; d.tick = setTimeout(() => dictateStop(false), DICT_MAX_MS); }
  rec.start(250);
  dictLook(btn, 'Listening… press to stop', true);
}
async function dictSend(d, blob) {
  d.busy = true; dictLook(d.btn, 'Working out what you said…', false); d.btn.setAttribute('aria-busy', 'true');
  const fd = new FormData(), ext = /mp4|aac/.test(blob.type) ? 'm4a' : /ogg/.test(blob.type) ? 'ogg' : 'webm';
  fd.append('audio', blob, 'note.' + ext); fd.append('mode', 'note');
  let r, j;
  try {
    let who = 'Unknown'; try { who = cleanName(viaTS() ? ME().name : getName()) || 'Unknown'; } catch (e) { /* no name yet */ }
    r = await fetch('/api/voice', { method: 'POST', body: fd, headers: { 'X-Editor': who }, credentials: 'same-origin' });
    j = await r.json().catch(() => ({}));
  } catch (e) { j = { error: navigator.onLine ? 'Cannot reach the plant server. Check that the container is running.' : 'You are offline. Speak needs the plant server.' }; r = { ok: false }; }
  d.busy = false; d.btn.removeAttribute('aria-busy'); if (DICT === d) DICT = null; dictLook(d.btn, 'Speak', false);
  if (!r.ok) { toast(j.error || `Speak did not work (${r.status}).`, true); return; }
  const said = (j.text || '').trim();
  if (!said) { toast('I could not make out any words. Press Speak and try again.', true); return; }
  const ta = d.ta; if (!ta.isConnected) return;
  ta.value = dictJoin(ta.value, said);
  ta.dispatchEvent(new Event('input', { bubbles: true })); ta.dispatchEvent(new Event('change', { bubbles: true }));
  toast('Added: ' + said);
  ta.focus(); try { ta.setSelectionRange(ta.value.length, ta.value.length); } catch (e) { /* not a text box */ }
}
Object.assign(acts, {
  dictate(el) { if (DICT && DICT.btn === el) { if (!DICT.busy) dictateStop(false); } else dictateStart(el); },
});
document.addEventListener('DOMContentLoaded', () => {        // voice.js (vsCan, vsStatus, vsMime) loads after this file
  if (!vsCan()) return;
  new MutationObserver(muts => { for (const m of muts) for (const n of m.addedNodes) if (n.nodeType === 1 && (n.tagName === 'TEXTAREA' || n.querySelector('textarea'))) addSpeakButtons(n.parentNode || n); }).observe(document.body, { childList: true, subtree: true });
  addSpeakButtons();
  window.addEventListener('hashchange', () => dictateStop(true));
  // the button shows while the box or the button itself has the focus (and while listening), so forms do not fill up with buttons
  const btnOf = ta => { const n = (ta.closest('label') || ta).nextElementSibling; return n && n.classList.contains('spk-btn') ? n : null; };
  document.addEventListener('focusin', e => {
    const t = e.target; const b = t.tagName === 'TEXTAREA' ? btnOf(t) : t.classList && t.classList.contains('spk-btn') ? t : null;
    if (b) b.classList.add('spk-show');
  });
  document.addEventListener('focusout', e => {
    const t = e.target; const b = t.tagName === 'TEXTAREA' ? btnOf(t) : t.classList && t.classList.contains('spk-btn') ? t : null;
    if (b) setTimeout(() => { const f = document.activeElement; if (f !== b && f !== b.spkTarget && !(DICT && DICT.btn === b)) b.classList.remove('spk-show'); }, 150);
  });
});
