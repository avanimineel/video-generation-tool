/* Studio engine: draws an editable film (window.FILM) at any moment. Shared by the Studio preview and
   the recorder, so the preview is the export.

   A film is layers on one continuous canvas. A camera flies across it (keyframes); each layer has a depth
   (0 = fixed to the screen, 1 = on the canvas, in between = parallax), its own entrance and exit, optional
   motion keyframes, and optional sounds. Transitions are moments where the whole frame whips, zooms through,
   flashes or wipes. Every frame is a pure function of time: window.seek(t). */
function mountFilm(F) {
  document.body.innerHTML = '';
  const W = F.aspect === '9:16' ? 1080 : 1920, H = F.aspect === '9:16' ? 1920 : (F.aspect === '1:1' ? 1080 : 1080);
  const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
  const ramp = (t, s, l) => l <= 0 ? (t >= s ? 1 : 0) : clamp((t - s) / l);
  const lerp = (a, b, p) => a + (b - a) * p;
  const EASE = {
    linear: x => clamp(x), out: x => 1 - Math.pow(1 - clamp(x), 3), in: x => Math.pow(clamp(x), 3),
    inOut: x => { x = clamp(x); return x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; },
    expo: x => { x = clamp(x); return x === 1 ? 1 : 1 - Math.pow(2, -10 * x); },
    back: x => { x = clamp(x); const c = 1.7; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); },
    elastic: x => { x = clamp(x); return x === 0 || x === 1 ? x : Math.pow(2, -10 * x) * Math.sin((x * 10 - .75) * (2 * Math.PI / 3)) + 1; },
  };
  const ease = name => EASE[name] || EASE.out;
  const rng = seed => { let s = (seed >>> 0) || 1; return () => { s ^= s << 13; s ^= s >>> 17; s ^= s << 5; return ((s >>> 0) % 100000) / 100000; }; };
  const C = F.brand && F.brand.colors || {};
  const color = c => !c ? undefined : (C[c] || c);
  const font = f => { const fonts = F.brand && F.brand.fonts || {}; return fonts[f] ? `'${fonts[f]}'` : (f ? `'${f}'` : `'${fonts.heading || 'Inter'}'`); };
  const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
  const NS = 'http://www.w3.org/2000/svg';

  document.documentElement.style.cssText = `width:${W}px;height:${H}px;overflow:hidden`;
  document.body.style.cssText = `margin:0;width:${W}px;height:${H}px;overflow:hidden;background:${color(F.background && F.background.color) || '#000'};position:relative`;
  const stage = document.createElement('div'); stage.style.cssText = `position:absolute;inset:0;overflow:hidden;transform-origin:50% 50%`;
  document.body.appendChild(stage);
  const overlay = document.createElement('div'); overlay.style.cssText = 'position:absolute;inset:0;pointer-events:none;opacity:0;z-index:9999';
  document.body.appendChild(overlay);

  // Background texture, fixed to the screen.
  const tex = (F.background && F.background.texture) || 'none', lineColor = color((F.background && F.background.lineColor) || 'rgba(127,127,127,.25)');
  if (tex !== 'none') {
    const bg = document.createElement('div'); bg.style.cssText = 'position:absolute;inset:0';
    if (tex === 'dots') bg.style.backgroundImage = `radial-gradient(${lineColor} 1.3px, transparent 1.5px)`, bg.style.backgroundSize = '34px 34px';
    if (tex === 'grid') bg.style.backgroundImage = `linear-gradient(${lineColor} 1px, transparent 1px), linear-gradient(90deg, ${lineColor} 1px, transparent 1px)`, bg.style.backgroundSize = '96px 96px';
    if (tex === 'guides') bg.style.backgroundImage = `linear-gradient(90deg, transparent 159px, ${lineColor} 159px, ${lineColor} 160px, transparent 160px, transparent ${W - 161}px, ${lineColor} ${W - 161}px, ${lineColor} ${W - 160}px, transparent ${W - 160}px)`;
    if (tex === 'vignette') bg.style.background = 'radial-gradient(ellipse at 50% 45%, transparent 45%, rgba(0,0,0,.45) 100%)';
    stage.appendChild(bg);
  }

  /* Blocks are sections of the film, each with its own spot (origin) on the canvas. A layer is placed in
     its block's frame like an ordinary screen; the camera flies to a block by name. */
  const ORIGIN = {}; (F.blocks || []).forEach(b => { ORIGIN[b.id] = {x: (b.origin && b.origin.x) || 0, y: (b.origin && b.origin.y) || 0}; });
  const origin = id => ORIGIN[id] || {x: 0, y: 0};
  /* Camera: keyframes of x, y, zoom and rotate on the canvas ("block" sets x and y to that block's spot). */
  const camKeys = (F.camera && F.camera.length ? F.camera : [{t: 0, x: 0, y: 0, zoom: 1, rotate: 0}]).map(k => k.block ? Object.assign({}, k, {x: origin(k.block).x + (k.x || 0), y: origin(k.block).y + (k.y || 0)}) : k).sort((a, b) => a.t - b.t);
  function camera(t) {
    let a = camKeys[0], b = camKeys[camKeys.length - 1];
    for (let i = 0; i < camKeys.length - 1; i++) if (t >= camKeys[i].t && t <= camKeys[i + 1].t) { a = camKeys[i]; b = camKeys[i + 1]; break; }
    if (t <= camKeys[0].t) a = b = camKeys[0];
    if (t >= b.t && b === camKeys[camKeys.length - 1]) a = b;
    const p = a === b ? 0 : ease(b.ease || 'inOut')((t - a.t) / Math.max(.001, b.t - a.t));
    const v = k => lerp(a[k] ?? (k === 'zoom' ? 1 : 0), b[k] ?? (k === 'zoom' ? 1 : 0), p);
    return {x: v('x'), y: v('y'), zoom: v('zoom'), rotate: v('rotate')};
  }

  /* Layer builders. Each returns {el, pose(u, layer)} where u is time since the layer's start. */
  function textLayer(L) {
    const st = L.style || {}, el = document.createElement('div');
    el.style.cssText = `position:absolute;white-space:pre-wrap;font-family:${font(st.font || 'heading')},sans-serif;font-size:${st.size || 72}px;font-weight:${st.weight || 700};` +
      `color:${color(st.color) || color('text') || '#fff'};line-height:${st.lineHeight || 1.05};letter-spacing:${st.tracking ?? -0.02}em;text-align:${st.align || 'left'};` +
      `text-transform:${st.case === 'upper' ? 'uppercase' : st.case === 'lower' ? 'lowercase' : 'none'};font-style:${st.italic ? 'italic' : 'normal'};` +
      `width:${L.width ? L.width + 'px' : 'max-content'};`;
    const accent = new Set(L.accent || []), accentColor = color(st.accentColor) || color('accent');
    const accentCss = {color: `color:${accentColor}`, italic: `color:${accentColor};font-style:italic`, underline: `color:${accentColor};text-decoration:underline;text-decoration-thickness:.07em;text-underline-offset:.12em`,
      highlight: `background:${accentColor};color:${color(st.color === 'text' ? 'background' : 'background') || '#000'};padding:0 .12em`, outline: `color:transparent;-webkit-text-stroke:2px ${accentColor}`}[st.accentStyle || 'color'];
    const effect = (L.in && L.in.effect) || 'rise-words';
    const byLetter = ['type', 'letters-scatter', 'letters-rise'].includes(effect);
    const words = String(L.text || '').split(/(\s+|\n)/);
    let wordIndex = -1; const units = [];
    words.forEach(w => {
      if (/^\n$/.test(w)) { el.appendChild(document.createElement('br')); return; }
      if (/^\s+$/.test(w)) { el.appendChild(document.createTextNode(' ')); return; }
      if (!w) return;
      wordIndex++;
      const span = document.createElement('span'); span.style.cssText = 'display:inline-block;' + (accent.has(wordIndex) ? accentCss : '');
      if (byLetter) [...w].forEach(ch => { const s = document.createElement('span'); s.style.display = 'inline-block'; s.textContent = ch; span.appendChild(s); units.push(s); });
      else { span.textContent = w; units.push(span); }
      el.appendChild(span);
    });
    const r = rng(L.seed || 7); const scatter = units.map(() => ({x: (r() - .5) * 900, y: (r() - .5) * 600, rot: (r() - .5) * 120}));
    return {el, pose(u) {
      const d = (L.in && L.in.duration) || .55, stagger = (L.in && L.in.stagger) ?? (byLetter ? .03 : .09), e = ease((L.in && L.in.ease) || (effect === 'letters-scatter' ? 'expo' : 'out'));
      units.forEach((s, i) => {
        const p = e(ramp(u, i * stagger, d));
        let o = p, tr = '', fl = '', clip = '';
        if (effect === 'rise-words' || effect === 'letters-rise') tr = `translateY(${(1 - p) * .5}em)`, fl = `blur(${(1 - p) * 8}px)`;
        else if (effect === 'mask-up') o = 1, tr = `translateY(${(1 - p) * .9}em)`, clip = `inset(-.2em 0 ${(1 - p) * 100}% 0)`;
        else if (effect === 'blur-in') fl = `blur(${(1 - p) * 18}px)`, tr = `scale(${1.08 - .08 * p})`;
        else if (effect === 'scale-pop') tr = `scale(${lerp(1.6, 1, EASE.back(ramp(u, i * stagger, d)))})`, o = p > 0 ? 1 : 0;
        else if (effect === 'type') o = u >= i * stagger ? 1 : 0;
        else if (effect === 'letters-scatter') tr = `translate(${scatter[i].x * (1 - p)}px, ${scatter[i].y * (1 - p)}px) rotate(${scatter[i].rot * (1 - p)}deg)`;
        else if (effect === 'none') o = 1;
        s.style.opacity = o; s.style.transform = tr; s.style.filter = fl; s.style.clipPath = clip;
      });
    }};
  }
  function imageLayer(L) {
    const el = document.createElement('div'); el.style.cssText = `position:absolute;overflow:hidden;width:${L.width || 600}px;height:${L.height || 400}px;border-radius:${L.mask === 'circle' ? '50%' : (L.radius || 0) + 'px'}`;
    const img = document.createElement('img'); img.src = L.src; img.style.cssText = `width:100%;height:100%;object-fit:${L.fit || 'cover'};object-position:${L.focus || '50% 50%'};transform-origin:50% 50%`;
    if (L.filter === 'grayscale') img.style.filter = 'grayscale(1) contrast(1.05)';
    if (L.filter === 'duotone') img.style.filter = 'grayscale(1) sepia(.5) saturate(1.6) hue-rotate(-12deg)';
    el.appendChild(img);
    return {el, pose(u, layer) {
      const span = Math.max(.1, layer.end - layer.start), p = clamp(u / span), kb = L.kenburns || 'none';
      const s = {push_in: 1 + .12 * EASE.inOut(p), pull_out: 1.12 - .12 * EASE.inOut(p), pan_left: 1.1, pan_right: 1.1}[kb] || 1;
      const dx = kb === 'pan_left' ? (.5 - p) * 8 : kb === 'pan_right' ? (p - .5) * 8 : 0;
      img.style.transform = `scale(${s}) translateX(${-dx}%)`;
    }};
  }
  function shapeLayer(L) {
    const w = L.width || 200, h = L.height || 200, svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('width', w); svg.setAttribute('height', h); svg.setAttribute('viewBox', `0 0 ${w} ${h}`); svg.style.cssText = 'position:absolute;overflow:visible';
    const kind = L.shape || 'rect', sw = L.strokeWidth || 0; let node;
    if (kind === 'circle' || kind === 'ring' || kind === 'ellipse') { node = document.createElementNS(NS, 'ellipse'); node.setAttribute('cx', w / 2); node.setAttribute('cy', h / 2); node.setAttribute('rx', w / 2 - sw / 2); node.setAttribute('ry', h / 2 - sw / 2); }
    else if (kind === 'line') { node = document.createElementNS(NS, 'line'); node.setAttribute('x1', 0); node.setAttribute('y1', h / 2); node.setAttribute('x2', w); node.setAttribute('y2', h / 2); }
    else { node = document.createElementNS(NS, 'rect'); node.setAttribute('width', w); node.setAttribute('height', h); node.setAttribute('rx', L.radius || 0); }
    node.setAttribute('fill', kind === 'ring' || kind === 'line' ? 'none' : (color(L.fill) || 'none'));
    if (L.stroke || kind === 'ring' || kind === 'line') { node.setAttribute('stroke', color(L.stroke) || color('accent')); node.setAttribute('stroke-width', sw || 2); }
    if (L.dash) node.setAttribute('stroke-dasharray', L.dash);
    svg.appendChild(node);
    let len = 0;
    return {el: svg, pose(u) {
      if (L.draw) { if (!len) { len = node.getTotalLength ? node.getTotalLength() : 1000; }
        const p = ease('inOut')(ramp(u, 0, (L.in && L.in.duration) || 1)); node.setAttribute('stroke-dasharray', `${len}`); node.setAttribute('stroke-dashoffset', len * (1 - p)); }
    }};
  }
  function pathLayer(L) {
    // A drawn line with optional glow, a bright travelling head and seeded sparks: trajectories, signatures, routes.
    const svg = document.createElementNS(NS, 'svg'); svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.setAttribute('width', W); svg.setAttribute('height', H);
    svg.style.cssText = 'position:absolute;left:0;top:0;overflow:visible';
    const stroke = color(L.stroke) || color('accent') || '#fff';
    const mk = (tag, a) => { const n = document.createElementNS(NS, tag); for (const k in a) n.setAttribute(k, a[k]); svg.appendChild(n); return n; };
    const glow = L.glow ? mk('path', {d: L.d, stroke, 'stroke-width': (L.width || 4) * 6, fill: 'none', opacity: .35, style: 'filter:blur(8px)'}) : null;
    const line = mk('path', {d: L.d, stroke, 'stroke-width': L.width || 4, fill: 'none', 'stroke-linecap': 'round'});
    const head = L.head ? mk('circle', {r: (L.width || 4) * 7, fill: stroke, style: 'filter:blur(4px)'}) : null;
    const core = L.head ? mk('circle', {r: (L.width || 4) * 2.2, fill: '#fff'}) : null;
    const r = rng(L.seed || 11), sparks = L.sparks ? Array.from({length: 36}, () => ({lag: r() * .15, dx: (r() - .5) * 70, dy: r() * 60, size: 1.5 + r() * 3, el: mk('circle', {fill: stroke})})) : [];
    const len = line.getTotalLength();
    return {el: svg, pose(u) {
      const p = ease((L.in && L.in.ease) || 'inOut')(ramp(u, 0, (L.in && L.in.duration) || 2));
      [line, glow].forEach(n => n && (n.setAttribute('stroke-dasharray', len), n.setAttribute('stroke-dashoffset', len * (1 - p))));
      const pt = line.getPointAtLength(len * p);
      [head, core].forEach(n => n && (n.setAttribute('cx', pt.x), n.setAttribute('cy', pt.y), n.setAttribute('opacity', p > 0 && p < 1 ? 1 : 0)));
      sparks.forEach(s => { const q = clamp(p - s.lag), at = line.getPointAtLength(len * q), life = 1 - s.lag / .15;
        s.el.setAttribute('cx', at.x + s.dx * (1 - life)); s.el.setAttribute('cy', at.y + s.dy * (1 - life)); s.el.setAttribute('r', s.size * life); s.el.setAttribute('opacity', p > 0 && p < 1 ? life * .9 : 0); });
    }};
  }
  function particleLayer(L) {
    const area = L.area || {x: 0, y: 0, w: W, h: H}, svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.setAttribute('width', W); svg.setAttribute('height', H); svg.style.cssText = 'position:absolute;left:0;top:0;overflow:visible';
    const r = rng(L.seed || 5), [s0, s1] = L.size || [2, 6], fill = color(L.color) || color('accent') || '#fff';
    const dots = Array.from({length: Math.min(400, L.count || 60)}, () => ({x: area.x + r() * area.w, y: area.y + r() * area.h, s: s0 + r() * (s1 - s0), ph: r() * 6.28, sp: .4 + r(), el: (() => { const c = document.createElementNS(NS, 'circle'); c.setAttribute('fill', fill); svg.appendChild(c); return c; })()}));
    return {el: svg, pose(u) {
      const kind = L.flow || 'drift', cx = area.x + area.w / 2, cy = area.y + area.h / 2;
      dots.forEach((d, i) => { let x = d.x, y = d.y, o = clamp(u / .6);
        if (kind === 'drift') x += Math.sin(u * d.sp + d.ph) * 18, y += Math.cos(u * d.sp * .8 + d.ph) * 14;
        if (kind === 'rise') y -= ((u * 60 * d.sp) % area.h), o *= .8;
        if (kind === 'orbit') { const a = d.ph + u * .5 * d.sp, rr = Math.hypot(d.x - cx, d.y - cy); x = cx + Math.cos(a) * rr; y = cy + Math.sin(a) * rr * .45; }
        if (kind === 'burst') { const p = EASE.expo(ramp(u, 0, 1.2)); x = lerp(cx, d.x, p); y = lerp(cy, d.y, p); o = 1 - ramp(u, 1.2, 1.2); }
        d.el.setAttribute('cx', x); d.el.setAttribute('cy', y); d.el.setAttribute('r', d.s); d.el.setAttribute('opacity', o * (L.opacity ?? .8)); });
    }};
  }
  function counterLayer(L) {
    const t = textLayer(Object.assign({}, L, {text: L.value, in: {effect: 'none'}})), m = String(L.value).match(/^([^\d]*)(\d[\d,]*\.?\d*)(.*)$/);
    return {el: t.el, pose(u) { t.pose(u); if (!m) return; const digits = m[2].replace(/,/g, ''), dec = (digits.split('.')[1] || '').length;
      const v = (parseFloat(digits) * EASE.out(ramp(u, 0, (L.in && L.in.duration) || 1.2))).toFixed(dec);
      t.el.firstChild && (t.el.firstChild.textContent = m[1] + (m[2].includes(',') ? Number(v).toLocaleString('en-US', {minimumFractionDigits: dec}) : v) + m[3]); }};
  }
  const BUILD = {text: textLayer, image: imageLayer, shape: shapeLayer, path: pathLayer, particles: particleLayer, counter: counterLayer,
    logo: L => L.src ? imageLayer(Object.assign({fit: 'contain'}, L)) : textLayer(Object.assign({text: L.text || (F.title || '')}, L))};

  /* Place every layer once. */
  const layers = (F.layers || []).map((L, i) => {
    const b = (BUILD[L.type] || BUILD.text)(L); b.el.dataset.layer = L.id || ('layer' + i);
    b.el.style.zIndex = String(L.z ?? i + 1); stage.appendChild(b.el);
    return {L, b, start: L.start ?? 0, end: L.end ?? (F.duration || 10)};
  });

  function keyframed(L, u) {
    // Optional motion keyframes, relative to the layer's own start: offsets, scale, rotation, opacity.
    const ks = L.motion || []; if (!ks.length) return {dx: 0, dy: 0, scale: 1, rotate: 0, opacity: 1};
    let a = ks[0], b = ks[ks.length - 1];
    for (let i = 0; i < ks.length - 1; i++) if (u >= ks[i].t && u <= ks[i + 1].t) { a = ks[i]; b = ks[i + 1]; break; }
    if (u <= ks[0].t) a = b = ks[0]; if (u >= ks[ks.length - 1].t) a = b = ks[ks.length - 1];
    const p = a === b ? 0 : ease(b.ease || 'inOut')((u - a.t) / Math.max(.001, b.t - a.t)), v = (k, d) => lerp(a[k] ?? d, b[k] ?? d, p);
    return {dx: v('dx', 0), dy: v('dy', 0), scale: v('scale', 1), rotate: v('rotate', 0), opacity: v('opacity', 1)};
  }

  function poseLayer(item, t, cam) {
    const {L, b, start, end} = item, el = b.el;
    const visible = t >= start && t < end;
    el.style.display = visible ? '' : 'none'; if (!visible) return;
    const u = t - start, left = end - t, inFx = (L.in && L.in.effect) || 'fade', outFx = (L.out && L.out.effect) || 'fade';
    const inD = (L.in && L.in.duration) || .5, outD = (L.out && L.out.duration) || .4;
    const k = keyframed(L, u);
    let opacity = (L.opacity ?? 1) * k.opacity, dx = k.dx, dy = k.dy, scale = (L.scale || 1) * k.scale, blur = 0, clip = '';
    const whole = ['fade', 'rise', 'scale', 'blur', 'mask-circle', 'wipe-left', 'zoom-in', 'pop'];
    if (L.type !== 'text' || whole.includes(inFx)) {
      const p = ease((L.in && L.in.ease) || 'out')(ramp(u, 0, inD));
      if (inFx === 'fade') opacity *= p; if (inFx === 'rise') opacity *= p, dy += (1 - p) * 40;
      if (inFx === 'scale' || inFx === 'zoom-in') opacity *= p, scale *= lerp(inFx === 'zoom-in' ? 1.25 : .85, 1, p);
      if (inFx === 'pop') scale *= lerp(.4, 1, EASE.back(ramp(u, 0, inD))), opacity *= p > 0 ? 1 : 0;
      if (inFx === 'blur') opacity *= p, blur += (1 - p) * 16;
      if (inFx === 'mask-circle') clip = `circle(${p * 75}% at 50% 50%)`;
      if (inFx === 'wipe-left') clip = `inset(0 ${(1 - p) * 100}% 0 0)`;
    }
    if (outFx !== 'none' && left < outD) {
      const q = ease('in')(1 - left / outD);
      opacity *= 1 - q; if (outFx === 'rise') dy -= q * 40; if (outFx === 'blur') blur += q * 16; if (outFx === 'scale') scale *= 1 - .15 * q;
    }
    /* Depth: 0 stays on the screen; 1 moves with the canvas under the camera; values between give parallax.
       Parallax is measured from the layer's block, so a layer sits where it was placed whenever the camera
       is on its block, at any depth. */
    const depth = L.depth ?? 1, zoom = 1 + (cam.zoom - 1) * depth;
    const o = origin(L.block), cx = W / 2, cy = H / 2, offX = (cam.x - o.x) * depth, offY = (cam.y - o.y) * depth;
    const x = (L.x ?? cx) + dx - offX, y = (L.y ?? cy) + dy - offY;
    const sx = cx + (x - cx) * zoom, sy = cy + (y - cy) * zoom;
    const anchor = L.anchor || 'center', ax = anchor.includes('left') ? 0 : anchor.includes('right') ? -100 : -50, ay = anchor.includes('top') ? 0 : anchor.includes('bottom') ? -100 : -50;
    if (L.type === 'path' || L.type === 'particles') {
      el.style.left = '0px'; el.style.top = '0px';
      el.style.transform = `translate(${dx - offX}px, ${dy - offY}px) scale(${zoom * scale})`; el.style.transformOrigin = `${cx + offX}px ${cy + offY}px`;
    } else {
      el.style.left = sx + 'px'; el.style.top = sy + 'px';
      el.style.transform = `translate(${ax}%, ${ay}%) scale(${zoom * scale}) rotate(${(L.rotate || 0) + k.rotate + cam.rotate * depth}deg)`;
      el.style.transformOrigin = `${-ax}% ${-ay}%`;
    }
    el.style.opacity = opacity; el.style.filter = blur > .2 ? `blur(${blur}px)` : ''; el.style.clipPath = clip;
    b.pose(u, item);
  }

  /* Whole-frame transitions around a moment. */
  function transitions(t) {
    let tx = 0, ts = 1, tb = 0, flash = 0, wipe = null;
    (F.transitions || []).forEach(tr => {
      const d = tr.duration || .5, p = (t - (tr.at - d / 2)) / d; if (p < 0 || p > 1) return;
      const bell = Math.sin(Math.PI * p);
      if (tr.type === 'whip') tx += (EASE.inOut(p) - .5) * -60 * bell, tb += bell * 22;
      if (tr.type === 'zoom-through') ts *= 1 + bell * .7, tb += bell * 7, flash = Math.max(flash, Math.pow(bell, 8) * .18);
      if (tr.type === 'flash') flash = Math.max(flash, bell);
      if (tr.type === 'wipe') wipe = {p, color: color(tr.color) || color('accent') || '#fff'};
      if (tr.type === 'dip') flash = Math.max(flash, bell), overlay.style.background = color(tr.color) || '#000';
    });
    stage.style.transform = `translateX(${tx}%) scale(${ts})`; stage.style.filter = tb > .3 ? `blur(${tb}px)` : '';
    if (wipe) { overlay.style.opacity = 1; overlay.style.background = wipe.color; const p = wipe.p; overlay.style.clipPath = p < .5 ? `inset(0 ${100 - p * 200}% 0 0)` : `inset(0 0 0 ${(p - .5) * 200}%)`; }
    else { overlay.style.clipPath = ''; overlay.style.opacity = flash; if (!(F.transitions || []).some(tr => tr.type === 'dip' && Math.abs(t - tr.at) < (tr.duration || .5) / 2)) overlay.style.background = '#fff'; }
  }

  window.TOTAL = F.duration || Math.max(1, ...layers.map(l => l.end));
  window.seek = t => { const cam = camera(t); layers.forEach(item => poseLayer(item, t, cam)); transitions(t); };
  // Sounds: explicit ones, each layer's entrance sound, and a whoosh under every transition unless set.
  window.CUES = [...(F.sounds || []).map(s => ({t: s.t, kind: s.name, gain: s.gain ?? 1})),
    ...layers.filter(l => l.L.sound && l.L.sound.in).map(l => ({t: l.start, kind: l.L.sound.in, gain: l.L.sound.gain ?? .8})),
    ...(F.transitions || []).filter(tr => tr.sound !== 'none').map(tr => ({t: tr.at - (tr.duration || .5) / 2, kind: tr.sound || 'whoosh', gain: .9}))];
  window.seek(0);
}
mountFilm(window.FILM);

/* In the Studio editor the page sits in a frame: the editor sends the edited film and the moment to show,
   and a click on a layer tells the editor which one to select. The recorder never sends messages. */
let lastT = 0;
window.addEventListener('message', e => {
  const m = e.data || {};
  if (m.type === 'film' && m.film) { window.FILM = m.film; mountFilm(m.film); window.seek(lastT); }
  if (m.type === 'seek') { lastT = +m.t || 0; window.seek(lastT); }
});
document.addEventListener('click', e => {
  const el = e.target.closest && e.target.closest('[data-layer]');
  if (window.parent !== window) window.parent.postMessage({type: 'select', id: el ? el.dataset.layer : null}, '*');
});
// Keyboard shortcuts pressed while the preview has focus belong to the editor.
document.addEventListener('keydown', e => {
  if (window.parent === window) return;
  if (e.code === 'Space' || ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'z')) e.preventDefault();
  window.parent.postMessage({type: 'key', key: e.key, code: e.code, meta: e.metaKey || e.ctrlKey, shift: e.shiftKey}, '*');
});
if (window.parent !== window) window.parent.postMessage({type: 'ready', total: window.TOTAL}, '*');
