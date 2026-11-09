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
      ${x.history.length ? html`<details class="fr-hist"><summary>History (${x.history.length})</summary><ul>${x.history.map(h => html`<li><span class="tag">${h.status}</span> ${frValue(h)}<br><span class="hint">${frWho(h)}</span></li>`)}</ul></details>` : ''}</dd></div>`;
}
function frSpeciesHtml(R, name) {
  if (!R.groups.length) return html`<p class="muted">No facts kept for ${name} yet. They come from the upgrade batches, from Claude's care sheets and species notes, and (step 6b) from what you and other editors add.</p>`;
  const keys = [...new Set(R.groups.flatMap(g => g.fields.flatMap(f => [f.accepted].concat(f.history).filter(Boolean).map(x => x.key))))];
  const cap = k => k.charAt(0).toUpperCase() + k.slice(1);
  const forWhom = keys.length === 1 && !keys[0].includes(' ') ? html`the genus <i class="latin">${cap(keys[0])}</i> as a whole` : keys.length === 1 ? html`<i class="latin">${cap(keys[0])}</i>` : html`<i class="latin">${cap(keys.find(k => k.includes(' ')) || keys[0])}</i> and its genus`;
  return html`<p class="hint">${R.accepted} accepted ${R.accepted === 1 ? 'fact' : 'facts'} for ${forWhom}${R.total > R.accepted ? html`, with ${R.total - R.accepted} earlier or proposed values in the history` : ''}. Each says where it came from and how sure it is. Open a group to read it.</p>
    ${R.groups.map(g => html`<details class="fr-group" ${g.group === 'Temperature' || g.group === 'Light' ? raw('open') : ''}><summary>${g.group} <span class="muted">(${g.fields.length})</span></summary><dl class="dl fr-dl">${g.fields.map(frRow)}</dl></details>`)}
    <p class="hint"><a href="/api/facts/export.csv" class="noprint">Download every fact (CSV)</a>. Correcting a fact from here comes with step 6b of the plan.</p>`;
}

addFeature({
  name: 'facts',
  adds: [
    { id: 'sp-facts-rows', match: parts => parts[0] === 'species' && parts[1], anchor: main => { const h = main.querySelector('#sp-facts-h'); return h && h.closest('section'); }, where: 'beforebegin',
      load: async parts => { const name = decodeURIComponent(parts[1]); const R = await api('GET', '/api/facts/rows?name=' + enc(name)); return { R, name }; },
      html: ({ R, name }) => html`<section aria-labelledby="sp-facts-rows-h" id="sp-facts-rows" class="fr-box"><h2 id="sp-facts-rows-h">Facts and where they come from</h2>${frSpeciesHtml(R, name)}</section>` },
    { id: 'fr-plant', match: parts => parts[0] === 'plant' && parts[1] && parts[2] !== 'edit', anchor: '#temp', where: 'beforebegin',
      load: async parts => { const p = CUR && CUR.p && CUR.p.code === parts[1] ? CUR.p : null; const F = p && p.from_species; return F && Object.keys(F).length ? { F, p } : null; },
      html: ({ F, p }) => { const names = Object.values(F).map(x => x.label.toLowerCase()); const srcs = [...new Set(Object.values(F).map(x => x.source))];
        return html`<p class="hint fr-plant" id="fr-plant">Not set for this plant, so shown from <i class="latin">${p.scientific_name}</i>'s facts: ${names.slice(0, 6).join(', ')}${names.length > 6 ? ` and ${names.length - 6} more` : ''}
          (${srcs.length === 1 ? srcs[0] : srcs.length + ' sources'}). <a href="#/species/${enc(p.scientific_name)}">The species' facts</a>.</p>`; } },
  ],
});
