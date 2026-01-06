from flask import Flask, jsonify, render_template, request, Response
from datetime import datetime
from functools import wraps
import os
import subprocess

from sensors import telemetry, start_dht_reader, dht_cached
from db import init_db, daily_stats, set_setting, get_setting

# ========= Meteo FFVL / balisemeteo =========
from ffvl_meteo import start_ffvl, ffvl_cached

# ======================================================
# CONFIG AUTHENTIFICATION
# ======================================================
AUTH_USER = "admin"
AUTH_PASS = "svxlink"
# ======================================================

app = Flask(__name__)
init_db()

# DHT en tâche de fond (ne bloque jamais l'API)
start_dht_reader(26)

# Météo en tâche de fond
start_ffvl(300)  # 5 minutes

# ------------------------------------------------------
# Auth Basic
# ------------------------------------------------------
def check_auth(username, password):
    return username == AUTH_USER and password == AUTH_PASS

def authenticate():
    return Response(
        "Accès protégé\n",
        401,
        {"WWW-Authenticate": 'Basic realm="SVX Dashboard"'}
    )

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# ------------------------------------------------------
# ROUTES
# ------------------------------------------------------
@app.route("/")
@requires_auth
def index():
    return render_template("index.html")

@app.route("/api/status")
@requires_auth
def status():
    today = datetime.now().strftime("%Y-%m-%d")
    return jsonify({
        "relay": {
            "mode": get_setting("relay_mode", "AUTO"),
            "manual": get_setting("relay_manual", "OFF"),
            "state": get_setting("relay_state", "OFF"),
        },
        "telemetry": telemetry(),
        "dht": dht_cached(),
        "ffvl": ffvl_cached(),
        "today": today,
        "daily": daily_stats(today),
    })

@app.route("/api/relay/auto", methods=["POST"])
@requires_auth
def relay_auto():
    set_setting("relay_mode", "AUTO")
    return jsonify(ok=True)

@app.route("/api/relay/manual", methods=["POST"])
@requires_auth
def relay_manual():
    state = (request.json or {}).get("state", "OFF").upper()
    if state not in ("ON", "OFF"):
        return jsonify(error="state must be ON or OFF"), 400
    set_setting("relay_mode", "MANUAL")
    set_setting("relay_manual", state)
    return jsonify(ok=True)

@app.route("/api/reboot", methods=["POST"])
@requires_auth
def reboot():
    # Répond tout de suite, puis redémarre
    def do_reboot():
        try:
            # préférable sur système avec systemd
            subprocess.Popen(["/bin/systemctl", "reboot"])
        except Exception:
            subprocess.Popen(["/sbin/reboot"])

    # lancer après un petit délai pour que la réponse HTTP parte
    subprocess.Popen(["/bin/sh", "-c", "sleep 1; /bin/systemctl reboot || /sbin/reboot"])
    return jsonify(ok=True, message="Redémarrage en cours...")

# ------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, threaded=True)

