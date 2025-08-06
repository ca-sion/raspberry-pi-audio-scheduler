#!/bin/bash

# ==============================================================================
# Script de configuration du Point d'Accès Wi-Fi
# ==============================================================================
# Ce script installe et configure hostapd et dnsmasq pour que le Raspberry Pi
# agisse comme un point d'accès Wi-Fi indépendant.
#
# À noter: La configuration de l'adresse IP et des mots de passe provient
# des variables d'environnement (si elles sont définies) ou des valeurs par défaut.
# ==============================================================================

set -e
set -u
set -o pipefail

echo "--- Démarrage de la configuration du point d'accès Wi-Fi ---"

# --- Variables de configuration ---
# Les variables sont lues depuis le .env (déployé par le script principal)
# Si elles ne sont pas définies, des valeurs par défaut sont utilisées.
WLAN_INTERFACE=${WLAN_INTERFACE:-wlan0}
AP_SSID=${AP_SSID:-raspberrypi-audio}
AP_PASSWORD=${AP_PASSWORD:-password}
AP_IP=${AP_IP:-192.168.1.1}

# --- Vérification des Prérequis ---
if [ "$EUID" -ne 0 ]; then
  echo "Ce script doit être exécuté avec les privilèges root. Veuillez utiliser sudo."
  exit 1
fi

# 1. Installation des dépendances
echo "--- Installation des dépendances (hostapd, dnsmasq) ---"
apt update
apt install -y hostapd dnsmasq

# 2. Configuration de l'interface Wi-Fi
echo "--- Configuration de l'interface Wi-Fi ($WLAN_INTERFACE) ---"
ip a flush dev $WLAN_INTERFACE
ip a add $AP_IP/24 dev $WLAN_INTERFACE

# 3. Configuration de hostapd
echo "--- Écriture du fichier /etc/hostapd/hostapd.conf ---"
cat > /etc/hostapd/hostapd.conf <<EOF
interface=$WLAN_INTERFACE
ssid=$AP_SSID
hw_mode=g
channel=7
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=$AP_PASSWORD
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
EOF

# 4. Configuration de dnsmasq
echo "--- Écriture du fichier /etc/dnsmasq.conf ---"
cat > /etc/dnsmasq.conf <<EOF
interface=$WLAN_INTERFACE
dhcp-range=$AP_IP,192.168.0.254,12h
EOF

# 5. Démarrage des services
echo "--- Démarrage des services hostapd et dnsmasq ---"
systemctl unmask hostapd
systemctl enable hostapd
systemctl start hostapd
systemctl enable dnsmasq
systemctl start dnsmasq

# 6. Activation du routage IP
echo "--- Activation du routage IP ---"
sysctl net.ipv4.ip_forward=1
echo "net.ipv4.ip_forward=1" > /etc/sysctl.d/99-ip-forward.conf

echo "--- Configuration du point d'accès Wi-Fi terminée ---"