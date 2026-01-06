#!/usr/bin/env python3
import time
import re
import os
from datetime import datetime

from relay import Relay
from db import init_db, insert_tx, get_setting, set_setting

# =========================================================
# CONFIG
# =========================================================
LOG_PATH = "/tmp/svxlink.log"
GPIO_RELAY = 12
ACTIVE_LOW = True

TRIGGER_SECONDS = 60
OFF_DELAY_SECONDS = 30

TX_START_RE = re.compile(r".*: Tx1: Turning the transmitter ON$")
TX_END_RE   = re.compile(r".*: Tx1: Turning the transmitter OFF$")

# =========================================================

def parse_log_timestamp(line: str) -> int:
    try:
        prefix = line.split(":", 1)[0]
        dt = datetime.strptime(prefix, "%a %b %d %H:%M:%S %Y")
        return int(dt.timestamp())
    except Exception:
        return int(time.time())

_last_written_state = None  # "ON"/"OFF"

def relay_set(relay: Relay, on: bool):
    global _last_written_state
    desired = "ON" if on else "OFF"
    if _last_written_state == desired:
        return
    if on:
        relay.on()
    else:
        relay.off()
    set_setting("relay_state", desired)
    _last_written_state = desired

def open_log_wait(path: str):
    # Attend que le fichier existe (important si /tmp est vide au boot)
    while not os.path.exists(path):
        print(f"[worker] attente du log: {path}")
        time.sleep(2)
    f = open(path, "r", errors="ignore")
    f.seek(0, 2)
    return f

def main():
    print("=== SVXLink TX Worker démarré ===")
    print("Log :", LOG_PATH)
    print("Relais GPIO :", GPIO_RELAY)
    print("Relais ON si TX >", TRIGGER_SECONDS, "s")
    print("Relais OFF après", OFF_DELAY_SECONDS, "s")

    init_db()
    relay = Relay(gpio=GPIO_RELAY, active_low=ACTIVE_LOW)
    relay_set(relay, False)

    tx_active = False
    tx_start_ts = None
    relay_triggered = False
    relay_off_at = None

    last_mode_check = 0.0
    last_manual_applied = None

    f = open_log_wait(LOG_PATH)

    while True:
        # si le fichier est recréé (rotation /tmp), on le ré-ouvre
        if not os.path.exists(LOG_PATH):
            try:
                f.close()
            except Exception:
                pass
            f = open_log_wait(LOG_PATH)

        now_wall = time.time()

        # --------- MODE manuel / auto ----------
        if now_wall - last_mode_check >= 0.2:
            last_mode_check = now_wall
            mode = get_setting("relay_mode", "AUTO")

            if mode == "MANUAL":
                manual = get_setting("relay_manual", "OFF")
                if manual != last_manual_applied:
                    relay_set(relay, manual == "ON")
                    last_manual_applied = manual
            else:
                last_manual_applied = None
                if relay_off_at and (time.time() >= relay_off_at) and (not tx_active):
                    relay_set(relay, False)
                    relay_off_at = None
                    print("RELAY OFF (delay elapsed)")

        # --------- lire une ligne ----------
        line = f.readline()
        if not line:
            time.sleep(0.05)
            continue

        line = line.rstrip("\n")
        now_log = parse_log_timestamp(line)

        # Si MANUAL -> ignorer TX
        if get_setting("relay_mode", "AUTO") == "MANUAL":
            continue

        # TX START
        if TX_START_RE.match(line):
            tx_active = True
            tx_start_ts = now_log
            relay_triggered = False
            relay_off_at = None
            print("TX START", datetime.fromtimestamp(now_log))
            continue

        # TX END
        if TX_END_RE.match(line) and tx_active and tx_start_ts:
            tx_active = False
            tx_end_ts = now_log
            duration, _day = insert_tx(tx_start_ts, tx_end_ts)
            print(f"TX END {datetime.fromtimestamp(now_log)} | durée={duration}s")

            relay_off_at = time.time() + OFF_DELAY_SECONDS

            tx_start_ts = None
            relay_triggered = False
            continue

        # pendant TX
        if tx_active and tx_start_ts and (not relay_triggered):
            elapsed = now_log - tx_start_ts
            if elapsed >= TRIGGER_SECONDS:
                relay_set(relay, True)
                relay_triggered = True
                print("RELAY ON (TX >", TRIGGER_SECONDS, "s)")

if __name__ == "__main__":
    main()

