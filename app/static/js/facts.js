/* Plant record front end: knowledge with provenance (1.53.0, PLAN.md step 6a; plantdb/facts.py). One of the files loaded in order
   by index.html (js/manifest.json); they share one scope. Plain JavaScript, no inline handlers (the server's content policy forbids them).

   Two additions, registered with addFeature() (features.js):
   - on a species page (#/species/<name>): "Facts and where they come from", every fact the record holds for the
     species by group, each with its accepted value, its source, how sure, who noted it and when, and the history behind it;
   - on a plant's page: a line saying which care fields are not set for this plant and are shown from the species' facts instead
     (the server fills them in when the page asks with ?fill=1, plant.js), with their sources. */
'use strict';

const FR_CONF = { certain: 'Certain', likely: 'Likely', unsure: 'Unsure' };
const FR_KIND = { reference: 'a reference', trial: 'a trial', grower: 'a grower', observation: 'own observation', claude: 'Claude', batch: 'an upgrade batch' };
const frLink = s => /^https?:\/\//.test(s) ? html`<a href="${s}" target="_blank" rel="noopener noreferrer">${s.replace(/^https?:\/\/(www\.)?/, '').slice(0, 60)}</a>` : esc(s);
// a value as words: numbers and text as they are, lists and records summarised
function frValue(f) {
  const v = f.value, k = f.value_kind || 'text';
  if (v == null || v === '') return html`<span class="muted">(empty)</span>`;
  if (k !== 'json') return html`${String(v)}`;
  if (Array.isArray(v)) {
    if (!v.length) return html`<span class="muted">(none)</span>`;
    return html`<ul class="fr-list">${v.slice(0, 8).map(x => html`<li>${typeof x === 'string' ? x : x.url ? html`<a href="${x.url}" target="_blank" rel="noopener noreferrer">${x.title || x.url}</a>` : x.kind || x.name || x.what || x.method || x.title ? html`<strong>${x.kind || x.name || x.what || x.method || x.title}</strong>${x.text || x.why || x.how || x.sci ? html`: ${x.text || x.why || x.how || x.sci}` : ''}` : JSON.stringify(x)}</li>`)}${v.length > 8 ? html`<li class="muted">and ${v.length - 8} more</li>` : ''}</ul>`;
  }
  if (typeof v === 'object') return html`${v.verdict ? html`<strong>${v.verdict}.</strong> ` : ''}${v.text || v.why || ''}${v.patent ? html` <span class="fact-warn">⚠ ${v.patent}</span>` : ''}`;
  return html`${String(v)}`;
}
const frWho = f => html`${f.source ? frLink(f.source) : html`<span class="muted">no source given</span>`}${f.source_kind ? html` (${FR_KIND[f.source_kind] || f.source_kind})` : ''}${f.noted_by ? html`. Noted by ${f.noted_by}` : ''}${f.noted_at ? html` on ${when(f.noted_at)}` : ''}. ${FR_CONF[f.confidence] || f.confidence}.`;
function frRow(x) {
  const a = x.accepted;
  return html`<div class="fr-row"><dt>${x.label}</dt>
    <dd>${a ? html`<div class="fr-val">${frValue(a)}</div><p class="hint fr-src">${frWho(a)}${a.note ? html` ${a.note}.` : ''}</p>` : html`<p class="muted">No accepted value${x.history.length ? ' now' : ''}.</p>`}
      ${x.history.filter(h => h.status === 'proposed').map(h => frProposed(h))}
      ${canChange() ? html`<p class="row fr-acts noprint"><button class="btn small ghost" type="button" data-act="frpropose" data-field="${x.field}" aria-label="Suggest a change to ${x.label}">${a ? 'Suggest a change' : 'Suggest a value'}</button></p>` : ''}
      ${x.history.filter(h => h.status !== 'proposed').length ? html`<details class="fr-hist"><summary>History (${x.history.filter(h => h.status !== 'proposed').length})</summary><ul>${x.history.filter(h => h.status !== 'proposed').map(h => html`<li><span class="tag">${h.status}</span> ${frValue(h)}<br><span class="hint">${frWho(h)}${h.note ? html` ${h.note}` : ''}</span></li>`)}</ul></details>` : ''}</dd></div>`;
}
// a proposal waiting for review: what it says, who, and Accept / Reject for someone else (or the owner)
function frProposed(h, withField) {
  return html`<div class="fr-prop notice" role="note"><p><strong>Proposed${withField ? html` for ${h.label}` : ''}:</strong> ${frValue(h)}</p><p class="hint">${frWho(h)}${h.note ? html` ${h.note}` : ''}</p>
    ${h.can_accept ? html`<p class="row noprint"><button class="btn small" type="button" data-act="fraccept" data-id="${h.id}">Accept</button><button class="btn small ghost" type="button" data-act="frreject" data-id="${h.id}">Reject</button></p>`
      : h.mine ? html`<p class="hint">Yours: another editor or the owner accepts it.</p>` : ''}</div>`;
}
// 6b: the form to propose a fact or a correction
const FR_FORM_KINDS = { reference: 'A reference (a book, a site, a label)', trial: 'A trial or study', grower: 'A grower or nursery', observation: 'My own observation', claude: 'Claude' };
async function frPropose(el, R, name, kind) {
  if (!(await needName())) return;
  const field = el.dataset.field || '', f = R.fields.find(x => x.field === field);
  const groups = [...new Set(R.fields.map(x => x.group))];
  const r = await modal(html`<form method="dialog" class="fr-form"><h2>${f ? `Suggest a change: ${f.label}` : 'Add a fact'}</h2>
    <p class="hint">For <i class="latin">${name}</i>. Another editor, or the owner, reviews it before it shows as the accepted value.</p>
    ${f ? '' : html`<label class="f">Which fact<select name="field" required><option value="">Choose one</option>${groups.filter(g => kind !== 'fungus' || ['Uses and partners', 'Propagation', 'Origin and safety', 'Care sheet'].includes(g)).map(g => html`<optgroup label="${g}">${R.fields.filter(x => x.group === g).map(x => html`<option value="${x.field}">${x.label}</option>`)}</optgroup>`)}</select></label>`}
    <label class="f">${f ? 'New value' : 'Value'}${f && (f.kind === 'int' || f.kind === 'num') ? html`<input type="number" name="value" step="${f.kind === 'int' ? '1' : 'any'}" required>` : html`<textarea name="value" rows="3" required></textarea>`}</label>
    <label class="f">Where it comes from<input type="text" name="source" required placeholder="A link, a book and page, a grower's name, or 'my own plants'"></label>
    <label class="f">What kind of source<select name="source_kind">${Object.entries(FR_FORM_KINDS).map(([k, l]) => html`<option value="${k}" ${k === 'reference' ? raw('selected') : ''}>${l}</option>`)}</select></label>
    <label class="f">How sure<select name="confidence"><option value="likely" selected>Likely</option><option value="certain">Certain</option><option value="unsure">Unsure</option></select></label>
    <label class="f">Note (optional)<input type="text" name="note" maxlength="300"></label>
    ${kind === 'fungus' ? html`<p class="hint">Nothing here may say or suggest that a mushroom is edible, safe or medicinal.</p>` : ''}
    <div class="row"><button class="btn" value="ok">Send for review</button><button class="btn ghost" value="cancel">Cancel</button></div></form>`, 'fr-form');
  if (r !== 'ok') return;
  const fd = new FormData(dlg.querySelector('form'));
  const body = { name, kind, field: field || fd.get('field'), value: fd.get('value'), source: fd.get('source'), source_kind: fd.get('source_kind'), confidence: fd.get('confidence'), note: fd.get('note') };
  await guard(async () => { await api('POST', '/api/facts/rows', body); toast('Sent for review. It shows as proposed until another editor accepts it.'); await frReload(); });
}
async function frReview(el, accept) {
  if (!(await needName())) return;
  let note = '';
  if (!accept) { const r = await modal(html`<form method="dialog"><h2>Reject this proposal</h2><label class="f">Why (optional)<input type="text" name="note" maxlength="300"></label><div class="row"><button class="btn" value="ok">Reject</button><button class="btn ghost" value="cancel">Cancel</button></div></form>`); if (r !== 'ok') return; note = new FormData(dlg.querySelector('form')).get('note') || ''; }
  await guard(async () => { await api('POST', `/api/facts/rows/${el.dataset.id}/${accept ? 'accept' : 'reject'}`, { note }); toast(accept ? 'Accepted: it is now the value shown.' : 'Rejected.'); await frReload(); });
}
async function frReload() { await featAdds(location.hash.slice(1).split('?')[0].split('/').filter(Boolean).map(decodeURIComponent)); const q = document.getElementById('fr-queue'); if (q) route(); }
Object.assign(acts, {
  frpropose: el => { const sec = el.closest('#sp-facts-rows'); frPropose(el, FR_CUR.R, FR_CUR.name, FR_CUR.kind); },
  fradd: el => frPropose(el, FR_CUR.R, FR_CUR.name, FR_CUR.kind),
  fraccept: el => frReview(el, true), frreject: el => frReview(el, false),
});
let FR_CUR = { R: null, name: '', kind: 'plant' };
function frSpeciesHtml(R, name) {
  if (!R.groups.length) return html`<p class="muted">No facts kept for ${name} yet. They come from the upgrade batches, from Claude's care sheets and species notes, and from what you and other editors add.</p>
    ${canChange() ? html`<p class="row noprint"><button class="btn ghost" type="button" data-act="fradd">Add a fact</button></p>` : ''}`;
  const keys = [...new Set(R.groups.flatMap(g => g.fields.flatMap(f => [f.accepted].concat(f.history).filter(Boolean).map(x => x.key))))];
  const cap = k => k.charAt(0).toUpperCase() + k.slice(1);
  const forWhom = keys.length === 1 && !keys[0].includes(' ') ? html`the genus <i class="latin">${cap(keys[0])}</i> as a whole` : keys.length === 1 ? html`<i class="latin">${cap(keys[0])}</i>` : html`<i class="latin">${cap(keys.find(k => k.includes(' ')) || keys[0])}</i> and its genus`;
  return html`<p class="hint">${R.accepted} accepted ${R.accepted === 1 ? 'fact' : 'facts'} for ${forWhom}${R.total > R.accepted ? html`, with ${R.total - R.accepted} earlier or proposed values in the history` : ''}. Each says where it came from and how sure it is. Open a group to read it.</p>
    ${R.groups.map(g => html`<details class="fr-group" ${g.group === 'Temperature' || g.group === 'Light' || g.fields.some(f => f.history.some(h => h.status === 'proposed')) ? raw('open') : ''}><summary>${g.group} <span class="muted">(${g.fields.length}${g.fields.some(f => f.history.some(h => h.status === 'proposed')) ? ', a proposal to review' : ''})</span></summary><dl class="dl fr-dl">${g.fields.map(frRow)}</dl></details>`)}
    <p class="row noprint">${canChange() ? html`<button class="btn ghost" type="button" data-act="fradd">Add a fact</button>` : ''}<a href="/api/facts/export.csv" class="btn ghost small">Download every fact (CSV)</a></p>
    <p class="hint">Anyone who can edit may suggest a fact or a correction; another editor or the owner accepts it. The Audit log keeps who did what.</p>`;
}

// 6b: the review queue, a page of its own (#/facts), and a Today block for editors while something waits
async function viewFactsQueue() {
  const Q = await api('GET', '/api/facts/queue');
  const cap = k => k.charAt(0).toUpperCase() + k.slice(1);
  return { title: 'Facts to review', html: html`<h1>Facts to review</h1>
    <p>${Q.count ? `${Q.count} ${Q.count === 1 ? 'proposal is' : 'proposals are'} waiting.` : 'Nothing is waiting for review.'} A proposal is a fact or a correction an editor suggested on a species page; accepting it makes it the value every page shows, and the old value goes into the history. Nobody but the owner accepts their own.</p>
    ${Q.queue.length ? html`<ul class="fr-queue">${Q.queue.map(h => html`<li class="fr-qitem" id="fr-q-${h.id}"><h2><a href="#/species/${enc(cap(h.key))}"><i class="latin">${cap(h.key)}</i></a>: ${h.label}</h2>
      ${h.current ? html`<p class="hint">Now${h.current.key !== h.key ? html` (for the genus <i class="latin">${cap(h.current.key)}</i>)` : ''}: ${frValue(h.current)} <span class="muted">(${h.current.source})</span></p>` : html`<p class="hint">No accepted value yet.</p>`}${frProposed(h)}</li>`)}</ul>` : ''}
    <p class="hint">Facts can also be brought in from another install: the owner or an editor sends the file from <code>/api/facts/export</code> to <code>/api/facts/import</code>; every row arrives as a proposal here.</p>`,
    after: () => { const q = document.querySelector('.fr-queue'); if (q) q.id = 'fr-queue'; } };
}
addFeature({
  name: 'facts',
  pages: { facts: { view: viewFactsQueue, nav: 'facts', section: 'plants', label: 'Facts to review', href: '#/facts', after: 'review' } },
  today: { id: 'today-facts', order: 72, load: async () => { if (!canChange()) return null; const Q = await api('GET', '/api/facts/queue'); return Q.count ? Q : null; },
    jump: Q => `Facts (${Q.count})`,
    html: Q => html`<section class="blk" id="today-facts"><h2>Facts to review (${Q.count})</h2><p>${Q.count === 1 ? 'A fact an editor suggested is' : `${Q.count} facts editors suggested are`} waiting for someone to accept or reject ${Q.count === 1 ? 'it' : 'them'}.</p><p><a class="btn small ghost" href="#/facts">Review them</a></p></section>` },
  adds: [
    { id: 'sp-facts-rows', match: parts => parts[0] === 'species' && parts[1], anchor: main => { const h = main.querySelector('#sp-facts-h'); return h && h.closest('section'); }, where: 'beforebegin',
      load: async parts => { const name = decodeURIComponent(parts[1]); const R = await api('GET', '/api/facts/rows?name=' + enc(name)); const kind = typeof SPCUR !== 'undefined' && SPCUR && SPCUR.kingdom === 'Fungi' ? 'fungus' : 'plant'; FR_CUR = { R, name, kind }; return { R, name }; },
      html: ({ R, name }) => html`<section aria-labelledby="sp-facts-rows-h" id="sp-facts-rows" class="fr-box"><h2 id="sp-facts-rows-h">Facts and where they come from</h2>${frSpeciesHtml(R, name)}</section>` },
    { id: 'fr-plant', match: parts => parts[0] === 'plant' && parts[1] && parts[2] !== 'edit', anchor: '#temp', where: 'beforebegin',
      load: async parts => { const p = CUR && CUR.p && CUR.p.code === parts[1] ? CUR.p : null; const F = p && p.from_species; return F && Object.keys(F).length ? { F, p } : null; },
      html: ({ F, p }) => { const names = Object.values(F).map(x => x.label.toLowerCase()); const srcs = [...new Set(Object.values(F).map(x => x.source))];
        return html`<p class="hint fr-plant" id="fr-plant">Not set for this plant, so shown from <i class="latin">${p.scientific_name}</i>'s facts: ${names.slice(0, 6).join(', ')}${names.length > 6 ? ` and ${names.length - 6} more` : ''}
          (${srcs.length === 1 ? srcs[0] : srcs.length + ' sources'}). <a href="#/species/${enc(p.scientific_name)}">The species' facts</a>.</p>`; } },
  ],
});
