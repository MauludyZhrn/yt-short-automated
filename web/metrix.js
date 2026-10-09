/* Tab Analytics (Metrix): daftar laporan, KPI, insight bias, Top 10, tabel sortable, export, tombol jalankan.
   Memakai helper global dari app.js: $, $$, api, safe, toast, esc. */
(() => {
  const nf = n => Number(n ?? 0).toLocaleString('id-ID');
  const num = v => (v === null || v === undefined ? '–' : nf(v));
  const pct = v => (v === null || v === undefined ? '–' : v + '%');
  const sel = $('#mxReport'); if (!sel) return;
  let cur = null, sortK = 'score', sortDir = -1, busy = false;

  const setBusy = b => {
    busy = b; const btn = $('#mxRefresh'); btn.disabled = b;
    btn.innerHTML = b ? '<i class="fi-rr-refresh"></i> Menyusun…' : '<i class="fi-rr-refresh"></i> Jalankan Metrix';
  };
  const showEmpty = (title, text) => {
    $('#mxEmpty').hidden = false; $('#mxBody').hidden = true;
    $('#mxEmpty b').textContent = title; $('#mxEmpty span').textContent = text;
  };

  const kpis = d => {
    const a = d.aggregate_stats || {};
    return [
      ['Video Dianalisis', nf(d.total_videos_analyzed), 'video-camera', 'y'],
      ['Total Views', nf(a.total_views), 'eye', 's'],
      ['Total Likes', nf(a.total_likes), 'heart', 'r'],
      ['Total Share', num(a.total_shares), 'share', 'a'],
      ['Rata-rata Engagement', (a.avg_engagement_rate ?? 0) + '%', 'chart-histogram', 'g'],
      ['Rata-rata Retensi', pct(a.avg_view_percentage), 'time-fast', 'k'],
    ];
  };

  const renderBias = async () => {
    let b = {}; try { b = await api('/metrix/bias'); } catch { }
    const chips = (arr, cls) => (arr || []).map(x => `<span class="pill ${cls}" style="margin:0 6px 6px 0;display:inline-block">${esc(x)}</span>`).join('') || '<small>belum ada</small>';
    $('#mxBoostPill').innerHTML = b.boost_comments ? '<span class="pill amber">EchoBee: boost komentar ON</span>' : '';
    $('#mxBias').innerHTML = b.generated_at
      ? `<p><b>Niche pemenang</b><br>${chips(b.winning_niches, 'green')}</p>
         <p><b>Hook pemenang</b><br>${chips(b.winning_hooks, 'yellow')}</p>
         <p><b>Keyword terbukti laku</b><br>${chips(b.winning_keywords, 'sky')}</p>
         <small>Skor rata-rata ${esc(b.avg_score)} · engagement ${esc(b.avg_engagement_rate)}% · dipakai NexaTrend, CrossByte & EchoBee.</small>`
      : '<small>Belum ada bias. Akan terisi setelah ada video YouTube yang bisa dianalisis.</small>';
  };

  const renderTable = () => {
    const rows = [...(cur.detailed_metrics || [])];
    rows.sort((x, y) => {
      const a = x[sortK], b = y[sortK];
      if (a === b) return 0; if (a === null || a === undefined) return 1; if (b === null || b === undefined) return -1;
      return (typeof a === 'string' ? a.localeCompare(b) : a - b) * sortDir;
    });
    $('#mxCount').textContent = `${rows.length} video`;
    $('#mxTbody').innerHTML = rows.map(r => `<tr>
      <td>${esc(r.row_id)}</td><td>${esc(r.niche)}</td><td>${esc(r.topic)}</td>
      <td>${nf(r.views)}</td><td>${nf(r.likes)}</td><td>${nf(r.comments)}</td>
      <td>${num(r.shares)}</td><td>${pct(r.avg_view_pct)}</td>
      <td>${esc(r.engagement_rate)}%</td><td><b>${esc(r.score)}</b></td>
      <td><a href="https://www.youtube.com/shorts/${encodeURIComponent(r.video_id)}" target="_blank" rel="noopener">YouTube</a></td></tr>`).join('');
    $$('#analytics th[data-k]').forEach(th => th.dataset.s = th.dataset.k === sortK ? (sortDir < 0 ? '▼' : '▲') : '');
  };

  const render = async d => {
    cur = d;
    const n = d.total_videos_analyzed || 0;
    if (!n) {
      showEmpty('Belum ada video yang bisa dianalisis',
        d.error ? 'Gagal menarik data YouTube: ' + d.error
          : 'Pastikan kolom output di Sheets berisi link YouTube asli (status Done) dan token YouTube sudah login.');
      return;
    }
    $('#mxEmpty').hidden = true; $('#mxBody').hidden = false;
    $('#mxKpis').innerHTML = kpis(d).map(([t, v, i, k]) =>
      `<div class="kpi t-${k}"><div class="ico"><i class="fi-rr-${i}"></i></div><div><small>${t}</small><h2>${v}</h2></div></div>`).join('');
    const top = [...(d.detailed_metrics || [])].sort((a, b) => b.score - a.score).slice(0, 10);
    $('#mxTop').innerHTML = top.map(r => `<div class="mx-bar" title="${esc(r.topic)}">
      <span class="mx-bar-lb">#${esc(r.row_id)} ${esc(r.topic)}</span>
      <span class="mx-bar-track"><i style="width:${Math.min(100, r.score)}%"></i></span><b>${esc(r.score)}</b></div>`).join('');
    renderTable(); renderBias();
  };

  const open = safe(async file => render(await api('/metrix/reports/' + encodeURIComponent(file))));

  const loadList = safe(async () => {
    const { reports, generating } = await api('/metrix/reports');
    setBusy(!!generating);
    const keep = sel.value;
    sel.innerHTML = reports.map(r => `<option value="${esc(r.file)}">${esc(r.generated_at)} — ${r.total_videos_analyzed} video</option>`).join('');
    if (!reports.length) return showEmpty('Belum ada laporan Metrix', 'Klik "Jalankan Metrix" untuk menyusun laporan performa pertama.');
    if (reports.some(r => r.file === keep)) sel.value = keep;
    await open(sel.value);
    return reports[0].file;
  });

  const run = safe(async () => {
    if (busy) return;
    const before = sel.options[0]?.value || null;
    const r = await api('/metrix/run', { method: 'POST' });
    toast(r.message, 'ok'); setBusy(true);
    let seen = false;
    for (let i = 0; i < 60; i++) {                       // maks ~3 menit
      await new Promise(res => setTimeout(res, 3000));
      const { reports, generating } = await api('/metrix/reports');
      seen = seen || generating;
      if ((seen && !generating) || (reports[0] && reports[0].file !== before)) {
        await loadList(); toast('Laporan Metrix terbaru siap.', 'ok'); return;
      }
    }
    setBusy(false); toast('Metrix belum selesai. Cek log server lalu muat ulang tab.', 'warn');
  });

  const download = (name, mime, text) => {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([text], { type: mime })); a.download = name; a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  };
  const csvCell = v => { const s = String(v ?? ''); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };

  $('#mxRefresh').onclick = run;
  sel.onchange = () => open(sel.value);
  $$('#analytics th[data-k]').forEach(th => th.onclick = () => {
    if (!cur) return; sortDir = sortK === th.dataset.k ? -sortDir : -1; sortK = th.dataset.k; renderTable();
  });
  $('#mxExportJson').onclick = () => cur && download(sel.value || 'metrix.json', 'application/json', JSON.stringify(cur, null, 2));
  $('#mxExportCsv').onclick = () => {
    if (!cur) return;
    const cols = ['row_id', 'niche', 'topic', 'hook', 'video_id', 'views', 'likes', 'comments', 'shares', 'avg_view_pct', 'avg_view_sec', 'watch_minutes', 'subs_gained', 'engagement_rate', 'score', 'published_at'];
    const csv = [cols.join(',')].concat((cur.detailed_metrics || []).map(r => cols.map(c => csvCell(r[c])).join(','))).join('\n');
    download((sel.value || 'metrix').replace('.json', '') + '.csv', 'text/csv', '\ufeff' + csv);
  };
  document.querySelector('nav [data-tab=analytics]').addEventListener('click', loadList);
})();