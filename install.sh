#!/bin/bash
set -e

APP_DIR="/root/svx-dashboard"
PY="/usr/bin/python3"

echo "== Installation SVX Dashboard =="

cd "$APP_DIR"

# dépendances python
echo "[1/4] Installation des dépendances python..."
pip3 install --upgrade pip || true
pip3 install -r requirements.txt

# services systemd
echo "[2/4] Installation des services systemd..."

cat >/etc/systemd/system/svx-dashboard.service <<'EOF'
[Unit]
Description=SVX Dashboard (Flask web)
After=network.target
Wants=network.target

[Service]
Type=simple
WorkingDirectory=/root/svx-dashboard
ExecStart=/usr/bin/python3 /root/svx-dashboard/app.py
Restart=always
RestartSec=2
User=root
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

cat >/etc/systemd/system/svx-worker.service <<'EOF'
[Unit]
Description=SVX Worker (SVXLink log + relay control)
After=network.target svx-dashboard.service
Wants=network.target

[Service]
Type=simple
WorkingDirectory=/root/svx-dashboard
ExecStart=/usr/bin/python3 /root/svx-dashboard/worker.py
Restart=always
RestartSec=2
User=root
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable svx-dashboard.service
systemctl enable svx-worker.service

echo "[3/4] Démarrage des services..."
systemctl restart svx-dashboard.service
systemctl restart svx-worker.service

echo "[4/4] Terminé ✅"
echo "Dashboard: http://<IP_DU_PI>:8080/"
echo "Logs: journalctl -u svx-dashboard -f  |  journalctl -u svx-worker -f"

