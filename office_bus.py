"""Bus event untuk Office. Modul MANDIRI: jangan `from server import ...`
(server.py dijalankan sebagai __main__, jadi import itu memuat salinan kedua server.py
dengan event-loop kosong -> notify_office diam-diam tidak pernah mengirim apa pun).

notify_office() mengirim event ke DUA tujuan:
  1) WebSocket /ws/office           -> kantor 3D bawaan ("Ringan")
  2) HTTP POST {adapter}/office/event -> Hermes3D (Next.js + Three.js) lewat adapter Hermes
Pengiriman ke Hermes3D dilakukan di thread terpisah sehingga pipeline tidak pernah terblokir."""
import asyncio
import json
import os
import queue
import threading
import time
import urllib.request

connections = set()
loop = None
last = {}          # state terakhir per agent -> dikirim ke klien yang baru connect

ADAPTER_URL = os.getenv("HERMES_ADAPTER_URL", "http://127.0.0.1:%s" % os.getenv("HERMES_ADAPTER_PORT", "18789")).rstrip("/")
OFFICE_TOKEN = os.getenv("OFFICE_EVENT_TOKEN", "")
adapter_ok = False                       # status terakhir pengiriman ke Hermes3D

_q = queue.Queue(maxsize=300)
_worker = None
_worker_lock = threading.Lock()


def set_loop(lp):
    global loop
    loop = lp


async def _send_all(data):
    for ws in list(connections):
        try:
            await ws.send_json(data)
        except Exception:
            connections.discard(ws)


def _forward_loop():
    """Satu worker -> urutan event terjaga. Jika adapter mati, jeda 10 dtk lalu coba lagi."""
    global adapter_ok
    pause_until = 0.0
    while True:
        data = _q.get()
        if time.time() < pause_until:
            continue
        try:
            headers = {"Content-Type": "application/json"}
            if OFFICE_TOKEN:
                headers["X-Office-Token"] = OFFICE_TOKEN
            req = urllib.request.Request(ADAPTER_URL + "/office/event", json.dumps(data).encode(), headers)
            urllib.request.urlopen(req, timeout=2).read()
            adapter_ok = True
        except Exception:
            adapter_ok = False
            pause_until = time.time() + 10


def _ensure_worker():
    global _worker
    with _worker_lock:
        if _worker is None or not _worker.is_alive():
            _worker = threading.Thread(target=_forward_loop, daemon=True, name="office-forward")
            _worker.start()


def notify_office(agent, action, message, progress=0):
    """Thread-safe; aman dipanggil dari thread automation mana pun."""
    data = {"agent": agent, "action": action, "message": message,
            "progress": progress, "ts": time.time()}
    last[agent] = data
    if loop is not None and loop.is_running():
        asyncio.run_coroutine_threadsafe(_send_all(data), loop)
    _ensure_worker()
    try:
        _q.put_nowait(data)
    except queue.Full:
        pass


async def register(ws):
    await ws.accept()
    connections.add(ws)
    for d in list(last.values()):
        await ws.send_json(d)
