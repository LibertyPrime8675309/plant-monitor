/* Display settings, applied before the page paints. Stored in this browser only. */
(function () {
  var D = { size: '115', space: 'normal', contrast: 'normal', layout: 'split', theme: 'auto', navside: 'left', navopen: '1', width: 'normal',
            readbtns: '1', rate: '1', voice: 'auto', keys: '1',   // 1.8.0: read aloud, reading speed and voice, keyboard shortcuts
            swipe: '1',                                           // 1.14.1: swipe between plants
            photofit: 'auto' };                                   // 1.21.0: Plants page photos: auto (wide ones whole), fill, whole
  var p = {};
  try { p = JSON.parse(localStorage.getItem('plantdb.display') || '{}') || {}; } catch (e) { p = {}; }
  var r = document.documentElement;
  function apply(v) {
    var x = {}; for (var k in D) x[k] = (v && v[k]) || D[k];
    r.setAttribute('data-size', x.size);
    r.setAttribute('data-space', x.space);
    r.setAttribute('data-contrast', x.contrast);
    r.setAttribute('data-layout', x.layout);
    r.setAttribute('data-navside', x.navside);
    r.setAttribute('data-navpref', x.navopen);
    r.setAttribute('data-width', x.width);
    r.setAttribute('data-readbtns', x.readbtns);
    r.setAttribute('data-photofit', x.photofit);
    if (x.theme === 'auto') r.removeAttribute('data-theme'); else r.setAttribute('data-theme', x.theme);
    var rem = parseFloat(getComputedStyle(r).fontSize) || 16;
    r.setAttribute('data-narrow', (window.innerWidth / rem) < 58 ? '1' : '0');
  }
  window.PlantPrefs = {
    defaults: D,
    get: function () { var x = {}; for (var k in D) x[k] = p[k] || D[k]; return x; },
    set: function (k, v) { p[k] = v; try { localStorage.setItem('plantdb.display', JSON.stringify(p)); } catch (e) { /* storage blocked: applies for this visit only */ } apply(p); document.dispatchEvent(new Event('prefs')); },
    reset: function () { p = {}; try { localStorage.removeItem('plantdb.display'); } catch (e) { } apply(p); document.dispatchEvent(new Event('prefs')); },
    relayout: function () { apply(p); }
  };
  apply(p);
  window.addEventListener('resize', function () { apply(p); });
})();
