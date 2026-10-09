"""Klien Ollama tanpa dependensi (urllib). 100% gratis & lokal.
Setup:  ollama pull hermes3:8b   (atau set OLLAMA_MODEL=llama3.2 / qwen2.5:7b)"""
import json
import os
import urllib.request

HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
MODEL = os.getenv("OLLAMA_MODEL") or os.getenv("HERMES_MODEL") or "hermes3:8b"   # satu model untuk Python & Hermes3D
ACTIONS = {"none", "start", "stop", "generate"}


def _call(path, payload=None, timeout=120):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(HOST + path, data, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def chat(messages, json_mode=False, timeout=120, **options):
    p = {"model": MODEL, "messages": messages, "stream": False, "keep_alive": os.getenv("OLLAMA_KEEP_ALIVE", "10m")}
    if json_mode:
        p["format"] = "json"
    if options:
        p["options"] = options
    return _call("/api/chat", p, timeout)["message"]["content"]


def status():
    try:
        names = [m["name"] for m in _call("/api/tags", timeout=3).get("models", [])]
        want = MODEL if ":" in MODEL else MODEL + ":latest"      # "llama3.2" == "llama3.2:latest"
        return {"online": True, "model": MODEL, "installed": MODEL in names or want in names, "models": names}
    except Exception as exc:
        return {"online": False, "model": MODEL, "installed": False, "models": [], "error": str(exc)}


def _json(raw):
    try:
        return json.loads(raw)
    except ValueError:
        a, b = raw.find("{"), raw.rfind("}")
        return json.loads(raw[a:b + 1])


def generate_script(niche, topic, hook_style):
    """Sama dengan modules.script_gen.generate_script (naskah > 1 menit, hook_text, callouts)."""
    from modules.script_gen import build_prompt, _normalize, MIN_WORDS
    prompt = build_prompt(niche, topic, hook_style)
    sys_p = "Kamu penulis naskah YouTube Shorts berbahasa Indonesia. Balas HANYA JSON valid sesuai format yang diminta."
    best, last = None, None
    for _ in range(3):
        try:
            d = _normalize(_json(chat([{"role": "system", "content": sys_p}, {"role": "user", "content": prompt}],
                                      json_mode=True, timeout=300, temperature=0.7, num_predict=4096)))
            if best is None or len(d["script"].split()) > len(best["script"].split()):
                best = d
            if len(d["script"].split()) >= MIN_WORDS:
                break
        except Exception as exc:
            last = exc
    if best is None:
        raise RuntimeError(f"Ollama gagal membuat naskah: {last}")
    return best


SYSTEM = ("Kamu MorbMyth, CEO kantor virtual bot YouTube Shorts. Timmu: KaelQuill (scriptwriter), VoxArden (voice actor), MikaPixel (designer), RivenCut (editor). "
          "Jawab singkat, ramah, bahasa Indonesia santai. Balas HANYA JSON: "
          '{"reply": "...", "action": "none|start|stop|generate"}. '
          "start=jalankan automation, stop=hentikan, generate=buat 5 ide konten baru; pakai hanya jika user jelas memintanya. "
          "Konteks saat ini: ")


def hermes_chat(text, ctx):
    raw = chat([{"role": "system", "content": SYSTEM + json.dumps(ctx, ensure_ascii=False)},
                {"role": "user", "content": text}], json_mode=True, timeout=90, temperature=0.4)
    try:
        d = _json(raw)
    except Exception:
        d = {"reply": raw, "action": "none"}
    if d.get("action") not in ACTIONS:
        d["action"] = "none"
    d["reply"] = str(d.get("reply", "")).strip() or "…"
    return d