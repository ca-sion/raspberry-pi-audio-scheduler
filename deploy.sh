#!/bin/bash

# =============================================================================
# Script de Déploiement et Mise à Jour pour Raspberry Pi
# =============================================================================
# Ce script automatise le transfert des fichiers, l'installation des dépendances,
# et la configuration/redémarrage des services systemd sur un Raspberry Pi.
# Il utilise les variables d'environnement définies dans un fichier .env local.
#
# À exécuter depuis le dossier racine de votre projet (là où se trouve deploy.sh).
# =============================================================================

# --- Configuration du Script ---
set -e
set -u
set -o pipefail

# --- Chemin du fichier .env local ---
LOCAL_ENV_FILE=".env"

# --- Chemin du projet local ---
LOCAL_PROJECT_DIR=$(pwd)

# --- Vérification et Chargement du fichier .env local ---
if [ ! -f "$LOCAL_ENV_FILE" ]; then
    echo "ERREUR: Le fichier .env local n'a pas été trouvé à la racine du répertoire courant."
    echo "Créez un fichier '.env' en vous basant sur '.env.example' et remplissez les variables."
    exit 1
fi

# --- S'assurer que le répertoire audio existe localement
if [ ! -d "${LOCAL_PROJECT_DIR}/audio" ]; then
    echo "ATTENTION: Le dossier 'audio' n'existe pas. Création d'un dossier vide."
    mkdir -p "${LOCAL_PROJECT_DIR}/audio"
fi

# --- Chargement des variables d'environnement depuis .env de manière portable ---
set -a # Exporte automatiquement toutes les variables qui suivent
. "$LOCAL_ENV_FILE" # Charge les variables du fichier .env
set +a # Arrête l'exportation automatique

# --- Vérification que les variables essentielles du .env sont chargées ---
if [ -z "${RASPBERRY_PI_HOST+x}" ]; then echo "ERREUR: La variable RASPBERRY_PI_HOST n'a pas été trouvée dans le fichier .env."; exit 1; fi
if [ -z "${RASPBERRY_PI_USER+x}" ]; then echo "ERREUR: La variable RASPBERRY_PI_USER n'a pas été trouvée dans le fichier .env."; exit 1; fi
if [ -z "${PI_PROJECT_ROOT+x}" ]; then echo "ERREUR: La variable PI_PROJECT_ROOT n'a pas été trouvée dans le fichier .env."; exit 1; fi
if [ -z "${AP_SSID+x}" ]; then echo "ERREUR: La variable AP_SSID n'a pas été trouvée dans le fichier .env."; exit 1; fi
if [ -z "${AP_WIFI_PASSWORD+x}" ]; then echo "ERREUR: La variable AP_WIFI_PASSWORD n'a pas été trouvée dans le fichier .env."; exit 1; fi


# --- Variables de configuration du projet ---
PYTHON_DEPS="flask flask-cors python-dotenv"
FLASK_SERVICE_NAME="pi-audio-api"
AUDIO_PLAYER_SERVICE_NAME="pi-audio-player"
AP_SERVICE_NAME="configure-ap"


# --- Fonctions utilitaires ---
function ssh_exec() {
    ssh "$RASPBERRY_PI_USER@$RASPBERRY_PI_HOST" "$@"
    if [ $? -ne 0 ]; then
      echo "Erreur: Échec de la commande SSH. Sortie."
      exit 1
    fi
}

function create_systemd_service() {
    SERVICE_NAME=$1
    DESCRIPTION=$2
    PYTHON_SCRIPT=$3
    AFTER_SERVICE=$4

    echo "   -> Création/Mise à jour du service Systemd pour ${SERVICE_NAME}..."
    ssh_exec "sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null <<EOF
[Unit]
Description=${DESCRIPTION}
After=${AFTER_SERVICE}

[Service]
ExecStart=${PI_PROJECT_ROOT}/venv/bin/python3 ${PI_PROJECT_ROOT}/${PYTHON_SCRIPT}
WorkingDirectory=${PI_PROJECT_ROOT}
Restart=always
User=${RASPBERRY_PI_USER}
Environment=IS_RASPBERRY_PI=True
Environment=FLASK_APP=${PI_PROJECT_ROOT}/api.py

[Install]
WantedBy=multi-user.target
EOF
"

    ssh_exec "sudo systemctl daemon-reload"
    ssh_exec "sudo systemctl enable ${SERVICE_NAME}"
    ssh_exec "sudo systemctl restart ${SERVICE_NAME}"
}

# --- Déploiement ---

echo "--- Démarrage du déploiement vers ${RASPBERRY_PI_USER}@${RASPBERRY_PI_HOST} ---"

# 1. Créer les dossiers de destination sur le Raspberry Pi
echo "--- 1. Création des dossiers de destination ---"
ssh_exec "mkdir -p ${PI_PROJECT_ROOT}/etc ${PI_PROJECT_ROOT}/audio ${PI_PROJECT_ROOT}/logs"

# 2. Copier les fichiers essentiels du projet
echo "--- 2. Copie des fichiers du projet ---"
scp -r ${LOCAL_PROJECT_DIR}/.env ${LOCAL_PROJECT_DIR}/*.py ${LOCAL_PROJECT_DIR}/*.html ${LOCAL_PROJECT_DIR}/audio/ ${RASPBERRY_PI_USER}@${RASPBERRY_PI_HOST}:${PI_PROJECT_ROOT}/
if [ $? -ne 0 ]; then echo "Erreur: Échec de la copie des fichiers. Sortie."; exit 1; fi

# 3. Copier les scripts de configuration
echo "--- 3. Copie des scripts de configuration ---"
scp ${LOCAL_PROJECT_DIR}/config_ap.sh ${RASPBERRY_PI_USER}@${RASPBERRY_PI_HOST}:${PI_PROJECT_ROOT}/
if [ $? -ne 0 ]; then echo "Erreur: Échec de la copie de config_ap.sh. Sortie."; exit 1; fi

# 4. Copier le fichier de service pour le point d'accès
echo "--- 4. Copie du service systemd pour le point d'accès ---"
scp ${LOCAL_PROJECT_DIR}/configure-ap.service ${RASPBERRY_PI_USER}@${RASPBERRY_PI_HOST}:${PI_PROJECT_ROOT}/etc/
if [ $? -ne 0 ]; then echo "Erreur: Échec de la copie de configure-ap.service. Sortie."; exit 1; fi

# 5. Installation du lecteur audio (mpv)
echo "--- 5. Installation du lecteur audio mpv ---"
ssh_exec "sudo apt-get update && sudo apt-get install -y mpv"

# 6. Configuration du point d'accès et installation de ses services
echo "--- 6. Configuration du point d'accès Wi-Fi (hostapd, dnsmasq) ---"
# Utilisation de 'AP_PASSWORD' qui est attendu par 'config_ap.sh', en lui passant la valeur de 'AP_WIFI_PASSWORD'
ssh_exec "export AP_SSID='${AP_SSID}' && export AP_PASSWORD='${AP_WIFI_PASSWORD}' && sudo ${PI_PROJECT_ROOT}/config_ap.sh"
echo "   Point d'accès configuré avec succès."

# 7. Installation des dépendances Python dans un environnement virtuel
echo "--- 7. Installation des dépendances Python (${PYTHON_DEPS}) ---"
ssh_exec "
    cd ${PI_PROJECT_ROOT} && \
    python3 -m venv venv && \
    source venv/bin/activate && \
    pip install ${PYTHON_DEPS} && \
    deactivate
"
echo "   Dépendances Python installées dans l'environnement virtuel."

# 8. Création et redémarrage des services Systemd
echo "--- 8. Création et redémarrage des services Systemd ---"
create_systemd_service "${FLASK_SERVICE_NAME}" "Flask API for Audio Player" "api.py" "${AP_SERVICE_NAME}"
create_systemd_service "${AUDIO_PLAYER_SERVICE_NAME}" "Audio Player Scheduler" "audio_player.py" "${FLASK_SERVICE_NAME}"
echo "   Services Flask et Audio Player créés/mis à jour."

# 9. Nettoyage et finalisation
echo "--- 9. Nettoyage et finalisation ---"
ssh_exec "sudo chmod 700 ${PI_PROJECT_ROOT}/config_ap.sh"
ssh_exec "sudo mv ${PI_PROJECT_ROOT}/etc/configure-ap.service /etc/systemd/system/${AP_SERVICE_NAME}.service"
ssh_exec "sudo systemctl daemon-reload"
ssh_exec "sudo systemctl enable ${AP_SERVICE_NAME}"
ssh_exec "sudo systemctl start ${AP_SERVICE_NAME}"
echo "   Service de configuration du point d'accès démarré."

echo ""
echo "==================================================================="
echo "           DÉPLOIEMENT TERMINÉ AVEC SUCCÈS ! 🎉"
echo "==================================================================="
echo "Accédez à l'interface via : http://${RASPBERRY_PI_HOST}:5000"
echo "Pour vérifier les logs sur le Pi (via SSH) :"
echo "  - Service API : journalctl -u ${FLASK_SERVICE_NAME} -f"
echo "  - Service planificateur : journalctl -u ${AUDIO_PLAYER_SERVICE_NAME} -f"
echo "  - Service point d'accès : journalctl -u ${AP_SERVICE_NAME} -f"