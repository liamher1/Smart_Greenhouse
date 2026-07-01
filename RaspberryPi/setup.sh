#!/bin/bash
# One-time setup script for the Greenhouse Raspberry Pi server.
# Run once as root: sudo bash RaspberryPi/setup.sh
set -e

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PI_USER="${SUDO_USER:-pi}"
HOME_DIR="/home/$PI_USER"

HOTSPOT_SSID="Greenhouse"
HOTSPOT_PASSWORD="greenhouse2024"
HOTSPOT_IP="192.168.4.1"

echo "=== Installing dependencies ==="
apt-get update -q
apt-get install -y docker.io docker-compose nodejs npm python3-pip python3-venv

systemctl enable docker
usermod -aG docker "$PI_USER"

echo "=== Setting up WiFi hotspot ==="
# Works on Raspberry Pi OS Bookworm (NetworkManager) and Bullseye (dhcpcd)
if systemctl is-active --quiet NetworkManager; then
    nmcli device wifi hotspot ifname wlan0 ssid "$HOTSPOT_SSID" password "$HOTSPOT_PASSWORD" || true
    nmcli connection modify Hotspot \
        ipv4.addresses "$HOTSPOT_IP/24" \
        ipv4.method shared \
        connection.autoconnect yes
    nmcli connection up Hotspot || true
else
    # Fallback: hostapd + dnsmasq
    apt-get install -y hostapd dnsmasq

    cat > /etc/hostapd/hostapd.conf <<EOF
interface=wlan0
driver=nl80211
ssid=$HOTSPOT_SSID
hw_mode=g
channel=6
wmm_enabled=0
auth_algs=1
wpa=2
wpa_passphrase=$HOTSPOT_PASSWORD
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
EOF

    cat > /etc/dnsmasq.conf <<EOF
interface=wlan0
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
EOF

    cat >> /etc/dhcpcd.conf <<EOF
interface wlan0
    static ip_address=$HOTSPOT_IP/24
    nohook wpa_supplicant
EOF

    sed -i 's|#DAEMON_CONF=""|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' /etc/default/hostapd
    systemctl unmask hostapd
    systemctl enable hostapd dnsmasq
fi

echo "=== Installing Python dependencies ==="
cd "$REPO_DIR/Backend"
pip3 install -r requirements.txt --break-system-packages

echo "=== Building frontend ==="
cd "$REPO_DIR/Frontend"
npm install
npm run build

echo "=== Creating .env files from templates ==="
if [ ! -f "$REPO_DIR/Backend/.env" ]; then
    cp "$REPO_DIR/Backend/.env.example" "$REPO_DIR/Backend/.env"
    echo "  Created Backend/.env — edit it to set DB_PASSWORD before rebooting."
fi
if [ ! -f "$REPO_DIR/RaspberryPi/.env" ]; then
    cp "$REPO_DIR/RaspberryPi/.env.example" "$REPO_DIR/RaspberryPi/.env"
    echo "  Created RaspberryPi/.env — edit it to set ROBOFLOW_API_KEY before rebooting."
fi

echo "=== Starting infrastructure and seeding database ==="
cd "$REPO_DIR/Backend"
docker-compose up -d db mqtt
sleep 5
PYTHONPATH="$REPO_DIR/Backend/src" python3 "$REPO_DIR/Backend/seeds/seed_albion.py"
docker-compose stop

echo "=== Installing systemd services ==="
cp "$REPO_DIR/RaspberryPi/greenhouse-backend.service" /etc/systemd/system/
cp "$REPO_DIR/RaspberryPi/greenhouse-vision.service" /etc/systemd/system/

sed -i "s|__REPO_DIR__|$REPO_DIR|g" /etc/systemd/system/greenhouse-backend.service
sed -i "s|__REPO_DIR__|$REPO_DIR|g" /etc/systemd/system/greenhouse-vision.service
sed -i "s|__USER__|$PI_USER|g" /etc/systemd/system/greenhouse-backend.service
sed -i "s|__USER__|$PI_USER|g" /etc/systemd/system/greenhouse-vision.service

systemctl daemon-reload
systemctl enable greenhouse-backend greenhouse-vision

echo ""
echo "=== Setup complete ==="
echo "Hotspot SSID : $HOTSPOT_SSID"
echo "Hotspot Pass : $HOTSPOT_PASSWORD"
echo "Pi IP        : $HOTSPOT_IP"
echo "Dashboard    : http://$HOTSPOT_IP:8000"
echo ""
echo "Reboot the Pi to start everything automatically."
