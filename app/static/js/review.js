// ---------- 1.37.0: a year in review ----------
// One page per year (#/review?year=2026), one card per plant: how its year went, from the logs the app already keeps.
'use strict';
let RV = { sort: 'worse', only: '' };
function rvLine(p) {
  const bits = [];
  if (p.new_this_year) bits.push('new this year');
  if (p.archived) bits.push('archived');
  if (p.health.trend === 'better') bits.push(`health ${p.health.start} → ${p.health.end}`);
  else if (p.health.trend === 'worse') bits.push(`health ${p.health.start} → ${p.health.end}`);
  else if (p.health.end) bits.push(`health ${p.health.end} all year`);
  if (p.moves.length) bits.push(`moved ${p.moves.length} time${p.moves.length === 1 ? '' : 's'}`);
  if (p.cold_nights) bits.push(`${p.cold_nights} cold night${p.cold_nights === 1 ? '' : 's'} outside below its damage point`);
  if (p.hot_days) bits.push(`${p.hot_days} day${p.hot_days === 1 ? '' : 's'} at or above its heat-damage temperature`);
  return bits.join('; ');
}
function rvCard(p, year) {
  const mark = p.health.trend === 'worse' || p.cold_nights >= 3 ? '■' : p.health.trend === 'better' ? '✓' : '●';
  const cls = p.health.trend === 'worse' || p.cold_nights >= 3 ? 'rv-bad' : p.health.trend === 'better' ? 'rv-good' : '';
  const ph = x => x ? html`<figure class="rv-ph"><img src="${thumbUrl(x.file)}" alt="${x.caption || p.name}" loading="lazy" width="120" height="120"><figcaption>${dayLong(x.added_at.slice(0, 10))}</figcaption></figure>` : '';
  return html`<article class="rv-card ${cls}" aria-labelledby="rv-${enc(p.code)}">
    <h3 id="rv-${enc(p.code)}"><span aria-hidden="true">${mark}</span> <a href="#/plant/${enc(p.code)}">${p.name}</a> <span class="muted">${p.code}</span></h3>
    <p>${rvLine(p) || 'A quiet year: no changes logged.'}</p>
    ${p.photos.n ? html`<div class="rv-phs">${ph(p.photos.first)}${ph(p.photos.last)}</div>` : ''}
    <ul class="rv-facts"><li>${p.photos.n} photo${p.photos.n === 1 ? '' : 's'}</li><li>${p.water} watering${p.water === 1 ? '' : 's'} logged</li><li>${p.fed} feeding${p.fed === 1 ? '' : 's'}</li>
      ${Object.entries(p.care).map(([k, n]) => html`<li>${n} ${k}</li>`)}${p.requests.asked ? html`<li>${p.requests.answered} of ${p.requests.asked} requests answered</li>` : ''}
      ${p.moves.length ? html`<li>${p.moves.map(m => `${m.from} → ${m.to} (${dayLong(m.at.slice(0, 10))})`).join('; ')}</li>` : ''}</ul></article>`;
}
async function viewReview(qs) {
  const year = qs.get('year') || '';
  const D = await api('GET', '/api/review' + (year ? '?year=' + enc(year) : ''));
  let list = D.plants.slice();
  if (RV.only === 'worse') list = list.filter(p => p.health.trend === 'worse' || p.cold_nights >= 3);
  else if (RV.only === 'better') list = list.filter(p => p.health.trend === 'better');
  else if (RV.only === 'new') list = list.filter(p => p.new_this_year);
  else if (RV.only === 'quiet') list = list.filter(p => !rvLine(p));
  const rank = p => (p.health.trend === 'worse' ? 0 : p.cold_nights >= 3 ? 1 : p.health.trend === 'better' ? 3 : 2);
  if (RV.sort === 'worse') list.sort((a, b) => rank(a) - rank(b) || a.code.localeCompare(b.code));
  else if (RV.sort === 'photos') list.sort((a, b) => b.photos.n - a.photos.n);
  else list.sort((a, b) => a.code.localeCompare(b.code));
  const T = D.totals, W = D.weather;
  return {
    title: `${D.year} in review`,
    html: html`<h1>${D.year} in review</h1>
    <p class="muted">How each plant's year went, from everything the app logged. Good for deciding what to keep, what to move and what to let go.</p>
    <div class="filters"><label class="f">Year<select data-act="rvyear">${D.years.map(y => html`<option value="${y}" ${y === D.year ? raw('selected') : ''}>${y}</option>`)}</select></label>
      <label class="f">Show<select data-act="rvonly"><option value="">Every plant (${D.plants.length})</option><option value="worse" ${RV.only === 'worse' ? raw('selected') : ''}>Had a hard year</option><option value="better" ${RV.only === 'better' ? raw('selected') : ''}>Got better</option><option value="new" ${RV.only === 'new' ? raw('selected') : ''}>New this year</option><option value="quiet" ${RV.only === 'quiet' ? raw('selected') : ''}>Quiet, nothing logged</option></select></label>
      <label class="f">Sort<select data-act="rvsort"><option value="worse" ${RV.sort === 'worse' ? raw('selected') : ''}>Hardest year first</option><option value="code" ${RV.sort === 'code' ? raw('selected') : ''}>By code</option><option value="photos" ${RV.sort === 'photos' ? raw('selected') : ''}>Most photographed first</option></select></label>
      </div><p class="row noprint"><button class="btn ghost" type="button" data-act="print">Print this review</button></p>
    <div class="verdict-box" role="status"><p><strong>${T.plants} plants in ${D.year}: ${T.new} new, ${T.archived} archived, ${T.better} got better, ${T.worse} got worse.</strong>
      ${T.photos} photos, ${T.water} waterings, ${T.fed} feedings, ${T.moves} moves and ${T.answered} requests answered. The weather at ${D.place}: ${W.days ? `${W.cold_nights} night${W.cold_nights === 1 ? '' : 's'} at or below ${tF(32)}${W.coldest != null ? ` (coldest ${tF(W.coldest)})` : ''} and ${W.hot_days} day${W.hot_days === 1 ? '' : 's'} above ${tF(86)}${W.hottest != null ? ` (hottest ${tF(W.hottest)})` : ''}, over ${W.days} days of history` : 'no weather history for this year'}.</p></div>
    ${list.length ? html`<h2 class="sr">Each plant's year</h2><div class="rv-grid">${list.map(p => rvCard(p, D.year))}</div>` : html`<p class="muted">No plants match.</p>`}
    <p class="hint">■ a hard year (health got worse, or 3 or more cold nights outside below its damage point); ✓ got better; ● steady. Cold nights and hot days count only while the plant was outside or on the porch, as far as the log knows.</p>`,
  };
}
Object.assign(changeActs, {
  rvyear(el) { go('#/review?year=' + enc(el.value)); },
  rvonly(el) { RV.only = el.value; route(); },
  rvsort(el) { RV.sort = el.value; route(); },
});

// ---------- 1.37.0: photos shared from the phone's share sheet ("Share → Plant record") ----------
// The service worker takes the share (a POST to /share), keeps the pictures in a cache and opens #/share. Here they are shown
// with a plant to choose; "Add" uploads them to that plant (or as unassigned photos). Android Chrome and Edge only.
async function sharedFiles() {
  try {
    const c = await caches.open('plantdb-share'), keys = await c.keys(), out = [];
    for (const k of keys) { const r = await c.match(k); const b = await r.blob(); out.push({ key: k.url, name: r.headers.get('X-Name') || 'photo.jpg', blob: b, url: URL.createObjectURL(b) }); }
    return out.sort((a, b) => a.key.localeCompare(b.key));
  } catch (e) { return []; }
}
async function viewShare() {
  const files = await sharedFiles(), plants = await api('GET', '/api/plants');
  const recent = plants.slice().sort((a, b) => (b.updated_at || '').localeCompare(a.updated_at || '')).slice(0, 8);
  const can = canChange();
  return {
    title: 'Shared photos',
    html: html`<h1>Photos shared with Plant record</h1>
    ${files.length ? html`<p>${files.length} photo${files.length === 1 ? '' : 's'} from the share sheet. Choose the plant they belong to and press Add.</p>
      <div class="share-grid">${files.map(f => html`<figure><img src="${f.url}" alt="${f.name}"><figcaption>${f.name}</figcaption></figure>`)}</div>
      ${can ? html`<form data-form="shareadd" class="f-grid"><label class="f">Plant<select name="plant"><option value="">No plant yet: keep them under Photos to assign later</option>
          <optgroup label="Recently changed">${recent.map(p => html`<option value="${p.code}">${p.code}  ${p.common_name}</option>`)}</optgroup>
          <optgroup label="Every plant">${plants.map(p => html`<option value="${p.code}">${p.code}  ${p.common_name}</option>`)}</optgroup></select></label>
        <label class="f">Caption<small>Optional, the same for all of them</small><input type="text" name="caption" maxlength="200"></label>
        <div class="row"><button class="btn" type="submit">Add the photo${files.length === 1 ? '' : 's'}</button><button class="btn ghost" type="button" data-act="sharedrop">Throw them away</button></div></form>` : html`<p class="notice">Changes are turned off for you, so these cannot be added. <button class="btn ghost" type="button" data-act="sharedrop">Throw them away</button></p>`}`
      : html`<p class="muted">Nothing shared right now. On an Android phone with the app added to the Home Screen, share a photo and choose <strong>Plants</strong>: it lands here, ready to add to a plant.</p>
        <p><a class="btn ghost" href="#/photos">Photos and the list to photograph</a></p>`}`,
  };
}
async function shareClear() { try { await caches.delete('plantdb-share'); } catch (e) { /* none */ } }
Object.assign(acts, {
  async sharedrop() { await shareClear(); toast('Thrown away'); go('#/plants'); },
});
Object.assign(formActs, {
  async shareadd(form) {
    if (!(await needName())) return;
    const files = await sharedFiles(); if (!files.length) { toast('Nothing to add', true); return; }
    const code = form.elements.plant.value, fd = new FormData();
    files.forEach(f => fd.append('files', new File([f.blob], f.name, { type: f.blob.type || 'image/jpeg' })));
    if (form.elements.caption.value.trim()) fd.append('caption', form.elements.caption.value.trim());
    toast('Uploading ' + files.length + ' photo(s)');
    await guard(async () => {
      await api('POST', code ? '/api/plants/' + enc(code) + '/photos' : '/api/photos', undefined, fd);
      await shareClear(); toast('Photos added');
      go(code ? '#/plant/' + enc(code) + '?sec=photos' : '#/photos');
    });
  },
});
