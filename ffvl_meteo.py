import time
import threading
import re
from urllib.request import urlopen, Request

BALISE_ID = 5013
URL = f"https://www.balisemeteo.com/balise.php?idBalise={BALISE_ID}"

_lock = threading.Lock()
_started = False

_cache = {
    "ok": False,
    "station": "FFVL 5013 - Petit Ballon",
    "releve": None,
    "wind_avg_kmh": None,
    "wind_avg_dir_deg": None,
    "wind_max_kmh": None,
    "wind_max_dir_deg": None,
    "temp_c": None,
    "ts": 0,
    "error": None,
    "source": URL,
}

DEG = r"(?:°|&deg;|&#176;|&#xB0;)"
KMH = r"km\s*/?\s*h"

def _fetch_html(url: str) -> str:
    req = Request(url, headers={
        "User-Agent": "svx-dashboard/1.0",
        "Accept": "text/html,*/*",
        "Accept-Encoding": "identity",
    })
    with urlopen(req, timeout=10) as r:
        return r.read().decode("utf-8", errors="ignore")

def _html_to_text(html: str) -> str:
    # remplace entités de base
    html = html.replace("&nbsp;", " ").replace("&deg;", "°").replace("&#176;", "°").replace("&#xB0;", "°")
    # enlève scripts/styles
    html = re.sub(r"<script.*?>.*?</script>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    html = re.sub(r"<style.*?>.*?</style>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    # enlève toutes balises
    text = re.sub(r"<[^>]+>", " ", html)
    # compact espaces
    text = re.sub(r"\s+", " ", text).strip()
    return text

def _to_int(s):
    try:
        return int(s)
    except Exception:
        return None

def _to_float(s):
    try:
        return float(s)
    except Exception:
        return None

def _norm_dir(d):
    if d is None:
        return None
    if d == 65535:
        return None
    return d

def _find(pattern: str, text: str):
    m = re.search(pattern, text, flags=re.IGNORECASE)
    return m.group(1) if m else None

def _parse_from_text(text: str):
    # Relevé
    releve = _find(r"Relev[ée]\s+du\s+(\d{2}/\d{2}/\d{4}\s*-\s*\d{2}:\d{2})", text)

    # Température (très stable)
    temp = _find(rf"Temp[ée]rature\s*:\s*([-+]?\d+(?:\.\d+)?)\s*{DEG}", text)

    # Vent moyen / maxi (on prend la première occurrence après les mots clés)
    # On accepte différents libellés
    avg_spd = None
    max_spd = None
    avg_dir = None
    max_dir = None

    # Vent moyen: chercher une zone autour de "Vent moyen"
    m = re.search(r"Vent\s*moyen(.{0,200})", text, flags=re.IGNORECASE)
    if m:
        chunk = m.group(1)
        avg_spd = _find(rf"Vitesse\s*:\s*([0-9]+)\s*{KMH}", chunk)
        avg_dir = _find(rf"Direction\s*:\s*:?\s*([0-9]+)\s*{DEG}", chunk)

    # Vent maxi: autour de "Vent maxi"
    m = re.search(r"Vent\s*maxi(.{0,200})", text, flags=re.IGNORECASE)
    if m:
        chunk = m.group(1)
        max_spd = _find(rf"Vitesse\s*:\s*([0-9]+)\s*{KMH}", chunk)
        max_dir = _find(rf"Direction\s*:\s*:?\s*([0-9]+)\s*{DEG}", chunk)

    return {
        "releve": releve,
        "temp_c": _to_float(temp),
        "wind_avg_kmh": _to_float(avg_spd),
        "wind_avg_dir_deg": _norm_dir(_to_int(avg_dir)),
        "wind_max_kmh": _to_float(max_spd),
        "wind_max_dir_deg": _norm_dir(_to_int(max_dir)),
    }

def _worker(period_s=120):
    while True:
        try:
            html = _fetch_html(URL)
            text = _html_to_text(html)
            data = _parse_from_text(text)
            with _lock:
                _cache.update(data)
                _cache["ok"] = True
                _cache["error"] = None
                _cache["ts"] = int(time.time())
        except Exception as e:
            with _lock:
                _cache["ok"] = False
                _cache["error"] = str(e)
                _cache["ts"] = int(time.time())
        time.sleep(period_s)

def start_ffvl(period_s=120):
    global _started
    if _started:
        return
    _started = True
    t = threading.Thread(target=_worker, args=(period_s,), daemon=True)
    t.start()

def ffvl_cached():
    with _lock:
        return dict(_cache)

