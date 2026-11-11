/* Plant record front end: pests that eat plants (prototype proto/browse-risk; plantdb/browse.py). One of the files loaded in order
   by index.html (js/manifest.json); they share one scope. Plain JavaScript, no inline handlers.
   - The page #/browse (not a link in the top bar, which would wrap; each plant's page links to it and Search finds it): every plant
     here sorted by how likely rabbits, rats, mice and deer are to eat it, with the reason in words, the pests seen eating them, and
     what to do about it.
   - Change the risk of one plant (the plant field browse_risk; empty means the usual for its kind) and log a sighting: who ate it,
     what they did, when, with pictures as evidence (pictures of the plant already in the record, or new ones).
   - On Today, in the evening: the plants outside to cover tonight.
   The risk is always written out, never carried by colour alone. */
'use strict';

const BR_ORDER = ['High', 'Moderate', 'Low', 'Unknown'];
const BR_HEAD = { High: 'Most likely to be eaten', Moderate: 'Some risk', Low: 'Usually left alone', Unknown: 'Not known yet' };
const BR_ICON = { High: '▲ ', Moderate: '◆ ', Low: '● ', Unknown: '? ' };       // a shape as well as words
const BR_DONE = 'plantdb.browsedone';                                              // the day "Done for tonight" was pressed (this device only)
const brPl = (n, one, many) => `${n} ${n === 1 ? one : many}`;
const brDay = s => { const d = parseYmd(s), m = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']; return `${m[d.getMonth()]} ${d.getDate()}`; };
const brSeenWords = p => !p.seen.count ? '' : `Seen eaten ${brPl(p.seen.count, 'time', 'times')} in the last ${BR_DAYS} days${p.seen.pests.length ? ' (' + p.seen.pests.join(', ').toLowerCase() + ')' : ''}, last on ${brDay(p.seen.last)}.`;
let BR_DAYS = 60;
const brBase = p => p.base === 'Unknown' ? 'not known' : p.base.toLowerCase();
const brWhy = p => p.raised ? html`<strong>${BR_ICON[p.risk]}${p.word}.</strong> <strong>Raised because it was eaten ${brPl(p.seen.count, 'time', 'times')} in the last ${BR_DAYS} days</strong> (${p.source === 'you' ? 'you set it to ' : 'the usual for this kind of plant is '}${brBase(p)}). It goes back when those sightings are older than ${BR_DAYS} days. <span class="muted br-usual">${p.why}</span>`
  : p.source === 'you' ? html`<strong>${BR_ICON[p.risk]}${p.word}</strong>, as you set it. <span class="muted br-usual">The usual for this kind of plant: ${p.usual === 'Unknown' ? 'not known' : p.usual.toLowerCase()}.</span> ${p.why}`
  : html`<strong>${BR_ICON[p.risk]}${p.word}.</strong> ${p.why}`;
const brBtns = p => html`<button class="btn small ghost" type="button" data-act="brseen" data-code="${p.code}" data-name="${p.name}" aria-label="${'Log a pest seen eating ' + p.name}">Log a sighting</button>
  <button class="btn small ghost" type="button" data-act="brrisk" data-code="${p.code}" data-name="${p.name}" aria-label="${'Change the pest risk of ' + p.name}">Change risk</button>`;
const brRow = p => jobRow({ code: p.code, common_name: p.name, photo: p.photo }, html`${brWhy(p)} ${brSeenWords(p) ? html`<strong class="br-seen">${brSeenWords(p)}</strong>` : ''}`, brBtns(p));
const brThumbs = x => x.photos.length ? html`<span class="br-pics">${x.photos.map(f => html`<a href="${photoUrl(f)}" target="_blank" rel="noopener"><img src="${thumbUrl(f)}" alt="${'Picture of ' + (x.name || x.plant) + ' eaten, ' + brDay(x.seen_on)}" width="64" height="64" loading="lazy"></a>`)}</span>` : '';
const brSighting = x => html`<li class="br-sight"><div><strong>${brDay(x.seen_on)}.</strong> <a href="#/plant/${enc(x.plant)}">${x.name || x.plant}</a>: ${x.pest.toLowerCase()}${x.damage ? ', ' + x.damage.toLowerCase() : ''}.
  ${x.note ? html`${x.note} ` : ''}<span class="muted">Logged by ${x.by || 'someone'}.</span>
  <button class="btn small ghost" type="button" data-act="brdel" data-id="${x.id}" aria-label="${'Remove the sighting of ' + (x.name || x.plant) + ' on ' + brDay(x.seen_on)}">Remove</button></div>${brThumbs(x)}</li>`;

async function brAfter() { await route(); }                      // draw the page or plant again with the new answers

// ---- Log a sighting: who, what, when, with pictures as evidence ----
async function brSeenDialog(code, name) {
  if (!(await needName())) return;
  const B = await api('GET', '/api/browse?plant=' + enc(code)), pl = await api('GET', '/api/plants/' + enc(code));
  const photos = (pl.photos || []).slice(0, 24);
  const r = await modal(html`<form method="dialog" class="br-dlg"><h2>A pest ate ${name}</h2>
    <label class="f">What day<input type="date" name="day" value="${todayStr()}" max="${todayStr()}"></label>
    <label class="f">Who did it<select name="pest">${B.pests.map(x => html`<option ${x === 'Not sure' ? raw('selected') : ''}>${x}</option>`)}</select></label>
    <label class="f">What was damaged<select name="damage"><option value="">Not said</option>${B.damage.map(x => html`<option>${x}</option>`)}</select></label>
    <label class="f">Note (optional)<textarea name="note" rows="2" maxlength="500"></textarea></label>
    <fieldset><legend>Pictures as evidence (optional)</legend>
      ${photos.length ? html`<p class="hint">Tick pictures of ${name} that are already in the record:</p><div class="br-pick">${photos.map((p, i) => html`<label class="chk"><input type="checkbox" name="pic" value="${p.file}"> <img src="${thumbUrl(p.file)}" alt="" width="64" height="64"> <span>Picture ${i + 1}${p.caption ? ': ' + p.caption : ''}</span></label>`)}</div>` : html`<p class="hint">This plant has no pictures yet. Add one below.</p>`}
      <label class="f">Add new pictures<input type="file" name="files" accept="image/*" multiple></label>
      <p class="hint">New pictures are kept with this sighting. They are not added to the plant's own pictures.</p></fieldset>
    <div class="row"><button class="btn" value="ok">Save sighting</button><button class="btn ghost" value="cancel">Cancel</button></div></form>`);
  if (r !== 'ok') return;
  const f = dlg.querySelector('form');
  const day = f.elements.day.value, pest = f.elements.pest.value, damage = f.elements.damage.value, note = f.elements.note.value;
  const picks = [...f.querySelectorAll('[name=pic]:checked')].map(x => x.value), files = [...f.elements.files.files];
  await guard(async () => {
    const sent = [];
    for (const file of files) { const fd = new FormData(); fd.append('file', file, file.name); sent.push((await api('POST', '/api/browse/photo', undefined, fd)).file); }
    await api('POST', '/api/browse/sightings', { plant: code, seen_on: day, pest, damage, note, photos: picks.concat(sent) });
    toast(`${name}: sighting saved` + (picks.length + sent.length ? ` with ${brPl(picks.length + sent.length, 'picture', 'pictures')}` : ''));
    await brAfter();
  });
}
// ---- Change the risk of one plant ----
async function brRiskDialog(code, name) {
  if (!(await needName())) return;
  const [B, pl] = await Promise.all([api('GET', '/api/browse?plant=' + enc(code)), api('GET', '/api/plants/' + enc(code))]);
  const p = B.plants[0]; if (!p) return;
  const cur = p.own || '';
  const r = await modal(html`<form method="dialog" class="br-dlg"><h2>Pest risk: ${name}</h2>
    <label class="f">How likely is it to be eaten<select name="risk">
      <option value="" ${cur === '' ? raw('selected') : ''}>The usual for this kind of plant (${p.usual === 'Unknown' ? 'not known' : p.usual.toLowerCase()})</option>
      ${B.risks.map(x => html`<option value="${x}" ${cur === x ? raw('selected') : ''}>${x === 'Low' ? 'Low: usually left alone' : x === 'Moderate' ? 'Some risk' : 'High: a favourite'}</option>`)}</select></label>
    <p class="hint">${p.why || 'Nothing is known about this kind of plant yet.'} Set it by hand once you see what really gets eaten. Whatever you set, a plant seen eaten is raised for ${B.days} days: once to some risk, three times to high.</p>
    <div class="row"><button class="btn" value="ok">Save</button><button class="btn ghost" value="cancel">Cancel</button></div></form>`);
  if (r !== 'ok') return;
  const v = dlg.querySelector('[name=risk]').value;
  if (v === cur) return;
  await guard(async () => {
    const x = await api('PUT', '/api/plants/' + enc(code), { base_version: pl.version, base_values: { browse_risk: pl.browse_risk || '' }, fields: { browse_risk: v } });
    if (x.conflicts) toast('Someone else changed this plant too. Their other changes are kept.');
    toast(`${name}: ${v ? 'pest risk set to ' + v.toLowerCase() : 'back to the usual for its kind'}`);
    await brAfter();
  });
}
Object.assign(acts, {
  async brseen(el) { await brSeenDialog(el.dataset.code, el.dataset.name); },
  async brrisk(el) { await brRiskDialog(el.dataset.code, el.dataset.name); },
  async brdel(el) {
    if (!(await needName())) return;
    if (!(await confirmBox('Remove this sighting?', 'It leaves the list and the plant’s count. Its pictures are kept on the computer.', 'Remove it', true))) return;
    await guard(async () => { await api('DELETE', '/api/browse/sightings/' + el.dataset.id); toast('Sighting removed'); await brAfter(); });
  },
  brdone(el) { try { localStorage.setItem(BR_DONE, todayStr()); } catch (e) { /* this visit only */ } const b = document.getElementById('today-browse'); if (b) b.remove(); toast('Done for tonight'); },
});

async function viewBrowse() {
  const B = await api('GET', '/api/browse');
  BR_DAYS = B.days;
  const by = k => B.plants.filter(p => p.risk === k);
  const C = B.counts, S = B.sightings || [];
  return {
    title: 'Pests that eat plants',
    html: html`<h1>Pests that eat plants</h1>
    <p class="muted">Rabbits, rats, mice and deer choose plants that are soft, tasty and have no defence. This sorts your plants by that, from the kind of plant, unless you have set a plant's risk yourself. The usual comes from gardeners' and extension-service knowledge, not a test on your garden, and a plant you log as eaten is raised (once to some risk, three times to high) for ${B.days} days: a hungry animal eats almost anything, and a plant that is "usually left alone" is not safe if nothing else is on offer.</p>
    <div class="verdict-box" role="status"><p><strong>${C.High} most likely to be eaten, ${C.Moderate} with some risk, ${C.Low} usually left alone${C.Unknown ? `, ${C.Unknown} not known yet` : ''}.</strong></p></div>
    <section class="blk" id="br-seen"><h2>Seen eating, last ${B.days} days (${S.length})</h2>
      ${S.length ? html`<p>${Object.entries(B.by_pest).map(([k, n]) => `${k} ${n}`).join(', ')}. Logging each time shows who it is and which plants they go for.</p>
        <ul class="br-sights">${S.map(brSighting)}</ul>` : html`<p class="muted">Nothing logged. When you find chewed leaves, droppings or an animal at a plant, press <strong>Log a sighting</strong> on that plant below, and add a picture as evidence.</p>`}</section>
    ${BR_ORDER.map(k => by(k).length ? html`<section class="blk" id="br-${k.toLowerCase()}"><h2>${BR_HEAD[k]} (${by(k).length})</h2><ul class="jobs">${by(k).map(brRow)}</ul></section>` : '')}
    <section class="blk" id="br-plan"><h2>What to do</h2>
      <ul class="rp-list">
        <li>Put the high-risk plants in the middle of a group of pots and ring them with plants that are usually left alone (aroids, aloes, crown of thorns).</li>
        <li>Cover the high-risk plants that matter most with a wire cloche or a frame of hardware cloth (small mesh, about half an inch). Rats and mice climb, so a cover with a closed top works better than a low fence.</li>
        <li>Raise pots off the ground on a stand, and keep cactus bases clear of soil, where mice gnaw.</li>
        <li>Look for droppings and chew marks to see who it is: rabbit droppings are round pellets and cuts are clean at an angle; rodents leave small gnawed edges and smaller droppings. Log what you find with a picture.</li>
        <li>Plants animals dislike for their smell, such as lavender, rosemary, sage, thyme, marigolds, chives and potted mint, help a little next to the plants you want to protect. They are not a fence.</li></ul></section>`,
  };
}
// Today, in the evening: what to cover tonight
const brDoneToday = () => { try { return localStorage.getItem(BR_DONE) === todayStr(); } catch (e) { return false; } };
addFeature({
  name: 'browse',
  // No link in the top bar (the row would wrap); each plant's page links to it and Search finds it.
  pages: { browse: { view: viewBrowse, nav: 'plants', label: 'Pests that eat plants', href: '#/browse' } },
  today: {
    id: 'today-browse', order: 66,                                   // after turn the pots (65), before repotting (68)
    load: async () => {
      if (brDoneToday()) return null;
      const B = await api('GET', '/api/browse?tonight=1');
      BR_DAYS = B.days;
      return B.evening && B.tonight.length ? B : null;
    },
    jump: B => `Cover (${B.tonight.length})`,
    html: B => html`<section class="blk" id="today-browse"><h2>Cover tonight (${B.tonight.length})</h2>
      <p>Rabbits, rats and mice feed at night. These plants outside are the ones most likely to be eaten, or were eaten in the last two weeks. Cover them with a wire cloche or hardware cloth, or move them under cover.</p>
      <ul class="jobs">${B.tonight.map(brRow)}</ul>
      <p><button class="btn small" type="button" data-act="brdone">Done for tonight</button> <a class="btn small ghost" href="#/browse">All plants by pest risk</a></p></section>`,
  },
  adds: {
    id: 'br-plant',
    match: parts => parts[0] === 'plant' && parts[1] && parts[2] !== 'edit',
    anchor: main => { const b = main.querySelector('.quick-btns'); return b && b.parentElement; }, where: 'beforeend',
    load: async parts => {
      if (!CUR || CUR.p.code !== parts[1]) return null;
      const B = await api('GET', '/api/browse?plant=' + enc(parts[1]));
      BR_DAYS = B.days;
      const p = B.plants[0]; if (!p) return null;
      return Object.assign(p, { sightings: await api('GET', '/api/browse/sightings?plant=' + enc(parts[1])) });
    },
    html: p => html`<div class="hint br-plant" id="br-plant"><p>Eaten by pests: ${brWhy(p)} ${brSeenWords(p) ? html`<strong>${brSeenWords(p)}</strong>` : ''}</p>
      <p>${brBtns(p)} <a href="#/browse">All plants by pest risk</a></p>
      ${p.sightings.length ? html`<ul class="br-sights">${p.sightings.slice(0, 5).map(x => brSighting(Object.assign(x, { name: p.name })))}</ul>` : ''}</div>`,
  },
});
