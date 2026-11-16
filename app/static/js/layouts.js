/* Plant record front end: layouts (1.58.0, prototype #131; plantdb/layouts.py). One of the files loaded in order by index.html
   (js/manifest.json); they share one scope. Plain JavaScript, no inline handlers (the server's content policy forbids them).

   A layout is a room, a porch or one shelf unit drawn to scale, with the plants, grow lights, shelves and anything else in it as
   things to move about on the page before the real ones are moved. Everything is a box: a place (x from the left, y from the back,
   z off the floor: its left, back, bottom corner) and a size (w across, d back to front, h tall), in inches. The top view draws x
   and y, the front view x and z, so the same things are seen and moved in both; a view in three dimensions needs no more than this.

   - #/layouts lists the layouts, each with a small drawing, and starts one from a room, a shelf or a size you type.
   - #/layouts/ID is one layout: the drawing (top view, front view or both), a grid that things snap to, the chosen thing's place
     and size as boxes to type in, what to look at, and a list of everything on it. A thing moves by dragging, by the arrow keys,
     or by typing its place, so nothing needs a mouse; its corner handle, or its size boxes, resize it.
   - lyFindings() is the one place that decides what overlaps, sticks out or may be a problem. It runs on every move, so the marks
     follow a thing while it is dragged. A mark is always a pattern and a sign as well as a colour, and each is said in a sentence.
   - lyLight() works out the light each plant gets where it is drawn, from the lights drawn above it, their makers' figures, and the
     hours and brightness each is drawn with: the same figures and words as Grow lights. It runs with lyFindings(), so it follows
     a plant or a light while it is dragged.
   Changes are saved as they are made (PUT /api/layouts/items/ID); Undo takes back the ones made on this visit, newest first.
   Two things reach the record (Ethan, November 15, 2026): a plant's height given here is saved on its page, and "Move it in the
   record" puts a drawn plant where the layout has it (POST /api/layouts/ID/record). Undo takes those back too. */
'use strict';

let LY = null;                                     // the layout on screen: { d: the server's answer, sel, fview, view, zoom, level, grid, photos, Sv: pixels to the inch in each view, mode, rem, F, undo, q }
let LYL = null;                                    // the list page's answer (layouts, places)
const LY_EPS = 0.01, LY_KEYS = ['x', 'y', 'z', 'w', 'd', 'h', 'shape', 'locked', 'size_locked', 'name', 'hours', 'dim_pct'];
// Two locks (Ethan, November 16, 2026: "lock in any item's size values separately from the lock for its location"): locked keeps a
// thing where it is (dragging, the arrow keys, its place boxes, Stands on, Hangs under); size_locked keeps its size (the corner handle,
// its size boxes, its shape). Turning it changes both, so either lock stops it.
const LY_SIZE_KEYS = ['w', 'd', 'h', 'shape'], LY_PLACE_KEYS = ['x', 'y', 'z', 'on', 'under'];
const LY_KINDS = ['plant', 'light', 'shelf', 'other', 'zone'];      // the kinds of thing, in the order they are offered (their words come from the server)
const LY_PREF = 'plantdb.layouts';                 // this device's own choices: which view, the grid shown, photos on the plants
const lyPref = () => { try { return JSON.parse(localStorage.getItem(LY_PREF) || '{}') || {}; } catch (e) { return {}; } };
const lyPrefSave = p => { try { localStorage.setItem(LY_PREF, JSON.stringify({ ...lyPref(), ...p })); } catch (e) { /* this visit only */ } };
const lyPrefEach = p => { const each = lyPref().each || {}; each[LY.d.id] = { ...(each[LY.d.id] || {}), ...p }; lyPrefSave({ each }); };       // kept for each layout: its view and the size of its drawing
const LY_WORD = { outside: 'Sticks out', overlap: 'Overlap', zone: 'In an area to keep clear', tight: 'Tight', floating: 'Nothing under it', nearlight: 'Close to a light', toodim: 'Too dim', dim: 'A bit dim', bright: 'A bit bright', toobright: 'Too bright', count: 'More than you own' };
// A plant's light against what it needs is a mark of its own kind (Ethan, November 15, 2026: marks for more than too dim and too bright).
const LY_LV = { too_dim: 'toodim', dim: 'dim', bright: 'bright', too_bright: 'toobright' }, lyIsLv = k => k === 'toodim' || k === 'dim' || k === 'bright' || k === 'toobright';
const LY_LV_SIGN = { too_dim: '▼▼', dim: '▼', good: '✓', bright: '▲', too_bright: '▲▲', unknown: '?', none: '–' };       // as Grow lights has them (LV_ICON in js/lights.js); none: no drawn light reaches the plant (grey; Ethan, November 15, 2026)
const LY_NAMES = { other: ['Humidifier', 'Fan', 'Heater', 'Heat mat', 'Sensor', 'Table', 'Chair', 'Watering can', 'Storage box'], zone: ['Walkway', 'Door', 'Window', 'Heating vent', 'Outlet'] };
const r2 = n => Math.round(n * 100) / 100;
const lyNum = n => String(Math.round(n * 1000) / 1000);
const lyCan = () => canChange() && !(META && META.mirror && META.mirror.on) && !(LY && LY.stale);
const lyItem = id => (LY && id != null ? LY.d.items.find(x => x.id === id) : null) || null;
const lyOn = () => !!LY && !!document.getElementById('ly-draw');

// ---------- the geometry: all of it is here, and none of it touches the page ----------
// Seen from above, a round thing as wide as it is deep is a circle; an oval is taken as the box around it.
const lyRound = it => it.shape === 'round' && Math.abs(it.w - it.d) < 0.05;
// Seen from above: the gap between two things (0 when they touch), or minus how far one reaches into the other.
function lyPlan(a, b) {
  const ra = lyRound(a), rb = lyRound(b);
  if (ra && rb) return Math.hypot(a.x + a.w / 2 - b.x - b.w / 2, a.y + a.d / 2 - b.y - b.d / 2) - (a.w + b.w) / 2;
  if (ra || rb) {
    const c = ra ? a : b, q = ra ? b : a, r = c.w / 2, cx = c.x + r, cy = c.y + r;
    const dist = Math.hypot(cx - clamp(cx, q.x, q.x + q.w), cy - clamp(cy, q.y, q.y + q.d));
    return dist > 0 ? dist - r : -(r + Math.min(cx - q.x, q.x + q.w - cx, cy - q.y, q.y + q.d - cy));     // else its centre is inside the box
  }
  const dx = Math.max(a.x - b.x - b.w, b.x - a.x - a.w), dy = Math.max(a.y - b.y - b.d, b.y - a.y - a.d);
  return dx > 0 || dy > 0 ? Math.hypot(Math.max(dx, 0), Math.max(dy, 0)) : Math.max(dx, dy);
}
const lyNm = it => `${it.name} (${it.sort})`;       // the number is the one drawn on it
// ---------- shelves with levels ----------
// One of the record's shelves drawn as a block on a room's layout carries its levels when its measurements give them (levels:
// [{ n, name, z: the height of that level's top above the block's foot, room: the clear height above it, none for the top one }]).
// Such a block is not solid: its boards are, and a thing may stand on any of them, with the room between them open.
//   lyLv(b)      its levels (none for anything else)
//   lySolids(b)  a thing's solid parts, as { z, h }; every part has the thing's own footprint
//   lySurf(b)    the places on it to stand: { b, n (0 for a plain top), z, room, name }
//   lyRoom(t, b) how much room thing t has above it before the nearest part of b over it: { gap, name }, or null
const lyLv = b => (b.kind === 'shelf' && b.levels && b.levels.length ? b.levels.filter(v => v.z <= b.h + 0.05) : []);
const lySolids = b => { const lv = lyLv(b), t = b.board_in || 0.75; return lv.length ? lv.map(v => ({ z: b.z + v.z - t, h: t, lv: v })) : [b]; };
const lySurf = b => { const lv = lyLv(b); return lv.length ? lv.map(v => ({ b, n: v.n, z: r2(b.z + v.z), room: v.room, name: `${v.name} of ${lyNm(b)}` })) : [{ b, n: 0, z: r2(b.z + b.h), room: null, name: lyNm(b) }]; };
const lyOnSurf = (a, b) => lySurf(b).find(q => Math.abs(q.z - a.z) < 0.05) || null;      // the surface of b that a stands on
function lyRoom(t, b) {
  let best = null;
  for (const q of lySolids(b)) if (q.z >= t.z + t.h - LY_EPS && (!best || q.z < best.q.z)) best = { q };
  return best ? { gap: best.q.z - t.z - t.h, name: best.q.lv ? `${best.q.lv.name} of ${lyNm(b)}` : lyNm(b) } : null;
}
// Up and down: the gap between two things (between their nearest solid parts), or minus how much height they share.
function lyUp(a, b) {
  let m = Infinity;
  for (const p of lySolids(a)) for (const q of lySolids(b)) m = Math.min(m, Math.max(p.z - q.z - q.h, q.z - p.z - p.h));
  return m;
}
const lySizeWords = it => lyRound(it) ? `${lenF(it.w)} across, ${lenF(it.h)} tall` : `${lenF(it.w, false)} by ${lenF(it.d, false)} by ${lenF(it.h)}`;
// What a thing stands on: 'floor', the thing whose top it rests on, or null (it is in the air, or reaches into something).
function lyUnder(L, a) {
  if (Math.abs(a.z) < 0.05) return 'floor';
  return L.items.find(b => b.id !== a.id && b.kind !== 'zone' && b.kind !== 'light' && lyPlan(a, b) < -LY_EPS && lySolids(b).some(q => Math.abs(q.z + q.h - a.z) < 0.05)) || null;
}
// What a thing hangs under: 'top' (the top of the space), the thing whose underside its top touches, or null.
function lyOver(L, a) {
  if (Math.abs(a.z + a.h - L.height_in) < 0.05) return 'top';
  return L.items.find(b => b.id !== a.id && b.kind !== 'zone' && lyPlan(a, b) < -LY_EPS && lySolids(b).some(q => Math.abs(q.z - a.z - a.h) < 0.05)) || null;
}
// What a thing carries when it is moved (Ethan, November 15, 2026: "Plants should be carried with shelves"): everything that stands
// on it, on any of its levels, or hangs under one of its solid parts, and what those carry in turn. A thing locked in place stays
// where it is, and so does an area to keep clear.
function lyRiders(L, it) {
  const out = [], seen = new Set([it.id]);
  const rides = (t, c) => lyPlan(t, c) < -LY_EPS && ((c.kind !== 'light' && lySolids(c).some(q => Math.abs(q.z + q.h - t.z) < 0.05))
    || (t.kind === 'light' && lySolids(c).some(q => Math.abs(q.z - t.z - t.h) < 0.05) && !lyUnder(L, t)));
  const walk = c => { for (const t of L.items) if (!seen.has(t.id) && t.kind !== 'zone' && !t.locked && rides(t, c)) { seen.add(t.id); out.push(t); walk(t); } };
  if (it.kind !== 'zone') walk(it);
  return out;
}
// A move begins: what the thing carries, each with its place as it is now. As the thing moves, each goes as far as it has gone.
const lyCarryStart = (L, it) => lyRiders(L, it).map(t => ({ it: t, was: { ...t } }));
const lyCarrySkip = riders => new Set((riders || []).map(r => r.it.id));
function lyCarryMove(it, from, riders) {
  const dx = it.x - from.x, dy = it.y - from.y, dz = it.z - from.z;
  for (const r of riders || []) { r.it.x = r2(r.was.x + dx); r.it.y = r2(r.was.y + dy); r.it.z = r2(r.was.z + dz); }
}
function lyWhere(L, a) {
  const u = lyUnder(L, a), o = a.kind === 'light' && !u ? lyOver(L, a) : null;
  const up = o === 'top' ? 'at the top of the space' : o ? `under ${lyNm(o)}` : u === 'floor' ? 'on the floor' : u ? `on ${(lyOnSurf(a, u) || { name: lyNm(u) }).name}` : `${lenF(r1(a.z))} off the floor`;
  return `${lenF(r1(a.x))} from the left, ${lenF(r1(a.y))} from the back, ${up}`;
}
// ---------- light from the drawing ----------
// The light a plant gets where it is drawn, in the figures and words of Grow lights (plantdb/lights.py), so the two pages agree for a
// plant straight under a light. For each drawn light that has its maker's figures:
//   - the light comes from its underside if it hangs, and from its top if it stands on something (a lamp's head is at its top);
//   - its figure for the distance from there to the top of the plant is read off the maker's figures (straight lines on log-log
//     axes, as lights.py does), and no closer than those figures can be trusted (near_in);
//   - a plant off to the side gets less: the square of (how far below) over (how far away). Straight under, all of it; as far to
//     the side as it is below, half of what that distance gives;
//   - a shelf or other thing between the light and the top of the plant shuts it out;
//   - its hours a day and its brightness make that a daily amount (mol/m² a day), and the lights add up.
// Daylight is not known here and is not counted. Other plants are not taken to shade it.
function lyPar(pts, d) {
  const p = (pts || []).filter(q => q[0] > 0 && q[1] > 0); if (!p.length) return null;
  if (p.length === 1) return p[0][1] * (p[0][0] / d) ** 1.6;
  let a, b;
  if (d <= p[0][0]) [a, b] = [p[0], p[1]];
  else if (d >= p[p.length - 1][0]) [a, b] = [p[p.length - 2], p[p.length - 1]];
  else { const i = p.findIndex(q => q[0] >= d); [a, b] = [p[i - 1], p[i]]; }
  return b[0] === a[0] ? a[1] : a[1] * (d / a[0]) ** (Math.log(b[1] / a[1]) / Math.log(b[0] / a[0]));
}
const lyInPlan = (b, x, y) => lyRound(b) ? Math.hypot(x - b.x - b.w / 2, y - b.y - b.d / 2) <= b.w / 2 + LY_EPS
  : x >= b.x - LY_EPS && x <= b.x + b.w + LY_EPS && y >= b.y - LY_EPS && y <= b.y + b.d + LY_EPS;
const lyHangs = (L, li) => !lyUnder(L, li);              // a light with nothing under it hangs; one on the floor or on a shelf stands
// What one light gives one plant: { li, up (from the plant's top up to the light), side, par, dli, far or close (outside the distances
// its figures cover), by (the thing in the way), nofig (it has no figures) }, or null when the light is not above the plant's top.
function lyLightOn(L, pl, li) {
  const top = pl.z + pl.h, src = lyHangs(L, li) ? li.z : li.z + li.h, up = src - top;
  if (up <= LY_EPS) return null;
  const cx = pl.x + pl.w / 2, cy = pl.y + pl.d / 2;
  let sx, sy;                                           // the point of the light nearest the plant, seen from above
  if (lyRound(li)) { const mx = li.x + li.w / 2, my = li.y + li.d / 2, off = Math.hypot(cx - mx, cy - my), k = off > li.w / 2 ? li.w / 2 / off : 1; sx = mx + (cx - mx) * k; sy = my + (cy - my) * k; }
  else { sx = clamp(cx, li.x, li.x + li.w); sy = clamp(cy, li.y, li.y + li.d); }
  const side = Math.hypot(cx - sx, cy - sy), dist = Math.hypot(up, side), out = { li, up: r2(up), side: r2(side), par: 0, dli: 0, by: null };
  if (!(li.pts || []).length) return { ...out, nofig: true };
  const near = li.near_in || 3;
  out.par = lyPar(li.pts, Math.max(dist, near)) * (up / dist) ** 2;
  out.dli = out.par * (li.dim_pct == null ? 100 : li.dim_pct) / 100 * (li.hours == null ? 12 : li.hours) * 0.0036;
  out.far = !!li.far_in && dist > li.far_in + LY_EPS; out.close = dist < near - LY_EPS;
  out.by = L.items.find(b => {                          // a board or other thing that the straight line from the light to the plant's top goes through
    if (b === li || b === pl || (b.kind !== 'shelf' && b.kind !== 'other')) return false;
    return lySolids(b).some(q => {
      const lo = Math.max(q.z, top), hi = Math.min(q.z + q.h, src); if (hi - lo < LY_EPS) return false;
      const t = ((lo + hi) / 2 - top) / up;
      return lyInPlan(b, cx + (sx - cx) * t, cy + (sy - cy) * t);
    });
  }) || null;
  return out;
}
function lyVerdict(dli, need) {                         // as lights.py, light_verdict
  if (!need) return 'unknown';
  if (dli < need.lo) return dli < need.lo * 0.8 ? 'too_dim' : 'dim';
  if (dli > need.hi) return dli > need.hi * 1.3 ? 'too_bright' : 'bright';
  return 'good';
}
// The light each plant on a layout gets: a Map from the plant's id to { dli (to one decimal, as Grow lights gives it), need, verdict,
// reached, on: the lights that reach it (the strongest first), shut: lights that would but for something in the way, nofig: lights
// straight over it that have no figures }. A plant is reached by the drawn lights when it gets 1 mol/m² a day from them or is
// straight under one that is on: only then is it called too dim, since a plant across the room has its daylight. The Map's own
// `any` says that some drawn light has figures; with none, nothing is said about light.
function lyLight(L) {
  const m = new Map(), lights = L.items.filter(b => b.kind === 'light' && !b.gone);
  m.any = lights.some(li => (li.pts || []).length);
  if (!lights.length) return m;
  for (const pl of L.items) {
    if (pl.kind !== 'plant') continue;
    const all = lights.map(li => lyLightOn(L, pl, li)).filter(Boolean);
    const on = all.filter(x => !x.nofig && !x.by && x.dli >= 0.05).sort((a, b) => b.dli - a.dli);
    const dli = r1(on.reduce((t, x) => t + x.dli, 0)), reached = dli >= 1 || on.some(x => x.side < 0.05);
    m.set(pl.id, { dli, need: pl.need || null, verdict: reached ? lyVerdict(dli, pl.need) : 'none', reached, on,
      shut: all.filter(x => !x.nofig && x.by && x.dli >= 0.5), nofig: all.filter(x => x.nofig && x.side < 0.05) });
  }
  return m;
}
const lyMol = n => `${fmt(n, 1)} mol/m² a day`;
function lyLightHtml(L, it) {                           // for the chosen thing's boxes: a plant's light where it is drawn; for a light, the plants it lights
  const m = LY.F.light; if (!m) return '';
  if (it.kind === 'light') {
    if (it.gone) return '';
    if (!(it.pts || []).length) return html`<p class="hint">${it.light_id ? 'This light has no maker’s figures in Grow lights' : 'This is not one of the lights in Grow lights'}, so the light it gives is not counted here.</p>`;
    const lit = [...m].filter(([, x]) => x.on.some(o => o.li.id === it.id)).map(([id]) => lyItem(id)).filter(Boolean);
    return html`<p class="hint">${lit.length ? `It lights ${lit.length === 1 ? 'one plant' : lit.length + ' plants'} drawn here: ${lit.slice(0, 4).map(lyNm).join(', ')}${lit.length > 4 ? ` and ${lit.length - 4} more` : ''}.` : 'No plant drawn here gets light from it.'}
      Its light is taken to come from its ${lyHangs(L, it) ? 'underside' : 'top, since it stands on something'}.</p>`;
  }
  const x = it.kind === 'plant' ? m.get(it.id) : null; if (!x) return '';
  if (!m.any) return x.nofig.length ? html`<p class="hint">${x.nofig.map(o => `${lyNm(o.li)} is over it, but has no maker’s figures, so the light it gives is not counted. `)}</p>` : '';
  const V = L.verdicts || {}, set = li => `${fmt(li.hours, 1)} hours a day${li.dim_pct < 100 ? ` at ${li.dim_pct}% brightness` : ''}`;
  return html`<p><strong>Light here:</strong> ${x.reached ? html`about ${lyMol(x.dli)}. ${lvTag(x.verdict, V[x.verdict] || '')}` : x.dli > 0 ? `about ${lyMol(x.dli)}: the lights drawn here hardly reach it.` : 'none of the lights drawn here reaches it.'}
      ${x.reached ? (x.need ? `It needs ${fmt(x.need.lo, 1)} to ${fmt(x.need.hi, 1)}.` : 'Its light needs are not set on its page.') : ''}</p>
    ${x.on.length || x.shut.length || x.nofig.length ? html`<ul class="ly-lightlist">
      ${x.on.slice(0, 4).map(o => html`<li>${lyNm(o.li)}: ${lenF(r1(o.up))} above its top${o.side >= 0.5 ? `, ${lenF(r1(o.side))} to the side` : ''}, ${set(o.li)}, about ${fmt(o.dli, 1)}.${o.close ? ' Closer than its figures go.' : o.far ? ' Further than its figures go, so this is rough.' : ''}</li>`)}
      ${x.shut.map(o => html`<li>${lyNm(o.li)} is shut out by ${lyNm(o.by)}.</li>`)}
      ${x.nofig.map(o => html`<li>${lyNm(o.li)} is over it, but has no maker’s figures, so its light is not counted.</li>`)}</ul>` : ''}
    <p class="hint">${x.on.length ? 'From the lights drawn here and their makers’ figures. ' : ''}Daylight is not counted.</p>`;
}
// ---------- the record ----------
// Where the drawing puts a plant, as a place in the record: { pid, label }. On a shelf's own layout, that shelf. On a room's or an
// area's, the shelf it stands in or on when that shelf is one of the record's (the smallest, if they nest), else the room itself.
// A space of your own is no place in the record, and a plant that is gone has no page: null.
const lyPaged = it => it.kind === 'plant' && !!it.plant && !it.gone;
function lyRecTo(L, it) {
  if (!lyPaged(it) || !L.pid) return null;
  if (L.spot_id) return { pid: L.spot_id, label: L.place };
  const cx = it.x + it.w / 2, cy = it.y + it.d / 2;
  const sh = L.items.filter(b => b.kind === 'shelf' && b.spot_id && !b.gone && lyInPlan(b, cx, cy)).sort((a, b) => a.w * a.d - b.w * b.d)[0];
  return sh ? { pid: sh.spot_id, label: sh.place || sh.name } : { pid: L.pid, label: L.place };
}
const lyRecList = L => L.items.map(it => ({ it, to: lyRecTo(L, it) })).filter(x => x.to && x.to.pid !== x.it.rec);      // the plants drawn here that the record has somewhere else
function lyRecHtml(L, it) {                             // for a plant's own boxes: where the record has it, and the way to move it there
  if (!lyPaged(it)) return '';
  const to = lyRecTo(L, it), at = it.rec_label || 'no room or shelf';
  if (!to) return html`In your record it is at ${at}.`;
  if (to.pid === it.rec) return html`In your record it is here, at ${at}.`;
  return html`In your record it is at ${at}. This layout has it at ${to.label}.
    ${lyCan() ? html`<button class="btn small ghost" type="button" id="ly-recone" data-act="lyrec" data-id="${it.id}">Move it in the record</button>` : ''}`;
}
function lyTallHtml(it) {                               // under a plant's size boxes: that its height here is its page's
  return it.page_h != null ? html`${LY.tall === it.id ? html`<strong>Saved on its page: ${lenF(it.page_h)} tall.</strong> ` : ''}Its height is the one on its page. Change it here and its page changes too.`
    : html`Its page has no height yet. A height typed here is saved on its page.
      ${lyCan() ? html`<button class="btn small ghost" type="button" id="ly-tallsave" data-act="lytall">Save this height on its page</button>` : ''}`;
}
function lyTallSave(it) {                               // the height drawn is right as it is (a guess that was good, or one typed before its page lost it): it goes on the page
  const id = it.id; lyPageH(it, it.h); LY.tall = id;
  const page = h => async () => { const t = lyItem(lyCur(id)); if (!t) return; lyPageH(t, h == null ? null : t.h); LY.tall = null; lyDrawAll(); await lySaveItem(t, t, { page_h: h == null ? null : t.h }); };
  lyUndoPush(`${it.name}: height saved on its page`, 'height saved', page(null), page(true));
  lyPanel(); lyLists(); lySay(`${it.name} is now ${lenF(it.h)} tall on its page. Undo takes that back.`);
  lySaveItem(it, it, { page_h: it.h });
  const b = document.getElementById('ly-f-h'); if (b) b.focus({ preventScroll: true });
}
function lyPageH(it, h) {                               // what the plant's page now says its height is, kept in step on this page
  it.page_h = h; const P = LY.d.plants.find(p => p.code === it.plant); if (!P) return;
  if (h != null) { P.h = h; P.guessed = P.guessed.filter(x => x !== 'height'); } else if (!P.guessed.includes('height')) P.guessed.push('height');
}
// What to look at on a layout: [{ kind, hard, ids, text }], the things that do not fit first.
//   outside   (hard) a thing sticks out of the space
//   overlap   (hard) two things take up the same room
//   zone             a thing is in an area to keep clear
//   nearlight        the top of a plant is closer to the light over it than the nearest distance the light's figures give (3 in for a light with none)
//   tight            a plant is closer to something than the room to leave around a plant (clear_in), beside it or above it
//   floating         a plant or other thing has nothing under it
//   toodim, dim, bright, toobright   a plant the drawn lights reach gets less, or more, light from them than its page says it needs,
//                    by a lot or by a little (lyLight)
//   count            more of one light are drawn than are owned
// The answer also carries the light each plant gets (its own `light`: lyLight), worked out once for the marks and the words.
function lyFindings(L) {
  const out = [], items = L.items, W = L.width_in, D = L.depth_in, H = L.height_in, clear = +L.clear_in || 0;
  const solid = it => it.kind !== 'zone';
  for (const a of items) {
    const s = [];
    if (a.x < -LY_EPS) s.push(['the left side', -a.x]);
    if (a.x + a.w > W + LY_EPS) s.push(['the right side', a.x + a.w - W]);
    if (a.y < -LY_EPS) s.push(['the back', -a.y]);
    if (a.y + a.d > D + LY_EPS) s.push(['the front', a.y + a.d - D]);
    if (a.z < -LY_EPS) s.push(['the floor', -a.z]);
    if (a.z + a.h > H + LY_EPS) s.push(['the top', a.z + a.h - H]);
    if (s.length) out.push({ kind: 'outside', hard: true, ids: [a.id], text: `${lyNm(a)} sticks out past ${s.map(([side, n]) => `${side} by ${lenF(r1(n))}`).join(' and ')}.` });
  }
  for (let i = 0; i < items.length; i++) for (let j = i + 1; j < items.length; j++) {
    const a = items[i], b = items[j];
    if (!solid(a) && !solid(b)) continue;
    const p = lyPlan(a, b), v = lyUp(a, b);
    if (!solid(a) || !solid(b)) {
      const [t, z] = solid(a) ? [a, b] : [b, a];
      if (p < -LY_EPS && v < -LY_EPS) out.push({ kind: 'zone', ids: [t.id, z.id], text: `${lyNm(t)} is in the area to keep clear, ${lyNm(z)}.` });
      continue;
    }
    if (p < -LY_EPS && v < -LY_EPS) {                    // on a level of a shelf and reaching into the level above: said as what it is
      const [t, sh] = lyLv(b).length ? [a, b] : lyLv(a).length ? [b, a] : [null, null], on = t && lyOnSurf(t, sh);
      out.push({ kind: 'overlap', hard: true, ids: [a.id, b.id], text: on && on.room != null && t.h > on.room + LY_EPS ? `${lyNm(t)} is too tall for ${on.name} by ${lenF(r1(t.h - on.room))}.` : `${lyNm(a)} and ${lyNm(b)} overlap by ${lenF(r1(Math.min(-p, -v)))}.` });
      continue;
    }
    const [pl, li] = a.kind === 'plant' && b.kind === 'light' ? [a, b] : b.kind === 'plant' && a.kind === 'light' ? [b, a] : [null, null];
    if (pl && p < LY_EPS && li.z >= pl.z + pl.h - LY_EPS) {                 // a plant with a light straight over it
      const gap = li.z - pl.z - pl.h, near = li.near_in || 3;
      if (gap < near - LY_EPS) out.push({ kind: 'nearlight', ids: [pl.id, li.id], text: `The top of ${lyNm(pl)} is ${lenF(r1(gap))} under ${lyNm(li)}: ${li.near_in ? `closer than that light's figures go (they start at ${lenF(near)})` : `closer than ${lenF(near)}`}. Leaves that close to a light can scorch.` });
      continue;
    }
    if (!clear || (a.kind !== 'plant' && b.kind !== 'plant')) continue;
    if (v < -LY_EPS && p < clear - LY_EPS) out.push({ kind: 'tight', ids: [a.id, b.id], text: p < 0.05 ? `${lyNm(a)} and ${lyNm(b)} touch.` : `${lyNm(a)} and ${lyNm(b)} are ${lenF(r1(p))} apart.` });
    else if (p < -LY_EPS) for (const [lo, hi] of [[a, b], [b, a]]) {          // one over the other: a plant with little room above it
      const r = lo.kind === 'plant' ? lyRoom(lo, hi) : null;
      if (r && r.gap < clear - LY_EPS) out.push({ kind: 'tight', ids: [lo.id, hi.id], text: r.gap < 0.05 ? `The top of ${lyNm(lo)} touches ${r.name}.` : `There is ${lenF(r1(r.gap))} between the top of ${lyNm(lo)} and ${r.name}.` });
    }
  }
  const stuck = new Set(out.filter(f => f.hard).flatMap(f => f.ids));
  for (const a of items) {
    if ((a.kind !== 'plant' && a.kind !== 'other') || a.z < 0.05 || stuck.has(a.id)) continue;
    let under = null, at = 0;
    for (const b of items) if (b !== a && solid(b) && lyPlan(a, b) < -LY_EPS) for (const q of lySolids(b)) if (q.z + q.h <= a.z + 0.05 && q.z + q.h > at) { at = q.z + q.h; under = b; }
    const gap = a.z - at;
    if (gap > 0.05) out.push({ kind: 'floating', ids: [a.id], text: `${lyNm(a)} has nothing under it: it is ${lenF(r1(gap))} above ${under ? lyNm(under) : 'the floor'}.` });
  }
  const light = lyLight(L);
  for (const [id, x] of light) {
    if (!LY_LV[x.verdict]) continue;
    out.push({ kind: LY_LV[x.verdict], ids: [id], text: `${lyNm(items.find(a => a.id === id))} gets about ${lyMol(x.dli)} from the lights drawn here, and needs ${fmt(x.need.lo, 1)} to ${fmt(x.need.hi, 1)}.` });
  }
  const drawn = {};
  for (const a of items) if (a.kind === 'light' && a.light_id) (drawn[a.light_id] = drawn[a.light_id] || []).push(a);
  for (const list of Object.values(drawn)) if (list[0].owned != null && list.length > list[0].owned) out.push({ kind: 'count', ids: list.map(x => x.id), text: `${list[0].name}: ${list.length} are drawn and you own ${list[0].owned}.` });
  const F = out.filter(f => f.hard).concat(out.filter(f => !f.hard));
  F.light = light;
  return F;
}
// The things a finding puts its mark on: the thing in an area to keep clear and not the area, the plant under a light and not the light.
const lyMarked = f => f.kind === 'zone' || f.kind === 'nearlight' ? f.ids.slice(0, 1) : f.ids;
function lyState(F) {                                   // each thing's mark: 'hard' (it does not fit), 'soft' (to look at) or none
  const m = new Map();
  for (const f of F) for (const id of lyMarked(f)) if (m.get(id) !== 'hard') m.set(id, f.hard ? 'hard' : 'soft');
  return m;
}
// Would thing t be clear of everything on the layout? margin is the room to leave around a plant.
function lyFree(L, t, margin) {
  if (t.x < -LY_EPS || t.y < -LY_EPS || t.z < -LY_EPS || t.x + t.w > L.width_in + LY_EPS || t.y + t.d > L.depth_in + LY_EPS || t.z + t.h > L.height_in + LY_EPS) return false;
  return L.items.every(b => {
    const p = lyPlan(t, b), v = lyUp(t, b);
    if (p < -LY_EPS && v < -LY_EPS) return false;                 // this keeps a new thing out of an area to keep clear, too
    if (b.kind === 'zone' || t.kind === 'zone' || !margin) return true;
    const r = p < -LY_EPS ? lyRoom(t, b) : null;
    return !(v < -LY_EPS && p < margin - LY_EPS) && !(r && r.gap < margin - LY_EPS);
  });
}
// Puts a thing on one place to stand (q: from lySurf, or null for the floor). Already over that shelf, it keeps its place and
// changes height; else it goes to the first place on it that is clear, from the back left; else to its back left corner, and the
// marks say what it runs into.
function lyPutOn(L, it, q, skip) {
  const z = r2(q ? q.z : 0);
  if (!q || lyInPlan(q.b, it.x + it.w / 2, it.y + it.d / 2)) return { ...it, z };
  const T = { ...L, items: L.items.filter(b => b.id !== it.id && !(skip && skip.has(b.id))) }, g = Math.max(+L.grid_in || 1, 0.5), step = g * Math.max(1, Math.floor(Math.min(it.w, it.d) / (2 * g))), s = q.b;
  for (const margin of it.kind === 'plant' && +L.clear_in ? [+L.clear_in, 0] : [0])
    for (let y = Math.max(s.y, 0); y + it.d <= s.y + s.d + LY_EPS; y += step) for (let x = Math.max(s.x, 0); x + it.w <= s.x + s.w + LY_EPS; x += step) {
      const t = { ...it, x: r2(x), y: r2(y), z }; if (lyFree(T, t, margin)) return t;
    }
  return { ...it, x: r2(Math.max(s.x, 0)), y: r2(Math.max(s.y, 0)), z };
}
// A thing that rests on something goes with what is under it when it is moved sideways (dragged or stepped in the top view, or its
// place typed). was: the thing before the move. Still over what it stood on, it keeps its height. Over another shelf or thing, it
// goes onto it: on a shelf with levels, the lowest level it fits on with nothing in its way, else the lowest it is not too tall
// for, else the top. Over nothing, it goes down to the floor. A thing in the air (a hanging light, a basket) keeps its height, and
// so do a shelf, an area to keep clear, and a thing whose middle has left the space. This is how a plant is dropped onto a shelf.
function lyLand(L, it, was, skip) {                     // skip: what it carries, which is not in its way and is nothing to land on
  if (it.kind === 'zone' || it.kind === 'shelf') return;
  const u = lyUnder(L, was); if (!u) return;
  const cx = it.x + it.w / 2, cy = it.y + it.d / 2;
  if (cx < -LY_EPS || cy < -LY_EPS || cx > L.width_in + LY_EPS || cy > L.depth_in + LY_EPS) return;
  if (u !== 'floor' && lyInPlan(u, cx, cy)) return;
  const mine = q => q.id === it.id || (skip && skip.has(q.id));
  const b = L.items.filter(q => !mine(q) && (q.kind === 'shelf' || q.kind === 'other') && lyInPlan(q, cx, cy)).sort((p, q) => p.w * p.d - q.w * q.d)[0];
  if (!b) { it.z = 0; return; }
  const T = { ...L, items: L.items.filter(q => !mine(q)) }, all = lySurf(b), fits = all.filter(q => q.room == null || it.h <= q.room + LY_EPS);
  it.z = (fits.find(q => lyFree(T, { ...it, z: q.z }, 0)) || fits[0] || all[all.length - 1]).z;
}
// Where a new thing goes: the first place it is clear of everything, level by level from the bottom (the floor, then the top of
// each shelf or other thing), from the back left corner across. on: a shelf to try first (the one chosen on the drawing). A thing
// that hangs starts up under that shelf, or at the top of the space. An area to keep clear starts on the floor. Where nothing is
// free it goes to the back left corner of that shelf, or of the space, and the marks say what it runs into.
function lyPlace(L, it, on, hangs) {
  const g = Math.max(+L.grid_in || 1, 0.5), step = g * Math.max(1, Math.floor(Math.min(it.w, it.d) / (2 * g)));
  const tops = L.items.filter(b => (b.kind === 'shelf' || b.kind === 'other') && b !== on).flatMap(lySurf).sort((a, b) => a.z - b.z);
  const levels = hangs ? [on ? { b: on } : null] : it.kind === 'zone' ? [null] : (on ? lySurf(on).concat([null]) : [null]).concat(tops);      // each a place to stand (lySurf), or null for the floor
  for (const margin of it.kind === 'plant' && +L.clear_in ? [+L.clear_in, 0] : [0]) for (const q of levels) {
    const s = q ? q.b : null, x0 = s ? Math.max(s.x, 0) : 0, y0 = s ? Math.max(s.y, 0) : 0, x1 = s ? s.x + s.w : L.width_in, y1 = s ? s.y + s.d : L.depth_in;
    const z = hangs ? (s ? s.z : L.height_in) - it.h : (q ? q.z : 0);
    for (let y = y0; y + it.d <= y1 + LY_EPS; y += step) for (let x = x0; x + it.w <= x1 + LY_EPS; x += step) {
      const t = { ...it, x: r2(x), y: r2(y), z: r2(z) };
      if (lyFree(L, t, margin)) return t;
    }
  }
  const s = it.kind === 'zone' ? null : on || null;
  return { ...it, x: s ? r2(Math.max(s.x, 0)) : 0, y: s ? r2(Math.max(s.y, 0)) : 0, z: r2(Math.max(0, hangs ? (s ? s.z : L.height_in) - it.h : s ? lySurf(s)[0].z : 0)) };
}
// The level being shown in the top view, when one is chosen: the things standing on that shelf, up to the next shelf above it.
function lyDim(L, level) {
  const s = level ? L.items.find(x => x.id === level) : null; if (!s) return null;
  const above = L.items.filter(b => b !== s && b.kind === 'shelf' && b.z >= s.z + s.h - LY_EPS && lyPlan(s, b) < -LY_EPS).sort((a, b) => a.z - b.z)[0];
  const lo = s.z + s.h - 0.05, hi = above ? above.z : Infinity;
  return new Set(L.items.filter(b => b !== s && !(b.z >= lo && b.z < hi - LY_EPS)).map(b => b.id));
}
const lyLevels = L => L.items.filter(a => a.kind === 'shelf' && L.items.some(b => b !== a && b.kind === 'shelf' && lyPlan(a, b) < -LY_EPS && lyUp(a, b) >= -LY_EPS)).sort((a, b) => a.z - b.z);
// Which level the top view shows (0: every level). level 'auto', the usual, is the level the chosen thing is on, so that the top view
// of a shelf unit is not just its top board with everything else hidden under it.
function lyLevelOf(L, level, sel) {
  const levels = lyLevels(L); if (levels.length < 2) return 0;
  if (level !== 'auto') return levels.some(s => s.id === level) ? level : 0;
  const it = sel != null ? L.items.find(x => x.id === sel) : null; if (!it) return 0;
  if (levels.includes(it)) return it.id;
  const below = levels.filter(s => s.z + s.h <= it.z + 0.05 && lyPlan(it, s) < -LY_EPS).sort((a, b) => b.z - a.z)[0];
  return below ? below.id : 0;
}

// Is the layout one shelf unit (its levels fill most of the space), and not a room with shelves in it?
const lyIsUnit = L => { const lv = lyLevels(L); return lv.length > 1 && lv[0].w * lv[0].d >= 0.6 * L.width_in * L.depth_in; };
// The level the top view shows now (0: every level). "The chosen thing's level" stays on the level last shown when nothing is
// chosen; to begin with, on a layout that is one shelf unit, that is the lowest level with something on it, so the first thing
// seen is not every level drawn over the others.
function lyLevelNow() {
  const L = LY.d;
  if (LY.level !== 'auto') return lyLevelOf(L, LY.level, null);
  const levels = lyLevels(L); if (levels.length < 2) return 0;
  if (lyItem(LY.sel)) { const lv = lyLevelOf(L, 'auto', LY.sel); if (lv) LY.lastLv = lv; return lv; }
  if (LY.lastLv && levels.some(s => s.id === LY.lastLv)) return LY.lastLv;
  if (!lyIsUnit(L)) return 0;                                                        // a room with a shelf unit in it: all of it
  const used = levels.find(s => L.items.some(b => b.kind !== 'shelf' && b.kind !== 'zone' && Math.abs(b.z - s.z - s.h) < 0.05 && lyPlan(b, s) < -LY_EPS));
  return (LY.lastLv = (used || levels[0]).id);
}

// ---------- the front view, one wall at a time ----------
// In a room, an area or a space of your own the front view looks at one wall from inside and draws only the things at that wall
// (Ethan, November 15, 2026: "focus its perspective on one wall at a time, to reduce screen clutter"). A thing is at a wall when it
// is within LY_WALL_IN of it; what stands on a thing or hangs under it is wherever that thing is. A thing far from every wall is
// at none of them: those have a view of their own, 'mid' (Ethan, November 15: "Things far away from every wall should have a view
// of their own and not be shown in the front view for the specified wall"). So every thing is in at least one view. 'all' draws
// everything, as the layout of one shelf or spot always does. 'mid' and 'all' look the way the back wall's view does. Looking at
// a wall, the view's left is your left as you face it:
//   back   left to right is the top view's left to right
//   right  left to right is the top view's back to front
//   front  left to right is the top view's right to left
//   left   left to right is the top view's front to back
const LY_WALLS = { back: 'The back wall', left: 'The left wall', right: 'The right wall', front: 'The front wall', mid: 'The middle, away from the walls', all: 'Everything at once' };
const LY_WALL_OPT = { back: 'Back wall', left: 'Left wall', right: 'Right wall', front: 'Front wall', mid: 'Middle', all: 'Everything' };      // as the list beside the front view has them: short, so none is cut off in the list at the largest, widest text on a phone
const LY_WALL_ENDS = { back: ['Left', 'Right'], right: ['Back', 'Front'], front: ['Right', 'Left'], left: ['Front', 'Back'] };      // what is at the view's left and right
const LY_WALL_IN = 24;                                  // nearer a wall than this (2 ft), a thing is at that wall
const lyWalled = L => !L.spot_id;
const lyFaceOf = wall => (LY_WALL_ENDS[wall] ? wall : 'back');
const lyFaceNow = () => (LY && lyWalled(LY.d) ? lyFaceOf(LY.wall) : 'back');
const lySide = face => face === 'left' || face === 'right';
const lyAcrossW = (L, face) => (lySide(face) ? L.depth_in : L.width_in);                                   // how wide that wall is
const lyAc = (L, it, face) => (face === 'left' ? L.depth_in - it.y - it.d : face === 'right' ? it.y : face === 'front' ? L.width_in - it.x - it.w : it.x);      // where a thing is across the view, from its left
const lyAw = (it, face) => (lySide(face) ? it.d : it.w);                                                  // and how wide it is there
const lyNear = (L, it, face) => (face === 'left' ? it.x + it.w : face === 'right' ? L.width_in - it.x : face === 'front' ? L.depth_in - it.y : it.y + it.d);      // how far its near side is from the wall: the larger, the nearer to you
function lyWallsOf(L, it, seen) {                        // the walls a thing is at (or 'mid' alone), the first being the view the front view goes to for it
  const u = lyUnder(L, it), c = u && u !== 'floor' ? u : it.kind === 'light' && !u ? lyOver(L, it) : null;
  seen = seen || new Set(); seen.add(it.id);
  if (c && c !== 'top' && !seen.has(c.id)) return lyWallsOf(L, c, seen);
  const d = { back: Math.max(0, it.y), left: Math.max(0, it.x), right: Math.max(0, L.width_in - it.x - it.w), front: Math.max(0, L.depth_in - it.y - it.d) };
  const at = Object.keys(d).filter(w => d[w] <= LY_WALL_IN + LY_EPS);
  return at.length ? at : ['mid'];
}
const lyWallSet = (L, wall) => (wall === 'all' ? null : new Set(L.items.filter(it => lyWallsOf(L, it).includes(wall)).map(it => it.id)));      // the things a wall's view draws (null: all of them)
// The front view goes to the wall the thing is at, unless it is at the wall being looked at already. Called when a thing is
// chosen and when the chosen thing has been moved, so the chosen thing is in the front view; a wall picked by hand stays until then.
function lyWallFollow(it) {
  if (!LY || !it || !lyWalled(LY.d) || LY.wall === 'all' || lyViewNow() === 'top') return false;
  const at = lyWallsOf(LY.d, it); if (at.includes(LY.wall)) return false;
  LY.wall = at[0]; lyPrefEach({ wall: LY.wall }); return true;
}

// ---------- the drawing ----------
const lyMargin = (L, view, face) => Math.max(1, 0.04 * Math.max(view === 'top' ? L.width_in : lyAcrossW(L, face), view === 'top' ? L.depth_in : L.height_in));      // room round the space in a view, so a thing that sticks out is still seen
function lyMajor(step) {                                // every how many grid lines a heavier one is drawn: each foot, or each 10 cm
  if (lenU() === 'cm') { const cm = step * 2.54, k = 10 / cm; return cm < 9.5 && Math.abs(k - Math.round(k)) < 0.02 ? Math.round(k) : 5; }
  const k = 12 / step; return step < 12 && Math.abs(k - Math.round(k)) < 1e-6 ? Math.round(k) : 4;
}
function lyDrawnStep(L, S) {                            // the squares drawn: the grid's own, or where those would be too fine to see, a few of them to a square
  const g = +L.grid_in || 1; let step = g;
  for (const k of [1, 2, 4, 6, 12, 24, 48, 96, 192]) { step = g * k; if (step * S >= 7) break; }
  return step;
}
const lyItTf = (L, it, view, o) => `translate(${lyNum(view === 'top' ? it.x : lyAc(L, it, (o && o.face) || 'back'))} ${lyNum(view === 'top' ? it.y : L.height_in - it.z - it.h)})`;
const lyItCls = (it, o) => `ly-it ly-k-${it.kind}${lyLv(it).length ? ' ly-open' : ''}${o.state.get(it.id) ? ' is-' + o.state.get(it.id) : ''}${o.sel === it.id ? ' is-sel' : ''}${it.locked ? ' is-locked' : ''}${it.size_locked ? ' is-sizelocked' : ''}${o.dim && o.dim.has(it.id) ? ' is-dim' : ''}${o.can && !it.locked ? ' can-move' : ''}`;
const lyTopOf = it => (lyLv(it).length ? it.z + lyLv(it)[0].z : it.z + it.h);      // seen from above, a shelf with levels is drawn under what stands in it
function lyItLabel(L, it, F) {
  const mine = (F || []).filter(f => f.ids.includes(it.id)), said = mine.some(f => lyIsLv(f.kind));       // a plant marked for its light is already told it
  return `${it.sort}. ${it.name}, ${(L.kinds || LYL.kinds)[it.kind].toLowerCase()}. ${lySizeWords(it)}. ${lyWhere(L, it)}.${it.locked ? ' Locked in place.' : ''}${it.size_locked ? ' Its size is locked.' : ''}${said ? '' : lyLightWords(L, F, it)}${mine.length ? ' ' + mine.map(f => f.text).join(' ') : ''}`;
}
// One thing in one view, in pixels: its size, the disc its number sits in, and where that disc goes. A pot's number is in its
// corner; a board's or a strip's is part of the way along it (a light's and a shelf's at different places, so the number of a
// shelf and that of the strip under it do not sit on each other); a shelf seen from above has it in its front right corner,
// clear of the pots, which fill a shelf from the back left.
function lyGeo(it, view, o) {
  const top = view === 'top', w = top ? it.w : lyAw(it, o.face || 'back'), h = top ? it.d : it.h, wpx = w * o.S, hpx = h * o.S;
  const br = clamp(Math.min(wpx, hpx) * 0.45, 0.45 * o.rem, 0.72 * o.rem);
  const inside = wpx >= 3.4 * br && hpx >= 2.4 * br;                                   // room for the disc in a corner; else it sits in the middle
  const along = wpx >= 5 * br && (!inside || it.kind === 'light'), far = inside && !along && it.kind === 'shelf' && top;
  const at = along ? (o.along && o.along.get(it.id)) || lyAlong(it)[0] : 0;
  const bx = along ? wpx * at : far ? wpx - br - 3 : inside ? br + 3 : wpx / 2;
  const by = along || !inside ? hpx / 2 : far ? hpx - br - 3 : br + 3;
  return { top, w, h, wpx, hpx, br, inside, along, far, bx, by, fx: wpx - (inside ? br + 3 : 0), fy: inside ? br + 3 : 0 };      // fx, fy: where its mark (the cross or the exclamation mark) goes
}
// How far along a board or a strip its number may sit, the place to try first leading. A light's is never in its middle, where its sun is drawn.
const lyAlong = it => (it.kind === 'light' ? [0.3, 0.7, 0.15, 0.85, 0.4, 0.6] : it.kind === 'shelf' ? [0.5, 0.7, 0.3, 0.85, 0.15, 0.6, 0.4] : [0.7, 0.5, 0.3, 0.85, 0.15, 0.6, 0.4]);
// For each board and strip in a view, where along it its number goes: the first of those places that is clear of the numbers and
// marks of the other things, so a strip's number is not on top of the number of a pot under it.
const lyDrawn = (it, view, o) => view === 'top' || !o.only || o.only.has(it.id);      // is the thing in this view at all (the front view of one wall leaves out the things at the others)
// The names along the lower edges of the things in a front view: a name that would run into the name of a nearer thing, or
// that a nearer thing stands in front of, is left out (the thing keeps its number, and its name is in the list).
function lyNameClash(L, o) {
  const out = new Set(), kept = [], fs = 0.8 * o.rem, face = o.face || 'back';
  const things = L.items.filter(it => lyDrawn(it, 'front', o)).sort((a, b) => lyNear(L, b, face) - lyNear(L, a, face) || a.sort - b.sort);
  for (const it of things) {
    const g = lyGeo(it, 'front', o), nm = lyNameOf(it, g, o); if (!nm) continue;
    const cx = lyAc(L, it, face) * o.S + g.wpx / 2, y = (L.height_in - it.z) * o.S - 6 - fs * 0.4, hw = nm.length * fs * 0.29 + 3;
    const behind = things.some(b => b !== it && b.kind !== 'zone' && !lyLv(b).length && lyNear(L, b, face) > lyNear(L, it, face) + LY_EPS
      && Math.abs(lyAc(L, b, face) * o.S + lyAw(b, face) * o.S / 2 - cx) < lyAw(b, face) * o.S / 2 + hw * 0.5 && (L.height_in - b.z - b.h) * o.S < y && (L.height_in - b.z) * o.S > y);
    if (behind || kept.some(k => Math.abs(k.cx - cx) < k.hw + hw && Math.abs(k.y - y) < fs * 1.2)) out.add(it.id); else kept.push({ cx, y, hw });
  }
  return out;
}
function lyLabSpots(L, view, o) {
  const out = new Map(), taken = [], faint = it => !!(o.dim && o.dim.has(it.id));
  const all = L.items.filter(it => !faint(it) && lyDrawn(it, view, o)).map(it => ({ it, g: lyGeo(it, view, o), x: (view === 'top' ? it.x : lyAc(L, it, o.face || 'back')) * o.S, y: (view === 'top' ? it.y : L.height_in - it.z - it.h) * o.S }));
  for (const { it, g, x, y } of all) if (!g.along) { taken.push([x + g.bx, y + g.by, g.br]); if (o.state.get(it.id)) taken.push([x + g.fx, y + g.fy, g.br]); const lv = lyLvAt(it, g, o); if (lv) taken.push([x + lv.x, y + lv.y, g.br]); }
  for (const { it, g, x, y } of all) if (g.along) {
    const clear = f => taken.every(([tx, ty, tr]) => Math.hypot(tx - x - g.wpx * f, ty - y - g.hpx / 2) > tr + g.br + 1), tries = lyAlong(it), f = tries.find(clear) || tries[0];
    out.set(it.id, f); taken.push([x + g.wpx * f, y + g.hpx / 2, g.br]);
    if (o.state.get(it.id)) taken.push([x + g.fx, y + g.fy, g.br]);
  }
  return out;
}
// What is drawn of one thing: its shape, and (lyItemLab) its number, its mark and its name. The shapes of every thing are drawn
// first and the numbers after them, so that no number is hidden under another thing. Each group carries the thing's place
// (transform) and its marks (class); the shape's group is the control, with its words (aria-label).
function lyItemInner(L, it, view, o) {
  const { top, w, h, wpx, hpx } = lyGeo(it, view, o), S = o.S, u = n => lyNum(n / S), rem = o.rem, min = 1.5 * rem;
  const oval = top && it.shape === 'round', soft = !top && it.shape === 'round';
  const shape = (cls, more) => oval ? html`<ellipse class="${cls}" cx="${lyNum(w / 2)}" cy="${lyNum(h / 2)}" rx="${lyNum(w / 2)}" ry="${lyNum(h / 2)}" ${raw(more || '')}/>`
    : html`<rect class="${cls}" width="${lyNum(w)}" height="${lyNum(h)}" ${soft ? raw(`rx="${lyNum(Math.min(w, h) * 0.14)}"`) : ''} ${raw(more || '')}/>`;
  const photo = it.photo && o.photos && wpx >= 1.6 * rem && hpx >= 1.6 * rem, cid = `ly-c-${o.id}-${it.id}`;
  return html`${wpx < min || hpx < min ? html`<rect class="ly-hit" x="${u((wpx - Math.max(wpx, min)) / 2)}" y="${u((hpx - Math.max(hpx, min)) / 2)}" width="${u(Math.max(wpx, min))}" height="${u(Math.max(hpx, min))}"/>` : ''}
    ${shape('ly-shape', `stroke-width="${u(2.5)}"${it.kind === 'zone' || it.kind === 'light' ? ` stroke-dasharray="${u(7)} ${u(4)}"` : ''}`)}
    ${photo ? html`<clipPath id="${cid}">${shape('ly-clip')}</clipPath><image class="ly-photo" href="${thumbUrl(it.photo)}" width="${lyNum(w)}" height="${lyNum(h)}" preserveAspectRatio="xMidYMid slice" clip-path="url(#${cid})"/>${shape('ly-rim', `stroke-width="${u(2.5)}"`)}` : ''}
    ${it.kind === 'zone' ? shape('ly-zfill', `fill="url(#ly-z-${o.id})"`) : ''}
    ${top ? '' : lyLv(it).map(v => html`<rect class="ly-board" y="${lyNum(h - v.z)}" width="${lyNum(w)}" height="${lyNum(it.board_in || 0.75)}"/>`)}
    ${it.kind === 'light' && Math.min(wpx, hpx) >= 1.3 * rem ? html`<g class="ly-sun" transform="translate(${lyNum(w / 2)} ${lyNum(h / 2)})"><circle r="${u(0.22 * rem)}"/><circle class="ly-rays" r="${u(0.45 * rem)}" stroke-width="${u(0.2 * rem)}" stroke-dasharray="${u(0.12 * rem)} ${u(0.233 * rem)}"/></g>` : ''}
    ${shape('ly-hatch ly-hatch-h', `fill="url(#ly-hh-${o.id})"`)}${shape('ly-hatch ly-hatch-s', `fill="url(#ly-hs-${o.id})"`)}`;
}
// A plant's light, as the sign Grow lights gives it, in that verdict's colour: where the thing's mark would be when it has none,
// else beside the mark (or under it on a narrow thing). A plant no drawn light reaches has a grey dash. No signs at all on a layout
// with no light that has its maker's figures.
function lyLvAt(it, g, o) {
  const x = it.kind === 'plant' && !o.mini && o.F && o.F.light && o.F.light.any ? o.F.light.get(it.id) : null;
  if (!x || !LY_LV_SIGN[x.verdict]) return null;
  const marked = !!o.state.get(it.id), wide = g.wpx >= 6.2 * g.br;
  return { v: x.verdict, x: marked && wide ? g.fx - 2 * g.br - 2 : g.fx, y: marked && !wide ? g.fy + 2 * g.br + 2 : g.fy };
}
const lyLvKey = (it, o) => { const x = it.kind === 'plant' && o.F && o.F.light && o.F.light.any ? o.F.light.get(it.id) : null; return x ? `${x.verdict}${o.state.get(it.id) ? '!' : ''}` : ''; };
// A thing's name along its lower edge: in the middle, or for a shelf seen from above, from the left as far as its number in the
// corner. Cut short to the thing's width, and left out where there is no room for four letters.
function lyNameOf(it, g, o) {
  const fs = 0.8 * o.rem, chars = Math.floor((g.wpx - 8 - (g.far ? 2 * g.br + 8 : 0)) / (fs * 0.56)), named = !o.mini && chars >= 4 && g.hpx >= (g.inside && !g.far ? 2 * g.br + 8 : 0) + fs * 1.5;
  return named ? (it.name.length > chars ? it.name.slice(0, chars - 1).trimEnd() + '…' : it.name) : '';
}
function lyItemLab(L, it, view, o) {
  const g = lyGeo(it, view, o), { w, h, wpx, hpx, br, inside, far, bx, by, fx, fy } = g, u = n => lyNum(n / o.S), fs = 0.8 * o.rem, lv = lyLvAt(it, g, o);
  const name = o.noname && o.noname.has(it.id) ? '' : lyNameOf(it, g, o);
  return html`${o.mini ? '' : html`<g class="ly-badge" transform="translate(${u(bx)} ${u(by)})"><circle r="${u(br)}" stroke-width="${u(1.5)}"/><text font-size="${u(Math.min(fs, br * 1.3))}" text-anchor="middle" dominant-baseline="central">${it.sort}</text></g>`}
    <g class="ly-flag" transform="translate(${u(fx)} ${u(fy)})"><circle r="${u(br)}" stroke-width="${u(1.5)}"/>
      <text class="ly-flag-h" font-size="${u(br * 1.4)}" text-anchor="middle" dominant-baseline="central">✗</text><text class="ly-flag-s" font-size="${u(br * 1.5)}" text-anchor="middle" dominant-baseline="central">!</text></g>
    ${lv ? html`<g class="ly-lvb ly-lvb-${lv.v}" transform="translate(${u(lv.x)} ${u(lv.y)})"><circle r="${u(br)}" stroke-width="${u(1.5)}"/><text font-size="${u(br * (LY_LV_SIGN[lv.v].length > 1 ? 0.82 : 1.25))}" text-anchor="middle" dominant-baseline="central">${LY_LV_SIGN[lv.v]}</text></g>` : ''}
    ${name ? html`<text class="ly-name" x="${far ? u(6) : lyNum(w / 2)}" y="${lyNum(h - 6 / o.S)}" font-size="${u(fs)}" stroke-width="${u(4)}" text-anchor="${far ? 'start' : 'middle'}">${name}</text>` : ''}`;
}
const lyLabCls = (it, o) => lyItCls(it, o).replace('ly-it', 'ly-lab');
function lySelMark(L, it, view, o) {                    // the ring round the chosen thing, drawn last so nothing hides it, and its corner handle
  const top = view === 'top', u = n => lyNum(n / o.S), w = top ? it.w : lyAw(it, o.face || 'back'), h = top ? it.d : it.h, pad = 4 / o.S, hs = 1.05 * o.rem;
  return html`<g class="ly-selmark" data-id="${it.id}" transform="${lyItTf(L, it, view, o)}">${top && it.shape === 'round'
    ? html`<ellipse class="ly-selring" cx="${lyNum(w / 2)}" cy="${lyNum(h / 2)}" rx="${lyNum(w / 2 + pad)}" ry="${lyNum(h / 2 + pad)}" stroke-width="${u(3)}"/>`
    : html`<rect class="ly-selring" x="${lyNum(-pad)}" y="${lyNum(-pad)}" width="${lyNum(w + 2 * pad)}" height="${lyNum(h + 2 * pad)}" stroke-width="${u(3)}"/>`}
    ${o.can && !it.size_locked ? html`<rect class="ly-handle ly-handle-${view}" x="${lyNum(w - hs / 2 / o.S)}" y="${lyNum((top ? h : 0) - hs / 2 / o.S)}" width="${u(hs)}" height="${u(hs)}" stroke-width="${u(2)}"><title>Drag this corner to change its size</title></rect>` : ''}</g>`;
}
// A drawing is one stop for the Tab key, not one for each thing on it: Tab lands on the chosen thing, or on the first thing when
// none is chosen, and Page Down and Page Up go from thing to thing (the arrow keys move the thing itself).
function lyTabStop(L, o) {
  const can = L.items.filter(it => !(o.dim && o.dim.has(it.id)) && (!o.only || o.only.has(it.id)));
  return (can.find(it => it.id === o.sel) || can[0] || {}).id;
}
// One view of a layout as an SVG. o: { S: pixels to the inch, rem: pixels to the rem, id, live (things can be chosen and moved),
// can, sel, state, dim, grid, photos, label, mini }
function lySvg(L, view, o) {
  const top = view === 'top', face = o.face || 'back', W = top ? L.width_in : lyAcrossW(L, face), V = top ? L.depth_in : L.height_in, S = o.S, m = o.m != null ? o.m : lyMargin(L, view, face), u = n => lyNum(n / S);
  if (!o.along) o = { ...o, along: lyLabSpots(L, view, o) };
  if (!top && !o.noname) o = { ...o, noname: lyNameClash(L, o) };
  const items = L.items.filter(it => lyDrawn(it, view, o));
  const mark = top && o.wallmark ? { back: [0, 0, W, 0], front: [0, V, W, V], left: [0, 0, 0, V], right: [W, 0, W, V] }[o.wallmark] : null;      // the wall the front view is looking at
  const step = lyDrawnStep(L, S), major = step * lyMajor(step);
  const faint = it => !!(o.dim && o.dim.has(it.id));
  const order = items.slice().sort((a, b) => faint(b) - faint(a) || (b.kind === 'zone') - (a.kind === 'zone') || (top ? lyTopOf(a) - lyTopOf(b) : lyNear(L, a, face) - lyNear(L, b, face)) || a.sort - b.sort);
  const sel = o.live && o.sel != null ? items.find(x => x.id === o.sel) : null;
  const stop = lyTabStop(L, o);                         // the one thing in this drawing that Tab lands on
  const pat = (id, size, cls, sw, oy) => html`<pattern id="${id}" width="${lyNum(size)}" height="${lyNum(size)}" y="${lyNum(oy)}" patternUnits="userSpaceOnUse"><path class="${cls}" d="M ${lyNum(size)} 0 H 0 V ${lyNum(size)}" fill="none" stroke-width="${u(sw)}"/></pattern>`;
  const hatch = (id, cls, gap, bar, turn) => html`<pattern id="${id}" width="${u(gap)}" height="${u(gap)}" patternUnits="userSpaceOnUse" patternTransform="rotate(${turn})"><rect class="${cls}" width="${u(bar)}" height="${u(gap)}"/></pattern>`;
  return html`<svg class="ly-svg${o.live ? '' : ' ly-still'}${top && !o.dim && lyLevels(L).length > 1 ? ' ly-through' : ''}" data-view="${view}" ${o.live ? raw('data-live="1"') : ''} viewBox="${lyNum(-m)} ${lyNum(-m)} ${lyNum(W + 2 * m)} ${lyNum(V + 2 * m)}"
      width="${Math.round((W + 2 * m) * S)}" height="${Math.round((V + 2 * m) * S)}" role="${o.live ? 'group' : 'img'}" aria-label="${o.label}">
    <defs>${o.grid ? html`${pat('ly-g-' + o.id, step, 'ly-gl', 2, top ? 0 : V % step)}${pat('ly-G-' + o.id, major, 'ly-gL', 3.4, top ? 0 : V % major)}` : ''}
      ${hatch('ly-hh-' + o.id, 'ly-hh', 9, 2.5, 45)}${hatch('ly-hs-' + o.id, 'ly-hs', 15, 2.5, -45)}${hatch('ly-z-' + o.id, 'ly-zz', 11, 1.5, 45)}</defs>
    <rect class="ly-space" width="${lyNum(W)}" height="${lyNum(V)}" stroke-width="${u(2.5)}"/>
    ${o.grid ? html`<rect class="ly-gridfill" width="${lyNum(W)}" height="${lyNum(V)}" fill="url(#ly-g-${o.id})"/><rect class="ly-gridfill" width="${lyNum(W)}" height="${lyNum(V)}" fill="url(#ly-G-${o.id})"/>` : ''}
    <rect class="ly-edge-line" width="${lyNum(W)}" height="${lyNum(V)}" stroke-width="${u(2.5)}"/>
    ${top ? '' : html`<line class="ly-floor" x1="${lyNum(-m)}" x2="${lyNum(W + m)}" y1="${lyNum(V)}" y2="${lyNum(V)}" stroke-width="${u(5)}"/>`}
    ${mark ? html`<line class="ly-wallmark" x1="${lyNum(mark[0])}" y1="${lyNum(mark[1])}" x2="${lyNum(mark[2])}" y2="${lyNum(mark[3])}" stroke-width="${u(7)}"/>` : ''}
    ${order.map(it => html`<g class="${lyItCls(it, o)}" data-id="${it.id}" transform="${lyItTf(L, it, view, o)}" ${o.live && !(o.dim && o.dim.has(it.id))
      ? raw(`tabindex="${it.id === stop ? 0 : -1}" role="button" aria-pressed="${o.sel === it.id}" aria-describedby="ly-keys" aria-label="${esc(lyItLabel(L, it, o.F))}"`) : raw('aria-hidden="true"')}>${lyItemInner(L, it, view, o)}</g>`)}
    ${order.map(it => html`<g class="${lyLabCls(it, o)}" data-id="${it.id}" data-lv="${lyLvKey(it, o)}" transform="${lyItTf(L, it, view, o)}" aria-hidden="true">${lyItemLab(L, it, view, o)}</g>`)}
    ${sel ? lySelMark(L, sel, view, o) : ''}
  </svg>`;
}

// ---------- the list of layouts (#/layouts) ----------
function lyCard(x, rem) {
  const view = lyIsUnit(x) ? 'front' : 'top', m = lyMargin(x, view), S = Math.min(15 * rem / (x.width_in + 2 * m), 11 * rem / ((view === 'top' ? x.depth_in : x.height_in) + 2 * m));      // a shelf unit is shown from the front: from above its levels hide each other
  const F = lyFindings(x), hard = F.filter(f => f.hard).length, soft = F.length - hard, n = x.items.length;
  const says = !n ? 'Nothing on it yet.' : hard ? `${hard} ${hard === 1 ? 'problem' : 'problems'}.` : soft ? `${soft} ${soft === 1 ? 'warning' : 'warnings'}.` : 'Everything fits.';
  return html`<li class="ly-card" data-id="${x.id}"><a class="ly-card-link" href="#/layouts/${x.id}">
      <span class="ly-card-pic">${lySvg(x, view, { S, rem, id: 'm' + x.id, live: false, mini: true, state: lyState(F), grid: false, photos: true, label: `${view === 'top' ? 'Top' : 'Front'} view of ${x.name}` })}</span>
      <strong class="ly-card-name">${x.name}</strong></a>
    <p>${x.place ? html`${x.place}. ` : ''}${lenF(x.width_in, false)} by ${lenF(x.depth_in, false)} by ${lenF(x.height_in)}. ${n} ${n === 1 ? 'thing' : 'things'} on it.
      <span class="ly-tag ${hard ? 'ly-tag-hard' : soft ? 'ly-tag-soft' : 'ly-tag-ok'}"><span aria-hidden="true">${hard ? '✗' : soft ? '!' : n ? '✓' : ''} </span>${says}</span></p>
    ${canChange() ? html`<p class="row noprint"><button class="btn small ghost danger" type="button" data-act="lydel" data-id="${x.id}" data-name="${x.name}" aria-label="Remove the layout ${x.name}">Remove</button></p>` : ''}</li>`;
}
async function viewLayouts(parts, qs) {
  if (parts[1]) return viewLayout(parts[1], qs);
  LY = null;
  const d = await api('GET', '/api/layouts'); LYL = d;
  const rem = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16, homes = [...new Set(d.layouts.map(x => x.home))], want = +qs.get('place');
  const cards = list => html`<ul class="ly-cards">${list.map(x => lyCard(x, rem))}</ul>`;
  return { title: 'Layouts', html: html`<h1>Room and shelf layouts</h1>
    <p class="lede">Draw a room, a porch or one shelf unit to scale. Put your plants, grow lights and shelves on it. Move them about here before you move the real ones.</p>
    <p>As you go, it marks these:</p><ul class="ly-lede-list"><li>Things that overlap or stick out.</li><li>A plant that is crowded or too close to a light.</li><li>A plant too dim or too bright under the lights you draw.</li></ul>
    ${canChange() ? html`<p class="row noprint"><button class="btn" type="button" data-act="lynew">Start a layout</button></p>` : ''}
    ${!d.layouts.length ? html`<p class="notice">No layouts yet. ${canChange() ? html`<strong>Start a layout</strong> draws one of your rooms or shelves from its measurements, or a space of any size you type.` : ''}</p>`
      : homes.length > 1 ? homes.map(h => html`<section class="blk"><h2>${h}</h2>${cards(d.layouts.filter(x => x.home === h))}</section>`) : cards(d.layouts)}
    <p class="hint">A plant moved on a layout keeps its place on its page. Press <strong>Move it in the record</strong> there to change that too. A plant's height typed on a layout is saved on its page.</p>`,
    after: () => { if (want) lyWant(want); } };
}
function lyWant(pid) {                                  // came from a room's or shelf's own button: open its layout, or start one
  const p = LYL.places.find(x => x.pid === pid);
  history.replaceState(null, '', '#/layouts');
  if (p && p.layout_id) { go('#/layouts/' + p.layout_id); return; }
  if (p && canChange()) lyStartDialog(pid);
}
function lyStartFill(first) {
  const f = dlg.querySelector('form[data-lystart]'); if (!f) return;
  const p = LYL.places.find(x => String(x.pid) === f.elements.place.value), st = p ? p.start : { width_in: 48, depth_in: 24, height_in: 72, items: [], notes: [] };
  if (first || !f.elements.name.value || f.elements.name.value === f.dataset.auto) f.elements.name.value = f.dataset.auto = p ? p.name : '';
  for (const k of ['width_in', 'depth_in', 'height_in']) f.elements[k].value = lenF(st[k], false);
  const box = document.getElementById('ly-st-items'), n = st.items.length;
  box.hidden = !n; f.elements.items.checked = true;
  box.querySelector('span').textContent = !n ? '' : p.kind === 'shelf' ? `Draw its ${n} levels from its measurements` : `Draw its ${n} ${n === 1 ? 'spot' : 'spots'} as ${n === 1 ? 'a block' : 'blocks'}`;
  document.getElementById('ly-st-notes').innerHTML = rend(html`${p && p.words ? html`<p>Its measurements: ${p.words}.</p>` : ''}${st.notes.map(x => html`<p>${x}</p>`)}`);
}
async function lyStartDialog(pid) {
  if (!(await needName())) return;
  const P = LYL.places, homes = [...new Set(P.map(p => p.home))];
  const opt = p => html`<option value="${p.pid}" ${p.pid === pid ? raw('selected') : ''}>${p.kind === 'shelf' ? '   ' + p.name : `${p.name} (the whole ${p.kind})`}${p.layout_id ? ', has a layout' : ''}</option>`;
  const num = (k, label) => html`<label class="f">${label} (${lenU()})<input type="number" inputmode="decimal" min="0" step="any" name="${k}"></label>`;
  const shown = modal(html`<form method="dialog" class="ly-form" data-lystart><h2>Start a layout</h2>
    <label class="f">What is it a layout of?<select name="place" data-act="lyplace"><option value="">A space of my own</option>
      ${homes.map(h => html`<optgroup label="${h}">${P.filter(p => p.home === h).map(opt)}</optgroup>`)}</select></label>
    <label class="f">Name<input type="text" name="name" maxlength="80" autocomplete="off"></label>
    <div class="field-grid three">${num('width_in', 'Width, left to right')}${num('depth_in', 'Depth, back to front')}${num('height_in', 'Height')}</div>
    <label class="chk" id="ly-st-items" hidden><input type="checkbox" name="items" checked> <span></span></label>
    <div class="hint" id="ly-st-notes"></div>
    <div class="row"><button class="btn" value="ok">Start the layout</button><button class="btn ghost" value="cancel" formnovalidate>Cancel</button></div></form>`);
  lyStartFill(true);
  if ((await shown) !== 'ok') return;
  const f = dlg.querySelector('form[data-lystart]'), p = P.find(x => String(x.pid) === f.elements.place.value);
  const body = { name: f.elements.name.value, place: p ? p.pid : null, items: p && f.elements.items.checked ? p.start.items : [] };
  for (const k of ['width_in', 'depth_in', 'height_in']) body[k] = lenIn(f.elements[k].value);
  await guard(async () => { const r = await api('POST', '/api/layouts', body); toast('Layout started: ' + r.name); go('#/layouts/' + r.id); });
}

// ---------- one layout (#/layouts/ID) ----------
const lyNarrow = () => { const m = document.querySelector('.ly-main'); return !!m && m.clientWidth < 620; };
const lyViewNow = () => LY.view === 'both' && lyNarrow() ? LY.fview : LY.view;
async function viewLayout(id, qs) {
  const d = await api('GET', `/api/layouts/${enc(id)}?_=${Date.now()}`), p = lyPref(), mine = (p.each || {})[d.id] || {}, same = LY && LY.d.id === d.id;
  LY = { d, sel: same ? LY.sel : null, fview: same ? LY.fview : 'top', view: ['top', 'front', 'both'].includes(mine.view) ? mine.view : d.area_id && !d.spot_id ? 'top' : 'both', zoom: clamp(+mine.zoom || 1, 0.5, 4), level: same ? LY.level : 'auto', wall: same ? LY.wall : Object.keys(LY_WALLS).includes(mine.wall) ? mine.wall : 'back',
    grid: p.grid !== false, photos: p.photos !== false, more: !!p.more, undo: same ? LY.undo : [], redo: same ? LY.redo : [], ids: same ? LY.ids : new Map(), lastLv: same ? LY.lastLv : 0, Sv: { top: 1, front: 1 }, mv: {}, mode: 'one', order: ['top', 'front'], rem: 16, F: [], q: Promise.resolve() };
  const sel = +qs.get('sel'); if (sel && d.items.some(x => x.id === sel)) LY.sel = sel;
  if (LY.sel && !lyItem(LY.sel)) LY.sel = null;
  if (sel && LY.sel === sel) lyWallFollow(lyItem(sel));
  return { title: d.name + ' layout', html: html`<p class="crumb ly-crumb"><span><a class="noprint" href="#/layouts">All layouts</a> <span class="muted" id="ly-sub"></span></span></p>
    <h1 id="ly-title">${d.name}</h1>
    <div class="verdict-box ly-status" id="ly-status" role="status"></div>
    <div class="ly-tools noprint" id="ly-tools" role="group" aria-label="Layout tools"></div>
    <div class="ly-main">
      <div class="ly-draw" id="ly-draw"></div>
      <div class="ly-side">
        <section class="blk" id="ly-sel"><h2>Chosen thing</h2><div id="ly-panel"></div></section>
        <section class="blk" id="ly-find"><h2>To look at</h2><div id="ly-find-body"></div>
          <details class="ly-fold ly-key" id="ly-marks"><summary class="btn small ghost"><span>What the marks mean</span></summary><ul>
            <li><strong><span aria-hidden="true">✗ </span>A cross and close bars:</strong> it overlaps something, or sticks out of the space.</li>
            <li><strong><span aria-hidden="true">! </span>An exclamation mark and wide bars:</strong> something to look at. It may be one of these:<ul><li>Tight, or close to a light.</li><li>In an area to keep clear.</li><li>Standing on nothing.</li><li>Getting more or less light than it needs.</li></ul></li>
            <li><strong><span aria-hidden="true">▼▼ ▼ ✓ ▲ ▲▲ – </span>A sign for its light:</strong> on each plant, once a grow light is drawn. Too dim, a bit dim, good, a bit bright, too bright, against what its page says it needs. Red is too much or too little, amber is a bit, green is good. A grey dash: no light drawn here reaches it (it may have a window).</li>
            <li><strong>A heavy edge in the top view:</strong> the wall the front view is looking at.</li>
            <li><strong>A dashed outline:</strong> a grow light, with a sun in it, or an area to keep clear, with thin bars.</li>
            <li><strong>A ring round it:</strong> the chosen thing. The square on its corner changes its size.</li>
            <li><strong>Faint:</strong> on another level than the one the top view is showing.</li></ul></details>
          <details class="ly-fold ly-key" id="ly-keyhelp"><summary class="btn small ghost"><span>Keys for the drawing</span></summary><ul>
            <li><strong>Tab</strong> goes to the drawing: to the chosen thing, or the first thing.</li>
            <li><strong>Page Down</strong> and <strong>Page Up</strong> go to the next and the previous thing, and choose it.</li>
            <li><strong>The arrow keys</strong> move the thing one square; with <strong>Shift</strong>, five. In the front view, Up and Down stop at each shelf, and Left and Right are your left and right as you face that wall. What stands on a thing moves with it.</li>
            <li><strong>Enter</strong> or <strong>Space</strong> chooses the thing; <strong>Escape</strong> chooses nothing.</li>
            <li><strong>Delete</strong> takes the thing off the layout. <strong>Ctrl+Z</strong> takes back the last change, and <strong>Ctrl+Y</strong> does it again.</li></ul></details></section>
      </div>
    </div>
    <section class="blk" id="ly-things"><h2>On this layout</h2><div id="ly-things-body"></div></section>
    <section class="blk" id="ly-tray" hidden><h2>Here, but not drawn yet</h2><div id="ly-tray-body"></div></section>
    <section class="blk" id="ly-rec" hidden><h2>Somewhere else in your record</h2><div id="ly-rec-body"></div></section>
    <p class="sr" id="ly-say" role="status" aria-live="polite"></p>
    <p class="sr" id="ly-keys">Arrow keys move it one square, or five with Shift. Page Down and Page Up go to the next and the previous thing. Delete takes it off the layout.</p>`,
    after: () => { lyDrawAll(); lyWatch(); } };
}
// The page's width can change without the window's (the Navigation menu opens or moves, the text size changes): the drawing is made
// again for the width it now has.
function lyWatch() {
  const main = document.querySelector('.ly-main'); if (!main || !window.ResizeObserver) return;
  new ResizeObserver(() => {
    if (!lyOn() || !main.isConnected || Math.abs(main.clientWidth - LY.mw) < 3) return;
    clearTimeout(LY.rz); LY.rz = setTimeout(() => { if (lyOn() && !LY.drag) { lyToolsDraw(); lyDrawViews(); } }, 120);
  }).observe(main);
}
// How many pixels an inch gets in each view, and how the views and the chosen thing's boxes are set out, so that the drawing uses
// the width it has and about a screen and a half of height. With both views:
//   stack  the top view above the front view at one scale, so a thing is straight below itself (a room, a wide shelf)
//   pair   side by side, each as large as its share of the width allows: a tall narrow shelf's front view is held back by its
//          height, and the top view takes the width that leaves, so one level is seen large beside the whole unit
//   tall   the same, with the chosen thing's boxes under the top view instead of under everything (a page too narrow for a third column)
function lyMeasure() {
  const box = document.getElementById('ly-draw'), main = box.parentElement, L = LY.d, root = getComputedStyle(document.documentElement), rem = parseFloat(root.fontSize) || 16;
  const two = main.clientWidth >= 62 * rem;                         // the chosen thing beside the drawing only where there is room for both
  main.classList.remove('ly-tall'); main.classList.toggle('ly-two', two);
  LY.mw = main.clientWidth;
  const aw = Math.max(160, box.clientWidth - 4), view = lyViewNow(), gap = 2 * rem, W = L.width_in, D = L.depth_in, H = L.height_in;
  const face = lyFaceNow(), Wa = lyAcrossW(L, face);              // the front view is as wide as the wall it looks at
  const mt = lyMargin(L, 'top'), mf = lyMargin(L, 'front', face), ms = Math.max(mt, mf), Wt = W + 2 * mt, Dt = D + 2 * mt, Wf = Wa + 2 * mf, Hf = H + 2 * mf;
  const seen = Math.max(260, window.innerHeight - (parseFloat(root.getPropertyValue('--top-h')) || 0)), most = 1.5 * Math.max(260, seen - 5 * rem);
  let st, sf, mode = 'one', mv = { top: mt, front: mf };
  if (view === 'both') {
    const stack = Math.min(aw / (Math.max(W, Wa) + 2 * ms), most / (D + H + 4 * ms)), half = (aw - gap) / 2, beside = Math.min(most, seen - 4 * rem);      // beside: the top view stays in sight as the page scrolls, so it is no taller than the window
    sf = Math.min(most / Hf, half / Wf); st = Math.min(beside / Dt, half / Wt);
    if (sf * Wf < half - 1) st = Math.min(beside / Dt, (aw - gap - sf * Wf) / Wt);
    else if (st * Wt < half - 1) sf = Math.min(most / Hf, (aw - gap - st * Wt) / Wf);
    const rest = aw - gap - sf * Wf, low = Math.min(0.6 * seen / Dt, rest / Wt);       // tall: the top view no more than 0.6 of the window high, so the boxes under it start in sight
    if (Math.min(sf, st) < stack) { mode = 'stack'; sf = st = stack; mv = { top: ms, front: ms }; }      // one scale and one margin, so a thing is straight below itself
    else if (!two && rest >= 19 * rem && low >= 0.75 * st) { mode = 'tall'; st = low; }
    else mode = 'pair';
  } else sf = st = view === 'top' ? Math.min(aw / Wt, most / Dt) : Math.min(aw / Wf, most / Hf);
  LY.Sv = { top: Math.max(0.15, st) * LY.zoom, front: Math.max(0.15, sf) * LY.zoom }; LY.mv = mv; LY.rem = rem; LY.mode = mode;
  LY.order = mode === 'tall' || (mode === 'pair' && sf * Wf <= st * Wt) ? ['front', 'top'] : ['top', 'front'];       // side by side, the narrower view is on the left; one above the other, the top view is above
}
function lyOpts(view) {
  const walled = lyWalled(LY.d);
  const o = { S: LY.Sv[view], m: LY.mv[view], rem: LY.rem, id: view, live: true, can: lyCan(), sel: LY.sel, state: lyState(LY.F), F: LY.F, grid: LY.grid, photos: LY.photos,
    dim: view === 'top' ? lyDim(LY.d, lyLevelNow()) : null,
    label: view === 'top' ? `Top view of ${LY.d.name}, looking down. The back is at the top of the drawing and the front at the bottom.`
      : `Front view of ${LY.d.name}${walled && LY.wall !== 'all' ? `, looking at ${LY_WALLS[LY.wall].toLowerCase()}` : ''}. The floor is at the bottom of the drawing.` };
  if (view === 'top') o.wallmark = walled && LY_WALL_ENDS[LY.wall] && lyViewNow() === 'both' ? LY.wall : null;
  else { o.face = lyFaceNow(); o.only = walled ? lyWallSet(LY.d, LY.wall) : null; o.noname = lyNameClash(LY.d, o); }
  o.along = lyLabSpots(LY.d, view, o);
  return o;
}
function lyFigure(view) {
  const L = LY.d, top = view === 'top', lv = top ? lyItem(lyLevelNow()) : null, step = lyDrawnStep(L, LY.Sv[view]), o = lyOpts(view);
  const walled = lyWalled(L), one = walled && LY.wall !== 'all', face = lyFaceNow(), ends = top ? ['Left', 'Right'] : LY_WALL_ENDS[face];
  return html`<figure class="ly-fig" data-view="${view}">
    <figcaption><strong>${top ? 'Top view' : one ? `Front view: ${LY_WALLS[LY.wall].toLowerCase()}` : 'Front view'}</strong> <span class="muted">${lenF(top ? L.width_in : lyAcrossW(L, face))} wide, ${top ? `${lenF(L.depth_in)} deep` : `${lenF(L.height_in)} high`}.${
      LY.grid && Math.abs(step - L.grid_in) > 0.006 ? ` The squares drawn here are ${lenF(step)}.` : ''}${top && lv ? ` Showing ${lv.name}; the other levels are faint.` : ''}${
      top && o.wallmark ? ' The heavy edge is the wall the front view looks at.' : ''}${
      !top && one ? (o.only.size ? ` ${o.only.size} of the ${L.items.length} things are here.` : ' Nothing is here.') : ''}</span></figcaption>
    ${!top && walled ? html`<label class="f ly-wall noprint">Front view looks at<select id="ly-wall" data-act="lywall">${Object.keys(LY_WALLS).map(w => html`<option value="${w}" ${LY.wall === w ? raw('selected') : ''}>${LY_WALL_OPT[w]}</option>`)}</select></label>` : ''}
    <div class="ly-frame"><p class="ly-edge" aria-hidden="true">${top ? 'Back' : 'Top'}</p>
      <div class="ly-scroll" id="ly-scroll-${view}">${lySvg(L, view, o)}</div>
      <p class="ly-edge ly-edge-row" aria-hidden="true"><span>${ends[0]}</span><span>${top ? 'Front' : 'Floor'}</span><span>${ends[1]}</span></p></div></figure>`;
}
function lyFocusIt(id, view) {                           // the keyboard goes to a thing on the drawing: in the view asked for, else in the other one
  const gs = [...document.querySelectorAll(`svg.ly-svg[data-live] g.ly-it[data-id="${id}"]`)].filter(g => g.hasAttribute('tabindex'));
  const g = gs.find(x => x.closest('svg').dataset.view === view) || gs[0];
  if (g) g.focus({ preventScroll: true });
  return !!g;
}
function lyShow(id) {                                    // brings a thing on the drawing into sight, if the page or the drawing's own box is scrolled away from it
  const g = document.querySelector(`svg.ly-svg[data-view="${lyViewNow() === 'both' ? LY.fview : lyViewNow()}"] g.ly-it[data-id="${id}"]`); if (!g) return;
  const r = g.getBoundingClientRect(), bar = document.querySelector('header.top'), top = bar ? bar.getBoundingClientRect().bottom : 0;
  if (r.top < top + 8 || r.bottom > window.innerHeight - 8 || r.left < 0 || r.right > window.innerWidth) g.scrollIntoView({ block: 'center', inline: 'nearest' });
}
function lyDrawViews() {                                // the drawings, made again whole; the thing with the keyboard on it keeps it
  const box = document.getElementById('ly-draw'); if (!box || !LY) return;
  const a = document.activeElement, fg = a && a.closest ? a.closest('g.ly-it') : null, had = fg ? [+fg.dataset.id, fg.closest('svg').dataset.view] : null, onWall = !!a && a.id === 'ly-wall';
  const at = {}; box.querySelectorAll('.ly-scroll').forEach(s => { at[s.id] = [s.scrollLeft, s.scrollTop]; });
  lyMeasure();
  const view = lyViewNow(), views = view === 'both' ? LY.order : [view];
  box.className = 'ly-draw' + (LY.mode === 'stack' ? ' ly-stack' : LY.mode === 'pair' ? ' ly-pair' : '');
  box.parentElement.classList.toggle('ly-tall', LY.mode === 'tall');
  box.innerHTML = rend(views.map(lyFigure));
  box.querySelectorAll('.ly-scroll').forEach(s => {
    if (s.scrollWidth > s.clientWidth + 1) s.classList.add('is-wide');         // made larger than its place: its box keeps to the window's height, so both of its scroll bars are in reach
    if (at[s.id]) { s.scrollLeft = at[s.id][0]; s.scrollTop = at[s.id][1]; }
    if (s.scrollWidth > s.clientWidth + 1 || s.scrollHeight > s.clientHeight + 1) { s.tabIndex = 0; s.setAttribute('role', 'region'); s.setAttribute('aria-label', 'The drawing is larger than its box. Scroll it with the arrow keys.'); }
  });
  if (had) lyFocusIt(had[0], had[1]);
  if (onWall) { const w = document.getElementById('ly-wall'); if (w) w.focus({ preventScroll: true }); }      // the list of walls was drawn again with its view
}
function lyHead() {
  const L = LY.d, F = LY.F, hard = F.filter(f => f.hard).length, soft = F.length - hard, n = L.items.length, box = document.getElementById('ly-status');
  document.getElementById('ly-title').textContent = L.name;
  document.getElementById('ly-sub').textContent = `${L.place ? `A layout of ${L.place}` : 'A layout of a space of your own'}${L.home ? `, ${L.home}` : ''}`;
  box.className = 'verdict-box ly-status ' + (hard ? 'v-hold' : soft ? 'v-due' : 'v-wait');
  box.innerHTML = rend(html`<p><strong><span aria-hidden="true">${!n ? '' : hard ? '✗ ' : soft ? '! ' : '✓ '}</span>${!n ? 'Nothing is on this layout yet.' : hard ? `${hard} ${hard === 1 ? 'problem' : 'problems'}: something overlaps or sticks out.`
    : soft ? 'Nothing overlaps or sticks out.' : 'Everything fits: nothing overlaps, sticks out or is crowded.'}</strong>
    ${!n ? (lyCan() ? html`Press <strong>Add something</strong> to put the first plant, light or shelf on it.` : '') : html`${soft ? `${soft} ${soft === 1 ? 'warning' : 'warnings'} to look at${hard ? ' as well' : ''}. ` : ''}${n} ${n === 1 ? 'thing' : 'things'} on it.`}</p>
    ${LY.stale ? html`<p class="ly-stale"><strong><span aria-hidden="true">! </span>The last change was not saved,</strong> and the plant server could not be reached to read the layout again. Nothing more can be changed here until it has been.
      <button class="btn small" type="button" data-act="lyreload">Read it again</button></p>` : ''}`);
}
function lyToolsDraw() {
  const box = document.getElementById('ly-tools'); if (!box) return;
  const L = LY.d, can = lyCan(), view = lyViewNow(), cm = lenU() === 'cm', levels = lyLevels(L), last = LY.undo[LY.undo.length - 1], again = LY.redo[LY.redo.length - 1];
  const grids = (cm ? [1, 2, 5, 10, 20, 30].map(x => [r2(x / 2.54), `${x} cm`]) : L.grids.map(x => [x, x === 12 ? '1 ft' : `${x} in`]));
  if (!grids.some(([v]) => Math.abs(v - L.grid_in) < 0.006)) grids.push([L.grid_in, lenF(L.grid_in)]);
  const keep = document.activeElement && box.contains(document.activeElement) ? (document.activeElement.id || '') : '';
  const sq = (grids.find(([v]) => Math.abs(v - L.grid_in) < 0.006) || [0, lenF(L.grid_in)])[1];
  box.innerHTML = rend(html`<fieldset class="ly-viewset"><legend class="sr">Which view to show</legend><div class="opts">${[['top', 'Top view'], ['front', 'Front view']].concat(lyNarrow() ? [] : [['both', 'Both']]).map(([v, w]) =>
      html`<label><input type="radio" name="lyview" id="ly-v-${v}" value="${v}" data-act="lyview" ${view === v ? raw('checked') : ''}><span>${w}</span></label>`)}</div></fieldset>
    ${can ? html`<button class="btn" type="button" id="ly-add" data-act="lyadd">Add something</button>
      <button class="btn ghost" type="button" id="ly-undo" data-act="lyundo" ${last ? raw(`aria-label="${esc(`Undo: ${last.short}. ${last.label}`)}"`) : raw('disabled')}>${last ? `Undo: ${last.short}` : 'Undo'}</button>
      <button class="btn ghost" type="button" id="ly-redo" data-act="lyredo" ${again ? raw(`aria-label="${esc(`Redo: ${again.short}. ${again.label}`)}"`) : raw('disabled')}>${again ? `Redo: ${again.short}` : 'Redo'}</button>` : ''}
    <span class="ly-zoom" role="group" aria-label="Size of the drawing"><button class="btn ghost" type="button" id="ly-zout" data-act="lyzoom" data-d="-1" aria-label="Smaller drawing" ${LY.zoom <= 0.5 ? raw('disabled') : ''}>Smaller</button>
      <button class="btn ghost" type="button" id="ly-zin" data-act="lyzoom" data-d="1" aria-label="Larger drawing" ${LY.zoom >= 4 ? raw('disabled') : ''}>Larger</button></span>
    <details class="ly-more" ${LY.more ? raw('open') : ''}><summary class="btn ghost" id="ly-more" data-act="lymore"><span>Grid and settings<span class="ly-more-now">: ${sq} squares, snapping ${L.snap ? 'on' : 'off'}</span></span></summary>
      <div class="ly-more-in"><label class="chk ly-chk"><input type="checkbox" id="ly-snap" data-act="lysnap" ${L.snap ? raw('checked') : ''} ${can ? '' : raw('disabled')}>Snap to the grid</label>
        <label class="chk ly-chk"><input type="checkbox" id="ly-gridshow" data-act="lygridshow" ${LY.grid ? raw('checked') : ''}>Show the grid</label>
        <label class="f ly-step">Squares of<select id="ly-step" data-act="lystep" ${can ? '' : raw('disabled')}>${grids.map(([v, w]) => html`<option value="${v}" ${Math.abs(v - L.grid_in) < 0.006 ? raw('selected') : ''}>${w}</option>`)}</select></label>
        ${levels.length > 1 ? html`<label class="f ly-step">Top view shows<select id="ly-level" data-act="lylevel"><option value="auto" ${LY.level === 'auto' ? raw('selected') : ''}>The chosen thing's level</option>
          <option value="0" ${LY.level === 0 ? raw('selected') : ''}>Every level</option>${levels.map(s => html`<option value="${s.id}" ${LY.level === s.id ? raw('selected') : ''}>${s.name} only</option>`)}</select></label>` : ''}
        ${can ? html`<button class="btn ghost" type="button" id="ly-space" data-act="lyspace">Size and name</button>` : ''}</div></details>`);
  if (keep) { const el = document.getElementById(keep); if (el && !el.disabled) el.focus({ preventScroll: true }); else { const b = document.getElementById('ly-add'); if (b) b.focus({ preventScroll: true }); } }
}
const lyFindLi = f => html`<li class="ly-f ${f.hard ? 'ly-f-hard' : 'ly-f-soft'}"><span><strong><span aria-hidden="true">${f.hard ? '✗' : '!'} </span>${LY_WORD[f.kind]}:</strong> ${f.text}</span></li>`;
// What a thing could stand on: the floor; every shelf on the layout, level by level where it has them, in the order of their
// numbers; and each other thing that is under it where it is. Choosing one it is not over moves it there (lyPutOn).
function lyStandOpts(L, a) {
  const mine = lyCarrySkip(lyCarryStart(L, a));          // not onto something it carries
  return [{ v: 'floor', w: 'The floor', q: null }].concat(L.items.filter(b => b.id !== a.id && !mine.has(b.id) && (b.kind === 'shelf' || (b.kind === 'other' && lyPlan(a, b) < -LY_EPS)))
    .flatMap(lySurf).map(q => ({ v: `${q.b.id}:${q.n}`, w: q.name, q })));
}
function lyHangOpts(L, a) {                             // what a light could hang under where it is: the top of the space, and each thing (or each level of a shelf) over it
  return [{ v: 'top', w: 'The top of the space', z: r2(L.height_in - a.h) }].concat(L.items.filter(b => b.id !== a.id && (b.kind === 'shelf' || b.kind === 'other') && lyPlan(a, b) < -LY_EPS)
    .flatMap(b => lySolids(b).map((q, n) => ({ b, q, n }))).filter(x => x.q.z - a.h >= -LY_EPS).sort((x, y) => x.q.z - y.q.z)
    .map(x => ({ v: `${x.b.id}:${x.n}`, w: x.q.lv ? `${x.q.lv.name} of ${lyNm(x.b)}` : lyNm(x.b), z: r2(x.q.z - a.h) })));
}
function lyRestHtml(L, it, ro) {                        // the boxes that depend on what is under and over the thing, drawn again as it moves
  const u = lyUnder(L, it), on = u && u !== 'floor' ? lyOnSurf(it, u) : null, uv = u === 'floor' ? 'floor' : on ? `${u.id}:${on.n}` : '';
  const o = it.kind === 'light' ? lyOver(L, it) : null, ov = o === 'top' ? 'top' : o ? `${o.id}:${lySolids(o).findIndex(q => Math.abs(q.z - it.z - it.h) < 0.05)}` : '';
  const sel = (id, k, label, opts, cur, none) => html`<label class="f">${label}<select id="${id}" data-act="lyset" data-k="${k}" ${ro}>${cur === '' ? html`<option value="" selected>${none}</option>` : ''}
    ${opts.map(x => html`<option value="${x.v}" ${x.v === cur ? raw('selected') : ''}>${x.w}</option>`)}</select></label>`;
  return html`${it.kind === 'zone' ? '' : sel('ly-f-on', 'on', 'Stands on', lyStandOpts(L, it), uv, it.kind === 'light' && ov ? 'Nothing: it hangs' : 'Nothing: it is in the air')}
    ${it.kind === 'light' ? sel('ly-f-under', 'under', 'Hangs under', lyHangOpts(L, it), ov, 'Nothing') : ''}`;
}
function lyPanel() {                                    // the chosen thing: what it is, what is wrong with it, and its place and size to type in
  const box = document.getElementById('ly-panel'); if (!box) return;
  const L = LY.d, it = lyItem(LY.sel), can = lyCan();
  if (!it) { box.innerHTML = rend(html`<p class="muted">Press a thing on the drawing, or <strong>Choose</strong> beside it in the list below, to see its place and size here.${can ? ' Then drag it, move it with the arrow keys, or type where it goes.' : ''}</p>`); return; }
  const ro = can && !it.locked ? '' : raw('disabled'), rs = can && !it.size_locked ? '' : raw('disabled'), linked = it.plant || it.light_id || it.spot_id, lit = it.kind === 'light' && !it.gone && (it.pts || []).length;
  const dims = lit ? [...new Set((it.dims || [100]).concat(it.dim_pct))].sort((a, b) => b - a) : [];
  const lockedBox = k => can && (LY_SIZE_KEYS.includes(k) ? it.size_locked : it.locked);        // a locked box says so in its label, not only by looking greyed
  const num = (k, label) => html`<label class="f">${label} (${lenU()})${lockedBox(k) ? html`<span class="ly-lockword">, locked</span>` : ''}<input type="number" inputmode="decimal" step="any" id="ly-f-${k}" data-act="lyset" data-k="${k}" value="${lenF(it[k], false)}" ${LY_SIZE_KEYS.includes(k) ? rs : ro}></label>`;
  const P = it.plant ? L.plants.find(p => p.code === it.plant) : null;
  box.innerHTML = rend(html`<div class="ly-who">${it.photo ? html`<img src="${thumbUrl(it.photo)}" alt="" loading="lazy">` : ''}
      <p><span class="ly-num">${it.sort}</span> <strong>${it.plant && !it.gone ? html`<a href="#/plant/${enc(it.plant)}">${it.name}</a>` : it.name}</strong><br>
        <span class="muted">${L.kinds[it.kind]}${it.plant ? ',' : ''}</span>${it.plant ? html` <span class="code">${it.plant}</span>` : ''}${it.gone ? html`<span class="muted">. It is no longer in the record.</span>` : ''}</p></div>
    <ul class="ly-flist" id="ly-p-find">${LY.F.filter(f => f.ids.includes(it.id)).map(lyFindLi)}</ul>
    ${!linked ? html`<label class="f">Name<input type="text" maxlength="80" id="ly-f-name" data-act="lyset" data-k="name" value="${it.name}" autocomplete="off" ${can ? '' : raw('disabled')}></label>` : ''}
    <div class="field-grid three ly-fields">${num('x', 'From the left')}${num('y', 'From the back')}${num('z', 'Off the floor')}
      ${lyRound(it) ? num('w', 'Across') : html`${num('w', 'Width')}${num('d', 'Depth')}`}${num('h', 'Height')}</div>
    ${lyPaged(it) ? html`<p class="hint ly-recline" id="ly-p-tall">${lyTallHtml(it)}</p>` : ''}
    <div class="field-grid ly-fields" id="ly-f-rest">${lyRestHtml(L, it, ro)}</div>
    ${lit ? html`<div class="field-grid ly-fields"><label class="f">Hours a day<input type="number" inputmode="decimal" min="0" max="24" step="0.5" id="ly-f-hours" data-act="lyset" data-k="hours" value="${it.hours}" ${can ? '' : raw('disabled')}></label>
      ${dims.length > 1 ? html`<label class="f">Brightness<select id="ly-f-dim_pct" data-act="lyset" data-k="dim_pct" ${can ? '' : raw('disabled')}>${dims.map(x => html`<option value="${x}" ${x === it.dim_pct ? raw('selected') : ''}>${x === 100 ? 'Full (100%)' : x + '%'}</option>`)}</select></label>` : ''}</div>` : ''}
    <div class="ly-light" id="ly-p-light">${lyLightHtml(L, it)}</div>
    ${lyPaged(it) ? html`<p class="ly-recline" id="ly-p-rec">${lyRecHtml(L, it)}</p>` : ''}
    ${it.kind === 'shelf' || it.kind === 'zone' ? '' : html`<label class="f">Shape, seen from above<select id="ly-f-shape" data-act="lyset" data-k="shape" ${rs}><option value="round" ${it.shape === 'round' ? raw('selected') : ''}>Round</option><option value="box" ${it.shape === 'box' ? raw('selected') : ''}>Square or oblong</option></select></label>`}
    <fieldset class="ly-locks"><legend>Locks</legend>
      <label class="chk ly-chk"><input type="checkbox" id="ly-f-locked" data-act="lyset" data-k="locked" ${it.locked ? raw('checked') : ''} ${can ? '' : raw('disabled')}>Lock its place</label>
      <label class="chk ly-chk"><input type="checkbox" id="ly-f-size_locked" data-act="lyset" data-k="size_locked" ${it.size_locked ? raw('checked') : ''} ${can ? '' : raw('disabled')}>Lock its size</label>
      <p class="hint">With its size locked it can still be moved, but not made larger or smaller by accident.</p></fieldset>
    ${P && P.guessed.includes('width') ? html`<p class="hint">Its width here was a guess to start with: the plant has no pot or tray from Pots and trays. Type its real width above.</p>` : ''}
    ${it.spot_id && it.layout_id ? html`<p><a class="btn small ghost" href="#/layouts/${it.layout_id}">Open this shelf's own layout</a></p>` : ''}
    ${can ? html`<p class="row ly-acts">${it.locked || it.size_locked || lyRound(it) ? '' : html`<button class="btn small ghost" type="button" id="ly-turn" data-act="lyturn">Turn a quarter</button>`}
      ${it.plant || it.spot_id ? '' : html`<button class="btn small ghost" type="button" id="ly-copy" data-act="lycopy">Make a copy</button>`}
      <button class="btn small ghost danger" type="button" id="ly-rm" data-act="lyrm">Take it off the layout</button></p>` : ''}`);
}
function lyPanelPatch() {                               // the chosen thing moved: its boxes follow, except the one being typed in
  const it = lyItem(LY.sel), a = document.activeElement; if (!it) return;
  for (const k of ['x', 'y', 'z', 'w', 'd', 'h']) { const el = document.getElementById('ly-f-' + k); if (el && el !== a) el.value = lenF(it[k], false); }
  const rest = document.getElementById('ly-f-rest'), ro = lyCan() && !it.locked ? '' : raw('disabled');
  if (rest && !rest.contains(a)) rest.innerHTML = rend(lyRestHtml(LY.d, it, ro));
  const fl = document.getElementById('ly-p-find'); if (fl) fl.innerHTML = rend(LY.F.filter(f => f.ids.includes(it.id)).map(lyFindLi));
  const lw = document.getElementById('ly-p-light'); if (lw) lw.innerHTML = rend(lyLightHtml(LY.d, it));
  const rc = document.getElementById('ly-p-rec'); if (rc && !rc.contains(a)) rc.innerHTML = rend(lyRecHtml(LY.d, it));
  const tl = document.getElementById('ly-p-tall'); if (tl && !tl.contains(a)) tl.innerHTML = rend(lyTallHtml(it));
  const hb = document.getElementById('ly-f-hours'); if (hb && hb !== a) hb.value = it.hours;
  const db = document.getElementById('ly-f-dim_pct'); if (db && db !== a) db.value = String(it.dim_pct);
}
function lyLists() {                                    // what to look at, everything on the layout, and the plants that are here but not drawn
  const L = LY.d, F = LY.F, can = lyCan(), st = lyState(F), fb = document.getElementById('ly-find-body'); if (!fb) return;
  fb.innerHTML = rend(F.length ? html`<ul class="ly-flist">${F.map(f => html`<li class="ly-f ${f.hard ? 'ly-f-hard' : 'ly-f-soft'}"><span><strong><span aria-hidden="true">${f.hard ? '✗' : '!'} </span>${LY_WORD[f.kind]}:</strong> ${f.text}</span>
      <button class="btn small ghost" type="button" data-act="lypick" data-id="${f.ids[0]}" aria-label="Show it: ${(lyItem(f.ids[0]) || {}).name || 'on the drawing'}">Show it</button></li>`)}</ul>`
    : html`<p class="muted">${L.items.length ? 'Nothing to look at: everything fits.' : 'Nothing yet.'}</p>`);
  const lvOf = it => { const x = it.kind === 'plant' && F.light.any ? F.light.get(it.id) : null; return !x ? '' : x.reached && LY_LV_SIGN[x.verdict] ? html` ${lvTag(x.verdict, (L.verdicts || {})[x.verdict] || '')}` : html` <span class="tag ly-lv-none"><span aria-hidden="true">– </span>No light reaches it</span>`; };
  const tags = it => F.filter(f => lyMarked(f).includes(it.id) && !lyIsLv(f.kind)).map(f => f.kind).filter((k, i, a) => a.indexOf(k) === i).map(k => html` <span class="ly-tag ${['outside', 'overlap'].includes(k) ? 'ly-tag-hard' : 'ly-tag-soft'}"><span aria-hidden="true">${['outside', 'overlap'].includes(k) ? '✗' : '!'} </span>${LY_WORD[k]}</span>`);
  document.getElementById('ly-things-body').innerHTML = rend(L.items.length ? html`<ul class="ly-list">${L.items.map(it => html`<li class="ly-row${LY.sel === it.id ? ' is-sel' : ''}${st.get(it.id) ? ' is-' + st.get(it.id) : ''}" data-id="${it.id}">
      ${it.photo ? html`<img src="${thumbUrl(it.photo)}" alt="" loading="lazy">` : html`<span class="ly-nophoto ly-np-${it.kind}" aria-hidden="true"></span>`}
      <div class="ly-row-main"><div class="ly-row-txt"><span class="ly-num" aria-hidden="true">${it.sort}</span> <strong>${it.plant && !it.gone ? html`<a href="#/plant/${enc(it.plant)}">${it.name}</a>` : it.name}</strong> <span class="muted">${L.kinds[it.kind]}${it.plant ? ',' : ''}</span>${it.plant ? html` <span class="code">${it.plant}</span>` : ''}${tags(it)}${lvOf(it)}
        <br><span>${lySizeWords(it)}. ${lyWhere(L, it)[0].toUpperCase() + lyWhere(L, it).slice(1)}.${it.locked ? ' Locked in place.' : ''}${it.size_locked ? ' Its size is locked.' : ''}${it.gone ? ' No longer in the record.' : ''}${lyLightLine(it)}</span></div>
      <button class="btn small ghost" type="button" data-act="lypick" data-id="${it.id}" aria-label="${LY.sel === it.id ? 'Chosen' : 'Choose'}: ${it.sort}, ${it.name}" ${LY.sel === it.id ? raw('aria-pressed="true"') : ''}>${LY.sel === it.id ? 'Chosen' : 'Choose'}</button></div></li>`)}</ul>`
    : html`<p class="muted">Nothing is on it yet.</p>`);
  const tray = L.plants.filter(p => p.here && !p.on), tb = document.getElementById('ly-tray');
  tb.hidden = !tray.length || !can;
  document.getElementById('ly-tray-body').innerHTML = rend(html`<p>${tray.length === 1 ? 'This plant is' : `These ${tray.length} plants are`} at ${L.place || 'this place'} in your record but not on the drawing.</p>
    ${tray.length > 1 ? html`<p><button class="btn small" type="button" data-act="lytray" data-all="1">Put all ${tray.length} on the layout</button></p>` : ''}
    ${tray.length > 12 ? raw(`<details class="ly-fold"><summary class="btn small ghost"><span>Show these ${tray.length} plants</span></summary>`) : ''}<ul class="ly-list">${tray.map(p => html`<li class="ly-row">${p.photo ? html`<img src="${thumbUrl(p.photo)}" alt="" loading="lazy">` : html`<span class="ly-nophoto" aria-hidden="true"></span>`}
      <div class="ly-row-main"><div class="ly-row-txt"><strong><a href="#/plant/${enc(p.code)}">${p.name}</a></strong> <span class="code">${p.code}</span><br><span>${lySizeWords(p)}${p.guessed.length ? ' (a guess)' : ''}</span></div>
      <button class="btn small ghost" type="button" data-act="lytray" data-code="${p.code}" aria-label="Put it on: ${p.name}">Put it on</button></div></li>`)}</ul>${tray.length > 12 ? raw('</details>') : ''}`);
  lyRecDraw();
}
function lyLightWords(L, F, it) {                       // a plant's light in a sentence, or nothing when no drawn light has figures
  const x = it.kind === 'plant' && F && F.light && F.light.any ? F.light.get(it.id) : null; if (!x) return '';
  const w = (L.verdicts || {})[x.verdict];
  return x.reached ? ` Light: about ${lyMol(x.dli)}${w && x.verdict !== 'unknown' ? ', ' + w.toLowerCase() : ''}.` : ' Light: none drawn here reaches it.';
}
const lyLightLine = it => lyLightWords(LY.d, LY.F, it);  // for its line in the list
function lyRecDraw() {                                  // the plants drawn here that the record has somewhere else, and the way to move them there
  const L = LY.d, box = document.getElementById('ly-rec'), list = lyCan() ? lyRecList(L) : []; if (!box) return;
  const keep = box.contains(document.activeElement) ? document.activeElement.dataset.id || 'all' : '';
  box.hidden = !list.length;
  document.getElementById('ly-rec-body').innerHTML = rend(!list.length ? '' : html`<p>${list.length === 1 ? 'This plant is' : `These ${list.length} plants are`} drawn here, but your record has ${list.length === 1 ? 'it' : 'them'} somewhere else. Nothing in the record changes until you say so here.</p>
    ${list.length > 1 ? html`<p><button class="btn small" type="button" id="ly-recall" data-act="lyrec" data-all="1">Move ${list.length === 2 ? 'both' : `all ${list.length}`} in the record</button></p>` : ''}
    ${list.length > 12 ? raw(`<details class="ly-fold"><summary class="btn small ghost"><span>Show these ${list.length} plants</span></summary>`) : ''}<ul class="ly-list">${list.map(({ it, to }) => html`<li class="ly-row">${it.photo ? html`<img src="${thumbUrl(it.photo)}" alt="" loading="lazy">` : html`<span class="ly-nophoto" aria-hidden="true"></span>`}
      <div class="ly-row-main"><div class="ly-row-txt"><span class="ly-num" aria-hidden="true">${it.sort}</span> <strong><a href="#/plant/${enc(it.plant)}">${it.name}</a></strong> <span class="code">${it.plant}</span>
        <br><span>In your record: ${it.rec_label || 'no room or shelf'}. On this layout: ${to.label}.</span></div>
      <button class="btn small ghost" type="button" data-act="lyrec" data-id="${it.id}" aria-label="Move it in the record: ${it.name}">Move it in the record</button></div></li>`)}</ul>${list.length > 12 ? raw('</details>') : ''}`);
  if (keep) { const el = keep === 'all' ? document.getElementById('ly-recall') : box.querySelector(`[data-act=lyrec][data-id="${keep}"]`); if (el) el.focus({ preventScroll: true }); }
}
function lyDrawAll() { if (!lyOn()) return; LY.F = lyFindings(LY.d); lyHead(); lyToolsDraw(); lyDrawViews(); lyPanel(); lyLists(); }
function lySay(text) { const el = document.getElementById('ly-say'); if (el && text) el.textContent = text; }
const lySayIt = it => lySay(`${it.name}: ${lyWhere(LY.d, it)}.${LY.F.some(f => f.ids.includes(it.id) && lyIsLv(f.kind)) ? '' : lyLightLine(it)} ${LY.F.filter(f => f.ids.includes(it.id)).map(f => f.text).join(' ')}`);

// ---------- changing a layout ----------
// A thing moved or changed size while being dragged or stepped: only what changed on the page is touched, so the thing keeps the
// pointer and the keyboard. inner: its size changed, so what is drawn inside it is made again.
function lyLive(it, inner, also) {                      // also: the things it carries, which move with it
  const moving = t => t === it || (also && also.includes(t));
  LY.F = lyFindings(LY.d);
  document.querySelectorAll('svg.ly-svg[data-live]').forEach(svg => {
    const view = svg.dataset.view, o = lyOpts(view);
    svg.querySelectorAll('g.ly-it').forEach(g => {
      const t = lyItem(+g.dataset.id); if (!t) return;
      const cls = lyItCls(t, o); if (g.getAttribute('class') !== cls) g.setAttribute('class', cls);
      if (moving(t)) { g.setAttribute('transform', lyItTf(LY.d, t, view, o)); if (inner && t === it) g.innerHTML = rend(lyItemInner(LY.d, t, view, o)); }
      if (g.hasAttribute('aria-label') && (moving(t) || o.state.get(t.id))) g.setAttribute('aria-label', lyItLabel(LY.d, t, LY.F));
    });
    svg.querySelectorAll('g.ly-lab').forEach(g => {
      const t = lyItem(+g.dataset.id); if (!t) return;
      const cls = lyLabCls(t, o); if (g.getAttribute('class') !== cls) g.setAttribute('class', cls);
      const lv = lyLvKey(t, o), again = g.dataset.lv !== lv; if (again) g.dataset.lv = lv;                 // its light changed as something moved
      if (moving(t)) g.setAttribute('transform', lyItTf(LY.d, t, view, o));
      if ((t === it && inner) || again) g.innerHTML = rend(lyItemLab(LY.d, t, view, o));
    });
    const mark = svg.querySelector('.ly-selmark');
    if (mark && +mark.dataset.id === it.id) mark.outerHTML = rend(lySelMark(LY.d, it, view, o));
  });
  lyHead(); lyPanelPatch(); lyLists();
}
function lySelect(id, view, focus) {                    // choose a thing (or none): its ring on both drawings, and its place and size beside them
  if (view) LY.fview = view;
  const want = LY.fview;                                 // drawing the views again may put the keyboard back on the thing that had it, in the other view
  if (LY.sel !== id) {
    const shown = lyLevelNow();
    LY.sel = id; LY.tall = null;
    const turned = lyWallFollow(lyItem(id)); if (turned) lySay(`The front view now looks at ${LY_WALLS[LY.wall].toLowerCase()}.`);
    if (turned || lyLevelNow() !== shown) lyDrawViews();                     // the top view goes to the chosen thing's level, the front view to its wall
    else document.querySelectorAll('svg.ly-svg[data-live]').forEach(svg => {
      const o = lyOpts(svg.dataset.view), old = svg.querySelector('.ly-selmark'), it = lyItem(id);
      if (old) old.remove();
      const stop = lyTabStop(LY.d, o);
      svg.querySelectorAll('g.ly-it').forEach(g => {
        const on = +g.dataset.id === id; g.classList.toggle('is-sel', on);
        if (g.hasAttribute('aria-pressed')) { g.setAttribute('aria-pressed', String(on)); g.setAttribute('tabindex', +g.dataset.id === stop ? '0' : '-1'); }
      });
      if (it && svg.querySelector(`g.ly-it[data-id="${id}"]`)) svg.insertAdjacentHTML('beforeend', rend(lySelMark(LY.d, it, svg.dataset.view, o)));      // not in a front view of another wall
    });
    lyPanel(); lyLists();
  }
  if (focus && id != null) lyFocusIt(id, want);
}
function lySaveItem(it, was, more) {                    // sends what changed on one thing (and more: what the plant's page is to say its height is); saves go one after another, in the order they were made
  const body = {}; for (const k of LY_KEYS) if (it[k] !== was[k]) body[k] = it[k];
  if (more) Object.assign(body, more);
  if (!Object.keys(body).length) return LY.q;
  const id = it.id, lid = LY.d.id;
  LY.q = LY.q.then(() => api('PUT', '/api/layouts/items/' + id, body)).then(() => {}, e => lyNotSaved(e, lid));
  return LY.q;
}
// A change was not saved (the server refused it, or cannot be reached). The page says so and shows the layout as it is saved, so
// what is on the page is what is kept. If the layout cannot be read either, the page says its changes are not being saved, and
// nothing more can be changed until it has been read again (Read it again).
async function lyNotSaved(e, lid) {
  toast(e.message, true);
  if (!LY || LY.d.id !== lid) return;
  try { await lyReload(); } catch (e2) { LY.stale = true; lyDrawAll(); }
}
// What can be taken back, and done again: label says it whole ("Fig moved"), short is the word on the Undo button ("moved"),
// undo takes it back and redo does it again. A new change empties what could be done again. A thing that was taken off and put
// back has a new number in the record: LY.ids says which (lyCur), so older changes still find it.
function lyUndoPush(label, short, undo, redo) { LY.undo.push({ label, short, undo, redo }); if (LY.undo.length > 40) LY.undo.shift(); LY.redo = []; lyToolsDraw(); }
const lyCur = id => { while (LY.ids.has(id)) id = LY.ids.get(id); return id; };
// A change to a thing is done: draw it properly (what is in front of what may have changed), keep it for Undo, and save it.
// panel: 'full' draws the chosen thing's boxes again; otherwise they are only filled in, so a box being typed in keeps the keyboard.
function lyCommit(it, was, what, panel, riders) {       // riders: what it carried, each with the place it had (lyCarryStart)
  const keys = LY_KEYS.filter(k => it[k] !== was[k]); if (!keys.length) return;
  const id = it.id, back = {}; keys.forEach(k => { back[k] = was[k]; });
  const tall = keys.includes('h') && lyPaged(it), pageWas = was.page_h == null ? null : was.page_h;      // a plant's height is saved on its page too, and Undo puts back what the page said
  const fwd = {}; keys.forEach(k => { fwd[k] = it[k]; });
  const place = t => ({ x: t.x, y: t.y, z: t.z });
  const ride = (riders || []).filter(r => ['x', 'y', 'z'].some(k => r.it[k] !== r.was[k])).map(r => ({ id: r.it.id, back: place(r.was), fwd: place(r.it), it: r.it, was: r.was }));
  if (tall) { lyPageH(it, it.h); LY.tall = id; }
  const put = (vals, page, dir) => async () => {         // its changed values as they were, or as they became; a plant's page height with them; what it carried goes with it
    const t = lyItem(lyCur(id)); if (!t) return; const now = { ...t }; Object.assign(t, vals); if (tall) { lyPageH(t, page); LY.tall = null; }
    const also = ride.map(r => { const q = lyItem(lyCur(r.id)); if (!q) return null; const w = { ...q }; Object.assign(q, r[dir]); return [q, w]; }).filter(Boolean);
    if (LY.sel === t.id) lyWallFollow(t);
    lyDrawAll(); lySaveItem(t, now, tall ? { page_h: page } : null); for (const [q, w] of also) lySaveItem(q, w);
    await LY.q;
  };
  const with_ = ride.length ? `, and ${ride.length === 1 ? 'the one thing' : `the ${ride.length} things`} it carries` : '';
  LY.undo.push({ label: `${it.name} ${what}${with_}`, short: what, undo: put(back, pageWas, 'back'), redo: put(fwd, fwd.h, 'fwd') });
  if (LY.undo.length > 40) LY.undo.shift();
  LY.redo = [];
  LY.F = lyFindings(LY.d); lyHead();
  if (LY.sel === it.id) lyWallFollow(it);                // the front view stays with the chosen thing when it has gone to another wall
  lyToolsDraw(); lyDrawViews();
  if (panel === 'full') lyPanel(); else lyPanelPatch();
  lyLists();
  if (tall) lySay(`${it.name} is now ${lenF(it.h)} tall, here and on its page. ${LY.F.filter(f => f.ids.includes(it.id)).map(f => f.text).join(' ')}`);
  else { lySayIt(it); if (ride.length) lySay(document.getElementById('ly-say').textContent + ` ${ride.length === 1 ? 'The one thing it carries' : `The ${ride.length} things it carries`} moved with it.`); }
  lySaveItem(it, was); for (const r of ride) lySaveItem(r.it, r.was);
}
async function lyReload() {
  const id = LY.d.id, d = await api('GET', `/api/layouts/${id}?_=${Date.now()}`);
  if (!LY || LY.d.id !== id) return;
  LY.d = d; LY.stale = false; if (LY.sel && !lyItem(LY.sel)) LY.sel = null;
  if (LY.level !== 'auto' && LY.level && !lyItem(LY.level)) LY.level = 'auto';
  lyDrawAll();
}
function lyTake(d, pick) {                              // the server's answer after things were added or the space changed
  LY.d = d; if (pick !== undefined) LY.sel = pick;
  if (LY.sel && !lyItem(LY.sel)) LY.sel = null;
  if (LY.level !== 'auto' && LY.level && !lyItem(LY.level)) LY.level = 'auto';
  if (pick !== undefined) lyWallFollow(lyItem(LY.sel));      // a thing just put on is chosen: the front view goes to its wall
  lyDrawAll();
}
const lySpec = it => ({ kind: it.kind, name: it.name, shape: it.shape, x: it.x, y: it.y, z: it.z, w: it.w, d: it.d, h: it.h, locked: !!it.locked, size_locked: !!it.size_locked,
  ...(it.kind === 'light' && it.hours != null ? { hours: it.hours, dim_pct: it.dim_pct } : {}), ...(it.plant ? { plant: it.plant } : {}), ...(it.light_id ? { light_id: it.light_id } : {}), ...(it.spot_id ? { spot_id: it.spot_id } : {}) });
// Puts things on the layout, each in the first place it is clear of the others (unless it comes with its place), and chooses the last one.
// The chosen thing says where to start: on it if it is a shelf, over it if it is a plant and the new thing hangs. where: { shelf } says
// it instead (a copy starts on what the thing it copies stands on, or under what that hangs under).
async function lyAddItems(specs, placed, where) {
  if (!specs.length) return;
  await lyFlush();
  const L = LY.d, T = { ...L, items: L.items.slice() }, on = where ? null : lyItem(LY.sel), shelf = where ? where.shelf || null : on && (on.kind === 'shelf' || on.kind === 'other') ? on : null;
  const over = on && on.kind === 'plant' ? L.items.filter(b => (b.kind === 'shelf' || b.kind === 'other') && lyPlan(on, b) < -LY_EPS && b.z >= on.z + on.h - LY_EPS).sort((x, y) => x.z - y.z)[0] || null : null;       // what is over the chosen plant
  const body = specs.map((s, i) => {
    const { hangs, ...it } = s; let t = null;
    if (!placed && hangs && on && on.kind === 'plant') {         // straight over the chosen plant, if there is room there
      const c = { ...it, x: r2(on.x + on.w / 2 - it.w / 2), y: r2(on.y + on.d / 2 - it.d / 2), z: r2((over ? over.z : L.height_in) - it.h) };
      if (lyFree(T, c, 0)) t = c;
    }
    if (!t) t = placed ? it : lyPlace(T, it, shelf || (hangs ? over : null), hangs);
    T.items.push({ ...t, id: -1 - i, sort: 0 }); return lySpec(t);
  });
  const before = new Set(L.items.map(x => x.id));
  await guard(async () => {
    const d = await api('POST', `/api/layouts/${L.id}/items`, { items: body }), added = d.items.filter(x => !before.has(x.id));
    let gone = [];                                        // while they are taken back: [the id each had, what it was]
    lyUndoPush(added.length === 1 ? `${added[0].name} put on` : `${added.length} things put on`, added.length === 1 ? 'put on' : `${added.length} put on`,
      async () => { gone = added.map(x => [x.id, lyItem(lyCur(x.id))]).filter(([, t]) => t).map(([i, t]) => [i, lySpec(t)]); for (const [i] of gone) await api('DELETE', '/api/layouts/items/' + lyCur(i)); await lyReload(); },
      async () => {
        if (!gone.length) return;
        const had = new Set(LY.d.items.map(x => x.id)), r = await api('POST', `/api/layouts/${LY.d.id}/items`, { items: gone.map(([, spec]) => spec) }), back = r.items.filter(x => !had.has(x.id));
        gone.forEach(([i], n) => { if (back[n]) LY.ids.set(lyCur(i), back[n].id); });
        lyTake(r, back.length ? back[back.length - 1].id : undefined);
      });
    lyTake(d, added.length ? added[added.length - 1].id : undefined);
    const last = added[added.length - 1];
    if (last) { lyFocusIt(last.id, LY.fview); lyShow(last.id); lySay(`${added.length === 1 ? last.name : added.length + ' things'} put on the layout. ${last.name}: ${lyWhere(LY.d, last)}.`); }
  });
}
async function lyTakeOff(it) {                          // off the layout, in the record and on the page
  await api('DELETE', '/api/layouts/items/' + it.id);
  LY.d.items = LY.d.items.filter(x => x !== it);
  const p = it.plant && LY.d.plants.find(x => x.code === it.plant); if (p) p.on = false;
  if (LY.sel === it.id) LY.sel = null;
  if (LY.level === it.id) LY.level = 'auto';
}
async function lyRemove(it) {
  await lyFlush();
  const name = it.name, id = it.id; let spec = lySpec(it);
  await guard(async () => {
    await lyTakeOff(it);
    lyUndoPush(`${name} taken off`, 'taken off',
      async () => { const had = new Set(LY.d.items.map(x => x.id)), d = await api('POST', `/api/layouts/${LY.d.id}/items`, { items: [spec] }), n = d.items.find(x => !had.has(x.id)); if (n) LY.ids.set(lyCur(id), n.id); lyTake(d); },
      async () => { const t = lyItem(lyCur(id)); if (!t) return; spec = lySpec(t); await lyTakeOff(t); lyDrawAll(); });
    lyDrawAll(); toast(`Taken off the layout: ${name}. Undo puts it back.`);
    const b = document.getElementById('ly-add'); if (b) b.focus({ preventScroll: true });
  });
}
async function lyUndo() {
  await lyFlush();
  const u = LY.undo.pop(); if (!u) return;
  if (u.redo) LY.redo.push(u);                          // at once: a change made while this is still being saved empties Redo, and must not be followed by this
  lyToolsDraw();
  const ok = await guard(async () => { await u.undo(); toast('Undone: ' + u.label); return true; });
  if (!ok && LY.redo.includes(u)) LY.redo.splice(LY.redo.indexOf(u), 1);
  lyToolsDraw();
}
async function lyRedo() {                               // does again the change that Undo last took back
  await lyFlush();
  const u = LY.redo.pop(); if (!u) return;
  LY.undo.push(u); lyToolsDraw();
  const ok = await guard(async () => { await u.redo(); toast('Done again: ' + u.label); return true; });
  if (!ok && LY.undo.includes(u)) LY.undo.splice(LY.undo.indexOf(u), 1);
  lyToolsDraw();
}
async function lyPutLayout(changes, label) {
  await lyFlush();
  const L = LY.d, back = {}; Object.keys(changes).forEach(k => { back[k] = L[k]; });
  return guard(async () => {
    const d = await api('PUT', '/api/layouts/' + L.id, changes);
    if (label) lyUndoPush(label, 'size and name', async () => { lyTake(await api('PUT', '/api/layouts/' + L.id, back)); }, async () => { lyTake(await api('PUT', '/api/layouts/' + L.id, changes)); });
    lyTake(d); return true;
  });
}

// ---------- moving by the arrow keys ----------
// One square at a time (five with Shift). With snapping on, a thing that is off the grid goes to the next grid line first. Going up
// or down in the front view it stops on the way at anything it can stand on or hang under, so it lands on a shelf exactly.
function lyStops(L, it, skip) {                         // heights (of its bottom) at which it would rest on something or hang under something (skip: what it carries)
  const s = [0, L.height_in - it.h];
  for (const b of L.items) if (b !== it && !(skip && skip.has(b.id)) && b.kind !== 'zone' && lyPlan(it, b) < -LY_EPS) for (const q of lySolids(b)) { s.push(q.z + q.h); if (it.kind === 'light') s.push(q.z - it.h); }
  return s.filter(z => z >= -LY_EPS);
}
function lyNudge(it, view, dx, dy, n) {
  const L = LY.d, g = +L.grid_in || 1, going = LY.nudge && LY.nudge.id === it.id, was = going ? LY.nudge.was : { ...it }, riders = going ? LY.nudge.riders : lyCarryStart(L, it), skip = lyCarrySkip(riders);
  const step = (v, d) => !d ? v : !L.snap ? v + d * g * n : (d > 0 ? Math.floor(v / g + 1e-6) + n : Math.ceil(v / g - 1e-6) - n) * g;
  const keepIn = (v, size, max) => clamp(v, Math.min(0, g - size), Math.max(0, max - Math.min(g, size)));        // some of it stays in the space
  const before = { ...it };
  if (view === 'top') { it.x = r2(keepIn(step(it.x, dx), it.w, L.width_in)); it.y = r2(keepIn(step(it.y, dy), it.d, L.depth_in)); lyLand(L, it, before, skip); }
  else {                                                 // across the wall looked at: Right is to your right as you face it
    const face = lyFaceNow(), ax = lySide(face) ? 'y' : 'x', turn = face === 'left' || face === 'front' ? -1 : 1;
    it[ax] = r2(keepIn(step(it[ax], dx * turn), lyAw(it, face), lyAcrossW(L, face)));
    if (dy) {
      const from = it.z, to = clamp(step(it.z, -dy), 0, Math.max(0, L.height_in - Math.min(g, it.h)));
      const stop = lyStops(L, it, skip).filter(z => (to > from ? z > from + LY_EPS && z < to - LY_EPS : z < from - LY_EPS && z > to + LY_EPS)).sort((a, b) => (to > from ? a - b : b - a))[0];
      it.z = r2(stop != null ? stop : to);
    }
  }
  lyCarryMove(it, was, riders);
  lyLive(it, false, riders.map(r => r.it)); lySayIt(it);
  if (LY.nudge) clearTimeout(LY.nudge.t);
  LY.nudge = { id: it.id, was, riders, t: setTimeout(lyFlush, 700) };
}
function lyFlush() {                                    // the arrow keys' moves are saved once they pause, or before anything else is done
  const n = LY && LY.nudge; if (!n) return LY ? LY.q : Promise.resolve();
  clearTimeout(n.t); LY.nudge = null;
  const it = lyItem(n.id); if (it) lyCommit(it, n.was, 'moved', '', n.riders);
  return LY.q;
}

// ---------- moving and resizing with the pointer ----------
function lyPoint(svg, e) {                              // where the pointer is on the drawing, in inches
  const m = svg.getScreenCTM(); if (!m) return { x: 0, y: 0 };
  const p = svg.createSVGPoint(); p.x = e.clientX; p.y = e.clientY;
  const q = p.matrixTransform(m.inverse()); return { x: q.x, y: q.y };
}
document.addEventListener('pointerdown', e => {
  if (!lyOn() || e.button > 0 || !e.target.closest) return;
  const svg = e.target.closest('svg.ly-svg[data-live]'); if (!svg) return;
  const hd = e.target.closest('.ly-handle'), g = hd ? null : e.target.closest('g.ly-it');
  if (!hd && !g) return;
  const it = lyItem(+(hd ? hd.closest('.ly-selmark') : g).dataset.id); if (!it) return;
  const view = svg.dataset.view, chosen = LY.sel === it.id;
  lyFlush();                                                    // this may draw the views again, so the drawing is looked up afresh below
  if (!hd) lySelect(it.id, view, true);
  if (!lyCan() || (hd ? it.size_locked : it.locked)) return;           // the corner handle needs the size unlocked; a move needs the place unlocked
  if (e.pointerType === 'touch' && !chosen && !hd) return;      // on a touch screen the first touch chooses a thing, and the page still scrolls; the next one drags it
  if (!getName() && !viaTS()) { needName(); return; }
  e.preventDefault();
  const live = document.querySelector(`svg.ly-svg[data-live][data-view="${view}"]`); if (!live) return;
  LY.drag = { id: it.id, view, svg: live, resize: !!hd, pid: e.pointerId, p0: lyPoint(live, e), was: { ...it }, moved: false, at: null, face: lyFaceNow(), riders: hd ? [] : lyCarryStart(LY.d, it) };
  window.addEventListener('pointermove', lyDragMove); window.addEventListener('pointerup', lyDragEnd); window.addEventListener('pointercancel', lyDragEnd);
});
function lyDragEdge() {                                 // while a thing is held near the top or bottom of the window, the page scrolls and the thing keeps up
  const dg = LY && LY.drag; if (!dg) return;
  const bar = document.querySelector('header.top'), top = (bar ? bar.getBoundingClientRect().bottom : 0) + 36, y = dg.at ? dg.at.clientY : -1;
  const by = !dg.moved || y < 0 ? 0 : y < top ? -Math.min(18, (top - y) / 3 + 4) : y > window.innerHeight - 36 ? Math.min(18, (y - window.innerHeight + 36) / 3 + 4) : 0;
  if (by) { const was = window.scrollY; window.scrollBy(0, by); if (window.scrollY !== was) lyDragMove(dg.at); }
  dg.edge = requestAnimationFrame(lyDragEdge);
}
function lyDragMove(e) {
  const dg = LY && LY.drag; if (!dg || e.pointerId !== dg.pid) return;
  const it = lyItem(dg.id); if (!it) return;
  dg.at = { clientX: e.clientX, clientY: e.clientY, pointerId: e.pointerId, preventDefault() {} };
  if (!dg.edge) dg.edge = requestAnimationFrame(lyDragEdge);
  const L = LY.d, p = lyPoint(dg.svg, e), dx = p.x - dg.p0.x, dy = p.y - dg.p0.y, top = dg.view === 'top', g = +L.grid_in || 1, w = dg.was;
  if (!dg.moved && Math.hypot(dx, dy) * LY.Sv[dg.view] < 4) return;       // a press, not a drag yet
  dg.moved = true; e.preventDefault();
  const snap = v => L.snap ? Math.round(v / g) * g : v, least = L.snap ? g : 0.5;
  const face = dg.face, side = lySide(face), turned = face === 'left' || face === 'front', skip = lyCarrySkip(dg.riders);
  if (dg.resize && top) {                                       // the corner follows the pointer: the right edge and the front edge
    it.w = r2(Math.max(least, snap(w.x + w.w + dx) - w.x));
    it.d = r2(Math.max(least, snap(w.y + w.d + dy) - w.y)); if (lyRound(w)) it.w = it.d = Math.max(it.w, it.d);
  } else if (dg.resize) {                                       // in the front view: the edge at the view's right, and the top edge
    const ax = side ? 'y' : 'x', sz = side ? 'd' : 'w', other = side ? 'w' : 'd';
    if (turned) { const lo = snap(w[ax] - dx), n = r2(Math.max(least, w[ax] + w[sz] - lo)); it[ax] = r2(w[ax] + w[sz] - n); it[sz] = n; }      // that edge is the thing's left (or back) edge here
    else it[sz] = r2(Math.max(least, snap(w[ax] + w[sz] + dx) - w[ax]));
    it.h = r2(Math.max(least, snap(w.z + w.h - dy) - w.z)); if (lyPaged(it)) it.h = clamp(it.h, 0.5, 600);
    if (lyRound(w)) it[other] = it[sz];
  } else {
    const keepIn = (v, size, max) => clamp(v, Math.min(0, g - size), Math.max(0, max - Math.min(g, size)));
    if (top) { it.x = r2(keepIn(snap(w.x + dx), it.w, L.width_in)); it.y = r2(keepIn(snap(w.y + dy), it.d, L.depth_in)); it.z = w.z; lyLand(L, it, w, skip); }       // dropped onto a shelf, it stands on it
    else {                                                      // across the wall looked at; up the screen is up off the floor; near something to stand on or hang under, it goes to it
      const ax = side ? 'y' : 'x';
      it[ax] = r2(keepIn(snap(w[ax] + (turned ? -dx : dx)), lyAw(it, face), lyAcrossW(L, face)));
      const free = clamp(w.z - dy, 0, Math.max(0, L.height_in - Math.min(g, it.h))), near = lyStops(L, it, skip).map(z => [Math.abs(z - free), z]).sort((a, b) => a[0] - b[0])[0];
      it.z = r2(near && near[0] * LY.Sv.front <= 9 ? near[1] : clamp(snap(free), 0, L.height_in));
    }
    lyCarryMove(it, w, dg.riders);
  }
  if (dg.raf) return;
  dg.raf = requestAnimationFrame(() => { dg.raf = 0; if (LY && LY.drag === dg) lyLive(it, dg.resize, dg.riders.map(r => r.it)); });
}
function lyDragEnd(e) {
  const dg = LY && LY.drag; if (!dg || e.pointerId !== dg.pid) return;
  window.removeEventListener('pointermove', lyDragMove); window.removeEventListener('pointerup', lyDragEnd); window.removeEventListener('pointercancel', lyDragEnd);
  if (dg.raf) cancelAnimationFrame(dg.raf);
  if (dg.edge) cancelAnimationFrame(dg.edge);
  LY.drag = null;
  const it = lyItem(dg.id); if (!it || !dg.moved) return;
  if (e.type === 'pointercancel') { Object.assign(it, dg.was); for (const r of dg.riders) Object.assign(r.it, r.was); lyDrawAll(); return; }
  lyCommit(it, dg.was, dg.resize ? 'resized' : 'moved', '', dg.riders);
  lyFocusIt(it.id, dg.view);
}
document.addEventListener('keydown', e => {
  if (!lyOn() || e.defaultPrevented || e.altKey || !e.target.closest) return;
  const g = e.target.closest('g.ly-it'); if (!g) return;
  const view = g.closest('svg').dataset.view, it = lyItem(+g.dataset.id); if (!it) return;
  if (e.ctrlKey || e.metaKey) return;                     // Ctrl+Z and Ctrl+Y are heard by the whole page, below
  if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); lySelect(it.id, view, true); lySayIt(it); return; }
  if (e.key === 'Escape') { if (LY.sel != null) { e.preventDefault(); lyFlush(); lySelect(null); } return; }
  if (e.key === 'PageDown' || e.key === 'PageUp') {              // to the next or the previous thing, in the order of their numbers, and round again
    e.preventDefault(); lyFlush();
    const all = LY.d.items, at = all.indexOf(it), to = all[(at + (e.key === 'PageDown' ? 1 : all.length - 1)) % all.length];
    if (LY.level !== 'auto' && (lyDim(LY.d, lyLevelNow()) || new Set()).has(to.id)) { LY.level = 'auto'; lyToolsDraw(); }      // it is on a level that was not being shown
    lySelect(to.id, view, true); lyShow(to.id); lySayIt(to); return;
  }
  const dir = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[e.key];
  if (!dir && e.key !== 'Delete') return;
  e.preventDefault();
  if (!lyCan()) return;
  if (it.locked) { toast(`${it.name} is locked in place. Untick Lock its place to move it.`); return; }
  if (!getName() && !viaTS()) { needName(); return; }
  if (LY.sel !== it.id) lySelect(it.id, view);
  LY.fview = view;
  if (e.key === 'Delete') lyRemove(it); else lyNudge(it, view, dir[0], dir[1], e.shiftKey ? 5 : 1);
});
// Ctrl+Z takes back the last change and Ctrl+Y (or Ctrl+Shift+Z) does it again, anywhere on a layout's page except in a box where
// typing has its own undo, or while a window is open.
document.addEventListener('keydown', e => {
  if (!lyOn() || e.defaultPrevented || e.altKey || !(e.ctrlKey || e.metaKey)) return;
  const k = e.key.toLowerCase(), redo = k === 'y' || (k === 'z' && e.shiftKey); if (!redo && k !== 'z') return;
  const t = e.target, typing = t && t.matches && t.matches('input:not([type=checkbox]):not([type=radio]):not([type=button]), textarea, [contenteditable]');
  if (typing || document.querySelector('dialog[open]') || !lyCan()) return;
  e.preventDefault(); if (redo) lyRedo(); else lyUndo();
});
document.addEventListener('focusout', e => {            // leaving a thing saves its moves, once the keyboard has landed where it was going (so that keeps it)
  if (!LY || !LY.nudge || !e.target.closest || !e.target.closest('g.ly-it')) return;
  const id = LY.nudge.id;
  setTimeout(() => { const a = document.activeElement, g = a && a.closest ? a.closest('g.ly-it') : null; if (LY && LY.nudge && LY.nudge.id === id && !(g && +g.dataset.id === id)) lyFlush(); }, 0);
});
document.addEventListener('focusin', e => { const g = lyOn() && e.target.closest ? e.target.closest('g.ly-it') : null; if (g) LY.fview = g.closest('svg').dataset.view; });
window.addEventListener('hashchange', () => { if (LY && LY.nudge) lyFlush(); });
window.addEventListener('resize', () => { if (!lyOn()) return; clearTimeout(LY.rz); LY.rz = setTimeout(() => { if (lyOn() && !LY.drag) { lyToolsDraw(); lyDrawViews(); } }, 160); });
document.addEventListener('prefs', () => { if (lyOn()) setTimeout(() => { if (lyOn() && !LY.drag) { lyToolsDraw(); lyDrawViews(); } }, 60); });
document.addEventListener('input', e => {               // the search box in the Add window narrows the list of plants as you type
  if (e.target.id !== 'ly-add-q') return;
  const q = e.target.value.trim().toLowerCase(); let n = 0;
  dlg.querySelectorAll('.ly-pick').forEach(li => { const on = !q || li.dataset.q.includes(q) || li.querySelector('input').checked; li.hidden = !on; if (on) n++; });
  const m = document.getElementById('ly-add-n'); if (m) m.textContent = q ? `${n} ${n === 1 ? 'plant matches' : 'plants match'}.` : '';
});
document.addEventListener('keydown', e => { if (e.key === 'Enter' && e.target.id === 'ly-add-q') e.preventDefault(); });      // Enter in the search box must not add

// ---------- the windows: add something, size and name ----------
function lyKindShow() {
  const f = dlg.querySelector('form[data-lyadd]'); if (!f) return;
  const k = f.elements.kind.value;
  f.querySelectorAll('[data-lyk]').forEach(el => { el.hidden = el.dataset.lyk !== k; });
  const own = f.querySelector('[data-lyown]'); if (own) own.hidden = f.elements.shelf.value !== '';
}
async function lyAddDialog() {
  if (!(await needName())) return;
  await lyFlush();
  const L = LY.d, on = lyItem(LY.sel), shelf = on && (on.kind === 'shelf' || on.kind === 'other') ? on : null;
  const free = L.plants.filter(p => !p.on).sort((a, b) => (b.here - a.here) || a.name.localeCompare(b.name));
  const num = (name, label, v) => html`<label class="f">${label} (${lenU()})<input type="number" inputmode="decimal" min="0" step="any" name="${name}" value="${v == null ? '' : lenF(v, false)}"></label>`;
  const names = k => html`<datalist id="ly-names-${k}">${LY_NAMES[k].map(x => html`<option value="${x}"></option>`)}</datalist>`;
  const shown = modal(html`<form method="dialog" class="ly-form" data-lyadd><h2>Add to the layout</h2>
    <fieldset class="ly-kind"><legend>What is it?</legend><div class="opts">${LY_KINDS.map((k, i) => html`<label><input type="radio" name="kind" value="${k}" data-act="lykind" ${i === 0 ? raw('checked') : ''}><span>${L.kinds[k]}</span></label>`)}</div></fieldset>
    <div data-lyk="plant">
      <label class="f">Search your plants<input type="search" id="ly-add-q" autocomplete="off" placeholder="Name or code"></label><p class="hint" id="ly-add-n" role="status"></p>
      ${free.length ? html`<ul class="ly-picks">${free.map(p => html`<li class="ly-pick" data-q="${(p.name + ' ' + p.code).toLowerCase()}"><label class="chk"><input type="checkbox" name="plant" value="${p.code}">
        ${p.photo ? html`<img src="${thumbUrl(p.photo)}" alt="" loading="lazy">` : html`<span class="ly-nophoto" aria-hidden="true"></span>`}
        <span><strong>${p.name}</strong> <span class="code">${p.code}</span>${p.here ? html`<span class="muted">, here</span>` : ''}<br><span class="muted">${lySizeWords(p)}${p.guessed.length ? ' (a guess)' : ''}</span></span></label></li>`)}</ul>`
        : html`<p class="muted">Every plant at this home is on the layout already.</p>`}
      <label class="f">Or a plant with no page yet<input type="text" name="newplant" maxlength="80" autocomplete="off" placeholder="A Monstera I am thinking of buying"><small>It is drawn 8 in across and 12 in tall to start with.</small></label></div>
    <div data-lyk="light" hidden>${L.lights.length ? html`<label class="f">Which light<select name="light">${L.lights.map(x => { const n = L.items.filter(i => i.light_id === x.id).length; return html`<option value="${x.id}">${x.name} (${x.count} owned, ${n} drawn)</option>`; })}</select></label>
      <label class="f">How many<input type="number" name="lightn" min="1" max="20" step="1" value="1" inputmode="numeric"></label>
      <p class="hint">A light starts at a rough size from how it holds. A strip or a bulb starts under the chosen shelf, or at the top of the space. A light that stands starts on the floor or the chosen shelf.</p>`
      : html`<p class="muted">No lights in your list yet. <a href="#/lights">Grow lights</a> is where they are added.</p>`}</div>
    <div data-lyk="shelf" hidden><label class="f">Which<select name="shelf" data-act="lykind"><option value="">A board, a table or furniture I describe</option>
        ${L.shelves.map(s => html`<option value="b${s.spot_id}">${s.label}, as one block${s.guessed ? ' (size a guess)' : ''}</option>${s.boards.length ? html`<option value="l${s.spot_id}">${s.label}, level by level</option>` : ''}`)}</select></label>
      <div data-lyown><label class="f">Name<input type="text" name="shelfname" maxlength="80" autocomplete="off" value="Shelf"></label>
        <div class="field-grid three">${num('sw', 'Width', 24)}${num('sd', 'Depth', 12)}${num('sh', 'Height or thickness', 0.75)}</div></div></div>
    <div data-lyk="other" hidden><label class="f">Name<input type="text" name="othername" maxlength="80" autocomplete="off" list="ly-names-other"></label>${names('other')}
      <label class="f">Shape, seen from above<select name="othershape"><option value="box">Square or oblong</option><option value="round">Round</option></select></label>
      <div class="field-grid three">${num('ow', 'Width', 12)}${num('od', 'Depth', 12)}${num('oh', 'Height', 12)}</div></div>
    <div data-lyk="zone" hidden><label class="f">Name<input type="text" name="zonename" maxlength="80" autocomplete="off" list="ly-names-zone" value="Walkway"></label>${names('zone')}
      <div class="field-grid three">${num('zw', 'Width', Math.min(30, L.width_in))}${num('zd', 'Depth', Math.min(30, L.depth_in))}${num('zh', 'Height', L.height_in)}</div>
      <p class="hint">Anything put in this area is marked "In an area to keep clear". The area itself does not get in the way of anything.</p></div>
    <p class="hint">${shelf ? `It goes on ${shelf.name}, the thing chosen on the drawing, where there is room. A light that hangs goes under it.` : on && on.kind === 'plant' ? `It goes in the first free place. A light that hangs goes over ${on.name}, the plant chosen on the drawing.`
      : 'It goes in the first free place, from the back left corner. To put it on a shelf, or a light under one, choose that shelf on the drawing first.'}</p>
    <div class="row"><button class="btn" value="ok">Add to the layout</button><button class="btn ghost" value="cancel" formnovalidate>Cancel</button></div></form>`, 'wide');
  lyKindShow();
  if ((await shown) !== 'ok') return;
  const f = dlg.querySelector('form[data-lyadd]'), E = f.elements, kind = E.kind.value, len = (n, d) => { const v = lenIn(E[n].value); return E[n].value === '' || isNaN(v) || +v <= 0 ? d : r2(+v); };
  let specs = [], placed = false;
  if (kind === 'plant') {
    specs = [...f.querySelectorAll('input[name=plant]:checked')].map(c => L.plants.find(p => p.code === c.value)).filter(Boolean).map(p => ({ kind, plant: p.code, name: p.name, shape: p.shape, w: p.w, d: p.d, h: p.h }));
    if (E.newplant.value.trim()) specs.push({ kind, name: E.newplant.value.trim(), shape: 'round', w: 8, d: 8, h: 12 });
  } else if (kind === 'light' && E.light) {
    const x = L.lights.find(l => String(l.id) === E.light.value), n = clamp(parseInt(E.lightn.value, 10) || 1, 1, 20);
    if (x) for (let i = 0; i < n; i++) specs.push({ kind, light_id: x.id, name: x.name, shape: x.shape, w: x.w, d: x.d, h: x.h, hangs: x.hangs });
  } else if (kind === 'shelf') {
    const v = E.shelf.value, s = v ? L.shelves.find(x => String(x.spot_id) === v.slice(1)) : null;
    if (!v) specs.push({ kind, name: E.shelfname.value.trim() || 'Shelf', shape: 'box', w: len('sw', 24), d: len('sd', 12), h: len('sh', 0.75) });
    else if (s && v[0] === 'b') specs.push({ kind, spot_id: s.spot_id, name: s.name, shape: 'box', w: s.w, d: s.d, h: s.h });
    else if (s) {                                         // level by level: the whole unit finds its place as one block, then its boards go there
      const at = lyPlace(L, { kind, name: s.name, shape: 'box', w: s.w, d: s.d, h: s.h, x: 0, y: 0, z: 0 }, null);
      specs = s.boards.map(b => ({ ...b, name: `${s.name}, ${b.name.toLowerCase()}`, x: at.x, y: at.y, locked: false })); placed = true;
    }
  } else if (kind === 'other') specs.push({ kind, name: E.othername.value.trim() || 'Something else', shape: E.othershape.value, w: len('ow', 12), d: len('od', 12), h: len('oh', 12) });
  else if (kind === 'zone') specs.push({ kind, name: E.zonename.value.trim() || 'Keep clear', shape: 'box', w: len('zw', 30), d: len('zd', 30), h: len('zh', L.height_in) });
  if (!specs.length) { toast(kind === 'plant' ? 'Tick the plants to put on the layout.' : 'Nothing was added.', true); return; }
  await lyAddItems(specs, placed);
}
async function lySpaceDialog() {
  if (!(await needName())) return;
  const L = LY.d, num = (k, label, hint) => html`<label class="f">${label} (${lenU()})<input type="number" inputmode="decimal" min="0" step="any" name="${k}" value="${lenF(L[k], false)}">${hint ? html`<small>${hint}</small>` : ''}</label>`;
  const r = await modal(html`<form method="dialog" class="ly-form" data-lyspace><h2>Size and name</h2>
    <label class="f">Name<input type="text" name="name" maxlength="80" autocomplete="off" value="${L.name}"></label>
    <div class="field-grid three">${num('width_in', 'Width, left to right')}${num('depth_in', 'Depth, back to front')}${num('height_in', 'Height')}</div>
    ${num('clear_in', 'Room to leave around a plant', 'A plant closer than this to another thing, beside it or above it, is marked "Tight". 0 turns it off.')}
    <label class="chk ly-chk"><input type="checkbox" name="photos" ${LY.photos ? raw('checked') : ''}>Show each plant's photo on the drawing (on this device)</label>
    <label class="f">Notes<textarea name="notes" rows="2" maxlength="1000">${L.notes || ''}</textarea></label>
    <div class="row"><button class="btn" value="ok">Save changes</button><button class="btn ghost" value="cancel" formnovalidate>Cancel</button>
      <button class="btn ghost danger" type="button" data-act="lydel" data-id="${L.id}" data-name="${L.name}">Remove this layout</button></div></form>`);
  if (r !== 'ok') return;
  const E = dlg.querySelector('form[data-lyspace]').elements, ch = {};
  if (E.name.value.trim() && E.name.value.trim() !== L.name) ch.name = E.name.value.trim();
  for (const k of ['width_in', 'depth_in', 'height_in', 'clear_in']) { const v = lenIn(E[k].value); if (E[k].value !== '' && !isNaN(v) && Math.abs(+v - L[k]) > 0.004) ch[k] = r2(+v); }
  if (E.notes.value.trim() !== (L.notes || '')) ch.notes = E.notes.value.trim();
  if (E.photos.checked !== LY.photos) { LY.photos = E.photos.checked; lyPrefSave({ photos: LY.photos }); lyDrawViews(); }
  if (Object.keys(ch).length && (await lyPutLayout(ch, 'size and name changed'))) toast('Saved');
}

Object.assign(acts, {
  lynew: () => lyStartDialog(null),
  lyadd: () => lyAddDialog(),
  lyundo: () => lyUndo(),
  lyredo: () => lyRedo(),
  async lyreload() { try { await lyReload(); toast('The layout is shown as it is saved.'); } catch (e) { toast(e.message, true); } },
  lymore() { LY.more = !LY.more; lyPrefSave({ more: LY.more }); lyToolsDraw(); const b = document.getElementById('ly-more'); if (b) b.focus({ preventScroll: true }); },
  lyspace: () => lySpaceDialog(),
  lyzoom(el) {
    const steps = [0.5, 0.64, 0.8, 1, 1.25, 1.56, 1.95, 2.44, 3.05, 4], at = steps.reduce((b, v, i) => Math.abs(v - LY.zoom) < Math.abs(steps[b] - LY.zoom) ? i : b, 0);
    LY.zoom = steps[clamp(at + (+el.dataset.d > 0 ? 1 : -1), 0, steps.length - 1)]; lyPrefEach({ zoom: LY.zoom });
    lyToolsDraw(); lyDrawViews(); lySay(LY.zoom === 1 ? 'The drawing is at its usual size.' : `The drawing is ${fmt(LY.zoom, 2)} times its usual size.`);
  },
  async lypick(el) {
    await lyFlush();
    const id = +el.dataset.id, it = lyItem(id); if (!it) return;
    if (LY.level !== 'auto' && (lyDim(LY.d, lyLevelOf(LY.d, LY.level, id)) || new Set()).has(id)) { LY.level = 'auto'; lyToolsDraw(); }       // it is on a level that was not being shown
    lySelect(id, null, false);
    lyShow(id);
    if (!lyFocusIt(id, lyViewNow() === 'both' ? LY.fview : lyViewNow())) { const p = document.getElementById('ly-panel'); if (p) { p.setAttribute('tabindex', '-1'); p.focus({ preventScroll: true }); } }
    lySayIt(it);
  },
  async lyturn() {
    await lyFlush();
    const it = lyItem(LY.sel); if (!it || it.locked || it.size_locked || !(await needName())) return;
    const L = LY.d, g = +L.grid_in || 1, was = { ...it }, cx = it.x + it.w / 2, cy = it.y + it.d / 2;
    const at = (c, size, max) => { const v = L.snap ? Math.round((c - size / 2) / g) * g : c - size / 2; return r2(size <= max + LY_EPS ? clamp(v, 0, Math.max(0, max - size)) : v); };
    [it.w, it.d] = [it.d, it.w]; it.x = at(cx, it.w, L.width_in); it.y = at(cy, it.d, L.depth_in);       // turned about its middle, and kept inside the space where it fits there
    lyCommit(it, was, 'turned', 'full');
    const b = document.getElementById('ly-turn'); if (b) b.focus({ preventScroll: true });
  },
  async lycopy() {
    const it = lyItem(LY.sel); if (!it || !(await needName())) return;
    await lyFlush();
    const { x, y, z, ...rest } = lySpec(it), u = lyUnder(LY.d, it), o = lyOver(LY.d, it), hangs = it.kind === 'light' && !u, by = hangs ? o : u;
    await lyAddItems([{ ...rest, locked: false, size_locked: false, name: it.light_id ? it.name : `${it.name} (copy)`, hangs }], false, { shelf: by && typeof by === 'object' ? by : null });
  },
  async lytall() { const it = lyItem(LY.sel); if (!it || !lyPaged(it) || it.page_h != null || !(await needName())) return; await lyFlush(); lyTallSave(it); },
  async lyrm() { const it = lyItem(LY.sel); if (it && (await needName())) await lyRemove(it); },
  async lytray(el) {
    if (!(await needName())) return;
    const ps = LY.d.plants.filter(p => p.here && !p.on && (el.dataset.all || p.code === el.dataset.code));
    await lyAddItems(ps.map(p => ({ kind: 'plant', plant: p.code, name: p.name, shape: p.shape, w: p.w, d: p.d, h: p.h })));
  },
  async lyrec(el) {                                     // "Move it in the record": the plant's page says it is where this layout has it
    if (!(await needName())) return;
    await lyFlush();
    const L = LY.d, list = lyRecList(L).filter(x => el.dataset.all || x.it.id === +el.dataset.id); if (!list.length) return;
    if (list.length > 1 && !(await confirmBox(`Move ${list.length === 2 ? 'both' : list.length} plants in your record?`, `Each plant's own page will say it is where this layout has it${L.spot_id ? `: ${L.place}` : ''}. Undo puts them back.`, `Move ${list.length} plants`, false))) return;
    await guard(async () => {
      const d = await api('POST', `/api/layouts/${L.id}/record`, { moves: list.map(x => ({ plant: x.it.plant, place: x.to.pid })) });
      const done = d.moved.filter(m => m.changed), back = done.filter(m => m.from != null).map(m => ({ plant: m.plant, place: m.from }));
      const move = moves => async () => { lyTake((await api('POST', `/api/layouts/${LY.d.id}/record`, { moves })).layout); };
      if (back.length) lyUndoPush(done.length === 1 ? `${done[0].name} moved in the record` : `${done.length} plants moved in the record`, 'moved in the record',
        move(back), move(done.filter(m => m.from != null).map(m => ({ plant: m.plant, place: m.to }))));
      lyTake(d.layout);
      toast(done.length === 1 ? `Moved in your record: ${done[0].name} is now at ${done[0].to_label}. Undo puts it back.` : `${done.length} plants moved in your record. Undo puts them back.`);
      const b = document.getElementById('ly-undo'); if (b) b.focus({ preventScroll: true });
    });
  },
  async lydel(el) {
    if (!(await needName())) return;
    const open = document.querySelector('dialog[open]'); if (open) open.close('cancel');
    if (!(await confirmBox(`Remove the layout ${el.dataset.name}?`, 'The drawing and the places of the things on it are removed. Your plants, lights, rooms and shelves stay as they are.', 'Remove the layout', true))) return;
    await guard(async () => { await api('DELETE', '/api/layouts/' + el.dataset.id); toast(`Layout removed: ${el.dataset.name}`); LY = null; if (location.hash === '#/layouts') route(); else go('#/layouts'); });
  },
});
Object.assign(changeActs, {
  lyplace: () => lyStartFill(false),
  lykind: () => lyKindShow(),
  lyview(el) { LY.view = el.value; if (el.value !== 'both') LY.fview = el.value; lyPrefEach({ view: LY.view }); lyWallFollow(lyItem(LY.sel)); lyToolsDraw(); lyDrawViews(); },
  lywall(el) {                                          // which wall the front view looks at
    if (!LY_WALLS[el.value]) return;
    LY.wall = el.value; lyPrefEach({ wall: LY.wall }); lyDrawViews();
    const n = LY.wall === 'all' ? LY.d.items.length : lyWallSet(LY.d, LY.wall).size;
    lySay(`The front view now looks at ${LY_WALLS[LY.wall].toLowerCase()}: ${n} ${n === 1 ? 'thing' : 'things'}.`);
  },
  lygridshow(el) { LY.grid = el.checked; lyPrefSave({ grid: LY.grid }); lyDrawViews(); },
  async lysnap(el) { const on = el.checked; if (!(await needName()) || !(await lyPutLayout({ snap: on }))) { lyToolsDraw(); return; } lySay(on ? 'Things snap to the grid.' : 'Things move freely.'); },
  async lystep(el) { if (!(await needName()) || !(await lyPutLayout({ grid_in: +el.value }))) lyToolsDraw(); },
  lylevel(el) { LY.level = el.value === 'auto' ? 'auto' : +el.value || 0; lyDrawViews(); },
  async lyset(el) {                                     // a box of the chosen thing was changed: its place, its size, what it stands on, its shape, its lock, its name
    const val = el.type === 'checkbox' ? el.checked : el.value;       // read now: while this waits for earlier saves, the boxes may be filled in again from the thing as it then is
    await lyFlush();
    const L = LY.d, it = lyItem(LY.sel), k = el.dataset.k; if (!it) return;
    if (!(await needName())) { lyPanel(); return; }
    const was = { ...it }, riders = ['x', 'y', 'z', 'on', 'under'].includes(k) ? lyCarryStart(L, it) : [], skip = lyCarrySkip(riders); let what = 'moved', panel = '';
    const sz = LY_SIZE_KEYS.includes(k);
    if ((sz && it.size_locked) || (LY_PLACE_KEYS.includes(k) && it.locked)) { lyPanel(); toast(`${it.name}'s ${sz ? 'size' : 'place'} is locked. Untick Lock its ${sz ? 'size' : 'place'} to change it.`); return; }
    if (k === 'locked') { it.locked = val; what = val ? 'locked in place' : 'place unlocked'; panel = 'full'; }
    else if (k === 'size_locked') { it.size_locked = val; what = val ? 'size locked' : 'size unlocked'; panel = 'full'; }
    else if (k === 'shape') { it.shape = val; if (val === 'round') it.d = it.w; what = 'changed'; panel = 'full'; }
    else if (k === 'name') { const n = val.trim().replace(/\s+/g, ' '); if (!n) { el.value = it.name; return; } it.name = n; what = 'renamed'; }
    else if (k === 'hours') { const v = parseFloat(String(val).replace(',', '.')); if (val === '' || isNaN(v)) { el.value = it.hours; return; } it.hours = r2(clamp(v, 0, 24)); what = 'hours changed'; }
    else if (k === 'dim_pct') { it.dim_pct = clamp(Math.round(+val) || 100, 1, 100); what = 'brightness changed'; }
    else if (k === 'on') { const o = lyStandOpts(L, it).find(x => x.v === val); if (!o) return; const t = lyPutOn(L, it, o.q, skip); it.x = t.x; it.y = t.y; it.z = t.z; panel = 'rest'; }
    else if (k === 'under') { const o = lyHangOpts(L, it).find(x => x.v === val); if (!o) return; it.z = o.z; panel = 'rest'; }
    else {
      const v = lenIn(val), size = 'wdh'.includes(k);
      if (val === '' || isNaN(v) || (size && +v <= 0)) { el.value = lenF(it[k], false); return; }
      it[k] = r2(k === 'h' && lyPaged(it) ? clamp(+v, 0.5, 600) : size ? clamp(+v, 0.1, 2400) : clamp(+v, -2400, 4800));      // a plant's height goes on its page, which takes 0.5 to 600 in
      if (k === 'w' && lyRound(was)) it.d = it.w;
      if (size) what = 'resized'; else if (k !== 'z') lyLand(L, it, was, skip);
    }
    lyCarryMove(it, was, riders);
    lyCommit(it, was, what, panel === 'full' ? 'full' : '', riders);
    if (panel) { const again = document.getElementById(el.id); if (again) again.focus({ preventScroll: true }); }
  },
});

// What this module adds, said once (features.js): the Layouts page under Plants, after Rooms and spots; on Rooms and spots, a way
// in from the page and from each room, area and spot; and on a plant's own page, the layouts it is drawn on.
addFeature({
  name: 'layouts',
  pages: { layouts: { view: viewLayouts, nav: 'layouts', section: 'plants', label: 'Layouts', href: '#/layouts', after: 'where' } },
  adds: [{
    id: 'ly-wherelink',
    match: parts => parts[0] === 'where',
    anchor: main => main.querySelector('h1 ~ p:not(.hint)') || main.querySelector('h1'), where: 'afterend',
    load: async () => api('GET', '/api/layouts'),
    html: d => html`<p class="noprint" id="ly-wherelink"><a class="btn small ghost" href="#/layouts">Layouts</a> Draw a room or a shelf to scale and move things about on it${d.layouts.length ? ` (${d.layouts.length} so far)` : ''}.</p>`,
    then: (el, d) => {
      const has = new Map(d.places.map(p => [p.pid, p.layout_id]));
      const link = (pid, name) => rend(html`<a class="btn small ghost ly-wh" href="#/layouts?place=${pid}" aria-label="${has.get(pid) ? 'Open its layout' : 'Lay it out'}: ${name}">${has.get(pid) ? 'Open its layout' : 'Lay it out'}</a>`);
      document.querySelectorAll('#app .wh-spots [data-act=ltplace][data-id]').forEach(b => { if (!b.parentElement.querySelector('.ly-wh')) b.insertAdjacentHTML('afterend', link(+b.dataset.id, b.getAttribute('aria-label').replace(/^Measurements and photos of /, ''))); });
      document.querySelectorAll('#app .wh-area[data-aid] > .wh-row').forEach(r => { const t = r.querySelector('span.muted'), n = r.querySelector('input[data-k=name]'); if (t && !r.querySelector('.ly-wh')) t.insertAdjacentHTML('afterend', link(-r.parentElement.dataset.aid, n ? n.value : 'this place')); });
    },
  }, {
    id: 'ly-plant',
    match: parts => parts[0] === 'plant' && parts[1] && parts[2] !== 'edit',
    anchor: '#pl-grow', where: 'afterend',
    load: async parts => { const d = await api('GET', '/api/layouts?plant=' + enc(decodeURIComponent(parts[1]))); return d.on.length ? d : null; },
    html: d => html`<p class="hint" id="ly-plant">Drawn on ${d.on.length === 1 ? 'the layout' : 'the layouts'} ${d.on.map((x, i) => html`${i ? ', ' : ''}<a href="#/layouts/${x.id}?sel=${x.item}">${x.name}</a>`)}.</p>`,
  }],
});
