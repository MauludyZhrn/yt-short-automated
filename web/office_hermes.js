/* Tab Office 3D: pilih "Hermes3D" (Next.js + Three.js, penuh) atau "Ringan" (kantor bawaan). */
(() => {
  const sec = document.getElementById('office'); if (!sec) return;
  const light = sec.querySelector('.oscene'), chat = sec.querySelector('.card');
  const bar = document.createElement('div');
  bar.className = 'row'; bar.style.cssText = 'margin:0 0 12px;align-items:center';
  bar.innerHTML = '<button class="pri sm" data-m="h3d">Hermes3D</button><button class="ghost sm" data-m="light">Ringan</button>' +
    '<small class="muted" id="oHint" style="margin-left:auto"></small>';
  sec.prepend(bar);
  const frame = document.createElement('iframe');
  frame.style.cssText = 'width:100%;height:calc(100vh - 170px);min-height:560px;border:1px solid var(--bd);border-radius:var(--r);background:#14151A';
  frame.allow = 'microphone; fullscreen'; frame.hidden = true;
  light.before(frame);
  const hint = bar.querySelector('#oHint');
  let cfg = null, mode = localStorage.getItem('officeMode') || 'h3d';

  async function loadCfg() {
    try { cfg = await (await fetch('/api/office/config')).json(); } catch { cfg = null; }
    return cfg;
  }
  async function apply(m) {
    mode = m; localStorage.setItem('officeMode', m);
    bar.querySelectorAll('button').forEach(b => { const on = b.dataset.m === m; b.classList.toggle('pri', on); b.classList.toggle('ghost', !on); });
    const h = m === 'h3d';
    frame.hidden = !h; light.hidden = h; chat.hidden = h;
    if (!h) { hint.textContent = ''; return; }
    await loadCfg();
    if (!cfg || !cfg.hermes3d_up) {
      frame.hidden = true; light.hidden = false; chat.hidden = false;
      hint.textContent = 'Hermes3D belum jalan → pakai start_all / python desktop.py. Menampilkan kantor Ringan.';
      return;
    }
    hint.textContent = cfg.adapter_up ? 'Hermes3D · terhubung ke Ollama' : 'Adapter Hermes (port 18789) belum jalan';
    const src = cfg.hermes3d_url + '/office';
    if (frame.dataset.src !== src) { frame.src = src; frame.dataset.src = src; }
  }
  bar.onclick = e => { const b = e.target.closest('button[data-m]'); if (b) apply(b.dataset.m); };
  // muat saat tab Office dibuka pertama kali (hindari render 3D di tab tersembunyi)
  const ob = new MutationObserver(() => { if (sec.classList.contains('on') && !sec.dataset.init) { sec.dataset.init = 1; apply(mode); } });
  ob.observe(sec, { attributes: true, attributeFilter: ['class'] });
  if (sec.classList.contains('on')) { sec.dataset.init = 1; apply(mode); }
})();
