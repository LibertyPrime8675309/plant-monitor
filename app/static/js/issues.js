/* Plant record front end: the Issue tracker (1.58.0; plantdb/issues.py). One of the files loaded in order by index.html
   (js/manifest.json); they share one scope. Plain JavaScript, no inline handlers (the server's content policy forbids them).

   - "Report a problem" is at the foot of Navigation on every page (index.html; on a wide page with no sections, where there is no
     Navigation, pinLayout() in ui.js puts it in the top bar beside Display) and on a card on Settings. It opens one window: notes,
     pictures, this device's name, and a folded list of everything that is sent with it, so nothing is sent that cannot be read first.
   - The Issue tracker page (#/issues, in the Settings row) is the owner's: the reports as cards, with a status, a fixed-in version,
     the owner's notes, and "Copy for Claude".
   - Today tells the owner once about reports from other people that have not been looked at.
   Everyone may send a report, people who can only view included; sent offline it waits on the device like other changes. */
'use strict';

// ---------- what a report carries ----------
// The last few messages the app showed as errors, and script errors nobody saw: often the whole answer to "what went wrong".
const ISS_ERRS = [];
function issNoteError(msg, kind) {
  ISS_ERRS.unshift(`${new Date().toISOString().slice(11, 19)} UTC, ${location.hash || '#/'}: ${kind ? kind + ': ' : ''}${String(msg).slice(0, 240)}`);
  ISS_ERRS.length = Math.min(ISS_ERRS.length, 8);
}
window.addEventListener('error', e => issNoteError(e.message + (e.filename ? ` (${String(e.filename).split('/').pop()}:${e.lineno})` : ''), 'script'));
window.addEventListener('unhandledrejection', e => issNoteError((e.reason && e.reason.message) || e.reason, 'script'));

const ISS_SKIP = /^plantdb\.(display|editor|prefetch|timings|pending|shoplist|rlshown)$/;       // Display is listed by itself; the rest are names, saved answers or lists, not settings
function issSettings() {
  const out = {}, P = window.PlantPrefs.get(), D = window.PlantPrefs.defaults;
  Object.keys(P).forEach(k => { out['Display: ' + k] = P[k] + (D[k] !== P[k] ? ' (changed)' : ''); });
  try {
    Object.keys(localStorage).filter(k => k.startsWith('plantdb.') && !ISS_SKIP.test(k)).sort().forEach(k => { out[k.slice(8)] = String(localStorage.getItem(k)).slice(0, 300); });
  } catch (e) { out['Other settings'] = 'This browser does not let the app read them'; }
  return out;
}
async function issInfo() {
  const r = document.documentElement, n = navigator, mm = q => { try { return matchMedia(q).matches; } catch (e) { return false; } };
  const I = {
    'Kind of device': offGuessDevice(),
    'Browser says': n.userAgent,
    'System': (n.userAgentData && n.userAgentData.platform) || n.platform || '',
    'Opened as': mm('(display-mode: standalone)') || n.standalone === true ? 'An app on the Home Screen' : 'A browser tab',
    'Connected': `${viaTS() ? 'Through Tailscale' : 'On this computer or the home network'}, at ${location.host}`,
    'Screen': `${screen.width} by ${screen.height}, ${window.devicePixelRatio || 1} pixels per point`,
    'Window': `${innerWidth} by ${innerHeight}${mm('(orientation: portrait)') ? ', upright' : ', sideways'}`,
    'Text size': r.dataset.size + '%',
    'Layout': `${r.dataset.narrow === '1' ? 'Narrow (phone layout)' : 'Wide'}${r.dataset.touch === '1' ? ', touch' : ''}${r.dataset.navempty === '1' ? ', page with no sections' : ''}`,
    'Colours': `${r.dataset.theme || 'follows the device' + (mm('(prefers-color-scheme: dark)') ? ' (dark)' : ' (light)')}, contrast ${r.dataset.contrast}${mm('(forced-colors: active)') ? ', system high contrast on' : ''}`,
    'Language and time zone': `${n.language || ''}, ${(Intl.DateTimeFormat().resolvedOptions() || {}).timeZone || ''}`,
    'Home in use': placeName(),
    'Online': `${n.onLine ? 'The device says yes' : 'The device says no'}; plant server ${OFF.reach === false ? 'not reached' : 'reached'}${OFF.saved ? '; this page shows a copy saved ' + OFF.saved : ''}`,
    'Changes waiting to be sent': `${OFF.n || 0}${OFF.failed ? `, ${OFF.failed} refused` : ''}${OFF.conflicts ? `, ${OFF.conflicts} to decide` : ''}`,
    'Version the server said': (META && META.version) || '',
  };
  if (n.connection && n.connection.effectiveType) I.Network = n.connection.effectiveType + (n.connection.saveData ? ', data saver on' : '');
  try { I['Saved app copies'] = 'caches' in window ? ((await caches.keys()).filter(k => k.startsWith('plantdb-shell-')).map(k => k.slice(14)).join(', ') || 'none') : 'not available'; } catch (e) { I['Saved app copies'] = 'not available'; }
  try { I['Works offline here'] = 'serviceWorker' in n ? (n.serviceWorker.controller ? 'Yes' : 'Not yet (no saved app is in charge of this page)') : 'No: this browser or address does not allow it'; } catch (e) { /* leave it out */ }
  try { if (n.storage && n.storage.estimate) { const s = await n.storage.estimate(); I['Storage used by the app'] = `${Math.round((s.usage || 0) / 1e6)} MB of ${Math.round((s.quota || 0) / 1e6)} MB allowed`; } } catch (e) { /* leave it out */ }
  if (TIMINGS.length) I['Last pages opened'] = TIMINGS.slice(0, 3).map(t => `${t.page} ${(t.total / 1000).toFixed(1)} s (waiting ${(t.wait / 1000).toFixed(1)} s)`).join('; ');
  if (ISS_ERRS.length) I['Last errors shown'] = ISS_ERRS.join('\n');
  return I;
}
// the page a report is about, and the section of it that is on screen
function issWhere() {
  const h1 = document.querySelector('#app h1'), cur = document.querySelector('#sn-list a[aria-current]');
  const sec = cur && !/^Top of the page$/.test(cur.textContent.trim()) ? cur.textContent.trim() : '';
  return { page: location.hash || '#/', title: (h1 ? h1.textContent.trim() : document.title).slice(0, 120), section: sec };
}

// ---------- the window ----------
let ISS_DRAFT = null;                         // what will be sent, gathered when the window opens (so it describes the page behind it)
async function issReportDialog() {
  const w = issWhere(), info = await issInfo(), settings = issSettings(), me = ME();
  ISS_DRAFT = { w, info, settings };
  const who = viaTS() ? `${me.name} (${me.login})` : (getName() || 'the name typed in on this computer');
  const rows = [['Page', `${w.title} (${w.page})${w.section ? ', at ' + w.section : ''}`], ['Version of the app on this device', PAGE_VERSION || 'not known'],
    ['Account', `${who}, ${me.role_word || me.role}`], ['When', 'The time you send it']].concat(Object.entries(info), Object.entries(settings));
  const to = me.role === 'owner' ? 'your Issue tracker' : (me.owner_name || 'the owner');
  modal(html`<form method="dialog" class="iss-dlg" data-form="issreport"><h2>Report a problem</h2>
    <p>Say what went wrong, what looked odd or what you would like changed. It goes to ${to} with the details of this page and this device.</p>
    <label class="f">What happened?<small>About: ${w.title}${w.section ? ', ' + w.section : ''}</small><textarea name="notes" rows="6" maxlength="4000" autofocus></textarea></label>
    <label class="f iss-file">Pictures or screenshots<small>You can leave this empty. Up to 4.</small><input type="file" name="files" accept="image/*" multiple></label>
    <label class="f">This device is called<small>Typed once and kept on this device, so every report says where it came from. A browser cannot read the device's own name.</small><input type="text" name="device" maxlength="40" autocomplete="off" value="${offDevice()}"></label>
    <details class="iss-sent"><summary>Everything that is sent with it (${rows.length} details)</summary>
      <dl class="dl iss-dl">${rows.map(([k, v]) => html`<dt>${k}</dt><dd>${String(v)}</dd>`)}</dl></details>
    <p id="iss-msg" class="dbg-msg" role="status" aria-live="polite"></p>
    <div class="row"><button class="btn" type="submit">Send the report</button><button class="btn ghost" type="button" data-act="isscancel">Cancel</button></div></form>`, 'iss-win');
}
async function issSend(form) {            // Enter in the name box sends too: the form's own button is Send, so it never closes the window unsent
  const btn = form.querySelector('button[type=submit]'), msg = form.querySelector('#iss-msg'), say = t => { msg.textContent = ''; setTimeout(() => { msg.textContent = t; }, 30); };
  const notes = form.elements.notes.value.trim(), files = [...form.elements.files.files];
  if (!notes && !files.length) { say('Write what happened, or add a picture, before sending.'); form.elements.notes.focus(); return; }
  if (files.length > 4) { say('A report takes up to 4 pictures. Choose fewer, or send the rest in a second report.'); form.elements.files.focus(); return; }
  const dev = form.elements.device.value.trim().slice(0, 40);
  if (dev && dev !== offDevice()) { OFFDEV = dev; try { await idbPut('kv', OFFDEV, 'device'); } catch (e) { /* kept for this visit */ } }
  const D = ISS_DRAFT || { w: issWhere(), info: {}, settings: {} }, fd = new FormData();
  fd.append('notes', notes); fd.append('page', D.w.page); fd.append('page_title', D.w.title); fd.append('section', D.w.section);
  fd.append('page_version', PAGE_VERSION || ''); fd.append('device', offDevice()); fd.append('made_at', new Date().toISOString());
  fd.append('info', JSON.stringify(D.info)); fd.append('settings', JSON.stringify(D.settings));
  files.forEach(f => fd.append('files', f, f.name));
  btn.disabled = true; say('Sending');
  try {
    const r = await api('POST', '/api/report', undefined, fd);
    dlg.close('sent');
    toast(r && r.offline ? 'Report written' : `Report sent${r && r.id ? ' (number ' + r.id + ')' : ''}. Thank you.`);
    if (location.hash.startsWith('#/issues')) route();
  } catch (e) { btn.disabled = false; say('It could not be sent: ' + e.message); }
}

// ---------- the Issue tracker page (the owner's) ----------
const ISS = { show: 'active', q: '', data: null };
const ISS_SHOW = [['active', 'Open and being looked at'], ['open', 'Open'], ['looking', 'Being looked at'], ['fixed', 'Fixed'], ['closed', 'Closed'], ['all', 'All']];
const issShow = x => ISS.show === 'all' || (ISS.show === 'active' ? x.status === 'open' || x.status === 'looking' : x.status === ISS.show);
const issHay = x => [x.notes, x.name, x.login, x.device, x.page_title, x.page, x.owner_notes, 'number ' + x.id].join(' ');
let ISS_CLOSE = null;                        // the nearest word when the search shows close spellings
function issList() {                         // the reports for Show and the search box: exact letters first, else close spellings
  const shown = ISS.data.issues.filter(issShow), p = fzPick(shown.map(issHay), ISS.q);
  ISS_CLOSE = p.close; return shown.filter((x, i) => p.on[i]);
}
const issBehind = x => x.page_version && x.server_version && x.page_version !== x.server_version;
function issText(x) {                         // one report in plain words, for pasting into a chat with Claude
  const L = [`Report ${x.id}: ${x.status_word}${x.fixed_in ? ' in ' + x.fixed_in : ''}`,
    `Sent ${x.at} (UTC)${x.made_at && x.made_at.slice(0, 16) !== x.at.slice(0, 16) ? `, written ${x.made_at}` : ''} by ${x.name || 'someone'}${x.login ? ' (' + x.login + ')' : ''}, ${x.role_word}`,
    `Device: ${x.device || 'not named'}${x.addr ? ', from ' + x.addr : ''}`,
    `Page: ${x.page_title} (${x.page})${x.section ? ', at ' + x.section : ''}`,
    `Versions: the page was ${x.page_version || 'not known'}, the server ${x.server_version}${issBehind(x) ? ' (THE DEVICE WAS SHOWING AN OLDER VERSION)' : ''}`,
    '', 'What they wrote:', x.notes || '(nothing; see the pictures)'];
  if (x.photos.length) L.push('', `${x.photos.length} picture${x.photos.length === 1 ? '' : 's'} attached (in the app, not in this text).`);
  if (x.owner_notes) L.push('', "The owner's notes:", x.owner_notes);
  L.push('', 'Device details:', ...Object.entries(x.info).map(([k, v]) => `  ${k}: ${String(v).replace(/\n/g, '\n    ')}`));
  L.push('', 'Settings on the device:', ...Object.entries(x.settings).map(([k, v]) => `  ${k}: ${v}`));
  return L.join('\n');
}
function issCard(x) {
  const fixed = x.status === 'fixed';
  return html`<article class="iss-card" id="iss-${x.id}" data-id="${x.id}" aria-labelledby="iss-h-${x.id}">
    <h3 id="iss-h-${x.id}">Report ${x.id}: ${x.page_title || 'a page'}</h3>
    <p class="iss-tags"><span class="tag iss-st" data-st="${x.status}">${x.status_word}${fixed && x.fixed_in ? ' in ' + x.fixed_in : ''}</span>
      ${issBehind(x) ? html`<span class="tag iss-old">Device was on ${x.page_version}, server on ${x.server_version}</span>` : ''}
      ${x.photos.length ? html`<span class="tag">${x.photos.length} picture${x.photos.length === 1 ? '' : 's'}</span>` : ''}</p>
    <p class="iss-by">${timeEl(x.at)}, from <strong>${x.name || 'someone'}</strong> (${x.role_word}) on <strong>${x.device || 'a device with no name'}</strong>.
      Page: <a href="${x.page || '#/'}">${x.page_title || x.page}</a>${x.section ? `, at ${x.section}` : ''}.</p>
    <div class="iss-notes">${x.notes || html`<span class="muted">Nothing written; see the pictures.</span>`}</div>
    ${x.photos.length ? html`<ul class="iss-pics">${x.photos.map((p, i) => html`<li><a href="/api/issues/${x.id}/photo/${p.id}" target="_blank" rel="noopener"><img src="/api/issues/${x.id}/photo/${p.id}" alt="Picture ${i + 1} of report ${x.id}${p.name ? ': ' + p.name : ''}" loading="lazy"><span>Open picture ${i + 1} at full size</span></a></li>`)}</ul>` : ''}
    <details class="iss-more"><summary>Device, versions and settings (${4 + Object.keys(x.info).length + Object.keys(x.settings).length} details)</summary>
      <dl class="dl iss-dl"><dt>Account</dt><dd>${x.name}${x.login ? ` (${x.login})` : ''}, ${x.role_word}, ${x.via === 'tailscale' ? 'through Tailscale' : 'on this computer or the home network'}${x.addr ? ', from ' + x.addr : ''}</dd>
        <dt>Version of the app on the device</dt><dd>${x.page_version || 'Not known'}</dd><dt>Version the server was running</dt><dd>${x.server_version}</dd>
        <dt>Written</dt><dd>${x.made_at ? when(x.made_at) : when(x.at)}${x.made_at && Math.abs(new Date(x.at) - new Date(x.made_at)) > 120000 ? `, received ${when(x.at)} (it waited on the device)` : ''}</dd>
        ${Object.entries(x.info).map(([k, v]) => html`<dt>${k}</dt><dd>${String(v)}</dd>`)}
        ${Object.entries(x.settings).map(([k, v]) => html`<dt>${/^Display: /.test(k) ? k : 'Setting: ' + k}</dt><dd>${String(v)}</dd>`)}</dl></details>
    <div class="iss-work">
      <label class="f">Status of report ${x.id}<select data-act="issstatus" data-id="${x.id}">${Object.entries(ISS.data.status_words).map(([k, w]) => html`<option value="${k}" ${k === x.status ? raw('selected') : ''}>${w}</option>`)}</select></label>
      ${fixed ? html`<label class="f">Fixed in version<small>Like ${ISS.data.version}</small><input type="text" inputmode="decimal" data-act="issfixed" data-id="${x.id}" value="${x.fixed_in}" maxlength="20" autocomplete="off"></label>` : ''}
      <label class="f iss-own">Your notes on report ${x.id}<small>Only you see these. Saved when you leave the box.</small><textarea rows="2" data-act="issnote" data-id="${x.id}" maxlength="4000">${x.owner_notes}</textarea></label></div>
    <div class="row iss-acts"><button class="btn small ghost" type="button" data-act="isscopy" data-id="${x.id}">Copy for Claude<span class="sr">: report ${x.id}</span></button>
      <button class="btn small danger" type="button" data-act="issdel" data-id="${x.id}">Remove<span class="sr"> report ${x.id}</span></button></div></article>`;
}
function issListHtml() {
  const list = issList();
  return html`<p class="iss-count" role="status" aria-live="polite">${list.length === ISS.data.issues.length ? `${list.length} report${list.length === 1 ? '' : 's'}` : `${list.length} of ${ISS.data.issues.length} reports`}, newest first.${fzNote(ISS.q, ISS_CLOSE)}</p>
    ${list.length ? html`<div class="iss-grid">${list.map(issCard)}</div>`
      : html`<p class="notice">${ISS.data.issues.length ? 'No report matches. Choose All under Show, or clear the search box.' : 'No reports yet. They arrive here when someone presses Report a problem, at the foot of Navigation on any page.'}</p>`}`;
}
function issRedraw() { const b = document.getElementById('iss-list'); if (b && ISS.data) b.innerHTML = rend(issListHtml()); }
async function viewIssues() {
  const title = 'Issue tracker';
  if (ME().role !== 'owner') return { title, html: html`<h1>${title}</h1><p class="notice">Only ${ME().owner_name || 'the owner'} can open the Issue tracker. Anyone can send a report: press Report a problem at the foot of Navigation.</p>
    <p><button class="btn" type="button" data-act="issreport" aria-haspopup="dialog">Report a problem</button></p>` };
  ISS.data = await api('GET', '/api/issues');
  const c = ISS.data.counts;
  if (ISS.data.fresh) api('POST', '/api/issues/seen', {}).catch(() => {});       // Today stops announcing them once the page has been opened
  return { title, html: html`<h1>${title}</h1>
    <p class="muted">Problems and ideas sent with Report a problem, each with the device, version, page and settings it came from. ${c.open} open, ${c.looking} being looked at, ${c.fixed} fixed, ${c.closed} closed.</p>
    <div class="iss-bar noprint">
      <label class="f">Show<select data-act="issshow">${ISS_SHOW.map(([k, w]) => html`<option value="${k}" ${k === ISS.show ? raw('selected') : ''}>${w}</option>`)}</select></label>
      <label class="f iss-q">Search the reports<input type="search" data-f="issq" value="${ISS.q}" autocomplete="off"></label>
      <div class="row"><button class="btn" type="button" data-act="issreport" aria-haspopup="dialog">Report a problem</button>
        <button class="btn ghost" type="button" data-act="isscopy" data-id="all">Copy the ones shown for Claude</button></div></div>
    <p id="iss-say" class="dbg-msg" role="status" aria-live="polite"></p>
    <div id="iss-list">${issListHtml()}</div>` };
}
function issSay(t) { const m = document.getElementById('iss-say'); if (m) { m.textContent = ''; setTimeout(() => { m.textContent = t; }, 30); } }
async function issPut(el, body, done) {
  const id = +el.dataset.id;
  try {
    const x = await api('PUT', '/api/issues/' + id, body), i = ISS.data.issues.findIndex(y => y.id === id);
    if (i >= 0) { const was = ISS.data.issues[i].status; ISS.data.issues[i] = x; if (was !== x.status) { ISS.data.counts[was]--; ISS.data.counts[x.status]++; } }
    if (done) done(x);
  } catch (e) { toast(e.message, true); issRedraw(); }
}

addFeature({
  name: 'issues',
  pages: { issues: { view: viewIssues, nav: 'issues', section: 'settings', label: 'Issue tracker', href: '#/issues', after: 'history' } },
  today: [{ id: 'iss-today', order: 7,         // one line for the owner about reports from other people not looked at yet
    load: async () => { if (ME().role !== 'owner') return null; const d = await api('GET', '/api/issues?brief=1'); return d.fresh ? d : null; },
    html: d => html`<div class="notice iss-today" id="iss-today"><p><span><strong>${d.fresh === 1 ? 'A new problem report is waiting' : `${d.fresh} new problem reports are waiting`}.</strong>
      Sent from another account with Report a problem.</span> <a class="btn small" href="#/issues">Open the Issue tracker</a></p></div>` }],
  adds: [{ id: 'iss-set', match: parts => parts[0] === 'settings', anchor: main => main.querySelector('.set-health'), where: 'afterend',
    load: async () => { if (ME().role !== 'owner') return { owner: false }; try { return Object.assign({ owner: true }, await api('GET', '/api/issues?brief=1')); } catch (e) { return { owner: true, counts: null }; } },
    html: d => html`<section class="blk set-card" id="iss-set"><h2>Problems and ideas</h2>
      <p>Tell ${d.owner ? 'yourself' : (ME().owner_name || 'the owner')} about something that went wrong or could be better. The report carries the page, the version, this device and its settings. Also at the foot of Navigation on every page.</p>
      <div class="row"><button class="btn" type="button" data-act="issreport" aria-haspopup="dialog">Report a problem</button>
        ${d.owner ? html`<a class="btn ghost" href="#/issues">Open the Issue tracker${d.counts ? ` (${d.counts.open + d.counts.looking} open)` : ''}</a>` : ''}</div></section>` }],
});
Object.assign(acts, {
  issreport() { const d = document.querySelector('dialog[open]'); if (d) d.close(); issReportDialog(); },
  isscancel() { if (dlg.open) dlg.close('cancel'); },
  async isscopy(el) {
    const list = el.dataset.id === 'all' ? issList() : ISS.data.issues.filter(x => x.id === +el.dataset.id);
    if (!list.length) { issSay('There is nothing shown to copy.'); return; }
    const text = `Problem reports from Plant record ${ISS.data.version} (${list.length}):\n\n` + list.map(issText).join('\n\n----------\n\n');
    try { await navigator.clipboard.writeText(text); issSay(`Copied ${list.length === 1 ? 'report ' + list[0].id : list.length + ' reports'}. Paste ${list.length === 1 ? 'it' : 'them'} into the chat with Claude. Pictures are not copied: attach them there yourself.`); toast('Copied'); }
    catch (e) { await modal(html`<form method="dialog"><h2>Copy for Claude</h2><p>This browser did not allow copying. Select the text below and copy it yourself.</p>
      <label class="f">The report${list.length === 1 ? '' : 's'} as text<textarea rows="14" readonly>${text}</textarea></label><div class="row"><button class="btn" value="ok">Done</button></div></form>`); }
  },
  async issdel(el) {
    const id = +el.dataset.id;
    if (!(await confirmBox(`Remove report ${id}?`, 'The report, your notes on it and its pictures go for good. To keep it out of the way instead, set its status to Fixed or Closed.', 'Remove it', true))) return;
    try { await api('DELETE', '/api/issues/' + id); toast(`Report ${id} removed`); await route(); } catch (e) { toast(e.message, true); }
  },
});
Object.assign(formActs, { issreport: form => issSend(form) });
Object.assign(changeActs, {
  issshow(el) { ISS.show = el.value; issRedraw(); },
  issstatus(el) { issPut(el, { status: el.value }, x => { issRedraw(); toast(`Report ${x.id}: ${x.status_word}`); const s = document.querySelector(`#iss-${x.id} select[data-act=issstatus]`) || document.querySelector('select[data-act=issshow]'); if (s) s.focus(); }); },
  issfixed(el) { issPut(el, { fixed_in: el.value.trim() }, x => { const t = document.querySelector(`#iss-${x.id} .iss-st`); if (t) t.textContent = x.status_word + (x.fixed_in ? ' in ' + x.fixed_in : ''); issSay(`Report ${x.id}: ${x.fixed_in ? 'fixed in ' + x.fixed_in : 'no version given'}. Saved.`); }); },
  issnote(el) { issPut(el, { owner_notes: el.value }, x => issSay(`Your notes on report ${x.id} are saved.`)); },
});
document.addEventListener('input', e => { if (e.target.dataset && e.target.dataset.f === 'issq') { ISS.q = e.target.value; issRedraw(); } });
