"""modules/social_oauth.py — route OAuth untuk TikTok & Meta (Instagram + Facebook)."""
import html
import webbrowser

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from modules import social_real as social

router = APIRouter()


def _page(title, body, ok):
    color = "#0F9D58" if ok else "#D93025"
    return HTMLResponse(
        f"<!doctype html><meta charset=utf-8><title>{html.escape(title)}</title>"
        f"<body style='font-family:system-ui;text-align:center;padding:60px'>"
        f"<h2 style='color:{color}'>{html.escape(title)}</h2><p>{html.escape(body)}</p>"
        f"<p>Jendela ini boleh ditutup.</p><script>setTimeout(()=>window.close(),2500)</script>")


@router.get("/api/oauth/{pid}/start")
def oauth_start(pid: str, open: bool = False):
    """open=true: buka browser sistem (server jalan lokal; pywebview tidak mendukung popup)."""
    try:
        url = social.auth_url(pid)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    opened = False
    if open:
        try:
            opened = bool(webbrowser.open(url))
        except Exception:
            opened = False
    return {"auth_url": url, "opened": opened}


@router.get("/api/oauth/{provider}/callback")
def oauth_callback(provider: str, code: str = "", state: str = "", error: str = "",
                   error_description: str = "", error_reason: str = ""):
    if error or not code:
        return _page("Login dibatalkan", error_description or error_reason or error or "Tidak ada kode otorisasi.", False)
    try:
        pids = social.handle_callback(provider, code, state)
    except Exception as exc:
        print(f"❌ OAuth {provider} gagal: {exc}")
        return _page("Gagal menghubungkan", str(exc), False)
    names = ", ".join(social.PLATFORMS[p]["label"] for p in pids)
    print(f"✅ OAuth {provider}: terhubung → {names}")
    return _page("Berhasil terhubung", names, True)