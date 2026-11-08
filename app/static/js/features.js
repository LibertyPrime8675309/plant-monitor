/* Plant record front end: the feature registry (1.46.0, PLAN.md step 2). One of the files loaded in order by index.html; they share
   one scope. Plain JavaScript, no inline handlers (the server's content policy forbids them).

   A feature module (turning.js, checkup.js, ...) says what it adds with one addFeature() call when it loads, instead of wrapping
   viewToday or loadCarePlant or watching the page for changes with a MutationObserver. The router, the Today page and the care
   part of a plant's page then ask the registry. Four kinds of thing can be registered:

   pages:  { turning: { view: async (parts, qs) => ({ title, html, after }), nav: 'turning',
                        section: 'care', label: 'Turn the pots', href: '#/turning', after: 'outside' } }
           The router opens view() for #/turning; the page joins the top bar's Care section after Back outside, and navMark()
           marks it. A page that is already in SECTIONS (sensors) gives only view and nav.
   today:  [{ id: 'today-turn', order: 65, load: async () => data or null, html: d => html, jump: d => 'Turn (3)' or '', cold: false }]
           A block on Today. load() runs alongside the page's own data; null or a failure leaves the block out. cold: true marks a
           block that belongs to a home with a winter: Today leaves it out at a tropical home (1.48.0). Blocks draw in
           order: the page's own are 10 cold night, 20 sensors, 30 water, 40 feed, 50 shopping, 60 coming inside, 70 needed
           from you, 80 quiet today; lines under the summary box are 1 to 9. jump() names a button in the summary's row.
   adds:   [{ id: 'tn-plant', match: parts => parts[0] === 'plant', anchor: '.quick-btns', where: 'afterend',
              load: async (parts, at) => data or null, failed: e => data, html: (d, parts, at) => html, care: true, then: (el, d) => {} }]
           Something added to a page after it draws (a line, a button, a section). The router runs every add whose match()
           is true once the page is on screen; an add with care: true runs again whenever the care part of a plant's page
           redraws (loadCarePlant). An add is replaced, never doubled: an element with its id is removed first. anchor is a
           selector (or a function of the main element) and where is an insertAdjacentHTML position, or 'inside' to fill a
           box the page left for it (a .fd-box, say). A failed load leaves the add out unless failed() gives something to show.
   care:   { turn: 'Turned the pot' }  words for care log kinds (CARE_WORD), also offered in Log other care.

   Everything here is plain data and functions; nothing runs until the page it belongs to draws. */
'use strict';

const FEAT = { pages: {}, today: [], adds: [], names: [] };
function addFeature(f) {
  if (f.name) FEAT.names.push(f.name);
  if (f.care) Object.assign(CARE_WORD, f.care);
  if (f.pages) for (const [key, p] of Object.entries(f.pages)) {
    FEAT.pages[key] = p;
    if (p.section && p.label) {                                   // join the top bar once, after the page named (or at the end)
      const sec = SECTIONS.find(s => s[0] === p.section);
      if (sec && !sec[2].some(x => x[0] === key)) {
        const i = p.after ? sec[2].findIndex(x => x[0] === p.after) : -1;
        sec[2].splice(i < 0 ? sec[2].length : i + 1, 0, [key, p.label, p.href || '#/' + key]);
      }
    }
  }
  if (f.today) FEAT.today.push(...[].concat(f.today));
  if (f.adds) FEAT.adds.push(...[].concat(f.adds));
}
// the Today page: load every registered block's data (alongside the page's own), then the blocks that have something to show
async function featTodayLoad() {
  return (await Promise.all(FEAT.today.map(async b => { try { return { b, d: await b.load() }; } catch (e) { return { b, d: null }; } }))).filter(x => x.d != null);
}
// additions to the page that is on screen. parts = the route's parts; care = only the adds that follow the care part
const ADDS_RUN = { page: 0, care: 0 };              // a newer run of the same kind cancels an older one still loading
async function featAdds(parts, care) {
  const main = document.getElementById('app'); if (!main) return;
  const kind = care ? 'care' : 'page', my = ++ADDS_RUN[kind], path = location.hash;
  const todo = FEAT.adds.filter(a => (!care || a.care) && (!a.match || a.match(parts, path)));
  await Promise.all(todo.map(async a => {
    const at = typeof a.anchor === 'function' ? a.anchor(main) : main.querySelector(a.anchor); if (!at) return;   // the page has no place for it
    let d = null;
    try { d = a.load ? await a.load(parts, at) : {}; } catch (e) { d = a.failed ? a.failed(e) : null; }           // offline, or the feature's data is missing: leave it out
    if (d == null || my !== ADDS_RUN[kind] || location.hash !== path || !at.isConnected) return;
    const old = a.id && document.getElementById(a.id); if (old && old !== at) old.remove();
    const h = a.html(d, parts, at); if (!h) return;
    if (a.where === 'inside') at.innerHTML = rend(h); else at.insertAdjacentHTML(a.where || 'afterend', rend(h));   // 'inside' fills a box the page left for it
    if (a.then) a.then(a.id ? document.getElementById(a.id) : at, d);
  }));
  if (my === ADDS_RUN[kind] && todo.length && !care) { buildSideNav(); addFoldButtons(); navLayout(); addReadButtons(); }   // a new section joins Navigation with Show or hide
}
