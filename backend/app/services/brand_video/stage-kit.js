/* Stage kit: small helpers for hand-designed brand films. Optional; a film may use none of them.

   The only contract a film must keep:
     window.TOTAL      length of the film in seconds
     window.seek(t)    pose the whole page for time t (seconds). Pure: the same t always gives the
                       same picture, whatever order frames are asked in. No CSS animations, no
                       transitions, no timers, no requestAnimationFrame, no Math.random.
     window.CUES       optional [{t, kind}] sound cues; kind is 'whoosh', 'pop', 'paper', 'typewriter' or 'highlight'.
*/
(function () {
  const K = {};
  K.clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
  K.ramp = (t, start, length) => K.clamp((t - start) / length);          // 0 before start, 1 after start + length
  K.lerp = (a, b, p) => a + (b - a) * p;
  K.ease = {
    out: x => 1 - Math.pow(1 - K.clamp(x), 3),
    in: x => Math.pow(K.clamp(x), 3),
    inOut: x => { x = K.clamp(x); return x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; },
    expo: x => { x = K.clamp(x); return x === 1 ? 1 : 1 - Math.pow(2, -10 * x); },
    back: x => { x = K.clamp(x); const c = 1.7; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); },
    elastic: x => { x = K.clamp(x); return x === 0 || x === 1 ? x : Math.pow(2, -10 * x) * Math.sin((x * 10 - .75) * (2 * Math.PI / 3)) + 1; },
  };
  // Deterministic randomness: the same seed gives the same sequence on every frame.
  K.random = seed => { let s = seed >>> 0 || 1; return () => { s ^= s << 13; s ^= s >>> 17; s ^= s << 5; return ((s >>> 0) % 100000) / 100000; }; };
  // Wrap each word (or letter) of an element in spans so they can be animated one by one.
  K.split = (el, by = 'word') => {
    const text = el.textContent; el.textContent = '';
    const parts = by === 'letter' ? [...text] : text.split(/(\s+)/);
    return parts.filter(p => p.length).map(p => {
      if (/^\s+$/.test(p)) { el.appendChild(document.createTextNode(p)); return null; }
      const span = document.createElement('span'); span.textContent = p; span.style.display = 'inline-block'; el.appendChild(span); return span;
    }).filter(Boolean);
  };
  // "30+" counts 0 -> 30 with its prefix and suffix kept; p runs 0..1.
  K.count = (value, p) => {
    const m = String(value).match(/^([^\d]*)(\d[\d,]*\.?\d*)(.*)$/); if (!m) return value;
    const digits = m[2].replace(/,/g, ''), decimals = (digits.split('.')[1] || '').length;
    const shown = (parseFloat(digits) * K.ease.out(p)).toFixed(decimals);
    return m[1] + (m[2].includes(',') ? Number(shown).toLocaleString('en-US', {minimumFractionDigits: decimals}) : shown) + m[3];
  };
  // Scenes on a timeline: K.scenes([{name, start, end, el}]) returns a function giving local time or null.
  K.local = (t, start, end, pad = 0) => (t >= start - pad && t < end + pad) ? t - start : null;
  window.K = K;
})();
