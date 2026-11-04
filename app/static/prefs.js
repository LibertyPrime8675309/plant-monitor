/* Display settings, applied before the page paints. Stored in this browser only. */
(function () {
  var D = { size: '115', space: 'normal', contrast: 'normal', layout: 'split', theme: 'auto', navside: 'left', navopen: '1', width: 'normal',
            readbtns: '1', rate: '1', voice: 'auto', keys: '1',   // 1.8.0: read aloud, reading speed and voice, keyboard shortcuts
            swipe: '1',                                           // 1.14.1: swipe between plants
            photofit: 'auto',                                     // 1.21.0: Plants page photos: auto (wide ones whole), fill, whole
            lines: 'full' };                                      // 1.26.0: line length: full (use the width) or short (about 70 characters)
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
    r.setAttribute('data-lines', x.lines);
    if (x.theme === 'auto') r.removeAttribute('data-theme'); else r.setAttribute('data-theme', x.theme);
    var rem = parseFloat(getComputedStyle(r).fontSize) || 16;
    r.setAttribute('data-narrow', (window.innerWidth / rem) < 58 ? '1' : '0');
    if (r.getAttribute('data-touch') !== '1')    // 1.26.0: a phone or tablet with no mouse or keyboard (once seen, kept for the visit)
      r.setAttribute('data-touch', window.matchMedia && matchMedia('(hover: none) and (pointer: coarse)').matches ? '1' : '0');
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
/* 1.29.0: settings that follow you. The keys below are saved on the server for your sign-in (the owner's on this computer) as well
   as in this browser, so any device you sign in on picks them up. Display settings stay on this device unless you tick "Use these on
   every device I sign in on" for a part of them in Display; the device name and the offline copy never leave the device. */
(function () {
  var KEYS = ['plantdb.filters', 'plantdb.library', 'plantdb.fungi', 'plantdb.ltlights', 'plantdb.auditf', 'plantdb.calview', 'plantdb.wxchart',
              'plantdb.wxhide', 'plantdb.wxper', 'plantdb.idscope', 'plantdb.place', 'plantdb.frosthide', 'plantdb.shopping'];   // 1.30.0: Shopping's home and kind
  var PARTS = { text: ['size', 'space', 'contrast', 'theme'], layout: ['width', 'lines', 'layout', 'navside', 'navopen'], read: ['readbtns', 'rate', 'voice'],
                photos: ['photofit', 'swipe'], keys: ['keys'] };
  var LS = window.localStorage, setI = Storage.prototype.setItem, remI = Storage.prototype.removeItem, queue = {}, timer = 0, applying = false;
  function shared() { try { return JSON.parse(LS.getItem('plantdb.dshare') || '{}') || {}; } catch (e) { return {}; } }
  function send() {
    var body = queue; queue = {}; timer = 0;
    if (!Object.keys(body).length) return;
    var h = { 'Content-Type': 'application/json' };
    try { var n = LS.getItem('plantdb.editor'); if (n) h['X-Editor'] = n; } catch (e) { /* none */ }
    fetch('/api/me/prefs', { method: 'PUT', headers: h, body: JSON.stringify(body), credentials: 'same-origin' }).catch(function () { for (var k in body) if (!(k in queue)) queue[k] = body[k]; });
  }
  function push(k, v) { queue[k] = v; clearTimeout(timer); timer = setTimeout(send, 800); }
  function displayParts(raw) {      // the shared parts of the Display settings
    var p = {}; try { p = JSON.parse(raw || '{}') || {}; } catch (e) { p = {}; }
    var sh = shared();
    for (var part in PARTS) if (sh[part]) { var x = {}; PARTS[part].forEach(function (k) { if (p[k] != null) x[k] = p[k]; }); push('display.' + part, JSON.stringify(x)); }
  }
  Storage.prototype.setItem = function (k, v) {
    setI.call(this, k, v);
    if (this !== LS || applying) return;
    if (KEYS.indexOf(k) >= 0) push(k.slice(8), v);
    else if (k === 'plantdb.display') displayParts(v);
  };
  Storage.prototype.removeItem = function (k) {
    remI.call(this, k);
    if (this === LS && !applying && KEYS.indexOf(k) >= 0) push(k.slice(8), null);
  };
  window.PlantSync = {
    parts: PARTS,
    shared: shared,
    share: function (part, on) {     // a part of Display: on every device (on) or this device only
      var sh = shared(); if (on) sh[part] = true; else delete sh[part];
      setI.call(LS, 'plantdb.dshare', JSON.stringify(sh));
      if (!on) return Promise.resolve(false);
      // ticked here after another device: take the ones already shared; the first device to tick it shares its own
      return fetch('/api/me/prefs', { credentials: 'same-origin' }).then(function (r) { return r.ok ? r.json() : { prefs: {} }; }).then(function (d) {
        var v = (d.prefs || {})['display.' + part];
        if (v) { var x = {}; try { x = JSON.parse(v) || {}; } catch (e) { x = {}; } applying = true; try { for (var k in x) window.PlantPrefs.set(k, x[k]); } finally { applying = false; } return true; }
        displayParts(LS.getItem('plantdb.display')); return false;
      }).catch(function () { displayParts(LS.getItem('plantdb.display')); return false; });
    },
    load: function () {              // fetch what the server keeps for you and use it here; returns true if anything changed
      return fetch('/api/me/prefs', { credentials: 'same-origin' }).then(function (r) { return r.ok ? r.json() : { prefs: {} }; }).then(function (d) {
        var P = d.prefs || {}, changed = false, sh = shared();
        applying = true;
        try {
          KEYS.forEach(function (k) {
            var v = P[k.slice(8)];
            if (v != null && LS.getItem(k) !== v) { setI.call(LS, k, v); changed = true; }
          });
          var disp = {}; try { disp = JSON.parse(LS.getItem('plantdb.display') || '{}') || {}; } catch (e) { disp = {}; }
          var dch = false;
          for (var part in PARTS) if (sh[part] && P['display.' + part]) {
            var x = {}; try { x = JSON.parse(P['display.' + part]) || {}; } catch (e) { x = {}; }
            for (var k in x) if (disp[k] !== x[k]) { disp[k] = x[k]; dch = true; }
          }
          if (dch) { for (var k2 in disp) window.PlantPrefs.set(k2, disp[k2]); changed = true; }
        } finally { applying = false; }
        return changed;
      }).catch(function () { return false; });
    }
  };
})();
