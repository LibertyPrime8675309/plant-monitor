/* Plant record front end: care cards, and the start-up: the first route() and the listeners. One of the files app.js was split into in 1.32.0; they load in order (index.html) and share one scope,
   so a function here may call any other. Plain JavaScript, no inline handlers (the server's content policy forbids them). */
'use strict';

// ---------- prototype proto/care-card: links to the large-print care cards (card.html), added when a plant or group page draws ----------
(function careCardLinks() {
  const main = document.getElementById('app'); if (!main) return;
  const add = () => {
    const h = location.hash;
    let m = h.match(/^#\/plant\/([^/]+)$/), row, href, label;
    if (m) { row = main.querySelector('#details .row.acts') || main.querySelector('.row.acts'); href = '/card.html?plant=' + m[1]; label = 'Large-print care card'; }
    else if ((m = h.match(/^#\/group\/(\d+)$/)) && main.querySelector('#g-plants li.job')) { row = main.querySelector('h1 ~ .row.noprint'); href = '/card.html?group=' + m[1]; label = 'Large-print care cards'; }
    if (!row || row.querySelector('.pc-link')) return;
    const a = document.createElement('a');
    a.className = 'btn ghost pc-link'; a.href = href; a.textContent = label;
    a.title = 'Water, light and temperature needs in big type, to print and keep beside the plants';
    row.insertBefore(a, row.querySelector('[data-act=archive],[data-act=grpdel]'));   // before Archive / Remove this group, or at the end
  };
  new MutationObserver(add).observe(main, { childList: true, subtree: true });
})();

route();
offStart();
wxPoll();                      // shows the progress box on every page while a history load runs
// 1.29.0: settings that follow you. If another device changed them, this tab starts again once with them (at most once a visit)
if (window.PlantSync && navigator.onLine) window.PlantSync.load().then(changed => {
  let again = false; try { again = sessionStorage.getItem('plantdb.synced') === '1'; sessionStorage.setItem('plantdb.synced', '1'); } catch (e) { again = true; }
  if (changed && !again && !document.querySelector('main form[data-form] input:focus, dialog[open]')) location.reload();
});
