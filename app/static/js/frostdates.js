/* Plant record front end: frost dates (prototype, proto/frost-dates). One of the files loaded in order by index.html; they share one scope.
   Plain JavaScript, no inline handlers (the server's content policy forbids them). Read only: nothing here changes data.
   The Weather page, the Cold-night checklist and Back outside each carry a placeholder <div class="fd-box" data-fd="weather|frost|outside">;
   a MutationObserver on #app fills it from GET /api/frost/dates when the page draws, and adds a line to Today in October and November
   (the usual first freeze) and in February and March (the usual last freeze).
   Ethan's answers of November 6: a "frost possible" line at 36°F; one plant a line with its photo on the checklist; the same numbers
   on Back outside; the line on Today. */
'use strict';

const fdDate = (d, year) => new Date(d + 'T12:00:00').toLocaleDateString([], year ? { month: 'short', day: 'numeric', year: 'numeric' } : { month: 'short', day: 'numeric' });
const fdPlural = (n, one, many) => `${n} ${n === 1 ? one : many || one + 's'}`;
const fdNeed = D => html`<p class="muted">Frost dates appear after ${D.need} whole winters (July to June) of weather history here${D.winters ? ` (${D.winters} so far)` : ''}. Load history on the Weather page fills them in.</p>`;
const fdAway = (n, what) => n > 0 ? `${what} is ${fdPlural(n, 'day')} away` : n === 0 ? `${what} is today` : `${what} was ${fdPlural(-n, 'day')} ago`;
const FD_POSSIBLE_WHY = 'At 36°F at the weather station, frost can still form on a clear, still night, in low spots and on leaves out in the open.';

// this winter so far, as a sentence
function fdNow(D) {
  const N = D.now || {};
  if (!N.nights) return '';
  const first = N.first_freeze, cold = N.coldest, maybe = N.first_possible;
  let s = first ? html`<strong>This winter's first freeze was ${fdDate(first.date)}</strong> (${first.low}°F)${N.freezes > 1 ? `, with ${fdPlural(N.freezes, 'freezing night')} so far` : ''}.`
    : html`<strong>No freeze yet this winter.</strong>${maybe ? ` Frost was possible on ${fdDate(maybe.date)} (${maybe.low}°F)${N.possibles > 1 ? `, and on ${fdPlural(N.possibles - 1, 'other night')}` : ''}.` : cold ? ` The coldest night so far was ${cold.low}°F on ${fdDate(cold.date)}.` : ''}`;
  if (!first && D.days_to_usual != null) s = html`${s} ${D.days_to_usual > 0 ? `The usual first freeze is ${fdPlural(D.days_to_usual, 'day')} away.` : D.days_to_usual === 0 ? 'Today is the usual date of the first freeze.' : `The usual date of the first freeze was ${fdPlural(-D.days_to_usual, 'day')} ago, so one could come any night.`}`;
  return html`<p class="notice ${first ? '' : 'ok'} fd-now" role="status">${s}</p>`;
}

const fdPair = (S, word) => !S.first ? html`<p>None of the last ${S.winters} winters had a ${word}.</p>`
  : html`<dl class="fd-dl"><div><dt>Usual first ${word}</dt><dd><strong>${S.first.usual}</strong> <span class="hint">earliest ${S.first.earliest}, latest ${S.first.latest}</span></dd></div>
      <div><dt>Usual last ${word}</dt><dd><strong>${S.last.usual}</strong> <span class="hint">earliest ${S.last.earliest}, latest ${S.last.latest}</span></dd></div></dl>
      ${S.none ? html`<p class="hint">${fdPlural(S.none, 'winter')} of ${S.winters} had no ${word} at all, so the dates are from the other ${S.had}.</p>` : ''}`;

function fdWeather(D) {
  if (!D.ready) return html`${fdNow(D)}${fdNeed(D)}`;
  const F = D.freeze, H = D.hard, P = D.possible;
  return html`${fdNow(D)}
    <h3>Frost possible: 36°F or colder</h3>${fdPair(P, 'night of 36°F or colder')}<p class="hint">${FD_POSSIBLE_WHY}</p>
    <h3>Freeze: 32°F or colder</h3>${fdPair(F, 'freeze')}
    ${D.frost_free_days ? html`<p>That leaves about <strong>${D.frost_free_days} days without a freeze</strong> from the last one in spring to the first one in the fall.</p>` : ''}
    <h3>Hard freeze: 28°F or colder</h3>${fdPair(H, 'hard freeze')}
    <p class="hint">"Usual" is the middle date of the last ${D.winters} winters (since ${D.since}). Plan for the earliest date, not the usual one: half of all winters freeze before the usual date. A low spot in the garden, or a clear and still night, can be a few degrees colder than the weather station.</p>
    <div class="tbl-wrap"><table class="tbl fd-tbl"><caption class="sr">Cold nights each winter in ${D.place}</caption>
      <thead><tr><th scope="col">Winter</th><th scope="col">First night of 36°F or colder</th><th scope="col">First freeze</th><th scope="col">Last freeze</th><th scope="col" class="num">Freezing nights</th><th scope="col" class="num">Hard freezes</th><th scope="col">Coldest night</th></tr></thead>
      <tbody>${D.per_winter.map(w => html`<tr><th scope="row">${w.winter}</th><td>${w.first_possible ? fdDate(w.first_possible) : 'None'}</td><td>${w.first ? fdDate(w.first) : 'None'}</td><td>${w.last ? fdDate(w.last) : 'None'}</td>
        <td class="num">${w.freezes}</td><td class="num">${w.hard}</td><td>${w.coldest}°F on ${fdDate(w.coldest_on, true)}</td></tr>`)}</tbody></table></div>
    <p class="row"><a class="btn small ghost" href="#/frost?sec=fz-dates">When each of your plants outside usually meets its first damaging night</a>
      <a class="btn small ghost" href="#/outside?sec=bo-frostdates">When the cold nights usually end (Back outside)</a></p>`;
}

// the Cold-night checklist: one plant a line, with its photo (Ethan, November 6); a long group shows 5 and folds the rest
const FD_SHOW = 5;
const fdPlantLi = p => html`<li class="fd-p">${p.photo ? html`<img src="${thumbUrl(p.photo)}" alt="" loading="lazy" width="48" height="48">` : html`<span class="fd-nophoto" aria-hidden="true"></span>`}
  <span class="fd-pt"><a class="nm" href="#/plant/${enc(p.code)}">${p.name}</a><span class="muted">${p.code}${p.plan === 'Move indoors' ? ', moves indoors' : ''}${p.site && p.site !== 'Outdoors' ? `, ${p.site.toLowerCase()}` : ''}</span></span></li>`;
function fdPlants(D) {
  if (!D.ready) return fdNeed(D);
  if (!D.plants.length) return html`<p class="muted">None of your plants outside has a "damage below" temperature, so there is nothing to work out.</p>`;
  const when = g => g.this_winter ? html`<strong>Already this winter</strong>: ${g.this_winter.low}°F on ${fdDate(g.this_winter.date)}.`
    : !g.first ? html`<strong>Not in any of the last ${g.winters} winters.</strong>`
    : g.most_none ? html`<strong>Only ${g.had} of the last ${g.winters} winters</strong> got that cold (the first time around ${g.first.usual}).`
    : html`<strong>Usually from about ${g.first.usual}</strong> (earliest ${g.first.earliest}, latest ${g.first.latest}${g.had < g.winters ? `; ${g.winters - g.had} of ${g.winters} winters never got that cold` : ''}).`;
  const list = g => g.plants.length <= FD_SHOW + 1 ? html`<ul class="fd-plants">${g.plants.map(fdPlantLi)}</ul>`
    : html`<ul class="fd-plants">${g.plants.slice(0, FD_SHOW).map(fdPlantLi)}</ul>
      <details class="fd-more"><summary>Show the other ${fdPlural(g.plants.length - FD_SHOW, 'plant')} damaged below ${g.below}°F</summary><ul class="fd-plants">${g.plants.slice(FD_SHOW).map(fdPlantLi)}</ul></details>`;
  return html`<p class="muted">Your plants outside, grouped by the temperature that damages them, earliest first: the date their first damaging night usually comes, from the last ${D.winters} winters in ${D.place}.</p>
    <ul class="fd-groups">${D.plants.map(g => html`<li class="fd-g"><h3 class="fd-h">Damaged below ${g.below}°F <span class="muted">(${fdPlural(g.plants.length, 'plant')})</span></h3>
      <p>${when(g)}</p>${list(g)}</li>`)}</ul>`;
}

// Back outside: when the cold nights usually end, with days to go in spring (Ethan, November 6)
function fdOutside(D) {
  if (!D.ready) return fdNeed(D);
  const L = D.days_to_last || {}, F = D.freeze, H = D.hard, P = D.possible, N = D.now || {}, spring = D.month >= 1 && D.month <= 6;
  const row = (S, word, k) => !S.last ? html`<div><dt>Last ${word}</dt><dd>None in the last ${S.winters} winters.</dd></div>`
    : html`<div><dt>Usual last ${word}</dt><dd><strong>${S.last.usual}</strong>${spring && L[k] != null ? html` <span class="fd-away">(${L[k] > 0 ? `in ${fdPlural(L[k], 'day')}` : L[k] === 0 ? 'today' : `${fdPlural(-L[k], 'day')} ago`})</span>` : ''}
        <span class="hint">earliest ${S.last.earliest}, latest ${S.last.latest}</span></dd></div>`;
  const lead = !F.last ? '' : spring ? html`<strong>${fdAway(L.freeze, `The usual last freeze (${F.last.usual})`)}.</strong>${L.freeze <= 0 && F.last.latest ? ` A late one can still come: the latest in the last ${D.winters} winters was ${F.last.latest}.` : ''}`
    : html`<strong>The usual last freeze in spring is ${F.last.usual}</strong> (the latest in the last ${D.winters} winters was ${F.last.latest}).`;
  return html`${lead ? html`<p class="notice ${spring && L.freeze <= 0 ? 'ok' : ''} fd-now" role="status">${lead}${N.last_freeze ? ` This winter's latest freeze so far was ${fdDate(N.last_freeze.date)} (${N.last_freeze.low}°F).` : ''}</p>` : ''}
    <dl class="fd-dl">${row(H, 'hard freeze (28°F)', 'hard')}${row(F, 'freeze (32°F)', 'freeze')}${row(P, 'night of 36°F or colder', 'possible')}</dl>
    <p class="hint">From the last ${D.winters} winters in ${D.place}. Plan by the latest date, not the usual one, for plants that are damaged near freezing: half of all springs have a freeze after the usual date. ${FD_POSSIBLE_WHY} Each plant above is still checked against the 7-day forecast.</p>
    <p><a class="btn small ghost" href="#/weather?sec=wx-frostdates">All the frost dates (Weather page)</a></p>`;
}

async function fdFill(box) {
  box.dataset.fdDone = '1';
  try {
    const D = await api('GET', '/api/frost/dates?x=1' + (box.dataset.fd === 'weather' ? locQS() : ''));
    box.innerHTML = rend(box.dataset.fd === 'weather' ? fdWeather(D) : box.dataset.fd === 'outside' ? fdOutside(D) : fdPlants(D));
    if (typeof fitTables === 'function') fitTables();
  } catch (e) { box.innerHTML = rend(html`<p class="muted">Frost dates could not be worked out: ${e.message}</p>`); }
}

// Today: a line in October and November while no freeze has come yet, and in February and March up to three weeks after the usual
// last freeze. Only with enough history (3 whole winters). Added when the page draws, after the summary at the top.
function fdTodayLine(D) {
  if (!D.ready || !D.freeze || !D.freeze.first) return '';
  const N = D.now || {}, F = D.freeze, L = D.days_to_last || {};
  if ((D.month === 10 || D.month === 11) && !N.first_freeze && D.days_to_usual != null)
    return html`<strong>No freeze yet.</strong> ${D.days_to_usual > 0 ? `The usual first freeze is ${fdPlural(D.days_to_usual, 'day')} away (${F.first.usual}).` : D.days_to_usual === 0 ? `Today (${F.first.usual}) is the usual date of the first freeze.` : `The usual first freeze (${F.first.usual}) was ${fdPlural(-D.days_to_usual, 'day')} ago, so one could come any night.`}
      <a href="#/weather?sec=wx-frostdates">Frost dates</a>`;
  if ((D.month === 2 || D.month === 3) && F.last && L.freeze != null && L.freeze >= -21)
    return html`<strong>${fdAway(L.freeze, `The usual last freeze (${F.last.usual})`)}.</strong> ${L.freeze > 0 ? 'Plants that came inside stay in until the nights are warm enough for each one.' : `A late one can still come (the latest was ${F.last.latest}).`}
      <a href="#/outside?sec=bo-frostdates">Back outside</a>`;
  return '';
}
// the summary's jump buttons (.td-jumps) are only on Today; marking them means each drawing of the page asks once
function fdToday(main) {
  const top = main.querySelector('.td-jumps:not([data-fd-asked])'); if (!top) return;
  top.dataset.fdAsked = '1';
  api('GET', '/api/frost/dates?x=1' + locQS()).then(D => {
    if (!top.isConnected || main.querySelector('.fd-today')) return;
    const line = fdTodayLine(D); if (!line) return;
    const p = document.createElement('p'); p.className = 'notice ok fd-today';
    p.innerHTML = rend(line);
    (top.closest('.verdict-box') || top).after(p);
  }).catch(() => {});
}
(function frostDatesFill() {
  const main = document.getElementById('app'); if (!main) return;
  new MutationObserver(() => { for (const b of main.querySelectorAll('.fd-box[data-fd]:not([data-fd-done])')) fdFill(b); fdToday(main); })
    .observe(main, { childList: true, subtree: true });
})();
