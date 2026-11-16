/* Display settings, applied before the page paints. Stored in this browser only. */
(function () {
  var D = { size: '115', space: 'normal', contrast: 'auto', layout: 'split', theme: 'auto', navside: 'left', navopen: '1', width: 'normal',
            readbtns: '1', rate: '1', voice: 'auto', keys: '1',   // 1.8.0: read aloud, reading speed and voice, keyboard shortcuts
            swipe: '1',                                           // 1.14.1: swipe between plants
            vsearch: '1',                                         // search by voice: '1' buttons and say what was heard, 'quiet' buttons only, '0' hidden
            photofit: 'auto',                                     // 1.21.0: Plants page photos: auto (wide ones whole), fill, whole
            lines: 'short',                                       // 1.26.0: line length: full (use the width) or short (about 70 characters); short is the usual from 1.58.0 (the dyslexia audit)
            notes: 'show',                                        // 1.57.0: small notes under controls: 'show', or 'ask' (a Note chip that opens them)
            font: 'atkinson', plain: '0', cvd: 'usual',            // 1.58.0: letter shapes, one plain font, colour vision. contrast 'auto' follows the device
            abbr: '1', guide: '0', tint: 'none' };   // 1.58.0 (the dyslexia audit): short forms in plain words, the reading guide, a page tint
  var p = {};
  try { p = JSON.parse(localStorage.getItem('plantdb.display') || '{}') || {}; } catch (e) { p = {}; }
  var r = document.documentElement;
  var TONE = { cream: ['light', 'cream'], softdark: ['dark', 'soft'] };
  function mq(q) { return !!(window.matchMedia && matchMedia(q).matches); }
  function apply(v) {
    var x = {}; for (var k in D) x[k] = (v && v[k]) || D[k];
    r.setAttribute('data-size', x.size);
    r.setAttribute('data-space', x.space);
    // 1.58.0: "Match my device" (the usual) is high contrast when the device asks for more contrast
    r.setAttribute('data-contrast', x.contrast === 'auto' ? (mq('(prefers-contrast: more)') ? 'high' : 'normal') : x.contrast);
    r.setAttribute('data-layout', x.layout);
    r.setAttribute('data-navside', x.navside);
    r.setAttribute('data-navpref', x.navopen);
    r.setAttribute('data-width', x.width);
    r.setAttribute('data-readbtns', x.readbtns);
    r.setAttribute('data-vsearch', x.vsearch);
    r.setAttribute('data-photofit', x.photofit);
    r.setAttribute('data-lines', x.lines);
    r.setAttribute('data-notes', x.notes);
    // 1.58.0: Cream paper is light and Soft dark is dark underneath (data-theme), with data-tone saying which; data-mode is light or
    // dark once "Match my device" is worked out, for the colours that differ between the two
    var tone = TONE[x.theme], th = tone ? tone[0] : x.theme;
    if (th === 'auto') r.removeAttribute('data-theme'); else r.setAttribute('data-theme', th);
    if (tone) r.setAttribute('data-tone', tone[1]); else r.removeAttribute('data-tone');
    r.setAttribute('data-mode', th === 'auto' ? (mq('(prefers-color-scheme: dark)') ? 'dark' : 'light') : th);
    // a page tint is for light pages only (Cream paper is a tint of its own): it replaces the light page's paper colour
    if (x.tint === 'none' || r.getAttribute('data-mode') === 'dark' || tone) r.removeAttribute('data-tint'); else r.setAttribute('data-tint', x.tint);
    r.setAttribute('data-font', x.font);
    r.setAttribute('data-plain', x.plain);
    r.setAttribute('data-abbr', x.abbr);
    r.setAttribute('data-rguide', x.guide);
    if (x.cvd === 'usual') r.removeAttribute('data-cvd'); else r.setAttribute('data-cvd', x.cvd);
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
  // the device's own light or dark and contrast settings can change while the page is open
  if (window.matchMedia) ['(prefers-color-scheme: dark)', '(prefers-contrast: more)'].forEach(function (q) {
    var m = matchMedia(q), f = function () { apply(p); };
    if (m.addEventListener) m.addEventListener('change', f); else if (m.addListener) m.addListener(f);
  });
})();
/* 1.29.0: settings that follow you. The keys below are saved on the server for your sign-in (the owner's on this computer) as well
   as in this browser, so any device you sign in on picks them up. Display settings stay on this device unless you tick "Use these on
   every device I sign in on" for a part of them in Display; the device name and the offline copy never leave the device. */
(function () {
  var KEYS = ['plantdb.filters', 'plantdb.library', 'plantdb.fungi', 'plantdb.ltlights', 'plantdb.auditf', 'plantdb.calview', 'plantdb.wxchart',
              'plantdb.wxhide', 'plantdb.wxper', 'plantdb.idscope', 'plantdb.place', 'plantdb.frosthide', 'plantdb.shopping', 'plantdb.shoplist',
              'plantdb.units', 'plantdb.idmode', 'plantdb.compare'];                    // 1.47.0: °F or °C, inches or cm; 1.51.0: Identify's two ways, per page   // 1.30.0: Shopping's home and kind; 1.34.0: the shopping list's extras
  // 1.58.0: Reading has its own part (spacing and line length moved there); a device that shared Text and colours shares Reading too
  var PARTS = { text: ['size', 'contrast', 'theme', 'cvd'], reading: ['font', 'plain', 'space', 'lines', 'abbr', 'guide', 'tint'], layout: ['width', 'notes', 'layout', 'navside', 'navopen'], read: ['readbtns', 'rate', 'voice'],
                photos: ['photofit', 'swipe'], keys: ['keys', 'vsearch'] };
  var LS = window.localStorage, setI = Storage.prototype.setItem, remI = Storage.prototype.removeItem, queue = {}, timer = 0, applying = false;
  function shared() { var sh; try { sh = JSON.parse(LS.getItem('plantdb.dshare') || '{}') || {}; } catch (e) { sh = {}; }
    if (sh.text && !('reading' in sh)) sh.reading = true; return sh; }
  function send() {
    var body = queue; queue = {}; timer = 0;
    if (!Object.keys(body).length) return;
    var h = { 'Content-Type': 'application/json' };
    try { var n = LS.getItem('plantdb.editor'); if (n) h['X-Editor'] = n; } catch (e) { /* none */ }
    fetch('/api/me/prefs', { method: 'PUT', headers: h, body: JSON.stringify(body), credentials: 'same-origin', keepalive: true }).catch(function () { for (var k in body) if (!(k in queue)) queue[k] = body[k]; });
  }
  // a choice made just before the page is left (a reload, another page, the phone's screen turning off) is sent at once
  function flush() { if (loaded && Object.keys(queue).length) { clearTimeout(timer); send(); } }
  window.addEventListener('pagehide', flush);
  document.addEventListener('visibilitychange', function () { if (document.visibilityState === 'hidden') flush(); });
  var loaded = false;               // 1.30.0: nothing is sent until what the server keeps has been read, so a page that saves its
                                     // starting choices early does not overwrite the ones from another device
  // what this page has pushed but not seen come back from the server yet, kept across a reload (sessionStorage), so a reload a
  // moment after a choice does not let the server's older copy win
  function pending() { try { return JSON.parse(sessionStorage.getItem('plantdb.pending') || '{}') || {}; } catch (e) { return {}; } }
  function setPending(p) { try { sessionStorage.setItem('plantdb.pending', JSON.stringify(p)); } catch (e) { /* this visit only */ } }
  function push(k, v) { queue[k] = v; var p = pending(); p[k] = v; setPending(p); clearTimeout(timer); if (loaded) timer = setTimeout(send, 800); }
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
    applying: function () { return applying; },
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
        var P = d.prefs || {}, changed = false, sh = shared(), took = [];
        applying = true;
        try {
          var pend = pending(), still = {};
          KEYS.forEach(function (k) {
            var v = P[k.slice(8)], short = k.slice(8);
            if (short in pend) {
              if (v === pend[short]) return;                                  // our push landed
              if (LS.getItem(k) === pend[short] || (pend[short] === null && LS.getItem(k) === null)) { still[short] = pend[short]; queue[short] = pend[short]; return; }   // not yet: keep ours, send it again
            }
            if (v != null && LS.getItem(k) !== v) { setI.call(LS, k, v); changed = true; took.push(k); }
          });
          setPending(still);
          var disp = {}; try { disp = JSON.parse(LS.getItem('plantdb.display') || '{}') || {}; } catch (e) { disp = {}; }
          var dch = false;
          for (var part in PARTS) if (sh[part] && P['display.' + part]) {
            var x = {}; try { x = JSON.parse(P['display.' + part]) || {}; } catch (e) { x = {}; }
            for (var k in x) if (disp[k] !== x[k]) { disp[k] = x[k]; dch = true; }
          }
          if (dch) { for (var k2 in disp) window.PlantPrefs.set(k2, disp[k2]); changed = true; }
        } finally { applying = false; }
        if (took.length) { try { document.dispatchEvent(new CustomEvent('plantsync', { detail: took })); } catch (e) { /* older browser */ } }
        for (var q in queue) if (P[q] != null) delete queue[q];      // the server's own value wins over a choice this page made before it was read
        // when something changed, this page still holds the old choices and starts again with the new ones: send nothing from it
        if (!changed) { loaded = true; if (Object.keys(queue).length) timer = setTimeout(send, 800); }
        return changed;
      }).catch(function () { loaded = true; if (Object.keys(queue).length) timer = setTimeout(send, 800); return false; });
    }
  };
})();
