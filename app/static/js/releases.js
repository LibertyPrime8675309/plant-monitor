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
      html: W => { const body = html`<p><strong>New in ${W.entry.version}${W.entry.date ? ` (${W.entry.date})` : ''}:</strong> ${rlLine(W.entry.lines[0] || '')}</p>
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
      html: U => html`<div class="notice rl-update" id="rl-update"><p><strong>An update is ready: ${U.version}</strong>${U.published ? ` (released ${U.published})` : ''}. On your PC, run <code>Update Plant Database.cmd</code> in the Plants folder: it fetches this release from GitHub, makes a backup and installs it in a couple of minutes.
        <a href="${U.url}" target="_blank" rel="noopener noreferrer">What changed</a>.</p></div>` },
    { id: 'rl-restore', order: 85,
      load: async () => { const W = await rlLoad(); return W.restore && W.restore.due ? W.restore : null; },
      html: R => html`<section class="blk" id="rl-restore"><h2>Test a restore</h2><p>${R.last ? `The last restore was ${R.days} days ago.` : 'A backup has never been restored on this install.'} Once a quarter, make sure a backup really comes back:
        on <a href="#/backups">Backups</a>, press <strong>Back up now</strong>, then <strong>Restore</strong> on that newest backup. The database from just before is kept as another backup, so nothing is lost, and the date here resets.</p></section>` },
  ],
});
Object.assign(acts, {
  rlseen: async el => { await api('POST', '/api/whatsnew/seen', {}); const box = el.closest('#rl-new'); if (box) box.remove(); RLP = null; toast('Noted. It will not show again on this version.'); },
});
