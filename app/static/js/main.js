/* Plant record front end: care cards, and the start-up: the first route() and the listeners. One of the files app.js was split into in 1.32.0; they load in order (index.html) and share one scope,
   so a function here may call any other. Plain JavaScript, no inline handlers (the server's content policy forbids them). */
'use strict';

// ---------- links to the large-print care cards (card.html) and the plant-sitter sheet (sitter.html) ----------
// 1.46.0: registered (features.js) instead of watching the page for changes. A plant's page gets its care-card link in the row of
// actions under its name; a group's page gets both links in its row of buttons; Today gets the sitter link under the summary.
const careCardA = (href, label) => html`<a class="btn ghost pc-link" href="${href}" title="Water, light and temperature needs in big type, to print and keep beside the plants">${label}</a>`;
addFeature({
  name: 'cards',
  adds: [
    { id: 'pc-link-plant', match: parts => parts[0] === 'plant' && !!parts[1] && parts[2] !== 'edit',
      anchor: main => main.querySelector('#details .row.acts') || main.querySelector('.row.acts'), where: 'beforeend',
      html: (d, parts) => html`<span id="pc-link-plant">${careCardA('/card.html?plant=' + parts[1], 'Large-print care card')}</span>` },
    { id: 'pc-link-group', match: parts => parts[0] === 'group' && !!parts[1],
      anchor: main => main.querySelector('#g-plants li.job') && main.querySelector('h1 ~ .row.noprint'),
      where: 'beforeend', html: (d, parts) => html`<span id="pc-link-group">${careCardA('/card.html?group=' + parts[1], 'Large-print care cards')}</span>`,
      then: el => { const row = el.parentElement, end = row.querySelector('[data-act=archive],[data-act=grpdel]'); if (end) row.insertBefore(el, end); } },   // before Archive / Remove this group
    { id: 'ps-link', match: parts => parts[0] === 'group' && !!parts[1],
      anchor: main => main.querySelector('#g-plants li.job') && main.querySelector('h1 ~ .row.noprint'), where: 'afterend',
      html: (d, parts) => html`<p class="ps-link noprint" id="ps-link"><a class="btn ghost" href="/sitter.html#group=${parts[1]}">Plant-sitter sheet for this group</a></p>` },
  ],
  today: { id: 'ps-link', order: 6, load: async () => ({}),
    html: () => html`<p class="ps-link noprint" id="ps-link"><a class="btn ghost" href="/sitter.html">Going away? Make a plant-sitter sheet</a></p>` },
});

route();
offStart();
wxPoll();                      // shows the progress box on every page while a history load runs
// 1.29.0: settings that follow you. If another device changed them, this tab starts again once with them (at most once a visit)
if (window.PlantSync && navigator.onLine) window.PlantSync.load().then(changed => {
  let again = false; try { again = sessionStorage.getItem('plantdb.synced') === '1'; sessionStorage.setItem('plantdb.synced', '1'); } catch (e) { again = true; }
  if (changed && !again && !document.querySelector('main form[data-form] input:focus, dialog[open]')) location.reload();
});
