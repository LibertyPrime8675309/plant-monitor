/* Plant record front end: pests that eat plants (prototype proto/browse-risk; plantdb/browse.py). One of the files loaded in order
   by index.html (js/manifest.json); they share one scope. Plain JavaScript, no inline handlers.
   - The page #/browse (not a link in the top bar, which would wrap; each plant's page links to it and Search finds it): every plant
     here sorted by how likely rabbits, rats, mice and deer are to eat it, with the reason in words, then what to do about it.
   - A plant's own page gets a line with its risk and the reason. The risk is always written out, never carried by colour alone. */
'use strict';

const BR_ORDER = ['High', 'Moderate', 'Low', 'Unknown'];
const BR_HEAD = { High: 'Most likely to be eaten', Moderate: 'Some risk', Low: 'Usually left alone', Unknown: 'Not known yet' };
const BR_ICON = { High: '▲ ', Moderate: '◆ ', Low: '● ', Unknown: '? ' };       // a shape as well as words
const brRow = p => jobRow({ code: p.code, common_name: p.name, photo: p.photo }, html`<strong>${BR_ICON[p.risk]}${p.word}.</strong> ${p.why}`, '');

async function viewBrowse() {
  const B = await api('GET', '/api/browse');
  const by = k => B.plants.filter(p => p.risk === k);
  const C = B.counts;
  return {
    title: 'Pests that eat plants',
    html: html`<h1>Pests that eat plants</h1>
    <p class="muted">Rabbits, rats, mice and deer choose plants that are soft, tasty and have no defence. This sorts your plants by that, from the kind of plant. It is gardeners' and extension-service knowledge, not a test on your garden: a hungry animal eats almost anything, and a plant that is "usually left alone" is not safe if nothing else is on offer.</p>
    <div class="verdict-box" role="status"><p><strong>${C.High} most likely to be eaten, ${C.Moderate} with some risk, ${C.Low} usually left alone${C.Unknown ? `, ${C.Unknown} not known yet` : ''}.</strong></p></div>
    ${BR_ORDER.map(k => by(k).length ? html`<section class="blk" id="br-${k.toLowerCase()}"><h2>${BR_HEAD[k]} (${by(k).length})</h2><ul class="jobs">${by(k).map(brRow)}</ul></section>` : '')}
    <section class="blk" id="br-plan"><h2>What to do</h2>
      <ul class="rp-list">
        <li>Put the high-risk plants in the middle of a group of pots and ring them with plants that are usually left alone (aroids, aloes, crown of thorns).</li>
        <li>Cover the high-risk plants that matter most with a wire cloche or a frame of hardware cloth (small mesh, about half an inch). Rats and mice climb, so a cover with a closed top works better than a low fence.</li>
        <li>Raise pots off the ground on a stand, and keep cactus bases clear of soil, where mice gnaw.</li>
        <li>Look for droppings and chew marks to see who it is: rabbit droppings are round pellets and cuts are clean at an angle; rodents leave small gnawed edges and smaller droppings.</li>
        <li>Plants animals dislike for their smell, such as lavender, rosemary, sage, thyme, marigolds, chives and potted mint, help a little next to the plants you want to protect. They are not a fence.</li></ul></section>`,
  };
}
addFeature({
  name: 'browse',
  // No link in the top bar (the row would wrap); each plant's page links to it and Search finds it.
  pages: { browse: { view: viewBrowse, nav: 'plants', label: 'Pests that eat plants', href: '#/browse' } },
  adds: {
    id: 'br-plant',
    match: parts => parts[0] === 'plant' && parts[1] && parts[2] !== 'edit',
    anchor: main => { const b = main.querySelector('.quick-btns'); return b && b.parentElement; }, where: 'beforeend',
    load: async parts => {
      if (!CUR || CUR.p.code !== parts[1]) return null;
      const B = await api('GET', '/api/browse?plant=' + enc(parts[1]));
      return B.plants[0] || null;
    },
    html: p => html`<p class="hint br-plant" id="br-plant">Eaten by pests: <strong>${BR_ICON[p.risk]}${p.word}.</strong> ${p.why} <a href="#/browse">All plants by pest risk</a></p>`,
  },
});
