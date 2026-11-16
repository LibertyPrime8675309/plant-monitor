"""The contrast measure the browser checks share (names_check, reading_check): every piece of text on the page against what is behind it,
listing each below 7 to 1 (1.58.0)."""
CONTRAST = r'''() => {
  const lum = c => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
  const parse = s => { const m = /rgba?\(([^)]+)\)/.exec(s); if (!m) return null; const p = m[1].split(/[ ,\/]+/).map(Number); return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1]; };
  const over = (top, under) => { const a = top[3]; return [0, 1, 2].map(i => top[i] * a + under[i] * (1 - a)).concat(1); };
  const bgOf = el => { const stack = []; for (let e = el; e; e = e.parentElement) { const cs = getComputedStyle(e); if (cs.backgroundImage !== 'none') return null;      // a picture or a gradient: not judged here
      const c = parse(cs.backgroundColor); if (c && c[3] > 0) { stack.push(c); if (c[3] === 1) break; } }
    let b = parse(getComputedStyle(document.documentElement).backgroundColor) || [255, 255, 255, 1]; if (b[3] < 1) b = [255, 255, 255, 1];
    for (const c of stack.reverse()) b = over(c, b); return b; };
  const out = [], seen = new Set(), walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const t = walker.currentNode, el = t.parentElement; if (!el || !t.textContent.trim() || seen.has(el)) continue; seen.add(el);
    const cs = getComputedStyle(el); if (cs.visibility === 'hidden' || cs.display === 'none' || el.closest('[disabled],[aria-disabled=true],option,.ph-n,.photo-wrap figcaption')) continue;
    const r = el.getBoundingClientRect(); if (!r.width || !r.height) continue;
    const bg = bgOf(el); let fg = parse(cs.color); if (!fg || !bg) continue; fg = over(fg, bg);
    const L1 = lum(fg), L2 = lum(bg), cr = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
    if (cr < 6.95) out.push(`${cr.toFixed(2)} to 1: "${t.textContent.trim().slice(0, 30)}" (${el.tagName.toLowerCase()}.${[...el.classList].join('.')})`);
  }
  return out; }'''
