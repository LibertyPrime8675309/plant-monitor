/* Plant record front end: the release rhythm (1.55.0, PLAN.md step 7; plantdb/releases.py). One of the files loaded in order by
   index.html (js/manifest.json); they share one scope. Plain JavaScript, no inline handlers (the server's content policy forbids them).

   Three lines under Today's summary, registered with addFeature():
   - What's new in the version that is running, from the CHANGELOG, with "Got it" (a setting of the person's own, so it follows them);
   - An update is ready: the owner is told when GitHub has a newer release than the one running (checked twice a day);
   - Test a restore: the owner is reminded once a quarter to restore the newest backup from the Backups page. */
'use strict';

// **bold** in a CHANGELOG line becomes <strong>; everything else is plain text
function rlLine(t) {
  const parts = String(t).split(/\*\*([^*]+)\*\*/g);
  return html`${parts.map((p, i) => i % 2 ? html`<strong>${p}</strong>` : p)}`;
}
let RLP = null, RLT = 0;                       // one request serves the three blocks of a Today draw
function rlLoad() { if (!RLP || Date.now() - RLT > 5000) { RLP = api('GET', '/api/whatsnew'); RLT = Date.now(); } return RLP; }

addFeature({
  name: 'releases',
  today: [
    { id: 'rl-new', order: 2,
      load: async () => { const W = await rlLoad(); return W.entry && !W.seen ? W : null; },
      // 1.56.5: shown in full the first time on this device; after that folded to one line until Got it, so the jobs come first
      html: W => { const body = html`<p><strong>New in ${W.entry.version}${W.entry.date ? ` (${/^\d{4}-\d\d-\d\d$/.test(W.entry.date) ? parseYmd(W.entry.date).toLocaleDateString([], { month: 'long', day: 'numeric', year: 'numeric' }) : W.entry.date})` : ''}:</strong> ${rlLine(W.entry.lines[0] || '')}</p>
        ${W.entry.lines.length > 1 ? html`<details class="rl-more"><summary>The rest of what changed (${W.entry.lines.length - 1})</summary><ul>${W.entry.lines.slice(1).map(l => html`<li>${rlLine(l)}</li>`)}</ul></details>` : ''}
        <p class="row noprint"><button class="btn small ghost" type="button" data-act="rlseen">Got it</button><a class="btn small ghost" href="/api/whatsnew/all" target="_blank" rel="noopener">Every version's changes</a></p>`;
        const v = W.entry.version; let fold = false;                  // folded from the next visit on (this tab keeps showing it in full)
        try { const seen = localStorage.getItem('plantdb.rlshown'), here = sessionStorage.getItem('plantdb.rlshown');
          fold = seen === v && here !== v; if (seen !== v) { localStorage.setItem('plantdb.rlshown', v); sessionStorage.setItem('plantdb.rlshown', v); } } catch (e) { /* shown in full */ }
        return fold
          ? html`<details class="notice rl-new rl-fold" id="rl-new"><summary><strong>What's new in ${W.entry.version}</strong> (${W.entry.lines.length} ${W.entry.lines.length === 1 ? 'change' : 'changes'})</summary>${body}</details>`
          : html`<div class="notice rl-new" id="rl-new">${body}</div>`; } },
    { id: 'rl-update', order: 3,
      load: async () => { const W = await rlLoad(); return W.update ? W.update : null; },
      html: U => html`<div class="notice rl-update" id="rl-update"><p><strong>An update is ready: ${U.version}</strong>${U.published ? ` (released ${U.published})` : ''}. On your PC, run <code>Update Plant Database.cmd</code> in the Plants folder. It fetches this release from GitHub, makes a backup and installs it, in a couple of minutes.
        <a href="${U.url}" target="_blank" rel="noopener noreferrer">What changed</a>.</p></div>` },
    { id: 'rl-restore', order: 85,
      load: async () => { const W = await rlLoad(); return W.restore && W.restore.due ? W.restore : null; },
      html: R => html`<section class="blk" id="rl-restore"><h2>Test a restore</h2><p>${R.last ? `The last restore was ${R.days} days ago.` : 'A backup has never been restored on this install.'} Once a quarter, make sure a backup really comes back.
        On <a href="#/backups">Backups</a>, press <strong>Back up now</strong>. Then press <strong>Restore</strong> on that newest backup. The database from just before is kept as another backup, so nothing is lost, and the date here resets.</p></section>` },
  ],
});
// ---------- 1.58.0: Check for updates (beside the version on Settings, and at the foot of Navigation) ----------
// A page that has been open since before an update keeps running the old version. From 1.56.5 it notices by itself (newerApp() in
// core.js), but nothing let a person ask, and a Home Screen app on an iPad has no reload button at all: on November 15, 2026 Ethan's
// iPad showed 1.55.0 for days while the PC ran 1.57.0. The button asks three things and says each answer in a window:
//   1. which version the plant server runs, asked past every saved copy (X-Probe makes the service worker ask the server itself,
//      and an answer marked X-Offline-Saved is a saved copy, so it counts as "could not be reached");
//   2. the service worker is told to look for its own newer copy, so the next start is the new app;
//   3. for the owner, GitHub is asked for the newest release now (POST /api/whatsnew/check).
// "Reload the app" is always there: it is the reload a Home Screen app lacks.
async function rlServerVersion() {
  try {
    const r = await fetch('/api/version?nosave=1&_=' + Date.now(), { cache: 'no-store', headers: { 'X-Probe': '1' } });
    if (!r.ok || r.headers.get('X-Offline-Saved')) return null;
    const v = (await r.json()).version;
    return typeof v === 'string' && /^\d+\.\d+\.\d+/.test(v) ? v : null;
  } catch (e) { return null; }
}
function rlCheckBody(R) {
  const here = PAGE_VERSION || (META && META.version) || '', owner = ME().role === 'owner', who = ME().owner_name || 'the owner';
  const L = R.gh && R.gh.latest;
  return html`<h2>Check for updates</h2>
    <div id="rl-check-box">
    ${R.busy ? html`<p class="loading">Asking the plant server</p>` : html`
    <dl class="dl rl-check">
      <dt>This device is showing</dt><dd>${here ? 'Version ' + here : 'A version from before 1.56.5 (it does not say which)'}</dd>
      <dt>The plant server is running</dt><dd>${R.server ? 'Version ' + R.server : 'Not known: it could not be reached just now'}</dd>
      ${owner ? html`<dt>The newest release</dt><dd>${L ? html`Version ${L.version}${L.published ? ` (released ${L.published})` : ''}${R.gh.asked ? ', asked just now' : ', as last asked'}` : R.gh && R.gh.off ? 'Not asked: looking for new releases is turned off on this install' : 'Not known: GitHub could not be asked just now'}</dd>` : ''}
    </dl>
    ${!R.server ? html`<p class="notice bad" id="rl-check-say"><strong>The plant server did not answer.</strong> This device may be offline, or the PC may be asleep or off. Reloading now would only open the copy saved on this device.</p>`
      : R.server !== here ? html`<p class="notice" id="rl-check-say"><strong>This device is behind.</strong> Reload the app to open version ${R.server}.</p>`
      : html`<p class="notice good" id="rl-check-say"><strong>This device is up to date:</strong> it is showing the version the plant server runs.</p>`}
    ${owner && R.gh && R.gh.newer && L ? html`<p class="notice" id="rl-check-new"><strong>An update is ready: ${L.version}.</strong> On your PC, run <code>Update Plant Database.cmd</code> in the Plants folder. It fetches the release, makes a backup and installs it.${L.url ? html` <a href="${L.url}" target="_blank" rel="noopener noreferrer">What changed</a>` : ''}</p>`
      : owner && R.server && L ? html`<p id="rl-check-new">The plant server has the newest release. New versions come out on the first of each month.</p>`
      : !owner && R.server ? html`<p id="rl-check-new">New versions are installed on the plant server by ${who}. This device follows by itself; this button is for when it has not.</p>` : ''}`}
    </div>
    <div class="row">
      <button class="btn${R.server && R.server !== here ? '' : ' ghost'}" type="button" data-act="reloadnow" ${R.busy ? raw('disabled') : ''}>${R.server && R.server !== here ? 'Reload the app to open version ' + R.server : 'Reload the app'}</button>
      <button class="btn ghost" type="button" data-act="rlcheck" ${R.busy ? raw('disabled') : ''}>Check again</button>
      <button class="btn${R.server && R.server !== here ? ' ghost' : ''}" value="ok">Close</button></div>
    <p class="sr" id="rl-check-live" role="status" aria-live="polite"></p>`;
}
async function rlCheck() {
  const paint = R => {
    if (dlg.open && dlg.querySelector('.rl-check-dlg')) { dlg.querySelector('.rl-check-dlg').innerHTML = rend(rlCheckBody(R)); }
    else modal(html`<form method="dialog" class="rl-check-dlg">${rlCheckBody(R)}</form>`, 'small rl-check-win');
  };
  paint({ busy: true });
  const R = { server: await rlServerVersion(), gh: null };
  try { if ('serviceWorker' in navigator) { const reg = await navigator.serviceWorker.getRegistration(); if (reg) reg.update().catch(() => {}); } } catch (e) { /* no service worker here */ }
  if (R.server && ME().role === 'owner') { try { R.gh = await api('POST', '/api/whatsnew/check', {}); } catch (e) { R.gh = null; } }
  if (!dlg.open || !dlg.querySelector('.rl-check-dlg')) return;                // closed while it was asking
  paint(R);
  const say = dlg.querySelector('#rl-check-say'), live = dlg.querySelector('#rl-check-live'), go = dlg.querySelector('[data-act=reloadnow]');
  if (live && say) live.textContent = say.textContent;                          // said once, when the answer is in
  if (go) go.focus();
}

Object.assign(acts, {
  rlcheck() { rlCheck(); },
  rlseen: async el => { await api('POST', '/api/whatsnew/seen', {}); const box = el.closest('#rl-new'); if (box) box.remove(); RLP = null; toast('Noted. It will not show again on this version.'); },
});
