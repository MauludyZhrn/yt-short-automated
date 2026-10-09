const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const CLS = { ready: 'amber', 'ready for review': 'yellow', processing: 'sky', done: 'green', failed: 'rose' };
const sk = r => String(r.status || '').trim().toLowerCase();
const pill = r => `<span class="pill ${CLS[sk(r)] || 'gray'}">${esc(r.status || '-')}</span>`;
let rows = [], meta = {}, sel = null, drafts = {}, variant = 0, wasBusy = false, seoTimer;
let isWaiting = false;
let platforms = [], selPlats = new Set(), wasGen = false;
const idn = r => Number(r.id) || 0;   // id non-numerik tidak lagi merusak urutan (NaN)
const isHttp = u => /^https?:\/\//i.test(String(u || ''));

async function api(path, opt = {}) {
  const r = await fetch('/api' + path, {
    ...opt, headers: { 'Content-Type': 'application/json' },
    body: opt.body === undefined ? undefined : JSON.stringify(opt.body)
  });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof d.detail === 'string' ? d.detail : r.statusText);
  return d;
}
let cfg = {}, notifs = [], unread = 0, prevReview = null;
try { notifs = JSON.parse(localStorage.getItem('notifs') || '[]'); } catch { }
const updBadge = () => { const b = $('#bdg'); b.hidden = !unread; b.textContent = unread; };
const NC = { info: 'yellow', ok: 'green', warn: 'amber', err: 'rose' };
function renderNotif() {
  $('#nList').innerHTML = notifs.map(n => `<div class="nitem"><span class="pill ${NC[n.k] || 'gray'}">${n.k}</span><span>${esc(n.m)}</span><small>${n.t}</small></div>`).join('') || 'Belum ada notifikasi.';
}
function toast(msg, kind = 'info', actionText, action) {
  notifs.unshift({ t: new Date().toLocaleTimeString('id-ID'), k: kind, m: msg }); notifs.length = Math.min(notifs.length, 100);
  try { localStorage.setItem('notifs', JSON.stringify(notifs)); } catch { }
  if ($('#notifications').classList.contains('on')) renderNotif(); else { unread++; updBadge(); }
  if ((kind === 'info' || kind === 'ok') && cfg.notifications === false) return;
  const t = document.createElement('div');
  t.className = 'toast ' + kind; t.innerHTML = `<i class="fi-rr-${{ ok: 'check-circle', err: 'cross-circle', warn: 'exclamation' }[kind] || 'info'}"></i><span>${esc(msg)}</span>`;
  if (action) { const b = document.createElement('button'); b.className = 'pri'; b.textContent = actionText; b.onclick = () => { t.remove(); action(); }; t.append(b); }
  $('#toasts').append(t); setTimeout(() => t.remove(), 4500);
}
const safe = fn => async (...a) => { try { return await fn(...a); } catch (e) { toast(e.message, 'err'); } };

// ---------- Tabs ----------
$$('nav button').forEach(b => b.onclick = () => {
  $$('nav button').forEach(x => x.classList.toggle('on', x === b));
  $('#pageTitle').textContent = b.querySelector('.lb').textContent;
  $$('.tab').forEach(t => t.classList.toggle('on', t.id === b.dataset.tab));
  if (b.dataset.tab === 'account') loadAccount();
  if (b.dataset.tab === 'notifications') { unread = 0; updBadge(); renderNotif(); }
  if (b.dataset.tab === 'settings') loadSettings();
});
const goTab = name => $(`nav [data-tab=${name}]`).click();

// ---------- Rows / Dashboard / Planner ----------
const loadRows = safe(async (force = false) => {
  const d = await api('/rows?force=' + force);
  if (d.rows) { rows = d.rows; renderAll(); }
  loadChart();
});
function filtered() {
  const q = $('#q').value.toLowerCase(), st = $('#fStatus').value;
  return rows.filter(r => (!st || sk(r) === st) && (!q || (r.topic + r.niche + r.hook).toLowerCase().includes(q)));
}
function renderAll() {
  const c = k => rows.filter(r => sk(r) === k).length;
  const rv = c('ready for review');
  if (prevReview !== null && rv > prevReview) toast(`${rv - prevReview} video baru siap direview`, 'ok', 'Buka Studio', () => goTab('studio'));
  prevReview = rv; renderQueue();
  const kp = [['Total', rows.length, 'film', 'k'], ['Ready', c('ready'), 'clock', 'a'], ['Processing', c('processing'), 'refresh', 's'],
    ['Review', rv, 'eye', 'y'], ['Done', c('done'), 'check-circle', 'g'], ['Failed', c('failed'), 'cross-circle', 'r']];
  $('#kpis').innerHTML = kp.map(([t, n, i, k]) => `<div class="kpi t-${k}"><div class="ico"><i class="fi-rr-${i}"></i></div><div><small>${t}</small><h2>${n}</h2></div></div>`).join('');
  $('#tbody').innerHTML = filtered().sort((a, b) => idn(b) - idn(a)).map(r =>
    `<tr class="click" data-id="${esc(r.id)}"><td>${esc(r.id)}</td><td>${esc(r.niche)}</td><td>${esc(r.topic)}</td><td>${esc(r.hook)}</td><td>${pill(r)}</td></tr>`).join('')
    || '<tr><td colspan="5">Tidak ada data.</td></tr>';
  $$('#tbody tr.click').forEach(tr => tr.ondblclick = () => openStudio(tr.dataset.id));
  renderVideoList();
}
const loadChart = safe(async () => {
  hist = (await api('/history')).history; renderCal();
  const { days } = await api('/analytics?days=14');
  const max = Math.max(1, ...days.flatMap(d => [d.rendered, d.uploaded]));
  $('#chart').innerHTML = days.map(d => `<div title="${d.date}: ${d.rendered} render, ${d.uploaded} upload"><span class="pair">
    <i style="height:${d.rendered / max * 100}%"></i><i class="u" style="height:${d.uploaded / max * 100}%"></i></span><em>${d.date.slice(8)}</em></div>`).join('');
});
$('#btnRefresh').onclick = () => loadRows(true);
$('#q').oninput = renderAll; $('#fStatus').onchange = renderAll;
$('#btnGen').onclick = safe(async () => {
  const r = await api('/planner/generate', { method: 'POST' });
  wasGen = r.status !== 'processing' || wasGen; toast(r.message); pollStatus();
});

// ---------- Automation, status & log polling ----------
$('#btnAuto').onclick = safe(async () => {
  const s = await api('/status');
  await api(s.is_running ? '/automation/stop' : '/automation/start', { method: 'POST' });
  pollStatus();
});
const pollStatus = safe(async () => {
  const s = await api('/status');
  $('#ver').textContent = 'v' + s.version;
  const st = s.is_running ? 'run' : s.stopping ? 'stop' : '';
  $('.status').className = 'status ' + st;
  $('#stTxt').textContent = s.is_running ? 'Running' : s.stopping ? 'Stopping' : 'Stopped';
  
  // Update teks countdown
  $('#cd').textContent = (s.is_running && s.countdown) ? `Cek berikutnya: ${s.countdown} dtk` : 
                         (s.waiting_for_user) ? 'Menunggu konfirmasi...' : '';
  
  const b = $('#btnAuto');
  b.innerHTML = s.is_running ? '<i class="fi-rr-stop"></i> Stop Automation' : '<i class="fi-rr-play"></i> Start Automation';
  b.className = s.is_running ? 'dark' : 'pri'; b.disabled = s.stopping;
  
  const p = s.publish || {};
  $('#prog').hidden = !p.busy; $('#prog').value = p.progress || 0;
  renderPubItems(p);
  if (wasBusy && !p.busy) {
    toast(p.error ? 'Upload gagal: ' + p.error : p.message, p.error ? 'err' : p.partial ? 'warn' : 'ok');
    loadRows(true); loadPubLog();
  }
  wasBusy = !!p.busy; updateEditorState();

  if (wasGen && !s.generating_ideas) { toast('Proses generate ide selesai — cek Live Log untuk hasilnya.', 'ok'); loadRows(true); }
  wasGen = !!s.generating_ideas; $('#btnGen').disabled = wasGen;

  // Logika memunculkan Modal Pop-up
  if (s.waiting_for_user && !isWaiting) {
      isWaiting = true;
      $('#modalConfirm').hidden = false;
      loadRows(true);   // video baru selesai -> langsung segarkan tabel, KPI & toast
  } else if (!s.waiting_for_user && isWaiting) {
      isWaiting = false;
      $('#modalConfirm').hidden = true;
  }
});

const pollLogs = safe(async () => {
  const { logs } = await api('/logs'); if (!logs.length) return;
  const el = $('#log');
  logs.forEach(l => { const s = document.createElement('span'); s.className = l.level; s.textContent = `[${l.time}] ${l.text}\n`; el.append(s); });
  while (el.childNodes.length > 800) el.firstChild.remove();
  el.scrollTop = el.scrollHeight;
});
$('#btnClearLog').onclick = () => $('#log').textContent = '';

// ---------- Video Studio ----------
const exists = r => r.exists;
function renderVideoList() {
  const list = filtered().filter(r => ['ready for review', 'done'].includes(sk(r))).sort((a, b) => idn(b) - idn(a));
  $('#vlist').innerHTML = list.map(r => `<div class="vitem ${sel && sel.id == r.id ? 'on' : ''}" data-id="${esc(r.id)}">
    <span><b>#${esc(r.id)}</b> ${esc(r.topic)}</span>${pill(r)}</div>`).join('') || 'Belum ada video.';
  $$('.vitem').forEach(v => v.onclick = () => openStudio(v.dataset.id));
}
function saveDraft() {
  if (sel) drafts[sel.id] = { t: $('#yTitle').value, d: $('#yDesc').value, g: $('#yTags').value };
}
const openStudio = safe(async id => {
  goTab('studio'); saveDraft();
  sel = rows.find(r => String(r.id) === String(id)); if (!sel) return;
  $('#editor').hidden = false; $('#empty').hidden = true; $('#eHead').innerHTML = `#${esc(sel.id)} — ${esc(sel.topic)} ${pill(sel)}`;
  const d = drafts[sel.id];
  if (d) { $('#yTitle').value = d.t; $('#yDesc').value = d.d; $('#yTags').value = d.g; refreshSeo(); }
  else { variant = 0; await genSeo(false, false); }
  $('#player').innerHTML = !sel.exists ? '' : sel.is_url
    ? `<a href="${esc(sel.output)}" target="_blank"><i class="fi-rr-link-alt"></i> Buka di YouTube</a>`
    : `<video controls src="/api/video/file/${encodeURIComponent(sel.id)}"></video>`;
  renderVideoList(); updateEditorState(); renderPubItems({}); loadPubLog();
});
const genSeo = safe(async (nextVariant = false, announce = true) => {
  if (!sel) return toast('Pilih video terlebih dahulu.', 'warn');
  const v = nextVariant ? variant + 1 : variant, prev = [$('#yTitle').value, $('#yDesc').value, $('#yTags').value];
  const m = await api('/seo/generate', { method: 'POST', body: { title: '', description: '', tags: [], topic: sel.topic, niche: sel.niche, hook: sel.hook, variant: v, disclose_ai: $('#ySynth').checked } });
  variant = m.variant ?? v;
  $('#yTitle').value = m.title;
  if (!nextVariant) { $('#yDesc').value = m.description; $('#yTags').value = m.tags.join(', '); }
  refreshSeo();
  if (announce && !nextVariant && prev.some(Boolean)) toast('SEO di-generate ulang.', 'info', 'Batalkan', () => { [$('#yTitle').value, $('#yDesc').value, $('#yTags').value] = prev; refreshSeo(); });
});
const tags = () => $('#yTags').value.split(',').map(t => t.trim()).filter(Boolean);
function refreshSeo() {
  $('#tCount').textContent = `${$('#yTitle').value.length}/${meta.title_max || 100}`;
  clearTimeout(seoTimer);
  seoTimer = setTimeout(safe(async () => {
    const r = await api('/seo/analyze', { method: 'POST', body: { title: $('#yTitle').value, description: $('#yDesc').value, tags: tags(), topic: sel?.topic || '' } });
    $('#seo').innerHTML = `<b>Skor SEO: ${r.score}/100</b>` + r.checks.map(([k, t]) => `<div class="${k}"><i class="fi-rr-${k === 'ok' ? 'check-circle' : k === 'warn' ? 'exclamation' : 'cross-circle'}"></i> ${esc(t)}</div>`).join('');
  }), 400);
}
['#yTitle', '#yDesc', '#yTags'].forEach(s => $(s).oninput = refreshSeo);
$('#yPriv').onchange = () => $('#schedBox').hidden = $('#yPriv').value !== 'Jadwalkan';
$('#btnSeo').onclick = () => genSeo(false); $('#btnVar').onclick = () => genSeo(true);
// ---------- Platform (YouTube asli · TikTok/Instagram/Facebook simulasi) ----------
const chosen = () => platforms.filter(p => p.ready && selPlats.has(p.id));
const saveSel = () => { try { localStorage.setItem('plats', JSON.stringify([...selPlats])); } catch { } };
function chipHtml(p, on, off, name) {
  const tag = off ? 'belum terhubung' : p.dummy ? 'simulasi' : '';
  return `<label class="plat ${on ? 'on' : ''} ${off ? 'off' : ''}" style="--c:${esc(p.color)}" title="${esc(p.message || '')}">
    <input type="checkbox" name="${name}" value="${esc(p.id)}" ${on ? 'checked' : ''} ${off ? 'disabled' : ''}>
    <i class="${esc(p.icon)}"></i><span>${esc(p.label)}</span>${tag ? `<em>${tag}</em>` : ''}</label>`;
}
function renderPlats() {
  $('#plats').innerHTML = platforms.map(p => chipHtml(p, p.ready && selPlats.has(p.id), !p.ready, 'pp')).join('');
  $$('#plats input').forEach(i => i.onchange = () => {
    i.checked ? selPlats.add(i.value) : selPlats.delete(i.value);
    i.closest('.plat').classList.toggle('on', i.checked); saveSel(); updateEditorState();
  });
  updateEditorState();
}
const loadPlatforms = safe(async () => { platforms = (await api('/platforms')).platforms; renderPlats(); });
function renderPubItems(p) {
  const it = Object.values(p.items || {});
  const show = it.length && sel && String(p.row_id) === String(sel.id);
  const lbl = x => ({ pending: 'Menunggu', running: (x.progress || 0) + '%', ok: 'Selesai', error: 'Gagal' }[x.status]);
  $('#pubItems').innerHTML = show ? it.map(x => `<div class="pi ${esc(x.status)}"><i class="${esc(x.icon)}"></i>
    <span>${esc(x.label)} ${x.dummy ? '<em>simulasi</em>' : ''}</span><b>${lbl(x)}</b>
    ${isHttp(x.url) ? `<a href="${esc(x.url)}" target="_blank" rel="noopener" title="Buka"><i class="fi-rr-link-alt"></i></a>` : ''}
    ${x.error ? `<small class="pe">${esc(x.error)}</small>` : ''}</div>`).join('') : '';
}
const loadPubLog = safe(async () => {
  if (!sel) return;
  const id = sel.id, { log } = await api('/publish/log/' + encodeURIComponent(id));
  if (!sel || sel.id !== id) return;
  const ok = (log || []).filter(l => l.ok).slice(-8).reverse();
  $('#pubLog').innerHTML = ok.length ? '<div class="hist-h">Riwayat publish</div>' + ok.map(l => {
    const p = platforms.find(x => x.id === l.platform) || {};
    return `<div class="pi ok"><i class="${esc(p.icon || 'fi-rr-share')}"></i><span>${esc(p.label || l.platform)} ${l.dummy ? '<em>simulasi</em>' : ''}</span>
      <small>${esc(l.time)}</small>${isHttp(l.url) ? `<a href="${esc(l.url)}" target="_blank" rel="noopener" title="Buka"><i class="fi-rr-link-alt"></i></a>` : ''}</div>`;
  }).join('') : '';
});

function updateEditorState() {
  const b = $('#btnPub'); if (!sel) return;
  const cur = rows.find(r => r.id == sel.id) || sel, busy = wasBusy, k = sk(cur), n = chosen().length;
  b.disabled = busy || k !== 'ready for review' || !cur.exists || !n;
  b.innerHTML = busy ? '<i class="fi-rr-cloud-upload"></i> Uploading…'
    : k === 'ready for review' ? `<i class="fi-rr-paper-plane"></i> ${n ? `Publish ke ${n} platform` : 'Pilih platform'}`
    : k === 'done' ? '<i class="fi-rr-check-circle"></i> Sudah Dipublish' : 'Belum Siap Publish';
}
$('#btnPub').onclick = safe(async () => {
  const ps = chosen();
  if (!ps.length) return toast('Pilih minimal satu platform tujuan.', 'warn');
  if ($('#yPriv').value === 'Jadwalkan') { const bad = window.schedValidate && window.schedValidate(); if (bad) return toast(bad, 'warn'); }
  const body = { id: String(sel.id), title: $('#yTitle').value, description: $('#yDesc').value, tags: tags(),
    privacy: $('#yPriv').value, category: $('#yCat').value, schedule: $('#ySched').value,
    synthetic: $('#ySynth').checked, notify: $('#yNotify').checked, platforms: ps.map(p => p.id) };
  const rep = await api('/seo/analyze', { method: 'POST', body: { ...body, topic: sel.topic } });
  if (rep.errors?.length) return toast('Perbaiki dulu: ' + rep.errors.join('; '), 'err');
  let msg = `Publish ke: ${ps.map(p => p.label + (p.dummy ? ' (simulasi)' : '')).join(', ')}?\n\nJudul: ${body.title}\nPrivasi: ${body.privacy}${body.privacy === 'Jadwalkan' ? ' (' + body.schedule + ')' : ''}\nKategori: ${body.category}\nSkor SEO: ${rep.score}/100`;
  if (rep.warnings?.length) msg += '\n\nSaran:\n• ' + rep.warnings.slice(0, 5).join('\n• ');
  if (!confirm(msg)) return;
  await api('/video/publish', { method: 'POST', body });
  delete drafts[sel.id]; toast('Upload dimulai di background.'); pollStatus();
});

// ---------- Akun ----------
const loadAccount = safe(async () => {
  const a = await api('/account'); platforms = a.platforms || platforms; renderPlats();
  const P = { connected: ['green', 'Connected'], login: ['amber', 'Belum Login'], missing: ['rose', 'Not Connected'], disconnected: ['gray', 'Belum Terhubung'] };
  const card = (icon, color, title, pl, txt, extra = '') =>
    `<div class="card acc"><div class="acc-ic" style="background:${color}1A;color:${color}"><i class="${icon}"></i></div>
     <div class="grow"><h3>${title}</h3><div>${esc(txt)}</div>${extra}</div><span class="pill ${pl[0]}">${pl[1]}</span></div>`;
  const yt = platforms.find(p => p.id === 'youtube') || { icon: 'fi-brands-youtube', color: '#FF0000' };
  const others = platforms.filter(p => p.id !== 'youtube').map(p => card(p.icon, p.color, esc(p.label),
    P[p.state] || P.disconnected, p.message,
    p.ready
      ? `<button class="ghost sm" data-act="disconnect" data-id="${esc(p.id)}" style="margin-top:10px"><i class="fi-rr-link-slash"></i> Putuskan</button>`
      : `<div class="acc-form"><button class="pri sm" data-act="connect" data-id="${esc(p.id)}"><i class="fi-rr-plug-connection"></i> Hubungkan (Login)</button></div>`)).join('');
  $('#accBox').innerHTML =
    card(yt.icon, yt.color, 'YouTube Channel', P[a.youtube.state], a.youtube.message, '<button class="ghost sm" id="btnTok" style="margin-top:10px"><i class="fi-rr-exchange"></i> Switch / Reset Akun YouTube</button>') +
    others +
    card('fi-rr-table-list', '#0F9D58', 'Google Sheets', a.sheet.ok ? P.connected : P.missing, a.sheet.message, '<button class="ghost sm" id="btnSheet" style="margin-top:10px"><i class="fi-rr-plug-connection"></i> Tes Koneksi</button>') +
    card('fi-rr-cloud', '#8A6D00', 'Google Drive', ['gray', 'Segera Hadir'], 'Integrasi Drive belum tersedia.');
  $('#btnTok').onclick = safe(async () => {
    if (!confirm('Hapus token login YouTube? Browser server akan terbuka untuk login ulang saat upload berikutnya.')) return;
    toast((await api('/account/reset-token', { method: 'POST' })).message, 'ok'); loadAccount();
  });
  $('#btnSheet').onclick = safe(async () => { await loadRows(true); loadAccount(); });
});
const platAct = safe(async (act, id) => {
  if (act === 'connect') {
    const r = await api(`/oauth/${id}/start?open=true`);
    if (!r.opened) window.open(r.auth_url, '_blank');
    toast('Login dibuka di browser. Selesaikan di sana, lalu kembali ke sini.', 'ok');
    for (let i = 0; i < 90; i++) {                        // tunggu s.d. ~3 menit
      await new Promise(res => setTimeout(res, 2000));
      await loadPlatforms();
      const p = platforms.find(x => x.id === id);
      if (p && p.ready) { toast(`${p.label} terhubung.`, 'ok'); break; }
    }
    return loadAccount();
  } else {
    if (!confirm('Putuskan akun ini?')) return;
    toast((await api(`/platforms/${id}/disconnect`, { method: 'POST' })).message, 'ok');
  }
  loadAccount();
});
$('#accBox').onclick = e => { const b = e.target.closest('[data-act]'); if (b) platAct(b.dataset.act, b.dataset.id); };

// ---------- Settings ----------
const renderSettingsPlats = sel_ => {
  $('#sPlats').innerHTML = platforms.map(p => chipHtml(p, sel_.includes(p.id), false, 'dp')).join('');
  $$('#sPlats input').forEach(i => i.onchange = () => i.closest('.plat').classList.toggle('on', i.checked));
};
const loadSettings = safe(async () => {
  const s = cfg = await api('/settings');
  if (!platforms.length) await loadPlatforms();
  $('#sMode').value = s.upload_mode; $('#sInterval').value = s.interval; $('#sRetries').value = s.retries;
  $('#sLog').value = s.log_level; $('#sOut').value = s.output_folder; $('#sChannel').value = s.channel_name;
  $('#sNotif').checked = s.notifications; $('#sAuto').checked = s.autostart;
  renderSettingsPlats(s.default_platforms || ['youtube']);
  const k = s.keys_set || {};
  $('#sGroq').placeholder = k.groq ? '•••••••• tersimpan' : 'belum diisi';
  $('#sPexels').placeholder = k.pexels ? '•••••••• tersimpan' : 'belum diisi';
  $('#sMagick').placeholder = k.magick ? 'tersimpan — kosongkan = tidak diubah' : 'mis. C:\\Program Files\\ImageMagick\\magick.exe';
});
$('#btnSave').onclick = safe(async () => {
  const dp = $$('#sPlats input:checked').map(i => i.value);
  if (!dp.length) return toast('Pilih minimal satu platform default.', 'warn');
  await api('/settings', { method: 'PUT', body: {
    upload_mode: $('#sMode').value, interval: +$('#sInterval').value || 30, retries: +$('#sRetries').value || 3,
    log_level: $('#sLog').value, output_folder: $('#sOut').value, channel_name: $('#sChannel').value,
    notifications: $('#sNotif').checked, autostart: $('#sAuto').checked, default_platforms: dp,
    groq_api_key: $('#sGroq').value, pexels_api_key: $('#sPexels').value, imagemagick_path: $('#sMagick').value } });
  ['#sGroq', '#sPexels', '#sMagick'].forEach(s => $(s).value = '');
  cfg.notifications = $('#sNotif').checked; cfg.default_platforms = dp;
  toast('Pengaturan disimpan dan langsung aktif.', 'ok'); loadSettings();
});
$('#btnCache').onclick = safe(async () => {
  if (confirm('Hapus semua file sementara render? Video final tidak ikut terhapus.'))
    toast((await api('/cache/clear', { method: 'POST' })).message, 'ok');
});
$('#btnReset').onclick = safe(async () => {
  if (confirm('Kembalikan preferensi ke default? API key tidak diubah.')) { await api('/settings/reset', { method: 'POST' }); loadSettings(); toast('Preferensi direset.', 'ok'); }
});

// ---------- Init ----------
(safe(async () => {
  meta = await api('/meta'); cfg = await api('/settings');
  $('#sMode').innerHTML = meta.upload_modes.map(m => `<option>${esc(m)}</option>`).join('');
  $('#yPriv').innerHTML = meta.privacy.map(m => `<option>${esc(m)}</option>`).join('');
  $('#yCat').innerHTML = meta.categories.map(m => `<option ${m === meta.default_category ? 'selected' : ''}>${esc(m)}</option>`).join('');
  $('#fStatus').innerHTML += ['ready', 'processing', 'ready for review', 'done', 'failed'].map(s => `<option>${s}</option>`).join('');
  try { const st = JSON.parse(localStorage.getItem('plats') || 'null'); selPlats = new Set(Array.isArray(st) ? st : (cfg.default_platforms || ['youtube'])); }
  catch { selPlats = new Set(cfg.default_platforms || ['youtube']); }
  await loadPlatforms();
  await loadRows(false);
}))();
pollStatus(); setInterval(pollStatus, 2000); setInterval(pollLogs, 1500); setInterval(() => loadRows(false), 30000);

// ---------- Kalender & antrean ----------
const MONTHS = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'];
let hist = {}, cal = new Date(); cal.setDate(1);
const iso = (y, m, d) => `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
function renderCal() {
  const y = cal.getFullYear(), m = cal.getMonth(), t = new Date(), today = iso(t.getFullYear(), t.getMonth(), t.getDate());
  $('#calTitle').textContent = `${MONTHS[m]} ${y}`;
  let h = ['Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab', 'Min'].map(n => `<b>${n}</b>`).join('') + '<i></i>'.repeat((new Date(y, m, 1).getDay() + 6) % 7);
  for (let d = 1, n = new Date(y, m + 1, 0).getDate(); d <= n; d++) {
    const k = iso(y, m, d), cls = k === today ? 'today' : (hist[k]?.uploaded > 0 ? 'up' : '');
    h += `<span class="${cls}">${d}</span>`;
  }
  $('#cal').innerHTML = h;
}
const shiftMonth = n => { cal.setMonth(cal.getMonth() + n); renderCal(); };
$('#calPrev').onclick = () => shiftMonth(-1); $('#calNext').onclick = () => shiftMonth(1);
function renderQueue() {
  const ready = rows.filter(r => sk(r) === 'ready').sort((a, b) => idn(a) - idn(b));
  $('#qCount').textContent = `${ready.length} Pending`;
  $('#queue').innerHTML = ready.slice(0, 3).map(r => `<div class="qitem"><span>${esc((r.topic || '(tanpa judul)').slice(0, 34))}<small>${esc(r.niche || '-')}</small></span><b>#${esc(r.id)}</b></div>`).join('')
    || 'Antrean kosong — generate ide di Content Planner.';
  $$('.qitem').forEach(q => q.onclick = () => goTab('planner'));
}
renderCal();

// ---------- Sidebar, ikon, tooltip, shortcut, export log, folder ----------
const toggleSide = () => { const c = document.body.classList.toggle('collapsed'); try { localStorage.setItem('collapsed', c ? 1 : 0); } catch { } };
if (localStorage.getItem('collapsed') === '1') document.body.classList.add('collapsed');
$('#btnCollapse').onclick = toggleSide;
$$('nav button').forEach(b => b.title = b.querySelector('.lb').textContent);
$('#q').onkeydown = e => { if (e.key === 'Enter') goTab('planner'); if (e.key === 'Escape') { $('#q').value = ''; renderAll(); } };
addEventListener('keydown', e => {
  if (!(e.ctrlKey || e.metaKey || e.altKey)) return;
  const k = e.key.toLowerCase(), tabs = ['dashboard', 'planner', 'studio', 'account'];
  if (k === 'k') { $('#q').focus(); $('#q').select(); }
  else if (k === 'r') loadRows(true);
  else if (k === 'b') toggleSide();
  else if (/^[1-4]$/.test(k)) goTab(tabs[+k - 1]);
  else return;
  e.preventDefault();
});
$('#btnExport').onclick = () => {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([$('#log').textContent], { type: 'text/plain' }));
  a.download = `shorts-log-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')}.txt`; a.click(); URL.revokeObjectURL(a.href);
};
$$('[data-open]').forEach(b => b.onclick = safe(async () => toast((await api('/open/' + b.dataset.open, { method: 'POST' })).message)));

// Aksi Tombol Modal Konfirmasi Video Selesai
$('#btnModalLanjut').onclick = safe(async () => {
    await api('/automation/resume', { method: 'POST' });
    $('#modalConfirm').hidden = true;
    isWaiting = false;
    toast('Melanjutkan otomasi ke antrean berikutnya...', 'info');
});

$('#btnModalStop').onclick = safe(async () => {
    await api('/automation/stop', { method: 'POST' });
    await api('/automation/resume', { method: 'POST' }); // Paksa lepas gembok while loop di python
    $('#modalConfirm').hidden = true;
    isWaiting = false;
    toast('Automasi dihentikan.', 'warn');
});