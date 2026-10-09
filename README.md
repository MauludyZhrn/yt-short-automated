# Shorts AutoBot + Hermes3D (gratis, Ollama)

## Setup sekali
1. Pasang Ollama (https://ollama.com) lalu: `ollama pull hermes3:8b`  (model harus mendukung tool-calling)
2. Pasang Node.js 20+ dan `pip install pywebview uvicorn python-dotenv`
3. Salin file ini ke folder project lama (timpa `server.py`, `office_bus.py`, `desktop.py`, `modules/fetch_bg.py`,
   `modules/sheets_manager.py`, `modules/ollama_client.py`, dan seluruh isi `web/`). Salin `.env.example` → tambahkan ke `.env`.
4. Jalankan: `python desktop.py` (atau `start_all.bat` / `./start_all.sh`)
   Pertama kali otomatis: git clone Hermes3D → pasang patch → `npm install` → start semua layanan.

Opsional: `USE_OLLAMA=1` di `.env` agar naskah video juga dibuat Ollama.

## Arsitektur
FastAPI :8000 (dashboard) ── iframe ──> Hermes3D :3000 ── WS ──> adapter :18789 ──> Ollama :11434
`notify_office()` di pipeline → POST adapter `/office/event` → 5 agen 3D (CEO, Scriptwriter, Voice Actor, Designer, Editor) beranimasi.
Chat di Hermes3D: "mulai automation", "buat 5 ide baru", "gimana antreannya?" → tool `shorts_*` memanggil API FastAPI.

## MorbMyth AI Studio HQ (tab Office)
Gedung 4 lantai (isometrik, cutaway), 16+ area, 10 agen berjalan antar lantai lewat lift.

| Lantai | Area | Agen |
|---|---|---|
| FL.01 Public & Operations | Meeting Room, Creator Café, Community Lounge, Lobby & Reception, Wellness Gym, Game Zone | semua berkumpul di Meeting Room saat briefing |
| FL.02 Content Production | Trend Research Lab, Scriptwriting Studio, Voice Recording Studio, Design Studio, Video Editing Suite, Content Library | NexaTrend, KaelQuill, VoxArden, MikaPixel, RivenCut |
| FL.03 Automation & Intelligence | QC Command Center, Publishing Hub, Community Command Center, Analytics Observatory, Automation Server Room, Ops Lounge | ByteGuard, CrossByte, EchoBee, Metrix |
| FL.04 Executive | MorbMyth CEO Office, Strategy Room, Creative War Room, Rooftop Garden (kolam) | MorbMyth |

**Agen baru (sementara, tampilan saja)**: NexaTrend (Trend Researcher), ByteGuard (QC Inspector), CrossByte (Multi-Platform Publisher), EchoBee (Community Manager), Metrix (Data Analyst).
Backend `.py` untuk mereka belum ada. Saat siap, kirim event ke `/ws/office` / `notify_office(agent="nexa"|"byte"|"cross"|"echo"|"metrix", action=..., message=..., progress=...)`
(action bebas: researching, inspecting, publishing, replying, analyzing, typing, working, rendering, idle, alert). Simulasi (tombol SIMULASI) sudah memutar alur lengkap 10 agen.

**Kontrol**
- Panel kiri "Building section": klik lantai = masuk lantai; VIEW WHOLE BUILDING = seluruh gedung (3D bertumpuk / 2D 2x2). Keyboard: 1–4 lantai, B gedung, PageUp/PageDown, N siang/malam.
- **DAY / NIGHT**: malam = jendela & layar menyala, langit gelap (3D dan 2D).
- 3D: seret = putar, klik kanan = geser, scroll = zoom. PIXEL/HD = kualitas render. Klik agen = kamera mengikuti (otomatis pindah lantai).
- START (HUD/Dashboard/chat/autostart): 10 agen naik lift ke Meeting Room FL.01, briefing, lalu kembali ke lantai masing-masing; event pipeline selama briefing ditahan lalu diterapkan.
- Sprite: 10 atlas di `web/sprites/` (5 baru dari `New_5_Agent.zip`). Peta/ruangan/aktivitas/briefing: `web/office_sim.js` (FLOORS, SPOTS, BRIEF_LINES).

## Video Studio: jadwal publikasi
Pilih Privasi = **Jadwalkan** -> muncul kalender mini + pemilih jam (menit per 5), ringkasan "Sabtu, 31 Oktober 2026 · 09:35 (28 hari lagi)",
dan tombol pilih cepat (+1 jam, Hari ini 18:00, Besok 09:00, Besok 18:00, Sabtu 10:00). Hari lampau tidak bisa dipilih, waktu minimal 5 menit dari sekarang.
Default saat pertama dipilih: besok 18:00. Kode ada di `web/sched.js`; nilai tetap dikirim ke server sebagai `YYYY-MM-DD HH:MM` (server tidak berubah).
