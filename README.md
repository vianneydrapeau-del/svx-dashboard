# SVX Dashboard (SVXLink + GPIO + DHT + Météo)

## Fonctionnalités
- Interface web (Flask) protégée par mot de passe
- Relais GPIO12 (actif LOW) : AUTO / MANUEL + temporisations
- DHT11 sur GPIO26 (temp/hum)
- Télémetrie Raspberry (CPU/RAM/DISK/Temp CPU)
- Météo balisemeteo (Petit Ballon 5013) via parsing page
- Services systemd (auto-start + restart)

## Câblage
- Relais: GPIO12 (BCM 12), GND, +V selon module relais
- DHT11: GPIO26 (BCM 26), 3.3V, GND

## Installation sur un nouveau Raspberry (root)
```bash
apt-get update || true
apt-get install -y git python3-pip || true

cd /root
git clone https://github.com/vianneydrapeau-del/svx-dashboard
cd svx-dashboard
./install.sh

