/* Plant record front end: missing details (prototype, proto/missing-details). One of the files loaded in order by index.html; they
   share one scope. Plain JavaScript, no inline handlers (the server's content policy forbids them).

   Several pages need a detail about a plant to work for it (pot size, leaf type, height, the coldest it can take, how often to check
   for water, feeding months, safety for pets). #/missing lists, detail by detail, the plants that do not have it yet, with a box to
   fill it in right there (feeding months open the plant's Edit page). Saving is an ordinary page edit, so it has a version, an
   audit row and shows in Page history. All plants gets a line that links here when anything is missing. */
'use strict';

const msPl = (n, one, many) => `${n} ${n === 1 ? one : many}`;
const msRow = p => ({ code: p.code, common_name: p.name, photo: p.photo });
function msControl(d, p) {
  const id = `ms-${d.key}-${p.code}`, lbl = d.title + ' for ' + p.name;
  const save = html`<button class="btn small" type="submit" aria-label="${'Save ' + lbl}">Save</button>`;
  const form = (inner, unit) => html`<form class="ms-form" data-form="msave" data-code="${p.code}" data-key="${d.key}" data-version="${p.version}" data-name="${p.name}" data-title="${d.title}">
    <label class="f" for="${id}">${d.title}${unit ? ` (${unit})` : ''}</label>
    <div class="ms-in">${inner}${save}</div></form>`;
  if (d.how === 'enum') return form(html`<select id="${id}" name="v" aria-label="${lbl}" required><option value="">Choose…</option>${d.options.map(o => html`<option>${o}</option>`)}</select>`);
  if (d.how === 'length') return form(html`<input id="${id}" name="v" type="text" inputmode="decimal" maxlength="8" required aria-label="${lbl + ', in ' + (lenU() === 'cm' ? 'centimetres' : 'inches')}">`, lenU());
  if (d.how === 'temp') return form(html`<input id="${id}" name="v" type="number" step="1" min="${tU() === '°C' ? -50 : -60}" max="${tU() === '°C' ? 65 : 150}" required aria-label="${lbl + ', in degrees ' + (tU() === '°C' ? 'Celsius' : 'Fahrenheit')}">`, tU());
  if (d.how === 'days') return form(html`<input id="${id}" name="v" type="number" step="1" min="1" max="60" required aria-label="${lbl + ', every so many days'}">`, 'every so many days');
  return html`<a class="btn small ghost" href="#/plant/${enc(p.code)}/edit" aria-label="${'Open Edit for ' + p.name}">Open Edit</a>`;
}
async function viewMissing(parts, qs) {
  const only = qs && qs.get('plant');
  const M = await api('GET', '/api/missing' + (only ? '?plant=' + enc(only) : ''));
  const todo = M.details.filter(d => d.plants.length), done = M.details.filter(d => !d.plants.length);
  const head = only
    ? (M.plants_with ? `${only} is missing ${msPl(M.gaps, 'detail', 'details')}.` : `${only} has every detail on this list.`)
    : M.plants_with ? `${M.plants_with} of the ${msPl(M.plants, 'plant', 'plants')} at ${placeName()} ${M.plants_with === 1 ? 'is' : 'are'} missing something (${msPl(M.gaps, 'gap', 'gaps')} in all).` : `Every plant at ${placeName()} has every detail on this list.`;
  return {
    title: 'Missing details',
    html: html`<h1>Missing details</h1>
    <p class="muted">Some pages need a detail about a plant to work for it. A plant without it is left out, or gets a guess. Fill them in here one after another; each one is saved to the plant's page like an edit, and shows in its Page history.</p>
    <div class="verdict-box" role="status"><p><strong>${head}</strong></p>
      ${only ? html`<p><a href="#/missing">Every plant</a> · <a href="#/plant/${enc(only)}">Back to ${only}</a></p>` : ''}</div>
    ${todo.length > 1 ? html`<nav class="ms-jumps noprint" aria-label="Details on this page"><ul>${todo.map(d => html`<li><a class="btn small ghost" href="#ms-${d.key}" data-act="msjump" data-to="ms-${d.key}">${d.title} (${d.plants.length})</a></li>`)}</ul></nav>` : ''}
    ${todo.map(d => html`<section class="blk" id="ms-${d.key}"><h2>${d.title} (${d.plants.length})</h2>
      <p class="hint">${d.why}</p>
      <ul class="jobs ms-list">${d.plants.map(p => jobRow(msRow(p), p.site || '', msControl(d, p)))}</ul></section>`)}
    ${done.length ? html`<section class="blk" id="ms-done"><h2>Filled in for every plant (${done.length})</h2>
      <ul>${done.map(d => html`<li><strong>${d.title}</strong>: ${d.why}</li>`)}</ul></section>` : ''}
    <p class="hint">A plant at another home is on that home's list: choose the home at the top. Archived plants are left out.</p>`,
  };
}
function msValue(key, v) {                      // what is typed, in the person's units, to what the plant page keeps
  v = String(v).trim().replace(',', '.');
  if (key === 'height_in') return String(lenIn(v));
  if (key === 'temp_damage_below') return String(Math.round(tIn(v)));
  return v;
}
Object.assign(formActs, {
  async msave(form) {
    if (!(await needName())) return;
    const key = form.dataset.key, code = form.dataset.code, v = form.elements.v.value;
    if (String(v).trim() === '') { form.elements.v.focus(); return; }
    if (key === 'height_in' && isNaN(+String(v).replace(',', '.'))) { toast('Type the height as a number, such as 14 or 14.5.', true); form.elements.v.focus(); return; }
    const field = key === 'water' ? 'water_every_days' : key;
    const sec = form.closest('section'), li = form.closest('li'), next = li && li.nextElementSibling, nextCode = next && next.dataset.code;
    await guard(async () => {
      let saved = true;
      try {
        await api('PUT', '/api/plants/' + enc(code), { base_version: +form.dataset.version, fields: { [field]: msValue(key, v) }, note: 'Filled in on Missing details' });
      } catch (e) {
        if (e.status !== 409) throw e;
        saved = false;
        toast(`${form.dataset.name} was changed by someone else just now, so nothing was saved. The list is up to date again: try once more.`, true);
      }
      if (saved) toast(`Saved: ${form.dataset.title} for ${form.dataset.name}`);
      const y = window.scrollY; await route(); window.scrollTo(0, y);
      // focus goes to the next plant in the same detail (the same one if nothing was saved), or the detail's heading if that was the last one
      const s = sec && document.getElementById(sec.id);
      const to = saved ? nextCode : code, sel = to && `#${sec.id} .job[data-code="${to}"]`;
      const f = (sel && document.querySelector(`${sel} select, ${sel} input, ${sel} a.btn`))
        || (s && s.querySelector('.job select, .job input, .job a.btn')) || (s && s.querySelector('h2')) || document.querySelector('main h1');
      if (f) { if (!f.matches('select, input, a')) f.setAttribute('tabindex', '-1'); f.focus({ preventScroll: false }); }
    });
  },
});
Object.assign(acts, {
  msjump(el) {
    const t = document.getElementById(el.dataset.to); if (!t) return;
    t.scrollIntoView({ block: 'start' }); const h = t.querySelector('h2'); if (h) { h.setAttribute('tabindex', '-1'); h.focus({ preventScroll: true }); }
  },
});
// What this module adds (features.js): the page #/missing, part of Plants (nav 'missing' is in no section, so Plants is marked) but with no link of its own in the top bar
// (a ninth link wraps the row); All plants links to it when anything is missing, and Search finds it by name.
addFeature({
  name: 'missing',
  pages: { missing: { view: viewMissing, nav: 'missing', label: 'Missing details', href: '#/missing' } },
  adds: {
    id: 'ms-link', match: parts => parts[0] === 'plants', anchor: '#g-title', where: 'afterend',
    load: async () => { const M = await api('GET', '/api/missing'); return M.plants_with ? M : null; },
    html: M => html`<p class="hint noprint" id="ms-link">${msPl(M.plants_with, 'plant is', 'plants are')} missing details that other pages use. <a href="#/missing">Missing details</a></p>`,
  },
});
