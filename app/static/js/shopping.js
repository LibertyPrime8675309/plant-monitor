/* Plant record front end: the wishlist, Shopping, the stores and the shopping list for a store visit. Split out of discover.js in 1.57.0 (review item 25); the scripts load in the order js/manifest.json
   gives and share one scope, so a function here may call any other. Plain JavaScript, no inline handlers (the content policy forbids them). */
'use strict';

// ---------- 1.22.0: the wishlist (#/wishlist) ----------
let WL = [];
async function viewWishlist() {
  const wl = await api('GET', '/api/wishlist');
  WL = wl.wishlist.filter(w => (w.kind || 'plant') === 'plant');        // 1.30.0: supplies are on Shopping only
  const want = WL.filter(w => w.status === 'want'), got = WL.filter(w => w.status === 'got');
  const money = n => n == null ? '' : '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const item = (w, i) => html`<li class="wl-item"><h3><a href="${spHref(w.name)}">${w.common_name || w.name}</a></h3>
    ${w.common_name ? html`<p class="latin">${w.name}</p>` : ''}
    ${w.yours && w.yours.length ? html`<p><span class="tag tag-yours">You have it: ${w.yours.join(', ')}</span></p>` : ''}
    ${w.status === 'want' ? html`<div class="wl-price">
      ${w.offers && w.offers.best ? html`<p><strong>Cheapest now:</strong> ${money(w.offers.best.price)} at ${w.offers.best.shop_name}: <a href="${w.offers.best.url}" target="_blank" rel="noopener noreferrer">${w.offers.best.title}</a></p>` : ''}
      <p>${w.offers && w.offers.count ? `In stock at ${w.offers.shops} shop${w.offers.shops === 1 ? '' : 's'} (${w.offers.count} listing${w.offers.count === 1 ? '' : 's'}).` : wl.checked ? 'Not found at the shops checked.' : 'The shops have not been checked yet.'}
        <strong>Alerts:</strong> ${[w.max_price != null ? `${money(w.max_price)} or less` : '', w.alert_stock ? 'when it is in stock' : ''].filter(Boolean).join('; ') || 'none set (Edit to add one)'}.</p>
      <p class="hint">Searching for: ${(w.terms || []).join('; ') || 'nothing (Edit to add search words)'}.</p>
      <details class="wl-offers" data-wish="${w.name}"><summary>Every listing found, with past prices</summary><div class="wl-offers-box"><p class="loading">Loading</p></div></details></div>` : ''}
    ${w.where_seen ? html`<p><strong>Where to find it:</strong> ${w.where_seen}</p>` : ''}
    ${w.notes ? html`<p class="pl">${w.notes}</p>` : ''}
    <p class="hint">Added by ${w.added_by} on ${when(w.added_at)}.</p>
    <div class="row wl-acts"><button class="btn small" type="button" data-act="wlgot" data-i="${i}">${w.status === 'got' ? 'Move back to wanted' : 'Got it'}</button>
      <button class="btn ghost small" type="button" data-act="wledit" data-name="${w.name}">Edit, and set alerts</button>
      <button class="btn danger small" type="button" data-act="wlrm" data-i="${i}">Take it off the list</button></div></li>`;
  const al = (wl.alerts || []).filter(a => WL.some(w => w.name === a.wish));
  return {
    title: 'Wishlist',
    html: html`<p class="crumb"><a href="#/library">Back to the library</a></p><h1>Wishlist</h1>
    <p>Plants (or fungi) you would like to have or find. Add one from its page in the <a href="#/library">library</a>. Everyone you have given access to the app sees this list.</p>
    <p class="notice" role="note">The stores, prices and alerts are on <a href="#/shopping">Shopping</a>${al.length ? html`, with <strong>${al.length} alert${al.length === 1 ? '' : 's'}</strong> waiting` : ''}. ${wl.checked ? `The stores were last checked ${when(wl.checked)}.` : ''}</p>
    <h2>Wanted (${want.length})</h2>${want.length ? html`<ul class="wl-list">${want.map(w => item(w, WL.indexOf(w)))}</ul>` : html`<p class="muted">Nothing wanted yet. Open a species in the library and press "Add to my wishlist".</p>`}
    ${got.length ? html`<h2>Got them (${got.length})</h2><ul class="wl-list">${got.map(w => item(w, WL.indexOf(w)))}</ul>` : ''}`,
  };
}
let WLSHOPS = null, WLBADGE = 0;
async function wlBadge() {           // 1.27.0: the number of wishlist alerts beside Library in the top bar (checked at most once a minute)
  if (Date.now() - WLBADGE < 60000) return;
  WLBADGE = Date.now();
  let n = 0; try { n = (await api('GET', '/api/wishlist/alerts')).alerts.length; } catch (e) { return; }
  const a = document.querySelector('#main-nav a[data-sec=discover]'), w = document.querySelector('#sub-nav a[data-nav=shopping]');
  if (w) { let bw = w.querySelector('.nav-badge'); if (!n) { if (bw) bw.remove(); } else { if (!bw) { bw = document.createElement('span'); bw.className = 'nav-badge'; w.append(bw); } bw.innerHTML = rend(html` <span aria-hidden="true">(${n})</span><span class="sr">, ${n} shopping alert${n === 1 ? '' : 's'}</span>`); } }
  if (!a) return;
  let b = a.querySelector('.nav-badge');
  if (!n) { if (b) b.remove(); return; }
  if (!b) { b = document.createElement('span'); b.className = 'nav-badge'; a.append(b); }
  b.innerHTML = rend(html` <span aria-hidden="true">(${n})</span><span class="sr">, ${n} shopping alert${n === 1 ? '' : 's'}</span>`);
}
function wlAlertsHtml(al, today) {
  return html`<ul class="wl-alert-list">${al.map(a => html`<li><span class="tag ${a.kind === 'price' ? 'tag-yours' : ''}">${a.kind === 'price' ? 'Price' : 'In stock'}</span>
      ${a.url ? html`<a href="${a.url}" target="_blank" rel="noopener noreferrer">${a.text}</a>` : a.text} <small class="muted">${when(a.created_at)}</small>
      <button class="btn ghost small" type="button" data-act="wldismiss" data-id="${a.id}">Dismiss</button></li>`)}</ul>
    <div class="row">${al.length > 1 ? html`<button class="btn ghost small" type="button" data-act="wldismiss" data-id="all">Dismiss them all</button>` : ''}${today ? html`<a class="btn ghost small" href="#/shopping">Open Shopping</a>` : ''}</div>`;
}
async function wlPoll() {
  const msg = () => document.getElementById('wl-check-msg');
  for (let n = 0; n < 900 && msg(); n++) {
    let r; try { r = await api('GET', '/api/wishlist/check'); } catch (e) { return; }
    if (!r.busy) { if (msg()) { toast('Shops checked'); WLBADGE = 0; await route(); } return; }
    if (msg()) msg().textContent = `Checking ${r.now || 'the shops'} (${r.done + 1} of ${r.total})…`;
    await new Promise(res => setTimeout(res, 2000));
  }
}
document.addEventListener('toggle', async e => {         // the listings for one entry, loaded when opened
  const d = e.target; if (!d.matches || !d.matches('details.wl-offers') || !d.open || d.dataset.loaded) return;
  d.dataset.loaded = '1';
  const box = d.querySelector('.wl-offers-box');
  try {
    const r = await api('GET', '/api/wishlist/offers?name=' + enc(d.dataset.wish));
    const money = n => n == null ? 'no price shown' : '$' + Number(n).toFixed(2);
    box.innerHTML = rend(r.offers.length ? html`<ul class="wl-offer-list">${r.offers.map(o => html`<li class="${o.gone ? 'muted' : ''}">
        <strong>${money(o.price)}</strong>${o.unit ? html` (${'$' + Number(o.unit.per).toFixed(2)} a ${o.unit.unit})` : ''} at <a href="#/store/${enc(o.shop)}">${o.shop_name}</a>: <a href="${o.url}" target="_blank" rel="noopener noreferrer">${o.title}</a>
        ${o.gone ? html` <span class="tag">No longer listed</span>` : o.available ? '' : html` <span class="tag">Out of stock</span>`}
        ${o.detail ? html`<br><small>${o.detail}</small>` : ''}
        ${o.history.length > 1 ? html`<br><small>Past: ${o.history.slice(-6).map(h => `${when(h.at)} ${h.available ? money(h.price) : 'gone or out of stock'}`).join('; ')}</small>` : ''}
        <br><small class="muted">First seen ${when(o.first_seen)}, last seen ${when(o.last_seen)}</small></li>`)}</ul>` : html`<p class="muted">Nothing found yet.</p>`);
  } catch (err) { box.innerHTML = rend(html`<p class="muted">${err.message}</p>`); }
}, true);
Object.assign(acts, {
  async wlcheck(el) {
    if (!(await needName())) return;
    el.disabled = true;
    await guard(async () => { await api('POST', '/api/wishlist/check'); wlPoll(); });
  },
  async wldismiss(el) {
    if (!(await needName())) return;
    await guard(async () => { await api('POST', '/api/wishlist/alerts', el.dataset.id === 'all' ? { all: true } : { id: +el.dataset.id }); toast('Dismissed'); WLBADGE = 0; await route(); });
  },
  async shopedit(el) {
    const s = WLSHOPS && WLSHOPS.shops.find(x => x.key === el.dataset.key); if (!s) return;
    const r = await modal(html`<form method="dialog"><h2>${s.name}</h2>
      <label class="f">Web address<input type="url" name="url" maxlength="300" value="${s.url}"></label>
      <label class="f">More pages to read<small>For a shop without an online store: the pages that list its plants, one per line</small><textarea name="pages" rows="5">${s.pages.join('\n')}</textarea></label>
      <div class="row"><button class="btn" value="ok">Save changes</button><button class="btn ghost" value="cancel">Cancel</button></div></form>`);
    if (r !== 'ok') return;
    await guard(async () => { await api('PUT', '/api/shops', { key: s.key, url: dlg.querySelector('[name=url]').value, pages: dlg.querySelector('[name=pages]').value }); toast('Saved'); await route(); });
  },
  async shoprm(el) {
    const s = WLSHOPS && WLSHOPS.shops.find(x => x.key === el.dataset.key); if (!s) return;
    if (!(await confirmBox('Remove this shop?', `${s.name} is no longer checked, and what it had is forgotten.`, 'Remove the shop', true))) return;
    await guard(async () => { await api('DELETE', '/api/shops?key=' + enc(s.key)); toast('Removed'); await route(); });
  },
  async shopkeyrm(el) {
    if (!(await confirmBox('Remove the key?', `${el.dataset.shop === 'ebay' ? 'eBay' : 'Etsy'} is not searched again until a key is saved.`, 'Remove it', true))) return;
    await guard(async () => { await api('DELETE', '/api/shops/keys', { shop: el.dataset.shop }); toast('Removed'); await route(); });
  },
});
Object.assign(changeActs, {
  async shopon(el) { await guard(async () => { await api('PUT', '/api/shops', { key: el.dataset.key, enabled: el.checked }); toast(el.checked ? 'Turned on' : 'Turned off'); }); },
  async shophours(el) { await guard(async () => { await api('PUT', '/api/shops', { hours: el.value }); toast('Saved'); }); },
});
Object.assign(formActs, {
  async shopadd(form) {
    const e = form.elements;
    await api('POST', '/api/shops', { name: e.name.value, url: e.url.value, local: e.local.checked, online: e.online ? e.online.checked : false,
      home_id: e.home_id ? e.home_id.value : '', phone: e.phone ? e.phone.value : '', address: e.address ? e.address.value : '' });
    toast('Store added. It is read on the next check.'); route();
  },
  async shopkeys(form) {
    const b = { shop: form.dataset.shop }; [...form.elements].forEach(x => { if (x.name) b[x.name] = x.value.trim(); });
    await api('PUT', '/api/shops/keys', b); toast('Saved'); route();
  },
});
Object.assign(acts, {
  async wlgot(el) {
    const w = WL[+el.dataset.i]; if (!w || !(await needName())) return;
    await guard(async () => { await api('PUT', '/api/wishlist', { name: w.name, status: w.status === 'got' ? 'want' : 'got' }); toast(w.status === 'got' ? 'Moved back to wanted' : 'Marked as got it'); await route(); });
  },
  async wlrm(el) {
    const w = WL[+el.dataset.i]; if (!w || !(await needName())) return;
    if (!(await confirmBox('Take it off the wishlist?', `${w.common_name || w.name} and its notes leave the list.`, 'Take it off the list', true))) return;
    await guard(async () => { await api('DELETE', '/api/wishlist', { name: w.name }); toast('Taken off the wishlist'); await route(); });
  },
  async wledit(el) {
    if (!(await needName())) return;
    const all = (await api('GET', '/api/wishlist')).wishlist, w = all.find(x => x.name === el.dataset.name); if (!w) return;
    const r = await modal(html`<form method="dialog"><h2>Edit: ${w.common_name || w.name}</h2>
      <label class="f">Where to find it<small>A nursery, a website, a friend's garden</small><input type="text" name="where" maxlength="300" value="${w.where_seen}"></label>
      <label class="f">Notes<textarea name="notes" rows="4" maxlength="2000">${w.notes}</textarea></label>
      <label class="f">Status<select name="status"><option value="want" ${w.status === 'want' ? raw('selected') : ''}>Wanted</option><option value="got" ${w.status === 'got' ? raw('selected') : ''}>Got it</option></select></label>
      <fieldset class="opt-group"><legend>Shops and alerts</legend>
        <label class="f">Search the shops for<small>One search per line, such as a variety: Monstera Thai Constellation. Left empty, its common and scientific names are used.</small><textarea name="search" rows="2" maxlength="300">${w.search_words || ''}</textarea></label>
        <label class="f">Alert me when the price is at or under<small>In dollars, such as 25. Shipping is not included. Leave empty for no price alert.</small><input type="number" name="max_price" min="0.01" step="0.01" inputmode="decimal" value="${w.max_price == null ? '' : w.max_price}"></label>
        <label class="chk"><input type="checkbox" name="alert_stock" ${w.alert_stock ? raw('checked') : ''}> Alert me when a shop has it in stock</label></fieldset>
      <div class="row"><button class="btn" value="ok">Save changes</button><button class="btn ghost" value="cancel">Cancel</button></div></form>`);
    if (r !== 'ok') return;
    const q = n => dlg.querySelector(`[name=${n}]`);
    await guard(async () => { await api('PUT', '/api/wishlist', { name: w.name, where_seen: q('where').value, notes: q('notes').value, status: q('status').value,
      search_words: q('search').value, max_price: q('max_price').value, alert_stock: q('alert_stock').checked }); toast('Saved'); await route(); });
  },
});
// ---------- 1.30.0: Shopping: wishlist plants and garden supplies, the stores, and each store's details ----------
let SHOPF = { near: 'all', kind: 'all' };
try { const s = JSON.parse(localStorage.getItem('plantdb.shopping') || '{}'); if (s && typeof s.near === 'string') SHOPF.near = s.near; if (s && typeof s.kind === 'string') SHOPF.kind = s.kind; } catch (e) { /* defaults */ }
const shopSave = () => { try { localStorage.setItem('plantdb.shopping', JSON.stringify(SHOPF)); } catch (e) { /* this visit only */ } };
let SHOPD = null;                    // the last answer from /api/shopping
const money2 = n => (n == null ? '' : '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
const unitMoney = u => (u ? `${money2(u.per)} a ${u.unit}` : '');
const telHref = p => 'tel:' + String(p).replace(/[^\d+]/g, '');
function phoneLinks(text) {           // "(530) 272-4769; toll-free (888) 784-1722": each number is a link you can tap to call
  const t = String(text || ''), re = /\+?1?[\s.-]?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}/g, out = []; let last = 0, m;
  while ((m = re.exec(t))) { const lead = m[0].match(/^\s*/)[0]; out.push(t.slice(last, m.index) + lead); out.push(html`<a href="${telHref(m[0])}">${m[0].trim()}</a>`); last = m.index + m[0].length; }
  if (last < t.length) out.push(t.slice(last));
  return out;
}
const kindWord = k => ((SHOPD && SHOPD.kinds.find(x => x.key === k)) || {}).label || k;
const kindUnit = k => ((SHOPD && SHOPD.kinds.find(x => x.key === k)) || {}).unit || '';
function buySource(w) {
  const s = w.source || '';
  if (s.startsWith('pots:')) return html`<p class="hint">From <a href="#/pots">Pots and trays</a>.</p>`;
  if (s.startsWith('fert:')) return html`<p class="hint">From the <a href="#/fertilizer">Fertilizer</a> page: the N-P-K ratio ${s.slice(5)}.</p>`;
  if (s === 'frost') return html`<p class="hint">From the <a href="#/frost">cold-night checklist</a>.</p>`;
  return '';
}
function buyCard(w) {
  const o = w.offers || {}, b = o.best, can = canChange(), plant = w.kind === 'plant';
  const visit = (SHOPD.visit || []).filter(s => (s.carries || []).includes(w.kind));
  return html`<li class="wl-item buy-item" id="buy-${enc(w.name)}"><p><span class="tag">${kindWord(w.kind)}</span>${w.status === 'got' ? html` <span class="tag tag-yours">Got it</span>` : ''}</p>
    <h3>${plant ? html`<a href="${spHref(w.name)}">${w.common_name || w.name}</a>` : w.name}</h3>${plant && w.common_name ? html`<p class="latin">${w.name}</p>` : ''}
    ${buySource(w)}
    ${w.status === 'want' ? html`<div class="wl-price">
      ${b ? html`<p><strong>Cheapest now:</strong> ${money2(b.price)}${b.unit && b.unit.unit !== 'each' ? html` for ${b.unit.size} (<strong>${unitMoney(b.unit)}</strong>)` : b.unit ? html` (${unitMoney(b.unit)})` : ''} at <a href="#/store/${enc(b.shop)}">${b.shop_name}</a>: <a href="${b.url}" target="_blank" rel="noopener noreferrer">${b.title}</a></p>` : ''}
      <p>${o.count ? `In stock at ${o.shops} store${o.shops === 1 ? '' : 's'} (${o.count} listing${o.count === 1 ? '' : 's'}).` : SHOPD.checked ? 'Not found at the stores checked.' : 'The stores have not been checked yet.'}
        <strong>Alerts:</strong> ${[w.max_price != null ? `${money2(w.max_price)}${w.price_per === 'unit' ? ' a ' + kindUnit(w.kind) : ''} or less` : '', w.alert_stock ? 'when it is in stock' : ''].filter(Boolean).join('; ') || 'none set (Edit to add one)'}.</p>
      <p class="hint">Searching for: ${(w.terms || []).join('; ') || 'nothing (Edit to add search words)'}.</p>
      <details class="wl-offers" data-wish="${w.name}"><summary>Every listing found, with past prices</summary><div class="wl-offers-box"><p class="loading">Loading</p></div></details></div>` : ''}
    ${w.status === 'want' && visit.length ? html`<details class="buy-visit"><summary>Stores near you that carry ${kindWord(w.kind).toLowerCase()} (${visit.length})</summary><ul>${visit.map(s => html`<li><a href="#/store/${enc(s.key)}">${s.name}</a>${s.phone ? html`: ${phoneLinks(s.phone)}` : ''}${s.miles != null ? html` <small class="muted">about ${fmt(s.miles, 0)} miles</small>` : ''}</li>`)}</ul></details>` : ''}
    ${w.where_seen ? html`<p><strong>Where to find it:</strong> ${w.where_seen}</p>` : ''}
    ${w.notes ? html`<p class="pl">${w.notes}</p>` : ''}
    ${can ? html`<div class="row wl-acts"><button class="btn small" type="button" data-act="buygot" data-name="${w.name}">${w.status === 'got' ? 'Move back to watching' : 'Got it'}</button>
      <button class="btn ghost small" type="button" data-act="buyedit" data-name="${w.name}">Edit, and set alerts</button>
      <button class="btn danger small" type="button" data-act="buyrm" data-name="${w.name}">Stop watching</button></div>` : ''}</li>`;
}
async function viewShopping() {
  const d = SHOPD = await api('GET', '/api/shopping?near=' + enc(SHOPF.near));
  if (SHOPF.near !== 'all' && !d.homes.some(h => String(h.id) === SHOPF.near)) SHOPF.near = 'all';
  const want = d.items.filter(w => w.status === 'want'), got = d.items.filter(w => w.status === 'got');
  const count = k => want.filter(w => k === 'all' || w.kind === k).length;
  const show = want.filter(w => SHOPF.kind === 'all' || w.kind === SHOPF.kind), shownGot = got.filter(w => SHOPF.kind === 'all' || w.kind === SHOPF.kind);
  const opts = [['all', 'All']].concat(d.kinds.map(k => [k.key, k.label]));
  const al = d.alerts || [];
  return {
    title: 'Shopping',
    after: () => { if (d.busy) wlPoll(); },
    html: html`<h1>Shopping</h1>
    <p>Plants from your <a href="#/wishlist">wishlist</a> and garden supplies you are watching for. The stores are checked ${d.hours !== '0' ? `every ${d.hours} hours` : 'only when you ask'}, with alerts here and on the Today page.</p>
    ${al.length ? html`<section class="blk wl-alerts" aria-labelledby="wl-al-h"><h2 id="wl-al-h">Alerts (${al.length})</h2>${wlAlertsHtml(al)}</section>` : ''}
    <div class="filters buy-top"><label class="f">Stores near<select data-act="shopnear"><option value="all" ${SHOPF.near === 'all' ? raw('selected') : ''}>Both homes${d.homes.length > 2 ? ' (all)' : ''}</option>
        ${d.homes.map(h => html`<option value="${h.id}" ${String(h.id) === SHOPF.near ? raw('selected') : ''}>${h.name}</option>`)}</select></label>
      <div class="row wl-check">${canChange() ? html`<button class="btn" type="button" data-act="wlcheck" ${want.length ? '' : raw('disabled')} aria-describedby="wl-check-why">Check the stores now</button><span class="why" id="wl-check-why">Add something to watch first.</span>` : ''}
        <span id="wl-check-msg" role="status" aria-live="polite">${d.checked ? `Last checked ${when(d.checked)}.` : 'Not checked yet.'}</span></div></div>
    <fieldset class="buy-kinds-r"><legend>Show</legend><div class="opts">${opts.map(([k, l]) => html`<label><input type="radio" name="buykind" data-act="shopkind" value="${k}" ${SHOPF.kind === k ? raw('checked') : ''}><span>${l} (${count(k)})</span></label>`)}</div></fieldset>
    <label class="f buy-kinds-s">Show<select data-act="shopkind">${opts.map(([k, l]) => html`<option value="${k}" ${SHOPF.kind === k ? raw('selected') : ''}>${l} (${count(k)})</option>`)}</select></label>
    <div class="row">${canChange() ? html`<button class="btn" type="button" data-act="buynew">Add something to watch</button>` : ''}<a class="btn ghost" href="#/shopping/list">Shopping list for a store visit</a><a class="btn ghost" href="#/shopping/stores">Stores (${d.stores})</a></div>
    <h2>Watching (${show.length})</h2>
    ${show.length ? html`<ul class="wl-list">${show.map(buyCard)}</ul>` : html`<p class="muted">${want.length ? 'Nothing of this kind yet.' : 'Nothing yet.'} ${canChange() ? 'Press "Add something to watch", or add a plant from its page in the library.' : ''}</p>`}
    ${shownGot.length ? html`<details class="blk"><summary><h2 class="sum-h">Got them (${shownGot.length})</h2></summary><ul class="wl-list">${shownGot.map(buyCard)}</ul></details>` : ''}`,
  };
}
// ---------- 1.34.0: the shopping list for a store visit ----------
// What to look for on a visit, from everything on Shopping. Ticks are kept on this device until "Done shopping"; the extra
// items (things not on Shopping) follow your sign-in like the other settings (plantdb.shoplist in prefs.js).
const SL = { store: null, big: false, ticks: {}, extra: [] };     // store null: not chosen yet, so the first store you can visit
function slLoad() {
  try { const x = JSON.parse(localStorage.getItem('plantdb.shoplist') || '{}'); if (Array.isArray(x.extra)) SL.extra = x.extra.filter(t => typeof t === 'string').slice(0, 60); if (typeof x.store === 'string') SL.store = x.store; } catch (e) { /* defaults */ }
  try { const t = JSON.parse(sessionStorage.getItem('plantdb.shopticks') || '{}'); if (t && typeof t === 'object') SL.ticks = t; } catch (e) { /* none */ }
}
function slSave() {
  try { localStorage.setItem('plantdb.shoplist', JSON.stringify({ extra: SL.extra, store: SL.store })); } catch (e) { /* this visit only */ }
  try { sessionStorage.setItem('plantdb.shopticks', JSON.stringify(SL.ticks)); } catch (e) { /* not kept */ }
}
slLoad();
function slCarries(store, w) {           // the store carries this kind, or a listing of it was found there
  const o = w.offers || {};
  return (store.carries || []).includes(w.kind) || (o.best && o.best.shop === store.key);
}
function slWhy(w) {
  const o = w.offers || {}, b = o.best, bits = [];
  if (w.max_price != null) bits.push(`Watching for ${money2(w.max_price)}${w.price_per === 'unit' ? ' a ' + kindUnit(w.kind) : ''} or less.`);
  if (b) bits.push(`Online it is ${money2(b.price)}${b.unit && b.unit.unit !== 'each' ? ` for ${b.unit.size} (${unitMoney(b.unit)})` : ''} at ${b.shop_name}.`);
  if (w.source) bits.push(w.source);
  if (w.where_seen) bits.push(`Where to find it: ${w.where_seen}.`);
  if (w.notes) bits.push(w.notes);
  return bits.join(' ');
}
async function viewShopList() {
  const d = SHOPD = await api('GET', '/api/shopping?near=all');
  const want = d.items.filter(w => w.status === 'want');
  const stores = (d.visit || []).map(s => ({ ...s, n: want.filter(w => slCarries(s, w)).length }));
  const homes = d.homes || [];
  const opts = [...stores.map(s => [s.key, `${s.name} (carries ${s.n} of these)`]), ...homes.map(h => ['home:' + h.id, `Any store near ${h.name}`]), ['', 'Everything you are watching']];
  if (SL.store == null || !opts.some(o => o[0] === SL.store)) SL.store = stores.length ? stores[0].key : '';
  const store = stores.find(s => s.key === SL.store) || null, homeId = SL.store.startsWith('home:') ? SL.store.slice(5) : '';
  const carried = store ? want.filter(w => slCarries(store, w)) : want, missing = store ? want.filter(w => !slCarries(store, w)) : [];
  const nearStores = homeId ? stores.filter(s => String(s.home_id_eff) === homeId) : [];
  const ticked = k => !!SL.ticks[k];
  const item = w => html`<li><label class="chk"><input type="checkbox" data-act="sltick" data-k="${w.name}" ${ticked(w.name) ? raw('checked') : ''}> <span class="sl-txt"><strong>${w.common_name || w.name}</strong> <span class="tag">${kindWord(w.kind)}</span>${w.kind === 'plant' && w.common_name ? html` <span class="latin">${w.name}</span>` : ''}
    ${slWhy(w) ? html`<br><span class="muted">${slWhy(w)}</span>` : ''}</span></label></li>`;
  const nTick = Object.keys(SL.ticks).filter(ticked).length;
  return {
    title: 'Shopping list',
    html: html`<p class="crumb noprint"><a href="#/shopping">Back to Shopping</a></p><h1>Shopping list${store ? html`: ${store.name}` : homeId ? html`: near ${(homes.find(h => String(h.id) === homeId) || {}).name || ''}` : ''}</h1>
    <p class="noprint">What to look for on a visit, from everything you are watching on Shopping. Tick what you bought; "Done shopping" then marks the ticked ones as <strong>got it</strong>. Print it, or show it large for the store.</p>
    <div class="filters noprint"><label class="f">Store<select data-act="slstore">${opts.map(([v, t]) => html`<option value="${v}" ${v === SL.store ? raw('selected') : ''}>${t}</option>`)}</select></label>
      <div class="row" style="align-items:end"><button class="btn ghost" type="button" data-act="slbig" aria-pressed="${SL.big ? 'true' : 'false'}">${SL.big ? 'Normal print' : 'Large print'}</button><button class="btn ghost" type="button" data-act="print">Print</button></div></div>
    <section class="blk sl-list ${SL.big ? 'sl-big' : ''}" id="sl-main">
      ${store ? html`<h2>${store.name}</h2><p>${store.address || ''}${store.address && store.phone ? ' · ' : ''}${store.phone ? phoneLinks(store.phone) : ''}${store.hours ? html` · ${store.hours}` : ''}${store.maps ? html` <a class="noprint" href="${store.maps}" target="_blank" rel="noopener noreferrer">Open in a map</a>` : ''}</p>`
        : homeId ? html`<h2>Stores near ${(homes.find(h => String(h.id) === homeId) || {}).name || ''}</h2>${nearStores.length ? html`<ul class="sl-stores">${nearStores.map(s => html`<li><strong>${s.name}</strong>${s.n ? ` carries ${s.n} of these` : ''}${s.address ? html`<br>${s.address}` : ''}${s.phone ? html` · ${phoneLinks(s.phone)}` : ''}${s.hours ? html` · ${s.hours}` : ''}</li>`)}</ul>` : html`<p class="muted">No stores you can visit are set near here yet (Shopping → Stores).</p>`}`
        : html`<h2>Everything you are watching</h2>`}
      ${carried.length ? html`<ul class="tick-list">${carried.map(item)}</ul>` : html`<p class="muted">Nothing on Shopping ${store ? 'that this store carries, as far as the app knows' : 'yet'}.</p>`}
      ${missing.length ? html`<h3>Not carried here, as far as the app knows (${missing.length})</h3><p class="hint noprint">Ask at the store, or set what it carries on its page under Shopping → Stores.</p><ul class="tick-list">${missing.map(item)}</ul>` : ''}
      <h3>Anything else</h3>
      <form class="row noprint" data-form="sladd"><label class="f" style="flex:1 1 16rem">Add to the list<small>Things not on Shopping: twine, a new trowel</small><input type="text" name="text" maxlength="80" autocomplete="off"></label><button class="btn ghost" type="submit" style="align-self:end">Add</button></form>
      ${SL.extra.length ? html`<ul class="tick-list">${SL.extra.map(t => html`<li><label class="chk"><input type="checkbox" data-act="sltick" data-k="${'extra:' + t}" ${ticked('extra:' + t) ? raw('checked') : ''}> <span class="sl-txt"><strong>${t}</strong></span></label> <button class="btn small ghost noprint" type="button" data-act="slrm" data-t="${t}" aria-label="Remove ${t} from the list">Remove</button></li>`)}</ul>` : html`<p class="muted noprint">Nothing extra yet.</p>`}
      <div class="row noprint"><button class="btn" type="button" data-act="sldone" ${nTick ? '' : raw('disabled')} aria-describedby="sl-done-why">Done shopping: mark the ${nTick} ticked as got</button><span class="why" id="sl-done-why">Tick what you got first.</span>${nTick ? html`<button class="btn ghost" type="button" data-act="slclear">Clear the ticks</button>` : ''}</div></section>`,
  };
}
function storeRows(list, cols) {
  const how = s => s.kind === 'api' ? 'Searches its listings' : s.platform === 'shopify' || s.platform === 'woo' ? 'Reads its online store' : s.platform === 'page' || s.kind === 'page' ? 'Call or visit: its pages are read for the names you watch' : 'Finds out on the first check';
  const owner = ME().role === 'owner';
  return html`<div class="tbl-wrap"><table class="tbl wl-shops"><thead><tr><th scope="col">Store</th><th scope="col">Carries</th><th scope="col">How it is checked</th>${cols.phone ? html`<th scope="col">Phone</th>` : ''}<th scope="col">Last check</th>${owner ? html`<th scope="col">Check it</th>` : ''}</tr></thead><tbody>
    ${list.map(s => html`<tr><th scope="row"><a href="#/store/${enc(s.key)}">${s.name}</a>${s.miles != null ? html`<br><small class="muted">about ${fmt(s.miles, 0)} miles</small>` : ''}</th>
      <td>${s.carries.length ? s.carries.map(k => kindWord(k)).join(', ') : html`<span class="muted">Not set</span>`}</td><td>${how(s)}</td>
      ${cols.phone ? html`<td>${s.phone ? phoneLinks(s.phone) : html`<span class="muted">Not known</span>`}</td>` : ''}
      <td>${s.error ? html`<span class="bad-text">⚠ ${s.status}</span>` : s.status || (s.enabled ? 'Not checked yet' : 'Off')}${s.checked_at ? html`<br><small class="muted">${when(s.checked_at)}</small>` : ''}</td>
      ${owner ? html`<td><label class="chk"><input type="checkbox" data-act="shopon" data-key="${s.key}" ${s.enabled ? raw('checked') : ''}> On</label>
        ${s.kind !== 'api' ? html`<button class="btn ghost small" type="button" data-act="shopedit" data-key="${s.key}">Change address</button>` : ''}
        ${s.custom ? html`<button class="btn danger small" type="button" data-act="shoprm" data-key="${s.key}" aria-label="Remove the store ${s.name}">Remove</button>` : ''}</td>` : ''}</tr>`)}
  </tbody></table></div>`;
}
let STF = { show: 'all', carries: '' };
async function viewStores() {
  const sh = WLSHOPS = await api('GET', '/api/shops');
  if (!SHOPD) SHOPD = { kinds: sh.kinds, visit: [] };
  const owner = ME().role === 'owner';
  const keep = s => !STF.carries || s.carries.includes(STF.carries);
  const groups = sh.homes.map(h => [h, sh.shops.filter(s => s.local && s.home_id_eff === h.id && keep(s))]);
  const online = sh.shops.filter(s => !s.local && keep(s)), alsoOnline = sh.shops.filter(s => s.local && s.online && keep(s));
  const showHome = h => STF.show === 'all' || STF.show === String(h.id), showOnline = STF.show === 'all' || STF.show === 'online';
  return {
    title: 'Stores',
    html: html`<p class="crumb"><a href="#/shopping">Back to Shopping</a></p><h1>Stores</h1>
    <p>Every store Shopping checks or lists. Choose one for its address, phone number, hours and listings. Stores you can visit are read for the names you watch; call them to be sure.</p>
    <div class="filters"><label class="f">Show<select data-act="storeshow"><option value="all">${sh.homes.length > 1 ? 'Every home, and online' : 'Near home, and online'}</option>
        ${sh.homes.map(h => html`<option value="${h.id}" ${STF.show === String(h.id) ? raw('selected') : ''}>Near ${h.name}</option>`)}<option value="online" ${STF.show === 'online' ? raw('selected') : ''}>Online only</option></select></label>
      <label class="f">Carries<select data-act="storecarries"><option value="">Anything</option>${sh.kinds.map(k => html`<option value="${k.key}" ${STF.carries === k.key ? raw('selected') : ''}>${k.label}</option>`)}</select></label></div>
    ${groups.filter(([h]) => showHome(h)).map(([h, list]) => html`<section class="blk" aria-labelledby="st-h-${h.id}"><h2 id="st-h-${h.id}">Near ${h.name} (${list.length})</h2>
      ${list.length ? storeRows(list, { phone: true }) : html`<p class="muted">None yet.${owner ? ' Add one below.' : ''}</p>`}</section>`)}
    ${showOnline ? html`<section class="blk" aria-labelledby="st-h-on"><h2 id="st-h-on">Online (${online.length})</h2>${storeRows(online, { phone: false })}
      ${alsoOnline.length ? html`<p class="hint">Also selling online, and counted for every home: ${alsoOnline.map((s, i) => html`${i ? ', ' : ''}<a href="#/store/${enc(s.key)}">${s.name}</a>`)}.</p>` : ''}</section>` : ''}
    ${owner ? html`<section class="blk" aria-labelledby="st-own-h"><h2 id="st-own-h">Store settings</h2>
      <label class="f">Check the stores<select data-act="shophours">${[['6', 'Every 6 hours'], ['12', 'Every 12 hours (twice a day)'], ['24', 'Once a day'], ['48', 'Every 2 days'], ['0', 'Only when I press "Check the stores now"']].map(([v, t]) => html`<option value="${v}" ${sh.hours === v ? raw('selected') : ''}>${t}</option>`)}</select></label>
      <h3>Add a store</h3>
      <form data-form="shopadd" class="f-grid" autocomplete="off"><label class="f">Store name<input type="text" name="name" maxlength="80" required></label>
        <label class="f">Web address<small>Its home page, or the page that lists what it sells</small><input type="url" name="url" maxlength="300" placeholder="https://" required></label>
        <label class="chk"><input type="checkbox" name="local"> A store you can visit</label>
        <label class="f">Near<select name="home_id">${sh.homes.map(h => html`<option value="${h.id}">${h.name}</option>`)}</select></label>
        <label class="chk"><input type="checkbox" name="online"> It also sells online (counts for every home)</label>
        <label class="f">Phone<input type="tel" name="phone" maxlength="120"></label><label class="f">Address<input type="text" name="address" maxlength="200"></label>
        <div class="row"><button class="btn" type="submit">Add the store</button></div></form>
      <h3>eBay and Etsy keys</h3>
      <p class="hint">eBay and Etsy are searched through their official services, which need free keys. They are kept on this computer and never shown again.</p>
      <form data-form="shopkeys" data-shop="ebay" class="f-grid" autocomplete="off"><p><strong>eBay</strong>: ${sh.have_ebay ? 'saved.' : 'not set.'} Create a free account at <a href="https://developer.ebay.com/" target="_blank" rel="noopener noreferrer">developer.ebay.com</a>, make a "Production" keyset, and paste its App ID (Client ID) and Cert ID (Client Secret).</p>
        <label class="f">App ID<input type="password" name="ebay_app_id" autocomplete="off"></label><label class="f">Cert ID<input type="password" name="ebay_cert_id" autocomplete="off"></label>
        <div class="row"><button class="btn" type="submit">Save the eBay keys</button>${sh.have_ebay ? html`<button class="btn ghost" type="button" data-act="shopkeyrm" data-shop="ebay">Remove them</button>` : ''}</div></form>
      <form data-form="shopkeys" data-shop="etsy" autocomplete="off"><p><strong>Etsy</strong>: ${sh.have_etsy ? 'saved.' : 'not set.'} Register an app at <a href="https://www.etsy.com/developers/register" target="_blank" rel="noopener noreferrer">etsy.com/developers</a> and paste its key (keystring).</p>
        <label class="f">Etsy key<input type="password" name="etsy_key" autocomplete="off"></label>
        <div class="row"><button class="btn" type="submit">Save the Etsy key</button>${sh.have_etsy ? html`<button class="btn ghost" type="button" data-act="shopkeyrm" data-shop="etsy">Remove it</button>` : ''}</div></form></section>` : ''}`,
  };
}
let STORE = null;
async function viewStore(key) {
  const [s, sh] = await Promise.all([api('GET', '/api/shops/' + enc(key)), SHOPD ? Promise.resolve(null) : api('GET', '/api/shops')]);
  if (sh) SHOPD = { kinds: sh.kinds, visit: [] };
  STORE = s;
  const can = canChange(), owner = ME().role === 'owner', me = cleanName(viaTS() ? ME().name : getName());
  const how = s.kind === 'api' ? 'its listings are searched for what you watch' : s.platform === 'shopify' || s.platform === 'woo' ? 'its online store is read for names, prices and stock' : s.platform === 'page' || s.kind === 'page' ? 'its pages are read for the names you watch, with a price if the page shows one. Call to be sure' : 'found out on the first check';
  return {
    title: s.name,
    html: html`<p class="crumb"><a href="#/shopping/stores">Back to the stores</a></p><h1>${s.name}</h1>
    <p>${s.local ? html`<span class="tag">Near ${s.home_name}</span> <span class="tag">Store you can visit</span> ` : ''}${s.online || !s.local ? html`<span class="tag">Online store</span>` : ''}${s.enabled ? '' : html` <span class="tag">Not checked (turned off)</span>`}</p>
    <div class="set-grid">
    <section class="set-card blk" aria-labelledby="st-find"><h2 id="st-find">${s.local ? 'Find it' : 'Its details'}</h2>
      ${s.local ? html`<p><strong>Address:</strong> ${s.address || html`<span class="muted">not known yet</span>`}${s.maps ? html`<br><a href="${s.maps}" target="_blank" rel="noopener noreferrer">Open in a map</a>` : ''}${s.miles != null ? html` · about ${fmt(s.miles, 0)} miles from ${s.home_name}` : ''}</p>` : ''}
      <p><strong>Phone:</strong> ${s.phone ? phoneLinks(s.phone) : html`<span class="muted">not known yet</span>`}</p>
      ${s.local ? html`<p><strong>Hours:</strong> ${s.hours || html`<span class="muted">not known yet</span>`}</p>` : ''}
      ${s.email ? html`<p><strong>Email:</strong> <a href="mailto:${s.email}">${s.email}</a></p>` : ''}
      <p><strong>Website:</strong> <a href="${s.website || s.url}" target="_blank" rel="noopener noreferrer">${(s.website || s.url).replace(/^https?:\/\/(www\.)?/, '').replace(/\/$/, '')}</a></p>
      ${s.details_src ? html`<p class="hint">${s.details_src}${s.details_at && !/\d{4}/.test(s.details_src) ? `, ${when(s.details_at)}` : ''}.${s.local ? ' Hours and phone numbers change: call before a long drive.' : ''}</p>` : ''}
      ${can ? html`<div class="row"><button class="btn ghost small" type="button" data-act="storeedit">Edit details</button>${s.local ? html`<button class="btn ghost small" type="button" data-act="storelookup">Look them up on OpenStreetMap</button>` : ''}</div>
        <p id="st-look" role="status" aria-live="polite"></p>` : ''}</section>
    <section class="set-card blk" aria-labelledby="st-car"><h2 id="st-car">What it carries</h2>
      <p>${s.carries.length ? s.carries.map(k => html`<span class="tag">${kindWord(k)}</span> `) : html`<span class="muted">Not set yet.${can ? ' Choose Edit details to set it.' : ''}</span>`}</p>
      <p><strong>How it is checked:</strong> ${how}.</p>
      <p><strong>Last check:</strong> ${s.checked_at ? html`${when(s.checked_at)}. ${s.error ? html`<span class="bad-text">⚠ ${s.status}</span>` : s.status || ''}` : 'not checked yet.'}</p>
      ${owner ? html`<label class="chk"><input type="checkbox" data-act="shopon" data-key="${s.key}" ${s.enabled ? raw('checked') : ''}> Check this store</label>` : ''}</section>
    </div>
    <section class="blk" aria-labelledby="st-has"><h2 id="st-has">What you are watching that it has (${s.listings.length})</h2>
      ${s.listings.length ? html`<div class="tbl-wrap"><table class="tbl"><thead><tr><th scope="col">Watching</th><th scope="col">Listing</th><th scope="col">Price</th><th scope="col">Per unit</th><th scope="col">In stock</th></tr></thead><tbody>
        ${s.listings.map(o => html`<tr><th scope="row"><a href="#/shopping">${o.common_name || o.wish}</a></th><td><a href="${o.url}" target="_blank" rel="noopener noreferrer">${o.title}</a>${o.size ? html`<br><small class="muted">${o.size}</small>` : ''}</td>
          <td>${o.price == null ? html`<span class="muted">Not shown</span>` : money2(o.price)}${o.before ? html`<br><small class="muted">was ${money2(o.before.price)} on ${when(o.before.at)}</small>` : ''}</td>
          <td>${o.unit ? unitMoney(o.unit) : ''}</td><td>${o.available ? html`<span aria-hidden="true">✓</span> Yes` : html`<span aria-hidden="true">✗</span> Sold out`}</td></tr>`)}
      </tbody></table></div>` : html`<p class="muted">Nothing you are watching was found here at the last check.</p>`}</section>
    <section class="blk" aria-labelledby="st-notes"><h2 id="st-notes">What they had</h2>
      <p class="hint">For notes after you call or visit. Everyone who can open the plant record sees them.</p>
      ${s.notes.length ? html`<ul class="wl-alert-list">${s.notes.map(n => html`<li><strong>${midDay(n.created_at.slice(0, 10))}</strong>, ${n.created_by}: ${n.text}
        ${can && (owner || n.created_by === me) ? html` <button class="btn ghost small" type="button" data-act="storenoterm" data-id="${n.id}" aria-label="Remove this note">Remove</button>` : ''}</li>`)}</ul>` : html`<p class="muted">No notes yet.</p>`}
      ${can ? html`<form data-form="storenote" class="store-note"><label class="f">Add a note<textarea name="text" rows="2" maxlength="1000" required></textarea></label><div class="row"><button class="btn" type="submit">Save the note</button></div></form>` : ''}</section>`,
  };
}
function buyDialog(w) {                  // add or edit something on Shopping
  const kinds = SHOPD.kinds, isNew = !w, plant = w && w.kind === 'plant';
  w = w || { name: '', kind: SHOPF.kind !== 'all' && SHOPF.kind !== 'plant' ? SHOPF.kind : 'mix', search_words: '', max_price: null, price_per: '', alert_stock: 0, notes: '', where_seen: '', status: 'want' };
  const unitOf = k => (kinds.find(x => x.key === k) || {}).unit || '';
  return modal(html`<form method="dialog" class="buy-dlg"><h2>${isNew ? 'Add something to watch' : 'Edit: ' + (w.common_name || w.name)}</h2>
    ${plant ? html`<p>${w.common_name ? html`${w.common_name} (<i>${w.name}</i>)` : html`<i>${w.name}</i>`}, from your wishlist.</p>`
      : html`<label class="f">What it is<small>As you would say it, for example "Pumice, 1/4 in" or "8 in terracotta pot"</small><input type="text" name="name" maxlength="120" value="${w.name}" required></label>
        <label class="f">Kind<select name="kind">${kinds.filter(k => k.key !== 'plant').map(k => html`<option value="${k.key}" ${k.key === w.kind ? raw('selected') : ''}>${k.label}</option>`)}</select></label>`}
    <label class="f">Search the stores for<small>One search per line, for example "pumice" and "horticultural pumice". Left empty, its name is used.</small><textarea name="search" rows="2" maxlength="300">${w.search_words || ''}</textarea></label>
    <fieldset class="opt-group"><legend>Alerts</legend>
      <label class="f">Alert me when the price is at or under<small>In dollars, such as 25. Shipping is not included. Leave empty for no price alert.</small><input type="number" name="max_price" min="0.01" step="0.01" inputmode="decimal" value="${w.max_price == null ? '' : w.max_price}"></label>
      <div class="opts buy-per" data-unit-for="kind">${[['', 'For the whole listing'], ['unit', 'Per unit (a quart, a pound or a square foot)']].map(([v, l]) => html`<label><input type="radio" name="price_per" value="${v}" ${(w.price_per || '') === v ? raw('checked') : ''}><span>${l}</span></label>`)}</div>
      <p class="hint">Per unit works for potting mixes and amendments (a quart), fertilizers (a pound) and frost cloth (a square foot), when a listing says its size.</p>
      <label class="chk"><input type="checkbox" name="alert_stock" ${w.alert_stock ? raw('checked') : ''}> Alert me when a store has it in stock</label></fieldset>
    <label class="f">Where to find it<small>A store, a website, a friend</small><input type="text" name="where" maxlength="300" value="${w.where_seen || ''}"></label>
    <label class="f">Notes<textarea name="notes" rows="3" maxlength="2000">${w.notes || ''}</textarea></label>
    <div class="row"><button class="btn" value="ok">${isNew ? 'Start watching' : 'Save changes'}</button><button class="btn ghost" value="cancel">Cancel</button></div></form>`);
}
function buyBody(w) {
  const q = n => dlg.querySelector(`[name=${n}]`), per = dlg.querySelector('[name=price_per]:checked');
  const b = { search_words: q('search').value, max_price: q('max_price').value, alert_stock: q('alert_stock').checked, where_seen: q('where').value, notes: q('notes').value,
    price_per: per ? per.value : '' };
  if (!w || w.kind !== 'plant') { b.kind = q('kind').value; if (w && q('name').value.trim() !== w.name) b.rename = q('name').value.trim(); if (!w) b.name = q('name').value.trim(); }
  return b;
}
const buyItem = name => SHOPD && SHOPD.items.find(x => x.name === name);
Object.assign(acts, {
  async buynew() {
    if (!(await needName())) return;
    if ((await buyDialog(null)) !== 'ok') return;
    const b = buyBody(null);
    if (!b.name) { toast('Give it a name first', true); return; }
    if (buyItem(b.name)) { toast(`"${b.name}" is already on Shopping`, true); return; }
    await guard(async () => { await api('PUT', '/api/wishlist', b); toast('Watching ' + b.name); SHOPF.kind = 'all'; shopSave(); await route(); });
  },
  async buyedit(el) {
    const w = buyItem(el.dataset.name); if (!w || !(await needName())) return;
    if ((await buyDialog(w)) !== 'ok') return;
    await guard(async () => { await api('PUT', '/api/wishlist', { name: w.name, ...buyBody(w) }); toast('Saved'); await route(); });
  },
  slbig(el) { SL.big = !SL.big; const b = document.getElementById('sl-main'); if (b) b.classList.toggle('sl-big', SL.big); el.textContent = SL.big ? 'Normal print' : 'Large print'; el.setAttribute('aria-pressed', SL.big ? 'true' : 'false'); },
  slclear() { SL.ticks = {}; slSave(); route(); },
  slrm(el) { SL.extra = SL.extra.filter(t => t !== el.dataset.t); delete SL.ticks['extra:' + el.dataset.t]; slSave(); route(); },
  async sldone() {
    const names = Object.keys(SL.ticks).filter(k => SL.ticks[k] && !k.startsWith('extra:')), extras = Object.keys(SL.ticks).filter(k => SL.ticks[k] && k.startsWith('extra:')).map(k => k.slice(6));
    if (names.length && !(await needName())) return;
    await guard(async () => {
      for (const n of names) await api('PUT', '/api/wishlist', { name: n, status: 'got' });
      SL.extra = SL.extra.filter(t => !extras.includes(t)); SL.ticks = {}; slSave();
      toast(names.length ? `Marked ${names.length} as got it` + (extras.length ? ` and crossed off ${extras.length} extra` : '') : `Crossed off ${extras.length}`); await route();
    });
  },
  async buygot(el) {
    const w = buyItem(el.dataset.name); if (!w || !(await needName())) return;
    await guard(async () => { await api('PUT', '/api/wishlist', { name: w.name, status: w.status === 'got' ? 'want' : 'got' }); toast(w.status === 'got' ? 'Moved back to watching' : 'Marked as got it'); await route(); });
  },
  async buyrm(el) {
    const w = buyItem(el.dataset.name); if (!w || !(await needName())) return;
    if (!(await confirmBox('Stop watching it?', `${w.common_name || w.name} leaves Shopping${w.kind === 'plant' ? ' and the wishlist' : ''}, with its listings and notes.`, 'Stop watching', true))) return;
    await guard(async () => { await api('DELETE', '/api/wishlist', { name: w.name }); toast('Stopped watching ' + (w.common_name || w.name)); await route(); });
  },
  async buywatch(el) {                   // from Pots and trays, Fertilizer and the cold-night checklist: watch for it on Shopping
    if (!(await needName())) return;
    await guard(async () => {
      const have = (await api('GET', '/api/wishlist')).wishlist.find(x => x.name === el.dataset.name);
      if (!have) await api('PUT', '/api/wishlist', { name: el.dataset.name, kind: el.dataset.kind, search_words: el.dataset.search || '', source: el.dataset.src || '' });
      toast(have ? 'Already on Shopping' : 'Watching ' + el.dataset.name + ' on Shopping'); SHOPF.kind = el.dataset.kind; shopSave(); go('#/shopping');
    });
  },
  async storeedit() {
    const s = STORE; if (!s || !(await needName())) return;
    const homes = (META && META.homes) || [];
    const r = await modal(html`<form method="dialog"><h2>Edit: ${s.name}</h2>
      <label class="f">Address<input type="text" name="address" maxlength="200" value="${s.address}"></label>
      <label class="f">Phone<small>More than one? Separate them with a semicolon.</small><input type="tel" name="phone" maxlength="120" value="${s.phone}"></label>
      <label class="f">Hours<input type="text" name="hours" maxlength="300" value="${s.hours}"></label>
      <label class="f">Email<input type="email" name="email" maxlength="120" value="${s.email}"></label>
      <label class="f">Website<input type="url" name="website" maxlength="300" value="${s.website}"></label>
      ${s.local && homes.length > 1 ? html`<label class="f">Near<select name="home_id">${homes.map(h => html`<option value="${h.id}" ${h.id === s.home_id_eff ? raw('selected') : ''}>${h.name}</option>`)}</select></label>` : ''}
      <fieldset class="opt-group"><legend>What it carries</legend>${SHOPD.kinds.map(k => html`<label class="chk"><input type="checkbox" name="carries" value="${k.key}" ${s.carries.includes(k.key) ? raw('checked') : ''}> ${k.label}</label>`)}</fieldset>
      <div class="row"><button class="btn" value="ok">Save changes</button><button class="btn ghost" value="cancel">Cancel</button></div></form>`);
    if (r !== 'ok') return;
    const q = n => dlg.querySelector(`[name=${n}]`), b = { carries: [...dlg.querySelectorAll('[name=carries]:checked')].map(x => x.value) };
    ['address', 'phone', 'hours', 'email', 'website'].forEach(k => { b[k] = q(k).value; });
    if (q('home_id')) b.home_id = q('home_id').value;
    await guard(async () => { await api('PUT', '/api/stores/' + enc(s.key) + '/details', b); toast('Saved'); await route(); });
  },
  async storelookup(el) {
    const s = STORE; if (!s || !(await needName())) return;
    el.disabled = true; const m = document.getElementById('st-look'); if (m) m.textContent = 'Looking it up…';
    try {
      const r = await api('POST', '/api/stores/' + enc(s.key) + '/lookup');
      toast(r.filled.length ? 'Filled in: ' + r.filled.join(', ') : 'Nothing new was found on OpenStreetMap');
      await route();
    } catch (e) { if (m) m.textContent = e.message; el.disabled = false; }
  },
  async storenoterm(el) {
    if (!(await confirmBox('Remove this note?', 'It is taken off the store\'s page for everyone.', 'Remove the note', true))) return;
    await guard(async () => { await api('DELETE', '/api/stores/notes/' + enc(el.dataset.id)); toast('Removed'); await route(); });
  },
});
Object.assign(changeActs, {
  shopnear(el) { SHOPF.near = el.value; shopSave(); route(); },
  shopkind(el) { SHOPF.kind = el.value; shopSave(); route(); },
  storeshow(el) { STF.show = el.value; route(); },
  storecarries(el) { STF.carries = el.value; route(); },
  slstore(el) { SL.store = el.value; slSave(); route(); },
  sltick(el) { SL.ticks[el.dataset.k] = el.checked; slSave(); const n = Object.values(SL.ticks).filter(Boolean).length, b = document.querySelector('[data-act=sldone]'); if (b) { b.disabled = !n; b.textContent = `Done shopping: mark the ${n} ticked as got`; } const c = document.querySelector('[data-act=slclear]'); if (c && !n) c.remove(); },
});
Object.assign(formActs, {
  sladd(form) {                          // 1.34.0: an extra line on the shopping list
    const t = form.elements.text.value.trim().slice(0, 80); if (!t) return;
    if (!SL.extra.includes(t)) SL.extra.push(t);
    slSave(); route();
  },
  async storenote(form) {
    if (!(await needName())) return;
    await api('POST', '/api/stores/' + enc(STORE.key) + '/notes', { text: form.elements.text.value }); toast('Note saved'); await route();
  },
});
