/* Plant record front end: push notifications (1.33.0) and the search window (1.33.0). One of the files loaded in order by
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
        <button class="btn ghost small" type="button" data-act="pushrm" data-id="${x.id}">Remove</button></li>`)}</ul>` : html`<p class="muted">None yet.</p>`}</fieldset>
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
const PAGES_LIST = [['Today', '#/today'], ['All plants', '#/'], ['Groups', '#/groups'], ['Add plants', '#/new'], ['Mushrooms', '#/fungi'], ['Rooms and spots', '#/where'], ['Photos', '#/photos'],
  ['Labels', '#/labels'], ['Winter plan', '#/winter'], ['Cold-night checklist', '#/frost'], ['Getting plants ready to come inside', '#/inside'], ['Back outside', '#/outside'], ['Fertilizer', '#/fertilizer'],
  ['Grow lights', '#/lights'], ['Pots and trays', '#/pots'], ['Weather', '#/weather'], ['Homes and places', '#/weather?sec=places'], ['Identify', '#/identify'], ['Library', '#/library'], ['Around home', '#/around'],
  ['Wishlist', '#/wishlist'], ['Shopping', '#/shopping'], ['Stores', '#/shopping/stores'], ['Settings', '#/settings'], ['Offline use', '#/offline'], ['Backups', '#/backups'], ['Audit log', '#/history'], ['Needs your decision', '#/decisions']];
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
  const pages = q.length >= 2 ? PAGES_LIST.filter(([n]) => n.toLowerCase().includes(q.toLowerCase())).map(([n, h]) => ({ title: n, sub: 'page', href: h })) : [];
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
