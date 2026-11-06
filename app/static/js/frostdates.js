/* Plant record front end: frost dates (prototype, proto/frost-dates). One of the files loaded in order by index.html; they share one scope.
   Plain JavaScript, no inline handlers (the server's content policy forbids them). Read only: nothing here changes data.
   The Weather page and the Cold-night checklist each carry a placeholder <div class="fd-box" data-fd="weather|frost">;
   a MutationObserver on #app fills it from GET /api/frost/dates when the page draws. */
'use strict';

const fdDate = (d, year) => new Date(d + 'T12:00:00').toLocaleDateString([], year ? { month: 'short', day: 'numeric', year: 'numeric' } : { month: 'short', day: 'numeric' });
const fdPlural = (n, one, many) => `${n} ${n === 1 ? one : many || one + 's'}`;
const fdNeed = D => html`<p class="muted">Frost dates appear after ${D.need} whole winters (July to June) of weather history here${D.winters ? ` (${D.winters} so far)` : ''}. Load history on the Weather page fills them in.</p>`;

// this winter so far, as a sentence
function fdNow(D) {
  const N = D.now || {};
  if (!N.nights) return '';
  const first = N.first_freeze, cold = N.coldest;
  let s = first ? html`<strong>This winter's first freeze was ${fdDate(first.date)}</strong> (${first.low}°F)${N.freezes > 1 ? `, with ${fdPlural(N.freezes, 'freezing night')} so far` : ''}.`
    : html`<strong>No freeze yet this winter.</strong>${cold ? ` The coldest night so far was ${cold.low}°F on ${fdDate(cold.date)}.` : ''}`;
  if (!first && D.days_to_usual != null) s = html`${s} ${D.days_to_usual > 0 ? `The usual first freeze is ${fdPlural(D.days_to_usual, 'day')} away.` : D.days_to_usual === 0 ? 'Today is the usual date of the first freeze.' : `The usual date of the first freeze was ${fdPlural(-D.days_to_usual, 'day')} ago, so one could come any night.`}`;
  return html`<p class="notice ${first ? '' : 'ok'} fd-now" role="status">${s}</p>`;
}

function fdWeather(D) {
  if (!D.ready) return html`${fdNow(D)}${fdNeed(D)}`;
  const F = D.freeze, H = D.hard;
  const pair = (S, word) => !S.first ? html`<p>None of the last ${S.winters} winters had a ${word}.</p>`
    : html`<dl class="fd-dl"><div><dt>Usual first ${word}</dt><dd><strong>${S.first.usual}</strong> <span class="hint">earliest ${S.first.earliest}, latest ${S.first.latest}</span></dd></div>
        <div><dt>Usual last ${word}</dt><dd><strong>${S.last.usual}</strong> <span class="hint">earliest ${S.last.earliest}, latest ${S.last.latest}</span></dd></div></dl>
        ${S.none ? html`<p class="hint">${fdPlural(S.none, 'winter')} of ${S.winters} had no ${word} at all, so the dates are from the other ${S.had}.</p>` : ''}`;
  return html`${fdNow(D)}
    <h3>Freeze: 32°F or colder</h3>${pair(F, 'freeze')}
    ${D.frost_free_days ? html`<p>That leaves about <strong>${D.frost_free_days} days without a freeze</strong> from the last one in spring to the first one in the fall.</p>` : ''}
    <h3>Hard freeze: 28°F or colder</h3>${pair(H, 'hard freeze')}
    <p class="hint">"Usual" is the middle date of the last ${D.winters} winters (since ${D.since}). Plan for the earliest date, not the usual one: half of all winters freeze before the usual date. A low spot in the garden, or a clear and still night, can be a few degrees colder than the weather station.</p>
    <div class="tbl-wrap"><table class="tbl fd-tbl"><caption class="sr">Freezes each winter in ${D.place}</caption>
      <thead><tr><th scope="col">Winter</th><th scope="col">First freeze</th><th scope="col">Last freeze</th><th scope="col" class="num">Freezing nights</th><th scope="col" class="num">Hard freezes</th><th scope="col">Coldest night</th></tr></thead>
      <tbody>${D.per_winter.map(w => html`<tr><th scope="row">${w.winter}</th><td>${w.first ? fdDate(w.first) : 'None'}</td><td>${w.last ? fdDate(w.last) : 'None'}</td>
        <td class="num">${w.freezes}</td><td class="num">${w.hard}</td><td>${w.coldest}°F on ${fdDate(w.coldest_on, true)}</td></tr>`)}</tbody></table></div>
    <p><a class="btn small ghost" href="#/frost?sec=fz-dates">When each of your plants outside usually meets its first damaging night</a></p>`;
}

function fdPlants(D) {
  if (!D.ready) return fdNeed(D);
  if (!D.plants.length) return html`<p class="muted">None of your plants outside has a "damage below" temperature, so there is nothing to work out.</p>`;
  const when = g => g.this_winter ? html`<strong>Already this winter</strong>: ${g.this_winter.low}°F on ${fdDate(g.this_winter.date)}.`
    : !g.first ? html`<strong>Not in any of the last ${g.winters} winters.</strong>`
    : g.most_none ? html`<strong>Only ${g.had} of the last ${g.winters} winters</strong> got that cold (the first time around ${g.first.usual}).`
    : html`<strong>Usually from about ${g.first.usual}</strong> (earliest ${g.first.earliest}, latest ${g.first.latest}${g.had < g.winters ? `; ${g.winters - g.had} of ${g.winters} winters never got that cold` : ''}).`;
  return html`<p class="muted">Your plants outside, grouped by the temperature that damages them, earliest first: the date their first damaging night usually comes, from the last ${D.winters} winters in ${D.place}.</p>
    <ul class="fd-groups">${D.plants.map(g => html`<li class="fd-g"><h3 class="fd-h">Damaged below ${g.below}°F <span class="muted">(${fdPlural(g.plants.length, 'plant')})</span></h3>
      <p>${when(g)}</p>
      <p class="fd-names">${g.plants.map((p, i) => html`${i ? ', ' : ''}<a href="#/plant/${enc(p.code)}">${p.name}</a> <span class="muted">${p.code}${p.plan === 'Move indoors' ? ', moves indoors' : ''}</span>`)}</p></li>`)}</ul>`;
}

async function fdFill(box) {
  box.dataset.fdDone = '1';
  try {
    const D = await api('GET', '/api/frost/dates?x=1' + (box.dataset.fd === 'weather' ? locQS() : ''));
    box.innerHTML = rend(box.dataset.fd === 'weather' ? fdWeather(D) : fdPlants(D));
    if (typeof fitTables === 'function') fitTables();
  } catch (e) { box.innerHTML = rend(html`<p class="muted">Frost dates could not be worked out: ${e.message}</p>`); }
}
(function frostDatesFill() {
  const main = document.getElementById('app'); if (!main) return;
  new MutationObserver(() => { for (const b of main.querySelectorAll('.fd-box[data-fd]:not([data-fd-done])')) fdFill(b); })
    .observe(main, { childList: true, subtree: true });
})();
