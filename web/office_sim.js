/* MorbMyth AI Studio HQ — simulasi 4 lantai (tanpa rendering): peta, ruangan, lift, aktivitas, pathfinding, briefing.
   Dipakai bersama renderer 3D/2D (office.js). */
(function (root) {
  'use strict';
  const W = 32, H = 20, SPEED = 2.4, LIFT = { x: 15, y: 10 }, LIFT_T = 1.0;
  const TL = [0, 0, 10, 8], TM = [10, 0, 21, 8], TR = [21, 0, 31, 8], BL = [0, 12, 10, 19], BM = [10, 12, 21, 19], BR = [21, 12, 31, 19], COR = [0, 8, 31, 12];
  const DOORS = [[5, 8], [15, 8], [26, 8], [5, 12], [15, 12], [26, 12]];
  const room = (id, name, r, fl, c, c2) => ({ id, name, r, fl, c, c2 });
  const cor = (p, c, c2) => room(p + '_cor', 'Koridor & Lift', COR, 'tile', c || '#E4DDD0', c2 || '#DDD5C6');
  const F = (t, x, y, w, h, o) => Object.assign({ t, x, y, w: w || 1, h: h || 1 }, o || {});
  const corFurn = [F('plant', 2, 9), F('plant', 12, 9), F('plant', 19, 9), F('plant', 29, 9), F('plant', 2, 11), F('plant', 29, 11), F('liftpad', 14, 9, 3, 3, { block: false }), F('bench', 7, 9, 3, 1), F('bench', 21, 11, 3, 1)];

  const FLOORS = [
    { id: 'f1', n: 1, name: 'Public & Operations', tag: 'Lobby · Lounge · Meeting · Café',
      rooms: [room('f1_meeting', 'Meeting Room', TL, 'carpet', '#8E83D0', '#9A90DA'), room('f1_cafe', 'Creator Café', TM, 'tile', '#D5D8DC', '#E6E8EB'), room('f1_lounge', 'Community Lounge', TR, 'carpet', '#B6A2E4', '#BFAEEA'),
        room('f1_gym', 'Wellness Gym', BL, 'tile', '#B7C9DE', '#C4D4E6'), room('f1_lobby', 'Lobby & Reception', BM, 'wood', '#D8B48A', '#CFA97D'), room('f1_game', 'Game Zone', BR, 'carpet', '#A7C5F0', '#B3CEF4'), cor('f1')],
      furniture: [F('rug', 2, 1, 7, 6, { c: '#6F64B8', block: false }), F('table', 3, 3, 5, 3, { c: '#9C7A54' }), F('whiteboard', 7, 0, 3, 1, { block: false }), F('plant', 1, 1), F('plant', 1, 7), F('plant', 9, 7),
        F('counter', 12, 1, 6, 1), F('fridge', 19, 1), F('table', 13, 4, 4, 2, { c: '#D9B88A' }), F('plant', 11, 7), F('plant', 20, 7), F('plant', 20, 3),
        F('sofa', 23, 1, 4, 1, { c: '#B4536B' }), F('tv', 24, 0, 2, 1, { block: false }), F('table', 24, 3, 2, 1, { c: '#6B4A2E', low: true }), F('armchair', 28, 3), F('arcade', 29, 1), F('arcade', 30, 1), F('plant', 22, 7), F('plant', 30, 7), F('rug', 23, 2, 5, 3, { c: '#5A3E6B', block: false }),
        F('treadmill', 1, 13), F('treadmill', 2, 13), F('treadmill', 3, 13), F('dumbbell', 7, 13), F('dumbbell', 8, 13), F('rug', 2, 16, 3, 3, { c: '#38BDF8', block: false }), F('plant', 1, 18), F('plant', 9, 18),
        F('rcpt', 13, 14, 5, 2), F('sign', 12, 13, 7, 1, { block: false, float: true, rot: Math.PI / 4, text: 'MorbMyth AI Studio · HQ' }), F('plant', 11, 13), F('plant', 20, 13), F('plant', 11, 18), F('plant', 20, 18), F('armchair', 12, 17), F('armchair', 19, 17), F('rug', 12, 16, 7, 3, { c: '#B08A5C', block: false }),
        F('pingpong', 24, 15, 3, 2), F('arcade', 22, 13), F('arcade', 23, 13), F('arcade', 29, 13), F('plant', 22, 18), F('plant', 30, 18), F('rug', 23, 14, 7, 5, { c: '#7FA6E8', block: false })].concat(corFurn) },
    { id: 'f2', n: 2, name: 'Content Production', tag: 'Trend · Script · Voice · Design · Edit',
      rooms: [room('f2_trend', 'Trend Research Lab', TL, 'tile', '#C7D8E6', '#D3E1EC'), room('f2_script', 'Scriptwriting Studio', TM, 'wood', '#C99A6B', '#BF9061'), room('f2_voice', 'Voice Recording Studio', TR, 'carpet', '#4A3B5E', '#54446A'),
        room('f2_design', 'Design Studio', BL, 'carpet', '#F1D9E8', '#F7E4F0'), room('f2_edit', 'Video Editing Suite', BM, 'grid', '#22232F', '#2B2D3C'), room('f2_lib', 'Content Library', BR, 'wood', '#B98E63', '#AF845A'), cor('f2')],
      furniture: [F('screenwall', 2, 0, 7, 1, { block: false, c: '#22D3EE' }), F('desk', 3, 3, 3, 1, { owner: 'nexa' }), F('holo', 7, 5), F('plant', 1, 1), F('plant', 9, 1), F('plant', 1, 7), F('plant', 9, 7), F('table', 7, 2, 2, 1, { c: '#B8C4D0' }),
        F('shelf', 11, 1, 3, 1), F('shelf', 17, 1, 3, 1), F('whiteboard', 14, 0, 3, 1, { block: false }), F('desk', 14, 3, 2, 1, { owner: 'scriptwriter' }), F('armchair', 19, 5), F('plant', 11, 7), F('plant', 20, 7), F('rug', 12, 2, 8, 5, { c: '#A9764A', block: false }),
        F('booth', 24, 2, 3, 3), F('desk', 27, 3, 2, 1, { owner: 'voiceactor' }), F('plant', 22, 1), F('plant', 30, 1), F('plant', 22, 7), F('plant', 30, 7), F('rack', 29, 6),
        F('whiteboard', 1, 12, 3, 1, { block: false }), F('whiteboard', 7, 12, 3, 1, { block: false }), F('desk', 3, 15, 2, 1, { owner: 'designer' }), F('desk', 6, 15, 2, 1), F('plant', 1, 13), F('plant', 9, 13), F('plant', 1, 18), F('plant', 9, 18),
        F('screenwall', 12, 12, 7, 1, { block: false, c: '#A78BFA' }), F('desk', 14, 15, 3, 1, { owner: 'editor' }), F('desk', 18, 15, 2, 1), F('plant', 11, 13), F('plant', 20, 13), F('plant', 11, 18), F('plant', 20, 18),
        F('shelf', 22, 13, 4, 1), F('shelf', 27, 13, 3, 1), F('table', 24, 16, 3, 1, { c: '#7A5A3C' }), F('armchair', 29, 16), F('plant', 22, 18), F('plant', 30, 18)].concat(corFurn) },
    { id: 'f3', n: 3, name: 'Automation & Intelligence', tag: 'QC · Publish · Community · Analytics · Servers',
      rooms: [room('f3_qc', 'QC Command Center', TL, 'grid', '#1E2A3A', '#26364A'), room('f3_pub', 'Publishing Hub', TM, 'tile', '#D6E2F0', '#E3ECF6'), room('f3_comm', 'Community Command Center', TR, 'carpet', '#F3E1B5', '#F8EBC8'),
        room('f3_ana', 'Analytics Observatory', BL, 'tile', '#C9C7E8', '#D6D4F0'), room('f3_srv', 'Automation Server Room', BM, 'grid', '#2A2838', '#34314A'), room('f3_ops', 'Ops Lounge', BR, 'tile', '#D5D8DC', '#E6E8EB'), cor('f3')],
      furniture: [F('screenwall', 2, 0, 7, 1, { block: false, c: '#34D399' }), F('desk', 3, 3, 4, 1, { owner: 'byte' }), F('plant', 1, 7), F('plant', 9, 7), F('rack', 1, 1), F('rack', 9, 1),
        F('screenwall', 12, 0, 7, 1, { block: false, c: '#60A5FA' }), F('desk', 13, 3, 4, 1, { owner: 'cross' }), F('desk', 18, 3, 2, 1), F('plant', 11, 7), F('plant', 20, 7), F('holo', 12, 5),
        F('screenwall', 22, 0, 7, 1, { block: false, c: '#FACC15' }), F('desk', 24, 3, 3, 1, { owner: 'echo' }), F('sofa', 22, 6, 3, 1, { c: '#E58FA8' }), F('plant', 30, 1), F('plant', 30, 7),
        F('screenwall', 1, 12, 8, 1, { block: false, c: '#A78BFA' }), F('desk', 3, 15, 3, 1, { owner: 'metrix' }), F('holo', 7, 15), F('plant', 1, 18), F('plant', 9, 18), F('plant', 9, 13),
        F('cube', 13, 14, 4, 3), F('rack', 11, 18), F('rack', 12, 18), F('rack', 18, 18), F('rack', 19, 18), F('desk', 19, 15, 2, 1, { owner: 'ops' }), F('plant', 11, 13), F('plant', 20, 13),
        F('counter', 22, 13, 4, 1), F('fridge', 27, 13), F('table', 24, 16, 3, 1, { c: '#D9B88A' }), F('sofa', 28, 17, 2, 1, { c: '#7C6BC4' }), F('plant', 22, 18), F('plant', 30, 15)].concat(corFurn) },
    { id: 'f4', n: 4, name: 'Executive', tag: 'CEO · Strategy · War Room · Rooftop',
      rooms: [room('f4_strategy', 'Strategy Room', TL, 'carpet', '#6E7FA8', '#7B8CB4'), room('f4_ceo', 'MorbMyth CEO Office', TM, 'wood', '#B88A5E', '#AE8054'), room('f4_war', 'Creative War Room', TR, 'carpet', '#D4A5A5', '#DBB0B0'),
        room('f4_roof', 'Rooftop Garden', [0, 12, 31, 19], 'grass', '#7FB069', '#76A860'), cor('f4')],
      furniture: [F('rug', 2, 1, 7, 6, { c: '#4F5F88', block: false }), F('table', 3, 3, 5, 2, { c: '#8A6B4A' }), F('whiteboard', 1, 0, 3, 1, { block: false }), F('whiteboard', 6, 0, 3, 1, { block: false }), F('plant', 1, 7), F('plant', 9, 7), F('plant', 1, 1), F('plant', 9, 1),
        F('screenwall', 12, 0, 8, 1, { block: false, c: '#FFD027' }), F('desk', 14, 2, 3, 1, { owner: 'ceo' }), F('shelf', 11, 1, 1, 1), F('shelf', 20, 1, 1, 1), F('sofa', 12, 6, 3, 1, { c: '#7C6BC4' }), F('plant', 11, 7), F('plant', 20, 7), F('rug', 13, 3, 5, 3, { c: '#7A4B30', block: false }), F('table', 17, 5, 2, 1, { c: '#6B4A2E', low: true }),
        F('whiteboard', 22, 0, 3, 1, { block: false }), F('whiteboard', 27, 0, 3, 1, { block: false }), F('table', 24, 3, 4, 2, { c: '#9C7A54' }), F('holo', 29, 4), F('plant', 22, 7), F('plant', 30, 7), F('plant', 22, 1), F('plant', 30, 1),
        F('pool', 18, 14, 5, 3), F('tree', 2, 13), F('tree', 9, 18), F('tree', 28, 13), F('tree', 29, 18), F('bench', 7, 15, 3, 1), F('bench', 25, 17, 3, 1), F('flower', 12, 18), F('flower', 14, 13), F('flower', 20, 18), F('flower', 3, 17), F('sofa', 11, 16, 3, 1, { c: '#E58FA8' })].concat(corFurn) },
  ];

  const DEFS = [
    { id: 'ceo',          name: 'MorbMyth',  role: 'CEO',                      color: '#FFD027', hair: '#7A4B12', home: 3, desk: [15, 3] },
    { id: 'nexa',         name: 'NexaTrend', role: 'Trend Researcher',         color: '#22D3EE', hair: '#3B2A33', home: 1, desk: [4, 4] },
    { id: 'scriptwriter', name: 'KaelQuill', role: 'Scriptwriter',             color: '#60A5FA', hair: '#2B3A67', home: 1, desk: [14, 4] },
    { id: 'voiceactor',   name: 'VoxArden',  role: 'Voice Actor',              color: '#F472B6', hair: '#6B2145', home: 1, desk: [27, 4] },
    { id: 'designer',     name: 'MikaPixel', role: 'Designer',                 color: '#34D399', hair: '#5A3A1E', home: 1, desk: [3, 16] },
    { id: 'editor',       name: 'RivenCut',  role: 'Editor',                   color: '#A78BFA', hair: '#3B2A6B', home: 1, desk: [15, 16] },
    { id: 'byte',         name: 'ByteGuard', role: 'QC Inspector',             color: '#3B82F6', hair: '#12203F', home: 2, desk: [4, 4] },
    { id: 'cross',        name: 'CrossByte', role: 'Multi-Platform Publisher', color: '#FB923C', hair: '#F97316', home: 2, desk: [14, 4] },
    { id: 'echo',         name: 'EchoBee',   role: 'Community Manager',        color: '#FACC15', hair: '#FCD34D', home: 2, desk: [25, 4] },
    { id: 'metrix',       name: 'Metrix',    role: 'Data Analyst',             color: '#8B5CF6', hair: '#1E3A8A', home: 2, desk: [4, 16] },
  ];

  const D = { n: [0, -1], s: [0, 1], e: [1, 0], w: [-1, 0] };
  const mk = fi => (id, room, x, y, face, pose, kind, act, say, extra) => Object.assign({ id: 'f' + (fi + 1) + '_' + id, floor: fi, room: 'f' + (fi + 1) + '_' + room, x, y, face: D[face], pose, kind, act, say: say || [] }, extra || {});
  const C = { chair: true };
  const SPOTS = [];
  { // ---- Lantai 1 ----
    const S = mk(0);
    SPOTS.push(S('m_wb', 'meeting', 8, 1, 'n', 'stand', 'meet', 'Mencoret whiteboard', ['Brainstorm konten…', 'Hook dulu, baru fakta!']));
    [3, 4, 5, 6, 7].forEach((x, i) => SPOTS.push(S('m_n' + i, 'meeting', x, 2, 's', i % 2 ? 'speak' : 'sit', 'meet', 'Rapat kecil', ['Setuju!', 'Boleh juga idenya', 'Catat ya'], C)));
    [3, 4, 6, 7].forEach((x, i) => SPOTS.push(S('m_s' + i, 'meeting', x, 6, 'n', i % 2 ? 'sit' : 'speak', 'meet', 'Rapat kecil', ['Noted!', 'Ada usul lain?'], C)));
    SPOTS.push(S('k_coffee', 'cafe', 13, 2, 'n', 'drink', 'food', 'Bikin kopi', ['Kopi dulu biar melek', 'Pahit tapi nikmat']), S('k_fridge', 'cafe', 19, 2, 'n', 'stand', 'food', 'Cari camilan', ['Ada es krim?']));
    [[12, 4, 'e'], [12, 5, 'e'], [17, 4, 'w'], [17, 5, 'w']].forEach(([x, y, f], i) => SPOTS.push(S('k_eat' + i, 'cafe', x, y, f, 'eat', 'food', 'Ngemil', ['Enak!', 'Camilan sore'], C)));
    [23, 24, 25, 26].forEach((x, i) => SPOTS.push(S('l_sofa' + i, 'lounge', x, 1, 's', 'sit', 'rest', 'Santai di sofa', ['Capek juga ya…', 'Rebahan sebentar'])));
    SPOTS.push(S('l_arm', 'lounge', 28, 3, 'n', 'sit', 'rest', 'Santai', ['Hmm, adem']), S('l_arc1', 'lounge', 29, 2, 'n', 'arcade', 'game', 'Main arcade', ['High score!']), S('l_arc2', 'lounge', 30, 2, 'n', 'arcade', 'game', 'Main arcade', ['Satu ronde lagi']));
    SPOTS.push(S('g_run1', 'gym', 1, 13, 's', 'run', 'sport', 'Jogging di treadmill', ['Huh… huh…']), S('g_run2', 'gym', 2, 13, 's', 'run', 'sport', 'Jogging di treadmill', ['Semangat!']), S('g_run3', 'gym', 3, 13, 's', 'run', 'sport', 'Jogging di treadmill', ['Kuat!']),
      S('g_lift', 'gym', 7, 14, 'n', 'exercise', 'sport', 'Angkat dumbbell', ['Berat…', 'Gas!']), S('g_yoga', 'gym', 3, 17, 's', 'exercise', 'sport', 'Senam di matras', ['Tarik napas…']));
    SPOTS.push(S('b_wait1', 'lobby', 12, 17, 'n', 'sit', 'rest', 'Duduk di lobby', ['Menunggu tamu…']), S('b_wait2', 'lobby', 19, 17, 'n', 'sit', 'rest', 'Duduk di lobby', ['Lobby tenang banget']), S('b_view', 'lobby', 15, 17, 'n', 'stand', 'meet', 'Menyambut tamu', ['Selamat datang di HQ!']));
    SPOTS.push(S('z_pp1', 'game', 23, 15, 'e', 'play', 'game', 'Main ping pong', ['Smash!']), S('z_pp2', 'game', 27, 15, 'w', 'play', 'game', 'Main ping pong', ['Tangkis!']), S('z_pp3', 'game', 23, 16, 'e', 'play', 'game', 'Main ping pong', ['Servis!']), S('z_pp4', 'game', 27, 16, 'w', 'play', 'game', 'Main ping pong', ['Jangan kalah!']),
      S('z_arc1', 'game', 22, 14, 'n', 'arcade', 'game', 'Main arcade', ['Level terakhir!']), S('z_arc2', 'game', 23, 14, 'n', 'arcade', 'game', 'Main arcade', ['Hampir!']), S('z_arc3', 'game', 29, 14, 'n', 'arcade', 'game', 'Main arcade', ['Satu lagi!']));
    SPOTS.push(S('c_chat1', 'cor', 8, 10, 's', 'stand', 'chat', 'Ngobrol di koridor', ['Eh, tau nggak…', 'Sudah makan?']), S('c_chat2', 'cor', 22, 10, 's', 'stand', 'chat', 'Ngobrol di koridor', ['Kerjaan lancar?']));
  }
  { // ---- Lantai 2 ----
    const S = mk(1);
    SPOTS.push(S('t_scan', 'trend', 5, 2, 'n', 'stand', 'tech', 'Memantau tren', ['Tren baru di TikTok!', 'Reddit lagi ramai']), S('t_holo', 'trend', 7, 6, 'n', 'stand', 'tech', 'Baca hologram', ['Data masuk…']), S('t_tab', 'trend', 7, 3, 's', 'sit', 'focus', 'Riset di meja', ['Catat topiknya'], C));
    SPOTS.push(S('s_read1', 'script', 12, 2, 'n', 'read', 'read', 'Cari referensi', ['Buku ini menarik']), S('s_read2', 'script', 18, 2, 'n', 'read', 'read', 'Cari referensi', ['Fakta sejarah baru!']), S('s_arm', 'script', 19, 5, 'n', 'sitread', 'read', 'Baca santai', ['Tenang banget']));
    SPOTS.push(S('v_booth', 'voice', 25, 5, 's', 'speak', 'tech', 'Latihan vokal', ['Tes, satu dua…', 'La la la…']), S('v_rack', 'voice', 29, 7, 'n', 'stand', 'tech', 'Cek peralatan audio', ['Level audio aman']));
    SPOTS.push(S('d_board', 'design', 2, 13, 's', 'stand', 'focus', 'Lihat moodboard', ['Warnanya kurang pop']), S('d_tab', 'design', 6, 16, 'n', 'type', 'focus', 'Sketsa di tablet', ['Sketsa dulu'], C), S('d_wall', 'design', 8, 13, 's', 'stand', 'focus', 'Review desain', ['Layout rapi!']));
    SPOTS.push(S('e_screen', 'edit', 13, 13, 's', 'stand', 'tech', 'Review footage', ['Cut-nya pas']), S('e_desk2', 'edit', 18, 16, 'n', 'type', 'tech', 'Edit di meja 2', ['Render dikit lagi'], C));
    SPOTS.push(S('l_read1', 'lib', 23, 14, 's', 'read', 'read', 'Cari buku', ['Referensi bagus']), S('l_read2', 'lib', 28, 14, 's', 'read', 'read', 'Cari buku', ['Menarik…']), S('l_arm', 'lib', 29, 16, 'n', 'sitread', 'read', 'Baca santai', ['Rehat sebentar']), S('l_tab', 'lib', 24, 17, 'n', 'sit', 'read', 'Menulis catatan', ['Catat dulu'], C));
    SPOTS.push(S('c_chat1', 'cor', 8, 10, 's', 'stand', 'chat', 'Ngobrol di koridor', ['Brief hari ini?']), S('c_chat2', 'cor', 22, 10, 's', 'stand', 'chat', 'Ngobrol di koridor', ['Mantap!']), S('patrol', 'cor', 18, 10, 's', 'stand', 'patrol', 'Keliling cek tim', ['Gimana progresnya?'], { owner: 'ceo', idle: false }));
  }
  { // ---- Lantai 3 ----
    const S = mk(2);
    SPOTS.push(S('q_screen', 'qc', 5, 2, 'n', 'stand', 'tech', 'Inspeksi video', ['Rasio 9:16 aman', 'Durasi di bawah 60 detik']), S('q_rack', 'qc', 2, 2, 's', 'stand', 'tech', 'Cek rack QC', ['Semua hijau']));
    SPOTS.push(S('p_screen', 'pub', 15, 2, 'n', 'stand', 'tech', 'Atur jadwal posting', ['Kirim ke 4 platform!']), S('p_desk2', 'pub', 19, 4, 'n', 'type', 'tech', 'Meja distribusi', ['Upload serentak'], C), S('p_holo', 'pub', 12, 6, 'n', 'stand', 'tech', 'Baca hologram', ['Jalur publish siap']));
    SPOTS.push(S('m_screen', 'comm', 26, 2, 'n', 'stand', 'tech', 'Pantau komentar', ['Banyak yang suka!']), S('m_sofa', 'comm', 22, 6, 's', 'sit', 'rest', 'Santai di sofa', ['Balas komentar dulu']), S('m_sofa2', 'comm', 23, 6, 's', 'sit', 'rest', 'Santai di sofa', ['Hehe lucu']));
    SPOTS.push(S('a_screen', 'ana', 3, 13, 's', 'stand', 'tech', 'Baca grafik', ['Retensi naik!']), S('a_holo', 'ana', 7, 14, 's', 'stand', 'tech', 'Analisis hologram', ['Tren harian cerah']));
    SPOTS.push(S('v_check1', 'srv', 12, 14, 'e', 'stand', 'tech', 'Cek server', ['Uptime aman']), S('v_check2', 'srv', 19, 14, 'w', 'stand', 'tech', 'Cek server', ['Suhu normal']), S('v_ops', 'srv', 19, 16, 'n', 'type', 'tech', 'Monitoring server', ['Log bersih'], C));
    SPOTS.push(S('o_coffee', 'ops', 23, 14, 'n', 'drink', 'food', 'Bikin kopi', ['Kopi dulu']), S('o_fridge', 'ops', 27, 14, 'n', 'stand', 'food', 'Cari camilan', ['Ada yogurt?']), S('o_eat1', 'ops', 24, 17, 'n', 'eat', 'food', 'Ngemil', ['Nyam'], C), S('o_eat2', 'ops', 26, 17, 'n', 'eat', 'food', 'Ngemil', ['Enak!'], C), S('o_sofa', 'ops', 28, 17, 'n', 'sit', 'rest', 'Santai', ['Istirahat']));
    SPOTS.push(S('c_chat1', 'cor', 8, 10, 's', 'stand', 'chat', 'Ngobrol di koridor', ['Laporan masuk?']), S('c_chat2', 'cor', 22, 10, 's', 'stand', 'chat', 'Ngobrol di koridor', ['Aman terkendali']));
  }
  { // ---- Lantai 4 ----
    const S = mk(3);
    [3, 4, 5, 6, 7].forEach((x, i) => SPOTS.push(S('s_n' + i, 'strategy', x, 2, 's', 'sit', 'meet', 'Diskusi strategi', ['Target kuartal ini…', 'Fokus ke retensi']), S('s_s' + i, 'strategy', x, 5, 'n', 'sit', 'meet', 'Diskusi strategi', ['Setuju!'])));
    SPOTS.push(S('c_view', 'ceo', 17, 4, 'n', 'stand', 'meet', 'Menatap kota', ['Semua lancar?', 'Target hari ini: 3 video'], { owner: 'ceo' }), S('c_sofa', 'ceo', 12, 6, 's', 'sit', 'rest', 'Santai di sofa', ['Sebentar saja…'], { owner: 'ceo' }));
    SPOTS.push(S('w_board', 'war', 23, 1, 's', 'stand', 'meet', 'Susun ide kreatif', ['Ide liar dulu!']), S('w_n', 'war', 25, 2, 's', 'sit', 'meet', 'Brainstorm', ['Nah ini bagus']), S('w_s', 'war', 25, 5, 'n', 'sit', 'meet', 'Brainstorm', ['Coba sudut lain']), S('w_holo', 'war', 28, 4, 'n', 'stand', 'tech', 'Lihat hologram', ['Mockup keren']));
    SPOTS.push(S('r_pool', 'roof', 17, 14, 's', 'stand', 'nature', 'Santai dekat kolam', ['Airnya segar']), S('r_bench1', 'roof', 8, 15, 's', 'sit', 'rest', 'Duduk di taman', ['Anginnya sejuk']), S('r_bench2', 'roof', 26, 17, 'n', 'sit', 'rest', 'Duduk di taman', ['Damai…']),
      S('r_sofa', 'roof', 12, 16, 's', 'sit', 'rest', 'Rebahan di rooftop', ['Langitnya bagus']), S('r_stroll', 'roof', 15, 17, 'n', 'stand', 'nature', 'Menikmati angin', ['Hirup udara segar']), S('r_flower', 'roof', 13, 14, 's', 'stand', 'nature', 'Menyiram bunga', ['Tumbuh ya']));
    SPOTS.push(S('c_chat1', 'cor', 8, 10, 's', 'stand', 'chat', 'Ngobrol di koridor', ['Rapat selesai?']), S('c_chat2', 'cor', 22, 10, 's', 'stand', 'chat', 'Ngobrol di koridor', ['Oke bos']));
  }
  for (const d of DEFS) SPOTS.push(Object.assign(mk(d.home)('d_' + d.id, '', d.desk[0], d.desk[1], 'n', 'sit', 'desk', 'Di meja kerja', ['Rapikan meja dulu', 'Cek email'], { owner: d.id, desk: true, chair: true }), { id: 'd_' + d.id, room: '' }));
  // ops desk (kursi kosong ops) tidak punya pemilik: owner 'ops' hanya dekor.
  for (const s of SPOTS) if (!s.room) { const f = FLOORS[s.floor]; const r = f.rooms.find(r => s.x > r.r[0] && s.x < r.r[2] && s.y > r.r[1] && s.y < r.r[3]); s.room = r ? r.id : f.id + '_cor'; }

  const FAV = {
    ceo: { meet: 3, rest: 1.5, nature: 2 }, nexa: { tech: 3, focus: 1.5, chat: 1.2 }, scriptwriter: { read: 3.5, focus: 2.5, meet: 1.3 }, voiceactor: { tech: 2, food: 1.8, rest: 1.3 },
    designer: { focus: 2.5, nature: 2, read: 1.5 }, editor: { tech: 2.5, game: 2.5, sport: 1.3 }, byte: { tech: 3, sport: 1.5 }, cross: { tech: 3, game: 1.5 }, echo: { rest: 2, food: 2, chat: 2.5 }, metrix: { tech: 3, read: 1.5, nature: 1.3 },
  };
  const ACTION_POSE = { typing: 'type', working: 'type', rendering: 'type', researching: 'type', inspecting: 'type', publishing: 'type', replying: 'type', speaking: 'speak', delegating: 'wave', monitoring: 'sit', approving: 'cheer', analyzing: 'type', alert: 'alert' };

  // Briefing: semua ke Meeting Room Lantai 1 dulu
  const BRIEF_SPOT = { ceo: 'f1_m_wb', nexa: 'f1_m_n0', scriptwriter: 'f1_m_n1', voiceactor: 'f1_m_n2', designer: 'f1_m_n3', editor: 'f1_m_n4', byte: 'f1_m_s0', cross: 'f1_m_s1', echo: 'f1_m_s2', metrix: 'f1_m_s3' };
  const BRIEF_LINES = [
    [0.5, 'ceo', 'Pagi tim! Kita produksi video Shorts baru hari ini.', 2.3],
    [3.0, 'nexa', 'NexaTrend: topik panas sudah masuk Sheets.', 2.2], [5.4, 'scriptwriter', 'KaelQuill siap. Hook-nya kuat!', 2.1], [7.7, 'voiceactor', 'VoxArden standby, suara siap.', 2.1],
    [10.0, 'designer', 'MikaPixel: visual & BGM aman.', 2.1], [12.3, 'editor', 'RivenCut siap render. Gas!', 2.1], [14.6, 'byte', 'ByteGuard akan cek durasi & rasio.', 2.1],
    [16.9, 'cross', 'CrossByte kirim ke 4 platform.', 2.1], [19.2, 'echo', 'EchoBee jaga kolom komentar!', 2.1], [21.5, 'metrix', 'Metrix siapkan laporan harian.', 2.1],
    [23.9, 'ceo', 'Oke, semua ke lantai masing-masing. Mulai!', 2.4],
  ];
  const BRIEF_END = 27.2;

  function buildTiles(f) {
    const g = [];
    for (let y = 0; y < H; y++) { g.push([]); for (let x = 0; x < W; x++) g[y].push({ wall: false, room: null, door: false, block: false, lift: false }); }
    for (const r of f.rooms) {
      const [x0, y0, x1, y1] = r.r;
      for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) { if (x === x0 || x === x1 || y === y0 || y === y1) g[y][x].wall = true; else g[y][x].room = r.id; }
    }
    for (const [x, y] of DOORS) { g[y][x].wall = false; g[y][x].door = true; }
    g[LIFT.y][LIFT.x].lift = true;
    for (const t of f.furniture) { if (t.block === false) continue; for (let y = t.y; y < t.y + t.h; y++) for (let x = t.x; x < t.x + t.w; x++) g[y][x].block = true; }
    return g;
  }

  function create(opts) {
    opts = opts || {}; const rand = opts.rand || Math.random;
    const floors = FLOORS.map(f => Object.assign({}, f, { tiles: buildTiles(f), spots: SPOTS.filter(s => s.floor === FLOORS.indexOf(f)) }));
    const roomName = id => { for (const f of FLOORS) { const r = f.rooms.find(r => r.id === id); if (r) return r.name; } return ''; };
    const walk = (fi, x, y) => x >= 0 && y >= 0 && x < W && y < H && !floors[fi].tiles[y][x].wall && !floors[fi].tiles[y][x].block;
    function bfs(fi, sx, sy, gx, gy) {
      if (sx === gx && sy === gy) return [];
      const prev = new Map(), key = (x, y) => y * W + x, q = [[sx, sy]], T = floors[fi].tiles; prev.set(key(sx, sy), null);
      for (let i = 0; i < q.length; i++) {
        const [x, y] = q[i];
        for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
          const nx = x + dx, ny = y + dy, k = key(nx, ny); if (prev.has(k) || nx < 0 || ny < 0 || nx >= W || ny >= H) continue;
          const goal = nx === gx && ny === gy; if (!goal && !walk(fi, nx, ny)) continue; if (goal && T[ny][nx].wall) continue;
          prev.set(k, [x, y]);
          if (goal) { const path = []; let c = [nx, ny]; while (c && !(c[0] === sx && c[1] === sy)) { path.push(c); c = prev.get(key(c[0], c[1])); } return path.reverse(); }
          q.push([nx, ny]);
        }
      }
      return null;
    }
    const reserved = {}, spotById = {}; SPOTS.forEach(s => spotById[s.id] = s);
    const agents = DEFS.map((d, i) => { const desk = spotById['d_' + d.id];
      return Object.assign({}, d, { floor: desk.floor, tx: desk.x, ty: desk.y, x: desk.x + .5, y: desk.y + .5, path: [], target: desk, arrived: true, work: null, leaveAt: 1 + i * 1.3, bubble: '', bubbleUntil: 0, pose: 'sit', face: desk.face.slice(), moving: false, fx: '', act: 'Di meja kerja', phase: 0, room: desk.room, lifting: false, liftT: 0 }); });
    for (const a of agents) reserved[a.target.id] = a.id;
    const byId = {}; agents.forEach(a => byId[a.id] = a);
    const sim = { W, H, LIFT, floors, spots: SPOTS, spotById, agents, byId, t: 0, bfs, walk, roomName };

    function plan(a, spot) {
      if (a.floor === spot.floor) return bfs(a.floor, a.tx, a.ty, spot.x, spot.y);
      const p1 = bfs(a.floor, a.tx, a.ty, LIFT.x, LIFT.y), p2 = bfs(spot.floor, LIFT.x, LIFT.y, spot.x, spot.y); if (!p1 || !p2) return null;
      return p1.concat([{ lift: spot.floor }], p2);
    }
    function goTo(a, spot) {
      if (a.lifting) { a.pendingSpot = spot; if (reserved[a.target && a.target.id] === a.id) delete reserved[a.target.id]; reserved[spot.id] = a.id; a.target = spot; return true; }
      const p = plan(a, spot); if (!p) return false;
      const off = Math.hypot(a.x - (a.tx + .5), a.y - (a.ty + .5)) > .05;
      if (reserved[a.target && a.target.id] === a.id) delete reserved[a.target.id];
      reserved[spot.id] = a.id; a.target = spot; a.arrived = false; a.pendingSpot = null;
      a.path = off ? [[a.tx, a.ty]].concat(p) : p; if (!a.path.length) arrive(a); return true;
    }
    function arrive(a) {
      const s = a.target; a.arrived = true; a.moving = false; a.face = s.face.slice(); a.room = s.room;
      if (!a.work && !a.brief) { a.leaveAt = sim.t + 8 + rand() * 9; if (s.say.length && rand() < .65) { a.bubble = s.say[Math.floor(rand() * s.say.length)]; a.bubbleUntil = sim.t + 5; } }
    }
    function pickSpot(a) {
      const pool = SPOTS.filter(s => s.idle !== false && (!s.owner || s.owner === a.id) && s !== a.target && (!reserved[s.id] || reserved[s.id] === a.id));
      const fav = FAV[a.id] || {}, wts = pool.map(s => (fav[s.kind] || 1) * (s.floor === a.home ? 4 : .7));
      let r = rand() * wts.reduce((p, c) => p + c, 0); for (let i = 0; i < pool.length; i++) { r -= wts[i]; if (r <= 0) return pool[i]; } return pool[0];
    }

    sim.briefing = null; sim.pending = [];
    sim.endBriefing = () => { if (sim.briefing) endBriefing(); };
    sim.startBriefing = () => {
      if (sim.briefing) return false; sim.briefing = { phase: 'gather', t0: sim.t, tMeet: 0, idx: 0, speaker: null, speakUntil: 0 };
      for (const a of agents) { a.work = null; a.fx = ''; a.bubble = ''; a.brief = true; goTo(a, spotById[BRIEF_SPOT[a.id]]); } return true;
    };
    function endBriefing() {
      const ev = sim.pending.splice(0); sim.briefing = null;
      for (const a of agents) { a.brief = false; a.bubble = ''; a.work = null; goTo(a, spotById[a.id === 'ceo' ? 'f2_patrol' : 'd_' + a.id]); a.holdUntil = sim.t + 45; }
      for (const e of ev) sim.event(e);
    }
    function stepBriefing() {
      const b = sim.briefing; if (!b) return;
      if (b.phase === 'gather') { if (agents.every(a => a.arrived && !a.path.length && !a.lifting) || sim.t - b.t0 > 70) { b.phase = 'meet'; b.tMeet = sim.t; } }
      else {
        while (b.idx < BRIEF_LINES.length && sim.t - b.tMeet >= BRIEF_LINES[b.idx][0]) { const [, id, txt, dur] = BRIEF_LINES[b.idx++]; sim.say(id, txt, dur + .3); b.speaker = id; b.speakUntil = sim.t + dur; }
        if (b.speaker && sim.t > b.speakUntil) b.speaker = null;
        if (b.idx >= BRIEF_LINES.length && sim.t - b.tMeet > BRIEF_END) endBriefing();
      }
    }
    sim.say = (id, msg, secs) => { const a = byId[id]; if (a) { a.bubble = String(msg || ''); a.bubbleUntil = sim.t + (secs || 6); } };
    sim.agentsOnFloor = fi => agents.filter(a => a.floor === fi && !a.lifting);

    sim.event = ev => {
      const a = byId[String(ev.agent || '').toLowerCase()]; if (!a) return;
      if (sim.briefing) { if (sim.pending.length < 120) sim.pending.push(ev); return; }
      const act = String(ev.action || 'working'), msg = String(ev.message || '');
      if (act === 'idle') { if (a.work) { a.work.until = sim.t + 3; a.work.action = 'idle'; } if (msg) { a.bubble = msg; a.bubbleUntil = sim.t + 4; } return; }
      a.work = { action: act, msg, until: sim.t + (act === 'alert' ? 9 : a.id === 'ceo' ? 12 : 150) }; a.bubble = msg; a.bubbleUntil = a.work.until;
      if (a.id !== 'ceo' && act !== 'alert') for (const o of agents) if (o !== a && o.id !== 'ceo' && o.work && o.work.until > sim.t + 3) { o.work.until = sim.t + 3; o.work.action = 'idle'; }
      const want = (a.id === 'ceo' && act === 'monitoring') ? spotById.f2_patrol : spotById['d_' + a.id]; if (a.target !== want) goTo(a, want);
    };

    function step(a, dt) {
      if (a.work && sim.t > a.work.until) { a.work = null; a.fx = ''; a.leaveAt = sim.t + 2 + rand() * 3; if (a.bubbleUntil > sim.t + 4) a.bubbleUntil = sim.t + 1; }
      if (a.bubble && sim.t > a.bubbleUntil) a.bubble = '';
      if (a.path.length) {
        const it = a.path[0];
        if (it.lift !== undefined) {                                   // naik/turun lift
          if (!a.lifting) { a.lifting = true; a.liftT = LIFT_T + .45 * Math.abs(it.lift - a.floor); }
          a.liftT -= dt; a.moving = false; a.pose = 'stand'; a.act = 'Naik lift ke Lantai ' + (it.lift + 1);
          if (a.liftT <= 0) { a.floor = it.lift; a.lifting = false; a.path.shift(); if (a.pendingSpot) { const s = a.pendingSpot; a.pendingSpot = null; a.path = []; a.target = s; goTo(a, s); } else if (!a.path.length) arrive(a); }
          return;
        }
        const [nx, ny] = it, cx = nx + .5, cy = ny + .5, dx = cx - a.x, dy = cy - a.y, d = Math.hypot(dx, dy), st = SPEED * dt; a.moving = true; a.phase += dt * 9;
        if (d <= st) { a.x = cx; a.y = cy; a.tx = nx; a.ty = ny; a.path.shift(); if (!a.path.length) arrive(a); } else { a.x += dx / d * st; a.y += dy / d * st; a.face = [dx / d, dy / d]; }
        a.pose = 'walk'; a.fx = ''; a.act = a.brief ? 'Menuju Meeting Room' : 'Menuju ' + roomName(a.target.room); return;
      }
      a.moving = false;
      if (a.brief) { const b = sim.briefing, talk = b && b.speaker === a.id; a.pose = talk ? 'speak' : a.target.pose; a.fx = ''; a.face = a.target.face.slice(); a.act = 'Briefing di Meeting Room'; return; }
      if (a.work) { const w = a.work; a.pose = (a.target.id === 'f2_patrol') ? 'stand' : (ACTION_POSE[w.action] || 'type'); a.fx = w.action === 'rendering' ? 'render' : w.action === 'alert' ? 'alert' : ''; a.act = w.msg || w.action; a.face = a.target.face.slice(); return; }
      a.pose = a.target.pose; a.fx = ''; a.act = a.target.act;
      if (sim.t >= a.leaveAt && sim.t >= (a.holdUntil || 0)) { const s = pickSpot(a); if (s) goTo(a, s); }
    }
    sim.update = dt => { dt = Math.min(dt, .1); sim.t += dt; for (const a of agents) step(a, dt); stepBriefing(); };
    return sim;
  }
  const api = { create, W, H, FLOORS, DOORS, SPOTS, DEFS, SPEED, LIFT, BRIEF_SPOT };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.OfficeSim = api;
})(typeof window !== 'undefined' ? window : globalThis);
