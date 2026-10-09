/* Office HQ — layar penuh bergaya Hermes3D. Karakter = sprite pixel-art (atlas di /sprites).
   Mode 3D (Three.js r128; Pixel atau HD) & 2D (pixel art). Simulasi (peta, aktivitas, briefing) ada di office_sim.js. */
(() => {
  const sec = document.getElementById('office'), stage = document.getElementById('oStage'), host = document.getElementById('oCanvas');
  if (!sec || !stage || !host || !window.OfficeSim) return;
  const OS = window.OfficeSim, W = OS.W, H = OS.H, sim = OS.create();
  const $ = s => stage.querySelector(s);
  const esc = s => String(s == null ? '' : s).replace(/[<>&"]/g, c => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;' }[c]));
  const store = { get: k => { try { return localStorage.getItem(k); } catch { return null; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch { } } };
  const hex = c => parseInt(c.slice(1), 16);
  const shade = (c, a) => { const n = hex(c), f = v => Math.max(0, Math.min(255, v + a)); return '#' + [(n >> 16) & 255, (n >> 8) & 255, n & 255].map(v => f(v).toString(16).padStart(2, '0')).join(''); };
  const SCREEN = { type: 0x2563EB, speak: 0xDB2777, alert: 0xDC2626, wave: 0x2563EB, cheer: 0x10B981 };
  const SITTING = new Set(['sit', 'type', 'speak', 'wave', 'cheer', 'alert', 'sitread', 'eat']);
  const REDUCED = !!(window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches);
  const SV = 'aria-hidden="true" focusable="false"';
  const IC = {
    full: `<svg ${SV} viewBox="0 0 24 24"><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/></svg>`,
    center: `<svg ${SV} viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v4M12 18v4M2 12h4M18 12h4"/></svg>`,
    cube: `<svg ${SV} viewBox="0 0 24 24"><path d="M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3zM4 7.5l8 4.5 8-4.5M12 12v9"/></svg>`,
    users: `<svg ${SV} viewBox="0 0 24 24"><circle cx="9" cy="8" r="3"/><path d="M3 19c0-3.3 2.7-6 6-6s6 2.7 6 6M16 5.2a3 3 0 010 5.6M21 19c0-2.5-1.5-4.6-3.6-5.5"/></svg>`,
    chat: `<svg ${SV} viewBox="0 0 24 24"><path d="M4 5h16v11H9l-5 4V5z"/></svg>`,
    play: `<svg ${SV} viewBox="0 0 24 24"><path d="M7 4l13 8-13 8z" fill="currentColor"/></svg>`,
    stop: `<svg ${SV} viewBox="0 0 24 24"><rect x="6" y="6" width="12" height="12" rx="1" fill="currentColor"/></svg>`,
    plus: `<svg ${SV} viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>`,
    minus: `<svg ${SV} viewBox="0 0 24 24"><path d="M5 12h14"/></svg>`,
    rot: `<svg ${SV} viewBox="0 0 24 24"><path d="M20 12a8 8 0 11-2.3-5.7M20 4v4h-4"/></svg>`,
    list: `<svg ${SV} viewBox="0 0 24 24"><path d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01"/></svg>`,
    flow: `<svg ${SV} viewBox="0 0 24 24"><rect x="3" y="4" width="6" height="5" rx="1"/><rect x="15" y="15" width="6" height="5" rx="1"/><path d="M6 9v2a2 2 0 002 2h8a2 2 0 012 2"/></svg>`,
    doc: `<svg ${SV} viewBox="0 0 24 24"><path d="M7 3h7l5 5v13H7zM14 3v5h5M10 13h6M10 17h6"/></svg>`,
    chev: `<svg ${SV} viewBox="0 0 24 24"><path d="M9 6l6 6-6 6"/></svg>`,
  };

  // ---------- HUD ----------
  const hud = document.createElement('div'); hud.className = 'o-hud';
  hud.innerHTML = `
  <canvas id="o2d" hidden aria-label="Peta kantor 2D"></canvas>
  <div id="oLabels" class="o-labels" hidden aria-hidden="true"></div>
  <iframe class="o-frame" id="oFrame" title="Hermes3D" hidden allow="microphone; fullscreen"></iframe>
  <div class="o-brand"><span class="bi" aria-hidden="true">${IC.users}</span><div><b>MorbMyth AI Studio</b><small><span id="oCount"></span> · 4 lantai</small></div></div>
  <div class="o-bar">
    <button class="ob sq" id="oFull" aria-label="Layar penuh tanpa sidebar" title="Layar penuh (Esc untuk keluar)">${IC.full}</button>
    <button class="ob sq" id="oH3D" aria-label="Hermes3D penuh" aria-pressed="false" title="Hermes3D (Next.js) — butuh Node.js">${IC.cube}</button>
    <i class="sep"></i>
    <button class="ob" id="oNight" aria-pressed="false" aria-label="Mode malam" title="Siang / Malam (tombol N)">Siang</button>
    <button class="ob" id="oQual" aria-pressed="true" title="Tampilan 3D: Pixel (chunky) atau HD (halus)">Pixel</button>
    <button class="ob" id="oMode" aria-label="Ganti ke mode 2D" title="Ganti 2D / 3D">2D</button>
    <i class="sep"></i>
    <span class="ob stat off" id="oStat" role="status">Hermes …</span>
    <button class="ob" id="oDemo" title="Putar simulasi alur kerja tanpa menjalankan automation">${IC.play} Simulasi</button>
    <button class="ob" id="oKanban" aria-expanded="false">${IC.list} Kanban <em class="kc" id="oKbCnt" hidden></em></button>
    <button class="ob gold" id="oRun">${IC.play} Start</button></div>
  <div class="o-brief" id="oBrief" role="status" aria-live="polite" hidden></div>
  <div class="o-build" id="oBuild" aria-label="Building section"><button class="o-ch" id="oBuildT" aria-expanded="true" aria-controls="oBuildB"><span>Building section</span><small id="oBuildCur"></small>${IC.chev}</button><div class="cbody" id="oBuildB"><div class="fl-list" id="oFlList"></div><button class="ob wide" id="oWhole" aria-pressed="false">${IC.doc}<span>Lihat seluruh gedung</span></button></div></div>
  <div class="o-panel" id="oPanel" hidden></div>
  <div class="o-console" id="oCons"><button class="o-ch" id="oConsT" aria-expanded="true" aria-controls="oConsB"><b>Office log</b><span class="tag" id="oConsInfo">Siaga</span>${IC.chev}</button><div class="cbody" id="oConsB">
    <div class="stats"><div><b id="oStWork">0</b><small>Bekerja</small></div><div><b id="oStFree">0</b><small>Santai</small></div><div><b id="oStEv">0</b><small>Event</small></div></div>
    <div class="last" id="oLast"></div>
    <div class="acts"><button id="oCopy">Salin JSON</button><button id="oDown">Unduh JSON</button><button id="oClr">Hapus</button><button id="oExp" aria-expanded="false">Perluas</button></div>
    <div class="b" id="oConsBody" hidden></div></div></div>
  <div class="o-legend" id="oLegend"><div class="lh"><span>MorbMyth HQ</span><span>Building section</span></div><div class="lb"><h5>Kantor, dari bawah ke atas.</h5><p id="oLegTxt"></p></div><div class="lf">Denah interpretasi · karakter ilustrasi</div></div>
  <div class="o-hint" id="oHint"></div>
  <div class="o-chat" id="oChat" hidden role="dialog" aria-label="Chat dengan MorbMyth"><div class="ch"><b>Ngobrol dengan MorbMyth (CEO)</b><button id="oChatX" aria-label="Tutup chat">✕</button></div>
    <div class="cm" id="oChatMsgs"><div class="m bot">Halo, aku MorbMyth. Coba: “mulai automation”, “buatkan 5 ide baru”, atau “gimana antreannya?”</div></div>
    <div class="ci"><input id="oMsg" aria-label="Pesan untuk MorbMyth" placeholder="Tulis pesan…" autocomplete="off"><button id="oSend">Kirim</button></div></div>
  <div class="o-dock">
    <div class="o-tabs"><button class="ob" data-p="agents" aria-expanded="false">${IC.users} Agen</button><button class="ob" data-p="kanban" aria-expanded="false">${IC.list} Antrean</button><button class="ob" data-p="pipe" aria-expanded="false">${IC.flow} Pipeline</button></div>
    <i class="sep"></i>
    <button class="ob" id="oChatBtn" aria-expanded="false">${IC.chat} Chat</button>
    <i class="sep"></i>
    <button class="ob sq" id="oZin" aria-label="Perbesar" title="Perbesar (+)">${IC.plus}</button>
    <button class="ob sq" id="oZout" aria-label="Perkecil" title="Perkecil (−)">${IC.minus}</button>
    <button class="ob" id="oRot" aria-label="Putar kamera 90 derajat" title="Putar 90°">${IC.rot} Putar</button>
    <button class="ob" id="oReset" aria-label="Reset kamera" title="Reset kamera (tombol 0)">${IC.center} Reset</button></div>`;
  stage.appendChild(hud); stage.tabIndex = 0; stage.setAttribute('aria-label', 'Kantor virtual agen');
  host.innerHTML = '<div id="o3d"></div>';
  const g = id => stage.querySelector('#' + id), frame = g('oFrame');

  let mode = store.get('officeMode2'); if (mode !== '3d' && mode !== '2d') mode = '3d';
  if (mode === '3d' && !window.THREE) mode = '2d';
  let pixelQ = store.get('officeQ') !== 'hd';
  let follow = null, r3 = null, r2 = null, panel = null, h3dOn = false;
  g('oCount').textContent = sim.agents.length + ' agen';

  // ---------- sprite karakter (atlas pixel-art per agen) ----------
  const SPR = { meta: null, img: {}, ready: false };
  const FALLBACK = { w: 80, h: 92, foot: 86, cols: 1, idleH: 64, anims: { idle: [0] } };
  const ALT = { walkD: ['walkR'], walkU: ['walkR'], run: ['walkR'], type: ['idle'], speak: ['wave', 'idle'], alert: ['cheer', 'wave', 'idle'], read: ['think', 'idle'], think: ['idle'], cheer: ['wave', 'idle'], wave: ['idle'] };
  const FPS = { idle: 3, walkR: 11, walkD: 9, walkU: 7, run: 13, wave: 8, cheer: 9, type: 7, speak: 7, think: 4, read: 4, alert: 10 };
  const spritesReady = (async () => {
    try {
      const meta = await (await fetch('/sprites/sprites.json')).json();
      await Promise.all(Object.keys(meta).map(id => new Promise((res, rej) => { const im = new Image(); im.onload = res; im.onerror = rej; im.src = `/sprites/${id}.png`; SPR.img[id] = im; })));
      SPR.meta = meta; SPR.ready = true;
    } catch (e) { console.warn('sprite gagal dimuat, memakai karakter cadangan', e); }
  })();
  const metaOf = id => (SPR.meta && SPR.meta[id]) || FALLBACK;
  const pickAnim = (m, n) => { for (const k of [n].concat(ALT[n] || [], 'idle')) if (m.anims[k] && m.anims[k].length) return k; return 'idle'; };
  function spriteFor(a, t) {
    const m = metaOf(a.id), p = a.pose; let name = 'idle', flip = false, icon = null;
    const dx = a.face[0], dy = a.face[1];
    if (p === 'walk') { if (Math.abs(dx) >= Math.abs(dy) * .8) { name = 'walkR'; flip = dx < 0; } else if (dy < 0) name = 'walkU'; else { name = 'walkD'; flip = dx < 0; } }
    else if (p === 'run') name = 'run';
    else if (p === 'type') name = 'type'; else if (p === 'speak') name = 'speak'; else if (p === 'wave') name = 'wave';
    else if (p === 'cheer') name = 'cheer'; else if (p === 'alert') name = 'alert';
    else if (p === 'read' || p === 'sitread') { name = 'read'; icon = 'book'; }
    else if (p === 'eat') icon = 'food'; else if (p === 'drink') icon = 'cup';
    else if (p === 'exercise') { const lift = /dumbbell/i.test(a.act); name = lift ? 'idle' : 'cheer'; if (lift) icon = 'weight'; }
    else if (p === 'play') { name = 'wave'; icon = 'paddle'; } else if (p === 'arcade') icon = 'joy';
    const sit = !a.moving && SITTING.has(a.target.pose) && p !== 'cheer' && p !== 'alert' && p !== 'run';
    name = pickAnim(m, name); const fr = m.anims[name], fps = FPS[name] || 6;
    const tt = a.moving ? a.phase / 9 : t + a.id.length * .37;
    let idx = fr[Math.floor(tt * fps) % fr.length]; if (REDUCED && !a.moving) idx = fr[0];
    return { m, name, idx, flip, sit, icon };
  }
  // ikon prop pixel (tanpa emoji)
  const ICONS = {
    cup: ['kkkkk..', 'kbbbkk.', 'kbbbk.k', 'kbbbk.k', 'kbbbkk.', '.kkkk..'], food: ['..ooo..', '.oyyyo.', '..rrr..', '..ggg..', '.obbbo.', '..ooo..'],
    paddle: ['..kkk..', '.krrrk.', 'krrrrrk', '.krrrk.', '..kbk..', '..kbk..'], joy: ['...r...', '..rrr..', '...k...', '...k...', '.kkkkk.', 'kkkkkkk'],
    book: ['kkkkkk.', 'krrrrk.', 'krwwrk.', 'krwwrk.', 'krrrrk.', 'kkkkkk.'], weight: ['k.....k', 'kk...kk', 'kkkkkkk', 'kk...kk', 'k.....k'],
  }, ICOL = { k: '#1B1B24', w: '#F3F4F6', r: '#DC2626', b: '#92400E', y: '#FACC15', g: '#22C55E', o: '#F59E0B' };
  function drawIconPx(c, kind, x, y, px) {
    const pat = ICONS[kind]; if (!pat) return;
    pat.forEach((row, j) => { for (let i = 0; i < row.length; i++) { const col = ICOL[row[i]]; if (col) { c.fillStyle = col; c.fillRect(Math.round(x + i * px), Math.round(y + j * px), Math.ceil(px), Math.ceil(px)); } } });
  }
  // gambar satu frame ke ctx (k = skala). sit: kaki disembunyikan & badan turun (duduk di kursi).
  function drawFrame(c, id, s, dx, dy, k) {
    const m = s.m, img = SPR.img[id], col = s.idx % m.cols, row = (s.idx / m.cols) | 0, cut = s.sit ? 18 : 0, drop = s.sit ? 7 : 0;
    if (img && SPR.ready) c.drawImage(img, col * m.w, row * m.h, m.w, m.foot - (cut ? cut : 0) + (cut ? 0 : m.h - m.foot), dx, dy + drop * k, m.w * k, (m.foot - cut + (cut ? 0 : m.h - m.foot)) * k);
    else { const ag = sim.byId[id]; c.fillStyle = ag.color; c.fillRect(dx + 24 * k, dy + 46 * k, 32 * k, 28 * k); c.fillStyle = '#F6D3B3'; c.fillRect(dx + 22 * k, dy + 22 * k, 36 * k, 26 * k); c.fillStyle = ag.hair; c.fillRect(dx + 22 * k, dy + 22 * k, 36 * k, 9 * k); }
    if (s.icon) drawIconPx(c, s.icon, dx + (m.w - 24) * k, dy + (m.foot - m.idleH + 4 + drop) * k, 3 * k);
  }

  // ---------- label nama (DOM, tajam di mode pixel) ----------
  const labs = {}, labBox = g('oLabels');
  for (const a of sim.agents) {
    const d = document.createElement('div'); d.className = 'o-lab'; d.innerHTML = `<div class="bb" hidden></div><div class="nm"><b>${esc(a.name)}</b><span>${esc(a.role)}</span></div>`;
    labBox.appendChild(d); labs[a.id] = { d, bb: d.querySelector('.bb'), txt: '' };
  }

  // ---------- lantai, tema, kamera ----------
  const FLOORS = OS.FLOORS, FH = 11, NF = FLOORS.length, NIGHT_KEY = 'officeNight', FLOOR_KEY = 'officeFloor';
  let viewFloor = (() => { const v = store.get(FLOOR_KEY); return v === null ? 1 : Math.max(-1, Math.min(NF - 1, +v)); })();   // -1 = seluruh gedung
  let night = store.get(NIGHT_KEY) === '1';
  const TSZ = 16, floorCache = {};
  function floorCanvas(r) {
    if (floorCache[r.id]) return floorCache[r.id];
    const [x0, y0, x1, y1] = r.r, w = x1 - x0 - 1, h = y1 - y0 - 1, cv = document.createElement('canvas'); cv.width = w * TSZ; cv.height = h * TSZ;
    const c = cv.getContext('2d'), P = (col, x, y, ww, hh) => { c.fillStyle = col; c.fillRect(x, y, ww, hh); };
    const rnd = i => { const v = Math.sin(i * 127.1 + r.id.length * 311.7 + r.id.charCodeAt(r.id.length - 1)) * 43758.5453; return v - Math.floor(v); };
    for (let ty = 0; ty < h; ty++) for (let tx = 0; tx < w; tx++) {
      const X = tx * TSZ, Y = ty * TSZ, alt = (tx + ty) % 2, n = tx * 31 + ty * 17;
      if (r.fl === 'tile') { P(alt ? r.c : r.c2, X, Y, TSZ, TSZ); P(shade(r.c, -22), X, Y, TSZ, 1); P(shade(r.c, -22), X, Y, 1, TSZ); }
      else if (r.fl === 'wood') { for (let k = 0; k < 4; k++) { P((k + tx * 2 + ty) % 3 ? r.c : r.c2, X, Y + k * 4, TSZ, 4); P(shade(r.c, -30), X, Y + k * 4 + 3, TSZ, 1); P(shade(r.c, -30), X + ((k * 5 + ty * 3 + tx * 7) % 12) + 2, Y + k * 4, 1, 3); } }
      else if (r.fl === 'grid') { P(r.c, X, Y, TSZ, TSZ); P(r.c2, X + 1, Y + 1, TSZ - 2, TSZ - 2); P('rgba(139,92,246,.6)', X, Y, TSZ, 1); P('rgba(139,92,246,.6)', X, Y, 1, TSZ); }
      else if (r.fl === 'grass') { P(alt ? r.c : r.c2, X, Y, TSZ, TSZ); for (let k = 0; k < 4; k++) P(shade(r.c, -28), X + ((rnd(n + k) * 14) | 0), Y + ((rnd(n + k + 9) * 13) | 0), 1, 2); }
      else { P(alt ? r.c : r.c2, X, Y, TSZ, TSZ); for (let k = 0; k < 5; k++) P(shade(r.c, k % 2 ? -14 : 12), X + ((rnd(n + k) * 15) | 0), Y + ((rnd(n + k + 5) * 15) | 0), 1, 1); }
    }
    return floorCache[r.id] = cv;
  }
  // tekstur layar dinding (grafik palsu) & papan nama
  function screenTex(color, seed) {
    const cv = document.createElement('canvas'); cv.width = 256; cv.height = 64; const c = cv.getContext('2d'); c.fillStyle = '#0B1220'; c.fillRect(0, 0, 256, 64);
    const tiles = 4, tw = 256 / tiles; let sd = seed * 7 + 3; const rn = () => (sd = (sd * 16807) % 2147483647) / 2147483647;
    for (let i = 0; i < tiles; i++) {
      const x = i * tw; c.strokeStyle = 'rgba(255,255,255,.12)'; c.strokeRect(x + 2.5, 2.5, tw - 5, 59); c.fillStyle = color;
      if (i % 2) { for (let b = 0; b < 7; b++) c.fillRect(x + 8 + b * 8, 56 - (8 + rn() * 34), 5, 8 + rn() * 34); } else { c.beginPath(); c.moveTo(x + 6, 40); for (let k = 1; k <= 8; k++) c.lineTo(x + 6 + k * 6.5, 14 + rn() * 34); c.lineWidth = 2; c.strokeStyle = color; c.stroke(); c.globalAlpha = .25; c.fillRect(x + 6, 50, tw - 12, 3); c.globalAlpha = 1; }
    }
    return cv;
  }
  function signCanvas(text) {
    const cv = document.createElement('canvas'); cv.width = 512; cv.height = 96; const c = cv.getContext('2d'); c.fillStyle = '#10131C'; c.fillRect(0, 0, 512, 96); c.strokeStyle = '#FFD027'; c.lineWidth = 4; c.strokeRect(4, 4, 504, 88);
    c.fillStyle = '#FFD027'; let fs = 40; c.font = `700 ${fs}px system-ui,sans-serif`; while (fs > 18 && c.measureText(text).width > 470) { fs -= 2; c.font = `700 ${fs}px system-ui,sans-serif`; } c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText(text, 256, 50); return cv;
  }
  const wallH = (x, y) => (y === 0 || x === 0 ? 2.5 : (y === H - 1 || x === W - 1 ? .55 : 1.15));

  // ===================================================================
  //  3D — isometrik ortografis, 4 lantai bertumpuk, siang/malam
  // ===================================================================
  function init3D(pixel) {
    const el = $('#o3d'); let rd;
    try { rd = new THREE.WebGLRenderer({ antialias: !pixel }); } catch { return null; }
    const PX = pixel ? 2 : 1;
    rd.setPixelRatio(pixel ? 1 : Math.min(window.devicePixelRatio || 1, 2));
    try { rd.shadowMap.enabled = true; rd.shadowMap.type = THREE.PCFSoftShadowMap; } catch { }
    rd.domElement.classList.toggle('px', !!pixel); el.append(rd.domElement);
    const scene = new THREE.Scene(), cam = new THREE.OrthographicCamera(-10, 10, 10, -10, -400, 600);
    const hemi = new THREE.HemisphereLight(0xffffff, 0x6b7a5a, .6); scene.add(hemi);
    const sun = new THREE.DirectionalLight(0xfff4e0, .62); sun.position.set(-20, 60, 24); sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048); Object.assign(sun.shadow.camera, { left: -30, right: 30, top: 30, bottom: -30, near: 1, far: 160 }); sun.shadow.bias = -.0006; scene.add(sun);
    const gx = x => x - W / 2, gz = y => y - H / 2, fy = fi => fi * FH, cache = {};
    const mat = (c, o) => { const k = c + (o ? JSON.stringify(o) : ''); return cache[k] || (cache[k] = new THREE.MeshLambertMaterial(Object.assign({ color: c }, o || {}))); };
    const bx = (grp, w, h, d, c, x, y, z, o, nosh) => { const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat(typeof c === 'string' ? hex(c) : c, o)); m.position.set(x, y, z); if (!nosh) { m.castShadow = true; m.receiveShadow = true; } grp.add(m); return m; };
    const crisp = t => { t.magFilter = THREE.NearestFilter; t.needsUpdate = true; return t; };
    const basicTex = (cv, o) => new THREE.MeshBasicMaterial(Object.assign({ map: crisp(new THREE.CanvasTexture(cv)) }, o || {}));
    const winMat = new THREE.MeshBasicMaterial({ color: 0xA8D4F5 }), trees = [], glass = [], groundMat = mat(0x7BA05B);

    function label(parent, text, x, y, z, s) {
      const cv = document.createElement('canvas'); cv.width = 512; cv.height = 96; const c = cv.getContext('2d');
      c.font = '700 44px system-ui,sans-serif'; const tw = Math.min(480, c.measureText(text).width + 56), x0 = 256 - tw / 2;
      c.fillStyle = 'rgba(255,255,255,.92)'; c.beginPath(); c.moveTo(x0 + 24, 12); c.arcTo(x0 + tw, 12, x0 + tw, 84, 24); c.arcTo(x0 + tw, 84, x0, 84, 24); c.arcTo(x0, 84, x0, 12, 24); c.arcTo(x0, 12, x0 + tw, 12, 24); c.fill();
      c.fillStyle = '#374151'; c.textAlign = 'center'; c.fillText(text, 256, 63);
      const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(cv), transparent: true, depthWrite: false })); sp.renderOrder = 5;
      sp.scale.set(512 / 96 * s, s, 1); sp.position.set(x, y, z); parent.add(sp); return sp;
    }
    // tanah + pohon
    const ground = new THREE.Mesh(new THREE.PlaneGeometry(560, 460), groundMat); ground.rotation.x = -Math.PI / 2; ground.position.y = -1.6; ground.receiveShadow = true; scene.add(ground);
    const crownGeo = new THREE.IcosahedronGeometry(1, 1), trunkGeo = new THREE.BoxGeometry(.35, 1.3, .35); let seed = 11; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
    for (let i = 0; i < 80; i++) {
      const x = (rnd() - .5) * (W + 60), z = (rnd() - .5) * (H + 50); if (Math.abs(x) < W / 2 + 4 && Math.abs(z) < H / 2 + 4) continue;
      const t = new THREE.Group(), sc = 1 + rnd() * .9, cm = new THREE.MeshPhongMaterial({ color: [0x4E8F3A, 0x5FA046, 0x3F7D32][i % 3], flatShading: true, shininess: 0 }); trees.push(cm);
      const tr = new THREE.Mesh(trunkGeo, mat(0x6B4423)); tr.position.y = .65; t.add(tr); const cr = new THREE.Mesh(crownGeo, cm); cr.position.y = 2.0; cr.scale.set(1.15, 1.05, 1.15); cr.castShadow = true; t.add(cr);
      t.scale.setScalar(sc); t.position.set(x, -1.6, z); scene.add(t);
    }

    const OS_FACE = { n: [0, -1], s: [0, 1], e: [1, 0], w: [-1, 0] }, deskColor = {}; sim.agents.forEach(a => deskColor[a.id] = hex(a.color));
    const screens = {}, groups = [], elev = [];
    function buildFloor(fi) {
      const F = FLOORS[fi], T = sim.floors[fi].tiles, G = new THREE.Group(); G.position.y = fy(fi); scene.add(G); groups.push(G);
      // lempeng lantai + bingkai
      const slab = new THREE.Mesh(new THREE.BoxGeometry(W + .8, .6, H + .8), [mat(0xCFC6B4), mat(0xCFC6B4), mat(0xE9E2D3), mat(0x8F8878), mat(0xCFC6B4), mat(0xCFC6B4)]); slab.position.y = -.31; slab.receiveShadow = true; slab.castShadow = true; G.add(slab);
      for (const r of F.rooms) {
        const [x0, y0, x1, y1] = r.r, w = x1 - x0 - 1, h = y1 - y0 - 1, m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshLambertMaterial({ map: crisp(new THREE.CanvasTexture(floorCanvas(r))) }));
        m.rotation.x = -Math.PI / 2; m.position.set(gx(x0 + 1 + w / 2), .01, gz(y0 + 1 + h / 2)); m.receiveShadow = true; G.add(m);
        if (!/_cor$/.test(r.id)) label(G, r.name, gx(x0 + 1 + w / 2), 1.25, gz(y1 - .7), .62);
      }
      const side = mat(0xEAE4D3), top = mat(0x55576B), low = mat(0xD9D2C2);
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
        const t = T[y][x];
        if (t.wall) {
          const h = wallH(x, y), m = new THREE.Mesh(new THREE.BoxGeometry(1, h, 1), [side, side, top, side, side, side]); m.position.set(gx(x + .5), h / 2, gz(y + .5)); m.castShadow = true; m.receiveShadow = true; G.add(m);
          if (h > 2 && y === 0 && x % 3 === 1 && x > 1 && x < W - 2) { const w = new THREE.Mesh(new THREE.PlaneGeometry(1.7, 1.25), winMat); w.position.set(gx(x + .5), 1.55, gz(y + 1) + .02); G.add(w); }
          if (h > 2 && x === 0 && y % 3 === 1 && y > 1 && y < H - 2) { const w = new THREE.Mesh(new THREE.PlaneGeometry(1.7, 1.25), winMat); w.rotation.y = Math.PI / 2; w.position.set(gx(x + 1) + .02, 1.55, gz(y + .5)); G.add(w); }
        } else if (t.door) { const m = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), mat(0xB8A688)); m.rotation.x = -Math.PI / 2; m.position.set(gx(x + .5), .02, gz(y + .5)); m.receiveShadow = true; G.add(m); }
      }
      const chairAt = (x, y, face, c) => { const gg = new THREE.Group(); gg.position.set(gx(x + .5), 0, gz(y + .5)); G.add(gg); bx(gg, .5, .08, .5, c, 0, .38, 0); bx(gg, .5, .5, .07, shade('#' + c.toString(16).padStart(6, '0'), -25), -face[0] * .22, .65, -face[1] * .22); bx(gg, .06, .38, .06, 0x374151, 0, .19, 0); };
      let sci = 0;
      for (const f of F.furniture) {
        const w = f.w || 1, h = f.h || 1, gg = new THREE.Group(); gg.position.set(gx(f.x + w / 2), 0, gz(f.y + h / 2)); if (f.rot) gg.rotation.y = f.rot; G.add(gg);
        const leg = (c, hh, ox, oz) => bx(gg, .08, hh, .08, c, ox, hh / 2, oz), wh = wallH(f.x, f.y), wy = Math.min(1.55, wh * .55), wsz = Math.min(1.2, wh * .62);
        switch (f.t) {
          case 'desk': {
            bx(gg, w * .96, .07, .8, 0xE8E2D4, 0, .72, 0); for (const sx of [-1, 1]) for (const sz of [-1, 1]) leg(0x8A8F9C, .72, sx * (w / 2 - .12), sz * .3);
            const nm = w >= 4 ? 3 : w >= 3 ? 2 : 1, list = []; for (let k = 0; k < nm; k++) {
              const sc = new THREE.Mesh(new THREE.BoxGeometry(.62, .42, .05), new THREE.MeshLambertMaterial({ color: 0x0B1020, emissive: f.owner ? 0x112244 : 0x0A0F1C })); sc.position.set((k - (nm - 1) / 2) * .9, 1.0, -.1); sc.castShadow = true; gg.add(sc); list.push(sc); bx(gg, .1, .2, .1, 0x333844, (k - (nm - 1) / 2) * .9, .85, -.1);
            }
            if (f.owner) screens[f.owner] = list; bx(gg, .4, .03, .16, 0xD1D5DB, 0, .77, .18); break;
          }
          case 'chair': chairAt(f.x, f.y, OS_FACE[f.face] || [0, -1], 0x4B5563); gg.visible = false; break;
          case 'table': { const lo = f.low; bx(gg, w * .96, .07, h * .9, f.c, 0, lo ? .38 : .7, 0); for (const sx of [-1, 1]) for (const sz of [-1, 1]) leg(0x4A3828, lo ? .38 : .7, sx * (w / 2 - .12), sz * (h / 2 - .12)); break; }
          case 'rug': bx(gg, w, .02, h, f.c, 0, .025, 0, null, true).receiveShadow = true; break;
          case 'shelf': { bx(gg, w * .96, 1.25, .5, 0x7A5A3C, 0, .63, 0); const cols = [0xEF4444, 0x3B82F6, 0xF59E0B, 0x10B981, 0xA78BFA, 0xF472B6]; for (let i = 0; i < w * 4; i++) for (let r = 0; r < 3; r++) bx(gg, .16, .26, .06, cols[(i * 3 + r * 5) % cols.length], -w / 2 + .15 + i * .24, .3 + r * .35, .27, null, true); break; }
          case 'sofa': bx(gg, w, .35, .85, f.c, 0, .2, .02); bx(gg, w, .55, .22, shade(f.c, -25), 0, .55, -.32); for (const sx of [-1, 1]) bx(gg, .2, .5, .85, shade(f.c, -15), sx * (w / 2 - .1), .3, .02); break;
          case 'tv': bx(gg, w * .9, wsz * .6, .06, 0x0B0C10, 0, wy, .56, { emissive: 0x1D3A6B }); break;
          case 'whiteboard': bx(gg, w * .9, wsz * .6, .05, 0xF3F4F6, 0, wy, .54); bx(gg, .5, .04, .02, 0xEF4444, -.2, wy + .1, .58, null, true); bx(gg, .4, .04, .02, 0x3B82F6, .2, wy - .1, .58, null, true); break;
          case 'screenwall': { const m = new THREE.Mesh(new THREE.PlaneGeometry(w * .94, wsz), basicTex(screenTex(f.c, ++sci), { side: THREE.DoubleSide })); m.position.set(0, wy, .52); gg.add(m); bx(gg, w * .98, wsz + .1, .04, 0x111827, 0, wy, .5, null, true); break; }
          case 'sign': { const m = new THREE.Mesh(new THREE.PlaneGeometry(w * .9, w * .9 * 96 / 512), basicTex(signCanvas(f.text || ''), { side: THREE.DoubleSide })); m.position.set(0, f.float ? 2.3 : wy, f.float ? 0 : .52); gg.add(m); if (f.float) { bx(gg, .08, 1.7, .08, 0x6B7280, -w * .42, 1.2, 0, null, true); bx(gg, .08, 1.7, .08, 0x6B7280, w * .42, 1.2, 0, null, true); } break; }
          case 'arcade': bx(gg, .7, 1.2, .6, 0x1E3A8A, 0, .6, 0); bx(gg, .5, .35, .05, 0x111827, 0, .95, .31, { emissive: 0x22D3EE }); bx(gg, .6, .1, .3, 0xEF4444, 0, .62, .35); break;
          case 'rack': bx(gg, .85, 1.3, .8, 0x1F2937, 0, .65, 0); for (let i = 0; i < 5; i++) { bx(gg, .6, .04, .02, 0x374151, 0, .25 + i * .22, .41, null, true); bx(gg, .05, .05, .02, i % 2 ? 0x22C55E : 0x38BDF8, .25, .25 + i * .22, .42, { emissive: i % 2 ? 0x22C55E : 0x38BDF8 }, true); } break;
          case 'cube': { bx(gg, w * .9, .15, h * .9, 0x1F2937, 0, .08, 0); for (let k = 0; k < 3; k++) { bx(gg, .6, 1.5, .6, 0x1F2937, (k - 1) * 1.0, .85, -.3); bx(gg, .5, .05, .02, 0x38BDF8, (k - 1) * 1.0, 1.4, .02, { emissive: 0x38BDF8 }, true); bx(gg, .5, .05, .02, 0x22C55E, (k - 1) * 1.0, 1.0, .02, { emissive: 0x22C55E }, true); }
            const gm = new THREE.MeshLambertMaterial({ color: 0x7FD3FF, transparent: true, opacity: .22, depthWrite: false }); const gl = new THREE.Mesh(new THREE.BoxGeometry(w * .96, 2.1, h * .96), gm); gl.position.y = 1.1; gg.add(gl); glass.push(gm); break; }
          case 'booth': { bx(gg, w * .96, .12, h * .96, 0x2A2535, 0, .06, 0); bx(gg, w * .9, 1.7, .12, 0x3B3148, 0, .95, -h / 2 + .15); bx(gg, .12, 1.7, h * .9, 0x3B3148, -w / 2 + .15, .95, 0); bx(gg, .1, .9, .1, 0x9CA3AF, 0, .5, 0); bx(gg, .26, .16, .1, 0x111827, 0, 1.05, .05);
            const gm = new THREE.MeshLambertMaterial({ color: 0xBFE6FF, transparent: true, opacity: .2, depthWrite: false }); const gl = new THREE.Mesh(new THREE.BoxGeometry(w * .96, 1.9, h * .96), gm); gl.position.y = 1.0; gg.add(gl); glass.push(gm); break; }
          case 'holo': { bx(gg, .5, .12, .5, 0x1F2937, 0, .06, 0); const hm = new THREE.MeshBasicMaterial({ color: 0x38BDF8, transparent: true, opacity: .55 }); const hc = new THREE.Mesh(new THREE.BoxGeometry(.45, .45, .45), hm); hc.position.y = 1.0; hc.rotation.set(.6, .6, 0); gg.add(hc); elev.push(hc); break; }
          case 'pool': { bx(gg, w, .2, h, 0xE5E7EB, 0, .1, 0); const wm = new THREE.MeshLambertMaterial({ color: 0x38BDF8, emissive: 0x0B4A7A }); const wt = new THREE.Mesh(new THREE.BoxGeometry(w - .5, .1, h - .5), wm); wt.position.y = .22; gg.add(wt); break; }
          case 'rcpt': bx(gg, w, .9, h * .7, 0xE8D8C0, 0, .45, -.2); bx(gg, w, .08, h * .8, 0xB08A5C, 0, .93, -.2); bx(gg, w * .9, .08, .04, 0xFFD027, 0, .5, .2, { emissive: 0xFFD027 }, true); bx(gg, .5, .4, .06, 0x0B1020, -w / 4, 1.2, -.3, { emissive: 0x112244 }); break;
          case 'liftpad': { const lm = new THREE.MeshBasicMaterial({ color: 0x22D3EE, transparent: true, opacity: .55 }); const ring = new THREE.Mesh(new THREE.CylinderGeometry(1.1, 1.1, .05, 28), lm); ring.position.y = .04; gg.add(ring); bx(gg, 2.4, .06, 2.4, 0x2B3A4A, 0, .02, 0, null, true); break; }
          case 'cooler': bx(gg, .5, .9, .5, 0xE5E7EB, 0, .45, 0); bx(gg, .34, .4, .34, 0x60A5FA, 0, 1.1, 0, { transparent: true, opacity: .8 }); break;
          case 'counter': bx(gg, w, .8, .8, 0x7A5A3C, 0, .4, 0); bx(gg, w, .06, .86, 0xE5E7EB, 0, .83, 0); bx(gg, .35, .35, .3, 0x374151, -w / 2 + .5, 1.03, 0); bx(gg, .08, .08, .02, 0xEF4444, -w / 2 + .5, 1.1, .16, { emissive: 0xEF4444 }, true); break;
          case 'fridge': bx(gg, .85, 1.35, .85, 0xF3F4F6, 0, .68, 0); bx(gg, .05, .5, .05, 0x9CA3AF, .3, .9, .45); break;
          case 'plant': bx(gg, .32, .26, .32, 0x92400E, 0, .13, 0); bx(gg, .44, .34, .44, 0x16A34A, 0, .45, 0); bx(gg, .3, .3, .3, 0x22C55E, 0, .75, 0); break;
          case 'tree': bx(gg, .28, .7, .28, 0x78350F, 0, .35, 0); bx(gg, 1.0, .7, 1.0, 0x15803D, 0, 1.0, 0); bx(gg, .7, .6, .7, 0x22C55E, 0, 1.55, 0); break;
          case 'flower': bx(gg, .5, .12, .5, 0x166534, 0, .06, 0); for (let i = 0; i < 4; i++) bx(gg, .1, .1, .1, [0xF472B6, 0xFACC15, 0xFFFFFF, 0xFB923C][i], -.15 + (i % 2) * .3, .2, -.15 + (i >> 1) * .3, null, true); break;
          case 'armchair': bx(gg, .8, .35, .8, 0x7C3AED, 0, .2, 0); bx(gg, .8, .55, .2, 0x6D28D9, 0, .55, .32); for (const sx of [-1, 1]) bx(gg, .15, .45, .8, 0x6D28D9, sx * .33, .3, 0); break;
          case 'treadmill': bx(gg, .7, .14, .95, 0x1F2937, 0, .1, 0); bx(gg, .55, .02, .8, 0x4B5563, 0, .18, 0); bx(gg, .6, .5, .06, 0x111827, 0, .85, -.4, { emissive: 0x0E7490 }); bx(gg, .05, .7, .05, 0x9CA3AF, -.28, .5, -.4); bx(gg, .05, .7, .05, 0x9CA3AF, .28, .5, -.4); break;
          case 'pingpong': bx(gg, w * .96, .07, h * .95, 0x1D4ED8, 0, .7, 0); bx(gg, .03, .02, h * .95, 0xFFFFFF, 0, .74, 0, null, true); bx(gg, .04, .18, h * .95, 0xE5E7EB, 0, .8, 0, { transparent: true, opacity: .8 }, true); for (const sx of [-1, 1]) for (const sz of [-1, 1]) leg(0x374151, .7, sx * (w / 2 - .12), sz * (h / 2 - .12)); break;
          case 'dumbbell': bx(gg, .8, .5, .4, 0x374151, 0, .25, 0); for (const sx of [-1, 1]) { bx(gg, .2, .14, .14, 0x111827, sx * .22, .6, 0); bx(gg, .3, .05, .05, 0x9CA3AF, sx * .22, .6, 0); } break;
          case 'bench': bx(gg, w, .1, .5, 0x92400E, 0, .38, 0); bx(gg, w, .4, .08, 0x78350F, 0, .6, -.24); for (const sx of [-1, 1]) bx(gg, .1, .38, .5, 0x5A3A1E, sx * (w / 2 - .1), .19, 0); break;
        }
      }
      for (const s of sim.floors[fi].spots) if (s.chair) chairAt(s.x, s.y, s.face, s.desk ? deskColor[s.owner] : 0x6B7280);
      return G;
    }
    for (let fi = 0; fi < NF; fi++) buildFloor(fi);

    // ---------- karakter sprite ----------
    const CHAR_H = 2.05, VS = 1.18;
    function makeChar(a) {
      const m = metaOf(a.id), gg = new THREE.Group(), c = { a, g: gg, m, key: '' };
      const cv = document.createElement('canvas'); cv.width = m.w; cv.height = m.h; c.cv = cv; c.cx = cv.getContext('2d');
      c.tex = new THREE.CanvasTexture(cv); c.tex.generateMipmaps = false; c.tex.minFilter = THREE.LinearFilter; c.tex.magFilter = THREE.NearestFilter;
      const ph = (m.h / m.idleH) * CHAR_H * VS, pw = ph * m.w / m.h, geo = new THREE.PlaneGeometry(pw, ph); geo.translate(0, ph / 2 - ((m.h - m.foot) / m.h) * ph, 0);
      c.smat = new THREE.MeshBasicMaterial({ map: c.tex, transparent: true, alphaTest: .45, side: THREE.DoubleSide }); c.mesh = new THREE.Mesh(geo, c.smat); c.mesh.renderOrder = 2;
      c.shadow = new THREE.Mesh(new THREE.CircleGeometry(.45, 18), new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: .3, depthWrite: false })); c.shadow.rotation.x = -Math.PI / 2; c.shadow.position.y = .03; c.shadow.scale.set(1, .62, 1);
      c.sel = new THREE.Mesh(new THREE.RingGeometry(.5, .62, 24), new THREE.MeshBasicMaterial({ color: 0xFFD027, transparent: true, opacity: .95, side: THREE.DoubleSide })); c.sel.rotation.x = -Math.PI / 2; c.sel.position.y = .04; c.sel.scale.set(1, .62, 1); c.sel.visible = false;
      c.ring = new THREE.Mesh(new THREE.TorusGeometry(.34, .04, 6, 20), new THREE.MeshBasicMaterial({ color: 0xA78BFA })); c.ring.rotation.x = Math.PI / 2; c.ring.position.y = CHAR_H * VS + .25; c.ring.visible = false;
      gg.add(c.shadow, c.mesh, c.sel, c.ring); scene.add(gg); return c;
    }
    function paintChar(c, s) {
      const key = s.idx + '|' + s.sit + '|' + s.icon + '|' + (SPR.ready ? 1 : 0); if (key === c.key) return; c.key = key;
      c.cx.clearRect(0, 0, c.m.w, c.m.h); drawFrame(c.cx, c.a.id, s, 0, 0, 1); c.tex.needsUpdate = true;
    }
    const chars = sim.agents.map(makeChar), charById = {}; chars.forEach(c => charById[c.a.id] = c);

    // ---------- tema siang / malam ----------
    function applyTheme() {
      const n = night;
      scene.background = new THREE.Color(n ? 0x0A1026 : 0xBFE3F7); groundMat.color.setHex(n ? 0x1F3B2C : 0x7BA05B);
      hemi.color.setHex(n ? 0x7F94D6 : 0xffffff); hemi.groundColor.setHex(n ? 0x1B2240 : 0x6b7a5a); hemi.intensity = n ? .78 : .6;
      sun.color.setHex(n ? 0x9DB4FF : 0xfff4e0); sun.intensity = n ? .28 : .62; winMat.color.setHex(n ? 0xFFD27A : 0xA8D4F5);
      trees.forEach((m, i) => m.color.setHex(n ? [0x1F4A2A, 0x265A33, 0x1A3F26][i % 3] : [0x4E8F3A, 0x5FA046, 0x3F7D32][i % 3])); glass.forEach(m => m.opacity = n ? .32 : .22);
      for (const c of chars) c.smat.color.setHex(n ? 0xB4C0F0 : 0xFFFFFF);
      for (const k in screens) for (const sc of screens[k]) sc.material.emissiveIntensity = n ? 2.2 : 1;
    }
    applyTheme();

    // ---------- kamera isometrik ----------
    let th = Math.PI / 4, ph = .95, Zh = 16, Zgoal = 16, zoomed = false, focusOn = false;
    const tgt = new THREE.Vector3(0, fy(1) + .5, 1.2), tgtGoal = tgt.clone();
    const place = () => { cam.position.set(tgt.x + 140 * Math.sin(th) * Math.sin(ph), tgt.y + 140 * Math.cos(ph), tgt.z + 140 * Math.cos(th) * Math.sin(ph)); cam.lookAt(tgt); };
    const aspect = () => (el.clientWidth || 1) / (el.clientHeight || 1);
    const fitZ = () => (viewFloor < 0 ? Math.max(28, 22 / aspect()) : Math.max(14.5, 21 / aspect()));
    const goalFor = () => { if (viewFloor < 0) tgtGoal.set(0, fy(1.5) + .5, 0); else tgtGoal.set(0, fy(viewFloor) + .4, 1.2); };
    const syncVis = () => groups.forEach((G, i) => G.visible = viewFloor < 0 || i <= viewFloor);
    let drag = null, moved = 0; const cv = rd.domElement;
    cv.oncontextmenu = e => e.preventDefault();
    cv.onpointerdown = e => { drag = { x: e.clientX, y: e.clientY, b: e.button }; moved = 0; try { cv.setPointerCapture(e.pointerId); } catch { } };
    cv.onpointerup = e => { const d = drag; drag = null; if (d && moved < 5 && e.button === 0) { const id = pick(e); if (id) selectAgent(id); } };
    cv.onpointermove = e => {
      if (!drag) return; const dx = e.clientX - drag.x, dy = e.clientY - drag.y; moved += Math.abs(dx) + Math.abs(dy); drag.x = e.clientX; drag.y = e.clientY;
      if (drag.b === 2 || e.shiftKey) { const k = Zh * .0022; tgtGoal.x = Math.max(-W, Math.min(W, tgtGoal.x - (dx * Math.cos(th) - dy * Math.sin(th) * .8) * k)); tgtGoal.z = Math.max(-H, Math.min(H, tgtGoal.z + (dx * Math.sin(th) + dy * Math.cos(th) * .8) * k)); follow = null; focusOn = false; paint(); }
      else { th -= dx * .006; ph = Math.min(1.4, Math.max(.45, ph - dy * .006)); }
    };
    cv.onwheel = e => { e.preventDefault(); zoomed = true; Zgoal = Math.min(48, Math.max(4, Zgoal * (1 + e.deltaY * .0012))); };
    const rc = new THREE.Raycaster(), v2 = new THREE.Vector2();
    function pick(e) {
      const r = cv.getBoundingClientRect(); v2.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1); rc.setFromCamera(v2, cam);
      const hit = rc.intersectObjects(chars.filter(c => c.g.visible).map(c => c.mesh), false)[0]; if (!hit) return null; const c = chars.find(k => k.mesh === hit.object); return c ? c.a.id : null;
    }
    const resize = () => { const w = el.clientWidth, h = el.clientHeight; if (!w || !h) return; rd.setSize(Math.max(2, Math.round(w / PX)), Math.max(2, Math.round(h / PX)), false); if (!zoomed && !focusOn) Zgoal = fitZ(); };
    const ro = new ResizeObserver(resize); ro.observe(el); resize(); syncVis(); goalFor(); tgt.copy(tgtGoal); Zh = Zgoal; place();
    const home = () => { zoomed = false; focusOn = false; goalFor(); resize(); };

    const pv = new THREE.Vector3();
    function updateLabels() {
      const w = el.clientWidth, h = el.clientHeight, items = [];
      for (const c of chars) {
        const a = c.a, L = labs[a.id], fl = a.floor, vis0 = !a.lifting && (viewFloor < 0 || fl <= viewFloor);
        pv.set(gx(a.x), fy(fl) + CHAR_H * VS + .12 - (c.sitNow ? .1 : 0), gz(a.y)).project(cam);
        const vis = vis0 && Math.abs(pv.x) < 1.08 && Math.abs(pv.y) < 1.08; L.d.style.display = vis ? '' : 'none'; if (!vis) continue;
        const t = a.bubble || ''; if (t !== L.txt) { L.txt = t; L.bb.textContent = t; L.bb.hidden = !t; L.w = L.h = 0; }
        if (!L.w) { L.w = L.d.offsetWidth || 120; L.h = L.d.offsetHeight || 40; }
        items.push({ L, x: Math.round((pv.x * .5 + .5) * w), y: Math.round((-pv.y * .5 + .5) * h) });
      }
      items.sort((p, q) => q.y - p.y); const placed = [];
      for (const it of items) {
        for (let n = 0; n < 8; n++) { const hit = placed.find(r => Math.abs(r.x - it.x) < (r.L.w + it.L.w) / 2 + 4 && it.y - it.L.h < r.y && it.y > r.y - r.L.h); if (!hit) break; it.y = hit.y - hit.L.h - 4; }
        placed.push(it); it.L.d.style.transform = `translate(${it.x}px,${it.y}px) translate(-50%,-100%)`;
      }
    }
    let prevT = 0;
    return {
      resize, theme: applyTheme, rot(d) { th += d; },
      ctl: { set(a, b, c) { th = a; ph = b; Zgoal = Zh = c; zoomed = true; } },
      setFloor() { syncVis(); if (!focusOn) { zoomed = false; goalFor(); Zgoal = fitZ(); } },
      reset() { th = Math.PI / 4; ph = .95; home(); follow = null; paint(); },
      focusTile(x, y, zz, fl) { focusOn = true; tgtGoal.set(gx(x + .5), fy(fl || 0) + .4, gz(y + .5)); Zgoal = zz; }, unfocus() { if (focusOn) home(); },
      key(k) {
        if (k === 'ArrowLeft') th += .09; else if (k === 'ArrowRight') th -= .09; else if (k === 'ArrowUp') ph = Math.max(.45, ph - .05); else if (k === 'ArrowDown') ph = Math.min(1.4, ph + .05);
        else if (k === '+' || k === '=') { zoomed = true; Zgoal = Math.max(4, Zgoal * .88); } else if (k === '-' || k === '_') { zoomed = true; Zgoal = Math.min(48, Zgoal * 1.14); } else if (k === '0') { this.reset(); } else return false;
        return true;
      },
      destroy() { try { ro.disconnect && ro.disconnect(); rd.dispose(); } catch { } rd.domElement.remove(); },
      render(t) {
        const dt = Math.min(.1, t - prevT || .016); prevT = t;
        for (const c of chars) {
          const a = c.a, s = spriteFor(a, t); c.sitNow = s.sit; paintChar(c, s); const vis = !a.lifting && (viewFloor < 0 || a.floor <= viewFloor); c.g.visible = vis; if (!vis) continue;
          c.mesh.rotation.y = th; c.mesh.scale.x = s.flip ? -1 : 1; c.g.position.set(gx(a.x) + (a.fx === 'alert' ? Math.sin(t * 60) * .03 : 0), fy(a.floor), gz(a.y));
          c.ring.visible = !!a.fx; if (a.fx) { c.ring.rotation.z = t * 5; c.ring.material.color.setHex(a.fx === 'alert' ? 0xEF4444 : 0xA78BFA); } c.sel.visible = follow === a.id;
        }
        for (const e of elev) { e.rotation.y += dt * 1.2; e.position.y = 1.0 + Math.sin(t * 2 + e.id) * .06; }
        for (const a of sim.agents) {
          const list = screens[a.id]; if (!list) continue; let col = 0x112244; const here = !a.lifting && a.arrived && a.target.desk && a.target.owner === a.id;
          if (here && a.work) col = a.fx === 'render' ? (Math.sin(t * 8) > 0 ? 0x7C3AED : 0x4C1D95) : a.fx === 'alert' ? 0xDC2626 : (SCREEN[a.pose] || 0x2563EB); for (const sc of list) sc.material.emissive.setHex(col);
        }
        const f = follow && charById[follow]; if (f) { if (viewFloor >= 0 && viewFloor !== f.a.floor && !f.a.lifting) setFloor(f.a.floor); tgtGoal.set(gx(f.a.x), fy(f.a.floor) + .5, gz(f.a.y)); focusOn = false; }
        const k = REDUCED ? 1 : 1 - Math.exp(-dt * 3.4); Zh += (Zgoal - Zh) * k; tgt.lerp(tgtGoal, REDUCED ? 1 : 1 - Math.exp(-dt * 4));
        const as = aspect(); cam.left = -Zh * as; cam.right = Zh * as; cam.top = Zh; cam.bottom = -Zh; cam.updateProjectionMatrix(); place(); rd.render(scene, cam); updateLabels();
      },
    };
  }

  // ===================================================================
  //  2D — pixel art per lantai (16px/tile); lantai tunggal atau 2x2 seluruh gedung; siang/malam
  // ===================================================================
  function init2D() {
    const TS = 16, M = 2, MY = 1, LW = (W + 2 * M) * TS, LH = (H + 2 * MY) * TS, OX = M * TS, OY = MY * TS, CHAR_TILES = 1.75;
    const cv = g('o2d'), m = cv.getContext('2d'), mk = () => { const c = document.createElement('canvas'); c.width = LW; c.height = LH; return c; };
    const lcs = FLOORS.map(mk), ctxs = lcs.map(c => c.getContext('2d')), bg = mk(), b = bg.getContext('2d'), bgN = mk();
    let c = ctxs[0], glows = []; const R = (x, y, w, h, col) => { c.fillStyle = col; c.fillRect(Math.round(x) + OX, Math.round(y) + OY, w, h); };
    const GL = (x, y, w, h, col) => { if (night) glows.push([x + OX, y + OY, w, h, col]); };
    const grass = () => (night ? '#27432F' : '#B5DB9C');
    { let sd = 5; const rn = () => (sd = (sd * 16807) % 2147483647) / 2147483647; b.fillStyle = '#B5DB9C'; b.fillRect(0, 0, LW, LH);
      for (let i = 0; i < 260; i++) { b.fillStyle = i % 3 ? '#A5CD8B' : '#C4E6AE'; b.fillRect((rn() * LW) | 0, (rn() * LH) | 0, 2, 1); }
      const tree = (x, y) => { b.fillStyle = 'rgba(0,0,0,.12)'; b.fillRect(x - 5, y + 10, 12, 3); b.fillStyle = '#7A4A22'; b.fillRect(x, y + 6, 3, 6); b.fillStyle = '#3F8F3A'; b.fillRect(x - 5, y - 4, 13, 11); b.fillStyle = '#58AE4C'; b.fillRect(x - 3, y - 6, 9, 6); b.fillStyle = '#2F7A2E'; b.fillRect(x - 5, y + 3, 13, 3); };
      for (let i = 0; i < 26; i++) { const x = (rn() * (LW - 16) + 8) | 0, y = (rn() * (LH - 16) + 8) | 0; if (x > OX - 6 && x < OX + W * TS + 6 && y > OY - 6 && y < OY + H * TS + 6) continue; tree(x, y); }
      const n = bgN.getContext('2d'); n.drawImage(bg, 0, 0); n.globalCompositeOperation = 'multiply'; n.fillStyle = '#4D5F9A'; n.fillRect(0, 0, LW, LH); }
    const owners = {}; sim.agents.forEach(a => owners[a.id] = a);

    function drawFurn(f, t, wallArt) {
      const x = f.x * TS, y = f.y * TS, w = (f.w || 1) * TS, h = (f.h || 1) * TS;
      switch (f.t) {
        case 'rug': R(x + 1, y + 1, w - 2, h - 2, f.c); R(x + 3, y + 3, w - 6, 1, shade(f.c, 25)); R(x + 3, y + h - 4, w - 6, 1, shade(f.c, 25)); break;
        case 'desk': {
          R(x + 1, y + 2, w - 2, h - 5, '#E8E2D4'); R(x + 1, y + h - 3, w - 2, 2, '#9AA0AC'); const a = owners[f.owner], nm = w >= 4 * TS ? 3 : w >= 3 * TS ? 2 : 1;
          let col = f.owner ? '#112244' : '#1B2438'; if (a && a.work && a.arrived && a.target.desk) col = a.fx === 'render' ? (Math.sin(t * 8) > 0 ? '#7C3AED' : '#4C1D95') : a.fx === 'alert' ? '#DC2626' : a.pose === 'speak' ? '#DB2777' : '#2563EB';
          for (let k = 0; k < nm; k++) { const cx = x + w * (k + .5) / nm; R(cx - 5, y + 1, 10, 6, '#0B1020'); R(cx - 4, y + 2, 8, 4, col); R(cx - 1, y + 7, 2, 1, '#333844'); GL(cx - 4, y + 2, 8, 4, col === '#112244' || col === '#1B2438' ? '#2B4A8A' : col); } break;
        }
        case 'chair': R(x + 4, y + 4, 8, 8, '#4B5563'); R(x + 4, y + 11, 8, 2, '#374151'); break;
        case 'table': R(x + 1, y + 2, w - 2, h - 4, f.c); R(x + 1, y + h - 3, w - 2, 2, shade(f.c, -35)); R(x + 2, y + 3, w - 4, 1, shade(f.c, 25)); break;
        case 'shelf': R(x + 1, y + 1, w - 2, h - 2, '#7A5A3C'); for (let i = 0; i < w - 3; i += 3) { R(x + 2 + i, y + 3, 2, 4, ['#EF4444', '#3B82F6', '#F59E0B', '#10B981', '#A78BFA'][(i / 3 | 0) % 5]); R(x + 2 + i, y + 9, 2, 4, ['#F472B6', '#FACC15', '#60A5FA', '#34D399'][(i / 3 | 0) % 4]); } break;
        case 'sofa': R(x + 1, y + 1, w - 2, h - 2, f.c); R(x + 1, y + 1, w - 2, 5, shade(f.c, -30)); R(x + 1, y + h - 3, w - 2, 2, shade(f.c, -45)); for (let i = 1; i < w / TS; i++) R(x + i * TS, y + 6, 1, 8, shade(f.c, -30)); break;
        case 'tv': R(x + 2, y + 2, w - 4, 8, '#0B0C10'); R(x + 3, y + 3, w - 6, 6, '#1D3A6B'); GL(x + 3, y + 3, w - 6, 6, '#3B6AD0'); break;
        case 'whiteboard': R(x + 2, y + 2, w - 4, 9, '#F3F4F6'); R(x + 5, y + 4, 8, 1, '#EF4444'); R(x + 7, y + 7, 10, 1, '#3B82F6'); break;
        case 'screenwall': { R(x + 1, y + 1, w - 2, 12, '#0B1220'); const n = Math.max(2, Math.floor(w / 28)); for (let i = 0; i < n; i++) { const sx = x + 3 + i * ((w - 6) / n); R(sx, y + 3, (w - 6) / n - 3, 8, '#152238'); for (let k = 0; k < 5; k++) R(sx + 2 + k * 4, y + 10 - ((k * 5 + i * 3 + (t * 2 | 0)) % 6 + 2), 2, ((k * 5 + i * 3 + (t * 2 | 0)) % 6 + 2), f.c); GL(sx, y + 3, (w - 6) / n - 3, 8, f.c); } break; }
        case 'sign': R(x + 2, y + 3, w - 4, 8, '#10131C'); R(x + 3, y + 4, w - 6, 1, '#FFD027'); R(x + 3, y + 9, w - 6, 1, '#FFD027'); for (let i = 0; i < (w - 14) / 4; i++) R(x + 7 + i * 4, y + 6, 2, 2, '#FFD027'); GL(x + 3, y + 4, w - 6, 6, '#FFD027'); break;
        case 'arcade': R(x + 3, y + 1, 10, 14, '#1E3A8A'); R(x + 4, y + 3, 8, 5, '#22D3EE'); R(x + 5, y + 10, 6, 2, '#EF4444'); GL(x + 4, y + 3, 8, 5, '#22D3EE'); break;
        case 'rack': R(x + 1, y + 1, 14, 14, '#1F2937'); for (let i = 0; i < 4; i++) { R(x + 3, y + 3 + i * 3, 7, 1, '#374151'); const lc = (i + (t * 2 | 0)) % 2 ? '#22C55E' : '#38BDF8'; R(x + 11, y + 3 + i * 3, 2, 1, lc); GL(x + 11, y + 3 + i * 3, 2, 1, lc); } break;
        case 'cube': R(x + 1, y + 1, w - 2, h - 2, '#1F2937'); R(x + 2, y + 2, w - 4, h - 4, '#16324A'); for (let i = 0; i < 3; i++) { R(x + 6 + i * 16, y + 5, 10, h - 12, '#0F1B2B'); for (let k = 0; k < 4; k++) { const lc = (i + k + (t * 2 | 0)) % 2 ? '#22C55E' : '#38BDF8'; R(x + 8 + i * 16, y + 8 + k * 6, 6, 1, lc); GL(x + 8 + i * 16, y + 8 + k * 6, 6, 1, lc); } } R(x, y, w, 1, '#7FD3FF'); R(x, y + h - 1, w, 1, '#7FD3FF'); break;
        case 'booth': R(x + 1, y + 1, w - 2, h - 2, '#2A2535'); R(x + 3, y + 3, w - 6, h - 6, '#3B3148'); R(x, y, w, 1, '#BFE6FF'); R(x, y + h - 1, w, 1, '#BFE6FF'); R(x + w / 2 - 1, y + h / 2 - 4, 2, 8, '#9CA3AF'); break;
        case 'holo': R(x + 4, y + 10, 8, 4, '#1F2937'); R(x + 5, y + 3, 6, 6, '#38BDF8'); R(x + 6, y + 4, 4, 4, '#BAE6FD'); GL(x + 5, y + 3, 6, 6, '#38BDF8'); break;
        case 'pool': R(x + 1, y + 1, w - 2, h - 2, '#E5E7EB'); R(x + 3, y + 3, w - 6, h - 6, '#38BDF8'); for (let i = 0; i < 6; i++) R(x + 6 + ((i * 11 + (t * 6 | 0)) % (w - 14)), y + 7 + (i * 7) % (h - 14), 4, 1, '#BAE6FD'); break;
        case 'rcpt': R(x + 1, y + 2, w - 2, h - 4, '#E8D8C0'); R(x + 1, y + 2, w - 2, 5, '#B08A5C'); R(x + 3, y + h - 5, w - 6, 1, '#FFD027'); R(x + 5, y + 3, 8, 5, '#0B1020'); GL(x + 3, y + h - 5, w - 6, 1, '#FFD027'); break;
        case 'liftpad': { R(x + 2, y + 2, w - 4, h - 4, '#2B3A4A'); R(x + w / 2 - 14, y + h / 2 - 14, 28, 28, '#22D3EE'); R(x + w / 2 - 12, y + h / 2 - 12, 24, 24, '#16324A'); R(x + w / 2 - 6, y + h / 2 - 1, 12, 2, '#22D3EE'); R(x + w / 2 - 1, y + h / 2 - 6, 2, 12, '#22D3EE'); GL(x + w / 2 - 14, y + h / 2 - 14, 28, 28, '#22D3EE'); break; }
        case 'cooler': R(x + 4, y + 5, 8, 10, '#E5E7EB'); R(x + 5, y + 1, 6, 5, '#60A5FA'); break;
        case 'counter': R(x + 1, y + 3, w - 2, h - 5, '#7A5A3C'); R(x + 1, y + 2, w - 2, 3, '#E5E7EB'); R(x + 4, y + 1, 6, 5, '#374151'); R(x + 6, y + 3, 2, 1, '#EF4444'); break;
        case 'fridge': R(x + 2, y + 1, 12, 14, '#F3F4F6'); R(x + 2, y + 6, 12, 1, '#9CA3AF'); R(x + 11, y + 3, 1, 2, '#6B7280'); break;
        case 'plant': R(x + 5, y + 10, 6, 5, '#92400E'); R(x + 3, y + 4, 10, 7, '#16A34A'); R(x + 5, y + 2, 6, 4, '#22C55E'); break;
        case 'tree': R(x + 6, y + 9, 4, 6, '#78350F'); R(x + 1, y + 2, 14, 9, '#15803D'); R(x + 4, y, 8, 5, '#22C55E'); break;
        case 'flower': R(x + 1, y + 5, w - 2, 9, '#166534'); for (let i = 0; i < 5; i++) R(x + 3 + i * 5 - (i > 2 ? 1 : 0), y + 7 + (i % 2) * 3, 2, 2, ['#F472B6', '#FACC15', '#FFFFFF', '#FB923C', '#F472B6'][i]); break;
        case 'armchair': R(x + 2, y + 2, 12, 12, '#7C3AED'); R(x + 2, y + 2, 12, 4, '#6D28D9'); R(x + 1, y + 5, 2, 9, '#6D28D9'); R(x + 13, y + 5, 2, 9, '#6D28D9'); break;
        case 'treadmill': R(x + 2, y + 3, 12, 12, '#1F2937'); R(x + 4, y + 6, 8, 8, '#4B5563'); R(x + 3, y + 1, 10, 4, '#0E7490'); for (let i = 0; i < 3; i++) R(x + 5, y + 7 + i * 3 + ((t * 8 | 0) % 3), 6, 1, '#6B7280'); break;
        case 'pingpong': R(x + 1, y + 2, w - 2, h - 4, '#1D4ED8'); R(x + 1, y + h - 3, w - 2, 2, '#1E3A8A'); R(x + w / 2, y + 2, 1, h - 4, '#E5E7EB'); R(x + 2, y + h / 2 - 1, w - 4, 1, '#93C5FD'); break;
        case 'dumbbell': R(x + 2, y + 4, 12, 10, '#374151'); R(x + 3, y + 6, 3, 3, '#111827'); R(x + 10, y + 6, 3, 3, '#111827'); R(x + 5, y + 7, 6, 1, '#9CA3AF'); break;
        case 'bench': R(x + 1, y + 4, w - 2, h - 8, '#92400E'); R(x + 1, y + 2, w - 2, 3, '#78350F'); R(x + 1, y + h - 5, w - 2, 1, '#5A3A1E'); break;
      }
    }
    function drawFloor(fi, t) {
      c = ctxs[fi]; glows = []; const F = FLOORS[fi], T = sim.floors[fi].tiles; c.setTransform(1, 0, 0, 1, 0, 0); c.globalCompositeOperation = 'source-over'; c.globalAlpha = 1; c.imageSmoothingEnabled = false; c.drawImage(bg, 0, 0);
      for (const r of F.rooms) { const [x0, y0] = r.r; c.drawImage(floorCanvas(r), OX + (x0 + 1) * TSZ, OY + (y0 + 1) * TSZ); }
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) { const tl = T[y][x]; if (tl.wall) { R(x * TS, y * TS, TS, TS, '#5F6176'); R(x * TS, y * TS, TS, 4, '#82849B'); R(x * TS, y * TS + TS - 2, TS, 2, '#4A4B5E'); if (y === 0 && x % 3 === 1 && x > 1 && x < W - 2) { R(x * TS + 2, y * TS + 5, TS - 4, 6, night ? '#FFD27A' : '#A8D4F5'); GL(x * TS + 2, y * TS + 5, TS - 4, 6, '#FFD27A'); } } else if (tl.door) { R(x * TS, y * TS, TS, TS, '#D9CBB0'); R(x * TS + 2, y * TS + 2, TS - 4, TS - 4, '#E6DAC2'); } }
      F.furniture.filter(f => f.t === 'rug').forEach(f => drawFurn(f, t));
      for (const s of sim.floors[fi].spots) if (s.chair) { const x = s.x * TS, y = s.y * TS; R(x + 4, y + 5, 8, 8, '#6B7280'); R(x + 4 + (s.face[0] > 0 ? -2 : s.face[0] < 0 ? 8 : 0), y + 4 + (s.face[1] < 0 ? 8 : s.face[1] > 0 ? -2 : 0), s.face[0] ? 2 : 8, s.face[0] ? 8 : 2, '#4B5563'); }
      F.furniture.filter(f => f.t !== 'rug').slice().sort((a, b) => a.y - b.y).forEach(f => drawFurn(f, t));
      if (night) { c.globalCompositeOperation = 'multiply'; c.fillStyle = '#5566A6'; c.fillRect(OX, OY, W * TS, H * TS); c.globalCompositeOperation = 'lighter'; c.globalAlpha = .75; for (const [x, y, w, h, col] of glows) { c.fillStyle = col; c.fillRect(x - 2, y - 2, w + 4, h + 4); c.globalAlpha = .9; c.fillRect(x, y, w, h); c.globalAlpha = .75; } c.globalCompositeOperation = 'source-over'; c.globalAlpha = 1; }
    }

    const view = { z: 1, px: 0, py: 0, gz: 1, gpx: 0, gpy: 0 }; let cw = 1, ch = 1, dpr = 1;
    const padT = () => (ch > 560 ? 92 : 8), padB = () => (ch > 560 ? 74 : 8);
    const baseY = s => padT() + ((ch - padT() - padB()) - LH * s) / 2, fitOf = () => Math.min(cw / LW, (ch - padT() - padB()) / LH);
    function layouts() {
      if (viewFloor >= 0) { const fit = fitOf(), s = fit * view.z; return [{ fi: viewFloor, s, ox: (cw - LW * s) / 2 + view.px, oy: baseY(s) + view.py, big: true }]; }
      const aw = cw, ah = ch - padT() - padB(), cwid = aw / 2, chei = ah / 2, s = Math.min(cwid / LW, chei / LH) * .98;
      return FLOORS.map((_, fi) => ({ fi, s, ox: (fi % 2) * cwid + (cwid - LW * s) / 2, oy: padT() + (fi >> 1) * chei + (chei - LH * s) / 2, big: false }));
    }
    const xf = () => layouts()[0];
    function resize() { dpr = Math.min(2, window.devicePixelRatio || 1); cw = cv.clientWidth || host.clientWidth; ch = cv.clientHeight || host.clientHeight; if (!cw || !ch) return; cv.width = Math.round(cw * dpr); cv.height = Math.round(ch * dpr); }
    const ro = new ResizeObserver(resize); ro.observe(stage); resize();
    const snap = () => { view.gz = view.z; view.gpx = view.px; view.gpy = view.py; };
    let drag = null, moved = 0; cv.oncontextmenu = e => e.preventDefault();
    cv.onpointerdown = e => { drag = { x: e.clientX, y: e.clientY }; moved = 0; try { cv.setPointerCapture(e.pointerId); } catch { } };
    cv.onpointermove = e => { if (!drag) return; const dx = e.clientX - drag.x, dy = e.clientY - drag.y; moved += Math.abs(dx) + Math.abs(dy); drag.x = e.clientX; drag.y = e.clientY; if (viewFloor >= 0) { view.px += dx; view.py += dy; snap(); } };
    cv.onpointerup = e => {
      drag = null; if (moved >= 5) return; const r = cv.getBoundingClientRect(), mx = e.clientX - r.left, my = e.clientY - r.top; let best = null;
      for (const L of layouts()) for (const a of sim.agents) { if (a.floor !== L.fi || a.lifting) continue; const tx = (mx - L.ox) / L.s / TS - M, ty = (my - L.oy) / L.s / TS - MY; if (Math.abs(tx - a.x) < .7 && ty > a.y - CHAR_TILES - .1 && ty < a.y + .5) best = a.id; }
      if (best) selectAgent(best); else if (viewFloor < 0) { for (const L of layouts()) if (mx > L.ox && mx < L.ox + LW * L.s && my > L.oy && my < L.oy + LH * L.s) { setFloor(L.fi); break; } }
    };
    cv.onwheel = e => { e.preventDefault(); if (viewFloor < 0) return; const r = cv.getBoundingClientRect(), mx = e.clientX - r.left, my = e.clientY - r.top, o = xf(), fit = fitOf(), ux = (mx - o.ox) / o.s, uy = (my - o.oy) / o.s;
      view.z = Math.min(5, Math.max(.7, view.z * (1 - e.deltaY * .0012))); const s2 = fit * view.z; view.px = mx - (cw - LW * s2) / 2 - ux * s2; view.py = my - baseY(s2) - uy * s2; snap(); };
    const centerOn = (tx, ty, z) => { const fit = fitOf(), s2 = fit * z, uxp = (M + tx + .5) * TS * s2, uyp = (MY + ty + .5) * TS * s2; view.gz = z; view.gpx = cw / 2 - uxp - (cw - LW * s2) / 2; view.gpy = (padT() + (ch - padT() - padB()) / 2) - uyp - baseY(s2); };
    return {
      resize, theme() { }, destroy() { try { ro.disconnect && ro.disconnect(); } catch { } }, setFloor() { view.z = 1; view.px = view.py = 0; snap(); },
      reset() { view.z = 1; view.px = view.py = 0; snap(); follow = null; paint(); },
      focusTile(x, y, zz) { centerOn(x, y, zz || 2.2); }, unfocus() { view.gz = 1; view.gpx = view.gpy = 0; },
      key(k) { if (k === 'ArrowLeft') view.px += 40; else if (k === 'ArrowRight') view.px -= 40; else if (k === 'ArrowUp') view.py += 40; else if (k === 'ArrowDown') view.py -= 40; else if (k === '+' || k === '=') view.z = Math.min(5, view.z * 1.15); else if (k === '-' || k === '_') view.z = Math.max(.7, view.z / 1.15); else if (k === '0') { this.reset(); return true; } else return false; snap(); return true; },
      render(t) {
        if (cv.width < 2) resize(); if (cw < 2) return;
        if (view.z !== view.gz || view.px !== view.gpx || view.py !== view.gpy) { const k = REDUCED ? 1 : .12; view.z += (view.gz - view.z) * k; view.px += (view.gpx - view.px) * k; view.py += (view.gpy - view.py) * k; if (Math.abs(view.gz - view.z) < .002) { view.z = view.gz; view.px = view.gpx; view.py = view.gpy; } }
        const L = layouts(); for (const l of L) drawFloor(l.fi, t);
        m.setTransform(1, 0, 0, 1, 0, 0); m.fillStyle = grass(); m.fillRect(0, 0, cv.width, cv.height); m.imageSmoothingEnabled = false;
        for (const l of L) m.drawImage(lcs[l.fi], l.ox * dpr, l.oy * dpr, LW * l.s * dpr, LH * l.s * dpr);
        m.setTransform(dpr, 0, 0, dpr, 0, 0); m.imageSmoothingEnabled = false;
        for (const l of L) {
          const { fi, s, ox, oy, big } = l, tile = TS * s, fs = big ? Math.max(12, Math.min(16, 2.7 * s)) : Math.max(9, Math.min(12, 2.6 * s)); m.textAlign = 'left'; m.textBaseline = 'middle';
          if (!big) { m.font = `700 ${fs + 2}px system-ui,sans-serif`; const tt = `FL.0${fi + 1} · ${FLOORS[fi].name}`, tw = m.measureText(tt).width + 14; m.fillStyle = 'rgba(15,16,20,.85)'; m.fillRect(ox + 4, oy + 4, tw, fs + 12); m.fillStyle = '#FFD027'; m.fillText(tt, ox + 11, oy + 4 + (fs + 12) / 2); }
          if (big) for (const r of FLOORS[fi].rooms) { if (/_cor$/.test(r.id)) continue; const [x0, y0] = r.r; m.font = `600 ${fs}px system-ui,sans-serif`; const tw = m.measureText(r.name).width + 10, X = ox + (M + x0 + 1) * tile + 5, Y = oy + (MY + y0 + 1) * tile + 5; m.fillStyle = 'rgba(255,255,255,.9)'; m.fillRect(X, Y, tw, fs + 6); m.fillStyle = '#374151'; m.fillText(r.name, X + 5, Y + (fs + 6) / 2 + 1); }
          const list = sim.agents.filter(a => a.floor === fi && !a.lifting).sort((p, q) => p.y - q.y), tags = [];
          for (const a of list) {
            const sp = spriteFor(a, t), mt = sp.m, k = tile * CHAR_TILES / mt.idleH, X = ox + (M + a.x) * tile, Y = oy + (MY + a.y + .38) * tile;
            m.fillStyle = 'rgba(0,0,0,.28)'; m.beginPath(); m.ellipse(X, Y, tile * .42, tile * .2, 0, 0, 7); m.fill();
            if (follow === a.id) { m.strokeStyle = '#FFD027'; m.lineWidth = 2; m.beginPath(); m.ellipse(X, Y, tile * .55, tile * .27, 0, 0, 7); m.stroke(); }
            m.save(); m.translate(X, Y - mt.foot * k); if (night) m.globalAlpha = .92; if (sp.flip) { m.scale(-1, 1); m.translate(-mt.w * k / 2, 0); drawFrame(m, a.id, sp, 0, 0, k); } else drawFrame(m, a.id, sp, -mt.w * k / 2, 0, k); m.restore(); m.globalAlpha = 1;
            tags.push([a, X, Y - (mt.idleH - (sp.sit ? 7 : 0)) * k]);
            if (a.fx) { m.fillStyle = a.fx === 'alert' ? '#EF4444' : '#A78BFA'; for (let i = 0; i < 6; i++) { const an = t * 5 + i * 1.047; m.fillRect(X + Math.cos(an) * tile * .5 - 2, Y - (mt.idleH + 6) * k + Math.sin(an) * 4, 4, 4); } }
          }
          m.textAlign = 'center'; const placed = [];
          for (const [a, X, Yh] of tags) {
            const Y = Yh - 6;
            if (!big) { m.font = `700 ${fs}px system-ui,sans-serif`; const nw = m.measureText(a.name).width + 8; m.fillStyle = 'rgba(15,16,20,.9)'; m.fillRect(X - nw / 2, Y - fs - 4, nw, fs + 4); m.fillStyle = '#fff'; m.fillText(a.name, X, Y - fs / 2 - 2); continue; }
            m.font = `700 ${fs}px system-ui,sans-serif`; const nw = Math.max(m.measureText(a.name).width, (m.font = `500 ${fs - 1}px system-ui,sans-serif`, m.measureText(a.role).width)) + 12, ph = fs * 2 + 7;
            m.fillStyle = 'rgba(15,16,20,.92)'; m.fillRect(X - nw / 2, Y - ph, nw, ph); m.fillStyle = '#fff'; m.font = `700 ${fs}px system-ui,sans-serif`; m.fillText(a.name, X, Y - ph + fs / 2 + 3); m.fillStyle = '#E7C04A'; m.font = `500 ${fs - 1}px system-ui,sans-serif`; m.fillText(a.role, X, Y - ph + fs * 1.5 + 4);
            if (a.bubble) {
              m.font = `600 ${fs}px system-ui,sans-serif`; const lim = 180, lines = []; let cur = ''; for (const wd of a.bubble.split(' ')) { if (m.measureText((cur + ' ' + wd).trim()).width > lim) { lines.push(cur); cur = wd; } else cur = (cur + ' ' + wd).trim(); } lines.push(cur);
              const LL = lines.slice(0, 3), lh = fs + 4, bw = Math.min(lim + 14, Math.max(...LL.map(l => m.measureText(l).width)) + 14), bh = LL.length * lh + 8; let by = Y - ph - 8 - bh;
              for (let n = 0; n < 5 && placed.some(r => Math.abs(r.x - X) < (r.w + bw) / 2 + 4 && by < r.y + r.h + 3 && by + bh + 3 > r.y); n++) by -= bh + 6; placed.push({ x: X, y: by, w: bw, h: bh });
              m.fillStyle = 'rgba(255,255,255,.97)'; m.fillRect(X - bw / 2, by, bw, bh); m.fillRect(X - 3, by + bh, 6, 4); m.fillStyle = '#111317'; LL.forEach((l, i) => m.fillText(l + (i === 2 && lines.length > 3 ? '…' : ''), X, by + 4 + lh / 2 + i * lh));
            }
          }
        }
      },
    };
  }

  // ===================================================================
  //  mode, panel, console, chat
  // ===================================================================
  function selectAgent(id) { follow = follow === id ? null : id; if (follow) { const a = sim.byId[id]; if (viewFloor >= 0 && a.floor !== viewFloor) setFloor(a.floor); } if (id === 'ceo' && follow) openChat(true); paint(); }
  function setFloor(i) {
    viewFloor = Math.max(-1, Math.min(NF - 1, i)); store.set(FLOOR_KEY, String(viewFloor)); if (viewFloor < 0) follow = null;
    if (r3) r3.setFloor(); if (r2) r2.setFloor(); renderBuild();
  }
  const bgColor = () => (mode === '3d' ? (night ? '#0A1026' : '#BFE3F7') : (night ? '#27432F' : '#B5DB9C'));
  function setNight(n) { night = !!n; store.set(NIGHT_KEY, night ? '1' : '0'); const b = g('oNight'); b.textContent = night ? 'Malam' : 'Siang'; b.setAttribute('aria-pressed', String(night)); b.setAttribute('aria-label', night ? 'Mode malam aktif. Klik untuk siang.' : 'Mode siang aktif. Klik untuk malam.'); stage.style.background = bgColor(); stage.classList.toggle('night', night); if (r3) r3.theme(); }
  g('oNight').onclick = () => setNight(!night);
  function renderBuild() {
    const L = g('oFlList'), html = FLOORS.slice().reverse().map(F => { const i = F.n - 1, ag = sim.agents.filter(a => a.floor === i && !a.lifting);
      const mp = F.rooms.map(r => { const [x0, y0, x1, y1] = r.r; return `<i style="left:${x0 / W * 100}%;top:${y0 / H * 100}%;width:${(x1 - x0) / W * 100}%;height:${(y1 - y0) / H * 100}%;background:${r.c}"></i>`; }).join('');
      return `<button class="fl${viewFloor === i ? ' on' : ''}" data-f="${i}" aria-pressed="${viewFloor === i}" aria-label="Lantai ${F.n}, ${esc(F.name)}, ${ag.length} agen"><span class="th" aria-hidden="true"><span class="mp">${mp}</span><span class="cnt">${ag.length}</span></span><span class="tx"><small>FL. 0${F.n}</small><b>${esc(F.name)}</b><em>${esc(F.tag)}</em></span></button>`; }).join('');
    if (html !== renderBuild.last) { renderBuild.last = html; L.innerHTML = html; }
    g('oBuildCur').textContent = viewFloor < 0 ? 'Semua' : 'FL. 0' + (viewFloor + 1);
    g('oWhole').classList.toggle('on', viewFloor < 0); g('oWhole').setAttribute('aria-pressed', String(viewFloor < 0));
  }
  g('oFlList').onclick = e => { const b = e.target.closest('.fl'); if (b) setFloor(+b.dataset.f); };
  g('oWhole').onclick = () => setFloor(viewFloor < 0 ? 1 : -1);
  setInterval(renderBuild, 900);
  g('oLegTxt').textContent = FLOORS.map(F => String(F.n).padStart(2, '0') + ' ' + F.name).join(' · ');
  // kartu bisa dilipat (default: terlipat, status diingat)
  function fold(box, btn, key) {
    const v = store.get(key); let min = v === null ? true : v === '1';
    const ap = () => { box.classList.toggle('min', min); btn.setAttribute('aria-expanded', String(!min)); };
    btn.onclick = () => { min = !min; store.set(key, min ? '1' : '0'); ap(); }; ap();
  }
  fold(g('oBuild'), g('oBuildT'), 'officeBuildMin'); fold(g('oCons'), g('oConsT'), 'officeLogMin');
  function paint() { if (panel === 'agents') renderPanel(); }
  const cur = () => (mode === '3d' ? r3 : mode === '2d' ? r2 : null);
  const setHint = () => { g('oHint').textContent = mode === '3d' ? 'Seret = putar · klik kanan = geser · scroll = zoom · 1–4 = lantai · B = gedung · N = siang/malam · klik agen = ikuti' : 'Seret = geser · scroll = zoom · 1–4 = lantai · B = gedung · N = siang/malam · klik agen = ikuti'; };
  async function applyMode(m) {
    g('oHint').textContent = 'Memuat karakter…'; await spritesReady;
    if (m === '3d' && !window.THREE) m = '2d';
    mode = m; store.set('officeMode2', m); g('oMode').textContent = m === '3d' ? '2D' : '3D'; g('oMode').setAttribute('aria-label', m === '3d' ? 'Ganti ke mode 2D' : 'Ganti ke mode 3D');
    g('o3d').hidden = m !== '3d'; g('o2d').hidden = m !== '2d'; labBox.hidden = m !== '3d'; g('oQual').hidden = m !== '3d'; g('oRot').hidden = m !== '3d'; 
    if (m === '3d' && !r3) { r3 = init3D(pixelQ); if (!r3) return applyMode('2d'); }
    if (m === '2d' && !r2) r2 = init2D();
    stage.style.background = bgColor(); cur().resize(); if (cur().setFloor) cur().setFloor(); setHint();
  }
  function paintQual() { const b = g('oQual'); b.textContent = pixelQ ? 'Pixel' : 'HD'; b.setAttribute('aria-pressed', String(pixelQ)); b.setAttribute('aria-label', 'Kualitas 3D: ' + (pixelQ ? 'Pixel' : 'HD') + '. Klik untuk ganti.'); }
  g('oQual').onclick = () => { pixelQ = !pixelQ; store.set('officeQ', pixelQ ? 'pixel' : 'hd'); paintQual(); if (r3) { r3.destroy(); r3 = init3D(pixelQ); if (!r3) applyMode('2d'); else r3.resize(); } };
  paintQual();
  g('oMode').onclick = () => applyMode(mode === '3d' ? '2d' : '3d');
  g('oReset').onclick = () => { const r = cur(); if (r) r.reset(); };
  g('oZin').onclick = () => { const r = cur(); if (r && r.key) r.key('+'); };
  g('oZout').onclick = () => { const r = cur(); if (r && r.key) r.key('-'); };
  g('oRot').onclick = () => { if (r3 && mode === '3d') r3.rot(Math.PI / 2); };
  g('oFull').onclick = () => {
    const on = document.body.classList.toggle('ofull');
    try { if (on && document.documentElement.requestFullscreen) document.documentElement.requestFullscreen().catch(() => { }); else if (!on && document.fullscreenElement) document.exitFullscreen(); } catch { }
    setTimeout(() => { const r = cur(); if (r) r.resize(); }, 60);
  };
  document.addEventListener('fullscreenchange', () => { if (!document.fullscreenElement) document.body.classList.remove('ofull'); setTimeout(() => { const r = cur(); if (r) r.resize(); }, 60); });
  addEventListener('keydown', e => {
    if (!sec.classList.contains('on') || e.ctrlKey || e.metaKey || e.altKey) return; const tg = e.target; if (tg && /^(INPUT|TEXTAREA|SELECT)$/.test(tg.tagName)) return;
    if (e.key === 'Escape') { if (!g('oChat').hidden) openChat(false); else if (panel) setPanel(panel); else if (document.body.classList.contains('ofull')) g('oFull').click(); return; }
    if (/^[1-4]$/.test(e.key)) { setFloor(+e.key - 1); e.preventDefault(); return; } if (e.key === 'b' || e.key === 'B') { setFloor(viewFloor < 0 ? 1 : -1); return; } if (e.key === 'n' || e.key === 'N') { setNight(!night); return; }
    if (e.key === 'PageUp') { setFloor(Math.min(NF - 1, (viewFloor < 0 ? 0 : viewFloor) + 1)); e.preventDefault(); return; } if (e.key === 'PageDown') { setFloor(Math.max(0, (viewFloor < 0 ? 1 : viewFloor) - 1)); e.preventDefault(); return; }
    const r = cur(); if (r && r.key && r.key(e.key)) e.preventDefault();
  });

  g('oH3D').onclick = async () => {
    if (h3dOn) { h3dOn = false; frame.hidden = true; g('oH3D').classList.remove('on'); g('oH3D').setAttribute('aria-pressed', 'false'); return; }
    let cfg = null; try { cfg = await (await fetch('/api/office/config')).json(); } catch { }
    if (!cfg || !cfg.hermes3d_up) { toastMsg('Hermes3D belum jalan — python desktop.py menyalakannya (butuh Node.js).'); return; }
    const src = cfg.hermes3d_url + '/office'; if (frame.dataset.src !== src) { frame.src = src; frame.dataset.src = src; }
    h3dOn = true; frame.hidden = false; g('oH3D').classList.add('on'); g('oH3D').setAttribute('aria-pressed', 'true');
  };
  function toastMsg(t) { const el = document.createElement('div'); el.className = 'o-toast'; el.setAttribute('role', 'status'); el.textContent = t; hud.appendChild(el); setTimeout(() => el.remove(), 4200); }

  // --- panel kanan ---
  const STATUSES = [['ready', 'Ready'], ['processing', 'Processing'], ['ready for review', 'Ready for Review'], ['done', 'Done'], ['failed', 'Failed']];
  let rowsData = null, rowsErr = '', rowsAt = 0; const feed = [];
  const updKb = () => { const b = g('oKbCnt'); if (!rowsData) return; const n = rowsData.filter(r => !['done', 'failed'].includes(String(r.status || '').trim().toLowerCase())).length; b.textContent = n; b.hidden = !n; };
  async function loadRows() {
    if (Date.now() - rowsAt < 8000) return; rowsAt = Date.now();
    try { const d = await (await fetch('/api/rows')).json(); if (d.detail) throw new Error(d.detail); rowsData = d.rows || []; rowsErr = ''; updKb(); } catch (e) { rowsErr = 'Gagal memuat Google Sheets — ' + e.message; }
    if (panel === 'kanban') renderPanel();
  }
  const STATE_TXT = { work: 'bekerja', walk: 'berjalan', idle: 'santai' };
  function renderPanel() {
    const P = g('oPanel'); P.hidden = !panel; if (!panel) return; P.className = 'o-panel' + (panel === 'kanban' ? ' wide' : '');
    if (panel === 'agents') {
      P.innerHTML = '<h4>Agen <small>klik untuk ikuti</small></h4><div class="ag">' + sim.agents.map(a => {
        const st = a.work || a.brief ? 'work' : a.moving || a.lifting ? 'walk' : 'idle', room = 'FL.0' + (a.floor + 1) + ' · ' + (sim.roomName(a.room) || '');
        return `<button class="o-ag${follow === a.id ? ' on' : ''}" data-id="${a.id}" aria-pressed="${follow === a.id}"><span class="av" style="background:${a.color}" aria-hidden="true">${esc(a.name[0])}</span><span class="tx"><b>${esc(a.name)} <small>${esc(a.role)}</small></b><em>${esc(room)} · ${esc(a.act)}</em></span><span class="st ${st}">${STATE_TXT[st]}</span></button>`;
      }).join('') + '</div>';
    } else if (panel === 'kanban') {
      if (!rowsData && !rowsErr) { P.innerHTML = '<h4>Kanban board</h4><p class="mut">Memuat…</p>'; loadRows(); return; }
      if (rowsErr && !rowsData) { P.innerHTML = `<h4>Kanban board</h4><p class="err">${esc(rowsErr)}</p>`; return; }
      const cols = STATUSES.map(([k, label]) => { const rs = rowsData.filter(r => String(r.status || '').trim().toLowerCase() === k);
        return `<div class="col"><h5>${label}<em>${rs.length}</em></h5>${rs.slice(0, 40).map(r => `<div class="k"><b>${esc(r.topic)}</b><span>${esc(r.niche)}</span></div>`).join('') || '<p class="mut">—</p>'}</div>`; }).join('');
      P.innerHTML = `<h4>Kanban board <small>${rowsData.length} topik</small></h4><div class="kb">${cols}</div>`;
    } else if (panel === 'pipe') {
      const p = P.dataset.prog || 0;
      P.innerHTML = `<h4>Pipeline <small>${esc(P.dataset.who || 'menunggu tugas')}</small></h4><progress max="100" value="${p}" aria-label="Progres pipeline"></progress><div class="fd">${feed.map(f => `<div>${esc(f)}</div>`).join('') || '<p class="mut">Belum ada aktivitas. Tekan Start atau Simulasi.</p>'}</div>`;
    }
  }
  function setPanel(p) {
    panel = panel === p ? null : p; hud.classList.toggle('pn', !!panel);
    stage.querySelectorAll('.o-tabs button').forEach(b => { const on = b.dataset.p === panel; b.classList.toggle('on', on); b.setAttribute('aria-expanded', String(on)); });
    g('oKanban').classList.toggle('on', panel === 'kanban'); g('oKanban').setAttribute('aria-expanded', String(panel === 'kanban')); renderPanel(); if (panel === 'kanban') loadRows();
  }
  stage.querySelectorAll('.o-tabs button').forEach(b => b.onclick = () => setPanel(b.dataset.p));
  g('oKanban').onclick = () => setPanel('kanban');
  g('oPanel').onclick = e => { const b = e.target.closest('.o-ag'); if (b) selectAgent(b.dataset.id); };
  setInterval(() => { if (panel === 'agents' || panel === 'pipe') renderPanel(); loadRows(); }, 700);

  // --- console event ---
  const events = []; let consOpen = false;
  function consInfo() {
    const w = sim.agents.filter(a => a.work || a.brief).length, e = events[events.length - 1], ag = e && sim.byId[e.agent];
    g('oStWork').textContent = w; g('oStFree').textContent = sim.agents.length - w; g('oStEv').textContent = events.length;
    g('oConsInfo').textContent = events.length ? 'Aktivitas live' : 'Siaga';
    g('oLast').innerHTML = e ? `<time>${new Date(e.ts * 1000).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' })}</time><span class="chip">${esc(ag ? ag.name : e.agent)}</span><span>${esc(e.message || e.action)}</span>` : '<span class="mut">Belum ada aktivitas. Tekan Start atau Simulasi.</span>';
  }
  function consBody() { const b = g('oConsBody'); b.hidden = !consOpen; if (consOpen) b.innerHTML = events.slice(-60).reverse().map(e => `<div><em>${new Date(e.ts * 1000).toLocaleTimeString('id-ID')}</em> <b>${esc((sim.byId[e.agent] || {}).name || e.agent)}</b> · ${esc(e.action)} — ${esc(e.message)}</div>`).join('') || '<div class="mut">Belum ada event.</div>'; g('oExp').textContent = consOpen ? 'Ciutkan' : 'Perluas'; g('oExp').setAttribute('aria-expanded', String(consOpen)); }
  g('oExp').onclick = () => { consOpen = !consOpen; consBody(); };
  g('oClr').onclick = () => { events.length = 0; consInfo(); consBody(); };
  g('oCopy').onclick = async () => { const t = JSON.stringify(events, null, 2); try { await navigator.clipboard.writeText(t); toastMsg('JSON event disalin'); } catch { toastMsg('Gagal menyalin (izin clipboard ditolak)'); } };
  g('oDown').onclick = () => { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([JSON.stringify(events, null, 2)], { type: 'application/json' })); a.download = 'office-events.json'; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000); };
  consInfo(); setInterval(consInfo, 1000);

  // --- chat ---
  function openChat(on) { g('oChat').hidden = !on; g('oChatBtn').setAttribute('aria-expanded', String(on)); if (on) g('oMsg').focus(); }
  g('oChatBtn').onclick = () => openChat(g('oChat').hidden); g('oChatX').onclick = () => openChat(false);
  const addMsg = (cls, t) => { const d = document.createElement('div'); d.className = 'm ' + cls; d.textContent = t; const L = g('oChatMsgs'); L.appendChild(d); L.scrollTop = L.scrollHeight; return d; };
  async function ask() {
    const i = g('oMsg'), t = i.value.trim(); if (!t) return; i.value = ''; addMsg('me', t); const pend = addMsg('bot', 'MorbMyth sedang berpikir…'); sim.say('ceo', 'Hmm, mikir dulu…', 30);
    try {
      const r = await fetch('/api/office/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: t }) });
      const d = await r.json(); if (!r.ok) throw new Error(d.detail || r.statusText);
      pend.textContent = d.reply; sim.say('ceo', d.reply, 9);
      if (d.action && d.action !== 'none') { sim.event({ agent: 'ceo', action: 'delegating', message: d.reply }); setTimeout(() => sim.event({ agent: 'ceo', action: 'idle', message: '' }), 4000); }
    } catch (e) { pend.textContent = 'Ollama error: ' + e.message; pend.classList.add('err'); sim.say('ceo', 'Ollama error', 6); }
  }
  g('oSend').onclick = ask; g('oMsg').onkeydown = e => { if (e.key === 'Enter') ask(); };

  // --- status: Hermes/Ollama + automation (+ briefing saat START) ---
  async function pollOllama() {
    const b = g('oStat'); try {
      const s = await (await fetch('/api/ollama/status')).json(), ok = s.online && s.installed;
      b.className = 'ob stat ' + (ok ? 'on' : 'off'); b.textContent = !s.online ? 'Ollama offline' : s.installed ? `Hermes terhubung · ${s.model}` : `Model belum ada · ollama pull ${s.model}`; b.title = b.textContent;
    } catch { b.className = 'ob stat off'; b.textContent = 'Server terputus'; }
  }
  let running = false, runKnown = false;
  async function pollRun() {
    try {
      const s = await (await fetch('/api/status')).json(), now = !!s.is_running;
      if (runKnown && now && !running) sim.startBriefing();                               // automation dimulai dari mana pun (Dashboard, chat, autostart)
      if (runKnown && !now && running) sim.endBriefing();
      running = now; runKnown = true;
      const b = g('oRun'); b.innerHTML = (running ? IC.stop + ' Stop' : IC.play + ' Start') + (running && s.countdown ? ` · ${s.countdown}s` : ''); b.classList.toggle('gold', !running); b.classList.toggle('dark', running); b.disabled = !!s.stopping;
    } catch { }
  }
  g('oRun').onclick = async () => { if (!running) sim.startBriefing(); else sim.endBriefing(); try { await fetch(running ? '/api/automation/stop' : '/api/automation/start', { method: 'POST' }); } catch { } pollRun(); };
  loadRows(); pollOllama(); pollRun(); setInterval(pollOllama, 15000); setInterval(pollRun, 3000);

  // --- data masuk ---
  function onEvent(d) {
    sim.event(d); events.push({ ts: d.ts || Date.now() / 1000, agent: d.agent, action: d.action, message: d.message, progress: d.progress }); if (events.length > 500) events.shift(); consInfo(); if (consOpen) consBody();
    const a = sim.byId[d.agent]; if (!a) return;
    if (d.progress != null) { g('oPanel').dataset.prog = d.progress; g('oPanel').dataset.who = `${d.progress}% · ${a.name}`; }
    feed.unshift(`${new Date().toLocaleTimeString('id-ID')} — ${d.message}`); feed.length = Math.min(feed.length, 8);
  }
  let ws, wait = 1000;
  (function connect() {
    ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/office`);
    ws.onopen = () => wait = 1000;
    ws.onmessage = e => { try { onEvent(JSON.parse(e.data)); } catch (x) { console.warn('office msg', x); } };
    ws.onclose = () => setTimeout(connect, wait = Math.min(wait * 2, 15000));
  })();
  let demoTimers = [], demoPending = false;
  const DEMO = [[0, 'ceo', 'delegating', 'MorbMyth: Memulai produksi video…', 3], [2500, 'nexa', 'researching', 'NexaTrend: riset topik panas di Trends/TikTok/Reddit…', 8], [7000, 'scriptwriter', 'typing', 'KaelQuill menulis naskah…', 20], [11500, 'voiceactor', 'speaking', 'VoxArden merekam audio…', 35],
    [16000, 'designer', 'working', 'MikaPixel mencari background & BGM…', 50], [20500, 'editor', 'rendering', 'RivenCut merender video MP4…', 65], [26000, 'editor', 'idle', 'Render selesai!', 70], [27500, 'byte', 'inspecting', 'ByteGuard cek durasi, rasio 9:16 & audio…', 75],
    [32500, 'cross', 'publishing', 'CrossByte upload ke YouTube/TikTok/IG/FB…', 85], [37500, 'echo', 'replying', 'EchoBee membalas komentar penonton…', 90], [42500, 'metrix', 'analyzing', 'Metrix menyusun laporan harian…', 95], [47500, 'ceo', 'approving', 'MorbMyth: Laporan diterima!', 100], [51500, 'ceo', 'idle', 'Selesai.', 100]];
  function runDemo() { for (const [ms, agent, action, message, progress] of DEMO) demoTimers.push(setTimeout(() => onEvent({ agent, action, message, progress }), ms)); }
  g('oDemo').onclick = () => {
    demoTimers.forEach(clearTimeout); demoTimers = []; if (panel !== 'pipe') setPanel('pipe');
    if (sim.startBriefing()) demoPending = true; else runDemo();                       // briefing dulu, simulasi menyusul setelah semua ke Studio Kerja
  };

  // --- briefing: banner + kamera fokus ke Ruang Rapat ---
  let briefCam = false, briefTxt = '', prevFloor = 1;
  function stepBriefUI() {
    const b = sim.briefing, el = g('oBrief');
    if (b) {
      const txt = b.phase === 'gather' ? 'BRIEFING — semua agen menuju Meeting Room (Lantai 1)' : 'BRIEFING — rapat berlangsung, lalu kembali ke lantai masing-masing';
      if (txt !== briefTxt) { briefTxt = txt; el.textContent = txt; } el.hidden = false;
      if (!briefCam) { briefCam = true; prevFloor = viewFloor; follow = null; setFloor(0); const r = cur(); if (r && r.focusTile) mode === '3d' ? r.focusTile(5, 3, 9, 0) : r.focusTile(5, 3, 2.3); }
    } else {
      if (!el.hidden) { el.hidden = true; briefTxt = ''; }
      if (briefCam) { briefCam = false; const r = cur(); if (r && r.unfocus) r.unfocus(); setFloor(prevFloor); if (demoPending) { demoPending = false; runDemo(); } }
    }
  }

  // --- loop ---
  let last = performance.now();
  (function loop(now) {
    requestAnimationFrame(loop); const dt = (now - last) / 1000; last = now; sim.update(dt); stepBriefUI();
    if (!sec.classList.contains('on') || document.hidden) return;
    const t = now / 1000;
    try { if (mode === '3d' && r3) r3.render(t); else if (mode === '2d' && r2) r2.render(t); }
    catch (e) { console.error('office render', e); if (mode === '3d') { r3 = null; applyMode('2d'); } }
  })(last);
  applyMode(mode);
  setNight(night); renderBuild();
  window.__office = { setFloor, setNight, floor: () => viewFloor, sim, r3: () => r3, r2: () => r2, select: selectAgent, setPanel, events, spr: SPR, pending: () => demoPending };
})();