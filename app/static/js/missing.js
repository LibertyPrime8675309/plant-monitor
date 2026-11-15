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
  const form = (inner, unit) => html`<form class="ms-form" data-form="msave" data-code="${p.code}" data-key="${d.key}" data-field="${d.key === 'water' ? 'water_every_days' : d.fields[0]}" data-version="${p.version}" data-name="${p.name}" data-title="${d.title}">
    <label class="f" for="${id}">${d.title}${unit ? ` (${unit})` : ''}</label>
    <div class="ms-in">${inner}${save}</div></form>`;
  if (d.how === 'enum') return form(html`<select id="${id}" name="v" aria-label="${lbl}" required><option value="">Choose…</option>${d.options.map(o => html`<option>${o}</option>`)}</select>`);
  if (d.how === 'length') return form(html`<input id="${id}" name="v" type="text" inputmode="decimal" maxlength="8" required aria-label="${lbl + ', in ' + (lenU() === 'cm' ? 'centimetres' : 'inches')}">`, lenU());
  if (d.how === 'temp') return form(html`<input id="${id}" name="v" type="number" step="1" min="${tU() === '°C' ? -50 : -60}" max="${tU() === '°C' ? 65 : 150}" required aria-label="${lbl + ', in degrees ' + (tU() === '°C' ? 'Celsius' : 'Fahrenheit')}">`, tU());
  if (d.how === 'days') return form(html`<input id="${id}" name="v" type="number" step="1" min="1" max="60" required aria-label="${lbl + ', every so many days'}">`, 'every so many days');
  if (d.how === 'text') return form(html`<input id="${id}" name="v" type="text" maxlength="200" required aria-label="${lbl}" placeholder="Bright shade, morning sun">`);
  if (d.how === 'date') return form(html`<input id="${id}" name="v" type="date" min="1900-01-01" max="${todayStr()}" required aria-label="${lbl}">`);
  if (d.how === 'page') return html`<a class="btn small ghost" href="#/plant/${enc(p.code)}" aria-label="${'Open its page: ' + p.name + ', to write down its potting mix'}">Open its page</a>`;
  return html`<a class="btn small ghost" href="#/plant/${enc(p.code)}/edit" aria-label="${'Open Edit for ' + p.name}">Open Edit</a>`;
}
// "Not now": you do not know this yet, so the plant leaves this one list for a month
const msLater = (d, p) => html`<button class="btn small ghost ms-later" type="button" data-act="mslater" data-code="${p.code}" data-key="${d.key}" data-name="${p.name}" data-title="${d.title}" aria-label="${'Not now: ' + d.title + ' for ' + p.name}">Not now</button>`;
const MS_STEP = 10, MS_SHOW = {};          // a long list shows ten plants at a time; how many each detail shows is kept while the app is open
async function viewMissing(parts, qs) {
  const only = qs && qs.get('plant');
  const M = await api('GET', '/api/missing' + (only ? '?plant=' + enc(only) : ''));
  const todo = M.details.filter(d => d.plants.length), done = M.details.filter(d => !d.plants.length && !d.later), can = canChange();
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
      <ul class="jobs ms-list">${d.plants.slice(0, only ? d.plants.length : MS_SHOW[d.key] || MS_STEP).map(p => jobRow(msRow(p), p.site || '', html`${msControl(d, p)}${can ? msLater(d, p) : ''}`))}</ul>
      ${!only && d.plants.length > (MS_SHOW[d.key] || MS_STEP) ? html`<p class="noprint"><button class="btn small ghost" type="button" data-act="msmore" data-key="${d.key}" aria-label="${'Show ' + Math.min(MS_STEP, d.plants.length - (MS_SHOW[d.key] || MS_STEP)) + ' more: ' + d.title}">Show ${Math.min(MS_STEP, d.plants.length - (MS_SHOW[d.key] || MS_STEP))} more</button>
        <span class="muted">Showing ${MS_SHOW[d.key] || MS_STEP} of ${d.plants.length}.</span></p>` : ''}
      ${d.later ? html`<p class="ms-off"><span>${msPl(d.later, 'plant is', 'plants are')} left off this list for now (Not now, ${M.later_days} days).</span> ${can ? html`<button class="btn small ghost" type="button" data-act="msback" data-key="${d.key}" aria-label="${'Show them again: ' + d.title}">Show them again</button>` : ''}</p>` : ''}</section>`)}
    ${M.details.filter(d => !d.plants.length && d.later).map(d => html`<p class="ms-off" id="ms-off-${d.key}"><span><strong>${d.title}:</strong> ${msPl(d.later, 'plant is', 'plants are')} left off for now.</span> ${can ? html`<button class="btn small ghost" type="button" data-act="msback" data-key="${d.key}" aria-label="${'Show them again: ' + d.title}">Show them again</button>` : ''}</p>`)}
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
    const field = form.dataset.field;                    // the plant field the box fills (a detail's key is not always a field's name: Light is light_summary)
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
async function msRedraw(focusSel) {
  const y = window.scrollY; await route(); window.scrollTo(0, y);
  const f = (focusSel && document.querySelector(focusSel)) || document.querySelector('main h1');
  if (f) { if (!f.matches('select, input, a, button')) f.setAttribute('tabindex', '-1'); f.focus({ preventScroll: true }); }
}
Object.assign(acts, {
  async msmore(el) {
    const key = el.dataset.key, had = MS_SHOW[key] || MS_STEP; MS_SHOW[key] = had + MS_STEP;
    await msRedraw(`#ms-${key} .ms-list > li:nth-child(${had + 1}) :is(select, input, a.btn)`);      // on to the first of the new ones
  },
  async mslater(el) {
    if (!(await needName())) return;
    const key = el.dataset.key, li = el.closest('li'), next = li && li.nextElementSibling, nextCode = next && next.dataset.code;
    await guard(async () => {
      await api('POST', '/api/missing/later', { plant: el.dataset.code, key });
      toast(`Not now: ${el.dataset.title} for ${el.dataset.name}. It comes back to this list in a month.`);
      await msRedraw(nextCode ? `#ms-${key} .job[data-code="${nextCode}"] :is(select, input, a.btn)` : `#ms-${key} h2, #ms-off-${key} button`);
    });
  },
  async msback(el) {
    if (!(await needName())) return;
    const key = el.dataset.key;
    await guard(async () => { await api('DELETE', '/api/missing/later', { key }); toast('They are on the list again.'); await msRedraw(`#ms-${key} h2`); });
  },
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
  adds: [{
    id: 'ms-link', match: parts => parts[0] === 'plants', anchor: '#g-title', where: 'afterend',
    load: async () => { const M = await api('GET', '/api/missing'); return M.plants_with ? M : null; },
    html: M => html`<p class="hint noprint" id="ms-link">${msPl(M.plants_with, 'plant is', 'plants are')} missing details that other pages use. <a href="#/missing">Missing details</a></p>`,
  }, {
    // on a plant's own page, under its name and care buttons: what it is missing, with a link to fill it in
    id: 'ms-plant', match: parts => parts[0] === 'plant' && parts[1] && parts[2] !== 'edit', anchor: '.quick', where: 'afterend',
    load: async parts => { const M = await api('GET', '/api/missing?plant=' + enc(decodeURIComponent(parts[1]))); return M.gaps ? M : null; },
    html: (M, parts) => { const t = M.details.filter(d => d.plants.length).map(d => d.title.toLowerCase());
      return html`<p class="hint noprint" id="ms-plant"><span>Missing: ${t.length > 1 ? t.slice(0, -1).join(', ') + ' and ' + t[t.length - 1] : t[0]}.</span> <a href="#/missing?plant=${enc(decodeURIComponent(parts[1]))}">Fill ${t.length > 1 ? 'them' : 'it'} in</a></p>`; },
  }],
});
