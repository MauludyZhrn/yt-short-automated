"""Aplikasi desktop 100% gratis: FastAPI (Shorts) + adapter Hermes (Ollama) + Hermes3D (3D Office)
dalam satu jendela native (pywebview).

    pip install pywebview uvicorn      |   python desktop.py
Opsi env:  SERVER_PORT=8000  HERMES3D_PORT=3000  HERMES3D_DIR=./Hermes3D  NO_HERMES3D=1
Build .exe (opsional): pyinstaller --noconfirm --add-data "web;web" desktop.py  (Node & folder Hermes3D tetap diperlukan)"""
import atexit, os, shutil, socket, subprocess, sys, threading, time, urllib.request
import uvicorn

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT, ".env"))
except ImportError:
    pass

HOST = "127.0.0.1"
PORT = int(os.getenv("SERVER_PORT", "8000"))
H3D_PORT = int(os.getenv("HERMES3D_PORT", "3000"))
ADAPTER_PORT = int(os.getenv("HERMES_ADAPTER_PORT", "18789"))
H3D_DIR = os.path.abspath(os.getenv("HERMES3D_DIR", os.path.join(ROOT, "Hermes3D")))
OLLAMA = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
procs, logs = [], []
server_error = []


def port_open(port, host=HOST):
    try:
        socket.create_connection((host, port), 0.4).close()
        return True
    except OSError:
        return False


def wait_port(port, tries=60, delay=0.5):
    for _ in range(tries):
        if port_open(port):
            return True
        time.sleep(delay)
    return False


def spawn(cmd, cwd, env_extra=None, name=""):
    env = {**os.environ, **(env_extra or {})}
    log = open(os.path.join(ROOT, f"{name or 'proc'}.log"), "ab")
    logs.append(log)
    kw = {"creationflags": 0x08000000} if os.name == "nt" else {}     # CREATE_NO_WINDOW
    p = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, **kw)
    procs.append(p)
    return p


def stop_all():
    for p in procs:
        try:
            p.terminate()
        except Exception:
            pass
    for f in logs:
        try:
            f.close()
        except Exception:
            pass


atexit.register(stop_all)


def ensure_ollama():
    """Ollama harus jalan lokal. Coba `ollama serve` otomatis bila terpasang."""
    def up():
        try:
            urllib.request.urlopen(OLLAMA + "/api/tags", timeout=1.5).read(8)
            return True
        except Exception:
            return False
    if up():
        return True
    exe = shutil.which("ollama")
    if exe:
        spawn([exe, "serve"], ROOT, name="ollama")
        for _ in range(20):
            time.sleep(0.5)
            if up():
                return True
    print("⚠️ Ollama tidak terdeteksi. Pasang dari https://ollama.com lalu: ollama pull hermes3:8b")
    return False


def _same_file(a, b):
    with open(a, "rb") as fa, open(b, "rb") as fb:
        return fa.read() == fb.read()


def prepare_hermes3d():
    """Clone Hermes3D bila belum ada, lalu pasang patch (Ollama + bridge pipeline + embed iframe)."""
    if not os.path.isdir(H3D_DIR) and shutil.which("git"):
        print("⬇️ git clone Hermes3D...")
        subprocess.run(["git", "clone", "https://github.com/iamlukethedev/Hermes3D.git", H3D_DIR])
    patch = os.path.join(ROOT, "hermes3d_patch")
    if os.path.isdir(H3D_DIR) and os.path.isdir(patch):
        for dp, _, files in os.walk(patch):
            for f in files:
                src = os.path.join(dp, f)
                dst = os.path.join(H3D_DIR, os.path.relpath(src, patch))
                if not os.path.exists(dst) or not _same_file(src, dst):
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copyfile(src, dst)


def start_hermes3d():
    if os.getenv("NO_HERMES3D") == "1":
        return
    prepare_hermes3d()
    if not os.path.isdir(H3D_DIR):
        print(f"⚠️ Folder Hermes3D tidak ada ({H3D_DIR}). Jalankan: git clone https://github.com/iamlukethedev/Hermes3D.git")
        return
    node, npm = shutil.which("node"), shutil.which("npm")
    if not node or not npm:
        print("⚠️ Node.js 20+ belum terpasang (https://nodejs.org) → tab Office memakai kantor Ringan.")
        return
    if not os.path.isdir(os.path.join(H3D_DIR, "node_modules")):
        print("📦 Pertama kali: npm install Hermes3D (beberapa menit)...")
        subprocess.run([npm, "install", "--no-audit", "--no-fund"], cwd=H3D_DIR, shell=(os.name == "nt"))
    common = {"HOST": HOST, "PORT": str(H3D_PORT),
              "HERMES_API_URL": os.getenv("HERMES_API_URL", OLLAMA),
              "HERMES_MODEL": os.getenv("OLLAMA_MODEL") or os.getenv("HERMES_MODEL", "hermes3:8b"),
              "HERMES3D_GATEWAY_URL": f"ws://{HOST}:{ADAPTER_PORT}",
              "HERMES3D_GATEWAY_ADAPTER_TYPE": "hermes",
              "SHORTS_API_URL": f"http://{HOST}:{PORT}",
              "HERMES3D_FRAME_ANCESTORS": f"http://{HOST}:{PORT} http://localhost:{PORT}"}
    if not port_open(ADAPTER_PORT):
        spawn([node, "server/hermes-gateway-adapter.js"], H3D_DIR, common, "hermes-adapter")
    if not port_open(H3D_PORT):
        prod = os.path.exists(os.path.join(H3D_DIR, ".next", "BUILD_ID"))
        cmd = [node, "server/index.js"] + ([] if prod else ["--dev"])
        spawn(cmd, H3D_DIR, {**common, "NODE_ENV": "production" if prod else "development"}, "hermes3d")


def _serve():
    try:
        import server
        uvicorn.run(server.app, host=HOST, port=PORT, access_log=False)
    except BaseException as exc:          # tampilkan penyebab asli, jangan menunggu timeout diam-diam
        server_error.append(exc)
        print(f"❌ Server FastAPI berhenti: {exc!r}")


if __name__ == "__main__":
    if port_open(PORT):
        sys.exit(f"❌ Port {PORT} sudah dipakai proses lain (mungkin instance lama). Tutup dulu atau ubah SERVER_PORT di .env.")
    ensure_ollama()
    start_hermes3d()
    threading.Thread(target=_serve, daemon=True).start()
    for _ in range(240):                  # maks ~120 dtk, berhenti cepat jika server crash
        if server_error or port_open(PORT):
            break
        time.sleep(0.5)
    if server_error or not port_open(PORT):
        sys.exit("❌ Server FastAPI gagal start. Lihat pesan error di atas.")

    url = f"http://{HOST}:{PORT}"
    try:
        import webview
        webview.create_window("Shorts AutoBot — Hermes Office", url, width=1440, height=900, min_size=(1000, 650))
        try:   # simpan localStorage (notifikasi, platform terpilih) antar sesi
            webview.start(private_mode=False, storage_path=os.path.join(ROOT, ".webview"))
        except TypeError:   # pywebview lama tanpa opsi ini
            webview.start()
    except ImportError:
        import webbrowser
        print("pywebview belum terpasang -> membuka browser. (pip install pywebview)")
        webbrowser.open(url)
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass