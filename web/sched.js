/* Pemilih jadwal publikasi (Video Studio): kalender mini + jam.
   Mengisi <input type="hidden" id="ySched"> dengan "YYYY-MM-DD HH:MM" (format lama) -> server tidak berubah.
   Nilai kosong = jadwal belum valid. window.schedValidate() -> '' jika valid, atau pesan error. */
(() => {
  const $ = s => document.querySelector(s), box = $('#schedBox'); if (!box) return;
  const MON = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'];
  const DOW = ['Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab', 'Min'], DAYN = ['Minggu', 'Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu'];
  const MIN_LEAD = 5 * 60000, pad = n => String(n).padStart(2, '0');
  const now0 = new Date(), sch = { vy: now0.getFullYear(), vm: now0.getMonth(), d: null, h: 18, mi: 0 };

  $('#scH').innerHTML = Array.from({ length: 24 }, (_, i) => `<option value="${i}">${pad(i)}</option>`).join('');
  $('#scM').innerHTML = Array.from({ length: 12 }, (_, i) => `<option value="${i * 5}">${pad(i * 5)}</option>`).join('');

  const atDay = (base, addDays, h, mi) => new Date(base.getFullYear(), base.getMonth(), base.getDate() + addDays, h, mi);
  function quickList() {
    const n = new Date(), out = [], ok = d => d.getTime() > n.getTime() + MIN_LEAD;
    const plus = new Date(Math.ceil((n.getTime() + 3600000) / 300000) * 300000); out.push(['+1 jam', plus]);
    const t18 = atDay(n, 0, 18, 0); if (ok(t18)) out.push(['Hari ini 18:00', t18]);
    out.push(['Besok 09:00', atDay(n, 1, 9, 0)], ['Besok 18:00', atDay(n, 1, 18, 0)]);
    let sat = atDay(n, (6 - n.getDay() + 7) % 7, 10, 0); if (!ok(sat)) sat = atDay(sat, 7, 10, 0); out.push(['Sabtu 10:00', sat]);
    return out;
  }
  function setFrom(dt) {
    sch.d = new Date(dt.getFullYear(), dt.getMonth(), dt.getDate()); sch.h = dt.getHours(); sch.mi = Math.floor(dt.getMinutes() / 5) * 5;
    sch.vy = dt.getFullYear(); sch.vm = dt.getMonth(); render();
  }
  const chosen = () => sch.d ? new Date(sch.d.getFullYear(), sch.d.getMonth(), sch.d.getDate(), sch.h, sch.mi) : null;

  function render() {
    const now = new Date(), today = new Date(now.getFullYear(), now.getMonth(), now.getDate()), first = new Date(sch.vy, sch.vm, 1);
    const off = (first.getDay() + 6) % 7, days = new Date(sch.vy, sch.vm + 1, 0).getDate();
    $('#scTitle').textContent = `${MON[sch.vm]} ${sch.vy}`;
    let h = DOW.map(d => `<b>${d}</b>`).join('') + '<span></span>'.repeat(off);
    for (let d = 1; d <= days; d++) {
      const dt = new Date(sch.vy, sch.vm, d), past = dt < today, sel = sch.d && dt.getTime() === sch.d.getTime(), isToday = dt.getTime() === today.getTime();
      h += `<button type="button" class="sc-d${sel ? ' sel' : ''}${isToday ? ' today' : ''}" data-d="${d}"${past ? ' disabled' : ''}>${d}</button>`;
    }
    $('#scGrid').innerHTML = h;
    $('#scPrev').disabled = sch.vy === now.getFullYear() && sch.vm <= now.getMonth();
    $('#scH').value = sch.h; $('#scM').value = sch.mi;
    $('#scQuick').innerHTML = quickList().map(([l, d]) => `<button type="button" class="ghost sm" data-ts="${d.getTime()}">${l}</button>`).join('');
    const dt = chosen(), sum = $('#scSum'), hid = $('#ySched');
    if (!dt) { hid.value = ''; sum.className = 'sc-sum'; sum.textContent = 'Pilih tanggal di kalender.'; return; }
    if (dt.getTime() < Date.now() + MIN_LEAD) { hid.value = ''; sum.className = 'sc-sum bad'; sum.textContent = 'Waktu sudah lewat atau terlalu dekat (minimal 5 menit dari sekarang) — pilih jam yang lebih akhir.'; return; }
    hid.value = `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())} ${pad(dt.getHours())}:${pad(dt.getMinutes())}`;
    const mins = Math.round((dt - Date.now()) / 60000), rel = mins < 60 ? `${mins} menit lagi` : mins < 1440 ? `${Math.round(mins / 60)} jam lagi` : `${Math.round(mins / 1440)} hari lagi`;
    sum.className = 'sc-sum ok'; sum.innerHTML = `<b>${DAYN[dt.getDay()]}, ${dt.getDate()} ${MON[dt.getMonth()]} ${dt.getFullYear()} · ${pad(sch.h)}:${pad(sch.mi)}</b><small>${rel}</small>`;
  }

  box.addEventListener('click', e => {
    const d = e.target.closest('.sc-d'), q = e.target.closest('[data-ts]');
    if (d && !d.disabled) { sch.d = new Date(sch.vy, sch.vm, +d.dataset.d); render(); }
    else if (q) setFrom(new Date(+q.dataset.ts));
    else if (e.target.closest('#scPrev') && !$('#scPrev').disabled) { sch.vm--; if (sch.vm < 0) { sch.vm = 11; sch.vy--; } render(); }
    else if (e.target.closest('#scNext')) { sch.vm++; if (sch.vm > 11) { sch.vm = 0; sch.vy++; } render(); }
  });
  $('#scH').onchange = () => { sch.h = +$('#scH').value; render(); };
  $('#scM').onchange = () => { sch.mi = +$('#scM').value; render(); };
  // saat "Jadwalkan" dipilih untuk pertama kali -> isi default (besok 18:00)
  $('#yPriv').addEventListener('change', () => { if ($('#yPriv').value === 'Jadwalkan' && !sch.d) setFrom(atDay(new Date(), 1, 18, 0)); else render(); });
  window.schedValidate = () => { render(); if (!chosen()) return 'Pilih tanggal dan jam jadwal terlebih dahulu.'; return $('#ySched').value ? '' : 'Jadwal harus di masa depan (minimal 5 menit dari sekarang).'; };
  render();
})();
