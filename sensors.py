import time
import threading
import psutil

# ======= Cache DHT (mis à jour en fond) =======
_dht_lock = threading.Lock()
_dht_data = {"temp": None, "hum": None, "ts": 0}
_dht_started = False

def cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return int(f.read()) / 1000.0
    except Exception:
        return None

def telemetry():
    # interval=0.0 => non bloquant
    return {
        "cpu": psutil.cpu_percent(interval=0.0),
        "ram": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage("/").percent,
        "temp_cpu": cpu_temp()
    }

def _dht_thread(gpio=26, period_s=3):
    # Import dans le thread (évite soucis au chargement)
    try:
        import board
        import adafruit_dht
        # Pour DHT11 sur GPIO26 => board.D26
        dht = adafruit_dht.DHT11(board.D26)
    except Exception:
        dht = None

    while True:
        temp = None
        hum = None
        try:
            if dht is not None:
                # adafruit_dht peut lever RuntimeError souvent -> normal
                temp = dht.temperature
                hum = dht.humidity
        except Exception:
            pass

        with _dht_lock:
            # On met à jour même si None, mais on garde la dernière valeur valide si dispo
            if temp is not None:
                _dht_data["temp"] = temp
            if hum is not None:
                _dht_data["hum"] = hum
            _dht_data["ts"] = int(time.time())

        time.sleep(period_s)

def start_dht_reader(gpio=26):
    global _dht_started
    if _dht_started:
        return
    _dht_started = True
    t = threading.Thread(target=_dht_thread, args=(gpio,), daemon=True)
    t.start()

def dht_cached():
    with _dht_lock:
        return {"temp": _dht_data["temp"], "hum": _dht_data["hum"], "ts": _dht_data["ts"]}

